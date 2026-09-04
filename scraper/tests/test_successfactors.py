from __future__ import annotations

import asyncio
import unittest
from datetime import date
from unittest.mock import patch

from scraper.scrapers.ats.successfactors import (
    ENRICHMENT_BUDGET_FRACTION,
    MAX_PAGES,
    PAGE_SIZE,
    SuccessFactorsScraper,
    apply_detail,
    extract_detail,
    extract_external_id,
    parse_listing_page,
)

CAREERS_URL = "https://careers.demant.com/search/"
ORIGIN = "https://careers.demant.com"

MUST_MATCH_URLS = [
    "https://careers.demant.com/search/",
    "https://careers.belden.com/search/?q=",
    "https://jobs.ferrari.com/search/",
    "https://careers.acer.com/search/",
    "https://careers.acer.com/go/All-Jobs/7865610/",
]

MUST_NOT_MATCH_URLS = [
    "https://www.tesla.com/careers/search/",
    "https://careers.zoom.us/jobs/search",
    "https://www.amazon.jobs/en/search?base_query=audio",
    "https://jobs.apple.com/en-us/search",
    "https://careershub-shure.icims.com/jobs/search?hashed=-435589572",
]


def make_company(url: str, ats_type: str | None = None):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Hardware",
        careers_url=url,
        ats_type=ats_type,
    )


def make_anchor(title: str, href: str) -> str:
    return (
        f'<a class="jobTitle-link fontcolorb6a533a1" data-focus-tile=".job-id-1" '
        f'href="{href}">{title}</a>'
    )


def make_listing_html(count: int, offset: int = 0) -> str:
    anchors = "\n".join(
        make_anchor(
            f"Audio Engineer {offset + i}",
            f"/DemantPoland/job/Role-{offset + i}/{1000000 + offset + i}/",
        )
        for i in range(count)
    )
    return f"<html><body>{anchors}</body></html>"


DETAIL_HTML = """
<html><body>
<span itemprop="title">DSP Engineer (f/m/d)</span>
<span itemprop="datePosted" content="2026-08-15">Aug 15, 2026</span>
<span itemprop="jobLocation">Middelfart, Denmark</span>
<span itemprop="description">
  <span class="jobdescription"><p>Design audio DSP pipelines.</p></span>
</span>
</body></html>
"""

REAL_DETAIL_HTML = """
<html><body>
<span itemprop="jobLocation" itemscope itemtype="http://schema.org/Place"><span
 itemprop="address" itemscope itemtype="http://schema.org/PostalAddress"><meta
 itemprop="streetAddress" content="Middelfart, DK, 5500"></span></span><meta
 itemprop="datePosted" content="Fri Aug 21 00:00:00 UTC 2026"><meta
 itemprop="validThrough" content="Sun Sep 13 22:00:00 UTC 2026">
<span itemprop="description"><span class="jobdescription"><p>Advanced signal
 processing.</p></span></span>
</body></html>
"""

DETAIL_HTML_NO_JOBDESCRIPTION_WRAPPER = """
<html><body>
<span itemprop="description">Plain description text.</span>
</body></html>
"""


