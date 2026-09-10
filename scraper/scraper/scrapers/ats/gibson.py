from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import parse_date, post_json

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://www\.gibson\.com/apps/adpJobRequisition/?(?:\?[^\s]{0,2000})?$",
    re.IGNORECASE,
)

REQUISITION_URL = "https://www.gibson.com/apps/adpJobRequisition/"

OPEN_STATUS = "ON"

JOB_ID_RE = re.compile(r"[?&]jobId=", re.IGNORECASE)


class GibsonScraper(BaseScraper):
    name = "gibson"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "gibson":
            return True
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        response = await asyncio.to_thread(
            post_json, REQUISITION_URL, {}, self.settings
        )
        if not isinstance(response, dict):
            raise ScrapeError("Unexpected gibson response: not a dict")
        if not response.get("success"):
            raise ScrapeError("Unexpected gibson response: success is not truthy")
        data = response.get("data")
        requisitions = data.get("jobRequisitions") if isinstance(data, dict) else None
        if not isinstance(requisitions, list):
            raise ScrapeError(
                "Unexpected gibson response: data.jobRequisitions is not a list"
            )
        jobs: list[RawJob] = []
        for requisition in requisitions:
            if not isinstance(requisition, dict):
                continue
            job = _parse_requisition(requisition, company)
            if job is not None:
                jobs.append(job)
        return jobs


def _parse_requisition(requisition: dict, company: Company) -> RawJob | None:
    if _status_code(requisition) != OPEN_STATUS:
        return None
    posting = _first_posting_instruction(requisition)
    name_code = posting.get("nameCode")
    name_code = name_code if isinstance(name_code, dict) else {}
    title = name_code.get("codeValue")
    if not isinstance(title, str) or not title.strip():
        return None
    description = name_code.get("longName")
    if not isinstance(description, str) or not description.strip():
        description = None
    external_id = requisition.get("itemID")
    external_id = str(external_id) if external_id is not None else None
    return RawJob(
        title=title,
        url=_job_url(requisition, company),
        external_id=external_id,
        location=_location(requisition),
        description=description,
        posted_date=parse_date(posting.get("postDate")),
    )


def _first_posting_instruction(requisition: dict) -> dict:
    postings = requisition.get("postingInstructions")
    if isinstance(postings, list) and postings and isinstance(postings[0], dict):
        return postings[0]
    return {}


def _status_code(requisition: dict) -> str | None:
    status = requisition.get("requisitionStatusCode")
    if isinstance(status, dict):
        value = status.get("codeValue")
        return value if isinstance(value, str) else None
    return None


def _location(requisition: dict) -> str | None:
    locations = requisition.get("requisitionLocations")
    if not isinstance(locations, list) or not locations:
        return None
    first = locations[0]
    if not isinstance(first, dict):
        return None
    address = first.get("address")
    if not isinstance(address, dict):
        return None
    parts: list[str] = []
    city = address.get("cityName")
    if isinstance(city, str) and city.strip():
        parts.append(city.strip())
    region_raw = address.get("countrySubdivisionLevel1")
    if isinstance(region_raw, dict):
        region = region_raw.get("codeValue")
        if isinstance(region, str) and region.strip():
            parts.append(region.strip())
    country = address.get("countryCode")
    if isinstance(country, str) and country.strip():
        parts.append(country.strip())
    return ", ".join(parts) if parts else None


def _job_url(requisition: dict, company: Company) -> str:
    hrefs: list[str] = []
    links = requisition.get("links")
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            href = link.get("href")
            if isinstance(href, str) and _is_http_url(href):
                hrefs.append(href)
    for href in hrefs:
        if JOB_ID_RE.search(href):
            return href
    if hrefs:
        return hrefs[0]
    return (company.careers_url or "").strip()


def _is_http_url(value: str) -> bool:
    return urlsplit(value).scheme.lower() in ("http", "https")
