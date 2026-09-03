from __future__ import annotations

import unittest

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.routers import admin as admin_router
from api.schemas import AdminCompanyCreate, AdminCompanyUpdate
from scraper.company_loader import load_companies
from scraper.models import Company, Job, JobSubmission, ScrapeLog


def make_session() -> Session:
    engine = create_engine("sqlite://")
    Company.metadata.create_all(engine)
    return Session(engine)


class TestSourceFlipOnManagedFields(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.company = Company(
            name="Acme Audio",
            slug="acme-audio",
            category="Audio Software",
            careers_url="https://example.com/careers",
            verified=True,
            source="auto",
        )
        self.session.add(self.company)
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()

    def _update(self, **fields) -> None:
        admin_router.admin_update_company(
            self.company.id, AdminCompanyUpdate(**fields), self.session, "tester"
        )

    def test_unverifying_flips_source_to_manual(self) -> None:
        self._update(verified=False)
        self.assertEqual(self.company.source, "manual")
        self.assertFalse(self.company.verified)

    def test_verifying_flips_source_to_manual(self) -> None:
        self.company.verified = False
        self.company.source = "auto"
        self.session.flush()
        self._update(verified=True)
        self.assertEqual(self.company.source, "manual")
        self.assertTrue(self.company.verified)

    def test_editing_an_unmanaged_field_does_not_flip_source(self) -> None:
        self._update(description="A great audio company")
        self.assertEqual(self.company.source, "auto")
        self.assertEqual(self.company.description, "A great audio company")


class TestRename(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.acme = Company(
            name="Acme Audio",
            slug="acme-audio",
            category="Audio Software",
            source="auto",
        )
        self.other = Company(
            name="Other Co",
            slug="other-co",
            category="Audio Software",
            source="auto",
        )
        self.session.add_all([self.acme, self.other])
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()

    def test_rename_succeeds_and_slug_is_unchanged(self) -> None:
        admin_router.admin_update_company(
            self.other.id,
            AdminCompanyUpdate(name="Other Audio Co"),
            self.session,
            "tester",
        )
        self.assertEqual(self.other.name, "Other Audio Co")
        self.assertEqual(self.other.slug, "other-co")
        self.assertEqual(self.other.source, "manual")

    def test_case_insensitive_collision_raises_409(self) -> None:
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            admin_router.admin_update_company(
                self.other.id,
                AdminCompanyUpdate(name="acme audio"),
                self.session,
                "tester",
            )
        self.assertEqual(ctx.exception.status_code, 409)


class TestExtraCareersUrls(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.company = Company(
            name="Acme Audio",
            slug="acme-audio",
            category="Audio Software",
            careers_url="https://example.com/careers",
            source="auto",
        )
        self.session.add(self.company)
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()

    def test_set_dedupes_against_primary_and_drops_non_http(self) -> None:
        admin_router.admin_update_company(
            self.company.id,
            AdminCompanyUpdate(
                extra_careers_urls=[
                    "https://example.com/careers",
                    "https://example.com/careers/",
                    "ftp://bad.com/careers",
                    "https://example.com/other",
                ]
            ),
            self.session,
            "tester",
        )
        self.assertEqual(self.company.extra_careers_urls, ["https://example.com/other"])

    def test_empty_list_clears_to_none(self) -> None:
        self.company.extra_careers_urls = ["https://example.com/other"]
        self.session.flush()
        admin_router.admin_update_company(
            self.company.id,
            AdminCompanyUpdate(extra_careers_urls=[]),
            self.session,
            "tester",
        )
        self.assertIsNone(self.company.extra_careers_urls)

    def test_clearing_the_primary_url_stores_null_not_empty_string(self) -> None:
        admin_router.admin_update_company(
            self.company.id,
            AdminCompanyUpdate(careers_url="   ", extra_careers_urls=[]),
            self.session,
            "tester",
        )
        self.assertIsNone(self.company.careers_url)
        self.assertIsNone(self.company.extra_careers_urls)

    def test_primary_url_is_stripped(self) -> None:
        admin_router.admin_update_company(
            self.company.id,
            AdminCompanyUpdate(careers_url="  https://example.com/jobs  "),
            self.session,
            "tester",
        )
        self.assertEqual(self.company.careers_url, "https://example.com/jobs")

    def test_more_than_five_is_rejected_by_the_schema(self) -> None:
        with self.assertRaises(ValidationError):
            AdminCompanyUpdate(extra_careers_urls=[f"https://example.com/{n}" for n in range(6)])

    def test_create_passes_extra_careers_urls_through(self) -> None:
        result = admin_router.admin_create_company(
            AdminCompanyCreate(
                name="Beta Sound",
                category="Audio Software",
                careers_url="https://example.com/careers",
                extra_careers_urls=["https://example.com/careers", "https://example.com/jobs"],
            ),
            self.session,
            "tester",
        )
        created = self.session.get(Company, result["id"])
        assert created is not None
        self.assertEqual(created.extra_careers_urls, ["https://example.com/jobs"])


class TestDeleteCompany(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.company = Company(
            name="Acme Audio",
            slug="acme-audio",
            category="Audio Software",
            source="auto",
        )
        self.session.add(self.company)
        self.session.flush()
        self.session.add(
            Job(
                company_id=self.company.id,
                title="DSP Engineer",
                url="https://example.com/jobs/1",
                is_active=True,
                source="scraper",
            )
        )
        self.session.add(ScrapeLog(company_id=self.company.id, status="success"))
        self.session.add(
            JobSubmission(
                company_name="Acme Audio",
                company_id=self.company.id,
                title="Mix Engineer",
                description="A description that is long enough to be valid here.",
                url="https://example.com/jobs/2",
                status="pending",
            )
        )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()

    def test_delete_removes_jobs_and_scrape_logs_and_detaches_submissions(self) -> None:
        company_id = self.company.id
        result = admin_router.admin_delete_company(company_id, self.session, "tester")
        self.assertEqual(result["deleted"]["company"], "Acme Audio")
        self.assertEqual(result["deleted"]["jobs"], 1)
        self.assertEqual(result["deleted"]["scrape_logs"], 1)
        self.assertEqual(result["deleted"]["submissions_detached"], 1)

        self.assertEqual(
            self.session.execute(
                select(Job).where(Job.company_id == company_id)
            ).scalars().all(),
            [],
        )
        self.assertEqual(
            self.session.execute(
                select(ScrapeLog).where(ScrapeLog.company_id == company_id)
            ).scalars().all(),
            [],
        )
        submission = self.session.execute(select(JobSubmission)).scalars().one()
        self.assertIsNone(submission.company_id)
        self.assertEqual(submission.company_name, "Acme Audio")
        self.assertIsNone(self.session.get(Company, company_id))

    def test_delete_missing_company_is_404(self) -> None:
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            admin_router.admin_delete_company(999999, self.session, "tester")
        self.assertEqual(ctx.exception.status_code, 404)


class TestUnverifyRevertBugIsDead(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.close()

    def test_unverifying_survives_a_reload_of_the_original_seed(self) -> None:
        seed = [
            {
                "name": "Acme Audio",
                "category": "Audio Software",
                "careers_url": "https://example.com/careers",
                "verified": True,
                "source": "auto",
                "scrape_method": "http",
            }
        ]
        load_companies(self.session, seed)
        company = self.session.execute(
            select(Company).where(Company.name == "Acme Audio")
        ).scalar_one()
        self.assertTrue(company.verified)

        admin_router.admin_update_company(
            company.id, AdminCompanyUpdate(verified=False), self.session, "tester"
        )
        self.assertEqual(company.source, "manual")

        load_companies(self.session, seed)
        self.session.refresh(company)
        self.assertFalse(company.verified)


if __name__ == "__main__":
    unittest.main()
