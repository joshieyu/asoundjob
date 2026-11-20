from __future__ import annotations

import json
import unittest
from datetime import date
from types import SimpleNamespace
from urllib.parse import quote

from scraper.config import load_settings
from scraper.scrapers.ats.paylocity import PaylocityScraper, parse_board
from scraper.scrapers.ats.taleo import TaleoScraper, parse_detail_description, parse_search
from scraper.scrapers.base import ScrapeError

SEARCH_PAYLOAD = {
    "pagingData": {"currentPageNo": 1, "pageSize": 25, "totalCount": 2},
    "requisitionList": [
        {
            "jobId": "793697",
            "contestNo": "197715",
            "column": ["Acoustician", '["Multiple Locations"]', "Nov 3, 2026"],
            "locationsColumns": [1],
        },
        {
            "jobId": "1",
            "contestNo": "196404",
            "column": ["Noise Specialist 1", '["Denver, CO", "Omaha, NE"]', "Oct 30, 2026"],
            "locationsColumns": [1],
        },
        {"jobId": "2", "contestNo": "", "column": ["No contest number"]},
    ],
}


def _history(*parts: str) -> str:
    encoded = "!|!".join(quote(part) for part in parts)
    return f'<input type="hidden" id="initialHistory" value="{encoded}" />'


class TestTaleo(unittest.TestCase):
    def test_parse_search_builds_detail_urls(self) -> None:
        jobs = parse_search(SEARCH_PAYLOAD, "hdr.taleo.net", "ex")
        self.assertEqual([j.title for j in jobs], ["Acoustician", "Noise Specialist 1"])
        self.assertEqual(
            jobs[0].url, "https://hdr.taleo.net/careersection/ex/jobdetail.ftl?job=197715&lang=en"
        )
        self.assertEqual(jobs[0].external_id, "197715")
        self.assertEqual(jobs[0].posted_date, date(2026, 11, 3))
        self.assertEqual(jobs[1].location, "Denver, CO; Omaha, NE")

    def test_parse_search_rejects_unexpected_payload(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_search({"requisitionList": None}, "hdr.taleo.net", "ex")

    def test_detail_description_keeps_role_text_and_drops_eeo(self) -> None:
        role = "!*!<p>Perform noise monitoring and modeling for highway projects. " + "x" * 200
        eeo = "!*!<p>We are an Affirmative Action and equal opportunity employer. " + "y" * 200
        page = _history("short", role, eeo)
        description = parse_detail_description(page) or ""
        self.assertIn("noise monitoring", description)
        self.assertNotIn("Affirmative Action", description)

    def test_handles_taleo_career_section_urls(self) -> None:
        scraper = TaleoScraper(load_settings())
        company = SimpleNamespace(
            ats_type=None,
            careers_url="https://hdr.taleo.net/careersection/ex/jobsearch.ftl?keyword=acoustics",
        )
        self.assertTrue(scraper.can_handle(company))


def _board(rows: list[dict]) -> str:
    data = {"Departments": ["All Departments"], "Jobs": rows}
    return f"<script>\n window.pageData = {json.dumps(data)};\n</script>"


class TestPaylocity(unittest.TestCase):
    def test_parse_board_reads_public_jobs(self) -> None:
        page = _board(
            [
                {
                    "JobId": 4675512,
                    "JobTitle": "Sr. Acoustic Engineer",
                    "PublishedDate": "2026-11-18T11:15:11-06:00",
                    "Description": "Design communication headsets.",
                    "IsInternal": False,
                    "JobLocation": {"City": "Manchester", "State": "NH"},
                    "IsRemote": False,
                },
                {"JobId": 2, "JobTitle": "Internal Only", "IsInternal": True},
            ]
        )
        jobs = parse_board(page)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(
            jobs[0].url, "https://recruiting.paylocity.com/Recruiting/Jobs/Details/4675512"
        )
        self.assertEqual(jobs[0].location, "Manchester, NH")
        self.assertEqual(jobs[0].posted_date, date(2026, 11, 18))

    def test_parse_board_without_page_data_fails(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_board("<html></html>")

    def test_handles_paylocity_board_urls(self) -> None:
        scraper = PaylocityScraper(load_settings())
        company = SimpleNamespace(
            ats_type=None,
            careers_url=(
                "https://recruiting.paylocity.com/Recruiting/Jobs/All/"
                "302a0fa8-9c10-4c4f-bc49-27fd3045595d/Gentex-Corp"
            ),
        )
        self.assertTrue(scraper.can_handle(company))
