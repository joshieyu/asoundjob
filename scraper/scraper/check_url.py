from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

from sqlalchemy import func, select

from scraper.company_loader import slugify
from scraper.config import load_settings
from scraper.database import dispose_engine, session_scope
from scraper.models import Company
from scraper.normalizer import NormalizedJob, Normalizer
from scraper.scrapers.ats_discovery import discover
from scraper.scrapers.pipeline import ScrapePipeline

DEFAULT_AUDIO_SCOPE = "native"
LONG_DESCRIPTION_THRESHOLD = 200
SAMPLE_LIMIT = 10


@dataclass
class ResolvedContext:
    matched_company: Optional[str]
    category: Optional[str]
    audio_scope: str
    used_default: bool


@dataclass(frozen=True)
class DiscoveredAts:
    ats_type: str
    ats_slug: str


@dataclass
class Report:
    url: str
    context: ResolvedContext
    method: str
    success: bool
    error: Optional[str]
    discovered: list[DiscoveredAts] = field(default_factory=list)
    jobs: list[NormalizedJob] = field(default_factory=list)

    @property
    def total_jobs(self) -> int:
        return len(self.jobs)

    @property
    def long_description_count(self) -> int:
        return sum(
            1
            for job in self.jobs
            if job.description and len(job.description) > LONG_DESCRIPTION_THRESHOLD
        )

    @property
    def board_count(self) -> int:
        return sum(1 for job in self.jobs if job.is_audio_related)


def find_company_by_name(name: str) -> Optional[Company]:
    with session_scope() as session:
        row = session.execute(
            select(Company).where(func.lower(Company.name) == name.strip().lower())
        ).scalar_one_or_none()
        if row is None:
            return None
        return Company(
            id=row.id,
            name=row.name,
            slug=row.slug,
            category=row.category,
            careers_url=row.careers_url,
            audio_scope=row.audio_scope,
        )


def resolve_context(
    name: Optional[str],
    category_override: Optional[str],
    lookup: Callable[[str], Optional[Company]],
) -> ResolvedContext:
    matched = lookup(name) if name else None
    audio_scope = matched.audio_scope if matched is not None else DEFAULT_AUDIO_SCOPE
    if category_override is not None:
        category = category_override
    elif matched is not None:
        category = matched.category
    else:
        category = None
    used_default = category_override is None and matched is None
    return ResolvedContext(
        matched_company=matched.name if matched is not None else None,
        category=category,
        audio_scope=audio_scope or DEFAULT_AUDIO_SCOPE,
        used_default=used_default,
    )


def build_company(url: str, name: Optional[str], context: ResolvedContext) -> Company:
    display_name = name or url
    return Company(
        id=0,
        name=display_name,
        slug=slugify(display_name),
        careers_url=url,
        verified=True,
        category=context.category,
        audio_scope=context.audio_scope,
        ats_type=None,
        ats_slug=None,
        scrape_method="http",
    )


async def check_url(url: str, name: Optional[str], category_override: Optional[str]) -> Report:
    context = resolve_context(name, category_override, find_company_by_name)
    company = build_company(url, name, context)

    settings = load_settings()
    pipeline = ScrapePipeline(settings)
    discovered: list[DiscoveredAts] = []

    def _record_discovery(
        target: Company, html: Optional[str], overwrite: bool = False
    ) -> None:
        if not html:
            return
        for ats_type, ats_slug in discover(html, target.careers_url or ""):
            found = DiscoveredAts(ats_type=ats_type, ats_slug=ats_slug)
            if found not in discovered:
                discovered.append(found)

    pipeline._try_discovery = _record_discovery  # type: ignore[assignment,method-assign]

    try:
        result = await pipeline.scrape_company(company)
    finally:
        await pipeline.close()

    normalizer = Normalizer(settings)
    jobs = [
        normalizer.normalize(
            raw, audio_scope=company.audio_scope, company_category=company.category
        )
        for raw in result.jobs
    ]

    return Report(
        url=url,
        context=context,
        method=result.method,
        success=result.success,
        error=result.error,
        discovered=discovered,
        jobs=jobs,
    )


def report_to_dict(report: Report) -> dict:
    return {
        "url": report.url,
        "matched_company": report.context.matched_company,
        "category": report.context.category,
        "audio_scope": report.context.audio_scope,
        "used_default_category": report.context.used_default,
        "method": report.method,
        "success": report.success,
        "error": report.error,
        "discovered_ats": [
            {"ats_type": d.ats_type, "ats_slug": d.ats_slug, "saved": False}
            for d in report.discovered
        ],
        "total_jobs": report.total_jobs,
        "long_description_count": report.long_description_count,
        "board_count": report.board_count,
        "samples": [
            {
                "on_board": job.is_audio_related,
                "relevance_score": job.relevance_score,
                "categories": job.job_categories,
                "title": job.title,
            }
            for job in report.jobs[:SAMPLE_LIMIT]
        ],
    }


def format_report(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"url: {report.url}")
    if report.context.matched_company is not None:
        lines.append(f"matched company: {report.context.matched_company}")
    else:
        lines.append("matched company: none")
    if report.context.used_default:
        lines.append(
            f"category: {report.context.category} (default), audio_scope: "
            f"{report.context.audio_scope} (default)"
        )
    else:
        lines.append(
            f"category: {report.context.category}, audio_scope: {report.context.audio_scope}"
        )

    status = "success" if report.success else "FAILED"
    lines.append(f"scraper: {report.method} ({status})")
    if not report.success:
        lines.append(f"error: {report.error}")

    if report.discovered:
        for d in report.discovered:
            lines.append(
                f"ats discovered: {d.ats_type}/{d.ats_slug} (not saved to the database)"
            )
    else:
        lines.append("ats discovered: none")

    lines.append(f"total jobs found: {report.total_jobs}")
    lines.append(
        f"jobs with description > {LONG_DESCRIPTION_THRESHOLD} chars: "
        f"{report.long_description_count}"
    )
    lines.append("")
    lines.append(
        f">>> would appear on the public board: {report.board_count} / "
        f"{report.total_jobs} <<<"
    )
    lines.append("")

    if report.jobs:
        lines.append(f"sample rows (showing up to {SAMPLE_LIMIT}):")
        for job in report.jobs[:SAMPLE_LIMIT]:
            marker = "BOARD" if job.is_audio_related else "skip "
            categories = ",".join(job.job_categories) if job.job_categories else "-"
            lines.append(
                f"  [{marker}] score={job.relevance_score:<4} {categories:<30} {job.title}"
            )

    return "\n".join(lines)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test what a candidate careers URL would yield if seeded into the pipeline"
    )
    parser.add_argument("url", help="Candidate careers URL")
    parser.add_argument("--name", default=None, help="Company name, used for DB lookup")
    parser.add_argument(
        "--category", default=None, help="Explicit company category, overrides DB lookup"
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        report = asyncio.run(check_url(args.url, args.name, args.category))
    finally:
        dispose_engine()

    if args.json:
        print(json.dumps(report_to_dict(report), indent=2))
    else:
        print(format_report(report))

    return 0 if report.success else 1


if __name__ == "__main__":
    sys.exit(main())
