from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from scraper.export_seed_edits import (
    DbRow,
    build_export,
    main,
    read_db_rows,
    render,
)
from scraper.models import Base, Company


def _db_row(
    name: str,
    slug: str,
    category: str = "Audio Software",
    careers_url: str = "https://example.com/careers",
    extra_careers_urls=None,
    open_application: bool = False,
    verified: bool = True,
    source: str = "manual",
    scrape_method: str = "http",
    company_id: int = 1,
) -> DbRow:
    return DbRow(
        id=company_id,
        name=name,
        slug=slug,
        category=category,
        careers_url=careers_url,
        extra_careers_urls=extra_careers_urls,
        open_application=open_application,
        verified=verified,
        source=source,
        scrape_method=scrape_method,
    )


def _seed_entry(
    name: str,
    category: str = "Audio Software",
    careers_url: str = "https://example.com/careers",
    extra_careers_urls=None,
    open_application=None,
    verified: bool = True,
    source: str = "manual",
    scrape_method: str = "http",
) -> dict:
    entry = {
        "name": name,
        "careers_url": careers_url,
        "category": category,
        "verified": verified,
        "source": source,
        "scrape_method": scrape_method,
    }
    if extra_careers_urls:
        entry["extra_careers_urls"] = extra_careers_urls
    if open_application:
        entry["open_application"] = open_application
    return entry


class TestNoDrift(unittest.TestCase):
    def test_no_drift_produces_empty_buckets_and_identical_output(self) -> None:
        seed = [_seed_entry("Acme")]
        db = [_db_row("Acme", "acme")]
        result = build_export(seed, db)
        self.assertEqual(result.renamed, [])
        self.assertEqual(result.changed, [])
        self.assertEqual(result.deleted, [])
        self.assertEqual(result.added, [])
        self.assertEqual(result.output_seed, seed)


class TestChanged(unittest.TestCase):
    def test_careers_url_change_on_manual_row_is_proposed(self) -> None:
        seed = [_seed_entry("Acme", careers_url="https://old.example.com/careers")]
        db = [_db_row("Acme", "acme", careers_url="https://new.example.com/careers")]
        result = build_export(seed, db)
        self.assertEqual(len(result.changed), 1)
        self.assertEqual(result.changed[0].name, "Acme")
        fields = {c.field: (c.old, c.new) for c in result.changed[0].changes}
        self.assertEqual(
            fields["careers_url"],
            ("https://old.example.com/careers", "https://new.example.com/careers"),
        )
        self.assertEqual(result.output_seed[0]["careers_url"], "https://new.example.com/careers")
        self.assertEqual(result.deleted, [])
        self.assertEqual(result.added, [])

    def test_same_change_on_auto_row_is_ignored(self) -> None:
        seed = [
            _seed_entry(
                "Acme", careers_url="https://old.example.com/careers", source="auto"
            )
        ]
        db = [
            _db_row(
                "Acme",
                "acme",
                careers_url="https://new.example.com/careers",
                source="auto",
            )
        ]
        result = build_export(seed, db)
        self.assertEqual(result.changed, [])
        self.assertEqual(result.ignored_auto_changed, 1)
        self.assertEqual(result.output_seed, seed)
        self.assertEqual(
            result.output_seed[0]["careers_url"], "https://old.example.com/careers"
        )


class TestRenamed(unittest.TestCase):
    def test_rename_detected_via_slug_fallback(self) -> None:
        seed = [_seed_entry("Acme Studios")]
        db = [_db_row("Acme Studios Inc", "acme-studios")]
        result = build_export(seed, db)
        self.assertEqual(len(result.renamed), 1)
        self.assertEqual(result.renamed[0].seed_name, "Acme Studios")
        self.assertEqual(result.renamed[0].db_name, "Acme Studios Inc")
        self.assertEqual(result.output_seed[0]["name"], "Acme Studios Inc")
        self.assertEqual(result.changed, [])
        self.assertEqual(result.deleted, [])

    def test_rename_only_applies_to_manual_source_rows(self) -> None:
        seed = [_seed_entry("Acme Studios")]
        db = [_db_row("Acme Studios Inc", "acme-studios", source="auto")]
        result = build_export(seed, db)
        self.assertEqual(result.renamed, [])
        self.assertEqual(len(result.deleted), 1)


class TestDeleted(unittest.TestCase):
    def test_deletion_detected(self) -> None:
        seed = [_seed_entry("Gone Co")]
        db: list = []
        result = build_export(seed, db)
        self.assertEqual(len(result.deleted), 1)
        self.assertEqual(result.deleted[0].name, "Gone Co")
        self.assertEqual(result.output_seed, [])


class TestAdded(unittest.TestCase):
    def test_admin_created_manual_company_is_proposed_as_addition(self) -> None:
        seed: list = []
        db = [_db_row("New Co", "new-co", source="manual")]
        result = build_export(seed, db)
        self.assertEqual(len(result.added), 1)
        self.assertEqual(result.added[0].name, "New Co")
        self.assertEqual(len(result.output_seed), 1)
        self.assertEqual(result.output_seed[0]["name"], "New Co")
        self.assertEqual(result.output_seed[0]["source"], "manual")

    def test_auto_source_unmatched_row_is_not_an_addition(self) -> None:
        seed: list = []
        db = [_db_row("Stale Co", "stale-co", source="auto")]
        result = build_export(seed, db)
        self.assertEqual(result.added, [])
        self.assertEqual(result.ignored_auto_added, 1)
        self.assertEqual(result.output_seed, [])


