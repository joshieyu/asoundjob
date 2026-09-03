from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select

from scraper.company_loader import slugify
from scraper.config import load_settings
from scraper.database import get_session_factory
from scraper.models import Company

COMPARED_FIELDS = (
    "category",
    "careers_url",
    "extra_careers_urls",
    "open_application",
    "verified",
    "scrape_method",
)

MAX_URL_LEN = 90


@dataclass
class DbRow:
    id: int
    name: str
    slug: str
    category: str
    careers_url: Optional[str]
    extra_careers_urls: Optional[list]
    open_application: bool
    verified: bool
    source: str
    scrape_method: str


@dataclass
class FieldChange:
    field: str
    old: Any
    new: Any


@dataclass
class Renamed:
    seed_name: str
    db_name: str
    changes: list = field(default_factory=list)


@dataclass
class Changed:
    name: str
    changes: list = field(default_factory=list)


@dataclass
class Deleted:
    name: str


@dataclass
class Added:
    name: str


@dataclass
class ExportResult:
    output_seed: list = field(default_factory=list)
    renamed: list = field(default_factory=list)
    changed: list = field(default_factory=list)
    deleted: list = field(default_factory=list)
    added: list = field(default_factory=list)
    ignored_auto_changed: int = 0
    ignored_auto_added: int = 0


