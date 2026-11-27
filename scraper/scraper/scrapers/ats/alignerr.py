from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlsplit

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError, listing
from scraper.scrapers.fetch import fetch_html, fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

ORIGIN = "https://www.alignerr.com"
HOSTS = frozenset({"alignerr.com", "www.alignerr.com"})
PAGE_SIZE = 60
MAX_PAGES = 5
JOB_ID_RE = re.compile(r"^[0-9a-fA-F-]{8,64}$")
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(?P<data>.{1,2000000}?)</script>', re.S
)


class AlignerrScraper(BaseScraper):
    name = "alignerr"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "alignerr":
            return True
        return urlsplit((company.careers_url or "").strip()).netloc.lower() in HOSTS

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        query = parse_qs(urlsplit((company.careers_url or "").strip()).query)
        searches = [s.strip() for s in query.get("search", []) if s.strip()]
        if not searches:
            raise ScrapeError("alignerr boards must name at least one search= term")
        rows: list[dict[str, Any]] = []
        for search in searches:
            rows.extend(await self._search(search))
        jobs = listing()
        jobs.extend(collapse(rows))
        await asyncio.gather(*(self._describe(job) for job in jobs))
        return jobs

    async def _search(self, search: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for page in range(MAX_PAGES):
            params = {"limit": PAGE_SIZE, "offset": page * PAGE_SIZE, "search": search}
            url = f"{ORIGIN}/api/jobs?{urlencode(params)}"
            payload = await asyncio.to_thread(fetch_json, url, self.settings)
            if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
                raise ScrapeError(f"Unexpected alignerr response from {url}")
            batch = [row for row in payload["jobs"] if isinstance(row, dict)]
            rows.extend(batch)
            total = payload.get("total")
            if not batch or not isinstance(total, int) or len(rows) >= total:
                return rows
        return rows

    async def _describe(self, job: RawJob) -> None:
        try:
            page = await asyncio.to_thread(fetch_html, job.url, self.settings)
        except Exception as exc:
            logger.warning("alignerr: detail fetch failed for %s: %s", job.url, exc)
            return
        apply_detail(job, page)


def collapse(rows: list[dict[str, Any]]) -> list[RawJob]:
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        job_id = str(row.get("id") or "").strip()
        title = " ".join(str(row.get("title") or "").split())
        if not title or not JOB_ID_RE.match(job_id):
            continue
        key = title.lower()
        kept = groups.get(key)
        if kept is None or job_id < str(kept["id"]):
            groups[key] = row
    jobs: list[RawJob] = []
    for row in groups.values():
        job_id = str(row["id"])
        location = str(row.get("location") or "").strip() or None
        jobs.append(
            RawJob(
                title=" ".join(str(row["title"]).split()),
                url=f"{ORIGIN}/jobs/{job_id}",
                external_id=job_id,
                location=location,
                description=str(row.get("description") or "").strip() or None,
                job_type="contract",
                remote_hint=(location or "").lower() == "remote",
            )
        )
    return jobs


def apply_detail(job: RawJob, page: str) -> None:
    match = NEXT_DATA_RE.search(page)
    if match is None:
        return
    try:
        data = json.loads(match.group("data"))
    except ValueError:
        return
    detail = data.get("props", {}).get("pageProps", {}).get("job")
    if not isinstance(detail, dict):
        return
    description = detail.get("htmlLongDescription") or detail.get("longDescription")
    if isinstance(description, str) and description.strip():
        job.description = description.strip()
    job.posted_date = parse_date(detail.get("firstPostDate") or detail.get("createdAt"))
