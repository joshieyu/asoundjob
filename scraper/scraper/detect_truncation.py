from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qsl, urlsplit

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from scraper.database import dispose_engine, init_db, session_scope
from scraper.models import Company, Job, ScrapeLog
from scraper.scrapers.ats.adp import MAX_PAGES as ADP_MAX_PAGES
from scraper.scrapers.ats.adp import PAGE_SIZE as ADP_PAGE_SIZE
from scraper.scrapers.ats.amazon import MAX_PAGES as AMAZON_MAX_PAGES
from scraper.scrapers.ats.amazon import PAGE_SIZE as AMAZON_PAGE_SIZE
from scraper.scrapers.ats.apple import MAX_PAGES as APPLE_MAX_PAGES
from scraper.scrapers.ats.apple import PAGE_SIZE as APPLE_PAGE_SIZE
from scraper.scrapers.ats.eightfold import MAX_PAGES as EIGHTFOLD_MAX_PAGES
from scraper.scrapers.ats.icims import MAX_PAGES as ICIMS_MAX_PAGES
from scraper.scrapers.ats.icims import PAGE_SIZE as ICIMS_PAGE_SIZE
from scraper.scrapers.ats.successfactors import MAX_PAGES as SUCCESSFACTORS_MAX_PAGES
from scraper.scrapers.ats.successfactors import PAGE_SIZE as SUCCESSFACTORS_PAGE_SIZE
from scraper.scrapers.ats.ultipro import MAX_PAGES as ULTIPRO_MAX_PAGES
from scraper.scrapers.ats.ultipro import PAGE_SIZE as ULTIPRO_PAGE_SIZE
from scraper.scrapers.ats.workday import MAX_PAGES as WORKDAY_MAX_PAGES
from scraper.scrapers.ats.workday import PAGE_SIZE as WORKDAY_PAGE_SIZE

EIGHTFOLD_SEARCH_RESPONSE_PAGE_SIZE = 10

CAP_BY_SCRAPE_METHOD: dict = {
    "eightfold": EIGHTFOLD_MAX_PAGES * EIGHTFOLD_SEARCH_RESPONSE_PAGE_SIZE,
    "apple": APPLE_MAX_PAGES * APPLE_PAGE_SIZE,
    "icims": ICIMS_MAX_PAGES * ICIMS_PAGE_SIZE,
    "adp": ADP_MAX_PAGES * ADP_PAGE_SIZE,
    "ultipro": ULTIPRO_MAX_PAGES * ULTIPRO_PAGE_SIZE,
    "successfactors": SUCCESSFACTORS_MAX_PAGES * SUCCESSFACTORS_PAGE_SIZE,
    "workday": WORKDAY_MAX_PAGES * WORKDAY_PAGE_SIZE,
    "amazon": AMAZON_MAX_PAGES * AMAZON_PAGE_SIZE,
}

SCOPING_QUERY_KEYS = frozenset({"q", "query", "search", "keyword"})

MAX_COMPANY_COL_LEN = 32
MAX_URL_COL_LEN = 90


@dataclass
class CompanyMetrics:
    company_id: int
    company: str
    scrape_method: str
    jobs_found: int
    active_jobs: int
    board_jobs: int
    audio_scope: str
    careers_url: str
    careers_url_count: int = 1


@dataclass
class TruncationFinding:
    company_id: int
    company: str
    scrape_method: str
    cap: int
    careers_url_count: int
    jobs_found: int
    active_jobs: int
    board_jobs: int
    audio_scope: str
    careers_url: str
    already_scoped: bool


def has_scoping_query(careers_url: str) -> bool:
    query = urlsplit(careers_url.strip()).query
    for key, value in parse_qsl(query, keep_blank_values=True):
        if key.strip().lower() in SCOPING_QUERY_KEYS and value.strip():
            return True
    return False


def evaluate(
    rows: list,
    cap_by_method: Optional[dict] = None,
) -> list:
    caps = cap_by_method if cap_by_method is not None else CAP_BY_SCRAPE_METHOD
    findings: list = []
    for row in rows:
        per_url_cap = caps.get(row.scrape_method)
        if per_url_cap is None:
            continue
        url_count = max(1, row.careers_url_count)
        cap = per_url_cap * url_count
        if row.jobs_found < cap:
            continue
        findings.append(
            TruncationFinding(
                company_id=row.company_id,
                company=row.company,
                scrape_method=row.scrape_method,
                cap=cap,
                careers_url_count=url_count,
                jobs_found=row.jobs_found,
                active_jobs=row.active_jobs,
                board_jobs=row.board_jobs,
                audio_scope=row.audio_scope,
                careers_url=row.careers_url,
                already_scoped=has_scoping_query(row.careers_url),
            )
        )
    findings.sort(key=lambda finding: (finding.board_jobs, -finding.jobs_found))
    return findings


