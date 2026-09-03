from __future__ import annotations

import unittest
from datetime import date, timedelta

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.config import COMMUNITY_JOB_TTL_DAYS, MAX_COMMUNITY_JOB_DAYS
from api.routers import admin as admin_router
from api.routers import jobs as jobs_router
from api.schemas import ApproveRequest, JobSubmissionRequest
from scraper.models import Base, Company, Job, JobSubmission


class FakeClient:
    def __init__(self, host: str) -> None:
        self.host = host


class FakeRequest:
    def __init__(self, host: str = "203.0.113.7") -> None:
        self.client = FakeClient(host)


class TestResolveExpiryDays(unittest.TestCase):
    def test_moderator_override_wins(self) -> None:
        self.assertEqual(admin_router.resolve_expiry_days(90, 45), (90, "moderator"))

    def test_submitter_request_is_used_when_no_override(self) -> None:
        self.assertEqual(admin_router.resolve_expiry_days(None, 45), (45, "submitter"))

    def test_default_when_neither_is_given(self) -> None:
        self.assertEqual(
            admin_router.resolve_expiry_days(None, None),
            (COMMUNITY_JOB_TTL_DAYS, "default"),
        )

    def test_override_of_zero_is_not_mistaken_for_absent(self) -> None:
        days, source = admin_router.resolve_expiry_days(0, 45)
        self.assertEqual(source, "moderator")
        self.assertEqual(days, 1)

    def test_values_are_clamped_to_the_maximum(self) -> None:
        days, _ = admin_router.resolve_expiry_days(99999, None)
        self.assertEqual(days, MAX_COMMUNITY_JOB_DAYS)

    def test_a_stored_out_of_range_request_is_clamped(self) -> None:
        days, source = admin_router.resolve_expiry_days(None, 99999)
        self.assertEqual((days, source), (MAX_COMMUNITY_JOB_DAYS, "submitter"))


class TestSubmissionDuration(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        company = Company(
            name="Acme Audio", slug="acme-audio", category="Audio Software", verified=True
        )
        self.session.add(company)
        self.session.commit()
        jobs_router.rate_limiter.reset()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        jobs_router.rate_limiter.reset()

    def _submit(self, **kwargs) -> int:
        payload = JobSubmissionRequest(
            title="DSP Engineer",
            company_name="Acme Audio",
            url="https://example.com/jobs/1",
            description="A real audio role with a description long enough to pass.",
            **kwargs,
        )
        result = jobs_router.submit_job(FakeRequest(), payload, self.session)
        return result.id

    def test_duration_is_stored_on_the_submission(self) -> None:
        submission_id = self._submit(duration_days=120)
        row = self.session.get(JobSubmission, submission_id)
        assert row is not None
        self.assertEqual(row.requested_days, 120)

    def test_omitting_duration_stores_null(self) -> None:
        row = self.session.get(JobSubmission, self._submit())
        assert row is not None
        self.assertIsNone(row.requested_days)

    def test_duration_below_one_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            JobSubmissionRequest(
                title="DSP Engineer",
                company_name="Acme Audio",
                url="https://example.com/jobs/1",
                description="A real audio role with a description long enough to pass.",
                duration_days=0,
            )

    def test_duration_above_the_maximum_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            JobSubmissionRequest(
                title="DSP Engineer",
                company_name="Acme Audio",
                url="https://example.com/jobs/1",
                description="A real audio role with a description long enough to pass.",
                duration_days=MAX_COMMUNITY_JOB_DAYS + 1,
            )

    def _approve(self, submission_id: int, payload=None):
        return admin_router.approve_submission(
            submission_id, payload, self.session, "tester"
        )

    def test_approval_honours_the_submitted_duration(self) -> None:
        result = self._approve(self._submit(duration_days=200))
        self.assertEqual(result.expires_source, "submitter")
        self.assertEqual(result.expires_date, date.today() + timedelta(days=200))
        job = self.session.get(Job, result.job_id)
        assert job is not None
        self.assertEqual(job.expires_date, date.today() + timedelta(days=200))

    def test_moderator_override_beats_the_submitted_duration(self) -> None:
        result = self._approve(
            self._submit(duration_days=200), ApproveRequest(expires_days=14)
        )
        self.assertEqual(result.expires_source, "moderator")
        self.assertEqual(result.expires_date, date.today() + timedelta(days=14))

    def test_an_empty_body_falls_back_to_the_submitted_duration(self) -> None:
        result = self._approve(self._submit(duration_days=90), ApproveRequest())
        self.assertEqual(result.expires_source, "submitter")
        self.assertEqual(result.expires_days, 90)

    def test_default_applies_when_nobody_chose(self) -> None:
        result = self._approve(self._submit())
        self.assertEqual(result.expires_source, "default")
        self.assertEqual(result.expires_days, COMMUNITY_JOB_TTL_DAYS)

    def test_moderator_can_set_a_duration_when_none_was_requested(self) -> None:
        result = self._approve(self._submit(), ApproveRequest(expires_days=365))
        self.assertEqual(result.expires_source, "moderator")
        self.assertEqual(result.expires_days, 365)

    def test_a_second_submission_of_the_same_url_unpublishes_the_first(self) -> None:
        first = self._approve(self._submit(duration_days=90))
        job = self.session.get(Job, first.job_id)
        assert job is not None
        self.assertTrue(job.is_active)

        second = self._approve(self._submit(duration_days=90))
        self.assertEqual(second.status, "approved")
        self.assertIsNone(second.job_id)
        self.session.refresh(job)
        self.assertFalse(job.is_active)
        remaining = (
            self.session.query(Job).filter(Job.is_active.is_(True)).count()
        )
        self.assertEqual(remaining, 0)

    def test_approving_twice_is_a_conflict(self) -> None:
        submission_id = self._submit(duration_days=30)
        self._approve(submission_id)
        with self.assertRaises(HTTPException) as ctx:
            self._approve(submission_id)
        self.assertEqual(ctx.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
