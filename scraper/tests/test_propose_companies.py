from __future__ import annotations

import unittest

from scraper.propose_companies import (
    build_known_index,
    build_proposals,
    filter_audio_relevant,
    match_known_company,
    normalize_company_name,
)

SEED_COMPANIES = [
    {"name": "Sennheiser"},
    {"name": "AKG"},
    {"name": "AMD"},
    {"name": "EAW"},
    {"name": "dCS"},
    {"name": "8x8"},
    {"name": "Bang & Olufsen"},
]


class TestNormalizeCompanyName(unittest.TestCase):
    def test_strips_legal_suffixes(self) -> None:
        self.assertEqual(normalize_company_name("Acme Inc"), "acme")
        self.assertEqual(normalize_company_name("Acme Corp."), "acme")
        self.assertEqual(normalize_company_name("Acme Holdings Group"), "acme")

    def test_strips_co_kg_and_co_ltd(self) -> None:
        self.assertEqual(
            normalize_company_name("Sennheiser Electronic GmbH & Co. KG"),
            "sennheiser electronic",
        )
        self.assertEqual(normalize_company_name("Foo Co. Ltd."), "foo")

    def test_handles_ampersand(self) -> None:
        self.assertEqual(normalize_company_name("Bang & Olufsen"), "bang olufsen")

    def test_ampersand_leaves_no_dangling_and_token(self) -> None:
        tokens = normalize_company_name("A & B Audio").split(" ")
        self.assertNotIn("and", tokens)

    def test_handles_accents(self) -> None:
        self.assertEqual(normalize_company_name("Café Audio"), "cafe audio")
        self.assertEqual(normalize_company_name("Mötley Audio"), "motley audio")

    def test_collapses_whitespace_and_punctuation(self) -> None:
        self.assertEqual(normalize_company_name("  Acme,   Inc.  "), "acme")


class TestMatchKnownCompany(unittest.TestCase):
    def setUp(self) -> None:
        self.known_index = build_known_index(SEED_COMPANIES)

    def test_short_names_never_fuzzy_match(self) -> None:
        self.assertIsNone(match_known_company(normalize_company_name("AK"), self.known_index))
        self.assertIsNone(match_known_company(normalize_company_name("AKGX"), self.known_index))
        self.assertEqual(
            match_known_company(normalize_company_name("AKG"), self.known_index), "AKG"
        )

    def test_exact_short_name_still_matches(self) -> None:
        for name in ("AMD", "EAW", "dCS", "8x8"):
            self.assertEqual(
                match_known_company(normalize_company_name(name), self.known_index), name
            )

    def test_four_letter_brands_match_on_first_token(self) -> None:
        index = build_known_index(
            [{"name": "Sony"}, {"name": "Bose"}, {"name": "Korg"}, {"name": "AKG"}]
        )
        for incoming, expected in (
            ("Sony Interactive Entertainment", "Sony"),
            ("Bose Corporation", "Bose"),
            ("Korg USA", "Korg"),
        ):
            self.assertEqual(
                match_known_company(normalize_company_name(incoming), index), expected
            )
        self.assertIsNone(
            match_known_company(normalize_company_name("AKG Unrelated Holdings"), index)
        )

    def test_sennheiser_subsidiary_spelling_matches(self) -> None:
        result = match_known_company(
            normalize_company_name("Sennheiser Electronic GmbH & Co. KG"), self.known_index
        )
        self.assertEqual(result, "Sennheiser")

    def test_new_company_is_not_matched(self) -> None:
        self.assertIsNone(
            match_known_company(normalize_company_name("Totally New Audio Co"), self.known_index)
        )


class TestSingleTokenSwallowRegression(unittest.TestCase):
    def setUp(self) -> None:
        self.known_index = build_known_index(
            [{"name": "Audio Ltd"}, {"name": "Focusrite"}, {"name": "Meyer Sound"}]
        )

    def test_generic_single_token_does_not_swallow_unrelated_startup(self) -> None:
        self.assertIsNone(
            match_known_company(
                normalize_company_name("Some Brand New Audio Startup"), self.known_index
            )
        )

    def test_generic_single_token_does_not_swallow_boston_audio_labs(self) -> None:
        self.assertIsNone(
            match_known_company(normalize_company_name("Boston Audio Labs"), self.known_index)
        )

    def test_first_token_matches_the_right_company_not_the_generic_one(self) -> None:
        result = match_known_company(
            normalize_company_name("Focusrite Audio Engineering"), self.known_index
        )
        self.assertEqual(result, "Focusrite")

    def test_two_token_subset_still_matches(self) -> None:
        result = match_known_company(
            normalize_company_name("Meyer Sound Laboratories"), self.known_index
        )
        self.assertEqual(result, "Meyer Sound")