class TestCanHandle(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = SuccessFactorsScraper(load_settings())

    def test_must_match_urls_are_handled(self) -> None:
        for url in MUST_MATCH_URLS:
            with self.subTest(url=url):
                self.assertTrue(self.scraper.can_handle(make_company(url)))

    def test_must_not_match_urls_are_rejected(self) -> None:
        for url in MUST_NOT_MATCH_URLS:
            with self.subTest(url=url):
                self.assertFalse(self.scraper.can_handle(make_company(url)))

    def test_ats_type_with_unrelated_url_is_handled(self) -> None:
        company = make_company("https://example.com/careers", ats_type="successfactors")
        self.assertTrue(self.scraper.can_handle(company))

    def test_no_careers_url_is_rejected(self) -> None:
        self.assertFalse(self.scraper.can_handle(make_company("")))


class TestParseListingPage(unittest.TestCase):
    def test_parses_title_url_and_external_id(self) -> None:
        html_text = (
            '<a class="jobTitle-link fontcolorb6a533a1" '
            'data-focus-tile=".job-id-1392155133" '
            'aria-describedby="jobSearchTileHelpText-1392155133" '
            'href="/DemantPoland/job/Warszawa-Azure-Cloud-Engineer-%28Regular-Senior%29'
            '-mazo-00-133/1392155133/">\n'
            "            Azure Cloud Engineer (Regular / Senior)\n"
            "</a>"
        )
        jobs = parse_listing_page(html_text, ORIGIN)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Azure Cloud Engineer (Regular / Senior)")
        self.assertEqual(
            job.url,
            "https://careers.demant.com/DemantPoland/job/Warszawa-Azure-Cloud-Engineer-"
            "%28Regular-Senior%29-mazo-00-133/1392155133/",
        )
        self.assertEqual(job.external_id, "1392155133")

    def test_repeated_tiles_for_one_job_collapse_to_a_single_row(self) -> None:
        anchor = (
            '<a class="jobTitle-link" '
            'href="/demant/job/Middelfart-DSP-Engineer/1428516433/">'
            "DSP Engineer (f/m/d)</a>"
        )
        jobs = parse_listing_page(anchor * 3, ORIGIN)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].external_id, "1428516433")

    def test_ignores_anchors_without_job_title_link_class(self) -> None:
        html_text = '<a class="other-link" href="/x/job/y/1/">Not a job</a>'
        self.assertEqual(parse_listing_page(html_text, ORIGIN), [])

    def test_no_rows_returns_empty_list(self) -> None:
        self.assertEqual(parse_listing_page("<html><body></body></html>", ORIGIN), [])

    def test_extract_external_id_trailing_numeric_segment(self) -> None:
        self.assertEqual(
            extract_external_id("/DemantPoland/job/Role/1392155133/"), "1392155133"
        )
        self.assertIsNone(extract_external_id("/DemantPoland/job/Role/"))


class TestExtractDetail(unittest.TestCase):
    def test_extracts_description_posted_date_and_location(self) -> None:
        detail = extract_detail(DETAIL_HTML)
        self.assertEqual(detail["description"], "<p>Design audio DSP pipelines.</p>")
        self.assertEqual(detail["posted_date"], date(2026, 8, 15))
        self.assertEqual(detail["location"], "Middelfart, Denmark")

    def test_reads_location_and_date_from_meta_content_attributes(self) -> None:
        detail = extract_detail(REAL_DETAIL_HTML)
        self.assertEqual(detail["location"], "Middelfart, DK, 5500")
        self.assertEqual(detail["posted_date"], date(2026, 8, 21))
        self.assertIn("Advanced signal", detail["description"])

    def test_falls_back_to_description_node_without_jobdescription_span(self) -> None:
        detail = extract_detail(DETAIL_HTML_NO_JOBDESCRIPTION_WRAPPER)
        self.assertEqual(detail["description"], "Plain description text.")

    def test_missing_microdata_yields_empty_detail(self) -> None:
        self.assertEqual(extract_detail("<html><body>nothing here</body></html>"), {})

    def test_apply_detail_only_sets_present_fields(self) -> None:
        from scraper.scrapers.base import RawJob

        job = RawJob(title="Existing", url="https://x/job/1/", location="Old Loc")
        apply_detail(job, {"description": "New desc"})
        self.assertEqual(job.description, "New desc")
        self.assertEqual(job.location, "Old Loc")
        self.assertIsNone(job.posted_date)


