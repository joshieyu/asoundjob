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


class TestCommunityFieldsSurviveReload(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_a_seed_reload_leaves_community_contributions_alone(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.description = "Builds loudspeaker DSP."
        company.community_links = [{"label": "Wikipedia", "url": "https://example.org"}]
        company.headquarters = "Copenhagen, Denmark"
        company.founded = 1977
        self.session.flush()

        load_companies(self.session, [entry("Acme", verified=True)])
        self.session.refresh(company)
        self.assertEqual(company.description, "Builds loudspeaker DSP.")
        self.assertEqual(
            company.community_links,
            [{"label": "Wikipedia", "url": "https://example.org"}],
        )
        self.assertEqual(company.headquarters, "Copenhagen, Denmark")
        self.assertEqual(company.founded, 1977)

    def test_they_survive_a_reload_that_does_change_seed_fields(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.description = "Builds loudspeaker DSP."
        self.session.flush()

        load_companies(self.session, [entry("Acme", verified=False)])
        self.session.refresh(company)
        self.assertFalse(company.verified)
        self.assertEqual(company.description, "Builds loudspeaker DSP.")


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


class TestScrapeBlocked(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_seed_entry_sets_scrape_blocked_on_insert(self) -> None:
        seed = entry("acme", verified=True)
        seed["scrape_blocked"] = True
        load_companies(self.session, [seed])
        company = self.session.execute(select(Company)).scalar_one()
        self.assertTrue(company.scrape_blocked)

    def test_flipping_scrape_blocked_updates_existing_company(self) -> None:
        load_companies(self.session, [entry("acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        self.assertFalse(company.scrape_blocked)

        seed = entry("acme", verified=True)
        seed["scrape_blocked"] = True
        stats = load_companies(self.session, [seed])

        company = self.session.execute(select(Company)).scalar_one()
        self.assertTrue(company.scrape_blocked)
        self.assertEqual(stats.updated, 1)


class TestRenameMatchedBySlug(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_a_renamed_manual_row_is_matched_by_slug_and_skipped(self) -> None:
        self.session.add(
            Company(
                name="New Name",
                slug="old-name",
                category="Audio Software",
                careers_url="https://example.com/careers",
                verified=True,
                source="manual",
            )
        )
        self.session.flush()

        stats = load_companies(self.session, [entry("Old Name", verified=False)])

        companies = self.session.execute(select(Company)).scalars().all()
        self.assertEqual(len(companies), 1)
        self.assertEqual(stats.matched_by_slug, 1)
        self.assertEqual(stats.skipped_manual, 1)
        self.assertEqual(companies[0].name, "New Name")
        self.assertTrue(companies[0].verified)

    def test_a_renamed_auto_row_still_inserts_as_today(self) -> None:
        self.session.add(
            Company(
                name="New Name",
                slug="old-name",
                category="Audio Software",
                careers_url="https://example.com/careers",
                verified=True,
                source="auto",
            )
        )
        self.session.flush()

        stats = load_companies(self.session, [entry("Old Name", verified=False)])

        companies = self.session.execute(select(Company)).scalars().all()
        self.assertEqual(len(companies), 2)
        self.assertEqual(stats.matched_by_slug, 0)
        self.assertEqual(stats.inserted, 1)


if __name__ == "__main__":
    unittest.main()
