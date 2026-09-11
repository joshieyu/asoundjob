"""Move "internship" from job_type to seniority on existing rows.

An internship is a career stage, not a commitment shape. Holding it in
`job_type` — a single-valued column — meant that a posting saying "Full-time
Internship" recorded `full-time` and lost the internship entirely, because
the full-time pattern is tested first. 11 live rows were in exactly that state.

`scraper/normalizer.py` now classifies the intern family as
`seniority='internship'` and leaves `job_type` for the hours, so newly scraped
rows are already correct. This brings existing rows in line.

    python scripts/migrate_internship_to_level.py            # dry run
    python scripts/migrate_internship_to_level.py --apply
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scraper"))

import sqlite3  # noqa: E402

from scraper.normalizer import detect_seniority, normalize_job_type  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the changes")
    ap.add_argument("--db", default=str(REPO_ROOT / "asoundjob.db"))
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, job_type, seniority FROM jobs"
    ).fetchall()

    updates: list[tuple[str | None, str, int]] = []
    reasons: Counter[str] = Counter()

    for row in rows:
        title = row["title"] or ""
        job_type = row["job_type"]
        seniority = row["seniority"]

        title_says_internship = detect_seniority(title) == "internship"
        tagged_internship = job_type == "internship"
        if not (title_says_internship or tagged_internship):
            continue

        # Trust the title, not the tag. 23 rows carry job_type='internship'
        # while being titled "Global Account Manager", "Sr. CMF Engineer" and
        # the like — the tag came from somewhere other than the title and is
        # demonstrably unreliable. Promoting those to seniority='internship'
        # would launder a bad tag into a bad level.
        new_seniority = "internship" if title_says_internship else seniority
        new_job_type = job_type
        if tagged_internship:
            # "internship" is no longer a valid job_type. Re-derive the hours
            # from the title; None is the honest answer when it does not say.
            new_job_type = normalize_job_type(title)

        if new_seniority == seniority and new_job_type == job_type:
            continue

        if tagged_internship and not title_says_internship:
            reasons["job_type internship -> %s on a row the title says is NOT an internship"
                    % new_job_type] += 1
        elif tagged_internship and new_job_type is None:
            reasons["job_type internship -> NULL (hours not stated)"] += 1
        elif tagged_internship:
            reasons[f"job_type internship -> {new_job_type} (title states hours)"] += 1
        else:
            reasons[f"kept job_type={job_type} (internship-ness was being lost)"] += 1
        if new_seniority != seniority:
            reasons[f"seniority {seniority} -> internship"] += 1

        updates.append((new_job_type, new_seniority, row["id"]))

    print(f"database: {args.db}")
    print(f"rows scanned: {len(rows)}")
    print(f"rows to update: {len(updates)}\n")
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {count:5}  {reason}")

    if not args.apply:
        print("\ndry run — nothing written. Re-run with --apply.")
        return 0

    conn.executemany(
        "UPDATE jobs SET job_type = ?, seniority = ? WHERE id = ?", updates
    )
    conn.commit()
    print(f"\napplied: {len(updates)} rows updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
