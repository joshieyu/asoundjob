from __future__ import annotations

import unittest
from datetime import date, timedelta

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.routers import admin as admin_router
from api.routers import jobs as jobs_router
from api.schemas import (
    AdminJobFeatureUpdate,
    FeedbackApproveRequest,
    JobFeedbackRequest,
    JobSummary,
)
from scraper.models import Base, Company, Job, JobFeedback


class FeaturedJobsBase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.company = Company(
            name="Acme Audio", slug="acme-audio", category="Audio Software", verified=True
        )
        self.session.add(self.company)
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def make_job(self, title: str = "DSP Engineer", **kwargs) -> Job:
        fields = {"is_active": True, "is_audio_related": True, **kwargs}
        job = Job(
            company_id=self.company.id,
            title=title,
            url=f"https://example.com/jobs/{title}",
            external_id=title,
            source="scraper",
            **fields,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def feature(self, job: Job, note=None, days: int = 30):
        return admin_router.admin_set_job_featured(
            job.id,
            AdminJobFeatureUpdate(featured=True, days=days, note=note),
            self.session,
            "admin",
        )

    def featured_ids(self) -> list[int]:
        return [job.id for job in jobs_router.list_featured_jobs(self.session)]


class TestFeaturing(FeaturedJobsBase):
    def test_featuring_lists_the_job_with_its_note(self) -> None:
        job = self.make_job()
        row = self.feature(job, note="  Hiring manager: jane@acme.audio — wants someone ASAP  ")
        self.assertTrue(row.featured)
        self.assertEqual(row.featured_until, date.today() + timedelta(days=30))
        featured = jobs_router.list_featured_jobs(self.session)
        self.assertEqual([j.id for j in featured], [job.id])
        self.assertEqual(
            featured[0].featured_note, "Hiring manager: jane@acme.audio — wants someone ASAP"
        )

    def test_newest_feature_comes_first(self) -> None:
        first = self.make_job("First")
        second = self.make_job("Second")
        self.feature(first)
        self.feature(second)
        self.assertEqual(self.featured_ids(), [second.id, first.id])

    def test_refeaturing_keeps_position_but_updates_note(self) -> None:
        job = self.make_job()
        self.feature(job, note="old")
        featured_at = job.featured_at
        self.feature(job, note="new", days=60)
        self.assertEqual(job.featured_at, featured_at)
        self.assertEqual(job.featured_note, "new")
        self.assertEqual(job.featured_until, date.today() + timedelta(days=60))

    def test_unfeaturing_clears_everything(self) -> None:
        job = self.make_job()
        self.feature(job, note="note")
        admin_router.admin_set_job_featured(
            job.id, AdminJobFeatureUpdate(featured=False), self.session, "admin"
        )
        self.assertIsNone(job.featured_until)
        self.assertIsNone(job.featured_note)
        self.assertEqual(self.featured_ids(), [])

    def test_lapsed_feature_drops_off_and_hides_its_note(self) -> None:
        job = self.make_job(
            featured_until=date.today() - timedelta(days=1), featured_note="stale"
        )
        self.assertEqual(self.featured_ids(), [])
        summary = JobSummary.model_validate(job)
        self.assertFalse(summary.featured)
        self.assertIsNone(summary.featured_note)

    def test_inactive_or_stale_company_jobs_are_not_featured(self) -> None:
        inactive = self.make_job("Gone", is_active=False)
        self.feature(inactive)
        self.assertEqual(self.featured_ids(), [])
        live = self.make_job("Live")
        self.feature(live)
        self.company.consecutive_failures = 5
        self.session.flush()
        self.assertEqual(self.featured_ids(), [])

    def test_admin_filter_lists_featured_jobs(self) -> None:
        job = self.make_job()
        self.make_job("Other")
        self.feature(job)
        result = admin_router.admin_list_jobs(
            search=None, show="featured", page=1, per_page=25, db=self.session, _="admin"
        )
        self.assertEqual([row.id for row in result["items"]], [job.id])

    def test_admin_can_feature_indefinitely(self) -> None:
        job = self.make_job()
        row = admin_router.admin_set_job_featured(
            job.id,
            AdminJobFeatureUpdate(featured=True, indefinite=True),
            self.session,
            "admin",
        )
        self.assertTrue(row.featured)
        self.assertIsNone(row.featured_until)
        self.assertEqual(self.featured_ids(), [job.id])
        result = admin_router.admin_list_jobs(
            search=None, show="featured", page=1, per_page=25, db=self.session, _="admin"
        )
        self.assertEqual([r.id for r in result["items"]], [job.id])

    def test_days_are_bounded(self) -> None:
        with self.assertRaises(ValidationError):
            AdminJobFeatureUpdate(featured=True, days=0)
        with self.assertRaises(ValidationError):
            AdminJobFeatureUpdate(featured=True, days=366)


class TestFeatureRequests(FeaturedJobsBase):
    def test_feature_request_is_an_accepted_kind(self) -> None:
        self.assertEqual(JobFeedbackRequest(kind="feature_request").kind, "feature_request")

    def request(self, job: Job, days=30, note=None) -> JobFeedback:
        feedback = JobFeedback(
            job_id=job.id,
            kind="feature_request",
            status="pending",
            feature_days=days,
            feature_note=note,
        )
        self.session.add(feedback)
        self.session.flush()
        return feedback

    def test_approving_a_request_features_the_job(self) -> None:
        job = self.make_job()
        feedback = self.request(job, days=14, note="Contact: hiring@acme.audio")
        result = admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        self.assertIn("featured until", result.applied)
        self.assertEqual(job.featured_until, date.today() + timedelta(days=14))
        self.assertEqual(job.featured_note, "Contact: hiring@acme.audio")
        self.assertEqual(self.featured_ids(), [job.id])

    def test_an_empty_approve_body_keeps_the_requested_terms(self) -> None:
        job = self.make_job()
        feedback = self.request(job, days=7, note="ASAP")
        admin_router.approve_job_feedback(
            feedback.id, self.session, "admin", FeedbackApproveRequest()
        )
        self.assertEqual(job.featured_until, date.today() + timedelta(days=7))
        self.assertEqual(job.featured_note, "ASAP")

    def test_admin_can_edit_terms_when_approving(self) -> None:
        job = self.make_job()
        feedback = self.request(job, days=7, note="original")
        admin_router.approve_job_feedback(
            feedback.id,
            self.session,
            "admin",
            FeedbackApproveRequest(feature_days=45, feature_note="edited"),
        )
        self.assertEqual(job.featured_until, date.today() + timedelta(days=45))
        self.assertEqual(job.featured_note, "edited")

    def test_admin_can_clear_the_note_and_make_it_indefinite(self) -> None:
        job = self.make_job()
        feedback = self.request(job, days=7, note="original")
        result = admin_router.approve_job_feedback(
            feedback.id,
            self.session,
            "admin",
            FeedbackApproveRequest(feature_indefinite=True, feature_note=None),
        )
        self.assertEqual(result.applied, "featured indefinitely")
        self.assertIsNone(job.featured_until)
        self.assertIsNone(job.featured_note)
        self.assertTrue(job.featured)
        self.assertEqual(self.featured_ids(), [job.id])

    def test_requested_indefinite_feature(self) -> None:
        job = self.make_job()
        feedback = self.request(job, days=None)
        admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        self.assertIsNone(job.featured_until)
        self.assertTrue(job.featured)

    def test_request_schema_defaults_and_cleans_feature_fields(self) -> None:
        self.assertEqual(JobFeedbackRequest(kind="feature_request").feature_days, 30)
        indefinite = JobFeedbackRequest(
            kind="feature_request", feature_days=10, feature_indefinite=True
        )
        self.assertIsNone(indefinite.feature_days)
        other = JobFeedbackRequest(kind="broken_link", feature_days=10, feature_note="x")
        self.assertIsNone(other.feature_days)
        self.assertIsNone(other.feature_note)
        with self.assertRaises(ValidationError):
            JobFeedbackRequest(kind="feature_request", feature_days=400)


if __name__ == "__main__":
    unittest.main()
