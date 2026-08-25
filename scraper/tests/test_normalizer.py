from __future__ import annotations

import unittest

from scraper.normalizer import (
    NormalizedJob,
    Normalizer,
    classify_categories,
    detect_remote,
    detect_seniority,
    normalize_job_type,
    parse_salary,
)
from scraper.scrapers.base import RawJob


class TestSeniority(unittest.TestCase):
    def test_entry(self) -> None:
        for title in (
            "Junior DSP Engineer",
            "Audio Intern - Summer 2026",
            "Entry Level Acoustics Role",
            "Graduate Software Engineer, Audio",
        ):
            self.assertEqual(detect_seniority(title), "entry", title)

    def test_senior(self) -> None:
        self.assertEqual(detect_seniority("Senior Audio Engineer"), "senior")
        self.assertEqual(detect_seniority("Sr. DSP Developer"), "senior")

    def test_lead(self) -> None:
        for title in ("Lead Audio Programmer", "Principal DSP Engineer", "Staff ML Engineer"):
            self.assertEqual(detect_seniority(title), "lead", title)

    def test_manager(self) -> None:
        for title in (
            "Engineering Manager, Audio Team",
            "Director of Acoustics",
            "Head of Audio",
        ):
            self.assertEqual(detect_seniority(title), "manager", title)

    def test_mid_default(self) -> None:
        self.assertEqual(detect_seniority("Audio Systems Engineer"), "mid")
        self.assertEqual(detect_seniority("DSP Developer"), "mid")


class TestCategories(unittest.TestCase):
    def test_dsp_title(self) -> None:
        cats = classify_categories("Senior DSP Engineer", "Design filters and EQs")
        self.assertIn("audio_dsp", cats)

    def test_multiple_categories(self) -> None:
        cats = classify_categories(
            "Automotive Audio Tuning Engineer",
            "NVH measurements and cabin audio system tuning",
        )
        self.assertIn("automotive_audio", cats)
        self.assertIn("audio_systems", cats)
        self.assertIn("nvh", cats)

    def test_description_only_match(self) -> None:
        cats = classify_categories("Software Engineer", None)
        self.assertEqual(cats, [])
        cats = classify_categories("Software Engineer", "Build JUCE plugins in C++")
        self.assertIn("audio_software", cats)

    def test_word_boundary_avoids_substring(self) -> None:
        cats = classify_categories("Accounts Payable Specialist", "Handle invoices")
        self.assertNotIn("audio_aiml", cats)

    def test_game_audio(self) -> None:
        cats = classify_categories("Sound Designer II", "Wwise implementation for AAA games")
        self.assertIn("game_audio_interactive", cats)


class TestSalary(unittest.TestCase):
    def test_range_with_k(self) -> None:
        low, high, cur = parse_salary("Salary: $80k-$120k DOE")
        self.assertEqual((low, high, cur), (80000, 120000, "USD"))

    def test_range_full_numbers(self) -> None:
        low, high, cur = parse_salary("$80,000 - $120,000 per year")
        self.assertEqual((low, high, cur), (80000, 120000, "USD"))

    def test_asymmetric_k(self) -> None:
        low, high, cur = parse_salary("80-100k USD depending on experience")
        self.assertEqual((low, high, cur), (80000, 100000, "USD"))

    def test_euro_symbol(self) -> None:
        low, _, cur = parse_salary("€45k–€60k annually")
        self.assertEqual(cur, "EUR")
        self.assertEqual(low, 45000)

    def test_single_value_plus(self) -> None:
        low, high, cur = parse_salary("Compensation: $150,000+")
        self.assertEqual(low, 150000)
        self.assertIsNone(high)
        self.assertEqual(cur, "USD")

    def test_hourly_annualized(self) -> None:
        low, _, _ = parse_salary("$50-$70/hr")
        self.assertIsNotNone(low)
        self.assertGreaterEqual(low, 50000)

    def test_rejects_dates(self) -> None:
        low, high, _ = parse_salary("Posted 2024-2025 season")
        self.assertIsNone(low)
        self.assertIsNone(high)

    def test_none(self) -> None:
        self.assertEqual(parse_salary(None), (None, None, None))
        self.assertEqual(parse_salary("Great team culture"), (None, None, None))


class TestJobType(unittest.TestCase):
    def test_mappings(self) -> None:
        self.assertEqual(normalize_job_type("Full-time"), "full-time")
        self.assertEqual(normalize_job_type("permanent full time"), "full-time")
        self.assertEqual(normalize_job_type("Part-Time"), "part-time")
        self.assertEqual(normalize_job_type("Contract"), "contract")
        self.assertEqual(normalize_job_type("Freelance"), "contract")
        self.assertEqual(normalize_job_type("Internship"), "internship")
        self.assertIsNone(normalize_job_type("Mystery"))


class TestRemote(unittest.TestCase):
    def test_location_remote(self) -> None:
        self.assertTrue(detect_remote("Remote, US", "Engineer", None))
        self.assertTrue(detect_remote(None, "Work From Home QA Tester", None))

    def test_not_remote(self) -> None:
        self.assertFalse(detect_remote("San Francisco, CA", "Audio Engineer", None))

    def test_description_remote(self) -> None:
        self.assertTrue(
            detect_remote("New York, NY", "Engineer", "This role is fully remote.")
        )


class TestNormalizerPipeline(unittest.TestCase):
    def test_normalize_full(self) -> None:
        from scraper.config import load_settings

        raw = RawJob(
            title="Senior DSP Engineer",
            url="https://example.com/jobs/123",
            external_id="123",
            location="Remote",
            description="Work on filters, FFTs and codecs. Salary: $150k-$190k. Full-time.",
            posted_date=None,
        )
        normalizer = Normalizer(load_settings())
        job = normalizer.normalize(raw)
        self.assertIsInstance(job, NormalizedJob)
        self.assertEqual(job.seniority, "senior")
        self.assertTrue(job.remote)
        self.assertEqual(job.salary_min, 150000)
        self.assertEqual(job.salary_max, 190000)
        self.assertEqual(job.job_type, "full-time")
        self.assertIn("audio_dsp", job.job_categories)


if __name__ == "__main__":
    unittest.main()
