from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scraper.config import load_settings

ATS_HOSTS = (
    "greenhouse.io", "lever.co", "workable.com", "ashbyhq.com", "smartrecruiters.com",
    "recruitee.com", "bamboohr.com", "myworkdayjobs.com", "workday.com", "icims.com",
    "taleo.net", "successfactors", "teamtailor.com", "personio", "jobvite.com",
    "pinpointhq.com", "adp.com", "oraclecloud.com", "paylocity.com", "breezy.hr",
    "jazzhr.com", "ultipro.com", "dayforcehcm.com", "eightfold.ai", "avature.net",
    "zenats.com", "applytojob.com", "paycomonline.net", "trakstar.com", "rippling.com",
    "phenompeople.com", "brassring.com", "silkroad", "careers-page.com", "join.com",
    "softgarden", "hrmdirect", "clearcompany.com", "paycor.com", "dayforce.com",
    "isolvedhire.com", "bullhorn", "myworkdaysite.com", "zohopublic", "recruitee",
    "jobs.gecareers", "eightfold", "hirehive", "workforcenow",
)

STOP = {
    "the", "and", "inc", "llc", "ltd", "gmbh", "corp", "corporation", "co", "company",
    "group", "technologies", "technology", "tech", "systems", "audio", "sound", "music",
    "labs", "lab", "studios", "studio", "international", "holdings", "sa", "ag", "kg",
    "bv", "srl", "spa", "plc", "limited", "of", "for", "by",
}

CAREERS_VOCAB = re.compile(
    r"career|job|vacan|recruit|join|hiring|hire|employment|opportunit|work-with|"
    r"workwith|work-for|working-at|life-at|people|talent|stellen|emploi|karriere|"
    r"lavora|trabaja|empleo|saiyo|recruitment",
    re.IGNORECASE,
)

HARD_BAD = re.compile(
    r"accessdenied|/error|404|page-not-found|buy-domain|domain_profile|"
    r"press-releases?|/newsroom|\.pdf$|/password\b|aspxerrorpath",
    re.IGNORECASE,
)

MAX_NAME_LEN = 32
MAX_URL_LEN = 105


@dataclass
class Finding:
    company: str
    verified: bool
    url: str


@dataclass
class AuditResult:
    bad_page: list[Finding] = field(default_factory=list)
    wrong_host_no_vocab: list[Finding] = field(default_factory=list)
    right_host_no_vocab: list[Finding] = field(default_factory=list)
    wrong_host_careers_shaped: list[Finding] = field(default_factory=list)


def name_tokens(name: str) -> list[str]:
    parts = re.split(r"[^a-z0-9]+", name.lower())
    return [p for p in parts if p and p not in STOP and len(p) > 2]


def host_of(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host.split(":")[0]


def is_ats_host(host: str) -> bool:
    return any(marker in host for marker in ATS_HOSTS)


def classify(rows: list[dict[str, Any]]) -> AuditResult:
    result = AuditResult()
    for row in rows:
        url = str(row.get("careers_url") or "").strip()
        if not url:
            continue
        parsed = urlparse(url)
        host = host_of(url)
        if not host or is_ats_host(host):
            continue
        flat = re.sub(r"[^a-z0-9]", "", host)
        tokens = name_tokens(str(row.get("name") or ""))
        name_hit = (
            any(token in flat or (len(token) > 5 and token[:5] in flat) for token in tokens)
            if tokens
            else True
        )
        path = (parsed.path or "") + ("?" + parsed.query if parsed.query else "")
        careers_hit = bool(CAREERS_VOCAB.search(path) or CAREERS_VOCAB.search(host))
        bad_page = bool(HARD_BAD.search(path))
        finding = Finding(
            company=str(row.get("name") or ""),
            verified=bool(row.get("verified")),
            url=url,
        )
        if bad_page:
            result.bad_page.append(finding)
        elif not name_hit and not careers_hit:
            result.wrong_host_no_vocab.append(finding)
        elif not name_hit:
            result.wrong_host_careers_shaped.append(finding)
        elif not careers_hit:
            result.right_host_no_vocab.append(finding)
    return result


def _section(title: str, findings: list[Finding]) -> list[str]:
    verified = sum(1 for f in findings if f.verified)
    lines = [f"## {title} — {len(findings)} ({verified} verified)", ""]
    ordered = sorted(findings, key=lambda f: (not f.verified, f.company))
    for f in ordered:
        flag = "V" if f.verified else "-"
        name = f.company[:MAX_NAME_LEN].ljust(MAX_NAME_LEN)
        lines.append(f"{flag}  {name} {f.url[:MAX_URL_LEN]}")
    lines.append("")
    return lines


def render(result: AuditResult) -> str:
    total = (
        len(result.bad_page)
        + len(result.wrong_host_no_vocab)
        + len(result.right_host_no_vocab)
    )
    b_verified = sum(1 for f in result.wrong_host_careers_shaped if f.verified)
    lines = [
        "# Seed careers-URL audit",
        "",
        "Read-only. This is a proposal list requiring human confirmation, not a",
        "list of confirmed problems. Nothing here is written to",
        "data/audio_companies_final.json or to the database. Classification is",
        "by URL shape alone — there is no network access, so this cannot see",
        "what the URL actually serves.",
        "",
        "Bucket A in particular contains legitimate parent-company URLs. A",
        "careers page hosted on a different domain than the company's own is a",
        "common and correct pattern — for example Soundtrap's careers URL",
        "points at lifeatspotify.com, which is correct because Soundtrap is",
        "owned by Spotify, but this heuristic flags it anyway because the host",
        "does not contain \"soundtrap\". Verify each bucket A entry before",
        "treating it as wrong.",
        "",
        f"- entries flagged: {total}",
        f"- D — error / for-sale / press release: {len(result.bad_page)}",
        f"- A — wrong host, no careers vocabulary: {len(result.wrong_host_no_vocab)}",
        f"- C — right host, no careers vocabulary: {len(result.right_host_no_vocab)}",
        "- B — wrong host, careers-shaped (likely parent company, not listed): "
        f"{len(result.wrong_host_careers_shaped)} ({b_verified} verified)",
        "",
    ]
    lines += _section(
        "D. the URL is an error page, a for-sale page, or a press release",
        result.bad_page,
    )
    lines += _section(
        "A. wrong host and no careers vocabulary anywhere in the URL",
        result.wrong_host_no_vocab,
    )
    lines += _section(
        "C. right host, but no careers vocabulary in the URL",
        result.right_host_no_vocab,
    )
    return "\n".join(lines)


def load_rows(seed_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(seed_path.read_text())
    return list(payload)


def main() -> None:
    settings = load_settings()
    parser = argparse.ArgumentParser(
        description=(
            "Bucket careers URLs in the seed by URL shape alone: error pages, "
            "for-sale pages, press releases, and URLs that look like they "
            "point at the wrong company. Read-only, no network calls."
        )
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=settings.data_dir / "audio_companies_final.json",
    )
    parser.add_argument("--output", type=Path, default=Path("seed_url_audit.md"))
    args = parser.parse_args()

    rows = load_rows(args.seed)
    result = classify(rows)
    args.output.write_text(render(result))

    print(f"D: {len(result.bad_page)}")
    print(f"A: {len(result.wrong_host_no_vocab)}")
    print(f"C: {len(result.right_host_no_vocab)}")
    print(f"B: {len(result.wrong_host_careers_shaped)} (not listed)")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
