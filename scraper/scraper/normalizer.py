from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from scraper.config import Settings
from scraper.scrapers.base import RawJob

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "acoustics_architectural": (
        "acoustician",
        "acoustic consultant",
        "acoustical consulting",
        "room acoustics",
        "architectural acoustics",
        "acoustic design",
        "acoustic modeling",
        "acoustic simulation",
        "noise mitigation",
        "noise control",
        "sound isolation",
    ),
    "audio_ee": (
        "electrical engineer",
        "analog design",
        "analog engineer",
        "pcb layout",
        "pcb design",
        "circuit design",
        "amplifier design",
        "hardware engineer",
        "electronics engineer",
        "schematic capture",
    ),
    "transducers_microphones": (
        "transducer",
        "loudspeaker",
        "microphone design",
        "microphone engineer",
        "speaker design",
        "speaker engineer",
        "headphone design",
        "earbud",
        "hearing aid",
        "voice coil",
        "electroacoustic",
        "driver design",
    ),
    "audio_software": (
        "audio software",
        "audio programmer",
        "audio developer",
        "audio engineer software",
        "audio sdk",
        "audio api",
        "audio engine",
        "juce",
        "daw",
        "audio plugin",
        "vst",
        "aax",
        "clap plugin",
        "audio middleware",
    ),
    "music_technology": (
        "synthesizer",
        "synth designer",
        "midi",
        "guitar pedal",
        "effects pedal",
        "virtual instrument",
        "drum machine",
        "music technology",
        "music electronics",
        "sampler instruments",
    ),
    "audio_systems": (
        "audio systems engineer",
        "audio system engineer",
        "system integration audio",
        "audio tuning",
        "acoustic tuning",
        "tuning engineer",
        "audio validation",
        "audio test engineer",
        "audio measurement",
        "audio quality",
    ),
    "automotive_audio": (
        "automotive audio",
        "car audio",
        "vehicle audio",
        "cabin audio",
        "in-car audio",
        "infotainment",
        "automotive sound",
    ),
    "audio_dsp": (
        "dsp",
        "digital signal processing",
        "signal processing",
        "filter design",
        "fft",
        "convolution",
        "codec",
        "audio algorithm",
        "spatial audio",
        "3d audio",
        "surround sound",
        "equalization",
        "beamforming",
        "noise cancellation",
        "active noise cancelling",
        "echo cancellation",
        "sample rate conversion",
    ),
    "audio_aiml": (
        "machine learning",
        "deep learning",
        "neural network",
        "speech recognition",
        "speech processing",
        "source separation",
        "music information retrieval",
        "generative audio",
        "generative music",
        "ai ml",
        "ml engineer",
        "computational audiology",
        "voice assistant",
    ),
    "music_production_recording": (
        "mixing engineer",
        "mastering engineer",
        "recording engineer",
        "studio engineer",
        "music producer",
        "pro tools",
        "ableton",
        "logic pro",
        "beat making",
        "track mixing",
    ),
    "live_sound_events": (
        "live sound",
        "front of house",
        "foh engineer",
        "monitor engineer",
        "monitor mixer",
        "a/v technician",
        "av technician",
        "audio visual",
        "concert audio",
        "touring audio",
        "system tech",
        "rigging",
        "event production",
    ),
    "nvh": (
        "nvh",
        "noise vibration",
        "vibration analysis",
        "harshness",
        "vibro-acoustic",
        "vibroacoustic",
    ),
    "psychoacoustics_perception": (
        "psychoacoustic",
        "listening test",
        "perceptual audio",
        "sound quality evaluation",
        "hrtf",
        "audiology",
        "auditory",
        "hearing science",
        "subjective evaluation",
    ),
    "game_audio_interactive": (
        "game audio",
        "video game audio",
        "sound designer",
        "sound design",
        "interactive audio",
        "adaptive audio",
        "wwise",
        "fmod",
        "xr audio",
        "vr audio",
        "ar audio",
        "dialogue implementation",
    ),
}

SENIORITY_PATTERNS: list[tuple[str, str]] = [
    (r"\b(intern|internship|co-?op|trainee|apprentice|graduate|grad)\b", "entry"),
    (r"\b(entry[- ]level|junior|jr\.?)\b", "entry"),
    (
        r"\b(manager|director|vp\b|vice president|chief|head of)",
        "manager",
    ),
    (r"\b(lead|principal|staff|distinguished|fellow)\b", "lead"),
    (r"\b(senior|snr\.?|sr\.?)\b", "senior"),
]

JOB_TYPE_PATTERNS: list[tuple[str, str]] = [
    (r"full[- ]?time|permanent", "full-time"),
    (r"part[- ]?time", "part-time"),
    (r"contract|contractor|freelance|c2h|corp[- ]to[- ]corp", "contract"),
    (r"intern(ship)?|co-?op", "internship"),
    (r"temporary|temp[- ]to[- ]perm|seasonal", "temporary"),
    (r"volunteer", "volunteer"),
]

