from __future__ import annotations

import time
import unittest

from scraper.discover_careers_urls import (
    CandidateResult,
    build_candidates,
    careers_links_from_html,
    confidence,
    has_careers_vocab,
    is_login,
    is_storefront,
    redirect_lost_identity,
    score_candidate,
    slug_candidates,
)


class TestScoreCandidate(unittest.TestCase):
    def test_error_scores_zero(self) -> None:
        c = CandidateResult(url="https://x.example.com", error="ConnectionError: boom")
        self.assertEqual(score_candidate(c), 0)

    def test_non_200_status_scores_zero(self) -> None:
        c = CandidateResult(url="https://x.example.com", status=404)
        self.assertEqual(score_candidate(c), 0)

    def test_supported_ats_beats_many_job_links(self) -> None:
        ats = CandidateResult(url="https://x.example.com", status=200, ats_type="greenhouse")
        links_only = CandidateResult(url="https://y.example.com", status=200, job_links=20)
        self.assertGreater(score_candidate(ats), score_candidate(links_only))

    def test_storefront_penalty_reduces_score(self) -> None:
        base = CandidateResult(
            url="https://x.example.com", status=200, has_careers_vocab=True, job_links=5
        )
        flagged = CandidateResult(
            url="https://x.example.com",
            status=200,
            has_careers_vocab=True,
            job_links=5,
            is_storefront=True,
        )
        self.assertLess(score_candidate(flagged), score_candidate(base))

    def test_login_penalty_reduces_score(self) -> None:
        base = CandidateResult(
            url="https://x.example.com", status=200, has_careers_vocab=True, job_links=5
        )
        flagged = CandidateResult(
            url="https://x.example.com",
            status=200,
            has_careers_vocab=True,
            job_links=5,
            is_login=True,
        )
        self.assertLess(score_candidate(flagged), score_candidate(base))

    def test_score_never_negative(self) -> None:
        c = CandidateResult(
            url="https://x.example.com",
            status=200,
            is_storefront=True,
            is_login=True,
        )
        self.assertEqual(score_candidate(c), 0)


class TestConfidence(unittest.TestCase):
    def test_high_boundary(self) -> None:
        self.assertEqual(confidence(70), "high")
        self.assertEqual(confidence(100), "high")

    def test_medium_boundary(self) -> None:
        self.assertEqual(confidence(35), "medium")
        self.assertEqual(confidence(69), "medium")

    def test_low_boundary(self) -> None:
        self.assertEqual(confidence(1), "low")
        self.assertEqual(confidence(34), "low")

    def test_none_boundary(self) -> None:
        self.assertEqual(confidence(0), "none")


class TestSlugCandidates(unittest.TestCase):
    def test_domain_label_extracted(self) -> None:
        slugs = slug_candidates("Westone Audio", "", "https://www.westoneaudio.com/careers")
        self.assertIn("westoneaudio", slugs)

    def test_short_slugs_dropped(self) -> None:
        slugs = slug_candidates("Hi", "", "https://ab.io")
        for slug in slugs:
            self.assertGreaterEqual(len(slug), 3)

    def test_capped_at_four(self) -> None:
        slugs = slug_candidates(
            "Some Long Company Name Inc", "https://careers.example.com", "https://www.example.org"
        )
        self.assertLessEqual(len(slugs), 4)

    def test_deduped(self) -> None:
        slugs = slug_candidates("Acme", "https://acme.com", "https://acme.com")
        self.assertEqual(len(slugs), len(set(slugs)))


class TestBuildCandidates(unittest.TestCase):
    def test_existing_careers_url_first(self) -> None:
        candidates = build_candidates(
            "Acme", "https://acme.com/jobs-old", "https://acme.com", None
        )
        self.assertEqual(candidates[0], "https://acme.com/jobs-old")

    def test_includes_root_careers_path(self) -> None:
        candidates = build_candidates("Acme", None, "https://acme.com", None)
        self.assertIn("https://acme.com/careers", candidates)

    def test_includes_ats_template_urls(self) -> None:
        candidates = build_candidates("Acme", None, "https://acme.com", None)
        self.assertTrue(any("boards.greenhouse.io/acme" in c for c in candidates))
        self.assertTrue(any("jobs.lever.co/acme" in c for c in candidates))

    def test_deduped_and_capped(self) -> None:
        candidates = build_candidates(
            "Acme Corporation International Holdings",
            "https://acme.com/careers",
            "https://acme.com",
            None,
        )
        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertLessEqual(len(candidates), 24)

    def test_root_links_ordered_before_ats_and_guessed_paths(self) -> None:
        candidates = build_candidates(
            "Acme",
            "https://acme.com/jobs-old",
            "https://acme.com",
            None,
            root_links=["https://acme.com/join-our-team"],
        )
        self.assertEqual(
            candidates[:2],
            ["https://acme.com/jobs-old", "https://acme.com/join-our-team"],
        )
        ats_index = next(i for i, c in enumerate(candidates) if "greenhouse.io" in c)
        guessed_index = next(
            i for i, c in enumerate(candidates) if c == "https://acme.com/careers"
        )
        self.assertLess(ats_index, guessed_index)


