#!/usr/bin/env python3
"""Deep crawl v2 - find careers URLs by crawling company websites ONLY.

No ATS pattern guessing. Instead:
  1. Crawl homepage, find ALL links pointing to known ATS domains
  2. Multi-language careers keyword detection
  3. Sitemap parsing
  4. Subdomain and path guessing (content-verified)
  5. Checkpointing every 25 entries
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
RESULT_FILE = "deep_crawl_v2_results.json"
MAX_WORKERS = 30
TIMEOUT     = 5

HEADER_SETS = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,*/*",
    },
]

# ATS domains - if we find a link to these FROM the company's own site, trust it
ATS_DOMAINS = [
    "greenhouse.io", "greenhouse.com", "lever.co", "workable.com",
    "workdayjobs.com", "myworkdayjobs.com", "icims.com", "jobvite.com",
    "smartrecruiters.com", "ashbyhq.com", "bamboohr.com", "applytojob.com",
    "recruitee.com", "pinpointhq.com", "breezy.hr", "adp.com",
    "workforcenow", "taleo.net", "brassring.com", "successfactors.com",
    "apply.workable", "boards.greenhouse", "jobs.lever",
    "jobs.smartrecruiters", "careers.jobvite", "app.ashbyhq",
    "apply.ashbyhq", "jobs.breezy", "pinpointhq",
]

# Multi-language careers keywords for link text matching
CAREERS_TEXT_KEYWORDS = [
    # English
    "career", "careers", "job", "jobs", "join us", "join our team",
    "opportunities", "vacancies", "open positions", "open roles",
    "hiring", "work for", "work with", "we're hiring", "work at",
    "life at", "our team", "current opening", "job opening",
    "job listing", "search jobs", "browse jobs", "view jobs",
    "see openings", "explore careers", "employment",
    # German
    "karriere", "stellen", "stellenangebote", "arbeiten bei", "wir suchen",
    "bewerbung", "offene stellen", "jobbörse",
    # French
    "carriere", "carrieres", "emploi", "emplois", "travail",
    "recrutement", "offres d'emploi", "nous rejoindre",
    # Spanish
    "empleo", "trabajo", "trabajos", "carrera", "oportunidades",
    "únete", "unete", "ofertas de empleo", "vacantes",
    # Italian
    "carriera", "lavoro", "lavori", "opportunità", "opportunita",
    "lavora con noi", "posizioni aperte",
    # Japanese
    "採用", "求人", "キャリア", "就職", "募集", "人事",
    # Chinese
    "加入我们", "招聘", "人才", "招贤", "诚聘",
    # Korean
    "채용", "취업", "인재", "입사",
    # Portuguese
    "carreira", "emprego", "trabalho", "vagas",
    # Dutch
    "vacatures", "banen", "werken", "solliciteren",
    # Other
    "recruit", "recruitment", "talent", "human resources",
]

# Keywords for href matching
CAREERS_HREF_KEYWORDS = [
    "career", "careers", "job", "jobs", "opportunit", "vacanc",
    "hiring", "recruit", "karriere", "carriere", "emploi", "empleo",
    "trabajo", "lavoro", "stellen", "arbeit", "vacature", "werken",
    "採用", "求人", "招聘", "加入", "채용", "vagas",
    "workforce", "workdayjobs", "myworkday", "talent", "employment",
]


def fetch(url, header_idx=0, timeout=TIMEOUT):
    headers = HEADER_SETS[header_idx % len(HEADER_SETS)]
    try:
        r = requests.get(url, headers=headers, timeout=timeout,
                         allow_redirects=True, verify=False)
        return r
    except Exception:
        if header_idx < len(HEADER_SETS) - 1:
            return fetch(url, header_idx + 1, timeout)
        return None


def head_check(url, timeout=TIMEOUT):
    """Quick HEAD check - NO fallback from 403."""
    for headers in HEADER_SETS:
        try:
            r = requests.head(url, headers=headers, timeout=timeout,
                              allow_redirects=True, verify=False)
            # Only fall back to GET for 405 (method not allowed)
            if r.status_code == 405:
                r = requests.get(url, headers=headers, timeout=timeout,
                                 allow_redirects=True, stream=True, verify=False)
                r.close()
            if 200 <= r.status_code < 400:
                return r.status_code, r.url
        except:
            continue
    return None, None


def is_ok(status):
    return status is not None and 200 <= status < 400


def root_domain(url):
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def find_all_links(base_url, html):
    """Extract ALL links from HTML, categorized."""
    soup = BeautifulSoup(html, "html.parser")
    links = []  # (text, href, full_url)
    
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        href = a["href"]
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        full_url = urljoin(base_url, href)
        links.append((text, href, full_url))
    
    return links


def is_careers_link(text, href, full_url):
    """Check if a link is likely a careers page."""
    text_lower = text.lower()
    href_lower = href.lower()
    full_lower = full_url.lower()
    
    # Check link text for careers keywords
    for kw in CAREERS_TEXT_KEYWORDS:
        if kw in text_lower:
            return True
    
    # Check href for careers keywords
    for kw in CAREERS_HREF_KEYWORDS:
        if kw in href_lower:
            return True
    
    # Check if link points to a known ATS domain
    for ats in ATS_DOMAINS:
        if ats in full_lower:
            return True
    
    return False


def verify_careers_page(url):
    """Verify a URL is actually a careers page by checking its content."""
    r = fetch(url)
    if not r or r.status_code >= 400:
        return False, url
    
    # Check if redirected to an error/blocked page
    if any(kw in r.url.lower() for kw in ["forbidden", "error", "block", "403", "404"]):
        return False, r.url
    
    # Check page content for careers indicators
    text_lower = r.text.lower()
    careers_indicators = [
        "career", "job", "position", "opening", "vacanc", "hiring",
        "apply", "opportunit", "role", "recruit", "join our",
        "search jobs", "browse job", "view job", "equal opportunity",
        "karriere", "carriere", "emploi", "empleo", "lavoro",
        "stellen", "採用", "求人", "招聘", "채용", "vagas",
    ]
    indicator_count = sum(1 for ind in careers_indicators if ind in text_lower)
    
    # Need at least 2 indicators to confirm it's a careers page
    return indicator_count >= 2, r.url


def parse_sitemap(url, depth=0, max_depth=2):
    """Fetch sitemap and extract career-related URLs."""
    if depth > max_depth:
        return []
    r = fetch(url, timeout=5)
    if not r or r.status_code >= 400:
        return []
    
    text = r.text
    if "<sitemapindex" in text:
        sub_urls = re.findall(r'<loc>(.+?)</loc>', text)
        results = []
        for sub_url in sub_urls[:10]:
            results.extend(parse_sitemap(sub_url, depth + 1, max_depth))
        return results
    
    urls = re.findall(r'<loc>(.+?)</loc>', text)
    career_urls = []
    for u in urls:
        u_lower = u.lower()
        if any(kw in u_lower for kw in CAREERS_HREF_KEYWORDS):
            career_urls.append(u)
        # Also check for ATS domains in sitemap URLs
        for ats in ATS_DOMAINS:
            if ats in u_lower:
                career_urls.append(u)
                break
    return career_urls


def deep_crawl_v2(url, company_name):
    """Comprehensive careers URL discovery - NO ATS guessing."""
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    domain_parts = p.netloc.split(".")
    if domain_parts[0] == "www":
        domain_parts = domain_parts[1:]
    base_domain = ".".join(domain_parts)
    
    # 1. Crawl homepage and find careers links
    r = fetch(root)
    if r and r.status_code < 400 and r.text:
        links = find_all_links(root, r.text)
        
        # Find careers-related links
        careers_links = []
        ats_links = []
        for text, href, full_url in links:
            if is_careers_link(text, href, full_url):
                # Separate ATS links from same-domain links
                if any(ats in full_url.lower() for ats in ATS_DOMAINS):
                    ats_links.append(full_url)
                else:
                    careers_links.append(full_url)
        
        # Try ATS links first (these are the actual job listing pages)
        for link in ats_links[:3]:
            is_real, final = verify_careers_page(link)
            if is_real:
                return final
        
        # Try same-domain careers links
        for link in careers_links[:5]:
            is_real, final = verify_careers_page(link)
            if is_real:
                return final
        
        # 2. Check sitemap
        for sitemap_path in ["/sitemap.xml", "/sitemap_index.xml",
                             "/sitemap-index.xml", "/sitemaps.xml"]:
            sm_url = root + sitemap_path
            sm_r = fetch(sm_url, timeout=5)
            if sm_r and sm_r.status_code < 400:
                sitemap_career_urls = parse_sitemap(sm_url)
                if sitemap_career_urls:
                    for career_url in sitemap_career_urls[:3]:
                        is_real, final = verify_careers_page(career_url)
                        if is_real:
                            return final
                    break
    
    # 3. Try subdomains (content-verified)
    for sub in ["jobs", "careers", "career"]:
        candidate = f"https://{sub}.{base_domain}"
        is_real, final = verify_careers_page(candidate)
        if is_real:
            return final
    
    # 4. Try common paths (content-verified)
    paths = [
        "/careers", "/careers/", "/careers.html", "/careers.php",
        "/careers.aspx", "/jobs", "/jobs/", "/jobs.html",
        "/about/careers", "/about-us/careers", "/about/jobs",
        "/en/careers", "/us/careers", "/us/en/careers",
        "/company/careers", "/career", "/career/",
        "/en-us/careers", "/en/careers/", "/en-us/careers/",
        "/global/en/careers", "/en/jobs", "/en/about/careers",
        "/work-with-us", "/join-us", "/join", "/team",
        "/us/careers.html", "/us/careers.aspx",
        "/about/careers.html", "/about-us/careers.html",
        "/careers/search", "/careers/jobs", "/careers/openings",
        "/us/about/careers", "/us/company/careers",
        "/de/karriere", "/fr/carriere", "/es/empleo",
        "/ja/careers", "/zh/careers", "/ko/careers",
        "/job-opportunities", "/job-openings", "/employment",
        "/about/careers/", "/about-us/careers/",
        "/company/careers/", "/career/opportunities",
        "/careers/en", "/careers/us", "/careers/global",
        "/our-team", "/people", "/join-our-team",
        "/us/en/careers/", "/global/careers",
        "/content/careers", "/pages/careers",
        "/careers/en-us", "/careers/us-en",
        "/en/careers.html", "/fr/careers", "/de/careers",
        "/us/jobs", "/en/jobs/", "/us/en/jobs",
    ]
    orig_path = p.path
    if orig_path and orig_path != "/":
        paths.insert(0, orig_path)
    
    for path in paths:
        candidate = root + path
        is_real, final = verify_careers_page(candidate)
        if is_real:
            # Avoid pages that just redirect to homepage
            if root_domain(final) == root and urlparse(final).path in ("", "/"):
                continue
            return final
    
    return None


def main():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)
    
    unverif = [e for e in data if not e["verified"]]
    print(f"Unverified companies: {len(unverif)}")
    
    # Load existing results
    try:
        with open(RESULT_FILE, "r") as f:
            results = json.load(f)
        print(f"Loaded {len(results)} existing results, resuming...")
    except FileNotFoundError:
        results = {}
    
    todo = [e for e in unverif if e["name"] not in results]
    print(f"Remaining: {len(todo)}")
    print()
    
    t0 = time.time()
    done = 0
    found_count = 0
    
    def crawl(entry):
        return entry["name"], deep_crawl_v2(entry["careers_url"], entry["name"])
    
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
                with open(RESULT_FILE, "w") as f:
                    json.dump(results, f, indent=2)
                print(f"  {done}/{len(todo)} done ({time.time()-t0:.0f}s) "
                      f"| found: {found_count} | total: {len(results)}")
    
    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    total_found = sum(1 for v in results.values() if v)
    print(f"\nDeep crawl v2 complete: {total_found}/{len(results)} URLs found ({time.time()-t0:.0f}s)")
    print(f"Results saved to {RESULT_FILE}")


if __name__ == "__main__":
    main()
