#!/usr/bin/env python3
"""Follow through verified careers landing pages to find the TRUE job-listing URL.

Many companies have a careers landing page on their own site that links to
an ATS platform (Greenhouse, Lever, Workday, etc.) where jobs are actually
listed. This script follows those links and updates the URL to point to
the actual job listings.

Also checks for "Search Jobs" / "View Jobs" / "Browse Jobs" buttons that
lead to a deeper job search page.
"""

import json
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")

INPUT_FILE  = "audio_companies_verified.json"
OUTPUT_FILE = "follow_through_results.json"
MAX_WORKERS = 30
TIMEOUT     = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# ATS domains - if the careers page links to these, follow them
ATS_DOMAINS = {
    "boards.greenhouse.io", "job-boards.greenhouse.io", "greenhouse.com",
    "jobs.lever.co", "lever.co",
    "apply.workable.com", "careers.workable.com", "workable.com",
    "workdayjobs.com", "myworkdayjobs.com", "myworkdaysite.com",
    "careers.icims.com", "icims.com",
    "careers.jobvite.com", "jobvite.com",
    "jobs.smartrecruiters.com", "smartrecruiters.com",
    "app.ashbyhq.com", "ashbyhq.com",
    "jobs.breezy.hr", "breezy.hr",
    "bamboohr.com", "applytojob.com", "recruitee.com",
    "pinpointhq.com", "adp.com", "workforcenow",
    "taleo.net", "brassring.com", "successfactors.com",
    "force.com", "livecareer.com", "indeed.com/cmp/",
    "linkedin.com/jobs", "linkedin.com/company",
}

# Button/link text that indicates a link to actual job listings
JOB_SEARCH_KEYWORDS = [
    "search jobs", "search positions", "search openings",
    "view jobs", "view positions", "view openings", "view all jobs",
    "view all positions", "view all openings",
    "browse jobs", "browse positions", "browse openings",
    "find jobs", "find positions", "find openings",
    "see jobs", "see positions", "see openings", "see all jobs",
    "see all positions", "see all openings",
    "all jobs", "all positions", "all openings",
    "current openings", "current jobs", "current positions",
    "open jobs", "open positions", "open openings",
    "job listings", "list of jobs", "job board",
    "apply now", "apply today", "start your application",
    "explore jobs", "explore positions", "explore openings",
    "explore opportunities", "explore roles",
    "shop jobs", "shop positions", "shop openings",
]


def fetch(url, timeout=TIMEOUT):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout,
                         allow_redirects=True, verify=False)
        return r
    except:
        return None


def is_ats_url(url):
    """Check if URL is on a known ATS domain."""
    url_lower = url.lower()
    p = urlparse(url_lower)
    host = p.netloc
    
    for ats in ATS_DOMAINS:
        if ats in host or ats in url_lower:
            return True
    return False


def is_already_ats(url):
    """Check if the current URL is already an ATS job-listing page."""
    return is_ats_url(url)


def find_job_search_link(base_url, html):
    """Find links to actual job search/listing pages."""
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True).lower()
        href = a["href"]
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        
        full_url = urljoin(base_url, href)
        
        # Check if it's a link to an ATS platform
        if is_ats_url(full_url):
            candidates.append((0, full_url, "ATS"))
            continue
        
        # Check if link text matches job search keywords
        for kw in JOB_SEARCH_KEYWORDS:
            if kw in text:
                candidates.append((1, full_url, "search_button"))
                break
        
        # Check if href contains job search patterns
        href_lower = href.lower()
        if any(kw in href_lower for kw in ["search", "listing", "board", "all-jobs",
                                            "all-jobs", "job-search", "find-jobs"]):
            candidates.append((2, full_url, "href_pattern"))
    
    if not candidates:
        return None
    
    # Sort: ATS links first, then search buttons, then href patterns
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def follow_through(url, company_name):
    """Follow a careers landing page to find the true job-listing URL.
    
    Returns (final_url, was_updated) or (original_url, False) if no better URL found.
    """
    # If URL is already on an ATS platform, it's likely the true job page
    if is_already_ats(url):
        return url, False
    
    # Fetch the page
    r = fetch(url)
    if not r or r.status_code >= 400:
        return url, False
    
    # Check if we were redirected to an ATS
    if is_ats_url(r.url) and r.url != url:
        return r.url, True
    
    # Look for links to ATS or job search pages
    found = find_job_search_link(r.url, r.text)
    if found:
        # Verify the found URL
        r2 = fetch(found)
        if r2 and r2.status_code < 400:
            # If it's an ATS URL, it's the true job page
            if is_ats_url(r2.url):
                return r2.url, True
            # If it redirected to an ATS, use that
            if is_ats_url(r2.url) and r2.url != found:
                return r2.url, True
            # If it's a different page on the same domain with job listings
            text_lower = r2.text.lower()
            if sum(1 for ind in ["career", "job", "position", "opening", "apply",
                                  "opportunit", "recruit"] if ind in text_lower) >= 3:
                # Only update if this looks more like a job listing page
                if r2.url != url:
                    return r2.url, True
    
    return url, False


def main():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)
    
    verified = [e for e in data if e["verified"]]
    print(f"Verified companies to follow-through: {len(verified)}")
    
    # Load existing results
    try:
        with open(OUTPUT_FILE, "r") as f:
            results = json.load(f)
        print(f"Loaded {len(results)} existing results, resuming...")
    except FileNotFoundError:
        results = {}
    
    todo = [e for e in verified if e["name"] not in results]
    print(f"Remaining: {len(todo)}")
    print()
    
    t0 = time.time()
    done = 0
    updated_count = 0
    
    def process(entry):
        url = entry["careers_url"]
        name = entry["name"]
        final_url, was_updated = follow_through(url, name)
        return name, {"url": final_url, "updated": was_updated}
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process, e): e for e in todo}
        for fut in as_completed(futures):
            try:
                name, result = fut.result()
            except Exception:
                name = futures[fut]["name"]
                result = {"url": futures[fut]["careers_url"], "updated": False}
            results[name] = result
            done += 1
            if result["updated"]:
                updated_count += 1
            if done % 50 == 0:
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"  {done}/{len(todo)} done ({time.time()-t0:.0f}s) "
                      f"| updated: {updated_count}")
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    total_updated = sum(1 for v in results.values() if v.get("updated"))
    print(f"\nFollow-through complete: {total_updated}/{len(results)} URLs updated ({time.time()-t0:.0f}s)")
    print(f"Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
