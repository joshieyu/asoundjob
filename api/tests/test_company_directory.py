from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.routers import admin as admin_router
from api.routers import companies as companies_router
from api.schemas import CompanyResponse, CompanySuggestionRequest, RejectRequest
from scraper.models import Base, Company, CompanySuggestion, Job


class FakeClient:
    def __init__(self, host: str) -> None:
        self.host = host


class FakeRequest:
    def __init__(self, host: str = "203.0.113.9") -> None:
        self.client = FakeClient(host)


class DirectoryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        companies_router.suggestion_rate_limiter.reset()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def add_company(self, name: str, slug: str, category: str, verified: bool = True):
        company = Company(
            name=name, slug=slug, category=category, verified=verified
        )
        self.session.add(company)
        self.session.flush()
        return company

    def add_job(self, company, title: str, active=True, audio=True):
        job = Job(
            company_id=company.id,
            title=title,
            url=f"https://example.com/{title}",
            is_active=active,
            is_audio_related=audio,
        )
        self.session.add(job)
        self.session.flush()
        return job


class TestBoardCounts(DirectoryCase):
    def test_board_count_excludes_non_audio_and_inactive_jobs(self) -> None:
        company = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        self.add_job(company, "DSP Engineer")
        self.add_job(company, "Warehouse Picker", audio=False)
        self.add_job(company, "Closed Role", active=False)

        result = companies_router.list_companies(
            page=1, per_page=25, sort="board", direction="desc", db=self.session
        )
        row = result["items"][0]
        self.assertEqual(row["board_jobs_count"], 1)
        self.assertEqual(row["active_jobs_count"], 2)

    def test_hiring_only_drops_companies_with_no_board_jobs(self) -> None:
        hiring = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        self.add_job(hiring, "DSP Engineer")
        quiet = self.add_company("Quiet Co", "quiet-co", "Audio Software")
        self.add_job(quiet, "Warehouse Picker", audio=False)

        result = companies_router.list_companies(
            page=1,
            per_page=25,
            hiring_only=True,
            sort="board",
            direction="desc",
            db=self.session,
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["slug"], "acme-audio")

    def test_default_sort_puts_hiring_companies_first(self) -> None:
        quiet = self.add_company("AAA Quiet", "aaa-quiet", "Audio Software")
        self.add_job(quiet, "Warehouse Picker", audio=False)
        hiring = self.add_company("ZZZ Hiring", "zzz-hiring", "Audio Software")
        self.add_job(hiring, "DSP Engineer")

        result = companies_router.list_companies(
            page=1, per_page=25, sort="board", direction="desc", db=self.session
        )
        self.assertEqual(result["items"][0]["slug"], "zzz-hiring")


class TestCompanyCategories(DirectoryCase):
    def test_categories_report_company_and_board_counts(self) -> None:
        acme = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        self.add_job(acme, "DSP Engineer")
        self.add_company("Quiet Co", "quiet-co", "Audio Software")
        speakers = self.add_company("Loud Co", "loud-co", "Hi-Fi")
        self.add_job(speakers, "Acoustic Engineer")
        self.add_job(speakers, "Warehouse Picker", audio=False)

        result = companies_router.list_company_categories(db=self.session)
        by_name = {c.name: c for c in result.categories}
        self.assertEqual(by_name["Audio Software"].company_count, 2)
        self.assertEqual(by_name["Audio Software"].board_jobs_count, 1)
        self.assertEqual(by_name["Hi-Fi"].company_count, 1)
        self.assertEqual(by_name["Hi-Fi"].board_jobs_count, 1)
        self.assertEqual(result.total, 3)

    def test_categories_route_is_not_shadowed_by_the_slug_route(self) -> None:
        paths = [
            route.path
            for route in companies_router.router.routes
            if getattr(route, "path", "").startswith("/api/companies")
        ]
        self.assertLess(
            paths.index("/api/companies/categories"),
            paths.index("/api/companies/{slug}"),
        )


