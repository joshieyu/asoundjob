from __future__ import annotations

import argparse
import difflib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select

from scraper.company_loader import read_companies_file
from scraper.config import load_settings
from scraper.database import get_session_factory
from scraper.models import Company
from scraper.normalizer import score_relevance

SHORT_NAME_MAX_LEN = 4
FUZZY_MATCH_THRESHOLD = 0.92
MAX_SAMPLE_TITLES = 5
MAX_SAMPLE_LOCATIONS = 3

LEGAL_SUFFIX_WORDS: tuple[str, ...] = (
    "gmbh",
    "inc",
    "ltd",
    "limited",
    "llc",
    "corp",
    "corporation",
    "sa",
    "bv",
    "nv",
    "ab",
    "oy",
    "sas",
    "srl",
    "spa",
    "plc",
    "pty",
    "kk",
    "holdings",
    "group",
    "technologies",
    "technology",
)

LEGAL_SUFFIX_PHRASES: tuple[str, ...] = ("co kg", "co ltd", "a s")

_SUFFIX_TERMS = sorted(LEGAL_SUFFIX_PHRASES + LEGAL_SUFFIX_WORDS, key=len, reverse=True)
_SUFFIX_ALTERNATION = "|".join(re.escape(term) for term in _SUFFIX_TERMS)
LEGAL_SUFFIX_RE = re.compile(rf"\b(?:{_SUFFIX_ALTERNATION})\b")

WHITESPACE_RE = re.compile(r"\s{1,20}")
PUNCTUATION_RE = re.compile(r"[^\w\s]{1,20}")


def normalize_company_name(name: str) -> str:
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("&", " and ")
    text = PUNCTUATION_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    text = LEGAL_SUFFIX_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    tokens = [t for t in text.split(" ") if t and t != "and"]
    return " ".join(tokens)


def _tokens(normalized: str) -> frozenset:
    return frozenset(t for t in normalized.split(" ") if t and t != "and")


def build_known_index(companies: list[dict[str, Any]]) -> dict[str, str]:
    index: dict[str, str] = {}
    for entry in companies:
        raw_name = str(entry.get("name") or "").strip()
        if not raw_name:
            continue
        normalized = normalize_company_name(raw_name)
        if normalized and normalized not in index:
            index[normalized] = raw_name
    return index


RANK_SUBSET = 2
RANK_FIRST_TOKEN = 1
RANK_FUZZY = 0


def match_known_company(normalized_name: str, known_index: dict[str, str]) -> Optional[str]:
    if not normalized_name:
        return None
    if normalized_name in known_index:
        return known_index[normalized_name]
    if len(normalized_name) <= SHORT_NAME_MAX_LEN:
        return None
    incoming_tokens = _tokens(normalized_name)
    if not incoming_tokens:
        return None
    incoming_first_token = normalized_name.split(" ", 1)[0]

    best_display: Optional[str] = None
    best_rank = -1
    best_ratio = -1.0

    for known_normalized, display_name in known_index.items():
        if len(known_normalized) <= SHORT_NAME_MAX_LEN:
            continue
        known_tokens = _tokens(known_normalized)
        if not known_tokens:
            continue

        if (
            len(known_tokens) >= 2
            and len(incoming_tokens) >= 2
            and (known_tokens <= incoming_tokens or incoming_tokens <= known_tokens)
        ):
            rank, ratio = RANK_SUBSET, 1.0
        elif len(known_tokens) == 1 and known_normalized == incoming_first_token:
            rank, ratio = RANK_FIRST_TOKEN, 1.0
        else:
            ratio = difflib.SequenceMatcher(None, normalized_name, known_normalized).ratio()
            if ratio < FUZZY_MATCH_THRESHOLD:
                continue
            rank = RANK_FUZZY

        is_better = rank > best_rank or (
            rank == best_rank
            and (
                ratio > best_ratio
                or (
                    ratio == best_ratio
                    and (best_display is None or display_name < best_display)
                )
            )
        )
        if is_better:
            best_rank = rank
            best_ratio = ratio
            best_display = display_name

    return best_display


