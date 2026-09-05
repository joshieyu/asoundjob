from __future__ import annotations

import asyncio
import re
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlparse

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_json

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?amazon\.jobs(?:/[a-zA-Z]{2,5})?(?:/|$|\?)",
    re.IGNORECASE,
)

SEARCH_URL = "https://www.amazon.jobs/en/search.json"

PAGE_SIZE = 100
MAX_PAGES = 10

POSTED_DATE_FORMAT = "%B %d, %Y"

DESCRIPTION_FIELDS = ("description", "basic_qualifications", "preferred_qualifications")


class AmazonScraper(BaseScraper):
    name = "amazon"

    def can_handle(self, company: Company) -> bool:
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        careers_url = (company.careers_url or "").strip()
        query = extract_base_query(careers_url)
        raw_jobs = await self._fetch_all(query)
        return parse_jobs(raw_jobs)

    async def _fetch_all(self, query: str) -> list[Any]:
        jobs: list[Any] = []
        hits: int | None = None
        offset = 0
        for page_index in range(MAX_PAGES):
            url = _search_url(query, offset)
            response = await asyncio.to_thread(fetch_json, url, self.settings)
            if page_index == 0 and not isinstance(response, dict):
                raise ScrapeError(
                    f"Unexpected amazon search response for base_query={query!r}"
                )
            page = response.get("jobs") if isinstance(response, dict) else None
            if not isinstance(page, list) or not page:
                break
            jobs.extend(page)
            page_hits = response.get("hits") if isinstance(response, dict) else None
            if hits is None and page_hits:
                hits = page_hits
            offset += len(page)
            if (hits is not None and offset >= hits) or len(page) < PAGE_SIZE:
                break
        return jobs


def _search_url(query: str, offset: int) -> str:
    params = urlencode({"base_query": query, "result_limit": PAGE_SIZE, "offset": offset})
    return f"{SEARCH_URL}?{params}"


def extract_base_query(url: str) -> str:
    parsed = urlparse((url or "").strip())
    values = parse_qs(parsed.query).get("base_query")
    return values[0] if values else ""


def parse_jobs(items: Any) -> list[RawJob]:
    if not isinstance(items, list):
        raise ValueError("Unexpected amazon payload: expected a list")
    jobs: list[RawJob] = []
    for item in items:
        job = _parse_job(item)
        if job is not None:
            jobs.append(job)
    return jobs


def _parse_job(item: Any) -> RawJob | None:
    if not isinstance(item, dict):
        return None
    title = str(item.get("title") or "").strip()
    job_path = item.get("job_path")
    if not title or not job_path:
        return None
    id_icims = item.get("id_icims")
    return RawJob(
        title=title,
        url="https://www.amazon.jobs" + job_path,
        external_id=str(id_icims) if id_icims is not None else None,
        location=item.get("normalized_location"),
        description=_build_description(item),
        job_type=_parse_job_type(item.get("job_schedule_type")),
        posted_date=_parse_posted_date(item.get("posted_date")),
    )


def _build_description(item: dict) -> str | None:
    parts = []
    for field in DESCRIPTION_FIELDS:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    return "\n".join(parts) if parts else None


def _parse_job_type(value: Any) -> str | None:
    if not value:
        return None
    return str(value).lower().replace("_", "-")


def _parse_posted_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), POSTED_DATE_FORMAT).date()
    except ValueError:
        return None
