from __future__ import annotations

import unittest

from scraper.check_url import (
    DEFAULT_AUDIO_SCOPE,
    DiscoveredAts,
    Report,
    ResolvedContext,
    build_company,
    format_report,
    parse_args,
    report_to_dict,
    resolve_context,
)
from scraper.models import Company
from scraper.normalizer import NormalizedJob


def make_lookup(company: Company | None):
    def lookup(name: str) -> Company | None:
        return company

    return lookup


class TestParseArgs(unittest.TestCase):
    def test_url_is_required_positional(self) -> None:
        args = parse_args(["https://example.com/careers"])
        self.assertEqual(args.url, "https://example.com/careers")
        self.assertIsNone(args.name)
        self.assertIsNone(args.category)
        self.assertFalse(args.json)

    def test_all_options(self) -> None:
        args = parse_args(
            [
                "https://example.com/careers",
                "--name",
                "Acme Audio",
                "--category",
                "Professional Audio & Live Sound",
                "--json",
            ]
        )
        self.assertEqual(args.name, "Acme Audio")
        self.assertEqual(args.category, "Professional Audio & Live Sound")
        self.assertTrue(args.json)


class TestResolveContext(unittest.TestCase):
    def test_no_name_no_category_uses_defaults(self) -> None:
        context = resolve_context(None, None, make_lookup(None))
        self.assertIsNone(context.matched_company)
        self.assertIsNone(context.category)
        self.assertEqual(context.audio_scope, DEFAULT_AUDIO_SCOPE)
        self.assertTrue(context.used_default)

    def test_name_with_no_db_match_falls_back_to_defaults(self) -> None:
        context = resolve_context("Nonexistent Co", None, make_lookup(None))
        self.assertIsNone(context.matched_company)
        self.assertIsNone(context.category)
        self.assertEqual(context.audio_scope, DEFAULT_AUDIO_SCOPE)
        self.assertTrue(context.used_default)

    def test_db_match_supplies_category_and_scope(self) -> None:
        found = Company(
            id=5,
            name="Acme Audio",
            slug="acme-audio",
            category="Professional Audio & Live Sound",
            audio_scope="crossover",
        )
        context = resolve_context("acme audio", None, make_lookup(found))
        self.assertEqual(context.matched_company, "Acme Audio")
        self.assertEqual(context.category, "Professional Audio & Live Sound")
        self.assertEqual(context.audio_scope, "crossover")
        self.assertFalse(context.used_default)

    def test_explicit_category_overrides_db_lookup(self) -> None:
        found = Company(
            id=5,
            name="Acme Audio",
            slug="acme-audio",
            category="Professional Audio & Live Sound",
            audio_scope="crossover",
        )
        context = resolve_context("acme audio", "Consumer Electronics & Tech", make_lookup(found))
        self.assertEqual(context.matched_company, "Acme Audio")
        self.assertEqual(context.category, "Consumer Electronics & Tech")
        self.assertEqual(context.audio_scope, "crossover")
        self.assertFalse(context.used_default)

    def test_explicit_category_without_db_match(self) -> None:
        context = resolve_context(None, "Consumer Electronics & Tech", make_lookup(None))
        self.assertIsNone(context.matched_company)
        self.assertEqual(context.category, "Consumer Electronics & Tech")
        self.assertEqual(context.audio_scope, DEFAULT_AUDIO_SCOPE)
        self.assertFalse(context.used_default)


