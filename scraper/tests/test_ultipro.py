from __future__ import annotations

import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from scraper.scrapers.ats.ultipro import (
    MAX_PAGES,
    PAGE_SIZE,
    UltiproScraper,
    format_location,
    parse_opportunities,
)
from scraper.scrapers.base import ScrapeError

HOST = "recruiting2.ultipro.com"
TENANT = "STA1003STARK"
BOARD = "a1b2c3d4-e5f6-4789-9abc-def012345678"
CAREERS_URL = f"https://{HOST}/{TENANT}/JobBoard/{BOARD}/?q=&o=postedDateDesc"


def make_company(url: str, ats_type: str | None = None, ats_slug: str | None = None):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Hardware",
        careers_url=url,
        ats_type=ats_type,
        ats_slug=ats_slug,
    )


def make_opportunity(**overrides):
    item = {
        "Id": "11111111-1111-1111-1111-111111111111",
        "Title": "Senior Audio Engineer",
        "RequisitionNumber": "REQ-100",
        "FullTime": True,
        "JobCategoryName": "Engineering",
        "Locations": [
            {
                "Id": "loc-1",
                "LocalizedDescription": "NY020 - Yorktown Heights",
                "Address": {
                    "Line1": "123 Main St",
                    "City": "Yorktown Heights",
                    "PostalCode": "10598",
                    "State": {"Code": "NY", "Name": "New York"},
                    "Country": {"Code": "USA", "Name": "United States"},
                },
            }
        ],
        "PostedDate": "2026-08-15T00:00:00Z",
        "BriefDescription": "Design audio DSP pipelines.",
    }
    item.update(overrides)
    return item


def make_response(opportunities, total_count):
    return {
        "opportunities": opportunities,
        "totalCount": total_count,
        "locations": [],
    }


class TestCanHandle(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = UltiproScraper(load_settings())

    def test_ultipro_url_is_handled(self) -> None:
        self.assertTrue(self.scraper.can_handle(make_company(CAREERS_URL)))

    def test_ats_type_with_unrelated_url_is_handled(self) -> None:
        company = make_company("https://example.com/careers", ats_type="ultipro")
        self.assertTrue(self.scraper.can_handle(company))

    def test_unrelated_url_without_ats_type_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("https://jobs.lever.co/acme")))

    def test_no_careers_url_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("")))


class TestExtractSlug(unittest.TestCase):
    def test_extracts_tenant_and_board(self) -> None:
        self.assertEqual(
            UltiproScraper.extract_slug(CAREERS_URL), f"{TENANT}/{BOARD}"
        )

    def test_allows_host_without_digit(self) -> None:
        url = f"https://recruiting.ultipro.com/{TENANT}/JobBoard/{BOARD}/"
        self.assertEqual(UltiproScraper.extract_slug(url), f"{TENANT}/{BOARD}")

    def test_non_matching_url_returns_none(self) -> None:
        self.assertIsNone(UltiproScraper.extract_slug("https://example.com/careers"))
        self.assertIsNone(
            UltiproScraper.extract_slug(f"https://recruiting2.ultipro.com/{TENANT}/JobBoard/not-a-uuid/")
        )


class TestParseOpportunities(unittest.TestCase):
    def test_parses_fields(self) -> None:
        payload = make_response([make_opportunity()], 1)
        jobs = parse_opportunities(payload, HOST, TENANT, BOARD)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Senior Audio Engineer")
        self.assertEqual(
            job.url,
            f"https://{HOST}/{TENANT}/JobBoard/{BOARD}/OpportunityDetail"
            "?opportunityId=11111111-1111-1111-1111-111111111111",
        )
        self.assertEqual(job.external_id, "11111111-1111-1111-1111-111111111111")
        self.assertEqual(job.description, "Design audio DSP pipelines.")
        self.assertEqual(job.job_type, "full-time")
        self.assertEqual(job.posted_date, date(2026, 8, 15))
        self.assertEqual(job.location, "Yorktown Heights, NY, USA")

    def test_part_time_job_has_no_job_type(self) -> None:
        payload = make_response([make_opportunity(FullTime=False)], 1)
        jobs = parse_opportunities(payload, HOST, TENANT, BOARD)
        self.assertIsNone(jobs[0].job_type)

    def test_missing_brief_description_is_none(self) -> None:
        item = make_opportunity()
        del item["BriefDescription"]
        payload = make_response([item], 1)
        jobs = parse_opportunities(payload, HOST, TENANT, BOARD)
        self.assertIsNone(jobs[0].description)

    def test_multi_location_join_uses_segment_separator(self) -> None:
        item = make_opportunity(
            Locations=[
                {
                    "LocalizedDescription": "NY020 - Yorktown Heights",
                    "Address": {
                        "City": "Yorktown Heights",
                        "State": {"Code": "NY"},
                        "Country": {"Code": "USA"},
                    },
                },
                {
                    "LocalizedDescription": "MN010 - Eden Prairie",
                    "Address": {
                        "City": "Eden Prairie",
                        "State": {"Code": "MN"},
                        "Country": {"Code": "USA"},
                    },
                },
            ]
        )
        payload = make_response([item], 1)
        jobs = parse_opportunities(payload, HOST, TENANT, BOARD)
        self.assertEqual(
            jobs[0].location, "Yorktown Heights, NY, USA; Eden Prairie, MN, USA"
        )

    def test_missing_address_falls_back_to_localized_description(self) -> None:
        item = make_opportunity(
            Locations=[{"LocalizedDescription": "Remote - USA"}]
        )
        payload = make_response([item], 1)
        jobs = parse_opportunities(payload, HOST, TENANT, BOARD)
        self.assertEqual(jobs[0].location, "Remote - USA")

    def test_rejects_non_dict_payload(self) -> None:
        with self.assertRaises(ValueError):
            parse_opportunities([], HOST, TENANT, BOARD)

    def test_rejects_non_list_opportunities(self) -> None:
        with self.assertRaises(ValueError):
            parse_opportunities({"opportunities": "nope"}, HOST, TENANT, BOARD)

    def test_skips_item_with_no_title_or_id(self) -> None:
        payload = make_response(
            [make_opportunity(Title=""), make_opportunity(Id=None)], 2
        )
        jobs = parse_opportunities(payload, HOST, TENANT, BOARD)
        self.assertEqual(jobs, [])


