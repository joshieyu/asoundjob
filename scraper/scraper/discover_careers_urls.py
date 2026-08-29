from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests  # type: ignore[import-untyped]
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scraper.config import load_settings
from scraper.database import dispose_engine, init_db, session_scope
from scraper.models import Company, ScrapeLog
from scraper.scrapers.ats_discovery import discover
from scraper.scrapers.link_extraction import extract_jobs

CANDIDATE_PATHS: tuple[str, ...] = (
    "/careers",
    "/careers/",
    "/jobs",
    "/jobs/",
    "/about/careers",
    "/company/careers",
    "/karriere",
    "/pages/careers",
)

ATS_URL_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("greenhouse", "https://boards.greenhouse.io/{slug}"),
    ("lever", "https://jobs.lever.co/{slug}"),
    ("ashby", "https://jobs.ashbyhq.com/{slug}"),
    ("workable", "https://apply.workable.com/{slug}"),
    ("recruitee", "https://{slug}.recruitee.com"),
    ("bamboohr", "https://{slug}.bamboohr.com/careers"),
    ("smartrecruiters", "https://careers.smartrecruiters.com/{slug}"),
)

SUPPORTED_ATS = frozenset(
    {
        "greenhouse",
        "lever",
        "workable",
        "ashby",
        "smartrecruiters",
        "recruitee",
        "bamboohr",
        "workday",
        "apple",
        "pinpoint",
    }
)

STOREFRONT_MARKERS = (
    "cdn.shopify.com",
    "shopify.theme",
    "woocommerce",
    "bigcommerce",
    "magento",
    "add to cart",
    "add to basket",
)

LOGIN_MARKERS = (
    'type="password"',
    "sign in to your account",
    "account-login",
    "shopify-login",
    "forgot your password",
)

CAREERS_VOCAB = re.compile(
    r"career|careers|job|jobs|vacanc|opening|position|recruit|hiring|"
    r"stelle|karriere|emploi|empleo|vacature",
    re.IGNORECASE,
)

CAREERS_LINK_VOCAB = re.compile(
    r"career|job|vacanc|opening|position|recruit|hiring|join|"
    r"work-with-us|karriere|stelle|emploi|empleo|vacature",
    re.IGNORECASE,
)

ATS_HOST_HINTS: tuple[str, ...] = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "recruitee.com",
    "bamboohr.com",
    "smartrecruiters.com",
    "myworkdayjobs.com",
)

ANCHOR_RE = re.compile(
    r'<a\b[^>]{0,400}href=["\']([^"\']{1,400})["\'][^>]{0,200}>(.{0,120}?)</a>',
    re.IGNORECASE | re.DOTALL,
)

TAG_RE = re.compile(r"<[^>]{0,200}>")

SKIPPED_LINK_SCHEMES = frozenset({"mailto", "tel", "javascript"})

MAX_CANDIDATES = 24
MAX_SLUGS = 4
MIN_SLUG_LEN = 3
MAX_HARVESTED_LINKS = 6
MAX_EVALUATED_CANDIDATES = 14
SHORT_CIRCUIT_SCORE = 70
BLOCKED_STATUS_CODES = frozenset({401, 403, 429})
REPLACE_MARGIN = 20
MAX_RESPONSE_BYTES = 2_000_000
MAX_MENTION_CHECK_CHARS = 200_000
PROGRESS_EVERY = 25
REQUEST_TIMEOUT = 15.0

DOMAIN_ERROR_HINTS = (
    "nameresolutionerror",
    "name_not_resolved",
    "getaddrinfo",
    "sslerror",
    "certificateerror",
    "connectionerror",
    "connect timeout",
    "max retries exceeded",
    "failed to establish a new connection",
)


@dataclass
class CandidateResult:
    url: str
    status: Optional[int] = None
    error: Optional[str] = None
    ats_type: Optional[str] = None
    ats_slug: str = ""
    job_links: int = 0
    has_careers_vocab: bool = False
    mentions_company: bool = False
    is_storefront: bool = False
    is_login: bool = False
    html: str = ""
    final_url: str = ""


def score_candidate(c: CandidateResult) -> int:
    if c.error is not None or c.status != 200:
        return 0
    score = 0
    if c.ats_type in SUPPORTED_ATS:
        score += 60
    elif c.ats_type:
        score += 25
    score += min(c.job_links * 4, 40)
    if c.has_careers_vocab:
        score += 10
    if c.mentions_company:
        score += 15
    if c.is_storefront:
        score -= 30
    if c.is_login:
        score -= 40
    return max(score, 0)


