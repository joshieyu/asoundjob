from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scraper.diagnose_failures import select_companies
from scraper.models import Base, Company, ScrapeLog


class TestSelectCompanies(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.now = datetime.now(timezone.utc)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def _company(self, name: str, careers_url: str | None) -> Company:
        company = Company(
            name=name,
            slug=name.lower().replace(" ", "-"),
            category="Audio Software",
            careers_url=careers_url,
            verified=True,
        )
        self.session.add(company)
        self.session.flush()
        return company

    def _log(self, company: Company, status: str, minutes_ago: int) -> None:
        started = self.now - timedelta(minutes=minutes_ago)
        self.session.add(
            ScrapeLog(
                company_id=company.id,
                started_at=started,
                finished_at=started,
                status=status,
                jobs_found=0,
            )
        )
        self.session.flush()

    def test_failed_selects_only_latest_failures(self) -> None:
        bad = self._company("Bad Co", "https://bad.example/careers")
        self._log(bad, "failed", 10)
        names = [row[1] for row in select_companies(self.session, "failed")]
        self.assertEqual(names, ["Bad Co"])

    def test_recovered_company_is_not_a_failure(self) -> None:
        company = self._company("Recovered", "https://ok.example/careers")
        self._log(company, "failed", 20)
        self._log(company, "success", 5)
        self.assertEqual(select_companies(self.session, "failed"), [])
        names = [row[1] for row in select_companies(self.session, "success")]
        self.assertEqual(names, ["Recovered"])

    def test_regressed_company_is_not_a_success(self) -> None:
        company = self._company("Regressed", "https://x.example/careers")
        self._log(company, "success", 20)
        self._log(company, "failed", 5)
        self.assertEqual(select_companies(self.session, "success"), [])
        names = [row[1] for row in select_companies(self.session, "failed")]
        self.assertEqual(names, ["Regressed"])

    def test_all_returns_both(self) -> None:
        good = self._company("Good Co", "https://good.example/careers")
        bad = self._company("Bad Co", "https://bad.example/careers")
        self._log(good, "success", 5)
        self._log(bad, "failed", 5)
        names = sorted(row[1] for row in select_companies(self.session, "all"))
        self.assertEqual(names, ["Bad Co", "Good Co"])

    def test_company_without_careers_url_is_skipped(self) -> None:
        company = self._company("No URL", None)
        self._log(company, "success", 5)
        self.assertEqual(select_companies(self.session, "success"), [])

    def test_blank_careers_url_is_skipped(self) -> None:
        company = self._company("Blank URL", "   ")
        self._log(company, "success", 5)
        self.assertEqual(select_companies(self.session, "success"), [])

    def test_never_scraped_company_is_absent_from_all(self) -> None:
        self._company("Never Scraped", "https://never.example/careers")
        self.assertEqual(select_companies(self.session, "all"), [])

    def test_unknown_status_raises(self) -> None:
        with self.assertRaises(ValueError):
            select_companies(self.session, "partial")

    def test_url_is_stripped(self) -> None:
        company = self._company("Spaced", "  https://spaced.example/careers  ")
        self._log(company, "success", 5)
        rows = select_companies(self.session, "success")
        self.assertEqual(rows[0][2], "https://spaced.example/careers")


if __name__ == "__main__":
    unittest.main()
