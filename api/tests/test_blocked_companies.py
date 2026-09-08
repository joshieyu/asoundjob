from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.routers.companies import list_blocked_companies, router
from scraper.models import Base, Company, Job


def company(name: str, slug: str, **kwargs) -> Company:
    base = dict(
        name=name,
        slug=slug,
        category="Transducer & Driver Manufacturers",
        careers_url=f"https://{slug}.example/careers",
        verified=True,
        source="auto",
    )
    base.update(kwargs)
    return Company(**base)


class TestBlockedCompanies(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()

    def _add(self, *companies) -> None:
        for c in companies:
            self.session.add(c)
        self.session.flush()

    def _job(self, company_id: int, **kwargs) -> Job:
        base = dict(
            company_id=company_id,
            title="Audio Engineer",
            url="https://example.com/job",
            is_active=True,
            is_audio_related=True,
        )
        base.update(kwargs)
        return Job(**base)

    def test_returns_only_flagged_companies(self) -> None:
        self._add(
            company("Celestion", "celestion", scrape_blocked=True),
            company("Bose", "bose", scrape_blocked=False),
        )
        result = list_blocked_companies(db=self.session)
        self.assertEqual(result.total, 1)
        self.assertEqual([c.name for c in result.companies], ["Celestion"])

    def test_unverified_companies_are_still_listed(self) -> None:
        self._add(
            company("Celestion", "celestion", scrape_blocked=True),
            company("Ghost Audio", "ghost", scrape_blocked=True, verified=False),
        )
        result = list_blocked_companies(db=self.session)
        self.assertEqual(
            [c.name for c in result.companies], ["Celestion", "Ghost Audio"]
        )

    def test_company_with_active_audio_job_is_excluded(self) -> None:
        c = company("Celestion", "celestion", scrape_blocked=True)
        self._add(c)
        self._add(self._job(c.id, is_active=True, is_audio_related=True))
        result = list_blocked_companies(db=self.session)
        self.assertEqual(result.total, 0)
        self.assertEqual(result.companies, [])

    def test_company_with_only_inactive_job_is_still_returned(self) -> None:
        c = company("Celestion", "celestion", scrape_blocked=True)
        self._add(c)
        self._add(self._job(c.id, is_active=False, is_audio_related=True))
        result = list_blocked_companies(db=self.session)
        self.assertEqual([c.name for c in result.companies], ["Celestion"])

    def test_company_with_only_non_audio_job_is_still_returned(self) -> None:
        c = company("Celestion", "celestion", scrape_blocked=True)
        self._add(c)
        self._add(self._job(c.id, is_active=True, is_audio_related=False))
        result = list_blocked_companies(db=self.session)
        self.assertEqual([c.name for c in result.companies], ["Celestion"])

    def test_sorted_by_name(self) -> None:
        self._add(
            company("Sonible", "sonible", scrape_blocked=True),
            company("Arturia", "arturia", scrape_blocked=True),
            company("DALI", "dali", scrape_blocked=True),
        )
        result = list_blocked_companies(db=self.session)
        self.assertEqual(
            [c.name for c in result.companies], ["Arturia", "DALI", "Sonible"]
        )

    def test_empty_when_nothing_is_flagged(self) -> None:
        self._add(company("Bose", "bose"))
        result = list_blocked_companies(db=self.session)
        self.assertEqual(result.total, 0)
        self.assertEqual(result.companies, [])

    def test_carries_the_careers_url(self) -> None:
        self._add(company("Celestion", "celestion", scrape_blocked=True))
        result = list_blocked_companies(db=self.session)
        self.assertEqual(
            result.companies[0].careers_url, "https://celestion.example/careers"
        )

    def test_default_flag_is_false(self) -> None:
        self._add(company("Bose", "bose"))
        row = self.session.query(Company).one()
        self.assertFalse(row.scrape_blocked)


class TestRouteOrdering(unittest.TestCase):
    def test_blocked_is_registered_before_the_slug_route(self) -> None:
        paths = [getattr(r, "path", "") for r in router.routes]
        self.assertIn("/api/companies/blocked", paths)
        self.assertIn("/api/companies/{slug}", paths)
        self.assertLess(
            paths.index("/api/companies/blocked"),
            paths.index("/api/companies/{slug}"),
            "the slug route would swallow /blocked",
        )


if __name__ == "__main__":
    unittest.main()
