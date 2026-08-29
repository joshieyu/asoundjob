from __future__ import annotations

import argparse

from sqlalchemy import select

from scraper.database import dispose_engine, init_db, session_scope
from scraper.models import Company, Job
from scraper.normalizer import category_to_scope, classify_categories, score_relevance


def backfill(dry_run: bool = False) -> None:
    with session_scope() as session:
        companies = session.execute(select(Company)).scalars().all()
        scoped = 0
        for company in companies:
            if company.source == "manual":
                continue
            desired = category_to_scope(company.category)
            if company.audio_scope != desired:
                company.audio_scope = desired
                scoped += 1
        print(f"company scopes synced: {scoped} updated, {len(companies) - scoped} unchanged")

        rows = session.execute(
            select(Job, Company.audio_scope)
            .join(Company, Job.company_id == Company.id)
            .where(Job.source == "scraper")
        ).all()

        related = 0
        recategorized = 0
        for job, scope in rows:
            categories = classify_categories(job.title, job.description)
            score, is_related = score_relevance(
                job.title, job.description, categories, scope or "native"
            )
            if list(job.job_categories or []) != categories:
                job.job_categories = categories
                recategorized += 1
            job.relevance_score = score
            job.is_audio_related = is_related
            related += is_related

        print(
            f"scored {len(rows)} scraped jobs: {related} audio-related, "
            f"{len(rows) - related} filtered out, {recategorized} recategorized"
        )

        if dry_run:
            session.rollback()
            print("dry run: no changes written")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score existing jobs for audio relevance")
    parser.add_argument("--dry-run", action="store_true", help="Report counts without writing")
    args = parser.parse_args()
    init_db()
    try:
        backfill(dry_run=args.dry_run)
    finally:
        dispose_engine()


if __name__ == "__main__":
    main()
