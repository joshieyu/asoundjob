#!/usr/bin/env python3
"""Verify careers URLs - Phase 1 only (check existing URLs).

Saves results to url_check_results.json for resumability.
"""

import json
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

warnings.filterwarnings("ignore")

INPUT_FILE  = "audio_companies.json"
RESULT_FILE = "url_check_results.json"
MAX_WORKERS = 30
TIMEOUT     = 12
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def check_url(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code in (405, 403, 501):
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True)
            r.close()
        return r.status_code, r.url
    except requests.exceptions.SSLError:
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True, stream=True, verify=False)
            r.close()
            return r.status_code, r.url
        except Exception:
            return None, None
    except Exception:
        return None, None


def main():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)
    urls = sorted(set(e["careers_url"] for e in data))
    print(f"Checking {len(urls)} unique URLs...")

    # Load existing results if any
    try:
        with open(RESULT_FILE, "r") as f:
            results = json.load(f)
        print(f"Loaded {len(results)} existing results, resuming...")
    except FileNotFoundError:
        results = {}

    todo = [u for u in urls if u not in results]
    print(f"Remaining: {len(todo)}")

    t0 = time.time()
    done = 0

    def verify(url):
        status, final = check_url(url)
        if status and 200 <= status < 400:
            return url, {"status": "ok", "code": status, "final": final or url}
        # Retry with GET
        status, final = check_url(url)
        if status and 200 <= status < 400:
            return url, {"status": "ok", "code": status, "final": final or url}
        return url, {"status": "bad", "code": status, "final": final}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(verify, u): u for u in todo}
        for fut in as_completed(futures):
            url, result = fut.result()
            results[url] = result
            done += 1
            if done % 100 == 0:
                # Checkpoint
                with open(RESULT_FILE, "w") as f:
                    json.dump(results, f, indent=2)
                ok = sum(1 for v in results.values() if v["status"] == "ok")
                print(f"  {done}/{len(todo)} done ({time.time()-t0:.0f}s) "
                      f"| total: {ok} ok, {len(results)-ok} bad")

    # Final save
    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    ok = sum(1 for v in results.values() if v["status"] == "ok")
    bad = sum(1 for v in results.values() if v["status"] == "bad")
    print(f"\nPhase 1 complete: {ok} OK, {bad} bad ({time.time()-t0:.0f}s)")
    print(f"Results saved to {RESULT_FILE}")


if __name__ == "__main__":
    main()