class TestCareersLinksFromHtml(unittest.TestCase):
    def test_finds_link_with_matching_href(self) -> None:
        html = '<a href="/careers">Careers</a>'
        links = careers_links_from_html("https://acme.com", html)
        self.assertEqual(links, ["https://acme.com/careers"])

    def test_finds_link_with_matching_label_only(self) -> None:
        html = '<a href="/join-our-team">Join our team</a>'
        links = careers_links_from_html("https://acme.com", html)
        self.assertEqual(links, ["https://acme.com/join-our-team"])

    def test_finds_offsite_ats_link_without_vocab_match(self) -> None:
        html = '<a href="https://boards.greenhouse.io/acme">Open roles</a>'
        links = careers_links_from_html("https://acme.com", html)
        self.assertEqual(links, ["https://boards.greenhouse.io/acme"])

    def test_ignores_mailto_tel_javascript(self) -> None:
        html = (
            '<a href="mailto:careers@acme.com">Careers</a>'
            '<a href="tel:+15551234567">Careers</a>'
            '<a href="javascript:void(0)">Careers</a>'
        )
        links = careers_links_from_html("https://acme.com", html)
        self.assertEqual(links, [])

    def test_ignores_link_resolving_to_base_url(self) -> None:
        html = '<a href="/">Careers home</a>'
        links = careers_links_from_html("https://acme.com", html)
        self.assertEqual(links, [])

    def test_dedupes(self) -> None:
        html = '<a href="/careers">Careers</a><a href="/careers">Careers again</a>'
        links = careers_links_from_html("https://acme.com", html)
        self.assertEqual(links, ["https://acme.com/careers"])

    def test_capped_at_six(self) -> None:
        html = "".join(f'<a href="/careers-{i}">Careers {i}</a>' for i in range(10))
        links = careers_links_from_html("https://acme.com", html)
        self.assertEqual(len(links), 6)

    def test_backtracking_guard_on_large_page(self) -> None:
        html = "z" * 50_000
        start = time.monotonic()
        links = careers_links_from_html("https://acme.com", html)
        elapsed = time.monotonic() - start
        self.assertEqual(links, [])
        self.assertLess(elapsed, 1.0)


class TestRedirectLostIdentity(unittest.TestCase):
    def test_recruitee_subdomain_dropped_is_lost(self) -> None:
        self.assertTrue(
            redirect_lost_identity("https://8x8.recruitee.com", "https://recruitee.com/")
        )

    def test_greenhouse_host_rename_keeps_token_in_path(self) -> None:
        self.assertFalse(
            redirect_lost_identity(
                "https://boards.greenhouse.io/acme",
                "https://job-boards.greenhouse.io/acme",
            )
        )

    def test_recruitee_subdomain_preserved_with_extra_path(self) -> None:
        self.assertFalse(
            redirect_lost_identity(
                "https://acme.recruitee.com", "https://acme.recruitee.com/careers"
            )
        )

    def test_ordinary_url_never_guarded(self) -> None:
        self.assertFalse(
            redirect_lost_identity(
                "https://www.example.com/careers", "https://www.example.com/en/careers"
            )
        )

    def test_smartrecruiters_path_dropped_is_lost(self) -> None:
        self.assertTrue(
            redirect_lost_identity(
                "https://careers.smartrecruiters.com/Acme",
                "https://www.smartrecruiters.com/",
            )
        )


class TestDetectors(unittest.TestCase):
    def test_storefront_detected(self) -> None:
        html = "<html>shop now <script src='https://cdn.shopify.com/x.js'></script></html>"
        self.assertTrue(is_storefront(html.lower()))

    def test_normal_careers_page_not_storefront(self) -> None:
        html = "<html><body>Join our team. Open positions: Audio Engineer.</body></html>"
        self.assertFalse(is_storefront(html.lower()))

    def test_login_detected(self) -> None:
        html = '<form><input type="password"></form>'
        self.assertTrue(is_login(html.lower()))

    def test_login_not_flagged_for_normal_page(self) -> None:
        html = "<html><body>Careers at Acme. View open jobs.</body></html>"
        self.assertFalse(is_login(html.lower()))

    def test_careers_vocab_detected(self) -> None:
        html = "we have several job openings in engineering"
        self.assertTrue(has_careers_vocab(html.lower()))

    def test_careers_vocab_absent(self) -> None:
        html = "welcome to our online store, browse our catalog"
        self.assertFalse(has_careers_vocab(html.lower()))


class TestDeadCurrentUrlIsReplaced(unittest.TestCase):
    def test_margin_does_not_protect_a_dead_current_url(self) -> None:
        from scraper.discover_careers_urls import REPLACE_MARGIN, score_candidate

        dead = CandidateResult(url="https://acme.example/careers", status=404)
        self.assertEqual(score_candidate(dead), 0)

        modest = CandidateResult(
            url="https://acme.example/about/jobs",
            status=200,
            job_links=1,
            has_careers_vocab=True,
        )
        modest_score = score_candidate(modest)
        self.assertGreater(modest_score, 0)
        self.assertLess(modest_score, REPLACE_MARGIN)


if __name__ == "__main__":
    unittest.main()
