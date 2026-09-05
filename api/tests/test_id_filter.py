from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.query import apply_job_filters, fetch_job_page
from api.routers.jobs import MAX_ID_FILTER, _parse_ids
from scraper.models import Base, Company, Job

TITLES = [
    "Acoustic Engineer",
    "Audio DSP Engineer",
    "Transducer Engineer",
    "Audio Systems Engineer",
]


class TestParseIds(unittest.TestCase):
    def test_none_means_no_filter(self) -> None:
        self.assertIsNone(_parse_ids(None))

    def test_parses_a_csv(self) -> None:
        self.assertEqual(_parse_ids("3,1,2"), [3, 1, 2])

    def test_tolerates_spaces(self) -> None:
        self.assertEqual(_parse_ids(" 3 , 1 "), [3, 1])

    def test_drops_non_numeric_entries(self) -> None:
        self.assertEqual(_parse_ids("3,abc,-1,2"), [3, 2])

    def test_empty_string_yields_empty_list_not_none(self) -> None:
        self.assertEqual(_parse_ids(""), [])

    def test_is_bounded(self) -> None:
        raw = ",".join(str(n) for n in range(1, MAX_ID_FILTER + 50))
        self.assertEqual(len(_parse_ids(raw) or []), MAX_ID_FILTER)


class TestIdFilter(unittest.TestCase):
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
        self.ids = []
        for index, title in enumerate(TITLES):
            job = Job(
                company_id=company.id,
                title=title,
                url=f"https://example.com/{index}",
                remote=index == 0,
                is_active=True,
                is_audio_related=True,
                source="scraper",
                external_id=str(index),
            )
            self.session.add(job)
            self.session.flush()
            self.ids.append(job.id)

    def tearDown(self) -> None:
        self.session.close()

    def _titles(self, **kwargs) -> list[str]:
        stmt = apply_job_filters(select(Job), **kwargs)
        jobs, _ = fetch_job_page(self.session, stmt, 1, 50)
        return sorted(job.title for job in jobs)

    def test_no_ids_returns_everything(self) -> None:
        self.assertEqual(len(self._titles()), 4)

    def test_ids_restrict_the_result(self) -> None:
        self.assertEqual(
            self._titles(ids=[self.ids[0], self.ids[2]]),
            ["Acoustic Engineer", "Transducer Engineer"],
        )

    def test_empty_id_list_returns_nothing(self) -> None:
        self.assertEqual(self._titles(ids=[]), [])

    def test_unknown_id_returns_nothing(self) -> None:
        self.assertEqual(self._titles(ids=[9_999_999]), [])

    def test_ids_compose_with_other_filters(self) -> None:
        self.assertEqual(
            self._titles(ids=self.ids, remote=True), ["Acoustic Engineer"]
        )


if __name__ == "__main__":
    unittest.main()
