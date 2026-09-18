from __future__ import annotations

import asyncio
import unittest
from contextlib import contextmanager
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper import main as scraper_main
from scraper.config import load_settings
from scraper.models import Base, Company
from scraper.scrapers.base import ScrapeResult


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_session_allowing_null_scrape_blocked():
    engine = create_engine("sqlite:///:memory:")
    column = Company.__table__.c.scrape_blocked
    original_nullable = column.nullable
    column.nullable = True
    try:
        Base.metadata.create_all(engine)
    finally:
        column.nullable = original_nullable
    return sessionmaker(bind=engine)()


def make_company(session, slug: str, scrape_blocked: bool = False) -> Company:
    company = Company(
        name=slug,
        slug=slug,
        category="Audio Software",
        careers_url=f"https://{slug}.example/careers",
        verified=True,
        source="auto",
        scrape_method="http",
        scrape_blocked=scrape_blocked,
    )
    session.add(company)
    session.flush()
    return company


class FakePipeline:
    def __init__(self, settings) -> None:
        pass

    async def scrape_company(self, company: Company) -> ScrapeResult:
        return ScrapeResult(company_id=company.id, success=False, method="http", error="test")

    async def close(self) -> None:
        return None


class RunCycleBlockedFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def _run(self, only_slug: str | None = None):
        @contextmanager
        def fake_session_scope():
            yield self.session
            self.session.flush()

        with mock.patch.object(scraper_main, "session_scope", fake_session_scope), \
                mock.patch.object(scraper_main, "ScrapePipeline", FakePipeline):
            return asyncio.run(
                scraper_main.run_cycle(load_settings(), None, only_slug, True)
            )

    def test_blocked_company_is_not_scraped(self) -> None:
        make_company(self.session, "blocked-co", scrape_blocked=True)
        cycle = self._run()
        self.assertEqual(cycle.companies_attempted, 0)
        self.assertEqual(cycle.blocked_skipped, 1)

    def test_unblocked_company_is_scraped(self) -> None:
        make_company(self.session, "unblocked-co", scrape_blocked=False)
        cycle = self._run()
        self.assertEqual(cycle.companies_attempted, 1)
        self.assertEqual(cycle.blocked_skipped, 0)

    def test_null_scrape_blocked_is_scraped(self) -> None:
        self.session = make_session_allowing_null_scrape_blocked()
        make_company(self.session, "null-blocked-co", scrape_blocked=None)
        cycle = self._run()
        self.assertEqual(cycle.companies_attempted, 1)
        self.assertEqual(cycle.blocked_skipped, 0)

    def test_blocked_company_scraped_when_named_with_only_slug(self) -> None:
        make_company(self.session, "blocked-co", scrape_blocked=True)
        cycle = self._run(only_slug="blocked-co")
        self.assertEqual(cycle.companies_attempted, 1)
        self.assertEqual(cycle.blocked_skipped, 0)


if __name__ == "__main__":
    unittest.main()
