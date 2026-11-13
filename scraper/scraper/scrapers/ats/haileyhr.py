from __future__ import annotations

import asyncio
import json
import re
from time import monotonic
from typing import TYPE_CHECKING, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError, company_budget, listing
from scraper.scrapers.fetch import fetch_html

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://(?P<slug>[a-z0-9-]{1,63})\.careers\.haileyhr\.app",
    re.IGNORECASE,
)
JOB_PATH = re.compile(r"/job/(?:[0-9a-f-]{36}/){2}(?P<id>[0-9a-f-]{36})", re.IGNORECASE)
PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.){0,500000}")\]\)')
TEXT_CHUNK_RE = re.compile(r"(?:^|\n)[0-9a-f]{1,8}:T(?P<size>[0-9a-f]{1,8}),")
MARKDOWN_HEADING_RE = re.compile(r"(?m)^#{1,6}\s{0,3}")
MARKDOWN_EMPHASIS_RE = re.compile(r"\*{1,3}|_{2,3}")
REMOTE_RE = re.compile(r"\bremote\b", re.IGNORECASE)
MIN_DESCRIPTION_CHARS = 200
DETAIL_CONCURRENCY = 4
MAX_DETAIL_FETCHES = 60
ENRICHMENT_BUDGET_FRACTION = 0.85


class HaileyHrScraper(BaseScraper):
    name = "haileyhr"

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
            raise ValueError(f"No haileyhr slug in {company.careers_url}")
        deadline = monotonic() + company_budget(self.settings, company) * ENRICHMENT_BUDGET_FRACTION
        base = f"https://{slug}.careers.haileyhr.app/"
        html = await asyncio.to_thread(fetch_html, base, self.settings)
        jobs = listing()
        jobs.extend(parse_listing(html, base))
        await self._fetch_descriptions(jobs, deadline)
        return jobs

    async def _fetch_descriptions(self, jobs: list[RawJob], deadline: float) -> None:
        semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)

        async def fetch_one(job: RawJob) -> None:
            async with semaphore:
                if monotonic() >= deadline:
                    return
                try:
                    html = await asyncio.to_thread(fetch_html, job.url, self.settings)
                except Exception:
                    return
            job.description = description_from_page(html) or job.description

        await asyncio.gather(*(fetch_one(job) for job in jobs[:MAX_DETAIL_FETCHES]))


def parse_listing(html: str, base: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[RawJob] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        match = JOB_PATH.search(href)
        if not match or match.group("id") in seen:
            continue
        heading = anchor.find(["h2", "h3", "h4"])
        title = " ".join((heading or anchor).get_text(" ").split())
        if not title:
            continue
        chips = [
            " ".join(chip.get_text(" ").split())
            for chip in anchor.select("div.flex-wrap > div")
        ]
        chips = [chip for chip in chips if chip]
        seen.add(match.group("id"))
        jobs.append(
            RawJob(
                title=title,
                url=urljoin(base, href),
                external_id=match.group("id"),
                location=chips[0] if chips else None,
                remote_hint=any(REMOTE_RE.search(chip) for chip in chips),
            )
        )
    if not jobs and "haileyhr" not in html.lower():
        raise ScrapeError("haileyhr listing had no job links")
    return jobs


def description_from_page(html: str) -> Optional[str]:
    parts: list[str] = []
    for match in PUSH_RE.finditer(html):
        try:
            parts.append(json.loads(match.group(1)))
        except ValueError:
            continue
    payload = "".join(parts)
    best: Optional[str] = None
    for chunk in TEXT_CHUNK_RE.finditer(payload):
        start = len(payload[: chunk.end()].encode("utf-8"))
        size = int(chunk.group("size"), 16)
        text = payload.encode("utf-8")[start : start + size].decode("utf-8", "ignore")
        if best is None or len(text) > len(best):
            best = text
    if not best or len(best) < MIN_DESCRIPTION_CHARS:
        return None
    text = MARKDOWN_HEADING_RE.sub("", best)
    text = MARKDOWN_EMPHASIS_RE.sub("", text)
    return text.strip()
