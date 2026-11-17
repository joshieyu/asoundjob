from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlencode, urlsplit

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError, listing
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

JOBSYN_HOSTS: frozenset[str] = frozenset({"stantec.jobs"})

API_URL = "https://prod-search-api.jobsyn.org/api/v1/google-talent/search"
PAGE_SIZE = 50
MAX_PAGES = 20


class JobsynScraper(BaseScraper):
    name = "jobsyn"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "jobsyn":
            return True
        if not company.careers_url:
            return False
        return normalize_host(company.careers_url.strip()) in JOBSYN_HOSTS

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        careers_url = (company.careers_url or "").strip()
        host = normalize_host(careers_url)
        if not host:
            raise ScrapeError(f"No jobsyn host in {company.careers_url}")
        items: list[dict[str, Any]] = []
        for query in extract_queries(careers_url):
            items.extend(await self._search(host, query))
        jobs = listing()
        jobs.extend(group_jobs(items, host))
        return jobs

    async def _search(self, host: str, query: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        headers = {"x-origin": host}
        for page in range(1, MAX_PAGES + 1):
            url = build_api_url(query, page)
            payload = await asyncio.to_thread(
                fetch_json, url, self.settings, None, headers
            )
            page_items, has_more = parse_page(payload, url)
            items.extend(page_items)
            if not has_more or not page_items:
                return items
        logger.info(
            "jobsyn: hit MAX_PAGES=%d cap for %s q=%r, jobs may be truncated",
            MAX_PAGES, host, query,
        )
        return items


def normalize_host(url: str) -> str:
    netloc = urlsplit(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def extract_queries(url: str) -> list[str]:
    values = parse_qs(urlsplit(url).query).get("q") or []
    queries: list[str] = []
    for value in values:
        query = value.strip()
        if query and query not in queries:
            queries.append(query)
    return queries or [""]


def build_api_url(query: str, page: int) -> str:
    params: dict[str, Any] = {"page": page, "num_items": PAGE_SIZE}
    if query:
        params["q"] = query
    return f"{API_URL}?{urlencode(params)}"


def parse_page(payload: Any, url: str) -> tuple[list[dict[str, Any]], bool]:
    if not isinstance(payload, dict):
        raise ScrapeError(f"Unexpected jobsyn payload from {url}: expected a dict")
    jobs_raw = payload.get("jobs")
    if not isinstance(jobs_raw, list):
        raise ScrapeError(f"Unexpected jobsyn payload from {url}: jobs is not a list")
    items = [
        wrapper["job"]
        for wrapper in jobs_raw
        if isinstance(wrapper, dict) and isinstance(wrapper.get("job"), dict)
    ]
    pagination = payload.get("pagination")
    has_more = isinstance(pagination, dict) and pagination.get("has_more_pages") is True
    return items, has_more


def group_jobs(items: list[dict[str, Any]], host: str) -> list[RawJob]:
    grouped: dict[str, RawJob] = {}
    locations: dict[str, list[str]] = {}
    seen: set[str] = set()
    for item in items:
        guid = item.get("requisitionId")
        title = item.get("title")
        if not isinstance(guid, str) or not guid or guid in seen:
            continue
        if not isinstance(title, str) or not title.strip():
            continue
        seen.add(guid)
        attributes = item.get("customAttributes")
        attributes = attributes if isinstance(attributes, dict) else {}
        key = _attribute(attributes, "reqid") or guid
        location = _attribute(attributes, "city_display") or _first_address(item)
        if key not in grouped:
            grouped[key] = RawJob(
                title=title.strip(),
                url=_job_url(host, attributes, guid),
                external_id=key,
                description=item.get("description"),
                posted_date=parse_date(
                    item.get("postingPublishTime") or item.get("postingCreateTime")
                ),
            )
            locations[key] = []
        if location and location not in locations[key]:
            locations[key].append(location)
    for key, job in grouped.items():
        job.location = "; ".join(locations[key]) or None
    return list(grouped.values())


def _attribute(attributes: dict[str, Any], name: str) -> str | None:
    entry = attributes.get(name)
    if not isinstance(entry, dict):
        return None
    values = entry.get("stringValues")
    if isinstance(values, list) and values and isinstance(values[0], str):
        return values[0].strip() or None
    return None


def _first_address(item: dict[str, Any]) -> str | None:
    addresses = item.get("addresses")
    if isinstance(addresses, list) and addresses and isinstance(addresses[0], str):
        return addresses[0].strip() or None
    return None


def _job_url(host: str, attributes: dict[str, Any], guid: str) -> str:
    city = _attribute(attributes, "city_display_slug")
    title = _attribute(attributes, "title_slug")
    if city and title:
        return f"https://{host}/{city}/{title}/{guid}/job/"
    return f"https://{host}/{guid}/job/"
