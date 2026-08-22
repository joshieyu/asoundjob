#!/usr/bin/env python3
"""Phase 2: Discover correct careers URLs for bad ones.

For each bad URL:
  1. Try jobs.<domain> and careers.<domain> subdomains
  2. Fetch homepage and look for careers links
  3. Try common careers paths
Saves to url_discovery_results.json incrementally.
"""

import json
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")

CHECK_FILE    = "url_check_results.json"
RESULT_FILE   = "url_discovery_results.json"
MAX_WORKERS   = 40
TIMEOUT       = 6
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

CAREERS_KEYWORDS = [
    "career", "careers", "job", "jobs", "join us", "join our team",
    "opportunities", "vacancies", "open positions", "open roles",
    "hiring", "work for", "work with", "we're hiring",
]


def check_url(url, method="HEAD"):
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code in (405, 403, 501):
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True)
            r.close()
        return r.status_code, r.url
    except:
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True, verify=False)
            r.close()
            return r.status_code, r.url
        except:
            return None, None


def is_ok(status):
    return status is not None and 200 <= status < 400


def find_careers_link(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True).lower()
        href = a["href"]
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        for kw in CAREERS_KEYWORDS:
            if kw in text:
                full = urljoin(base_url, href)
                candidates.append((len(text), full))
                break
        href_lower = href.lower()
        for kw in ["career", "jobs", "opportunities", "vacancies", "hiring"]:
            if kw in href_lower:
                full = urljoin(base_url, href)
                candidates.append((0, full))
                break
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def discover(url):
    """Try to find the real careers URL."""
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    domain_parts = p.netloc.split(".")
    if domain_parts[0] == "www":
        domain_parts = domain_parts[1:]
    base_domain = ".".join(domain_parts)

    # 1. Try subdomains: jobs., careers.
    for sub in ["jobs", "careers", "career", "job"]:
        candidate = f"https://{sub}.{base_domain}"
        status, final = check_url(candidate)
        if is_ok(status):
            if final and urlparse(final).path not in ("", "/"):
                return final
            if final and root_domain(final) != root:
                return final
            # Check content
            status2, final2 = check_url(candidate, method="GET")
            if is_ok(status2) and final2 and urlparse(final2).path not in ("", "/"):
                return final2

    # 2. Crawl homepage
    try:
        r = requests.get(root, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, verify=False)
        if r.status_code < 400 and r.text:
            found = find_careers_link(root, r.text)
            if found:
                status, final = check_url(found)
                if is_ok(status):
                    return final or found
    except:
        pass

    # 3. Try common paths
    paths = [
        "/careers", "/careers/", "/careers.html", "/careers.php", "/careers.aspx",
        "/jobs", "/jobs/", "/jobs.html",
        "/about/careers", "/about-us/careers", "/about/jobs",
        "/en/careers", "/us/careers", "/us/en/careers",
        "/company/careers", "/career", "/career/",
        "/en-us/careers", "/en/careers/", "/en-us/careers/",
        "/global/en/careers", "/en/jobs", "/en/about/careers",
        "/work-with-us", "/join-us", "/join", "/team",
        "/us/careers.html", "/us/careers.aspx",
        "/about/careers.html", "/about-us/careers.html",
        "/careers/search", "/careers/jobs",
    ]
    orig_path = p.path
    if orig_path and orig_path != "/":
        paths.insert(0, orig_path)

    for path in paths:
        candidate = root + path
        status, final = check_url(candidate)
        if is_ok(status):
            if final and root_domain(final) == root and urlparse(final).path in ("", "/"):
                continue
            return final

    return None


def root_domain(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def main():
    with open(CHECK_FILE, "r") as f:
        check_results = json.load(f)

    bad_urls = [u for u, v in check_results.items() if v["status"] == "bad"]
    print(f"Bad URLs to discover: {len(bad_urls)}")

    # Load existing results
    try:
        with open(RESULT_FILE, "r") as f:
            results = json.load(f)
        print(f"Loaded {len(results)} existing discoveries, resuming...")
    except FileNotFoundError:
        results = {}

    todo = [u for u in bad_urls if u not in results]
    print(f"Remaining: {len(todo)}")

    t0 = time.time()
    done = 0
    found_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(discover, u): u for u in todo}
        for fut in as_completed(futures):
            url = futures[fut]
            try:
                found = fut.result()
            except Exception:
                found = None
            results[url] = found
            done += 1
            if found:
                found_count += 1
            if done % 50 == 0:
                with open(RESULT_FILE, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"  {done}/{len(todo)} done ({time.time()-t0:.0f}s) "
                      f"| found: {found_count}")

    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    total_found = sum(1 for v in results.values() if v)
    print(f"\nPhase 2 complete: {total_found}/{len(bad_urls)} URLs discovered ({time.time()-t0:.0f}s)")
    print(f"Results saved to {RESULT_FILE}")


if __name__ == "__main__":
    main()
