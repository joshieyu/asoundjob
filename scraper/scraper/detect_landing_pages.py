from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from scraper.countries import COUNTRY_ALIASES, COUNTRY_NAMES
from scraper.database import dispose_engine, init_db, session_scope
from scraper.detect_nonjob_rows import (
    MAX_COMPANY_COL_LEN,
    MAX_TITLE_COL_LEN,
    MAX_TITLES_LISTED,
    MAX_URL_COL_LEN,
    classify_title,
    normalize_title,
)
from scraper.models import Company, Job, ScrapeLog

TAXONOMY_SHARE_THRESHOLD = 0.5
BOARD_SHARE_THRESHOLD = 0.2
MAX_HOSTS_LISTED = 6

REGION_SUFFIX_WORDS = frozenset(
    {"careers", "career", "jobs", "job", "positions", "opportunities", "vacancies"}
)

COUNTRY_TOKENS = frozenset(name.lower() for name in COUNTRY_NAMES.values()) | frozenset(
    COUNTRY_ALIASES
)


@dataclass
class CompanyLandingRows:
    company_id: int
    company: str
    audio_scope: str
    careers_url: str
    board_rows: int
    rows: list = field(default_factory=list)


@dataclass
class HostCount:
    host: str
    count: int
    off_host: bool


@dataclass
class LandingPageFinding:
    company_id: int
    company: str
    audio_scope: str
    careers_url: str
    total_rows: int
    board_rows: int
    taxonomy_share: float
    board_share: float
    hosts: list
    distinct_off_host_hosts: int
    rows_lead_to: Optional[str]
    rows_lead_to_host: str
    rows_lead_to_count: int
    sample_titles: list


def normalize_host(url: str) -> str:
    host = urlparse(url or "").netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_region_row(normalized: str) -> bool:
    if normalized in COUNTRY_TOKENS:
        return True
    words = normalized.split()
    if len(words) >= 2 and words[-1] in REGION_SUFFIX_WORDS:
        remainder = " ".join(words[:-1])
        if remainder in COUNTRY_TOKENS:
            return True
    return False


def is_taxonomy_row(title: str) -> bool:
    classification = classify_title(title)
    if classification in ("navigation", "boilerplate"):
        return True
    return is_region_row(normalize_title(title))


def _host_counts(rows: list, careers_host: str) -> list:
    counts: Counter = Counter()
    for _, url in rows:
        counts[normalize_host(url)] += 1
    hosts = [
        HostCount(host=host, count=count, off_host=bool(host) and host != careers_host)
        for host, count in counts.items()
    ]
    hosts.sort(key=lambda entry: (-entry.count, entry.host))
    return hosts


def _path_length(url: str) -> int:
    return len(urlparse(url).path)


def _pick_listing_like_url(urls_at_host: list) -> str:
    counts: Counter = Counter(urls_at_host)
    distinct_urls = list(counts.keys())
    distinct_urls.sort(key=lambda url: (_path_length(url), -counts[url], url))
    return distinct_urls[0]


def _rows_lead_to(rows: list, careers_host: str) -> tuple:
    if not careers_host:
        return None, "", 0
    host_counts: Counter = Counter(
        normalize_host(url)
        for _, url in rows
        if url and normalize_host(url) not in ("", careers_host)
    )
    if not host_counts:
        return None, "", 0
    top_host, top_count = host_counts.most_common(1)[0]
    urls_at_host = [url for _, url in rows if normalize_host(url) == top_host]
    lead_url = _pick_listing_like_url(urls_at_host)
    return lead_url, top_host, top_count


def _sort_key(finding: LandingPageFinding) -> tuple:
    return (
        finding.audio_scope != "native",
        -finding.taxonomy_share,
        finding.board_share,
        finding.company_id,
    )


