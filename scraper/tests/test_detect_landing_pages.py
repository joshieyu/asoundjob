from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scraper.detect_landing_pages import (
    CompanyLandingRows,
    evaluate,
    is_region_row,
    is_taxonomy_row,
    normalize_host,
    select_landing_page_candidates,
)
from scraper.models import Base, Company, Job, ScrapeLog


def make_rows(**overrides) -> CompanyLandingRows:
    kwargs = dict(
        company_id=1,
        company="Example Co",
        audio_scope="native",
        careers_url="https://example.com/careers",
        board_rows=0,
        rows=[("Careers", "https://example.com/careers")],
    )
    kwargs.update(overrides)
    return CompanyLandingRows(**kwargs)


class TestNormalizeHost(unittest.TestCase):
    def test_strips_www(self) -> None:
        self.assertEqual(normalize_host("https://www.onsemi.com/careers"), "onsemi.com")

    def test_lowercases(self) -> None:
        result = normalize_host("https://Hctz.FA.US2.OracleCloud.com/x")
        self.assertEqual(result, "hctz.fa.us2.oraclecloud.com")

    def test_blank_url_is_empty_host(self) -> None:
        self.assertEqual(normalize_host(""), "")


class TestIsRegionRow(unittest.TestCase):
    def test_bare_country_name_is_region_row(self) -> None:
        self.assertTrue(is_region_row("germany"))

    def test_country_with_careers_suffix_is_region_row(self) -> None:
        self.assertTrue(is_region_row("germany careers"))

    def test_country_alias_with_jobs_suffix_is_region_row(self) -> None:
        self.assertTrue(is_region_row("uk jobs"))

    def test_japan_careers_is_region_row(self) -> None:
        self.assertTrue(is_region_row("japan careers"))

    def test_real_job_title_is_not_region_row(self) -> None:
        self.assertFalse(is_region_row("audio dsp engineer"))


class TestIsTaxonomyRow(unittest.TestCase):
    def test_engineering_jobs_is_taxonomy(self) -> None:
        self.assertTrue(is_taxonomy_row("Engineering Jobs"))

    def test_manufacturing_jobs_is_taxonomy(self) -> None:
        self.assertTrue(is_taxonomy_row("Manufacturing Jobs"))

    def test_germany_careers_is_taxonomy(self) -> None:
        self.assertTrue(is_taxonomy_row("Germany Careers"))

    def test_bare_careers_is_taxonomy(self) -> None:
        self.assertTrue(is_taxonomy_row("Careers"))

    def test_consulting_jobs_is_taxonomy(self) -> None:
        self.assertTrue(is_taxonomy_row("Consulting Jobs"))

    def test_real_job_title_is_not_taxonomy(self) -> None:
        self.assertFalse(is_taxonomy_row("Audio DSP Engineer"))


class TestEvaluateFlagsDepartmentSuffixLandingPage(unittest.TestCase):
    def test_on_semiconductor_style_company_is_flagged_with_off_host_suggestion(self) -> None:
        row = make_rows(
            company="ON Semiconductor",
            careers_url="https://www.onsemi.com/careers",
            board_rows=0,
            rows=[
                ("Engineering Jobs", "https://hctz.fa.us2.oraclecloud.com/hcmUI/req/1"),
                ("Manufacturing Jobs", "https://hctz.fa.us2.oraclecloud.com/hcmUI/req/2"),
                ("Germany Careers", "https://hctz.fa.us2.oraclecloud.com/hcmUI/req/3"),
                ("UK Jobs", "https://hctz.fa.us2.oraclecloud.com/hcmUI/req/4"),
            ],
        )
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.company, "ON Semiconductor")
        self.assertEqual(finding.rows_lead_to_host, "hctz.fa.us2.oraclecloud.com")
        self.assertTrue(finding.rows_lead_to.startswith("https://hctz.fa.us2.oraclecloud.com"))
        self.assertEqual(finding.rows_lead_to_count, 4)
        self.assertEqual(finding.taxonomy_share, 1.0)
        self.assertEqual(finding.distinct_off_host_hosts, 1)