def _job_counts(session: Session) -> dict:
    active_expr = func.sum(case((Job.is_active.is_(True), 1), else_=0))
    board_expr = func.sum(
        case((Job.is_active.is_(True) & Job.is_audio_related.is_(True), 1), else_=0)
    )
    query = select(Job.company_id, active_expr, board_expr).group_by(Job.company_id)
    counts: dict = {}
    for company_id, active_jobs, board_jobs in session.execute(query).all():
        if company_id is None:
            continue
        counts[company_id] = (int(active_jobs or 0), int(board_jobs or 0))
    return counts


def select_scrape_metrics(session: Session) -> list:
    latest_ids = (
        select(ScrapeLog.company_id, func.max(ScrapeLog.id).label("max_id"))
        .group_by(ScrapeLog.company_id)
        .subquery()
    )
    query = (
        select(
            Company.id,
            Company.name,
            Company.careers_url,
            Company.extra_careers_urls,
            Company.audio_scope,
            ScrapeLog.scrape_method,
            ScrapeLog.jobs_found,
        )
        .join(ScrapeLog, ScrapeLog.company_id == Company.id)
        .join(
            latest_ids,
            (ScrapeLog.company_id == latest_ids.c.company_id)
            & (ScrapeLog.id == latest_ids.c.max_id),
        )
        .where(Company.verified.is_(True))
        .where(ScrapeLog.status == "success")
        .order_by(Company.id)
    )
    rows = session.execute(query).all()
    job_counts = _job_counts(session)

    metrics: list = []
    for (
        company_id,
        name,
        careers_url,
        extra_careers_urls,
        audio_scope,
        scrape_method,
        jobs_found,
    ) in rows:
        active_jobs, board_jobs = job_counts.get(company_id, (0, 0))
        metrics.append(
            CompanyMetrics(
                company_id=company_id,
                company=name,
                scrape_method=(scrape_method or "").strip(),
                jobs_found=jobs_found,
                active_jobs=active_jobs,
                board_jobs=board_jobs,
                audio_scope=audio_scope or "",
                careers_url=(careers_url or "").strip(),
                careers_url_count=1 + len(extra_careers_urls or []),
            )
        )
    return metrics


def _summary_by_method(findings: list) -> dict:
    counts: dict = {}
    for finding in findings:
        counts[finding.scrape_method] = counts.get(finding.scrape_method, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def render(findings: list) -> str:
    summary = _summary_by_method(findings)
    lines = [
        "# Truncation detection report",
        "",
        "Read-only. This is a proposal list requiring human confirmation, not a",
        "list of confirmed problems. A company that genuinely has exactly",
        "cap-many openings looks identical to a truncated one from jobs_found",
        "alone — the only way to tell them apart is to ask the ATS directly,",
        "and this tool makes no network calls. It only compares each company's",
        "most recent successful jobs_found against its parser's known page",
        "cap. Nothing here is written to data/audio_companies_final.json or to",
        "the database.",
        "",
        "The usual fix for a truncated partial-scope employer is a scoping",
        "query in the seed careers URL (for example ?query=audio) so the ATS",
        "itself returns fewer, more relevant pages instead of the whole board.",
        "The seed is hand-edited truth — this tool never edits it, it only",
        "points at where a human should look.",
        "",
        "A company with several careers URLs is measured against its per-URL",
        "cap times the number of URLs it holds, because jobs_found is their",
        "deduplicated union. That keeps every multi-URL company from being",
        "flagged on arithmetic alone, at the cost of a blind spot: one query",
        "of several can be truncated without the union reaching the total.",
        "",
        f"- companies flagged: {len(findings)}",
    ]
    for method, count in summary.items():
        lines.append(
            f"- {method}: {count} (cap {CAP_BY_SCRAPE_METHOD.get(method)} per careers URL)"
        )
    lines.append("")
    lines.append(
        "Sorted worst waste first: fewest board rows for the most jobs fetched."
    )
    lines.append("")
    for finding in findings:
        name = finding.company[:MAX_COMPANY_COL_LEN]
        scoped = "already scoped" if finding.already_scoped else "no scoping query"
        lines.append(f"## {name}")
        lines.append(
            f"- method={finding.scrape_method} cap={finding.cap} "
            f"careers_urls={finding.careers_url_count} "
            f"jobs_found={finding.jobs_found}"
        )
        lines.append(
            f"- active_jobs={finding.active_jobs} board_jobs={finding.board_jobs} "
            f"audio_scope={finding.audio_scope}"
        )
        lines.append(f"- careers_url ({scoped}): {finding.careers_url[:MAX_URL_COL_LEN]}")
        lines.append("")
    return "\n".join(lines)


def run(output_path: Path, limit: Optional[int]) -> list:
    init_db()
    try:
        with session_scope() as session:
            rows = select_scrape_metrics(session)
    finally:
        dispose_engine()
    findings = evaluate(rows)
    if limit is not None:
        findings = findings[:limit]
    output_path.write_text(render(findings))
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Flag companies whose most recent successful scrape likely hit "
            "their parser's page cap. Read-only, no network calls."
        )
    )
    parser.add_argument("--output", type=Path, default=Path("truncation_report.md"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    findings = run(args.output, args.limit)

    print(f"companies flagged: {len(findings)}")
    for method, count in _summary_by_method(findings).items():
        print(f"{method}: {count}")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
