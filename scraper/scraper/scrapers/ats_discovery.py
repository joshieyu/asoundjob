from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "greenhouse",
        re.compile(
            r"(?:job-)?boards(?:\.[a-z]{2,4})?\.greenhouse\.io/"
            r"(?:embed/job_board(?:/js)?\?for=)?(?P<slug>[a-z0-9_-]{1,63})",
            re.IGNORECASE,
        ),
    ),
    (
        "lever",
        re.compile(
            r"jobs\.lever\.co/(?P<slug>[a-z0-9_-]+)", re.IGNORECASE
        ),
    ),
    (
        "workable",
        re.compile(
            r"apply\.workable\.com/(?P<slug>[a-z0-9_-]+)", re.IGNORECASE
        ),
    ),
    (
        "ashby",
        re.compile(
            r"jobs\.ashbyhq\.com/(?P<slug>[a-z0-9_-]+)", re.IGNORECASE
        ),
    ),
    (
        "smartrecruiters",
        re.compile(
            r"careers\.smartrecruiters\.com/(?P<slug>[a-z0-9_-]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "recruitee",
        re.compile(
            r"(?P<slug>[a-z0-9-]{1,63})\.recruitee\.com", re.IGNORECASE
        ),
    ),
    (
        "workday",
        re.compile(
            r"(?P<tenant>[a-z0-9]{1,63})\.(?P<dc>wd\d+)\.myworkdayjobs\.com"
            r"(?:/[a-z]{2}-[a-z]{2})?/(?P<site>[a-z0-9_-]{1,80})",
            re.IGNORECASE,
        ),
    ),
    (
        "bamboohr",
        re.compile(
            r"(?P<slug>[a-z0-9-]{1,63})\.bamboohr\.com/careers", re.IGNORECASE
        ),
    ),
    (
        "breezy",
        re.compile(
            r"(?P<slug>[a-z0-9-]{1,63})\.breezy\.hr", re.IGNORECASE
        ),
    ),
    (
        "pinpoint",
        re.compile(
            r"(?P<slug>[a-z0-9-]{1,63})\.pinpointhq\.com", re.IGNORECASE
        ),
    ),
    (
        "adp",
        re.compile(
            r"myjobs\.adp\.com/(?P<slug>[a-z0-9_]+)", re.IGNORECASE
        ),
    ),
    (
        "adp",
        re.compile(
            r"workforcenow\.adp\.com/[^\s\"'<>]{1,200}[?&]cid="
            r"(?P<slug>[0-9a-fA-F-]{36})",
            re.IGNORECASE,
        ),
    ),
    (
        "icims",
        re.compile(
            r"(?P<slug>[a-z0-9-]{1,63})\.icims\.com", re.IGNORECASE
        ),
    ),
    ("apple", re.compile(r"jobs\.apple\.com", re.IGNORECASE)),
]

SLUGLESS_ATS = {"apple"}

NON_BOARD_SUBDOMAINS = frozenset(
    {
        "analytics",
        "api",
        "assets",
        "cdn",
        "help",
        "static",
        "support",
        "www",
    }
)

NON_BOARD_SUBDOMAIN_RE = re.compile(
    r"^(?:assets|static|cdn|img|images|media|files|analytics)[-.]"
    r"|[-.](?:cdn|assets|analytics)$",
    re.IGNORECASE,
)


def discover(html: str, base_url: str = "") -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for ats_type, pattern in PATTERNS:
        for m in pattern.finditer(html):
            groups = m.groupdict()
            if ats_type in SLUGLESS_ATS:
                slug = ""
            elif groups.get("tenant") and groups.get("site"):
                host = groups["tenant"]
                if groups.get("dc"):
                    host = f"{host}.{groups['dc']}"
                slug = f"{host}/{groups['site'].rstrip('/')}"
            else:
                slug = (groups.get("slug") or "").strip("/")
                lowered = slug.lower()
                if lowered in NON_BOARD_SUBDOMAINS:
                    continue
                if NON_BOARD_SUBDOMAIN_RE.search(lowered):
                    continue
            key = (ats_type, slug.lower())
            if key not in seen:
                seen.add(key)
                results.append((ats_type, slug))
    return results


def first_discovery(html: str, base_url: str = "") -> tuple[str, str] | None:
    results = discover(html, base_url)
    return results[0] if results else None
