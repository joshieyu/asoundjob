from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scraper.company_loader import read_companies_file
from scraper.config import load_settings
from scraper.database import dispose_engine, get_session_factory
from scraper.models import (
    Company,
    CompanySuggestion,
    Job,
    JobFeedback,
    JobSubmission,
    ScrapeLog,
)


@dataclass
class Orphan:
    company_id: int
    name: str
    slug: str
    category: str
    job_count: int
    board_count: int
    scrape_log_count: int
    blockers: list[str] = field(default_factory=list)


@dataclass
class DeleteStats:
    companies: int = 0
    jobs: int = 0
    job_feedback: int = 0
    job_submissions: int = 0
    company_suggestions: int = 0
    scrape_logs: int = 0

    def summary(self) -> str:
        return (
            f"companies={self.companies} jobs={self.jobs} "
            f"job_feedback={self.job_feedback} "
            f"job_submissions={self.job_submissions} "
            f"company_suggestions={self.company_suggestions} "
            f"scrape_logs={self.scrape_logs}"
        )


def find_orphans(session: Session, seed_entries: list[dict[str, Any]]) -> list[Orphan]:
    seed_names = {str(entry["name"]).strip().lower() for entry in seed_entries}
    companies = session.execute(
        select(Company).where(Company.source != "manual")
    ).scalars().all()

    orphans: list[Orphan] = []
    for company in companies:
        if company.name.strip().lower() in seed_names:
            continue

        jobs = session.execute(
            select(Job).where(Job.company_id == company.id)
        ).scalars().all()
        job_ids = [job.id for job in jobs]
        board_count = sum(
            1 for job in jobs if job.is_active and job.is_audio_related
        )
        scrape_log_count = int(
            session.execute(
                select(func.count()).where(ScrapeLog.company_id == company.id)
            ).scalar_one()
        )

        blockers: list[str] = []

        non_scraper_jobs = sum(1 for job in jobs if job.source != "scraper")
        if non_scraper_jobs:
            blockers.append(f"{non_scraper_jobs} job(s) with source != scraper")

        overridden_jobs = sum(
            1
            for job in jobs
            if job.categories_override is not None
            or job.is_audio_related_override is not None
            or job.is_active_override is not None
        )
        if overridden_jobs:
            blockers.append(f"{overridden_jobs} job(s) with a human override set")

        if job_ids:
            feedback_count = int(
                session.execute(
                    select(func.count()).where(JobFeedback.job_id.in_(job_ids))
                ).scalar_one()
            )
        else:
            feedback_count = 0
        if feedback_count:
            blockers.append(f"{feedback_count} job feedback row(s)")

        submission_count = int(
            session.execute(
                select(func.count()).where(JobSubmission.company_id == company.id)
            ).scalar_one()
        )
        if submission_count:
            blockers.append(f"{submission_count} job submission(s)")

        suggestion_count = int(
            session.execute(
                select(func.count()).where(CompanySuggestion.company_id == company.id)
            ).scalar_one()
        )
        if suggestion_count:
            blockers.append(f"{suggestion_count} company suggestion(s)")

        orphans.append(
            Orphan(
                company_id=company.id,
                name=company.name,
                slug=company.slug,
                category=company.category,
                job_count=len(jobs),
                board_count=board_count,
                scrape_log_count=scrape_log_count,
                blockers=blockers,
            )
        )
    return orphans


def delete_orphans(
    session: Session, orphans: list[Orphan], allow_blocked: bool = False
) -> DeleteStats:
    blocked = [orphan for orphan in orphans if orphan.blockers]
    if blocked and not allow_blocked:
        names = ", ".join(orphan.name for orphan in blocked)
        raise ValueError(f"refusing to delete blocked orphan(s): {names}")

    stats = DeleteStats()
    for orphan in orphans:
        job_ids = [
            job_id
            for (job_id,) in session.execute(
                select(Job.id).where(Job.company_id == orphan.company_id)
            ).all()
        ]

        if job_ids:
            feedback_rows = session.execute(
                select(JobFeedback).where(JobFeedback.job_id.in_(job_ids))
            ).scalars().all()
            for feedback_row in feedback_rows:
                session.delete(feedback_row)
                stats.job_feedback += 1

        jobs = session.execute(
            select(Job).where(Job.company_id == orphan.company_id)
        ).scalars().all()
        for job in jobs:
            session.delete(job)
            stats.jobs += 1

        submissions = session.execute(
            select(JobSubmission).where(JobSubmission.company_id == orphan.company_id)
        ).scalars().all()
        for submission_row in submissions:
            session.delete(submission_row)
            stats.job_submissions += 1

        suggestions = session.execute(
            select(CompanySuggestion).where(
                CompanySuggestion.company_id == orphan.company_id
            )
        ).scalars().all()
        for suggestion_row in suggestions:
            session.delete(suggestion_row)
            stats.company_suggestions += 1

        scrape_logs = session.execute(
            select(ScrapeLog).where(ScrapeLog.company_id == orphan.company_id)
        ).scalars().all()
        for scrape_log_row in scrape_logs:
            session.delete(scrape_log_row)
            stats.scrape_logs += 1

        company = session.get(Company, orphan.company_id)
        if company is not None:
            session.delete(company)
            stats.companies += 1

    session.flush()
    return stats


def format_orphan_line(orphan: Orphan) -> str:
    return (
        f"- {orphan.name} (slug={orphan.slug}, category={orphan.category}) "
        f"jobs={orphan.job_count} board={orphan.board_count} "
        f"scrape_logs={orphan.scrape_log_count}"
    )


def render_report(
    orphans: list[Orphan],
    targets: list[Orphan],
    skipped: list[Orphan],
    applied: bool,
    stats: Optional[DeleteStats],
) -> str:
    lines: list[str] = []
    lines.append(f"orphans found: {len(orphans)}")
    lines.append("")
    for orphan in orphans:
        lines.append(format_orphan_line(orphan))
        for blocker in orphan.blockers:
            lines.append(f"    blocked: {blocker}")
    lines.append("")

    if skipped:
        lines.append(
            f"skipped (blocked, re-run with --include-blocked to override): "
            f"{len(skipped)}"
        )
        for orphan in skipped:
            lines.append(f"  - {orphan.name}")
        lines.append("")

    if applied:
        applied_stats = stats or DeleteStats()
        lines.append(f"applied: deleted {len(targets)} companies")
        lines.append(applied_stats.summary())
    else:
        lines.append(f"dry run: would delete {len(targets)} companies")
        lines.append("re-run with --apply to perform the deletion")

    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(
        description=(
            "Find companies whose rows have fallen out of the seed and "
            "optionally delete them, along with their jobs and scrape logs."
        )
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=settings.data_dir / "audio_companies_final.json",
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--include-blocked", action="store_true")
    args = parser.parse_args(argv)

    seed_entries = read_companies_file(args.file)

    factory = get_session_factory()
    try:
        with factory() as session:
            orphans = find_orphans(session, seed_entries)
            blocked = [orphan for orphan in orphans if orphan.blockers]
            clean = [orphan for orphan in orphans if not orphan.blockers]
            targets = orphans if args.include_blocked else clean
            skipped = [] if args.include_blocked else blocked

            stats: Optional[DeleteStats] = None
            if args.apply and targets:
                stats = delete_orphans(
                    session, targets, allow_blocked=args.include_blocked
                )
                session.commit()

            print(render_report(orphans, targets, skipped, args.apply, stats))
            print(
                f"summary: found={len(orphans)} deletable={len(targets)} "
                f"blocked_skipped={len(skipped)} applied={args.apply}"
            )
    finally:
        dispose_engine()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
