from __future__ import annotations

import unittest
from datetime import date

from scraper.scrapers.ats.jobsyn import (
    JobsynScraper,
    build_api_url,
    extract_queries,
    group_jobs,
    parse_page,
)
from scraper.scrapers.base import ScrapeError


def make_company(url: str, ats_type=None):
    from scraper.models import Company

    return Company(
        id=1,
        name="Stantec",
        slug="stantec",
        category="Acoustic Consulting & Engineering",
        careers_url=url,
        ats_type=ats_type,
    )


def attrs(**values: str) -> dict:
    return {name: {"stringValues": [value]} for name, value in values.items()}


def item(guid: str, title: str, reqid: str, city: str, city_slug: str, title_slug: str) -> dict:
    return {
        "requisitionId": guid,
        "title": title,
        "description": "<p>Measure rooms.</p>",
        "postingPublishTime": "2026-11-16T18:07:12.458Z",
        "addresses": [f"{city}, USA"],
        "customAttributes": attrs(
            reqid=reqid,
            city_display=city,
            city_display_slug=city_slug,
            title_slug=title_slug,
        ),
    }


INTERN = item(
    "7883E0DACFC0413F8EADD30F6398ED5C",
    "Acoustics Intern (Summer 2027)",
    "1008256",
    "Chicago, IL",
    "chicago-il",
    "acoustics-intern-summer-2027",
)
SENIOR_TAMPA = item(
    "AAA", "Senior Acoustical Consultant", "1008460", "Tampa, FL", "tampa-fl", "senior"
)
SENIOR_HOUSTON = item(
    "BBB", "Senior Acoustical Consultant", "1008460", "Houston, TX", "houston-tx", "senior"
)


class TestCanHandle(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = JobsynScraper(load_settings())

    def test_known_host_is_handled(self) -> None:
        self.assertTrue(self.scraper.can_handle(make_company("https://stantec.jobs/jobs/?q=acoustic")))

    def test_ats_type_is_handled_regardless_of_url(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(make_company("https://example.jobs/", ats_type="jobsyn"))
        )

    def test_unrelated_host_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("https://example.com/jobs/")))


class TestQueries(unittest.TestCase):
    def test_repeated_q_values_are_all_searched_once(self) -> None:
        url = "https://stantec.jobs/jobs/?q=acoustic&q=acoustical&q=acoustic&q=+"
        self.assertEqual(extract_queries(url), ["acoustic", "acoustical"])

    def test_no_query_searches_everything(self) -> None:
        self.assertEqual(extract_queries("https://stantec.jobs/jobs/"), [""])
        self.assertNotIn("q=", build_api_url("", 1))
        self.assertIn("q=audio+visual", build_api_url("audio visual", 2))


class TestParsing(unittest.TestCase):
    def test_page_reads_jobs_and_more_pages_flag(self) -> None:
        payload = {
            "jobs": [{"job": INTERN}, {"other": 1}],
            "pagination": {"has_more_pages": True},
        }
        items, has_more = parse_page(payload, "u")
        self.assertEqual(items, [INTERN])
        self.assertTrue(has_more)
        self.assertEqual(parse_page({"jobs": []}, "u"), ([], False))

    def test_reads_flat_search_documents(self) -> None:
        doc = {
            "guid": "9F59FE26557B484784E26E997B9B122F",
            "title_exact": "Staff Noise Control Engineer - Environmental Services",
            "reqid": "262912",
            "location_exact": "Kansas City, MO",
            "description": "**Description** Model noise from power plants.",
            "date_new": "2026-11-04T13:33:19Z",
        }
        other_site = {
            **doc, "guid": "A60F3CA08BC9470DBAFF4ECCD836D069", "location_exact": "Brea, CA"
        }
        items, has_more = parse_page({"jobs": [doc, other_site], "pagination": {}}, "u")
        self.assertFalse(has_more)
        (job,) = group_jobs(items, "burnsmcd.jobs")
        self.assertEqual(job.title, "Staff Noise Control Engineer - Environmental Services")
        self.assertEqual(job.external_id, "262912")
        self.assertEqual(job.url, "https://burnsmcd.jobs/9F59FE26557B484784E26E997B9B122F/job/")
        self.assertEqual(job.location, "Kansas City, MO; Brea, CA")
        self.assertIn("power plants", job.description or "")
        self.assertIsNotNone(job.posted_date)

    def test_bad_payload_raises(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_page({"errors": {"origin": "The origin is required."}}, "u")

    def test_one_job_per_requisition_with_all_locations(self) -> None:
        jobs = group_jobs([INTERN, SENIOR_TAMPA, SENIOR_HOUSTON, SENIOR_TAMPA], "stantec.jobs")
        self.assertEqual([j.external_id for j in jobs], ["1008256", "1008460"])
        intern, senior = jobs
        self.assertEqual(
            intern.url,
            "https://stantec.jobs/chicago-il/acoustics-intern-summer-2027/"
            "7883E0DACFC0413F8EADD30F6398ED5C/job/",
        )
        self.assertEqual(intern.location, "Chicago, IL")
        self.assertEqual(intern.posted_date, date(2026, 11, 16))
        self.assertEqual(senior.location, "Tampa, FL; Houston, TX")

    def test_jobs_without_title_or_id_are_skipped(self) -> None:
        self.assertEqual(group_jobs([{"title": "x"}, {"requisitionId": "y"}], "stantec.jobs"), [])


if __name__ == "__main__":
    unittest.main()
