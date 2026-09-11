from __future__ import annotations

import asyncio
import unittest

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.base import BaseScraper, ScrapeError, ScrapeResult
from scraper.scrapers.pipeline import ScrapePipeline

GREENHOUSE_PAGE = (
    "<html><body><iframe "
    'src="https://boards.greenhouse.io/embed/job_board?for=acmeaudio">'
    "</iframe></body></html>"
)


def make_company(scrape_method: str = "http") -> Company:
    return Company(
        id=7,
        name="Acme Audio",
        slug="acme-audio",
        category="Professional Audio & Live Sound",
        careers_url="https://acmeaudio.example/careers",
        scrape_method=scrape_method,
    )


class RecordingScraper(BaseScraper):
    name = "recording"

    def __init__(self, settings, html: str, fail: bool) -> None:
        super().__init__(settings)
        self.html = html
        self.fail = fail

    async def fetch_jobs(self, company):
        self._last_html = self.html
        if self.fail:
            raise ScrapeError("page loaded but no job links found")
        return []


class TestHtmlPreservedOnFailure(unittest.TestCase):
    def test_failed_scrape_keeps_html(self) -> None:
        scraper = RecordingScraper(load_settings(), GREENHOUSE_PAGE, fail=True)
        result = asyncio.run(scraper.scrape(make_company()))
        self.assertFalse(result.success)
        self.assertEqual(result.html, GREENHOUSE_PAGE)

    def test_successful_scrape_still_keeps_html(self) -> None:
        scraper = RecordingScraper(load_settings(), GREENHOUSE_PAGE, fail=False)
        result = asyncio.run(scraper.scrape(make_company()))
        self.assertTrue(result.success)
        self.assertEqual(result.html, GREENHOUSE_PAGE)


class TestDiscoveryOnFailure(unittest.TestCase):
    def _run(self, html: str) -> tuple[ScrapeResult, list]:
        persisted: list = []

        async def go():
            settings = load_settings()
            pipeline = ScrapePipeline(settings)
            pipeline._persist_ats_discovery = (  # type: ignore[method-assign]
                lambda company_id, ats_type, ats_slug, overwrite=False: persisted.append(
                    (company_id, ats_type, ats_slug)
                )
            )
            pipeline._board_claimed_elsewhere = (  # type: ignore[method-assign]
                lambda company_id, ats_type, ats_slug: False
            )
            failing = RecordingScraper(settings, html, fail=True)
            pipeline.http = failing  # type: ignore[assignment]
            pipeline._playwright_scraper = lambda: failing  # type: ignore[method-assign]
            pipeline._stealth_scraper = lambda: failing  # type: ignore[method-assign]
            return await pipeline.scrape_company(make_company())

        return asyncio.run(go()), persisted

    def test_discovery_runs_when_every_attempt_fails(self) -> None:
        result, persisted = self._run(GREENHOUSE_PAGE)
        self.assertFalse(result.success)
        self.assertIn((7, "greenhouse", "acmeaudio"), persisted)

    def test_no_discovery_when_page_has_no_ats(self) -> None:
        result, persisted = self._run("<html><body>No openings</body></html>")
        self.assertFalse(result.success)
        self.assertEqual(persisted, [])


WORKDAY_PAGE = (
    "<html><body>"
    '<a href="https://boseallaboutme.wd503.myworkdayjobs.com/Bose_Careers">Jobs</a>'
    "</body></html>"
)


class TestStoredAtsSelfHealing(unittest.TestCase):
    def _run(self, html: str, stored_type: str, stored_slug: str) -> list:
        persisted: list = []

        async def go():
            settings = load_settings()
            pipeline = ScrapePipeline(settings)
            pipeline._persist_ats_discovery = (  # type: ignore[method-assign]
                lambda company_id, ats_type, ats_slug, overwrite=False: persisted.append(
                    (ats_type, ats_slug, overwrite)
                )
            )
            pipeline._board_claimed_elsewhere = (  # type: ignore[method-assign]
                lambda company_id, ats_type, ats_slug: False
            )
            failing = RecordingScraper(settings, html, fail=True)
            for key in list(pipeline._ats_map):
                pipeline._ats_map[key] = failing
            pipeline.http = failing  # type: ignore[assignment]
            pipeline._playwright_scraper = lambda: failing  # type: ignore[method-assign]
            pipeline._stealth_scraper = lambda: failing  # type: ignore[method-assign]
            company = make_company()
            company.ats_type = stored_type
            company.ats_slug = stored_slug
            return await pipeline.scrape_company(company)

        asyncio.run(go())
        return persisted

    def test_failed_stored_route_is_corrected(self) -> None:
        persisted = self._run(WORKDAY_PAGE, "workday", "Bose_Careers")
        self.assertIn(
            ("workday", "boseallaboutme.wd503/Bose_Careers", True), persisted
        )

    def test_unchanged_slug_is_not_rewritten(self) -> None:
        persisted = self._run(
            WORKDAY_PAGE, "workday", "boseallaboutme.wd503/Bose_Careers"
        )
        self.assertEqual(persisted, [])

    def test_no_overwrite_when_no_stored_ats(self) -> None:
        persisted = self._run(WORKDAY_PAGE, "", "")
        self.assertTrue(persisted)
        self.assertTrue(all(entry[2] is False for entry in persisted))


