from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
from dataclasses import dataclass, field
from typing import Mapping, Optional
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]
from sqlalchemy import select

from scraper.config import Settings, load_settings
from scraper.database import dispose_engine, session_scope
from scraper.models import Company, Job

HTTP_CONCURRENCY_CEILING = 50
PROGRESS_EVERY = 50
RETRY_DELAY_SECONDS = 1.0
DEFAULT_EXAMPLES = 5

BOT_DEFENCE_STATUSES = frozenset({401, 403, 405, 406, 429, 999})
BOT_DEFENCE_HOSTS = frozenset({"metacareers.com", "www.metacareers.com"})
BROKEN_STATUSES = frozenset({404, 410})
READABLE_CONTENT_TYPES = frozenset(
    {"text/html", "application/xhtml+xml", "application/pdf"}
)
BUCKET_ORDER = [
    "ok",
    "broken",
    "wrong_content",
    "bot_defence",
    "server_error",
    "other_status",
    "error",
]

_LOCAL = threading.local()


@dataclass(frozen=True)
class JobRef:
    job_id: int
    url: str
    title: str
    company_name: str


@dataclass(frozen=True)
class UrlGroup:
    url: str
    jobs: list[JobRef]


@dataclass
class UrlCheck:
    url: str
    jobs: list[JobRef]
    status: Optional[int]
    error: Optional[str]
    final_url: str
    bucket: str
    content_type: Optional[str] = None

    @property
    def row_count(self) -> int:
        return len(self.jobs)


@dataclass
class LinkCheckReport:
    checks: list[UrlCheck] = field(default_factory=list)

    @property
    def total_urls(self) -> int:
        return len(self.checks)

    @property
    def total_rows(self) -> int:
        return sum(check.row_count for check in self.checks)


@dataclass(frozen=True)
class CompanyBucketSummary:
    company_name: str
    count: int
    total_rows: int
    examples: list[tuple[str, str, Optional[str]]]


def _is_bot_defence_host(host: str) -> bool:
    if not host:
        return False
    for whitelisted in BOT_DEFENCE_HOSTS:
        if host == whitelisted or host.endswith("." + whitelisted):
            return True
    return False


def classify(
    status: Optional[int],
    url: str,
    error: Optional[str],
    content_type: Optional[str] = None,
) -> str:
    if status is None:
        return "error"
    if 200 <= status < 300:
        if content_type is not None and content_type not in READABLE_CONTENT_TYPES:
            return "wrong_content"
        return "ok"
    host = (urlparse(url).hostname or "").lower()
    if _is_bot_defence_host(host):
        return "bot_defence"
    if status in BOT_DEFENCE_STATUSES:
        return "bot_defence"
    if status in BROKEN_STATUSES:
        return "broken"
    if 500 <= status < 600:
        return "server_error"
    return "other_status"


def has_bad_links(report: LinkCheckReport) -> bool:
    return any(check.bucket in ("broken", "wrong_content") for check in report.checks)


def bucket_counts(report: LinkCheckReport) -> dict:
    counts = {bucket: 0 for bucket in BUCKET_ORDER}
    for check in report.checks:
        counts[check.bucket] = counts.get(check.bucket, 0) + 1
    return counts


def _company_total_rows(report: LinkCheckReport) -> dict:
    totals: dict = {}
    for check in report.checks:
        for job in check.jobs:
            totals[job.company_name] = totals.get(job.company_name, 0) + 1
    return totals


def company_bucket_summaries(
    report: LinkCheckReport, bucket: str, examples_limit: int
) -> list[CompanyBucketSummary]:
    totals = _company_total_rows(report)
    counts: dict = {}
    examples: dict = {}
    for check in report.checks:
        if check.bucket != bucket:
            continue
        for job in check.jobs:
            counts[job.company_name] = counts.get(job.company_name, 0) + 1
            bucket_examples = examples.setdefault(job.company_name, [])
            if len(bucket_examples) < examples_limit:
                bucket_examples.append((check.url, job.title, check.content_type))
    summaries = [
        CompanyBucketSummary(
            company_name=name,
            count=count,
            total_rows=totals.get(name, 0),
            examples=examples.get(name, []),
        )
        for name, count in counts.items()
    ]
    summaries.sort(key=lambda summary: summary.count, reverse=True)
    return summaries


