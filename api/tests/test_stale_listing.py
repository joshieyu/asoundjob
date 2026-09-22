from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.config import STALE_AFTER_FAILURES
from api.query import company_health_rows
from api.routers.admin import admin_stats
from api.routers.categories import get_categories
from api.routers.companies import (
    get_company,
    list_companies,
    list_company_categories,
    list_open_applications,
)
from api.routers.countries import get_countries
from api.routers.jobs import list_jobs
from api.routers.search import search_jobs
from scraper.models import Base, Company, Job


def make_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_company(session: Session, name: str, **kwargs) -> Company:
    defaults = dict(
        slug=name.lower().replace(" ", "-"),
        category="Audio Software",
        verified=True,
        careers_url=f"https://{name.lower().replace(' ', '-')}.example/careers",
        source="auto",
        consecutive_failures=0,
    )
    defaults.update(kwargs)
    company = Company(name=name, **defaults)
    session.add(company)
    session.flush()
    return company


def add_job(session: Session, title: str, **kwargs) -> Job:
    defaults = dict(
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        is_active=True,
        is_audio_related=True,
        source="scraper",
        country="US",
        job_categories=["audio_software"],
    )
    defaults.update(kwargs)
    job = Job(title=title, **defaults)
    session.add(job)
    session.flush()
    return job


def endpoint_defaults(func) -> dict:
    import inspect

    values = {}
    for name, param in inspect.signature(func).parameters.items():
        if name == "db":
            continue
        default = param.default
        if default is inspect.Parameter.empty:
            continue
        values[name] = getattr(default, "default", default)
    return values


class TestStaleListingHiddenFromBoard(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.stale = add_company(
            self.session, "Ramboll Group", consecutive_failures=STALE_AFTER_FAILURES
        )
        self.stale_job = add_job(
            self.session, "Acoustic Consultant", company_id=self.stale.id
        )
        self.fine = add_company(
            self.session, "Fairphone", consecutive_failures=STALE_AFTER_FAILURES - 1
        )
        self.fine_job = add_job(
            self.session, "Hardware Audio Engineer", company_id=self.fine.id
        )

    def tearDown(self) -> None:
        self.session.close()

    def _list_jobs(self, **overrides):
        params = endpoint_defaults(list_jobs)
        params.update(overrides)
        return list_jobs(db=self.session, **params)

    def _search_jobs(self, q: str, **overrides):
        params = endpoint_defaults(search_jobs)
        params.pop("q", None)
        params.update(overrides)
        return search_jobs(q=q, db=self.session, **params)

    def test_stale_company_job_absent_from_list_jobs(self) -> None:
        result = self._list_jobs()
        titles = {item.title for item in result["items"]}
        self.assertNotIn("Acoustic Consultant", titles)
        self.assertIn("Hardware Audio Engineer", titles)

    def test_stale_company_job_absent_from_search(self) -> None:
        result = self._search_jobs("Acoustic")
        titles = {item.title for item in result["items"]}
        self.assertNotIn("Acoustic Consultant", titles)

    def test_below_threshold_job_present_in_search(self) -> None:
        result = self._search_jobs("Hardware")
        titles = {item.title for item in result["items"]}
        self.assertIn("Hardware Audio Engineer", titles)

    def test_stale_company_excluded_from_country_counts(self) -> None:
        result = get_countries(db=self.session)
        by_code = {c.code: c.job_count for c in result.countries}
        self.assertEqual(by_code.get("US", 0), 1)

    def test_stale_company_excluded_from_category_counts(self) -> None:
        result = get_categories(db=self.session)
        by_id = {c.id: c.job_count for c in result.categories}
        self.assertEqual(by_id.get("audio_software", 0), 1)

    def test_stale_company_excluded_from_directory_counts(self) -> None:
        result = list_companies(
            page=1, per_page=25, sort="board", direction="desc", db=self.session
        )
        by_slug = {item["slug"]: item for item in result["items"]}
        self.assertEqual(by_slug[self.stale.slug]["board_jobs_count"], 0)
        self.assertEqual(by_slug[self.stale.slug]["active_jobs_count"], 0)
        self.assertEqual(by_slug[self.fine.slug]["board_jobs_count"], 1)
        self.assertEqual(by_slug[self.fine.slug]["active_jobs_count"], 1)

    def test_stale_company_excluded_from_company_categories(self) -> None:
        result = list_company_categories(db=self.session)
        row = next(c for c in result.categories if c.name == "Audio Software")
        self.assertEqual(row.board_jobs_count, 1)

    def test_stale_company_excluded_from_open_applications(self) -> None:
        self.stale.open_application = True
        self.fine.open_application = True
        self.session.flush()
        result = list_open_applications(db=self.session)
        by_slug = {c.slug: c.open_roles for c in result.companies}
        self.assertEqual(by_slug[self.stale.slug], 0)
        self.assertEqual(by_slug[self.fine.slug], 1)

    def test_stale_company_detail_hides_the_job(self) -> None:
        result = get_company(self.stale.slug, db=self.session)
        self.assertEqual(result.active_jobs_count, 0)
        self.assertEqual(result.jobs, [])

    def test_fine_company_detail_still_shows_the_job(self) -> None:
        result = get_company(self.fine.slug, db=self.session)
        self.assertEqual(result.active_jobs_count, 1)
        self.assertEqual(len(result.jobs), 1)

    def test_community_job_at_stale_company_still_listed(self) -> None:
        add_job(
            self.session,
            "Community Sound Tech",
            company_id=self.stale.id,
            source="community",
        )
        result = self._list_jobs()
        titles = {item.title for item in result["items"]}
        self.assertIn("Community Sound Tech", titles)

    def test_override_true_at_stale_company_still_listed(self) -> None:
        add_job(
            self.session,
            "Pinned Visible Role",
            company_id=self.stale.id,
            is_active_override=True,
        )
        result = self._list_jobs()
        titles = {item.title for item in result["items"]}
        self.assertIn("Pinned Visible Role", titles)

    def test_job_with_no_company_still_listed(self) -> None:
        add_job(self.session, "Freelance Mix Engineer", company_id=None)
        result = self._list_jobs()
        titles = {item.title for item in result["items"]}
        self.assertIn("Freelance Mix Engineer", titles)

    def test_company_health_rows_flags_hidden_from_board(self) -> None:
        rows = company_health_rows(self.session)
        by_id = {r["company_id"]: r for r in rows}
        self.assertTrue(by_id[self.stale.id]["hidden_from_board"])
        self.assertFalse(by_id[self.fine.id]["hidden_from_board"])

    def test_admin_stats_still_counts_the_stale_job(self) -> None:
        result = admin_stats(db=self.session, _="tester")
        self.assertEqual(result.total_active_jobs, 2)
        self.assertEqual(result.audio_related_jobs, 2)


if __name__ == "__main__":
    unittest.main()
