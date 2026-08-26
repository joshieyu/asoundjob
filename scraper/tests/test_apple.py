from __future__ import annotations

import unittest

from scraper.scrapers.ats.apple import (
    AppleScraper,
    _extract_hydration_data,
    _parse_result,
    _parse_search_page,
)


def make_company(url: str):
    from scraper.models import Company

    return Company(
        id=1,
        name="Apple",
        slug="apple",
        category="Audio Software",
        careers_url=url,
    )


HYDRATION_JSON = (
    '{"loaderData":{"search":{"searchResults":['
    '{"id":"200679909-0836","postingTitle":"Software Engineer - VE",'
    '"jobSummary":"Work on virtual engineering.",'
    '"locations":[{"name":"Cupertino","countryName":"United States"}],'
    '"postingDate":"Aug 26, 2026",'
    '"team":{"teamName":"Hardware"},'
    '"transformedPostingTitle":"software-engineer-ve",'
    '"reqId":"200679909-0836"},'
    '{"id":"PIPE-123","postingTitle":"Audio DSP Engineer",'
    '"jobSummary":"Design audio algorithms.",'
    '"locations":[{"name":"Cupertino"}],'
    '"postingDate":"Aug 25, 2026",'
    '"team":{"teamName":"Software and Services"},'
    '"transformedPostingTitle":"audio-dsp-engineer",'
    '"reqId":"PIPE-123"}'
    '],"totalRecords":2,"page":1}}}'
)

HYDRATION_HTML = (
    '<html><script>window.__staticRouterHydrationData = JSON.parse("'
    + HYDRATION_JSON.replace('"', '\\"')
    + '");</script></html>'
)


class TestAppleParser(unittest.TestCase):
    def test_parse_search_page(self) -> None:
        jobs = _parse_search_page(HYDRATION_HTML)
        self.assertEqual(len(jobs), 2)
        first = jobs[0]
        self.assertEqual(first.title, "Software Engineer - VE")
        self.assertEqual(first.external_id, "200679909-0836")
        self.assertEqual(
            first.url,
            "https://jobs.apple.com/en-us/details/200679909-0836/software-engineer-ve",
        )
        self.assertEqual(first.location, "Cupertino")
        self.assertIn("Hardware", first.description or "")
        self.assertIn("virtual engineering", first.description or "")

    def test_parse_result_missing_title(self) -> None:
        self.assertIsNone(_parse_result({"id": "1", "postingTitle": ""}))

    def test_parse_result_missing_url(self) -> None:
        self.assertIsNone(_parse_result({"postingTitle": "Engineer", "id": ""}))

    def test_extract_hydration_data(self) -> None:
        data = _extract_hydration_data(HYDRATION_HTML)
        assert data is not None
        self.assertIn("loaderData", data)

    def test_extract_hydration_data_none(self) -> None:
        self.assertIsNone(_extract_hydration_data("<html>no data</html>"))

    def test_can_handle(self) -> None:
        from scraper.config import load_settings

        scraper = AppleScraper(load_settings())
        self.assertTrue(
            scraper.can_handle(make_company("https://jobs.apple.com/en-us/search"))
        )
        self.assertFalse(scraper.can_handle(make_company("https://jobs.lever.co/acme")))
        self.assertFalse(scraper.can_handle(make_company("")))


if __name__ == "__main__":
    unittest.main()
