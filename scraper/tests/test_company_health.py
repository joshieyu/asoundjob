from __future__ import annotations

import unittest

from scraper.company_health import (
    DESCRIPTION_MIN_CHARS,
    FURNITURE_MAX_ROLE_SHARE,
    FURNITURE_MIN_ROWS,
    GRADE_ORDER,
    grade_company,
    grade_rank,
    is_described,
    looks_like_role,
    shape_shares,
)


class TestGradeCompany(unittest.TestCase):
    def test_failed_scrape_wins_even_with_good_rows_and_board(self) -> None:
        self.assertEqual(
            grade_company(
                active_rows=20,
                described_share=0.9,
                role_share=0.9,
                board_count=5,
                last_scrape_status="failed",
            ),
            "failing",
        )

    def test_nav_furniture(self) -> None:
        self.assertEqual(
            grade_company(
                active_rows=6,
                described_share=0.0,
                role_share=0.0,
                board_count=1,
                last_scrape_status="success",
            ),
            "furniture",
        )

    def test_titles_fine_but_ten_percent_described_is_thin(self) -> None:
        self.assertEqual(
            grade_company(
                active_rows=10,
                described_share=0.1,
                role_share=1.0,
                board_count=2,
                last_scrape_status="success",
            ),
            "thin",
        )

    def test_clean_company_with_no_board_presence_is_idle(self) -> None:
        self.assertEqual(
            grade_company(
                active_rows=5,
                described_share=1.0,
                role_share=1.0,
                board_count=0,
                last_scrape_status="success",
            ),
            "idle",
        )

    def test_described_with_board_job_is_healthy(self) -> None:
        self.assertEqual(
            grade_company(
                active_rows=5,
                described_share=1.0,
                role_share=1.0,
                board_count=1,
                last_scrape_status="success",
            ),
            "healthy",
        )

    def test_furniture_does_not_trigger_below_min_rows(self) -> None:
        self.assertLess(2, FURNITURE_MIN_ROWS)
        grade = grade_company(
            active_rows=2,
            described_share=0.0,
            role_share=0.0,
            board_count=0,
            last_scrape_status="success",
        )
        self.assertNotEqual(grade, "furniture")

    def test_thin_does_not_trigger_below_min_rows(self) -> None:
        grade = grade_company(
            active_rows=2,
            described_share=0.1,
            role_share=1.0,
            board_count=1,
            last_scrape_status="success",
        )
        self.assertNotEqual(grade, "thin")

    def test_role_share_at_thirty_percent_is_not_furniture(self) -> None:
        self.assertGreaterEqual(0.30, FURNITURE_MAX_ROLE_SHARE)
        grade = grade_company(
            active_rows=10,
            described_share=0.0,
            role_share=0.30,
            board_count=1,
            last_scrape_status="success",
        )
        self.assertNotEqual(grade, "furniture")

    def test_role_share_at_ten_percent_is_furniture(self) -> None:
        self.assertLess(0.10, FURNITURE_MAX_ROLE_SHARE)
        grade = grade_company(
            active_rows=10,
            described_share=0.0,
            role_share=0.10,
            board_count=1,
            last_scrape_status="success",
        )
        self.assertEqual(grade, "furniture")


class TestLooksLikeRole(unittest.TestCase):
    def test_accepts_french_engineer_title(self) -> None:
        self.assertTrue(looks_like_role("Ingénieur Electronique R&D"))

    def test_accepts_german_compound_acoustics_engineer_title(self) -> None:
        self.assertTrue(looks_like_role("Akustik-Ingenieur"))

    def test_accepts_french_supply_chain_manager_title(self) -> None:
        self.assertTrue(looks_like_role("Responsable Supply Chain"))

    def test_accepts_german_purchasing_technician_title(self) -> None:
        self.assertTrue(
            looks_like_role("Technischer Einkäufer IT & Telekommunikation")
        )

    def test_accepts_hr_generalist_title(self) -> None:
        self.assertTrue(looks_like_role("HR generalist"))

    def test_rejects_view_jobs_nav_phrase(self) -> None:
        self.assertFalse(looks_like_role("View Jobs"))

    def test_rejects_current_openings_nav_phrase(self) -> None:
        self.assertFalse(looks_like_role("Current Openings"))

    def test_rejects_open_roles_count_phrase(self) -> None:
        self.assertFalse(looks_like_role("342 open roles"))

    def test_rejects_corporate_functions_nav_phrase(self) -> None:
        self.assertFalse(looks_like_role("Corporate Functions"))


class TestShapeShares(unittest.TestCase):
    def test_empty_list_returns_zero_zero(self) -> None:
        self.assertEqual(shape_shares([], []), (0.0, 0.0))

    def test_all_job_shaped_and_described(self) -> None:
        titles = ["Senior Audio Engineer", "DSP Software Developer"]
        described = [True, True]
        self.assertEqual(shape_shares(titles, described), (1.0, 1.0))

    def test_mixed_shares_are_rounded_to_two_places(self) -> None:
        titles = ["Careers", "Jobs", "Audio Engineer"]
        described = [False, False, True]
        described_share, role_share = shape_shares(titles, described)
        self.assertEqual(described_share, round(1 / 3, 2))
        self.assertEqual(role_share, round(1 / 3, 2))

    def test_international_role_nouns_count_toward_role_share(self) -> None:
        titles = ["Ingénieur Méthodes Industrialisation", "Careers"]
        described = [False, False]
        described_share, role_share = shape_shares(titles, described)
        self.assertEqual(described_share, 0.0)
        self.assertEqual(role_share, round(1 / 2, 2))


class TestIsDescribed(unittest.TestCase):
    def test_none_is_not_described(self) -> None:
        self.assertFalse(is_described(None))

    def test_whitespace_only_is_not_described(self) -> None:
        self.assertFalse(is_described("   \n\t  "))

    def test_exactly_at_boundary_is_described(self) -> None:
        text = "a" * DESCRIPTION_MIN_CHARS
        self.assertTrue(is_described(text))

    def test_one_under_boundary_is_not_described(self) -> None:
        text = "a" * (DESCRIPTION_MIN_CHARS - 1)
        self.assertFalse(is_described(text))

    def test_boundary_counts_stripped_length(self) -> None:
        text = "  " + ("a" * DESCRIPTION_MIN_CHARS) + "  "
        self.assertTrue(is_described(text))


class TestGradeRank(unittest.TestCase):
    def test_orders_worst_first(self) -> None:
        ranks = [grade_rank(grade) for grade in GRADE_ORDER]
        self.assertEqual(ranks, sorted(ranks))

    def test_failing_is_worse_than_healthy(self) -> None:
        self.assertLess(grade_rank("failing"), grade_rank("healthy"))

    def test_unknown_grade_sorts_last(self) -> None:
        worst_known = max(grade_rank(grade) for grade in GRADE_ORDER)
        self.assertGreater(grade_rank("bogus"), worst_known)


if __name__ == "__main__":
    unittest.main()
