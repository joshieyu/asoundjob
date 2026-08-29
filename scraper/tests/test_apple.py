from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch

from scraper.scrapers.ats.apple import (
    DETAIL_URL,
    ENRICHMENT_BUDGET_FRACTION,
    AppleScraper,
    _compose_description,
    _extract_hydration_data,
    _extract_jobs_data,
    _extract_pay_benefits,
    _map_employment_type,
    _parse_result,
    _parse_search_page,
)


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Apple",
        slug="apple",
        category="Audio Software",
        careers_url=url,
    )


HYDRATION_JSON = (
    '{"loaderData":{"search":{"searchResults":['
    '{"id":"200679909-0836","postingTitle":"Software Engineer - VE",'
    '"jobSummary":"Work on virtual engineering.",'
    '"locations":[{"name":"Cupertino","countryName":"United States"}],'
    '"postingDate":"Aug 26, 2026",'
    '"team":{"teamName":"Hardware"},'
    '"transformedPostingTitle":"software-engineer-ve",'
    '"reqId":"200679909-0836"},'
    '{"id":"PIPE-123","postingTitle":"Audio DSP Engineer",'
    '"jobSummary":"Design audio algorithms.",'
    '"locations":[{"name":"Cupertino"}],'
    '"postingDate":"Aug 25, 2026",'
    '"team":{"teamName":"Software and Services"},'
    '"transformedPostingTitle":"audio-dsp-engineer",'
    '"reqId":"PIPE-123"}'
    '],"totalRecords":2,"page":1}}}'
)

HYDRATION_HTML = (
    '<html><script>window.__staticRouterHydrationData = JSON.parse("'
    + HYDRATION_JSON.replace('"', '\\"')
    + '");</script></html>'
)


def _wrap_hydration(payload: dict) -> str:
    encoded = json.dumps(payload).replace('"', '\\"')
    return (
        '<html><script>window.__staticRouterHydrationData = JSON.parse("'
        + encoded
        + '");</script></html>'
    )


FULL_JOBS_DATA = {
    "jobSummary": "Join our team building next-generation audio hardware.",
    "description": "You will design and validate audio subsystems end to end.",
    "responsibilities": (
        "Own audio subsystem architecture.\n"
        "Partner with & mentor <junior> engineers.\n"
        "Drive validation across programs."
    ),
    "minimumQualifications": (
        "5+ years of audio engineering experience.\nBS in EE or related field."
    ),
    "preferredQualifications": "Experience with DSP tuning.\nExperience with C++.",
    "employmentType": "Standard",
    "postingFooters": [
        {
            "postLocationId": "postLocation-USA",
            "localizations": {
                "en_US": [
                    {
                        "name": "Pay & Benefits",
                        "content": (
                            "The base pay range for this role is between "
                            "$195,700 and $338,400."
                        ),
                    },
                    {
                        "name": "EEO Statement",
                        "content": "<p>Apple is an equal opportunity employer.</p>",
                    },
                ]
            },
        }
    ],
}

FULL_DETAIL_HTML = _wrap_hydration(
    {"loaderData": {"jobDetails": {"jobsData": FULL_JOBS_DATA}}}
)

EXPIRED_DETAIL_HTML = _wrap_hydration({"loaderData": {"root": {}}})

THREE_JOB_IDS = ["JOB-0", "JOB-1", "JOB-2"]

THREE_JOB_SEARCH_HTML = _wrap_hydration(
    {
        "loaderData": {
            "search": {
                "searchResults": [
                    {
                        "id": job_id,
                        "postingTitle": f"Audio Engineer {i}",
                        "jobSummary": f"Summary for job {i}.",
                        "locations": [{"name": "Cupertino"}],
                        "postingDate": "Aug 25, 2026",
                        "team": {"teamName": "Audio Team"},
                        "transformedPostingTitle": f"audio-engineer-{i}",
                        "reqId": job_id,
                    }
                    for i, job_id in enumerate(THREE_JOB_IDS)
                ],
                "totalRecords": len(THREE_JOB_IDS),
                "page": 1,
            }
        }
    }
)


