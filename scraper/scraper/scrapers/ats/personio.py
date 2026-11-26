from __future__ import annotations

import asyncio
import html
import re
import xml.etree.ElementTree as ElementTree
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_html, parse_date

if TYPE_CHECKING:
    from scraper.models import Company

HOST_PATTERN = re.compile(r"^[a-z0-9-]{1,63}\.jobs\.personio\.(?:de|com)$", re.IGNORECASE)
JOB_ID_RE = re.compile(r"^\d{1,15}$")
EMPLOYMENT_TYPES = {"intern": "internship", "trainee": "internship", "freelance": "contract"}


class PersonioScraper(BaseScraper):
    name = "personio"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "personio":
            return True
        host = urlsplit((company.careers_url or "").strip()).netloc
        return HOST_PATTERN.match(host) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        parts = urlsplit((company.careers_url or "").strip())
        if not parts.netloc:
            raise ScrapeError(f"No personio host in {company.careers_url}")
        origin = f"{parts.scheme or 'https'}://{parts.netloc}"
        feed = await asyncio.to_thread(fetch_html, f"{origin}/xml?language=en", self.settings)
        return parse_feed(feed, origin)


def parse_feed(feed: str, origin: str) -> list[RawJob]:
    if "<!ENTITY" in feed or "<!DOCTYPE" in feed:
        raise ScrapeError("personio feed declares entities; refusing to parse")
    try:
        root = ElementTree.fromstring(feed)
    except ElementTree.ParseError as exc:
        raise ScrapeError(f"personio feed is not valid XML: {exc}") from exc
    if root.tag != "workzag-jobs":
        raise ScrapeError("personio feed has no workzag-jobs root")
    jobs: list[RawJob] = []
    for position in root.findall("position"):
        job_id = (position.findtext("id") or "").strip()
        title = (position.findtext("name") or "").strip()
        if not title or not JOB_ID_RE.match(job_id):
            continue
        jobs.append(
            RawJob(
                title=title,
                url=f"{origin}/job/{job_id}",
                external_id=job_id,
                location=_location(position),
                description=_description(position),
                posted_date=parse_date((position.findtext("createdAt") or "").strip() or None),
                job_type=_job_type(position),
            )
        )
    return jobs


def _location(position: ElementTree.Element) -> str | None:
    names: list[str] = []
    offices = [position.find("office")]
    additional = position.find("additionalOffices")
    if additional is not None:
        offices.extend(additional.findall("office"))
    for office in offices:
        text = (office.text or "").strip() if office is not None else ""
        if text and text not in names:
            names.append(text)
    return "; ".join(names) or None


def _description(position: ElementTree.Element) -> str | None:
    sections: list[str] = []
    for block in position.iter("jobDescription"):
        heading = (block.findtext("name") or "").strip()
        body = (block.findtext("value") or "").strip()
        if not body:
            continue
        sections.append(f"<h3>{html.escape(heading)}</h3>{body}" if heading else body)
    return "".join(sections) or None


def _job_type(position: ElementTree.Element) -> str | None:
    employment = (position.findtext("employmentType") or "").strip().lower()
    if employment in EMPLOYMENT_TYPES:
        return EMPLOYMENT_TYPES[employment]
    schedule = (position.findtext("schedule") or "").strip().lower()
    return schedule or None
