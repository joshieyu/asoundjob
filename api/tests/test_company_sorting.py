from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.query import companies_with_counts
from scraper.models import Base, Company, Job


class TestCompanySorting(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        plan = [
            ("Delta Audio", True, 5, 5),
            ("Alpha Sound", False, 12, 0),
            ("Charlie Labs", True, 0, 0),
            ("Bravo Acoustics", False, 3, 2),
        ]
        for name, verified, jobs, on_board in plan:
            company = Company(
                name=name,
                slug=name.lower().replace(" ", "-"),
                category="Audio Software",
                verified=verified,
            )
            self.session.add(company)
            self.session.flush()
            for n in range(jobs):
                self.session.add(
                    Job(
                        company_id=company.id,
                        title=f"{name} role {n}",
                        url=f"https://example.com/{company.slug}/{n}",
                        is_active=True,
                        is_audio_related=n < on_board,
                        source="scraper",
                    )
                )
        self.session.add(
            Job(
                company_id=self.session.execute(
                    select(Company).where(Company.name == "Charlie Labs")
                ).scalar_one().id,
                title="expired",
                url="https://example.com/charlie-labs/old",
                is_active=False,
                is_audio_related=True,
                source="scraper",
            )
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def _names(self, **kwargs) -> list:
        items, _ = companies_with_counts(self.session, select(Company), 1, 50, **kwargs)
        return [i["name"] for i in items]

    def _counts(self, **kwargs) -> list:
        items, _ = companies_with_counts(self.session, select(Company), 1, 50, **kwargs)
        return [i["active_jobs_count"] for i in items]

    def test_default_is_name_ascending(self) -> None:
        self.assertEqual(
            self._names(),
            ["Alpha Sound", "Bravo Acoustics", "Charlie Labs", "Delta Audio"],
        )

    def test_name_descending(self) -> None:
        self.assertEqual(
            self._names(sort="name", direction="desc"),
            ["Delta Audio", "Charlie Labs", "Bravo Acoustics", "Alpha Sound"],
        )

    def test_jobs_descending(self) -> None:
        self.assertEqual(self._counts(sort="jobs", direction="desc"), [12, 5, 3, 0])

    def test_jobs_ascending(self) -> None:
        self.assertEqual(self._counts(sort="jobs", direction="asc"), [0, 3, 5, 12])

    def test_a_company_with_no_jobs_sorts_as_zero_not_missing(self) -> None:
        names = self._names(sort="jobs", direction="asc")
        self.assertEqual(names[0], "Charlie Labs")
        self.assertEqual(len(names), 4)

    def test_inactive_jobs_are_not_counted(self) -> None:
        items, _ = companies_with_counts(self.session, select(Company), 1, 50)
        charlie = next(i for i in items if i["name"] == "Charlie Labs")
        self.assertEqual(charlie["active_jobs_count"], 0)

    def _board(self, **kwargs) -> list:
        items, _ = companies_with_counts(self.session, select(Company), 1, 50, **kwargs)
        return [i["board_jobs_count"] for i in items]

    def test_board_count_excludes_rows_that_never_reach_the_board(self) -> None:
        items, _ = companies_with_counts(self.session, select(Company), 1, 50)
        alpha = next(i for i in items if i["name"] == "Alpha Sound")
        self.assertEqual(alpha["active_jobs_count"], 12)
        self.assertEqual(alpha["board_jobs_count"], 0)

    def test_board_count_is_a_subset_of_the_active_count(self) -> None:
        items, _ = companies_with_counts(self.session, select(Company), 1, 50)
        for item in items:
            self.assertLessEqual(item["board_jobs_count"], item["active_jobs_count"])

    def test_board_descending(self) -> None:
        self.assertEqual(self._board(sort="board", direction="desc"), [5, 2, 0, 0])

    def test_board_ascending(self) -> None:
        self.assertEqual(self._board(sort="board", direction="asc"), [0, 0, 2, 5])

    def test_board_and_jobs_are_different_orders(self) -> None:
        self.assertNotEqual(
            self._names(sort="board", direction="desc"),
            self._names(sort="jobs", direction="desc"),
        )

    def test_the_biggest_scraper_can_have_an_empty_board(self) -> None:
        by_jobs = self._names(sort="jobs", direction="desc")
        self.assertEqual(by_jobs[0], "Alpha Sound")
        items, _ = companies_with_counts(self.session, select(Company), 1, 50)
        alpha = next(i for i in items if i["name"] == "Alpha Sound")
        self.assertEqual(alpha["board_jobs_count"], 0)

    def test_an_inactive_audio_row_is_not_counted_on_the_board(self) -> None:
        delta = self.session.execute(
            select(Company).where(Company.name == "Delta Audio")
        ).scalar_one()
        self.session.add(
            Job(
                company_id=delta.id,
                title="Retired audio role",
                url="https://example.com/delta-audio/retired",
                is_active=False,
                is_audio_related=True,
                source="scraper",
            )
        )
        self.session.flush()
        items, _ = companies_with_counts(self.session, select(Company), 1, 50)
        row = next(i for i in items if i["name"] == "Delta Audio")
        self.assertEqual(row["board_jobs_count"], 5)

    def test_verified_descending_puts_verified_first(self) -> None:
        items, _ = companies_with_counts(
            self.session, select(Company), 1, 50, sort="verified", direction="desc"
        )
        self.assertEqual([i["verified"] for i in items], [True, True, False, False])

    def test_verified_ascending_puts_unverified_first(self) -> None:
        items, _ = companies_with_counts(
            self.session, select(Company), 1, 50, sort="verified", direction="asc"
        )
        self.assertEqual([i["verified"] for i in items], [False, False, True, True])

    def test_ties_fall_back_to_name(self) -> None:
        self.assertEqual(
            self._names(sort="verified", direction="desc"),
            ["Charlie Labs", "Delta Audio", "Alpha Sound", "Bravo Acoustics"],
        )

    def test_an_unknown_sort_falls_back_to_name(self) -> None:
        self.assertEqual(self._names(sort="dropping tables"), self._names())

    def test_an_unknown_direction_falls_back_to_ascending(self) -> None:
        self.assertEqual(self._names(sort="jobs", direction="sideways"),
                         self._names(sort="jobs", direction="asc"))

    def test_sorting_is_stable_across_pages(self) -> None:
        first, total = companies_with_counts(
            self.session, select(Company), 1, 2, sort="jobs", direction="desc"
        )
        second, _ = companies_with_counts(
            self.session, select(Company), 2, 2, sort="jobs", direction="desc"
        )
        self.assertEqual(total, 4)
        self.assertEqual(
            [i["active_jobs_count"] for i in first + second], [12, 5, 3, 0]
        )


class TestAdminSortValidation(unittest.TestCase):
    def _param(self, name: str):
        import inspect

        from api.routers.admin import admin_list_companies

        return inspect.signature(admin_list_companies).parameters[name].default

    def _pattern(self, name: str) -> str:
        param = self._param(name)
        return next(
            entry.pattern
            for entry in param.metadata
            if getattr(entry, "pattern", None)
        )

    def test_sort_is_constrained_at_the_route(self) -> None:
        self.assertEqual(self._pattern("sort"), "^(name|jobs|board|verified)$")

    def test_direction_is_constrained_at_the_route(self) -> None:
        self.assertEqual(self._pattern("direction"), "^(asc|desc)$")

    def test_every_supported_sort_is_allowed_by_the_route_pattern(self) -> None:
        import re

        from api.query import COMPANY_SORTS, SORT_DIRECTIONS

        sort_pattern = re.compile(self._pattern("sort"))
        for value in COMPANY_SORTS:
            self.assertTrue(sort_pattern.match(value), value)
        direction_pattern = re.compile(self._pattern("direction"))
        for value in SORT_DIRECTIONS:
            self.assertTrue(direction_pattern.match(value), value)

    def test_the_route_defaults_match_the_query_defaults(self) -> None:
        self.assertEqual(self._param("sort").default, "name")
        self.assertEqual(self._param("direction").default, "asc")


if __name__ == "__main__":
    unittest.main()
