from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.query import apply_job_filters, fetch_job_page
from scraper.models import Base, Company, Job

FIXTURES = [
    ("Acoustic Engineer", "Berlin, Germany", "DE"),
    ("Audio DSP Engineer", "Hamburg", "DE"),
    ("Audio Test Engineer", "San Francisco, CA", "US"),
    ("Transducer Engineer", "London, UK", "GB"),
    ("Audio Systems Engineer", "2 Locations", None),
    ("Audio Software Engineer", None, None),
]


class TestCountryFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        company = Company(
            name="Acme Audio",
            slug="acme-audio",
            category="Professional Audio & Live Sound",
            verified=True,
        )
        self.session.add(company)
        self.session.flush()
        for index, (title, location, country) in enumerate(FIXTURES):
            self.session.add(
                Job(
                    company_id=company.id,
                    title=title,
                    url=f"https://example.com/{index}",
                    location=location,
                    country=country,
                    is_active=True,
                    is_audio_related=True,
                    external_id=str(index),
                )
            )
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def _page(self, country=None):
        stmt = apply_job_filters(select(Job), country=country)
        jobs, total = fetch_job_page(
            self.session, stmt, 1, 50, "newest", country_first=country
        )
        return jobs, total

    def test_no_country_returns_everything(self) -> None:
        _, total = self._page()
        self.assertEqual(total, len(FIXTURES))

    def test_other_countries_are_excluded(self) -> None:
        jobs, _ = self._page("DE")
        self.assertEqual({job.country for job in jobs}, {"DE", None})

    def test_unplaced_jobs_are_kept_so_none_are_hidden(self) -> None:
        jobs, total = self._page("DE")
        self.assertEqual(total, 4)
        self.assertEqual(sum(1 for job in jobs if job.country is None), 2)

    def test_matches_are_ordered_ahead_of_unplaced_jobs(self) -> None:
        jobs, _ = self._page("DE")
        countries = [job.country for job in jobs]
        self.assertEqual(countries[:2], ["DE", "DE"])
        self.assertEqual(countries[2:], [None, None])

    def test_country_code_is_case_insensitive(self) -> None:
        self.assertEqual(self._page("de")[1], self._page("DE")[1])

    def test_unknown_country_code_returns_only_unplaced_jobs(self) -> None:
        jobs, _ = self._page("ZZ")
        self.assertTrue(all(job.country is None for job in jobs))

    def test_country_name_is_exposed_for_display(self) -> None:
        jobs, _ = self._page("DE")
        self.assertEqual(jobs[0].country_name, "Germany")
        self.assertIsNone(jobs[-1].country_name)


if __name__ == "__main__":
    unittest.main()
