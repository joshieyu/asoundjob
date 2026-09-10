from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from scraper.scrapers.ats.icims import (
    IcimsScraper,
    detail_url,
    parse_listing_page,
    redirect_target,
    strip_query_params,
)
from scraper.scrapers.base import ScrapeError


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url=url,
    )


LISTING_PAGE_HTML = """
<html><body>
<a href="https://careers-shure.icims.com/jobs/12345/audio-dsp-engineer/job?in_iframe=1&hub=1">
Audio DSP Engineer
</a>
<a href="https://careershub-shure.icims.com/jobs/67890/senior-acoustic-engineer/job?mobile=false&in_iframe=1">
  Senior Acoustic Engineer
</a>
<a href="https://careershub-shure.icims.com/jobs/search?ss=1">Search Jobs</a>
<a href="https://careershub-shure.icims.com/connect">Join our talent community</a>
</body></html>
"""

NO_JOBS_HTML = """
<html><body>
<p>Sorry, no jobs were found matching your search criteria.</p>
</body></html>
"""

REDIRECT_HTML = (
    "<script>window.top.location.href = 'https:\\/\\/jobs.keysight.com\\/jobs';</script>"
)

UNRECOGNIZED_HTML = "<html><body><div>Careers at Acme</div></body></html>"

DETAIL_JSONLD_HTML = """
<html><body>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "Audio DSP Engineer",
  "description": "<p>Work on DSP pipelines.</p>",
  "datePosted": "2026-08-01",
  "jobLocation": {"address": {"addressLocality": "Chicago", "addressRegion": "IL"}}
}
</script>
</body></html>
"""


class TestIcimsParser(unittest.TestCase):
    def test_parse_listing_page(self) -> None:
        jobs = parse_listing_page(LISTING_PAGE_HTML)
        self.assertEqual(len(jobs), 2)

        first, second = jobs
        self.assertEqual(first.title, "Audio DSP Engineer")
        self.assertEqual(first.external_id, "12345")
        self.assertEqual(
            first.url,
            "https://careers-shure.icims.com/jobs/12345/audio-dsp-engineer/job",
        )

        self.assertEqual(second.title, "Senior Acoustic Engineer")
        self.assertEqual(second.external_id, "67890")
        self.assertEqual(
            second.url,
            "https://careershub-shure.icims.com/jobs/67890/senior-acoustic-engineer/job?mobile=false",
        )

    def test_parse_listing_page_cross_subdomain_preserved(self) -> None:
        jobs = parse_listing_page(LISTING_PAGE_HTML)
        hosts = {j.url.split("/")[2] for j in jobs}
        self.assertIn("careers-shure.icims.com", hosts)
        self.assertIn("careershub-shure.icims.com", hosts)

    def test_parse_listing_page_no_jobs(self) -> None:
        self.assertEqual(parse_listing_page(NO_JOBS_HTML), [])

    def test_parse_listing_page_drops_screen_reader_label(self) -> None:
        html_text = (
            '<a href="https://careers-shure.icims.com/jobs/4878/process/job">'
            '<span class="sr-only field-label">Job Title</span>'
            "<h3>Engineer Associate Staff, Process</h3></a>"
        )
        jobs = parse_listing_page(html_text)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Engineer Associate Staff, Process")

    def test_strip_query_params(self) -> None:
        self.assertEqual(
            strip_query_params(
                "https://x.icims.com/jobs/1/a/job?in_iframe=1&hub=abc&mobile=false"
            ),
            "https://x.icims.com/jobs/1/a/job?mobile=false",
        )
        self.assertEqual(
            strip_query_params("https://x.icims.com/jobs/1/a/job?in_iframe=1"),
            "https://x.icims.com/jobs/1/a/job",
        )

    def test_redirect_target_present(self) -> None:
        self.assertEqual(
            redirect_target(REDIRECT_HTML), "https://jobs.keysight.com/jobs"
        )

    def test_redirect_target_absent(self) -> None:
        self.assertIsNone(redirect_target(LISTING_PAGE_HTML))
        self.assertIsNone(redirect_target(NO_JOBS_HTML))

    def test_detail_url(self) -> None:
        self.assertEqual(
            detail_url("https://x.icims.com/jobs/1/a/job"),
            "https://x.icims.com/jobs/1/a/job?in_iframe=1",
        )
        self.assertEqual(
            detail_url("https://x.icims.com/jobs/1/a/job?mobile=false"),
            "https://x.icims.com/jobs/1/a/job?mobile=false&in_iframe=1",
        )

    def test_extract_slug(self) -> None:
        self.assertEqual(
            IcimsScraper.extract_slug("https://careershub-shure.icims.com/jobs/search"),
            "careershub-shure",
        )
        self.assertIsNone(IcimsScraper.extract_slug("https://example.com/careers"))

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = IcimsScraper(load_settings())
        self.assertTrue(
            scraper.can_handle(make_company("https://careershub-shure.icims.com/jobs/search"))
        )
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))


