from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.base import ScrapeError
from scraper.scrapers.http_scraper import (
    MIN_DESCRIPTION_CHARS,
    HttpScraper,
    _is_same_page_anchor,
    extract_description,
)

LISTING_HTML = """
<html><body>
<a href="https://example.com/careers/jobs/1">Audio DSP Engineer</a>
<a href="https://example.com/careers/jobs/2">Acoustic Engineer</a>
</body></html>
"""

NO_JOBS_HTML = "<html><body><h1>Careers</h1><p>Nothing here yet.</p></body></html>"

LONG_DESCRIPTION = "Full role description. " * 20

DETAIL_HTML_TEMPLATE = """
<html><body>
<nav>Home | Careers | About</nav>
<header>Site Header</header>
<main>
<h1>{title}</h1>
<p>{body}</p>
</main>
<footer>Site Footer</footer>
</body></html>
"""


def detail_html(title: str, body: str) -> str:
    return DETAIL_HTML_TEMPLATE.format(title=title, body=body)


LISTING_WITH_LONG_DESCRIPTION_HTML = """
<html><body>
<a href="https://example.com/careers/jobs/1">Audio DSP Engineer</a>
<a href="https://example.com/careers/jobs/2">Acoustic Engineer</a>
<script type="application/ld+json">{jsonld}</script>
</body></html>
""".format(
    jsonld=json.dumps(
        {
            "@type": "JobPosting",
            "title": "Audio DSP Engineer",
            "url": "https://example.com/careers/jobs/1",
            "description": LONG_DESCRIPTION,
        }
    )
)

OFFSITE_LISTING_HTML = """
<html><body>
<a href="https://example.com/careers/jobs/1">Audio DSP Engineer</a>
<a href="https://jobs.otherboard.com/careers/jobs/2">Acoustic Engineer</a>
</body></html>
"""

MANY_JOBS_HTML = "<html><body>" + "".join(
    f'<a href="https://example.com/careers/jobs/{i}">Audio Engineer {i}</a>'
    for i in range(5)
) + "</body></html>"


def make_company() -> Company:
    company = Company(
        name="Acme Audio",
        slug="acme-audio",
        category="Professional Audio & Live Sound",
        careers_url="https://example.com/careers",
        verified=True,
    )
    company.id = 0
    return company


