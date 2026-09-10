from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper import backfill_relevance
from scraper.deduplicator import reconcile_company_jobs
from scraper.models import Base, Company, Job
from scraper.normalizer import NormalizedJob
from scraper.overrides import effective_categories, effective_is_audio


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_company(session) -> Company:
    company = Company(
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url="https://example.com/careers",
        verified=True,
        source="auto",
        audio_scope="native",
    )
    session.add(company)
    session.flush()
    return company


class TestEffectiveHelpers(unittest.TestCase):
    def test_effective_categories_returns_override_when_set(self) -> None:
        job = Job(categories_override=["foo"])
        self.assertEqual(effective_categories(job, ["bar"]), ["foo"])

    def test_effective_categories_falls_back_to_computed(self) -> None:
        job = Job(categories_override=None)
        self.assertEqual(effective_categories(job, ["bar"]), ["bar"])

    def test_effective_is_audio_returns_override_when_set(self) -> None:
        job = Job(is_audio_related_override=False)
        self.assertEqual(effective_is_audio(job, True), False)

    def test_effective_is_audio_falls_back_to_computed(self) -> None:
        job = Job(is_audio_related_override=None)
        self.assertEqual(effective_is_audio(job, True), True)


class TestBackfillHonorsOverride(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.company = make_company(self.session)

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_override_survives_a_full_backfill_cycle(self) -> None:
        job = Job(
            company_id=self.company.id,
            title="Marketing Manager",
            description=None,
            url="https://example.com/jobs/1",
            location=None,
            job_categories=["audio_software"],
            categories_override=["audio_software"],
            is_audio_related=True,
            is_audio_related_override=True,
            is_active=True,
            external_id="1",
            source="scraper",
        )
        self.session.add(job)
        self.session.flush()

        @contextmanager
        def fake_session_scope():
            yield self.session
            self.session.flush()

        with mock.patch.object(
            backfill_relevance, "session_scope", fake_session_scope
        ):
            backfill_relevance.backfill(dry_run=False)

        self.session.expire_all()
        refreshed = self.session.get(Job, job.id)
        assert refreshed is not None

        self.assertEqual(refreshed.categories_override, ["audio_software"])
        self.assertTrue(refreshed.is_audio_related_override)
        self.assertEqual(refreshed.job_categories, ["audio_software"])
        self.assertTrue(refreshed.is_audio_related)


class TestDeduplicatorHonorsOverride(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.company = make_company(self.session)

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_override_survives_the_update_path(self) -> None:
        job = Job(
            company_id=self.company.id,
            title="Marketing Manager",
            url="https://example.com/jobs/1",
            job_categories=["audio_software"],
            categories_override=["audio_software"],
            is_audio_related=True,
            is_audio_related_override=True,
            is_active=True,
            external_id="1",
            source="scraper",
        )
        self.session.add(job)
        self.session.flush()

        refetched = NormalizedJob(
            title="Marketing Manager (updated)",
            url="https://example.com/jobs/1",
            external_id="1",
            job_categories=["marketing"],
            is_audio_related=False,
        )

        stats = reconcile_company_jobs(
            self.session, self.company, [refetched], trust_empty=False
        )
        self.session.flush()

        self.assertEqual(stats.updated, 1)
        refreshed = self.session.get(Job, job.id)
        assert refreshed is not None

        self.assertEqual(refreshed.title, "Marketing Manager (updated)")
        self.assertEqual(refreshed.categories_override, ["audio_software"])
        self.assertTrue(refreshed.is_audio_related_override)
        self.assertEqual(refreshed.job_categories, ["audio_software"])
        self.assertTrue(refreshed.is_audio_related)


class TestNotAudioOverrideSurvives(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.company = make_company(self.session)

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def _audio_job(self) -> Job:
        job = Job(
            company_id=self.company.id,
            title="Senior Audio DSP Engineer",
            description="Design audio signal processing algorithms for loudspeakers.",
            url="https://example.com/jobs/9",
            job_categories=["audio_dsp_embedded"],
            is_audio_related=True,
            is_active=True,
            external_id="9",
            source="scraper",
        )
        self.session.add(job)
        self.session.flush()
        return job

    def test_scorer_would_admit_this_job_without_an_override(self) -> None:
        job = self._audio_job()

        @contextmanager
        def fake_session_scope():
            yield self.session
            self.session.flush()

        with mock.patch.object(backfill_relevance, "session_scope", fake_session_scope):
            backfill_relevance.backfill(dry_run=False)

        self.session.expire_all()
        refreshed = self.session.get(Job, job.id)
        assert refreshed is not None
        self.assertTrue(refreshed.is_audio_related)
        self.assertNotEqual(refreshed.job_categories, [])

    def test_not_audio_override_survives_a_backfill(self) -> None:
        job = self._audio_job()
        job.is_audio_related_override = False
        job.is_audio_related = False
        self.session.flush()

        @contextmanager
        def fake_session_scope():
            yield self.session
            self.session.flush()

        with mock.patch.object(backfill_relevance, "session_scope", fake_session_scope):
            backfill_relevance.backfill(dry_run=False)

        self.session.expire_all()
        refreshed = self.session.get(Job, job.id)
        assert refreshed is not None
        self.assertFalse(refreshed.is_audio_related)
        self.assertFalse(refreshed.is_audio_related_override)

    def test_not_audio_override_survives_the_scrape_update_path(self) -> None:
        job = self._audio_job()
        job.is_audio_related_override = False
        job.is_audio_related = False
        self.session.flush()

        refetched = NormalizedJob(
            title="Senior Audio DSP Engineer",
            url="https://example.com/jobs/9",
            external_id="9",
            job_categories=["audio_dsp_embedded"],
            is_audio_related=True,
        )
        reconcile_company_jobs(
            self.session, self.company, [refetched], trust_empty=False
        )
        self.session.flush()

        refreshed = self.session.get(Job, job.id)
        assert refreshed is not None
        self.assertFalse(refreshed.is_audio_related)

    def test_category_override_replaces_a_non_empty_computed_value(self) -> None:
        job = self._audio_job()
        job.categories_override = ["audio_systems"]
        self.session.flush()

        @contextmanager
        def fake_session_scope():
            yield self.session
            self.session.flush()

        with mock.patch.object(backfill_relevance, "session_scope", fake_session_scope):
            backfill_relevance.backfill(dry_run=False)

        self.session.expire_all()
        refreshed = self.session.get(Job, job.id)
        assert refreshed is not None
        self.assertEqual(refreshed.job_categories, ["audio_systems"])


if __name__ == "__main__":
    unittest.main()
