from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scraper.detect_truncation import (
    CAP_BY_SCRAPE_METHOD,
    CompanyMetrics,
    evaluate,
    has_scoping_query,
    select_scrape_metrics,
)
from scraper.models import Base, Company, Job, ScrapeLog
from scraper.scrapers.ats.ultipro import MAX_PAGES as ULTIPRO_MAX_PAGES
from scraper.scrapers.ats.ultipro import PAGE_SIZE as ULTIPRO_PAGE_SIZE

EIGHTFOLD_CAP = CAP_BY_SCRAPE_METHOD["eightfold"]


def make_metrics(**overrides) -> CompanyMetrics:
    kwargs = dict(
        company_id=1,
        company="Acme",
        scrape_method="eightfold",
        jobs_found=EIGHTFOLD_CAP,
        active_jobs=EIGHTFOLD_CAP,
        board_jobs=1,
        audio_scope="native",
        careers_url="https://acme.eightfold.ai/careers",
    )
    kwargs.update(overrides)
    return CompanyMetrics(**kwargs)


class TestEvaluateThreshold(unittest.TestCase):
    def test_company_at_exactly_its_cap_is_flagged(self) -> None:
        row = make_metrics(jobs_found=EIGHTFOLD_CAP)
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].cap, EIGHTFOLD_CAP)
        self.assertEqual(findings[0].jobs_found, EIGHTFOLD_CAP)

    def test_company_one_below_its_cap_is_not_flagged(self) -> None:
        row = make_metrics(jobs_found=EIGHTFOLD_CAP - 1)
        findings = evaluate([row])
        self.assertEqual(findings, [])

    def test_unknown_scrape_method_is_excluded(self) -> None:
        row = make_metrics(scrape_method="http", jobs_found=10_000)
        findings = evaluate([row])
        self.assertEqual(findings, [])


class TestUltiproCap(unittest.TestCase):
    def test_ultipro_cap_is_max_pages_times_page_size(self) -> None:
        self.assertIn("ultipro", CAP_BY_SCRAPE_METHOD)
        self.assertEqual(
            CAP_BY_SCRAPE_METHOD["ultipro"], ULTIPRO_MAX_PAGES * ULTIPRO_PAGE_SIZE
        )


class TestEvaluateSortOrder(unittest.TestCase):
    def test_fewer_board_rows_sorts_first_at_equal_jobs_found(self) -> None:
        heavy_waste = make_metrics(
            company_id=1, company="Qualcomm", jobs_found=EIGHTFOLD_CAP, board_jobs=0
        )
        lighter_waste = make_metrics(
            company_id=2, company="Infineon", jobs_found=EIGHTFOLD_CAP, board_jobs=14
        )
        findings = evaluate([lighter_waste, heavy_waste])
        self.assertEqual([f.company for f in findings], ["Qualcomm", "Infineon"])

    def test_higher_jobs_found_sorts_first_at_equal_board_rows(self) -> None:
        low = make_metrics(
            company_id=1, company="Low", jobs_found=EIGHTFOLD_CAP, board_jobs=2
        )
        high = make_metrics(
            company_id=2, company="High", jobs_found=EIGHTFOLD_CAP + 50, board_jobs=2
        )
        findings = evaluate([low, high])
        self.assertEqual([f.company for f in findings], ["High", "Low"])


class TestMultiUrlCap(unittest.TestCase):
    def test_cap_scales_with_the_number_of_careers_urls(self) -> None:
        row = make_metrics(jobs_found=294, careers_url_count=2)
        self.assertEqual(evaluate([row], {"eightfold": 200}), [])

    def test_a_multi_url_company_at_its_combined_cap_is_flagged(self) -> None:
        row = make_metrics(jobs_found=400, careers_url_count=2)
        findings = evaluate([row], {"eightfold": 200})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].cap, 400)
        self.assertEqual(findings[0].careers_url_count, 2)

    def test_a_single_url_company_is_unaffected(self) -> None:
        row = make_metrics(jobs_found=200, careers_url_count=1)
        findings = evaluate([row], {"eightfold": 200})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].cap, 200)

    def test_a_zero_url_count_is_treated_as_one(self) -> None:
        row = make_metrics(jobs_found=200, careers_url_count=0)
        findings = evaluate([row], {"eightfold": 200})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].cap, 200)


