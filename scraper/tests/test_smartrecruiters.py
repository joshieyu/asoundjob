from __future__ import annotations

import unittest
from datetime import date

from scraper.scrapers.ats.smartrecruiters import (
    SmartRecruitersScraper,
    _extract_detail_description,
    _format_location,
    _parse_list_item,
)


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url=url,
    )


LIST_ITEM = {
    "id": 744000056999494,
    "name": "Senior Audio Engineer",
    "releasedDate": "2026-08-01T17:29:16.500Z",
    "location": {"city": "Montréal", "region": "QC", "country": "ca"},
    "typeOfEmployment": {"label": "Full-time"},
    "ref": "https://careers.smartrecruiters.com/acme/744000056999494",
}

DETAIL_PAYLOAD = {
    "jobAd": {
        "sections": {
            "jobDescription": {"text": "<p>You will work on audio DSP.</p>"},
            "companyDescription": {"text": "<p>We are an audio company.</p>"},
            "qualifications": {"text": "<ul><li>C++ experience</li></ul>"},
        }
    }
}


class TestSmartRecruitersParser(unittest.TestCase):
    def test_parse_list_item(self) -> None:
        job = _parse_list_item(LIST_ITEM)
        assert job is not None
        self.assertEqual(job.title, "Senior Audio Engineer")
        self.assertEqual(job.external_id, "744000056999494")
        self.assertEqual(job.url, "https://careers.smartrecruiters.com/acme/744000056999494")
        self.assertEqual(job.location, "Montréal, ca")
        self.assertEqual(job.job_type, "full-time")
        self.assertEqual(job.posted_date, date(2026, 8, 1))

    def test_parse_list_item_missing_title(self) -> None:
        item = {"id": 1, "ref": "https://example.com"}
        self.assertIsNone(_parse_list_item(item))

    def test_format_location(self) -> None:
        self.assertEqual(_format_location("Remote"), "Remote")
        self.assertEqual(
            _format_location({"city": "Berlin", "country": "Germany"}),
            "Berlin, Germany",
        )
        self.assertEqual(_format_location({"city": "Berlin"}), "Berlin")
        self.assertEqual(_format_location({"country": "Germany"}), "Germany")
        self.assertIsNone(_format_location(None))
        self.assertIsNone(_format_location({}))

    def test_extract_detail_description(self) -> None:
        desc = _extract_detail_description(DETAIL_PAYLOAD)
        assert desc is not None
        self.assertIn("audio DSP", desc)
        self.assertIn("audio company", desc)
        self.assertIn("C++ experience", desc)

    def test_extract_detail_description_no_job_ad(self) -> None:
        self.assertIsNone(_extract_detail_description({"jobAd": None}))
        self.assertIsNone(_extract_detail_description({}))

    def test_extract_slug(self) -> None:
        self.assertEqual(
            SmartRecruitersScraper.extract_slug("https://careers.smartrecruiters.com/DONTNOD"),
            "DONTNOD",
        )
        self.assertIsNone(
            SmartRecruitersScraper.extract_slug("https://example.com/careers")
        )

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = SmartRecruitersScraper(load_settings())
        self.assertTrue(scraper.can_handle(make_company("https://careers.smartrecruiters.com/DONTNOD")))
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))


if __name__ == "__main__":
    unittest.main()
