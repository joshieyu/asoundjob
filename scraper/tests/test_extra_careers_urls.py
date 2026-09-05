from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scraper.company_loader import load_companies, parse_extra_careers_urls
from scraper.models import Base, Company

PRIMARY = "https://jobs.example.com/careers?search=audio"
ACOUSTIC = "https://jobs.example.com/careers?search=acoustic"
DSP = "https://jobs.example.com/careers?search=dsp"


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def entry(**overrides):
    base = {
        "name": "Acme Audio",
        "careers_url": PRIMARY,
        "category": "Professional Audio & Live Sound",
        "verified": True,
        "source": "auto",
        "scrape_method": "http",
    }
    base.update(overrides)
    return base


class TestParseExtraCareersUrls(unittest.TestCase):
    def test_absent_is_none(self) -> None:
        self.assertIsNone(parse_extra_careers_urls(None, PRIMARY))

    def test_empty_list_is_none(self) -> None:
        self.assertIsNone(parse_extra_careers_urls([], PRIMARY))

    def test_keeps_order_and_strips(self) -> None:
        self.assertEqual(
            parse_extra_careers_urls([f"  {ACOUSTIC} ", DSP], PRIMARY),
            [ACOUSTIC, DSP],
        )

    def test_drops_the_primary_url(self) -> None:
        self.assertEqual(parse_extra_careers_urls([PRIMARY, DSP], PRIMARY), [DSP])

    def test_drops_the_primary_ignoring_a_trailing_slash(self) -> None:
        self.assertIsNone(parse_extra_careers_urls([PRIMARY + "/"], PRIMARY))

    def test_drops_duplicates_within_the_list(self) -> None:
        self.assertEqual(parse_extra_careers_urls([DSP, DSP], PRIMARY), [DSP])

    def test_rejects_non_http_and_non_string(self) -> None:
        self.assertEqual(
            parse_extra_careers_urls(["mailto:a@b.com", 42, "ftp://x", DSP], PRIMARY),
            [DSP],
        )

    def test_rejects_a_non_list(self) -> None:
        self.assertIsNone(parse_extra_careers_urls(ACOUSTIC, PRIMARY))


class TestLoaderSyncsOpenApplication(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def _row(self):
        return self.session.execute(Company.__table__.select()).mappings().one()

    def test_default_is_false(self) -> None:
        load_companies(self.session, [entry()])
        self.session.flush()
        self.assertFalse(self._row()["open_application"])

    def test_flag_is_stored(self) -> None:
        load_companies(self.session, [entry(open_application=True)])
        self.session.flush()
        self.assertTrue(self._row()["open_application"])

    def test_turning_it_off_is_an_update(self) -> None:
        load_companies(self.session, [entry(open_application=True)])
        self.session.flush()
        stats = load_companies(self.session, [entry()])
        self.session.flush()
        self.assertEqual(stats.updated, 1)
        self.assertFalse(self._row()["open_application"])


class TestLoaderSyncsExtraUrls(unittest.TestCase):
    def setUp(self) -> None:
        self.session = make_session()

    def tearDown(self) -> None:
        self.session.rollback()
        self.session.close()

    def _company(self) -> Company:
        company = self.session.execute(
            Company.__table__.select()
        ).mappings().one()
        return company

    def test_insert_stores_the_extra_urls(self) -> None:
        stats = load_companies(self.session, [entry(extra_careers_urls=[ACOUSTIC])])
        self.session.flush()
        self.assertEqual(stats.inserted, 1)
        self.assertEqual(self._company()["extra_careers_urls"], [ACOUSTIC])

    def test_insert_without_the_key_stores_none(self) -> None:
        load_companies(self.session, [entry()])
        self.session.flush()
        self.assertIsNone(self._company()["extra_careers_urls"])

    def test_adding_a_url_is_an_update_not_unchanged(self) -> None:
        load_companies(self.session, [entry()])
        self.session.flush()
        stats = load_companies(self.session, [entry(extra_careers_urls=[ACOUSTIC])])
        self.session.flush()
        self.assertEqual(stats.updated, 1)
        self.assertEqual(self._company()["extra_careers_urls"], [ACOUSTIC])

    def test_removing_a_url_clears_the_column(self) -> None:
        load_companies(self.session, [entry(extra_careers_urls=[ACOUSTIC])])
        self.session.flush()
        stats = load_companies(self.session, [entry()])
        self.session.flush()
        self.assertEqual(stats.updated, 1)
        self.assertIsNone(self._company()["extra_careers_urls"])

    def test_an_unchanged_entry_stays_unchanged(self) -> None:
        load_companies(self.session, [entry(extra_careers_urls=[ACOUSTIC])])
        self.session.flush()
        stats = load_companies(self.session, [entry(extra_careers_urls=[ACOUSTIC])])
        self.assertEqual(stats.unchanged, 1)


if __name__ == "__main__":
    unittest.main()
