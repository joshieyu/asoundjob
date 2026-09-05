from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scraper.detect_nonjob_rows import (
    CompanyTitleRows,
    classify_title,
    evaluate,
    render,
    select_nonjob_candidates,
)
from scraper.models import Base, Company, Job, ScrapeLog


def make_rows(**overrides) -> CompanyTitleRows:
    kwargs = dict(
        company_id=1,
        company="Dear Reality",
        audio_scope="native",
        careers_url="https://dearreality.example.com/careers",
        titles=["Careers"],
    )
    kwargs.update(overrides)
    return CompanyTitleRows(**kwargs)


class TestClassifyTitleNavigation(unittest.TestCase):
    def test_careers_is_navigation(self) -> None:
        self.assertEqual(classify_title("Careers"), "navigation")

    def test_careers_home_is_navigation(self) -> None:
        self.assertEqual(classify_title("Careers Home"), "navigation")

    def test_browse_careers_all_caps_is_navigation(self) -> None:
        self.assertEqual(classify_title("BROWSE CAREERS"), "navigation")

    def test_jobs_is_navigation(self) -> None:
        self.assertEqual(classify_title("Jobs"), "navigation")

    def test_jobs_ampersand_career_is_navigation(self) -> None:
        self.assertEqual(classify_title("Jobs & Career"), "navigation")

    def test_job_is_navigation(self) -> None:
        self.assertEqual(classify_title("Job"), "navigation")

    def test_employment_is_navigation(self) -> None:
        self.assertEqual(classify_title("Employment"), "navigation")

    def test_available_positions_is_navigation(self) -> None:
        self.assertEqual(classify_title("Available Positions"), "navigation")

    def test_see_open_positions_is_navigation(self) -> None:
        self.assertEqual(classify_title("See open positions"), "navigation")

    def test_open_positions_is_navigation(self) -> None:
        self.assertEqual(classify_title("Open Positions"), "navigation")

    def test_explore_all_job_openings_is_navigation(self) -> None:
        self.assertEqual(classify_title("Explore all job openings"), "navigation")

    def test_search_job_is_navigation(self) -> None:
        self.assertEqual(classify_title("Search Job"), "navigation")

    def test_show_all_is_navigation(self) -> None:
        self.assertEqual(classify_title("Show all"), "navigation")

    def test_view_details_is_navigation(self) -> None:
        self.assertEqual(classify_title("View details"), "navigation")

    def test_plus_view_details_is_navigation(self) -> None:
        self.assertEqual(classify_title("+ View details"), "navigation")

    def test_find_out_more_is_navigation(self) -> None:
        self.assertEqual(classify_title("Find out more"), "navigation")

    def test_click_here_to_see_career_opportunities_is_navigation(self) -> None:
        self.assertEqual(
            classify_title("Click here to see career opportunities"), "navigation"
        )

    def test_wanna_join_us_is_navigation(self) -> None:
        self.assertEqual(classify_title("Wanna join us?"), "navigation")

    def test_our_programs_is_navigation(self) -> None:
        self.assertEqual(classify_title("Our Programs"), "navigation")

    def test_early_careers_is_navigation(self) -> None:
        self.assertEqual(classify_title("Early Careers"), "navigation")

    def test_early_career_programs_all_caps_is_navigation(self) -> None:
        self.assertEqual(classify_title("EARLY CAREER PROGRAMS"), "navigation")

    def test_students_and_graduates_is_navigation(self) -> None:
        self.assertEqual(classify_title("Students & Graduates"), "navigation")

    def test_international_opportunities_is_navigation(self) -> None:
        self.assertEqual(classify_title("International Opportunities"), "navigation")

    def test_job_subscription_is_navigation(self) -> None:
        self.assertEqual(classify_title("Job subscription"), "navigation")

    def test_working_at_ubisoft_is_navigation(self) -> None:
        self.assertEqual(classify_title("Working at Ubisoft"), "navigation")

    def test_preferences_is_navigation(self) -> None:
        self.assertEqual(classify_title("Preferences"), "navigation")

    def test_alfred_jobs_is_navigation(self) -> None:
        self.assertEqual(classify_title("Alfred jobs"), "navigation")

    def test_pdf_employment_application_is_navigation(self) -> None:
        self.assertEqual(classify_title("PDF employment application"), "navigation")

    def test_jobs_and_careers_is_navigation(self) -> None:
        self.assertEqual(classify_title("Jobs & careers"), "navigation")


