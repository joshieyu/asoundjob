from __future__ import annotations

import asyncio
import unittest
from contextlib import contextmanager
from time import monotonic
from unittest.mock import patch

from scraper.config import load_settings
from scraper.models import Company
from scraper.scrapers.base import RawJob
from scraper.scrapers.http_scraper import HttpScraper
from scraper.scrapers.pdf_description import (
    enrich_pdf_jobs,
    is_pdf_url,
    pdf_text,
    wants_pdf_description,
)


@contextmanager
def fake_fetches(side_effect):
    def fake_page(url, settings, *args, **kwargs):
        return side_effect(url, settings), url

    with patch(
        "scraper.scrapers.http_scraper.fetch_html", side_effect=side_effect
    ), patch("scraper.scrapers.http_scraper.fetch_page", side_effect=fake_page):
        yield


def make_pdf(lines: list[str]) -> bytes:
    text_ops = ["BT", "/F1 10 Tf", "14 TL", "40 800 Td"]
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        text_ops.append(f"({escaped}) Tj T*")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


JOB_LINES = [
    "Audio Systems Design Engineer II",
    "Design and tune amplifiers and speakers for car audio systems.",
    "Measure frequency response, run listening tests and work with DSP tuning tools.",
    "Requirements: degree in electrical engineering or acoustics.",
    "Experience with loudspeaker design, amplifier topologies and audio measurement.",
]


class TestPdfText(unittest.TestCase):
    def test_extracts_text_from_pdf(self) -> None:
        text = pdf_text(make_pdf(JOB_LINES))
        assert text is not None
        self.assertIn("Audio Systems Design Engineer II", text)
        self.assertIn("loudspeaker design", text)

    def test_rejects_non_pdf_bytes(self) -> None:
        self.assertIsNone(pdf_text(b"<html><body>Not found</body></html>"))

    def test_rejects_pdf_with_too_little_text(self) -> None:
        self.assertIsNone(pdf_text(make_pdf(["Scanned page"])))

    def test_rejects_corrupt_pdf(self) -> None:
        self.assertIsNone(pdf_text(b"%PDF-1.4\nthis is not really a pdf"))


class TestWantsPdfDescription(unittest.TestCase):
    def job(self, title: str, url: str = "https://example.com/files/job.pdf") -> RawJob:
        return RawJob(title=title, url=url)

    def test_pdf_detection_ignores_query(self) -> None:
        self.assertTrue(is_pdf_url("https://example.com/a/Job%20Spec.PDF?v=2"))
        self.assertFalse(is_pdf_url("https://example.com/jobs/pdf-engineer"))

    def test_job_titles_are_wanted(self) -> None:
        for title in ("Quality Engineer", "Accounting Clerk", "Import /Export Clerk III"):
            self.assertTrue(wants_pdf_description(self.job(title), 200), title)

    def test_non_job_pdfs_are_skipped(self) -> None:
        for title in (
            "Download our brochure",
            "Employee benefits",
            "PDF employment application",
            "Download Job Application",
            "Accessibility Statement for ITVjobs.com",
        ):
            self.assertFalse(wants_pdf_description(self.job(title), 200), title)

    def test_html_links_and_described_jobs_are_skipped(self) -> None:
        self.assertFalse(
            wants_pdf_description(self.job("Quality Engineer", "https://example.com/jobs/1"), 200)
        )
        described = self.job("Quality Engineer")
        described.description = "x" * 300
        self.assertFalse(wants_pdf_description(described, 200))


class TestEnrichPdfJobs(unittest.TestCase):
    def test_fills_descriptions_and_tolerates_failures(self) -> None:
        settings = load_settings()
        good = RawJob(title="Audio Systems Design Engineer II", url="https://e.com/a.pdf")
        broken = RawJob(title="Quality Engineer", url="https://e.com/b.pdf")
        html_job = RawJob(title="Web Manager", url="https://e.com/jobs/web")

        def fake_fetch(url, settings, *args, **kwargs):
            if url.endswith("a.pdf"):
                return make_pdf(JOB_LINES)
            raise RuntimeError("connection reset")

        with patch(
            "scraper.scrapers.pdf_description.fetch_pdf_bytes", side_effect=fake_fetch
        ):
            count = asyncio.run(
                enrich_pdf_jobs([good, broken, html_job], settings, monotonic() + 30, 200)
            )
        self.assertEqual(count, 1)
        assert good.description is not None
        self.assertIn("loudspeaker design", good.description)
        self.assertIsNone(broken.description)
        self.assertIsNone(html_job.description)

    def test_past_deadline_fetches_nothing(self) -> None:
        settings = load_settings()
        job = RawJob(title="Quality Engineer", url="https://e.com/a.pdf")
        with patch("scraper.scrapers.pdf_description.fetch_pdf_bytes") as fetch:
            count = asyncio.run(enrich_pdf_jobs([job], settings, monotonic() - 1, 200))
        self.assertEqual(count, 0)
        fetch.assert_not_called()


PDF_LISTING_HTML = """
<html><body>
<div class="job"><h2>Audio Systems Design Engineer II</h2>
<a href="/media/audio_systems_design_engineer.pdf">View Details</a></div>
<div class="job"><h2>Quality Engineer</h2>
<a href="/media/quality_engineer.pdf">View Details</a></div>
</body></html>
"""


class TestHttpScraperPdfJobs(unittest.TestCase):
    def test_pdf_jobs_are_read_as_pdfs_not_html(self) -> None:
        company = Company(
            id=1,
            name="Car Audio Co",
            slug="car-audio-co",
            category="Car Audio",
            careers_url="https://example.com/careers",
        )
        html_urls: list[str] = []

        def fake_html(url, settings):
            html_urls.append(url)
            return PDF_LISTING_HTML

        def fake_pdf(url, settings):
            if "audio_systems" in url:
                return make_pdf(JOB_LINES)
            return make_pdf(["Scanned page"])

        with fake_fetches(fake_html
        ), patch(
            "scraper.scrapers.pdf_description.fetch_pdf_bytes", side_effect=fake_pdf
        ):
            jobs = asyncio.run(HttpScraper(load_settings()).fetch_jobs(company))

        self.assertEqual(html_urls, ["https://example.com/careers"])
        by_title = {job.title: job for job in jobs}
        described = by_title["Audio Systems Design Engineer II"]
        assert described.description is not None
        self.assertIn("loudspeaker design", described.description)
        self.assertIsNone(by_title["Quality Engineer"].description)


if __name__ == "__main__":
    unittest.main()
