import argparse
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import requests

from jobspy import Country, scrape_jobs

DEFAULT_TERMS_FILE = Path(__file__).resolve().parent / "terms.txt"

OUTPUT_FIELDS = (
    "title",
    "company_name",
    "company_url",
    "job_url",
    "location",
    "date_posted",
    "site",
    "search_term",
    "description",
)

PROXY_SCHEMES = ("http://", "https://", "socks5://")

IP_ECHO_URL = "https://api.ipify.org?format=json"
IP_ECHO_TIMEOUT = 5.0

LINKEDIN_LOGGER_NAME = "JobSpy:LinkedIn"
BLOCK_MESSAGE_429 = "429 Response - Blocked by LinkedIn for too many requests"
BLOCK_MESSAGE_BAD_PROXY = "Bad proxy"


def valid_country_names() -> list[str]:
    names: list[str] = []
    for country in Country:
        names.extend(alias.strip() for alias in country.value[0].split(","))
    return sorted(set(names))


def validate_country(country: str) -> str:
    try:
        Country.from_string(country)
    except ValueError:
        valid = ", ".join(valid_country_names())
        sys.exit(f"invalid --country '{country}'. valid values: {valid}")
    return country


def read_terms(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def mask_proxy(proxy: str) -> str:
    value = proxy
    for scheme in PROXY_SCHEMES:
        if value.lower().startswith(scheme):
            value = value[len(scheme) :]
            break
    if "@" in value:
        value = value.rsplit("@", 1)[1]
    return value


def format_proxy_for_requests(proxy: str) -> dict[str, str]:
    value = proxy
    if not any(value.lower().startswith(scheme) for scheme in PROXY_SCHEMES):
        value = f"http://{value}"
    return {"http": value, "https": value}


def read_proxies_file(path: Path) -> list[str]:
    proxies: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        proxies.append(line)
    return proxies


def resolve_proxies(proxies_file: Optional[Path]) -> list[str]:
    if proxies_file is not None:
        if not proxies_file.exists():
            sys.exit(f"--proxies-file {proxies_file} does not exist")
        proxies = read_proxies_file(proxies_file)
        if not proxies:
            sys.exit(f"--proxies-file {proxies_file} resolved to zero usable proxies")
        return proxies

    env_value = os.environ.get("JOBSPY_PROXIES")
    if env_value is None:
        return []
    proxies = [item.strip() for item in env_value.split(",") if item.strip()]
    if not proxies:
        sys.exit("JOBSPY_PROXIES resolved to zero usable proxies")
    return proxies


def require_proxy_for_linkedin(
    sites: list[str], proxies: list[str], allow_unprotected: bool
) -> None:
    if "linkedin" not in sites:
        return
    if proxies:
        return
    if allow_unprotected:
        print(
            "WARNING: querying LinkedIn with no proxy configured. "
            "The IP making these requests can be rate-limited or blocked by LinkedIn.",
            file=sys.stderr,
        )
        return
    sys.exit(
        "refusing to query LinkedIn without a proxy: LinkedIn aggressively "
        "rate-limits the guest endpoint and can block the IP making these "
        "requests. Supply proxies with --proxies-file or the JOBSPY_PROXIES "
        "env var, or pass --i-understand-linkedin-without-proxy to proceed "
        "anyway at your own risk."
    )


def _fetch_egress_ip(proxies: Optional[dict[str, str]], timeout: float) -> str:
    response = requests.get(IP_ECHO_URL, proxies=proxies, timeout=timeout)
    response.raise_for_status()
    return response.json()["ip"]


def preflight_proxies(
    proxies: list[str],
    *,
    timeout: float = IP_ECHO_TIMEOUT,
    fetch_ip: Callable[[Optional[dict[str, str]], float], str] = _fetch_egress_ip,
) -> list[str]:
    direct_ip = fetch_ip(None, timeout)
    usable: list[str] = []
    for proxy in proxies:
        masked = mask_proxy(proxy)
        try:
            proxy_ip = fetch_ip(format_proxy_for_requests(proxy), timeout)
        except Exception as exc:
            print(f"{masked} -> failed ({exc})")
            continue
        if proxy_ip == direct_ip:
            print(f"{masked} -> failed (same IP as direct connection: {proxy_ip})")
            continue
        print(f"{masked} -> ok ({proxy_ip})")
        usable.append(proxy)
    return usable


class LinkedInBlockDetector(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.setLevel(logging.ERROR)
        self.blocked = False
        self.reason: Optional[str] = None

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if BLOCK_MESSAGE_429 in message:
            self.blocked = True
            self.reason = BLOCK_MESSAGE_429
        elif BLOCK_MESSAGE_BAD_PROXY in message:
            self.blocked = True
            self.reason = BLOCK_MESSAGE_BAD_PROXY


def install_block_detector() -> LinkedInBlockDetector:
    logger = logging.getLogger(LINKEDIN_LOGGER_NAME)
    detector = LinkedInBlockDetector()
    logger.addHandler(detector)
    return detector


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        import pandas as pd

        if value is pd.NaT:
            return None
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
    except ImportError:
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    return value


def flatten_job(row: dict[str, Any], search_term: str, country: str) -> dict[str, Any]:
    job: dict[str, Any] = {field: json_safe(row.get(field)) for field in OUTPUT_FIELDS}
    job["company_name"] = json_safe(row.get("company") or row.get("company_name"))
    job["search_term"] = search_term
    job["country"] = country
    for key, value in row.items():
        if key not in job:
            job[key] = json_safe(value)
    return job


def fetch_term(
    term: str,
    sites: list[str],
    results_wanted: int,
    hours_old: int,
    location: str,
    country: str,
    proxies: list[str],
    linkedin_fetch_description: bool,
) -> list[dict[str, Any]]:
    df = scrape_jobs(
        site_name=sites,
        search_term=term,
        location=location or None,
        results_wanted=results_wanted,
        hours_old=hours_old,
        country_indeed=country,
        proxies=proxies,
        linkedin_fetch_description=linkedin_fetch_description,
    )
    if df is None or df.empty:
        return []
    records = df.to_dict(orient="records")
    return [flatten_job(record, term, country) for record in records]


def run(
    terms_file: Path,
    sites: list[str],
    results_wanted: int,
    hours_old: int,
    location: str,
    country: str,
    output: Path,
    proxies: list[str],
    linkedin_fetch_description: bool,
    delay_between_terms: float,
    detector: Optional[LinkedInBlockDetector],
) -> None:
    terms = read_terms(terms_file)
    jobs: list[dict[str, Any]] = []
    aborted = False
    abort_reason: Optional[str] = None
    for index, term in enumerate(terms):
        jobs.extend(
            fetch_term(
                term,
                sites,
                results_wanted,
                hours_old,
                location,
                country,
                proxies,
                linkedin_fetch_description,
            )
        )
        if detector is not None and detector.blocked:
            aborted = True
            abort_reason = (
                f"blocked while fetching term '{term}' ({detector.reason}); "
                f"collected {len(jobs)} jobs before stopping"
            )
            break
        if delay_between_terms > 0 and index < len(terms) - 1:
            time.sleep(delay_between_terms)

    payload: dict[str, Any] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "terms": terms,
        "country": country,
        "proxy_count": len(proxies),
        "jobs": jobs,
    }
    if aborted:
        payload["aborted"] = True
        payload["abort_reason"] = abort_reason
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"terms: {len(terms)}")
    print(f"jobs fetched: {len(jobs)}")
    print(f"wrote {output}")
    if aborted:
        sys.exit(f"aborted: {abort_reason}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch raw job listings via python-jobspy and dump them to JSON."
    )
    parser.add_argument("--terms-file", type=Path, default=DEFAULT_TERMS_FILE)
    parser.add_argument("--sites", type=str, default="indeed,linkedin")
    parser.add_argument("--results-wanted", type=int, default=None)
    parser.add_argument("--hours-old", type=int, default=720)
    parser.add_argument("--location", type=str, default="")
    parser.add_argument("--country", type=str, default="usa")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--proxies-file", type=Path, default=None)
    parser.add_argument(
        "--i-understand-linkedin-without-proxy", action="store_true"
    )
    parser.add_argument("--allow-partial-proxies", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--linkedin-fetch-description", action="store_true")
    parser.add_argument("--delay-between-terms", type=float, default=0.0)
    args = parser.parse_args()

    country = validate_country(args.country)
    sites = [s.strip() for s in args.sites.split(",") if s.strip()]

    proxies = resolve_proxies(args.proxies_file)

    require_proxy_for_linkedin(
        sites, proxies, args.i_understand_linkedin_without_proxy
    )

    if proxies:
        if args.skip_preflight:
            print(
                "WARNING: --skip-preflight set; proxies were not verified to "
                "be carrying traffic before this run.",
                file=sys.stderr,
            )
        else:
            usable = preflight_proxies(proxies)
            failed_count = len(proxies) - len(usable)
            if failed_count > 0:
                if not args.allow_partial_proxies:
                    sys.exit(
                        f"preflight failed for {failed_count} of {len(proxies)} "
                        "proxies; pass --allow-partial-proxies to continue "
                        "with only the passing ones"
                    )
                if not usable:
                    sys.exit(
                        "preflight failed for all configured proxies; "
                        "nothing usable to continue with"
                    )
                print(
                    f"continuing with {len(usable)} of {len(proxies)} "
                    "proxies after preflight"
                )
            proxies = usable

    results_wanted = args.results_wanted
    if results_wanted is None:
        results_wanted = 25 if "linkedin" in sites else 50

    detector = install_block_detector() if "linkedin" in sites else None

    run(
        args.terms_file,
        sites,
        results_wanted,
        args.hours_old,
        args.location,
        country,
        args.output,
        proxies,
        args.linkedin_fetch_description,
        args.delay_between_terms,
        detector,
    )


if __name__ == "__main__":
    main()
