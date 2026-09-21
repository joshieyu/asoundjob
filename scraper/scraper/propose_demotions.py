from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scraper.company_health import (
    DESCRIPTION_MIN_CHARS,
    GRADE_ORDER,
    grade_company,
    grade_rank,
    in_scrape_population,
    shape_shares,
)
from scraper.database import dispose_engine, get_session_factory
from scraper.models import Company, Job, ScrapeLog
from scraper.url_shape import classify_careers_url

MAX_SAMPLE_TITLES = 8
DEFAULT_GRADES = ("furniture",)

GRADE_DESCRIPTIONS: dict[str, str] = {
    "failing": "the most recent scrape attempt failed outright.",
    "furniture": (
        "there are active rows, none of them carry a real description, and "
        "fewer than a quarter look role-shaped by title (English or "
        "international role nouns) — the classic sign of nav chrome or "
        "studio-location lists stored as if they were jobs."
    ),
    "thin": (
        "there are active rows, but fewer than 20% of them carry a real "
        "description."
    ),
    "idle": (
        "rows and descriptions look fine, but nothing from this company has "
        "ever reached the public board."
    ),
    "healthy": "not a demotion candidate.",
    "silent": (
        "the scrape succeeds but comes back with nothing. Either the "
        "company genuinely has no openings, or the parser cannot read the "
        "board — check audio_scope, because a native-scope company here is "
        "a coverage bug, not a demotion candidate."
    ),
    "unscraped": (
        "not in the scrape population at all (unverified, blocked, or no "
        "careers URL), so there is nothing to demote."
    ),
}


@dataclass
class DemotionCandidate:
    company_id: int
    name: str
    slug: str
    category: str
    careers_url: Optional[str]
    url_shape: str
    audio_scope: str
    grade: str
    active_rows: int
    board_count: int
    described_share: float
    role_share: float
    last_scrape_status: Optional[str]
    consecutive_failures: int
    sample_titles: list[str] = field(default_factory=list)
    removes_live_board_rows: bool = False


def _company_job_data(session: Session) -> dict[int, dict]:
    described_len = func.length(func.trim(func.coalesce(Job.description, "")))
    query = (
        select(Job.company_id, Job.title, described_len, Job.is_audio_related)
        .where(Job.is_active.is_(True))
        .order_by(Job.company_id, Job.id)
    )
    data: dict[int, dict] = {}
    for company_id, title, desc_len, is_audio_related in session.execute(query).all():
        if company_id is None:
            continue
        entry = data.setdefault(
            company_id, {"titles": [], "described_flags": [], "board_count": 0}
        )
        entry["titles"].append(title)
        entry["described_flags"].append(int(desc_len or 0) >= DESCRIPTION_MIN_CHARS)
        if is_audio_related:
            entry["board_count"] += 1
    return data


def _scrape_log_status(session: Session) -> dict[int, tuple[Optional[str], int]]:
    query = select(ScrapeLog.company_id, ScrapeLog.status).order_by(
        ScrapeLog.company_id, ScrapeLog.started_at.desc(), ScrapeLog.id.desc()
    )
    ordered_statuses: dict[int, list[str]] = {}
    for company_id, status in session.execute(query).all():
        if company_id is None:
            continue
        ordered_statuses.setdefault(company_id, []).append(status)

    result: dict[int, tuple[Optional[str], int]] = {}
    for company_id, statuses in ordered_statuses.items():
        last_status = statuses[0]
        consecutive_failures = 0
        for status in statuses:
            if status == "failed":
                consecutive_failures += 1
            else:
                break
        result[company_id] = (last_status, consecutive_failures)
    return result


