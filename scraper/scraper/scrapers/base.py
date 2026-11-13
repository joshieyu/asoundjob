from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Optional

import requests
from urllib3.exceptions import ReadTimeoutError

if TYPE_CHECKING:
    from scraper.config import Settings
    from scraper.models import Company

logger = logging.getLogger(__name__)


@dataclass
class RawJob:
    title: str
    url: str
    external_id: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    job_type: Optional[str] = None
    posted_date: Optional[date] = None
    remote_hint: bool = False


@dataclass
class ScrapeResult:
    company_id: int
    success: bool = False
    method: str = "none"
    jobs: list[RawJob] = field(default_factory=list)
    error: Optional[str] = None
    duration: float = 0.0
    trust_empty: bool = False
    partial: bool = False
    html: Optional[str] = None
    rate_limited: bool = False
    timed_out: bool = False


class ScrapeError(Exception):
    pass


class RateLimitedError(ScrapeError):
    pass


TIMEOUT_ERRORS = (requests.Timeout, ReadTimeoutError, asyncio.TimeoutError)


def is_timeout(exc: BaseException) -> bool:
    seen: set[int] = set()
    pending: list[BaseException] = [exc]
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, TIMEOUT_ERRORS):
            return True
        pending.extend(arg for arg in current.args if isinstance(arg, BaseException))
        for linked in (current.__cause__, current.__context__):
            if linked is not None:
                pending.append(linked)
    return False


class BaseScraper(ABC):
    """Base class for all scrapers.

    Subclasses implement fetch_jobs() and raise ScrapeError (or any exception)
    on failure. scrape() wraps fetch_jobs() with timing, error handling and
    logging so the orchestrator can rely on a uniform ScrapeResult.
    """

    name: str = "base"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._last_html: Optional[str] = None

    def can_handle(self, company: Company) -> bool:
        return True

    @abstractmethod
    async def fetch_jobs(self, company: Company) -> list[RawJob]:
        ...

    async def scrape(self, company: Company) -> ScrapeResult:
        import time

        self._last_html = None
        result = ScrapeResult(company_id=company.id, method=self.name)
        started = time.monotonic()
        try:
            result.jobs = await self.fetch_jobs(company)
            result.success = True
        except Exception as exc:
            logger.warning(
                "scraper=%s company=%s failed: %s", self.name, company.name, exc
            )
            result.error = f"{type(exc).__name__}: {exc}"
            result.rate_limited = isinstance(exc, RateLimitedError)
            result.timed_out = is_timeout(exc)
        result.html = self._last_html
        result.duration = round(time.monotonic() - started, 2)
        return result
