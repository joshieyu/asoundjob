from __future__ import annotations

import asyncio
import threading
import time
import unittest
from unittest.mock import patch

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.ats import eightfold
from scraper.scrapers.ats.eightfold import EightfoldScraper
from scraper.scrapers.base import BaseScraper, RateLimitedError
from scraper.scrapers.fetch import FetchError
from scraper.scrapers.pipeline import ScrapePipeline

CAREERS_URL = "https://apply.careers.microsoft.com/careers?query=audio"


def make_company(ats_type: str = "eightfold") -> Company:
    return Company(
        id=7,
        name="Microsoft",
        slug="microsoft",
        category="Consumer Electronics & Tech",
        careers_url=CAREERS_URL,
        scrape_method="http",
        ats_type=ats_type,
        ats_slug="microsoft.com",
    )


def search_payload(count: int) -> dict:
    return {
        "data": {
            "positions": [
                {"id": 100 + i, "name": f"Audio Engineer {i}", "positionUrl": f"/job/{i}"}
                for i in range(count)
            ],
            "count": count,
        }
    }


def too_many(url: str) -> FetchError:
    return FetchError(f"HTTP 429 for {url}", 429)


class TestSearchRetries(unittest.TestCase):
    def setUp(self) -> None:
        self.sleeps: list[float] = []

        async def fake_sleep(delay: float) -> None:
            self.sleeps.append(delay)

        patcher = patch.object(eightfold.asyncio, "sleep", side_effect=fake_sleep)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_scrape(self, responses: list) -> list:
        calls: list[str] = []

        def fake_fetch(url, settings, *args, **kwargs):
            calls.append(url)
            if "position_details" in url:
                return {"data": {"jobDescription": "<p>Role</p>"}}
            outcome = responses.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        async def go():
            scraper = EightfoldScraper(load_settings())
            return await scraper.fetch_jobs(make_company())

        with patch("scraper.scrapers.ats.eightfold.fetch_json", side_effect=fake_fetch):
            jobs = asyncio.run(go())
        return jobs

    def test_a_429_is_retried_after_backoff(self) -> None:
        jobs = self.run_scrape([too_many("search"), search_payload(2)])
        self.assertEqual(len(jobs), 2)
        self.assertEqual(self.sleeps, [eightfold.RATE_LIMIT_BACKOFF_SECONDS[0]])

    def test_persistent_429_raises_rate_limited(self) -> None:
        attempts = len(eightfold.RATE_LIMIT_BACKOFF_SECONDS) + 1
        with self.assertRaises(RateLimitedError):
            self.run_scrape([too_many("search") for _ in range(attempts)])
        self.assertEqual(self.sleeps, list(eightfold.RATE_LIMIT_BACKOFF_SECONDS))

    def test_other_errors_are_not_retried(self) -> None:
        with self.assertRaises(FetchError):
            self.run_scrape([FetchError("HTTP 500 for search", 500)])
        self.assertEqual(self.sleeps, [])


class TestDetailThrottling(unittest.TestCase):
    def test_detail_429_stops_enrichment_but_keeps_jobs(self) -> None:
        detail_calls: list[str] = []

        def fake_fetch(url, settings, *args, **kwargs):
            if "position_details" in url:
                detail_calls.append(url)
                raise too_many(url)
            return search_payload(30)

        async def go():
            scraper = EightfoldScraper(load_settings())
            return await scraper.fetch_jobs(make_company())

        with patch("scraper.scrapers.ats.eightfold.fetch_json", side_effect=fake_fetch):
            jobs = asyncio.run(go())
        self.assertEqual(len(jobs), 30)
        self.assertLessEqual(len(detail_calls), eightfold.DETAIL_CONCURRENCY)

    def test_detail_requests_never_exceed_the_shared_limit(self) -> None:
        lock = threading.Lock()
        state = {"in_flight": 0, "peak": 0}

        def fake_fetch(url, settings, *args, **kwargs):
            if "position_details" not in url:
                return search_payload(40)
            with lock:
                state["in_flight"] += 1
                state["peak"] = max(state["peak"], state["in_flight"])
            time.sleep(0.002)
            with lock:
                state["in_flight"] -= 1
            return {"data": {}}

        async def go():
            scraper = EightfoldScraper(load_settings())
            await asyncio.gather(
                scraper.fetch_jobs(make_company()), scraper.fetch_jobs(make_company())
            )

        with patch("scraper.scrapers.ats.eightfold.fetch_json", side_effect=fake_fetch):
            asyncio.run(go())
        self.assertGreater(state["peak"], 1)
        self.assertLessEqual(state["peak"], eightfold.DETAIL_CONCURRENCY)


class TestEnrichmentBudget(unittest.TestCase):
    def test_slow_search_leaves_enrichment_only_the_remaining_time(self) -> None:
        settings = load_settings()
        budget = settings.per_company_timeout * eightfold.ENRICHMENT_BUDGET_FRACTION
        clock = {"now": 1000.0}
        detail_calls: list[str] = []

        def fake_fetch(url, settings, *args, **kwargs):
            if "position_details" in url:
                detail_calls.append(url)
                return {"data": {}}
            clock["now"] += budget + 1
            return search_payload(3)

        async def go():
            scraper = EightfoldScraper(settings)
            return await scraper.fetch_jobs(make_company())

        with patch(
            "scraper.scrapers.ats.eightfold.fetch_json", side_effect=fake_fetch
        ), patch(
            "scraper.scrapers.ats.eightfold.monotonic", side_effect=lambda: clock["now"]
        ):
            jobs = asyncio.run(go())
        self.assertEqual(len(jobs), 3)
        self.assertEqual(detail_calls, [])


class RateLimitedScraper(BaseScraper):
    name = "eightfold"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        raise RateLimitedError("eightfold rate limited (HTTP 429)")


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


class TestPipelineSkipsFallbackWhenRateLimited(unittest.TestCase):
    def run_pipeline(self, company: Company):
        settings = load_settings()

        async def go():
            fallback = RecordingFallback(settings)
            pipeline = ScrapePipeline(settings)
            pipeline._try_discovery = _no_discovery  # type: ignore[method-assign,assignment]
            pipeline.http = fallback  # type: ignore[assignment]
            pipeline._playwright_scraper = lambda: fallback  # type: ignore[method-assign]
            pipeline._stealth_scraper = lambda: fallback  # type: ignore[method-assign]
            limited = RateLimitedScraper(settings)
            pipeline._ats_map["eightfold"] = limited
            pipeline.eightfold = limited  # type: ignore[assignment]
            result = await pipeline.scrape_company(company)
            return result, fallback.calls

        return asyncio.run(go())

    def test_stored_binding_rate_limit_fails_without_fallback(self) -> None:
        result, fallback_calls = self.run_pipeline(make_company())
        self.assertFalse(result.success)
        self.assertTrue(result.rate_limited)
        self.assertEqual(fallback_calls, 0)
        assert result.error is not None
        self.assertIn("eightfold binding failed", result.error)
        self.assertIn("429", result.error)

    def test_claimed_board_rate_limit_fails_without_fallback(self) -> None:
        result, fallback_calls = self.run_pipeline(make_company(ats_type=""))
        self.assertFalse(result.success)
        self.assertEqual(fallback_calls, 0)


if __name__ == "__main__":
    unittest.main()
