from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api import seed_file
from api.routers import admin as admin_router
from api.schemas import AdminCompanyCreate, AdminCompanyUpdate
from scraper.company_loader import load_companies
from scraper.models import Company

SEED_START = [
    {
        "name": "Acme Audio",
        "careers_url": "https://acme.example.com/careers",
        "category": "Audio Software",
        "verified": True,
        "source": "auto",
        "scrape_method": "http",
    },
    {
        "name": "Zeta Sound",
        "careers_url": "https://zeta.example.com/careers",
        "category": "Audio Software",
        "verified": True,
        "source": "auto",
        "scrape_method": "http",
    },
]


def make_session() -> Session:
    engine = create_engine("sqlite://")
    Company.metadata.create_all(engine)
    return Session(engine)


class SeedSyncCase(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "audio_companies_final.json"
        self.path.write_text(
            json.dumps(SEED_START, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self._ctx = seed_file.target(self.path)
        self._ctx.__enter__()
        self.session = make_session()
        self.company = Company(
            name="Acme Audio",
            slug="acme-audio",
            category="Audio Software",
            careers_url="https://acme.example.com/careers",
            verified=True,
            source="auto",
            scrape_method="http",
        )
        self.session.add(self.company)
        self.session.commit()

    def tearDown(self) -> None:
        self.session.close()
        self._ctx.__exit__(None, None, None)
        self._dir.cleanup()

    def entries(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def entry(self, name: str) -> dict:
        matches = [e for e in self.entries() if e["name"] == name]
        self.assertEqual(len(matches), 1, f"{name} not found exactly once")
        return matches[0]

    def update(self, **fields) -> None:
        admin_router.admin_update_company(
            self.company.id, AdminCompanyUpdate(**fields), self.session, "tester"
        )


class TestSyncIsOffUnlessEnabled(unittest.TestCase):
    def test_a_disabled_sync_never_touches_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audio_companies_final.json"
            path.write_text("[]\n", encoding="utf-8")
            seed_file.disable()
            company = Company(
                name="Ghost Audio",
                slug="ghost-audio",
                category="Audio Software",
                verified=True,
                source="manual",
                scrape_method="http",
            )
            seed_file.sync_company(company)
            seed_file.forget_company("Ghost Audio")
            self.assertEqual(path.read_text(encoding="utf-8"), "[]\n")

    def test_a_missing_seed_file_is_an_error_not_a_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audio_companies_final.json"
            with seed_file.target(path):
                company = Company(
                    name="Ghost Audio",
                    slug="ghost-audio",
                    category="Audio Software",
                    verified=True,
                    source="manual",
                    scrape_method="http",
                )
                with self.assertRaises(seed_file.SeedWriteError):
                    seed_file.sync_company(company)
            self.assertFalse(path.exists())


class TestAdminEditsReachTheSeed(SeedSyncCase):
    def test_unverifying_writes_both_verified_and_source(self) -> None:
        self.update(verified=False)
        entry = self.entry("Acme Audio")
        self.assertIs(entry["verified"], False)
        self.assertEqual(entry["source"], "manual")

    def test_source_manual_keeps_the_loader_managing_the_row(self) -> None:
        self.update(verified=False)
        loaded = load_companies(self.session, self.entries())
        self.assertEqual(loaded.skipped_manual, 0)

    def test_careers_url_and_extra_urls_round_trip(self) -> None:
        self.update(
            careers_url="https://acme.example.com/jobs",
            extra_careers_urls=["https://acme.example.com/jobs?q=audio"],
        )
        entry = self.entry("Acme Audio")
        self.assertEqual(entry["careers_url"], "https://acme.example.com/jobs")
        self.assertEqual(
            entry["extra_careers_urls"], ["https://acme.example.com/jobs?q=audio"]
        )

    def test_a_rename_moves_the_entry_and_leaves_no_duplicate(self) -> None:
        self.update(name="Acme Audio Labs")
        names = [e["name"] for e in self.entries()]
        self.assertEqual(names, ["Acme Audio Labs", "Zeta Sound"])

    def test_a_rename_that_sorts_later_is_resorted(self) -> None:
        self.update(name="Zzz Audio")
        names = [e["name"] for e in self.entries()]
        self.assertEqual(names, ["Zeta Sound", "Zzz Audio"])

    def test_untouched_entries_keep_their_exact_key_order(self) -> None:
        self.path.write_text(
            json.dumps(
                [
                    SEED_START[0],
                    {
                        "name": "Zeta Sound",
                        "careers_url": "https://zeta.example.com/careers",
                        "extra_careers_urls": ["https://zeta.example.com/more"],
                        "category": "Audio Software",
                        "verified": True,
                        "source": "auto",
                        "scrape_method": "http",
                    },
                ],
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        self.update(verified=False)
        self.assertEqual(
            list(self.entry("Zeta Sound").keys()),
            [
                "name",
                "careers_url",
                "extra_careers_urls",
                "category",
                "verified",
                "source",
                "scrape_method",
            ],
        )

    def test_the_edited_entry_uses_canonical_key_order(self) -> None:
        self.update(verified=False, scrape_method="playwright")
        self.assertEqual(
            list(self.entry("Acme Audio").keys()),
            ["name", "careers_url", "category", "verified", "source", "scrape_method"],
        )

    def test_the_file_stays_sorted_and_round_trips_byte_identical(self) -> None:
        self.update(verified=False)
        raw = self.path.read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertEqual(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", raw
        )
        names = [e["name"].lower() for e in data]
        self.assertEqual(names, sorted(names))

    def test_creating_a_company_adds_it_to_the_seed(self) -> None:
        admin_router.admin_create_company(
            AdminCompanyCreate(
                name="Beta Sound",
                category="Audio Software",
                careers_url="https://beta.example.com/careers",
                verified=True,
            ),
            self.session,
            "tester",
        )
        entry = self.entry("Beta Sound")
        self.assertEqual(entry["source"], "manual")
        self.assertEqual([e["name"] for e in self.entries()][0], "Acme Audio")
        self.assertIn("Beta Sound", [e["name"] for e in self.entries()])

    def test_deleting_a_company_removes_it_from_the_seed(self) -> None:
        admin_router.admin_delete_company(self.company.id, self.session, "tester")
        self.assertEqual([e["name"] for e in self.entries()], ["Zeta Sound"])

    def test_a_deleted_company_does_not_come_back_on_the_next_load(self) -> None:
        admin_router.admin_delete_company(self.company.id, self.session, "tester")
        load_companies(self.session, self.entries())
        remaining = self.session.query(Company).all()
        self.assertEqual([c.name for c in remaining], ["Zeta Sound"])


class TestEntryShape(unittest.TestCase):
    def build(self, **fields) -> dict:
        company = Company(
            name="Acme Audio",
            slug="acme-audio",
            category="Audio Software",
            careers_url="https://acme.example.com/careers",
            verified=True,
            source="auto",
            scrape_method="http",
            **fields,
        )
        return seed_file.entry_from_company(company)

    def test_falsy_optionals_are_omitted_entirely(self) -> None:
        entry = self.build()
        for key in (
            "open_application",
            "scrape_blocked",
            "extra_careers_urls",
            "website_url",
            "logo_url",
        ):
            self.assertNotIn(key, entry)

    def test_a_slug_is_never_written_without_its_type(self) -> None:
        entry = self.build(ats_type=None, ats_slug="orphaned")
        self.assertNotIn("ats_slug", entry)
        self.assertNotIn("ats_type", entry)

    def test_an_empty_slug_is_not_written(self) -> None:
        entry = self.build(ats_type="apple", ats_slug="")
        self.assertEqual(entry["ats_type"], "apple")
        self.assertNotIn("ats_slug", entry)

    def test_blocked_and_open_application_are_written_when_true(self) -> None:
        entry = self.build(scrape_blocked=True, open_application=True)
        self.assertIs(entry["scrape_blocked"], True)
        self.assertIs(entry["open_application"], True)


class TestSiteUrlsReachTheSeed(SeedSyncCase):
    def test_setting_them_writes_them(self) -> None:
        self.update(
            website_url="https://acme.example.com",
            logo_url="https://cdn.example.com/acme.svg",
        )
        entry = self.entry("Acme Audio")
        self.assertEqual(entry["website_url"], "https://acme.example.com")
        self.assertEqual(entry["logo_url"], "https://cdn.example.com/acme.svg")

    def test_they_survive_a_rebuild_from_the_seed(self) -> None:
        self.update(website_url="https://acme.example.com")
        fresh = make_session()
        try:
            load_companies(fresh, self.entries())
            rebuilt = fresh.query(Company).filter_by(name="Acme Audio").one()
            self.assertEqual(rebuilt.website_url, "https://acme.example.com")
        finally:
            fresh.close()

    def test_they_sit_after_the_required_keys(self) -> None:
        self.update(website_url="https://acme.example.com")
        self.assertEqual(
            list(self.entry("Acme Audio").keys()),
            [
                "name",
                "careers_url",
                "category",
                "verified",
                "source",
                "scrape_method",
                "website_url",
            ],
        )
