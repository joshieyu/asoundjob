from __future__ import annotations

import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from scraper.scrapers.ats.adp import (
    AdpScraper,
    extract_description,
    format_location,
    parse_requisition,
    requisitions,
)

CID = "12345678-90ab-cdef-1234-567890abcdef"
CAREERS_URL = (
    "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html"
    f"?cid={CID}&ccId=19000101_000001&lang=en_US"
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
    "requisitionTitle": "Software Engineer, Mechanical Modeling & Simu",
    "itemID": "9205207915066_1",
    "postDate": "2026-08-01T00:00:00.000Z",
    "requisitionLocations": [{"address": {"cityName": "Boston"}}],
}

LIST_ITEM_NO_CITY = {
    "requisitionTitle": "Acoustic Test Technician",
    "itemID": "9205207915067_1",
    "postDate": "2026-08-02T00:00:00.000Z",
    "requisitionLocations": [{"address": {"cityName": ""}}],
}

LIST_PAYLOAD = {"jobRequisitions": [LIST_ITEM, LIST_ITEM_NO_CITY]}

DETAIL_PAYLOAD = {
    "requisitionTitle": "Software Engineer, Mechanical Modeling & Simu",
    "itemID": "9205207915066_1",
    "requisitionDescription": (
        "<p>Design <strong>mechanical</strong> models.</p><ul><li>C++</li></ul>"
    ),
}


class TestAdpParser(unittest.TestCase):
    def test_parse_requisition(self) -> None:
        job = parse_requisition(LIST_ITEM, CID)
        assert job is not None
        self.assertEqual(job.title, "Software Engineer, Mechanical Modeling & Simu")
        self.assertEqual(job.external_id, "9205207915066_1")
        self.assertEqual(
            job.url,
            "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html"
            f"?cid={CID}&ccId=19000101_000001&type=MP&lang=en_US&jobId=9205207915066_1",
        )
        self.assertEqual(job.location, "Boston")
        self.assertEqual(job.posted_date, date(2026, 8, 1))

    def test_parse_requisition_missing_title_or_id(self) -> None:
        self.assertIsNone(parse_requisition({"itemID": "1"}, CID))
        self.assertIsNone(parse_requisition({"requisitionTitle": "Engineer"}, CID))

    def test_format_location_empty_city_name_is_none(self) -> None:
        self.assertIsNone(format_location([{"address": {"cityName": ""}}]))
        self.assertIsNone(format_location([]))
        self.assertIsNone(format_location(None))
        self.assertIsNone(format_location([{"address": {}}]))

    def test_format_location_present(self) -> None:
        self.assertEqual(format_location([{"address": {"cityName": "Boston"}}]), "Boston")

    def test_requisitions(self) -> None:
        self.assertEqual(requisitions(LIST_PAYLOAD), [LIST_ITEM, LIST_ITEM_NO_CITY])

    def test_requisitions_rejects_non_dict(self) -> None:
        with self.assertRaises(ValueError):
            requisitions([])

    def test_requisitions_rejects_bad_field(self) -> None:
        with self.assertRaises(ValueError):
            requisitions({"jobRequisitions": "not a list"})

    def test_extract_description_converts_html_to_text(self) -> None:
        text = extract_description(DETAIL_PAYLOAD)
        self.assertEqual(text, "Design mechanical models. C++")

    def test_extract_description_missing(self) -> None:
        self.assertIsNone(extract_description({}))
        self.assertIsNone(extract_description(None))

    def test_extract_slug_from_query(self) -> None:
        self.assertEqual(AdpScraper.extract_slug(CAREERS_URL), CID)

    def test_extract_slug_non_matching(self) -> None:
        self.assertIsNone(AdpScraper.extract_slug("https://example.com/careers"))
        self.assertIsNone(
            AdpScraper.extract_slug("https://workforcenow.adp.com/mascsr/default")
        )
        self.assertIsNone(
            AdpScraper.extract_slug("https://workforcenow.adp.com/mascsr?cid=not-a-guid")
        )

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = AdpScraper(load_settings())
        self.assertTrue(scraper.can_handle(make_company(CAREERS_URL)))
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(
            scraper.can_handle(
                make_company("https://myjobs.adp.com/some-other-shape?cid=" + CID)
            )
        )
        self.assertFalse(scraper.can_handle(make_company("")))


class TestAdpFetchJobs(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = AdpScraper(load_settings())
        self.company = make_company(CAREERS_URL)

    def test_fetch_jobs_lists_and_enriches(self) -> None:
        def fake_fetch_json(url: str, settings: object):
            if "job-requisitions/9205207915066_1" in url:
                return DETAIL_PAYLOAD
            if "$skip=0" in url:
                return LIST_PAYLOAD
            return {"jobRequisitions": []}

        with patch("scraper.scrapers.ats.adp.fetch_json", side_effect=fake_fetch_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 2)
        enriched = next(j for j in jobs if j.external_id == "9205207915066_1")
        self.assertEqual(enriched.description, "Design mechanical models. C++")
        unenriched = next(j for j in jobs if j.external_id == "9205207915067_1")
        self.assertIsNone(unenriched.location)

    def test_fetch_jobs_survives_detail_fetch_exception(self) -> None:
        def fake_fetch_json(url: str, settings: object):
            if "job-requisitions/9205207915066_1" in url:
                raise ConnectionError("boom")
            if "$skip=0" in url:
                return {"jobRequisitions": [LIST_ITEM]}
            return {"jobRequisitions": []}

        with patch("scraper.scrapers.ats.adp.fetch_json", side_effect=fake_fetch_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 1)
        self.assertIsNone(jobs[0].description)


if __name__ == "__main__":
    unittest.main()
