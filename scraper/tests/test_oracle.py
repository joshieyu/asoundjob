from __future__ import annotations

import asyncio
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from scraper.config import load_settings
from scraper.scrapers.ats.oracle import (
    OracleScraper,
    parse_detail_description,
    parse_requisitions,
)
from scraper.scrapers.base import ScrapeError

HOST = "elhe.fa.us8.oraclecloud.com"
CAREERS_URL = (
    f"https://{HOST}/hcmUI/CandidateExperience/en/sites/CX_1002/jobs?keyword=acoustic"
)


def search_payload(rows: list[dict], total: int) -> dict:
    return {"items": [{"TotalJobsCount": total, "requisitionList": rows}]}


ROW = {
    "Id": "2319",
    "Title": "Vibroacoustic Monitoring Intern - Summer 2027",
    "PrimaryLocation": "Idaho Falls, ID, United States",
    "PostedDate": "2026-11-11",
    "ShortDescriptionStr": "Help advance vibroacoustic monitoring.",
}

DETAIL = {
    "items": [
        {
            "ExternalDescriptionStr": "<p>Reporting to the Acoustic and Seismic Team.</p>",
            "ExternalQualificationsStr": "<p>Studying mechanical engineering.</p>",
        }
    ]
}


class TestParseRequisitions(unittest.TestCase):
    def test_builds_job_urls_on_the_same_site(self) -> None:
        jobs, total = parse_requisitions(search_payload([ROW], 1), HOST, "en", "CX_1002")
        self.assertEqual(total, 1)
        self.assertEqual(
            jobs[0].url, f"https://{HOST}/hcmUI/CandidateExperience/en/sites/CX_1002/job/2319"
        )
        self.assertEqual(jobs[0].external_id, "2319")
        self.assertEqual(jobs[0].location, "Idaho Falls, ID, United States")
        self.assertEqual(jobs[0].posted_date, date(2026, 11, 11))

    def test_empty_search_has_no_jobs(self) -> None:
        self.assertEqual(parse_requisitions({"items": []}, HOST, "en", "CX_1"), ([], 0))

    def test_unexpected_payload_raises(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_requisitions({"error": "x"}, HOST, "en", "CX_1")

    def test_detail_joins_description_sections(self) -> None:
        text = parse_detail_description(DETAIL) or ""
        self.assertIn("Seismic Team", text)
        self.assertIn("mechanical engineering", text)


class TestOracleScraper(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = OracleScraper(load_settings())

    def test_handles_candidate_experience_urls(self) -> None:
        company = SimpleNamespace(ats_type=None, careers_url=CAREERS_URL)
        self.assertTrue(self.scraper.can_handle(company))
        other = SimpleNamespace(ats_type=None, careers_url="https://example.com/careers")
        self.assertFalse(self.scraper.can_handle(other))

    def test_keyword_is_sent_and_detail_fills_description(self) -> None:
        urls: list[str] = []

        def fake_fetch(url: str, settings: object) -> dict:
            urls.append(url)
            if "recruitingCEJobRequisitionDetails" in url:
                return DETAIL
            return search_payload([ROW], 1)

        company = SimpleNamespace(ats_type=None, careers_url=CAREERS_URL, priority=False)
        with patch("scraper.scrapers.ats.oracle.fetch_json", side_effect=fake_fetch):
            jobs = asyncio.run(self.scraper.fetch_jobs(company))
        self.assertIn('keyword="acoustic"', urls[0])
        self.assertIn("siteNumber=CX_1002", urls[0])
        self.assertEqual(len(jobs), 1)
        self.assertIn("Seismic Team", jobs[0].description or "")

    def test_custom_domain_needs_the_oracle_ats_type(self) -> None:
        url = "https://careersearch.stanford.edu/hcmUI/CandidateExperience/en/sites/stanford/jobs?keyword=audio"
        urls: list[str] = []

        def fake_fetch(address: str, settings: object) -> dict:
            urls.append(address)
            if "recruitingCEJobRequisitionDetails" in address:
                return DETAIL
            return search_payload([ROW], 1)

        unbound = SimpleNamespace(ats_type=None, careers_url=url, priority=False)
        self.assertFalse(self.scraper.can_handle(unbound))
        with self.assertRaises(ScrapeError):
            asyncio.run(self.scraper.fetch_jobs(unbound))
        bound = SimpleNamespace(ats_type="oracle", careers_url=url, priority=False)
        with patch("scraper.scrapers.ats.oracle.fetch_json", side_effect=fake_fetch):
            jobs = asyncio.run(self.scraper.fetch_jobs(bound))
        self.assertTrue(urls[0].startswith("https://careersearch.stanford.edu/hcmRestApi/"))
        self.assertIn("siteNumber=stanford", urls[0])
        self.assertEqual(
            jobs[0].url,
            "https://careersearch.stanford.edu/hcmUI/CandidateExperience/en/sites/stanford/job/2319",
        )


if __name__ == "__main__":
    unittest.main()
