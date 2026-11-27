from __future__ import annotations

import asyncio
import html
import logging
import re
from time import monotonic
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlsplit

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError, company_budget, listing
from scraper.scrapers.detail_enrichment import apply_structured_detail, description_is_thin
from scraper.scrapers.fetch import fetch_html, fetch_json, parse_date
from scraper.scrapers.http_scraper import extract_description

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

PAGE_SIZE = 50
MAX_PAGES = 10
MAX_RESULTS_PER_KEYWORD = 40
MAX_DETAIL_FETCHES = 100
DETAIL_FETCH_CONCURRENCY = 4
ENRICHMENT_BUDGET_FRACTION = 0.6
JOB_ID_RE = re.compile(r"^[0-9a-fA-F-]{8,64}$")
TAG_RE = re.compile(r"<[^>]{0,500}>")


class JTableScraper(BaseScraper):
    name = "jtable"

    def can_handle(self, company: Company) -> bool:
        return company.ats_type == "jtable"

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        start = monotonic()
        parts = urlsplit((company.careers_url or "").strip())
        if not parts.netloc:
            raise ScrapeError(f"No jtable host in {company.careers_url}")
        origin = f"{parts.scheme or 'https'}://{parts.netloc}"
        keywords = [k.strip() for k in parse_qs(parts.query).get("keyword", []) if k.strip()]
        jobs = listing()
        seen: set[str] = set()
        for keyword in keywords or [""]:
            for job in await self._search(origin, keyword):
                key = job.external_id or job.url
                if key not in seen:
                    seen.add(key)
                    jobs.append(job)
        deadline = start + company_budget(self.settings, company) * ENRICHMENT_BUDGET_FRACTION
        semaphore = asyncio.Semaphore(DETAIL_FETCH_CONCURRENCY)
        await asyncio.gather(
            *(self._describe(job, semaphore, deadline) for job in jobs[:MAX_DETAIL_FETCHES])
        )
        return jobs

    async def _search(self, origin: str, keyword: str) -> list[RawJob]:
        found: list[RawJob] = []
        for page in range(MAX_PAGES):
            params: dict[str, str | int] = {}
            if keyword:
                params["keyword"] = keyword
            params["jtStartIndex"] = page * PAGE_SIZE
            params["jtPageSize"] = PAGE_SIZE
            url = f"{origin}/Search/SearchResults?{urlencode(params)}"
            payload = await asyncio.to_thread(fetch_json, url, self.settings)
            records, total = parse_page(payload, url)
            found.extend(job for job in (to_job(r, origin) for r in records) if job)
            if keyword and len(found) >= MAX_RESULTS_PER_KEYWORD:
                return found[:MAX_RESULTS_PER_KEYWORD]
            if not records or page * PAGE_SIZE + len(records) >= total:
                return found
        logger.info("jtable: hit MAX_PAGES=%d for %s keyword=%r", MAX_PAGES, origin, keyword)
        return found

    async def _describe(
        self, job: RawJob, semaphore: asyncio.Semaphore, deadline: float
    ) -> None:
        async with semaphore:
            if monotonic() >= deadline:
                return
            try:
                page = await asyncio.to_thread(fetch_html, job.url, self.settings)
            except Exception as exc:
                logger.warning("jtable: detail fetch failed for %s: %s", job.url, exc)
                return
        apply_structured_detail(job, page)
        if description_is_thin(job):
            job.description = extract_description(page) or job.description


def parse_page(payload: Any, url: str) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(payload, dict) or payload.get("Result") != "OK":
        raise ScrapeError(f"Unexpected jtable response from {url}")
    records = payload.get("Records")
    if not isinstance(records, list):
        raise ScrapeError(f"jtable response from {url} has no Records list")
    total = payload.get("TotalRecordCount")
    rows = [r for r in records if isinstance(r, dict)]
    return rows, total if isinstance(total, int) else len(rows)


def to_job(record: dict[str, Any], origin: str) -> RawJob | None:
    job_id = str(record.get("ID") or "").strip()
    tracking = record.get("TrackingObject")
    tracking = tracking if isinstance(tracking, dict) else {}
    title = _text(tracking.get("TitleJson")) or _text(record.get("Title"))
    if not title or not JOB_ID_RE.match(job_id):
        return None
    names = tracking.get("LocationNamesJson")
    locations = [_text(n) for n in names] if isinstance(names, list) else []
    location = "; ".join(dict.fromkeys(n for n in locations if n)) or _text(
        record.get("LocationName")
    )
    return RawJob(
        title=title,
        url=f"{origin}/search/jobdetails/job/{job_id}",
        external_id=job_id,
        location=location,
        posted_date=parse_date(record.get("PostedDateRaw")),
    )


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = html.unescape(TAG_RE.sub(" ", value)).replace("\xa0", " ")
    return " ".join(cleaned.split()) or None
