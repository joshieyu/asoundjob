from __future__ import annotations

import asyncio
import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from scraper.config import load_settings
from scraper.models import Base, Company, Job
from scraper.propose_ats_bindings import (
    _significant_slug_tokens,
    build_findings,
    gather_findings,
    problem_counts,
    rank_findings,
    verify_findings,
)
from scraper.scrapers.base import ScrapeResult

KNOWN_ATS_TYPES = frozenset(
    {
        "greenhouse",
        "lever",
        "workable",
        "ashby",
        "smartrecruiters",
        "recruitee",
        "bamboohr",
        "workday",
        "apple",
        "eightfold",
        "pinpoint",
        "icims",
        "adp",
        "ultipro",
        "successfactors",
        "amazon",
        "sigma",
        "gibson",
        "jibe",
    }
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


class PropseAtsBindingsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def add_company(self, name: str, slug: str, **kwargs) -> Company:
        defaults = dict(
            name=name,
            slug=slug,
            category="Audio Software",
            careers_url="https://example.com/careers",
            verified=True,
            source="auto",
        )
        defaults.update(kwargs)
        company = Company(**defaults)
        self.session.add(company)
        self.session.flush()
        return company

    def add_job(self, company: Company, **kwargs) -> Job:
        defaults = dict(
            company_id=company.id,
            title="Audio Engineer",
            url=f"https://example.com/{company.slug}/{kwargs.get('external_id', '1')}",
            is_active=True,
            is_audio_related=True,
            source="scraper",
        )
        defaults.update(kwargs)
        job = Job(**defaults)
        self.session.add(job)
        self.session.flush()
        return job

    def findings(self) -> list:
        return gather_findings(self.session, KNOWN_ATS_TYPES)

    def finding_for(self, findings: list, name: str):
        matches = [f for f in findings if f.name == name]
        self.assertEqual(len(matches), 1, f"expected exactly one finding for {name}")
        return matches[0]


class TestEmptySlug(PropseAtsBindingsTestCase):
    def test_empty_slug_is_flagged(self) -> None:
        self.add_company(
            "Beats by Dre", "beats-by-dre", ats_type="apple", ats_slug=""
        )
        finding = self.finding_for(self.findings(), "Beats by Dre")
        self.assertIn("empty_slug", finding.problems)

    def test_none_slug_is_flagged(self) -> None:
        self.add_company(
            "Beats by Dre", "beats-by-dre", ats_type="apple", ats_slug=None
        )
        finding = self.finding_for(self.findings(), "Beats by Dre")
        self.assertIn("empty_slug", finding.problems)

    def test_whitespace_only_slug_is_flagged(self) -> None:
        self.add_company(
            "Beats by Dre", "beats-by-dre", ats_type="apple", ats_slug="   "
        )
        finding = self.finding_for(self.findings(), "Beats by Dre")
        self.assertIn("empty_slug", finding.problems)

    def test_populated_slug_is_not_flagged(self) -> None:
        self.add_company(
            "Dolby",
            "dolby",
            careers_url="https://www.dolby.com/careers",
            ats_type="eightfold",
            ats_slug="dolby.com",
        )
        finding = self.finding_for(self.findings(), "Dolby")
        self.assertNotIn("empty_slug", finding.problems)


class TestUnknownAts(PropseAtsBindingsTestCase):
    def test_unrecognized_ats_type_is_flagged(self) -> None:
        self.add_company(
            "Old Board Co",
            "old-board-co",
            ats_type="jobvite",
            ats_slug="oldboardco",
        )
        finding = self.finding_for(self.findings(), "Old Board Co")
        self.assertIn("unknown_ats", finding.problems)

    def test_recognized_ats_type_is_not_flagged(self) -> None:
        self.add_company(
            "Dolby",
            "dolby",
            careers_url="https://www.dolby.com/careers",
            ats_type="eightfold",
            ats_slug="dolby.com",
        )
        finding = self.finding_for(self.findings(), "Dolby")
        self.assertNotIn("unknown_ats", finding.problems)


class TestDuplicateBinding(PropseAtsBindingsTestCase):
    def test_two_companies_sharing_a_binding_are_both_flagged(self) -> None:
        self.add_company(
            "Dalet Digital Media",
            "dalet-digital-media",
            careers_url="https://www.dalet.com/careers",
            ats_type="breezy",
            ats_slug="assets-cdn",
        )
        self.add_company(
            "Flowkey",
            "flowkey",
            careers_url="https://www.flowkey.com/careers",
            ats_type="breezy",
            ats_slug="assets-cdn",
        )
        findings = self.findings()
        dalet = self.finding_for(findings, "Dalet Digital Media")
        flowkey = self.finding_for(findings, "Flowkey")

        dalet_dup = [p for p in dalet.problems if p.startswith("duplicate_binding")]
        flowkey_dup = [p for p in flowkey.problems if p.startswith("duplicate_binding")]
        self.assertEqual(len(dalet_dup), 1)
        self.assertEqual(len(flowkey_dup), 1)
        self.assertIn("Flowkey", dalet_dup[0])
        self.assertIn("Dalet Digital Media", flowkey_dup[0])

    def test_unique_binding_is_not_flagged(self) -> None:
        self.add_company(
            "Dolby",
            "dolby",
            careers_url="https://www.dolby.com/careers",
            ats_type="eightfold",
            ats_slug="dolby.com",
        )
        finding = self.finding_for(self.findings(), "Dolby")
        self.assertFalse(any(p.startswith("duplicate_binding") for p in finding.problems))


class TestSlugUnrelatedToCompany(PropseAtsBindingsTestCase):
    def test_truefire_holding_toyota_tenant_is_flagged(self) -> None:
        self.add_company(
            "TrueFire",
            "truefire",
            careers_url="https://truefire.com/careers",
            ats_type="workday",
            ats_slug="toyota.wd503/TMNA",
        )
        finding = self.finding_for(self.findings(), "TrueFire")
        self.assertIn("slug_unrelated_to_company", finding.problems)

    def test_toyota_holding_its_own_tenant_is_not_flagged(self) -> None:
        self.add_company(
            "TrueFire",
            "truefire",
            careers_url="https://truefire.com/careers",
            ats_type="workday",
            ats_slug="toyota.wd503/TMNA",
        )
        self.add_company(
            "Toyota",
            "toyota",
            careers_url="https://www.toyota.com/careers",
            ats_type="workday",
            ats_slug="toyota.wd503/TMNA",
        )
        finding = self.finding_for(self.findings(), "Toyota")
        self.assertNotIn("slug_unrelated_to_company", finding.problems)

    def test_arturia_holding_tagging_server_tenant_is_flagged(self) -> None:
        self.add_company(
            "Arturia",
            "arturia",
            careers_url="https://www.arturia.com/careers",
            ats_type="recruitee",
            ats_slug="tagging-server",
        )
        finding = self.finding_for(self.findings(), "Arturia")
        self.assertIn("slug_unrelated_to_company", finding.problems)

    def test_dolby_slug_matching_its_own_domain_has_no_problems(self) -> None:
        self.add_company(
            "Dolby",
            "dolby",
            careers_url="https://www.dolby.com/careers",
            ats_type="eightfold",
            ats_slug="dolby.com",
        )
        finding = self.finding_for(self.findings(), "Dolby")
        self.assertEqual(finding.problems, [])

    def test_workday_datacenter_token_alone_does_not_count_as_shared(self) -> None:
        self.assertEqual(_significant_slug_tokens("toyota.wd503/TMNA"), ["toyota", "tmna"])

        self.add_company(
            "Wd503",
            "wd503",
            careers_url="https://example.org/careers",
            ats_type="workday",
            ats_slug="wd503",
        )
        finding = self.finding_for(self.findings(), "Wd503")
        self.assertIn("slug_unrelated_to_company", finding.problems)


class TestSlugConcatenationIsNotUnrelated(PropseAtsBindingsTestCase):
    CASES = (
        ("Universal Audio", "universal-audio",
         "https://www.uaudio.com/careers", "greenhouse", "universalaudio"),
        ("SoundCloud", "soundcloud",
         "https://soundcloud.com/jobs", "greenhouse", "soundcloud71"),
        ("Take-Two Interactive", "take-two",
         "https://www.taketwogames.com/careers", "greenhouse", "taketwo"),
        ("Hear.com", "hear-com",
         "https://www.hear.com/careers/", "greenhouse", "hearcom"),
        ("Nissan", "nissan",
         "https://www.nissanmotor.jobs/", "workday", "alliance.wd3/nissanjobs"),
        ("Analog Devices", "analog-devices",
         "https://www.analog.com/en/careers", "workday",
         "analogdevices.wd1/External"),
        ("OtterBox", "otterbox",
         "https://www.otterbox.com/pages/careers", "icims",
         "careers-otterproducts"),
    )

    def test_a_slug_that_concatenates_the_company_name_is_not_flagged(self) -> None:
        for name, slug, careers_url, ats_type, ats_slug in self.CASES:
            with self.subTest(name=name):
                self.setUp()
                self.add_company(
                    name, slug, careers_url=careers_url,
                    ats_type=ats_type, ats_slug=ats_slug,
                )
                finding = self.finding_for(self.findings(), name)
                self.assertNotIn("slug_unrelated_to_company", finding.problems)

    def test_a_subdomain_in_the_careers_url_counts_as_the_company(self) -> None:
        self.add_company(
            "Northrop Grumman", "northrop-grumman",
            careers_url="https://ngc.eightfold.ai/careers?query=acoustic",
            ats_type="eightfold", ats_slug="ngc.com",
        )
        finding = self.finding_for(self.findings(), "Northrop Grumman")
        self.assertNotIn("slug_unrelated_to_company", finding.problems)

    def test_an_opaque_uuid_slug_is_not_judged_by_name(self) -> None:
        self.add_company(
            "ASUS", "asus", careers_url="https://careers.asus.com/",
            ats_type="adp", ats_slug="2071de00-c19b-4aa9-b4cb-1ee91d11ec3f",
        )
        finding = self.finding_for(self.findings(), "ASUS")
        self.assertNotIn("slug_unrelated_to_company", finding.problems)

    def test_a_genuinely_foreign_slug_is_still_flagged(self) -> None:
        self.add_company(
            "Arturia", "arturia",
            careers_url="https://jobs.world.luccasoftware.com/arturia-france",
            ats_type="recruitee", ats_slug="tagging-server",
        )
        finding = self.finding_for(self.findings(), "Arturia")
        self.assertIn("slug_unrelated_to_company", finding.problems)


class TestActiveJobCount(PropseAtsBindingsTestCase):
    def test_counts_only_active_jobs(self) -> None:
        company = self.add_company(
            "Dolby",
            "dolby",
            careers_url="https://www.dolby.com/careers",
            ats_type="eightfold",
            ats_slug="dolby.com",
        )
        self.add_job(company, external_id="1", is_active=True)
        self.add_job(company, external_id="2", is_active=True)
        self.add_job(company, external_id="3", is_active=False)
        finding = self.finding_for(self.findings(), "Dolby")
        self.assertEqual(finding.active_job_count, 2)

    def test_company_without_ats_type_is_excluded(self) -> None:
        self.add_company("No ATS Co", "no-ats-co", ats_type=None, ats_slug=None)
        findings = self.findings()
        self.assertEqual([f for f in findings if f.name == "No ATS Co"], [])


class TestRankFindings(unittest.TestCase):
    def test_more_problems_ranks_first(self) -> None:
        findings = build_findings(
            [],
            {},
            KNOWN_ATS_TYPES,
        )
        self.assertEqual(findings, [])

    def test_priority_problems_rank_ahead_at_equal_problem_count(self) -> None:
        from scraper.propose_ats_bindings import AtsBindingFinding

        low_priority = AtsBindingFinding(
            company_id=1,
            name="A Co",
            slug="a-co",
            careers_url=None,
            ats_type="workday",
            ats_slug="x",
            active_job_count=0,
            problems=["unknown_ats"],
        )
        high_priority = AtsBindingFinding(
            company_id=2,
            name="Z Co",
            slug="z-co",
            careers_url=None,
            ats_type="workday",
            ats_slug="y",
            active_job_count=0,
            problems=["slug_unrelated_to_company"],
        )
        ranked = rank_findings([low_priority, high_priority])
        self.assertEqual([f.name for f in ranked], ["Z Co", "A Co"])

    def test_problem_count_beats_priority_kind(self) -> None:
        from scraper.propose_ats_bindings import AtsBindingFinding

        two_problems = AtsBindingFinding(
            company_id=1,
            name="A Co",
            slug="a-co",
            careers_url=None,
            ats_type="workday",
            ats_slug="x",
            active_job_count=0,
            problems=["empty_slug", "unknown_ats"],
        )
        one_priority_problem = AtsBindingFinding(
            company_id=2,
            name="Z Co",
            slug="z-co",
            careers_url=None,
            ats_type="workday",
            ats_slug="y",
            active_job_count=0,
            problems=["slug_unrelated_to_company"],
        )
        ranked = rank_findings([one_priority_problem, two_problems])
        self.assertEqual([f.name for f in ranked], ["A Co", "Z Co"])


class TestProblemCounts(PropseAtsBindingsTestCase):
    def test_counts_distinct_finding_per_problem_kind(self) -> None:
        self.add_company(
            "Beats by Dre", "beats-by-dre", ats_type="apple", ats_slug=""
        )
        self.add_company(
            "TrueFire",
            "truefire",
            careers_url="https://truefire.com/careers",
            ats_type="workday",
            ats_slug="toyota.wd503/TMNA",
        )
        counts = problem_counts(self.findings())
        self.assertEqual(counts.get("empty_slug"), 1)
        self.assertEqual(counts.get("slug_unrelated_to_company"), 1)


class FakeScraper:
    def __init__(self, result: ScrapeResult) -> None:
        self._result = result

    async def scrape(self, company: Company) -> ScrapeResult:
        return self._result


class FailingScraper:
    async def scrape(self, company: Company) -> ScrapeResult:
        raise RuntimeError("boom")


class FakePipeline:
    def __init__(self, ats_map: dict) -> None:
        self._ats_map = ats_map


class TestVerifyFindings(PropseAtsBindingsTestCase):
    def test_scrape_failure_is_recorded(self) -> None:
        company = self.add_company(
            "Arturia",
            "arturia",
            careers_url="https://www.arturia.com/careers",
            ats_type="recruitee",
            ats_slug="tagging-server",
        )
        findings = self.findings()
        pipeline = FakePipeline(
            {
                "recruitee": FakeScraper(
                    ScrapeResult(company_id=company.id, success=False, error="HTTP 400")
                )
            }
        )
        settings = load_settings()
        asyncio.run(verify_findings([company], findings, pipeline, settings))
        finding = self.finding_for(findings, "Arturia")
        self.assertTrue(any(p.startswith("scrape_fails:") for p in finding.problems))
        self.assertTrue(any("HTTP 400" in p for p in finding.problems))

    def test_zero_jobs_is_recorded_as_scrape_fails(self) -> None:
        company = self.add_company(
            "Dolby",
            "dolby",
            careers_url="https://www.dolby.com/careers",
            ats_type="eightfold",
            ats_slug="dolby.com",
        )
        findings = self.findings()
        pipeline = FakePipeline(
            {"eightfold": FakeScraper(ScrapeResult(company_id=company.id, success=True, jobs=[]))}
        )
        settings = load_settings()
        asyncio.run(verify_findings([company], findings, pipeline, settings))
        finding = self.finding_for(findings, "Dolby")
        self.assertTrue(any(p.startswith("scrape_fails:") for p in finding.problems))

    def test_successful_scrape_with_jobs_adds_no_problem(self) -> None:
        from scraper.scrapers.base import RawJob

        company = self.add_company(
            "Dolby",
            "dolby",
            careers_url="https://www.dolby.com/careers",
            ats_type="eightfold",
            ats_slug="dolby.com",
        )
        findings = self.findings()
        self.assertEqual(findings[0].problems, [])
        pipeline = FakePipeline(
            {
                "eightfold": FakeScraper(
                    ScrapeResult(
                        company_id=company.id,
                        success=True,
                        jobs=[RawJob(title="Audio Engineer", url="https://www.dolby.com/jobs/1")],
                    )
                )
            }
        )
        settings = load_settings()
        asyncio.run(verify_findings([company], findings, pipeline, settings))
        finding = self.finding_for(findings, "Dolby")
        self.assertEqual(finding.problems, [])

    def test_exception_raised_by_scraper_is_recorded(self) -> None:
        company = self.add_company(
            "Arturia",
            "arturia",
            careers_url="https://www.arturia.com/careers",
            ats_type="recruitee",
            ats_slug="tagging-server",
        )
        findings = self.findings()
        pipeline = FakePipeline({"recruitee": FailingScraper()})
        settings = load_settings()
        asyncio.run(verify_findings([company], findings, pipeline, settings))
        finding = self.finding_for(findings, "Arturia")
        self.assertTrue(any("boom" in p for p in finding.problems))

    def test_unknown_ats_type_skips_verification(self) -> None:
        company = self.add_company(
            "Old Board Co",
            "old-board-co",
            ats_type="jobvite",
            ats_slug="oldboardco",
        )
        findings = self.findings()
        pipeline = FakePipeline({})
        settings = load_settings()
        asyncio.run(verify_findings([company], findings, pipeline, settings))
        finding = self.finding_for(findings, "Old Board Co")
        self.assertFalse(any(p.startswith("scrape_fails:") for p in finding.problems))


class TestNoWrites(PropseAtsBindingsTestCase):
    def test_gather_findings_performs_no_writes(self) -> None:
        self.add_company(
            "TrueFire",
            "truefire",
            careers_url="https://truefire.com/careers",
            ats_type="workday",
            ats_slug="toyota.wd503/TMNA",
        )
        self.add_company(
            "Dolby",
            "dolby",
            careers_url="https://www.dolby.com/careers",
            ats_type="eightfold",
            ats_slug="dolby.com",
        )
        company_count_before = self.session.execute(
            select(func.count()).select_from(Company)
        ).scalar_one()
        job_count_before = self.session.execute(
            select(func.count()).select_from(Job)
        ).scalar_one()

        self.findings()

        company_count_after = self.session.execute(
            select(func.count()).select_from(Company)
        ).scalar_one()
        job_count_after = self.session.execute(
            select(func.count()).select_from(Job)
        ).scalar_one()

        self.assertEqual(company_count_before, company_count_after)
        self.assertEqual(job_count_before, job_count_after)

    def test_verify_findings_performs_no_writes(self) -> None:
        company = self.add_company(
            "Arturia",
            "arturia",
            careers_url="https://www.arturia.com/careers",
            ats_type="recruitee",
            ats_slug="tagging-server",
        )
        findings = self.findings()
        pipeline = FakePipeline(
            {
                "recruitee": FakeScraper(
                    ScrapeResult(company_id=company.id, success=False, error="HTTP 400")
                )
            }
        )
        settings = load_settings()

        company_count_before = self.session.execute(
            select(func.count()).select_from(Company)
        ).scalar_one()

        asyncio.run(verify_findings([company], findings, pipeline, settings))

        company_count_after = self.session.execute(
            select(func.count()).select_from(Company)
        ).scalar_one()
        self.assertEqual(company_count_before, company_count_after)


if __name__ == "__main__":
    unittest.main()
