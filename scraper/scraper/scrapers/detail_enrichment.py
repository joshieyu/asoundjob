from __future__ import annotations

from typing import Optional
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag

from scraper.scrapers.base import RawJob
from scraper.scrapers.link_extraction import extract_jsonld_jobs

MIN_DESCRIPTION_CHARS = 200
MAX_LOCATION_TEXT = 120
ADDRESS_PROPS = ("addressLocality", "addressRegion", "addressCountry")


def needs_detail(job: RawJob) -> bool:
    return description_is_thin(job) or not job.location


def description_is_thin(job: RawJob) -> bool:
    return job.description is None or len(job.description) < MIN_DESCRIPTION_CHARS


def apply_structured_detail(job: RawJob, html: str) -> None:
    posting = _matching_posting(job, extract_jsonld_jobs(html, job.url))
    if posting is not None:
        if posting.description and (
            description_is_thin(job)
            and len(posting.description) > len(job.description or "")
        ):
            job.description = posting.description
        if not job.location and posting.location:
            job.location = posting.location
        if not job.posted_date and posting.posted_date:
            job.posted_date = posting.posted_date
        if not job.job_type and posting.job_type:
            job.job_type = posting.job_type
    if not job.location:
        job.location = microdata_location(html)


def _matching_posting(job: RawJob, postings: list[RawJob]) -> Optional[RawJob]:
    if not postings:
        return None
    target = _comparable_url(job.url)
    for posting in postings:
        if _comparable_url(posting.url) == target:
            return posting
    title = job.title.strip().lower()
    titled = [p for p in postings if p.title.strip().lower() == title]
    return titled[0] if len(titled) == 1 else None


def _comparable_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return f"{host}{parts.path.rstrip('/')}?{parts.query}"


def microdata_location(html: str) -> Optional[str]:
    if 'itemprop="jobLocation"' not in html and "itemprop='jobLocation'" not in html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    node = soup.find(itemprop="jobLocation")
    if not isinstance(node, Tag):
        return None
    parts: list[str] = []
    for prop in ADDRESS_PROPS:
        part = node.find(itemprop=prop)
        if not isinstance(part, Tag):
            continue
        value = str(part.get("content") or part.get_text(" ", strip=True)).strip()
        if value and value not in parts:
            parts.append(value)
    if parts:
        return ", ".join(parts)
    street = node.find(itemprop="streetAddress")
    if isinstance(street, Tag):
        value = str(street.get("content") or street.get_text(" ", strip=True)).strip()
        if value:
            return value
    text = node.get_text(" ", strip=True)
    return text if 0 < len(text) <= MAX_LOCATION_TEXT else None
