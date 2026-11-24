from __future__ import annotations

import asyncio
import html
import json
import re
from datetime import date, datetime
from time import monotonic
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, unquote, urlparse

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError, company_budget, listing
from scraper.scrapers.fetch import FetchError, _send, fetch_html

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?P<host>[a-z0-9-]+\.taleo\.net)/careersection/(?P<section>[A-Za-z0-9_-]+)/",
    re.IGNORECASE,
)

PORTAL_RE = re.compile(r"portal=(\d{3,20})")

HISTORY_RE = re.compile(r'id="initialHistory"\s+value="([^"]*)"')

RICH_TEXT_MARKER = "!*!"

PAGE_SIZE = 25
MAX_PAGES = 20
MAX_DETAIL_FETCHES = 60
DETAIL_CONCURRENCY = 6
ENRICHMENT_BUDGET_FRACTION = 0.3
MIN_DESCRIPTION_PART = 200
EEO_HINTS = ("affirmative action", "employment equity", "equal opportunity")


class TaleoScraper(BaseScraper):
    name = "taleo"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "taleo":
            return True
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        deadline = monotonic() + company_budget(self.settings, company) * ENRICHMENT_BUDGET_FRACTION
        careers_url = (company.careers_url or "").strip()
        match = URL_PATTERN.match(careers_url)
        if not match:
            raise ScrapeError(f"No taleo career section in {company.careers_url}")
        host = match.group("host").lower()
        section = match.group("section")
        keyword = (parse_qs(urlparse(careers_url).query).get("keyword") or [""])[0]

        search_page = f"https://{host}/careersection/{section}/jobsearch.ftl?lang=en"
        page_html = await asyncio.to_thread(fetch_html, search_page, self.settings)
        portal = PORTAL_RE.search(page_html)
        if not portal:
            raise ScrapeError(f"No taleo portal id on {search_page}")

        jobs = listing()
        for page_no in range(1, MAX_PAGES + 1):
            payload = await asyncio.to_thread(
                self._search, host, portal.group(1), keyword, page_no
            )
            page_jobs = parse_search(payload, host, section)
            jobs.extend(page_jobs)
            paging = payload.get("pagingData") if isinstance(payload, dict) else None
            total = paging.get("totalCount") if isinstance(paging, dict) else None
            if not page_jobs or not isinstance(total, int) or page_no * PAGE_SIZE >= total:
                break

        semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
        await asyncio.gather(
            *(self._describe(job, semaphore, deadline) for job in jobs[:MAX_DETAIL_FETCHES])
        )
        return jobs

    def _search(self, host: str, portal: str, keyword: str, page_no: int) -> Any:
        url = f"https://{host}/careersection/rest/jobboard/searchjobs?lang=en&portal={portal}"
        body = {
            "multilineEnabled": False,
            "sortingSelection": {"sortBySelectionParam": "3", "ascendingSortingOrder": "false"},
            "fieldData": {"fields": {"KEYWORD": keyword, "LOCATION": ""}, "valid": True},
            "filterSelectionParam": {"searchFilterSelections": []},
            "advancedSearchFiltersSelectionParam": {"searchFilterSelections": []},
            "pageNo": page_no,
        }
        response = _send(
            "POST", url, self.settings, None, json=body, headers={"tz": "GMT+00:00"}
        )
        if response.status_code != 200:
            raise FetchError(f"HTTP {response.status_code} for {url}", response.status_code)
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise FetchError(f"Invalid JSON from {url}: {exc}") from exc

    async def _describe(
        self, job: RawJob, semaphore: asyncio.Semaphore, deadline: float
    ) -> None:
        async with semaphore:
            if monotonic() >= deadline:
                return
            try:
                page = await asyncio.to_thread(fetch_html, job.url, self.settings)
            except FetchError:
                return
        description = parse_detail_description(page)
        if description:
            job.description = description


def parse_search(payload: Any, host: str, section: str) -> list[RawJob]:
    if not isinstance(payload, dict):
        raise ScrapeError("Unexpected taleo payload: expected a dict")
    rows = payload.get("requisitionList")
    if not isinstance(rows, list):
        raise ScrapeError("Unexpected taleo payload: requisitionList is not a list")
    jobs: list[RawJob] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        columns = row.get("column")
        contest = str(row.get("contestNo") or "").strip()
        if not isinstance(columns, list) or not columns or not contest:
            continue
        title = str(columns[0] or "").strip()
        if not title:
            continue
        jobs.append(
            RawJob(
                title=title,
                url=f"https://{host}/careersection/{section}/jobdetail.ftl?job={contest}&lang=en",
                external_id=contest,
                location=_location(columns, row.get("locationsColumns")),
                posted_date=_posted(columns[-1]) if len(columns) > 2 else None,
            )
        )
    return jobs


def _posted(value: Any) -> date | None:
    try:
        return datetime.strptime(str(value).strip(), "%b %d, %Y").date()
    except ValueError:
        return None


def _location(columns: list[Any], location_indexes: Any) -> str | None:
    if not isinstance(location_indexes, list):
        return None
    names: list[str] = []
    for index in location_indexes:
        if not isinstance(index, int) or index >= len(columns):
            continue
        raw = columns[index]
        try:
            value = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            value = raw
        values = value if isinstance(value, list) else [value]
        names.extend(str(v).strip() for v in values if str(v or "").strip())
    return "; ".join(names) or None


def parse_detail_description(page: str) -> str | None:
    match = HISTORY_RE.search(page)
    if not match:
        return None
    parts: list[str] = []
    for raw in html.unescape(match.group(1)).split("!|!"):
        text = unquote(raw)
        if not text.startswith(RICH_TEXT_MARKER) or len(text) < MIN_DESCRIPTION_PART:
            continue
        body = text[len(RICH_TEXT_MARKER):].replace("\\:", ":")
        if any(hint in body.lower()[:400] for hint in EEO_HINTS):
            continue
        parts.append(body)
    return "\n".join(parts) or None
