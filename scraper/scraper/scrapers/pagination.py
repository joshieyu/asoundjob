from __future__ import annotations

import re
from typing import Awaitable, Callable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from scraper.scrapers.base import RawJob
from scraper.scrapers.link_extraction import extract_jobs

MAX_PAGES = 10

ARIA_NEXT_RE = re.compile(
    r"\bnext\s+page\b|\bgo\s+to\s+next\b|^next$",
    re.IGNORECASE,
)

TEXT_NEXT_RE = re.compile(
    r"^(?:next|next\s+page|»|›|>>)$",
    re.IGNORECASE,
)

CLASS_NEXT_RE = re.compile(
    r"pagination[\w-]{0,20}next|next[\w-]{0,10}(?:page|link)",
    re.IGNORECASE,
)


def _rel_has_next(anchor: Tag) -> bool:
    rel = anchor.get("rel")
    if rel is None:
        return False
    if isinstance(rel, str):
        values = rel.split()
    else:
        values = list(rel)
    return any(value.lower() == "next" for value in values)


def _aria_label_matches(anchor: Tag) -> bool:
    label = anchor.get("aria-label")
    if not label:
        return False
    return bool(ARIA_NEXT_RE.search(str(label)))


def _text_matches(anchor: Tag) -> bool:
    text = anchor.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return False
    return bool(TEXT_NEXT_RE.match(text))


def _class_matches(anchor: Tag) -> bool:
    classes = anchor.get("class")
    if not classes:
        return False
    if isinstance(classes, str):
        class_str = classes
    else:
        class_str = " ".join(classes)
    return bool(CLASS_NEXT_RE.search(class_str))


def _is_candidate(anchor: Tag) -> bool:
    return (
        _rel_has_next(anchor)
        or _aria_label_matches(anchor)
        or _text_matches(anchor)
        or _class_matches(anchor)
    )


def _page_key(url: str) -> Tuple[str, str, str]:
    parsed = urlparse(url)
    return (parsed.netloc.lower(), parsed.path.rstrip("/").lower(), parsed.query)


def find_next_page(html: str, base_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    base_key = _page_key(base_url)

    for anchor in soup.find_all("a", href=True):
        if not _is_candidate(anchor):
            continue
        href = anchor.get("href")
        if not href or not isinstance(href, str):
            continue
        resolved = urljoin(base_url, href)
        parsed = urlparse(resolved)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc.lower() != base_key[0]:
            continue
        if parsed.path.rstrip("/").lower() != base_key[1]:
            continue
        if not parsed.query:
            continue
        candidate_key = _page_key(resolved)
        if candidate_key == base_key:
            continue
        return resolved
    return None


FetchFn = Callable[[str], Awaitable[str]]


async def collect_paginated(
    fetch: FetchFn,
    start_url: str,
    max_pages: int = MAX_PAGES,
) -> Tuple[List[RawJob], Optional[str]]:
    jobs: List[RawJob] = []
    seen_job_urls: Set[str] = set()
    visited_pages: Set[Tuple[str, str, str]] = {_page_key(start_url)}
    first_page_html: Optional[str] = None

    url = start_url
    for _ in range(max_pages):
        html = await fetch(url)
        if first_page_html is None:
            first_page_html = html
        page_jobs = extract_jobs(html, url)
        new_jobs = [job for job in page_jobs if job.url not in seen_job_urls]
        if not new_jobs:
            break
        for job in new_jobs:
            seen_job_urls.add(job.url)
            jobs.append(job)

        next_url = find_next_page(html, url)
        if not next_url:
            break
        next_key = _page_key(next_url)
        if next_key in visited_pages:
            break
        visited_pages.add(next_key)
        url = next_url

    return jobs, first_page_html
