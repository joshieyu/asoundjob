from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from scraper.models import (
    Base,
    Company,
    CompanySuggestion,
    Job,
    JobFeedback,
    JobSubmission,
    ScrapeLog,
)
from scraper.prune_orphans import delete_orphans, find_orphans


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(name: str) -> dict:
    return {"name": name}


class PruneOrphansTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def add_company(
        self,
        name: str,
        source: str = "auto",
        category: str = "Audio Software",
    ) -> Company:
        company = Company(
            name=name,
            slug=name.lower().replace(" ", "-"),
            category=category,
            careers_url="https://example.com/careers",
            verified=True,
            source=source,
        )
        self.session.add(company)
        self.session.flush()
        return company

    def add_job(self, company: Company, **kwargs) -> Job:
        defaults = dict(
            company_id=company.id,
            title="Audio Engineer",
            url=f"https://example.com/{company.slug}/{kwargs.get('external_id', '1')}",
            is_active=True,
            is_audio_related=True,
            source="scraper",
        )
        defaults.update(kwargs)
        job = Job(**defaults)
        self.session.add(job)
        self.session.flush()
        return job


class TestFindOrphans(PruneOrphansTestCase):
    def test_company_absent_from_seed_is_found(self) -> None:
        self.add_company("Gone Audio")
        orphans = find_orphans(self.session, [seed("Other Co")])
        self.assertEqual([o.name for o in orphans], ["Gone Audio"])

    def test_company_present_in_seed_is_not_found(self) -> None:
        self.add_company("Present Audio")
        orphans = find_orphans(self.session, [seed("Present Audio")])
        self.assertEqual(orphans, [])

    def test_stored_name_with_surrounding_whitespace_still_matches(self) -> None:
        self.add_company("  Gone Audio  ")
        orphans = find_orphans(self.session, [seed("Gone Audio")])
        self.assertEqual(orphans, [])

    def test_case_insensitive_match_against_seed(self) -> None:
        self.add_company("Present Audio")
        orphans = find_orphans(self.session, [seed("PRESENT audio")])
        self.assertEqual(orphans, [])

    def test_manual_company_absent_from_seed_is_never_an_orphan(self) -> None:
        self.add_company("Admin Added Co", source="manual")
        orphans = find_orphans(self.session, [])
        self.assertEqual(orphans, [])

    def test_blocker_non_scraper_job_source(self) -> None:
        company = self.add_company("Gone Audio")
        self.add_job(company, source="manual")
        orphans = find_orphans(self.session, [])
        self.assertEqual(len(orphans), 1)
        self.assertEqual(len(orphans[0].blockers), 1)
        self.assertIn("source != scraper", orphans[0].blockers[0])

    def test_blocker_categories_override(self) -> None:
        company = self.add_company("Gone Audio")
        self.add_job(company, categories_override=["Mixing"])
        orphans = find_orphans(self.session, [])
        self.assertEqual(len(orphans[0].blockers), 1)
        self.assertIn("override", orphans[0].blockers[0])

    def test_blocker_is_audio_related_override(self) -> None:
        company = self.add_company("Gone Audio")
        self.add_job(company, is_audio_related_override=False)
        orphans = find_orphans(self.session, [])
        self.assertEqual(len(orphans[0].blockers), 1)

    def test_blocker_is_active_override(self) -> None:
        company = self.add_company("Gone Audio")
        self.add_job(company, is_active_override=True)
        orphans = find_orphans(self.session, [])
        self.assertEqual(len(orphans[0].blockers), 1)

    def test_blocker_job_feedback(self) -> None:
        company = self.add_company("Gone Audio")
        job = self.add_job(company)
        self.session.add(JobFeedback(job_id=job.id, kind="wrong_category"))
        self.session.flush()
        orphans = find_orphans(self.session, [])
        self.assertEqual(len(orphans[0].blockers), 1)
        self.assertIn("feedback", orphans[0].blockers[0])

    def test_blocker_job_submission(self) -> None:
        company = self.add_company("Gone Audio")
        self.session.add(
            JobSubmission(
                company_name=company.name,
                company_id=company.id,
                title="Mix Engineer",
                description="desc",
                url="https://example.com/job/1",
            )
        )
        self.session.flush()
        orphans = find_orphans(self.session, [])
        self.assertEqual(len(orphans[0].blockers), 1)
        self.assertIn("submission", orphans[0].blockers[0])

    def test_blocker_company_suggestion(self) -> None:
        company = self.add_company("Gone Audio")
        self.session.add(CompanySuggestion(company_id=company.id))
        self.session.flush()
        orphans = find_orphans(self.session, [])
        self.assertEqual(len(orphans[0].blockers), 1)
        self.assertIn("suggestion", orphans[0].blockers[0])

    def test_job_and_board_counts(self) -> None:
        company = self.add_company("Gone Audio")
        self.add_job(company, external_id="1", is_active=True, is_audio_related=True)
        self.add_job(company, external_id="2", is_active=False, is_audio_related=True)
        self.add_job(company, external_id="3", is_active=True, is_audio_related=False)
        orphans = find_orphans(self.session, [])
        self.assertEqual(orphans[0].job_count, 3)
        self.assertEqual(orphans[0].board_count, 1)

    def test_scrape_log_count(self) -> None:
        company = self.add_company("Gone Audio")
        self.session.add(ScrapeLog(company_id=company.id, status="ok"))
        self.session.add(ScrapeLog(company_id=company.id, status="failed"))
        self.session.flush()
        orphans = find_orphans(self.session, [])
        self.assertEqual(orphans[0].scrape_log_count, 2)