class TestCompanySuggestions(DirectoryCase):
    def test_a_suggestion_lands_pending_and_changes_nothing_yet(self) -> None:
        company = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        payload = CompanySuggestionRequest(
            description="Builds loudspeaker DSP.",
            links=[{"label": "Wikipedia", "url": "https://example.org/acme"}],
        )
        result = companies_router.submit_company_suggestion(
            "acme-audio", payload, FakeRequest(), self.session
        )
        self.assertEqual(result.status, "pending")
        self.session.refresh(company)
        self.assertIsNone(company.description)
        self.assertIsNone(company.community_links)

    def test_an_empty_suggestion_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            CompanySuggestionRequest(comment="   ")

    def test_a_comment_alone_is_accepted(self) -> None:
        payload = CompanySuggestionRequest(comment="This company closed in 2025.")
        self.assertEqual(payload.comment, "This company closed in 2025.")

    def test_a_careers_url_must_be_http(self) -> None:
        with self.assertRaises(ValidationError):
            CompanySuggestionRequest(careers_url="ftp://example.com/jobs")

    def test_an_unknown_category_is_refused(self) -> None:
        self.add_company("Acme Audio", "acme-audio", "Audio Software")
        payload = CompanySuggestionRequest(category="Made Up Category")
        with self.assertRaises(HTTPException) as caught:
            companies_router.submit_company_suggestion(
                "acme-audio", payload, FakeRequest(), self.session
            )
        self.assertEqual(caught.exception.status_code, 422)

    def test_approving_seed_fields_updates_the_company(self) -> None:
        company = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        self.add_company("Other", "other", "Pro Audio")
        company.careers_url = "https://boards.greenhouse.io/acme"
        company.ats_type = "greenhouse"
        company.ats_slug = "acme"
        self.session.flush()
        suggestion = self._submit(
            company,
            careers_url="https://jobs.lever.co/acme",
            website_url="https://acme.audio",
            category="Pro Audio",
        )
        result = admin_router.approve_company_suggestion(suggestion.id, self.session, "admin")
        self.session.refresh(company)
        self.assertEqual(company.careers_url, "https://jobs.lever.co/acme")
        self.assertIsNone(company.ats_type)
        self.assertIsNone(company.ats_slug)
        self.assertEqual(company.website_url, "https://acme.audio")
        self.assertEqual(company.category, "Pro Audio")
        self.assertEqual(company.source, "manual")
        self.assertIn("careers page", result.applied)

    def test_admin_list_shows_current_values_beside_suggested(self) -> None:
        company = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        company.careers_url = "https://old.example.com/jobs"
        self.session.flush()
        self._submit(company, careers_url="https://new.example.com/jobs")
        result = admin_router.admin_list_company_suggestions(
            status="pending", page=1, per_page=25, db=self.session, _="admin"
        )
        row = result["items"][0]
        self.assertEqual(row.careers_url, "https://new.example.com/jobs")
        self.assertEqual(row.current_careers_url, "https://old.example.com/jobs")

    def test_a_link_must_be_http(self) -> None:
        with self.assertRaises(ValidationError):
            CompanySuggestionRequest(
                links=[{"label": "Bad", "url": "javascript:alert(1)"}]
            )

    def test_unknown_company_is_404(self) -> None:
        payload = CompanySuggestionRequest(description="Hello")
        with self.assertRaises(HTTPException) as caught:
            companies_router.submit_company_suggestion(
                "nope", payload, FakeRequest(), self.session
            )
        self.assertEqual(caught.exception.status_code, 404)

    def _submit(self, company, **kwargs) -> CompanySuggestion:
        payload = CompanySuggestionRequest(**kwargs)
        result = companies_router.submit_company_suggestion(
            company.slug, payload, FakeRequest(), self.session
        )
        row = self.session.get(CompanySuggestion, result.id)
        assert row is not None
        return row

    def test_approving_applies_every_field(self) -> None:
        company = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        suggestion = self._submit(
            company,
            description="Builds loudspeaker DSP.",
            links=[{"label": "Wikipedia", "url": "https://example.org/acme"}],
            headquarters="Copenhagen, Denmark",
            founded=1977,
        )
        admin_router.approve_company_suggestion(suggestion.id, self.session, "admin")
        self.session.refresh(company)
        self.assertEqual(company.description, "Builds loudspeaker DSP.")
        self.assertEqual(
            company.community_links,
            [{"label": "Wikipedia", "url": "https://example.org/acme"}],
        )
        self.assertEqual(company.headquarters, "Copenhagen, Denmark")
        self.assertEqual(company.founded, 1977)

    def test_approving_marks_the_company_manual_so_the_loader_skips_it(self) -> None:
        company = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        company.source = "auto"
        self.session.flush()
        suggestion = self._submit(company, description="Builds loudspeaker DSP.")
        admin_router.approve_company_suggestion(suggestion.id, self.session, "admin")
        self.session.refresh(company)
        self.assertEqual(company.source, "manual")

    def test_approving_appends_links_without_duplicating(self) -> None:
        company = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        company.community_links = [
            {"label": "Wikipedia", "url": "https://example.org/acme"}
        ]
        self.session.flush()
        suggestion = self._submit(
            company,
            links=[
                {"label": "Wikipedia", "url": "https://example.org/acme"},
                {"label": "Docs", "url": "https://example.org/docs"},
            ],
        )
        admin_router.approve_company_suggestion(suggestion.id, self.session, "admin")
        self.session.refresh(company)
        self.assertEqual(len(company.community_links), 2)

    def test_rejecting_applies_nothing(self) -> None:
        company = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        suggestion = self._submit(company, description="Builds loudspeaker DSP.")
        admin_router.reject_company_suggestion(
            suggestion.id, RejectRequest(reason="spam"), self.session, "admin"
        )
        self.session.refresh(company)
        self.assertIsNone(company.description)
        self.session.refresh(suggestion)
        self.assertEqual(suggestion.status, "rejected")

    def test_double_approval_is_a_conflict(self) -> None:
        company = self.add_company("Acme Audio", "acme-audio", "Audio Software")
        suggestion = self._submit(company, description="Builds loudspeaker DSP.")
        admin_router.approve_company_suggestion(suggestion.id, self.session, "admin")
        with self.assertRaises(HTTPException) as caught:
            admin_router.approve_company_suggestion(suggestion.id, self.session, "admin")
        self.assertEqual(caught.exception.status_code, 409)


class TestScrapeStatus(unittest.TestCase):
    def status(self, **fields) -> str:
        base = {
            "id": 1,
            "name": "Acme",
            "slug": "acme",
            "category": "Audio Software",
            "careers_url": "https://acme.audio/jobs",
            "verified": True,
            "source": "auto",
            "created_at": datetime.now(timezone.utc),
            "last_scraped_at": datetime.now(timezone.utc),
            **fields,
        }
        return CompanyResponse.model_validate(base).scrape_status

    def test_a_recent_clean_scrape_is_tracked(self) -> None:
        self.assertEqual(self.status(), "tracked")

    def test_recent_failures_are_failing(self) -> None:
        self.assertEqual(self.status(consecutive_failures=2), "failing")

    def test_unverified_blocked_or_never_scraped_is_untracked(self) -> None:
        self.assertEqual(self.status(verified=False), "untracked")
        self.assertEqual(self.status(scrape_blocked=True), "untracked")
        self.assertEqual(self.status(open_application=True), "untracked")
        self.assertEqual(self.status(careers_url=None), "untracked")
        self.assertEqual(self.status(last_scraped_at=None), "untracked")


if __name__ == "__main__":
    unittest.main()
