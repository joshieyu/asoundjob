from __future__ import annotations

import unittest
from datetime import date, timedelta

from scraper.scrapers.ats.workday import (
    WorkdayScraper,
    _build_base,
    _extract_description,
    _parse_list_item,
    _parse_relative_date,
    _parse_time_type,
)


def make_company(url: str, audio_scope: str = "native"):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url=url,
        audio_scope=audio_scope,
    )


LIST_ITEM = {
    "title": "Senior DSP Engineer",
    "externalPath": "/job/Berlin/Senior-DSP-Engineer_R12345",
    "timeType": "Full time",
    "locationsText": "Berlin, Germany",
    "postedOn": "Posted 3 Days Ago",
    "bulletFields": ["R12345"],
}

DETAIL = {
    "jobPostingInfo": {
        "id": "R12345",
        "title": "Senior DSP Engineer",
        "jobDescription": "<p>Work on audio DSP algorithms.</p>",
        "postedOn": "Posted 3 Days Ago",
        "startDate": "2026-08-20",
    }
}


class TestWorkdayParser(unittest.TestCase):
    def test_parse_list_item(self) -> None:
        job = _parse_list_item(LIST_ITEM, "https://sonos.wd1.myworkdayjobs.com")
        assert job is not None
        self.assertEqual(job.title, "Senior DSP Engineer")
        self.assertEqual(
            job.external_id, "/job/Berlin/Senior-DSP-Engineer_R12345"
        )
        self.assertEqual(job.location, "Berlin, Germany")
        self.assertEqual(job.job_type, "full-time")
        expected = date.today() - timedelta(days=3)
        self.assertEqual(job.posted_date, expected)

    def test_parse_list_item_missing_fields(self) -> None:
        self.assertIsNone(_parse_list_item({}, "https://example.com"))
        self.assertIsNone(
            _parse_list_item({"title": "Engineer"}, "https://example.com")
        )

    def test_extract_description(self) -> None:
        desc = _extract_description(DETAIL)
        self.assertEqual(desc, "<p>Work on audio DSP algorithms.</p>")

    def test_extract_description_no_info(self) -> None:
        self.assertIsNone(_extract_description({}))

    def test_parse_time_type(self) -> None:
        self.assertEqual(_parse_time_type("Full time"), "full-time")
        self.assertEqual(_parse_time_type("Part time"), "part-time")
        self.assertEqual(_parse_time_type("Contract"), "contract")
        self.assertIsNone(_parse_time_type(None))

    def test_parse_relative_date(self) -> None:
        today = date.today()
        self.assertEqual(_parse_relative_date("Posted Today"), today)
        self.assertEqual(
            _parse_relative_date("Posted 5 Days Ago"),
            today - timedelta(days=5),
        )
        self.assertEqual(
            _parse_relative_date("Posted 2 Weeks Ago"),
            today - timedelta(weeks=2),
        )
        self.assertEqual(
            _parse_relative_date("Posted 3 Hours Ago"), today
        )
        self.assertIsNone(_parse_relative_date("Random text"))
        self.assertIsNone(_parse_relative_date(None))

    def test_extract_slug(self) -> None:
        self.assertEqual(
            WorkdayScraper.extract_slug("https://sonos.wd1.myworkdayjobs.com/Sonos"),
            "sonos.wd1/Sonos",
        )
        self.assertEqual(
            WorkdayScraper.extract_slug(
                "https://sec.wd3.myworkdayjobs.com/Samsung_Careers"
            ),
            "sec.wd3/Samsung_Careers",
        )
        self.assertEqual(
            WorkdayScraper.extract_slug(
                "https://sky.wd3.myworkdayjobs.com/en-US/sky_careers"
            ),
            "sky.wd3/sky_careers",
        )
        self.assertEqual(
            WorkdayScraper.extract_slug(
                "https://belkin.wd5.myworkdayjobs.com/belkin_careers/jobs"
            ),
            "belkin.wd5/belkin_careers",
        )
        self.assertIsNone(
            WorkdayScraper.extract_slug("https://example.com/careers")
        )

    def test_build_base(self) -> None:
        self.assertEqual(
            _build_base(
                "https://sonos.wd1.myworkdayjobs.com/Sonos",
                "sonos.wd1",
            ),
            "https://sonos.wd1.myworkdayjobs.com",
        )
        self.assertEqual(
            _build_base("https://careers.bose.com/us/en", "boseallaboutme.wd503"),
            "https://boseallaboutme.wd503.myworkdayjobs.com",
        )
        self.assertEqual(
            _build_base("https://careers.example.com", "acme"),
            "https://acme.wd1.myworkdayjobs.com",
        )

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = WorkdayScraper(load_settings())
        self.assertTrue(
            scraper.can_handle(make_company("https://sonos.wd1.myworkdayjobs.com/Sonos"))
        )
        self.assertTrue(
            scraper.can_handle(
                make_company("https://sec.wd3.myworkdayjobs.com/Samsung_Careers")
            )
        )
        self.assertFalse(
            scraper.can_handle(make_company("https://jobs.lever.co/acme"))
        )
        self.assertFalse(scraper.can_handle(make_company("")))


if __name__ == "__main__":
    unittest.main()