def gather_candidates(session: Session) -> list[DemotionCandidate]:
    job_data = _company_job_data(session)
    scrape_status = _scrape_log_status(session)
    companies = session.execute(
        select(
            Company.id,
            Company.name,
            Company.slug,
            Company.category,
            Company.careers_url,
            Company.verified,
            Company.scrape_blocked,
            Company.audio_scope,
        ).where(Company.verified.is_(True))
    ).all()

    candidates: list[DemotionCandidate] = []
    for (
        company_id,
        name,
        slug,
        category,
        careers_url,
        verified,
        scrape_blocked,
        audio_scope,
    ) in companies:
        entry = job_data.get(company_id) or {
            "titles": [], "described_flags": [], "board_count": 0,
        }
        titles: list[str] = entry["titles"]
        active_rows = len(titles)
        described_share, role_share = shape_shares(
            titles, entry["described_flags"]
        )
        board_count = entry["board_count"]
        last_scrape_status, consecutive_failures = scrape_status.get(
            company_id, (None, 0)
        )
        scraped = in_scrape_population(verified, careers_url, scrape_blocked)
        grade = grade_company(
            active_rows,
            described_share,
            role_share,
            board_count,
            last_scrape_status,
            scraped=scraped,
        )
        candidates.append(
            DemotionCandidate(
                company_id=company_id,
                name=name,
                slug=slug,
                category=category,
                careers_url=careers_url,
                url_shape=classify_careers_url(careers_url),
                audio_scope=audio_scope,
                grade=grade,
                active_rows=active_rows,
                board_count=board_count,
                described_share=described_share,
                role_share=role_share,
                last_scrape_status=last_scrape_status,
                consecutive_failures=consecutive_failures,
                sample_titles=titles[:MAX_SAMPLE_TITLES],
                removes_live_board_rows=board_count > 0,
            )
        )
    return candidates


def filter_candidates(
    candidates: list[DemotionCandidate],
    grades: list[str],
    min_active: int,
    min_consecutive_failures: int,
) -> list[DemotionCandidate]:
    grade_set = set(grades)
    kept: list[DemotionCandidate] = []
    for candidate in candidates:
        if candidate.grade not in grade_set:
            continue
        if (
            candidate.grade in ("furniture", "thin")
            and candidate.active_rows < min_active
        ):
            continue
        if (
            candidate.grade == "failing"
            and candidate.consecutive_failures < min_consecutive_failures
        ):
            continue
        kept.append(candidate)
    return kept


def rank_candidates(
    candidates: list[DemotionCandidate],
) -> list[DemotionCandidate]:
    return sorted(
        candidates,
        key=lambda c: (grade_rank(c.grade), -c.active_rows, c.name.lower()),
    )


def parse_grades(raw: str) -> list[str]:
    grades = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = [grade for grade in grades if grade not in GRADE_ORDER]
    if invalid:
        raise SystemExit(
            f"unknown grade(s): {', '.join(invalid)}; choose from "
            f"{', '.join(GRADE_ORDER)}"
        )
    return grades or list(DEFAULT_GRADES)


def grade_counts(candidates: list[DemotionCandidate]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.grade] = counts.get(candidate.grade, 0) + 1
    return counts


def write_json(
    path: Path,
    candidates: list[DemotionCandidate],
    grades: list[str],
    min_active: int,
    min_consecutive_failures: int,
    limit: Optional[int],
) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "grades": grades,
            "min_active": min_active,
            "min_consecutive_failures": min_consecutive_failures,
            "limit": limit,
        },
        "counts_by_grade": grade_counts(candidates),
        "candidates": [asdict(candidate) for candidate in candidates],
    }
    path.write_text(json.dumps(payload, indent=2))


