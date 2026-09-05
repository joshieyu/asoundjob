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

    def test_text_next_word_with_trailing_chevrons_is_followed(self) -> None:
        html = """
        <a href="/careers?page=2">Next &gt;&gt;</a>
        """
        self.assertEqual(
            find_next_page(html, START_URL), "https://example.com/careers?page=2"
        )

    def test_text_next_page_with_trailing_guillemet_is_followed(self) -> None:
        html = """
        <a href="/careers?page=2">next page &raquo;</a>
        """
        self.assertEqual(
            find_next_page(html, START_URL), "https://example.com/careers?page=2"
        )

    def test_text_guillemet_before_next_is_followed(self) -> None:
        html = """
        <a href="/careers?page=2">&raquo; Next</a>
        """
        self.assertEqual(
            find_next_page(html, START_URL), "https://example.com/careers?page=2"
        )

    def test_text_single_angle_bracket_guillemet_is_followed(self) -> None:
        html = """
        <a href="/careers?page=2">&rsaquo;</a>
        """
        self.assertEqual(
            find_next_page(html, START_URL), "https://example.com/careers?page=2"
        )

    def test_text_previous_is_rejected(self) -> None:
        html = """
        <a href="/careers?page=2">Previous</a>
        """
        self.assertIsNone(find_next_page(html, START_URL))

    def test_text_double_chevron_previous_is_rejected(self) -> None:
        html = """
        <a href="/careers?page=2">&lt;&lt; Previous</a>
        """
        self.assertIsNone(find_next_page(html, START_URL))

    def test_text_next_steps_is_rejected(self) -> None:
        html = """
        <a href="/careers?page=2">Next Steps</a>
        """
        self.assertIsNone(find_next_page(html, START_URL))

    def test_text_nextcloud_is_rejected(self) -> None:
        html = """
        <a href="/careers?page=2">Nextcloud</a>
        """
        self.assertIsNone(find_next_page(html, START_URL))

    def test_text_empty_is_rejected(self) -> None:
        html = """
        <a href="/careers?page=2"></a>
        """
        self.assertIsNone(find_next_page(html, START_URL))


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


class TestDescendantPathPagination(unittest.TestCase):
    def test_next_page_may_live_under_the_base_path(self) -> None:
        html = (
            '<a href="/en_US/careers/SearchJobs/?jobOffset=6">Next &gt;&gt;</a>'
        )
        self.assertEqual(
            find_next_page(html, "https://jobs.example.com/en_US/careers"),
            "https://jobs.example.com/en_US/careers/SearchJobs/?jobOffset=6",
        )

    def test_next_page_on_an_unrelated_path_is_rejected(self) -> None:
        html = '<a href="/other/section/?page=2">Next &gt;&gt;</a>'
        self.assertIsNone(
            find_next_page(html, "https://jobs.example.com/en_US/careers")
        )

    def test_a_sibling_path_sharing_a_prefix_is_rejected(self) -> None:
        html = '<a href="/en_US/careersXYZ/?page=2">Next &gt;&gt;</a>'
        self.assertIsNone(
            find_next_page(html, "https://jobs.example.com/en_US/careers")
        )

    def test_a_root_base_does_not_match_every_path(self) -> None:
        html = '<a href="/anything/?page=2">Next &gt;&gt;</a>'
        self.assertIsNone(find_next_page(html, "https://jobs.example.com/"))


ACCORDION_START_URL = "https://xmems.com/careers/"

ACCORDION_ONLY_HTML = """
<html><body>
<details id="e-n-accordion-item-1152">
  <summary>Field Applications Engineer, Shenzhen</summary>
  <p>Support customers designing audio products in the region.</p>
</details>
<details id="e-n-accordion-item-1153">
  <summary>Analog Design Engineer, Santa Clara</summary>
  <p>Design analog circuits for our next-generation audio hardware.</p>
</details>
</body></html>
"""


class TestAccordionFallback(unittest.TestCase):
    def test_falls_back_to_accordion_jobs_when_no_links_found(self) -> None:
        pages = {ACCORDION_START_URL: ACCORDION_ONLY_HTML}
        jobs, _ = asyncio.run(
            collect_paginated(make_fetch(pages), ACCORDION_START_URL)
        )
        self.assertEqual(len(jobs), 2)
        urls = {job.url for job in jobs}
        self.assertEqual(
            urls,
            {
                "https://xmems.com/careers/#e-n-accordion-item-1152",
                "https://xmems.com/careers/#e-n-accordion-item-1153",
            },
        )

    def test_accordion_fallback_is_not_used_when_normal_extraction_finds_jobs(
        self,
    ) -> None:
        html = f"""
        <html><body>
        {job_anchor(1)}
        {ACCORDION_ONLY_HTML}
        </body></html>
        """
        pages = {START_URL: html}
        jobs, _ = asyncio.run(collect_paginated(make_fetch(pages), START_URL))
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].url, "https://example.com/careers/jobs/1")


if __name__ == "__main__":
    unittest.main()