class TestBoardOwnership(unittest.TestCase):
    def test_board_claimed_by_another_company_is_not_persisted(self) -> None:
        persisted: list = []

        async def go():
            settings = load_settings()
            pipeline = ScrapePipeline(settings)
            pipeline._persist_ats_discovery = (  # type: ignore[method-assign]
                lambda *args, **kwargs: persisted.append(args)
            )
            pipeline._board_claimed_elsewhere = (  # type: ignore[method-assign]
                lambda company_id, ats_type, ats_slug: True
            )
            failing = RecordingScraper(settings, GREENHOUSE_PAGE, fail=True)
            pipeline.http = failing  # type: ignore[assignment]
            pipeline._playwright_scraper = lambda: failing  # type: ignore[method-assign]
            pipeline._stealth_scraper = lambda: failing  # type: ignore[method-assign]
            return await pipeline.scrape_company(make_company())

        asyncio.run(go())
        self.assertEqual(persisted, [])


class TestSharedBoardDedupe(unittest.TestCase):
    def _companies(self):
        from scraper.models import Company

        return [
            Company(
                id=78, name="Apple", slug="apple", category="Consumer Electronics & Tech",
                careers_url="https://jobs.apple.com/en-us/search",
                ats_type="apple", ats_slug="",
            ),
            Company(
                id=166, name="Beats by Dre", slug="beats",
                category="Headphones & Personal Audio",
                careers_url="https://www.apple.com/careers/",
                ats_type="apple", ats_slug="",
            ),
            Company(
                id=900, name="Sonos", slug="sonos", category="Hi-Fi & Consumer Speakers",
                careers_url="https://sonos.wd1.myworkdayjobs.com/Sonos",
                ats_type="workday", ats_slug="sonos.wd1/Sonos",
            ),
        ]

    def test_same_board_different_urls_is_deduped(self) -> None:
        from scraper.main import _dedupe_shared_urls

        keep, skip = _dedupe_shared_urls(self._companies())
        self.assertEqual([c.name for c in keep], ["Apple", "Sonos"])
        self.assertEqual([c.name for c in skip], ["Beats by Dre"])

    def test_uncorroborated_board_does_not_claim(self) -> None:
        from scraper.main import _dedupe_shared_urls
        from scraper.models import Company

        rows = [
            Company(
                id=1, name="Dalet Digital Media", slug="dalet", category="x",
                careers_url="https://jobs.dalet.com/",
                ats_type="breezy", ats_slug="assets-cdn",
            ),
            Company(
                id=2, name="Flowkey", slug="flowkey", category="x",
                careers_url="https://flowkey.breezy.hr/",
                ats_type="breezy", ats_slug="assets-cdn",
            ),
        ]
        keep, skip = _dedupe_shared_urls(rows)
        self.assertEqual([c.name for c in keep], ["Dalet Digital Media", "Flowkey"])
        self.assertEqual(skip, [])

    def test_a_foreign_tenant_does_not_claim_another_company(self) -> None:
        from scraper.main import _dedupe_shared_urls
        from scraper.models import Company

        rows = [
            Company(
                id=1, name="Toyota", slug="toyota", category="x",
                careers_url="https://careers.toyota.com/us/en",
                ats_type="workday", ats_slug="toyota.wd503/TMNA",
            ),
            Company(
                id=2, name="TrueFire", slug="truefire", category="x",
                careers_url="https://truefire.com/careers",
                ats_type="workday", ats_slug="toyota.wd503/TMNA",
            ),
        ]
        keep, skip = _dedupe_shared_urls(rows)
        self.assertEqual([c.name for c in keep], ["Toyota", "TrueFire"])
        self.assertEqual(skip, [])

    def test_a_corroborated_board_still_claims(self) -> None:
        from scraper.main import _dedupe_shared_urls
        from scraper.models import Company

        rows = [
            Company(
                id=1, name="Sonos", slug="sonos", category="x",
                careers_url="https://sonos.wd1.myworkdayjobs.com/Sonos",
                ats_type="workday", ats_slug="sonos.wd1/Sonos",
            ),
            Company(
                id=2, name="Sonos Europe", slug="sonos-eu", category="x",
                careers_url="https://www.sonos.com/en/careers",
                ats_type="workday", ats_slug="sonos.wd1/Sonos",
            ),
        ]
        keep, skip = _dedupe_shared_urls(rows)
        self.assertEqual([c.name for c in keep], ["Sonos"])
        self.assertEqual([c.name for c in skip], ["Sonos Europe"])

    def test_url_duplicates_are_still_deduped_without_any_ats(self) -> None:
        from scraper.main import _dedupe_shared_urls
        from scraper.models import Company

        rows = [
            Company(id=1, name="A", slug="a", category="x",
                    careers_url="https://shared.example/careers"),
            Company(id=2, name="B", slug="b", category="x",
                    careers_url="https://shared.example/careers"),
        ]
        keep, skip = _dedupe_shared_urls(rows)
        self.assertEqual([c.name for c in keep], ["A"])
        self.assertEqual([c.name for c in skip], ["B"])

    def test_companies_without_ats_are_untouched(self) -> None:
        from scraper.main import _dedupe_shared_urls
        from scraper.models import Company

        rows = [
            Company(id=1, name="A", slug="a", category="x",
                    careers_url="https://a.example/careers"),
            Company(id=2, name="B", slug="b", category="x",
                    careers_url="https://b.example/careers"),
        ]
        keep, skip = _dedupe_shared_urls(rows)
        self.assertEqual(len(keep), 2)
        self.assertEqual(skip, [])


