from __future__ import annotations

import json
import re
from datetime import date
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


def extract_jsonld_jobs(html: str, base_url: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[RawJob] = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.text
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if _is_job_posting(item):
                job = _parse_jsonld_job(item, base_url)
                if job:
                    jobs.append(job)
    return jobs


def extract_jobs(html: str, base_url: str) -> list[RawJob]:
    anchor_jobs = extract_job_links(html, base_url)
    jsonld_jobs = extract_jsonld_jobs(html, base_url)

    by_url: dict[str, RawJob] = {}
    for job in anchor_jobs:
        by_url[job.url] = job
    for job in jsonld_jobs:
        by_url[job.url] = job

    return sorted(by_url.values(), key=lambda j: j.url)


def _is_job_posting(item: dict) -> bool:
    item_type = item.get("@type", "")
    if isinstance(item_type, str):
        return item_type.lower() == "jobposting"
    if isinstance(item_type, list):
        return any(
            isinstance(t, str) and t.lower() == "jobposting" for t in item_type
        )
    return False


def _parse_jsonld_job(item: dict, base_url: str) -> RawJob | None:
    title = (item.get("title") or "").strip()
    if not title:
        return None

    url = item.get("url") or base_url
    if url != base_url:
        url = urljoin(base_url, url)

    description = item.get("description")
    location = _parse_jsonld_location(
        item.get("jobLocation") or item.get("location")
    )
    posted_date = _parse_jsonld_date(item.get("datePosted"))
    external_id = item.get("identifier") or item.get("uid")
    if external_id is not None:
        external_id = str(external_id)

    job_type = None
    emp_type = item.get("employmentType")
    if isinstance(emp_type, str):
        job_type = _normalize_employment_type(emp_type)
    elif isinstance(emp_type, list) and emp_type:
        job_type = _normalize_employment_type(emp_type[0])

    return RawJob(
        title=title,
        url=url,
        external_id=external_id,
        location=location,
        description=description,
        job_type=job_type,
        posted_date=posted_date,
    )


def _parse_jsonld_location(loc: object) -> str | None:
    if isinstance(loc, str):
        return loc.strip() or None
    if not isinstance(loc, dict):
        return None
    if "name" in loc:
        return str(loc["name"])
    address = loc.get("address")
    if isinstance(address, dict):
        locality = address.get("addressLocality")
        region = address.get("addressRegion")
        country = address.get("addressCountry")
        parts = [p for p in (locality, region, country) if p]
        if parts:
            return ", ".join(str(p) for p in parts)
    if "addressLocality" in loc:
        return str(loc["addressLocality"])
    return None


def _parse_jsonld_date(value: object) -> date | None:
    if not value or not isinstance(value, str):
        return None
    from scraper.scrapers.fetch import parse_date

    return parse_date(value)


def _normalize_employment_type(value: str) -> str | None:
    lower = value.lower().strip()
    mapping = {
        "full_time": "full-time",
        "full-time": "full-time",
        "part_time": "part-time",
        "part-time": "part-time",
        "contract": "contract",
        "contractor": "contract",
        "temporary": "contract",
        "intern": "internship",
        "internship": "internship",
    }
    return mapping.get(lower, lower.replace(" ", "-"))
