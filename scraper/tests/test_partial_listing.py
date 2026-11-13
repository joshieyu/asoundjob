from __future__ import annotations

import asyncio
import gc
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper.config import load_settings
from scraper.main import keep_stored_descriptions
from scraper.models import Base, Company, Job
from scraper.scrapers.ats.apple import AppleScraper
from scraper.scrapers.base import (
    BaseScraper,
    RawJob,
    company_budget,
    listing,
    track_listing,
)
from scraper.scrapers.fetch import retry_on_timeout
from scraper.scrapers.pipeline import ScrapePipeline


def _wrap_hydration(payload: dict) -> str:
    encoded = json.dumps(payload).replace('"', '\\"')
    return (
        '<html><script>window.__staticRouterHydrationData = JSON.parse("'
        + encoded
        + '");</script></html>'
    )


def make_company(ats_type: str = "workday", priority: bool = False, extra=None) -> Company:
    return Company(
        id=9,
        name="Big Board Co",
        slug="big-board-co",
        category="Consumer Electronics & Tech",
        careers_url="https://bigboard.wd1.myworkdayjobs.com/External?q=audio",
        extra_careers_urls=extra,
        scrape_method="http",
        ats_type=ats_type,
        ats_slug="bigboard.wd1/External" if ats_type else None,
        priority=priority,
    )


def two_jobs() -> list[RawJob]:
    return [
        RawJob(title="Audio DSP Engineer", url="https://x/1", external_id="1"),
        RawJob(title="Acoustics Engineer", url="https://x/2", external_id="2"),
    ]


class PageThenReadTimeout(BaseScraper):
    name = "workday"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        jobs = listing()
        jobs.extend(two_jobs())
        raise requests.exceptions.ReadTimeout("Read timed out.")


class PageThenHang(BaseScraper):
    name = "workday"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        jobs = listing()
        jobs.extend(two_jobs())
        await asyncio.sleep(5)
        return jobs


class SlowButFinishes(BaseScraper):
    name = "workday"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        await asyncio.sleep(0.08)
        return two_jobs()


class RecordingFallback(BaseScraper):
    name = "generic"

    def __init__(self, settings) -> None:
        super().__init__(settings)
        self.calls = 0

    async def fetch_jobs(self, company):
        self.calls += 1
        return [RawJob(title="Page one", url="https://x/page-one")]


async def _no_discovery(company, html, overwrite=False):
    return None


def run_pipeline(company: Company, scraper_class):
    settings = replace(load_settings(), per_company_timeout=0.05)

    async def go():
        fallback = RecordingFallback(settings)
        pipeline = ScrapePipeline(settings)
        pipeline._try_discovery = _no_discovery  # type: ignore[method-assign,assignment]
        pipeline.http = fallback  # type: ignore[assignment]
        pipeline._playwright_scraper = lambda: fallback  # type: ignore[method-assign]
        pipeline._stealth_scraper = lambda: fallback  # type: ignore[method-assign]
        scraper = scraper_class(settings)
        pipeline._ats_map["workday"] = scraper
        pipeline.workday = scraper  # type: ignore[assignment]
        result = await pipeline.scrape_company(company)
        return result, fallback.calls

    return asyncio.run(go())


class TestKeepWhatWasRead(unittest.TestCase):
    def test_read_timeout_after_a_page_keeps_the_jobs(self) -> None:
        result, fallback_calls = run_pipeline(make_company(), PageThenReadTimeout)
        self.assertTrue(result.success)
        self.assertTrue(result.partial)
        self.assertTrue(result.salvaged)
        self.assertFalse(result.trust_empty)
        self.assertEqual([job.external_id for job in result.jobs], ["1", "2"])
        self.assertEqual(fallback_calls, 0)
        assert result.error is not None
        self.assertIn("listing cut short, kept 2 jobs", result.error)

    def test_company_timeout_after_a_page_keeps_the_jobs(self) -> None:
        result, fallback_calls = run_pipeline(make_company(ats_type=""), PageThenHang)
        self.assertTrue(result.success)
        self.assertTrue(result.partial)
        self.assertTrue(result.salvaged)
        self.assertEqual(len(result.jobs), 2)
        self.assertEqual(fallback_calls, 0)

    def test_a_cut_short_url_makes_a_multi_url_company_partial(self) -> None:
        company = make_company(
            extra=["https://bigboard.wd1.myworkdayjobs.com/External?q=speech"]
        )
        result, _ = run_pipeline(company, PageThenReadTimeout)
        self.assertTrue(result.success)
        self.assertTrue(result.partial)
        self.assertTrue(result.salvaged)
        self.assertFalse(result.trust_empty)

    def test_without_tracking_a_failure_stays_a_failure(self) -> None:
        settings = load_settings()
        result = asyncio.run(PageThenReadTimeout(settings).scrape(make_company()))
        self.assertFalse(result.success)
        self.assertTrue(result.timed_out)


