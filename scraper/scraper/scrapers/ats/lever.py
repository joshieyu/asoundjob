from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any, Optional

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?:[a-z0-9-]{1,40}\.){0,4}jobs\.(?P<region>eu\.)?lever\.co/(?P<slug>[^/?#]{1,120})",
    re.IGNORECASE,
)

API_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"
EU_API_URL = "https://api.eu.lever.co/v0/postings/{slug}?mode=json"


def api_url_for(careers_url: str, slug: str) -> str:
    match = URL_PATTERN.match((careers_url or "").strip())
    if match and match.group("region"):
        return EU_API_URL.format(slug=slug)
    return API_URL.format(slug=slug)


class LeverScraper(BaseScraper):
    name = "lever"

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
            raise ValueError(f"No lever slug in {company.careers_url}")
        url = api_url_for(company.careers_url or "", slug)
        data = await asyncio.to_thread(fetch_json, url, self.settings)
        return parse_postings(data)


def _full_description(item: dict) -> Optional[str]:
    parts = [item.get("description") or item.get("descriptionPlain") or ""]
    for section in item.get("lists") or []:
        if not isinstance(section, dict):
            continue
        heading = (section.get("text") or "").strip()
        content = (section.get("content") or "").strip()
        if heading:
            parts.append(f"<h3>{heading}</h3>")
        if content:
            parts.append(content)
    parts.append(item.get("additional") or "")
    joined = "\n".join(p for p in parts if p)
    return joined or None


def parse_postings(data: Any) -> list[RawJob]:
    if not isinstance(data, list):
        raise ValueError("Unexpected lever payload: expected a list")
    jobs: list[RawJob] = []
    for item in data:
        title = (item.get("text") or "").strip()
        url = item.get("hostedUrl") or item.get("applyUrl") or ""
        if not title or not url:
            continue
        categories = item.get("categories") or {}
        commitment = categories.get("commitment")
        job_type = commitment.lower().replace("_", "-") if commitment else None
        jobs.append(
            RawJob(
                title=title,
                url=url,
                external_id=str(item["id"]) if item.get("id") is not None else None,
                location=categories.get("location"),
                description=_full_description(item),
                job_type=job_type,
                posted_date=parse_date(item.get("createdAt")),
            )
        )
    return jobs
