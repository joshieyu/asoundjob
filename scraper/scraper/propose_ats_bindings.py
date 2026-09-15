from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scraper.config import Settings, load_settings
from scraper.database import dispose_engine, get_session_factory
from scraper.models import Company, Job
from scraper.scrapers.pipeline import ScrapePipeline

IGNORED_SLUG_TOKENS = frozenset(
    {"www", "com", "careers", "jobs", "job", "external", "staff"}
)

WORKDAY_DATACENTER_RE = re.compile(r"^wd\d{1,3}$")
SLUG_SPLIT_RE = re.compile(r"[^0-9a-z]{1,64}")
NAME_TOKEN_RE = re.compile(r"[0-9a-z]{1,64}")

MIN_SHARED_TOKEN_LEN = 4
MIN_PREFIX_OVERLAP = 5
OPAQUE_SLUG_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
MAX_HTTP_CONCURRENCY = 50

PRIORITY_PROBLEMS = frozenset({"slug_unrelated_to_company", "duplicate_binding"})

PROBLEM_GUIDANCE = {
    "empty_slug": (
        "ats_slug is blank, so the stored ats_type can never resolve to a "
        "tenant. Clear ats_type/ats_slug or fill in the real slug."
    ),
    "unknown_ats": (
        "ats_type does not match any scraper the pipeline knows how to run, "
        "so this binding can never succeed. Clear it."
    ),
    "duplicate_binding": (
        "another company holds the identical (ats_type, ats_slug) pair; at "
        "most one of them can be right. Open both careers pages and clear "
        "the binding on whichever company does not actually run this "
        "ATS tenant."
    ),
    "slug_unrelated_to_company": (
        "ats_slug shares no meaningful word with this company's name or "
        "domain. Open careers_url and confirm the ATS tenant really belongs "
        "to this company before trusting the jobs it has produced."
    ),
    "scrape_fails": (
        "running the stored binding failed or returned zero jobs. Re-check "
        "the slug against the live careers page or clear the binding."
    ),
}


@dataclass
class AtsBindingFinding:
    company_id: int
    name: str
    slug: str
    careers_url: Optional[str]
    ats_type: Optional[str]
    ats_slug: Optional[str]
    active_job_count: int
    problems: list[str] = field(default_factory=list)


def _is_empty_slug(ats_slug: Optional[str]) -> bool:
    return ats_slug is None or not ats_slug.strip()


