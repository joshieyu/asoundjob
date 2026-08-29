from __future__ import annotations

import unittest
from datetime import date

from scraper.scrapers.ats.lever import LeverScraper, parse_postings

LEVER_PAYLOAD = [
    {
        "id": "a1b2c3d4",
        "text": "Audio Software Engineer",
        "hostedUrl": "https://jobs.lever.co/testco/a1b2c3d4",
        "applyUrl": "https://easyapply.co/a1b2c3d4",
        "createdAt": 1754006400000,
        "descriptionPlain": "Work on audio engines.",
        "categories": {
            "location": "Remote, US",
            "commitment": "Full-time",
            "team": "Engineering",
        },
    },
    {"id": "empty", "text": "", "hostedUrl": ""},
]


class TestLeverParser(unittest.TestCase):
    def test_parse_postings(self) -> None:
        jobs = parse_postings(LEVER_PAYLOAD)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Audio Software Engineer")
        self.assertEqual(job.external_id, "a1b2c3d4")
        self.assertEqual(job.url, "https://jobs.lever.co/testco/a1b2c3d4")
        self.assertEqual(job.location, "Remote, US")
        self.assertEqual(job.job_type, "full-time")
        self.assertEqual(job.description, "Work on audio engines.")
        self.assertEqual(job.posted_date, date(2025, 8, 1))

    def test_lists_sections_are_kept(self) -> None:
        payload = [
            {
                "id": "x1",
                "text": "Principal Engineer",
                "hostedUrl": "https://jobs.lever.co/testco/x1",
                "description": "<p>We lead the world in AV networking.</p>",
                "descriptionPlain": "We lead the world in AV networking.",
                "lists": [
                    {
                        "text": "What you'll be working on",
                        "content": "<li>Low latency audio transport</li>",
                    },
                    {"text": "What we're looking for", "content": "<li>C++ and DSP</li>"},
                ],
                "additional": "<p>Equal opportunity employer.</p>",
            }
        ]
        description = parse_postings(payload)[0].description or ""
        self.assertIn("AV networking", description)
        self.assertIn("What you&#39;ll be working on".replace("&#39;", "'"), description)
        self.assertIn("Low latency audio transport", description)
        self.assertIn("C++ and DSP", description)
        self.assertIn("Equal opportunity employer", description)

    def test_description_falls_back_to_plain(self) -> None:
        payload = [
            {
                "id": "x2",
                "text": "Audio Engineer",
                "hostedUrl": "https://jobs.lever.co/testco/x2",
                "descriptionPlain": "Only plain text here.",
            }
        ]
        self.assertEqual(parse_postings(payload)[0].description, "Only plain text here.")

    def test_parse_postings_rejects_non_list(self) -> None:
        with self.assertRaises(ValueError):
            parse_postings({"error": "not found"})

    def test_extract_slug(self) -> None:
        self.assertEqual(
            LeverScraper.extract_slug("https://jobs.lever.co/envato-2"), "envato-2"
        )
        self.assertIsNone(
            LeverScraper.extract_slug("https://example.com/careers")
        )


if __name__ == "__main__":
    unittest.main()