class TestBuildCompany(unittest.TestCase):
    def test_in_memory_company_fields(self) -> None:
        context = ResolvedContext(
            matched_company="Acme Audio",
            category="Professional Audio & Live Sound",
            audio_scope="native",
            used_default=False,
        )
        company = build_company("https://acme.example/careers", "Acme Audio", context)
        self.assertEqual(company.id, 0)
        self.assertEqual(company.name, "Acme Audio")
        self.assertEqual(company.slug, "acme-audio")
        self.assertEqual(company.careers_url, "https://acme.example/careers")
        self.assertTrue(company.verified)
        self.assertEqual(company.category, "Professional Audio & Live Sound")
        self.assertEqual(company.audio_scope, "native")
        self.assertIsNone(company.ats_type)
        self.assertIsNone(company.ats_slug)
        self.assertEqual(company.scrape_method, "http")

    def test_falls_back_to_url_when_name_missing(self) -> None:
        context = ResolvedContext(
            matched_company=None, category=None, audio_scope=DEFAULT_AUDIO_SCOPE, used_default=True
        )
        company = build_company("https://acme.example/careers", None, context)
        self.assertEqual(company.name, "https://acme.example/careers")


def make_job(
    title: str, score: int, on_board: bool, categories=(), description=None
) -> NormalizedJob:
    return NormalizedJob(
        title=title,
        url="https://acme.example/jobs/1",
        job_categories=list(categories),
        relevance_score=score,
        is_audio_related=on_board,
        description=description,
    )


class TestReportSummary(unittest.TestCase):
    def _report(self, jobs, success=True, method="greenhouse", error=None, discovered=None):
        context = ResolvedContext(
            matched_company=None, category=None, audio_scope=DEFAULT_AUDIO_SCOPE, used_default=True
        )
        return Report(
            url="https://acme.example/careers",
            context=context,
            method=method,
            success=success,
            error=error,
            discovered=discovered or [],
            jobs=jobs,
        )

    def test_counts(self) -> None:
        jobs = [
            make_job("Audio DSP Engineer", 90, True, description="x" * 250),
            make_job("Barista", 0, False, description="short"),
            make_job("Acoustic Engineer", 60, True),
        ]
        report = self._report(jobs)
        self.assertEqual(report.total_jobs, 3)
        self.assertEqual(report.board_count, 2)
        self.assertEqual(report.long_description_count, 1)

    def test_empty_jobs(self) -> None:
        report = self._report([])
        self.assertEqual(report.total_jobs, 0)
        self.assertEqual(report.board_count, 0)
        self.assertEqual(report.long_description_count, 0)

    def test_report_to_dict_matches_samples(self) -> None:
        jobs = [make_job("Audio DSP Engineer", 90, True, categories=["audio_dsp_embedded"])]
        report = self._report(jobs, discovered=[DiscoveredAts("greenhouse", "acme")])
        data = report_to_dict(report)
        self.assertEqual(data["total_jobs"], 1)
        self.assertEqual(data["board_count"], 1)
        self.assertEqual(
            data["discovered_ats"],
            [{"ats_type": "greenhouse", "ats_slug": "acme", "saved": False}],
        )
        self.assertEqual(len(data["samples"]), 1)
        self.assertEqual(data["samples"][0]["title"], "Audio DSP Engineer")
        self.assertEqual(data["samples"][0]["categories"], ["audio_dsp_embedded"])

    def test_samples_capped_at_ten(self) -> None:
        jobs = [make_job(f"Role {i}", i, True) for i in range(15)]
        report = self._report(jobs)
        data = report_to_dict(report)
        self.assertEqual(len(data["samples"]), 10)

    def test_failed_scrape_reports_error(self) -> None:
        report = self._report([], success=False, method="none", error="boom")
        text = format_report(report)
        self.assertIn("FAILED", text)
        self.assertIn("boom", text)

    def test_discovered_ats_marked_unsaved_in_text(self) -> None:
        report = self._report([], discovered=[DiscoveredAts("workday", "acme.wd1/Acme")])
        text = format_report(report)
        self.assertIn("workday/acme.wd1/Acme", text)
        self.assertIn("not saved", text)

    def test_board_count_is_prominent(self) -> None:
        jobs = [make_job("Audio DSP Engineer", 90, True)]
        report = self._report(jobs)
        text = format_report(report)
        self.assertIn("would appear on the public board: 1 / 1", text)


if __name__ == "__main__":
    unittest.main()
