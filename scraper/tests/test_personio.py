from __future__ import annotations

import asyncio
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from scraper.config import load_settings
from scraper.scrapers.ats.personio import PersonioScraper, parse_feed
from scraper.scrapers.base import ScrapeError

ORIGIN = "https://acme.jobs.personio.de"

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<workzag-jobs>
<position>
    <id>2907600</id>
    <office>Berlin</office>
    <additionalOffices><office>Hamburg</office><office>Berlin</office></additionalOffices>
    <name>Application Engineer (f/m/d)</name>
    <jobDescriptions>
        <jobDescription>
            <name>Systems &amp; you</name>
            <value><![CDATA[<p>Design matrix arrays.</p>]]></value>
        </jobDescription>
        <jobDescription>
            <name>Empty</name>
            <value></value>
        </jobDescription>
    </jobDescriptions>
    <employmentType>permanent</employmentType>
    <schedule>full-time</schedule>
    <createdAt>2026-11-26T11:01:28+00:00</createdAt>
</position>
<position>
    <id>17</id>
    <name>Audio Intern</name>
    <employmentType>intern</employmentType>
    <createdAt>soon</createdAt>
</position>
<position>
    <id>not-a-number</id>
    <name>Broken</name>
</position>
</workzag-jobs>
"""


def company(url: str, ats_type: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(careers_url=url, ats_type=ats_type)


class TestParseFeed(unittest.TestCase):
    def test_reads_positions(self) -> None:
        first, second = parse_feed(FEED, ORIGIN)
        self.assertEqual(first.title, "Application Engineer (f/m/d)")
        self.assertEqual(first.url, f"{ORIGIN}/job/2907600")
        self.assertEqual(first.external_id, "2907600")
        self.assertEqual(first.location, "Berlin; Hamburg")
        self.assertEqual(
            first.description, "<h3>Systems &amp; you</h3><p>Design matrix arrays.</p>"
        )
        self.assertEqual(first.posted_date, date(2026, 11, 26))
        self.assertEqual(first.job_type, "full-time")
        self.assertIsNone(second.location)
        self.assertIsNone(second.description)
        self.assertIsNone(second.posted_date)
        self.assertEqual(second.job_type, "internship")

    def test_an_empty_board_is_an_empty_list(self) -> None:
        self.assertEqual(parse_feed("<workzag-jobs>\n\n</workzag-jobs>", ORIGIN), [])

    def test_refuses_entity_declarations(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_feed('<!DOCTYPE x [<!ENTITY a "b">]><workzag-jobs/>', ORIGIN)

    def test_rejects_html_and_other_xml(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_feed("<html><body>404</body></html>", ORIGIN)
        with self.assertRaises(ScrapeError):
            parse_feed("<workzag-jobs>", ORIGIN)


class TestScraper(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = PersonioScraper(load_settings())

    def test_can_handle(self) -> None:
        self.assertTrue(self.scraper.can_handle(company("https://acme.jobs.personio.de/")))
        self.assertTrue(self.scraper.can_handle(company("https://acme.jobs.personio.com/")))
        self.assertTrue(self.scraper.can_handle(company("https://jobs.acme.com/", "personio")))
        self.assertFalse(self.scraper.can_handle(company("https://acme.jobs.personio.de.evil.net/")))
        self.assertFalse(self.scraper.can_handle(company("https://jobs.acme.com/")))

    def test_fetches_the_english_feed_at_the_board_origin(self) -> None:
        seen: list[str] = []

        def fake_fetch(url: str, settings: object) -> str:
            seen.append(url)
            return FEED

        with patch("scraper.scrapers.ats.personio.fetch_html", fake_fetch):
            jobs = asyncio.run(self.scraper.fetch_jobs(company(f"{ORIGIN}/?language=de")))
        self.assertEqual(seen, [f"{ORIGIN}/xml?language=en"])
        self.assertEqual(len(jobs), 2)


if __name__ == "__main__":
    unittest.main()