def format_report(report: LinkCheckReport, examples_limit: int = DEFAULT_EXAMPLES) -> str:
    lines: list[str] = []
    lines.append(f"total urls checked: {report.total_urls}")
    lines.append(f"total board rows covered: {report.total_rows}")
    lines.append("")

    counts = bucket_counts(report)
    lines.append("bucket counts:")
    for bucket in BUCKET_ORDER:
        lines.append(f"  {bucket:<14}{counts.get(bucket, 0)}")

    broken_summaries = company_bucket_summaries(report, "broken", examples_limit)
    if broken_summaries:
        lines.append("")
        lines.append("companies with broken links:")
        for summary in broken_summaries:
            lines.append(
                f"  {summary.company_name} — {summary.count} broken / "
                f"{summary.total_rows} board rows"
            )
            for url, title, _content_type in summary.examples:
                lines.append(f"      {title} -> {url}")

    wrong_content_summaries = company_bucket_summaries(report, "wrong_content", examples_limit)
    if wrong_content_summaries:
        lines.append("")
        lines.append("companies with wrong content type:")
        for summary in wrong_content_summaries:
            lines.append(
                f"  {summary.company_name} — {summary.count} wrong content type / "
                f"{summary.total_rows} board rows"
            )
            for url, title, content_type in summary.examples:
                lines.append(f"      {title} -> {url} [{content_type}]")

    for bucket in ("error", "server_error"):
        summaries = company_bucket_summaries(report, bucket, examples_limit)
        if summaries:
            lines.append("")
            lines.append(f"companies with {bucket}:")
            for summary in summaries:
                lines.append(f"  {summary.company_name} — {summary.count}")

    return "\n".join(lines)


def report_to_dict(report: LinkCheckReport, examples_limit: int = DEFAULT_EXAMPLES) -> dict:
    return {
        "total_urls": report.total_urls,
        "total_board_rows": report.total_rows,
        "bucket_counts": bucket_counts(report),
        "broken_companies": [
            {
                "company": summary.company_name,
                "broken_count": summary.count,
                "total_board_rows": summary.total_rows,
                "examples": [
                    {"title": title, "url": url}
                    for url, title, _content_type in summary.examples
                ],
            }
            for summary in company_bucket_summaries(report, "broken", examples_limit)
        ],
        "wrong_content_companies": [
            {
                "company": summary.company_name,
                "wrong_content_count": summary.count,
                "total_board_rows": summary.total_rows,
                "examples": [
                    {"title": title, "url": url, "content_type": content_type}
                    for url, title, content_type in summary.examples
                ],
            }
            for summary in company_bucket_summaries(report, "wrong_content", examples_limit)
        ],
        "error_companies": [
            {"company": summary.company_name, "count": summary.count}
            for summary in company_bucket_summaries(report, "error", examples_limit)
        ],
        "server_error_companies": [
            {"company": summary.company_name, "count": summary.count}
            for summary in company_bucket_summaries(report, "server_error", examples_limit)
        ],
        "checks": [
            {
                "url": check.url,
                "final_url": check.final_url,
                "status": check.status,
                "error": check.error,
                "content_type": check.content_type,
                "bucket": check.bucket,
                "job_ids": [job.job_id for job in check.jobs],
            }
            for check in report.checks
        ],
    }


