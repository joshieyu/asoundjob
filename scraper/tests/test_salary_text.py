from __future__ import annotations

import unittest

from scraper.normalizer import parse_salary


class SalaryScanTest(unittest.TestCase):
    def test_skips_a_non_salary_range_before_the_real_one(self) -> None:
        text = "3-5 years of experience. The base salary ranges from $86,600 to $147,300."
        self.assertEqual(parse_salary(text), (86600, 147300, "USD"))

    def test_cents_keep_both_ends(self) -> None:
        text = "Pay range: $121,000.00 - $171,000.00 The above"
        self.assertEqual(parse_salary(text), (121000, 171000, "USD"))

    def test_escaped_html_between_bounds(self) -> None:
        text = (
            "&lt;div class=&quot;pay-range&quot;&gt;&lt;span&gt;$101,000&lt;/span&gt;"
            "&lt;span&gt;&amp;mdash;&lt;/span&gt;&lt;span&gt;$135,000 USD&lt;/span&gt;"
        )
        self.assertEqual(parse_salary(text), (101000, 135000, "USD"))

    def test_invisible_characters_are_ignored(self) -> None:
        text = "salary range is $ ﻿96,000.00 - $ 146,000.00 ﻿ and"
        self.assertEqual(parse_salary(text), (96000, 146000, "USD"))

    def test_monthly_pay_is_not_annual(self) -> None:
        text = "The base pay range for this internship is USD $6,810 - $13,480 per month."
        self.assertEqual(parse_salary(text), (None, None, None))

    def test_company_money_is_not_salary(self) -> None:
        for text in (
            "generating over $35 Billion in annual revenues",
            "We have raised over $30M from investors",
            "subject to a fine not exceeding $100.",
            "life coverage of 3x your salary (up to $1,000,000).",
        ):
            self.assertEqual(parse_salary(text), (None, None, None), text)

    def test_retirement_plan_names_are_not_a_range(self) -> None:
        self.assertEqual(parse_salary("Optional 401K and 403B plans"), (None, None, None))

    def test_bare_numbers_need_salary_wording(self) -> None:
        self.assertEqual(parse_salary("Course numbers 40100 - 40300"), (None, None, None))
        self.assertEqual(
            parse_salary("Base Salary: 121,950.00 - 179,900.00 USD Annual"),
            (121950, 179900, "USD"),
        )

    def test_hourly_single_with_wording(self) -> None:
        self.assertEqual(parse_salary("the daily hire pay rate is $65.18 per hour."),
                         (135200, None, "USD"))

    def test_dotted_thousands(self) -> None:
        self.assertEqual(parse_salary("Gehalt: € 61.500 - € 90.200"), (61500, 90200, "EUR"))


if __name__ == "__main__":
    unittest.main()