def filter_audio_relevant(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relevant: list[dict[str, Any]] = []
    for job in jobs:
        title = str(job.get("title") or "")
        description = job.get("description")
        _, is_audio_related = score_relevance(title, description, [], audio_scope="all")
        if is_audio_related:
            relevant.append(job)
    return relevant


@dataclass
class ClassifiedJobs:
    matched_known: int
    unmatched: list[dict[str, Any]]


def classify_against_known(
    jobs: list[dict[str, Any]], known_index: dict[str, str]
) -> ClassifiedJobs:
    matched_known = 0
    unmatched: list[dict[str, Any]] = []
    cache: dict[str, Optional[str]] = {}
    for job in jobs:
        raw_name = str(job.get("company_name") or "").strip()
        normalized = normalize_company_name(raw_name)
        if normalized not in cache:
            cache[normalized] = match_known_company(normalized, known_index)
        if cache[normalized] is not None:
            matched_known += 1
        else:
            unmatched.append(job)
    return ClassifiedJobs(matched_known=matched_known, unmatched=unmatched)


@dataclass
class CandidateCompany:
    name: str
    normalized_name: str
    hit_count: int
    search_terms: list[str]
    sites: list[str]
    sample_titles: list[str]
    sample_locations: list[str]
    company_url: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "normalized_name": self.normalized_name,
            "hit_count": self.hit_count,
            "search_terms": self.search_terms,
            "sites": self.sites,
            "sample_titles": self.sample_titles,
            "sample_locations": self.sample_locations,
            "company_url": self.company_url,
        }


def _first_n_unique(values: list[str], limit: int) -> list[str]:
    seen: set = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def aggregate_candidates(jobs: list[dict[str, Any]]) -> list[CandidateCompany]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for job in jobs:
        raw_name = str(job.get("company_name") or "").strip()
        if not raw_name:
            continue
        normalized = normalize_company_name(raw_name)
        if not normalized:
            continue
        groups.setdefault(normalized, []).append(job)

    candidates: list[CandidateCompany] = []
    for normalized, group_jobs in groups.items():
        name_counts = Counter(
            str(job.get("company_name") or "").strip() for job in group_jobs
        )
        display_name = name_counts.most_common(1)[0][0]
        search_terms = sorted(
            {str(job.get("search_term") or "") for job in group_jobs if job.get("search_term")}
        )
        sites = sorted({str(job.get("site") or "") for job in group_jobs if job.get("site")})
        sample_titles = _first_n_unique(
            [str(job.get("title") or "") for job in group_jobs], MAX_SAMPLE_TITLES
        )
        sample_locations = _first_n_unique(
            [str(job.get("location") or "") for job in group_jobs], MAX_SAMPLE_LOCATIONS
        )
        company_url = next(
            (
                str(job.get("company_url")).strip()
                for job in group_jobs
                if job.get("company_url")
            ),
            None,
        )
        candidates.append(
            CandidateCompany(
                name=display_name,
                normalized_name=normalized,
                hit_count=len(group_jobs),
                search_terms=search_terms,
                sites=sites,
                sample_titles=sample_titles,
                sample_locations=sample_locations,
                company_url=company_url,
            )
        )
    return candidates


def rank_candidates(
    candidates: list[CandidateCompany], min_hits: int, limit: Optional[int]
) -> list[CandidateCompany]:
    filtered = [c for c in candidates if c.hit_count >= min_hits]
    ranked = sorted(
        filtered,
        key=lambda c: (-c.hit_count, -len(c.search_terms), c.name.lower()),
    )
    if limit is not None:
        ranked = ranked[:limit]
    return ranked


@dataclass
class ProposalRun:
    jobs_in: int
    audio_relevant: int
    matched_known: int
    candidates: list[CandidateCompany]


def build_proposals(
    jobs: list[dict[str, Any]],
    companies: list[dict[str, Any]],
    min_hits: int = 1,
    limit: Optional[int] = None,
) -> ProposalRun:
    known_index = build_known_index(companies)
    relevant = filter_audio_relevant(jobs)
    classified = classify_against_known(relevant, known_index)
    aggregated = aggregate_candidates(classified.unmatched)
    ranked = rank_candidates(aggregated, min_hits, limit)
    return ProposalRun(
        jobs_in=len(jobs),
        audio_relevant=len(relevant),
        matched_known=classified.matched_known,
        candidates=ranked,
    )


