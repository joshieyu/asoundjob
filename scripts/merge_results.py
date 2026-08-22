#!/usr/bin/env python3
"""Merge verification results into final audio_companies_verified.json.

Combines:
  - url_check_results.json (Phase 1: existing URL checks)
  - url_discovery_results.json (Phase 2: discovered URLs for bad ones)

Produces:
  - audio_companies_verified.json (updated with fixed URLs + verified flag)
  - verification_report.md (human-readable report)
"""

import json
from collections import Counter
from urllib.parse import urlparse


def main():
    with open("audio_companies.json", "r") as f:
        data = json.load(f)
    with open("url_check_results.json", "r") as f:
        checks = json.load(f)
    with open("url_discovery_results.json", "r") as f:
        discoveries = json.load(f)

    updated = []
    fixes = []
    redirects = []
    unverified = []

    for entry in data:
        url = entry["careers_url"]
        check = checks.get(url, {"status": "bad", "code": None, "final": url})

        if check["status"] == "ok":
            final = check.get("final", url)
            if final and final != url:
                # URL redirected (e.g. http -> https, or /careers -> /careers/)
                redirects.append((entry["name"], url, final))
                entry["careers_url"] = final
            entry["verified"] = True
            updated.append(entry)
        else:
            # Try discovered URL
            discovered = discoveries.get(url)
            if discovered:
                fixes.append((entry["name"], url, discovered))
                entry["careers_url"] = discovered
                entry["verified"] = True
                updated.append(entry)
            else:
                entry["verified"] = False
                unverified.append(entry)
                updated.append(entry)

    # Sort
    updated.sort(key=lambda e: e["name"].lower())

    # Save
    with open("audio_companies_verified.json", "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)

    # Stats
    verified = sum(1 for e in updated if e["verified"])
    unverif = sum(1 for e in updated if not e["verified"])
    print(f"Total companies: {len(updated)}")
    print(f"  Verified:   {verified}")
    print(f"  Unverified: {unverif}")
    print(f"  URL fixes:  {len(fixes)}")
    print(f"  Redirects:  {len(redirects)}")
    print()

    cat_counts = Counter(e["category"] for e in updated)
    verif_by_cat = Counter(e["category"] for e in updated if e["verified"])
    print("By category (verified/total):")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        v = verif_by_cat.get(cat, 0)
        print(f"  {cat}: {v}/{count}")

    # Report
    with open("verification_report.md", "w", encoding="utf-8") as f:
        f.write("# URL Verification Report\n\n")
        f.write(f"- Total companies: {len(updated)}\n")
        f.write(f"- Verified URLs: {verified}\n")
        f.write(f"- Unverified (no careers page found): {unverif}\n")
        f.write(f"- URLs fixed (discovered new URL): {len(fixes)}\n")
        f.write(f"- Redirects followed: {len(redirects)}\n\n")

        f.write(f"## Fixed URLs ({len(fixes)})\n\n")
        f.write("| Company | Old URL | New URL |\n|---|---|---|\n")
        for name, old, new in sorted(fixes):
            f.write(f"| {name} | {old} | {new} |\n")

        f.write(f"\n## Redirected URLs ({len(redirects)})\n\n")
        f.write("| Company | Original URL | Final URL |\n|---|---|---|\n")
        for name, old, new in sorted(redirects):
            f.write(f"| {name} | {old} | {new} |\n")

        f.write(f"\n## Unverified Companies ({unverif})\n\n")
        f.write("No careers page was found. These companies may:\n")
        f.write("- Not have a dedicated careers page\n")
        f.write("- Use a third-party ATS (Greenhouse, Lever, Workday) not linked from homepage\n")
        f.write("- Block automated requests (Cloudflare, etc.)\n")
        f.write("- Have a dead website\n\n")
        f.write("| Company | URL attempted |\n|---|---|\n")
        for e in sorted(unverified, key=lambda x: x["name"].lower()):
            f.write(f"| {e['name']} | {e['careers_url']} |\n")

    print(f"\nReport saved to verification_report.md")
    print(f"Verified JSON saved to audio_companies_verified.json")


if __name__ == "__main__":
    main()
