from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest import mock

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from scraper import main as scraper_main
from scraper.config import load_settings
from scraper.models import Base, Company, ScrapeLog
from scraper.normalizer import Normalizer
from scraper.scrapers.base import ScrapeResult


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_company(session, consecutive_failures: int = 0) -> Company:
    company = Company(
        name="Flaky Audio Co",
        slug="flaky-audio-co",
        category="Audio Software",
        careers_url="https://flaky-audio-co.example/careers",
        verified=True,
        source="auto",
        scrape_method="http",
        consecutive_failures=consecutive_failures,
    )
    session.add(company)
    session.flush()
    return company


class PersistResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        self.normalizer = Normalizer(load_settings())

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def _fake_session_scope(self):
        @contextmanager
        def fake_session_scope():
            yield self.session
            self.session.flush()

        return fake_session_scope

    def test_failure_increments_consecutive_failures(self) -> None:
        company = make_company(self.session, consecutive_failures=0)
        result = ScrapeResult(
            company_id=company.id, success=False, method="http", error="boom"
        )
        with mock.patch.object(
            scraper_main, "session_scope", self._fake_session_scope()
        ):
            scraper_main.persist_result(self.normalizer, company, result)
            scraper_main.persist_result(self.normalizer, company, result)

        self.session.refresh(company)
        self.assertEqual(company.consecutive_failures, 2)

    def test_failure_still_logs_when_company_is_missing(self) -> None:
        missing = Company(
            id=99999,
            name="Ghost Co",
            slug="ghost-co",
            category="Audio Software",
            verified=True,
            source="auto",
            scrape_method="http",
        )
        result = ScrapeResult(
            company_id=missing.id, success=False, method="http", error="boom"
        )
        with mock.patch.object(
            scraper_main, "session_scope", self._fake_session_scope()
        ):
            scraper_main.persist_result(self.normalizer, missing, result)

        logs = self.session.execute(select(ScrapeLog)).scalars().all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].status, "failed")

    def test_success_resets_consecutive_failures_to_zero(self) -> None:
        company = make_company(self.session, consecutive_failures=2)
        result = ScrapeResult(
            company_id=company.id,
            success=True,
            method="http",
            jobs=[],
            trust_empty=True,
        )
        with mock.patch.object(
            scraper_main, "session_scope", self._fake_session_scope()
        ):
            scraper_main.persist_result(self.normalizer, company, result)

        self.session.refresh(company)
        self.assertEqual(company.consecutive_failures, 0)


if __name__ == "__main__":
    unittest.main()
