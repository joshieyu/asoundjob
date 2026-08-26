from __future__ import annotations

import asyncio

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_html
from scraper.scrapers.link_extraction import extract_job_links


class HttpScraper(BaseScraper):
    name = "http"

    async def fetch_jobs(self, company) -> list[RawJob]:
        if not company.careers_url:
            raise ValueError(f"Company {company.name} has no careers_url")
        html = await asyncio.to_thread(
            fetch_html, company.careers_url.strip(), self.settings
        )
        self._last_html = html
        return extract_job_links(html, company.careers_url.strip())
