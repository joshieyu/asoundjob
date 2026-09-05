from __future__ import annotations

import unittest
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.routers import admin as admin_router
from api.routers import jobs as jobs_router
from api.schemas import ApproveRequest, JobSubmissionRequest
from scraper.models import Base, Company, Job

LONG_ENOUGH = "A real audio role with a description long enough to pass validation."


class FakeClient:
    def __init__(self, host: str) -> None:
        self.host = host


class FakeRequest:
    def __init__(self, host: str = "203.0.113.11") -> None:
        self.client = FakeClient(host)


class TestReapproval(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.session.add(
            Company(
                name="Acme Audio",
                slug="acme-audio",
                category="Audio Software",
                verified=True,
            )
        )
        self.session.commit()
        jobs_router.rate_limiter.reset()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        jobs_router.rate_limiter.reset()

    def _submit(self, company: str = "Acme Audio", **kwargs) -> int:
        payload = JobSubmissionRequest(
            title=kwargs.pop("title", "DSP Engineer"),
            company_name=company,
            url=kwargs.pop("url", "https://example.com/jobs/1"),
            description=kwargs.pop("description", LONG_ENOUGH),
            **kwargs,
        )
        return jobs_router.submit_job(FakeRequest(), payload, self.session).id

    def _approve(self, submission_id: int, payload=None):
        return admin_router.approve_submission(
            submission_id, payload, self.session, "tester"
        )

    def test_the_job_id_survives_a_second_approval(self) -> None:
        first = self._approve(self._submit(duration_days=30))
        second = self._approve(self._submit(duration_days=180))
        self.assertEqual(second.job_id, first.job_id)

    def test_no_second_row_is_created(self) -> None:
        self._approve(self._submit())
        self._approve(self._submit())
        self.assertEqual(self.session.query(Job).count(), 1)

    def test_the_listing_stays_live(self) -> None:
        first = self._approve(self._submit())
        self._approve(self._submit())
        job = self.session.get(Job, first.job_id)
        assert job is not None
        self.assertTrue(job.is_active)

    def test_the_new_expiry_is_applied_to_the_existing_row(self) -> None:
        first = self._approve(self._submit(duration_days=30))
        job = self.session.get(Job, first.job_id)
        assert job is not None
        self.assertEqual(job.expires_date, date.today() + timedelta(days=30))
        self._approve(self._submit(duration_days=180))
        self.session.refresh(job)
        self.assertEqual(job.expires_date, date.today() + timedelta(days=180))

    def test_a_moderator_override_applies_on_re_approval(self) -> None:
        first = self._approve(self._submit(duration_days=30))
        result = self._approve(self._submit(), ApproveRequest(expires_days=7))
        self.assertEqual(result.job_id, first.job_id)
        self.assertEqual(result.expires_source, "moderator")
        job = self.session.get(Job, first.job_id)
        assert job is not None
        self.assertEqual(job.expires_date, date.today() + timedelta(days=7))

    def test_corrected_content_replaces_the_old(self) -> None:
        first = self._approve(self._submit(title="DSP Enginer"))
        self._approve(self._submit(title="DSP Engineer"))
        job = self.session.get(Job, first.job_id)
        assert job is not None
        self.assertEqual(job.title, "DSP Engineer")

    def test_a_not_audio_override_is_not_reverted(self) -> None:
        first = self._approve(self._submit())
        job = self.session.get(Job, first.job_id)
        assert job is not None
        self.assertTrue(job.is_audio_related)
        job.is_audio_related_override = False
        job.is_audio_related = False
        self.session.flush()

        self._approve(self._submit())
        self.session.refresh(job)
        self.assertFalse(job.is_audio_related)

    def test_a_category_override_is_not_reverted(self) -> None:
        first = self._approve(self._submit())
        job = self.session.get(Job, first.job_id)
        assert job is not None
        job.categories_override = ["audio_ee"]
        job.job_categories = ["audio_ee"]
        self.session.flush()

        self._approve(self._submit())
        self.session.refresh(job)
        self.assertEqual(job.job_categories, ["audio_ee"])

    def test_a_different_url_at_the_same_company_is_a_new_job(self) -> None:
        self._approve(self._submit(url="https://example.com/jobs/1"))
        self._approve(self._submit(url="https://example.com/jobs/2"))
        self.assertEqual(self.session.query(Job).count(), 2)

    def test_an_unmatched_company_no_longer_stacks_duplicates(self) -> None:
        first = self._approve(self._submit(company="Nobody Ltd"))
        second = self._approve(self._submit(company="Nobody Ltd"))
        self.assertEqual(second.job_id, first.job_id)
        self.assertEqual(self.session.query(Job).count(), 1)

    def test_an_unmatched_company_does_not_match_a_known_company_url(self) -> None:
        known = self._approve(self._submit(company="Acme Audio"))
        other = self._approve(self._submit(company="Nobody Ltd"))
        self.assertNotEqual(other.job_id, known.job_id)
        self.assertEqual(self.session.query(Job).count(), 2)

    def test_country_is_stored_on_a_community_job(self) -> None:
        result = self._approve(self._submit(location="Berlin, Germany"))
        job = self.session.get(Job, result.job_id)
        assert job is not None
        self.assertEqual(job.country, "DE")


if __name__ == "__main__":
    unittest.main()
