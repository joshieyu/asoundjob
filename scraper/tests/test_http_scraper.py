from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.base import ScrapeError
from scraper.scrapers.http_scraper import HttpScraper

LISTING_HTML = """
<html><body>
<a href="https://example.com/careers/jobs/1">Audio DSP Engineer</a>
<a href="https://example.com/careers/jobs/2">Acoustic Engineer</a>
</body></html>
"""

NO_JOBS_HTML = "<html><body><h1>Careers</h1><p>Nothing here yet.</p></body></html>"


def make_company() -> Company:
    company = Company(
        name="Acme Audio",
        slug="acme-audio",
        category="Professional Audio & Live Sound",
        careers_url="https://example.com/careers",
        verified=True,
    )
    company.id = 0
    return company


class TestHttpScraper(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = load_settings()
        self.scraper = HttpScraper(self.settings)
        self.company = make_company()

    def test_extracted_jobs_are_returned(self) -> None:
        with patch(
            "scraper.scrapers.http_scraper.fetch_html",
            side_effect=lambda url, settings: LISTING_HTML,
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))
        self.assertEqual(len(jobs), 2)

    def test_no_job_links_raises_rather_than_returning_empty(self) -> None:
        with patch(
            "scraper.scrapers.http_scraper.fetch_html",
            side_effect=lambda url, settings: NO_JOBS_HTML,
        ):
            with self.assertRaises(ScrapeError):
                asyncio.run(self.scraper.fetch_jobs(self.company))

    def test_scrape_reports_failure_so_the_pipeline_falls_through(self) -> None:
        with patch(
            "scraper.scrapers.http_scraper.fetch_html",
            side_effect=lambda url, settings: NO_JOBS_HTML,
        ):
            result = asyncio.run(self.scraper.scrape(self.company))
        self.assertFalse(result.success)
        self.assertEqual(result.jobs, [])
        self.assertIsNotNone(result.html)

    def test_missing_careers_url_raises(self) -> None:
        self.company.careers_url = None
        with self.assertRaises(ValueError):
            asyncio.run(self.scraper.fetch_jobs(self.company))


if __name__ == "__main__":
    unittest.main()
