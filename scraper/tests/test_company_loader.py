from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from scraper.company_loader import load_companies
from scraper.models import Base, Company, Job


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def entry(name: str, verified: bool) -> dict:
    return {
        "name": name,
        "careers_url": "https://example.com/careers",
        "category": "Audio Software",
        "verified": verified,
        "source": "auto",
        "scrape_method": "http",
    }


class TestUnverifiedDeactivation(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def seed_company_with_job(self, name: str, verified: bool) -> Company:
        company = Company(
            name=name,
            slug=name.lower(),
            category="Audio Software",
            careers_url="https://example.com/careers",
            verified=verified,
        )
        self.session.add(company)
        self.session.flush()
        self.session.add(
            Job(
                company_id=company.id,
                title="Audio Engineer",
                url=f"https://example.com/{name}/1",
                is_active=True,
            )
        )
        self.session.flush()
        return company

    def active_titles(self, company_id: int) -> list[str]:
        rows = self.session.execute(
            select(Job.title).where(
                Job.company_id == company_id, Job.is_active.is_(True)
            )
        ).all()
        return [r[0] for r in rows]

    def test_demoting_to_unverified_deactivates_jobs(self) -> None:
        company = self.seed_company_with_job("acme", verified=True)
        stats = load_companies(self.session, [entry("acme", verified=False)])
        self.assertEqual(stats.deactivated_unverified, 1)
        self.assertEqual(self.active_titles(company.id), [])

    def test_verified_company_keeps_jobs(self) -> None:
        company = self.seed_company_with_job("acme", verified=True)
        stats = load_companies(self.session, [entry("acme", verified=True)])
        self.assertEqual(stats.deactivated_unverified, 0)
        self.assertEqual(self.active_titles(company.id), ["Audio Engineer"])

    def test_already_inactive_jobs_are_not_recounted(self) -> None:
        company = self.seed_company_with_job("acme", verified=False)
        load_companies(self.session, [entry("acme", verified=False)])
        stats = load_companies(self.session, [entry("acme", verified=False)])
        self.assertEqual(stats.deactivated_unverified, 0)
        self.assertEqual(self.active_titles(company.id), [])


if __name__ == "__main__":
    unittest.main()