class TestClassifyTitleBoilerplate(unittest.TestCase):
    def test_equal_employment_opportunity_policy_is_boilerplate(self) -> None:
        self.assertEqual(
            classify_title("Equal Employment Opportunity Policy"), "boilerplate"
        )

    def test_anti_fraud_hiring_policies_is_boilerplate(self) -> None:
        self.assertEqual(classify_title("Anti-Fraud Hiring Policies"), "boilerplate")

    def test_diversity_and_inclusion_policy_is_boilerplate(self) -> None:
        self.assertEqual(
            classify_title("Our diversity and inclusion policy"), "boilerplate"
        )

    def test_screen_reader_notice_is_boilerplate(self) -> None:
        self.assertEqual(
            classify_title("Screen readers cannot read the following searchable map."),
            "boilerplate",
        )

    def test_opens_in_a_new_tab_is_boilerplate(self) -> None:
        self.assertEqual(classify_title("Opens in a new tab."), "boilerplate")

    def test_hitachi_press_release_headline_is_boilerplate(self) -> None:
        self.assertEqual(
            classify_title(
                "The People of Hitachi: Developing Simulation Software to Free "
                "Society from Flooding"
            ),
            "boilerplate",
        )

    def test_kopn_transmitter_headline_is_unclear_not_boilerplate(self) -> None:
        title = "KOPN Community Radio Upgrades to BE's STX 10 Transmitter"
        self.assertEqual(len(title), 56)
        self.assertFalse(title.endswith("."))
        self.assertEqual(classify_title(title), "unclear")


class TestClassifyTitleUnreviewable(unittest.TestCase):
    def test_japanese_word_is_unreviewable(self) -> None:
        self.assertEqual(classify_title("日本語"), "unreviewable")

    def test_japanese_job_title_is_unreviewable(self) -> None:
        self.assertEqual(classify_title("中途採用（スタッフ系）"), "unreviewable")


class TestClassifyTitleRealJobsAreNotJunk(unittest.TestCase):
    def test_product_lead_deepfake_detection_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title(
            "Product Lead, Deepfake Detection Onsite (Mountain View, CA)"
        )
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_special_processes_fitter_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("Special Processes Fitter")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_director_product_management_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("Director, Product Management")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_talent_development_manager_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("Talent Development Manager")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_production_planner_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("PRODUCTION PLANNER")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_audiologist_molu_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("Audiologist MOLU")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_engineer_principal_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("Engineer, Principal")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_real_time_embedded_engineer_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("Real - Time Embedded Engineer")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_stage_automation_and_performance_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("STAGE - Automation & Performance")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_wild_card_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("Wild Card")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_audio_dsp_engineering_intern_is_not_navigation_or_boilerplate(self) -> None:
        result = classify_title("Audio DSP Engineering Intern")
        self.assertNotIn(result, ("navigation", "boilerplate"))

    def test_stage_automation_and_performance_is_unclear(self) -> None:
        self.assertEqual(classify_title("STAGE - Automation & Performance"), "unclear")

    def test_wild_card_is_unclear(self) -> None:
        self.assertEqual(classify_title("Wild Card"), "unclear")


class TestEvaluateFlagging(unittest.TestCase):
    def test_company_with_only_job_shaped_rows_is_not_flagged(self) -> None:
        row = make_rows(
            titles=["Audio DSP Engineer", "Special Processes Fitter", "PRODUCTION PLANNER"]
        )
        self.assertEqual(evaluate([row]), [])

    def test_company_with_one_navigation_row_among_ten_job_rows_is_flagged(self) -> None:
        titles = [f"Audio Engineer {n}" for n in range(10)] + ["Careers"]
        row = make_rows(titles=titles)
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].navigation, 1)
        self.assertEqual(findings[0].job_shaped, 10)
        self.assertEqual(findings[0].total_rows, 11)

    def test_company_with_only_boilerplate_row_is_flagged(self) -> None:
        row = make_rows(titles=["Equal Employment Opportunity Policy"])
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].boilerplate, 1)

    def test_company_with_no_job_shaped_row_is_flagged_on_the_weaker_tier(self) -> None:
        row = make_rows(titles=["Wild Card", "STAGE - Automation & Performance"])
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].reason, "no_job_shaped_row")
        self.assertEqual(findings[0].navigation, 0)
        self.assertEqual(findings[0].boilerplate, 0)

    def test_a_single_job_shaped_row_keeps_a_clean_company_unflagged(self) -> None:
        row = make_rows(titles=["Wild Card", "Audio Systems Engineer"])
        self.assertEqual(evaluate([row]), [])

    def test_chrome_rows_takes_precedence_over_the_weaker_tier(self) -> None:
        row = make_rows(titles=["Careers", "Wild Card"])
        findings = evaluate([row])
        self.assertEqual(findings[0].reason, "chrome_rows")

    def test_a_press_release_headline_alone_is_caught_by_the_weaker_tier(self) -> None:
        row = make_rows(titles=["KOPN Community Radio Upgrades to BE's STX 10 Transmitter"])
        findings = evaluate([row])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].reason, "no_job_shaped_row")

    def test_a_product_menu_is_caught_by_the_weaker_tier(self) -> None:
        row = make_rows(titles=["AC Power", "Cables", "Car Chargers"])
        findings = evaluate([row])
        self.assertEqual(findings[0].reason, "no_job_shaped_row")