def evaluate(rows: list) -> list:
    findings: list = []
    for row in rows:
        total_rows = len(row.rows)
        if total_rows == 0:
            continue
        taxonomy_count = sum(1 for title, _ in row.rows if is_taxonomy_row(title))
        taxonomy_share = taxonomy_count / total_rows
        board_share = row.board_rows / total_rows
        if taxonomy_share < TAXONOMY_SHARE_THRESHOLD:
            continue
        if board_share > BOARD_SHARE_THRESHOLD:
            continue
        careers_host = normalize_host(row.careers_url)
        hosts = _host_counts(row.rows, careers_host)
        distinct_off_host_hosts = sum(1 for host_count in hosts if host_count.off_host)
        lead_url, lead_host, lead_count = _rows_lead_to(row.rows, careers_host)
        findings.append(
            LandingPageFinding(
                company_id=row.company_id,
                company=row.company,
                audio_scope=row.audio_scope,
                careers_url=row.careers_url,
                total_rows=total_rows,
                board_rows=row.board_rows,
                taxonomy_share=taxonomy_share,
                board_share=board_share,
                hosts=hosts,
                distinct_off_host_hosts=distinct_off_host_hosts,
                rows_lead_to=lead_url,
                rows_lead_to_host=lead_host,
                rows_lead_to_count=lead_count,
                sample_titles=[title for title, _ in row.rows],
            )
        )
    findings.sort(key=_sort_key)
    return findings


def _job_rows(session: Session) -> dict:
    query = select(Job.company_id, Job.title, Job.url).where(Job.is_active.is_(True))
    rows: dict = {}
    for company_id, title, url in session.execute(query).all():
        if company_id is None:
            continue
        rows.setdefault(company_id, []).append((title, url))
    return rows


def _board_counts(session: Session) -> dict:
    board_expr = func.sum(
        case((Job.is_active.is_(True) & Job.is_audio_related.is_(True), 1), else_=0)
    )
    query = select(Job.company_id, board_expr).group_by(Job.company_id)
    counts: dict = {}
    for company_id, board_jobs in session.execute(query).all():
        if company_id is None:
            continue
        counts[company_id] = int(board_jobs or 0)
    return counts


