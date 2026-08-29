from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy import func, select

from scraper.config import Settings, load_settings
from scraper.database import dispose_engine, init_db, session_scope
from scraper.models import Company, ScrapeLog
from scraper.scrapers.ats_discovery import discover
from scraper.scrapers.link_extraction import extract_jobs

LAUNCH_ARGS = ["--disable-blink-features=AutomationControlled", "--no-sandbox"]

MAX_JSON_ENDPOINTS = 5
MAX_RESPONSE_BYTES = 2_000_000
MAX_LINKS = 500
PROGRESS_EVERY = 25
EXAMPLES_PER_BUCKET = 5


@dataclass
class PageProbe:
    company_id: int
    company_name: str
    url: str
    status: Optional[int] = None
    error: Optional[str] = None
    html: str = ""
    final_url: str = ""
    links: list = field(default_factory=list)
    json_endpoints: list = field(default_factory=list)
    job_link_count: int = 0


def probe_from_dict(data: dict) -> PageProbe:
    return PageProbe(
        company_id=data["company_id"],
        company_name=data["company_name"],
        url=data["url"],
        status=data.get("status"),
        error=data.get("error"),
        html=data.get("html", ""),
        final_url=data.get("final_url", ""),
        links=list(data.get("links", [])),
        json_endpoints=list(data.get("json_endpoints", [])),
        job_link_count=data.get("job_link_count", 0),
    )


SUPPORTED_ATS = frozenset(
    {
        "greenhouse",
        "lever",
        "workable",
        "ashby",
        "smartrecruiters",
        "recruitee",
        "bamboohr",
        "workday",
        "apple",
        "pinpoint",
    }
)

EXTENDED_ATS_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("jobvite", re.compile(r"jobs\.jobvite\.com", re.IGNORECASE)),
    ("icims", re.compile(r"[\w-]{1,63}\.icims\.com", re.IGNORECASE)),
    ("taleo", re.compile(r"[\w-]{1,63}\.taleo\.net", re.IGNORECASE)),
    ("successfactors", re.compile(r"[\w-]{1,63}\.successfactors\.(?:com|eu)", re.IGNORECASE)),
    ("teamtailor", re.compile(r"[\w-]{1,63}\.teamtailor\.com", re.IGNORECASE)),
    ("personio", re.compile(r"[\w-]{1,63}\.jobs\.personio\.(?:de|com)", re.IGNORECASE)),
    ("jazzhr", re.compile(r"[\w-]{1,63}\.applytojob\.com", re.IGNORECASE)),
    ("paylocity", re.compile(r"recruiting\.paylocity\.com", re.IGNORECASE)),
    ("ukg", re.compile(r"[\w-]{1,63}\.ultipro\.com|recruiting\d*\.ultipro\.com", re.IGNORECASE)),
    ("dayforce", re.compile(r"[\w-]{1,63}\.dayforcehcm\.com", re.IGNORECASE)),
    ("oraclecloud", re.compile(r"[\w-]{1,63}\.oraclecloud\.com", re.IGNORECASE)),
    ("avature", re.compile(r"[\w-]{1,63}\.avature\.net", re.IGNORECASE)),
    ("phenom", re.compile(r"phenompeople\.com", re.IGNORECASE)),
    ("eightfold", re.compile(r"[\w-]{1,63}\.eightfold\.ai", re.IGNORECASE)),
    ("rippling", re.compile(r"ats\.rippling\.com", re.IGNORECASE)),
    ("jobscore", re.compile(r"careers\.jobscore\.com", re.IGNORECASE)),
    ("join", re.compile(r"join\.com/companies", re.IGNORECASE)),
    ("softgarden", re.compile(r"[\w-]{1,63}\.softgarden\.io", re.IGNORECASE)),
    ("zohorecruit", re.compile(r"zohorecruit\.com", re.IGNORECASE)),
    ("factorial", re.compile(r"[\w-]{1,63}\.factorialhr\.com", re.IGNORECASE)),
    ("freshteam", re.compile(r"[\w-]{1,63}\.freshteam\.com", re.IGNORECASE)),
    ("darwinbox", re.compile(r"[\w-]{1,63}\.darwinbox\.com", re.IGNORECASE)),
    ("brassring", re.compile(r"[\w-]{1,63}\.brassring\.com", re.IGNORECASE)),
    ("clearcompany", re.compile(r"[\w-]{1,63}\.clearcompany\.com", re.IGNORECASE)),
    ("homerun", re.compile(r"[\w-]{1,63}\.homerun\.co", re.IGNORECASE)),
    ("recruitcrm", re.compile(r"[\w-]{1,63}\.recruitcrm\.io", re.IGNORECASE)),
    ("hirehive", re.compile(r"[\w-]{1,63}\.hirehive\.com", re.IGNORECASE)),
    ("talentlyft", re.compile(r"[\w-]{1,63}\.talentlyft\.com", re.IGNORECASE)),
]

