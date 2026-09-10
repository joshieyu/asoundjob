from __future__ import annotations

import unittest

from scraper.countries import COUNTRY_NAMES, country_name, detect_country


class TestExplicitCountryNames(unittest.TestCase):
    def test_trailing_country_name_wins(self) -> None:
        cases = {
            "Berlin, Germany (Hybrid)": "DE",
            "Hsinchu, Taiwan": "TW",
            "London, England, United Kingdom": "GB",
            "Paris, France": "FR",
            "Toluca, Estado de México - Mexico": "MX",
        }
        for location, expected in cases.items():
            with self.subTest(location=location):
                self.assertEqual(detect_country(location), expected)

    def test_country_name_outranks_a_conflicting_prefix_code(self) -> None:
        self.assertEqual(detect_country("CH - Shanghai, China"), "CN")
        self.assertEqual(detect_country("IN - Bangalore, India"), "IN")
        self.assertEqual(detect_country("ES - Barcelona, Spain"), "ES")

    def test_two_letter_country_alias(self) -> None:
        self.assertEqual(detect_country("USA | Remote"), "US")
        self.assertEqual(detect_country("US, MA - Framingham"), "US")
        self.assertEqual(detect_country("Cambridge, UK"), "GB")

    def test_alpha3_codes(self) -> None:
        self.assertEqual(detect_country("CHN, Shenzhen BOC"), "CN")


class TestUsStatesAndCities(unittest.TestCase):
    def test_state_code_after_a_city(self) -> None:
        for location in ("San Francisco, CA", "Pasadena, CA", "Brooklyn, NY"):
            with self.subTest(location=location):
                self.assertEqual(detect_country(location), "US")

    def test_state_name(self) -> None:
        self.assertEqual(detect_country("Denver, Colorado"), "US")
        self.assertEqual(detect_country("Washington, District of Columbia"), "US")

    def test_address_with_a_trailing_zip(self) -> None:
        self.assertEqual(
            detect_country("Spokane, WA: 5106 S. Palouse Hwy, 99223"), "US"
        )

    def test_bare_city(self) -> None:
        self.assertEqual(detect_country("Cupertino"), "US")
        self.assertEqual(detect_country("Ballerup"), "DK")

    def test_a_city_outranks_a_colliding_state_code(self) -> None:
        self.assertEqual(detect_country("Darmstadt, DE"), "DE")

    def test_city_with_a_trailing_qualifier(self) -> None:
        self.assertEqual(detect_country("Stockholm HQ"), "SE")
        self.assertEqual(detect_country("Shanghai Metro Area"), "CN")
        self.assertEqual(detect_country("Navi Mumbai, Rupa Renaissance"), "IN")


class TestCanada(unittest.TestCase):
    def test_province_code_before_a_city(self) -> None:
        self.assertEqual(detect_country("AB, Edmonton"), "CA")

    def test_country_name_not_read_as_california(self) -> None:
        self.assertEqual(detect_country("CA - Canada"), "CA")

    def test_parenthetical_province(self) -> None:
        self.assertEqual(detect_country("Remote (Quebec)"), "CA")


class TestAmbiguityResolvesToUnknown(unittest.TestCase):
    def test_placeholder_locations(self) -> None:
        for location in (
            "2 Locations",
            "Remote",
            "Remote Worker - WFH",
            "EMEA | Remote",
            "Worldwide",
            "Currie Gymnasium",
            "",
            None,
        ):
            with self.subTest(location=location):
                self.assertIsNone(detect_country(location))

    def test_a_city_in_two_countries_is_not_guessed(self) -> None:
        self.assertIsNone(detect_country("Cambridge"))

    def test_multiple_countries_are_not_guessed(self) -> None:
        for location in (
            "CA - Canada; US - United States",
            "Berlin, London",
            "Remote - United Kingdom; Remote - USA CENTRAL time zone",
            "ES - Spain; GB - United Kingdom; IE - Ireland; PT - Portugal",
        ):
            with self.subTest(location=location):
                self.assertIsNone(detect_country(location))


class TestCountryNames(unittest.TestCase):
    def test_lookup(self) -> None:
        self.assertEqual(country_name("US"), "United States")
        self.assertEqual(country_name("gb"), "United Kingdom")
        self.assertIsNone(country_name(None))
        self.assertIsNone(country_name("ZZ"))

    def test_every_mapped_code_has_a_display_name(self) -> None:
        from scraper.countries import CITY_COUNTRY, COUNTRY_ALIASES, COUNTRY_ALPHA3

        for mapping in (COUNTRY_ALIASES, CITY_COUNTRY, COUNTRY_ALPHA3):
            for code in set(mapping.values()):
                with self.subTest(code=code):
                    self.assertIn(code, COUNTRY_NAMES)


if __name__ == "__main__":
    unittest.main()
