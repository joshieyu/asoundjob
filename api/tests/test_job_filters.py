from __future__ import annotations

import inspect
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.query import _as_list
from api.routers.jobs import list_jobs
from scraper.models import Base, Company, Job


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def endpoint_defaults() -> dict:
    values = {}
    for name, param in inspect.signature(list_jobs).parameters.items():
        if name == "db":
            continue
        default = param.default
        if default is inspect.Parameter.empty:
            continue
        values[name] = getattr(default, "default", default)
    return values


def call_list_jobs(session, **kwargs):
    params = endpoint_defaults()
    params.update(kwargs)
    return list_jobs(db=session, **params)


def titles(result) -> set:
    return {item.title for item in result["items"]}


class TestMultiValueFilters(unittest.TestCase):
    """seniority and job_type accept a CSV list and OR the values together."""

    def setUp(self) -> None:
        self.session = make_session()
        plan = [
            ("Junior Recordist", "entry", "internship"),
            ("Staff DSP Engineer", "mid", "full-time"),
            ("Senior Acoustician", "senior", "full-time"),
            ("Lead Game Audio", "lead", "contract"),
            ("Audio Program Manager", "manager", "part-time"),
        ]
        for title, seniority, job_type in plan:
            self.session.add(
                Job(
                    title=title,
                    description="x",
                    url=f"https://example.com/{title.lower().replace(' ', '-')}",
                    seniority=seniority,
                    job_type=job_type,
                    is_active=True,
                    is_audio_related=True,
                )
            )
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()

    def test_single_seniority_still_works(self) -> None:
        """Old single-value URLs must keep working after the multi-select change."""
        result = call_list_jobs(self.session, seniority="senior")
        self.assertEqual(titles(result), {"Senior Acoustician"})

    def test_multiple_seniorities_are_ored(self) -> None:
        result = call_list_jobs(self.session, seniority="senior,manager")
        self.assertEqual(titles(result), {"Senior Acoustician", "Audio Program Manager"})

    def test_multiple_seniorities_are_additive(self) -> None:
        one = call_list_jobs(self.session, seniority="entry")["total"]
        two = call_list_jobs(self.session, seniority="lead")["total"]
        both = call_list_jobs(self.session, seniority="entry,lead")["total"]
        self.assertEqual(both, one + two)

    def test_multiple_job_types_are_ored(self) -> None:
        result = call_list_jobs(self.session, job_type="internship,contract")
        self.assertEqual(titles(result), {"Junior Recordist", "Lead Game Audio"})

    def test_seniority_and_job_type_intersect(self) -> None:
        """Different filters AND together even though values within one OR."""
        result = call_list_jobs(
            self.session, seniority="senior,lead", job_type="full-time"
        )
        self.assertEqual(titles(result), {"Senior Acoustician"})

    def test_values_are_case_insensitive(self) -> None:
        result = call_list_jobs(self.session, seniority="SENIOR,Manager")
        self.assertEqual(titles(result), {"Senior Acoustician", "Audio Program Manager"})

    def test_empty_and_junk_values_do_not_filter(self) -> None:
        total = call_list_jobs(self.session)["total"]
        for junk in ("", ",", " , , "):
            with self.subTest(value=junk):
                self.assertEqual(call_list_jobs(self.session, seniority=junk)["total"], total)

    def test_unknown_value_returns_nothing_rather_than_everything(self) -> None:
        self.assertEqual(call_list_jobs(self.session, seniority="archmage")["total"], 0)


class TestCompanyNameFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()
        for name in ("Dolby Laboratories", "Bolby Audio", "Sennheiser"):
            company = Company(
                name=name,
                slug=name.lower().replace(" ", "-"),
                category="Audio Software",
                verified=True,
            )
            self.session.add(company)
            self.session.flush()
            self.session.add(
                Job(
                    title=f"Engineer at {name}",
                    description="x",
                    url=f"https://example.com/{company.slug}",
                    company_id=company.id,
                    is_active=True,
                    is_audio_related=True,
                )
            )
        # A job with no company at all must never match a company filter.
        self.session.add(
            Job(
                title="Orphan Role",
                description="x",
                url="https://example.com/orphan",
                is_active=True,
                is_audio_related=True,
            )
        )
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()

    def test_matches_on_substring(self) -> None:
        result = call_list_jobs(self.session, company="dolby")
        self.assertEqual(titles(result), {"Engineer at Dolby Laboratories"})

    def test_is_case_insensitive(self) -> None:
        for value in ("DOLBY", "Dolby", "dOlBy"):
            with self.subTest(value=value):
                self.assertEqual(call_list_jobs(self.session, company=value)["total"], 1)

    def test_matches_mid_word(self) -> None:
        """'olby' hits both Dolby and Bolby — substring, not prefix."""
        result = call_list_jobs(self.session, company="olby")
        self.assertEqual(
            titles(result), {"Engineer at Dolby Laboratories", "Engineer at Bolby Audio"}
        )

    def test_companyless_jobs_are_excluded(self) -> None:
        result = call_list_jobs(self.session, company="e")
        self.assertNotIn("Orphan Role", titles(result))

    def test_blank_filter_is_ignored(self) -> None:
        total = call_list_jobs(self.session)["total"]
        for blank in ("", "   "):
            with self.subTest(value=blank):
                self.assertEqual(call_list_jobs(self.session, company=blank)["total"], total)

    def test_no_match_returns_nothing(self) -> None:
        self.assertEqual(call_list_jobs(self.session, company="zzzznope")["total"], 0)


class TestAsList(unittest.TestCase):
    def test_accepts_a_bare_string(self) -> None:
        """routers/search.py still passes a plain string; that must keep working."""
        self.assertEqual(_as_list("Senior"), ["senior"])

    def test_accepts_a_list(self) -> None:
        self.assertEqual(_as_list(["Senior", "MID"]), ["senior", "mid"])

    def test_drops_blanks(self) -> None:
        self.assertEqual(_as_list(["senior", "", "  "]), ["senior"])

    def test_empty_becomes_none_so_no_where_clause_is_added(self) -> None:
        for value in (None, "", "   ", [], ["", " "]):
            with self.subTest(value=value):
                self.assertIsNone(_as_list(value))


if __name__ == "__main__":
    unittest.main()
