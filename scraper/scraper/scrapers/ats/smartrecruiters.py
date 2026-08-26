from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_json, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://careers\.smartrecruiters\.com/(?P<slug>[^/?#]+)",
    re.IGNORECASE,
)

API_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
DETAIL_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings/{job_id}"
PAGE_SIZE = 100
MAX_DETAIL_FETCHES = 100

AUDIO_TITLE_RE = re.compile(
    r"(audio|sound|acoustic|dsp|transducer|microphone|loudspeaker|speaker|"
    r"headphone|noise|vibration|nvh|music|recording|mixing|mastering|"
    r"live sound|foh|monitor|amplifier|codec|juce|plugin|synth)",
    re.IGNORECASE,
)


class SmartRecruitersScraper(BaseScraper):
    name = "smartrecruiters"

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
            raise ValueError(f"No smartrecruiters slug in {company.careers_url}")
        jobs = await self._fetch_all(slug)
        await self._fetch_descriptions(jobs, slug)
        return jobs

    async def _fetch_all(self, slug: str) -> list[RawJob]:
        jobs: list[RawJob] = []
        offset = 0
        while True:
            url = f"{API_URL.format(slug=slug)}?limit={PAGE_SIZE}&offset={offset}"
            data = await asyncio.to_thread(fetch_json, url, self.settings)
            content = data.get("content", [])
            if not content:
                break
            for item in content:
                parsed = _parse_list_item(item)
                if parsed is not None:
                    jobs.append(parsed)
            total = data.get("totalFound", 0)
            offset += len(content)
            if offset >= total or len(content) < PAGE_SIZE:
                break
        return jobs

    async def _fetch_descriptions(
        self, jobs: list[RawJob], slug: str
    ) -> None:
        fetch_list = jobs[:MAX_DETAIL_FETCHES]
        if len(jobs) > MAX_DETAIL_FETCHES:
            fetch_list = [
                j for j in jobs if AUDIO_TITLE_RE.search(j.title)
            ][:MAX_DETAIL_FETCHES]

        sem = asyncio.Semaphore(self.settings.http_concurrency)

        async def fetch_one(job: RawJob) -> None:
            if not job.external_id:
                return
            async with sem:
                try:
                    detail = await asyncio.to_thread(
                        fetch_json,
                        DETAIL_URL.format(slug=slug, job_id=job.external_id),
                        self.settings,
                    )
                    job.description = _extract_detail_description(detail)
                except Exception:
                    pass

        await asyncio.gather(*(fetch_one(j) for j in fetch_list))


def _parse_list_item(item: dict[str, Any]) -> RawJob | None:
    title = (item.get("name") or "").strip()
    if not title:
        return None
    job_id = item.get("id")
    external_id = str(job_id) if job_id is not None else None
    posting_url = item.get("ref") or ""
    if not posting_url:
        posting_url = f"https://careers.smartrecruiters.com/{external_id}"
    location_obj = item.get("location") or {}
    location = _format_location(location_obj)
    emp_type = item.get("typeOfEmployment") or {}
    job_type = None
    if isinstance(emp_type, dict):
        job_type = _normalize_employment_type(emp_type.get("label"))
    return RawJob(
        title=title,
        url=posting_url,
        external_id=external_id,
        location=location,
        description=None,
        job_type=job_type,
        posted_date=parse_date(item.get("releasedDate")),
    )


def _format_location(loc: Any) -> str | None:
    if isinstance(loc, str):
        return loc or None
    if not isinstance(loc, dict):
        return None
    city = loc.get("city")
    country = loc.get("country")
    if city and country:
        return f"{city}, {country}"
    return city or country or None


def _extract_detail_description(detail: dict[str, Any]) -> str | None:
    job_ad = detail.get("jobAd")
    if not isinstance(job_ad, dict):
        return None
    sections = job_ad.get("sections")
    if not isinstance(sections, dict):
        return None
    parts: list[str] = []
    for key in ("jobDescription", "companyDescription", "qualifications"):
        section = sections.get(key)
        if isinstance(section, dict):
            text = section.get("text")
            if text:
                parts.append(text)
    return "\n\n".join(parts) if parts else None


def _normalize_employment_type(label: str | None) -> str | None:
    if not label:
        return None
    lower = label.lower().strip()
    mapping = {
        "full-time": "full-time",
        "part-time": "part-time",
        "contract": "contract",
        "temporary": "contract",
        "internship": "internship",
    }
    return mapping.get(lower, lower)
