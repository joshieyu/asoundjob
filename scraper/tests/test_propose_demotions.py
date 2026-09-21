from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper.models import Base, Company, Job
from scraper.propose_demotions import (
    DemotionCandidate,
    filter_candidates,
    gather_candidates,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


class PropseDemotionsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def add_company(self, name: str, slug: str, **kwargs) -> Company:
        defaults = dict(
            name=name,
            slug=slug,
            category="Audio Software",
            careers_url="https://example.com/careers",
            verified=True,
            source="auto",
        )
        defaults.update(kwargs)
        company = Company(**defaults)
        self.session.add(company)
        self.session.flush()
        return company

    def add_job(self, company: Company, **kwargs) -> Job:
        defaults = dict(
            company_id=company.id,
            title="Audio Engineer",
            url=f"https://example.com/{company.slug}/{kwargs.get('external_id', '1')}",
            is_active=True,
            is_audio_related=True,
            source="scraper",
        )
        defaults.update(kwargs)
        job = Job(**defaults)
        self.session.add(job)
        self.session.flush()
        return job

    def candidate_for(self, name: str) -> DemotionCandidate:
        candidates = gather_candidates(self.session)
        matches = [c for c in candidates if c.name == name]
        self.assertEqual(len(matches), 1, f"expected exactly one candidate for {name}")
        return matches[0]


class TestZeroRowCompanyIsACandidate(PropseDemotionsTestCase):
    def test_verified_scraped_company_with_no_jobs_now_appears(self) -> None:
        self.add_company("No Rows At All Co", "no-rows-at-all-co")
        candidate = self.candidate_for("No Rows At All Co")
        self.assertEqual(candidate.active_rows, 0)
        self.assertEqual(candidate.grade, "silent")


class TestPopulationAndScope(PropseDemotionsTestCase):
    def test_blocked_company_grades_unscraped(self) -> None:
        self.add_company("Blocked Co", "blocked-co", scrape_blocked=True)
        candidate = self.candidate_for("Blocked Co")
        self.assertEqual(candidate.grade, "unscraped")

    def test_missing_careers_url_grades_unscraped(self) -> None:
        self.add_company("No Url Co", "no-url-co", careers_url=None)
        candidate = self.candidate_for("No Url Co")
        self.assertEqual(candidate.grade, "unscraped")

    def test_audio_scope_is_populated_on_candidate(self) -> None:
        self.add_company("Native Scope Co", "native-scope-co", audio_scope="native")
        candidate = self.candidate_for("Native Scope Co")
        self.assertEqual(candidate.audio_scope, "native")


class TestMinActiveOnlyAppliesToFurnitureAndThin(PropseDemotionsTestCase):
    def test_silent_candidate_survives_min_active_filter(self) -> None:
        self.add_company("Silent Zero Rows Co", "silent-zero-rows-co")
        candidates = gather_candidates(self.session)
        kept = filter_candidates(
            candidates,
            grades=["silent"],
            min_active=3,
            min_consecutive_failures=3,
        )
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].name, "Silent Zero Rows Co")

    def test_thin_candidate_below_min_active_is_dropped(self) -> None:
        company = self.add_company("Thin Below Threshold Co", "thin-below-threshold-co")
        for i in range(4):
            self.add_job(
                company,
                title=f"Audio Engineer {i}",
                external_id=str(i),
            )
        candidate = self.candidate_for("Thin Below Threshold Co")
        self.assertEqual(candidate.grade, "thin")
        candidates = gather_candidates(self.session)
        kept = filter_candidates(
            candidates,
            grades=["thin"],
            min_active=5,
            min_consecutive_failures=3,
        )
        self.assertEqual(kept, [])


if __name__ == "__main__":
    unittest.main()
