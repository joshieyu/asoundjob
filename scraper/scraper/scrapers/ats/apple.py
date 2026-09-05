from __future__ import annotations

import asyncio
import html
import json
import logging
import re
from time import monotonic
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, quote, urlsplit

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_html, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

SEARCH_URL = "https://jobs.apple.com/en-us/search?search={term}&page={page}"
DEFAULT_SEARCH_TERM = "audio"
MAX_SEARCH_TERM_LEN = 40
DETAIL_URL = "https://jobs.apple.com/en-us/details/{job_id}/{slug}"
HYDRATION_RE = re.compile(
    r'__staticRouterHydrationData\s*=\s*JSON\.parse\("(.*?)"\);',
    re.DOTALL,
)
PAGE_SIZE = 20
MAX_PAGES = 20
DETAIL_FETCH_CONCURRENCY = 8
ENRICHMENT_BUDGET_FRACTION = 0.85

EMPLOYMENT_TYPE_MAP = {
    "standard": "full-time",
    "part time": "part-time",
    "part-time": "part-time",
    "intern": "internship",
    "internship": "internship",
    "contractor": "contract",
    "contract": "contract",
    "temporary": "temporary",
}


class AppleScraper(BaseScraper):
    name = "apple"

    def can_handle(self, company: Company) -> bool:
        if not company.careers_url:
            return False
        return "jobs.apple.com" in company.careers_url.strip().lower()

    @staticmethod
    def extract_slug(url: str) -> str | None:
        return "apple" if "jobs.apple.com" in url.lower() else None

    @staticmethod
    def search_term(careers_url: str | None) -> str:
        if not careers_url:
            return DEFAULT_SEARCH_TERM
        query = urlsplit(careers_url.strip()).query
        for key, value in parse_qsl(query, keep_blank_values=True):
            if key.strip().lower() != "search":
                continue
            term = value.strip()
            if term:
                return term[:MAX_SEARCH_TERM_LEN]
        return DEFAULT_SEARCH_TERM

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        start = monotonic()
        term = self.search_term(company.careers_url)
        pairs: list[tuple[RawJob, str | None]] = []
        for page in range(1, MAX_PAGES + 1):
            url = SEARCH_URL.format(term=quote(term, safe=""), page=page)
            html_text = await asyncio.to_thread(fetch_html, url, self.settings)
            page_pairs = _parse_search_page_with_teams(html_text)
            if not page_pairs:
                break
            pairs.extend(page_pairs)
            if len(page_pairs) < PAGE_SIZE:
                break

        deadline = start + self.settings.per_company_timeout * ENRICHMENT_BUDGET_FRACTION
        semaphore = asyncio.Semaphore(DETAIL_FETCH_CONCURRENCY)
        counts = {"enriched": 0, "budget_skipped": 0}
        await asyncio.gather(
            *(
                self._enrich_job(job, team_name, semaphore, deadline, counts)
                for job, team_name in pairs
            )
        )
        if counts["budget_skipped"] > 0:
            logger.info(
                "apple: enrichment budget exhausted, enriched %d/%d jobs",
                counts["enriched"],
                len(pairs),
            )
        return [job for job, _team_name in pairs]

    async def _enrich_job(
        self,
        job: RawJob,
        team_name: str | None,
        semaphore: asyncio.Semaphore,
        deadline: float,
        counts: dict[str, int],
    ) -> None:
        async with semaphore:
            if monotonic() >= deadline:
                counts["budget_skipped"] += 1
                return
            try:
                detail_html = await asyncio.to_thread(fetch_html, job.url, self.settings)
                jobs_data = _extract_jobs_data(detail_html)
            except Exception as exc:
                logger.warning(
                    "apple: detail fetch failed for %s: %s", job.url, exc
                )
                return
        if jobs_data is None:
            logger.warning("apple: detail page had no job data for %s", job.url)
            return
        _apply_jobs_data(job, team_name, jobs_data)
        counts["enriched"] += 1


def _parse_search_page(html_text: str) -> list[RawJob]:
    return [job for job, _team_name in _parse_search_page_with_teams(html_text)]


def _parse_search_page_with_teams(html_text: str) -> list[tuple[RawJob, str | None]]:
    data = _extract_hydration_data(html_text)
    if data is None:
        return []
    search = data.get("loaderData", {}).get("search", {})
    results = search.get("searchResults", [])
    pairs: list[tuple[RawJob, str | None]] = []
    for item in results:
        job = _parse_result(item)
        if job is None:
            continue
        team = item.get("team") or {}
        team_name = team.get("teamName") if isinstance(team, dict) else None
        pairs.append((job, team_name))
    return pairs


