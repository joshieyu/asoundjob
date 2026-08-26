from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from scraper.scrapers.base import BaseScraper, RawJob
from scraper.scrapers.fetch import fetch_html, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?:apply\.workable\.com/(?P<path_slug>[^/?#]+)"
    r"|(?P<sub_slug>[a-z0-9-]+)\.workable\.com)",
    re.IGNORECASE,
)

JOBS_MD_PATH = "https://apply.workable.com/{slug}/jobs.md"
DETAIL_MD_PATH = "https://apply.workable.com/{slug}/jobs/view/{job_id}.md"

TABLE_ROW = re.compile(
    r"^\|\s*(?P<title>[^|]+)\|[^|]*\|(?P<location>[^|]*)\|(?P<job_type>[^|]*)\|"
    r"(?P<salary>[^|]*)\|(?P<posted>[^|]*)\|\s*\[View\]\((?P<url>[^)]+)\)",
    re.MULTILINE,
)


class WorkableScraper(BaseScraper):
    name = "workable"

    def can_handle(self, company: Company) -> bool:
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    @staticmethod
    def extract_slug(url: str) -> str | None:
        match = URL_PATTERN.match(url.strip())
        if not match:
            return None
        slug = match.group("path_slug") or match.group("sub_slug")
        return slug.rstrip("/") if slug else None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        slug = company.ats_slug or self.extract_slug(company.careers_url or "")
        if not slug:
            raise ValueError(f"No workable slug in {company.careers_url}")
        md = await asyncio.to_thread(
            fetch_html, JOBS_MD_PATH.format(slug=slug), self.settings
        )
        jobs = parse_jobs_md(md, slug)
        await self._fetch_descriptions(jobs, slug)
        return jobs

    async def _fetch_descriptions(
        self, jobs: list[RawJob], slug: str
    ) -> None:
        sem = asyncio.Semaphore(self.settings.http_concurrency)

        async def fetch_one(job: RawJob) -> None:
            job_id = _extract_job_id(job.url)
            if not job_id:
                return
            async with sem:
                try:
                    detail = await asyncio.to_thread(
                        fetch_html,
                        DETAIL_MD_PATH.format(slug=slug, job_id=job_id),
                        self.settings,
                    )
                    job.description = _extract_description(detail)
                except Exception:
                    pass

        await asyncio.gather(*(fetch_one(j) for j in jobs))


def parse_jobs_md(md: str, slug: str) -> list[RawJob]:
    jobs: list[RawJob] = []
    for m in TABLE_ROW.finditer(md):
        title = m.group("title").strip()
        url = m.group("url").strip()
        if not title or not url:
            continue
        location = m.group("location").strip() or None
        if location == "—":
            location = None
        job_type = m.group("job_type").strip() or None
        if job_type == "—":
            job_type = None
        salary_text = m.group("salary").strip()
        salary_min, salary_max, currency = _parse_salary(salary_text)
        posted = m.group("posted").strip()
        posted_date = parse_date(posted) if posted and posted != "—" else None
        job_id = _extract_job_id(url)
        jobs.append(
            RawJob(
                title=title,
                url=url.replace(".md", ""),
                external_id=job_id,
                location=location,
                description=None,
                job_type=_normalize_job_type(job_type),
                posted_date=posted_date,
            )
        )
    return jobs


def _extract_job_id(url: str) -> str | None:
    m = re.search(r"/jobs/view/([A-F0-9]+)(?:\.md)?", url, re.IGNORECASE)
    return m.group(1) if m else None


def _extract_description(md: str) -> str:
    parts = md.split("## Description", 1)
    if len(parts) == 2:
        body = parts[1]
        body = re.sub(r"^---\n.*$", "", body, flags=re.MULTILINE | re.DOTALL)
        body = re.sub(r"Powered by \[.*$", "", body)
        return body.strip()
    idx = md.find("\n## ")
    if idx >= 0:
        return md[idx:].strip()
    return md.strip()


def _parse_salary(text: str) -> tuple[int | None, int | None, str | None]:
    text = text.strip()
    if not text or text == "—":
        return None, None, None
    m = re.match(
        r"(?P<curr>[A-Z]{3})\s*(?P<min>[\d,]+)\s*[–-]\s*(?P<max>[\d,]+)",
        text,
    )
    if m:
        currency = m.group("curr")
        smin = int(m.group("min").replace(",", ""))
        smax = int(m.group("max").replace(",", ""))
        return smin, smax, currency
    return None, None, None


def _normalize_job_type(text: str | None) -> str | None:
    if not text:
        return None
    lower = text.lower().strip()
    mapping = {
        "full-time": "full-time",
        "part-time": "part-time",
        "contract": "contract",
        "contractor": "contract",
        "internship": "internship",
        "temporary": "contract",
    }
    return mapping.get(lower, lower.replace(" ", "-"))
