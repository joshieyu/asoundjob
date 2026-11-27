from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

from scraper.scrapers.base import RawJob

MAX_KEYWORDS = 10


def url_keywords(url: str) -> list[str]:
    values = parse_qs(urlsplit(url.strip()).query).get("q") or []
    keywords: list[str] = []
    for value in values:
        keyword = " ".join(value.split()).lower()
        if keyword and keyword not in keywords:
            keywords.append(keyword)
    return keywords[:MAX_KEYWORDS]


def scope_to_keywords(jobs: list[RawJob], url: str) -> list[RawJob]:
    keywords = url_keywords(url)
    if not keywords:
        return jobs
    patterns = [re.compile(r"\b" + re.escape(k), re.IGNORECASE) for k in keywords]
    kept = [job for job in jobs if any(_matches(p, job) for p in patterns)]
    jobs[:] = kept
    return jobs


def _matches(pattern: re.Pattern[str], job: RawJob) -> bool:
    return bool(pattern.search(job.title or "") or pattern.search(job.description or ""))
