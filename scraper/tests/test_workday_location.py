from __future__ import annotations

import unittest

from scraper.scrapers.ats.workday import apply_detail_location
from scraper.scrapers.base import RawJob


def job(location: str | None) -> RawJob:
    return RawJob(title="Audio Engineer", url="https://x.test/1", location=location)


def detail(**info: object) -> dict:
    return {"jobPostingInfo": info}


class WorkdayDetailLocationTest(unittest.TestCase):
    def test_bare_city_gets_its_country(self) -> None:
        j = job("Palaiseau")
        apply_detail_location(j, detail(location="Palaiseau", country={"descriptor": "France"}))
        self.assertEqual(j.location, "Palaiseau, France")

    def test_location_count_is_replaced_by_names(self) -> None:
        j = job("2 Locations")
        apply_detail_location(
            j,
            detail(
                location="Lititz",
                additionalLocations=["Boston", "Lititz"],
                country={"descriptor": "United States of America"},
            ),
        )
        self.assertEqual(j.location, "Lititz, United States of America; Boston")

    def test_known_country_is_left_alone(self) -> None:
        j = job("Berlin, Germany")
        apply_detail_location(
            j, detail(location="Berlin, Germany", country={"descriptor": "Germany"})
        )
        self.assertEqual(j.location, "Berlin, Germany")

    def test_requisition_country_is_a_fallback(self) -> None:
        j = job("Brest")
        apply_detail_location(
            j,
            detail(location="Brest", jobRequisitionLocation={"country": {"descriptor": "France"}}),
        )
        self.assertEqual(j.location, "Brest, France")

    def test_missing_detail_changes_nothing(self) -> None:
        j = job("3 Locations")
        apply_detail_location(j, {})
        self.assertEqual(j.location, "3 Locations")

    def test_empty_listing_location_uses_country(self) -> None:
        j = job(None)
        apply_detail_location(j, detail(country={"descriptor": "United States of America"}))
        self.assertEqual(j.location, "United States of America")


if __name__ == "__main__":
    unittest.main()
