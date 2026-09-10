from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, quote, urlparse

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?P<slug>[a-z0-9-]{1,63})\.eightfold\.ai",
    re.IGNORECASE,
)

SEARCH_PATH = "/api/pcsx/search"
DETAIL_PATH = "/api/pcsx/position_details"

MAX_PAGES = 20
MAX_DETAIL_FETCHES = 200
ENRICHMENT_BUDGET_FRACTION = 0.85

SPECIAL_SECOND_LEVEL_LABELS = frozenset({"co", "com", "net", "org", "ac", "gov", "edu"})


def registrable_domain(host: str) -> str:
    cleaned = host.strip().lower().rstrip(".")
    labels = cleaned.split(".")
    if len(labels) <= 2:
        return cleaned
    second_last = labels[-2]
    last = labels[-1]
    if second_last in SPECIAL_SECOND_LEVEL_LABELS and len(last) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


class EightfoldScraper(BaseScraper):
    name = "eightfold"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "eightfold":
            return True
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        careers_url = (company.careers_url or "").strip()
        parsed = urlparse(careers_url)
        host = parsed.netloc
        if not host:
            raise ScrapeError(f"No eightfold host in {company.careers_url}")
        domain = company.ats_slug or registrable_domain(host)
        query = (parse_qs(parsed.query).get("query") or [""])[0]

        all_positions: list[Any] = []
        start = 0
        for page_index in range(MAX_PAGES):
            url = (
                f"https://{host}{SEARCH_PATH}?domain={quote(domain)}"
                f"&query={quote(query)}&location=&start={start}&sort_by=relevance"
            )
            payload = await asyncio.to_thread(fetch_json, url, self.settings)
            if page_index == 0:
                try:
                    parse_positions(payload, host)
                except ValueError as exc:
                    raise ScrapeError(
                        f"Unexpected eightfold search response for domain="
                        f"{domain}: {exc}"
                    ) from exc
            data = payload.get("data") if isinstance(payload, dict) else None
            page_positions = data.get("positions") if isinstance(data, dict) else None
            if not isinstance(page_positions, list) or not page_positions:
                break
            all_positions.extend(page_positions)
            count = data.get("count") if isinstance(data, dict) else None
            start += len(page_positions)
            if isinstance(count, int) and len(all_positions) >= count:
                break

        jobs = parse_positions({"data": {"positions": all_positions}}, host)
        await self._enrich_descriptions(jobs, host, domain)
        return jobs

    async def _enrich_descriptions(
        self, jobs: list[RawJob], host: str, domain: str
    ) -> None:
        fetch_list = jobs[:MAX_DETAIL_FETCHES]
        sem = asyncio.Semaphore(min(self.settings.http_concurrency, 50))

        async def fetch_one(job: RawJob) -> None:
            if not job.external_id:
                return
            async with sem:
                try:
                    detail = await asyncio.to_thread(
                        fetch_json,
                        f"https://{host}{DETAIL_PATH}?position_id="
                        f"{quote(job.external_id)}&domain={quote(domain)}&hl=en",
                        self.settings,
                    )
                    job.description = _extract_description(detail)
                except Exception:
                    pass

        timeout = self.settings.per_company_timeout * ENRICHMENT_BUDGET_FRACTION
        try:
            await asyncio.wait_for(
                asyncio.gather(*(fetch_one(j) for j in fetch_list)),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            pass


def parse_positions(payload: Any, host: str) -> list[RawJob]:
    if not isinstance(payload, dict):
        raise ValueError("Unexpected eightfold payload: expected a dict")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Unexpected eightfold payload: missing data")
    positions = data.get("positions")
    if not isinstance(positions, list):
        raise ValueError("Unexpected eightfold data: positions is not a list")
    jobs: list[RawJob] = []
    for item in positions:
        job = _parse_position(item, host)
        if job is not None:
            jobs.append(job)
    return jobs


def _parse_position(item: Any, host: str) -> RawJob | None:
    if not isinstance(item, dict):
        return None
    title = str(item.get("name") or "").strip()
    position_url = str(item.get("positionUrl") or "")
    url = f"https://{host}{position_url}" if position_url else ""
    if not title or not url:
        return None
    locations = item.get("locations")
    location = (
        "; ".join(str(loc) for loc in locations)
        if isinstance(locations, list) and locations
        else None
    )
    position_id = item.get("id")
    external_id = str(position_id) if position_id is not None else None
    return RawJob(
        title=title,
        url=url,
        external_id=external_id,
        location=location,
        description=None,
        job_type=None,
        posted_date=parse_date(item.get("postedTs")),
        remote_hint=item.get("workLocationOption") == "remote",
    )


def _extract_description(detail: Any) -> str | None:
    if not isinstance(detail, dict):
        return None
    data = detail.get("data")
    if not isinstance(data, dict):
        return None
    description = data.get("jobDescription")
    return description if isinstance(description, str) and description.strip() else None
