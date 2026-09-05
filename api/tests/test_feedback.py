from __future__ import annotations

import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.routers import feedback as feedback_router
from api.schemas import JobFeedbackRequest, SiteFeedbackRequest
from scraper.models import Base, Company, Job, JobFeedback, SiteFeedback


class FakeClient:
    def __init__(self, host: str) -> None:
        self.host = host


class FakeRequest:
    def __init__(self, host: str = "203.0.113.5") -> None:
        self.client = FakeClient(host)


class TestJobFeedback(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        company = Company(
            name="Acme Audio", slug="acme-audio", category="Audio Software", verified=True
        )
        self.session.add(company)
        self.session.flush()
        self.job = Job(
            company_id=company.id,
            title="DSP Engineer",
            url="https://example.com/jobs/1",
            is_active=True,
            is_audio_related=True,
            external_id="1",
            source="scraper",
        )
        self.session.add(self.job)
        self.session.commit()
        feedback_router.feedback_rate_limiter.reset()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        feedback_router.feedback_rate_limiter.reset()

    def test_happy_path_wrong_category(self) -> None:
        payload = JobFeedbackRequest(kind="wrong_category", suggested_categories=["audio_ee"])
        result = feedback_router.submit_job_feedback(
            self.job.id, payload, FakeRequest(), self.session
        )
        self.assertEqual(result.status, "pending")
        row = self.session.get(JobFeedback, result.id)
        assert row is not None
        self.assertEqual(row.kind, "wrong_category")
        self.assertEqual(row.suggested_categories, ["audio_ee"])

    def test_happy_path_not_audio(self) -> None:
        payload = JobFeedbackRequest(kind="not_audio", comment="This isn't an audio job")
        result = feedback_router.submit_job_feedback(
            self.job.id, payload, FakeRequest(), self.session
        )
        self.assertEqual(result.status, "pending")

    def test_happy_path_broken_description(self) -> None:
        payload = JobFeedbackRequest(kind="broken_description")
        result = feedback_router.submit_job_feedback(
            self.job.id, payload, FakeRequest(), self.session
        )
        self.assertEqual(result.status, "pending")

    def test_happy_path_broken_link(self) -> None:
        payload = JobFeedbackRequest(kind="broken_link")
        result = feedback_router.submit_job_feedback(
            self.job.id, payload, FakeRequest(), self.session
        )
        self.assertEqual(result.status, "pending")

    def test_unknown_job_is_404(self) -> None:
        payload = JobFeedbackRequest(kind="broken_link")
        with self.assertRaises(HTTPException) as ctx:
            feedback_router.submit_job_feedback(999999, payload, FakeRequest(), self.session)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_unknown_category_id_is_422(self) -> None:
        payload = JobFeedbackRequest(
            kind="wrong_category", suggested_categories=["not_a_real_category"]
        )
        with self.assertRaises(HTTPException) as ctx:
            feedback_router.submit_job_feedback(
                self.job.id, payload, FakeRequest(), self.session
            )
        self.assertEqual(ctx.exception.status_code, 422)

    def test_wrong_category_missing_detail_is_422(self) -> None:
        with self.assertRaises(ValidationError):
            JobFeedbackRequest(kind="wrong_category")

    def test_rate_limit_returns_429(self) -> None:
        for _ in range(20):
            payload = JobFeedbackRequest(kind="broken_link")
            feedback_router.submit_job_feedback(
                self.job.id, payload, FakeRequest(), self.session
            )
        payload = JobFeedbackRequest(kind="broken_link")
        with self.assertRaises(HTTPException) as ctx:
            feedback_router.submit_job_feedback(
                self.job.id, payload, FakeRequest(), self.session
            )
        self.assertEqual(ctx.exception.status_code, 429)

    def test_rate_limit_is_keyed_per_ip(self) -> None:
        for _ in range(20):
            payload = JobFeedbackRequest(kind="broken_link")
            feedback_router.submit_job_feedback(
                self.job.id, payload, FakeRequest("203.0.113.5"), self.session
            )
        payload = JobFeedbackRequest(kind="broken_link")
        result = feedback_router.submit_job_feedback(
            self.job.id, payload, FakeRequest("203.0.113.9"), self.session
        )
        self.assertEqual(result.status, "pending")


class TestSiteFeedback(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        feedback_router.feedback_rate_limiter.reset()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        feedback_router.feedback_rate_limiter.reset()

    def test_happy_path_company_suggestion(self) -> None:
        payload = SiteFeedbackRequest(kind="company_suggestion", company_name="New Audio Co")
        result = feedback_router.submit_site_feedback(payload, FakeRequest(), self.session)
        self.assertEqual(result.status, "pending")
        row = self.session.get(SiteFeedback, result.id)
        assert row is not None
        self.assertEqual(row.company_name, "New Audio Co")

    def test_happy_path_general(self) -> None:
        payload = SiteFeedbackRequest(kind="general", comment="Loving this site!")
        result = feedback_router.submit_site_feedback(payload, FakeRequest(), self.session)
        self.assertEqual(result.status, "pending")

    def test_company_suggestion_missing_name_is_422(self) -> None:
        with self.assertRaises(ValidationError):
            SiteFeedbackRequest(kind="company_suggestion")

    def test_general_missing_comment_is_422(self) -> None:
        with self.assertRaises(ValidationError):
            SiteFeedbackRequest(kind="general")

    def test_general_short_comment_is_422(self) -> None:
        with self.assertRaises(ValidationError):
            SiteFeedbackRequest(kind="general", comment="hi")

    def test_company_url_must_be_http(self) -> None:
        with self.assertRaises(ValidationError):
            SiteFeedbackRequest(
                kind="company_suggestion", company_name="X", company_url="ftp://example.com"
            )

    def test_rate_limit_returns_429(self) -> None:
        for _ in range(20):
            payload = SiteFeedbackRequest(kind="general", comment="another note here")
            feedback_router.submit_site_feedback(payload, FakeRequest(), self.session)
        payload = SiteFeedbackRequest(kind="general", comment="one too many")
        with self.assertRaises(HTTPException) as ctx:
            feedback_router.submit_site_feedback(payload, FakeRequest(), self.session)
        self.assertEqual(ctx.exception.status_code, 429)


if __name__ == "__main__":
    unittest.main()