class TestFormatLocation(unittest.TestCase):
    def test_no_locations_is_none(self) -> None:
        self.assertIsNone(format_location([]))
        self.assertIsNone(format_location(None))

    def test_skips_missing_parts(self) -> None:
        loc = {"Address": {"City": "Yorktown Heights", "Country": {"Code": "USA"}}}
        self.assertEqual(format_location([loc]), "Yorktown Heights, USA")


class TestFetchJobs(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = UltiproScraper(load_settings())
        self.company = make_company(CAREERS_URL)

    def test_single_page(self) -> None:
        response = make_response([make_opportunity()], 1)

        def fake_post_json(url, payload, settings):
            return response

        with patch("scraper.scrapers.ats.ultipro.post_json", side_effect=fake_post_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Senior Audio Engineer")

    def test_paginates_across_two_pages_stopping_at_total_count(self) -> None:
        calls: list[int] = []

        def fake_post_json(url, payload, settings):
            skip = payload["opportunitySearch"]["Skip"]
            calls.append(skip)
            if skip == 0:
                items = [
                    make_opportunity(Id=f"11111111-1111-1111-1111-11111111111{i}")
                    for i in range(PAGE_SIZE)
                ]
                return make_response(items, PAGE_SIZE + 5)
            items = [
                make_opportunity(Id=f"22222222-2222-2222-2222-22222222222{i}")
                for i in range(5)
            ]
            return make_response(items, PAGE_SIZE + 5)

        with patch("scraper.scrapers.ats.ultipro.post_json", side_effect=fake_post_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), PAGE_SIZE + 5)
        self.assertEqual(calls, [0, PAGE_SIZE])

    def test_max_pages_bounds_a_board_that_never_satisfies_total_count(self) -> None:
        call_count = 0

        def fake_post_json(url, payload, settings):
            nonlocal call_count
            call_count += 1
            skip = payload["opportunitySearch"]["Skip"]
            items = [
                make_opportunity(Id=f"33333333-3333-3333-3333-{skip:012d}{i}")
                for i in range(PAGE_SIZE)
            ]
            return make_response(items, 100_000)

        with patch("scraper.scrapers.ats.ultipro.post_json", side_effect=fake_post_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(call_count, MAX_PAGES)
        self.assertEqual(len(jobs), MAX_PAGES * PAGE_SIZE)

    def test_non_empty_query_param_is_sent_as_query_string(self) -> None:
        url = f"https://{HOST}/{TENANT}/JobBoard/{BOARD}/?q=audio&o=postedDateDesc"
        company = make_company(url)
        captured: dict = {}

        def fake_post_json(request_url, payload, settings):
            captured["query"] = payload["opportunitySearch"]["QueryString"]
            return make_response([], 0)

        with patch("scraper.scrapers.ats.ultipro.post_json", side_effect=fake_post_json):
            asyncio.run(self.scraper.fetch_jobs(company))

        self.assertEqual(captured["query"], "audio")

    def test_empty_query_param_is_sent_as_empty_string(self) -> None:
        captured: dict = {}

        def fake_post_json(request_url, payload, settings):
            captured["query"] = payload["opportunitySearch"]["QueryString"]
            return make_response([], 0)

        with patch("scraper.scrapers.ats.ultipro.post_json", side_effect=fake_post_json):
            asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(captured["query"], "")

    def test_malformed_payload_raises_scrape_error(self) -> None:
        def fake_post_json(url, payload, settings):
            return {"opportunities": "not-a-list"}

        with patch("scraper.scrapers.ats.ultipro.post_json", side_effect=fake_post_json):
            with self.assertRaises(ScrapeError):
                asyncio.run(self.scraper.fetch_jobs(self.company))


if __name__ == "__main__":
    unittest.main()