class TestIcimsFetchJobs(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = IcimsScraper(load_settings())
        self.company = make_company("https://careershub-shure.icims.com/jobs/search")

    def test_fetch_jobs_paginates_and_enriches(self) -> None:
        page0 = (
            '<a href="https://careershub-shure.icims.com/jobs/1/audio-dsp-engineer/job">'
            "Audio DSP Engineer</a>"
        ) * 1
        page0 = "<html><body>" + "".join(
            f'<a href="https://careershub-shure.icims.com/jobs/{i}/role-{i}/job">Role {i}</a>'
            for i in range(20)
        ) + "</body></html>"
        page1 = (
            '<html><body>'
            '<a href="https://careershub-shure.icims.com/jobs/999/audio-dsp-engineer/job">'
            "Audio DSP Engineer</a></body></html>"
        )

        def fake_fetch_html(url: str, settings: object) -> str:
            if "pr=0" in url:
                return page0
            if "pr=1" in url:
                return page1
            if "jobs/999/audio-dsp-engineer/job" in url:
                return DETAIL_JSONLD_HTML
            return "<html><body>no jobs</body></html>"

        with patch("scraper.scrapers.ats.icims.fetch_html", side_effect=fake_fetch_html):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 21)
        enriched = next(j for j in jobs if j.external_id == "999")
        self.assertEqual(enriched.description, "<p>Work on DSP pipelines.</p>")
        self.assertEqual(enriched.location, "Chicago, IL")

    def test_fetch_jobs_empty_board_returns_empty_list(self) -> None:
        with patch(
            "scraper.scrapers.ats.icims.fetch_html", side_effect=lambda url, settings: NO_JOBS_HTML
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))
        self.assertEqual(jobs, [])

    def test_fetch_jobs_unrecognized_page_raises(self) -> None:
        with patch(
            "scraper.scrapers.ats.icims.fetch_html",
            side_effect=lambda url, settings: UNRECOGNIZED_HTML,
        ):
            with self.assertRaises(ScrapeError) as ctx:
                asyncio.run(self.scraper.fetch_jobs(self.company))
        self.assertIn("empty-board marker", str(ctx.exception))

    def test_fetch_jobs_migrated_redirect_raises(self) -> None:
        with patch(
            "scraper.scrapers.ats.icims.fetch_html", side_effect=lambda url, settings: REDIRECT_HTML
        ):
            with self.assertRaises(ScrapeError) as ctx:
                asyncio.run(self.scraper.fetch_jobs(self.company))
        self.assertIn("https://jobs.keysight.com/jobs", str(ctx.exception))

    def test_fetch_jobs_survives_detail_fetch_exception(self) -> None:
        page0 = (
            '<html><body><a href="https://careershub-shure.icims.com/jobs/5/role/job">'
            "Role</a></body></html>"
        )

        def fake_fetch_html(url: str, settings: object) -> str:
            if "pr=0" in url:
                return page0
            if "jobs/5/role/job" in url:
                raise ConnectionError("boom")
            return "<html><body>no jobs</body></html>"

        with patch("scraper.scrapers.ats.icims.fetch_html", side_effect=fake_fetch_html):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 1)
        self.assertIsNone(jobs[0].description)


if __name__ == "__main__":
    unittest.main()
