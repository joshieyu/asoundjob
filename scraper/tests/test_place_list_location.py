from __future__ import annotations

import unittest

from scraper.scrapers.link_extraction import extract_job_links

BASE = "https://careers.example.com/jobs"


def card(locations: str, title: str = "Audio Software Engineer", job_id: str = "101") -> str:
    return (
        f'<a href="/jobs/{job_id}"><div><div><h3>{title}</h3></div>'
        f"<div>{locations}</div></div>"
        "<div><span>AR/VR</span><span>Engineering</span></div></a>"
    )


def page(*cards: str) -> str:
    return "<html><body><main>" + "".join(cards) + "</main></body></html>"


class PlaceListLocationTest(unittest.TestCase):
    def test_dot_separated_cities_without_location_markup(self) -> None:
        html = page(
            card("<span>Sunnyvale, CA</span><span>⋅</span><span>Redmond, WA</span>"),
            card("<span>Cambridge, UK</span>", "Research Scientist, Audio", "102"),
        )
        found = {job.url.rsplit("/", 1)[-1]: job.location for job in extract_job_links(html, BASE)}
        self.assertEqual(found["101"], "Sunnyvale, CA; Redmond, WA")
        self.assertEqual(found["102"], "Cambridge, UK")

    def test_non_place_text_is_not_a_location(self) -> None:
        html = page(
            card("<span>Engineering</span><span>⋅</span><span>Full time</span>"),
            card("<span>Reality Labs</span>", "Acoustic Engineer", "102"),
        )
        for job in extract_job_links(html, BASE):
            self.assertIsNone(job.location)

    def test_mixed_list_keeps_only_the_place(self) -> None:
        html = page(
            card("<span>Austin, TX</span><span>|</span><span>Hardware</span>"),
            card("<span>Berlin, Germany</span>", "DSP Engineer", "102"),
        )
        found = {job.url.rsplit("/", 1)[-1]: job.location for job in extract_job_links(html, BASE)}
        self.assertEqual(found["101"], "Austin, TX")
        self.assertEqual(found["102"], "Berlin, Germany")


if __name__ == "__main__":
    unittest.main()