if __name__ == "__main__":
    unittest.main()


SUCCESSFACTORS_COMPANY_URL = "https://careers.example.com/search/"


def make_sf_company() -> Company:
    return Company(
        id=11,
        name="Hearing Co",
        slug="hearing-co",
        category="Hearing & Audiology",
        careers_url=SUCCESSFACTORS_COMPANY_URL,
        scrape_method="http",
    )


class StubJob:
    """Minimal stand-in for a RawJob; reconcile is not exercised here."""


class SucceedingScraper(BaseScraper):
    name = "generic"

    async def fetch_jobs(self, company):
        self._last_html = "<html><body>one page of jobs</body></html>"
        return [StubJob()]


class FailingAts(BaseScraper):
    name = "successfactors"

    def can_handle(self, company) -> bool:
        return True

    async def fetch_jobs(self, company):
        self._last_html = ""
        raise ScrapeError("read timed out")


class TestFallbackAfterAtsClaimIsPartial(unittest.TestCase):
    """A dedicated scraper recognising a board and then failing means the
    generic fallback is seeing, at best, page one. Trusting it to retire
    everything it did not see cost one real board 261 live jobs."""

    def _run(self, *, ats_fails: bool, stored_ats: bool = False) -> ScrapeResult:
        async def go():
            settings = load_settings()
            pipeline = ScrapePipeline(settings)
            pipeline._persist_ats_discovery = (  # type: ignore[method-assign]
                lambda *a, **k: None
            )
            pipeline._board_claimed_elsewhere = (  # type: ignore[method-assign]
                lambda *a, **k: False
            )
            generic = SucceedingScraper(settings)
            pipeline.http = generic  # type: ignore[assignment]
            pipeline._playwright_scraper = lambda: generic  # type: ignore[method-assign]
            pipeline._stealth_scraper = lambda: generic  # type: ignore[method-assign]

            company = make_sf_company()
            if ats_fails:
                failing = FailingAts(settings)
                if stored_ats:
                    company.ats_type = "successfactors"
                    pipeline._ats_map["successfactors"] = failing  # type: ignore[index]
                else:
                    pipeline.successfactors = failing  # type: ignore[assignment]
            return await pipeline.scrape_company(company)

        return asyncio.run(go())

    def test_fallback_is_partial_when_an_ats_claimed_and_failed(self) -> None:
        result = self._run(ats_fails=True)
        self.assertTrue(result.success)
        self.assertTrue(
            result.partial,
            "fallback after a failed ATS claim must suppress deactivation",
        )

    def test_fallback_is_partial_when_the_stored_ats_failed(self) -> None:
        result = self._run(ats_fails=True, stored_ats=True)
        self.assertTrue(result.success)
        self.assertTrue(result.partial)

    def test_plain_fallback_still_allows_deactivation(self) -> None:
        """No ATS ever claimed this board, so the generic read is the whole
        truth and stale jobs should still be retired."""

        async def go():
            settings = load_settings()
            pipeline = ScrapePipeline(settings)
            pipeline._persist_ats_discovery = (  # type: ignore[method-assign]
                lambda *a, **k: None
            )
            pipeline._board_claimed_elsewhere = (  # type: ignore[method-assign]
                lambda *a, **k: False
            )
            generic = SucceedingScraper(settings)
            pipeline.http = generic  # type: ignore[assignment]
            pipeline._playwright_scraper = lambda: generic  # type: ignore[method-assign]
            pipeline._stealth_scraper = lambda: generic  # type: ignore[method-assign]
            # A plain careers page: no ATS scraper recognises this URL, so the
            # generic read is authoritative. (The /search/ path used above is
            # claimed by the real SuccessFactors scraper on URL shape alone.)
            company = make_company()
            return await pipeline.scrape_company(company)

        result = asyncio.run(go())
        self.assertTrue(result.success)
        self.assertFalse(result.partial)
