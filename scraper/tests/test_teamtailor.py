from __future__ import annotations

import asyncio
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from scraper.config import load_settings
from scraper.scrapers.ats.teamtailor import TeamtailorScraper, parse_feed
from scraper.scrapers.base import ScrapeError

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:tt="https://teamtailor.com/locations">
  <channel>
    <title>Example Careers</title>
    <link>https://careers.example.com/jobs</link>
    <item>
      <title>Senior Machine Learning Engineer - Audio/Music Processing</title>
      <description>&lt;p&gt;Build models that identify music.&lt;/p&gt;</description>
      <pubDate>Wed, 18 Nov 2026 15:08:31 +0200</pubDate>
      <link>https://careers.example.com/jobs/8761999-senior-ml-engineer</link>
      <remoteStatus>fully</remoteStatus>
      <guid>7f5422a8-b0b1-4a74-842e-5cf59dc41c2b</guid>
      <tt:locations>
        <tt:location>
          <tt:city>Helsinki</tt:city>
          <tt:country>Finland</tt:country>
        </tt:location>
        <tt:location>
          <tt:city>Stockholm</tt:city>
          <tt:country>Sweden</tt:country>
        </tt:location>
      </tt:locations>
    </item>
    <item>
      <title>Open Application</title>
      <description></description>
      <pubDate>not a date</pubDate>
      <link>https://careers.example.com/connect</link>
      <remoteStatus>hybrid</remoteStatus>
      <guid>connect-guid</guid>
    </item>
    <item>
      <title></title>
      <link>https://careers.example.com/jobs/1-untitled</link>
    </item>
  </channel>
</rss>
"""

EMPTY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:tt="https://teamtailor.com/locations">
  <channel><title>Example Careers</title></channel>
</rss>
"""


def company(url: str, ats_type: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(careers_url=url, ats_type=ats_type)


class TestParseFeed(unittest.TestCase):
    def test_reads_items(self) -> None:
        jobs = parse_feed(FEED)
        self.assertEqual(len(jobs), 2)
        first, second = jobs
        self.assertEqual(first.title, "Senior Machine Learning Engineer - Audio/Music Processing")
        self.assertEqual(first.external_id, "8761999")
        self.assertEqual(first.url, "https://careers.example.com/jobs/8761999-senior-ml-engineer")
        self.assertEqual(first.location, "Helsinki, Finland; Stockholm, Sweden")
        self.assertEqual(first.posted_date, date(2026, 11, 18))
        self.assertTrue(first.remote_hint)
        self.assertIn("identify music", first.description or "")
        self.assertEqual(second.external_id, "connect-guid")
        self.assertIsNone(second.location)
        self.assertIsNone(second.posted_date)
        self.assertFalse(second.remote_hint)
        self.assertIsNone(second.description)

    def test_empty_feed_is_an_empty_board(self) -> None:
        self.assertEqual(parse_feed(EMPTY_FEED), [])

    def test_refuses_entity_declarations(self) -> None:
        feed = '<?xml version="1.0"?><!DOCTYPE rss [<!ENTITY a "b">]><rss><channel/></rss>'
        with self.assertRaises(ScrapeError):
            parse_feed(feed)

    def test_rejects_html(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_feed("<html><body>404</body></html>")

    def test_rejects_invalid_xml(self) -> None:
        with self.assertRaises(ScrapeError):
            parse_feed("<rss><channel>")


class TestScraper(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = TeamtailorScraper(load_settings())

    def test_can_handle(self) -> None:
        self.assertTrue(self.scraper.can_handle(company("https://acme.teamtailor.com/jobs")))
        custom = company("https://careers.acme.com/jobs", "teamtailor")
        self.assertTrue(self.scraper.can_handle(custom))
        self.assertFalse(self.scraper.can_handle(company("https://careers.acme.com/jobs")))
        self.assertFalse(self.scraper.can_handle(company("https://teamtailor.com.evil.example/jobs")))

    def test_fetches_the_feed_at_the_board_origin(self) -> None:
        seen: list[str] = []

        def fake_fetch(url: str, settings: object) -> str:
            seen.append(url)
            return FEED

        board = company("https://careers.acme.com/jobs?department=audio", "teamtailor")
        with patch("scraper.scrapers.ats.teamtailor.fetch_html", fake_fetch):
            jobs = asyncio.run(self.scraper.fetch_jobs(board))
        self.assertEqual(seen, ["https://careers.acme.com/jobs.rss"])
        self.assertEqual(len(jobs), 2)

    def test_missing_host_raises(self) -> None:
        with self.assertRaises(ScrapeError):
            asyncio.run(self.scraper.fetch_jobs(company("", "teamtailor")))


if __name__ == "__main__":
    unittest.main()
