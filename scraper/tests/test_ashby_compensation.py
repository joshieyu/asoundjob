from __future__ import annotations

import unittest

from scraper.config import load_settings
from scraper.normalizer import Normalizer
from scraper.scrapers.ats.ashby import API_URL, compensation, parse_jobs
from scraper.scrapers.base import RawJob


def salary(low: object, high: object, interval: str = "1 YEAR", currency: str = "USD") -> dict:
    return {
        "summaryComponents": [
            {"compensationType": "EquityCashValue", "minValue": None, "maxValue": None},
            {
                "compensationType": "Salary",
                "minValue": low,
                "maxValue": high,
                "currencyCode": currency,
                "interval": interval,
            },
        ]
    }


class AshbyCompensationTest(unittest.TestCase):
    def test_api_requests_compensation(self) -> None:
        self.assertIn("includeCompensation=true", API_URL)

    def test_annual_salary_range(self) -> None:
        self.assertEqual(compensation(salary(220000, 350000)), (220000, 350000, "USD"))

    def test_hourly_is_annualized(self) -> None:
        self.assertEqual(compensation(salary(25, 30, "1 HOUR")), (52000, 62400, "USD"))

    def test_unknown_interval_and_bad_values_are_ignored(self) -> None:
        self.assertEqual(compensation(salary(5000, 7000, "1 MONTH")), (None, None, None))
        self.assertEqual(compensation(salary(None, None)), (None, None, None))
        self.assertEqual(compensation(salary(300000, 200000)), (None, None, None))
        self.assertEqual(compensation(None), (None, None, None))

    def test_single_bound(self) -> None:
        self.assertEqual(compensation(salary(90000, None, currency="EUR")), (90000, None, "EUR"))

    def test_parse_jobs_carries_salary(self) -> None:
        data = {
            "jobs": [
                {
                    "id": "abc",
                    "title": "Audio Engineer",
                    "jobUrl": "https://jobs.ashbyhq.com/x/abc",
                    "compensation": salary(120000, 150000),
                }
            ]
        }
        job = parse_jobs(data)[0]
        found = (job.salary_min, job.salary_max, job.salary_currency)
        self.assertEqual(found, (120000, 150000, "USD"))


class StructuredSalaryWinsTest(unittest.TestCase):
    def test_structured_salary_overrides_text(self) -> None:
        raw = RawJob(
            title="Audio Engineer",
            url="https://example.com/1",
            description="We raised $30,000,000 - $40,000,000 last year.",
            salary_min=100000,
            salary_max=130000,
            salary_currency="USD",
        )
        job = Normalizer(load_settings()).normalize(raw)
        found = (job.salary_min, job.salary_max, job.salary_currency)
        self.assertEqual(found, (100000, 130000, "USD"))

    def test_text_is_used_without_structured_salary(self) -> None:
        raw = RawJob(
            title="Audio Engineer",
            url="https://example.com/2",
            description="Pay: $90,000 - $110,000 per year",
        )
        job = Normalizer(load_settings()).normalize(raw)
        self.assertEqual((job.salary_min, job.salary_max), (90000, 110000))


if __name__ == "__main__":
    unittest.main()