def _get(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    return getattr(row, key, None)


def _normalize_list(value: Any) -> Optional[list]:
    return list(value) if value else None


def _seed_field(entry: dict, key: str) -> Any:
    if key == "extra_careers_urls":
        return _normalize_list(entry.get("extra_careers_urls"))
    if key in ("open_application", "verified"):
        return bool(entry.get(key, False))
    return entry.get(key)


def _db_field(row: Any, key: str) -> Any:
    if key == "extra_careers_urls":
        return _normalize_list(_get(row, "extra_careers_urls"))
    if key in ("open_application", "verified"):
        return bool(_get(row, key))
    return _get(row, key)


def _field_diffs(entry: dict, row: Any) -> list:
    diffs = []
    for key in COMPARED_FIELDS:
        old = _seed_field(entry, key)
        new = _db_field(row, key)
        if old != new:
            diffs.append(FieldChange(field=key, old=old, new=new))
    return diffs


def _entry_from_row(name: str, source: str, row: Any) -> dict:
    entry: dict = {"name": name}
    entry["careers_url"] = _get(row, "careers_url")
    extra = _normalize_list(_get(row, "extra_careers_urls"))
    if extra:
        entry["extra_careers_urls"] = extra
    entry["category"] = _get(row, "category")
    entry["verified"] = bool(_get(row, "verified"))
    if bool(_get(row, "open_application")):
        entry["open_application"] = True
    entry["source"] = source
    entry["scrape_method"] = _get(row, "scrape_method")
    return entry


def build_export(seed_rows: list, db_rows: list) -> ExportResult:
    result = ExportResult()

    by_lower_name: dict = {}
    by_slug_manual: dict = {}
    for row in db_rows:
        name = str(_get(row, "name") or "")
        by_lower_name[name.lower()] = row
        if str(_get(row, "source") or "") == "manual":
            by_slug_manual[str(_get(row, "slug") or "")] = row

    matched_ids: set = set()

    for entry in seed_rows:
        seed_name = str(entry.get("name") or "").strip()
        name_key = seed_name.lower()
        row = by_lower_name.get(name_key)
        renamed_match = False
        if row is None:
            candidate = by_slug_manual.get(slugify(seed_name))
            if candidate is not None:
                row = candidate
                renamed_match = True

        if row is None:
            result.deleted.append(Deleted(name=seed_name))
            continue

        matched_ids.add(id(row))
        source = str(_get(row, "source") or "")

        if renamed_match:
            db_name = str(_get(row, "name") or "")
            result.renamed.append(
                Renamed(
                    seed_name=seed_name,
                    db_name=db_name,
                    changes=_field_diffs(entry, row),
                )
            )
            result.output_seed.append(
                _entry_from_row(db_name, str(entry.get("source", "auto")), row)
            )
            continue

        if source != "manual":
            if _field_diffs(entry, row):
                result.ignored_auto_changed += 1
            result.output_seed.append(entry)
            continue

        diffs = _field_diffs(entry, row)
        if diffs:
            result.changed.append(Changed(name=seed_name, changes=diffs))
            result.output_seed.append(
                _entry_from_row(seed_name, str(entry.get("source", "auto")), row)
            )
        else:
            result.output_seed.append(entry)

    for row in db_rows:
        if id(row) in matched_ids:
            continue
        source = str(_get(row, "source") or "")
        if source == "manual":
            name = str(_get(row, "name") or "")
            result.added.append(Added(name=name))
            result.output_seed.append(_entry_from_row(name, source, row))
        else:
            result.ignored_auto_added += 1

    return result


def _truncate_url(url: str) -> str:
    return url if len(url) <= MAX_URL_LEN else url[: MAX_URL_LEN - 1] + "…"


def _format_value(value: Any) -> str:
    if isinstance(value, str) and (value.startswith("http://") or value.startswith("https://")):
        return _truncate_url(value)
    return repr(value)


def render(result: ExportResult, output_path: Path) -> str:
    lines = [
        "# Seed edit export",
        "",
        "Read-only. Nothing here is written to the seed file or the database.",
        f"{output_path} is a candidate replacement seed for the owner to diff",
        "against data/audio_companies_final.json and move into place by hand",
        "after review.",
        "",
        "Deletions in particular must be applied to the seed, or the company",
        "will be re-inserted on the next scrape cycle: run_cycle reloads the",
        "seed at the start of every run.",
        "",
        f"- renamed: {len(result.renamed)}",
        f"- changed: {len(result.changed)}",
        f"- deleted: {len(result.deleted)}",
        f"- added: {len(result.added)}",
        f"- ignored (auto source, drifted, not proposed): {result.ignored_auto_changed}",
        f"- ignored (auto source, not in seed, not proposed): {result.ignored_auto_added}",
        "",
    ]

    lines += ["## Renamed", ""]
    if result.renamed:
        for r in sorted(result.renamed, key=lambda x: x.seed_name):
            lines.append(f"### {r.seed_name}")
            lines.append(f"- name: {r.seed_name!r} -> {r.db_name!r}")
            for d in r.changes:
                lines.append(f"- {d.field}: {_format_value(d.old)} -> {_format_value(d.new)}")
            lines.append("")
    else:
        lines.append("(none)")
        lines.append("")

    lines += ["## Changed", ""]
    if result.changed:
        for c in sorted(result.changed, key=lambda x: x.name):
            lines.append(f"### {c.name}")
            for d in c.changes:
                lines.append(f"- {d.field}: {_format_value(d.old)} -> {_format_value(d.new)}")
            lines.append("")
    else:
        lines.append("(none)")
        lines.append("")

    lines += ["## Deleted", ""]
    if result.deleted:
        for d in sorted(result.deleted, key=lambda x: x.name):
            lines.append(f"- {d.name}")
    else:
        lines.append("(none)")
    lines.append("")

    lines += ["## Added", ""]
    if result.added:
        for a in sorted(result.added, key=lambda x: x.name):
            lines.append(f"- {a.name}")
    else:
        lines.append("(none)")
    lines.append("")

    return "\n".join(lines)


def load_seed_rows(seed_path: Path) -> list:
    payload = json.loads(seed_path.read_text())
    return list(payload)


def read_db_rows() -> list:
    factory = get_session_factory()
    with factory() as session:
        rows = session.execute(
            select(
                Company.id,
                Company.name,
                Company.slug,
                Company.category,
                Company.careers_url,
                Company.extra_careers_urls,
                Company.open_application,
                Company.verified,
                Company.source,
                Company.scrape_method,
            )
        ).all()
    return [
        DbRow(
            id=row.id,
            name=row.name,
            slug=row.slug,
            category=row.category,
            careers_url=row.careers_url,
            extra_careers_urls=row.extra_careers_urls,
            open_application=bool(row.open_application),
            verified=bool(row.verified),
            source=row.source,
            scrape_method=row.scrape_method,
        )
        for row in rows
    ]


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(
        description=(
            "Compare the seed JSON against the companies table and propose a "
            "replacement seed capturing admin edits made in the web UI. "
            "Read-only: SELECT-only against the database, and it refuses to "
            "write over the seed file itself."
        )
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=settings.data_dir / "audio_companies_final.json",
    )
    parser.add_argument("--output", type=Path, default=Path("seed_export.json"))
    parser.add_argument("--report", type=Path, default=Path("seed_export.md"))
    args = parser.parse_args()

    if args.output.resolve() == args.seed.resolve():
        raise SystemExit(
            f"refusing to write --output over --seed: both resolve to {args.output.resolve()}"
        )

    seed_rows = load_seed_rows(args.seed)
    db_rows = read_db_rows()
    result = build_export(seed_rows, db_rows)

    args.output.write_text(
        json.dumps(result.output_seed, indent=2, ensure_ascii=False) + "\n"
    )
    args.report.write_text(render(result, args.output))

    print(f"renamed: {len(result.renamed)}")
    print(f"changed: {len(result.changed)}")
    print(f"deleted: {len(result.deleted)}")
    print(f"added: {len(result.added)}")
    print(f"ignored (auto, drifted): {result.ignored_auto_changed}")
    print(f"ignored (auto, not in seed): {result.ignored_auto_added}")
    print(f"wrote {args.output}")
    print(f"wrote {args.report}")


if __name__ == "__main__":
    main()
