from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from sqlalchemy import select

from scraper.database import get_session_factory
from scraper.models import Company

INVITATION_PATTERNS = (
    r"send us your (?:resume|cv)",
    r"send your (?:resume|cv)",
    r"spontaneous application",
    r"open application",
    r"unsolicited application",
    r"speculative application",
    r"initiativbewerbung",
    r"candidature spontan\w{0,4}",
    r"we(?:'re| are) always looking for",
    r"always on the lookout",
    r"don'?t see (?:a|the) (?:right )?(?:role|position|job)",
)

INVITATION_RE = re.compile("|".join(INVITATION_PATTERNS), re.IGNORECASE)

NO_OPENINGS_RE = re.compile(
    r"no open positions|no current openings|no vacancies|no job openings|"
    r"there are currently no|no positions available|keine offenen stellen",
    re.IGNORECASE,
)

BLOCKED_RE = re.compile(
    r"you have been blocked|cloudflare ray id|please enable cookies|"
    r"verifying you are human|captcha",
    re.IGNORECASE,
)

MAX_CONTEXT = 160
STRIP_TAGS = ("script", "style", "noscript")


@dataclass
class Proposal:
    company_id: int
    company: str
    url: str
    marker: str
    context: str
    also_says_no_openings: bool


def page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(STRIP_TAGS):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True))


def find_invitation(text: str) -> Optional[tuple[str, str]]:
    match = INVITATION_RE.search(text)
    if match is None:
        return None
    start = max(0, match.start() - MAX_CONTEXT // 2)
    return match.group(0), text[start : match.end() + MAX_CONTEXT // 2].strip()


def inspect(company_id: int, company: str, url: str, html: str) -> Optional[Proposal]:
    if not html:
        return None
    text = page_text(html)
    if BLOCKED_RE.search(text):
        return None
    found = find_invitation(text)
    if found is None:
        return None
    marker, context = found
    return Proposal(
        company_id=company_id,
        company=company,
        url=url,
        marker=marker,
        context=context,
        also_says_no_openings=bool(NO_OPENINGS_RE.search(text)),
    )


def load_flags() -> dict[int, bool]:
    factory = get_session_factory()
    with factory() as session:
        rows = session.execute(
            select(Company.id, Company.open_application)
        ).all()
    return {row[0]: bool(row[1]) for row in rows}


def scan_cache(cache_dir: Path) -> list[Proposal]:
    proposals: list[Proposal] = []
    for path in sorted(cache_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        proposal = inspect(
            int(payload.get("company_id") or 0),
            str(payload.get("company_name") or path.stem),
            str(payload.get("url") or ""),
            payload.get("html") or "",
        )
        if proposal is not None:
            proposals.append(proposal)
    return proposals


def render(proposals: list[Proposal], flagged: dict[int, bool]) -> str:
    new = [p for p in proposals if not flagged.get(p.company_id)]
    already = [p for p in proposals if flagged.get(p.company_id)]
    lines = [
        "# Open-application proposals",
        "",
        "Read-only. Nothing here is written to the database or the seed file.",
        "",
        "A match means the page invites speculative applications in its own",
        "words. Confirm each one by opening the URL before setting",
        '`"open_application": true` in data/audio_companies_final.json.',
        "",
        "A page that only says it has no openings is NOT an invitation, and is",
        "reported separately below so it is not mistaken for one.",
        "",
        f"- candidates found: {len(proposals)}",
        f"- not yet flagged in the seed: {len(new)}",
        f"- already flagged: {len(already)}",
        "",
    ]
    clean = [p for p in new if not p.also_says_no_openings]
    mixed = [p for p in new if p.also_says_no_openings]

    lines += ["## Candidates", ""]
    for p in clean:
        lines += [
            f"### {p.company}",
            f"- url: {p.url}",
            f"- matched: `{p.marker}`",
            f"- context: {p.context}",
            "",
        ]
    if mixed:
        lines += [
            "## Also says it has no openings — read these carefully",
            "",
            "The invitation may be boilerplate sitting beside a real 'nothing",
            "open right now' message. Only flag one if the invitation stands"
            " on its own.",
            "",
        ]
        for p in mixed:
            lines += [
                f"### {p.company}",
                f"- url: {p.url}",
                f"- matched: `{p.marker}`",
                f"- context: {p.context}",
                "",
            ]
    if already:
        lines += ["## Already flagged in the seed", ""]
        lines += [f"- {p.company} — {p.url}" for p in already]
        lines += [""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Propose companies that invite speculative applications. Read-only. "
            "Consumes the HTML cache written by "
            "`python -m scraper.diagnose_failures --html-cache DIR`."
        )
    )
    parser.add_argument("--from-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("open_application_proposals.md"))
    args = parser.parse_args()

    if not args.from_cache.is_dir():
        raise SystemExit(f"not a directory: {args.from_cache}")

    proposals = scan_cache(args.from_cache)
    flagged = load_flags()
    args.output.write_text(render(proposals, flagged))
    print(f"scanned {args.from_cache}")
    print(f"candidates: {len(proposals)}")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