class TestAppleParser(unittest.TestCase):
    def test_parse_search_page(self) -> None:
        jobs = _parse_search_page(HYDRATION_HTML)
        self.assertEqual(len(jobs), 2)
        first = jobs[0]
        self.assertEqual(first.title, "Software Engineer - VE")
        self.assertEqual(first.external_id, "200679909-0836")
        self.assertEqual(
            first.url,
            "https://jobs.apple.com/en-us/details/200679909-0836/software-engineer-ve",
        )
        self.assertEqual(first.location, "Cupertino")
        self.assertIn("Hardware", first.description or "")
        self.assertIn("virtual engineering", first.description or "")

    def test_parse_result_missing_title(self) -> None:
        self.assertIsNone(_parse_result({"id": "1", "postingTitle": ""}))

    def test_parse_result_missing_url(self) -> None:
        self.assertIsNone(_parse_result({"postingTitle": "Engineer", "id": ""}))

    def test_extract_hydration_data(self) -> None:
        data = _extract_hydration_data(HYDRATION_HTML)
        assert data is not None
        self.assertIn("loaderData", data)

    def test_extract_hydration_data_none(self) -> None:
        self.assertIsNone(_extract_hydration_data("<html>no data</html>"))

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = AppleScraper(load_settings())
        self.assertTrue(
            scraper.can_handle(make_company("https://jobs.apple.com/en-us/search"))
        )
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))

    def test_compose_description_full_order(self) -> None:
        description = _compose_description(
            team_name="Hardware",
            job_summary="Teaser summary.",
            description="Full role description.",
            responsibilities="Do the thing.\nDo another thing.",
            minimum_qualifications="5+ years experience.",
            preferred_qualifications="Nice to have skill.",
            pay_benefits="The base pay range for this role is between $100,000 and $150,000.",
        )
        assert description is not None
        self.assertIn("<p>Team: Hardware</p>", description)
        self.assertIn("<p>Teaser summary.</p>", description)
        self.assertIn("<p>Full role description.</p>", description)
        self.assertIn("<h3>Responsibilities</h3>", description)
        self.assertIn("<li>Do the thing.</li>", description)
        self.assertIn("<h3>Minimum Qualifications</h3>", description)
        self.assertIn("<h3>Preferred Qualifications</h3>", description)
        self.assertIn("<h3>Pay &amp; Benefits</h3>", description)
        self.assertIn("$100,000 and $150,000", description)

        team_idx = description.index("Team: Hardware")
        summary_idx = description.index("Teaser summary.")
        desc_idx = description.index("Full role description.")
        resp_idx = description.index("Responsibilities")
        min_idx = description.index("Minimum Qualifications")
        pref_idx = description.index("Preferred Qualifications")
        pay_idx = description.index("Pay &amp; Benefits")
        self.assertTrue(
            team_idx
            < summary_idx
            < desc_idx
            < resp_idx
            < min_idx
            < pref_idx
            < pay_idx
        )

    def test_compose_description_skips_missing_sections(self) -> None:
        description = _compose_description(team_name=None, job_summary="Only summary.")
        self.assertEqual(description, "<p>Only summary.</p>")

    def test_compose_description_none_when_empty(self) -> None:
        self.assertIsNone(_compose_description(team_name=None, job_summary=None))

    def test_bullet_fields_are_html_escaped(self) -> None:
        description = _compose_description(
            team_name=None,
            job_summary=None,
            responsibilities="Partner with <script>alert(1)</script> & mentor others.",
        )
        assert description is not None
        self.assertIn(
            "<li>Partner with &lt;script&gt;alert(1)&lt;/script&gt; &amp; mentor others.</li>",
            description,
        )
        self.assertNotIn("<script>alert(1)</script>", description)

    def test_extract_pay_benefits_when_not_first(self) -> None:
        footers = [
            {
                "postLocationId": "postLocation-USA",
                "localizations": {
                    "en_US": [
                        {"name": "EEO Statement", "content": "<p>Equal opportunity.</p>"},
                        {
                            "name": "Pay & Benefits",
                            "content": (
                                "The base pay range for this role is "
                                "between $80,000 and $120,000."
                            ),
                        },
                    ]
                },
            }
        ]
        content = _extract_pay_benefits(footers)
        self.assertEqual(
            content,
            "The base pay range for this role is between $80,000 and $120,000.",
        )

    def test_extract_pay_benefits_missing(self) -> None:
        self.assertIsNone(_extract_pay_benefits([]))
        self.assertIsNone(_extract_pay_benefits(None))

    def test_extract_jobs_data_present(self) -> None:
        jobs_data = _extract_jobs_data(FULL_DETAIL_HTML)
        assert jobs_data is not None
        self.assertEqual(jobs_data.get("employmentType"), "Standard")

    def test_extract_jobs_data_expired(self) -> None:
        self.assertIsNone(_extract_jobs_data(EXPIRED_DETAIL_HTML))

    def test_map_employment_type(self) -> None:
        self.assertEqual(_map_employment_type("Standard"), "full-time")
        self.assertEqual(_map_employment_type("Intern"), "internship")
        self.assertEqual(_map_employment_type("Contractor"), "contract")
        self.assertIsNone(_map_employment_type("Something Unusual"))
        self.assertIsNone(_map_employment_type(None))

    def test_salary_extractable_from_composed_description(self) -> None:
        from scraper.normalizer import parse_salary

        description = _compose_description(
            team_name=None,
            job_summary=None,
            pay_benefits=(
                "The base pay range for this role is between "
                "$195,700 and $338,400, and your base pay will depend on location."
            ),
        )
        assert description is not None
        low, high, currency = parse_salary(description)
        self.assertEqual(low, 195700)
        self.assertEqual(high, 338400)
        self.assertEqual(currency, "USD")
        self.assertIn("195,700", description)
        self.assertIn("338,400", description)