class TestFetchJobsPagination(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = SuccessFactorsScraper(load_settings())
        self.company = make_company(CAREERS_URL)

    def test_a_job_repeated_across_pages_is_stored_once(self) -> None:
        page = make_listing_html(PAGE_SIZE, offset=0)

        def fake_fetch_html(url: str, settings: object) -> str:
            if "startrow=" not in url:
                return "<html><body></body></html>"
            if "startrow=0" in url or "startrow=10" in url:
                return page
            return make_listing_html(0)

        with patch(
            "scraper.scrapers.ats.successfactors.fetch_html", fake_fetch_html
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))
        ids = [job.external_id for job in jobs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(jobs), PAGE_SIZE)

    def test_stops_on_short_page(self) -> None:
        listing_calls: list[str] = []

        def fake_fetch_html(url: str, settings: object) -> str:
            if "startrow=" not in url:
                return "<html><body></body></html>"
            listing_calls.append(url)
            if "startrow=0" in url:
                return make_listing_html(PAGE_SIZE, offset=0)
            if "startrow=10" in url:
                return make_listing_html(3, offset=PAGE_SIZE)
            return make_listing_html(0)

        with patch(
            "scraper.scrapers.ats.successfactors.fetch_html", side_effect=fake_fetch_html
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), PAGE_SIZE + 3)
        self.assertEqual(len(listing_calls), 2)

    def test_stops_on_no_rows(self) -> None:
        def fake_fetch_html(url: str, settings: object) -> str:
            if "startrow=0" in url:
                return make_listing_html(PAGE_SIZE, offset=0)
            return "<html><body></body></html>"

        with patch(
            "scraper.scrapers.ats.successfactors.fetch_html", side_effect=fake_fetch_html
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), PAGE_SIZE)

    def test_max_pages_bounds_an_always_full_sequence(self) -> None:
        listing_call_count = 0

        def fake_fetch_html(url: str, settings: object) -> str:
            nonlocal listing_call_count
            if "startrow=" not in url:
                return "<html><body></body></html>"
            offset = listing_call_count * PAGE_SIZE
            listing_call_count += 1
            return make_listing_html(PAGE_SIZE, offset=offset)

        with patch(
            "scraper.scrapers.ats.successfactors.fetch_html", side_effect=fake_fetch_html
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(listing_call_count, MAX_PAGES)
        self.assertEqual(len(jobs), MAX_PAGES * PAGE_SIZE)

    def test_query_param_is_forwarded_to_search_url(self) -> None:
        company = make_company("https://careers.demant.com/search/?q=audio")
        captured: list[str] = []

        def fake_fetch_html(url: str, settings: object) -> str:
            captured.append(url)
            return make_listing_html(0)

        with patch(
            "scraper.scrapers.ats.successfactors.fetch_html", side_effect=fake_fetch_html
        ):
            asyncio.run(self.scraper.fetch_jobs(company))

        self.assertIn("q=audio", captured[0])


class TestFetchJobsEnrichment(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = SuccessFactorsScraper(load_settings())
        self.company = make_company(CAREERS_URL)

    def test_detail_enrichment_fills_description_and_posted_date(self) -> None:
        listing_html = make_listing_html(1, offset=0)

        def fake_fetch_html(url: str, settings: object) -> str:
            if "startrow=0" in url:
                return listing_html
            if "startrow=" in url:
                return make_listing_html(0)
            return DETAIL_HTML

        with patch(
            "scraper.scrapers.ats.successfactors.fetch_html", side_effect=fake_fetch_html
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.description, "<p>Design audio DSP pipelines.</p>")
        self.assertEqual(job.posted_date, date(2026, 8, 15))
        self.assertEqual(job.location, "Middelfart, Denmark")

    def test_detail_fetch_exception_leaves_job_with_title_and_url(self) -> None:
        listing_html = make_listing_html(1, offset=0)
        job_url = "https://careers.demant.com/DemantPoland/job/Role-0/1000000/"

        def fake_fetch_html(url: str, settings: object) -> str:
            if "startrow=0" in url:
                return listing_html
            if "startrow=" in url:
                return make_listing_html(0)
            if url == job_url:
                raise ConnectionError("boom")
            raise AssertionError(f"unexpected url {url}")

        with patch(
            "scraper.scrapers.ats.successfactors.fetch_html", side_effect=fake_fetch_html
        ):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Audio Engineer 0")
        self.assertEqual(job.url, job_url)
        self.assertIsNone(job.description)

    def test_budget_exhaustion_skips_remaining_enrichment(self) -> None:
        listing_html = make_listing_html(3, offset=0)

        def fake_fetch_html(url: str, settings: object) -> str:
            if "startrow=0" in url:
                return listing_html
            if "startrow=" in url:
                return make_listing_html(0)
            return DETAIL_HTML

        budget = self.scraper.settings.per_company_timeout * ENRICHMENT_BUDGET_FRACTION

        with patch(
            "scraper.scrapers.ats.successfactors.fetch_html", side_effect=fake_fetch_html
        ), patch(
            "scraper.scrapers.ats.successfactors.monotonic",
            side_effect=[0.0, 0.0, 0.0, budget + 1.0],
        ):
            with self.assertLogs(
                "scraper.scrapers.ats.successfactors", level="INFO"
            ) as log_ctx:
                jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 3)
        enriched_count = sum(1 for j in jobs if j.description is not None)
        self.assertEqual(enriched_count, 2)
        self.assertTrue(
            any("enrichment budget exhausted" in msg for msg in log_ctx.output)
        )


if __name__ == "__main__":
    unittest.main()
