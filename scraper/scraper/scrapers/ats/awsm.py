from __future__ import annotations

import asyncio
import html
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urlsplit

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError, listing
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

AWSM_HOSTS: frozenset[str] = frozenset({"iaggroup.com"})

API_PATH = "/wp-json/wp/v2/awsm_job_openings"
PAGE_SIZE = 100
MAX_PAGES = 10

LOCATION_PREFIX = "location-"
EMPLOYMENT_TYPE_PREFIX = "employment-type-"


class AwsmScraper(BaseScraper):
    name = "awsm"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "awsm":
            return True
        if not company.careers_url:
            return False
        return normalize_host(company.careers_url.strip()) in AWSM_HOSTS

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        host = normalize_host((company.careers_url or "").strip())
        if not host:
            raise ScrapeError(f"No WP Job Openings host in {company.careers_url}")
        jobs = listing()
        for page in range(1, MAX_PAGES + 1):
            url = build_api_url(host, page)
            payload = await asyncio.to_thread(fetch_json, url, self.settings)
            page_jobs = parse_jobs(payload, url)
            jobs.extend(page_jobs)
            if not isinstance(payload, list) or len(payload) < PAGE_SIZE:
                return jobs
        logger.info("awsm: hit MAX_PAGES=%d cap for %s, jobs may be truncated", MAX_PAGES, host)
        return jobs


def normalize_host(url: str) -> str:
    netloc = urlsplit(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def build_api_url(host: str, page: int) -> str:
    return f"https://{host}{API_PATH}?{urlencode({'per_page': PAGE_SIZE, 'page': page})}"


def parse_jobs(payload: Any, url: str) -> list[RawJob]:
    if not isinstance(payload, list):
        raise ScrapeError(f"Unexpected WP Job Openings payload from {url}: expected a list")
    jobs: list[RawJob] = []
    for item in payload:
        if isinstance(item, dict):
            job = _parse_job(item)
            if job is not None:
                jobs.append(job)
    return jobs


def _parse_job(item: dict[str, Any]) -> RawJob | None:
    title = html.unescape(_rendered(item.get("title"))).strip()
    link = item.get("link")
    if not title or not isinstance(link, str) or not link.strip():
        return None
    classes = item.get("class_list")
    classes = [c for c in classes if isinstance(c, str)] if isinstance(classes, list) else []
    job_id = item.get("id")
    return RawJob(
        title=title,
        url=link.strip(),
        external_id=str(job_id) if job_id is not None else link.strip(),
        location=_terms(classes, LOCATION_PREFIX, reverse=True),
        description=_rendered(item.get("content")) or None,
        job_type=_terms(classes, EMPLOYMENT_TYPE_PREFIX),
        posted_date=parse_date(item.get("date_gmt") or item.get("date")),
    )


def _rendered(value: Any) -> str:
    if isinstance(value, dict):
        rendered = value.get("rendered")
        return rendered if isinstance(rendered, str) else ""
    return ""


def _terms(classes: list[str], prefix: str, reverse: bool = False) -> str | None:
    names = [
        c[len(prefix):].replace("-", " ").title()
        for c in classes
        if c.startswith(prefix) and len(c) > len(prefix)
    ]
    if reverse:
        names.reverse()
    return ", ".join(names) or None
