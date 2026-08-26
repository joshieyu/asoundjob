from __future__ import annotations

import unittest

from scraper.scrapers.ats.bamboohr import (
    BambooHRScraper,
    _extract_description,
    _format_location,
    parse_list,
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


BAMBOO_LIST = {
    "meta": {},
    "result": [
        {
            "id": "40",
            "jobOpeningName": "Customer Support Agent - Audio",
            "departmentLabel": "Marketing",
            "employmentStatusLabel": "Contractor",
            "location": {"city": "London", "state": None, "addressCountry": "United Kingdom"},
            "isRemote": False,
            "datePosted": "2026-08-01",
        },
        {
            "id": "45",
            "jobOpeningName": "DSP Engineer",
            "employmentStatusLabel": "Full-Time",
            "location": {"city": "Boston", "addressCountry": "USA"},
            "isRemote": True,
        },
        {
            "id": "",
            "jobOpeningName": "No ID",
        },
    ],
}

BAMBOO_DETAIL = {
    "result": {
        "jobOpening": {
            "jobOpeningName": "Customer Support Agent - Audio",
            "description": "<p>Provide support for audio products.</p>",
        }
    }
}


class TestBambooHRParser(unittest.TestCase):
    def test_parse_list(self) -> None:
        jobs = parse_list(BAMBOO_LIST, "cambridgeaudio")
        self.assertEqual(len(jobs), 2)
        first = jobs[0]
        self.assertEqual(first.title, "Customer Support Agent - Audio")
        self.assertEqual(first.external_id, "40")
        self.assertEqual(first.url, "https://cambridgeaudio.bamboohr.com/careers/40")
        self.assertEqual(first.location, "London, United Kingdom")
        self.assertEqual(first.job_type, "contract")
        self.assertFalse(first.remote_hint)

        second = jobs[1]
        self.assertEqual(second.title, "DSP Engineer")
        self.assertEqual(second.job_type, "full-time")
        self.assertTrue(second.remote_hint)

    def test_parse_list_rejects_non_dict(self) -> None:
        with self.assertRaises(ValueError):
            parse_list([], "sub")

    def test_parse_list_rejects_bad_result(self) -> None:
        with self.assertRaises(ValueError):
            parse_list({"result": "not a list"}, "sub")

    def test_format_location(self) -> None:
        self.assertEqual(
            _format_location({"city": "Berlin", "addressCountry": "Germany"}),
            "Berlin, Germany",
        )
        self.assertEqual(_format_location("Remote"), "Remote")
        self.assertIsNone(_format_location(None))
        self.assertIsNone(_format_location({}))

    def test_extract_description(self) -> None:
        desc = _extract_description(BAMBOO_DETAIL)
        self.assertEqual(desc, "<p>Provide support for audio products.</p>")

    def test_extract_description_no_result(self) -> None:
        self.assertIsNone(_extract_description({}))

    def test_extract_slug(self) -> None:
        self.assertEqual(
            BambooHRScraper.extract_slug("https://softube.bamboohr.com/careers"),
            "softube",
        )
        self.assertIsNone(
            BambooHRScraper.extract_slug("https://example.com/careers")
        )

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = BambooHRScraper(load_settings())
        self.assertTrue(scraper.can_handle(make_company("https://softube.bamboohr.com/careers")))
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))


if __name__ == "__main__":
    unittest.main()
