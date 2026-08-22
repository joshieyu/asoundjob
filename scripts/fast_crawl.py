#!/usr/bin/env python3
"""Fast deep crawl for remaining unverified companies.

Optimized: HEAD-check paths first, only content-verify on 200s.
Limited to top 15 most common paths.
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

INPUT_FILE  = "deep_crawl_v2_results.json"  # Resume from here
DATA_FILE   = "audio_companies_verified.json"
OUTPUT_FILE = "deep_crawl_v2_results.json"
MAX_WORKERS = 40
TIMEOUT     = 4

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

CAREERS_TEXT_KEYWORDS = [
    "career", "careers", "job", "jobs", "join us", "join our team",
    "opportunities", "vacancies", "open positions", "hiring", "work for",
    "work with", "we're hiring", "life at", "our team", "employment",
    "karriere", "stellen", "arbeiten bei", "bewerbung",
    "carriere", "emploi", "recrutement", "nous rejoindre",
    "empleo", "trabajo", "oportunidades", "únete", "vacantes",
    "carriera", "lavoro", "lavora con noi",
    "採用", "求人", "キャリア", "募集",
    "加入我们", "招聘", "人才",
    "채용", "인재", "입사",
    "recruit", "recruitment", "talent",
]

CAREERS_HREF_KEYWORDS = [
    "career", "careers", "job", "jobs", "opportunit", "vacanc",
    "hiring", "recruit", "karriere", "carriere", "emploi", "empleo",
    "trabajo", "lavoro", "stellen", "arbeit", "採用", "求人", "招聘",
    "加入", "채용", "vagas", "employment", "workforce", "workdayjobs",
]

ATS_DOMAINS = [
    "greenhouse.io", "greenhouse.com", "lever.co", "workable.com",
    "workdayjobs.com", "myworkdayjobs.com", "icims.com", "jobvite.com",
    "smartrecruiters.com", "ashbyhq.com", "bamboohr.com", "applytojob.com",
    "recruitee.com", "pinpointhq.com", "breezy.hr", "adp.com",
    "workforcenow", "taleo.net", "brassring.com", "successfactors.com",
]

TOP_PATHS = [
    "/careers", "/careers/", "/careers.html", "/careers.aspx",
    "/jobs", "/jobs/", "/about/careers", "/about-us/careers",
    "/en/careers", "/us/careers", "/company/careers",
    "/en-us/careers", "/work-with-us", "/join-us", "/career",
    "/career/", "/de/karriere", "/fr/carriere", "/es/empleo",
    "/about/careers.html", "/us/careers.html", "/careers/search",
    "/job-opportunities", "/employment", "/our-team", "/join",
    "/us/en/careers", "/global/en/careers", "/en/jobs",
    "/pages/careers", "/content/careers",
]


def quick_get(url, timeout=TIMEOUT, stream=True):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout,
                         allow_redirects=True, verify=False, stream=stream)
        if stream:
            r.close()
        return r
    except:
        return None


def quick_head(url, timeout=TIMEOUT):
    try:
        r = requests.head(url, headers=HEADERS, timeout=timeout,
                          allow_redirects=True, verify=False)
        if r.status_code == 405:
            r = quick_get(url, timeout, stream=True)
        return r
    except:
        return None


def is_ok(r):
    return r is not None and 200 <= r.status_code < 400


def verify_content(url, timeout=TIMEOUT):
    """Full GET + content check."""
    r = quick_get(url, timeout, stream=False)
    if not r or r.status_code >= 400:
        return False
    if any(kw in r.url.lower() for kw in ["forbidden", "error", "block"]):
        return False
    text_lower = r.text.lower()
    indicators = ["career", "job", "position", "opening", "vacanc", "hiring",
                  "apply", "opportunit", "role", "recruit", "join our",
                  "karriere", "carriere", "emploi", "empleo", "lavoro",
                  "stellen", "採用", "求人", "招聘", "채용", "vagas"]
    return sum(1 for ind in indicators if ind in text_lower) >= 2


def root_domain(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def fast_crawl(url, company_name):
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    domain_parts = p.netloc.split(".")
    if domain_parts[0] == "www":
        domain_parts = domain_parts[1:]
    base_domain = ".".join(domain_parts)

    # 1. Crawl homepage (once)
    r = quick_get(root, stream=False)
    if r and r.status_code < 400 and r.text:
        soup = BeautifulSoup(r.text, "html.parser")
        candidates = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(" ", strip=True).lower()
            href = a["href"]
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full_url = urljoin(root, href)
            full_lower = full_url.lower()
            href_lower = href.lower()

            matched = False
            for kw in CAREERS_TEXT_KEYWORDS:
                if kw in text:
                    matched = True
                    break
            if not matched:
                for kw in CAREERS_HREF_KEYWORDS:
                    if kw in href_lower:
                        matched = True
                        break
            if not matched:
                for ats in ATS_DOMAINS:
                    if ats in full_lower:
                        matched = True
                        break

            if matched:
                score = len(text) if text else 50
                candidates.append((score, full_url))

        if candidates:
            candidates.sort(key=lambda x: x[0])
            # Verify top 3 candidates
            for _, candidate_url in candidates[:3]:
                if verify_content(candidate_url):
                    return candidate_url

        # 2. Check sitemap quickly
        for sm_path in ["/sitemap.xml", "/sitemap_index.xml"]:
            sm_r = quick_get(root + sm_path, stream=False)
            if sm_r and sm_r.status_code < 400:
                sm_urls = re.findall(r'<loc>(.+?)</loc>', sm_r.text)
                career_sm = [u for u in sm_urls if
                             any(kw in u.lower() for kw in CAREERS_HREF_KEYWORDS)]
                for u in career_sm[:2]:
                    if verify_content(u):
                        return u
                break

    # 3. Subdomain HEAD checks
    for sub in ["jobs", "careers"]:
        candidate = f"https://{sub}.{base_domain}"
        r = quick_head(candidate)
        if is_ok(r):
            if urlparse(r.url).path not in ("", "/"):
                return r.url
            if root_domain(r.url) != root:
                return r.url

    # 4. Path HEAD checks (fast, no content verification)
    orig_path = p.path
    paths = list(TOP_PATHS)
    if orig_path and orig_path != "/":
        paths.insert(0, orig_path)

    for path in paths:
        candidate = root + path
        r = quick_head(candidate)
        if is_ok(r):
            final = r.url
            # Skip redirects to homepage
            if root_domain(final) == root and urlparse(final).path in ("", "/"):
                continue
            return final

    return None


def main():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    with open(OUTPUT_FILE, "r") as f:
        results = json.load(f)

    unverif = [e for e in data if not e["verified"]]
    todo = [e for e in unverif if e["name"] not in results]
    print(f"Total unverified: {len(unverif)}")
    print(f"Already processed: {len(results)}")
    print(f"Remaining: {len(todo)}")
    print()

    t0 = time.time()
    done = 0
    found_count = sum(1 for v in results.values() if v)

    def crawl(entry):
        return entry["name"], fast_crawl(entry["careers_url"], entry["name"])

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(crawl, e): e for e in todo}
        for fut in as_completed(futures):
            try:
                name, found = fut.result()
            except Exception:
                name = futures[fut]["name"]
                found = None
            results[name] = found
            done += 1
            if found:
                found_count += 1
            if done % 25 == 0:
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(results, f, indent=2)
                elapsed = time.time() - t0
                print(f"  {done}/{len(todo)} done ({elapsed:.0f}s) "
                      f"| found: {found_count} | rate: {done/max(elapsed,1):.1f}/s")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    total_found = sum(1 for v in results.values() if v)
    print(f"\nComplete: {total_found}/{len(results)} URLs found ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