class TestRowsLeadToPrefersListingLikePath(unittest.TestCase):
    def test_short_path_wins_over_a_more_frequent_job_detail_path(self) -> None:
        row = make_rows(
            company="AMX (Snap One)",
            careers_url="https://www.adiglobal.com/careers",
            board_rows=0,
            rows=[
                (
                    "Software Engineer Jobs",
                    "https://ehtl.fa.us6.oraclecloud.com/hcmUI/CandidateExperience/en/"
                    "sites/CX_2/requisitions/job/10293",
                ),
                (
                    "Manufacturing Jobs",
                    "https://ehtl.fa.us6.oraclecloud.com/hcmUI/CandidateExperience/en/"
                    "sites/CX_2/requisitions/job/10293",
                ),
                ("Careers", "https://ehtl.fa.us6.oraclecloud.com/jobs"),
            ],
        )
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.rows_lead_to, "https://ehtl.fa.us6.oraclecloud.com/jobs")
        self.assertEqual(finding.rows_lead_to_count, 3)

    def test_talent_community_style_single_row_is_still_reported_as_its_own_url(self) -> None:
        row = make_rows(
            company="Talent Pool Co",
            careers_url="https://www.talentpoolco.example.com/careers",
            board_rows=0,
            rows=[
                (
                    "Join our Talent Community Stay connected to new opportunities "
                    "and updates.",
                    "https://ehtl.fa.us6.oraclecloud.com/hcmUI/CandidateExperience/en/"
                    "sites/CX_2/join-talent-community",
                )
            ],
        )
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertTrue(finding.rows_lead_to.endswith("join-talent-community"))
        self.assertEqual(finding.rows_lead_to_count, 1)


class TestDistinctOffHostHosts(unittest.TestCase):
    def test_rows_scattered_across_several_hosts_are_counted(self) -> None:
        row = make_rows(
            company="Scattered Co",
            careers_url="https://www.scatteredco.example.com/careers",
            board_rows=0,
            rows=[
                ("Careers", "https://a.example.com/careers"),
                ("Jobs", "https://b.example.com/jobs"),
                ("Open Positions", "https://c.example.com/open"),
            ],
        )
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].distinct_off_host_hosts, 3)

    def test_rows_all_landing_on_one_host_are_counted_as_one(self) -> None:
        row = make_rows(
            company="Focused Co",
            careers_url="https://www.focusedco.example.com/careers",
            board_rows=0,
            rows=[
                ("Careers", "https://ats.example.com/careers/1"),
                ("Jobs", "https://ats.example.com/careers/2"),
            ],
        )
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].distinct_off_host_hosts, 1)


class TestEvaluateFlagsSingleCareersRow(unittest.TestCase):
    def test_hgc_engineering_style_single_careers_row_is_flagged(self) -> None:
        row = make_rows(
            company="HGC Engineering",
            careers_url="https://www.hgcengineering.com/careers",
            board_rows=0,
            rows=[("Careers", "https://www.hgcengineering.com/careers")],
        )
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].company, "HGC Engineering")

    def test_sivantos_group_style_single_careers_row_is_flagged(self) -> None:
        row = make_rows(
            company="Sivantos Group",
            careers_url="https://www.sivantos.com/careers",
            board_rows=0,
            rows=[("Careers", "https://www.sivantos.com/careers")],
        )
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].company, "Sivantos Group")


class TestEvaluateDoesNotFlagHealthyCompanies(unittest.TestCase):
    def test_real_job_titles_on_same_host_is_not_flagged(self) -> None:
        row = make_rows(
            company="Healthy Co",
            careers_url="https://healthyco.example.com/careers",
            board_rows=2,
            rows=[
                ("Audio DSP Engineer", "https://healthyco.example.com/jobs/1"),
                ("Firmware Engineer", "https://healthyco.example.com/jobs/2"),
                ("Production Planner", "https://healthyco.example.com/jobs/3"),
            ],
        )
        self.assertEqual(evaluate([row]), [])

    def test_off_host_real_job_titles_reaching_board_is_not_flagged(self) -> None:
        row = make_rows(
            company="ATS Hosted Co",
            careers_url="https://atshostedco.example.com/careers",
            board_rows=3,
            rows=[
                ("Audio DSP Engineer", "https://boards.greenhouse.io/atshostedco/1"),
                ("Firmware Engineer", "https://boards.greenhouse.io/atshostedco/2"),
                ("Production Planner", "https://boards.greenhouse.io/atshostedco/3"),
            ],
        )
        self.assertEqual(evaluate([row]), [])


