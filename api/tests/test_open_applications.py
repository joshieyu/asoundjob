from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.routers.companies import list_open_applications, router
from scraper.models import Base, Company


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


class TestOpenApplications(unittest.TestCase):
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

    def test_returns_only_flagged_companies(self) -> None:
        self._add(
            company("Celestion", "celestion", open_application=True),
            company("Bose", "bose", open_application=False),
        )
        result = list_open_applications(db=self.session)
        self.assertEqual(result.total, 1)
        self.assertEqual([c.name for c in result.companies], ["Celestion"])

    def test_unverified_companies_are_excluded(self) -> None:
        self._add(
            company("Celestion", "celestion", open_application=True),
            company("Ghost Audio", "ghost", open_application=True, verified=False),
        )
        result = list_open_applications(db=self.session)
        self.assertEqual([c.name for c in result.companies], ["Celestion"])

    def test_empty_when_nothing_is_flagged(self) -> None:
        self._add(company("Bose", "bose"))
        result = list_open_applications(db=self.session)
        self.assertEqual(result.total, 0)
        self.assertEqual(result.companies, [])

    def test_sorted_by_name(self) -> None:
        self._add(
            company("Sonible", "sonible", open_application=True),
            company("Arturia", "arturia", open_application=True),
            company("DALI", "dali", open_application=True),
        )
        result = list_open_applications(db=self.session)
        self.assertEqual(
            [c.name for c in result.companies], ["Arturia", "DALI", "Sonible"]
        )

    def test_carries_the_careers_url(self) -> None:
        self._add(company("Celestion", "celestion", open_application=True))
        result = list_open_applications(db=self.session)
        self.assertEqual(
            result.companies[0].careers_url, "https://celestion.example/careers"
        )

    def test_default_flag_is_false(self) -> None:
        self._add(company("Bose", "bose"))
        row = self.session.query(Company).one()
        self.assertFalse(row.open_application)


class TestRouteOrdering(unittest.TestCase):
    def test_open_applications_is_registered_before_the_slug_route(self) -> None:
        paths = [getattr(r, "path", "") for r in router.routes]
        self.assertIn("/api/companies/open-applications", paths)
        self.assertIn("/api/companies/{slug}", paths)
        self.assertLess(
            paths.index("/api/companies/open-applications"),
            paths.index("/api/companies/{slug}"),
            "the slug route would swallow /open-applications",
        )


if __name__ == "__main__":
    unittest.main()
