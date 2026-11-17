from __future__ import annotations

import unittest
from datetime import date

from scraper.scrapers.ats.awsm import AwsmScraper, build_api_url, parse_jobs
from scraper.scrapers.base import ScrapeError


def make_company(url: str, ats_type=None):
    from scraper.models import Company

    return Company(
        id=1,
        name="IAG",
        slug="iag",
        category="Hi-Fi & Consumer Speakers",
        careers_url=url,
        ats_type=ats_type,
    )


PAYLOAD = [
    {
        "id": 8984,
        "date": "2026-09-07T01:39:31",
        "date_gmt": "2026-09-07T00:39:31",
        "link": "https://iaggroup.com/jobs/acousitic-engineer/",
        "title": {"rendered": "Acoustics Engineer &amp; Designer"},
        "content": {"rendered": "<p>Design loudspeakers.</p>"},
        "class_list": [
            "post-8984",
            "department-rd",
            "employment-type-full-time",
            "location-china",
            "location-shenzhen",
        ],
    },
    {"id": 1, "link": "https://iaggroup.com/jobs/x/", "title": {"rendered": " "}},
    {"id": 2, "title": {"rendered": "No link"}},
]


class TestCanHandle(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = AwsmScraper(load_settings())

    def test_known_host_is_handled(self) -> None:
        self.assertTrue(self.scraper.can_handle(make_company("https://iaggroup.com/jobs/")))
        self.assertTrue(self.scraper.can_handle(make_company("https://www.iaggroup.com/jobs/")))

    def test_ats_type_is_handled_regardless_of_url(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(make_company("https://example.com/careers/", ats_type="awsm"))
        )

    def test_unrelated_host_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("https://example.com/jobs/")))


class TestParseJobs(unittest.TestCase):
    def test_parses_title_link_location_and_type(self) -> None:
        jobs = parse_jobs(PAYLOAD, "u")
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Acoustics Engineer & Designer")
        self.assertEqual(job.url, "https://iaggroup.com/jobs/acousitic-engineer/")
        self.assertEqual(job.external_id, "8984")
        self.assertEqual(job.location, "Shenzhen, China")
        self.assertEqual(job.job_type, "Full Time")
        self.assertEqual(job.description, "<p>Design loudspeakers.</p>")
        self.assertEqual(job.posted_date, date(2026, 9, 7))

    def test_non_list_payload_raises(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_jobs({"code": "rest_no_route"}, "u")

    def test_api_url(self) -> None:
        self.assertEqual(
            build_api_url("iaggroup.com", 2),
            "https://iaggroup.com/wp-json/wp/v2/awsm_job_openings?per_page=100&page=2",
        )


if __name__ == "__main__":
    unittest.main()
