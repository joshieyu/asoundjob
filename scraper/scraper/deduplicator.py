from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from scraper.models import Company, Job
from scraper.normalizer import NormalizedJob
from scraper.scrapers.base import RawJob


@dataclass
class ReconcileStats:
    inserted: int = 0
    updated: int = 0
    reactivated: int = 0
    deactivated: int = 0
    skipped_deactivation: bool = False

    def summary(self) -> str:
        parts = [
            f"inserted={self.inserted}",
            f"updated={self.updated}",
            f"reactivated={self.reactivated}",
            f"deactivated={self.deactivated}",
        ]
        if self.skipped_deactivation:
            parts.append("skipped_deactivation=True")
        return " ".join(parts)


def _url_identity(url: str) -> str:
    cleaned = url.strip().lower().split("#", 1)[0].rstrip("/")
    return cleaned


def identity_for_raw(raw: RawJob | NormalizedJob) -> str:
    if getattr(raw, "external_id", None):
        return f"ext:{raw.external_id}"
    return f"url:{_url_identity(raw.url)}"


def identity_for_job(job: Job) -> Optional[str]:
    if job.external_id:
        return f"ext:{job.external_id}"
    if job.url:
        return f"url:{_url_identity(job.url)}"
    return None


def reconcile_company_jobs(
    session: Session,
    company: Company,
    fetched: list[NormalizedJob],
    trust_empty: bool,
) -> ReconcileStats:
    stats = ReconcileStats()

    existing_rows = (
        session.execute(
            select(Job).where(Job.company_id == company.id, Job.source == "scraper")
        )
        .scalars()
        .all()
    )
    by_identity = {
        ident: row
        for row in existing_rows
        if (ident := identity_for_job(row)) is not None
    }

    fetched_identities: set[str] = set()
    for normalized in fetched:
        ident = identity_for_raw(normalized)
        fetched_identities.add(ident)
        row = by_identity.get(ident)
        if row is None:
            session.add(
                Job(
                    company_id=company.id,
                    title=normalized.title,
                    description=normalized.description,
                    url=normalized.url,
                    location=normalized.location,
                    country=normalized.country,
                    remote=normalized.remote,
                    job_type=normalized.job_type,
                    seniority=normalized.seniority,
                    salary_min=normalized.salary_min,
                    salary_max=normalized.salary_max,
                    salary_currency=normalized.salary_currency,
                    job_categories=normalized.job_categories,
                    posted_date=normalized.posted_date,
                    relevance_score=normalized.relevance_score,
                    is_audio_related=normalized.is_audio_related,
                    expires_date=None,
                    is_active=True,
                    external_id=normalized.external_id,
                    source="scraper",
                )
            )
            stats.inserted += 1
            continue

        row.title = normalized.title
        row.description = normalized.description
        row.url = normalized.url
        row.location = normalized.location
        row.country = normalized.country
        row.remote = normalized.remote
        row.job_type = normalized.job_type
        row.seniority = normalized.seniority
        row.salary_min = normalized.salary_min
        row.salary_max = normalized.salary_max
        row.salary_currency = normalized.salary_currency
        row.job_categories = normalized.job_categories
        row.relevance_score = normalized.relevance_score
        row.is_audio_related = normalized.is_audio_related
        if normalized.posted_date is not None:
            row.posted_date = normalized.posted_date
        if not row.is_active:
            row.is_active = True
            stats.reactivated += 1
        stats.updated += 1

    can_deactivate = trust_empty or len(fetched) > 0
    for row in existing_rows:
        if not row.is_active:
            continue
        ident = identity_for_job(row)
        if ident is not None and ident in fetched_identities:
            continue
        if can_deactivate:
            row.is_active = False
            stats.deactivated += 1
        else:
            stats.skipped_deactivation = True

    return stats