def _extract_hydration_data(html_text: str) -> dict[str, Any] | None:
    m = HYDRATION_RE.search(html_text)
    if not m:
        return None
    raw = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("failed to parse apple hydration data: %s", exc)
        return None


def _extract_jobs_data(html_text: str) -> dict[str, Any] | None:
    data = _extract_hydration_data(html_text)
    if data is None:
        return None
    job_details = data.get("loaderData", {}).get("jobDetails")
    if not isinstance(job_details, dict):
        return None
    jobs_data = job_details.get("jobsData")
    if not isinstance(jobs_data, dict):
        return None
    return jobs_data


def _parse_result(item: dict[str, Any]) -> RawJob | None:
    title = (item.get("postingTitle") or "").strip()
    if not title:
        return None
    job_id = item.get("id") or item.get("reqId") or ""
    slug = item.get("transformedPostingTitle") or ""
    url = DETAIL_URL.format(job_id=job_id, slug=slug) if job_id else ""
    if not url:
        return None
    locations = item.get("locations") or []
    location = _format_location(locations)
    team = item.get("team") or {}
    team_name = team.get("teamName") if isinstance(team, dict) else None
    description = _compose_description(
        team_name=team_name, job_summary=item.get("jobSummary")
    )
    posted = _parse_apple_date(item.get("postingDate"))
    return RawJob(
        title=title,
        url=url,
        external_id=job_id,
        location=location,
        description=description,
        posted_date=posted,
    )


def _apply_jobs_data(
    job: RawJob, team_name: str | None, jobs_data: dict[str, Any]
) -> None:
    composed = _compose_description(
        team_name=team_name,
        job_summary=jobs_data.get("jobSummary"),
        description=jobs_data.get("description"),
        responsibilities=jobs_data.get("responsibilities"),
        minimum_qualifications=jobs_data.get("minimumQualifications"),
        preferred_qualifications=jobs_data.get("preferredQualifications"),
        pay_benefits=_extract_pay_benefits(jobs_data.get("postingFooters")),
    )
    if composed:
        job.description = composed
    job_type = _map_employment_type(jobs_data.get("employmentType"))
    if job_type:
        job.job_type = job_type


def _compose_description(
    team_name: str | None,
    job_summary: str | None,
    description: str | None = None,
    responsibilities: str | None = None,
    minimum_qualifications: str | None = None,
    preferred_qualifications: str | None = None,
    pay_benefits: str | None = None,
) -> str | None:
    parts: list[str] = []
    if team_name:
        parts.append(f"<p>Team: {html.escape(team_name)}</p>")
    if job_summary:
        parts.append(f"<p>{html.escape(job_summary)}</p>")
    if description:
        parts.append(f"<p>{html.escape(description)}</p>")
    _append_bullet_section(parts, "Responsibilities", responsibilities)
    _append_bullet_section(parts, "Minimum Qualifications", minimum_qualifications)
    _append_bullet_section(parts, "Preferred Qualifications", preferred_qualifications)
    if pay_benefits:
        parts.append(f"<h3>Pay &amp; Benefits</h3>\n{pay_benefits}")
    if not parts:
        return None
    return "\n".join(parts)


def _append_bullet_section(parts: list[str], heading: str, text: str | None) -> None:
    if not text:
        return
    items = [line.strip() for line in text.split("\n") if line.strip()]
    if not items:
        return
    list_items = "\n".join(f"<li>{html.escape(item)}</li>" for item in items)
    parts.append(f"<h3>{heading}</h3>\n<ul>\n{list_items}\n</ul>")


def _extract_pay_benefits(footers: Any) -> str | None:
    if not isinstance(footers, list):
        return None
    for footer in footers:
        if not isinstance(footer, dict):
            continue
        localizations = footer.get("localizations")
        if not isinstance(localizations, dict):
            continue
        for entries in localizations.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and entry.get("name") == "Pay & Benefits":
                    content = entry.get("content")
                    if content:
                        return str(content)
    return None


def _map_employment_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return EMPLOYMENT_TYPE_MAP.get(value.strip().lower())


def _format_location(locations: list[dict[str, Any]]) -> str | None:
    if not locations:
        return None
    first = locations[0]
    name = first.get("name")
    if name:
        return str(name)
    city = first.get("city")
    country = first.get("countryName")
    if city and country:
        return f"{city}, {country}"
    return city or country or None


def _parse_apple_date(value: str | None) -> Any:
    if not value:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            from datetime import datetime

            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return parse_date(value)
