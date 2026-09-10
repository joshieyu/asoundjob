from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlparse

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import parse_date, post_json

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?P<host>recruiting\d{0,2}\.ultipro\.com)/"
    r"(?P<tenant>[A-Za-z0-9]{1,64})/JobBoard/"
    r"(?P<board>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
    re.IGNORECASE,
)

SEARCH_URL = "https://{host}/{tenant}/JobBoard/{board}/JobBoardView/LoadSearchResults"
DETAIL_URL = (
    "https://{host}/{tenant}/JobBoard/{board}/OpportunityDetail"
    "?opportunityId={opportunity_id}"
)

PAGE_SIZE = 100
MAX_PAGES = 10

LOCATION_SEPARATOR = "; "


class UltiproScraper(BaseScraper):
    name = "ultipro"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "ultipro":
            return True
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    @staticmethod
    def extract_slug(url: str) -> str | None:
        match = URL_PATTERN.match(url.strip())
        if not match:
            return None
        return f"{match.group('tenant')}/{match.group('board')}"

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        careers_url = (company.careers_url or "").strip()
        parsed = urlparse(careers_url)
        host = parsed.netloc
        if not host:
            raise ScrapeError(f"No ultipro host in {company.careers_url}")
        slug = company.ats_slug or self.extract_slug(careers_url)
        if not slug or "/" not in slug:
            raise ScrapeError(f"No ultipro slug in {company.careers_url}")
        tenant, board = slug.split("/", 1)
        query = (parse_qs(parsed.query).get("q") or [""])[0]

        search_url = SEARCH_URL.format(host=host, tenant=tenant, board=board)
        all_opportunities: list[Any] = []
        total_count: int | None = None
        for page_index in range(MAX_PAGES):
            payload = _build_payload(query, page_index * PAGE_SIZE)
            response = await asyncio.to_thread(
                post_json, search_url, payload, self.settings
            )
            if page_index == 0:
                try:
                    parse_opportunities(response, host, tenant, board)
                except ValueError as exc:
                    raise ScrapeError(
                        f"Unexpected ultipro search response for "
                        f"{tenant}/{board}: {exc}"
                    ) from exc
            opportunities = (
                response.get("opportunities") if isinstance(response, dict) else None
            )
            if not isinstance(opportunities, list) or not opportunities:
                break
            all_opportunities.extend(opportunities)
            count = response.get("totalCount") if isinstance(response, dict) else None
            if isinstance(count, int):
                total_count = count
            if isinstance(total_count, int) and len(all_opportunities) >= total_count:
                break

        return parse_opportunities(
            {"opportunities": all_opportunities}, host, tenant, board
        )


def _build_payload(query: str, skip: int) -> dict[str, Any]:
    return {
        "opportunitySearch": {
            "Top": PAGE_SIZE,
            "Skip": skip,
            "QueryString": query,
            "OrderBy": [{"Value": "postedDateDesc"}],
            "Filters": [],
        }
    }


def parse_opportunities(payload: Any, host: str, tenant: str, board: str) -> list[RawJob]:
    if not isinstance(payload, dict):
        raise ValueError("Unexpected ultipro payload: expected a dict")
    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list):
        raise ValueError("Unexpected ultipro payload: opportunities is not a list")
    jobs: list[RawJob] = []
    for item in opportunities:
        job = _parse_opportunity(item, host, tenant, board)
        if job is not None:
            jobs.append(job)
    return jobs


def _parse_opportunity(item: Any, host: str, tenant: str, board: str) -> RawJob | None:
    if not isinstance(item, dict):
        return None
    title = str(item.get("Title") or "").strip()
    opportunity_id = item.get("Id")
    if not title or not opportunity_id:
        return None
    url = DETAIL_URL.format(
        host=host, tenant=tenant, board=board, opportunity_id=opportunity_id
    )
    description = item.get("BriefDescription")
    description = (
        description if isinstance(description, str) and description.strip() else None
    )
    job_type = "full-time" if item.get("FullTime") is True else None
    return RawJob(
        title=title,
        url=url,
        external_id=str(opportunity_id),
        location=format_location(item.get("Locations")),
        description=description,
        job_type=job_type,
        posted_date=parse_date(item.get("PostedDate")),
    )


def format_location(locations: Any) -> str | None:
    if not isinstance(locations, list) or not locations:
        return None
    entries = [_format_location_entry(loc) for loc in locations]
    joined = [entry for entry in entries if entry]
    return LOCATION_SEPARATOR.join(joined) if joined else None


def _format_location_entry(location: Any) -> str | None:
    if not isinstance(location, dict):
        return None
    address = location.get("Address")
    if isinstance(address, dict):
        formatted = _format_address(address)
        if formatted:
            return formatted
    localized = location.get("LocalizedDescription")
    return str(localized).strip() or None if localized else None


def _format_address(address: dict[str, Any]) -> str | None:
    parts: list[str] = []
    city = address.get("City")
    if city:
        parts.append(str(city))
    state = address.get("State")
    state_code = state.get("Code") if isinstance(state, dict) else None
    if state_code:
        parts.append(str(state_code))
    country = address.get("Country")
    country_code = country.get("Code") if isinstance(country, dict) else None
    if country_code:
        parts.append(str(country_code))
    return ", ".join(parts) if parts else None
