#!/usr/bin/env python3
"""Merge all verification results into final audio_companies_verified.json.

Combines:
  1. Original verified data
  2. Deep crawl v2 results (new careers URLs found for previously unverified)
  3. Follow-through results (landing pages updated to true job-listing URLs)

Produces:
  - audio_companies_final.json (the definitive output)
  - final_verification_report.md
"""

import json
from collections import Counter


def main():
    with open("audio_companies_verified.json", "r") as f:
        data = json.load(f)
    with open("deep_crawl_v2_results.json", "r") as f:
        deep_crawl = json.load(f)
    with open("follow_through_results.json", "r") as f:
        follow = json.load(f)

    updated = 0
    newly_verified = 0
    url_changed = 0
    changes = []

    for entry in data:
        name = entry["name"]
        original_url = entry["careers_url"]

        # 1. If unverified, check deep crawl results
        if not entry["verified"]:
            crawled = deep_crawl.get(name)
            if crawled:
                entry["careers_url"] = crawled
                entry["verified"] = True
                newly_verified += 1
                changes.append((name, original_url, crawled, "deep_crawl"))

        # 2. If verified, apply follow-through results
        if entry["verified"]:
            ft = follow.get(name)
            if ft:
                if ft["updated"] and ft["url"] != entry["careers_url"]:
                    changes.append((name, entry["careers_url"], ft["url"], "follow_through"))
                    entry["careers_url"] = ft["url"]
                    url_changed += 1

    # Sort
    data.sort(key=lambda e: e["name"].lower())

    # Save
    with open("audio_companies_final.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Stats
    verified = sum(1 for e in data if e["verified"])
    unverified = sum(1 for e in data if not e["verified"])
    deep_crawl_found = sum(1 for c in changes if c[3] == "deep_crawl")
    follow_through_updated = sum(1 for c in changes if c[3] == "follow_through")

    print(f"Final Results:")
    print(f"  Total companies:     {len(data)}")
    print(f"  Verified:            {verified} ({100*verified/len(data):.0f}%)")
    print(f"  Unverified:          {unverified} ({100*unverified/len(data):.0f}%)")
    print(f"  Deep crawl found:    {deep_crawl_found} (newly verified)")
    print(f"  Follow-through:      {follow_through_updated} (URLs updated to true job pages)")
    print()

    # By category
    cat_counts = Counter(e["category"] for e in data)
    verif_by_cat = Counter(e["category"] for e in data if e["verified"])
    print("By category (verified/total):")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        v = verif_by_cat.get(cat, 0)
        pct = 100 * v / count if count else 0
        print(f"  {cat:40s}: {v:3d}/{count:3d} ({pct:.0f}%)")

    # Report
    with open("final_verification_report.md", "w", encoding="utf-8") as f:
        f.write("# Final URL Verification Report\n\n")
        f.write(f"- Total companies: {len(data)}\n")
        f.write(f"- Verified URLs: {verified} ({100*verified/len(data):.0f}%)\n")
        f.write(f"- Unverified: {unverified} ({100*unverified/len(data):.0f}%)\n")
        f.write(f"- Deep crawl recovered: {deep_crawl_found}\n")
        f.write(f"- Follow-through updated: {follow_through_updated}\n\n")

        f.write("## Verification by Category\n\n")
        f.write("| Category | Verified | Total | % |\n|---|---|---|---|\n")
        for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            v = verif_by_cat.get(cat, 0)
            pct = 100 * v / count if count else 0
            f.write(f"| {cat} | {v} | {count} | {pct:.0f}% |\n")

        # Deep crawl changes
        dc_changes = [c for c in changes if c[3] == "deep_crawl"]
        f.write(f"\n## Deep Crawl Recoveries ({len(dc_changes)})\n\n")
        f.write("These companies were previously unverified but a careers page was found by deep crawling.\n\n")
        f.write("| Company | Old URL | New URL |\n|---|---|---|\n")
        for name, old, new, _ in sorted(dc_changes):
            f.write(f"| {name} | {old} | {new} |\n")

        # Follow-through changes
        ft_changes = [c for c in changes if c[3] == "follow_through"]
        f.write(f"\n## Follow-Through Updates ({len(ft_changes)})\n\n")
        f.write("These careers landing pages were updated to point to the actual job-listing page (ATS or job search).\n\n")
        f.write("| Company | Landing Page | True Job URL |\n|---|---|---|\n")
        for name, old, new, _ in sorted(ft_changes):
            f.write(f"| {name} | {old} | {new} |\n")

        # Unverified
        f.write(f"\n## Unverified Companies ({unverified})\n\n")
        f.write("No careers page could be found. These companies may:\n")
        f.write("- Not have a dedicated careers page\n")
        f.write("- Use a third-party ATS not linked from their website\n")
        f.write("- Block automated requests\n")
        f.write("- Have a dead website\n\n")
        f.write("| Company | Category |\n|---|---|\n")
        for e in sorted([e for e in data if not e["verified"]], key=lambda x: x["name"].lower()):
            f.write(f"| {e['name']} | {e['category']} |\n")

    print(f"\nFinal JSON: audio_companies_final.json")
    print(f"Report:     final_verification_report.md")


if __name__ == "__main__":
    main()
