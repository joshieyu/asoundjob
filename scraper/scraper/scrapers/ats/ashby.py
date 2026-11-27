from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_json, parse_date
from scraper.scrapers.keyword_scope import scope_to_keywords

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://jobs\.ashbyhq\.com/(?P<slug>[^/?#]+)",
    re.IGNORECASE,
)

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
HOURS_PER_YEAR = 2080
MAX_ANNUAL_SALARY = 5_000_000


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
        slug = company.ats_slug or self.extract_slug(company.careers_url or "")
        if not slug:
            raise ValueError(f"No ashby slug in {company.careers_url}")
        data = await asyncio.to_thread(
            fetch_json, API_URL.format(slug=slug), self.settings
        )
        return scope_to_keywords(parse_jobs(data), company.careers_url or "")


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
        salary_min, salary_max, currency = compensation(item.get("compensation"))
        jobs.append(
            RawJob(
                title=title,
                url=url,
                external_id=str(item["id"]) if item.get("id") else None,
                location=location,
                description=description,
                job_type=job_type,
                posted_date=parse_date(item.get("publishedAt")),
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=currency,
            )
        )
    return jobs


def compensation(value: Any) -> tuple[int | None, int | None, str | None]:
    if not isinstance(value, dict):
        return None, None, None
    components = value.get("summaryComponents")
    if not isinstance(components, list):
        return None, None, None
    for component in components:
        if not isinstance(component, dict) or component.get("compensationType") != "Salary":
            continue
        multiplier = _annual_multiplier(component.get("interval"))
        if multiplier is None:
            continue
        low = _annual(component.get("minValue"), multiplier)
        high = _annual(component.get("maxValue"), multiplier)
        if low is None and high is None:
            continue
        if low is not None and high is not None and high < low:
            continue
        currency = component.get("currencyCode")
        return low, high, currency if isinstance(currency, str) and currency else None
    return None, None, None


def _annual_multiplier(interval: Any) -> int | None:
    if interval == "1 YEAR":
        return 1
    if interval == "1 HOUR":
        return HOURS_PER_YEAR
    return None


def _annual(value: Any, multiplier: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    annual = int(round(value * multiplier))
    return annual if annual <= MAX_ANNUAL_SALARY else None


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
