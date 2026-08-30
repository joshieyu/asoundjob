from __future__ import annotations

import asyncio

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_html
from scraper.scrapers.pagination import collect_paginated


class HttpScraper(BaseScraper):
    name = "http"

    async def fetch_jobs(self, company) -> list[RawJob]:
        if not company.careers_url:
            raise ValueError(f"Company {company.name} has no careers_url")
        url = company.careers_url.strip()

        async def fetch(page_url: str) -> str:
            return await asyncio.to_thread(fetch_html, page_url, self.settings)

        jobs, first_page_html = await collect_paginated(fetch, url)
        self._last_html = first_page_html
        if not jobs:
            raise ScrapeError("page loaded but no job links found")
        return jobs
