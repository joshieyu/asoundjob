from __future__ import annotations

import unittest

from scraper.scrapers.ats.jibe import JibeScraper, parse_jobs
from scraper.scrapers.base import ScrapeError


def make_company(url: str, ats_type=None):
    from scraper.models import Company

    return Company(
        id=1,
        name="Garmin",
        slug="garmin",
        category="Audio Hardware",
        careers_url=url,
        ats_type=ats_type,
    )


JIBE_PAYLOAD = {
    "totalCount": 2,
    "count": 2,
    "jobs": [
        {
            "data": {
                "title": "Audio DSP Engineer",
                "slug": "18832",
                "req_id": "R-1000",
                "description": "<p>Build audio pipelines.</p>",
                "city": "Olathe",
                "state": "Kansas",
                "country": "United States",
                "posted_date": "2026-06-16T16:04:26+0000",
                "employment_type": "Full time",
                "apply_url": "https://login.example.com/apply/18832",
            }
        },
        {
            "data": {
                "title": "",
                "slug": "18833",
            }
        },
    ],
}


class TestCanHandle(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = JibeScraper(load_settings())

    def test_garmin_url_is_handled(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(make_company("https://careers.garmin.com/jobs?keywords=audio"))
        )

    def test_ats_type_jibe_is_handled_regardless_of_url(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(
                make_company("https://example.com/jobs", ats_type="jibe")
            )
        )

    def test_unrelated_host_with_jobs_path_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("https://example.com/jobs")))

    def test_empty_careers_url_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("")))

    def test_www_prefix_is_stripped(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(make_company("https://www.careers.garmin.com/jobs"))
        )


class TestParseJobs(unittest.TestCase):
    def test_builds_public_url_from_slug_not_apply_url(self) -> None:
        jobs = parse_jobs(JIBE_PAYLOAD, "careers.garmin.com")
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Audio DSP Engineer")
        self.assertEqual(job.url, "https://careers.garmin.com/jobs/18832")
        self.assertEqual(job.external_id, "18832")

    def test_location_built_from_city_state_country(self) -> None:
        jobs = parse_jobs(JIBE_PAYLOAD, "careers.garmin.com")
        self.assertEqual(jobs[0].location, "Olathe, Kansas, United States")

    def test_location_none_when_all_absent(self) -> None:
        payload = {
            "totalCount": 1,
            "jobs": [{"data": {"title": "Engineer", "slug": "1"}}],
        }
        jobs = parse_jobs(payload, "careers.garmin.com")
        self.assertIsNone(jobs[0].location)

    def test_skips_entry_missing_title(self) -> None:
        jobs = parse_jobs(JIBE_PAYLOAD, "careers.garmin.com")
        self.assertEqual(len(jobs), 1)

    def test_skips_malformed_entries(self) -> None:
        payload = {
            "totalCount": 4,
            "jobs": [
                "not a dict",
                {"no": "data key"},
                {"data": "not a dict"},
                {"data": {"title": "Engineer"}},
            ],
        }
        jobs = parse_jobs(payload, "careers.garmin.com")
        self.assertEqual(jobs, [])

    def test_non_dict_payload_raises_scrape_error(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_jobs([], "careers.garmin.com")

    def test_non_list_jobs_field_raises_scrape_error(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_jobs({"jobs": "not a list"}, "careers.garmin.com")


if __name__ == "__main__":
    unittest.main()
