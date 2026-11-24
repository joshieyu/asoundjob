from __future__ import annotations

import asyncio
import json
import re
from time import monotonic
from typing import TYPE_CHECKING, Any

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError, company_budget, listing
from scraper.scrapers.fetch import FetchError, fetch_html, parse_date
from scraper.scrapers.link_extraction import extract_jsonld_jobs

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://recruiting\.paylocity\.com/recruiting/jobs/all/"
    r"(?P<board>[0-9a-f-]{36})",
    re.IGNORECASE,
)

PAGE_DATA_RE = re.compile(r"window\.pageData\s*=\s*(\{.*?\});\s*(?:</script>|\n)", re.DOTALL)

DETAIL_URL = "https://recruiting.paylocity.com/Recruiting/Jobs/Details/{job_id}"

MAX_DETAIL_FETCHES = 80
DETAIL_CONCURRENCY = 6
ENRICHMENT_BUDGET_FRACTION = 0.6


class PaylocityScraper(BaseScraper):
    name = "paylocity"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "paylocity":
            return True
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        careers_url = (company.careers_url or "").strip()
        if not URL_PATTERN.match(careers_url):
            raise ScrapeError(f"No paylocity board in {company.careers_url}")
        deadline = monotonic() + company_budget(self.settings, company) * ENRICHMENT_BUDGET_FRACTION
        page = await asyncio.to_thread(fetch_html, careers_url, self.settings)
        jobs = listing()
        jobs.extend(parse_board(page))
        semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
        await asyncio.gather(
            *(self._describe(job, semaphore, deadline) for job in jobs[:MAX_DETAIL_FETCHES])
        )
        return jobs

    async def _describe(
        self, job: RawJob, semaphore: asyncio.Semaphore, deadline: float
    ) -> None:
        async with semaphore:
            if monotonic() >= deadline:
                return
            try:
                page = await asyncio.to_thread(fetch_html, job.url, self.settings)
            except FetchError:
                return
        for detail in extract_jsonld_jobs(page, job.url):
            if detail.description:
                job.description = detail.description
                return


def parse_board(page: str) -> list[RawJob]:
    match = PAGE_DATA_RE.search(page)
    if not match:
        raise ScrapeError("No paylocity pageData on the board page")
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ScrapeError(f"Invalid paylocity pageData: {exc}") from exc
    rows = data.get("Jobs") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ScrapeError("Unexpected paylocity pageData: Jobs is not a list")
    jobs: list[RawJob] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("IsInternal"):
            continue
        title = str(row.get("JobTitle") or "").strip()
        job_id = row.get("JobId")
        if not title or not job_id:
            continue
        jobs.append(
            RawJob(
                title=title,
                url=DETAIL_URL.format(job_id=job_id),
                external_id=str(job_id),
                location=_location(row),
                description=row.get("Description") or None,
                posted_date=parse_date(row.get("PublishedDate")),
                remote_hint=bool(row.get("IsRemote")),
            )
        )
    return jobs


def _location(row: dict[str, Any]) -> str | None:
    place = row.get("JobLocation")
    if isinstance(place, dict):
        parts = [place.get("City"), place.get("State")]
        text = ", ".join(str(p).strip() for p in parts if p and str(p).strip())
        if text:
            return text
    name = row.get("LocationName")
    return str(name).strip() if name and str(name).strip() else None