class TestBestMatchNotFirstMatch(unittest.TestCase):
    def test_the_highest_ratio_wins_even_when_inserted_first_is_worse(self) -> None:
        known_index = {
            "sonartek audio dynamix": "SonarTek Dynamix",
            "sonartek audio dynamic": "SonarTek Dynamic",
        }
        incoming = normalize_company_name("SonarTek Audio Dynamics")
        result = match_known_company(incoming, known_index)
        self.assertEqual(result, "SonarTek Dynamic")


class TestFilterAudioRelevant(unittest.TestCase):
    def test_title_with_no_audio_signal_is_dropped(self) -> None:
        jobs = [
            {
                "title": "Software Engineer",
                "description": "Build web applications using Python and React.",
                "company_name": "Totally New Audio Co",
            }
        ]
        self.assertEqual(filter_audio_relevant(jobs), [])

    def test_title_with_strong_audio_signal_survives(self) -> None:
        jobs = [
            {
                "title": "Audio DSP Engineer",
                "description": (
                    "Design real-time audio DSP algorithms for our loudspeaker "
                    "products. You'll work on audio signal processing and "
                    "acoustic tuning."
                ),
                "company_name": "Totally New Audio Co",
            }
        ]
        self.assertEqual(len(filter_audio_relevant(jobs)), 1)


class TestBuildProposals(unittest.TestCase):
    def test_new_company_is_reported_as_candidate(self) -> None:
        jobs = [
            {
                "title": "Audio DSP Engineer",
                "description": (
                    "Design real-time audio DSP algorithms and acoustic tuning "
                    "for our loudspeaker products."
                ),
                "company_name": "Totally New Audio Co",
                "search_term": "audio dsp engineer",
                "site": "indeed",
                "location": "Austin, TX",
                "company_url": "https://totallynewaudio.example.com",
                "country": "usa",
            },
            {
                "title": "Senior Audio DSP Engineer",
                "description": (
                    "Lead our audio DSP algorithm work, including loudspeaker "
                    "protection and acoustic tuning."
                ),
                "company_name": "Totally New Audio Co.",
                "search_term": "audio dsp algorithm engineer",
                "site": "linkedin",
                "location": "Remote",
                "company_url": "",
                "country": "germany",
            },
        ]
        run = build_proposals(jobs, SEED_COMPANIES, min_hits=1, limit=None)
        self.assertEqual(run.jobs_in, 2)
        self.assertEqual(run.audio_relevant, 2)
        self.assertEqual(run.matched_known, 0)
        self.assertEqual(len(run.candidates), 1)
        candidate = run.candidates[0]
        self.assertEqual(candidate.hit_count, 2)
        self.assertIn("indeed", candidate.sites)
        self.assertIn("linkedin", candidate.sites)
        self.assertEqual(candidate.company_url, "https://totallynewaudio.example.com")
        self.assertEqual(candidate.countries, ["germany", "usa"])

    def test_missing_country_field_is_tolerated(self) -> None:
        jobs = [
            {
                "title": "Audio DSP Engineer",
                "description": (
                    "Design real-time audio DSP algorithms for our loudspeaker "
                    "products. You'll work on audio signal processing and "
                    "acoustic tuning."
                ),
                "company_name": "Totally New Audio Co",
                "search_term": "audio dsp engineer",
                "site": "indeed",
                "location": "Austin, TX",
            }
        ]
        run = build_proposals(jobs, SEED_COMPANIES, min_hits=1, limit=None)
        self.assertEqual(len(run.candidates), 1)
        self.assertEqual(run.candidates[0].countries, [])

    def test_known_company_is_matched_and_dropped(self) -> None:
        jobs = [
            {
                "title": "Audio DSP Engineer",
                "description": "Audio DSP algorithm work for loudspeaker products.",
                "company_name": "Sennheiser Electronic GmbH & Co. KG",
                "search_term": "audio dsp engineer",
                "site": "indeed",
            }
        ]
        run = build_proposals(jobs, SEED_COMPANIES, min_hits=1, limit=None)
        self.assertEqual(run.matched_known, 1)
        self.assertEqual(run.candidates, [])

    def test_min_hits_filters_out_single_hit_candidates(self) -> None:
        jobs = [
            {
                "title": "Audio DSP Engineer",
                "description": "Audio DSP algorithm work for loudspeaker products.",
                "company_name": "Totally New Audio Co",
                "search_term": "audio dsp engineer",
                "site": "indeed",
            }
        ]
        run = build_proposals(jobs, SEED_COMPANIES, min_hits=2, limit=None)
        self.assertEqual(run.candidates, [])

    def test_pure_function_accepts_plain_seed_list_with_no_database(self) -> None:
        jobs = [
            {
                "title": "Sound Designer",
                "description": "Sound design and foley work for interactive audio games.",
                "company_name": "Totally New Audio Co",
                "search_term": "sound designer",
                "site": "indeed",
            }
        ]
        run = build_proposals(jobs, SEED_COMPANIES, min_hits=1, limit=None)
        self.assertEqual(len(run.candidates), 1)
        self.assertIsInstance(SEED_COMPANIES, list)


if __name__ == "__main__":
    unittest.main()
