from __future__ import annotations

import asyncio
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper.company_loader import MAX_CAREERS_URLS, careers_urls_for
from scraper.deduplicator import reconcile_company_jobs
from scraper.models import Base, Company, Job
from scraper.normalizer import NormalizedJob
from scraper.scrapers.base import BaseScraper, RawJob, ScrapeError
from scraper.scrapers.pipeline import ScrapePipeline

PRIMARY = "https://jobs.example.com/careers?search=audio"
ACOUSTIC = "https://jobs.example.com/careers?search=acoustic"
DSP = "https://jobs.example.com/careers?search=dsp"


def make_company(extra=None) -> Company:
    return Company(
        id=7,
        name="Acme Audio",
        slug="acme-audio",
        category="Professional Audio & Live Sound",
        careers_url=PRIMARY,
        extra_careers_urls=extra,
        scrape_method="http",
        audio_scope="native",
    )


class PerUrlScraper(BaseScraper):
    name = "recording"

    def __init__(self, settings, jobs_by_url) -> None:
        super().__init__(settings)
        self.jobs_by_url = jobs_by_url
        self.seen: list[str] = []

    async def fetch_jobs(self, company):
        url = company.careers_url
        self.seen.append(url)
        self._last_html = "<html></html>"
        payload = self.jobs_by_url.get(url)
        if payload is None:
            raise ScrapeError("page loaded but no job links found")
        return payload


def run_pipeline(jobs_by_url, extra):
    from scraper.config import load_settings

    async def go():
        settings = load_settings()
        pipeline = ScrapePipeline(settings)
        scraper = PerUrlScraper(settings, jobs_by_url)
        pipeline.http = scraper  # type: ignore[assignment]
        pipeline._playwright_scraper = lambda: scraper  # type: ignore[method-assign]
        pipeline._stealth_scraper = lambda: scraper  # type: ignore[method-assign]
        pipeline._try_discovery = lambda *a, **k: None  # type: ignore[method-assign]
        result = await pipeline.scrape_company(make_company(extra))
        await pipeline.close()
        return result, scraper.seen

    return asyncio.run(go())


def job(ext: str, title: str) -> RawJob:
    return RawJob(title=title, url=f"https://jobs.example.com/j/{ext}", external_id=ext)


class TestCareersUrlsFor(unittest.TestCase):
    def test_primary_only(self) -> None:
        self.assertEqual(careers_urls_for(make_company()), [PRIMARY])

    def test_primary_first_then_extras(self) -> None:
        self.assertEqual(
            careers_urls_for(make_company([ACOUSTIC, DSP])), [PRIMARY, ACOUSTIC, DSP]
        )

    def test_a_repeated_primary_is_dropped(self) -> None:
        self.assertEqual(careers_urls_for(make_company([PRIMARY, DSP])), [PRIMARY, DSP])

    def test_is_capped(self) -> None:
        extras = [f"https://jobs.example.com/careers?search=q{i}" for i in range(20)]
        self.assertEqual(len(careers_urls_for(make_company(extras))), MAX_CAREERS_URLS)


class TestMultiUrlScrape(unittest.TestCase):
    def test_jobs_from_every_url_are_merged(self) -> None:
        result, seen = run_pipeline(
            {
                PRIMARY: [job("1", "Audio DSP Engineer")],
                ACOUSTIC: [job("2", "Acoustics Quality Director")],
            },
            [ACOUSTIC],
        )
        self.assertTrue(result.success)
        self.assertFalse(result.partial)
        self.assertEqual(seen, [PRIMARY, ACOUSTIC])
        self.assertEqual({j.external_id for j in result.jobs}, {"1", "2"})

    def test_overlapping_jobs_are_deduped(self) -> None:
        result, _ = run_pipeline(
            {
                PRIMARY: [job("1", "Audio DSP Engineer")],
                DSP: [job("1", "Audio DSP Engineer"), job("9", "DSP SW Engineer")],
            },
            [DSP],
        )
        self.assertEqual(len(result.jobs), 2)
        self.assertEqual({j.external_id for j in result.jobs}, {"1", "9"})

    def test_a_failing_extra_url_is_partial_but_still_succeeds(self) -> None:
        result, _ = run_pipeline({PRIMARY: [job("1", "Audio DSP Engineer")]}, [ACOUSTIC])
        self.assertTrue(result.success)
        self.assertTrue(result.partial)
        self.assertFalse(result.trust_empty)
        self.assertEqual([j.external_id for j in result.jobs], ["1"])

    def test_a_failing_primary_still_yields_the_extra(self) -> None:
        result, _ = run_pipeline({ACOUSTIC: [job("2", "Acoustics Director")]}, [ACOUSTIC])
        self.assertTrue(result.success)
        self.assertTrue(result.partial)
        self.assertEqual([j.external_id for j in result.jobs], ["2"])

    def test_all_urls_failing_is_a_failure(self) -> None:
        result, _ = run_pipeline({}, [ACOUSTIC])
        self.assertFalse(result.success)

    def test_a_single_url_company_is_never_partial(self) -> None:
        result, seen = run_pipeline({PRIMARY: [job("1", "Audio DSP Engineer")]}, None)
        self.assertTrue(result.success)
        self.assertFalse(result.partial)
        self.assertEqual(seen, [PRIMARY])


class TestPartialSuppressesDeactivation(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.session = sessionmaker(bind=engine)()
        self.company = Company(
            name="Acme Audio", slug="acme-audio",
            category="Professional Audio & Live Sound",
            careers_url=PRIMARY, verified=True, source="auto", audio_scope="native",
        )
        self.session.add(self.company)
        self.session.flush()
        self.session.add(
            Job(
                company_id=self.company.id, title="Acoustics Quality Director",
                url="https://jobs.example.com/j/2", external_id="2",
                job_categories=["audio_systems"], is_audio_related=True,
                is_active=True, source="scraper",
            )
        )
        self.session.flush()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def _fetched(self) -> list[NormalizedJob]:
        return [
            NormalizedJob(
                title="Audio DSP Engineer",
                url="https://jobs.example.com/j/1",
                external_id="1",
                job_categories=["audio_dsp_embedded"],
                is_audio_related=True,
            )
        ]

    def test_a_complete_scrape_still_deactivates(self) -> None:
        stats = reconcile_company_jobs(
            self.session, self.company, self._fetched(), trust_empty=True
        )
        self.session.flush()
        self.assertEqual(stats.deactivated, 1)

    def test_a_partial_scrape_does_not_deactivate(self) -> None:
        stats = reconcile_company_jobs(
            self.session, self.company, self._fetched(),
            trust_empty=True, allow_deactivation=False,
        )
        self.session.flush()
        self.assertEqual(stats.deactivated, 0)
        self.assertTrue(stats.skipped_deactivation)
        survivor = self.session.execute(
            Job.__table__.select().where(Job.external_id == "2")
        ).mappings().one()
        self.assertTrue(survivor["is_active"])


if __name__ == "__main__":
    unittest.main()
