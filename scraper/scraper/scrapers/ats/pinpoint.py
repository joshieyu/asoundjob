from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?P<slug>[a-z0-9-]+)\.pinpointhq\.com",
    re.IGNORECASE,
)

API_PATH = "/postings.json"


class PinpointScraper(BaseScraper):
    name = "pinpoint"

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
            raise ValueError(f"No pinpoint slug in {company.careers_url}")
        base = f"https://{slug}.pinpointhq.com"
        data = await asyncio.to_thread(
            fetch_json, f"{base}{API_PATH}", self.settings
        )
        return parse_postings(data)


def parse_postings(data: Any) -> list[RawJob]:
    if not isinstance(data, dict):
        raise ValueError("Unexpected pinpoint payload: expected a dict")
    postings = data.get("data", [])
    if not isinstance(postings, list):
        raise ValueError("Unexpected pinpoint data field: expected a list")
    jobs: list[RawJob] = []
    for item in postings:
        title = (item.get("title") or "").strip()
        url = item.get("url") or ""
        if not title or not url:
            continue
        location_obj = item.get("location") or {}
        location = None
        if isinstance(location_obj, str):
            location = location_obj
        elif isinstance(location_obj, dict):
            location = location_obj.get("name") or location_obj.get("city")
        description_parts: list[str] = []
        desc = item.get("description")
        if desc:
            description_parts.append(desc)
        resp = item.get("key_responsibilities")
        if resp:
            description_parts.append(resp)
        skills = item.get("skills_knowledge_expertise")
        if skills:
            description_parts.append(skills)
        description = "\n\n".join(description_parts) if description_parts else None
        emp_type = item.get("employment_type")
        job_type = _normalize_employment_type(emp_type)
        workplace = item.get("workplace_type")
        remote = workplace == "remote" if workplace else False
        external_id = str(item.get("id") or "")
        jobs.append(
            RawJob(
                title=title,
                url=url,
                external_id=external_id or None,
                location=location,
                description=description,
                job_type=job_type,
                posted_date=parse_date(item.get("deadline_at")),
                remote_hint=remote,
            )
        )
    return jobs


def _normalize_employment_type(value: str | None) -> str | None:
    if not value:
        return None
    lower = value.lower().strip()
    mapping = {
        "full_time": "full-time",
        "full-time": "full-time",
        "part_time": "part-time",
        "part-time": "part-time",
        "contract": "contract",
        "temporary": "contract",
        "internship": "internship",
    }
    return mapping.get(lower, lower.replace(" ", "-"))
