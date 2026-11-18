from __future__ import annotations

import asyncio
import unittest

from scraper.scrapers.playwright_scraper import settle_links


class FakePage:
    def __init__(self, counts: list[int]) -> None:
        self.counts = counts
        self.polls = 0
        self.waited = 0

    async def evaluate(self, _script: str) -> int:
        count = self.counts[min(self.polls, len(self.counts) - 1)]
        self.polls += 1
        return count

    async def wait_for_timeout(self, ms: int) -> None:
        self.waited += ms


class TestSettleLinks(unittest.TestCase):
    def test_waits_until_links_stop_growing(self) -> None:
        page = FakePage([0, 0, 12, 40, 75, 75, 75, 75])
        asyncio.run(settle_links(page, 25000))
        self.assertEqual(page.polls, 8)

    def test_gives_up_at_the_timeout(self) -> None:
        page = FakePage([0])
        asyncio.run(settle_links(page, 5000))
        self.assertEqual(page.waited, 5000)


if __name__ == "__main__":
    unittest.main()
