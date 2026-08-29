from __future__ import annotations

import asyncio
import unittest

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.base import BaseScraper, ScrapeError, ScrapeResult
from scraper.scrapers.pipeline import ScrapePipeline

GREENHOUSE_PAGE = (
    "<html><body><iframe "
    'src="https://boards.greenhouse.io/embed/job_board?for=acmeaudio">'
    "</iframe></body></html>"
)


def make_company(scrape_method: str = "http") -> Company:
    return Company(
        id=7,
        name="Acme Audio",
        slug="acme-audio",
        category="Professional Audio & Live Sound",
        careers_url="https://acmeaudio.example/careers",
        scrape_method=scrape_method,
    )


class RecordingScraper(BaseScraper):
    name = "recording"

    def __init__(self, settings, html: str, fail: bool) -> None:
        super().__init__(settings)
        self.html = html
        self.fail = fail

    async def fetch_jobs(self, company):
        self._last_html = self.html
        if self.fail:
            raise ScrapeError("page loaded but no job links found")
        return []


class TestHtmlPreservedOnFailure(unittest.TestCase):
    def test_failed_scrape_keeps_html(self) -> None:
        scraper = RecordingScraper(load_settings(), GREENHOUSE_PAGE, fail=True)
        result = asyncio.run(scraper.scrape(make_company()))
        self.assertFalse(result.success)
        self.assertEqual(result.html, GREENHOUSE_PAGE)

    def test_successful_scrape_still_keeps_html(self) -> None:
        scraper = RecordingScraper(load_settings(), GREENHOUSE_PAGE, fail=False)
        result = asyncio.run(scraper.scrape(make_company()))
        self.assertTrue(result.success)
        self.assertEqual(result.html, GREENHOUSE_PAGE)


class TestDiscoveryOnFailure(unittest.TestCase):
    def _run(self, html: str) -> tuple[ScrapeResult, list]:
        persisted: list = []

        async def go():
            settings = load_settings()
            pipeline = ScrapePipeline(settings)
            pipeline._persist_ats_discovery = (  # type: ignore[method-assign]
                lambda company_id, ats_type, ats_slug, overwrite=False: persisted.append(
                    (company_id, ats_type, ats_slug)
                )
            )
            failing = RecordingScraper(settings, html, fail=True)
            pipeline.http = failing  # type: ignore[assignment]
            pipeline._playwright_scraper = lambda: failing  # type: ignore[method-assign]
            pipeline._stealth_scraper = lambda: failing  # type: ignore[method-assign]
            return await pipeline.scrape_company(make_company())

        return asyncio.run(go()), persisted

    def test_discovery_runs_when_every_attempt_fails(self) -> None:
        result, persisted = self._run(GREENHOUSE_PAGE)
        self.assertFalse(result.success)
        self.assertIn((7, "greenhouse", "acmeaudio"), persisted)

    def test_no_discovery_when_page_has_no_ats(self) -> None:
        result, persisted = self._run("<html><body>No openings</body></html>")
        self.assertFalse(result.success)
        self.assertEqual(persisted, [])


WORKDAY_PAGE = (
    "<html><body>"
    '<a href="https://boseallaboutme.wd503.myworkdayjobs.com/Bose_Careers">Jobs</a>'
    "</body></html>"
)


class TestStoredAtsSelfHealing(unittest.TestCase):
    def _run(self, html: str, stored_type: str, stored_slug: str) -> list:
        persisted: list = []

        async def go():
            settings = load_settings()
            pipeline = ScrapePipeline(settings)
            pipeline._persist_ats_discovery = (  # type: ignore[method-assign]
                lambda company_id, ats_type, ats_slug, overwrite=False: persisted.append(
                    (ats_type, ats_slug, overwrite)
                )
            )
            failing = RecordingScraper(settings, html, fail=True)
            for key in list(pipeline._ats_map):
                pipeline._ats_map[key] = failing
            pipeline.http = failing  # type: ignore[assignment]
            pipeline._playwright_scraper = lambda: failing  # type: ignore[method-assign]
            pipeline._stealth_scraper = lambda: failing  # type: ignore[method-assign]
            company = make_company()
            company.ats_type = stored_type
            company.ats_slug = stored_slug
            return await pipeline.scrape_company(company)

        asyncio.run(go())
        return persisted

    def test_failed_stored_route_is_corrected(self) -> None:
        persisted = self._run(WORKDAY_PAGE, "workday", "Bose_Careers")
        self.assertIn(
            ("workday", "boseallaboutme.wd503/Bose_Careers", True), persisted
        )

    def test_unchanged_slug_is_not_rewritten(self) -> None:
        persisted = self._run(
            WORKDAY_PAGE, "workday", "boseallaboutme.wd503/Bose_Careers"
        )
        self.assertEqual(persisted, [])

    def test_no_overwrite_when_no_stored_ats(self) -> None:
        persisted = self._run(WORKDAY_PAGE, "", "")
        self.assertTrue(persisted)
        self.assertTrue(all(entry[2] is False for entry in persisted))


if __name__ == "__main__":
    unittest.main()
