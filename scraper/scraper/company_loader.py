from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from scraper.config import load_settings
from scraper.database import get_session_factory, session_scope
from scraper.models import Company, Job
from scraper.normalizer import category_to_scope
from scraper.overrides import effective_is_active

logger = logging.getLogger(__name__)


@dataclass
class LoadStats:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_manual: int = 0
    duplicates_in_json: int = 0
    deactivated_unverified: int = 0
    matched_by_slug: int = 0

    def summary(self) -> str:
        return (
            f"inserted={self.inserted} updated={self.updated} "
            f"unchanged={self.unchanged} skipped_manual={self.skipped_manual} "
            f"duplicates_in_json={self.duplicates_in_json} "
            f"deactivated_unverified={self.deactivated_unverified} "
            f"matched_by_slug={self.matched_by_slug}"
        )


SEED_KEY_ORDER = (
    "name",
    "careers_url",
    "category",
    "verified",
    "open_application",
    "source",
    "scrape_method",
    "extra_careers_urls",
    "website_url",
    "logo_url",
    "scrape_blocked",
    "ats_type",
    "ats_slug",
    "description",
    "headquarters",
    "founded",
    "community_links",
)


def order_seed_entry(entry: dict[str, Any]) -> dict[str, Any]:
    out = {key: entry[key] for key in SEED_KEY_ORDER if key in entry}
    for key, value in entry.items():
        if key not in out:
            out[key] = value
    return out


MAX_COMMUNITY_LINKS = 10
COMMUNITY_LINK_URL_RE = re.compile(r"^https?://.{1,2048}$")


def clean_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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


def parse_community_links(value: Any) -> Optional[list[dict[str, str]]]:
    if not isinstance(value, list):
        return None
    links: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        url = item.get("url")
        if not isinstance(label, str) or not label.strip():
            continue
        if not isinstance(url, str) or not url.strip():
            continue
        url = url.strip()
        if not COMMUNITY_LINK_URL_RE.match(url):
            continue
        links.append({"label": label.strip(), "url": url})
        if len(links) >= MAX_COMMUNITY_LINKS:
            break
    return links or None


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

        existing = session.execute(
            select(Company).where(func.lower(Company.name) == name_key)
        ).scalar_one_or_none()
        if existing is None:
            candidate = session.execute(
                select(Company).where(Company.slug == base_slug)
            ).scalar_one_or_none()
            if candidate is not None and candidate.source == "manual":
                existing = candidate
                stats.matched_by_slug += 1

        slug = base_slug
        if existing is None:
            suffix = 2
            while slug in seen_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            seen_slugs.add(slug)

        verified = bool(entry.get("verified", False))
        source = str(entry.get("source", "auto"))
        scrape_method = str(entry.get("scrape_method", "http"))
        category = str(entry["category"])
        careers_url = entry.get("careers_url")
        extra_careers_urls = parse_extra_careers_urls(
            entry.get("extra_careers_urls"), careers_url
        )
        open_application = bool(entry.get("open_application", False))
        scrape_blocked = bool(entry.get("scrape_blocked", False))

        has_website_url = "website_url" in entry
        website_url = clean_optional_str(entry.get("website_url")) if has_website_url else None
        has_logo_url = "logo_url" in entry
        logo_url = clean_optional_str(entry.get("logo_url")) if has_logo_url else None
        has_description = "description" in entry
        description = entry.get("description") if has_description else None
        has_headquarters = "headquarters" in entry
        headquarters = entry.get("headquarters") if has_headquarters else None
        has_founded = "founded" in entry
        founded = entry.get("founded") if has_founded else None
        has_community_links = "community_links" in entry
        community_links = (
            parse_community_links(entry.get("community_links"))
            if has_community_links
            else None
        )

        has_ats_type = "ats_type" in entry
        ats_type = clean_optional_str(entry.get("ats_type")) if has_ats_type else None
        has_ats_slug = "ats_slug" in entry
        ats_slug = clean_optional_str(entry.get("ats_slug")) if has_ats_slug else None
        if has_ats_slug and ats_slug is not None and not ats_type:
            logger.info(
                "seed ats_slug for %s ignored because ats_type is not set", name
            )
            has_ats_slug = False
            ats_slug = None

        if existing is None:
            company = Company(
                name=name,
                slug=slug,
                category=category,
                careers_url=careers_url,
                extra_careers_urls=extra_careers_urls,
                open_application=open_application,
                scrape_blocked=scrape_blocked,
                verified=verified,
                source=source,
                scrape_method=scrape_method,
                audio_scope=category_to_scope(category),
            )
            if has_website_url:
                company.website_url = website_url
            if has_logo_url:
                company.logo_url = logo_url
            if has_description:
                company.description = description
            if has_headquarters:
                company.headquarters = headquarters
            if has_founded:
                company.founded = founded
            if has_community_links:
                company.community_links = community_links
            if has_ats_type:
                company.ats_type = ats_type
            if has_ats_slug:
                company.ats_slug = ats_slug
            session.add(company)
            stats.inserted += 1
        elif existing.source == "manual" and source != "manual":
            stats.skipped_manual += 1
        else:
            changed = (
                existing.name != name
                or existing.category != category
                or existing.careers_url != careers_url
                or existing.extra_careers_urls != extra_careers_urls
                or existing.open_application != open_application
                or existing.scrape_blocked != scrape_blocked
                or existing.verified != verified
                or existing.source != source
                or existing.scrape_method != scrape_method
                or (has_website_url and existing.website_url != website_url)
                or (has_logo_url and existing.logo_url != logo_url)
                or (has_description and existing.description != description)
                or (has_headquarters and existing.headquarters != headquarters)
                or (has_founded and existing.founded != founded)
                or (has_community_links and existing.community_links != community_links)
                or (has_ats_type and existing.ats_type != ats_type)
                or (has_ats_slug and existing.ats_slug != ats_slug)
            )
            if changed:
                category_changed = existing.category != category
                existing.name = name
                existing.category = category
                existing.careers_url = careers_url
                existing.extra_careers_urls = extra_careers_urls
                existing.open_application = open_application
                existing.scrape_blocked = scrape_blocked
                existing.verified = verified
                existing.source = source
                existing.scrape_method = scrape_method
                if has_website_url:
                    existing.website_url = website_url
                if has_logo_url:
                    existing.logo_url = logo_url
                if has_description:
                    existing.description = description
                if has_headquarters:
                    existing.headquarters = headquarters
                if has_founded:
                    existing.founded = founded
                if has_community_links:
                    existing.community_links = community_links
                if has_ats_type:
                    existing.ats_type = ats_type
                if has_ats_slug:
                    existing.ats_slug = ats_slug
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


def deactivate_expired_jobs(session: Session, today: Optional[date] = None) -> int:
    cutoff = today or date.today()
    candidates = session.execute(
        select(Job).where(
            Job.expires_date.is_not(None),
            Job.expires_date < cutoff,
            Job.is_active.is_(True),
        )
    ).scalars().all()
    count = 0
    for job in candidates:
        next_active = effective_is_active(job, False)
        if next_active != job.is_active:
            job.is_active = next_active
            count += 1
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
