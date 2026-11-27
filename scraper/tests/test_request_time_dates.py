from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from scraper.scrapers.link_extraction import extract_jsonld_jobs, is_request_time_stamp

NOW = datetime(2026, 11, 27, 17, 31, 31, tzinfo=timezone.utc)


class TestRequestTimeStamps(unittest.TestCase):
    def test_now_minus_whole_years_is_a_request_stamp(self) -> None:
        self.assertTrue(is_request_time_stamp("2024-11-27T17:31:32.433Z", NOW))
        self.assertTrue(is_request_time_stamp("2025-11-27T17:10:00+00:00", NOW))

    def test_real_dates_are_kept(self) -> None:
        self.assertFalse(is_request_time_stamp("2026-10-27T00:00:00.000Z", NOW))
        self.assertFalse(is_request_time_stamp("2024-11-27T00:00:00Z", NOW))
        self.assertFalse(is_request_time_stamp("2024-11-26T09:00:00Z", NOW))
        self.assertFalse(is_request_time_stamp("2024-11-27", NOW))
        self.assertFalse(is_request_time_stamp("not a date", NOW))

    def test_a_live_icims_stamp_is_dropped_from_the_posting(self) -> None:
        now = datetime.now(timezone.utc)
        try:
            stamp = now.replace(year=now.year - 2)
        except ValueError:
            stamp = now.replace(year=now.year - 2, day=28)
        posting = {
            "@type": "JobPosting",
            "title": "Audio DSP Engineering Intern",
            "datePosted": stamp.isoformat().replace("+00:00", "Z"),
            "description": "DSP",
        }
        html = f'<script type="application/ld+json">{json.dumps(posting)}</script>'
        (job,) = extract_jsonld_jobs(html, "https://careers-acme.icims.com/jobs/1/job")
        self.assertIsNone(job.posted_date)


if __name__ == "__main__":
    unittest.main()
