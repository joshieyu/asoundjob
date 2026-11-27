from __future__ import annotations

import unittest

from scraper.scrapers.ats.recruitee import _format_salary


class RecruiteeSalaryTest(unittest.TestCase):
    def test_decimal_strings_do_not_raise(self) -> None:
        salary = {"min": "53.00", "max": "60000", "currency": "GBP"}
        self.assertEqual(_format_salary(salary), "GBP 53–60,000")

    def test_hourly_decimals_are_kept(self) -> None:
        salary = {"min": "17.65", "max": "22.97", "currency": "GBP"}
        self.assertEqual(_format_salary(salary), "GBP 17.65–22.97")

    def test_single_bound_and_junk(self) -> None:
        self.assertEqual(_format_salary({"min": 50000, "currency": "EUR"}), "EUR 50,000")
        self.assertEqual(_format_salary({"min": "n/a", "max": None}), "")
        self.assertEqual(_format_salary(None), "")


if __name__ == "__main__":
    unittest.main()
