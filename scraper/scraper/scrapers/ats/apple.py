from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Any

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_html, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

SEARCH_URL = "https://jobs.apple.com/en-us/search?search=audio&page={page}"
DETAIL_URL = "https://jobs.apple.com/en-us/details/{job_id}/{slug}"
HYDRATION_RE = re.compile(
    r'__staticRouterHydrationData\s*=\s*JSON\.parse\("(.*?)"\);',
    re.DOTALL,
)
PAGE_SIZE = 20
MAX_PAGES = 20


class AppleScraper(BaseScraper):
    name = "apple"

    def can_handle(self, company: Company) -> bool:
        if not company.careers_url:
            return False
        return "jobs.apple.com" in company.careers_url.strip().lower()

    @staticmethod
    def extract_slug(url: str) -> str | None:
        return "apple" if "jobs.apple.com" in url.lower() else None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        jobs: list[RawJob] = []
        for page in range(1, MAX_PAGES + 1):
            url = SEARCH_URL.format(page=page)
            html = await asyncio.to_thread(fetch_html, url, self.settings)
            page_jobs = _parse_search_page(html)
            if not page_jobs:
                break
            jobs.extend(page_jobs)
            if len(page_jobs) < PAGE_SIZE:
                break
        return jobs


def _parse_search_page(html: str) -> list[RawJob]:
    data = _extract_hydration_data(html)
    if data is None:
        return []
    search = data.get("loaderData", {}).get("search", {})
    results = search.get("searchResults", [])
    return [_parse_result(item) for item in results if _parse_result(item) is not None]  # type: ignore[misc]


def _extract_hydration_data(html: str) -> dict[str, Any] | None:
    m = HYDRATION_RE.search(html)
    if not m:
        return None
    raw = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("failed to parse apple hydration data: %s", exc)
        return None


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
    description = item.get("jobSummary")
    team = item.get("team") or {}
    team_name = team.get("teamName") if isinstance(team, dict) else None
    if team_name and description:
        description = f"<p>Team: {team_name}</p>\n{description}"
    posted = _parse_apple_date(item.get("postingDate"))
    return RawJob(
        title=title,
        url=url,
        external_id=job_id,
        location=location,
        description=description,
        posted_date=posted,
    )


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
