from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?P<slug>[a-z0-9-]+)\.recruitee\.com",
    re.IGNORECASE,
)

API_URL = "https://{slug}.recruitee.com/api/offers"


class RecruiteeScraper(BaseScraper):
    name = "recruitee"

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
            raise ValueError(f"No recruitee slug in {company.careers_url}")
        data = await asyncio.to_thread(
            fetch_json, API_URL.format(slug=slug), self.settings
        )
        return parse_offers(data)


def parse_offers(data: Any) -> list[RawJob]:
    if not isinstance(data, dict):
        raise ValueError("Unexpected recruitee payload: expected a dict")
    offers = data.get("offers", [])
    if not isinstance(offers, list):
        raise ValueError("Unexpected recruitee offers field: expected a list")
    jobs: list[RawJob] = []
    for item in offers:
        title = (item.get("title") or "").strip()
        url = item.get("careers_url") or item.get("url") or ""
        if not title or not url:
            continue
        location_parts: list[str] = []
        city = item.get("city")
        country = item.get("country")
        if city:
            location_parts.append(city)
        if country:
            location_parts.append(country)
        location = ", ".join(location_parts) if location_parts else None
        description = item.get("description") or item.get("requirements")
        emp_code = item.get("employment_type_code")
        job_type = _normalize_employment_type(emp_code)
        remote = bool(item.get("remote"))
        salary_obj = item.get("salary") or {}
        salary_text = _format_salary(salary_obj)
        if salary_text and description:
            description = f"{description}\n\nSalary: {salary_text}"
        elif salary_text:
            description = f"Salary: {salary_text}"
        jobs.append(
            RawJob(
                title=title,
                url=url,
                external_id=str(item["id"]) if item.get("id") else item.get("slug"),
                location=location,
                description=description,
                job_type=job_type,
                posted_date=parse_date(item.get("published_at")),
                remote_hint=remote,
            )
        )
    return jobs


def _format_salary(salary_obj: Any) -> str:
    if not isinstance(salary_obj, dict):
        return ""
    smin = salary_obj.get("min")
    smax = salary_obj.get("max")
    currency = salary_obj.get("currency") or ""
    if not smin and not smax:
        return ""
    parts: list[str] = []
    if currency:
        parts.append(currency)
    if smin and smax:
        parts.append(f"{int(smin):,}–{int(smax):,}")
    elif smin:
        parts.append(f"{int(smin):,}")
    elif smax:
        parts.append(f"{int(smax):,}")
    return " ".join(parts)


def _normalize_employment_type(code: str | None) -> str | None:
    if not code:
        return None
    lower = code.lower().strip()
    mapping = {
        "full_time": "full-time",
        "fulltime": "full-time",
        "part_time": "part-time",
        "parttime": "part-time",
        "contract": "contract",
        "temporary": "contract",
        "internship": "internship",
    }
    return mapping.get(lower, lower.replace(" ", "-"))
