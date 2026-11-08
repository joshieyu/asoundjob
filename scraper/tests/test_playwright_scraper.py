from __future__ import annotations

import asyncio
import unittest
from typing import Optional

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.base import ScrapeError
from scraper.scrapers.playwright_scraper import PlaywrightScraper

CAREERS_URL = "https://example.com/careers"

NO_JOBS_HTML = "<html><body><h1>Careers</h1><p>Nothing here yet.</p></body></html>"

JOBS_HTML = (
    "<html><body>"
    '<a href="https://example.com/careers/jobs/1">Audio DSP Engineer</a>'
    '<a href="https://example.com/careers/jobs/2">Acoustic Engineer</a>'
    "</body></html>"
)


def make_company() -> Company:
    return Company(
        id=0,
        name="Acme Audio",
        slug="acme-audio",
        category="Professional Audio & Live Sound",
        careers_url=CAREERS_URL,
        verified=True,
    )


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status


class FakePage:
    def __init__(self, goto_results: list, html: str) -> None:
        self._goto_results = list(goto_results)
        self.html = html
        self.goto_calls: list = []

    async def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls.append((url, wait_until, timeout))
        result = self._goto_results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    async def wait_for_timeout(self, ms):
        return None

    async def content(self):
        return self.html


class FakeContext:
    def __init__(self, page: FakePage) -> None:
        self._page = page
        self.closed = False

    async def add_init_script(self, script):
        return None

    async def new_page(self):
        return self._page

    async def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, context: FakeContext) -> None:
        self._context = context

    async def new_context(self):
        return self._context


def make_scraper(goto_results: list, html: str) -> PlaywrightScraper:
    scraper = PlaywrightScraper(load_settings())
    page = FakePage(goto_results, html)
    context = FakeContext(page)
    browser = FakeBrowser(context)

    async def fake_ensure_browser():
        return browser

    scraper._ensure_browser = fake_ensure_browser  # type: ignore[method-assign]
    return scraper


class TestPlaywrightStatusAwareErrors(unittest.TestCase):
    def _run(self, goto_results: list, html: str):
        async def go():
            scraper = make_scraper(goto_results, html)
            try:
                jobs = await scraper.fetch_jobs(make_company())
                return scraper, jobs, None
            except ScrapeError as exc:
                return scraper, None, exc

        return asyncio.run(go())

    def test_404_and_no_jobs_raises_http_status_error(self) -> None:
        scraper, jobs, exc = self._run([FakeResponse(404)], NO_JOBS_HTML)
        self.assertIsNone(jobs)
        assert exc is not None
        self.assertEqual(str(exc), f"HTTP 404 for {CAREERS_URL}")
        self.assertEqual(scraper._page_status, {})

    def test_200_and_no_jobs_keeps_generic_error(self) -> None:
        scraper, jobs, exc = self._run([FakeResponse(200)], NO_JOBS_HTML)
        self.assertIsNone(jobs)
        assert exc is not None
        self.assertEqual(str(exc), "page loaded but no job links found")
        self.assertEqual(scraper._page_status, {})

    def test_404_with_jobs_found_still_succeeds(self) -> None:
        scraper, jobs, exc = self._run([FakeResponse(404)], JOBS_HTML)
        self.assertIsNone(exc)
        assert jobs is not None
        self.assertEqual(len(jobs), 2)
        self.assertEqual(scraper._page_status, {})

    def test_goto_returning_none_keeps_generic_error(self) -> None:
        scraper, jobs, exc = self._run([None], NO_JOBS_HTML)
        self.assertIsNone(jobs)
        assert exc is not None
        self.assertEqual(str(exc), "page loaded but no job links found")
        self.assertEqual(scraper._page_status, {})

    def test_timeout_fallback_status_is_used(self) -> None:
        scraper, jobs, exc = self._run(
            [PlaywrightTimeoutError("timed out"), FakeResponse(404)], NO_JOBS_HTML
        )
        self.assertIsNone(jobs)
        assert exc is not None
        self.assertEqual(str(exc), f"HTTP 404 for {CAREERS_URL}")
        self.assertEqual(scraper._page_status, {})

    def test_timeout_fallback_with_200_keeps_generic_error(self) -> None:
        scraper, jobs, exc = self._run(
            [PlaywrightTimeoutError("timed out"), FakeResponse(200)], NO_JOBS_HTML
        )
        self.assertIsNone(jobs)
        assert exc is not None
        self.assertEqual(str(exc), "page loaded but no job links found")
        self.assertEqual(scraper._page_status, {})


class TestRecordStatusSeam(unittest.TestCase):
    def _run(self, url: str, response: Optional[FakeResponse]):
        async def go():
            scraper = PlaywrightScraper(load_settings())
            scraper._record_status(url, response)
            return scraper

        return asyncio.run(go())

    def test_record_status_stores_by_url(self) -> None:
        scraper = self._run("https://a.example/careers", FakeResponse(500))
        self.assertEqual(scraper._page_status, {"https://a.example/careers": 500})

    def test_record_status_ignores_none_response(self) -> None:
        scraper = self._run("https://a.example/careers", None)
        self.assertEqual(scraper._page_status, {})



class TestPlaywrightPaginationErrors(unittest.TestCase):
    START = "https://www.metacareers.com/jobsearch/?q=audio"

    def _scraper(self, pages: dict, statuses: dict) -> PlaywrightScraper:
        scraper = PlaywrightScraper(load_settings())

        async def fake_fetch(url: str) -> str:
            scraper._page_status[url] = statuses.get(url, 200)
            return pages[url]

        scraper.fetch_page_html = fake_fetch  # type: ignore[method-assign]
        return scraper

    def _company(self) -> Company:
        company = make_company()
        company.careers_url = self.START
        return company

    def card(self, job_id: int) -> str:
        return f'<a href="/profile/job_details/{job_id}"><h3>Audio Role {job_id}</h3></a>'

    def test_error_status_on_a_later_page_fails_the_scrape(self) -> None:
        pages = {
            self.START: self.card(1),
            self.START + "&page=2": "<html><body>Too many requests</body></html>",
        }
        async def go():
            scraper = self._scraper(pages, {self.START + "&page=2": 429})
            try:
                await scraper.fetch_jobs(self._company())
            except ScrapeError as exc:
                return scraper, exc
            return scraper, None

        scraper, exc = asyncio.run(go())
        self.assertIsNotNone(exc)
        self.assertIn("HTTP 429", str(exc))
        self.assertEqual(scraper._page_status, {})

    def test_clean_pagination_returns_every_page(self) -> None:
        pages = {
            self.START: self.card(1),
            self.START + "&page=2": self.card(2),
            self.START + "&page=3": "<html><body></body></html>",
        }
        async def go():
            scraper = self._scraper(pages, {})
            return scraper, await scraper.fetch_jobs(self._company())

        scraper, jobs = asyncio.run(go())
        self.assertEqual(sorted(job.title for job in jobs), ["Audio Role 1", "Audio Role 2"])
        self.assertEqual(scraper._page_status, {})


if __name__ == "__main__":
    unittest.main()
