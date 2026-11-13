from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Iterator, Optional

import requests  # type: ignore[import-untyped]
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
    salvaged: bool = False


class ScrapeError(Exception):
    pass


class RateLimitedError(ScrapeError):
    pass


PRIORITY_BUDGET_MULTIPLIER = 2.0

_LISTING: ContextVar[Optional[list[list[RawJob]]]] = ContextVar(
    "listing_progress", default=None
)


def company_budget(settings: Settings, company: Company) -> float:
    multiplier = PRIORITY_BUDGET_MULTIPLIER if company.priority else 1.0
    return settings.per_company_timeout * multiplier


def listing() -> list[RawJob]:
    jobs: list[RawJob] = []
    registry = _LISTING.get()
    if registry is not None:
        registry.append(jobs)
    return jobs


@contextmanager
def track_listing() -> Iterator[list[list[RawJob]]]:
    registry: list[list[RawJob]] = []
    token = _LISTING.set(registry)
    try:
        yield registry
    finally:
        _LISTING.reset(token)


def salvage(registry: Optional[list[list[RawJob]]]) -> list[RawJob]:
    kept: dict[str, RawJob] = {}
    for jobs in registry or []:
        for job in list(jobs):
            key = f"ext:{job.external_id}" if job.external_id else f"url:{job.url}"
            kept.setdefault(key, job)
    return list(kept.values())


def salvaged_result(
    company_id: int,
    method: str,
    jobs: list[RawJob],
    error: str,
    rate_limited: bool = False,
    timed_out: bool = False,
) -> ScrapeResult:
    return ScrapeResult(
        company_id=company_id,
        success=True,
        method=method,
        jobs=jobs,
        error=f"listing cut short, kept {len(jobs)} jobs read so far: {error}",
        partial=True,
        salvaged=True,
        rate_limited=rate_limited,
        timed_out=timed_out,
    )


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
            kept = salvage(_LISTING.get())
            if kept:
                result = salvaged_result(
                    company.id,
                    self.name,
                    kept,
                    result.error,
                    rate_limited=result.rate_limited,
                    timed_out=result.timed_out,
                )
        result.html = self._last_html
        result.duration = round(time.monotonic() - started, 2)
        return result
