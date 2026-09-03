from __future__ import annotations

import unittest

from bs4 import BeautifulSoup

from scraper.scrapers.link_extraction import (
    anchor_location,
    card_location,
    clean_location_value,
    extract_job_links,
    extract_jobs,
)

BASE = "https://example.com/careers"


def soup(html: str):
    return BeautifulSoup(html, "html.parser")


def first_anchor(html: str):
    return soup(html).find("a")


class TestCleanLocationValue(unittest.TestCase):
    def test_strips_a_leading_label(self) -> None:
        self.assertEqual(clean_location_value("Location: Berlin, Germany"), "Berlin, Germany")

    def test_strips_a_plural_label(self) -> None:
        self.assertEqual(clean_location_value("Locations - Tokyo, Japan"), "Tokyo, Japan")

    def test_collapses_whitespace(self) -> None:
        self.assertEqual(clean_location_value("  Staefa,\n\tSwitzerland "), "Staefa, Switzerland")

    def test_rejects_job_board_vocabulary(self) -> None:
        self.assertIsNone(clean_location_value("Browse Jobs"))
        self.assertIsNone(clean_location_value("This job is available in 2 locations"))
        self.assertIsNone(clean_location_value("All Locations"))
        self.assertIsNone(clean_location_value("Search by location"))

    def test_rejects_prose(self) -> None:
        long_text = "We are looking for someone to join our team in a hybrid capacity soon"
        self.assertIsNone(clean_location_value(long_text))

    def test_rejects_empty_and_overlong(self) -> None:
        self.assertIsNone(clean_location_value(""))
        self.assertIsNone(clean_location_value("A"))
        self.assertIsNone(clean_location_value("X" * 200))

    def test_keeps_a_place_name_that_merely_contains_a_reject_substring(self) -> None:
        self.assertEqual(clean_location_value("Jobstown, Ireland"), "Jobstown, Ireland")
        self.assertEqual(clean_location_value("Alicante, Spain"), "Alicante, Spain")


class TestCardLocation(unittest.TestCase):
    def test_reads_a_location_class(self) -> None:
        html = '<div><h3><a href="/jobs/1">Audio DSP Engineer</a></h3>' \
               '<p class="_sf_location">Staefa, Switzerland</p></div>'
        self.assertEqual(card_location(soup(html).find("div")), "Staefa, Switzerland")

    def test_reads_a_modifier_class(self) -> None:
        html = '<li><a href="/jobs/1">Audio DSP Engineer</a>' \
               '<span class="table__detail--location">Marlow, United Kingdom</span></li>'
        self.assertEqual(card_location(soup(html).find("li")), "Marlow, United Kingdom")

    def test_reads_an_aria_label(self) -> None:
        html = '<div><a href="/jobs/1">Audio DSP Engineer</a>' \
               '<span aria-label="Location">San Jose, California</span></div>'
        self.assertEqual(card_location(soup(html).find("div")), "San Jose, California")

    def test_reads_an_id_prefix(self) -> None:
        html = '<div><a href="/jobs/1">Audio DSP Engineer</a>' \
               '<span id="location_icon_text_abc123">Remote, Germany</span></div>'
        self.assertEqual(card_location(soup(html).find("div")), "Remote, Germany")

    def test_strips_an_inline_label(self) -> None:
        html = '<div><a href="/jobs/1">Audio DSP Engineer</a>' \
               '<span class="list-item-location"><strong> Location:</strong> ' \
               'Northridge - California, USA</span></div>'
        self.assertEqual(
            card_location(soup(html).find("div")), "Northridge - California, USA"
        )

    def test_reads_a_material_icon_sibling(self) -> None:
        html = '<div><a href="/jobs/1">Audio DSP Engineer</a>' \
               '<span><i class="material-icons">place</i>' \
               '<span>Shanghai, China</span></span></div>'
        self.assertEqual(card_location(soup(html).find("div")), "Shanghai, China")

    def test_ignores_a_filter_dropdown(self) -> None:
        html = '<div><a href="/jobs/1">Audio DSP Engineer</a>' \
               '<select title="Location" name="location_filter">' \
               '<option value="1">UK</option><option value="4">USA</option>' \
               '</select></div>'
        self.assertIsNone(card_location(soup(html).find("div")))

    def test_ignores_a_language_switcher(self) -> None:
        html = '<div><a href="/jobs/1">Audio DSP Engineer</a>' \
               '<span class="lang">Français (Canada)</span></div>'
        self.assertIsNone(card_location(soup(html).find("div")))

    def test_returns_none_when_the_card_has_no_location(self) -> None:
        html = '<div><a href="/jobs/1">Audio DSP Engineer</a>' \
               '<span class="contract">Full time (37.5 hours per week)</span></div>'
        self.assertIsNone(card_location(soup(html).find("div")))


