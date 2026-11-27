from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scraper.config import load_settings
from scraper.scrapers.ats import alignerr, jtable, rippling
from scraper.scrapers.base import RawJob, ScrapeError

LANL_RECORD = {
    "ID": "a4d6d2bd-fa21-4f59-afb7-48e1e5ab326c",
    "Title": "<span>Shock and Vibration Test Engineer</span>",
    "LocationName": "<span>Los Alamos, NM</span>",
    "PostedDateRaw": "2026-10-19T00:00:00",
    "TrackingObject": {
        "TitleJson": "Shock and Vibration Test Engineer (R&amp;D Engineer 2/3)",
        "LocationNamesJson": ["Los Alamos, NM", "Los Alamos, NM"],
    },
}


def company(url: str, ats_type: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        careers_url=url, ats_type=ats_type, ats_slug=None, priority=False, name="Acme"
    )


class TestJTable(unittest.TestCase):
    def test_reads_a_record(self) -> None:
        job = jtable.to_job(LANL_RECORD, "https://lanl.jobs")
        assert job is not None
        self.assertEqual(job.title, "Shock and Vibration Test Engineer (R&D Engineer 2/3)")
        self.assertEqual(
            job.url, "https://lanl.jobs/search/jobdetails/job/a4d6d2bd-fa21-4f59-afb7-48e1e5ab326c"
        )
        self.assertEqual(job.location, "Los Alamos, NM")
        self.assertIsNotNone(job.posted_date)

    def test_rejects_records_without_an_id(self) -> None:
        self.assertIsNone(jtable.to_job({**LANL_RECORD, "ID": "x"}, "https://lanl.jobs"))

    def test_a_failed_search_raises(self) -> None:
        with self.assertRaises(ScrapeError):
            jtable.parse_page({"Result": "ERROR", "Message": "nope"}, "u")

    def test_only_claims_boards_marked_jtable(self) -> None:
        scraper = jtable.JTableScraper(load_settings())
        url = "https://lanl.jobs/search/searchjobs"
        self.assertTrue(scraper.can_handle(company(url, "jtable")))
        self.assertFalse(scraper.can_handle(company(url)))

    def test_each_keyword_is_capped_and_paged(self) -> None:
        seen: list[str] = []

        def fake_json(url: str, settings: object) -> dict:
            seen.append(url)
            records = [
                {**LANL_RECORD, "ID": f"{len(seen):04d}{i:04d}-0000-0000-0000-000000000000"}
                for i in range(jtable.PAGE_SIZE)
            ]
            return {"Result": "OK", "Records": records, "TotalRecordCount": 500}

        scraper = jtable.JTableScraper(load_settings())
        board = company("https://lanl.jobs/search/searchjobs?keyword=acoustic", "jtable")
        with patch.object(jtable, "fetch_json", fake_json), patch.object(
            jtable, "fetch_html", side_effect=ConnectionError("offline")
        ):
            jobs = asyncio.run(scraper.fetch_jobs(board))
        self.assertEqual(len(jobs), jtable.MAX_RESULTS_PER_KEYWORD)
        self.assertEqual(len(seen), 1)
        self.assertIn("keyword=acoustic", seen[0])


class TestRippling(unittest.TestCase):
    def test_board_slug(self) -> None:
        board = "https://ats.rippling.com/turtlebox/jobs"
        self.assertEqual(rippling.board_slug(board), "turtlebox")
        self.assertEqual(rippling.board_slug("https://ats.rippling.com/en-GB/acme/jobs"), "acme")
        self.assertIsNone(rippling.board_slug("https://ats.rippling.com.evil.net/acme/jobs"))

    def test_reads_the_board_and_a_detail(self) -> None:
        payload = [
            {
                "uuid": "86731136-99aa-4659-84a9-4347fc2484da",
                "name": "Validation Engineer",
                "url": "https://ats.rippling.com/turtlebox/jobs/86731136-99aa-4659-84a9-4347fc2484da",
                "workLocation": {"label": "Houston, TX"},
            },
            {"uuid": "bad", "name": "Broken", "url": "x"},
        ]
        (job,) = rippling.parse_board(payload, "u")
        self.assertEqual(job.location, "Houston, TX")
        rippling.apply_detail(
            job,
            {
                "description": {
                    "company": "<p>About us</p>", "role": "<p>Run audio analyzers.</p>"
                },
                "workLocations": ["Houston, TX", "Austin, TX"],
                "createdOn": "2026-09-23T14:28:30.105000-07:00",
            },
        )
        self.assertEqual(job.description, "<p>Run audio analyzers.</p>")
        self.assertEqual(job.location, "Houston, TX; Austin, TX")
        self.assertIsNotNone(job.posted_date)

    def test_a_non_list_board_raises(self) -> None:
        with self.assertRaises(ScrapeError):
            rippling.parse_board({"error": "nope"}, "u")


class TestAlignerr(unittest.TestCase):
    def test_copies_of_one_posting_collapse_to_the_lowest_id(self) -> None:
        rows = [
            {"id": "c0a93837-be64-4e8d-a17e-aa50f5882608", "title": "Audio Engineer - Pro Tools",
             "location": "Remote", "description": "Teaser"},
            {"id": "6ab630ff-0000-0000-0000-000000000000", "title": "Audio Engineer -  Pro Tools",
             "location": "Remote"},
            {"id": "e29c3889-0000-0000-0000-000000000000", "title": "Audio Quality Reviewer",
             "location": "Remote"},
            {"id": "nope", "title": "Broken"},
        ]
        jobs = {job.title: job for job in alignerr.collapse(rows)}
        self.assertEqual(set(jobs), {"Audio Engineer - Pro Tools", "Audio Quality Reviewer"})
        pro_tools = jobs["Audio Engineer - Pro Tools"]
        self.assertEqual(pro_tools.external_id, "6ab630ff-0000-0000-0000-000000000000")
        self.assertEqual(pro_tools.url, "https://www.alignerr.com/jobs/6ab630ff-0000-0000-0000-000000000000")
        self.assertTrue(pro_tools.remote_hint)
        self.assertEqual(pro_tools.job_type, "contract")

    def test_detail_page_supplies_the_full_description(self) -> None:
        job = RawJob(title="Audio Engineer - Pro Tools", url="https://www.alignerr.com/jobs/x")
        page = (
            '<script id="__NEXT_DATA__" type="application/json">'
            '{"props": {"pageProps": {"job": {"htmlLongDescription": "<b>Mix in Pro Tools</b>",'
            ' "firstPostDate": "2026-11-27T00:00:02.777Z"}}}}</script>'
        )
        alignerr.apply_detail(job, page)
        self.assertEqual(job.description, "<b>Mix in Pro Tools</b>")
        self.assertIsNotNone(job.posted_date)

    def test_needs_a_search_term(self) -> None:
        scraper = alignerr.AlignerrScraper(load_settings())
        self.assertTrue(scraper.can_handle(company("https://www.alignerr.com/jobs?search=audio")))
        with self.assertRaises(ScrapeError):
            asyncio.run(scraper.fetch_jobs(company("https://www.alignerr.com/jobs")))


if __name__ == "__main__":
    unittest.main()
