from __future__ import annotations

import json
import unittest

from scraper.scrapers.base import RawJob
from scraper.scrapers.detail_enrichment import (
    apply_structured_detail,
    microdata_location,
    needs_detail,
)

JOB_URL = "https://careers.example.com/jobs/42-acoustic-engineer"
WWW_JOB_URL = "https://www.careers.example.com/jobs/42-acoustic-engineer"
LONG_TEXT = "Design and measure loudspeaker systems. " * 10


def jsonld(*postings: dict) -> str:
    scripts = "".join(
        f'<script type="application/ld+json">{json.dumps(p)}</script>' for p in postings
    )
    return f"<html><head>{scripts}</head><body></body></html>"


def posting(title: str, url: str, locality: str, description: str = LONG_TEXT) -> dict:
    return {
        "@type": "JobPosting",
        "title": title,
        "url": url,
        "description": description,
        "datePosted": "2026-11-20",
        "employmentType": "FULL_TIME",
        "jobLocation": {
            "@type": "Place",
            "address": {"addressLocality": locality, "addressCountry": "TR"},
        },
    }


class TestNeedsDetail(unittest.TestCase):
    def test_a_job_with_a_description_and_a_location_needs_nothing(self) -> None:
        job = RawJob(title="A", url=JOB_URL, description=LONG_TEXT, location="Oslo")
        self.assertFalse(needs_detail(job))

    def test_a_missing_location_or_thin_description_needs_the_detail_page(self) -> None:
        self.assertTrue(needs_detail(RawJob(title="A", url=JOB_URL, description=LONG_TEXT)))
        self.assertTrue(needs_detail(RawJob(title="A", url=JOB_URL, location="Oslo")))


class TestApplyStructuredDetail(unittest.TestCase):
    def test_fills_missing_fields_from_the_matching_posting(self) -> None:
        job = RawJob(title="Acoustic Engineer", url=JOB_URL)
        apply_structured_detail(job, jsonld(posting("Acoustic Engineer", JOB_URL, "Istanbul")))
        self.assertEqual(job.location, "Istanbul, TR")
        self.assertEqual(job.description, LONG_TEXT)
        self.assertIsNotNone(job.posted_date)
        self.assertEqual(job.job_type, "full-time")

    def test_keeps_a_full_description_and_an_existing_location(self) -> None:
        job = RawJob(
            title="Acoustic Engineer", url=JOB_URL, description=LONG_TEXT + "!", location="Izmir"
        )
        apply_structured_detail(
            job, jsonld(posting("Acoustic Engineer", JOB_URL, "Istanbul", "short"))
        )
        self.assertEqual(job.location, "Izmir")
        self.assertEqual(job.description, LONG_TEXT + "!")

    def test_picks_this_job_among_related_postings(self) -> None:
        job = RawJob(title="Acoustic Engineer", url=JOB_URL + "/")
        html = jsonld(
            posting("Sales Lead", "https://careers.example.com/jobs/7-sales", "Ankara"),
            posting("Acoustic Engineer", WWW_JOB_URL, "Istanbul"),
        )
        apply_structured_detail(job, html)
        self.assertEqual(job.location, "Istanbul, TR")

    def test_an_unrelated_lone_posting_is_ignored(self) -> None:
        job = RawJob(title="Acoustic Engineer", url=JOB_URL)
        html = jsonld(posting("Sales Lead", "https://careers.example.com/jobs/7-sales", "Ankara"))
        apply_structured_detail(job, html)
        self.assertIsNone(job.location)
        self.assertIsNone(job.description)

    def test_reads_a_posting_inside_a_graph(self) -> None:
        job = RawJob(title="Acoustic Engineer", url=JOB_URL)
        html = jsonld({"@context": "https://schema.org", "@graph": [
            {"@type": "WebPage", "url": JOB_URL},
            posting("Acoustic Engineer", JOB_URL, "Istanbul"),
        ]})
        apply_structured_detail(job, html)
        self.assertEqual(job.location, "Istanbul, TR")
        self.assertEqual(job.description, LONG_TEXT)

    def test_falls_back_to_microdata_for_the_location(self) -> None:
        job = RawJob(title="Acoustic Engineer", url=JOB_URL)
        html = (
            '<span itemprop="jobLocation" itemscope><span itemprop="address" itemscope>'
            '<meta itemprop="addressLocality" content="Mierzyn">'
            '<meta itemprop="addressCountry" content="PL"></span></span>'
        )
        apply_structured_detail(job, html)
        self.assertEqual(job.location, "Mierzyn, PL")


class TestMicrodataLocation(unittest.TestCase):
    def test_street_address_meta(self) -> None:
        html = (
            '<span itemprop="jobLocation" itemscope><span itemprop="address" itemscope>'
            '<meta itemprop="streetAddress" content="Warszawa, Poland"></span></span>'
        )
        self.assertEqual(microdata_location(html), "Warszawa, Poland")

    def test_plain_text_location(self) -> None:
        html = '<div itemprop="jobLocation">Hannover, Germany</div>'
        self.assertEqual(microdata_location(html), "Hannover, Germany")

    def test_a_long_block_is_not_a_location(self) -> None:
        html = f'<div itemprop="jobLocation">{LONG_TEXT}</div>'
        self.assertIsNone(microdata_location(html))

    def test_no_microdata(self) -> None:
        self.assertIsNone(microdata_location("<html></html>"))


if __name__ == "__main__":
    unittest.main()