class TestDeleteOrphans(PruneOrphansTestCase):
    def test_deletes_company_jobs_and_scrape_log_and_returns_counts(self) -> None:
        company = self.add_company("Gone Audio")
        self.add_job(company, external_id="1")
        self.add_job(company, external_id="2")
        self.session.add(ScrapeLog(company_id=company.id, status="ok"))
        self.session.flush()

        orphans = find_orphans(self.session, [])
        self.assertEqual(orphans[0].blockers, [])
        stats = delete_orphans(self.session, orphans)
        self.session.flush()

        self.assertEqual(stats.companies, 1)
        self.assertEqual(stats.jobs, 2)
        self.assertEqual(stats.scrape_logs, 1)
        self.assertEqual(
            self.session.execute(select(Company)).scalars().all(), []
        )
        self.assertEqual(self.session.execute(select(Job)).scalars().all(), [])
        self.assertEqual(
            self.session.execute(select(ScrapeLog)).scalars().all(), []
        )

    def test_deletes_job_feedback_submissions_and_suggestions(self) -> None:
        company = self.add_company("Gone Audio")
        job = self.add_job(company)
        self.session.add(JobFeedback(job_id=job.id, kind="wrong_category"))
        self.session.add(
            JobSubmission(
                company_name=company.name,
                company_id=company.id,
                title="Mix Engineer",
                description="desc",
                url="https://example.com/job/1",
            )
        )
        self.session.add(CompanySuggestion(company_id=company.id))
        self.session.flush()

        blocked_orphans = find_orphans(self.session, [])
        self.assertNotEqual(blocked_orphans[0].blockers, [])
        blocked_orphans[0].blockers = []
        stats = delete_orphans(self.session, blocked_orphans)
        self.session.flush()

        self.assertEqual(stats.job_feedback, 1)
        self.assertEqual(stats.job_submissions, 1)
        self.assertEqual(stats.company_suggestions, 1)
        self.assertEqual(
            self.session.execute(select(JobFeedback)).scalars().all(), []
        )
        self.assertEqual(
            self.session.execute(select(JobSubmission)).scalars().all(), []
        )
        self.assertEqual(
            self.session.execute(select(CompanySuggestion)).scalars().all(), []
        )

    def test_raises_value_error_for_blocked_orphan(self) -> None:
        company = self.add_company("Gone Audio")
        self.add_job(company, source="manual")
        orphans = find_orphans(self.session, [])
        self.assertNotEqual(orphans[0].blockers, [])
        with self.assertRaises(ValueError):
            delete_orphans(self.session, orphans)

    def test_allow_blocked_deletes_a_blocked_orphan(self) -> None:
        company = self.add_company("Gone Audio")
        self.add_job(company, source="manual")
        orphans = find_orphans(self.session, [])
        self.assertNotEqual(orphans[0].blockers, [])

        stats = delete_orphans(self.session, orphans, allow_blocked=True)

        self.assertEqual(stats.companies, 1)
        self.assertEqual(stats.jobs, 1)
        self.assertEqual(self.session.execute(select(Company)).scalars().all(), [])

    def test_dry_run_writes_nothing(self) -> None:
        company = self.add_company("Gone Audio")
        self.add_job(company)
        self.session.add(ScrapeLog(company_id=company.id, status="ok"))
        self.session.flush()

        find_orphans(self.session, [])

        self.assertEqual(len(self.session.execute(select(Company)).scalars().all()), 1)
        self.assertEqual(len(self.session.execute(select(Job)).scalars().all()), 1)
        self.assertEqual(
            len(self.session.execute(select(ScrapeLog)).scalars().all()), 1
        )


if __name__ == "__main__":
    unittest.main()
