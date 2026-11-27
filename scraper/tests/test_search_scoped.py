from __future__ import annotations

import unittest

from scraper.scrapers.pipeline import is_search_scoped


class SearchScopedTest(unittest.TestCase):
    def test_query_and_search_paths_are_scoped(self) -> None:
        self.assertTrue(is_search_scoped("https://x.wd1.myworkdayjobs.com/Site?q=audio"))
        self.assertTrue(is_search_scoped("https://careers.boozallen.com/careers/SearchJobs/acoustic"))
        self.assertTrue(is_search_scoped("https://jobs.example.com/en/search-jobs/audio/123/1"))

    def test_plain_careers_pages_are_not(self) -> None:
        self.assertFalse(is_search_scoped("https://example.com/careers"))
        self.assertFalse(is_search_scoped("https://example.com/careers/SearchJobs"))


if __name__ == "__main__":
    unittest.main()
