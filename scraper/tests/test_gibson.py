from __future__ import annotations

import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from scraper.scrapers.ats.gibson import GibsonScraper
from scraper.scrapers.base import ScrapeError

CAREERS_URL = "https://www.gibson.com/apps/adpJobRequisition/"


def make_company(url: str = CAREERS_URL, ats_type=None):
    from scraper.models import Company

    return Company(
        id=1,
        name="Gibson",
        slug="gibson",
        category="Audio Hardware",
        careers_url=url,
        ats_type=ats_type,
    )


def make_requisition(**overrides):
    requisition = {
        "itemID": "9200768350708_1",
        "postingInstructions": [
            {
                "nameCode": {
                    "codeValue": "Repair Technician - Gibson Certified Vintage",
                    "longName": "<div><p>The Gibson Certified Vintage Repair "
                    "Technician supports repairs.</p></div>",
                },
                "postDate": "2026-08-21",
                "expireDate": "2026-12-31",
            }
        ],
        "links": [
            {
                "href": "https://workforcenow.adp.com/mascsr/default/mdf/"
                "recruitment/recruitment.html?client=sinbl&ccId=19000101_000002"
                "&cid=a63e7571-1234&type=MP&lang=en_US"
            },
            {
                "href": "https://workforcenow.adp.com/mascsr/default/mdf/"
                "recruitment/recruitment.html?client=sinbl&ccId=19000101_000001"
                "&cid=a63e7571-1234&jobId=605900&lang=en_US&source=CC2"
            },
        ],
        "requisitionStatusCode": {"codeValue": "ON"},
        "requisitionLocations": [
            {
                "address": {
                    "cityName": "Nashville",
                    "countrySubdivisionLevel1": {"codeValue": "TN"},
                    "countryCode": "US",
                }
            }
        ],
        "job": {"jobTitle": "Repair Technician"},
    }
    requisition.update(overrides)
    return requisition


def make_response(requisitions):
    return {"success": True, "data": {"jobRequisitions": requisitions}}


class TestCanHandle(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = GibsonScraper(load_settings())

    def test_endpoint_url_is_handled(self) -> None:
        self.assertTrue(self.scraper.can_handle(make_company(CAREERS_URL)))

    def test_endpoint_url_without_trailing_slash_is_handled(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(
                make_company("https://www.gibson.com/apps/adpJobRequisition")
            )
        )

    def test_endpoint_url_with_query_string_is_handled(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(
                make_company(
                    "https://www.gibson.com/apps/adpJobRequisition/?foo=bar"
                )
            )
        )

    def test_ats_type_gibson_is_handled_regardless_of_url(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(
                make_company("https://jobs.lever.co/acme", ats_type="gibson")
            )
        )

    def test_unrelated_url_with_no_ats_type_is_rejected(self) -> None:
        self.assertFalse(
            self.scraper.can_handle(
                make_company("https://www.gibson.com/pages/open-positions")
            )
        )


class TestFetchJobs(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = GibsonScraper(load_settings())
        self.company = make_company()

    def _run(self, response):
        with patch(
            "scraper.scrapers.ats.gibson.post_json", return_value=response
        ):
            return asyncio.run(self.scraper.fetch_jobs(self.company))

    def test_parses_two_requisitions(self) -> None:
        requisitions = [
            make_requisition(itemID="1"),
            make_requisition(
                itemID="2",
                postingInstructions=[
                    {
                        "nameCode": {
                            "codeValue": "Guitar Technician",
                            "longName": "<p>Build and repair guitars.</p>",
                        },
                        "postDate": "2026-07-01",
                    }
                ],
            ),
        ]
        jobs = self._run(make_response(requisitions))

        self.assertEqual(len(jobs), 2)
        first = next(job for job in jobs if job.external_id == "1")
        self.assertEqual(
            first.title, "Repair Technician - Gibson Certified Vintage"
        )
        self.assertEqual(first.location, "Nashville, TN, US")
        self.assertIn("Repair Technician supports repairs", first.description)
        self.assertEqual(first.posted_date, date(2026, 8, 21))
        self.assertEqual(
            first.url,
            "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/"
            "recruitment.html?client=sinbl&ccId=19000101_000001&cid=a63e7571-1234"
            "&jobId=605900&lang=en_US&source=CC2",
        )

        second = next(job for job in jobs if job.external_id == "2")
        self.assertEqual(second.title, "Guitar Technician")

    def test_excludes_requisition_with_off_status(self) -> None:
        requisitions = [
            make_requisition(
                itemID="1", requisitionStatusCode={"codeValue": "OFF"}
            )
        ]
        jobs = self._run(make_response(requisitions))
        self.assertEqual(jobs, [])

    def test_excludes_requisition_with_no_status(self) -> None:
        requisitions = [make_requisition(itemID="1", requisitionStatusCode={})]
        jobs = self._run(make_response(requisitions))
        self.assertEqual(jobs, [])

    def test_excludes_requisition_missing_status_field(self) -> None:
        requisition = make_requisition(itemID="1")
        del requisition["requisitionStatusCode"]
        jobs = self._run(make_response([requisition]))
        self.assertEqual(jobs, [])

    def test_skips_requisition_with_blank_title(self) -> None:
        requisitions = [
            make_requisition(
                itemID="1",
                postingInstructions=[
                    {
                        "nameCode": {"codeValue": "  ", "longName": "<p>x</p>"},
                        "postDate": "2026-08-21",
                    }
                ],
            ),
            make_requisition(itemID="2"),
        ]
        jobs = self._run(make_response(requisitions))
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].external_id, "2")

    def test_no_locations_yields_none_location(self) -> None:
        requisition = make_requisition(itemID="1")
        del requisition["requisitionLocations"]
        jobs = self._run(make_response([requisition]))
        self.assertEqual(len(jobs), 1)
        self.assertIsNone(jobs[0].location)

    def test_non_dict_response_raises_scrape_error(self) -> None:
        with self.assertRaises(ScrapeError):
            self._run(["not", "a", "dict"])

    def test_success_false_raises_scrape_error(self) -> None:
        with self.assertRaises(ScrapeError):
            self._run({"success": False, "data": {"jobRequisitions": []}})

    def test_missing_job_requisitions_list_raises_scrape_error(self) -> None:
        with self.assertRaises(ScrapeError):
            self._run({"success": True, "data": {}})


if __name__ == "__main__":
    unittest.main()
