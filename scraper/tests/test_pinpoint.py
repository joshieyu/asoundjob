from __future__ import annotations

import unittest

from scraper.scrapers.ats.pinpoint import PinpointScraper, parse_postings


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Electronic Musical Instruments",
        careers_url=url,
    )


PINPOINT_PAYLOAD = {
    "data": [
        {
            "id": 252436,
            "title": "Junior Beta Liaison",
            "url": "https://inmusicbrands.pinpointhq.com/en/postings/abc123",
            "description": "<h3>Are you our next Beta Liaison?</h3>",
            "key_responsibilities": (
                "<h3>Key Responsibilities:</h3>"
                "<ul><li>Answer inquiries</li></ul>"
            ),
            "skills_knowledge_expertise": (
                "<strong>Requirements:</strong>"
                "<ul><li>1+ years experience</li></ul>"
            ),
            "employment_type": "full_time",
            "employment_type_text": "Full Time",
            "workplace_type": "hybrid",
            "location": {
                "id": "37608",
                "city": "Cambridge",
                "name": "Cambridge, UK",
            },
            "deadline_at": None,
        },
        {
            "id": 999,
            "title": "",
            "url": "",
        },
    ]
}


class TestPinpointParser(unittest.TestCase):
    def test_parse_postings(self) -> None:
        jobs = parse_postings(PINPOINT_PAYLOAD)
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Junior Beta Liaison")
        self.assertEqual(job.external_id, "252436")
        self.assertEqual(job.url, "https://inmusicbrands.pinpointhq.com/en/postings/abc123")
        self.assertEqual(job.location, "Cambridge, UK")
        self.assertEqual(job.job_type, "full-time")
        self.assertIn("Beta Liaison", job.description or "")
        self.assertIn("Key Responsibilities", job.description or "")
        self.assertIn("Requirements", job.description or "")
        self.assertFalse(job.remote_hint)

    def test_parse_postings_remote(self) -> None:
        payload = {
            "data": [
                {
                    "id": 1,
                    "title": "Remote Engineer",
                    "url": "https://example.com/job/1",
                    "employment_type": "contract",
                    "workplace_type": "remote",
                    "location": "Remote, US",
                }
            ]
        }
        jobs = parse_postings(payload)
        self.assertEqual(jobs[0].job_type, "contract")
        self.assertTrue(jobs[0].remote_hint)
        self.assertEqual(jobs[0].location, "Remote, US")

    def test_parse_postings_rejects_non_dict(self) -> None:
        with self.assertRaises(ValueError):
            parse_postings([])

    def test_parse_postings_rejects_bad_data(self) -> None:
        with self.assertRaises(ValueError):
            parse_postings({"data": "not a list"})

    def test_extract_slug(self) -> None:
        self.assertEqual(
            PinpointScraper.extract_slug("https://inmusicbrands.pinpointhq.com/"),
            "inmusicbrands",
        )
        self.assertIsNone(
            PinpointScraper.extract_slug("https://example.com/careers")
        )

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = PinpointScraper(load_settings())
        self.assertTrue(
            scraper.can_handle(make_company("https://inmusicbrands.pinpointhq.com/"))
        )
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))


if __name__ == "__main__":
    unittest.main()
