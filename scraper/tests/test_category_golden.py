from __future__ import annotations

import unittest

from scraper.category_eval import evaluate, load_golden
from scraper.normalizer import classify_categories


class TestGoldenSet(unittest.TestCase):
    def test_scores_do_not_regress(self) -> None:
        result = evaluate(load_golden())
        self.assertGreaterEqual(result.total, 200)
        self.assertGreaterEqual(result.hit_rate, 0.85)
        self.assertGreaterEqual(result.clean_rate, 0.80)
        self.assertGreaterEqual(result.label_precision, 0.95)


class TestCategoryRules(unittest.TestCase):
    def test_post_production_audio_engineer_is_not_audio_systems(self) -> None:
        description = (
            "Responsible for audio post production and location sound recording for marketing. "
            "Acts as an audio systems specialist for the editing suite. "
            "Proficient with ProTools HD, mastering tools, sound design and foley recording."
        )
        cats = classify_categories("Senior Audio Engineer", description)
        self.assertIn("music_production_recording", cats)
        self.assertNotIn("audio_systems", cats)

    def test_consultancy_acoustics_titles(self) -> None:
        consultancy = "Acoustic Consulting & Engineering"
        self.assertEqual(
            classify_categories("Senior Lead Consultant, Acoustics", None, consultancy),
            ["acoustics_consulting"],
        )
        self.assertEqual(
            classify_categories("Consultant, Acoustical", None, consultancy),
            ["acoustics_consulting"],
        )
        self.assertNotIn(
            "acoustics_consulting",
            classify_categories("Sonar Engineer/ Acoustic Engineer", None, consultancy),
        )
        self.assertEqual(
            classify_categories("Environmental / Ecology Consultant", None, consultancy), []
        )

    def test_av_roles(self) -> None:
        self.assertIn(
            "av_systems_integration",
            classify_categories("Audiovisual Systems Designer, Entry-Level", None),
        )
        self.assertIn(
            "av_systems_integration",
            classify_categories("Senior Audio Visual Control Systems Programmer", None),
        )

    def test_business_fallback(self) -> None:
        business = ["business_operations"]
        self.assertEqual(classify_categories("Chief Financial Officer", None), business)
        self.assertEqual(classify_categories("Head of Supply Planning", None), business)
        self.assertEqual(classify_categories("PhD Research Intern", None), [])
        self.assertEqual(classify_categories("Cloud Software Engineering Intern", None), [])


if __name__ == "__main__":
    unittest.main()
