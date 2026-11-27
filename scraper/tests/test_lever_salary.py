from __future__ import annotations

import unittest

from scraper.scrapers.ats.lever import parse_postings, salary_range


class LeverSalaryTest(unittest.TestCase):
    def test_yearly_range(self) -> None:
        value = {"min": 55000, "max": 85000, "currency": "EUR", "interval": "per-year-salary"}
        self.assertEqual(salary_range(value), (55000, 85000, "EUR"))

    def test_hourly_is_annualized(self) -> None:
        value = {"min": 25, "max": 30, "currency": "USD", "interval": "per-hour-wage"}
        self.assertEqual(salary_range(value), (52000, 62400, "USD"))

    def test_other_intervals_and_junk_are_ignored(self) -> None:
        monthly = {"min": 4000, "max": 5000, "currency": "USD", "interval": "per-month-salary"}
        self.assertEqual(salary_range(monthly), (None, None, None))
        self.assertEqual(salary_range(None), (None, None, None))
        inverted = {"min": 9, "max": 1, "interval": "per-year-salary"}
        self.assertEqual(salary_range(inverted), (None, None, None))

    def test_posting_carries_salary(self) -> None:
        data = [
            {
                "id": "1",
                "text": "Audio Engineer",
                "hostedUrl": "https://jobs.lever.co/x/1",
                "salaryRange": {
                    "min": 80000, "max": 100000, "currency": "USD", "interval": "per-year-salary"
                },
            }
        ]
        job = parse_postings(data)[0]
        self.assertEqual((job.salary_min, job.salary_max), (80000, 100000))


if __name__ == "__main__":
    unittest.main()
