from __future__ import annotations

import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from scraper.scrapers.ats.amazon import (
    MAX_PAGES,
    PAGE_SIZE,
    AmazonScraper,
    extract_base_query,
    parse_jobs,
)

CAREERS_URL = "https://www.amazon.jobs/en/search?base_query=audio"


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Amazon",
        slug="amazon",
        category="Audio Hardware",
        careers_url=url,
    )


def make_job(**overrides):
    item = {
        "title": "Audio/Sensor Lab Engineer, Audio and Data Technology",
        "job_path": "/en/jobs/10517516/audio-sensor-lab-engineer-audio-and-data-technology",
        "id_icims": 10517516,
        "normalized_location": "Sunnyvale, California, USA",
        "description": "Build the audio pipeline.",
        "basic_qualifications": "5+ years of audio DSP experience.",
        "preferred_qualifications": "Experience with acoustic transducers.",
        "job_schedule_type": "full-time",
        "posted_date": "August 27, 2026",
    }
    item.update(overrides)
    return item


def make_response(jobs, hits):
    return {"error": None, "hits": hits, "jobs": jobs}


class TestCanHandle(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = AmazonScraper(load_settings())

    def test_amazon_url_is_handled(self) -> None:
        self.assertTrue(self.scraper.can_handle(make_company(CAREERS_URL)))

    def test_bare_locale_less_url_is_handled(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(make_company("https://www.amazon.jobs/search?base_query=audio"))
        )

    def test_unrelated_url_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("https://jobs.lever.co/acme")))

    def test_no_careers_url_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("")))


class TestExtractBaseQuery(unittest.TestCase):
    def test_extracts_base_query(self) -> None:
        self.assertEqual(extract_base_query(CAREERS_URL), "audio")

    def test_missing_base_query_falls_back_to_empty_string(self) -> None:
        self.assertEqual(extract_base_query("https://www.amazon.jobs/en/search"), "")


class TestParseJobs(unittest.TestCase):
    def test_parses_fields(self) -> None:
        jobs = parse_jobs([make_job()])
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(
            job.url,
            "https://www.amazon.jobs/en/jobs/10517516/"
            "audio-sensor-lab-engineer-audio-and-data-technology",
        )
        self.assertEqual(job.external_id, "10517516")
        self.assertEqual(job.location, "Sunnyvale, California, USA")
        self.assertEqual(job.job_type, "full-time")
        self.assertIn("Build the audio pipeline.", job.description)
        self.assertIn("5+ years of audio DSP experience.", job.description)
        self.assertIn("Experience with acoustic transducers.", job.description)

    def test_job_type_underscores_become_hyphens(self) -> None:
        jobs = parse_jobs([make_job(job_schedule_type="part_time")])
        self.assertEqual(jobs[0].job_type, "part-time")

    def test_posted_date_parses(self) -> None:
        jobs = parse_jobs([make_job()])
        self.assertEqual(jobs[0].posted_date, date(2026, 8, 27))

    def test_unparseable_posted_date_is_none(self) -> None:
        jobs = parse_jobs([make_job(posted_date="not a date")])
        self.assertIsNone(jobs[0].posted_date)

    def test_skips_item_with_no_title_or_job_path(self) -> None:
        jobs = parse_jobs([make_job(title=""), make_job(job_path=None)])
        self.assertEqual(jobs, [])

    def test_rejects_non_list_payload(self) -> None:
        with self.assertRaises(ValueError):
            parse_jobs({"jobs": "nope"})


class TestFetchJobs(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = AmazonScraper(load_settings())
        self.company = make_company(CAREERS_URL)

    def test_single_page(self) -> None:
        response = make_response([make_job()], 1)

        def fake_fetch_json(url, settings):
            return response

        with patch("scraper.scrapers.ats.amazon.fetch_json", side_effect=fake_fetch_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 1)

    def test_short_page_stops_pagination(self) -> None:
        calls = []

        def fake_fetch_json(url, settings):
            calls.append(url)
            items = [
                make_job(id_icims=i, job_path=f"/en/jobs/{i}/audio-job")
                for i in range(5)
            ]
            return make_response(items, 351)

        with patch("scraper.scrapers.ats.amazon.fetch_json", side_effect=fake_fetch_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 5)
        self.assertEqual(len(calls), 1)

    def test_max_pages_caps_a_board_that_always_returns_a_full_page(self) -> None:
        call_count = 0

        def fake_fetch_json(url, settings):
            nonlocal call_count
            call_count += 1
            items = [
                make_job(
                    id_icims=call_count * PAGE_SIZE + i,
                    job_path=f"/en/jobs/{call_count}-{i}/audio-job",
                )
                for i in range(PAGE_SIZE)
            ]
            return make_response(items, 100_000)

        with patch("scraper.scrapers.ats.amazon.fetch_json", side_effect=fake_fetch_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(call_count, MAX_PAGES)
        self.assertEqual(len(jobs), MAX_PAGES * PAGE_SIZE)

    def test_hits_zero_on_a_later_page_does_not_end_the_loop_early(self) -> None:
        call_count = 0

        def fake_fetch_json(url, settings):
            nonlocal call_count
            call_count += 1
            items = [
                make_job(
                    id_icims=call_count * PAGE_SIZE + i,
                    job_path=f"/en/jobs/{call_count}-{i}/audio-job",
                )
                for i in range(PAGE_SIZE)
            ]
            hits = 351 if call_count == 1 else 0
            return make_response(items, hits)

        with patch("scraper.scrapers.ats.amazon.fetch_json", side_effect=fake_fetch_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(call_count, 4)
        self.assertEqual(len(jobs), 4 * PAGE_SIZE)


if __name__ == "__main__":
    unittest.main()
