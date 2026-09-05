from __future__ import annotations

import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from scraper.scrapers.ats.lever import LeverScraper, api_url_for, parse_postings


def make_company(url: str, ats_slug: str | None = None):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url=url,
        ats_slug=ats_slug,
    )

LEVER_PAYLOAD = [
    {
        "id": "a1b2c3d4",
        "text": "Audio Software Engineer",
        "hostedUrl": "https://jobs.lever.co/testco/a1b2c3d4",
        "applyUrl": "https://easyapply.co/a1b2c3d4",
        "createdAt": 1754006400000,
        "descriptionPlain": "Work on audio engines.",
        "categories": {
            "location": "Remote, US",
            "commitment": "Full-time",
            "team": "Engineering",
        },
    },
    {"id": "empty", "text": "", "hostedUrl": ""},
]


class TestLeverParser(unittest.TestCase):
    def test_parse_postings(self) -> None:
        jobs = parse_postings(LEVER_PAYLOAD)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Audio Software Engineer")
        self.assertEqual(job.external_id, "a1b2c3d4")
        self.assertEqual(job.url, "https://jobs.lever.co/testco/a1b2c3d4")
        self.assertEqual(job.location, "Remote, US")
        self.assertEqual(job.job_type, "full-time")
        self.assertEqual(job.description, "Work on audio engines.")
        self.assertEqual(job.posted_date, date(2025, 8, 1))

    def test_lists_sections_are_kept(self) -> None:
        payload = [
            {
                "id": "x1",
                "text": "Principal Engineer",
                "hostedUrl": "https://jobs.lever.co/testco/x1",
                "description": "<p>We lead the world in AV networking.</p>",
                "descriptionPlain": "We lead the world in AV networking.",
                "lists": [
                    {
                        "text": "What you'll be working on",
                        "content": "<li>Low latency audio transport</li>",
                    },
                    {"text": "What we're looking for", "content": "<li>C++ and DSP</li>"},
                ],
                "additional": "<p>Equal opportunity employer.</p>",
            }
        ]
        description = parse_postings(payload)[0].description or ""
        self.assertIn("AV networking", description)
        self.assertIn("What you&#39;ll be working on".replace("&#39;", "'"), description)
        self.assertIn("Low latency audio transport", description)
        self.assertIn("C++ and DSP", description)
        self.assertIn("Equal opportunity employer", description)

    def test_description_falls_back_to_plain(self) -> None:
        payload = [
            {
                "id": "x2",
                "text": "Audio Engineer",
                "hostedUrl": "https://jobs.lever.co/testco/x2",
                "descriptionPlain": "Only plain text here.",
            }
        ]
        self.assertEqual(parse_postings(payload)[0].description, "Only plain text here.")

    def test_parse_postings_rejects_non_list(self) -> None:
        with self.assertRaises(ValueError):
            parse_postings({"error": "not found"})

    def test_extract_slug(self) -> None:
        self.assertEqual(
            LeverScraper.extract_slug("https://jobs.lever.co/envato-2"), "envato-2"
        )
        self.assertIsNone(
            LeverScraper.extract_slug("https://example.com/careers")
        )

    def test_extract_slug_eu(self) -> None:
        self.assertEqual(
            LeverScraper.extract_slug("https://jobs.eu.lever.co/cirrus"), "cirrus"
        )

    def test_can_handle_us_and_eu(self) -> None:
        from scraper.config import load_settings

        scraper = LeverScraper(load_settings())
        self.assertTrue(scraper.can_handle(make_company("https://jobs.lever.co/envato-2")))
        self.assertTrue(scraper.can_handle(make_company("https://jobs.eu.lever.co/cirrus")))
        self.assertFalse(scraper.can_handle(make_company("https://example.com/careers")))


class TestApiUrlFor(unittest.TestCase):
    def test_eu_careers_url_routes_to_eu_host(self) -> None:
        self.assertEqual(
            api_url_for("https://jobs.eu.lever.co/cirrus", "cirrus"),
            "https://api.eu.lever.co/v0/postings/cirrus?mode=json",
        )

    def test_us_careers_url_routes_to_us_host(self) -> None:
        self.assertEqual(
            api_url_for("https://jobs.lever.co/envato-2", "envato-2"),
            "https://api.lever.co/v0/postings/envato-2?mode=json",
        )

    def test_non_matching_careers_url_falls_back_to_us_host(self) -> None:
        self.assertEqual(
            api_url_for("https://example.com/careers", "envato-2"),
            "https://api.lever.co/v0/postings/envato-2?mode=json",
        )


class TestLeverFetchJobs(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = LeverScraper(load_settings())

    def test_stored_ats_slug_with_eu_careers_url_still_routes_to_eu_host(self) -> None:
        company = make_company("https://jobs.eu.lever.co/cirrus", ats_slug="cirrus")
        seen_urls = []

        def fake_fetch_json(url: str, settings: object):
            seen_urls.append(url)
            return []

        with patch("scraper.scrapers.ats.lever.fetch_json", side_effect=fake_fetch_json):
            asyncio.run(self.scraper.fetch_jobs(company))

        self.assertEqual(seen_urls, ["https://api.eu.lever.co/v0/postings/cirrus?mode=json"])


if __name__ == "__main__":
    unittest.main()