def render(
    candidates: list[DemotionCandidate],
    grades: list[str],
    min_active: int,
    min_consecutive_failures: int,
) -> str:
    lines = [
        "# Demotion proposals",
        "",
        "Read-only. This tool wrote nothing to the database and nothing to "
        "data/audio_companies_final.json. Every company below is currently "
        '`"verified": true` in the seed. If a human agrees a company belongs '
        'here, the fix is to open the seed file by hand and set '
        '`"verified": false` on that entry — this tool never does that '
        "itself.",
        "",
        "Each candidate's url_shape is judged from its seeded careers_url "
        "alone, with no network call. A candidate whose url_shape is "
        "not_careers or bad_page is probably a wrong seeded URL rather than "
        "a company that deserves demoting — fix the URL before demoting.",
        "",
        f"Filters used: grades={', '.join(grades)}, min_active={min_active}, "
        f"min_consecutive_failures={min_consecutive_failures} "
        "(only applied to the failing grade).",
        "",
        "## What each grade means",
        "",
    ]
    for grade in GRADE_ORDER:
        if grade in grades:
            lines.append(f"- **{grade}**: {GRADE_DESCRIPTIONS[grade]}")
    lines.append("")
    lines.append(f"- candidates: {len(candidates)}")
    for grade, count in grade_counts(candidates).items():
        lines.append(f"- {grade}: {count}")
    lines.append("")

    board_impact = [c for c in candidates if c.removes_live_board_rows]
    if board_impact:
        lines += [
            "## WARNING — these demotions remove live board rows",
            "",
            "Setting `verified: false` on any of the following deactivates "
            "jobs that are on the public board right now. Read the evidence "
            "before acting.",
            "",
        ]
        for candidate in board_impact:
            lines.append(
                f"- {candidate.name} — {candidate.board_count} row(s) "
                "currently on the board"
            )
        lines.append("")

    lines += ["## Candidates", ""]
    for candidate in candidates:
        lines.append(f"### {candidate.name}")
        if candidate.removes_live_board_rows:
            lines.append(
                f"**REMOVES {candidate.board_count} LIVE BOARD ROW"
                f"{'S' if candidate.board_count != 1 else ''} — read "
                "before demoting**"
            )
        lines.append(f"- slug: {candidate.slug}")
        lines.append(f"- category: {candidate.category}")
        lines.append(f"- audio_scope: {candidate.audio_scope}")
        lines.append(
            f"- careers_url: {candidate.careers_url or '(none)'} "
            f"(url_shape={candidate.url_shape})"
        )
        lines.append(f"- grade: {candidate.grade}")
        lines.append(
            f"- active_rows={candidate.active_rows} "
            f"board_count={candidate.board_count} "
            f"described_share={candidate.described_share} "
            f"role_share={candidate.role_share}"
        )
        lines.append(
            f"- last_scrape_status={candidate.last_scrape_status} "
            f"consecutive_failures={candidate.consecutive_failures}"
        )
        lines.append("- sample active job titles (the evidence):")
        for title in candidate.sample_titles:
            lines.append(f"  - {title}")
        lines.append("")

    lines += ["## Copy-paste: seed entries to review", ""]
    for candidate in candidates:
        marker = " (removes live board rows)" if candidate.removes_live_board_rows else ""
        lines.append(f"- {candidate.name}{marker}")
    lines.append("")
    return "\n".join(lines)


def run(
    output_json: Path,
    output_review: Path,
    grades: list[str],
    min_active: int,
    min_consecutive_failures: int,
    limit: Optional[int],
) -> list[DemotionCandidate]:
    factory = get_session_factory()
    try:
        with factory() as session:
            candidates = gather_candidates(session)
    finally:
        dispose_engine()

    kept = filter_candidates(candidates, grades, min_active, min_consecutive_failures)
    ranked = rank_candidates(kept)
    if limit is not None:
        ranked = ranked[:limit]

    write_json(output_json, ranked, grades, min_active, min_consecutive_failures, limit)
    output_review.write_text(render(ranked, grades, min_active, min_consecutive_failures))
    return ranked


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Propose verified companies whose scraped rows look demotable "
            "(nav furniture, undescribed, never-boarded, or failing scrapes). "
            "Read-only: never writes to the database or the seed file."
        )
    )
    parser.add_argument("--output-json", type=Path, default=Path("demotion_proposals.json"))
    parser.add_argument("--output-review", type=Path, default=Path("demotion_proposals.md"))
    parser.add_argument("--grades", type=str, default="furniture")
    parser.add_argument("--min-active", type=int, default=3)
    parser.add_argument("--min-consecutive-failures", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    grades = parse_grades(args.grades)
    candidates = run(
        args.output_json,
        args.output_review,
        grades,
        args.min_active,
        args.min_consecutive_failures,
        args.limit,
    )

    print(f"candidates: {len(candidates)}")
    for grade, count in grade_counts(candidates).items():
        print(f"{grade}: {count}")
    print(f"wrote {args.output_json}")
    print(f"wrote {args.output_review}")


if __name__ == "__main__":
    main()
