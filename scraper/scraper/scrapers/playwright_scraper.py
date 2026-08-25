from __future__ import annotations

import asyncio
import logging
from typing import Any

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.link_extraction import extract_job_links

logger = logging.getLogger(__name__)

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
"""


class PlaywrightScraper(BaseScraper):
    name = "playwright"

    def __init__(self, settings, stealth: bool = False) -> None:
        super().__init__(settings)
        self.stealth = stealth
        if stealth:
            self.name = "playwright_stealth"
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self):
        if self._browser is None:
            async with self._lock:
                if self._browser is None:
                    from playwright.async_api import async_playwright

                    self._playwright = await async_playwright().start()
                    launch_kwargs: dict = {
                        "headless": True,
                        "args": [
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                        ],
                    }
                    self._browser = await self._playwright.chromium.launch(
                        **launch_kwargs
                    )
                    logger.info("playwright browser launched (stealth=%s)", self.stealth)
        return self._browser

    async def fetch_page_html(self, url: str) -> str:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        browser = await self._ensure_browser()
        context = await browser.new_context()
        try:
            if self.stealth:
                await context.add_init_script(STEALTH_INIT_SCRIPT)
            page = await context.new_page()
            timeout_ms = int(self.settings.page_load_timeout * 1000)
            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            except PlaywrightTimeoutError:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(500)
            return await page.content()
        finally:
            await context.close()

    async def fetch_jobs(self, company) -> list[RawJob]:
        if not company.careers_url:
            raise ValueError(f"Company {company.name} has no careers_url")
        url = company.careers_url.strip()
        html = await self.fetch_page_html(url)
        jobs = extract_job_links(html, url)
        if not jobs:
            raise ScrapeError("page loaded but no job links found")
        return jobs

    async def close(self) -> None:
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
