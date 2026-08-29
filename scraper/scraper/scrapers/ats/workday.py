from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import FetchError

if TYPE_CHECKING:
    from scraper.models import Company

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(
    r"^https?://(?P<tenant>[a-z0-9]+)\.(?P<dc>wd\d+)\.myworkdayjobs\.com"
    r"(?:/[a-z]{2}-[a-z]{2})?/(?P<site>[^/?#]+)",
    re.IGNORECASE,
)

HOST_WITH_DC_RE = re.compile(r"^[a-z0-9]{1,63}\.wd\d+$", re.IGNORECASE)

LIST_BODY = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
PAGE_SIZE = 20
MAX_DETAIL_FETCHES = 100

AUDIO_TITLE_RE = re.compile(
    r"(audio|sound|acoustic|dsp|transducer|microphone|loudspeaker|speaker|"
    r"headphone|noise|vibration|nvh|music|recording|mixing|mastering|"
    r"live sound|foh|monitor|amplifier|codec|juce|plugin|synth)",
    re.IGNORECASE,
)

RELATIVE_DATE_RE = re.compile(
    r"posted\s+(?:(?P<today>today)|"
    r"(?P<days>\d+)\s+day(?:s)?\s+ago|"
    r"(?P<weeks>\d+)\s+week(?:s)?\s+ago|"
    r"(?P<hours>\d+)\s+hour(?:s)?\s+ago)",
    re.IGNORECASE,
)


class WorkdayScraper(BaseScraper):
    name = "workday"

    def can_handle(self, company: Company) -> bool:
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    @staticmethod
    def extract_slug(url: str) -> str | None:
        match = URL_PATTERN.match(url.strip())
        if not match:
            return None
        tenant = match.group("tenant")
        site = match.group("site").rstrip("/")
        if site.lower() == "jobs":
            return None
        return f"{tenant}.{match.group('dc')}/{site}"

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        slug = company.ats_slug or self.extract_slug(company.careers_url or "")
        if not slug:
            raise ValueError(f"No workday slug in {company.careers_url}")
        host, site = slug.split("/", 1)
        tenant = host.split(".")[0]
        base = _build_base(company.careers_url or "", host)
        jobs = await self._fetch_all(base, tenant, site)
        should_fetch_details = company.audio_scope == "native"
        await self._fetch_descriptions(
            base, tenant, site, jobs, should_fetch_details
        )
        return jobs

    async def _fetch_all(self, base: str, tenant: str, site: str) -> list[RawJob]:
        jobs: list[RawJob] = []
        offset = 0
        while True:
            body = {**LIST_BODY, "offset": offset}
            url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
            data = await asyncio.to_thread(
                _post_json, url, body, self.settings
            )
            postings = data.get("jobPostings", [])
            if not postings:
                break
            for item in postings:
                parsed = _parse_list_item(item, base)
                if parsed:
                    jobs.append(parsed)
            total = data.get("total", 0)
            offset += len(postings)
            if offset >= total or len(postings) < PAGE_SIZE:
                break
        return jobs

    async def _fetch_descriptions(
        self, base: str, tenant: str, site: str,
        jobs: list[RawJob], force_all: bool,
    ) -> None:
        if force_all:
            fetch_list = jobs[:MAX_DETAIL_FETCHES]
        else:
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
                        _fetch_detail, base, tenant, site,
                        job.external_id, self.settings,
                    )
                    job.description = _extract_description(detail)
                except Exception:
                    pass

        await asyncio.gather(*(fetch_one(j) for j in fetch_list))


def _build_base(url: str, host: str) -> str:
    m = re.match(
        r"^(https?://[a-z0-9]+\.wd\d+\.myworkdayjobs\.com)",
        url.strip(),
        re.IGNORECASE,
    )
    if m:
        return m.group(1)
    if HOST_WITH_DC_RE.match(host):
        return f"https://{host}.myworkdayjobs.com"
    return f"https://{host}.wd1.myworkdayjobs.com"


def _post_json(url: str, body: dict, settings) -> Any:
    import requests as req

    response = req.post(
        url,
        json=body,
        timeout=settings.request_timeout,
        headers={
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} for {url}")
    try:
        return response.json()
    except Exception as exc:
        raise FetchError(f"Invalid JSON from {url}: {exc}") from exc


def _fetch_detail(
    base: str, tenant: str, site: str, external_path: str, settings
) -> Any:
    import requests as req

    url = f"{base}/wday/cxs/{tenant}/{site}{external_path}"
    response = req.get(
        url,
        timeout=settings.request_timeout,
        headers={
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
        },
    )
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code} for {url}")
    return response.json()


def _parse_list_item(item: dict[str, Any], base: str) -> RawJob | None:
    title = (item.get("title") or "").strip()
    external_path = item.get("externalPath") or ""
    if not title or not external_path:
        return None
    url = f"{base}{external_path}"
    job_type = _parse_time_type(item.get("timeType"))
    posted = _parse_relative_date(item.get("postedOn"))
    return RawJob(
        title=title,
        url=url,
        external_id=external_path,
        location=item.get("locationsText"),
        description=None,
        job_type=job_type,
        posted_date=posted,
    )


def _extract_description(detail: dict[str, Any]) -> str | None:
    info = detail.get("jobPostingInfo")
    if not isinstance(info, dict):
        return None
    return info.get("jobDescription")


def _parse_time_type(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        lower = value.lower().strip()
        mapping = {
            "full time": "full-time",
            "part time": "part-time",
            "fixed term": "contract",
            "contract": "contract",
            "temporary": "contract",
            "internship": "internship",
        }
        return mapping.get(lower, lower.replace(" ", "-"))
    return None


def _parse_relative_date(value: str | None) -> date | None:
    if not value:
        return None
    m = RELATIVE_DATE_RE.search(value)
    if not m:
        return None
    today = date.today()
    if m.group("today"):
        return today
    if m.group("hours"):
        return today
    days = m.group("days")
    if days:
        return today - timedelta(days=int(days))
    weeks = m.group("weeks")
    if weeks:
        return today - timedelta(weeks=int(weeks))
    return None
