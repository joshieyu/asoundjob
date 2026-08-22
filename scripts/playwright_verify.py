#!/usr/bin/env python3
"""Verify careers URLs using Playwright with a single shared browser.

Uses async Playwright with a pool of browser pages for concurrency.
Much more stable than launching a browser per task.
"""

import asyncio
import json
import time
import warnings

from playwright.async_api import async_playwright

warnings.filterwarnings("ignore")

INPUT_FILE  = "../data/audio_companies_final.json"
RESULT_FILE = "../data/playwright_results.json"
MAX_CONCURRENT = 6      # number of concurrent pages
TIMEOUT_MS  = 15000     # navigation timeout
WAIT_MS     = 2000      # extra wait for JS rendering

CAREERS_INDICATORS = [
    "career", "job", "position", "opening", "vacanc", "hiring",
    "apply", "opportunit", "role", "recruit", "join our",
    "search jobs", "browse job", "view job", "equal opportunity",
    "benefit", "employee",
    "karriere", "carriere", "emploi", "empleo", "lavoro",
    "stellen", "採用", "求人", "招聘", "채용", "vagas",
    "trabaja", "working at", "work with us", "we're hiring",
    "life at", "our people", "talent", "workforce",
]

ATS_DOMAINS = [
    "greenhouse.io", "greenhouse.com", "lever.co", "workable.com",
    "workdayjobs.com", "myworkdayjobs.com", "icims.com", "jobvite.com",
    "smartrecruiters.com", "ashbyhq.com", "bamboohr.com", "applytojob.com",
    "recruitee.com", "pinpointhq.com", "breezy.hr", "adp.com",
    "workforcenow", "taleo.net", "brassring.com", "successfactors.com",
    "metacareers.com", "amazon.jobs",
]


def is_ats_url(url):
    url_lower = url.lower()
    return any(ats in url_lower for ats in ATS_DOMAINS)


async def verify_url(context, url, semaphore):
    """Verify a single URL using a shared browser context."""
    async with semaphore:
        page = await context.new_page()
        try:
            response = await page.goto(url, timeout=TIMEOUT_MS, wait_until="domcontentloaded")

            if response is None:
                return False, url, "no_response"

            status = response.status
            if status >= 400:
                return False, url, f"http_{status}"

            # Wait for JS rendering
            await page.wait_for_timeout(WAIT_MS)

            final_url = page.url

            # Check if redirected to an ATS
            if is_ats_url(final_url):
                return True, final_url, "ats_redirect"

            # Get page content
            try:
                content = await page.content()
            except:
                return False, url, "content_error"

            # Check for careers content
            text_lower = content.lower()
            score = sum(1 for ind in CAREERS_INDICATORS if ind in text_lower)
            if score >= 2:
                return True, final_url, f"content_match_{score}"

            # Check for careers links on the page (landing page -> ATS)
            try:
                links = await page.eval_on_selector_all(
                    "a[href]",
                    """els => els.map(e => ({
                        text: (e.innerText || '').toLowerCase(),
                        href: e.href
                    }))"""
                )
                for link in links:
                    text = link.get("text", "")
                    href = link.get("href", "")
                    careers_kws = ["career", "job", "join us", "opportunit", "hiring",
                                   "view job", "search job", "browse job"]
                    if any(kw in text for kw in careers_kws):
                        if is_ats_url(href):
                            return True, href, "ats_link_found"
                        if href != url and href.startswith("http"):
                            return True, href, "careers_link_found"
            except:
                pass

            return False, url, "no_careers_content"

        except Exception as e:
            err = str(e)
            if "net::ERR" in err or "Timeout" in err:
                return False, url, "network_error"
            return False, url, "exception"
        finally:
            try:
                await page.close()
            except:
                pass


async def main():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    unverified = [e for e in data if not e["verified"]]
    print(f"Unverified companies to check: {len(unverified)}")

    # Load existing results (but clear the failed executor_error ones)
    try:
        with open(RESULT_FILE, "r") as f:
            results = json.load(f)
        # Clear executor_error entries - they need re-checking
        results = {k: v for k, v in results.items() if v.get("reason") != "executor_error"}
        print(f"Loaded {len(results)} valid existing results, re-checking rest...")
    except FileNotFoundError:
        results = {}

    todo = [e for e in unverified if e["name"] not in results]
    print(f"Remaining: {len(todo)}")
    print()

    t0 = time.time()
    done = 0
    verified_count = sum(1 for v in results.values() if v["verified"])
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0 Safari/537.36",
            locale="en-US",
        )

        async def work(entry):
            url = entry["careers_url"]
            name = entry["name"]
            is_ok, final_url, reason = await verify_url(context, url, semaphore)
            return name, {
                "verified": is_ok,
                "url": final_url,
                "original_url": url,
                "reason": reason,
            }

        # Process in batches to avoid overwhelming memory
        batch_size = 50
        for i in range(0, len(todo), batch_size):
            batch = todo[i:i + batch_size]
            tasks = [asyncio.create_task(work(e)) for e in batch]
            for coro in asyncio.as_completed(tasks):
                try:
                    name, result = await coro
                except Exception:
                    name = batch[tasks.index(coro)]["name"] if tasks.index(coro) < len(batch) else "unknown"
                    result = {"verified": False, "url": "", "original_url": "", "reason": "async_error"}
                results[name] = result
                done += 1
                if result["verified"]:
                    verified_count += 1

            # Checkpoint after each batch
            with open(RESULT_FILE, "w") as f:
                json.dump(results, f, indent=2)
            elapsed = time.time() - t0
            print(f"  {done}/{len(todo)} done ({elapsed:.0f}s) "
                  f"| verified: {verified_count} "
                  f"| rate: {done/max(elapsed,1):.1f}/s")

        await context.close()
        await browser.close()

    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    total_verified = sum(1 for v in results.values() if v["verified"])
    print(f"\nPlaywright verification complete: {total_verified}/{len(results)} verified ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    asyncio.run(main())
