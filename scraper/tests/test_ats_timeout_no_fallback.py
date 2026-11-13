from __future__ import annotations

import asyncio
import unittest
from dataclasses import replace

import requests
from urllib3.exceptions import NewConnectionError

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.base import BaseScraper
from scraper.scrapers.pipeline import ScrapePipeline


def make_company(ats_type: str = "workday") -> Company:
    return Company(
        id=9,
        name="Big Board Co",
        slug="big-board-co",
        category="Consumer Electronics & Tech",
        careers_url="https://bigboard.wd1.myworkdayjobs.com/External?q=audio",
        scrape_method="http",
        ats_type=ats_type,
        ats_slug="bigboard.wd1/External" if ats_type else None,
    )


class SlowScraper(BaseScraper):
    name = "workday"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        await asyncio.sleep(5)
        return []


class ReadTimeoutScraper(BaseScraper):
    name = "workday"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        raise requests.exceptions.ReadTimeout("Read timed out. (read timeout=15.0)")


class WrappedReadTimeoutScraper(BaseScraper):
    name = "workday"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        try:
            raise requests.exceptions.ReadTimeout("Read timed out.")
        except requests.exceptions.ReadTimeout as exc:
            raise RuntimeError("listing fetch failed") from exc


class NotFoundScraper(BaseScraper):
    name = "workday"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        raise requests.exceptions.HTTPError("404 Client Error: Not Found")


class DnsFailureScraper(BaseScraper):
    name = "workday"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        try:
            raise NewConnectionError(None, "Failed to resolve host")  # type: ignore[arg-type]
        except NewConnectionError as exc:
            raise requests.exceptions.ConnectionError(exc) from exc


class RecordingFallback(BaseScraper):
    name = "generic"

    def __init__(self, settings) -> None:
        super().__init__(settings)
        self.calls = 0

    async def fetch_jobs(self, company):
        self.calls += 1
        return [object()]


async def _no_discovery(company, html, overwrite=False):
    return None


class TestAtsTimeoutSkipsFallback(unittest.TestCase):
    def run_pipeline(self, company: Company, scraper_class=SlowScraper):
        settings = replace(load_settings(), per_company_timeout=0.05)

        async def go():
            fallback = RecordingFallback(settings)
            pipeline = ScrapePipeline(settings)
            pipeline._try_discovery = _no_discovery  # type: ignore[method-assign,assignment]
            pipeline.http = fallback  # type: ignore[assignment]
            pipeline._playwright_scraper = lambda: fallback  # type: ignore[method-assign]
            pipeline._stealth_scraper = lambda: fallback  # type: ignore[method-assign]
            slow = scraper_class(settings)
            pipeline._ats_map["workday"] = slow
            pipeline.workday = slow  # type: ignore[assignment]
            result = await pipeline.scrape_company(company)
            return result, fallback.calls

        return asyncio.run(go())

    def test_stored_binding_timeout_fails_without_fallback(self) -> None:
        result, fallback_calls = self.run_pipeline(make_company())
        self.assertFalse(result.success)
        self.assertTrue(result.timed_out)
        self.assertEqual(fallback_calls, 0)
        assert result.error is not None
        self.assertIn("workday binding failed: timeout", result.error)

    def test_claimed_board_timeout_fails_without_fallback(self) -> None:
        result, fallback_calls = self.run_pipeline(make_company(ats_type=""))
        self.assertFalse(result.success)
        self.assertTrue(result.timed_out)
        self.assertEqual(fallback_calls, 0)

    def test_stored_binding_read_timeout_fails_without_fallback(self) -> None:
        result, fallback_calls = self.run_pipeline(make_company(), ReadTimeoutScraper)
        self.assertFalse(result.success)
        self.assertTrue(result.timed_out)
        self.assertEqual(fallback_calls, 0)

    def test_claimed_board_read_timeout_fails_without_fallback(self) -> None:
        result, fallback_calls = self.run_pipeline(make_company(ats_type=""), ReadTimeoutScraper)
        self.assertTrue(result.timed_out)
        self.assertEqual(fallback_calls, 0)

    def test_wrapped_read_timeout_fails_without_fallback(self) -> None:
        result, fallback_calls = self.run_pipeline(make_company(), WrappedReadTimeoutScraper)
        self.assertTrue(result.timed_out)
        self.assertEqual(fallback_calls, 0)

    def test_other_errors_still_fall_back_as_partial(self) -> None:
        result, fallback_calls = self.run_pipeline(make_company(ats_type=""), NotFoundScraper)
        self.assertTrue(result.success)
        self.assertTrue(result.partial)
        self.assertFalse(result.timed_out)
        self.assertEqual(fallback_calls, 1)

    def test_connection_failure_is_not_a_timeout(self) -> None:
        result, fallback_calls = self.run_pipeline(make_company(ats_type=""), DnsFailureScraper)
        self.assertFalse(result.timed_out)
        self.assertEqual(fallback_calls, 1)


if __name__ == "__main__":
    unittest.main()
