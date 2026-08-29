from __future__ import annotations

import unittest

from scraper.normalizer import (
    NormalizedJob,
    Normalizer,
    classify_categories,
    clean_description,
    detect_remote,
    detect_seniority,
    extract_role_text,
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


class TestTitleAnchoring(unittest.TestCase):
    def test_weak_title_keyword_counts_when_title_names_audio(self) -> None:
        self.assertIn(
            "audio_dsp_embedded",
            classify_categories("Embedded Software Engineer, Audio & Media", ""),
        )
        self.assertIn(
            "audio_research",
            classify_categories("Senior Applied Scientist, Speech", ""),
        )

    def test_weak_title_keyword_alone_is_not_enough(self) -> None:
        self.assertEqual(
            classify_categories("Embedded Software Engineer, Networking", ""), []
        )

    def test_anchoring_does_not_make_audio_systems_a_catch_all(self) -> None:
        cats = classify_categories("Sr. Director of Finance, Audio Technology", "")
        self.assertNotIn("audio_systems", cats)


class TestCategories(unittest.TestCase):
    def test_dsp_title(self) -> None:
        cats = classify_categories("Senior DSP Engineer", "Design filters and EQs")
        self.assertIn("audio_dsp_embedded", cats)

    def test_multiple_categories(self) -> None:
        cats = classify_categories(
            "Automotive Audio Tuning Engineer",
            "Responsibilities: NVH measurements, vibration analysis, and harshness "
            "evaluation alongside cabin audio system tuning.",
        )
        self.assertIn("automotive_audio", cats)
        self.assertIn("audio_systems", cats)
        self.assertIn("nvh", cats)

    def test_description_only_match(self) -> None:
        cats = classify_categories("Software Engineer", None)
        self.assertEqual(cats, [])
        cats = classify_categories(
            "Software Engineer",
            "Responsibilities: build our JUCE-based audio plugin, extend the audio "
            "engine, and ship new VST integrations for our DAW.",
        )
        self.assertIn("audio_software", cats)

    def test_word_boundary_avoids_substring(self) -> None:
        cats = classify_categories("Accounts Payable Specialist", "Handle invoices")
        self.assertNotIn("audio_aiml", cats)

    def test_game_audio(self) -> None:
        cats = classify_categories(
            "Sound Designer II",
            "Responsibilities: Wwise and FMOD implementation for interactive game "
            "audio design across our AAA titles.",
        )
        self.assertIn("game_audio_interactive", cats)

    def test_audio_software_keyword_no_longer_concatenated(self) -> None:
        cats = classify_categories("Audio Software Specialist", None)
        self.assertIn("audio_software", cats)

    def test_acoustic_engineer_keyword_no_longer_concatenated(self) -> None:
        cats = classify_categories("Acoustic Engineer", None)
        self.assertIn("audio_systems", cats)

    def test_boilerplate_description_does_not_leak_category(self) -> None:
        blurb = (
            "Company Overview. Acme Voice is the leading platform underpinning "
            "the emerging trillion-dollar Voice AI economy, providing real-time "
            "APIs for speech-to-text and text-to-speech. "
            "What You'll Do: Build a strong sales pipeline of new logos, "
            "striving to exceed quarterly sales targets. Work closely with "
            "Partnerships, Account Executives, and fellow SDRs to qualify "
            "inbound leads, run discovery calls, and hand off opportunities "
            "ready for a demo to the Account Executive team."
        )
        cats = classify_categories("Sales Development Representative", blurb)
        self.assertNotIn("audio_aiml", cats)
        self.assertEqual(cats, [])

    def test_anchor_requires_nearby_audio_context(self) -> None:
        cats = classify_categories(
            "Machine Learning Engineer",
            "Responsibilities: apply machine learning to general computer vision "
            "and robotics perception problems.",
        )
        self.assertNotIn("audio_aiml", cats)

    def test_anchor_satisfied_by_nearby_audio_context(self) -> None:
        cats = classify_categories(
            "Machine Learning Engineer",
            "Responsibilities: apply machine learning for audio source "
            "separation and speech processing pipelines.",
        )
        self.assertIn("audio_aiml", cats)

    def test_sales_marketing_cs_ignores_description_matches(self) -> None:
        cats = classify_categories(
            "Solutions Engineer",
            "We are looking for a partnerships manager and customer success "
            "lead to join our go-to-market team.",
        )
        self.assertNotIn("sales_marketing_cs", cats)
        cats = classify_categories("Partnerships Manager", None)
        self.assertIn("sales_marketing_cs", cats)

    def test_category_cap_of_three(self) -> None:
        cats = classify_categories(
            "Automotive Audio Systems Engineer, DSP, NVH & Acoustic Tuning", None
        )
        self.assertEqual(len(cats), 3)
        self.assertNotIn("nvh", cats)

    def test_audiology_hearing_category(self) -> None:
        cats = classify_categories("Audiologist", None)
        self.assertIn("audiology_hearing", cats)

    def test_audio_product_mechanical_category(self) -> None:
        cats = classify_categories("Audio Product Design Engineer", None)
        self.assertIn("audio_product_mechanical", cats)

    def test_acoustics_consulting_category(self) -> None:
        cats = classify_categories("Senior Acoustic Consultant", None)
        self.assertIn("acoustics_consulting", cats)


class TestCompanyCategoryFallback(unittest.TestCase):
    def test_firmware_engineer_at_pro_audio_company(self) -> None:
        cats = classify_categories(
            "Firmware Engineer", None, "Professional Audio & Live Sound"
        )
        self.assertEqual(cats, ["audio_dsp_embedded"])

    def test_mechanical_engineer_at_instrument_company(self) -> None:
        cats = classify_categories(
            "Mechanical Engineer", None, "Electronic Musical Instruments"
        )
        self.assertEqual(cats, ["audio_product_mechanical", "music_technology"])

    def test_electrical_engineer_at_car_audio_company(self) -> None:
        cats = classify_categories(
            "Electrical Design Engineer", None, "Car Audio"
        )
        self.assertEqual(cats, ["audio_ee", "automotive_audio"])

    def test_ungated_company_category_does_not_fall_back(self) -> None:
        self.assertEqual(
            classify_categories(
                "Electrical Engineer", None, "Acoustic Consulting & Engineering"
            ),
            [],
        )
        self.assertEqual(
            classify_categories(
                "Software Engineer", None, "Recording Studios & Post Houses"
            ),
            [],
        )
        self.assertEqual(
            classify_categories(
                "Software Engineer", None, "Voice & Speech Technology"
            ),
            [],
        )

    def test_excluded_technical_roles_do_not_fall_back(self) -> None:
        self.assertEqual(
            classify_categories(
                "Cloud Infrastructure Engineer",
                None,
                "Professional Audio & Live Sound",
            ),
            [],
        )
        self.assertEqual(
            classify_categories(
                "Developer Relations Engineer",
                None,
                "Electronic Musical Instruments",
            ),
            [],
        )

    def test_non_role_title_does_not_fall_back(self) -> None:
        self.assertEqual(
            classify_categories("Careers", None, "Professional Audio & Live Sound"),
            [],
        )

    def test_software_role_not_gated_at_hardware_only_company(self) -> None:
        self.assertEqual(
            classify_categories(
                "Senior Software Engineer", None, "Headphones & Personal Audio"
            ),
            [],
        )

    def test_fallback_never_overrides_keyword_match(self) -> None:
        cats = classify_categories("Audio Software Engineer", None, "Car Audio")
        self.assertIn("audio_software", cats)
        self.assertNotIn("automotive_audio", cats)

    def test_no_company_category_keeps_existing_behaviour(self) -> None:
        self.assertEqual(classify_categories("Firmware Engineer", None), [])


class TestDescriptionCleaning(unittest.TestCase):
    def test_clean_description_handles_double_escaped_html(self) -> None:
        raw = (
            "&amp;lt;div class=&amp;quot;content-intro&amp;quot;&amp;gt;"
            "&amp;lt;p&amp;gt;&amp;lt;strong&amp;gt;About Acme&amp;lt;/strong&amp;gt;"
            "&amp;lt;/p&amp;gt;&amp;lt;p&amp;gt;Acme builds things.&amp;lt;/p&amp;gt;"
            "&amp;lt;/div&amp;gt;"
        )
        cleaned = clean_description(raw)
        self.assertIsNotNone(cleaned)
        assert cleaned is not None
        self.assertNotIn("&", cleaned)
        self.assertNotIn("<", cleaned)
        self.assertIn("About Acme", cleaned)
        self.assertIn("Acme builds things.", cleaned)

    def test_clean_description_handles_empty_input(self) -> None:
        self.assertIsNone(clean_description(None))
        self.assertIsNone(clean_description(""))

    def test_extract_role_text_skips_company_intro(self) -> None:
        intro = (
            "Acme is a leading company in the widget space, founded in 2010, "
            "backed by top investors, building the future of widgets for "
            "everyone everywhere around the globe with a passionate team of "
            "engineers and designers who love shipping great products."
        )
        role_body = (
            "Design and build audio DSP algorithms for our flagship headphone "
            "product. Collaborate closely with acoustics and firmware teams to "
            "ship active noise cancellation, beamforming, and echo cancellation "
            "features across our audio product line, iterating quickly with "
            "cross-functional partners."
        )
        desc = (
            f"<p>About Acme</p><p>{intro}</p><p><strong>What You Will Do</strong>"
            f"</p><p>{role_body}</p><p>Equal Opportunity Employer. We are an "
            "equal opportunity employer and value diversity in our workplace.</p>"
        )
        role_text = extract_role_text(desc)
        self.assertNotIn("Acme is a leading company", role_text)
        self.assertNotIn("Equal Opportunity Employer", role_text)
        self.assertIn("audio DSP algorithms", role_text)


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

    def test_between_and_range(self) -> None:
        low, high, cur = parse_salary(
            "The base pay range for this role is between $195,700 and $338,400"
        )
        self.assertEqual((low, high, cur), (195700, 338400, "USD"))

    def test_and_separator_without_currency_is_not_a_salary(self) -> None:
        low, high, cur = parse_salary("5 and 10 years of experience required")
        self.assertEqual((low, high, cur), (None, None, None))


class TestJobType(unittest.TestCase):
    def test_mappings(self) -> None:
        self.assertEqual(normalize_job_type("Full-time"), "full-time")
        self.assertEqual(normalize_job_type("permanent full time"), "full-time")
        self.assertEqual(normalize_job_type("Part-Time"), "part-time")
        self.assertEqual(normalize_job_type("Contract position"), "contract")
        self.assertEqual(normalize_job_type("Contractor"), "contract")
        self.assertEqual(normalize_job_type("Freelance"), "contract")
        self.assertEqual(normalize_job_type("Internship"), "internship")
        self.assertIsNone(normalize_job_type("Mystery"))
        self.assertIsNone(normalize_job_type("Internal communication"))


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
        self.assertIn("audio_dsp_embedded", job.job_categories)


if __name__ == "__main__":
    unittest.main()