class TestEvaluateSortOrder(unittest.TestCase):
    def test_native_scope_sorts_before_partial_scope(self) -> None:
        partial = make_rows(
            company_id=1,
            company="Partial Co",
            audio_scope="partial",
            rows=[("Careers", "https://partial.example.com/careers")],
        )
        native = make_rows(
            company_id=2,
            company="Native Co",
            audio_scope="native",
            rows=[("Careers", "https://native.example.com/careers")],
        )
        findings = evaluate([partial, native])
        self.assertEqual([f.company for f in findings], ["Native Co", "Partial Co"])

    def test_higher_taxonomy_share_sorts_first_within_the_same_scope(self) -> None:
        mostly_taxonomy = make_rows(
            company_id=1,
            company="Mostly Taxonomy",
            audio_scope="native",
            board_rows=0,
            rows=[
                ("Careers", "https://mt.example.com/careers"),
                ("Jobs", "https://mt.example.com/jobs"),
            ],
        )
        half_taxonomy = make_rows(
            company_id=2,
            company="Half Taxonomy",
            audio_scope="native",
            board_rows=0,
            rows=[
                ("Careers", "https://ht.example.com/careers"),
                ("Wild Card", "https://ht.example.com/wild"),
            ],
        )
        findings = evaluate([half_taxonomy, mostly_taxonomy])
        self.assertEqual([f.company for f in findings], ["Mostly Taxonomy", "Half Taxonomy"])


class TestSelectLandingPageCandidates(unittest.TestCase):
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
            careers_url=f"https://{name.lower().replace(' ', '')}.example.com/careers",
            verified=verified,
            audio_scope=audio_scope,
        )
        self.session.add(company)
        self.session.flush()
        return company

    def _log(self, company: Company, status: str, minutes_ago: int) -> None:
        started = self.now - timedelta(minutes=minutes_ago)
        self.session.add(
            ScrapeLog(
                company_id=company.id,
                started_at=started,
                finished_at=started,
                status=status,
                jobs_found=1,
                scrape_method="http",
            )
        )
        self.session.flush()

    def _job(
        self,
        company: Company,
        title: str,
        url: str,
        is_active: bool,
        is_audio_related: bool,
    ) -> None:
        self.session.add(
            Job(
                company_id=company.id,
                title=title,
                url=url,
                is_active=is_active,
                is_audio_related=is_audio_related,
            )
        )
        self.session.flush()

    def test_company_with_active_rows_is_included(self) -> None:
        company = self._company("Dear Reality")
        self._log(company, "success", 5)
        self._job(company, "Careers", "https://dearreality.example.com/careers", True, False)
        self._job(company, "Stale Row", "https://dearreality.example.com/old", False, True)
        rows = select_landing_page_candidates(self.session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].company, "Dear Reality")
        self.assertEqual(rows[0].rows, [("Careers", "https://dearreality.example.com/careers")])
        self.assertEqual(rows[0].board_rows, 0)

    def test_company_with_no_active_rows_is_excluded(self) -> None:
        company = self._company("Empty Co")
        self._log(company, "success", 5)
        rows = select_landing_page_candidates(self.session)
        self.assertEqual(rows, [])

    def test_unverified_company_is_excluded(self) -> None:
        company = self._company("Unverified Co", verified=False)
        self._log(company, "success", 5)
        self._job(company, "Careers", "https://unverified.example.com/careers", True, False)
        rows = select_landing_page_candidates(self.session)
        self.assertEqual(rows, [])

    def test_company_with_failed_latest_scrape_is_excluded(self) -> None:
        company = self._company("Failing Co")
        self._log(company, "failed", 5)
        self._job(company, "Careers", "https://failing.example.com/careers", True, False)
        rows = select_landing_page_candidates(self.session)
        self.assertEqual(rows, [])

    def test_board_rows_are_counted_and_active_only(self) -> None:
        company = self._company("Boarded Co")
        self._log(company, "success", 5)
        self._job(company, "Audio Engineer", "https://boarded.example.com/1", True, True)
        self._job(company, "Careers", "https://boarded.example.com/careers", True, False)
        self._job(company, "Stale Board Row", "https://boarded.example.com/2", False, True)
        rows = select_landing_page_candidates(self.session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].board_rows, 1)
        self.assertEqual(len(rows[0].rows), 2)


if __name__ == "__main__":
    unittest.main()
