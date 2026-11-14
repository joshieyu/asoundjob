from __future__ import annotations

import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.routers import admin as admin_router
from api.schemas import AdminJobAudioUpdate
from scraper.models import Base, Company, Job
from scraper.overrides import effective_is_audio

ML_DESCRIPTION = (
    "<b>Responsibilities</b><ul><li>Build ML pipelines for calls and meetings.</li>"
    "<li>Train and evaluate models.</li></ul>"
)


class TestJobAudioOverride(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.company = Company(
            name="Bigsoft",
            slug="bigsoft",
            category="Consumer Electronics & Tech",
            audio_scope="partial",
            verified=True,
        )
        self.session.add(self.company)
        self.session.flush()
        self.job = Job(
            company_id=self.company.id,
            title="Principal Applied Scientist - ML & Deep Learning",
            description=ML_DESCRIPTION,
            url="https://apply.careers.bigsoft.com/careers/job/1970393557050580",
            is_active=True,
            is_audio_related=False,
            relevance_score=20,
            external_id="1970393557050580",
            source="scraper",
        )
        self.session.add(self.job)
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def list_jobs(self, search=None, show="all"):
        return admin_router.admin_list_jobs(
            search=search, show=show, page=1, per_page=25, db=self.session, _="admin"
        )

    def test_search_by_pasted_url_with_tracking_params(self) -> None:
        result = self.list_jobs(
            search="https://apply.careers.bigsoft.com/careers/job/1970393557050580?utm_source=x"
        )
        self.assertEqual([row.id for row in result["items"]], [self.job.id])
        self.assertFalse(result["items"][0].on_board)

    def test_hidden_filter_lists_active_non_audio_jobs(self) -> None:
        self.assertEqual(len(self.list_jobs(show="hidden")["items"]), 1)
        self.assertEqual(len(self.list_jobs(show="overridden")["items"]), 0)

    def test_show_on_board_sets_the_override(self) -> None:
        row = admin_router.admin_set_job_audio(
            self.job.id, AdminJobAudioUpdate(is_audio_related=True), self.session, "admin"
        )
        self.assertTrue(row.on_board)
        self.assertTrue(row.is_audio_related_override)
        self.assertTrue(self.job.is_audio_related)
        self.assertEqual(len(self.list_jobs(show="overridden")["items"]), 1)

    def test_override_survives_a_rescore(self) -> None:
        admin_router.admin_set_job_audio(
            self.job.id, AdminJobAudioUpdate(is_audio_related=True), self.session, "admin"
        )
        admin_router.rescore_company_jobs(self.session, self.company)
        self.assertTrue(self.job.is_audio_related)
        self.assertTrue(effective_is_audio(self.job, False))

    def test_clearing_the_override_returns_to_the_score(self) -> None:
        admin_router.admin_set_job_audio(
            self.job.id, AdminJobAudioUpdate(is_audio_related=True), self.session, "admin"
        )
        row = admin_router.admin_set_job_audio(
            self.job.id, AdminJobAudioUpdate(is_audio_related=None), self.session, "admin"
        )
        self.assertIsNone(row.is_audio_related_override)
        self.assertFalse(row.is_audio_related)
        self.assertFalse(row.on_board)

    def test_unknown_job_is_404(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            admin_router.admin_set_job_audio(
                999, AdminJobAudioUpdate(is_audio_related=True), self.session, "admin"
            )
        self.assertEqual(ctx.exception.status_code, 404)

