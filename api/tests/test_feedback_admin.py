from __future__ import annotations

import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.routers import admin as admin_router
from api.schemas import RejectRequest
from scraper.models import Base, Company, Job, JobFeedback


class TestApproveJobFeedback(unittest.TestCase):
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

    def make_job(self) -> Job:
        job = Job(
            company_id=self.company.id,
            title="DSP Engineer",
            url="https://example.com/jobs/1",
            job_categories=["audio_software"],
            is_active=True,
            is_audio_related=True,
            external_id="1",
            source="scraper",
        )
        self.session.add(job)
        self.session.flush()
        return job

    def make_feedback(self, job: Job, kind: str, suggested_categories=None) -> JobFeedback:
        feedback = JobFeedback(
            job_id=job.id,
            kind=kind,
            suggested_categories=suggested_categories,
            status="pending",
        )
        self.session.add(feedback)
        self.session.flush()
        return feedback

    def test_approve_not_audio(self) -> None:
        job = self.make_job()
        feedback = self.make_feedback(job, "not_audio")
        result = admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        self.assertEqual(result.status, "approved")
        self.session.refresh(job)
        self.session.refresh(feedback)
        self.assertFalse(job.is_audio_related)
        self.assertFalse(job.is_audio_related_override)
        self.assertEqual(feedback.status, "approved")
        self.assertEqual(feedback.reviewed_by, "admin")
        self.assertIsNotNone(feedback.reviewed_at)

    def test_approve_wrong_category_with_suggestions(self) -> None:
        job = self.make_job()
        feedback = self.make_feedback(
            job, "wrong_category", suggested_categories=["microphones_recording"]
        )
        result = admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        self.assertEqual(result.status, "approved")
        self.session.refresh(job)
        self.assertEqual(job.job_categories, ["microphones_recording"])
        self.assertEqual(job.categories_override, ["microphones_recording"])

    def test_approve_wrong_category_without_suggestions_does_not_mutate_job(self) -> None:
        job = self.make_job()
        original_categories = list(job.job_categories)
        feedback = self.make_feedback(job, "wrong_category", suggested_categories=None)
        admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        self.session.refresh(job)
        self.assertEqual(job.job_categories, original_categories)
        self.assertIsNone(job.categories_override)

    def test_approve_broken_description_mutates_nothing(self) -> None:
        job = self.make_job()
        original_categories = list(job.job_categories)
        original_is_audio = job.is_audio_related
        feedback = self.make_feedback(job, "broken_description")
        result = admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        self.assertEqual(result.status, "approved")
        self.session.refresh(job)
        self.assertEqual(job.job_categories, original_categories)
        self.assertEqual(job.is_audio_related, original_is_audio)
        self.assertIsNone(job.categories_override)
        self.assertIsNone(job.is_audio_related_override)

    def test_approve_broken_link_mutates_nothing(self) -> None:
        job = self.make_job()
        original_categories = list(job.job_categories)
        original_is_audio = job.is_audio_related
        feedback = self.make_feedback(job, "broken_link")
        result = admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        self.assertEqual(result.status, "approved")
        self.session.refresh(job)
        self.assertEqual(job.job_categories, original_categories)
        self.assertEqual(job.is_audio_related, original_is_audio)
        self.assertIsNone(job.categories_override)
        self.assertIsNone(job.is_audio_related_override)

    def test_reject(self) -> None:
        job = self.make_job()
        feedback = self.make_feedback(job, "broken_link")
        result = admin_router.reject_job_feedback(
            feedback.id, RejectRequest(reason="not reproducible"), self.session, "admin"
        )
        self.assertEqual(result["status"], "rejected")
        self.session.refresh(feedback)
        self.assertEqual(feedback.status, "rejected")
        self.assertEqual(feedback.reject_reason, "not reproducible")
        self.assertEqual(feedback.reviewed_by, "admin")

    def test_approve_unknown_feedback_is_404(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            admin_router.approve_job_feedback(999999, self.session, "admin")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_double_review_is_409(self) -> None:
        job = self.make_job()
        feedback = self.make_feedback(job, "broken_link")
        admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        with self.assertRaises(HTTPException) as ctx:
            admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_reject_after_approve_is_409(self) -> None:
        job = self.make_job()
        feedback = self.make_feedback(job, "broken_link")
        admin_router.approve_job_feedback(feedback.id, self.session, "admin")
        with self.assertRaises(HTTPException) as ctx:
            admin_router.reject_job_feedback(
                feedback.id, RejectRequest(), self.session, "admin"
            )
        self.assertEqual(ctx.exception.status_code, 409)

    def test_list_job_feedback_includes_job_and_company_context(self) -> None:
        job = self.make_job()
        self.make_feedback(job, "broken_link")
        page = admin_router.admin_list_job_feedback("pending", 1, 25, self.session, "admin")
        self.assertEqual(page["total"], 1)
        item = page["items"][0]
        self.assertEqual(item.job_title, "DSP Engineer")
        self.assertEqual(item.company_name, "Acme Audio")
        self.assertEqual(item.status, "pending")


if __name__ == "__main__":
    unittest.main()
