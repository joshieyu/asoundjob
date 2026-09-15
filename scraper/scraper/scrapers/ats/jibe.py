from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlsplit

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

JIBE_HOSTS: frozenset[str] = frozenset({"careers.garmin.com"})

PAGE_SIZE = 100
MAX_PAGES = 20

LOCATION_FIELDS = ("city", "state", "country")


class JibeScraper(BaseScraper):
    name = "jibe"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "jibe":
            return True
        if not company.careers_url:
            return False
        return _normalize_host(company.careers_url.strip()) in JIBE_HOSTS

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        careers_url = (company.careers_url or "").strip()
        host = _normalize_host(careers_url)
        if not host:
            raise ScrapeError(f"No jibe host in {company.careers_url}")
        keywords = _extract_keywords(careers_url)
        return await self._fetch_all(host, keywords)

    async def _fetch_all(self, host: str, keywords: str | None) -> list[RawJob]:
        jobs: list[RawJob] = []
        total: int | None = None
        fetched = 0
        for page_index in range(MAX_PAGES):
            url = _build_api_url(host, keywords, page_index + 1)
            payload = await asyncio.to_thread(fetch_json, url, self.settings)
            jobs.extend(parse_jobs(payload, host))
            jobs_raw = payload.get("jobs") if isinstance(payload, dict) else None
            raw_count = len(jobs_raw) if isinstance(jobs_raw, list) else 0
            fetched += raw_count
            if total is None and isinstance(payload, dict):
                total_value = payload.get("totalCount")
                if isinstance(total_value, int):
                    total = total_value
            if raw_count == 0:
                break
            if total is not None and fetched >= total:
                break
            if page_index == MAX_PAGES - 1:
                logger.info(
                    "jibe: hit MAX_PAGES=%d cap for %s, jobs may be truncated",
                    MAX_PAGES, host,
                )
        return jobs


def _normalize_host(url: str) -> str:
    netloc = urlsplit(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def _extract_keywords(url: str) -> str | None:
    values = parse_qs(urlsplit(url).query).get("keywords")
    return values[0] if values else None


def _build_api_url(host: str, keywords: str | None, page: int) -> str:
    params: dict[str, Any] = {"limit": PAGE_SIZE, "page": page}
    if keywords:
        params["keywords"] = keywords
    return f"https://{host}/api/jobs?{urlencode(params)}"


def parse_jobs(payload: Any, host: str) -> list[RawJob]:
    api_url = f"https://{host}/api/jobs"
    if not isinstance(payload, dict):
        raise ScrapeError(f"Unexpected jibe payload from {api_url}: expected a dict")
    jobs_raw = payload.get("jobs")
    if not isinstance(jobs_raw, list):
        raise ScrapeError(f"Unexpected jibe payload from {api_url}: jobs is not a list")
    jobs: list[RawJob] = []
    for wrapper in jobs_raw:
        if not isinstance(wrapper, dict):
            continue
        data = wrapper.get("data")
        if not isinstance(data, dict):
            continue
        job = _parse_job(data, host)
        if job is not None:
            jobs.append(job)
    return jobs


def _parse_job(data: dict, host: str) -> RawJob | None:
    title = data.get("title")
    title = title.strip() if isinstance(title, str) else ""
    slug = data.get("slug")
    if not title or not slug:
        return None
    job_type = data.get("employment_type")
    job_type = job_type.strip() if isinstance(job_type, str) and job_type.strip() else None
    return RawJob(
        title=title,
        url=f"https://{host}/jobs/{slug}",
        external_id=str(slug),
        location=_build_location(data),
        description=data.get("description"),
        job_type=job_type,
        posted_date=parse_date(
            data.get("posted_date") or data.get("create_date") or data.get("update_date")
        ),
    )


def _build_location(data: dict) -> str | None:
    parts = []
    for field in LOCATION_FIELDS:
        value = data.get(field)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return ", ".join(parts) if parts else None
