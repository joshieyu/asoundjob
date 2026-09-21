from __future__ import annotations

import re
from typing import Optional

from scraper.detect_nonjob_rows import classify_title

DESCRIPTION_MIN_CHARS = 200
GRADE_ORDER: tuple[str, ...] = (
    "failing", "silent", "furniture", "thin", "idle", "healthy", "unscraped",
)
FURNITURE_MIN_ROWS = 3
FURNITURE_MAX_ROLE_SHARE = 0.25

INTL_ROLE_NOUNS_PATTERN = re.compile(
    r"\b(ing[ée]nieur|ingenieur|techniker|technicien|responsable|assistenz|"
    r"assistent|leitung|leiter|praktikant\w{0,3}|stage|stagiaire|alternan\w{1,3}|"
    r"chef|directeur|direktor|entwickler|mitarbeiter\w{0,3}|sp[ée]cialiste|"
    r"pr[ée]parateur|agent|apprenti\w{0,3}|ausbildung|werkstudent\w{0,3}|"
    r"konstrukteur|berater|vertrieb|einkauf|monteur|meister|kaufmann|kauffrau|"
    r"medewerker|ingenj[oö]r|utvecklare|konsult|clerk|specialist|generalist|"
    r"consultant|elektroniker|eink[äa]ufer)\b",
    re.IGNORECASE,
)


def looks_like_role(title: str) -> bool:
    return bool(INTL_ROLE_NOUNS_PATTERN.search(title))


def is_described(description: Optional[str]) -> bool:
    if description is None:
        return False
    return len(description.strip()) >= DESCRIPTION_MIN_CHARS


def shape_shares(
    titles: list[str], described_flags: list[bool]
) -> tuple[float, float]:
    if not titles:
        return (0.0, 0.0)
    described_count = sum(1 for flag in described_flags if flag)
    role_count = sum(
        1
        for title in titles
        if classify_title(title) == "job_shaped" or looks_like_role(title)
    )
    total = len(titles)
    return (
        round(described_count / total, 2),
        round(role_count / total, 2),
    )


def in_scrape_population(
    verified: bool, careers_url: Optional[str], scrape_blocked: bool
) -> bool:
    return bool(verified) and careers_url is not None and not scrape_blocked


def grade_company(
    active_rows: int,
    described_share: float,
    role_share: float,
    board_count: int,
    last_scrape_status: Optional[str],
    scraped: bool = True,
) -> str:
    if not scraped:
        return "unscraped"
    if last_scrape_status == "failed":
        return "failing"
    if active_rows == 0:
        return "silent"
    if (
        active_rows >= FURNITURE_MIN_ROWS
        and described_share == 0
        and role_share < FURNITURE_MAX_ROLE_SHARE
    ):
        return "furniture"
    if active_rows >= FURNITURE_MIN_ROWS and described_share < 0.2:
        return "thin"
    if board_count == 0:
        return "idle"
    return "healthy"


def grade_rank(grade: str) -> int:
    try:
        return GRADE_ORDER.index(grade)
    except ValueError:
        return len(GRADE_ORDER)
