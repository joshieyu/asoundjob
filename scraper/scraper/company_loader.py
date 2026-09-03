from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from scraper.config import load_settings
from scraper.database import get_session_factory, session_scope
from scraper.models import Company, Job
from scraper.normalizer import category_to_scope


@dataclass
class LoadStats:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_manual: int = 0
    duplicates_in_json: int = 0
    deactivated_unverified: int = 0

    def summary(self) -> str:
        return (
            f"inserted={self.inserted} updated={self.updated} "
            f"unchanged={self.unchanged} skipped_manual={self.skipped_manual} "
            f"duplicates_in_json={self.duplicates_in_json} "
            f"deactivated_unverified={self.deactivated_unverified}"
        )


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "company"


def parse_extra_careers_urls(
    value: Any, primary: Any = None
) -> Optional[list[str]]:
    if not isinstance(value, list):
        return None
    primary_key = str(primary or "").strip().rstrip("/").lower()
    seen: set[str] = set()
    urls: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        url = item.strip()
        if not url.lower().startswith(("http://", "https://")):
            continue
        key = url.rstrip("/").lower()
        if key == primary_key or key in seen:
            continue
        seen.add(key)
        urls.append(url)
    return urls or None


MAX_CAREERS_URLS = 6


def careers_urls_for(company: Company) -> list[str]:
    primary = (company.careers_url or "").strip()
    urls = [primary] if primary else []
    seen = {primary.rstrip("/").lower()} if primary else set()
    for url in company.extra_careers_urls or []:
        cleaned = str(url).strip()
        key = cleaned.rstrip("/").lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        urls.append(cleaned)
    return urls[:MAX_CAREERS_URLS]


def load_companies(session: Session, companies: list[dict[str, Any]]) -> LoadStats:
    stats = LoadStats()
    seen_names: set[str] = set()
    seen_slugs: set[str] = {slug for (slug,) in session.execute(select(Company.slug))}

    for entry in companies:
        name = str(entry["name"]).strip()
        name_key = name.lower()
        if name_key in seen_names:
            stats.duplicates_in_json += 1
            continue
        seen_names.add(name_key)

        base_slug = slugify(name)
        slug = base_slug
        suffix = 2
        while slug in seen_slugs:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        seen_slugs.add(slug)

        existing = session.execute(
            select(Company).where(func.lower(Company.name) == name_key)
        ).scalar_one_or_none()

        verified = bool(entry.get("verified", False))
        source = str(entry.get("source", "auto"))
        scrape_method = str(entry.get("scrape_method", "http"))
        category = str(entry["category"])
        careers_url = entry.get("careers_url")
        extra_careers_urls = parse_extra_careers_urls(
            entry.get("extra_careers_urls"), careers_url
        )

        if existing is None:
            session.add(
                Company(
                    name=name,
                    slug=slug,
                    category=category,
                    careers_url=careers_url,
                    extra_careers_urls=extra_careers_urls,
                    verified=verified,
                    source=source,
                    scrape_method=scrape_method,
                    audio_scope=category_to_scope(category),
                )
            )
            stats.inserted += 1
        elif existing.source == "manual" and source != "manual":
            stats.skipped_manual += 1
        else:
            changed = (
                existing.name != name
                or existing.category != category
                or existing.careers_url != careers_url
                or existing.extra_careers_urls != extra_careers_urls
                or existing.verified != verified
                or existing.source != source
                or existing.scrape_method != scrape_method
            )
            if changed:
                category_changed = existing.category != category
                existing.name = name
                existing.category = category
                existing.careers_url = careers_url
                existing.extra_careers_urls = extra_careers_urls
                existing.verified = verified
                existing.source = source
                existing.scrape_method = scrape_method
                if category_changed:
                    existing.audio_scope = category_to_scope(category)
                stats.updated += 1
            else:
                stats.unchanged += 1

    stats.deactivated_unverified = _deactivate_unverified_jobs(session)
    return stats


def _deactivate_unverified_jobs(session: Session) -> int:
    unverified = select(Company.id).where(Company.verified.is_(False))
    stale = select(func.count()).where(
        Job.company_id.in_(unverified), Job.is_active.is_(True)
    )
    count = int(session.execute(stale).scalar_one())
    if count:
        session.execute(
            update(Job)
            .where(Job.company_id.in_(unverified), Job.is_active.is_(True))
            .values(is_active=False)
        )
    return count


def read_companies_file(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("companies", [])
    if not isinstance(data, list):
        raise ValueError(f"Unexpected company data format in {path}")
    return data


def count_companies() -> int:
    session = get_session_factory()()
    try:
        return int(session.execute(select(func.count(Company.id))).scalar_one())
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load companies JSON into the database")
    parser.add_argument("--file", type=Path, default=None, help="Override companies JSON path")
    args = parser.parse_args()

    settings = load_settings()
    json_path = args.file or settings.data_dir / "audio_companies_final.json"
    companies = read_companies_file(json_path)
    print(f"Loaded {len(companies)} entries from {json_path}")

    with session_scope() as session:
        stats = load_companies(session, companies)

    print(f"Done: {stats.summary()}")
    print(f"Total companies in DB: {count_companies()}")


if __name__ == "__main__":
    main()