class TestHttpScraper(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = load_settings()
        self.scraper = HttpScraper(self.settings)
        self.company = make_company()

    def test_extracted_jobs_are_returned(self) -> None:
        with patch(
            "scraper.scrapers.http_scraper.fetch_html",
            side_effect=lambda url, settings: LISTING_HTML,
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))
        self.assertEqual(len(jobs), 2)

    def test_no_job_links_raises_rather_than_returning_empty(self) -> None:
        with patch(
            "scraper.scrapers.http_scraper.fetch_html",
            side_effect=lambda url, settings: NO_JOBS_HTML,
        ):
            with self.assertRaises(ScrapeError):
                asyncio.run(self.scraper.fetch_jobs(self.company))

    def test_scrape_reports_failure_so_the_pipeline_falls_through(self) -> None:
        with patch(
            "scraper.scrapers.http_scraper.fetch_html",
            side_effect=lambda url, settings: NO_JOBS_HTML,
        ):
            result = asyncio.run(self.scraper.scrape(self.company))
        self.assertFalse(result.success)
        self.assertEqual(result.jobs, [])
        self.assertIsNotNone(result.html)

    def test_missing_careers_url_raises(self) -> None:
        self.company.careers_url = None
        with self.assertRaises(ValueError):
            asyncio.run(self.scraper.fetch_jobs(self.company))

    def test_job_with_empty_description_is_enriched(self) -> None:
        def fake_fetch(url, settings):
            if url == self.company.careers_url:
                return LISTING_HTML
            return detail_html("Audio DSP Engineer", LONG_DESCRIPTION)

        with patch(
            "scraper.scrapers.http_scraper.fetch_html", side_effect=fake_fetch
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        job = next(j for j in jobs if j.url.endswith("/jobs/1"))
        assert job.description is not None
        self.assertGreaterEqual(len(job.description), MIN_DESCRIPTION_CHARS)
        self.assertIn("Full role description.", job.description)

    def test_job_with_long_description_is_not_refetched(self) -> None:
        fetch_calls: list[str] = []

        def fake_fetch(url, settings):
            fetch_calls.append(url)
            if url == self.company.careers_url:
                return LISTING_WITH_LONG_DESCRIPTION_HTML
            return detail_html("Acoustic Engineer", LONG_DESCRIPTION)

        with patch(
            "scraper.scrapers.http_scraper.fetch_html", side_effect=fake_fetch
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        job1 = next(j for j in jobs if j.url.endswith("/jobs/1"))
        self.assertEqual(job1.description, LONG_DESCRIPTION)
        self.assertEqual(fetch_calls.count(job1.url), 0)
        self.assertEqual(len(fetch_calls), 2)

    def test_offsite_detail_url_is_skipped(self) -> None:
        offsite_url = "https://jobs.otherboard.com/careers/jobs/2"

        def fake_fetch(url, settings):
            if url == self.company.careers_url:
                return OFFSITE_LISTING_HTML
            if url == offsite_url:
                raise AssertionError("must not fetch an offsite detail url")
            return detail_html("Audio DSP Engineer", LONG_DESCRIPTION)

        with patch(
            "scraper.scrapers.http_scraper.fetch_html", side_effect=fake_fetch
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 2)
        offsite = next(j for j in jobs if j.url == offsite_url)
        self.assertIsNone(offsite.description)

    def test_detail_fetch_exception_leaves_job_intact(self) -> None:
        broken_url = "https://example.com/careers/jobs/1"

        def fake_fetch(url, settings):
            if url == self.company.careers_url:
                return LISTING_HTML
            if url == broken_url:
                raise ConnectionError("boom")
            return detail_html("Acoustic Engineer", LONG_DESCRIPTION)

        with patch(
            "scraper.scrapers.http_scraper.fetch_html", side_effect=fake_fetch
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 2)
        broken = next(j for j in jobs if j.url == broken_url)
        self.assertIsNone(broken.description)
        enriched = next(j for j in jobs if j.url.endswith("/jobs/2"))
        assert enriched.description is not None
        self.assertIn("Full role description.", enriched.description)

    def test_max_detail_fetches_caps_detail_requests(self) -> None:
        detail_calls: list[str] = []

        def fake_fetch(url, settings):
            if url == self.company.careers_url:
                return MANY_JOBS_HTML
            detail_calls.append(url)
            return detail_html("Audio Engineer", LONG_DESCRIPTION)

        with patch(
            "scraper.scrapers.http_scraper.fetch_html", side_effect=fake_fetch
        ), patch("scraper.scrapers.http_scraper.MAX_DETAIL_FETCHES", 2):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 5)
        self.assertEqual(len(detail_calls), 2)


class TestIsSamePageAnchor(unittest.TestCase):
    def test_fragment_only_difference_is_same_page(self) -> None:
        self.assertTrue(
            _is_same_page_anchor(
                "https://x.com/careers/#a", "https://x.com/careers/"
            )
        )

    def test_different_path_is_not_same_page(self) -> None:
        self.assertFalse(
            _is_same_page_anchor(
                "https://x.com/careers/jobs/1", "https://x.com/careers/"
            )
        )


class TestExtractDescription(unittest.TestCase):
    def test_prefers_main_over_surrounding_nav_and_footer_text(self) -> None:
        html_text = """
        <html><body>
        <nav>Home Careers About Navigation Links</nav>
        <header>Site Header Content</header>
        <main><p>This is the real job description with plenty of detail.</p></main>
        <footer>Copyright footer boilerplate text</footer>
        </body></html>
        """
        description = extract_description(html_text)
        assert description is not None
        self.assertIn("real job description", description)
        self.assertNotIn("Navigation Links", description)
        self.assertNotIn("footer boilerplate", description)

    def test_falls_back_to_body_when_no_landmark_present(self) -> None:
        html_text = "<html><body><p>Just a plain body description.</p></body></html>"
        description = extract_description(html_text)
        assert description is not None
        self.assertIn("Just a plain body description.", description)

    def test_returns_none_when_nothing_sensible_found(self) -> None:
        self.assertIsNone(extract_description("<html><body></body></html>"))


if __name__ == "__main__":
    unittest.main()