def render_review_markdown(
    generated_at: str,
    jobs_in: int,
    audio_relevant: int,
    matched_known: int,
    candidates: list[CandidateCompany],
    db_read_ok: bool,
) -> str:
    lines: list[str] = []
    lines.append("# Company proposals")
    lines.append("")
    lines.append(f"Generated: {generated_at}")
    lines.append("")
    lines.append(
        "Read-only. This tool wrote nothing to the database or to "
        "data/audio_companies_final.json. Approved companies must be added "
        "by hand."
    )
    lines.append("")
    if not db_read_ok:
        lines.append(
            "The database could not be read; known-company matching used "
            "the seed file only."
        )
        lines.append("")
    lines.append("Counts:")
    lines.append(f"- jobs in: {jobs_in}")
    lines.append(f"- audio relevant: {audio_relevant}")
    lines.append(f"- matched known companies: {matched_known}")
    lines.append(f"- candidates: {len(candidates)}")
    lines.append("")
    lines.append(f"## Candidates ({len(candidates)})")
    lines.append("")
    for candidate in candidates:
        lines.append(f"### {candidate.name}")
        lines.append(f"- hits: {candidate.hit_count}")
        lines.append(f"- search terms: {', '.join(candidate.search_terms) or '(none)'}")
        lines.append(f"- sites: {', '.join(candidate.sites) or '(none)'}")
        if candidate.company_url:
            lines.append(f"- company url: {candidate.company_url}")
        if candidate.sample_locations:
            lines.append(f"- sample locations: {', '.join(candidate.sample_locations)}")
        lines.append("- sample titles:")
        for title in candidate.sample_titles:
            lines.append(f"  - {title}")
        lines.append("")
    return "\n".join(lines) + "\n"


def read_db_company_names() -> tuple[list[str], bool]:
    try:
        factory = get_session_factory()
        with factory() as session:
            rows = session.execute(select(Company.name)).all()
        return [str(row[0]) for row in rows], True
    except Exception:
        return [], False


def write_json_output(
    output_path: str,
    generated_at: str,
    run: ProposalRun,
) -> None:
    payload = {
        "generated_at": generated_at,
        "counts": {
            "jobs_in": run.jobs_in,
            "audio_relevant": run.audio_relevant,
            "matched_known": run.matched_known,
            "candidates": len(run.candidates),
        },
        "candidates": [candidate.to_dict() for candidate in run.candidates],
    }
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def write_review_output(
    output_path: str,
    generated_at: str,
    run: ProposalRun,
    db_read_ok: bool,
) -> None:
    text = render_review_markdown(
        generated_at, run.jobs_in, run.audio_relevant, run.matched_known, run.candidates, db_read_ok
    )
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Propose new companies found in jobspy-fetched job listings. Read-only."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--companies-file", type=Path, default=None)
    parser.add_argument("--output-json", type=str, default="company_proposals.json")
    parser.add_argument("--output-review", type=str, default="company_proposals.md")
    parser.add_argument("--min-hits", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    settings = load_settings()
    companies_path = args.companies_file or settings.data_dir / "audio_companies_final.json"
    seed_companies = read_companies_file(companies_path)
    db_names, db_read_ok = read_db_company_names()

    with args.input.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else payload

    combined_companies = list(seed_companies) + [{"name": name} for name in db_names]
    run = build_proposals(jobs, combined_companies, args.min_hits, args.limit)

    generated_at = datetime.now(timezone.utc).isoformat()
    write_json_output(args.output_json, generated_at, run)
    write_review_output(args.output_review, generated_at, run, db_read_ok)

    print(f"jobs_in: {run.jobs_in}")
    print(f"audio_relevant: {run.audio_relevant}")
    print(f"matched_known: {run.matched_known}")
    print(f"candidates: {len(run.candidates)}")
    print(f"wrote {args.output_json}")
    print(f"wrote {args.output_review}")


if __name__ == "__main__":
    main()
