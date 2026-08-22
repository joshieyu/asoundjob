#!/usr/bin/env python3
"""Re-verify suspicious URLs by checking page content for careers keywords.

Many Phase 2 "fixes" pointed to wrong pages (homepages, blog posts, error
pages). This script fetches each suspicious URL and checks if the page
content actually mentions careers/jobs/hiring.
"""

import json
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")

INPUT_FILE  = "audio_companies_verified.json"
OUTPUT_FILE = "audio_companies_verified.json"  # overwrite
MAX_WORKERS = 20
TIMEOUT     = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Keywords that indicate a real careers page
CONTENT_KEYWORDS = [
    "career", "job", "position", "opening", "vacanc", "hiring",
    "apply", "opportunit", "role", "team", "talent", "recruit",
    "join us", "join our", "work with", "work for", "we're hiring",
    "current opening", "job opening", "job listing", "search jobs",
    "browse job", "equal opportunity", "benefit",
]

# ATS platforms - if URL is on these, it's almost certainly a careers page
ATS_DOMAINS = [
    "workable.com", "greenhouse.io", "lever.co", "workday", "adp.com",
    "icims.com", "jobvite.com", "smartrecruiters.com", "recruitee.com",
    "ashbyhq.com", "apply.", "pinpointhq.com", "namely.com",
    "successfactors.com", "taleo.net", "brassring.com", "icims.com",
    "adpworkforce", "force.com", "myworkdayjobs.com",
]


def is_ats_url(url):
    url_lower = url.lower()
    return any(ats in url_lower for ats in ATS_DOMAINS)


def has_careers_keyword_in_url(url):
    url_lower = url.lower()
    return any(kw in url_lower for kw in ["career", "job", "work", "hire", "join", "talent", "opportunit", "vacanc", "recruit", "employ", "karriere", "carriere"])


def check_content(url):
    """Fetch URL and check if page content indicates a careers page."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, verify=False)
        if r.status_code >= 400:
            return False, r.url
        # Check if redirected to a blocked/error page
        if "forbidden" in r.url.lower() or "error" in r.url.lower() or "block" in r.url.lower():
            return False, r.url
        text = r.text.lower()
        # Check for careers keywords in page content
        keyword_count = sum(1 for kw in CONTENT_KEYWORDS if kw in text)
        return keyword_count >= 2, r.url  # Need at least 2 keywords
    except:
        return False, url


def main():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    # Find suspicious entries: verified but URL doesn't look like careers
    suspicious = []
    for e in data:
        if not e["verified"]:
            continue
        url = e["careers_url"]
        if is_ats_url(url) or has_careers_keyword_in_url(url):
            continue  # Trust these
        suspicious.append(e)

    print(f"Total entries: {len(data)}")
    print(f"Suspicious (need content check): {len(suspicious)}")
    print()

    # Check content of suspicious URLs
    t0 = time.time()
    results = {}  # name -> (is_real_careers, final_url)
    done = 0

    def check(entry):
        url = entry["careers_url"]
        is_real, final = check_content(url)
        return entry["name"], is_real, final

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(check, e): e for e in suspicious}
        for fut in as_completed(futures):
            name, is_real, final = fut.result()
            results[name] = (is_real, final)
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(suspicious)} checked ({time.time()-t0:.0f}s)")

    print(f"Content check done ({time.time()-t0:.0f}s)")

    # Update entries
    demoted = 0
    fixed_again = 0
    for entry in data:
        if entry["name"] not in results:
            continue
        is_real, final = results[entry["name"]]
        if not is_real:
            entry["verified"] = False
            demoted += 1
        elif final and final != entry["careers_url"]:
            entry["careers_url"] = final
            fixed_again += 1

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    verified = sum(1 for e in data if e["verified"])
    unverified = sum(1 for e in data if not e["verified"])
    print(f"\nResults:")
    print(f"  Demoted to unverified: {demoted}")
    print(f"  URL updated after content check: {fixed_again}")
    print(f"  Final verified: {verified}")
    print(f"  Final unverified: {unverified}")


if __name__ == "__main__":
    main()