def _get_session(settings: Settings) -> requests.Session:
    session = getattr(_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": settings.user_agent})
        _LOCAL.session = session
    return session


def _extract_media_type(headers: Mapping[str, str]) -> Optional[str]:
    value = headers.get("Content-Type")
    if value is None:
        return None
    media_type = value.split(";", 1)[0].strip().lower()
    return media_type or None


def _fetch_status(url: str, settings: Settings) -> tuple:
    session = _get_session(settings)
    try:
        response = session.head(url, allow_redirects=True, timeout=settings.request_timeout)
        if 200 <= response.status_code < 300:
            content_type = _extract_media_type(response.headers)
            if content_type == "text/html":
                return response.status_code, None, response.url, content_type
    except requests.RequestException:
        pass
    try:
        response = session.get(
            url, allow_redirects=True, timeout=settings.request_timeout, stream=True
        )
        try:
            return (
                response.status_code,
                None,
                response.url,
                _extract_media_type(response.headers),
            )
        finally:
            response.close()
    except requests.RequestException as exc:
        return None, str(exc), url, None


async def _check_url(
    url: str, settings: Settings, semaphore: asyncio.Semaphore
) -> tuple:
    async with semaphore:
        status, error, final_url, content_type = await asyncio.to_thread(
            _fetch_status, url, settings
        )
    needs_retry = error is not None or (status is not None and status >= 500)
    if needs_retry:
        await asyncio.sleep(RETRY_DELAY_SECONDS)
        async with semaphore:
            status, error, final_url, content_type = await asyncio.to_thread(
                _fetch_status, url, settings
            )
    return status, error, final_url, content_type


def _fetch_board_job_refs(include_all: bool, company_filter: Optional[str]) -> list:
    with session_scope() as session:
        stmt = (
            select(Job.id, Job.url, Job.title, Company.name)
            .join(Company, Job.company_id == Company.id)
            .where(Job.is_active.is_(True))
        )
        if not include_all:
            stmt = stmt.where(Job.is_audio_related.is_(True))
        if company_filter:
            stmt = stmt.where(Company.name.ilike(f"%{company_filter}%"))
        rows = session.execute(stmt).all()
    return [
        JobRef(job_id=row[0], url=row[1], title=row[2], company_name=row[3])
        for row in rows
        if row[1]
    ]


def _group_by_url(job_refs: list) -> list:
    order: list = []
    groups: dict = {}
    for ref in job_refs:
        bucket = groups.setdefault(ref.url, [])
        if not bucket:
            order.append(ref.url)
        bucket.append(ref)
    return [UrlGroup(url=url, jobs=groups[url]) for url in order]


async def run_checks(
    groups: list, settings: Settings, concurrency: int
) -> LinkCheckReport:
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    total = len(groups)
    state = {"completed": 0}

    async def _run_one(group: UrlGroup) -> UrlCheck:
        status, error, final_url, content_type = await _check_url(group.url, settings, semaphore)
        bucket = classify(status, final_url or group.url, error, content_type)
        async with lock:
            state["completed"] += 1
            if state["completed"] % PROGRESS_EVERY == 0:
                print(f"checked {state['completed']}/{total}", file=sys.stderr)
        return UrlCheck(
            url=group.url,
            jobs=group.jobs,
            status=status,
            error=error,
            final_url=final_url,
            bucket=bucket,
            content_type=content_type,
        )

    checks = await asyncio.gather(*(_run_one(group) for group in groups))
    return LinkCheckReport(checks=list(checks))


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep every public board job URL and report dead links"
    )
    parser.add_argument(
        "--all", action="store_true", help="Sweep every active row, not just the board"
    )
    parser.add_argument(
        "--company", default=None, help="Case-insensitive substring match on company name"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Check only the first N distinct URLs"
    )
    parser.add_argument(
        "--examples", type=int, default=DEFAULT_EXAMPLES, help="Example URLs shown per company"
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    try:
        settings = load_settings()
        job_refs = _fetch_board_job_refs(args.all, args.company)
        groups = _group_by_url(job_refs)
        if args.limit is not None:
            groups = groups[: args.limit]
        concurrency = min(settings.http_concurrency, HTTP_CONCURRENCY_CEILING)
        report = asyncio.run(run_checks(groups, settings, concurrency))
    finally:
        dispose_engine()

    if args.json:
        print(json.dumps(report_to_dict(report, args.examples), indent=2))
    else:
        print(format_report(report, args.examples))

    return 1 if has_bad_links(report) else 0


if __name__ == "__main__":
    sys.exit(main())