def _hostname(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    candidate = url.strip()
    if not candidate:
        return None
    if "//" not in candidate:
        candidate = "//" + candidate
    host = urlparse(candidate).hostname
    if not host:
        return None
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _registrable_label(host: str) -> str:
    labels = host.split(".")
    if len(labels) >= 2:
        return labels[-2]
    return labels[0]


def _company_tokens(
    name: str, careers_url: Optional[str], website_url: Optional[str]
) -> set[str]:
    tokens: set[str] = set()
    for url in (careers_url, website_url):
        host = _hostname(url)
        if not host:
            continue
        for label in host.split("."):
            if label and label not in IGNORED_SLUG_TOKENS:
                tokens.add(label)
    name_tokens = NAME_TOKEN_RE.findall(name.lower())
    tokens.update(name_tokens)
    if len(name_tokens) > 1:
        tokens.add("".join(name_tokens))
    return {tok for tok in tokens if tok}


def _forms_related(company_token: str, slug_token: str) -> bool:
    if company_token == slug_token:
        return True
    shorter, longer = sorted((company_token, slug_token), key=len)
    if len(shorter) >= MIN_SHARED_TOKEN_LEN and shorter in longer:
        return True
    overlap = 0
    for left, right in zip(company_token, slug_token):
        if left != right:
            break
        overlap += 1
    return overlap >= MIN_PREFIX_OVERLAP


def slug_matches_company(company_tokens: set[str], slug_tokens: list[str]) -> bool:
    return any(
        _forms_related(company_token, slug_token)
        for company_token in company_tokens
        for slug_token in slug_tokens
    )


def _is_noise_slug_token(token: str) -> bool:
    if token in IGNORED_SLUG_TOKENS:
        return True
    return bool(WORKDAY_DATACENTER_RE.match(token))


def _significant_slug_tokens(ats_slug: str) -> list[str]:
    raw_tokens = [tok for tok in SLUG_SPLIT_RE.split(ats_slug.lower()) if tok]
    return [tok for tok in raw_tokens if not _is_noise_slug_token(tok)]


def _problem_kind(problem: str) -> str:
    return problem.split(":", 1)[0]


def detect_problems(
    company: Company,
    known_ats_types: frozenset,
    duplicate_groups: dict[tuple[str, str], list[Company]],
) -> list[str]:
    problems: list[str] = []
    empty_slug = _is_empty_slug(company.ats_slug)
    if empty_slug:
        problems.append("empty_slug")

    if company.ats_type not in known_ats_types:
        problems.append("unknown_ats")

    if not empty_slug:
        ats_slug = (company.ats_slug or "").strip()
        key = (company.ats_type or "", ats_slug)
        others = [c for c in duplicate_groups.get(key, []) if c.id != company.id]
        if others:
            names = ", ".join(sorted(o.name for o in others))
            problems.append(f"duplicate_binding: shared with {names}")

        if not OPAQUE_SLUG_RE.match(ats_slug.lower()):
            company_tokens = _company_tokens(
                company.name, company.careers_url, company.website_url
            )
            significant_slug_tokens = _significant_slug_tokens(ats_slug)
            if not slug_matches_company(company_tokens, significant_slug_tokens):
                problems.append("slug_unrelated_to_company")

    return problems


def _load_bound_companies(session: Session) -> list[Company]:
    return list(
        session.execute(
            select(Company).where(Company.ats_type.isnot(None))
        )
        .scalars()
        .all()
    )


def _active_job_counts(session: Session) -> dict[int, int]:
    rows = session.execute(
        select(Job.company_id, func.count(Job.id))
        .where(Job.is_active.is_(True))
        .group_by(Job.company_id)
    ).all()
    return {company_id: count for company_id, count in rows if company_id is not None}


def build_findings(
    companies: list[Company],
    job_counts: dict[int, int],
    known_ats_types: frozenset,
) -> list[AtsBindingFinding]:
    duplicate_groups: dict[tuple[str, str], list[Company]] = {}
    for company in companies:
        if _is_empty_slug(company.ats_slug):
            continue
        key = (company.ats_type or "", (company.ats_slug or "").strip())
        duplicate_groups.setdefault(key, []).append(company)

    findings: list[AtsBindingFinding] = []
    for company in companies:
        problems = detect_problems(company, known_ats_types, duplicate_groups)
        findings.append(
            AtsBindingFinding(
                company_id=company.id,
                name=company.name,
                slug=company.slug,
                careers_url=company.careers_url,
                ats_type=company.ats_type,
                ats_slug=company.ats_slug,
                active_job_count=job_counts.get(company.id, 0),
                problems=problems,
            )
        )
    return findings


def gather_findings(session: Session, known_ats_types: frozenset) -> list[AtsBindingFinding]:
    companies = _load_bound_companies(session)
    job_counts = _active_job_counts(session)
    return build_findings(companies, job_counts, known_ats_types)


def rank_findings(findings: list[AtsBindingFinding]) -> list[AtsBindingFinding]:
    def sort_key(finding: AtsBindingFinding) -> tuple[int, int, str]:
        kinds = {_problem_kind(p) for p in finding.problems}
        has_priority = any(kind in PRIORITY_PROBLEMS for kind in kinds)
        return (-len(finding.problems), 0 if has_priority else 1, finding.name.lower())

    return sorted(findings, key=sort_key)


def problem_counts(findings: list[AtsBindingFinding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        kinds = {_problem_kind(p) for p in finding.problems}
        for kind in kinds:
            counts[kind] = counts.get(kind, 0) + 1
    return counts


async def _verify_company(
    scraper: object,
    company: Company,
    settings: Settings,
    semaphore: asyncio.Semaphore,
) -> Optional[str]:
    probe = Company(
        id=company.id,
        name=company.name,
        slug=company.slug,
        category=company.category,
        careers_url=company.careers_url,
        website_url=company.website_url,
        verified=company.verified,
        source=company.source,
        scrape_method=company.scrape_method,
        audio_scope=company.audio_scope,
        ats_type=company.ats_type,
        ats_slug=company.ats_slug,
    )
    async with semaphore:
        try:
            result = await asyncio.wait_for(
                scraper.scrape(probe), timeout=settings.per_company_timeout  # type: ignore[attr-defined]
            )
        except asyncio.TimeoutError:
            return f"timeout after {settings.per_company_timeout:.0f}s"
        except Exception as exc:
            return f"{type(exc).__name__}: {exc}"
    if not result.success:
        return result.error or "scrape failed"
    if not result.jobs:
        return "scrape succeeded with zero jobs"
    return None


async def verify_findings(
    companies: list[Company],
    findings: list[AtsBindingFinding],
    pipeline: ScrapePipeline,
    settings: Settings,
) -> None:
    findings_by_id = {finding.company_id: finding for finding in findings}
    semaphore = asyncio.Semaphore(min(settings.http_concurrency, MAX_HTTP_CONCURRENCY))
    ats_map = pipeline._ats_map

    async def _run(company: Company) -> tuple[int, Optional[str]]:
        ats_type = company.ats_type or ""
        scraper = ats_map.get(ats_type)
        if scraper is None:
            return company.id, None
        detail = await _verify_company(scraper, company, settings, semaphore)
        return company.id, detail

    targets = [c for c in companies if (c.ats_type or "") in ats_map]
    if not targets:
        return
    results = await asyncio.gather(*(_run(c) for c in targets))
    for company_id, detail in results:
        if detail is None:
            continue
        finding = findings_by_id.get(company_id)
        if finding is not None:
            finding.problems.append(f"scrape_fails: {detail}")


def write_json(
    path: Path,
    findings: list[AtsBindingFinding],
    verify: bool,
    limit: Optional[int],
    counts: dict[str, int],
    total_bound: int,
    flagged_count: int,
) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verify": verify,
        "limit": limit,
        "total_bound_companies": total_bound,
        "flagged_companies": flagged_count,
        "counts_by_problem": counts,
        "findings": [asdict(finding) for finding in findings],
    }
    path.write_text(json.dumps(payload, indent=2))


def render(
    findings: list[AtsBindingFinding],
    verify: bool,
    limit: Optional[int],
    counts: dict[str, int],
    total_bound: int,
    flagged_count: int,
) -> str:
    lines = [
        "# ATS binding proposals",
        "",
        "Read-only. This tool wrote nothing to the database. Every problem "
        "below is evidence that a stored `ats_type`/`ats_slug` pair should "
        "be reviewed by hand — the fix is to correct or clear the binding "
        "directly in the database; this tool never does that itself.",
        "",
        f"Bound companies checked: {total_bound}. Flagged: {flagged_count}.",
        "Network verification: "
        + ("ON (--verify)" if verify else "off (pass --verify to actually run the scrapers)"),
    ]
    if limit is not None:
        lines.append(f"Output limited to the worst {limit} findings.")
    lines.append("")
    lines.append("## Counts by problem")
    lines.append("")
    if counts:
        for kind, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
            lines.append(f"- {kind}: {count}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Flagged companies")
    lines.append("")
    flagged = [finding for finding in findings if finding.problems]
    if not flagged:
        lines.append("None.")
        lines.append("")
    for finding in flagged:
        lines.append(f"### {finding.name}")
        lines.append(f"- company slug: {finding.slug}")
        lines.append(f"- careers_url: {finding.careers_url or '(none)'}")
        lines.append(
            f"- stored binding: ats_type={finding.ats_type!r} "
            f"ats_slug={finding.ats_slug!r}"
        )
        lines.append(f"- active job count: {finding.active_job_count}")
        lines.append("- problems:")
        for problem in finding.problems:
            guidance = PROBLEM_GUIDANCE.get(_problem_kind(problem), "")
            lines.append(f"  - **{problem}** — {guidance}")
        lines.append("")

    lines.append("## Copy-paste: bindings to review")
    lines.append("")
    for finding in flagged:
        lines.append(f"- {finding.name} ({finding.ats_type}/{finding.ats_slug})")
    lines.append("")
    return "\n".join(lines)


def run(
    output_json: Path,
    output_review: Path,
    verify: bool,
    limit: Optional[int],
) -> list[AtsBindingFinding]:
    settings = load_settings()
    pipeline = ScrapePipeline(settings)
    known_ats_types = frozenset(pipeline._ats_map.keys())

    factory = get_session_factory()
    try:
        with factory() as session:
            companies = _load_bound_companies(session)
            job_counts = _active_job_counts(session)
    finally:
        dispose_engine()

    findings = build_findings(companies, job_counts, known_ats_types)

    if verify:
        asyncio.run(verify_findings(companies, findings, pipeline, settings))

    ranked = rank_findings(findings)
    counts = problem_counts(ranked)
    flagged_count = len([finding for finding in ranked if finding.problems])
    output_findings = ranked[:limit] if limit is not None else ranked

    write_json(
        output_json, output_findings, verify, limit, counts, len(companies), flagged_count
    )
    output_review.write_text(
        render(output_findings, verify, limit, counts, len(companies), flagged_count)
    )
    return ranked


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit stored ats_type/ats_slug bindings for signs they are "
            "wrong: an empty slug, an ats_type the pipeline no longer knows "
            "how to run, two companies claiming the identical binding, a "
            "slug that shares nothing with the company's own identity, and "
            "with --verify, a stored binding whose scraper actually fails "
            "or returns zero jobs. Read-only: never writes to the database."
        )
    )
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--output-json", type=Path, default=Path("ats_binding_proposals.json")
    )
    parser.add_argument(
        "--output-review", type=Path, default=Path("ats_binding_proposals.md")
    )
    args = parser.parse_args(argv)

    ranked = run(args.output_json, args.output_review, args.verify, args.limit)

    flagged = [finding for finding in ranked if finding.problems]
    counts = problem_counts(ranked)
    print(f"bound companies checked: {len(ranked)}")
    print(f"flagged: {len(flagged)}")
    for kind, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        print(f"{kind}: {count}")
    print(f"wrote {args.output_json}")
    print(f"wrote {args.output_review}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
