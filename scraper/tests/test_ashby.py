from __future__ import annotations

import unittest
from datetime import date

from scraper.scrapers.ats.ashby import AshbyScraper, parse_jobs


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url=url,
    )


ASHBY_PAYLOAD = {
    "jobs": [
        {
            "id": "306b0995-38c7-4133-b5a4-1a75085d4cc1",
            "title": "Senior DSP Engineer",
            "department": "Tech",
            "employmentType": "FullTime",
            "location": {"name": "Stockholm HQ"},
            "publishedAt": "2026-08-05T14:08:23.833+00:00",
            "jobUrl": "https://jobs.ashbyhq.com/testco/306b0995",
            "descriptionHtml": "<p>Work on audio engines.</p>",
            "descriptionPlain": "Work on audio engines.",
        },
        {
            "id": "abc",
            "title": "",
            "jobUrl": "https://jobs.ashbyhq.com/testco/abc",
        },
    ],
    "apiVersion": "1",
}


class TestAshbyParser(unittest.TestCase):
    def test_parse_jobs(self) -> None:
        jobs = parse_jobs(ASHBY_PAYLOAD)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Senior DSP Engineer")
        self.assertEqual(job.external_id, "306b0995-38c7-4133-b5a4-1a75085d4cc1")
        self.assertEqual(job.url, "https://jobs.ashbyhq.com/testco/306b0995")
        self.assertEqual(job.location, "Stockholm HQ")
        self.assertEqual(job.job_type, "full-time")
        self.assertEqual(job.description, "<p>Work on audio engines.</p>")
        self.assertEqual(job.posted_date, date(2026, 8, 5))

    def test_parse_jobs_rejects_non_dict(self) -> None:
        with self.assertRaises(ValueError):
            parse_jobs([])

    def test_parse_jobs_rejects_bad_jobs_field(self) -> None:
        with self.assertRaises(ValueError):
            parse_jobs({"jobs": "not a list"})

    def test_parse_jobs_string_location(self) -> None:
        payload = {
            "jobs": [
                {
                    "id": "1",
                    "title": "Engineer",
                    "jobUrl": "https://example.com",
                    "location": "Remote",
                }
            ]
        }
        jobs = parse_jobs(payload)
        self.assertEqual(jobs[0].location, "Remote")

    def test_extract_slug(self) -> None:
        self.assertEqual(
            AshbyScraper.extract_slug("https://jobs.ashbyhq.com/epidemic-sound"),
            "epidemic-sound",
        )
        self.assertIsNone(AshbyScraper.extract_slug("https://example.com/careers"))

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = AshbyScraper(load_settings())
        self.assertTrue(scraper.can_handle(make_company("https://jobs.ashbyhq.com/suno")))
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))


if __name__ == "__main__":
    unittest.main()
