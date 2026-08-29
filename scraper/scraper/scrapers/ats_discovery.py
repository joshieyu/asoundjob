from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "greenhouse",
        re.compile(
            r"(?:job-)?boards\.greenhouse\.io/"
            r"(?:embed/job_board\?for=)?(?P<slug>[a-z0-9_-]+)",
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
            r"(?:wd\d+\.)?myworkdayjobs\.com/(?P<slug>[a-z0-9_]+)",
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
    ("apple", re.compile(r"jobs\.apple\.com", re.IGNORECASE)),
]

SLUGLESS_ATS = {"apple"}


def discover(html: str, base_url: str = "") -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for ats_type, pattern in PATTERNS:
        for m in pattern.finditer(html):
            if ats_type in SLUGLESS_ATS:
                slug = ""
            else:
                slug = (m.groupdict().get("slug") or "").strip("/")
            key = (ats_type, slug.lower())
            if key not in seen:
                seen.add(key)
                results.append((ats_type, slug))
    return results


def first_discovery(html: str, base_url: str = "") -> tuple[str, str] | None:
    results = discover(html, base_url)
    return results[0] if results else None
