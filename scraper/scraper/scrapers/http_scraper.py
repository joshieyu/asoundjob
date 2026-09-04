from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_html
from scraper.scrapers.pagination import collect_paginated

logger = logging.getLogger(__name__)

MAX_DETAIL_FETCHES = 150
DETAIL_FETCH_CONCURRENCY = 8
ENRICHMENT_BUDGET_FRACTION = 0.85
MIN_DESCRIPTION_CHARS = 200

STRIP_TAGS = ("script", "style", "nav", "header", "footer", "aside", "form")


class HttpScraper(BaseScraper):
    name = "http"

    async def fetch_jobs(self, company) -> list[RawJob]:
        start = monotonic()
        if not company.careers_url:
            raise ValueError(f"Company {company.name} has no careers_url")
        url = company.careers_url.strip()

        async def fetch(page_url: str) -> str:
            return await asyncio.to_thread(fetch_html, page_url, self.settings)

        jobs, first_page_html = await collect_paginated(fetch, url)
        self._last_html = first_page_html
        if not jobs:
            raise ScrapeError("page loaded but no job links found")

        host = urlparse(url).netloc.lower()
        candidates = [
            job
            for job in jobs
            if _needs_enrichment(job) and urlparse(job.url).netloc.lower() == host
        ][:MAX_DETAIL_FETCHES]

        deadline = start + self.settings.per_company_timeout * ENRICHMENT_BUDGET_FRACTION
        semaphore = asyncio.Semaphore(DETAIL_FETCH_CONCURRENCY)
        counts = {"enriched": 0, "budget_skipped": 0}
        await asyncio.gather(
            *(self._enrich_job(job, semaphore, deadline, counts) for job in candidates)
        )
        if counts["budget_skipped"] > 0:
            logger.info(
                "http: enrichment budget exhausted, enriched %d/%d jobs",
                counts["enriched"],
                len(candidates),
            )
        return jobs

    async def _enrich_job(
        self,
        job: RawJob,
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
            except Exception as exc:
                logger.warning("http: detail fetch failed for %s: %s", job.url, exc)
                return
        description = extract_description(detail_html)
        if description:
            job.description = description
            counts["enriched"] += 1


def _needs_enrichment(job: RawJob) -> bool:
    return job.description is None or len(job.description) < MIN_DESCRIPTION_CHARS


def extract_description(html_text: str) -> Optional[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    for tag_name in STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    container = soup.find("main")
    if container is None:
        container = soup.find(True, attrs={"role": "main"})
    if container is None:
        container = soup.find("article")
    if container is None:
        container = _largest_text_div(soup)
    if container is None:
        container = soup.find("body")
    if not isinstance(container, Tag):
        return None

    text = container.get_text(" ", strip=True)
    return text or None


def _largest_text_div(soup: BeautifulSoup) -> Optional[Tag]:
    best: Optional[Tag] = None
    best_len = 0
    for div in soup.find_all("div"):
        length = len(div.get_text(strip=True))
        if length > best_len:
            best = div
            best_len = length
    return best
