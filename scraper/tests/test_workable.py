from __future__ import annotations

import unittest
from datetime import date

from scraper.scrapers.ats.workable import (
    WorkableScraper,
    _extract_description,
    _extract_job_id,
    _parse_salary,
    parse_jobs_md,
)


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Audio Software",
        careers_url=url,
    )


JOBS_MD = "\n".join([
    "# The Focusrite Group — All Open Positions",
    "",
    "> Last updated: 2026-08-26",
    "",
    "| Title | Department | Location | Type | Salary | Posted | Details |",
    "|-------|-----------|----------|------|--------|--------|---------|",
    "| Senior DSP Engineer | Engineering | Berlin, Germany (Hybrid) "
    "| Full-time | — | 2026-08-20 "
    "| [View]({url1}) |",
    "| IT Support Engineer | CS/Group | London, UK "
    "| Contract | GBP 25,000–35,000 | 2026-08-06 "
    "| [View]({url2}) |",
    "| Audio Intern | Engineering | Remote "
    "| Internship | — | 2026-07-01 "
    "| [View]({url3}) |",
    "",
    "---",
    "Powered by [Workable](https://www.workable.com)",
]).format(
    url1="https://apply.workable.com/focusrite/jobs/view/7FAF091965.md",
    url2="https://apply.workable.com/focusrite/jobs/view/7DC37844DE.md",
    url3="https://apply.workable.com/focusrite/jobs/view/ABC123DEF0.md",
)

DETAIL_MD = """# Senior DSP Engineer

> The Focusrite Group · Berlin, Germany (Hybrid) · Full-time · Posted 2026-08-20

**Workplace:** hybrid

**Department:** Engineering

## Description

We are looking for a Senior DSP Engineer to work on audio plugins.
You will design filters, EQs, and dynamic processors.

**Requirements:**
- 5+ years of DSP experience
- Proficient in C++ and JUCE

---
Powered by [Workable](https://www.workable.com)
"""


class TestWorkableParser(unittest.TestCase):
    def test_parse_jobs_md(self) -> None:
        jobs = parse_jobs_md(JOBS_MD, "focusrite")
        self.assertEqual(len(jobs), 3)
        first = jobs[0]
        self.assertEqual(first.title, "Senior DSP Engineer")
        self.assertEqual(first.external_id, "7FAF091965")
        self.assertEqual(first.location, "Berlin, Germany (Hybrid)")
        self.assertEqual(first.job_type, "full-time")
        self.assertEqual(first.posted_date, date(2026, 8, 20))
        self.assertEqual(
            first.url, "https://apply.workable.com/focusrite/jobs/view/7FAF091965"
        )
        self.assertIsNone(first.description)

    def test_parse_jobs_md_salary(self) -> None:
        jobs = parse_jobs_md(JOBS_MD, "focusrite")
        second = jobs[1]
        self.assertEqual(second.title, "IT Support Engineer")
        self.assertEqual(second.job_type, "contract")

    def test_extract_job_id(self) -> None:
        self.assertEqual(
            _extract_job_id("https://apply.workable.com/focusrite/jobs/view/7FAF091965.md"),
            "7FAF091965",
        )
        self.assertIsNone(_extract_job_id("https://example.com"))

    def test_extract_description(self) -> None:
        desc = _extract_description(DETAIL_MD)
        self.assertIn("Senior DSP Engineer", desc)
        self.assertIn("audio plugins", desc)
        self.assertIn("C++ and JUCE", desc)
        self.assertNotIn("Powered by", desc)

    def test_parse_salary(self) -> None:
        smin, smax, curr = _parse_salary("GBP 25,000–35,000")
        self.assertEqual(smin, 25000)
        self.assertEqual(smax, 35000)
        self.assertEqual(curr, "GBP")

        smin, smax, curr = _parse_salary("—")
        self.assertIsNone(smin)
        self.assertIsNone(smax)

    def test_extract_slug(self) -> None:
        self.assertEqual(
            WorkableScraper.extract_slug("https://apply.workable.com/focusrite/"),
            "focusrite",
        )
        self.assertEqual(
            WorkableScraper.extract_slug("https://focusrite.workable.com/"),
            "focusrite",
        )
        self.assertIsNone(
            WorkableScraper.extract_slug("https://example.com/careers")
        )

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = WorkableScraper(load_settings())
        self.assertTrue(scraper.can_handle(make_company("https://apply.workable.com/focusrite/")))
        self.assertTrue(scraper.can_handle(make_company("https://focusrite.workable.com/")))
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))


if __name__ == "__main__":
    unittest.main()