class TestHasScopingQuery(unittest.TestCase):
    def test_query_key_with_value_is_true(self) -> None:
        self.assertTrue(has_scoping_query("https://acme.icims.com/jobs?query=audio"))

    def test_q_key_with_empty_value_is_false(self) -> None:
        self.assertFalse(has_scoping_query("https://acme.icims.com/jobs?q="))

    def test_no_query_string_at_all_is_false(self) -> None:
        self.assertFalse(has_scoping_query("https://acme.icims.com/jobs"))

    def test_search_key_with_value_is_true(self) -> None:
        self.assertTrue(
            has_scoping_query("https://jobs.apple.com/en-us/search?search=audio&page=1")
        )

    def test_unrelated_query_param_is_false(self) -> None:
        self.assertFalse(has_scoping_query("https://acme.icims.com/jobs?ss=1&in_iframe=1"))


class TestSelectScrapeMetrics(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.now = datetime.now(timezone.utc)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def _company(self, name: str, verified: bool = True, audio_scope: str = "native") -> Company:
        company = Company(
            name=name,
            slug=name.lower().replace(" ", "-"),
            category="Audio Software",
            careers_url=f"https://{name.lower()}.eightfold.ai/careers",
            verified=verified,
            audio_scope=audio_scope,
        )
        self.session.add(company)
        self.session.flush()
        return company

    def _log(
        self,
        company: Company,
        status: str,
        minutes_ago: int,
        jobs_found: int = 0,
        scrape_method: str = "eightfold",
    ) -> None:
        started = self.now - timedelta(minutes=minutes_ago)
        self.session.add(
            ScrapeLog(
                company_id=company.id,
                started_at=started,
                finished_at=started,
                status=status,
                jobs_found=jobs_found,
                scrape_method=scrape_method,
            )
        )
        self.session.flush()

    def _job(self, company: Company, is_active: bool, is_audio_related: bool) -> None:
        self.session.add(
            Job(
                company_id=company.id,
                title="Engineer",
                url=f"https://example.com/jobs/{company.id}/{is_active}/{is_audio_related}",
                is_active=is_active,
                is_audio_related=is_audio_related,
            )
        )
        self.session.flush()

    def test_failed_latest_scrape_is_not_considered(self) -> None:
        company = self._company("Failing Co")
        self._log(company, "failed", 5, jobs_found=EIGHTFOLD_CAP)
        rows = select_scrape_metrics(self.session)
        self.assertEqual(rows, [])

    def test_unverified_company_is_excluded(self) -> None:
        company = self._company("Unverified Co", verified=False)
        self._log(company, "success", 5, jobs_found=EIGHTFOLD_CAP)
        rows = select_scrape_metrics(self.session)
        self.assertEqual(rows, [])

    def test_recovered_company_is_included_at_its_latest_success(self) -> None:
        company = self._company("Recovered Co")
        self._log(company, "failed", 20, jobs_found=0)
        self._log(company, "success", 5, jobs_found=EIGHTFOLD_CAP)
        rows = select_scrape_metrics(self.session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].company, "Recovered Co")
        self.assertEqual(rows[0].jobs_found, EIGHTFOLD_CAP)
        findings = evaluate(rows)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].company, "Recovered Co")

    def test_regressed_company_is_excluded(self) -> None:
        company = self._company("Regressed Co")
        self._log(company, "success", 20, jobs_found=EIGHTFOLD_CAP)
        self._log(company, "failed", 5, jobs_found=0)
        rows = select_scrape_metrics(self.session)
        self.assertEqual(rows, [])

    def test_active_and_board_job_counts_are_attached(self) -> None:
        company = self._company("Counted Co")
        self._log(company, "success", 5, jobs_found=EIGHTFOLD_CAP)
        self._job(company, is_active=True, is_audio_related=True)
        self._job(company, is_active=True, is_audio_related=False)
        self._job(company, is_active=False, is_audio_related=True)
        rows = select_scrape_metrics(self.session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].active_jobs, 2)
        self.assertEqual(rows[0].board_jobs, 1)

    def test_company_with_no_jobs_at_all_defaults_counts_to_zero(self) -> None:
        company = self._company("Empty Board Co")
        self._log(company, "success", 5, jobs_found=EIGHTFOLD_CAP)
        rows = select_scrape_metrics(self.session)
        self.assertEqual(rows[0].active_jobs, 0)
        self.assertEqual(rows[0].board_jobs, 0)


if __name__ == "__main__":
    unittest.main()