class TestAppleKeepsEarlierPages(unittest.TestCase):
    def test_timeout_on_page_two_keeps_page_one(self) -> None:
        page_one = _wrap_hydration(
            {
                "loaderData": {
                    "search": {
                        "searchResults": [
                            {
                                "id": f"JOB-{i}",
                                "postingTitle": f"Audio Engineer {i}",
                                "locations": [{"name": "Cupertino"}],
                                "postingDate": "Nov 12, 2026",
                                "transformedPostingTitle": f"audio-engineer-{i}",
                                "reqId": f"JOB-{i}",
                            }
                            for i in range(20)
                        ],
                        "totalRecords": 300,
                        "page": 1,
                    }
                }
            }
        )

        def fake_fetch_html(url: str, settings: object) -> str:
            if "page=1" in url:
                return page_one
            raise requests.exceptions.ReadTimeout("Read timed out.")

        async def go():
            with track_listing():
                return await AppleScraper(load_settings()).scrape(
                    Company(id=1, name="Apple", slug="apple", category="x",
                            careers_url="https://jobs.apple.com/en-us/search")
                )

        with patch("scraper.scrapers.ats.apple.fetch_html", side_effect=fake_fetch_html):
            result = asyncio.run(go())
        self.assertTrue(result.success)
        self.assertTrue(result.salvaged)
        self.assertEqual(len(result.jobs), 20)


class TestPriorityBudget(unittest.TestCase):
    def test_priority_doubles_the_budget(self) -> None:
        settings = load_settings()
        self.assertEqual(
            company_budget(settings, make_company(priority=True)),
            settings.per_company_timeout * 2,
        )
        self.assertEqual(
            company_budget(settings, make_company()), settings.per_company_timeout
        )

    def test_priority_board_gets_time_to_finish(self) -> None:
        normal, _ = run_pipeline(make_company(), SlowButFinishes)
        self.assertFalse(normal.success)
        priority, _ = run_pipeline(make_company(priority=True), SlowButFinishes)
        self.assertTrue(priority.success)
        self.assertFalse(priority.partial)


class TestRetryOnTimeout(unittest.TestCase):
    def test_retries_once_then_succeeds(self) -> None:
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise requests.exceptions.ReadTimeout("slow")
            return "ok"

        self.assertEqual(retry_on_timeout(flaky), "ok")
        self.assertEqual(len(calls), 2)

    def test_gives_up_after_one_retry(self) -> None:
        calls = []

        def always_slow():
            calls.append(1)
            raise requests.exceptions.ReadTimeout("slow")

        with self.assertRaises(requests.exceptions.ReadTimeout):
            retry_on_timeout(always_slow)
        self.assertEqual(len(calls), 2)

    def test_other_errors_are_not_retried(self) -> None:
        calls = []

        def refused():
            calls.append(1)
            raise requests.exceptions.ConnectionError("refused")

        with self.assertRaises(requests.exceptions.ConnectionError):
            retry_on_timeout(refused)
        self.assertEqual(len(calls), 1)


class TestKeepStoredDescriptions(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        company = Company(name="Co", slug="co", category="x", careers_url="https://x")
        self.session.add(company)
        self.session.flush()
        self.company_id = company.id
        self.session.add(
            Job(
                company_id=company.id,
                title="Audio DSP Engineer",
                url="https://x/1",
                external_id="1",
                description="Design audio DSP for headphones.",
                source="scraper",
            )
        )
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        gc.collect()

    def test_missing_description_reuses_the_stored_one(self) -> None:
        jobs = two_jobs()
        keep_stored_descriptions(self.session, self.company_id, jobs)
        self.assertEqual(jobs[0].description, "Design audio DSP for headphones.")
        self.assertIsNone(jobs[1].description)

    def test_fresh_description_wins(self) -> None:
        jobs = two_jobs()
        jobs[0].description = "Updated description."
        keep_stored_descriptions(self.session, self.company_id, jobs)
        self.assertEqual(jobs[0].description, "Updated description.")


if __name__ == "__main__":
    unittest.main()