def _detail_url_for(job_id: str, slug: str) -> str:
    return DETAIL_URL.format(job_id=job_id, slug=slug)


class TestAppleEnrichment(unittest.TestCase):
    def setUp(self) -> None:
        from scraper.config import load_settings

        self.scraper = AppleScraper(load_settings())
        self.company = make_company("https://jobs.apple.com/en-us/search")

    def test_fetch_jobs_enriches_and_falls_back_on_expired(self) -> None:
        full_url = _detail_url_for("200679909-0836", "software-engineer-ve")
        expired_url = _detail_url_for("PIPE-123", "audio-dsp-engineer")

        def fake_fetch_html(url: str, settings: object) -> str:
            if url.startswith("https://jobs.apple.com/en-us/search"):
                return HYDRATION_HTML
            if url == full_url:
                return FULL_DETAIL_HTML
            if url == expired_url:
                return EXPIRED_DETAIL_HTML
            raise AssertionError(f"unexpected url {url}")

        with patch("scraper.scrapers.ats.apple.fetch_html", side_effect=fake_fetch_html):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 2)
        enriched = next(j for j in jobs if j.url == full_url)
        expired = next(j for j in jobs if j.url == expired_url)

        assert enriched.description is not None
        self.assertIn("<h3>Responsibilities</h3>", enriched.description)
        self.assertIn("<h3>Pay &amp; Benefits</h3>", enriched.description)
        self.assertEqual(enriched.job_type, "full-time")

        assert expired.description is not None
        self.assertIn("Design audio algorithms.", expired.description)
        self.assertIsNone(expired.job_type)

    def test_fetch_jobs_survives_detail_fetch_exception(self) -> None:
        full_url = _detail_url_for("200679909-0836", "software-engineer-ve")
        broken_url = _detail_url_for("PIPE-123", "audio-dsp-engineer")

        def fake_fetch_html(url: str, settings: object) -> str:
            if url.startswith("https://jobs.apple.com/en-us/search"):
                return HYDRATION_HTML
            if url == full_url:
                return FULL_DETAIL_HTML
            if url == broken_url:
                raise ConnectionError("boom")
            raise AssertionError(f"unexpected url {url}")

        with patch("scraper.scrapers.ats.apple.fetch_html", side_effect=fake_fetch_html):
            jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 2)
        broken = next(j for j in jobs if j.url == broken_url)
        assert broken.description is not None
        self.assertIn("Design audio algorithms.", broken.description)

    def test_fetch_jobs_partial_enrichment_when_budget_runs_out(self) -> None:
        urls = [
            _detail_url_for(job_id, f"audio-engineer-{i}")
            for i, job_id in enumerate(THREE_JOB_IDS)
        ]

        def fake_fetch_html(url: str, settings: object) -> str:
            if url.startswith("https://jobs.apple.com/en-us/search"):
                return THREE_JOB_SEARCH_HTML
            if url in urls:
                return FULL_DETAIL_HTML
            raise AssertionError(f"unexpected url {url}")

        budget = self.scraper.settings.per_company_timeout * ENRICHMENT_BUDGET_FRACTION

        with patch(
            "scraper.scrapers.ats.apple.fetch_html", side_effect=fake_fetch_html
        ), patch(
            "scraper.scrapers.ats.apple.monotonic",
            side_effect=[0.0, 0.0, 0.0, budget + 1.0],
        ):
            with self.assertLogs(
                "scraper.scrapers.ats.apple", level="INFO"
            ) as log_ctx:
                jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 3)
        by_url = {job.url: job for job in jobs}
        for url in urls[:2]:
            enriched = by_url[url]
            assert enriched.description is not None
            self.assertIn("<h3>Responsibilities</h3>", enriched.description)

        skipped = by_url[urls[2]]
        assert skipped.description is not None
        self.assertNotIn("<h3>Responsibilities</h3>", skipped.description)
        self.assertIn("Summary for job 2.", skipped.description)
        self.assertTrue(
            any("enrichment budget exhausted" in msg for msg in log_ctx.output)
        )
        self.assertTrue(any("2/3" in msg for msg in log_ctx.output))

    def test_fetch_jobs_returns_full_list_when_budget_expires_immediately(
        self,
    ) -> None:
        urls = [
            _detail_url_for(job_id, f"audio-engineer-{i}")
            for i, job_id in enumerate(THREE_JOB_IDS)
        ]

        def fake_fetch_html(url: str, settings: object) -> str:
            if url.startswith("https://jobs.apple.com/en-us/search"):
                return THREE_JOB_SEARCH_HTML
            raise AssertionError(f"detail page should not be fetched for {url}")

        budget = self.scraper.settings.per_company_timeout * ENRICHMENT_BUDGET_FRACTION

        with patch(
            "scraper.scrapers.ats.apple.fetch_html", side_effect=fake_fetch_html
        ), patch(
            "scraper.scrapers.ats.apple.monotonic",
            side_effect=[0.0, budget + 1.0, budget + 1.0, budget + 1.0],
        ):
            with self.assertLogs(
                "scraper.scrapers.ats.apple", level="INFO"
            ) as log_ctx:
                jobs = asyncio.run(self.scraper.fetch_jobs(self.company))

        self.assertEqual(len(jobs), 3)
        self.assertEqual({job.url for job in jobs}, set(urls))
        for job in jobs:
            assert job.description is not None
            self.assertNotIn("<h3>Responsibilities</h3>", job.description)
        self.assertTrue(
            any("enrichment budget exhausted" in msg for msg in log_ctx.output)
        )
        self.assertTrue(any("0/3" in msg for msg in log_ctx.output))


if __name__ == "__main__":
    unittest.main()