def confidence(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def _alnum_lower(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _registrable_label(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) >= 2:
        return labels[-2]
    return labels[0] if labels else ""


def slug_candidates(name: str, careers_url: str, website_url: Optional[str]) -> list:
    candidates: list = []

    compact = _alnum_lower(name)
    if compact:
        candidates.append(compact)

    dashed = re.sub(r"[^a-z0-9\s-]", "", name.lower()).strip()
    dashed = re.sub(r"\s+", "-", dashed)
    if dashed:
        candidates.append(dashed)

    for url in (website_url, careers_url):
        if not url:
            continue
        label = _registrable_label(url)
        if label:
            candidates.append(label)

    deduped: list = []
    seen: set = set()
    for slug in candidates:
        if len(slug) < MIN_SLUG_LEN:
            continue
        if slug in seen:
            continue
        seen.add(slug)
        deduped.append(slug)
        if len(deduped) >= MAX_SLUGS:
            break
    return deduped


def _root_origin(url: str) -> Optional[str]:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


SUBDOMAIN_ATS_SUFFIXES: tuple[str, ...] = (
    ".recruitee.com",
    ".bamboohr.com",
    ".breezy.hr",
    ".teamtailor.com",
)

PATH_ATS_HOSTS: frozenset = frozenset(
    {
        "boards.greenhouse.io",
        "jobs.lever.co",
        "apply.workable.com",
        "jobs.ashbyhq.com",
        "careers.smartrecruiters.com",
    }
)


def _ats_identity_token(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    for suffix in SUBDOMAIN_ATS_SUFFIXES:
        if host.endswith(suffix) and len(host) > len(suffix):
            return host[: -len(suffix)]
    if host in PATH_ATS_HOSTS:
        segments = [seg for seg in parsed.path.split("/") if seg]
        if segments:
            return segments[0]
    return ""


def redirect_lost_identity(requested_url: str, final_url: str) -> bool:
    token = _ats_identity_token(requested_url).lower()
    if not token:
        return False
    final_parsed = urlparse(final_url)
    final_host = (final_parsed.hostname or "").lower()
    final_path = (final_parsed.path or "").lower()
    return token not in final_host and token not in final_path


def careers_links_from_html(base_url: str, html: str) -> list:
    links: list = []
    seen: set = set()
    base_norm = base_url.rstrip("/")

    for match in ANCHOR_RE.finditer(html):
        href = match.group(1).strip()
        if not href:
            continue
        scheme = href.split(":", 1)[0].strip().lower()
        if scheme in SKIPPED_LINK_SCHEMES:
            continue

        label = TAG_RE.sub("", match.group(2)).strip()
        href_lower = href.lower()
        matches_vocab = bool(
            CAREERS_LINK_VOCAB.search(label) or CAREERS_LINK_VOCAB.search(href)
        )
        matches_ats = any(hint in href_lower for hint in ATS_HOST_HINTS)
        if not (matches_vocab or matches_ats):
            continue

        resolved = urljoin(base_url, href)
        if resolved.rstrip("/") == base_norm:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        links.append(resolved)
        if len(links) >= MAX_HARVESTED_LINKS:
            break

    return links


def build_candidates(
    name: str,
    careers_url: Optional[str],
    website_url: Optional[str],
    existing_ats: Optional[str],
    root_links: Optional[list] = None,
) -> list:
    ordered: list = []

    if careers_url:
        ordered.append(careers_url)

    if root_links:
        ordered.extend(root_links)

    slugs = slug_candidates(name, careers_url or "", website_url)
    for slug in slugs:
        for _ats_name, template in ATS_URL_TEMPLATES:
            ordered.append(template.format(slug=slug))

    root = _root_origin(careers_url or "") or _root_origin(website_url or "")
    if root:
        for path in CANDIDATE_PATHS:
            ordered.append(urljoin(root + "/", path.lstrip("/")))

    deduped: list = []
    seen: set = set()
    for url in ordered:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
        if len(deduped) >= MAX_CANDIDATES:
            break
    return deduped


def is_storefront(html_lower: str) -> bool:
    return any(marker in html_lower for marker in STOREFRONT_MARKERS)


def is_login(html_lower: str) -> bool:
    return any(marker in html_lower for marker in LOGIN_MARKERS)


def has_careers_vocab(html_lower: str) -> bool:
    return bool(CAREERS_VOCAB.search(html_lower))


_THREAD_LOCAL = threading.local()


def _session(user_agent: str) -> requests.Session:
    session = getattr(_THREAD_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        _THREAD_LOCAL.session = session
    return session


def evaluate_candidate(url: str, company_name: str, settings_ua: str) -> CandidateResult:
    result = CandidateResult(url=url)
    try:
        response = _session(settings_ua).get(
            url, timeout=REQUEST_TIMEOUT, allow_redirects=True
        )
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        return result

    result.status = response.status_code
    result.final_url = response.url
    if response.status_code != 200:
        return result

    if redirect_lost_identity(url, response.url):
        result.error = "redirect_lost_identity"
        return result

    content = response.content[:MAX_RESPONSE_BYTES]
    html = content.decode(response.encoding or "utf-8", errors="replace")
    html_lower = html.lower()
    result.html = html

    discoveries = discover(html)
    supported = next((d for d in discoveries if d[0] in SUPPORTED_ATS), None)
    chosen = supported or (discoveries[0] if discoveries else None)
    if chosen is not None:
        result.ats_type, result.ats_slug = chosen

    try:
        result.job_links = len(extract_jobs(html, url))
    except Exception:
        result.job_links = 0

    result.has_careers_vocab = has_careers_vocab(html_lower)
    result.is_storefront = is_storefront(html_lower)
    result.is_login = is_login(html_lower)

    company_key = _alnum_lower(company_name)
    if company_key:
        haystack = _alnum_lower(html[:MAX_MENTION_CHECK_CHARS])
        result.mentions_company = company_key in haystack

    return result


def _is_domain_dead_error(error: str) -> bool:
    lowered = error.lower()
    return any(hint in lowered for hint in DOMAIN_ERROR_HINTS)


def evaluate_company(
    row: tuple,
    settings_ua: str,
) -> dict:
    company_id, name, careers_url, website_url, verified, ats_type = row

    root = _root_origin(careers_url or "") or _root_origin(website_url or "")
    root_links: list = []
    root_blocked = False
    if root:
        root_probe = evaluate_candidate(root, name, settings_ua)
        if root_probe.error is not None and _is_domain_dead_error(root_probe.error):
            return {
                "company_id": company_id,
                "company": name,
                "verified": bool(verified),
                "current_url": careers_url,
                "best_url": None,
                "best_score": 0,
                "confidence": "none",
                "outcome": "domain_dead",
                "evidence": root_probe.error or "domain unreachable",
                "candidates": [],
                "reason": "domain_dead",
            }
        if root_probe.status in BLOCKED_STATUS_CODES:
            root_blocked = True
        elif root_probe.status == 200 and root_probe.html:
            root_links = careers_links_from_html(root, root_probe.html)

    candidates = build_candidates(name, careers_url, website_url, ats_type, root_links)

    tried: list = []
    best: Optional[CandidateResult] = None
    best_score = -1

    for url in candidates[:MAX_EVALUATED_CANDIDATES]:
        candidate = evaluate_candidate(url, name, settings_ua)
        score = score_candidate(candidate)
        tried.append(
            {
                "url": candidate.url,
                "score": score,
                "status": candidate.status,
                "error": candidate.error,
                "ats_type": candidate.ats_type,
                "ats_slug": candidate.ats_slug,
                "job_links": candidate.job_links,
            }
        )
        if score > best_score:
            best = candidate
            best_score = score
        if score >= SHORT_CIRCUIT_SCORE:
            break

    if best is None or best_score <= 0:
        best_blocked = best is not None and best.status in BLOCKED_STATUS_CODES
        if root_blocked or best_blocked:
            reason = "blocked"
        elif not root_links:
            reason = "no_careers_link"
        else:
            reason = "candidates_failed"
        return {
            "company_id": company_id,
            "company": name,
            "verified": bool(verified),
            "current_url": careers_url,
            "best_url": None,
            "best_score": 0,
            "confidence": "none",
            "outcome": "no_candidate",
            "evidence": "no candidate scored above zero",
            "candidates": tried,
            "reason": reason,
        }

    evidence_parts: list = []
    if best.ats_type:
        if best.ats_type in SUPPORTED_ATS:
            label = best.ats_type
        else:
            label = f"{best.ats_type} (unsupported)"
        evidence_parts.append(f"{label} embed")
    if best.job_links:
        evidence_parts.append(f"{best.job_links} job links")
    if best.is_storefront:
        evidence_parts.append("storefront markers")
    if best.is_login:
        evidence_parts.append("login page markers")
    if not evidence_parts and best.has_careers_vocab:
        evidence_parts.append("careers vocabulary")
    evidence = ", ".join(evidence_parts) if evidence_parts else "matched, no strong signal"

    outcome: str
    if careers_url and best.url == careers_url:
        outcome = "keep_current"
    elif careers_url and careers_url in {t["url"] for t in tried}:
        current_tried = next(t for t in tried if t["url"] == careers_url)
        current_score = current_tried["score"]
        if current_score == 0 and best_score > 0:
            outcome = "replace"
        elif best_score - current_score >= REPLACE_MARGIN:
            outcome = "replace"
        else:
            outcome = "keep_current"
    elif not careers_url:
        outcome = "replace"
    else:
        outcome = "replace"

    return {
        "company_id": company_id,
        "company": name,
        "verified": bool(verified),
        "current_url": careers_url,
        "best_url": best.url,
        "best_score": best_score,
        "confidence": confidence(best_score),
        "outcome": outcome,
        "evidence": evidence,
        "candidates": tried,
        "reason": "",
    }


def _fetch_unverified_rows(session: Session) -> list:
    query = select(
        Company.id,
        Company.name,
        Company.careers_url,
        Company.website_url,
        Company.verified,
        Company.ats_type,
    ).where(Company.verified.is_(False))
    return [tuple(row) for row in session.execute(query).all()]


def _fetch_failing_rows(session: Session) -> list:
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
            Company.website_url,
            Company.verified,
            Company.ats_type,
        )
        .join(ScrapeLog, ScrapeLog.company_id == Company.id)
        .join(
            latest_ids,
            (ScrapeLog.company_id == latest_ids.c.company_id)
            & (ScrapeLog.id == latest_ids.c.max_id),
        )
        .where(ScrapeLog.status == "failed", Company.verified.is_(True))
    )
    return [tuple(row) for row in session.execute(query).all()]


def _fetch_population(population: str) -> list:
    with session_scope() as session:
        if population == "unverified":
            rows = _fetch_unverified_rows(session)
        elif population == "failing":
            rows = _fetch_failing_rows(session)
        else:
            rows = _fetch_unverified_rows(session) + _fetch_failing_rows(session)
    by_id: dict = {}
    for row in rows:
        by_id[row[0]] = row
    return list(by_id.values())


def _write_review_markdown(results: list, output_review: str) -> None:
    outcome_counts: dict = {}
    reason_counts: dict = {}
    for r in results:
        outcome_counts[r["outcome"]] = outcome_counts.get(r["outcome"], 0) + 1
        reason = r.get("reason") or "(none)"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    by_confidence: dict = {"high": [], "medium": [], "low": []}
    inert: list = []
    for r in results:
        if r["outcome"] in ("domain_dead", "no_candidate"):
            inert.append(r)
        elif r["confidence"] in by_confidence:
            by_confidence[r["confidence"]].append(r)

    lines: list = []
    lines.append("# Careers URL discovery proposals")
    lines.append("")
    lines.append(
        "Approved lines must be applied by hand to data/audio_companies_final.json "
        "— this tool never writes that file."
    )
    lines.append("")
    lines.append("Outcome counts:")
    for outcome, count in sorted(outcome_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"- {outcome}: {count}")
    lines.append("")
    lines.append("Reason breakdown (why nothing was found):")
    for reason, count in sorted(reason_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"- {reason}: {count}")
    lines.append("")

    for level in ("high", "medium", "low"):
        entries = by_confidence[level]
        lines.append(f"## {level} confidence ({len(entries)})")
        lines.append("")
        for r in entries:
            lines.append(
                f"- [ ] **{r['company']}** — `{r['current_url']}` -> "
                f"`{r['best_url']}`  ({r['evidence']})"
            )
        lines.append("")

    lines.append("## Domain dead or no candidate found")
    lines.append("")
    for r in inert:
        lines.append(f"- {r['company']}")

    with open(output_review, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def run(
    population: str,
    limit: Optional[int],
    concurrency: int,
    output_json: str,
    output_review: str,
) -> None:
    settings = load_settings()
    init_db()

    try:
        rows = _fetch_population(population)
        if limit is not None:
            rows = rows[:limit]

        results: list = []
        completed = 0
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(evaluate_company, row, settings.user_agent): row
                for row in rows
            }
            for future in as_completed(futures):
                results.append(future.result())
                completed += 1
                if completed % PROGRESS_EVERY == 0:
                    print(f"evaluated {completed}/{len(rows)}", file=sys.stderr)

        results.sort(key=lambda r: r["company_id"])

        with open(output_json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)

        _write_review_markdown(results, output_review)

        outcome_counts: dict = {}
        reason_counts: dict = {}
        for r in results:
            outcome_counts[r["outcome"]] = outcome_counts.get(r["outcome"], 0) + 1
            reason = r.get("reason") or "(none)"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        print(f"\n{len(results)} companies evaluated\n")
        print(f"{'outcome':<20}{'count':>7}")
        for outcome, count in sorted(outcome_counts.items(), key=lambda kv: -kv[1]):
            print(f"{outcome:<20}{count:>7}")
        print(f"\n{'reason':<20}{'count':>7}")
        for reason, count in sorted(reason_counts.items(), key=lambda kv: -kv[1]):
            print(f"{reason:<20}{count:>7}")
    finally:
        dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Propose corrected careers URLs for review"
    )
    parser.add_argument(
        "--population",
        choices=("unverified", "failing", "both"),
        default="both",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--output-json", type=str, default="careers_url_proposals.json")
    parser.add_argument("--output-review", type=str, default="careers_url_proposals.md")
    args = parser.parse_args()
    run(
        args.population,
        args.limit,
        args.concurrency,
        args.output_json,
        args.output_review,
    )


if __name__ == "__main__":
    main()
