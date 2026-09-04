from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from scraper.database import dispose_engine, init_db, session_scope
from scraper.models import Company, Job, ScrapeLog

ROLE_NOUNS = frozenset(
    {
        "engineer", "developer", "manager", "director", "designer", "scientist",
        "analyst", "specialist", "technician", "coordinator", "intern", "architect",
        "lead", "consultant", "producer", "editor", "accountant", "planner",
        "executive", "associate", "assistant", "supervisor", "operator",
        "administrator", "representative", "buyer", "recruiter", "controller",
        "machinist", "welder", "fitter", "audiologist", "luthier", "apprentice",
        "president", "officer", "head", "chief", "strategist", "marketer",
        "writer", "researcher",
    }
)

NAVIGATION_PHRASES = frozenset(
    {
        "careers", "careers home", "browse careers", "jobs", "jobs & career", "job",
        "employment", "available positions", "see open positions", "open positions",
        "explore all job openings", "search job", "show all", "view details",
        "find out more", "click here to see career opportunities", "wanna join us",
        "our programs", "early careers", "early career programs",
        "students & graduates", "international opportunities", "job subscription",
        "working at ubisoft", "preferences", "alfred jobs",
        "pdf employment application", "jobs & careers",
    }
)

MAX_NAV_CTA_WORDS = 6
MAX_NAV_SUFFIX_WORDS = 4
BOILERPLATE_MAX_LEN = 80
MAX_TITLES_LISTED = 8
MAX_COMPANY_COL_LEN = 32
MAX_URL_COL_LEN = 90
MAX_TITLE_COL_LEN = 90

