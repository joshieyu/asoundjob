from __future__ import annotations

import unittest

from scraper.config import load_settings
from scraper.normalizer import Normalizer
from scraper.scrapers.base import RawJob
from scraper.text_location import location_from_text


class TestLabelledLocations(unittest.TestCase):
    def test_reads_a_location_label(self) -> None:
        text = "<p>Job Location: Tempe, AZ (100% Onsite)</p><p>We are seeking an engineer.</p>"
        self.assertEqual(location_from_text(text), "Tempe, AZ")

    def test_reads_the_value_on_the_next_line(self) -> None:
        text = "Work location\nRosenthaler Straße 38, 10178 Berlin, Germany\nContract details"
        self.assertEqual(location_from_text(text), "Berlin, Germany")

    def test_stops_where_the_next_sentence_runs_on(self) -> None:
        text = "Location: Boston, MA We are searching for a smart, enthusiastic engineer."
        self.assertEqual(location_from_text(text), "Boston, MA")
        text = "Location: Boston, Massachusetts Listen, Inc., the world leader in audio test"
        self.assertEqual(location_from_text(text), "Boston, Massachusetts")

    def test_reads_escaped_html_and_non_breaking_spaces(self) -> None:
        text = "&lt;p&gt;Location:\xa0Dubai, UAE\xa0- Willingness to travel&lt;/p&gt;"
        self.assertEqual(location_from_text(text), "Dubai, UAE")

    def test_ignores_a_sentence_after_the_label(self) -> None:
        text = (
            "Location\nThis role is expected to work from the designated office 5 days a "
            "week, per company policy, in New York"
        )
        self.assertIsNone(location_from_text(text))


class TestProseLocations(unittest.TestCase):
    def test_reads_based_out_of(self) -> None:
        text = "This role is based out of our Plymouth, MI office. Join our team!"
        self.assertEqual(location_from_text(text), "Plymouth, MI")

    def test_strips_a_trailing_exclamation(self) -> None:
        self.assertEqual(location_from_text("Based out of Tampa, FL!"), "Tampa, FL")

    def test_skips_lists_of_company_offices(self) -> None:
        text = "We have offices in London, New York, San Francisco and Warsaw."
        self.assertIsNone(location_from_text(text))

    def test_conflicting_countries_give_no_guess(self) -> None:
        text = (
            "TuneIn San Francisco is located in San Francisco’s SoMa. "
            "TuneIn London is located in Chiswick, London."
        )
        self.assertIsNone(location_from_text(text))

    def test_lowercase_text_is_not_a_place(self) -> None:
        self.assertIsNone(location_from_text("The team is based in a converted warehouse."))

    def test_nothing_to_read(self) -> None:
        self.assertIsNone(location_from_text(None))
        self.assertIsNone(location_from_text(""))
        self.assertIsNone(location_from_text("Design loudspeakers. Measure rooms."))


class TestNormalizerUsesTheText(unittest.TestCase):
    def setUp(self) -> None:
        self.normalizer = Normalizer(load_settings())

    def test_a_job_without_a_location_takes_one_from_its_description(self) -> None:
        raw = RawJob(
            title="Acoustic Engineer",
            url="https://example.com/jobs/1",
            description="Location: Modena, Italy\nDesign loudspeakers.",
        )
        job = self.normalizer.normalize(raw)
        self.assertEqual(job.location, "Modena, Italy")
        self.assertEqual(job.country, "IT")

    def test_a_scraped_location_wins(self) -> None:
        raw = RawJob(
            title="Acoustic Engineer",
            url="https://example.com/jobs/1",
            location="Oslo, Norway",
            description="Location: Modena, Italy",
        )
        self.assertEqual(self.normalizer.normalize(raw).location, "Oslo, Norway")


if __name__ == "__main__":
    unittest.main()
