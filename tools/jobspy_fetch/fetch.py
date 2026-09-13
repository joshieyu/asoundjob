import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jobspy import scrape_jobs

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


def read_terms(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


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


def flatten_job(row: dict[str, Any], search_term: str) -> dict[str, Any]:
    job: dict[str, Any] = {field: json_safe(row.get(field)) for field in OUTPUT_FIELDS}
    job["company_name"] = json_safe(row.get("company") or row.get("company_name"))
    job["search_term"] = search_term
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
) -> list[dict[str, Any]]:
    df = scrape_jobs(
        site_name=sites,
        search_term=term,
        location=location or None,
        results_wanted=results_wanted,
        hours_old=hours_old,
    )
    if df is None or df.empty:
        return []
    records = df.to_dict(orient="records")
    return [flatten_job(record, term) for record in records]


def run(
    terms_file: Path,
    sites: list[str],
    results_wanted: int,
    hours_old: int,
    location: str,
    output: Path,
) -> None:
    terms = read_terms(terms_file)
    jobs: list[dict[str, Any]] = []
    for term in terms:
        jobs.extend(fetch_term(term, sites, results_wanted, hours_old, location))

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "terms": terms,
        "jobs": jobs,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"terms: {len(terms)}")
    print(f"jobs fetched: {len(jobs)}")
    print(f"wrote {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch raw job listings via python-jobspy and dump them to JSON."
    )
    parser.add_argument("--terms-file", type=Path, default=DEFAULT_TERMS_FILE)
    parser.add_argument("--sites", type=str, default="indeed,linkedin")
    parser.add_argument("--results-wanted", type=int, default=50)
    parser.add_argument("--hours-old", type=int, default=720)
    parser.add_argument("--location", type=str, default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    run(
        args.terms_file,
        sites,
        args.results_wanted,
        args.hours_old,
        args.location,
        args.output,
    )


if __name__ == "__main__":
    main()
