from __future__ import annotations

import asyncio
import unittest
from typing import Dict

from scraper.scrapers.pagination import MAX_PAGES, collect_paginated, find_next_page

START_URL = "https://example.com/careers?page=1"


def make_fetch(pages: Dict[str, str]):
    async def fetch(url: str) -> str:
        return pages[url]

    return fetch


class TestFindNextPage(unittest.TestCase):
    def test_rel_next_is_followed(self) -> None:
        html = """
        <a rel="next" href="/careers?page=2">More</a>
        """
        self.assertEqual(
            find_next_page(html, START_URL), "https://example.com/careers?page=2"
        )

    def test_aria_label_go_to_next_page(self) -> None:
        html = """
        <a aria-label="Go to next page" href="/careers?page=2">&gt;</a>
        """
        self.assertEqual(
            find_next_page(html, START_URL), "https://example.com/careers?page=2"
        )

    def test_text_next_is_followed(self) -> None:
        html = """
        <a href="/careers?page=2">Next</a>
        """
        self.assertEqual(
            find_next_page(html, START_URL), "https://example.com/careers?page=2"
        )

    def test_text_guillemet_is_followed(self) -> None:
        html = """
        <a href="/careers?page=2">&raquo;</a>
        """
        self.assertEqual(
            find_next_page(html, START_URL), "https://example.com/careers?page=2"
        )

    def test_different_path_is_rejected(self) -> None:
        html = """
        <a rel="next" href="/blog/some-post?page=2">Next</a>
        """
        self.assertIsNone(find_next_page(html, START_URL))

    def test_pure_fragment_is_rejected(self) -> None:
        html = """
        <a class="carousel-next-link" href="#slide-2">Next</a>
        """
        self.assertIsNone(find_next_page(html, START_URL))

    def test_self_link_is_rejected(self) -> None:
        html = """
        <a rel="next" href="/careers?page=1">Next</a>
        """
        self.assertIsNone(find_next_page(html, START_URL))

    def test_no_query_string_is_rejected(self) -> None:
        html = """
        <a rel="next" href="/careers">Next</a>
        """
        self.assertIsNone(find_next_page(html, START_URL))

    def test_class_pagination_next(self) -> None:
        html = """
        <a class="pagination-next" href="/careers?page=2">&gt;</a>
        """
        self.assertEqual(
            find_next_page(html, START_URL), "https://example.com/careers?page=2"
        )


def job_anchor(job_id: int) -> str:
    return (
        f'<a href="https://example.com/careers/jobs/{job_id}">'
        f"Audio Engineer {job_id}</a>"
    )


class TestCollectPaginated(unittest.TestCase):
    def test_merges_jobs_across_rel_next_pages(self) -> None:
        pages = {
            START_URL: f"""
            <html><body>
            {job_anchor(1)}
            <a rel="next" href="/careers?page=2">Next</a>
            </body></html>
            """,
            "https://example.com/careers?page=2": f"""
            <html><body>
            {job_anchor(2)}
            </body></html>
            """,
        }
        jobs, first_html = asyncio.run(
            collect_paginated(make_fetch(pages), START_URL)
        )
        self.assertEqual(len(jobs), 2)
        self.assertEqual(first_html, pages[START_URL])

    def test_stops_after_max_pages(self) -> None:
        pages: Dict[str, str] = {}
        for i in range(1, MAX_PAGES + 3):
            url = f"https://example.com/careers?page={i}"
            next_page = i + 1
            pages[url] = f"""
            <html><body>
            {job_anchor(i)}
            <a rel="next" href="/careers?page={next_page}">Next</a>
            </body></html>
            """
        jobs, _ = asyncio.run(
            collect_paginated(make_fetch(pages), "https://example.com/careers?page=1")
        )
        self.assertEqual(len(jobs), MAX_PAGES)

    def test_stops_when_page_yields_no_new_jobs(self) -> None:
        pages = {
            START_URL: f"""
            <html><body>
            {job_anchor(1)}
            <a rel="next" href="/careers?page=2">Next</a>
            </body></html>
            """,
            "https://example.com/careers?page=2": """
            <html><body>
            <p>No jobs currently.</p>
            <a rel="next" href="/careers?page=3">Next</a>
            </body></html>
            """,
            "https://example.com/careers?page=3": f"""
            <html><body>
            {job_anchor(3)}
            </body></html>
            """,
        }
        jobs, _ = asyncio.run(
            collect_paginated(make_fetch(pages), START_URL)
        )
        self.assertEqual(len(jobs), 1)

    def test_cycle_terminates(self) -> None:
        pages = {
            START_URL: f"""
            <html><body>
            {job_anchor(1)}
            <a rel="next" href="/careers?page=2">Next</a>
            </body></html>
            """,
            "https://example.com/careers?page=2": f"""
            <html><body>
            {job_anchor(2)}
            <a rel="next" href="/careers?page=1">Next</a>
            </body></html>
            """,
        }
        jobs, _ = asyncio.run(
            collect_paginated(make_fetch(pages), START_URL)
        )
        self.assertEqual(len(jobs), 2)

    def test_duplicate_jobs_across_pages_appear_once(self) -> None:
        pages = {
            START_URL: f"""
            <html><body>
            {job_anchor(1)}
            {job_anchor(2)}
            <a rel="next" href="/careers?page=2">Next</a>
            </body></html>
            """,
            "https://example.com/careers?page=2": f"""
            <html><body>
            {job_anchor(2)}
            {job_anchor(3)}
            </body></html>
            """,
        }
        jobs, _ = asyncio.run(
            collect_paginated(make_fetch(pages), START_URL)
        )
        self.assertEqual(len(jobs), 3)
        urls = [job.url for job in jobs]
        self.assertEqual(len(urls), len(set(urls)))

    def test_returns_first_page_html_not_last(self) -> None:
        pages = {
            START_URL: f"""
            <html><body>
            {job_anchor(1)}
            <a rel="next" href="/careers?page=2">Next</a>
            </body></html>
            """,
            "https://example.com/careers?page=2": f"""
            <html><body>
            {job_anchor(2)}
            </body></html>
            """,
        }
        _, first_html = asyncio.run(
            collect_paginated(make_fetch(pages), START_URL)
        )
        self.assertEqual(first_html, pages[START_URL])
        self.assertNotEqual(first_html, pages["https://example.com/careers?page=2"])


if __name__ == "__main__":
    unittest.main()
