from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.ats.haileyhr import (
    HaileyHrScraper,
    description_from_page,
    parse_listing,
)
from scraper.scrapers.ats_discovery import discover

BASE = "https://dirac.careers.haileyhr.app/"
JOB_ID = "8efa21d6-6d51-4af6-a16f-fbd344bdf158"
JOB_HREF = (
    "/en-GB/job/39bab463-1d6c-4895-9ef2-5d3fe7213eb3/"
    f"ecf1a943-147d-4d08-a3cc-cacc7a4d3ab3/{JOB_ID}"
)


def card(href: str, chips: list[str], title: str) -> str:
    chip_html = "".join(
        f'<div class="rounded text-sm"><div class="flex">{chip}</div></div>' for chip in chips
    )
    return (
        f'<a class="group" href="{href}"><div><div>'
        f'<div class="flex flex-wrap gap-2 mb-2">{chip_html}</div>'
        f'<h3 class="text-2xl">{title}</h3><p></p></div></div></a>'
    )


LISTING = (
    "<html><body>"
    + card(JOB_HREF, ["US", "Customer Solutions"], "Senior Audio Systems Engineer – Automotive")
    + card(
        "/en-GB/job/39bab463-1d6c-4895-9ef2-5d3fe7213eb3/"
        "7063a591-8b6c-4560-a41c-8ff205bc6453/5c927f9e-d5b6-4356-b8f5-fcd96ef0279b",
        ["Copenhagen", "R&amp;D"],
        "Software Application Developer - Home &amp; Pro",
    )
    + '<a href="https://haileyhr.com">A career page created in Hailey HR</a>'
    + "</body></html>"
)

MARKDOWN = (
    "## **About Dirac**\n\nDirac is one of Sweden's fastest-growing audio tech companies, "
    "with R&D in Copenhagen and Uppsala.\n\n## **About the role**\n\nYou will tune "
    "automotive audio systems, run listening sessions and work with DSP tuning tools "
    "alongside car makers and their suppliers."
)


def push(text: str) -> str:
    return f"<script>self.__next_f.push([1,{json.dumps(text)}])</script>"


def detail_page(markdown: str) -> str:
    size = format(len(markdown.encode("utf-8")), "x")
    return (
        "<html><body>"
        + push('3:null\n9:["$","html",null,{}]\n')
        + push(f"11:T{size},")
        + push(markdown)
        + push('12:["$","div",null,{}]\n')
        + "</body></html>"
    )


class TestHaileyHrListing(unittest.TestCase):
    def test_title_comes_from_heading_not_chips(self) -> None:
        jobs = parse_listing(LISTING, BASE)
        self.assertEqual(
            [job.title for job in jobs],
            [
                "Senior Audio Systems Engineer – Automotive",
                "Software Application Developer - Home & Pro",
            ],
        )
        self.assertEqual(jobs[0].location, "US")
        self.assertEqual(jobs[0].external_id, JOB_ID)
        self.assertEqual(jobs[0].url, BASE.rstrip("/") + JOB_HREF)

    def test_board_is_detected_from_its_host(self) -> None:
        company = Company(id=1, name="Dirac", slug="dirac", careers_url=BASE)
        self.assertTrue(HaileyHrScraper(load_settings()).can_handle(company))
        self.assertIn(("haileyhr", "dirac"), discover(f'<a href="{BASE}">Jobs</a>'))


class TestHaileyHrDescription(unittest.TestCase):
    def test_markdown_description_is_read_from_the_page_data(self) -> None:
        text = description_from_page(detail_page(MARKDOWN))
        assert text is not None
        self.assertTrue(text.startswith("About Dirac"))
        self.assertIn("R&D in Copenhagen", text)
        self.assertNotIn("**", text)
        self.assertNotIn("##", text)
        self.assertNotIn('"$"', text)

    def test_short_or_missing_text_is_ignored(self) -> None:
        self.assertIsNone(description_from_page(detail_page("Apply now")))
        self.assertIsNone(description_from_page("<html><body>nothing</body></html>"))

    def test_fetch_jobs_enriches_each_posting(self) -> None:
        def fake_fetch(url, settings, *args, **kwargs):
            return LISTING if url == BASE else detail_page(MARKDOWN)

        company = Company(id=1, name="Dirac", slug="dirac", careers_url=BASE)
        with patch("scraper.scrapers.ats.haileyhr.fetch_html", side_effect=fake_fetch):
            jobs = asyncio.run(HaileyHrScraper(load_settings()).fetch_jobs(company))
        self.assertEqual(len(jobs), 2)
        self.assertTrue(all(job.description for job in jobs))


if __name__ == "__main__":
    unittest.main()
