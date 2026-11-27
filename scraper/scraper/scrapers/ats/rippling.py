from __future__ import annotations

import asyncio
import logging
import re
from time import monotonic
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError, company_budget, listing
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

BOARD_URL_RE = re.compile(
    r"^https?://ats\.rippling\.com/(?:[a-z]{2}-[A-Z]{2}/)?(?P<slug>[A-Za-z0-9-]{1,100})(?:/|$)"
)
API_URL = "https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs"
JOB_ID_RE = re.compile(r"^[0-9a-fA-F-]{8,64}$")
MAX_DETAIL_FETCHES = 100
DETAIL_FETCH_CONCURRENCY = 6
ENRICHMENT_BUDGET_FRACTION = 0.7


class RipplingScraper(BaseScraper):
    name = "rippling"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "rippling":
            return True
        return board_slug(company.careers_url or "") is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        start = monotonic()
        slug = company.ats_slug or board_slug(company.careers_url or "")
        if not slug:
            raise ScrapeError(f"No rippling board in {company.careers_url}")
        base = API_URL.format(slug=quote(slug))
        payload = await asyncio.to_thread(fetch_json, base, self.settings)
        jobs = listing()
        jobs.extend(parse_board(payload, base))
        deadline = start + company_budget(self.settings, company) * ENRICHMENT_BUDGET_FRACTION
        semaphore = asyncio.Semaphore(DETAIL_FETCH_CONCURRENCY)
        await asyncio.gather(
            *(self._describe(job, base, semaphore, deadline) for job in jobs[:MAX_DETAIL_FETCHES])
        )
        return jobs

    async def _describe(
        self, job: RawJob, base: str, semaphore: asyncio.Semaphore, deadline: float
    ) -> None:
        async with semaphore:
            if monotonic() >= deadline:
                return
            try:
                detail = await asyncio.to_thread(
                    fetch_json, f"{base}/{job.external_id}", self.settings
                )
            except Exception as exc:
                logger.warning("rippling: detail fetch failed for %s: %s", job.url, exc)
                return
        apply_detail(job, detail)


def board_slug(url: str) -> str | None:
    match = BOARD_URL_RE.match(url.strip())
    return match.group("slug") if match else None


def parse_board(payload: Any, url: str) -> list[RawJob]:
    if not isinstance(payload, list):
        raise ScrapeError(f"Unexpected rippling board response from {url}")
    jobs: list[RawJob] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        job_id = str(item.get("uuid") or "").strip()
        title = str(item.get("name") or "").strip()
        link = str(item.get("url") or "").strip()
        if not title or not link or not JOB_ID_RE.match(job_id):
            continue
        location = item.get("workLocation")
        label = location.get("label") if isinstance(location, dict) else None
        jobs.append(
            RawJob(
                title=title,
                url=link,
                external_id=job_id,
                location=str(label).strip() if label else None,
            )
        )
    return jobs


def apply_detail(job: RawJob, detail: Any) -> None:
    if not isinstance(detail, dict):
        return
    description = detail.get("description")
    if isinstance(description, dict):
        role = description.get("role")
        if isinstance(role, str) and role.strip():
            job.description = role.strip()
    locations = detail.get("workLocations")
    if isinstance(locations, list):
        names = [str(n).strip() for n in locations if isinstance(n, str) and n.strip()]
        if names:
            job.location = "; ".join(dict.fromkeys(names))
    job.posted_date = job.posted_date or parse_date(detail.get("createdOn"))
