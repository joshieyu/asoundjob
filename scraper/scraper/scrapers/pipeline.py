from __future__ import annotations

import asyncio
import logging

from scraper.config import Settings
from scraper.models import Company
from scraper.scrapers.ats.greenhouse import GreenhouseScraper
from scraper.scrapers.ats.lever import LeverScraper
from scraper.scrapers.base import ScrapeResult
from scraper.scrapers.http_scraper import HttpScraper
from scraper.scrapers.playwright_scraper import PlaywrightScraper

logger = logging.getLogger(__name__)


class ScrapePipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http_semaphore = asyncio.Semaphore(settings.http_concurrency)
        self.playwright_semaphore = asyncio.Semaphore(settings.playwright_concurrency)
        self.attempts: list[tuple[str, str]] = []
        self.greenhouse = GreenhouseScraper(settings)
        self.lever = LeverScraper(settings)
        self.http = HttpScraper(settings)
        self.playwright: PlaywrightScraper | None = None
        self.stealth: PlaywrightScraper | None = None

    def _playwright_scraper(self) -> PlaywrightScraper:
        if self.playwright is None:
            self.playwright = PlaywrightScraper(self.settings)
        return self.playwright

    def _stealth_scraper(self) -> PlaywrightScraper:
        if self.stealth is None:
            self.stealth = PlaywrightScraper(self.settings, stealth=True)
        return self.stealth

    async def _attempt(
        self,
        scraper,
        company: Company,
        semaphore: asyncio.Semaphore,
        label: str,
    ) -> ScrapeResult:
        async with semaphore:
            try:
                result = await asyncio.wait_for(
                    scraper.scrape(company), timeout=self.settings.per_company_timeout
                )
            except asyncio.TimeoutError:
                result = ScrapeResult(
                    company_id=company.id,
                    method=label,
                    error=f"timeout after {self.settings.per_company_timeout}s",
                )
            except Exception as exc:
                result = ScrapeResult(
                    company_id=company.id, method=label, error=f"{type(exc).__name__}: {exc}"
                )
        self.attempts.append((label, "ok" if result.success else f"fail ({result.error})"))
        return result

    async def scrape_company(self, company: Company) -> ScrapeResult:
        if not company.careers_url:
            return ScrapeResult(
                company_id=company.id, method="none", error="no careers_url"
            )

        for ats in (self.greenhouse, self.lever):
            if ats.can_handle(company):
                result = await self._attempt(ats, company, self.http_semaphore, ats.name)
                if result.success:
                    result.trust_empty = True
                    return result
                break

        skip_http = company.scrape_method == "playwright"
        if not skip_http:
            result = await self._attempt(self.http, company, self.http_semaphore, "http")
            if result.success:
                return result

        result = await self._attempt(
            self._playwright_scraper(), company, self.playwright_semaphore, "playwright"
        )
        if result.success:
            return result

        result = await self._attempt(
            self._stealth_scraper(), company, self.playwright_semaphore, "stealth"
        )
        if result.success:
            return result

        last_error = result.error or "all methods failed"
        return ScrapeResult(company_id=company.id, method="none", error=last_error)

    async def close(self) -> None:
        if self.playwright is not None:
            await self.playwright.close()
        if self.stealth is not None:
            await self.stealth.close()
