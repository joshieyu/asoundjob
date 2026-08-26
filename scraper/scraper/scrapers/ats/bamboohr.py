from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?P<sub>[a-z0-9-]+)\.bamboohr\.com/careers",
    re.IGNORECASE,
)

LIST_URL = "https://{sub}.bamboohr.com/careers/list"
DETAIL_URL = "https://{sub}.bamboohr.com/careers/{job_id}/detail"


class BambooHRScraper(BaseScraper):
    name = "bamboohr"

    def can_handle(self, company: Company) -> bool:
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    @staticmethod
    def extract_slug(url: str) -> str | None:
        match = URL_PATTERN.match(url.strip())
        return match.group("sub") if match else None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        sub = self.extract_slug(company.careers_url or "")
        if not sub:
            raise ValueError(f"No bamboohr subdomain in {company.careers_url}")
        data = await asyncio.to_thread(
            fetch_json, LIST_URL.format(sub=sub), self.settings
        )
        jobs = parse_list(data, sub)
        await self._fetch_descriptions(jobs, sub)
        return jobs

    async def _fetch_descriptions(
        self, jobs: list[RawJob], sub: str
    ) -> None:
        sem = asyncio.Semaphore(self.settings.http_concurrency)

        async def fetch_one(job: RawJob) -> None:
            if not job.external_id:
                return
            async with sem:
                try:
                    detail = await asyncio.to_thread(
                        fetch_json,
                        DETAIL_URL.format(sub=sub, job_id=job.external_id),
                        self.settings,
                    )
                    job.description = _extract_description(detail)
                except Exception:
                    pass

        await asyncio.gather(*(fetch_one(j) for j in jobs))


def parse_list(data: Any, sub: str) -> list[RawJob]:
    if not isinstance(data, dict):
        raise ValueError("Unexpected bamboohr payload: expected a dict")
    result = data.get("result")
    if not isinstance(result, list):
        raise ValueError("Unexpected bamboohr result field: expected a list")
    jobs: list[RawJob] = []
    for item in result:
        title = (item.get("jobOpeningName") or "").strip()
        if not title:
            continue
        job_id = str(item.get("id") or "").strip()
        if not job_id:
            continue
        url = f"https://{sub}.bamboohr.com/careers/{job_id}"
        location = _format_location(item.get("location") or item.get("atsLocation"))
        emp_label = item.get("employmentStatusLabel") or item.get("employmentType")
        job_type = _normalize_employment_type(emp_label)
        remote = bool(item.get("isRemote"))
        jobs.append(
            RawJob(
                title=title,
                url=url,
                external_id=job_id,
                location=location,
                description=None,
                job_type=job_type,
                posted_date=parse_date(item.get("datePosted")),
                remote_hint=remote,
            )
        )
    return jobs


def _format_location(loc: Any) -> str | None:
    if isinstance(loc, str):
        return loc or None
    if not isinstance(loc, dict):
        return None
    city = loc.get("city")
    country = loc.get("addressCountry") or loc.get("country")
    if city and country:
        return f"{city}, {country}"
    return city or country or None


def _extract_description(detail: dict[str, Any]) -> str | None:
    result = detail.get("result")
    if not isinstance(result, dict):
        return None
    job = result.get("jobOpening")
    if not isinstance(job, dict):
        return None
    return job.get("description")


def _normalize_employment_type(label: str | None) -> str | None:
    if not label:
        return None
    lower = label.lower().strip()
    mapping = {
        "full-time": "full-time",
        "full time": "full-time",
        "regular full time": "full-time",
        "part-time": "part-time",
        "part time": "part-time",
        "contractor": "contract",
        "contract": "contract",
        "temporary": "contract",
        "internship": "internship",
    }
    return mapping.get(lower, lower.replace(" ", "-"))
