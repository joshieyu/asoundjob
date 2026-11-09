from __future__ import annotations

import asyncio
import io
import logging
import re
from time import monotonic
from typing import Optional
from urllib.parse import urlparse

from scraper.config import Settings
from scraper.detect_nonjob_rows import classify_title
from scraper.scrapers.base import RawJob
from scraper.scrapers.fetch import FetchError, _get_session

logger = logging.getLogger(__name__)

MAX_PDF_FETCHES = 25
PDF_FETCH_CONCURRENCY = 4
MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 10
MAX_PDF_TEXT_CHARS = 20000
MIN_PDF_TEXT_CHARS = 200
PDF_MAGIC = b"%PDF-"

NON_JOB_PDF_TITLE = re.compile(
    r"brochure|catalog|benefit|application form|employment application|"
    r"job application|download|privacy|polic(?:y|ies)|statement|cookie|"
    r"know your rights|eeo|harass|fraud|accessib|terms",
    re.IGNORECASE,
)
_INLINE_SPACE = re.compile(r"[ \t\r\f\v]+")
_SPACED_NEWLINES = re.compile(r" *\n *")
_EXTRA_NEWLINES = re.compile(r"\n{3,}")


def is_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def wants_pdf_description(job: RawJob, min_chars: int) -> bool:
    if not is_pdf_url(job.url):
        return False
    if job.description is not None and len(job.description) >= min_chars:
        return False
    if NON_JOB_PDF_TITLE.search(job.title):
        return False
    return classify_title(job.title) not in ("navigation", "boilerplate", "unreviewable")


def fetch_pdf_bytes(url: str, settings: Settings) -> bytes:
    response = _get_session(settings).get(
        url, timeout=settings.request_timeout, stream=True
    )
    try:
        if response.status_code != 200:
            raise FetchError(f"HTTP {response.status_code} for {url}")
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > MAX_PDF_BYTES:
                raise FetchError(f"PDF over {MAX_PDF_BYTES} bytes at {url}")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        response.close()


def pdf_text(data: bytes) -> Optional[str]:
    if not data.lstrip()[:5].startswith(PDF_MAGIC):
        return None
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [
            page.extract_text() or "" for page in reader.pages[:MAX_PDF_PAGES]
        ]
    except Exception as exc:
        logger.info("pdf: could not read document: %s", exc)
        return None
    text = "\n\n".join(pages)
    text = _INLINE_SPACE.sub(" ", text)
    text = _SPACED_NEWLINES.sub("\n", text)
    text = _EXTRA_NEWLINES.sub("\n\n", text).strip()
    if len(text) < MIN_PDF_TEXT_CHARS:
        return None
    return text[:MAX_PDF_TEXT_CHARS]


def fetch_pdf_description(url: str, settings: Settings) -> Optional[str]:
    return pdf_text(fetch_pdf_bytes(url, settings))


async def enrich_pdf_jobs(
    jobs: list[RawJob],
    settings: Settings,
    deadline: float,
    min_chars: int,
) -> int:
    candidates = [job for job in jobs if wants_pdf_description(job, min_chars)]
    candidates = candidates[:MAX_PDF_FETCHES]
    if not candidates:
        return 0
    semaphore = asyncio.Semaphore(PDF_FETCH_CONCURRENCY)
    enriched = 0

    async def enrich(job: RawJob) -> None:
        nonlocal enriched
        async with semaphore:
            if monotonic() >= deadline:
                return
            try:
                text = await asyncio.to_thread(fetch_pdf_description, job.url, settings)
            except Exception as exc:
                logger.warning("pdf: fetch failed for %s: %s", job.url, exc)
                return
        if text:
            job.description = text
            enriched += 1

    await asyncio.gather(*(enrich(job) for job in candidates))
    logger.info("pdf: read descriptions for %d/%d PDF jobs", enriched, len(candidates))
    return enriched
