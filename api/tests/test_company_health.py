from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from api.routers import admin as admin_router
from scraper.models import Base, Company, Job, ScrapeLog

NOW = datetime.now(timezone.utc)


def make_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_company(session: Session, name: str, **kwargs) -> Company:
    defaults = dict(
        slug=name.lower().replace(" ", "-"),
        category="Audio Software",
        verified=True,
        careers_url="https://example.com/careers",
    )
    defaults.update(kwargs)
    company = Company(name=name, **defaults)
    session.add(company)
    session.flush()
    return company


def add_job(session: Session, company: Company, title: str, **kwargs) -> Job:
    job = Job(
        company_id=company.id,
        title=title,
        url=f"https://example.com/{company.slug}/{title}",
        is_active=kwargs.pop("is_active", True),
        is_audio_related=kwargs.pop("is_audio_related", False),
        source="scraper",
        **kwargs,
    )
    session.add(job)
    session.flush()
    return job


def health(session: Session, **kwargs):
    params = dict(
        grade=None,
        q=None,
        page=1,
        per_page=50,
        sort="grade",
        direction="desc",
        db=session,
        _="tester",
    )
    params.update(kwargs)
    return admin_router.admin_company_health(**params)


class TestFurnitureGrade(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.close()

    def test_nav_chrome_titles_with_no_descriptions_grade_furniture(self) -> None:
        company = add_company(self.session, "Sennheiser Clone")
        for title in [
            "Corporate Functions",
            "Products & Marketing",
            "Sales & Service",
            "Jobs & Careers | Sennheiser",
        ]:
            add_job(self.session, company, title, is_audio_related=True)
        result = health(self.session)
        row = next(r for r in result.items if r.company_id == company.id)
        self.assertEqual(row.grade, "furniture")
        self.assertEqual(row.described_share, 0.0)
        self.assertLess(row.role_share, 0.25)


class TestFailingGrade(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.close()

    def test_failed_latest_scrape_grades_failing_even_with_good_rows(self) -> None:
        company = add_company(self.session, "Good Rows Bad Scrape")
        add_job(
            self.session,
            company,
            "Senior DSP Engineer",
            description="A" * 250,
            is_audio_related=True,
        )
        self.session.add(
            ScrapeLog(company_id=company.id, status="failed", started_at=NOW)
        )
        self.session.flush()
        result = health(self.session)
        row = next(r for r in result.items if r.company_id == company.id)
        self.assertEqual(row.last_scrape_status, "failed")
        self.assertEqual(row.grade, "failing")


class TestHealthyGrade(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.close()

    def test_real_descriptions_and_board_job_grade_healthy(self) -> None:
        company = add_company(self.session, "Real Audio Co")
        add_job(
            self.session,
            company,
            "Senior DSP Engineer",
            description="A detailed and genuine job description. " * 10,
            is_audio_related=True,
        )
        self.session.add(
            ScrapeLog(company_id=company.id, status="success", started_at=NOW)
        )
        self.session.flush()
        result = health(self.session)
        row = next(r for r in result.items if r.company_id == company.id)
        self.assertEqual(row.grade, "healthy")
        self.assertGreaterEqual(row.described_share, 0.2)
        self.assertGreater(row.board_count, 0)


class TestIdleGrade(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.close()

    def test_clean_company_with_zero_audio_jobs_grades_idle(self) -> None:
        company = add_company(self.session, "Empty Board Co")
        add_job(
            self.session,
            company,
            "Office Manager",
            description="A detailed and genuine job description. " * 10,
            is_audio_related=False,
        )
        result = health(self.session)
        row = next(r for r in result.items if r.company_id == company.id)
        self.assertEqual(row.active_rows, 1)
        self.assertEqual(row.board_count, 0)
        self.assertEqual(row.grade, "idle")


class TestUnscrapedGrade(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.close()

    def test_unverified_company_grades_unscraped_and_reports_scraped_false(self) -> None:
        company = add_company(self.session, "Not Yet Verified Co", verified=False)
        result = health(self.session)
        row = next(r for r in result.items if r.company_id == company.id)
        self.assertEqual(row.grade, "unscraped")
        self.assertFalse(row.scraped)


class TestSilentGrade(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.close()

    def test_scraped_company_with_no_rows_grades_silent(self) -> None:
        company = add_company(self.session, "Nothing Found Co")
        self.session.add(
            ScrapeLog(company_id=company.id, status="success", started_at=NOW)
        )
        self.session.flush()
        result = health(self.session)
        row = next(r for r in result.items if r.company_id == company.id)
        self.assertEqual(row.active_rows, 0)
        self.assertEqual(row.grade, "silent")
        self.assertTrue(row.scraped)


class TestNewGradeFilters(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.silent = add_company(self.session, "Silent Co")
        self.unscraped = add_company(self.session, "Unscraped Co", verified=False)

    def tearDown(self) -> None:
        self.session.close()

    def test_grade_filter_accepts_silent(self) -> None:
        result = health(self.session, grade="silent")
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].company_id, self.silent.id)

    def test_grade_filter_accepts_unscraped(self) -> None:
        result = health(self.session, grade="unscraped")
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].company_id, self.unscraped.id)

    def test_summary_dict_contains_all_seven_grades(self) -> None:
        result = health(self.session)
        summary_fields = set(result.summary.model_dump().keys())
        self.assertEqual(
            summary_fields,
            {"failing", "silent", "furniture", "thin", "idle", "healthy", "unscraped"},
        )


class TestConsecutiveFailures(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.close()

    def test_counts_trailing_failures_and_stops_at_success(self) -> None:
        company = add_company(self.session, "Flaky Scraper Co")
        base = NOW - timedelta(days=10)
        statuses = ["success", "failed", "failed", "failed"]
        for offset, status in enumerate(statuses):
            self.session.add(
                ScrapeLog(
                    company_id=company.id,
                    status=status,
                    started_at=base + timedelta(days=offset),
                )
            )
        self.session.flush()
        result = health(self.session)
        row = next(r for r in result.items if r.company_id == company.id)
        self.assertEqual(row.last_scrape_status, "failed")
        self.assertEqual(row.consecutive_failures, 3)


class TestGradeFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.furniture = add_company(self.session, "Furniture Co")
        for title in ["Corporate Functions", "Products & Marketing", "Sales & Service"]:
            add_job(self.session, self.furniture, title, is_audio_related=True)
        self.healthy = add_company(self.session, "Healthy Co")
        add_job(
            self.session,
            self.healthy,
            "Senior DSP Engineer",
            description="A detailed and genuine job description. " * 10,
            is_audio_related=True,
        )

    def tearDown(self) -> None:
        self.session.close()

    def test_grade_filter_narrows_to_matching_companies(self) -> None:
        result = health(self.session, grade="furniture")
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].company_id, self.furniture.id)

    def test_grade_filter_excludes_other_grades(self) -> None:
        result = health(self.session, grade="healthy")
        self.assertEqual(result.total, 1)
        self.assertEqual(result.items[0].company_id, self.healthy.id)


class TestSummary(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.furniture = add_company(self.session, "Furniture Co")
        for title in ["Corporate Functions", "Products & Marketing", "Sales & Service"]:
            add_job(self.session, self.furniture, title, is_audio_related=True)
        self.healthy_a = add_company(self.session, "Healthy Co A")
        self.healthy_b = add_company(self.session, "Healthy Co B")
        for company in (self.healthy_a, self.healthy_b):
            add_job(
                self.session,
                company,
                "Senior DSP Engineer",
                description="A detailed and genuine job description. " * 10,
                is_audio_related=True,
            )
        self.idle = add_company(self.session, "Idle Co")
        add_job(self.session, self.idle, "Office Manager", is_audio_related=False)

    def tearDown(self) -> None:
        self.session.close()

    def test_summary_counts_the_whole_filtered_set_not_just_the_page(self) -> None:
        result = health(self.session, per_page=1, page=1)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.total, 4)
        self.assertEqual(result.summary.furniture, 1)
        self.assertEqual(result.summary.healthy, 2)
        self.assertEqual(result.summary.idle, 1)
        self.assertEqual(result.summary.failing, 0)
        self.assertEqual(result.summary.thin, 0)
        self.assertEqual(result.summary.silent, 0)
        self.assertEqual(result.summary.unscraped, 0)


class TestNoWrites(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        company = add_company(self.session, "Read Only Co")
        add_job(
            self.session,
            company,
            "Senior DSP Engineer",
            description="A detailed and genuine job description. " * 10,
            is_audio_related=True,
        )
        self.session.add(ScrapeLog(company_id=company.id, status="success", started_at=NOW))
        self.session.flush()
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()

    def _counts(self) -> tuple:
        return (
            self.session.execute(select(func.count(Company.id))).scalar_one(),
            self.session.execute(select(func.count(Job.id))).scalar_one(),
            self.session.execute(select(func.count(ScrapeLog.id))).scalar_one(),
        )

    def test_endpoint_performs_no_writes(self) -> None:
        before = self._counts()
        health(self.session, grade="healthy")
        health(self.session, sort="board", direction="asc")
        health(self.session, q="Read")
        after = self._counts()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
