from __future__ import annotations

import unittest

from scraper.scrapers.ats.greenhouse import GreenhouseScraper
from scraper.scrapers.base import RawJob
from scraper.scrapers.keyword_scope import scope_to_keywords, url_keywords


def job(title: str, description: str | None = None) -> RawJob:
    return RawJob(title=title, url=f"https://example.com/{title}", description=description)


class KeywordScopeTest(unittest.TestCase):
    def test_reads_repeated_q_values(self) -> None:
        url = "https://job-boards.greenhouse.io/acme?q=Acoustic&q=sonar&q=acoustic&q=%20"
        self.assertEqual(url_keywords(url), ["acoustic", "sonar"])

    def test_without_q_keeps_everything(self) -> None:
        jobs = [job("Accountant"), job("Audio Engineer")]
        self.assertEqual(len(scope_to_keywords(jobs, "https://jobs.lever.co/acme")), 2)

    def test_matches_title_or_description_at_word_start(self) -> None:
        jobs = [
            job("Acoustics Engineer"),
            job("Field Engineer", "Deploys sonar arrays"),
            job("Accountant", "Works on payroll"),
            job("Engineer", "Electroacoustic transducers"),
        ]
        kept = scope_to_keywords(jobs, "https://x.test/?q=acoustic&q=sonar")
        self.assertEqual([j.title for j in kept], ["Acoustics Engineer", "Field Engineer"])

    def test_filters_in_place(self) -> None:
        jobs = [job("Audio Engineer"), job("Chef")]
        result = scope_to_keywords(jobs, "https://x.test/?q=audio")
        self.assertIs(result, jobs)
        self.assertEqual(len(jobs), 1)

    def test_greenhouse_slug_ignores_query(self) -> None:
        url = "https://job-boards.greenhouse.io/andurilindustries?q=sonar"
        self.assertEqual(GreenhouseScraper.extract_slug(url), "andurilindustries")


if __name__ == "__main__":
    unittest.main()