NO_OPENINGS_MARKERS = (
    "no open positions",
    "no current openings",
    "no vacancies",
    "no job openings",
    "there are currently no",
    "no positions available",
    "check back",
    "not hiring",
    "keine offenen stellen",
    "derzeit keine",
    "aucun poste",
    "pas de poste",
    "no hay vacantes",
    "no hay ofertas",
    "geen vacatures",
    "nessuna posizione",
)

BLOCK_MARKERS = (
    "/cdn-cgi/challenge-platform",
    "cf-browser-verification",
    "cf_chl_opt",
    "attention required! | cloudflare",
    "just a moment...",
    "checking your browser before accessing",
    "enable javascript and cookies to continue",
    "_incapsula_resource",
    "incapsula incident id",
    "px-captcha",
    "please verify you are a human",
    "are you a robot",
    "unusual traffic from your computer network",
    "access to this page has been denied",
    "request unsuccessful. incapsula incident",
    "ddos protection by",
)

BLOCK_PAGE_MAX_LEN = 20000

JS_APP_MARKERS = (
    "__next_data__",
    "__nuxt__",
    "data-reactroot",
    "ng-version",
    "window.__initial_state__",
    'id="root"',
    'id="app"',
    "wp-content/plugins",
)

CAREERS_SIGNAL = re.compile(
    r"career|careers|job|jobs|vacanc|opening|position|recruit|hiring|"
    r"stelle|stellenangebot|karriere|emploi|carriere|empleo|vacature|lavoro|"
    r"採用|募集|求人|招聘",
    re.IGNORECASE,
)

NOISE_ENDPOINT_HOST_SUBSTRINGS = (
    "cookielaw",
    "onetrust",
    "cookiebot",
    "usercentrics",
    "youtube",
    "ytimg",
    "google",
    "googletagmanager",
    "doubleclick",
    "facebook",
    "linkedin",
    "twitter",
    "hotjar",
    "segment.io",
    "segment.com",
    "mixpanel",
    "amplitude",
    "sentry",
    "datadog",
    "newrelic",
    "cloudflareinsights",
    "recaptcha",
    "gstatic",
    "algolia",
    "intercom",
    "zendesk",
    "hubspot",
    ".wp.com",
    "gravatar",
)

JOB_ENDPOINT_VOCAB = re.compile(
    r"job|career|vacan|position|opening|recruit|hiring|stelle|emploi|opportunit",
    re.IGNORECASE,
)

BLOCKED_STATUS_CODES = frozenset({401, 403, 429})

CERT_ERROR_HINTS = ("cert", "ssl")
DNS_ERROR_HINTS = ("err_name_not_resolved", "enotfound", "dns")
TIMEOUT_ERROR_HINTS = ("timeout",)

MAX_ERROR_DETAIL_LEN = 160
MAX_ENDPOINT_DETAIL_LEN = 120


def _short(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _registrable_ish(host: str) -> str:
    labels = host.lower().split(".")
    if len(labels) >= 2:
        return ".".join(labels[-2:])
    return host.lower()


def is_job_endpoint(page_url: str, endpoint_url: str) -> bool:
    endpoint_host = (urlparse(endpoint_url).hostname or "").lower()
    if any(noise in endpoint_host for noise in NOISE_ENDPOINT_HOST_SUBSTRINGS):
        return False

    parsed_endpoint = urlparse(endpoint_url)
    endpoint_target = parsed_endpoint.path + "?" + parsed_endpoint.query
    if JOB_ENDPOINT_VOCAB.search(endpoint_target):
        return True

    page_host = (urlparse(page_url).hostname or "").lower()
    if (
        endpoint_host
        and page_host
        and _registrable_ish(endpoint_host) == _registrable_ish(page_host)
    ):
        return True

    return False


def classify(probe: PageProbe) -> tuple[str, str]:
    if probe.error:
        lowered_error = probe.error.lower()
        if any(hint in lowered_error for hint in CERT_ERROR_HINTS):
            return ("unreachable", "tls: " + _short(probe.error, MAX_ERROR_DETAIL_LEN))
        if any(hint in lowered_error for hint in DNS_ERROR_HINTS):
            return ("unreachable", "dns")
        if any(hint in lowered_error for hint in TIMEOUT_ERROR_HINTS):
            return ("unreachable", "timeout")
        return ("unreachable", _short(probe.error, MAX_ERROR_DETAIL_LEN))

    if probe.status is not None and probe.status >= 400:
        if probe.status in BLOCKED_STATUS_CODES:
            return ("blocked", f"http {probe.status}")
        return ("dead_url", f"http {probe.status}")

    lowered_html = probe.html.lower()

    if len(probe.html) < BLOCK_PAGE_MAX_LEN:
        for marker in BLOCK_MARKERS:
            if marker in lowered_html:
                return ("blocked", marker)

    links_text = "\n".join(probe.links)
    discovered = discover(probe.html) + discover(links_text)
    for ats_type, _slug in discovered:
        if ats_type in SUPPORTED_ATS:
            return ("ats_discoverable", ats_type)

    haystack = probe.html + "\n" + links_text
    for name, pattern in EXTENDED_ATS_PATTERNS:
        if pattern.search(haystack):
            return ("ats_unsupported", name)

    for endpoint in probe.json_endpoints:
        if is_job_endpoint(probe.url, endpoint):
            return ("json_endpoint", _short(endpoint, MAX_ENDPOINT_DETAIL_LEN))

    for marker in NO_OPENINGS_MARKERS:
        if marker in lowered_html:
            return ("no_openings", marker)

    if not CAREERS_SIGNAL.search(lowered_html):
        return ("not_a_careers_page", "no careers vocabulary")

    if probe.job_link_count > 0:
        return (
            "extractor_gap",
            f"{probe.job_link_count} links extracted but scrape reported none",
        )

    for marker in JS_APP_MARKERS:
        if marker in lowered_html:
            return ("js_rendered", marker)

    return ("unknown", "")


def summarize(results: list) -> dict:
    counts: dict[str, int] = {}
    for bucket, _detail in results:
        counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True))


