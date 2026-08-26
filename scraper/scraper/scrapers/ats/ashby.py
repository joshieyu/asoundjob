from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://jobs\.ashbyhq\.com/(?P<slug>[^/?#]+)",
    re.IGNORECASE,
)

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"


class AshbyScraper(BaseScraper):
    name = "ashby"

    def can_handle(self, company: Company) -> bool:
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    @staticmethod
    def extract_slug(url: str) -> str | None:
        match = URL_PATTERN.match(url.strip())
        return match.group("slug") if match else None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        slug = self.extract_slug(company.careers_url or "")
        if not slug:
            raise ValueError(f"No ashby slug in {company.careers_url}")
        data = await asyncio.to_thread(
            fetch_json, API_URL.format(slug=slug), self.settings
        )
        return parse_jobs(data)


def parse_jobs(data: Any) -> list[RawJob]:
    if not isinstance(data, dict):
        raise ValueError("Unexpected ashby payload: expected a dict")
    jobs_raw = data.get("jobs") or data.get("jobBoard") or []
    if not isinstance(jobs_raw, list):
        raise ValueError("Unexpected ashby jobs field: expected a list")
    jobs: list[RawJob] = []
    for item in jobs_raw:
        title = (item.get("title") or "").strip()
        url = item.get("jobUrl") or item.get("url") or ""
        if not title or not url:
            continue
        location_obj = item.get("location") or {}
        location = None
        if isinstance(location_obj, str):
            location = location_obj
        elif isinstance(location_obj, dict):
            location = location_obj.get("name") or location_obj.get("city")
        emp_type = item.get("employmentType")
        job_type = _normalize_employment_type(emp_type)
        description = item.get("descriptionHtml") or item.get("descriptionPlain")
        jobs.append(
            RawJob(
                title=title,
                url=url,
                external_id=str(item["id"]) if item.get("id") else None,
                location=location,
                description=description,
                job_type=job_type,
                posted_date=parse_date(item.get("publishedAt")),
            )
        )
    return jobs


def _normalize_employment_type(value: str | None) -> str | None:
    if not value:
        return None
    lower = value.lower().strip()
    mapping = {
        "fulltime": "full-time",
        "full_time": "full-time",
        "full-time": "full-time",
        "parttime": "part-time",
        "part_time": "part-time",
        "part-time": "part-time",
        "contract": "contract",
        "internship": "internship",
        "temporary": "contract",
    }
    return mapping.get(lower, lower.replace(" ", "-"))
