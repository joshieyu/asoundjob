from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scraper.main import scrape_lock


class TestScrapeLock(unittest.TestCase):
    def test_a_second_holder_is_refused_until_the_first_releases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".scrape.lock"
            with scrape_lock(path) as first:
                self.assertTrue(first)
                with scrape_lock(path) as second:
                    self.assertFalse(second)
            with scrape_lock(path) as again:
                self.assertTrue(again)


if __name__ == "__main__":
    unittest.main()
