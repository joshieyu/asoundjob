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
        _, related = score_relevance(
            "Studio Manager",
            "Manage recording studio operations and audio equipment.",
            [],
            "native",
        )
        self.assertTrue(related)

    def test_noncorporate_role_at_native_company_no_desc_hidden(self) -> None:
        _, related = score_relevance("Studio Manager", None, [], "native")
        self.assertFalse(related)

    def test_company_boilerplate_alone_does_not_admit(self) -> None:
        boilerplate = (
            "Shure is a leading audio company. Our microphones and wireless "
            "audio systems are used worldwide. We build audio products."
        )
        _, related = score_relevance(
            "Senior Credit Collections Specialist", boilerplate, [], "native"
        )
        self.assertFalse(related)

    def test_boilerplate_plus_category_still_admits(self) -> None:
        boilerplate = (
            "Audix builds microphones. Our audio products are used on stage. "
            "We design audio transducers."
        )
        _, related = score_relevance(
            "Electrical Engineer", boilerplate, ["audio_ee"], "native"
        )
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

    def test_university_lecturer_at_native_company_hidden(self) -> None:
        _, related = score_relevance(
            "Lecturer - Department of English Writing",
            "Teach undergraduate writing courses and evaluate student work.",
            [],
            "native",
        )
        self.assertFalse(related)

    def test_plumber_at_native_company_hidden(self) -> None:
        _, related = score_relevance(
            "Plumber (Downtown)",
            "Repair plumbing fixtures and pipes across campus buildings.",
            [],
            "native",
        )
        self.assertFalse(related)

    def test_network_engineer_at_partial_company_hidden(self) -> None:
        _, related = score_relevance(
            "Network Engineer / Linux Administrator",
            "Maintain network infrastructure and Linux servers for cloud communications platform.",
            [],
            "partial",
        )
        self.assertFalse(related)

    def test_revenue_manager_at_partial_company_hidden(self) -> None:
        _, related = score_relevance(
            "Revenue Manager",
            "Own revenue recognition and monthly close processes.",
            [],
            "partial",
        )
        self.assertFalse(related)

    def test_strong_audio_role_at_partial_passes(self) -> None:
        _, related = score_relevance(
            "Senior DSP Engineer",
            "Design audio signal processing algorithms for noise cancellation.",
            ["audio_dsp_embedded"],
            "partial",
        )
        self.assertTrue(related)

    def test_corporate_role_exempted_by_strong_audio_title(self) -> None:
        _, related = score_relevance("Audio Project Manager", None, [], "native")
        self.assertTrue(related)

    def test_studio_leader_at_architecture_firm_not_related(self) -> None:
        desc = (
            "DLR Group is an integrated design firm delivering architecture, "
            "engineering, interiors, and planning for clients nationwide. "
            "About K-12 Education at DLR Group: our team of architects, "
            "engineers, and interior designers draw from evidence-based design "
            "to help schools improve outcomes for students. Position Summary: "
            "as a Studio Leader you will lead business development and manage "
            "client relationships across our K-12 Education practice."
        )
        _, related = score_relevance(
            "Studio Leader, K-12 Education", desc, [], "native"
        )
        self.assertFalse(related)


if __name__ == "__main__":
    unittest.main()
