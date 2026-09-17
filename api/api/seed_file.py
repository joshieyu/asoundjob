from __future__ import annotations

import json
import logging
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from scraper.company_loader import order_seed_entry
from scraper.config import load_settings
from scraper.models import Company

logger = logging.getLogger(__name__)

SEED_FILENAME = "audio_companies_final.json"

class SeedWriteError(RuntimeError):
    pass


_LOCK = threading.Lock()

_target: Optional[Path] = None


def default_path() -> Path:
    return load_settings().data_dir / SEED_FILENAME


def enable(path: Optional[Path] = None) -> None:
    global _target
    _target = path if path is not None else default_path()
    logger.info("seed sync enabled: %s", _target)


def disable() -> None:
    global _target
    _target = None


@contextmanager
def target(path: Path) -> Iterator[None]:
    global _target
    previous = _target
    _target = path
    try:
        yield
    finally:
        _target = previous


def _name_key(value: Any) -> str:
    return str(value or "").strip().lower()


def entry_from_company(company: Company) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": str(company.name).strip(),
        "careers_url": company.careers_url,
        "category": company.category,
        "verified": bool(company.verified),
    }
    if bool(company.open_application):
        entry["open_application"] = True
    entry["source"] = company.source or "auto"
    entry["scrape_method"] = company.scrape_method or "http"
    extra = list(company.extra_careers_urls or [])
    if extra:
        entry["extra_careers_urls"] = extra
    if bool(company.scrape_blocked):
        entry["scrape_blocked"] = True
    if company.ats_type:
        entry["ats_type"] = company.ats_type
        if company.ats_slug:
            entry["ats_slug"] = company.ats_slug
    return order_seed_entry(entry)


def upsert_entry(
    entries: list[dict[str, Any]],
    company: Company,
    previous_name: Optional[str] = None,
) -> list[dict[str, Any]]:
    old_key = _name_key(previous_name if previous_name is not None else company.name)
    new_key = _name_key(company.name)
    new_entry = entry_from_company(company)

    out: list[dict[str, Any]] = []
    replaced = False
    for entry in entries:
        key = _name_key(entry.get("name"))
        if key == old_key and not replaced:
            out.append(new_entry)
            replaced = True
            continue
        if key == new_key and old_key != new_key:
            continue
        out.append(entry)
    if not replaced:
        out.append(new_entry)
    return out


def remove_entry(
    entries: list[dict[str, Any]], name: str
) -> list[dict[str, Any]]:
    key = _name_key(name)
    return [entry for entry in entries if _name_key(entry.get("name")) != key]


def read_entries(path: Path) -> list[dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SeedWriteError(f"cannot read seed file {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise SeedWriteError(f"seed file {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise SeedWriteError(f"seed file {path} is not a JSON array")
    return data


def write_entries(path: Path, entries: list[dict[str, Any]]) -> None:
    ordered = sorted(entries, key=lambda entry: _name_key(entry.get("name")))
    payload = json.dumps(ordered, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(payload, encoding="utf-8")
        os.replace(str(tmp), str(path))
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise SeedWriteError(f"cannot write seed file {path}: {exc}") from exc


def sync_company(company: Company, previous_name: Optional[str] = None) -> None:
    with _LOCK:
        path = _target
        if path is None:
            logger.debug("seed sync is off, not writing %s", company.name)
            return
        entries = read_entries(path)
        write_entries(path, upsert_entry(entries, company, previous_name))
    logger.info("seed synced: upserted %s", company.name)


def forget_company(name: str) -> None:
    with _LOCK:
        path = _target
        if path is None:
            logger.debug("seed sync is off, not removing %s", name)
            return
        entries = read_entries(path)
        remaining = remove_entry(entries, name)
        if len(remaining) == len(entries):
            logger.info("seed sync: %s was not in the seed, nothing removed", name)
        write_entries(path, remaining)
    logger.info("seed synced: removed %s", name)
