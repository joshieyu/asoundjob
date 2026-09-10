from __future__ import annotations

import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from scraper.scrapers.ats.sigma import (
    SigmaScraper,
    _parse_job,
    city_list_for,
    extract_company_prefix,
    generate_job_url,
    parse_jobs,
)
from scraper.scrapers.base import ScrapeError

CAREERS_URL = "https://integration.sigma.se/esb/vacancy/portal/positions"
CAREERS_URL_WITH_PREFIX = (
    "https://integration.sigma.se/esb/vacancy/portal/positions"
    "?company_startswith=Sigma%20Connectivity"
)


def make_company(url: str, ats_type=None):
    from scraper.models import Company

    return Company(
        id=1,
        name="Sigma",
        slug="sigma",
        category="Audio Hardware",
        careers_url=url,
        ats_type=ats_type,
    )


def make_item(**overrides):
    item = {
        "id": "profiler-position-8172",
        "company": "Sigma Connectivity Inc.",
        "title": {"en": "Audio Silicon Development Engineer", "sv": None},
        "description": {"en": "Build audio silicon.", "sv": None},
        "qualifications": {"en": "5 years of experience.", "sv": None},
        "offer": {"en": "Great benefits.", "sv": None},
        "experience": {"en": "Senior level.", "sv": None},
        "cities": {"en": "Redmond, WA", "sv": None},
        "country": {"en": "United States", "sv": None},
        "publicationDate": "2026-06-25T22:37:32.597Z",
    }
    item.update(overrides)
    return item


class TestCanHandle(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = SigmaScraper(load_settings())

    def test_api_url_is_handled(self) -> None:
        self.assertTrue(self.scraper.can_handle(make_company(CAREERS_URL)))

    def test_api_url_with_prefix_query_is_handled(self) -> None:
        self.assertTrue(self.scraper.can_handle(make_company(CAREERS_URL_WITH_PREFIX)))

    def test_ats_type_sigma_is_handled_regardless_of_url(self) -> None:
        self.assertTrue(
            self.scraper.can_handle(
                make_company("https://jobs.lever.co/acme", ats_type="sigma")
            )
        )

    def test_unrelated_url_with_no_ats_type_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("https://jobs.lever.co/acme")))


class TestExtractCompanyPrefix(unittest.TestCase):
    def test_extracts_prefix(self) -> None:
        self.assertEqual(
            extract_company_prefix(CAREERS_URL_WITH_PREFIX), "Sigma Connectivity"
        )

    def test_missing_prefix_falls_back_to_empty_string(self) -> None:
        self.assertEqual(extract_company_prefix(CAREERS_URL), "")


class TestParseJobsPrefixFiltering(unittest.TestCase):
    def test_prefix_filtering_is_case_insensitive(self) -> None:
        items = [
            make_item(id="1", company="Sigma Connectivity Inc."),
            make_item(id="2", company="sigma connectivity medtech"),
            make_item(id="3", company="Sigma Technology Cloud"),
        ]
        jobs = parse_jobs(items, "Sigma Connectivity")
        ids = {job.external_id for job in jobs}
        self.assertEqual(ids, {"1", "2"})

    def test_empty_prefix_keeps_everything(self) -> None:
        items = [
            make_item(id="1", company="Sigma Connectivity Inc."),
            make_item(id="2", company="Sigma Technology Cloud"),
        ]
        jobs = parse_jobs(items, "")
        ids = {job.external_id for job in jobs}
        self.assertEqual(ids, {"1", "2"})


class TestCityListFor(unittest.TestCase):
    def test_rejoins_us_state_codes(self) -> None:
        item = make_item(cities={"en": "Bay Area, CA, Redmond, WA", "sv": None})
        self.assertEqual(city_list_for(item), ["Bay Area, CA", "Redmond, WA"])

    def test_list_valued_cities(self) -> None:
        item = make_item(cities={"en": ["Bay Area", "CA", "Redmond", "WA"], "sv": None})
        self.assertEqual(city_list_for(item), ["Bay Area, CA", "Redmond, WA"])


class TestGenerateJobUrl(unittest.TestCase):
    def test_us_location_drops_country(self) -> None:
        item = make_item(
            title={"en": "Audio Silicon Development Engineer", "sv": None},
            cities={"en": "Redmond, WA", "sv": None},
            country={"en": "United States", "sv": None},
            publicationDate="2026-06-25T22:37:32.597Z",
        )
        self.assertEqual(
            generate_job_url(item),
            "https://www.sigma.se/position/audio-silicon-development-"
            "engineer-redmond-wa-en-20260625",
        )

    def test_non_us_location_appends_country(self) -> None:
        item = make_item(
            title={"en": "Senior Embedded Software Architect, MedTech", "sv": None},
            cities={"en": "Lund", "sv": None},
            country={"en": "Sweden", "sv": None},
            publicationDate="2026-06-26T12:57:26.707Z",
        )
        self.assertEqual(
            generate_job_url(item),
            "https://www.sigma.se/position/senior-embedded-software-architect-"
            "medtech-lund-sweden-en-20260626",
        )

    def test_swedish_locale_uses_sv_path_segment(self) -> None:
        item = make_item(
            title={"en": None, "sv": "Hårdvarukonstruktör"},
            cities={"en": None, "sv": "Lund"},
            country={"en": None, "sv": "Sverige"},
            publicationDate="2022-04-11T14:05:02Z",
        )
        self.assertEqual(
            generate_job_url(item),
            "https://www.sigma.se/sv/position/hardvarukonstruktor-lund-sverige-sv-20220411",
        )


class TestParseJob(unittest.TestCase):
    def test_concatenates_description_fields(self) -> None:
        job = _parse_job(make_item())
        assert job is not None
        self.assertIn("Build audio silicon.", job.description)
        self.assertIn("5 years of experience.", job.description)
        self.assertIn("Great benefits.", job.description)
        self.assertIn("Senior level.", job.description)
        self.assertEqual(job.posted_date, date(2026, 6, 25))
        self.assertEqual(job.external_id, "profiler-position-8172")
        self.assertEqual(job.location, "Redmond, WA")

    def test_skips_item_with_no_title_in_either_locale(self) -> None:
        job = _parse_job(make_item(title={"en": None, "sv": None}))
        self.assertIsNone(job)


class TestFetchJobs(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = SigmaScraper(load_settings())
        self.company = make_company(CAREERS_URL_WITH_PREFIX)

    def test_dedupes_by_external_id(self) -> None:
        items = [make_item(id="1"), make_item(id="1")]

        def fake_fetch_json(url, settings):
            return items

        with patch("scraper.scrapers.ats.sigma.fetch_json", side_effect=fake_fetch_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 1)

    def test_filters_by_prefix_from_url(self) -> None:
        items = [
            make_item(id="1", company="Sigma Connectivity Inc."),
            make_item(id="2", company="Sigma Technology Cloud"),
        ]

        def fake_fetch_json(url, settings):
            return items

        with patch("scraper.scrapers.ats.sigma.fetch_json", side_effect=fake_fetch_json):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].external_id, "1")

    def test_non_list_response_raises_scrape_error(self) -> None:
        def fake_fetch_json(url, settings):
            return {"not": "a list"}

        with patch("scraper.scrapers.ats.sigma.fetch_json", side_effect=fake_fetch_json):
            with self.assertRaises(ScrapeError):
                asyncio.run(self.scraper.fetch_jobs(self.company))


if __name__ == "__main__":
    unittest.main()
