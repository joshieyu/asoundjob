from __future__ import annotations

import unittest
from datetime import date

from scraper.scrapers.ats.recruitee import RecruiteeScraper, parse_offers


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url=url,
    )


RECRUITEE_PAYLOAD = {
    "offers": [
        {
            "id": 12345,
            "slug": "senior-audio-engineer",
            "title": "Senior Audio Engineer",
            "careers_url": "https://auditdata.recruitee.com/o/senior-audio-engineer",
            "description": "<p>Work on audio systems.</p>",
            "requirements": "<p>C++ and DSP knowledge</p>",
            "city": "Copenhagen",
            "country": "Denmark",
            "employment_type_code": "full_time",
            "remote": True,
            "published_at": "2026-08-15T10:00:00Z",
            "salary": {"min": 60000, "max": 90000, "currency": "EUR"},
        },
        {
            "id": 99,
            "title": "",
            "careers_url": "",
        },
    ]
}


class TestRecruiteeParser(unittest.TestCase):
    def test_parse_offers(self) -> None:
        jobs = parse_offers(RECRUITEE_PAYLOAD)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Senior Audio Engineer")
        self.assertEqual(job.external_id, "12345")
        self.assertEqual(job.url, "https://auditdata.recruitee.com/o/senior-audio-engineer")
        self.assertEqual(job.location, "Copenhagen, Denmark")
        self.assertEqual(job.job_type, "full-time")
        self.assertTrue(job.remote_hint)
        self.assertEqual(job.posted_date, date(2026, 8, 15))
        self.assertIn("Work on audio systems", job.description or "")
        self.assertIn("Salary:", job.description or "")

    def test_parse_offers_rejects_non_dict(self) -> None:
        with self.assertRaises(ValueError):
            parse_offers([])

    def test_parse_offers_rejects_bad_offers_field(self) -> None:
        with self.assertRaises(ValueError):
            parse_offers({"offers": "not a list"})

    def test_parse_offers_no_salary(self) -> None:
        payload = {
            "offers": [
                {
                    "id": 1,
                    "title": "Engineer",
                    "careers_url": "https://example.com",
                    "description": "No salary info",
                    "salary": {},
                }
            ]
        }
        jobs = parse_offers(payload)
        self.assertEqual(jobs[0].description, "No salary info")

    def test_extract_slug(self) -> None:
        self.assertEqual(
            RecruiteeScraper.extract_slug("https://auditdata.recruitee.com/"),
            "auditdata",
        )
        self.assertIsNone(
            RecruiteeScraper.extract_slug("https://example.com/careers")
        )

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = RecruiteeScraper(load_settings())
        self.assertTrue(scraper.can_handle(make_company("https://auditdata.recruitee.com/")))
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))


if __name__ == "__main__":
    unittest.main()
