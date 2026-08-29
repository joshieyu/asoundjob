from __future__ import annotations

import asyncio
import copy
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_html
from scraper.scrapers.link_extraction import extract_jsonld_jobs

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?P<slug>[a-z0-9-]+)\.icims\.com",
    re.IGNORECASE,
)

LIST_URL = "https://{slug}.icims.com/jobs/search?ss=1&in_iframe=1&pr={page}"
JOB_PATH_RE = re.compile(r"^/jobs/(?P<id>\d{1,15})/[^/]{1,200}/job/?$", re.IGNORECASE)
DROP_QUERY_PARAMS = {"in_iframe", "hub"}
REDIRECT_MARKER = "window.top.location.href"
REDIRECT_URL_RE = re.compile(
    r"window\.top\.location\.href\s*=\s*['\"](?P<url>[^'\"]{1,500})['\"]"
)
EMPTY_BOARD_RE = re.compile(
    r"no jobs were found|no results found", re.IGNORECASE
)
SCREEN_READER_CLASSES = re.compile(r"sr-only|screen-reader|visually-hidden")
PAGE_SIZE = 20
MAX_PAGES = 20
MAX_DETAIL_FETCHES = 100


class IcimsScraper(BaseScraper):
    name = "icims"

    def can_handle(self, company: Company) -> bool:
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    @staticmethod
    def extract_slug(url: str) -> str | None:
        match = URL_PATTERN.match(url.strip())
        return match.group("slug") if match else None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        slug = company.ats_slug or self.extract_slug(company.careers_url or "")
        if not slug:
            raise ValueError(f"No icims slug in {company.careers_url}")
        jobs = await self._fetch_all(slug)
        await self._fetch_descriptions(jobs)
        return jobs

    async def _fetch_all(self, slug: str) -> list[RawJob]:
        jobs: list[RawJob] = []
        seen_ids: set[str] = set()
        for page in range(MAX_PAGES):
            url = LIST_URL.format(slug=slug, page=page)
            html_text = await asyncio.to_thread(fetch_html, url, self.settings)
            page_jobs = parse_listing_page(html_text)
            if not page_jobs:
                target = redirect_target(html_text)
                if target:
                    raise ScrapeError(
                        f"icims board for {slug} has migrated off-platform to {target}"
                    )
                if page == 0 and not EMPTY_BOARD_RE.search(html_text):
                    raise ScrapeError(
                        f"icims listing for {slug} had no job links and no "
                        f"empty-board marker"
                    )
                break
            new_jobs = [j for j in page_jobs if j.external_id not in seen_ids]
            if not new_jobs:
                break
            seen_ids.update(j.external_id for j in new_jobs if j.external_id)
            jobs.extend(new_jobs)
            if len(page_jobs) < PAGE_SIZE:
                break
        return jobs

    async def _fetch_descriptions(self, jobs: list[RawJob]) -> None:
        sem = asyncio.Semaphore(self.settings.http_concurrency)

        async def fetch_one(job: RawJob) -> None:
            async with sem:
                try:
                    detail_html = await asyncio.to_thread(
                        fetch_html, detail_url(job.url), self.settings
                    )
                except Exception:
                    return
                detail_jobs = extract_jsonld_jobs(detail_html, job.url)
                if not detail_jobs:
                    return
                detail = detail_jobs[0]
                job.description = detail.description
                job.location = detail.location or job.location
                job.posted_date = detail.posted_date or job.posted_date

        await asyncio.gather(*(fetch_one(j) for j in jobs[:MAX_DETAIL_FETCHES]))


def detail_url(url: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}in_iframe=1"


def parse_listing_page(html_text: str) -> list[RawJob]:
    soup = BeautifulSoup(html_text, "html.parser")
    jobs: list[RawJob] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href:
            continue
        path = urlsplit(href).path
        match = JOB_PATH_RE.match(path)
        if not match:
            continue
        external_id = match.group("id")
        if external_id in seen:
            continue
        title = anchor_title(anchor)
        if not title:
            continue
        seen.add(external_id)
        jobs.append(
            RawJob(
                title=title,
                url=strip_query_params(href),
                external_id=external_id,
            )
        )
    return jobs


def anchor_title(anchor: Any) -> str:
    candidate = copy.copy(anchor)
    for node in candidate.find_all(class_=SCREEN_READER_CLASSES):
        node.decompose()
    heading = candidate.find(["h1", "h2", "h3", "h4"])
    source = heading if heading is not None else candidate
    return " ".join(source.get_text(" ", strip=True).split())


def strip_query_params(href: str) -> str:
    parts = urlsplit(href)
    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in DROP_QUERY_PARAMS
    ]
    query = urlencode(kept)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def redirect_target(html_text: str) -> str | None:
    if REDIRECT_MARKER not in html_text:
        return None
    match = REDIRECT_URL_RE.search(html_text)
    return match.group("url").replace("\\/", "/") if match else None