_HAS_ASCII_LETTER = re.compile(r"[A-Za-z]")
_LEADING_PUNCT = re.compile(r"^[\s\"'“‘+*\-.,:;!?()\[\]]{1,20}")
_TRAILING_PUNCT = re.compile(r"[\s\"'”’+*\-.,:;!?()\[\]]{1,20}$")
_WHITESPACE_RUN = re.compile(r"\s{1,10}")
_POLICY_WORD = re.compile(r"\bpolic(?:y|ies)\b", re.IGNORECASE)
_NAV_CTA_LEAD_IN = re.compile(r"^(?:click here|find out|wanna|browse|explore|see|view|show)\b")
_NAV_WORKING_AT = re.compile(r"^working at [a-z0-9&.,' -]{1,40}$")
_NAV_JOB_SUFFIX = re.compile(r"^[a-z0-9&.,' -]{1,30} (?:jobs|careers|career)$")
_ROLE_NOUN_PATTERN = re.compile(
    r"\b(?:" + "|".join(sorted(ROLE_NOUNS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

CLASSIFICATIONS = ("navigation", "boilerplate", "unreviewable", "job_shaped", "unclear")


@dataclass
class CompanyTitleRows:
    company_id: int
    company: str
    audio_scope: str
    careers_url: str
    titles: list = field(default_factory=list)


@dataclass
class CompanyFinding:
    company_id: int
    company: str
    audio_scope: str
    careers_url: str
    total_rows: int
    navigation: int
    boilerplate: int
    unreviewable: int
    job_shaped: int
    unclear: int
    titles: list
    reason: str = "chrome_rows"


def normalize_title(raw: str) -> str:
    text = _LEADING_PUNCT.sub("", raw)
    text = _TRAILING_PUNCT.sub("", text)
    text = _WHITESPACE_RUN.sub(" ", text).strip()
    return text.lower()


def has_role_noun(normalized: str) -> bool:
    return bool(_ROLE_NOUN_PATTERN.search(normalized))


def is_navigation_chrome(normalized: str) -> bool:
    if normalized in NAVIGATION_PHRASES:
        return True
    if has_role_noun(normalized):
        return False
    word_count = len(normalized.split())
    if word_count <= MAX_NAV_CTA_WORDS and _NAV_CTA_LEAD_IN.match(normalized):
        return True
    if _NAV_WORKING_AT.match(normalized):
        return True
    if word_count <= MAX_NAV_SUFFIX_WORDS and _NAV_JOB_SUFFIX.match(normalized):
        return True
    return False


def classify_title(title: str) -> str:
    raw = title.strip()
    if not _HAS_ASCII_LETTER.search(raw):
        return "unreviewable"
    normalized = normalize_title(raw)
    if is_navigation_chrome(normalized):
        return "navigation"
    if _POLICY_WORD.search(raw):
        return "boilerplate"
    if raw.endswith("."):
        return "boilerplate"
    if len(raw) > BOILERPLATE_MAX_LEN and not has_role_noun(normalized):
        return "boilerplate"
    if has_role_noun(normalized):
        return "job_shaped"
    return "unclear"


def _junk_share(finding: CompanyFinding) -> float:
    if finding.total_rows == 0:
        return 0.0
    return (finding.navigation + finding.boilerplate) / finding.total_rows


def _sort_key(finding: CompanyFinding) -> tuple:
    return (
        finding.audio_scope != "native",
        -_junk_share(finding),
        finding.total_rows,
        finding.company_id,
    )


def evaluate(rows: list) -> list:
    findings: list = []
    for row in rows:
        counts = {key: 0 for key in CLASSIFICATIONS}
        for title in row.titles:
            counts[classify_title(title)] += 1
        chrome_rows = counts["navigation"] + counts["boilerplate"]
        if chrome_rows:
            reason = "chrome_rows"
        elif counts["job_shaped"] == 0:
            reason = "no_job_shaped_row"
        else:
            continue
        findings.append(
            CompanyFinding(
                company_id=row.company_id,
                company=row.company,
                audio_scope=row.audio_scope,
                careers_url=row.careers_url,
                total_rows=len(row.titles),
                navigation=counts["navigation"],
                boilerplate=counts["boilerplate"],
                unreviewable=counts["unreviewable"],
                job_shaped=counts["job_shaped"],
                unclear=counts["unclear"],
                titles=list(row.titles),
                reason=reason,
            )
        )
    findings.sort(key=_sort_key)
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


def _active_titles(session: Session) -> dict:
    query = select(Job.company_id, Job.title).where(Job.is_active.is_(True))
    titles: dict = {}
    for company_id, title in session.execute(query).all():
        if company_id is None:
            continue
        titles.setdefault(company_id, []).append(title)
    return titles


def select_nonjob_candidates(session: Session) -> list:
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
    job_counts = _job_counts(session)
    active_titles = _active_titles(session)

    rows: list = []
    for company_id, name, careers_url, audio_scope in companies:
        active_jobs, board_jobs = job_counts.get(company_id, (0, 0))
        if active_jobs == 0 or board_jobs > 0:
            continue
        rows.append(
            CompanyTitleRows(
                company_id=company_id,
                company=name,
                audio_scope=audio_scope or "",
                careers_url=(careers_url or "").strip(),
                titles=active_titles.get(company_id, []),
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
    unreviewable_total = sum(finding.unreviewable for finding in findings)
    lines = [
        "# Non-job row detection report",
        "",
        "Read-only. This is a proposal list requiring human confirmation, not a",
        "list of confirmed problems. These are companies whose most recent",
        "scrape reported success and stored active rows, but none of those",
        "rows ever reached the public board. Classification is by title text",
        "alone, with no network access, so this cannot tell a careers page",
        "that genuinely lists one open role apart from a page whose listings",
        "were never actually read by the scraper. The usual fix is a",
        "corrected seed careers URL. The seed is hand-edited truth this tool",
        "never touches — confirmed cases belong in SEED_WORKLIST.md.",
        "",
        "The unreviewable bucket holds titles with no ASCII letters at all,",
        "such as Japanese-language postings. Those are not junk; they need a",
        "human who reads the language to judge them, so they are reported",
        "separately rather than folded into navigation or boilerplate.",
        "",
        "A company is flagged for one of two reasons. chrome_rows means it",
        "stored at least one row that is plainly navigation or boilerplate.",
        "no_job_shaped_row means nothing it stored carries a role noun at",
        "all — no engineer, manager, designer or the like — which catches",
        "product menus and press-release headlines that no phrase list would",
        "recognise. The second is the weaker signal of the two: a real job",
        "title without a role noun exists, so read those titles before",
        "acting.",
        "",
        f"- companies flagged: {len(findings)}",
    ]
    for scope, count in scope_counts.items():
        lines.append(f"- {scope}: {count}")
    lines.append(f"- unreviewable rows across flagged companies: {unreviewable_total}")
    lines.append("")
    lines.append(
        "Sorted highest-value repair first: native scope before partial, then "
        "descending share of navigation/boilerplate rows, then ascending total "
        "rows so the cleanest, most certain fixes lead."
    )
    lines.append("")
    for finding in findings:
        name = finding.company[:MAX_COMPANY_COL_LEN]
        lines.append(f"## {name}")
        lines.append(
            f"- reason={finding.reason} audio_scope={finding.audio_scope} "
            f"careers_url={finding.careers_url[:MAX_URL_COL_LEN]}"
        )
        lines.append(
            f"- total_rows={finding.total_rows} navigation={finding.navigation} "
            f"boilerplate={finding.boilerplate} unreviewable={finding.unreviewable} "
            f"job_shaped={finding.job_shaped} unclear={finding.unclear}"
        )
        listed_titles = finding.titles[:MAX_TITLES_LISTED]
        for title in listed_titles:
            lines.append(f"  - {title[:MAX_TITLE_COL_LEN]}")
        remaining = len(finding.titles) - len(listed_titles)
        if remaining > 0:
            lines.append(f"  - ... and {remaining} more")
        lines.append("")
    return "\n".join(lines)


def run(output_path: Path, limit: Optional[int]) -> list:
    init_db()
    try:
        with session_scope() as session:
            rows = select_nonjob_candidates(session)
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
            "never reach the public board and whose stored titles look like "
            "navigation chrome or boilerplate rather than jobs. Read-only, no "
            "network calls."
        )
    )
    parser.add_argument("--output", type=Path, default=Path("nonjob_rows_report.md"))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    findings = run(args.output, args.limit)

    print(f"companies flagged: {len(findings)}")
    for scope, count in _scope_summary(findings).items():
        print(f"{scope}: {count}")
    print(f"unreviewable rows: {sum(finding.unreviewable for finding in findings)}")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