REMOTE_PATTERNS = re.compile(
    r"\b(remote|work from home|wfh|work anywhere|distributed team|telecommut)",
    re.IGNORECASE,
)

AUDIO_TITLE_STRONG = re.compile(
    r"\b(audio|sound|acoustic[s]?|dsp|signal processing|transducer|loudspeaker|"
    r"microphone|hearing aid|live sound|foh|front of house|mixing|mastering|"
    r"game audio|sound design|voice|speech|sonar|a/v|audio-?visual)\b",
    re.IGNORECASE,
)

AUDIO_TITLE_WEAK = re.compile(
    r"\b(music|midi|synth(esizer)?|studio|daw|vinyl|guitar|drum|hearing|"
    r"listening|psychoacoustic)\b",
    re.IGNORECASE,
)

AUDIO_DESCRIPTION = re.compile(
    r"\b(audio|sound|acoustic[s]?|dsp|loudspeaker|microphone|transducer|"
    r"listening tests|mixing|mastering|daw|studio|music)\b",
    re.IGNORECASE,
)

CORPORATE_ROLE = re.compile(
    r"\b(accountant|accounts? payable|accounts? receivable|paralegal|attorney|"
    r"counsel|recruiter|human resources|hr generalist|people operations|payroll|"
    r"barista|warehouse|forklift|delivery driver|truck driver|driver|real estate|"
    r"facilities|janitor|security guard|receptionist|data entry|call center|"
    r"insurance underwriter|tax|procurement|logistics|supply chain|help desk|"
    r"fp&a|financial analyst)\b",
    re.IGNORECASE,
)

PARTIAL_SCOPE_CATEGORIES = {
    "Automotive OEMs",
    "Consumer Electronics & Tech",
    "Streaming & Music Services",
    "Audio IP & Licensing",
    "Audio Retailers & Distributors",
}

SCOPE_THRESHOLDS = {"native": 30, "partial": 50, "all": 50}


def category_to_scope(category: str) -> str:
    return "partial" if category in PARTIAL_SCOPE_CATEGORIES else "native"


def score_relevance(
    title: str,
    description: str | None,
    job_categories: list[str],
    audio_scope: str = "native",
) -> tuple[int, bool]:
    score = 35 if audio_scope == "native" else 0

    if AUDIO_TITLE_STRONG.search(title):
        score += 50
    elif AUDIO_TITLE_WEAK.search(title):
        score += 25

    if job_categories:
        score += 25

    if description and AUDIO_DESCRIPTION.search(description[:4000]):
        score += 15

    if CORPORATE_ROLE.search(title):
        score -= 45

    threshold = SCOPE_THRESHOLDS.get(audio_scope, 50)
    return score, score >= threshold

CURRENCY_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR"}

SALARY_RANGE_RE = re.compile(
    r"(?P<cur1>[$£€]|USD|EUR|GBP|CAD|AUD|CHF|SEK|NOK|DKK)?\s*"
    r"(?P<a>\d{1,3}(?:[,.]\d{3})+|\d+(?:\.\d+)?)\s*(?P<amult>[kK])?\s*"
    r"(?:[-–—~]|\bto\b)\s*"
    r"(?P<cur2>[$£€])?\s*"
    r"(?P<b>\d{1,3}(?:[,.]\d{3})+|\d+(?:\.\d+)?)\s*(?P<bmult>[kK])?"
    r"(?:\s*(?P<code>USD|EUR|GBP|CAD|AUD|CHF|SEK|NOK|DKK))?",
)

SALARY_SINGLE_RE = re.compile(
    r"(?P<cur>[$£€])\s*(?P<v>\d{1,3}(?:[,.]\d{3})+|\d+(?:\.\d+)?)\s*(?P<mult>[kK])?"
    r"\s*(?P<plus>\+)?"
    r"(?:\s*(?P<code>USD|EUR|GBP))?",
)


@dataclass
class NormalizedJob:
    title: str
    url: str
    external_id: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    remote: bool = False
    job_type: Optional[str] = None
    seniority: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    job_categories: list[str] = field(default_factory=list)
    posted_date: Optional[date] = None
    relevance_score: int = 0
    is_audio_related: bool = True


def detect_seniority(title: str) -> Optional[str]:
    lowered = title.lower()
    for pattern, level in SENIORITY_PATTERNS:
        if re.search(pattern, lowered):
            return level
    return "mid"


def _compile_category_patterns() -> dict[str, re.Pattern[str]]:
    patterns: dict[str, re.Pattern[str]] = {}
    for category_id, keywords in CATEGORY_KEYWORDS.items():
        escaped = [re.escape(k) for k in keywords]
        joined = "|".join(escaped)
        patterns[category_id] = re.compile(rf"(?<!\w)(?:{joined})(?!\w)", re.IGNORECASE)
    return patterns


