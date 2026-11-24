from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, quote, urlparse

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError, listing
from scraper.scrapers.fetch import FetchError, fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?P<host>[a-z0-9-]+\.fa(?:\.[a-z0-9-]+)?\.oraclecloud\.com)"
    r"/hcmUI/CandidateExperience/(?P<lang>[a-z]{2}(?:-[A-Za-z]{2})?)/sites/(?P<site>[A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

API_ROOT = "https://{host}/hcmRestApi/resources/latest"
LIST_PATH = (
    "/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList"
    "&finder=findReqs;siteNumber={site},{keyword}limit={limit},offset={offset},"
    "sortBy=POSTING_DATES_DESC"
)
DETAIL_PATH = (
    "/recruitingCEJobRequisitionDetails?expand=all&onlyData=true"
    '&finder=ById;Id="{job_id}",siteNumber={site}'
)
JOB_URL = "https://{host}/hcmUI/CandidateExperience/{lang}/sites/{site}/job/{job_id}"

PAGE_SIZE = 25
MAX_PAGES = 20
MAX_DETAIL_FETCHES = 60
DETAIL_CONCURRENCY = 6
DESCRIPTION_FIELDS = (
    "ExternalDescriptionStr",
    "ExternalResponsibilitiesStr",
    "ExternalQualificationsStr",
)


class OracleScraper(BaseScraper):
    name = "oracle"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "oracle":
            return True
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        careers_url = (company.careers_url or "").strip()
        match = URL_PATTERN.match(careers_url)
        if not match:
            raise ScrapeError(f"No oracle candidate experience site in {company.careers_url}")
        host = match.group("host").lower()
        lang = match.group("lang")
        site = match.group("site")
        keyword = (parse_qs(urlparse(careers_url).query).get("keyword") or [""])[0].strip()
        keyword_part = f'keyword="{quote(keyword)}",' if keyword else ""

        jobs = listing()
        seen: set[str] = set()
        for page in range(MAX_PAGES):
            url = API_ROOT.format(host=host) + LIST_PATH.format(
                site=site, keyword=keyword_part, limit=PAGE_SIZE, offset=page * PAGE_SIZE
            )
            payload = await asyncio.to_thread(fetch_json, url, self.settings)
            page_jobs, total = parse_requisitions(payload, host, lang, site)
            new_jobs = [job for job in page_jobs if job.external_id not in seen]
            seen.update(job.external_id or "" for job in new_jobs)
            jobs.extend(new_jobs)
            if not new_jobs or total is None or len(seen) >= total:
                break

        semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
        await asyncio.gather(
            *(self._describe(job, host, site, semaphore) for job in jobs[:MAX_DETAIL_FETCHES])
        )
        return jobs

    async def _describe(
        self, job: RawJob, host: str, site: str, semaphore: asyncio.Semaphore
    ) -> None:
        url = API_ROOT.format(host=host) + DETAIL_PATH.format(job_id=job.external_id, site=site)
        async with semaphore:
            try:
                payload = await asyncio.to_thread(fetch_json, url, self.settings)
            except FetchError:
                return
        description = parse_detail_description(payload)
        if description:
            job.description = description


def parse_requisitions(
    payload: Any, host: str, lang: str, site: str
) -> tuple[list[RawJob], int | None]:
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise ScrapeError("Unexpected oracle payload: items is not a list")
    if not items:
        return [], 0
    search = items[0] if isinstance(items[0], dict) else {}
    rows = search.get("requisitionList")
    if not isinstance(rows, list):
        raise ScrapeError("Unexpected oracle payload: requisitionList is not a list")
    total = search.get("TotalJobsCount")
    jobs: list[RawJob] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        job_id = str(row.get("Id") or "").strip()
        title = str(row.get("Title") or "").strip()
        if not job_id or not title:
            continue
        location = str(row.get("PrimaryLocation") or "").strip() or None
        jobs.append(
            RawJob(
                title=title,
                url=JOB_URL.format(host=host, lang=lang, site=site, job_id=job_id),
                external_id=job_id,
                location=location,
                description=row.get("ShortDescriptionStr") or None,
                posted_date=parse_date(row.get("PostedDate")),
                remote_hint=str(row.get("WorkplaceTypeCode") or "").upper() == "ORA_REMOTE",
            )
        )
    return jobs, total if isinstance(total, int) else None


def parse_detail_description(payload: Any) -> str | None:
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        return None
    detail = items[0]
    parts = [str(detail.get(field) or "").strip() for field in DESCRIPTION_FIELDS]
    text = "\n".join(part for part in parts if part)
    return text or None
