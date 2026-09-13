from __future__ import annotations

import unittest

from scraper.config import REPO_ROOT
from scraper.normalizer import score_relevance

TERMS_DIR = REPO_ROOT / "tools" / "jobspy_fetch"

TERMS_FILES = (
    "terms-de.txt",
    "terms-fr.txt",
    "terms-nordic.txt",
    "terms-nl.txt",
    "terms-es-it.txt",
)


def read_terms(filename: str) -> list[str]:
    path = TERMS_DIR / filename
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


class TestIntlSearchTermsFileHygiene(unittest.TestCase):
    def test_files_are_non_empty_with_no_blank_or_duplicate_lines(self) -> None:
        for filename in TERMS_FILES:
            with self.subTest(filename=filename):
                path = TERMS_DIR / filename
                raw_lines = path.read_text(encoding="utf-8").splitlines()
                self.assertTrue(raw_lines)
                for line in raw_lines:
                    self.assertTrue(line.strip())
                self.assertEqual(len(raw_lines), len(set(raw_lines)))


class TestIntlSearchTermsSurviveClassifier(unittest.TestCase):
    def _assert_term_is_audio_related(self, term: str) -> None:
        title = f"{term} - Now Hiring"
        _, is_audio_related = score_relevance(title, None, [], audio_scope="all")
        self.assertTrue(is_audio_related, f"term did not survive the classifier: {term!r}")

    def test_german_terms_survive_classifier(self) -> None:
        for term in read_terms("terms-de.txt"):
            with self.subTest(term=term):
                self._assert_term_is_audio_related(term)

    def test_french_terms_survive_classifier(self) -> None:
        for term in read_terms("terms-fr.txt"):
            with self.subTest(term=term):
                self._assert_term_is_audio_related(term)

    def test_nordic_terms_survive_classifier(self) -> None:
        for term in read_terms("terms-nordic.txt"):
            with self.subTest(term=term):
                self._assert_term_is_audio_related(term)

    def test_dutch_terms_survive_classifier(self) -> None:
        for term in read_terms("terms-nl.txt"):
            with self.subTest(term=term):
                self._assert_term_is_audio_related(term)

    def test_spanish_italian_terms_survive_classifier(self) -> None:
        for term in read_terms("terms-es-it.txt"):
            with self.subTest(term=term):
                self._assert_term_is_audio_related(term)


if __name__ == "__main__":
    unittest.main()