class TestEvaluateSortOrder(unittest.TestCase):
    def test_native_scope_sorts_before_partial_scope(self) -> None:
        partial = make_rows(
            company_id=1, company="Partial Co", audio_scope="partial", titles=["Careers"]
        )
        native = make_rows(
            company_id=2, company="Native Co", audio_scope="native", titles=["Careers"]
        )
        findings = evaluate([partial, native])
        self.assertEqual([f.company for f in findings], ["Native Co", "Partial Co"])

    def test_higher_junk_share_sorts_first_within_the_same_scope(self) -> None:
        mostly_junk = make_rows(
            company_id=1,
            company="Mostly Junk",
            audio_scope="native",
            titles=["Careers", "Show all", "Audio Engineer"],
        )
        mostly_clean = make_rows(
            company_id=2,
            company="Mostly Clean",
            audio_scope="native",
            titles=["Careers"] + [f"Audio Engineer {n}" for n in range(9)],
        )
        findings = evaluate([mostly_clean, mostly_junk])
        self.assertEqual([f.company for f in findings], ["Mostly Junk", "Mostly Clean"])

    def test_fewer_total_rows_sorts_first_at_equal_junk_share(self) -> None:
        small = make_rows(
            company_id=1, company="Small Co", audio_scope="native", titles=["Careers"]
        )
        large = make_rows(
            company_id=2,
            company="Large Co",
            audio_scope="native",
            titles=["Careers"] * 4,
        )
        findings = evaluate([large, small])
        self.assertEqual([f.company for f in findings], ["Small Co", "Large Co"])


class TestRenderTitleCap(unittest.TestCase):
    def test_titles_beyond_the_cap_render_as_and_n_more(self) -> None:
        titles = [f"Audio Engineer {n}" for n in range(11)] + ["Careers"]
        row = make_rows(titles=titles)
        findings = evaluate([row])
        report = render(findings)
        self.assertIn("... and 4 more", report)
        self.assertEqual(report.count("Audio Engineer"), 8)


class TestSelectNonjobCandidates(unittest.TestCase):
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

    def _job(self, company: Company, title: str, is_active: bool, is_audio_related: bool) -> None:
        self.session.add(
            Job(
                company_id=company.id,
                title=title,
                url=f"https://example.com/jobs/{company.id}/{title}",
                is_active=is_active,
                is_audio_related=is_audio_related,
            )
        )
        self.session.flush()

    def test_company_with_board_rows_is_excluded(self) -> None:
        company = self._company("Boarded Co")
        self._log(company, "success", 5)
        self._job(company, "Careers", is_active=True, is_audio_related=False)
        self._job(company, "Audio Engineer", is_active=True, is_audio_related=True)
        rows = select_nonjob_candidates(self.session)
        self.assertEqual(rows, [])

    def test_company_with_failed_latest_scrape_is_excluded(self) -> None:
        company = self._company("Failing Co")
        self._log(company, "failed", 5)
        self._job(company, "Careers", is_active=True, is_audio_related=False)
        rows = select_nonjob_candidates(self.session)
        self.assertEqual(rows, [])

    def test_unverified_company_is_excluded(self) -> None:
        company = self._company("Unverified Co", verified=False)
        self._log(company, "success", 5)
        self._job(company, "Careers", is_active=True, is_audio_related=False)
        rows = select_nonjob_candidates(self.session)
        self.assertEqual(rows, [])

    def test_zero_board_company_with_active_rows_is_included(self) -> None:
        company = self._company("Dear Reality")
        self._log(company, "success", 5)
        self._job(company, "Careers", is_active=True, is_audio_related=False)
        self._job(company, "Show all", is_active=True, is_audio_related=False)
        self._job(company, "Stale Row", is_active=False, is_audio_related=True)
        rows = select_nonjob_candidates(self.session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].company, "Dear Reality")
        self.assertEqual(sorted(rows[0].titles), ["Careers", "Show all"])

    def test_company_with_no_active_rows_at_all_is_excluded(self) -> None:
        company = self._company("Empty Co")
        self._log(company, "success", 5)
        rows = select_nonjob_candidates(self.session)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
