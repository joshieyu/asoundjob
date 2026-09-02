from __future__ import annotations

import unittest

from scraper.scrapers.ats.eightfold import (
    EightfoldScraper,
    parse_positions,
    registrable_domain,
)
from scraper.scrapers.ats_discovery import discover


def make_company(url: str, ats_type: str | None = None, ats_slug: str | None = None):
    from scraper.models import Company

    return Company(
        id=1,
        name="Test Co",
        slug="test-co",
        category="Electronic Musical Instruments",
        careers_url=url,
        ats_type=ats_type,
        ats_slug=ats_slug,
    )


DOLBY_PAYLOAD = {
    "status": 200,
    "data": {
        "positions": [
            {
                "id": 43348620,
                "name": "Senior Audio Engineer",
                "locations": ["San Francisco, CA", "Remote - USA"],
                "postedTs": 1730419200,
                "department": "Engineering",
                "workLocationOption": "remote",
                "positionUrl": "/careers/job/43348620",
            },
            {
                "id": 43348621,
                "name": "Acoustic Research Scientist",
                "locations": [],
                "postedTs": 1730505600,
                "department": "Research",
                "workLocationOption": "onsite",
                "positionUrl": "/careers/job/43348621",
            },
            {
                "id": 43348622,
                "name": "",
                "locations": ["Sydney, Australia"],
                "postedTs": 1730505600,
                "department": "Sales",
                "workLocationOption": "hybrid",
                "positionUrl": "/careers/job/43348622",
            },
        ],
        "count": 62,
    },
}


class TestRegistrableDomain(unittest.TestCase):
    def test_two_labels_returns_itself(self) -> None:
        self.assertEqual(registrable_domain("dolby.com"), "dolby.com")

    def test_three_labels_strips_subdomain(self) -> None:
        self.assertEqual(registrable_domain("jobs.dolby.com"), "dolby.com")

    def test_deep_subdomain_strips_to_registrable(self) -> None:
        self.assertEqual(
            registrable_domain("careers.sub.example.com"), "example.com"
        )

    def test_special_second_level_domain(self) -> None:
        self.assertEqual(registrable_domain("jobs.acme.co.uk"), "acme.co.uk")

    def test_single_label_returns_itself(self) -> None:
        self.assertEqual(registrable_domain("localhost"), "localhost")


class TestParsePositions(unittest.TestCase):
    def test_parses_valid_positions(self) -> None:
        jobs = parse_positions(DOLBY_PAYLOAD, "jobs.dolby.com")
        self.assertEqual(len(jobs), 2)

        first = jobs[0]
        self.assertEqual(first.title, "Senior Audio Engineer")
        self.assertEqual(first.external_id, "43348620")
        self.assertEqual(
            first.url, "https://jobs.dolby.com/careers/job/43348620"
        )
        self.assertEqual(first.location, "San Francisco, CA; Remote - USA")
        self.assertTrue(first.remote_hint)
        self.assertEqual(first.posted_date.isoformat(), "2024-11-01")

        second = jobs[1]
        self.assertEqual(second.title, "Acoustic Research Scientist")
        self.assertIsNone(second.location)
        self.assertFalse(second.remote_hint)

    def test_skips_position_with_no_name(self) -> None:
        jobs = parse_positions(DOLBY_PAYLOAD, "jobs.dolby.com")
        titles = [job.title for job in jobs]
        self.assertNotIn("", titles)

    def test_rejects_non_dict_payload(self) -> None:
        with self.assertRaises(ValueError):
            parse_positions([], "jobs.dolby.com")

    def test_rejects_missing_data(self) -> None:
        with self.assertRaises(ValueError):
            parse_positions({"status": 200}, "jobs.dolby.com")

    def test_rejects_non_list_positions(self) -> None:
        with self.assertRaises(ValueError):
            parse_positions({"data": {"positions": "nope"}}, "jobs.dolby.com")


class TestCanHandle(unittest.TestCase):
    def test_ats_type_vanity_domain(self) -> None:
        from scraper.config import load_settings

        scraper = EightfoldScraper(load_settings())
        company = make_company(
            "https://jobs.dolby.com/careers?query=audio", ats_type="eightfold"
        )
        self.assertTrue(scraper.can_handle(company))

    def test_native_eightfold_host(self) -> None:
        from scraper.config import load_settings

        scraper = EightfoldScraper(load_settings())
        company = make_company("https://acme.eightfold.ai/careers")
        self.assertTrue(scraper.can_handle(company))

    def test_unrelated_url_without_ats_type(self) -> None:
        from scraper.config import load_settings

        scraper = EightfoldScraper(load_settings())
        company = make_company("https://jobs.lever.co/acme")
        self.assertFalse(scraper.can_handle(company))


class TestDiscovery(unittest.TestCase):
    def test_eightfold_marker_uses_base_url_domain(self) -> None:
        html = '<script src="https://app.eightfold.ai/pcsx/bundle.js"></script>'
        results = discover(html, "https://jobs.dolby.com/careers")
        self.assertIn(("eightfold", "dolby.com"), results)

    def test_eightfold_marker_without_base_url_yields_nothing(self) -> None:
        html = '<script src="https://app.eightfold.ai/pcsx/bundle.js"></script>'
        results = discover(html, "")
        types = [r[0] for r in results]
        self.assertNotIn("eightfold", types)


if __name__ == "__main__":
    unittest.main()
