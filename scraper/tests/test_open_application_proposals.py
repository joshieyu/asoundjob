from __future__ import annotations

import unittest

from scraper.propose_open_applications import (
    find_invitation,
    inspect,
    page_text,
    render,
)

INVITE = (
    "<html><body><h1>Careers</h1><p>Want to use your talents? "
    "Send us your resume at jobs@example.com</p></body></html>"
)
NO_OPENINGS = (
    "<html><body><h1>Careers</h1><p>We have no open positions right now. "
    "Please check back later.</p></body></html>"
)
BOTH = (
    "<html><body><p>There are currently no vacancies. However we are always "
    "looking for talented engineers, so send your CV.</p></body></html>"
)
BLOCKED = (
    "<html><body><h1>Sorry, you have been blocked</h1>"
    "<p>Cloudflare Ray ID: abc123. We are always looking for you.</p></body></html>"
)


class TestDetection(unittest.TestCase):
    def test_an_invitation_is_found(self) -> None:
        result = inspect(1, "Acme", "https://acme.example/careers", INVITE)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.marker.lower(), "send us your resume")
        self.assertFalse(result.also_says_no_openings)

    def test_no_openings_alone_is_not_an_invitation(self) -> None:
        self.assertIsNone(inspect(1, "Ableton", "https://a.example", NO_OPENINGS))

    def test_an_invitation_beside_no_openings_is_flagged_as_mixed(self) -> None:
        result = inspect(1, "Acme", "https://acme.example", BOTH)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.also_says_no_openings)

    def test_a_blocked_page_is_never_proposed(self) -> None:
        self.assertIsNone(inspect(1, "Peavey", "https://peavey.example", BLOCKED))

    def test_empty_html_is_ignored(self) -> None:
        self.assertIsNone(inspect(1, "Acme", "https://acme.example", ""))

    def test_scripts_do_not_contribute_text(self) -> None:
        html = "<html><body><script>var s='send us your resume';</script></body></html>"
        self.assertIsNone(inspect(1, "Acme", "https://acme.example", html))

    def test_german_and_french_invitations(self) -> None:
        for html in (
            "<html><body><p>Initiativbewerbung willkommen</p></body></html>",
            "<html><body><p>Candidature spontanee acceptee</p></body></html>",
        ):
            self.assertIsNotNone(inspect(1, "Acme", "https://acme.example", html))

    def test_context_is_returned_with_the_marker(self) -> None:
        found = find_invitation(page_text(INVITE))
        assert found is not None
        _, context = found
        self.assertIn("talents", context)


class TestRender(unittest.TestCase):
    def _proposal(self, cid: int, mixed: bool = False):
        html = BOTH if mixed else INVITE
        return inspect(cid, f"Company {cid}", f"https://c{cid}.example", html)

    def test_already_flagged_companies_are_separated(self) -> None:
        proposals = [self._proposal(1), self._proposal(2)]
        out = render([p for p in proposals if p], {1: True, 2: False})
        self.assertIn("Already flagged in the seed", out)
        self.assertIn("not yet flagged in the seed: 1", out)

    def test_mixed_candidates_get_their_own_section(self) -> None:
        proposals = [p for p in [self._proposal(3, mixed=True)] if p]
        out = render(proposals, {})
        self.assertIn("Also says it has no openings", out)

    def test_report_states_it_is_read_only(self) -> None:
        out = render([], {})
        self.assertIn("Read-only", out)
        self.assertIn("candidates found: 0", out)


if __name__ == "__main__":
    unittest.main()
