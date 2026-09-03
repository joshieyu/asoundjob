from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from scraper.company_loader import careers_urls_for
from scraper.config import Settings, load_settings
from scraper.database import dispose_engine, init_db, session_scope
from scraper.deduplicator import ReconcileStats, reconcile_company_jobs
from scraper.models import Company, Job, ScrapeLog
from scraper.normalizer import Normalizer
from scraper.scrapers.ats_discovery import discover
from scraper.scrapers.base import ScrapeResult
from scraper.scrapers.pipeline import ScrapePipeline

logger = logging.getLogger(__name__)

PROGRESS_EVERY = 25


@dataclass
class CycleStats:
    companies_attempted: int = 0
    succeeded: int = 0
    failed: int = 0
    jobs_found: int = 0
    inserted: int = 0
    updated: int = 0
    reactivated: int = 0
    deactivated: int = 0
    deactivations_skipped: int = 0
    method_counts: dict = field(default_factory=dict)

    def summary(self) -> str:
        methods = " ".join(
            f"{method}={count}" for method, count in sorted(self.method_counts.items())
        )
        return (
            f"companies={self.companies_attempted} ok={self.succeeded} "
            f"failed={self.failed} jobs_found={self.jobs_found} | "
            f"db: inserted={self.inserted} updated={self.updated} "
            f"reactivated={self.reactivated} deactivated={self.deactivated} "
            f"deactivation_skips={self.deactivations_skipped}"
            + (f" | via {methods}" if methods else "")
        )


async def _scrape_with_company(
    pipeline: ScrapePipeline, company: Company
) -> tuple[Company, ScrapeResult]:
    result = await pipeline.scrape_company(company)
    return company, result


def persist_result(
    normalizer: Normalizer,
    company: Company,
    result: ScrapeResult,
) -> tuple[int, ReconcileStats | None]:
    if not result.success:
        with session_scope() as session:
            session.add(
                ScrapeLog(
                    company_id=company.id,
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    status="failed",
                    jobs_found=0,
                    error_message=(result.error or "unknown error")[:500],
                    scrape_method=result.method,
                )
            )
        return 0, None

    with session_scope() as session:
        managed = session.get(Company, company.id)
        if managed is None:
            return 0, None
        normalized_jobs = [
            normalizer.normalize(
                raw,
                audio_scope=managed.audio_scope or "native",
                company_category=managed.category,
            )
            for raw in result.jobs
        ]
        stats = reconcile_company_jobs(
            session,
            managed,
            normalized_jobs,
            result.trust_empty,
            allow_deactivation=not result.partial,
        )
        finished_at = datetime.now(timezone.utc)
        session.add(
            ScrapeLog(
                company_id=company.id,
                started_at=finished_at,
                finished_at=finished_at,
                status="success",
                jobs_found=len(normalized_jobs),
                error_message=None,
                scrape_method=result.method,
            )
        )
        managed.last_scraped_at = finished_at
        return len(normalized_jobs), stats


