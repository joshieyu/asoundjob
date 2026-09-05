from __future__ import annotations

import asyncio
import re
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs, urlsplit

from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.fetch import fetch_json

if TYPE_CHECKING:
    from scraper.models import Company

URL_PATTERN = re.compile(
    r"^https?://integration\.sigma\.se/esb/vacancy/portal/positions/?"
    r"(?:\?[^\s]{0,2000})?$",
    re.IGNORECASE,
)

US_STATE_CODE = re.compile(r"^[A-Z]{2}$")

CITY_SPLIT_RE = re.compile(r"[;,|/]")
NON_SLUG_RE = re.compile(r"[^a-z0-9-]")
DASH_RUN_RE = re.compile(r"-{1,200}")

DESCRIPTION_FIELDS = ("description", "qualifications", "offer", "experience")


class SigmaScraper(BaseScraper):
    name = "sigma"

    def can_handle(self, company: Company) -> bool:
        if company.ats_type == "sigma":
            return True
        if not company.careers_url:
            return False
        return URL_PATTERN.match(company.careers_url.strip()) is not None

    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        careers_url = (company.careers_url or "").strip()
        prefix = extract_company_prefix(careers_url)
        response = await asyncio.to_thread(fetch_json, careers_url, self.settings)
        if not isinstance(response, list):
            raise ScrapeError(
                f"Unexpected sigma positions response for company_startswith={prefix!r}"
            )
        jobs = parse_jobs(response, prefix)
        seen: set[str] = set()
        deduped: list[RawJob] = []
        for job in jobs:
            key = job.external_id or job.url
            if key in seen:
                continue
            seen.add(key)
            deduped.append(job)
        return deduped


def extract_company_prefix(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    values = parse_qs(parsed.query).get("company_startswith")
    return values[0] if values else ""


def locale_for(item: dict) -> str:
    title = item.get("title") or {}
    return "en" if title.get("en") else "sv"


def city_list_for(item: dict) -> list[str]:
    locale = locale_for(item)
    cities = item.get("cities") or {}
    raw = cities.get(locale) or cities.get("en") or cities.get("sv") or ""
    if isinstance(raw, list):
        raw = ",".join(raw)
    tokens = [token.strip() for token in CITY_SPLIT_RE.split(raw) if token.strip()]
    result: list[str] = []
    for token in tokens:
        if US_STATE_CODE.match(token) and result:
            result[-1] = f"{result[-1]}, {token}"
        else:
            result.append(token)
    return result


def slugify(value: str) -> str:
    text = value.lower().replace("å", "a").replace("ä", "a").replace("ö", "o")
    text = NON_SLUG_RE.sub("-", text)
    text = DASH_RUN_RE.sub("-", text)
    return text.strip("-")


def _title_slug(title: str) -> str:
    text = title.lower().replace("+", "")
    text = text.replace("å", "a").replace("ä", "a").replace("ö", "o")
    text = NON_SLUG_RE.sub("-", text)
    text = DASH_RUN_RE.sub("-", text)
    if text.endswith("-"):
        text = text[:-1]
    return text


def generate_job_url(item: dict) -> str | None:
    publication_date = item.get("publicationDate")
    if not isinstance(publication_date, str):
        return None
    try:
        formatted_date = datetime.strptime(publication_date[:10], "%Y-%m-%d").strftime(
            "%Y%m%d"
        )
    except ValueError:
        return None

    locale = locale_for(item)
    cities = city_list_for(item)
    job_cities = slugify(cities[0]) if cities else None
    country = (item.get("country") or {}).get(locale)
    job_country = slugify(country) if country is not None else None

    job_location: str | None
    if job_country is None and job_cities is not None:
        job_location = job_cities
    elif job_country is not None and job_cities is None:
        job_location = job_country
    elif job_country == "united-states":
        job_location = job_cities
    else:
        job_location = f"{job_cities}-{job_country}"

    if job_location is not None and job_location.startswith("san-diego-ca-"):
        job_location = "san-diego-ca"

    title = (item.get("title") or {}).get(locale) or ""
    job_title = _title_slug(title)
    segment = "sv/position" if locale == "sv" else "position"
    return f"https://www.sigma.se/{segment}/{job_title}-{job_location}-{locale}-{formatted_date}"


def parse_jobs(items: list[Any], prefix: str) -> list[RawJob]:
    lowered_prefix = prefix.lower()
    jobs: list[RawJob] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        company_name = item.get("company")
        company_text = company_name if isinstance(company_name, str) else ""
        if not company_text.lower().startswith(lowered_prefix):
            continue
        job = _parse_job(item)
        if job is not None:
            jobs.append(job)
    return jobs


def _parse_job(item: dict) -> RawJob | None:
    locale = locale_for(item)
    title = (item.get("title") or {}).get(locale)
    if not title:
        return None
    url = generate_job_url(item)
    if url is None:
        return None
    cities = city_list_for(item)
    external_id = item.get("id")
    return RawJob(
        title=title,
        url=url,
        external_id=str(external_id) if external_id is not None else None,
        location=", ".join(cities) if cities else None,
        description=_build_description(item, locale),
        posted_date=_parse_posted_date(item.get("publicationDate")),
    )


def _build_description(item: dict, locale: str) -> str | None:
    parts = []
    for field in DESCRIPTION_FIELDS:
        value = (item.get(field) or {}).get(locale)
        if isinstance(value, str) and value.strip():
            parts.append(value)
    return "\n".join(parts) if parts else None


def _parse_posted_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
