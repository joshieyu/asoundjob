from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime
from time import monotonic
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import parse_qs, quote, urljoin, urlsplit

from bs4 import BeautifulSoup

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_html, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(
    r"^https?://(?P<host>[^/]{1,253})/"
    r"(?:search/?(?:\?[^\s]{0,2000})?"
    r"|go/(?P<board>[A-Za-z0-9][A-Za-z0-9-]{0,98})/(?P<board_id>\d{1,20})/?)"
    r"$",
    re.IGNORECASE,
)

JAVA_DATE_RE = re.compile(
    r"(?P<month>[A-Z][a-z]{2})\s{1,4}(?P<day>\d{1,2})\s{1,4}"
    r"\d{1,2}:\d{2}:\d{2}\s{1,4}[A-Za-z/_+-]{1,20}\s{1,4}(?P<year>\d{4})"
)

SEARCH_URL = "{origin}/search/?q={query}&startrow={startrow}"

PAGE_SIZE = 10
MAX_PAGES = 40
MAX_DETAIL_FETCHES = 150
DETAIL_FETCH_CONCURRENCY = 8
ENRICHMENT_BUDGET_FRACTION = 0.85

EXTERNAL_ID_RE = re.compile(r"/(?P<id>\d{1,20})/?$")


class SuccessFactorsScraper(BaseScraper):
    name = "successfactors"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "successfactors":
            return True
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        start = monotonic()
        careers_url = (company.careers_url or "").strip()
        parsed = urlsplit(careers_url)
        if not parsed.netloc:
            raise ScrapeError(f"No successfactors host in {company.careers_url}")
        origin = f"{parsed.scheme}://{parsed.netloc}"
        query = (parse_qs(parsed.query).get("q") or [""])[0]

        jobs: list[RawJob] = []
        seen_keys: set[str] = set()
        for page_index in range(MAX_PAGES):
            startrow = page_index * PAGE_SIZE
            url = SEARCH_URL.format(
                origin=origin, query=quote(query), startrow=startrow
            )
            html_text = await asyncio.to_thread(fetch_html, url, self.settings)
            page_jobs = parse_listing_page(html_text, origin)
            if not page_jobs:
                break
            for job in page_jobs:
                key = job.external_id or job.url
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                jobs.append(job)
            if len(page_jobs) < PAGE_SIZE:
                break

        deadline = start + self.settings.per_company_timeout * ENRICHMENT_BUDGET_FRACTION
        semaphore = asyncio.Semaphore(DETAIL_FETCH_CONCURRENCY)
        counts = {"enriched": 0, "budget_skipped": 0}
        fetch_list = jobs[:MAX_DETAIL_FETCHES]
        await asyncio.gather(
            *(
                self._enrich_job(job, semaphore, deadline, counts)
                for job in fetch_list
            )
        )
        if counts["budget_skipped"] > 0:
            logger.info(
                "successfactors: enrichment budget exhausted, enriched %d/%d jobs",
                counts["enriched"],
                len(fetch_list),
            )
        return jobs

    async def _enrich_job(
        self,
        job: RawJob,
        semaphore: asyncio.Semaphore,
        deadline: float,
        counts: dict[str, int],
    ) -> None:
        async with semaphore:
            if monotonic() >= deadline:
                counts["budget_skipped"] += 1
                return
            try:
                detail_html = await asyncio.to_thread(fetch_html, job.url, self.settings)
                detail = extract_detail(detail_html)
            except Exception as exc:
                logger.warning(
                    "successfactors: detail fetch failed for %s: %s", job.url, exc
                )
                return
        apply_detail(job, detail)
        counts["enriched"] += 1


def parse_listing_page(html_text: str, origin: str) -> list[RawJob]:
    soup = BeautifulSoup(html_text, "html.parser")
    jobs: list[RawJob] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        class_value: str | list[str] = anchor.get("class") or []
        classes = class_value if isinstance(class_value, list) else [class_value]
        if "jobTitle-link" not in classes:
            continue
        href = str(anchor["href"]).strip()
        if not href:
            continue
        title = anchor.get_text(" ", strip=True)
        if not title:
            continue
        url = urljoin(origin, href)
        external_id = extract_external_id(href)
        key = external_id or url
        if key in seen:
            continue
        seen.add(key)
        jobs.append(RawJob(title=title, url=url, external_id=external_id))
    return jobs


def extract_external_id(href: str) -> str | None:
    path = urlsplit(href).path
    match = EXTERNAL_ID_RE.search(path)
    return match.group("id") if match else None


def extract_detail(html_text: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_text, "html.parser")
    detail: dict[str, Any] = {}

    description_node = soup.find(itemprop="description")
    if description_node is not None:
        body = description_node.find(class_="jobdescription") or description_node
        content = body.decode_contents().strip()
        if content:
            detail["description"] = content

    posted_node = soup.find(itemprop="datePosted")
    if posted_node is not None:
        posted_value = posted_node.get("content") or posted_node.get_text(
            " ", strip=True
        )
        posted_date = parse_date(posted_value) or _parse_java_date(posted_value)
        if posted_date:
            detail["posted_date"] = posted_date

    location = _extract_location(soup)
    if location:
        detail["location"] = location

    return detail


def _extract_location(soup: BeautifulSoup) -> Optional[str]:
    address_node = soup.find("meta", attrs={"itemprop": "streetAddress"})
    if address_node is not None:
        content = str(address_node.get("content") or "").strip()
        if content:
            return content
    location_node = soup.find(itemprop="jobLocation")
    if location_node is None:
        return None
    text = location_node.get_text(" ", strip=True)
    return text or None


def _parse_java_date(value: Any) -> Optional[date]:
    if not value:
        return None
    match = JAVA_DATE_RE.search(str(value))
    if match is None:
        return None
    try:
        return datetime.strptime(
            f"{match.group('month')} {match.group('day')} {match.group('year')}",
            "%b %d %Y",
        ).date()
    except ValueError:
        return None


def apply_detail(job: RawJob, detail: dict[str, Any]) -> None:
    description = detail.get("description")
    if description:
        job.description = description
    posted_date = detail.get("posted_date")
    if posted_date:
        job.posted_date = posted_date
    location = detail.get("location")
    if location:
        job.location = location
