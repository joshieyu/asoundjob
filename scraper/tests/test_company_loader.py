from __future__ import annotations

import unittest
from datetime import date, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from scraper.company_loader import (
    deactivate_expired_jobs,
    load_companies,
    parse_community_links,
)
from scraper.models import Base, Company, Job


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def entry(name: str, verified: bool) -> dict:
    return {
        "name": name,
        "careers_url": "https://example.com/careers",
        "category": "Audio Software",
        "verified": verified,
        "source": "auto",
        "scrape_method": "http",
    }


class TestCommunityFieldsSurviveReload(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_a_seed_reload_leaves_community_contributions_alone(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.description = "Builds loudspeaker DSP."
        company.community_links = [{"label": "Wikipedia", "url": "https://example.org"}]
        company.headquarters = "Copenhagen, Denmark"
        company.founded = 1977
        self.session.flush()

        load_companies(self.session, [entry("Acme", verified=True)])
        self.session.refresh(company)
        self.assertEqual(company.description, "Builds loudspeaker DSP.")
        self.assertEqual(
            company.community_links,
            [{"label": "Wikipedia", "url": "https://example.org"}],
        )
        self.assertEqual(company.headquarters, "Copenhagen, Denmark")
        self.assertEqual(company.founded, 1977)

    def test_they_survive_a_reload_that_does_change_seed_fields(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.description = "Builds loudspeaker DSP."
        self.session.flush()

        load_companies(self.session, [entry("Acme", verified=False)])
        self.session.refresh(company)
        self.assertFalse(company.verified)
        self.assertEqual(company.description, "Builds loudspeaker DSP.")


class TestUnverifiedDeactivation(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def seed_company_with_job(self, name: str, verified: bool) -> Company:
        company = Company(
            name=name,
            slug=name.lower(),
            category="Audio Software",
            careers_url="https://example.com/careers",
            verified=verified,
        )
        self.session.add(company)
        self.session.flush()
        self.session.add(
            Job(
                company_id=company.id,
                title="Audio Engineer",
                url=f"https://example.com/{name}/1",
                is_active=True,
            )
        )
        self.session.flush()
        return company

    def active_titles(self, company_id: int) -> list[str]:
        rows = self.session.execute(
            select(Job.title).where(
                Job.company_id == company_id, Job.is_active.is_(True)
            )
        ).all()
        return [r[0] for r in rows]

    def test_demoting_to_unverified_deactivates_jobs(self) -> None:
        company = self.seed_company_with_job("acme", verified=True)
        stats = load_companies(self.session, [entry("acme", verified=False)])
        self.assertEqual(stats.deactivated_unverified, 1)
        self.assertEqual(self.active_titles(company.id), [])

    def test_verified_company_keeps_jobs(self) -> None:
        company = self.seed_company_with_job("acme", verified=True)
        stats = load_companies(self.session, [entry("acme", verified=True)])
        self.assertEqual(stats.deactivated_unverified, 0)
        self.assertEqual(self.active_titles(company.id), ["Audio Engineer"])

    def test_already_inactive_jobs_are_not_recounted(self) -> None:
        company = self.seed_company_with_job("acme", verified=False)
        load_companies(self.session, [entry("acme", verified=False)])
        stats = load_companies(self.session, [entry("acme", verified=False)])
        self.assertEqual(stats.deactivated_unverified, 0)
        self.assertEqual(self.active_titles(company.id), [])


class TestScrapeBlocked(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_seed_entry_sets_scrape_blocked_on_insert(self) -> None:
        seed = entry("acme", verified=True)
        seed["scrape_blocked"] = True
        load_companies(self.session, [seed])
        company = self.session.execute(select(Company)).scalar_one()
        self.assertTrue(company.scrape_blocked)

    def test_flipping_scrape_blocked_updates_existing_company(self) -> None:
        load_companies(self.session, [entry("acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        self.assertFalse(company.scrape_blocked)

        seed = entry("acme", verified=True)
        seed["scrape_blocked"] = True
        stats = load_companies(self.session, [seed])

        company = self.session.execute(select(Company)).scalar_one()
        self.assertTrue(company.scrape_blocked)
        self.assertEqual(stats.updated, 1)


class TestRenameMatchedBySlug(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_a_renamed_manual_row_is_matched_by_slug_and_skipped(self) -> None:
        self.session.add(
            Company(
                name="New Name",
                slug="old-name",
                category="Audio Software",
                careers_url="https://example.com/careers",
                verified=True,
                source="manual",
            )
        )
        self.session.flush()

        stats = load_companies(self.session, [entry("Old Name", verified=False)])

        companies = self.session.execute(select(Company)).scalars().all()
        self.assertEqual(len(companies), 1)
        self.assertEqual(stats.matched_by_slug, 1)
        self.assertEqual(stats.skipped_manual, 1)
        self.assertEqual(companies[0].name, "New Name")
        self.assertTrue(companies[0].verified)

    def test_a_renamed_auto_row_still_inserts_as_today(self) -> None:
        self.session.add(
            Company(
                name="New Name",
                slug="old-name",
                category="Audio Software",
                careers_url="https://example.com/careers",
                verified=True,
                source="auto",
            )
        )
        self.session.flush()

        stats = load_companies(self.session, [entry("Old Name", verified=False)])

        companies = self.session.execute(select(Company)).scalars().all()
        self.assertEqual(len(companies), 2)
        self.assertEqual(stats.matched_by_slug, 0)
        self.assertEqual(stats.inserted, 1)


class TestDeactivateExpiredJobs(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def make_company(self) -> Company:
        company = Company(
            name="Acme",
            slug="acme",
            category="Audio Software",
            careers_url="https://example.com/careers",
            verified=True,
        )
        self.session.add(company)
        self.session.flush()
        return company

    def make_job(
        self,
        company: Company,
        expires_date,
        is_active: bool = True,
        is_active_override=None,
    ) -> Job:
        job = Job(
            company_id=company.id,
            title="Community Job",
            url=f"https://example.com/jobs/{company.id}-{id(object())}",
            source="community",
            expires_date=expires_date,
            is_active=is_active,
            is_active_override=is_active_override,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def reload_is_active(self, job_id: int) -> bool:
        self.session.expire_all()
        return bool(
            self.session.execute(
                select(Job.is_active).where(Job.id == job_id)
            ).scalar_one()
        )

    def test_expired_job_is_deactivated(self) -> None:
        company = self.make_company()
        job = self.make_job(company, date(2020, 1, 1))
        count = deactivate_expired_jobs(self.session, today=date(2020, 1, 2))
        self.session.flush()
        self.assertEqual(count, 1)
        self.assertFalse(self.reload_is_active(job.id))

    def test_job_expiring_today_is_not_deactivated(self) -> None:
        company = self.make_company()
        job = self.make_job(company, date(2020, 1, 1))
        count = deactivate_expired_jobs(self.session, today=date(2020, 1, 1))
        self.session.flush()
        self.assertEqual(count, 0)
        self.assertTrue(self.reload_is_active(job.id))

    def test_job_without_expiry_is_untouched(self) -> None:
        company = self.make_company()
        job = self.make_job(company, None)
        count = deactivate_expired_jobs(self.session, today=date(2020, 1, 2))
        self.session.flush()
        self.assertEqual(count, 0)
        self.assertTrue(self.reload_is_active(job.id))

    def test_override_keeps_expired_job_active(self) -> None:
        company = self.make_company()
        job = self.make_job(company, date(2020, 1, 1), is_active_override=True)
        count = deactivate_expired_jobs(self.session, today=date(2020, 1, 2))
        self.session.flush()
        self.assertEqual(count, 0)
        self.assertTrue(self.reload_is_active(job.id))

    def test_already_inactive_expired_job_is_not_recounted(self) -> None:
        company = self.make_company()
        job = self.make_job(company, date(2020, 1, 1), is_active=False)
        count = deactivate_expired_jobs(self.session, today=date(2020, 1, 2))
        self.session.flush()
        self.assertEqual(count, 0)
        self.assertFalse(self.reload_is_active(job.id))

    def test_returned_count_matches_rows_actually_changed(self) -> None:
        company = self.make_company()
        self.make_job(company, date(2020, 1, 1))
        self.make_job(company, date(2020, 1, 1))
        self.make_job(company, date(2020, 1, 5))
        count = deactivate_expired_jobs(self.session, today=date(2020, 1, 2))
        self.assertEqual(count, 2)

    def test_today_defaults_to_the_real_today(self) -> None:
        company = self.make_company()
        job = self.make_job(company, date.today() - timedelta(days=1))
        count = deactivate_expired_jobs(self.session)
        self.session.flush()
        self.assertEqual(count, 1)
        self.assertFalse(self.reload_is_active(job.id))


class TestParseCommunityLinks(unittest.TestCase):
    def test_malformed_entries_are_dropped(self) -> None:
        value = [
            {"label": "Wikipedia", "url": "https://example.org"},
            {"label": "", "url": "https://example.org/empty-label"},
            {"label": "No URL"},
            "not-a-dict",
            {"label": "Bad Scheme", "url": "ftp://example.org"},
        ]
        result = parse_community_links(value)
        self.assertEqual(result, [{"label": "Wikipedia", "url": "https://example.org"}])

    def test_non_http_url_is_rejected(self) -> None:
        result = parse_community_links([{"label": "X", "url": "javascript:alert(1)"}])
        self.assertIsNone(result)

    def test_list_is_capped_at_ten(self) -> None:
        value = [
            {"label": f"Link {i}", "url": f"https://example.org/{i}"} for i in range(15)
        ]
        result = parse_community_links(value)
        self.assertEqual(len(result), 10)

    def test_non_list_input_returns_none(self) -> None:
        self.assertIsNone(parse_community_links("not-a-list"))
        self.assertIsNone(parse_community_links(None))


class TestCommunityFieldsFromSeed(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_seed_entry_with_community_fields_loads_onto_new_company(self) -> None:
        seed = entry("Acme", verified=True)
        seed["description"] = "Builds loudspeaker DSP."
        seed["headquarters"] = "Copenhagen, Denmark"
        seed["founded"] = 1977
        seed["community_links"] = [{"label": "Wikipedia", "url": "https://example.org"}]

        load_companies(self.session, [seed])

        company = self.session.execute(select(Company)).scalar_one()
        self.assertEqual(company.description, "Builds loudspeaker DSP.")
        self.assertEqual(company.headquarters, "Copenhagen, Denmark")
        self.assertEqual(company.founded, 1977)
        self.assertEqual(
            company.community_links,
            [{"label": "Wikipedia", "url": "https://example.org"}],
        )

    def test_omitting_keys_on_update_leaves_existing_values_untouched(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.description = "Builds loudspeaker DSP."
        company.headquarters = "Copenhagen, Denmark"
        company.founded = 1977
        company.community_links = [{"label": "Wikipedia", "url": "https://example.org"}]
        self.session.flush()

        stats = load_companies(self.session, [entry("Acme", verified=False)])

        self.session.refresh(company)
        self.assertEqual(stats.updated, 1)
        self.assertEqual(company.description, "Builds loudspeaker DSP.")
        self.assertEqual(company.headquarters, "Copenhagen, Denmark")
        self.assertEqual(company.founded, 1977)
        self.assertEqual(
            company.community_links,
            [{"label": "Wikipedia", "url": "https://example.org"}],
        )

    def test_explicit_null_clears_the_field(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.description = "Builds loudspeaker DSP."
        self.session.flush()

        seed = entry("Acme", verified=False)
        seed["description"] = None
        stats = load_companies(self.session, [seed])

        self.session.refresh(company)
        self.assertEqual(stats.updated, 1)
        self.assertIsNone(company.description)

    def test_reload_omitting_community_keys_with_no_other_changes_is_unchanged(self) -> None:
        seed = entry("Acme", verified=True)
        seed["description"] = "Builds loudspeaker DSP."
        load_companies(self.session, [seed])

        stats = load_companies(self.session, [entry("Acme", verified=True)])
        self.assertEqual(stats.unchanged, 1)
        self.assertEqual(stats.updated, 0)

    def test_malformed_community_links_in_seed_are_dropped_on_load(self) -> None:
        seed = entry("Acme", verified=True)
        seed["community_links"] = [
            {"label": "Wikipedia", "url": "https://example.org"},
            {"label": "Bad", "url": "not-a-url"},
        ]
        load_companies(self.session, [seed])
        company = self.session.execute(select(Company)).scalar_one()
        self.assertEqual(
            company.community_links,
            [{"label": "Wikipedia", "url": "https://example.org"}],
        )


class TestAtsFieldsFromSeed(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_seed_with_no_ats_keys_leaves_a_discovered_binding_untouched(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.ats_type = "greenhouse"
        company.ats_slug = "acme"
        self.session.flush()

        stats = load_companies(self.session, [entry("Acme", verified=True)])

        self.session.refresh(company)
        self.assertEqual(company.ats_type, "greenhouse")
        self.assertEqual(company.ats_slug, "acme")
        self.assertEqual(stats.unchanged, 1)
        self.assertEqual(stats.updated, 0)

    def test_seed_entry_with_binding_sets_it_on_insert(self) -> None:
        seed = entry("Northrop Grumman", verified=True)
        seed["ats_type"] = "eightfold"
        seed["ats_slug"] = "ngc.com"

        load_companies(self.session, [seed])

        company = self.session.execute(select(Company)).scalar_one()
        self.assertEqual(company.ats_type, "eightfold")
        self.assertEqual(company.ats_slug, "ngc.com")

    def test_seed_entry_with_binding_overwrites_a_different_db_value(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.ats_type = "greenhouse"
        company.ats_slug = "old-slug"
        self.session.flush()

        seed = entry("Acme", verified=True)
        seed["ats_type"] = "workday"
        seed["ats_slug"] = "acme.wd1/External"
        stats = load_companies(self.session, [seed])

        self.session.refresh(company)
        self.assertEqual(company.ats_type, "workday")
        self.assertEqual(company.ats_slug, "acme.wd1/External")
        self.assertEqual(stats.updated, 1)

    def test_explicit_null_clears_ats_type_and_ats_slug(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.ats_type = "greenhouse"
        company.ats_slug = "acme"
        self.session.flush()

        seed = entry("Acme", verified=True)
        seed["ats_type"] = None
        seed["ats_slug"] = None
        stats = load_companies(self.session, [seed])

        self.session.refresh(company)
        self.assertIsNone(company.ats_type)
        self.assertIsNone(company.ats_slug)
        self.assertEqual(stats.updated, 1)

    def test_unchanged_ats_binding_does_not_mark_the_row_changed(self) -> None:
        seed = entry("Acme", verified=True)
        seed["ats_type"] = "greenhouse"
        seed["ats_slug"] = "acme"
        load_companies(self.session, [seed])

        stats = load_companies(self.session, [dict(seed)])

        self.assertEqual(stats.unchanged, 1)
        self.assertEqual(stats.updated, 0)

    def test_ats_slug_without_ats_type_is_ignored(self) -> None:
        seed = entry("Acme", verified=True)
        seed["ats_slug"] = "acme"
        load_companies(self.session, [seed])

        company = self.session.execute(select(Company)).scalar_one()
        self.assertIsNone(company.ats_type)
        self.assertIsNone(company.ats_slug)

    def test_ats_slug_without_ats_type_does_not_clobber_an_existing_slug(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.ats_type = "greenhouse"
        company.ats_slug = "acme"
        self.session.flush()

        seed = entry("Acme", verified=True)
        seed["ats_slug"] = "some-other-slug"
        load_companies(self.session, [seed])

        self.session.refresh(company)
        self.assertEqual(company.ats_type, "greenhouse")
        self.assertEqual(company.ats_slug, "acme")

    def test_binding_is_stable_across_a_seed_reload_round_trip(self) -> None:
        seed = entry("Activision", verified=True)
        seed["ats_type"] = "workday"
        seed["ats_slug"] = "xboxgaming.wd1/External"

        load_companies(self.session, [seed])
        load_companies(self.session, [seed])

        company = self.session.execute(select(Company)).scalar_one()
        self.assertEqual(company.ats_type, "workday")
        self.assertEqual(company.ats_slug, "xboxgaming.wd1/External")


if __name__ == "__main__":
    unittest.main()


class TestSiteUrlsFollowKeyPresence(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def test_a_seed_entry_carrying_them_loads_them(self) -> None:
        seed = entry("Acme", verified=True)
        seed["website_url"] = "https://acme.example.com"
        seed["logo_url"] = "https://cdn.example.com/acme.svg"

        load_companies(self.session, [seed])

        company = self.session.execute(select(Company)).scalar_one()
        self.assertEqual(company.website_url, "https://acme.example.com")
        self.assertEqual(company.logo_url, "https://cdn.example.com/acme.svg")

    def test_omitting_them_never_wipes_what_is_stored(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.website_url = "https://acme.example.com"
        company.logo_url = "https://cdn.example.com/acme.svg"
        self.session.flush()

        stats = load_companies(self.session, [entry("Acme", verified=False)])

        self.session.refresh(company)
        self.assertEqual(stats.updated, 1)
        self.assertEqual(company.website_url, "https://acme.example.com")
        self.assertEqual(company.logo_url, "https://cdn.example.com/acme.svg")

    def test_an_explicit_null_clears_them(self) -> None:
        load_companies(self.session, [entry("Acme", verified=True)])
        company = self.session.execute(select(Company)).scalar_one()
        company.website_url = "https://acme.example.com"
        company.logo_url = "https://cdn.example.com/acme.svg"
        self.session.flush()

        seed = entry("Acme", verified=True)
        seed["website_url"] = None
        seed["logo_url"] = None
        load_companies(self.session, [seed])

        self.session.refresh(company)
        self.assertIsNone(company.website_url)
        self.assertIsNone(company.logo_url)

    def test_a_blank_string_is_treated_as_cleared_not_stored(self) -> None:
        seed = entry("Acme", verified=True)
        seed["website_url"] = "   "
        load_companies(self.session, [seed])

        company = self.session.execute(select(Company)).scalar_one()
        self.assertIsNone(company.website_url)

    def test_a_reload_with_the_same_values_is_unchanged(self) -> None:
        seed = entry("Acme", verified=True)
        seed["website_url"] = "https://acme.example.com"
        load_companies(self.session, [seed])

        stats = load_companies(self.session, [dict(seed)])
        self.assertEqual(stats.unchanged, 1)
