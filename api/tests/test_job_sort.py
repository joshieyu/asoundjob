from __future__ import annotations

import unittest
from datetime import date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api.query import apply_job_filters, fetch_job_page
from scraper.models import Base, Job


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


class TestNewestSortUsesSeenDate(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        rows = [
            ("Posted last month", date(2026, 10, 1), datetime(2026, 10, 2, 9)),
            ("Undated, found today", None, datetime(2026, 11, 11, 22)),
            ("Posted yesterday", date(2026, 11, 10), datetime(2026, 11, 10, 12)),
            ("Undated, found in October", None, datetime(2026, 10, 15, 8)),
        ]
        for title, posted, scraped in rows:
            self.session.add(
                Job(
                    title=title,
                    url=f"https://example.com/{title.replace(' ', '-')}",
                    posted_date=posted,
                    scraped_at=scraped,
                    is_active=True,
                    is_audio_related=True,
                )
            )
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()

    def titles(self, sort: str) -> list:
        jobs, _ = fetch_job_page(self.session, apply_job_filters(select(Job)), 1, 25, sort)
        return [job.title for job in jobs]

    def test_undated_jobs_sort_by_the_day_they_were_found(self) -> None:
        self.assertEqual(
            self.titles("newest"),
            [
                "Undated, found today",
                "Posted yesterday",
                "Undated, found in October",
                "Posted last month",
            ],
        )

    def test_oldest_is_the_reverse(self) -> None:
        self.assertEqual(
            self.titles("oldest"),
            [
                "Posted last month",
                "Undated, found in October",
                "Posted yesterday",
                "Undated, found today",
            ],
        )


if __name__ == "__main__":
    unittest.main()
