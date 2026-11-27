from __future__ import annotations

import unittest

from scraper.normalizer import score_relevance

MEET = (
    "Minimum qualifications: 8 years of experience in software development. "
    "About the job Google Meet connects hundreds of millions of users, and audio "
    "quality is the top driver of satisfaction. Responsibilities Lead Google Meet's "
    "Audio Processing and Systems team. Build real-time DSP and ML audio systems."
)


class AudioTeamTest(unittest.TestCase):
    def test_leading_an_audio_team_lists_a_generic_title(self) -> None:
        _, ok = score_relevance(
            "Software Engineering Manager, Google Meet", MEET, [], "partial", "Google"
        )
        self.assertTrue(ok)

    def test_scrum_master_on_an_audio_team_stays_off(self) -> None:
        _, ok = score_relevance(
            "Agile Scrum Master",
            "You will join our Audio team and run audio sprint ceremonies for audio DSP.",
            [],
            "partial",
            "Bosch Group",
        )
        self.assertFalse(ok)

    def test_audio_team_mention_without_role_text_stays_off(self) -> None:
        _, ok = score_relevance(
            "Software Engineer, Payments",
            "Minimum qualifications: 5 years of experience. Build payment systems.",
            [],
            "partial",
            "Google",
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
