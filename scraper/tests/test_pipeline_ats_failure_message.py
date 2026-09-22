from __future__ import annotations

import asyncio
import unittest

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.base import BaseScraper, ScrapeError
from scraper.scrapers.pipeline import ScrapePipeline


def make_company(ats_type: str = "", ats_slug: str = "") -> Company:
    return Company(
        id=42,
        name="Knowles Corporation",
        slug="knowles-corporation",
        category="Hearing & Audiology",
        careers_url="https://workforcenow.adp.com/mascsr/default/mdf/recruitment/x",
        scrape_method="http",
        ats_type=ats_type,
        ats_slug=ats_slug,
    )


class FailingScraper(BaseScraper):
    def __init__(self, settings, name: str, message: str, claims: bool = False) -> None:
        super().__init__(settings)
        self.name = name
        self.message = message
        self.claims = claims

    def can_handle(self, company) -> bool:
        return self.claims

    async def fetch_jobs(self, company):
        raise ScrapeError(self.message)


class SucceedingScraper(BaseScraper):
    name = "generic"

    async def fetch_jobs(self, company):
        self._last_html = "<html><body>one page of jobs</body></html>"
        return [object()]


def build_pipeline(settings, fallback):
    pipeline = ScrapePipeline(settings)
    pipeline._persist_ats_discovery = lambda *a, **k: None  # type: ignore[method-assign]
    pipeline._board_claimed_elsewhere = lambda *a, **k: False  # type: ignore[method-assign]
    pipeline._try_discovery = _no_discovery  # type: ignore[method-assign,assignment]
    pipeline.http = fallback  # type: ignore[assignment]
    pipeline._playwright_scraper = lambda: fallback  # type: ignore[method-assign]
    pipeline._stealth_scraper = lambda: fallback  # type: ignore[method-assign]
    return pipeline


async def _no_discovery(company, html, overwrite=False):
    return None


class TestStoredBindingFailureIsKept(unittest.TestCase):
    def test_combined_message_includes_binding_and_careers_page_errors(self) -> None:
        settings = load_settings()

        async def go():
            fallback = FailingScraper(
                settings, "http", "page loaded but no job links found"
            )
            pipeline = build_pipeline(settings, fallback)
            pipeline._ats_map["adp"] = FailingScraper(
                settings, "adp", f"HTTP 404 for {make_company().careers_url}"
            )
            company = make_company(ats_type="adp", ats_slug="knowles")
            return await pipeline.scrape_company(company)

        result = asyncio.run(go())
        self.assertFalse(result.success)
        careers_url = make_company().careers_url
        self.assertEqual(
            result.error,
            f"adp binding failed: ScrapeError: HTTP 404 for {careers_url}; "
            "careers page: ScrapeError: page loaded but no job links found",
        )

    def test_claiming_ats_failure_is_included_when_no_stored_binding(self) -> None:
        settings = load_settings()

        async def go():
            fallback = FailingScraper(
                settings, "http", "page loaded but no job links found"
            )
            pipeline = build_pipeline(settings, fallback)
            pipeline.adp = FailingScraper(  # type: ignore[assignment]
                settings, "adp", "HTTP 404 for https://workforcenow.adp.com/x", claims=True
            )
            company = make_company()
            return await pipeline.scrape_company(company)

        result = asyncio.run(go())
        self.assertFalse(result.success)
        self.assertEqual(
            result.error,
            "adp binding failed: ScrapeError: HTTP 404 for "
            "https://workforcenow.adp.com/x; "
            "careers page: ScrapeError: page loaded but no job links found",
        )

    def test_no_ats_involvement_message_is_unchanged(self) -> None:
        settings = load_settings()

        async def go():
            fallback = FailingScraper(
                settings, "http", "page loaded but no job links found"
            )
            pipeline = build_pipeline(settings, fallback)
            company = make_company()
            company.careers_url = "https://example.com/careers"
            return await pipeline.scrape_company(company)

        result = asyncio.run(go())
        self.assertFalse(result.success)
        self.assertEqual(result.error, "ScrapeError: page loaded but no job links found")

    def test_failing_ats_then_successful_fallback_is_unaffected(self) -> None:
        settings = load_settings()

        async def go():
            fallback = SucceedingScraper(settings)
            pipeline = build_pipeline(settings, fallback)
            pipeline._ats_map["adp"] = FailingScraper(
                settings, "adp", "HTTP 404 for https://workforcenow.adp.com/x"
            )
            company = make_company(ats_type="adp", ats_slug="knowles")
            return await pipeline.scrape_company(company)

        result = asyncio.run(go())
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
        self.assertTrue(result.partial)


if __name__ == "__main__":
    unittest.main()
