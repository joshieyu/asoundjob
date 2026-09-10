from __future__ import annotations

import unittest

from scraper.deduplicator import (
    PAGINATION_QUERY_KEYS,
    identity_for_raw,
    merge_identity,
    seed_query_keys,
)
from scraper.scrapers.base import RawJob


def job(url: str, external_id: str = "") -> RawJob:
    return RawJob(title="Audio Engineer", url=url, external_id=external_id or None)


class TestSeedQueryKeys(unittest.TestCase):
    def test_single_url_yields_no_keys(self) -> None:
        self.assertEqual(seed_query_keys(["https://x.example/jobs?q=audio"]), frozenset())

    def test_keys_are_collected_across_urls(self) -> None:
        keys = seed_query_keys(
            ["https://x.example/jobs?q=audio", "https://x.example/jobs?search=dsp"]
        )
        self.assertEqual(keys - PAGINATION_QUERY_KEYS, frozenset({"q", "search"}))

    def test_keys_are_lowercased(self) -> None:
        keys = seed_query_keys(
            ["https://x.example/jobs?Q=audio", "https://x.example/jobs?q=dsp"]
        )
        self.assertEqual(keys - PAGINATION_QUERY_KEYS, frozenset({"q"}))

    def test_urls_without_query_still_carry_pagination_keys(self) -> None:
        keys = seed_query_keys(["https://x.example/jobs", "https://x.example/careers"])
        self.assertEqual(keys, PAGINATION_QUERY_KEYS)

    def test_a_single_url_carries_no_pagination_keys_either(self) -> None:
        self.assertEqual(seed_query_keys(["https://x.example/jobs"]), frozenset())


class TestMergeIdentity(unittest.TestCase):
    def test_same_job_under_two_seed_queries_collapses(self) -> None:
        keys = seed_query_keys(
            [
                "https://jobs.example/search?q=audio",
                "https://jobs.example/search?q=dsp",
            ]
        )
        a = job("https://jobs.example/roles/1234-audio-engineer?q=audio")
        b = job("https://jobs.example/roles/1234-audio-engineer?q=dsp")
        self.assertEqual(merge_identity(a, keys), merge_identity(b, keys))

    def test_different_jobs_stay_distinct(self) -> None:
        keys = seed_query_keys(
            ["https://jobs.example/search?q=audio", "https://jobs.example/search?q=dsp"]
        )
        a = job("https://jobs.example/roles/1234-audio-engineer?q=audio")
        b = job("https://jobs.example/roles/9999-dsp-engineer?q=dsp")
        self.assertNotEqual(merge_identity(a, keys), merge_identity(b, keys))

    def test_job_id_in_a_non_seed_parameter_is_preserved(self) -> None:
        keys = seed_query_keys(
            ["https://boards.example/co?q=audio", "https://boards.example/co?q=dsp"]
        )
        a = job("https://boards.example/co/apply?gh_jid=111&q=audio")
        b = job("https://boards.example/co/apply?gh_jid=222&q=dsp")
        self.assertNotEqual(merge_identity(a, keys), merge_identity(b, keys))

    def test_job_id_in_a_seed_named_parameter_is_not_stripped_when_single_url(self) -> None:
        keys = seed_query_keys(["https://boards.example/co?q=audio"])
        a = job("https://boards.example/co/apply?q=111")
        b = job("https://boards.example/co/apply?q=222")
        self.assertNotEqual(merge_identity(a, keys), merge_identity(b, keys))

    def test_the_same_job_on_a_later_result_page_collapses(self) -> None:
        keys = seed_query_keys(
            [
                "https://jobs.example/search?q=audio",
                "https://jobs.example/search?q=dsp",
            ]
        )
        a = job("https://jobs.example/roles/1234-audio-engineer?q=audio")
        b = job("https://jobs.example/roles/1234-audio-engineer?q=dsp&page=2")
        self.assertEqual(merge_identity(a, keys), merge_identity(b, keys))

    def test_external_id_wins_over_url(self) -> None:
        keys = seed_query_keys(
            ["https://jobs.example/search?q=audio", "https://jobs.example/search?q=dsp"]
        )
        a = job("https://jobs.example/roles/1?q=audio", external_id="abc")
        b = job("https://jobs.example/roles/2?q=dsp", external_id="abc")
        self.assertEqual(merge_identity(a, keys), merge_identity(b, keys))
        self.assertTrue(merge_identity(a, keys).startswith("ext:"))

    def test_empty_keys_match_plain_identity(self) -> None:
        raw = job("https://jobs.example/roles/1?q=audio")
        self.assertEqual(merge_identity(raw, frozenset()), identity_for_raw(raw))

    def test_stored_identity_still_matches_the_first_seed_url(self) -> None:
        keys = seed_query_keys(
            ["https://jobs.example/search?q=audio", "https://jobs.example/search?q=dsp"]
        )
        raw = job("https://jobs.example/roles/1234?q=audio")
        self.assertEqual(merge_identity(raw, keys), "url:https://jobs.example/roles/1234")

    def test_fragment_and_trailing_slash_still_normalized(self) -> None:
        keys = seed_query_keys(
            ["https://jobs.example/search?q=audio", "https://jobs.example/search?q=dsp"]
        )
        a = job("https://jobs.example/roles/1234/?q=audio#apply")
        b = job("https://jobs.example/roles/1234?q=dsp")
        self.assertEqual(merge_identity(a, keys), merge_identity(b, keys))


if __name__ == "__main__":
    unittest.main()
