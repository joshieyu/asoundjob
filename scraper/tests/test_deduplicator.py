from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper.deduplicator import reconcile_company_jobs
from scraper.models import Base, Company, Job
from scraper.normalizer import NormalizedJob


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_company(session) -> Company:
    company = Company(
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url="https://example.com/careers",
        verified=True,
    )
    session.add(company)
    session.flush()
    return company


def nj(title: str, url: str, external_id: str | None = None) -> NormalizedJob:
    return NormalizedJob(title=title, url=url, external_id=external_id)


class TestReconcile(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.company = make_company(self.session)

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def all_jobs(self) -> list[Job]:
        return self.session.query(Job).all()

    def test_inserts_new_jobs(self) -> None:
        stats = reconcile_company_jobs(
            self.session,
            self.company,
            [nj("DSP Engineer", "https://example.com/jobs/1", "1")],
            trust_empty=False,
        )
        self.session.flush()
        self.assertEqual(stats.inserted, 1)
        self.assertEqual(len(self.all_jobs()), 1)
        row = self.all_jobs()[0]
        self.assertEqual(row.source, "scraper")
        self.assertTrue(row.is_active)

    def test_second_run_updates_without_duplicates(self) -> None:
        reconcile_company_jobs(
            self.session,
            self.company,
            [nj("DSP Engineer", "https://example.com/jobs/1", "1")],
            trust_empty=False,
        )
        stats = reconcile_company_jobs(
            self.session,
            self.company,
            [nj("DSP Engineer (updated)", "https://example.com/jobs/1", "1")],
            trust_empty=False,
        )
        self.session.flush()
        self.assertEqual(stats.inserted, 0)
        self.assertEqual(stats.updated, 1)
        rows = self.all_jobs()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].title, "DSP Engineer (updated)")

    def test_missing_job_deactivated_when_fetch_trusted(self) -> None:
        reconcile_company_jobs(
            self.session,
            self.company,
            [
                nj("Job A", "https://example.com/jobs/a", "a"),
                nj("Job B", "https://example.com/jobs/b", "b"),
            ],
            trust_empty=True,
        )
        stats = reconcile_company_jobs(
            self.session,
            self.company,
            [nj("Job A", "https://example.com/jobs/a", "a")],
            trust_empty=True,
        )
        self.session.flush()
        self.assertEqual(stats.deactivated, 1)
        rows = {j.title: j.is_active for j in self.all_jobs()}
        self.assertTrue(rows["Job A"])
        self.assertFalse(rows["Job B"])

    def test_reactivation(self) -> None:
        reconcile_company_jobs(
            self.session,
            self.company,
            [nj("Job A", "https://example.com/jobs/a", "a")],
            trust_empty=True,
        )
        reconcile_company_jobs(self.session, self.company, [], trust_empty=True)
        stats = reconcile_company_jobs(
            self.session,
            self.company,
            [nj("Job A", "https://example.com/jobs/a", "a")],
            trust_empty=True,
        )
        self.session.flush()
        self.assertEqual(stats.reactivated, 1)
        self.assertTrue(self.all_jobs()[0].is_active)

    def test_url_identity_when_no_external_id(self) -> None:
        first = nj("Role", "https://example.com/apply/123")
        stats = reconcile_company_jobs(
            self.session, self.company, [first], trust_empty=False
        )
        stats2 = reconcile_company_jobs(
            self.session,
            self.company,
            [nj("Role", "https://EXAMPLE.com/apply/123/")],
            trust_empty=False,
        )
        self.session.flush()
        self.assertEqual(stats.inserted, 1)
        self.assertEqual(stats2.inserted, 0)
        self.assertEqual(stats2.updated, 1)

    def test_never_touches_community_jobs(self) -> None:
        community = Job(
            company_id=self.company.id,
            title="Community Posting",
            url="https://elsewhere.example/job",
            source="community",
            is_active=True,
            expires_date=None,
        )
        self.session.add(community)
        self.session.flush()

        stats = reconcile_company_jobs(
            self.session,
            self.company,
            [nj("Scraped Role", "https://example.com/jobs/x", "x")],
            trust_empty=True,
        )
        self.session.flush()
        self.assertEqual(stats.deactivated, 0)
        self.assertTrue(community.is_active)

        stats = reconcile_company_jobs(
            self.session, self.company, [], trust_empty=True
        )
        self.session.flush()
        self.assertEqual(stats.deactivated, 1)
        scraped = self.session.query(Job).filter(Job.source == "scraper").one()
        self.assertFalse(scraped.is_active)
        self.assertTrue(community.is_active)


if __name__ == "__main__":
    unittest.main()