async def probe_company(
    browser: Any,
    company_id: int,
    company_name: str,
    url: str,
    settings: Settings,
) -> PageProbe:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    probe = PageProbe(company_id=company_id, company_name=company_name, url=url)

    async def _do_probe() -> None:
        context = await browser.new_context(user_agent=settings.user_agent)
        json_endpoints: list = []
        try:
            page = await context.new_page()

            async def on_response(response: Any) -> None:
                try:
                    if len(json_endpoints) >= MAX_JSON_ENDPOINTS:
                        return
                    request = response.request
                    if request.resource_type not in ("xhr", "fetch"):
                        return
                    content_type = (response.headers.get("content-type") or "").lower()
                    if "json" not in content_type:
                        return
                    if response.url == url:
                        return
                    if not is_job_endpoint(url, response.url):
                        return
                    content_length = response.headers.get("content-length")
                    if content_length is not None:
                        try:
                            if int(content_length) > MAX_RESPONSE_BYTES:
                                return
                        except ValueError:
                            pass
                    body = await response.text()
                    if len(body) > MAX_RESPONSE_BYTES:
                        return
                    lowered_body = body.lower()
                    if any(
                        token in lowered_body
                        for token in ("title", "job", "position", "vacanc")
                    ):
                        json_endpoints.append(response.url)
                except Exception:
                    pass

            page.on("response", on_response)

            timeout_ms = int(settings.page_load_timeout * 1000)
            nav_response = None
            try:
                nav_response = await page.goto(
                    url, wait_until="networkidle", timeout=timeout_ms
                )
            except PlaywrightTimeoutError:
                nav_response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=timeout_ms
                )

            if nav_response is not None:
                probe.status = nav_response.status

            await page.wait_for_timeout(500)

            try:
                probe.html = await page.content()
            except Exception:
                probe.html = ""

            probe.final_url = page.url
            probe.json_endpoints = list(json_endpoints)

            try:
                links = await page.eval_on_selector_all(
                    "a[href]", "els => els.map(e => e.href)"
                )
                probe.links = list(links)[:MAX_LINKS]
            except Exception:
                probe.links = []

            try:
                probe.job_link_count = len(extract_jobs(probe.html, url))
            except Exception:
                probe.job_link_count = 0
        finally:
            try:
                await context.close()
            except Exception:
                pass

    try:
        await asyncio.wait_for(_do_probe(), timeout=settings.per_company_timeout)
    except Exception as exc:
        probe.error = f"{type(exc).__name__}: {exc}"

    return probe


def _fetch_failed_companies(limit: Optional[int]) -> list:
    with session_scope() as session:
        latest_ids = (
            select(ScrapeLog.company_id, func.max(ScrapeLog.id).label("max_id"))
            .group_by(ScrapeLog.company_id)
            .subquery()
        )
        query = (
            select(Company.id, Company.name, Company.careers_url)
            .join(ScrapeLog, ScrapeLog.company_id == Company.id)
            .join(
                latest_ids,
                (ScrapeLog.company_id == latest_ids.c.company_id)
                & (ScrapeLog.id == latest_ids.c.max_id),
            )
            .where(ScrapeLog.status == "failed")
            .order_by(Company.id)
        )
        rows = session.execute(query).all()
        companies = []
        for row in rows:
            company_id, name, careers_url = row[0], row[1], row[2]
            if not careers_url or not careers_url.strip():
                continue
            companies.append((company_id, name, careers_url.strip()))

    if limit is not None:
        companies = companies[:limit]
    return companies