CATEGORY_PATTERNS = _compile_category_patterns()


def classify_categories(title: str, description: str | None) -> list[str]:
    text_parts = [title.lower()]
    if description:
        text_parts.append(description[:6000].lower())
    matched: list[str] = []
    for category_id in CATEGORY_KEYWORDS:
        pattern = CATEGORY_PATTERNS[category_id]
        if pattern.search(text_parts[0]):
            matched.append(category_id)
            continue
        if len(text_parts) > 1 and pattern.search(text_parts[1]):
            matched.append(category_id)
    return matched


def _parse_number(raw: str) -> int:
    cleaned = raw.replace(",", "")
    return int(float(cleaned))


def _annualize(value: int) -> int:
    if 15 <= value < 200:
        return value * 2080
    return value


def _plausible_annual(value: int) -> bool:
    return 10_000 <= value <= 2_000_000


def parse_salary(text: str | None) -> tuple[Optional[int], Optional[int], Optional[str]]:
    if not text:
        return None, None, None

    match = SALARY_RANGE_RE.search(text)
    if match:
        has_context = bool(
            match.group("cur1")
            or match.group("cur2")
            or match.group("code")
            or match.group("amult")
            or match.group("bmult")
        )
        low = _parse_number(match.group("a"))
        high = _parse_number(match.group("b"))
        if match.group("amult"):
            low *= 1000
        elif low < 1000 and match.group("bmult"):
            low *= 1000
        if match.group("bmult"):
            high *= 1000
        elif high < 1000 and match.group("amult"):
            high *= 1000
        if not has_context and (low < 10_000 or high < 10_000):
            return None, None, None
        low = _annualize(low)
        high = _annualize(high)
        if _plausible_annual(low) and _plausible_annual(high) and high >= low:
            currency = _resolve_currency(match.group("cur1"), match.group("code"))
            return low, high, currency

    match = SALARY_SINGLE_RE.search(text)
    if match:
        value = _parse_number(match.group("v"))
        if match.group("mult"):
            value *= 1000
        value = _annualize(value)
        if _plausible_annual(value):
            currency = _resolve_currency(match.group("cur"), match.group("code"))
            return value, None, currency

    return None, None, None


def _resolve_currency(symbol: str | None, code: str | None) -> Optional[str]:
    if code:
        return code.upper()
    if symbol:
        return CURRENCY_SYMBOLS.get(symbol, symbol)
    return None


def normalize_job_type(text: str | None) -> Optional[str]:
    if not text:
        return None
    lowered = text.lower()
    for pattern, job_type in JOB_TYPE_PATTERNS:
        if re.search(pattern, lowered):
            return job_type
    return None


def detect_remote(
    location: str | None, title: str, description: str | None
) -> bool:
    for candidate in (location, title):
        if candidate and REMOTE_PATTERNS.search(candidate):
            return True
    if description:
        head = description[:1500].lower()
        if REMOTE_PATTERNS.search(head):
            return True
    return False


def clean_location(location: str | None) -> Optional[str]:
    if not location:
        return None
    cleaned = re.sub(r"\s+", " ", location).strip(" ,;-")
    return cleaned or None


def load_valid_category_ids(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return {c["id"] for c in data["job_categories"]}


class Normalizer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.valid_ids: set[str] | None = None
        categories_path = settings.data_dir / "audio_job_categories.json"
        try:
            self.valid_ids = load_valid_category_ids(categories_path)
        except OSError:
            logger.warning("categories file missing at %s", categories_path)

    def normalize(self, raw: RawJob, audio_scope: str = "native") -> NormalizedJob:
        salary_text = " ".join(
            part for part in (raw.title, raw.description) if part
        )
        salary_min, salary_max, salary_currency = parse_salary(salary_text)

        categories = classify_categories(raw.title, raw.description)
        if self.valid_ids is not None:
            categories = [c for c in categories if c in self.valid_ids]

        relevance_score, is_audio_related = score_relevance(
            raw.title, raw.description, categories, audio_scope
        )

        job_type = normalize_job_type(raw.job_type)
        if job_type is None:
            job_type = normalize_job_type(raw.title)
        if job_type is None and raw.description:
            job_type = normalize_job_type(raw.description[:2000])

        return NormalizedJob(
            title=raw.title.strip(),
            url=raw.url.strip(),
            external_id=raw.external_id,
            location=clean_location(raw.location),
            description=raw.description,
            remote=detect_remote(raw.location, raw.title, raw.description) or raw.remote_hint,
            job_type=job_type,
            seniority=detect_seniority(raw.title),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            job_categories=categories,
            posted_date=raw.posted_date,
            relevance_score=relevance_score,
            is_audio_related=is_audio_related,
        )