class TestMultipleLocationEntries(unittest.TestCase):
    def _card(self, second: str):
        html = (
            '<div><a href="/jobs/1">Audio DSP Engineer</a>'
            '<div class="job-component-list-location"><ul>'
            '<li><span>Remote, Illinois, United States</span></li>'
            '<li><span>' + second + '</span></li>'
            '</ul></div></div>'
        )
        return soup(html).find("div")

    def test_entries_are_joined_with_a_segment_separator(self) -> None:
        self.assertEqual(
            card_location(self._card("Remote, Texas, United States")),
            "Remote, Illinois, United States; Remote, Texas, United States",
        )

    def test_two_countries_still_resolve_to_none(self) -> None:
        from scraper.countries import detect_country

        value = card_location(self._card("Remote, Bavaria, Germany"))
        self.assertEqual(
            value, "Remote, Illinois, United States; Remote, Bavaria, Germany"
        )
        self.assertIsNone(detect_country(value))

    def test_a_single_entry_is_not_reshaped(self) -> None:
        html = (
            '<div><a href="/jobs/1">Audio DSP Engineer</a>'
            '<div class="job-component-list-location"><ul>'
            '<li><span>Remote, Germany</span></li>'
            '</ul></div></div>'
        )
        self.assertEqual(card_location(soup(html).find("div")), "Remote, Germany")


class TestAnchorLocation(unittest.TestCase):
    def test_walks_past_a_heading_wrapper(self) -> None:
        html = '<div class="row"><h3><a href="/jobs/1">Audio DSP Engineer</a></h3>' \
               '<p class="_sf_location">Staefa, Switzerland</p></div>'
        self.assertEqual(anchor_location(first_anchor(html)), "Staefa, Switzerland")

    def test_stops_before_a_container_holding_other_jobs(self) -> None:
        html = (
            '<ul>'
            '<li><a href="/jobs/1">Audio DSP Engineer</a></li>'
            '<li><a href="/jobs/2">Acoustic Engineer</a>'
            '<span class="location">Berlin, Germany</span></li>'
            '</ul>'
        )
        anchor = soup(html).find("a", href="/jobs/1")
        self.assertIsNone(anchor_location(anchor))

    def test_does_not_reach_a_page_level_filter(self) -> None:
        html = (
            '<body><span class="location-filter">United Kingdom</span>'
            '<div><h3><a href="/jobs/1">Audio DSP Engineer</a></h3></div></body>'
        )
        self.assertIsNone(anchor_location(soup(html).find("a")))


class TestExtractJobLinksCarriesLocation(unittest.TestCase):
    def test_location_reaches_the_raw_job(self) -> None:
        html = (
            '<div class="card"><h3><a href="/careers/jobs/audio-dsp-engineer-123">'
            'Audio DSP Engineer</a></h3>'
            '<p class="_sf_location">Staefa, Switzerland</p></div>'
        )
        jobs = extract_job_links(html, BASE)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].location, "Staefa, Switzerland")

    def test_absent_location_stays_none(self) -> None:
        html = (
            '<div class="card"><h3><a href="/careers/jobs/audio-dsp-engineer-123">'
            'Audio DSP Engineer</a></h3></div>'
        )
        jobs = extract_job_links(html, BASE)
        self.assertEqual(len(jobs), 1)
        self.assertIsNone(jobs[0].location)


class TestJsonLdMerge(unittest.TestCase):
    def _html(self, jsonld_location: str) -> str:
        return (
            '<div class="card"><h3><a href="/careers/jobs/audio-dsp-engineer-123">'
            'Audio DSP Engineer</a></h3>'
            '<p class="_sf_location">Staefa, Switzerland</p></div>'
            '<script type="application/ld+json">'
            '{"@type": "JobPosting", "title": "Audio DSP Engineer",'
            ' "url": "https://example.com/careers/jobs/audio-dsp-engineer-123"'
            + jsonld_location
            + '}</script>'
        )

    def test_jsonld_location_wins_over_the_card(self) -> None:
        jobs = extract_jobs(self._html(', "jobLocation": "Munich, Germany"'), BASE)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].location, "Munich, Germany")

    def test_card_location_fills_in_when_jsonld_has_none(self) -> None:
        jobs = extract_jobs(self._html(""), BASE)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].location, "Staefa, Switzerland")


if __name__ == "__main__":
    unittest.main()
