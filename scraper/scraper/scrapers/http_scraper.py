from __future__ import annotations

import asyncio

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_html
from scraper.scrapers.link_extraction import extract_jobs


class HttpScraper(BaseScraper):
    name = "http"

    async def fetch_jobs(self, company) -> list[RawJob]:
        if not company.careers_url:
            raise ValueError(f"Company {company.name} has no careers_url")
        html = await asyncio.to_thread(
            fetch_html, company.careers_url.strip(), self.settings
        )
        self._last_html = html
        jobs = extract_jobs(html, company.careers_url.strip())
        if not jobs:
            raise ScrapeError("page loaded but no job links found")
        return jobs
