from __future__ import annotations

import unittest
from datetime import date

from scraper.scrapers.link_extraction import (
    extract_jobs,
    extract_jsonld_jobs,
)

JSONLD_SINGLE = """
<html><body>
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "JobPosting",
  "title": "Senior DSP Engineer",
  "description": "<p>Work on audio algorithms.</p>",
  "datePosted": "2026-08-15",
  "url": "https://example.com/jobs/dsp-engineer",
  "employmentType": "FULL_TIME",
  "jobLocation": {
    "address": {
      "addressLocality": "Berlin",
      "addressRegion": "BE",
      "addressCountry": "Germany"
    }
  },
  "identifier": "job-12345"
}
</script>
</body></html>
"""

JSONLD_ARRAY = """
<html><body>
<script type="application/ld+json">
[
  {
    "@type": "JobPosting",
    "title": "Audio Software Engineer",
    "description": "C++ and JUCE",
    "datePosted": "2026-08-10",
    "url": "https://example.com/jobs/audio-sw"
  },
  {
    "@type": "JobPosting",
    "title": "Acoustics Engineer",
    "description": "Room acoustics",
    "datePosted": "2026-08-12",
    "url": "https://example.com/jobs/acoustics"
  }
]
</script>
</body></html>
"""

JSONLD_MIXED = """
<html><body>
<script type="application/ld+json">
[
  {"@type": "Organization", "name": "Acme"},
  {"@type": "JobPosting", "title": "DSP Engineer", "url": "https://example.com/jobs/dsp"},
  {"@type": "WebSite", "name": "Careers"}
]
</script>
</body></html>
"""

JSONLD_INVALID = """
<html><body>
<script type="application/ld+json">{invalid json}</script>
</body></html>
"""

JSONLD_STRING_LOCATION = """
<html><body>
<script type="application/ld+json">
{
  "@type": "JobPosting",
  "title": "Live Sound Engineer",
  "url": "https://example.com/jobs/live",
  "jobLocation": "Remote, US"
}
</script>
</body></html>
"""

JSONLD_NESTED_TYPE = """
<html><body>
<script type="application/ld+json">
{
  "@type": ["JobPosting", "Organization"],
  "title": "Plugin Developer",
  "url": "https://example.com/jobs/plugin"
}
</script>
</body></html>
"""

ANCHOR_AND_JSONLD = """
<html><body>
<a href="https://example.com/jobs/dsp-engineer">DSP Engineer</a>
<a href="https://example.com/jobs/acoustics-engineer-role">Acoustics</a>
<script type="application/ld+json">
{
  "@type": "JobPosting",
  "title": "Senior DSP Engineer",
  "description": "<p>Rich description from JSON-LD.</p>",
  "datePosted": "2026-08-15",
  "url": "https://example.com/jobs/dsp-engineer"
}
</script>
</body></html>
"""


class TestJSONLDExtraction(unittest.TestCase):
    def test_single_job(self) -> None:
        jobs = extract_jsonld_jobs(JSONLD_SINGLE, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.title, "Senior DSP Engineer")
        self.assertEqual(job.url, "https://example.com/jobs/dsp-engineer")
        self.assertEqual(job.description, "<p>Work on audio algorithms.</p>")
        self.assertEqual(job.external_id, "job-12345")
        self.assertEqual(job.job_type, "full-time")
        self.assertEqual(job.posted_date, date(2026, 8, 15))
        self.assertEqual(job.location, "Berlin, BE, Germany")

    def test_array_of_jobs(self) -> None:
        jobs = extract_jsonld_jobs(JSONLD_ARRAY, "https://example.com/careers")
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0].title, "Audio Software Engineer")
        self.assertEqual(jobs[1].title, "Acoustics Engineer")

    def test_mixed_types(self) -> None:
        jobs = extract_jsonld_jobs(JSONLD_MIXED, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "DSP Engineer")

    def test_invalid_json(self) -> None:
        jobs = extract_jsonld_jobs(JSONLD_INVALID, "https://example.com/careers")
        self.assertEqual(len(jobs), 0)

    def test_string_location(self) -> None:
        jobs = extract_jsonld_jobs(
            JSONLD_STRING_LOCATION, "https://example.com/careers"
        )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].location, "Remote, US")

    def test_nested_type_list(self) -> None:
        jobs = extract_jsonld_jobs(
            JSONLD_NESTED_TYPE, "https://example.com/careers"
        )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Plugin Developer")


class TestMergeExtraction(unittest.TestCase):
    def test_jsonld_wins_on_url_match(self) -> None:
        jobs = extract_jobs(ANCHOR_AND_JSONLD, "https://example.com/careers")
        by_url = {j.url: j for j in jobs}
        self.assertIn("https://example.com/jobs/dsp-engineer", by_url)
        self.assertIn("https://example.com/jobs/acoustics-engineer-role", by_url)
        merged = by_url["https://example.com/jobs/dsp-engineer"]
        self.assertEqual(merged.title, "Senior DSP Engineer")
        self.assertEqual(merged.description, "<p>Rich description from JSON-LD.</p>")
        acoustics = by_url["https://example.com/jobs/acoustics-engineer-role"]
        self.assertEqual(acoustics.title, "Acoustics")
        self.assertIsNone(acoustics.description)

    def test_no_jsonld_returns_anchors(self) -> None:
        html = '<html><body><a href="https://example.com/jobs/1">Engineer</a></body></html>'
        jobs = extract_jobs(html, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].title, "Engineer")

    def test_no_anchors_returns_jsonld(self) -> None:
        jobs = extract_jobs(JSONLD_SINGLE, "https://example.com/careers")
        self.assertEqual(len(jobs), 1)


if __name__ == "__main__":
    unittest.main()
