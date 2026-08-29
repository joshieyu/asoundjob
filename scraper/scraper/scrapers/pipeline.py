from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select, update

from scraper.config import Settings
from scraper.database import get_session_factory
from scraper.models import Company
from scraper.scrapers.ats.adp import AdpScraper
from scraper.scrapers.ats.apple import AppleScraper
from scraper.scrapers.ats.ashby import AshbyScraper
from scraper.scrapers.ats.bamboohr import BambooHRScraper
from scraper.scrapers.ats.greenhouse import GreenhouseScraper
from scraper.scrapers.ats.icims import IcimsScraper
from scraper.scrapers.ats.lever import LeverScraper
from scraper.scrapers.ats.pinpoint import PinpointScraper
from scraper.scrapers.ats.recruitee import RecruiteeScraper
from scraper.scrapers.ats.smartrecruiters import SmartRecruitersScraper
from scraper.scrapers.ats.workable import WorkableScraper
from scraper.scrapers.ats.workday import WorkdayScraper
from scraper.scrapers.ats_discovery import discover
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
        self.workable = WorkableScraper(settings)
        self.ashby = AshbyScraper(settings)
        self.smartrecruiters = SmartRecruitersScraper(settings)
        self.recruitee = RecruiteeScraper(settings)
        self.bamboohr = BambooHRScraper(settings)
        self.workday = WorkdayScraper(settings)
        self.apple = AppleScraper(settings)
        self.pinpoint = PinpointScraper(settings)
        self.icims = IcimsScraper(settings)
        self.adp = AdpScraper(settings)
        self.http = HttpScraper(settings)
        self.playwright: PlaywrightScraper | None = None
        self.stealth: PlaywrightScraper | None = None
        self._ats_map: dict[str, object] = {
            "greenhouse": self.greenhouse,
            "lever": self.lever,
            "workable": self.workable,
            "ashby": self.ashby,
            "smartrecruiters": self.smartrecruiters,
            "recruitee": self.recruitee,
            "bamboohr": self.bamboohr,
            "workday": self.workday,
            "apple": self.apple,
            "pinpoint": self.pinpoint,
            "icims": self.icims,
            "adp": self.adp,
        }

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

    def _persist_ats_discovery(
        self, company_id: int, ats_type: str, ats_slug: str, overwrite: bool = False
    ) -> None:
        try:
            factory = get_session_factory()
            with factory() as session:
                statement = update(Company).where(Company.id == company_id)
                if not overwrite:
                    statement = statement.where(Company.ats_type.is_(None))
                session.execute(
                    statement.values(ats_type=ats_type, ats_slug=ats_slug)
                )
                session.commit()
            logger.info(
                "discovered ATS %s slug=%s for company_id=%s",
                ats_type,
                ats_slug,
                company_id,
            )
        except Exception as exc:
            logger.warning("failed to persist ATS discovery: %s", exc)

    async def scrape_company(self, company: Company) -> ScrapeResult:
        if not company.careers_url:
            return ScrapeResult(
                company_id=company.id, method="none", error="no careers_url"
            )

        stored_ats_failed = False
        if company.ats_type and company.ats_type in self._ats_map:
            scraper = self._ats_map[company.ats_type]
            result = await self._attempt(
                scraper, company, self.http_semaphore, company.ats_type
            )
            if result.success:
                result.trust_empty = True
                return result
            stored_ats_failed = True

        ats_scrapers = (
            self.greenhouse,
            self.lever,
            self.workable,
            self.ashby,
            self.smartrecruiters,
            self.recruitee,
            self.bamboohr,
            self.workday,
            self.pinpoint,
            self.icims,
            self.adp,
            self.apple,
        )
        for ats in ats_scrapers:
            if ats.can_handle(company):
                result = await self._attempt(ats, company, self.http_semaphore, ats.name)
                if result.success:
                    result.trust_empty = True
                    return result
                break

        skip_http = company.scrape_method == "playwright"
        if not skip_http:
            result = await self._attempt(self.http, company, self.http_semaphore, "http")
            self._try_discovery(company, result.html, stored_ats_failed)
            if result.success:
                return result

        result = await self._attempt(
            self._playwright_scraper(), company, self.playwright_semaphore, "playwright"
        )
        self._try_discovery(company, result.html, stored_ats_failed)
        if result.success:
            return result

        result = await self._attempt(
            self._stealth_scraper(), company, self.playwright_semaphore, "stealth"
        )
        self._try_discovery(company, result.html, stored_ats_failed)
        if result.success:
            return result

        last_error = result.error or "all methods failed"
        return ScrapeResult(company_id=company.id, method="none", error=last_error)

    def _try_discovery(
        self, company: Company, html: str | None, overwrite: bool = False
    ) -> None:
        if not html:
            return
        findings = discover(html, company.careers_url or "")
        if not findings:
            return
        ats_type, ats_slug = findings[0]
        if overwrite and (ats_type, ats_slug) == (company.ats_type, company.ats_slug):
            return
        if self._board_claimed_elsewhere(company.id, ats_type, ats_slug):
            logger.info(
                "skipping ATS %s slug=%s for company_id=%s: claimed by another company",
                ats_type,
                ats_slug,
                company.id,
            )
            return
        self._persist_ats_discovery(company.id, ats_type, ats_slug, overwrite)

    def _board_claimed_elsewhere(
        self, company_id: int, ats_type: str, ats_slug: str
    ) -> bool:
        try:
            factory = get_session_factory()
            with factory() as session:
                found = session.execute(
                    select(Company.id)
                    .where(Company.ats_type == ats_type)
                    .where(Company.ats_slug == ats_slug)
                    .where(Company.id != company_id)
                    .limit(1)
                ).first()
            return found is not None
        except Exception as exc:
            logger.warning("failed to check ATS ownership: %s", exc)
            return False

    async def close(self) -> None:
        if self.playwright is not None:
            await self.playwright.close()
        if self.stealth is not None:
            await self.stealth.close()
