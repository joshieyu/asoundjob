from __future__ import annotations

import unittest

from scraper.normalizer import category_to_scope, score_relevance


class TestCategoryScope(unittest.TestCase):
    def test_conglomerates_are_partial(self) -> None:
        cats = (
            "Automotive OEMs",
            "Consumer Electronics & Tech",
            "Audio Retailers & Distributors",
        )
        for cat in cats:
            self.assertEqual(category_to_scope(cat), "partial", cat)

    def test_audio_native_categories(self) -> None:
        for cat in (
            "Recording Studios & Post Houses",
            "Professional Audio & Live Sound",
            "Headphones & Personal Audio",
            "Transducer & Driver Manufacturers",
        ):
            self.assertEqual(category_to_scope(cat), "native", cat)


class TestScoreRelevance(unittest.TestCase):
    def test_audio_role_at_conglomerate_passes(self) -> None:
        score, related = score_relevance(
            "Senior DSP Engineer",
            "Design audio signal processing algorithms and filters.",
            ["audio_dsp"],
            "partial",
        )
        self.assertTrue(related)
        self.assertGreaterEqual(score, 50)

    def test_corporate_role_at_conglomerate_hidden(self) -> None:
        score, related = score_relevance(
            "Senior FP&A Analyst",
            "Build financial models and run the monthly close.",
            [],
            "partial",
        )
        self.assertFalse(related)

    def test_generic_role_at_conglomerate_hidden(self) -> None:
        _, related = score_relevance(
            "National Help Desk Engineer", "Provide IT support to employees.", [], "partial"
        )
        self.assertFalse(related)

    def test_noncorporate_role_at_native_company_passes(self) -> None:
        _, related = score_relevance("Studio Manager", None, [], "native")
        self.assertTrue(related)

    def test_corporate_role_at_native_company_hidden(self) -> None:
        _, related = score_relevance("Human Resources", None, [], "native")
        self.assertFalse(related)

    def test_weak_title_with_categories_passes_partial(self) -> None:
        _, related = score_relevance(
            "Studio Coordinator", None, ["music_production_recording"], "partial"
        )
        self.assertTrue(related)

    def test_photo_editor_at_partial_licenser_hidden(self) -> None:
        _, related = score_relevance("Senior Photo Editor, Sport", None, [], "partial")
        self.assertFalse(related)

    def test_description_signals_help(self) -> None:
        _, related = score_relevance(
            "Acoustics Researcher", None, [], "partial"
        )
        self.assertTrue(related)


if __name__ == "__main__":
    unittest.main()
