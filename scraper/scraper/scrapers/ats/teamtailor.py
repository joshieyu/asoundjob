from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ElementTree
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_html

if TYPE_CHECKING:
    from datetime import date

    from scraper.models import Company

HOST_PATTERN = re.compile(r"^[a-z0-9-]+\.teamtailor\.com$", re.IGNORECASE)
JOB_ID_RE = re.compile(r"/jobs/(?P<id>\d{1,15})(?:-|$)")
TT_NS = "{https://teamtailor.com/locations}"


class TeamtailorScraper(BaseScraper):
    name = "teamtailor"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "teamtailor":
            return True
        host = urlsplit((company.careers_url or "").strip()).netloc
        return HOST_PATTERN.match(host) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        parts = urlsplit((company.careers_url or "").strip())
        if not parts.netloc:
            raise ScrapeError(f"No teamtailor host in {company.careers_url}")
        feed_url = f"{parts.scheme or 'https'}://{parts.netloc}/jobs.rss"
        feed = await asyncio.to_thread(fetch_html, feed_url, self.settings)
        return parse_feed(feed)


def parse_feed(feed: str) -> list[RawJob]:
    if "<!ENTITY" in feed or "<!DOCTYPE" in feed:
        raise ScrapeError("teamtailor feed declares entities; refusing to parse")
    try:
        root = ElementTree.fromstring(feed)
    except ElementTree.ParseError as exc:
        raise ScrapeError(f"teamtailor feed is not valid XML: {exc}") from exc
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise ScrapeError("teamtailor feed has no rss channel")
    jobs: list[RawJob] = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        match = JOB_ID_RE.search(urlsplit(link).path)
        jobs.append(
            RawJob(
                title=title,
                url=link,
                external_id=match.group("id") if match else (item.findtext("guid") or link),
                location=_location(item),
                description=(item.findtext("description") or "").strip() or None,
                posted_date=_posted(item.findtext("pubDate")),
                remote_hint=(item.findtext("remoteStatus") or "").strip().lower() == "fully",
            )
        )
    return jobs


def _location(item: ElementTree.Element) -> str | None:
    names: list[str] = []
    for place in item.iter(f"{TT_NS}location"):
        city = (place.findtext(f"{TT_NS}city") or "").strip()
        country = (place.findtext(f"{TT_NS}country") or "").strip()
        text = ", ".join(part for part in (city, country) if part)
        if text and text not in names:
            names.append(text)
    return "; ".join(names) or None


def _posted(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).date()
    except (TypeError, ValueError):
        return None