async def run_cycle(
    settings: Settings,
    limit: int | None,
    only_slug: str | None,
    skip_load: bool,
) -> CycleStats:
    from scraper.company_loader import load_companies, read_companies_file

    if not skip_load:
        companies_data = read_companies_file(
            settings.data_dir / "audio_companies_final.json"
        )
        with session_scope() as session:
            stats = load_companies(session, companies_data)
        logger.info("company sync: %s", stats.summary())

    query = select(Company).where(Company.verified.is_(True), Company.careers_url.is_not(None))
    if only_slug:
        query = query.where(Company.slug == only_slug)
    query = query.order_by(Company.name)
    with session_scope() as session:
        companies = session.execute(query).scalars().all()
        detached = [
            Company(
                id=c.id,
                name=c.name,
                slug=c.slug,
                category=c.category,
                careers_url=c.careers_url,
                extra_careers_urls=c.extra_careers_urls,
                website_url=c.website_url,
                verified=c.verified,
                source=c.source,
                scrape_method=c.scrape_method,
                audio_scope=c.audio_scope,
                ats_type=c.ats_type,
                ats_slug=c.ats_slug,
            )
            for c in companies
        ]
    if limit:
        detached = detached[:limit]

    scrape_list, skip_list = _dedupe_shared_urls(detached)
    if skip_list:
        _deactivate_duplicate_jobs(skip_list)
        logger.info(
            "dedup: %d companies share URLs with already-scraped companies, "
            "deactivated their jobs",
            len(skip_list),
        )

    cycle = CycleStats(companies_attempted=len(scrape_list))
    if not scrape_list:
        return cycle

    normalizer = Normalizer(settings)
    pipeline = ScrapePipeline(settings)
    total = len(scrape_list)
    completed = 0
    started = time.monotonic()

    try:
        tasks = [_scrape_with_company(pipeline, c) for c in scrape_list]
        for fut in asyncio.as_completed(tasks):
            company, result = await fut
            completed += 1
            try:
                found, detail = persist_result(normalizer, company, result)
            except Exception:
                logger.exception("persist failed for %s", company.name)
                cycle.failed += 1
                continue

            if result.success:
                cycle.succeeded += 1
                cycle.jobs_found += found
                cycle.method_counts[result.method] = (
                    cycle.method_counts.get(result.method, 0) + 1
                )
                if detail is not None:
                    cycle.inserted += detail.inserted
                    cycle.updated += detail.updated
                    cycle.reactivated += detail.reactivated
                    cycle.deactivated += detail.deactivated
                    if detail.skipped_deactivation:
                        cycle.deactivations_skipped += 1
                logger.debug(
                    "%s ok via %s: %d jobs (%s)",
                    company.name,
                    result.method,
                    found,
                    detail.summary() if detail else "n/a",
                )
            else:
                cycle.failed += 1
                logger.info("%s FAILED via %s: %s", company.name, result.method, result.error)

            if completed % PROGRESS_EVERY == 0 or completed == total:
                elapsed = time.monotonic() - started
                print(
                    f"progress {completed}/{total} ({elapsed:.0f}s) — "
                    f"ok={cycle.succeeded} failed={cycle.failed}",
                    flush=True,
                )
    finally:
        await pipeline.close()

    return cycle


def _dedupe_shared_urls(
    companies: list[Company],
) -> tuple[list[Company], list[Company]]:
    seen_urls: set[str] = set()
    seen_boards: set[tuple[str, str]] = set()
    scrape_list: list[Company] = []
    skip_list: list[Company] = []
    for c in companies:
        url = (c.careers_url or "").strip().lower()
        board = (
            ((c.ats_type or "").strip().lower(), (c.ats_slug or "").strip().lower())
            if c.ats_type
            else None
        )
        if url in seen_urls:
            skip_list.append(c)
            continue
        if board is not None and board in seen_boards:
            logger.info(
                "dedup: skipping %s, board %s/%s already claimed",
                c.name,
                board[0],
                board[1],
            )
            skip_list.append(c)
            continue
        for extra in careers_urls_for(c):
            seen_urls.add(extra.strip().lower())
        seen_urls.add(url)
        if board is not None and _url_corroborates_board(c.careers_url, board):
            seen_boards.add(board)
        scrape_list.append(c)
    return scrape_list, skip_list


def _url_corroborates_board(careers_url: Optional[str], board: tuple[str, str]) -> bool:
    url = (careers_url or "").strip()
    if not url:
        return False
    for ats_type, ats_slug in discover(url, url):
        if (ats_type.strip().lower(), ats_slug.strip().lower()) == board:
            return True
    return False


def _deactivate_duplicate_jobs(companies: list[Company]) -> None:
    if not companies:
        return
    from sqlalchemy import update as sa_update

    company_ids = [c.id for c in companies]
    with session_scope() as session:
        session.execute(
            sa_update(Company)
            .where(Company.id.in_(company_ids))
            .values(last_scraped_at=datetime.now(timezone.utc))
        )
        session.execute(
            sa_update(Job)
            .where(Job.company_id.in_(company_ids))
            .values(is_active=False)
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ASoundJob scraper")
    parser.add_argument("--once", action="store_true", help="Run a single scrape cycle (default)")
    parser.add_argument("--limit", type=int, default=None, help="Scrape at most N companies")
    parser.add_argument("--company", type=str, default=None, help="Scrape a single company by slug")
    parser.add_argument("--skip-load", action="store_true", help="Skip company JSON sync")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    settings = load_settings()
    init_db()
    started = time.monotonic()
    try:
        cycle = asyncio.run(run_cycle(settings, args.limit, args.company, args.skip_load))
    except KeyboardInterrupt:
        print("\nInterrupted", flush=True)
        return 130
    finally:
        dispose_engine()

    elapsed = time.monotonic() - started
    print(f"\nCycle complete in {elapsed:.0f}s\n{cycle.summary()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
