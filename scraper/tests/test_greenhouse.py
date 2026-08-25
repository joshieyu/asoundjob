from __future__ import annotations

import unittest
from datetime import date

from scraper.scrapers.ats.greenhouse import GreenhouseScraper, decode_content, parse_board
from scraper.scrapers.base import ScrapeResult


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url=url,
    )


GREENHOUSE_PAYLOAD = {
    "jobs": [
        {
            "id": 123456,
            "title": "Senior DSP Engineer",
            "updated_at": "2026-08-01T12:00:00-04:00",
            "absolute_url": "https://boards.greenhouse.io/testco/jobs/123456",
            "location": {"name": "San Francisco, CA"},
            "content": None,
        },
        {
            "id": 789,
            "title": "",
            "absolute_url": "https://boards.greenhouse.io/testco/jobs/789",
            "location": {"name": "Remote"},
        },
        {
            "id": 999,
            "title": "Audio QA Tester",
            "absolute_url": "https://boards.greenhouse.io/testco/jobs/999",
            "location": None,
        },
    ]
}


class TestGreenhouseParser(unittest.TestCase):
    def test_parse_board(self) -> None:
        jobs = parse_board(GREENHOUSE_PAYLOAD)
        self.assertEqual(len(jobs), 2)
        first = jobs[0]
        self.assertEqual(first.title, "Senior DSP Engineer")
        self.assertEqual(first.external_id, "123456")
        self.assertEqual(first.location, "San Francisco, CA")
        self.assertEqual(first.posted_date, date(2026, 8, 1))
        self.assertIn("greenhouse.io/testco/jobs/123456", first.url)

    def test_extract_slug(self) -> None:
        self.assertEqual(
            GreenhouseScraper.extract_slug("https://job-boards.greenhouse.io/amplitude"),
            "amplitude",
        )
        self.assertEqual(
            GreenhouseScraper.extract_slug("https://boards.greenhouse.io/embed/job_board?for=acme"),
            "embed",
        )
        self.assertIsNone(
            GreenhouseScraper.extract_slug("https://example.com/careers")
        )

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = GreenhouseScraper(load_settings())
        self.assertTrue(scraper.can_handle(make_company("https://job-boards.greenhouse.io/calm")))
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))

    def test_decode_content(self) -> None:
        import base64

        encoded = base64.b64encode("<p>Hello</p>".encode()).decode()
        self.assertEqual(decode_content(encoded), "<p>Hello</p>")
        self.assertIsNone(decode_content(None))


class TestScrapeResult(unittest.TestCase):
    def test_defaults(self) -> None:
        result = ScrapeResult(company_id=1)
        self.assertFalse(result.success)
        self.assertEqual(result.jobs, [])


if __name__ == "__main__":
    unittest.main()
