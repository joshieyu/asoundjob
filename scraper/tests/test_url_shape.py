from __future__ import annotations

import unittest

from scraper.url_shape import classify_careers_url


class TestClassifyCareersUrl(unittest.TestCase):
    def test_ats_host_is_ats_board(self) -> None:
        self.assertEqual(
            classify_careers_url("https://boards.greenhouse.io/widgetco"), "ats_board"
        )

    def test_careers_path_is_careers_shaped(self) -> None:
        self.assertEqual(
            classify_careers_url("https://widgetco.com/careers"), "careers_shaped"
        )

    def test_careers_subdomain_with_non_careers_path_is_careers_shaped(self) -> None:
        self.assertEqual(
            classify_careers_url("https://careers.widgetco.com/team"), "careers_shaped"
        )

    def test_bare_homepage_is_not_careers(self) -> None:
        self.assertEqual(classify_careers_url("https://hegel.com/en/"), "not_careers")

    def test_about_page_is_not_careers(self) -> None:
        self.assertEqual(
            classify_careers_url("https://widgetco.com/pages/about-us"), "not_careers"
        )

    def test_404ish_path_is_bad_page(self) -> None:
        self.assertEqual(
            classify_careers_url("https://widgetco.com/careers/404"), "bad_page"
        )

    def test_none_is_missing(self) -> None:
        self.assertEqual(classify_careers_url(None), "missing")

    def test_empty_string_is_missing(self) -> None:
        self.assertEqual(classify_careers_url(""), "missing")

    def test_whitespace_only_is_missing(self) -> None:
        self.assertEqual(classify_careers_url("   "), "missing")

    def test_no_host_is_missing(self) -> None:
        self.assertEqual(classify_careers_url("not-a-url-at-all"), "missing")

    def test_hard_bad_path_on_ats_host_is_bad_page_not_ats_board(self) -> None:
        self.assertEqual(
            classify_careers_url("https://boards.greenhouse.io/widgetco/404"),
            "bad_page",
        )


if __name__ == "__main__":
    unittest.main()
