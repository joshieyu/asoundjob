from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

CID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

LIST_URL = (
    "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/"
    "staffing/v1/job-requisitions?cid={cid}&$top={top}&$skip={skip}"
)
DETAIL_URL = (
    "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/"
    "staffing/v1/job-requisitions/{item_id}?cid={cid}"
)
JOB_URL = (
    "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html"
    "?cid={cid}&ccId=19000101_000001&type=MP&lang=en_US&jobId={item_id}"
)
PAGE_SIZE = 100
MAX_PAGES = 10
MAX_DETAIL_FETCHES = 100


class AdpScraper(BaseScraper):
    name = "adp"

    def can_handle(self, company: Company) -> bool:
        if not company.careers_url:
            return False
        url = company.careers_url.strip()
        if urlsplit(url).netloc.lower() != "workforcenow.adp.com":
            return False
        return self.extract_slug(url) is not None

    @staticmethod
    def extract_slug(url: str) -> str | None:
        query = urlsplit(url.strip()).query
        values = parse_qs(query).get("cid")
        if not values:
            return None
        cid = values[0]
        return cid if CID_RE.match(cid) else None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        cid = company.ats_slug or self.extract_slug(company.careers_url or "")
        if not cid:
            raise ValueError(f"No adp cid in {company.careers_url}")
        jobs = await self._fetch_all(cid)
        await self._fetch_descriptions(jobs, cid)
        return jobs

    async def _fetch_all(self, cid: str) -> list[RawJob]:
        jobs: list[RawJob] = []
        for page in range(MAX_PAGES):
            skip = page * PAGE_SIZE
            url = LIST_URL.format(cid=cid, top=PAGE_SIZE, skip=skip)
            data = await asyncio.to_thread(fetch_json, url, self.settings)
            items = requisitions(data)
            if not items:
                break
            for item in items:
                parsed = parse_requisition(item, cid)
                if parsed is not None:
                    jobs.append(parsed)
            if len(items) < PAGE_SIZE:
                break
        return jobs

    async def _fetch_descriptions(self, jobs: list[RawJob], cid: str) -> None:
        sem = asyncio.Semaphore(self.settings.http_concurrency)

        async def fetch_one(job: RawJob) -> None:
            if not job.external_id:
                return
            async with sem:
                try:
                    detail = await asyncio.to_thread(
                        fetch_json,
                        DETAIL_URL.format(item_id=job.external_id, cid=cid),
                        self.settings,
                    )
                    job.description = extract_description(detail)
                except Exception:
                    pass

        await asyncio.gather(*(fetch_one(j) for j in jobs[:MAX_DETAIL_FETCHES]))


def requisitions(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise ValueError("Unexpected adp payload: expected a dict")
    items = data.get("jobRequisitions", [])
    if not isinstance(items, list):
        raise ValueError("Unexpected adp jobRequisitions field: expected a list")
    return items


def parse_requisition(item: dict[str, Any], cid: str) -> RawJob | None:
    title = (item.get("requisitionTitle") or "").strip()
    item_id = item.get("itemID")
    if not title or not item_id:
        return None
    return RawJob(
        title=title,
        url=JOB_URL.format(cid=cid, item_id=item_id),
        external_id=str(item_id),
        location=format_location(item.get("requisitionLocations")),
        description=None,
        posted_date=parse_date(item.get("postDate")),
    )


def format_location(locations: Any) -> str | None:
    if not isinstance(locations, list) or not locations:
        return None
    first = locations[0]
    if not isinstance(first, dict):
        return None
    address = first.get("address")
    if not isinstance(address, dict):
        return None
    city = address.get("cityName")
    return city or None


def extract_description(detail: Any) -> str | None:
    if not isinstance(detail, dict):
        return None
    raw_html = detail.get("requisitionDescription")
    if not raw_html:
        return None
    text = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)
    return text or None