class TestExtraCareersUrls(unittest.TestCase):
    def test_extra_careers_urls_added_round_trips(self) -> None:
        seed = [_seed_entry("Acme", extra_careers_urls=None)]
        db = [
            _db_row(
                "Acme",
                "acme",
                extra_careers_urls=["https://example.com/careers/eng"],
            )
        ]
        result = build_export(seed, db)
        self.assertEqual(len(result.changed), 1)
        self.assertEqual(
            result.output_seed[0]["extra_careers_urls"],
            ["https://example.com/careers/eng"],
        )

    def test_extra_careers_urls_cleared_round_trips(self) -> None:
        seed = [_seed_entry("Acme", extra_careers_urls=["https://example.com/careers/eng"])]
        db = [_db_row("Acme", "acme", extra_careers_urls=None)]
        result = build_export(seed, db)
        self.assertEqual(len(result.changed), 1)
        self.assertNotIn("extra_careers_urls", result.output_seed[0])


class TestOpenApplication(unittest.TestCase):
    def test_open_application_false_is_omitted(self) -> None:
        seed = [_seed_entry("Acme")]
        db = [_db_row("Acme", "acme", open_application=False)]
        result = build_export(seed, db)
        self.assertNotIn("open_application", result.output_seed[0])

    def test_open_application_true_is_included(self) -> None:
        seed = [_seed_entry("Acme", open_application=None)]
        db = [_db_row("Acme", "acme", open_application=True)]
        result = build_export(seed, db)
        self.assertEqual(len(result.changed), 1)
        self.assertTrue(result.output_seed[0]["open_application"])


class TestEmittedKeyOrder(unittest.TestCase):
    def test_key_order_matches_the_seed_file_shape(self) -> None:
        seed = [_seed_entry("Acme", careers_url="https://old.example.com/careers")]
        db = [
            _db_row(
                "Acme",
                "acme",
                careers_url="https://new.example.com/careers",
                extra_careers_urls=["https://new.example.com/jobs"],
                open_application=True,
            )
        ]
        result = build_export(seed, db)
        self.assertEqual(
            list(result.output_seed[0].keys()),
            [
                "name",
                "careers_url",
                "extra_careers_urls",
                "category",
                "verified",
                "open_application",
                "source",
                "scrape_method",
            ],
        )

    def test_untouched_entries_keep_their_own_key_order(self) -> None:
        seed = [_seed_entry("Acme", open_application=True)]
        db = [_db_row("Acme", "acme", open_application=True)]
        result = build_export(seed, db)
        self.assertEqual(list(result.output_seed[0].keys()), list(seed[0].keys()))


class TestRender(unittest.TestCase):
    def test_render_states_it_is_read_only_and_warns_about_deletions(self) -> None:
        result = build_export([], [])
        out = render(result, Path("seed_export.json"))
        self.assertIn("Read-only", out)
        self.assertIn("nothing here is written to the seed file or the database".lower(),
                       out.lower())
        self.assertIn("run_cycle reloads the", out)

    def test_render_lists_field_diffs(self) -> None:
        seed = [_seed_entry("Acme", careers_url="https://old.example.com/careers")]
        db = [_db_row("Acme", "acme", careers_url="https://new.example.com/careers")]
        result = build_export(seed, db)
        out = render(result, Path("seed_export.json"))
        self.assertIn("careers_url:", out)
        self.assertIn("old.example.com", out)
        self.assertIn("new.example.com", out)


    def test_renamed_entry_reports_its_other_field_changes(self) -> None:
        seed = [_seed_entry("Acme", careers_url="https://old.example.com/careers")]
        db = [
            _db_row("Acme Audio", "acme", careers_url="https://new.example.com/careers")
        ]
        result = build_export(seed, db)
        self.assertEqual(len(result.renamed), 1)
        out = render(result, Path("seed_export.json"))
        self.assertIn("'Acme' -> 'Acme Audio'", out)
        self.assertIn("careers_url:", out)
        self.assertIn("new.example.com", out)


class TestMainRefusesSameOutputAsSeed(unittest.TestCase):
    def test_output_equals_seed_path_is_refused(self) -> None:
        with TemporaryDirectory() as tmp:
            seed_path = Path(tmp) / "seed.json"
            seed_path.write_text("[]")
            argv = [
                "export_seed_edits.py",
                "--seed",
                str(seed_path),
                "--output",
                str(seed_path),
                "--report",
                str(Path(tmp) / "seed_export.md"),
            ]
            with patch.object(sys, "argv", argv):
                with self.assertRaises(SystemExit):
                    main()


class TestReadDbRows(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine, future=True)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_read_db_rows_returns_the_needed_columns(self) -> None:
        with Session(self.engine) as session:
            session.add(
                Company(
                    name="Acme",
                    slug="acme",
                    category="Audio Software",
                    careers_url="https://example.com/careers",
                    verified=True,
                    source="manual",
                    scrape_method="http",
                )
            )
            session.commit()
        with patch(
            "scraper.export_seed_edits.get_session_factory", return_value=self.factory
        ):
            rows = read_db_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].name, "Acme")
        self.assertEqual(rows[0].slug, "acme")
        self.assertEqual(rows[0].source, "manual")


if __name__ == "__main__":
    unittest.main()
