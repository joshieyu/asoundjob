from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?:[a-z0-9-]+\.)*(?:(?:job-)?boards)\.greenhouse\.io/"
    r"(?P<slug>[^/?#]+)",
    re.IGNORECASE,
)

API_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


class GreenhouseScraper(BaseScraper):
    name = "greenhouse"

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
            raise ValueError(f"No greenhouse slug in {company.careers_url}")
        data = await asyncio.to_thread(
            fetch_json, API_URL.format(slug=slug), self.settings
        )
        return parse_board(data)


def parse_board(data: dict) -> list[RawJob]:
    jobs: list[RawJob] = []
    for item in data.get("jobs", []):
        title = (item.get("title") or "").strip()
        url = item.get("absolute_url") or ""
        if not title or not url:
            continue
        location_obj = item.get("location") or {}
        location = location_obj.get("name") if isinstance(location_obj, dict) else None
        content = item.get("content")
        description = decode_content(content)
        jobs.append(
            RawJob(
                title=title,
                url=url,
                external_id=str(item["id"]) if item.get("id") is not None else None,
                location=location,
                description=description,
                job_type=None,
                posted_date=parse_date(item.get("updated_at")),
            )
        )
    return jobs


def decode_content(content: str | None) -> str | None:
    if not content:
        return None
    import base64

    try:
        return base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception:
        return content