def _print_summary(rows: list) -> None:
    if not rows:
        print("no failed companies with a careers_url were found")
        return

    pairs = [(row["bucket"], row["detail"]) for row in rows]
    summary = summarize(pairs)
    total = sum(summary.values())

    examples: dict[str, list] = {}
    for row in rows:
        bucket = row["bucket"]
        bucket_examples = examples.setdefault(bucket, [])
        if len(bucket_examples) < EXAMPLES_PER_BUCKET:
            bucket_examples.append(f"{row['company']} — {row['detail']}")

    print(f"\n{total} companies diagnosed\n")
    print(f"{'bucket':<22}{'count':>7}{'pct':>8}")
    for bucket, count in summary.items():
        pct = (count / total * 100) if total else 0.0
        print(f"{bucket:<22}{count:>7}{pct:>7.1f}%")

    for bucket in summary:
        print(f"\n{bucket}:")
        for line in examples.get(bucket, []):
            print(f"  {line}")


def _rows_from_probes(probes: list) -> list:
    rows: list = []
    for probe in probes:
        bucket, detail = classify(probe)
        rows.append(
            {
                "company_id": probe.company_id,
                "company": probe.company_name,
                "url": probe.url,
                "bucket": bucket,
                "detail": detail,
                "status": probe.status,
                "job_link_count": probe.job_link_count,
                "json_endpoints": probe.json_endpoints,
                "final_url": probe.final_url,
            }
        )
    return rows


def _write_probe_cache(cache_dir: str, probe: PageProbe) -> None:
    try:
        os.makedirs(cache_dir, exist_ok=True)
        path = os.path.join(cache_dir, f"{probe.company_id}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(probe), fh)
    except Exception as exc:
        print(f"failed to write cache for company {probe.company_id}: {exc}", file=sys.stderr)


def _load_cached_probes(cache_dir: str) -> list:
    probes: list = []
    for name in sorted(os.listdir(cache_dir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(cache_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            probes.append(probe_from_dict(data))
        except Exception as exc:
            print(f"failed to load cache file {path}: {exc}", file=sys.stderr)
    return probes


async def run(
    limit: Optional[int],
    concurrency: int,
    output_path: str,
    html_cache: Optional[str] = None,
    from_cache: Optional[str] = None,
) -> None:
    if from_cache is not None:
        cached_probes = _load_cached_probes(from_cache)
        cached_rows = _rows_from_probes(cached_probes)
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(cached_rows, fh, indent=2)
        _print_summary(cached_rows)
        return

    settings = load_settings()
    init_db()

    browser = None
    playwright_ctx = None
    try:
        companies = _fetch_failed_companies(limit)
        rows: list = []

        if companies:
            from playwright.async_api import async_playwright

            playwright_ctx = await async_playwright().start()
            browser = await playwright_ctx.chromium.launch(
                headless=True, args=LAUNCH_ARGS
            )

            semaphore = asyncio.Semaphore(concurrency)
            lock = asyncio.Lock()
            state = {"completed": 0}

            async def _run_one(company_id: int, name: str, careers_url: str) -> PageProbe:
                async with semaphore:
                    probe = await probe_company(
                        browser, company_id, name, careers_url, settings
                    )
                if html_cache is not None:
                    _write_probe_cache(html_cache, probe)
                async with lock:
                    state["completed"] += 1
                    if state["completed"] % PROGRESS_EVERY == 0:
                        print(
                            f"probed {state['completed']}/{len(companies)}",
                            file=sys.stderr,
                        )
                return probe

            probes = await asyncio.gather(
                *(_run_one(company_id, name, careers_url)
                  for company_id, name, careers_url in companies)
            )

            rows = _rows_from_probes(probes)

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=2)

        _print_summary(rows)
    finally:
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass
        if playwright_ctx is not None:
            try:
                await playwright_ctx.stop()
            except Exception:
                pass
        dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose why recently failed company scrapes yield no jobs"
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--output", type=str, default="diagnose_failures.json")
    parser.add_argument("--html-cache", type=str, default=None)
    parser.add_argument("--from-cache", type=str, default=None)
    args = parser.parse_args()
    asyncio.run(
        run(
            args.limit,
            args.concurrency,
            args.output,
            args.html_cache,
            args.from_cache,
        )
    )


if __name__ == "__main__":
    main()
