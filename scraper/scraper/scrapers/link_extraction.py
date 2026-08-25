from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scraper.scrapers.base import RawJob

JOB_HINT = re.compile(
    r"(job|jobs|career|careers|position|opening|vacanc|opportunit|hiring|"
    r"apply/|/apply|employment|roles)",
    re.IGNORECASE,
)

NON_JOB_URL = re.compile(
    r"(mailto:|tel:|javascript:|^#$|^$)",
    re.IGNORECASE,
)

SOCIAL_DOMAIN = re.compile(
    r"(linkedin\.com/share|facebook\.com/(share|sharer)|twitter\.com/(intent|share)|"
    r"x\.com/intent|instagram\.com|youtube\.com|wa\.me|whatsapp\.com|t\.me/|"
    r"glassdoor|indeed\.com|mailchi|us\d+\.list-manage|google\.com/maps)",
    re.IGNORECASE,
)

NON_JOB_TEXT = {
    "learn more",
    "read more",
    "about us",
    "contact",
    "contact us",
    "press",
    "blog",
    "news",
    "home",
    "back",
    "submit",
    "search",
    "sign in",
    "log in",
    "login",
    "sign up",
    "apply now",
    "view all jobs",
    "see all jobs",
    "all jobs",
    "view all openings",
    "join us",
    "join our team",
    "benefits",
    "culture",
    "diversity",
    "privacy policy",
    "terms of service",
    "cookie policy",
    "faq",
}

MIN_TITLE_LEN = 3
MAX_TITLE_LEN = 150


def _clean_text(text: object) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def extract_job_links(html: str, base_url: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "html.parser")
    best_by_url: dict[str, tuple[str, str]] = {}
    base_path = urlparse(base_url).path.rstrip("/").lower()

    for anchor in soup.find_all("a", href=True):
        href = _clean_text(anchor.get("href"))
        if not href or NON_JOB_URL.search(href):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if SOCIAL_DOMAIN.search(absolute):
            continue

        path = parsed.path.rstrip("/").lower()
        text = _clean_text(anchor.get_text())
        title_attr = _clean_text(anchor.get("title"))
        candidate_title = text or title_attr
        if len(candidate_title) < MIN_TITLE_LEN or len(candidate_title) > MAX_TITLE_LEN:
            continue
        if candidate_title.lower() in NON_JOB_TEXT:
            continue

        looks_like_job = bool(
            JOB_HINT.search(path)
            or (text and JOB_HINT.search(text))
            or (title_attr and JOB_HINT.search(title_attr))
        )
        if not looks_like_job:
            continue
        if path == base_path or path == "":
            continue

        existing = best_by_url.get(absolute)
        if existing is None or len(candidate_title) > len(existing[0]):
            best_by_url[absolute] = (candidate_title, path)

    return [
        RawJob(title=title, url=absolute)
        for absolute, (title, _) in sorted(best_by_url.items())
    ]
