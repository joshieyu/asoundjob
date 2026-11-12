from __future__ import annotations

import asyncio
import unittest

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.pipeline import ScrapePipeline

GLOBAL = "https://sonyglobal.wd1.myworkdayjobs.com/en-US/SonyGlobalCareers?q=audio"
JAPAN = "https://sonyglobal.wd1.myworkdayjobs.com/en-US/SonyJapanCareers?q=audio"


def make_company(ats_type: str, ats_slug: str, careers_url: str = GLOBAL) -> Company:
    return Company(
        id=3,
        name="Sony",
        slug="sony",
        category="Consumer Electronics & Tech",
        careers_url=careers_url,
        ats_type=ats_type,
        ats_slug=ats_slug,
    )


class TestExtraUrlAtsSlug(unittest.TestCase):
    def setUp(self) -> None:
        async def build() -> ScrapePipeline:
            return ScrapePipeline(load_settings())

        self.pipeline = asyncio.run(build())

    def test_extra_url_on_another_board_uses_its_own_slug(self) -> None:
        company = make_company("workday", "sonyglobal.wd1/SonyGlobalCareers")
        extra = self.pipeline._company_for_url(company, JAPAN)
        self.assertEqual(extra.ats_slug, "sonyglobal.wd1/SonyJapanCareers")
        self.assertEqual(extra.careers_url, JAPAN)

    def test_primary_url_keeps_the_stored_binding(self) -> None:
        company = make_company("workday", "sonyglobal.wd1/SonyGlobalCareers")
        self.assertIs(self.pipeline._company_for_url(company, GLOBAL), company)

    def test_ats_without_slug_extraction_keeps_stored_slug(self) -> None:
        company = make_company(
            "eightfold",
            "microsoft.com",
            "https://apply.careers.microsoft.com/careers?query=audio",
        )
        extra = self.pipeline._company_for_url(
            company, "https://apply.careers.microsoft.com/careers?query=speech"
        )
        self.assertEqual(extra.ats_slug, "microsoft.com")

    def test_unparseable_extra_url_keeps_stored_slug(self) -> None:
        company = make_company("workday", "sonyglobal.wd1/SonyGlobalCareers")
        extra = self.pipeline._company_for_url(company, "https://www.sony.com/careers")
        self.assertEqual(extra.ats_slug, "sonyglobal.wd1/SonyGlobalCareers")


if __name__ == "__main__":
    unittest.main()