def select_landing_page_candidates(session: Session) -> list:
    latest_ids = (
        select(ScrapeLog.company_id, func.max(ScrapeLog.id).label("max_id"))
        .group_by(ScrapeLog.company_id)
        .subquery()
    )
    query = (
        select(Company.id, Company.name, Company.careers_url, Company.audio_scope)
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
    companies = session.execute(query).all()
    job_rows = _job_rows(session)
    board_counts = _board_counts(session)

    rows: list = []
    for company_id, name, careers_url, audio_scope in companies:
        company_rows = job_rows.get(company_id, [])
        if not company_rows:
            continue
        rows.append(
            CompanyLandingRows(
                company_id=company_id,
                company=name,
                audio_scope=audio_scope or "",
                careers_url=(careers_url or "").strip(),
                board_rows=board_counts.get(company_id, 0),
                rows=company_rows,
            )
        )
    return rows


def _scope_summary(findings: list) -> dict:
    counts: dict = {}
    for finding in findings:
        key = finding.audio_scope or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


def render(findings: list) -> str:
    scope_counts = _scope_summary(findings)
    with_lead = sum(1 for finding in findings if finding.rows_lead_to)
    lines = [
        "# Landing page detection report",
        "",
        "Read-only. Nothing is written to the database or to",
        "data/audio_companies_final.json. This is a candidate list for a",
        "human to review, not a list of confirmed problems.",
        "",
        "A company is flagged when its stored active rows are mostly",
        "navigation or taxonomy labels rather than job titles, and few or",
        "none of those rows ever reached the public board. Concretely: at",
        f"least {TAXONOMY_SHARE_THRESHOLD:.0%} of its active rows classify as",
        "navigation, boilerplate, or a bare region name (Germany Careers,",
        "Japan Careers, UK Jobs and the like), and at most",
        f"{BOARD_SHARE_THRESHOLD:.0%} of its active rows ever reached",
        "jobs.is_audio_related. Off-host row URLs are not part of the",
        "flagging condition by themselves, because plenty of companies",
        "legitimately host their board on an ATS domain.",
        "",
        "rows_lead_to is where a company's own rows point, on whichever",
        "off-host domain they point to most. It is a lead to open in a",
        "browser, not a value to paste into the seed. It is frequently a",
        "talent-community signup or a single stale job rather than the",
        "real board, especially for a single-row company where it is",
        "simply that one row's URL. Two spot checks through",
        "scraper.check_url both came back empty: Audionova's lead,",
        "https://www.sonova.com/en/jobs?brand=&country=722&keywords=,",
        "returned HTTP 404 and 0 jobs from every scraper method; AMX (Snap",
        "One)'s lead, an Oracle Cloud",
        "join-talent-community page, loaded but had no job links and 0",
        "jobs, because the row behind it was a talent-pool signup, not a",
        "board. Treat every rows_lead_to value as unverified until a human",
        "opens it.",
        "",
        f"- companies flagged: {len(findings)}",
    ]
    for scope, count in scope_counts.items():
        lines.append(f"- {scope}: {count}")
    lines.append(f"- flagged companies with a rows_lead_to value: {with_lead}")
    lines.append("")
    lines.append(
        "Sorted highest-value repair first: native scope before partial, then "
        "descending taxonomy share, then ascending board share, then company id."
    )
    lines.append("")
    for finding in findings:
        name = finding.company[:MAX_COMPANY_COL_LEN]
        lines.append(f"## {name}")
        lines.append(
            f"- audio_scope={finding.audio_scope} "
            f"careers_url={finding.careers_url[:MAX_URL_COL_LEN]}"
        )
        lines.append(
            f"- total_rows={finding.total_rows} board_rows={finding.board_rows} "
            f"taxonomy_share={finding.taxonomy_share:.2f} "
            f"board_share={finding.board_share:.2f} "
            f"distinct_off_host_hosts={finding.distinct_off_host_hosts}"
        )
        if finding.rows_lead_to:
            lines.append(
                f"- rows_lead_to={finding.rows_lead_to[:MAX_URL_COL_LEN]} "
                f"(host={finding.rows_lead_to_host}, {finding.rows_lead_to_count} rows)"
            )
        else:
            lines.append("- rows_lead_to=none")
        lines.append("- hosts:")
        for host_count in finding.hosts[:MAX_HOSTS_LISTED]:
            marker = "off-host" if host_count.off_host else "same-host"
            host_label = host_count.host or "(unresolvable)"
            lines.append(f"  - {host_label}: {host_count.count} ({marker})")
        remaining_hosts = len(finding.hosts) - MAX_HOSTS_LISTED
        if remaining_hosts > 0:
            lines.append(f"  - ... and {remaining_hosts} more hosts")
        listed_titles = finding.sample_titles[:MAX_TITLES_LISTED]
        lines.append("- sample titles:")
        for title in listed_titles:
            lines.append(f"  - {title[:MAX_TITLE_COL_LEN]}")
        remaining_titles = len(finding.sample_titles) - len(listed_titles)
        if remaining_titles > 0:
            lines.append(f"  - ... and {remaining_titles} more")
        lines.append("")
    return "\n".join(lines)


def run(output_path: Path, limit: Optional[int]) -> list:
    init_db()
    try:
        with session_scope() as session:
            rows = select_landing_page_candidates(session)
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
            "Flag verified, successfully-scraped companies whose active rows "
            "are mostly navigation or taxonomy labels rather than job titles "
            "and whose rows rarely reach the public board, the pattern seen "
            "when careers_url points at a landing page rather than the real "
            "job board. Read-only, no network calls."
        )
    )
    parser.add_argument("--output", type=Path, default=Path("landing_pages_report.md"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    findings = run(args.output, args.limit)

    print(f"companies flagged: {len(findings)}")
    for scope, count in _scope_summary(findings).items():
        print(f"{scope}: {count}")
    with_lead = sum(1 for finding in findings if finding.rows_lead_to)
    print(f"flagged companies with a rows_lead_to value: {with_lead}")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
