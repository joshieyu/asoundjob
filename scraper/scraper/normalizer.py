from __future__ import annotations

import html
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

CATEGORY_KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "audio_ee": {
        "strong": (
            "analog design",
            "analog circuit",
            "pcb layout",
            "pcb design",
            "circuit design",
            "amplifier design",
            "electronics engineer",
            "schematic capture",
            "mixed-signal",
            "mixed signal",
            "power supply",
            "op-amp",
            "op amp",
            "signal integrity",
            "board bring-up",
            "pcba",
            "audio electronics",
            "audio circuit design",
            "audio pcb",
        ),
        "weak": (
            "electrical engineer",
            "hardware engineer",
        ),
    },
    "transducers": {
        "strong": (
            "transducer",
            "transducer design",
            "transducer engineer",
            "transducer characterization",
            "loudspeaker",
            "loudspeaker design",
            "speaker design",
            "speaker engineer",
            "speaker driver",
            "headphone design",
            "headphone driver",
            "earbud driver",
            "earbud",
            "voice coil",
            "electroacoustic",
            "electroacoustic transducer",
            "driver design",
            "acoustic transducer",
            "acoustic chamber",
            "acoustic simulation",
            "acoustic modeling",
            "acoustic design",
            "klippel",
            "soundcheck",
            "audio precision",
            "lumped parameter",
            "finite element",
            "comsol",
            "diaphragm design",
            "magnet design",
            "moving coil",
            "studio monitor",
            "acoustic engineer",
            "acoustics engineer",
        ),
        "weak": (
            "tweeter",
            "woofer",
            "subwoofer",
            "diaphragm",
            "magnet assembly",
        ),
    },
    "microphones_recording": {
        "strong": (
            "microphone design",
            "microphone engineer",
            "microphone array",
            "mems microphone",
            "microphone system",
            "microphone/telephony",
            "wireless microphone",
            "microphone integration",
            "audio capture",
            "audio capture system",
            "beamforming",
            "mic array",
            "microphone characterization",
            "microphone calibration",
            "microphone testing",
            "condenser microphone",
            "dynamic microphone",
            "microphone capsule",
            "microphone",
        ),
        "weak": (
            "ingress protection",
        ),
    },
    "audio_software": {
        "strong": (
            "audio software engineer",
            "audio application",
            "audio applications",
            "media applications engineer",
            "music app",
            "music apps",
            "airplay",
            "audio framework",
            "core audio",
            "audio playback",
            "audio streaming",
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
            "audio stack",
            "audio hal",
            "audio flinger",
            "audio driver",
            "audio & music apps",
        ),
        "weak": (
            "audio pipeline",
            "real-time audio",
        ),
    },
    "music_technology": {
        "strong": (
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
        "weak": (
            "synth",
            "sampler",
            "drum kit",
        ),
    },
    "audio_systems": {
        "strong": (
            "audio systems engineer",
            "audio system engineer",
            "audio system design",
            "system integration audio",
            "audio tuning",
            "acoustic tuning",
            "acoustic engineer",
            "tuning engineer",
            "audio subsystem",
            "audio subsystems",
            "acoustic system",
            "acoustic systems",
            "system-level audio",
            "audio integration",
            "av engineer",
            "audio video engineer",
            "acoustics engineer",
            "acoustic engineering",
            "acoustics engineering",
            "audio architecture",
            "audio system",
            "audio systems",
            "audio architect",
            "program manager, audio",
            "program manager - audio",
            "program manager- audio",
        ),
        "weak": (
            "systems engineering",
            "audio engineer",
            "connected audio",
            "audio device",
            "audio technology",
            "audio product",
            "audio video",
        ),
    },
    "test_measurement_qa": {
        "strong": (
            "audio test",
            "audio testing",
            "audio test engineer",
            "audio test plan",
            "audio test automation",
            "audio measurement",
            "audio metrology",
            "audio validation",
            "audio validation engineer",
            "audio verification",
            "audio qualification",
            "audio benchmark",
            "audio benchmarking",
            "audio quality engineer",
            "audio qa",
            "acoustic test",
            "acoustic testing",
            "acoustic measurement",
            "acoustical measurement",
            "acoustic validation",
            "acoustic characterization",
            "electroacoustic measurement",
            "electroacoustic test",
            "electroacoustic testing",
            "sound quality engineer",
            "anechoic chamber",
            "anechoic",
            "audio precision",
            "klippel",
            "real ear",
            "real-ear",
            "insertion gain",
            "ear simulator",
            "acoustic coupler",
            "acoustic calibrator",
            "acoustic test fixture",
            "measurement microphone",
            "head and torso simulator",
            "head-and-torso simulator",
        ),
        "weak": (
            "test engineer",
            "test engineering",
            "test automation",
            "test fixture",
            "test bench",
            "test equipment",
            "measurement engineer",
            "metrology",
            "calibration",
            "validation engineer",
            "verification engineer",
            "quality assurance",
            "quality engineer",
            "qa engineer",
            "reliability engineer",
            "reliability test",
            "production test",
            "device under test",
            "test protocol",
            "test report",
            "measurement bench",
            "measurement lab",
            "acoustic lab",
            "test lab",
            "design verification",
            "audio quality",
        ),
    },
    "automotive_audio": {
        "strong": (
            "automotive audio",
            "car audio",
            "vehicle audio",
            "cabin audio",
            "in-car audio",
            "automotive sound",
            "automotive acoustic",
        ),
        "weak": (
            "infotainment",
            "vehicle cabin",
        ),
    },
    "audio_dsp_embedded": {
        "strong": (
            "audio embedded",
            "audio firmware",
            "audio dsp",
            "audio codec",
            "audio sensor",
            "dsp",
            "digital signal processing",
            "filter design",
            "fft",
            "convolution",
            "audio algorithm",
            "spatial audio",
            "noise cancellation",
            "active noise cancelling",
            "echo cancellation",
            "sample rate conversion",
            "embedded linux",
            "dsp architecture",
            "audio sw",
            "alsa",
            "audio processing algorithm",
            "biquad",
            "agc",
            "drc",
            "noise suppression",
            "audio tuning algorithm",
            "dynamics processing",
            "loudspeaker protection",
        ),
        "weak": (
            "embedded system",
            "embedded software",
            "embedded firmware",
            "signal processing",
            "codec",
            "rtos",
            "bsp",
            "kernel driver",
            "bare metal",
            "iir",
            "fir",
        ),
    },
    "audio_aiml": {
        "strong": (
            "speech recognition",
            "speech model",
            "multimodal language",
            "speech and audio",
            "speech & audio",
            "audio understanding",
            "speech processing",
            "source separation",
            "music information retrieval",
            "generative audio",
            "generative music",
            "voice assistant",
            "computational audiology",
            "audio intelligence",
            "machine learned audio",
            "voice agent",
            "voice ai",
            "speech-to-text",
            "text-to-speech",
            "speech synthesis",
            "conversational ai",
            "speaker diarization",
            "wake word",
            "keyword spotting",
            "audio machine learning",
            "audio ml",
            "speech ai",
            "voice processing",
            "siri speech",
            "conversational speech",
            "computer vision & audio",
            "voice os",
        ),
        "weak": (
            "machine learning",
            "deep learning",
            "neural network",
            "ml engineer",
            "applied scientist",
            "genai",
            "ai ml",
            "asr",
            "tts",
        ),
    },
    "audio_research": {
        "strong": (
            "research acoustic",
            "acoustic research",
            "audio research",
            "novel acoustic",
            "acoustic architecture",
            "acoustic research engineer",
            "research scientist audio",
            "audio research engineer",
            "audio research scientist",
            "spatial audio research",
            "speech, vision and audio",
        ),
        "weak": (
            "research engineer",
            "research scientist",
            "member of technical staff",
            "research staff",
            "reality labs",
            "research hardware",
            "research platforms",
            "original research",
            "director of research",
            "applied scientist",
            "machine learning applied researcher",
        ),
    },
    "music_production_recording": {
        "strong": (
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
            "audio producer",
        ),
        "weak": (
            "music production",
            "studio session",
        ),
    },
    "live_sound_events": {
        "strong": (
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
            "event production",
            "audio technician",
            "sound engineer",
            "production audio",
            "broadcast audio",
            "live audio engineer",
            "stage audio",
        ),
        "weak": (
            "rigging",
            "event av",
            "touring",
        ),
    },
    "nvh": {
        "strong": (
            "nvh",
            "noise vibration",
            "noise and vibration",
            "noise & vibration",
            "vibration analysis",
            "harshness",
            "vibro-acoustic",
            "vibroacoustic",
        ),
        "weak": (
            "structural vibration",
        ),
    },
    "psychoacoustics_perception": {
        "strong": (
            "psychoacoustic",
            "listening test",
            "perceptual audio",
            "sound quality evaluation",
            "hrtf",
            "psycho-acoustic",
            "spatial sound",
            "auditory perception",
            "sound perception",
        ),
        "weak": (
            "auditory",
            "listening",
            "human perception",
            "hearing science",
            "subjective evaluation",
        ),
    },
    "game_audio_interactive": {
        "strong": (
            "game audio",
            "video game audio",
            "interactive audio",
            "adaptive audio",
            "wwise",
            "fmod",
            "xr audio",
            "vr audio",
            "ar audio",
            "dialogue implementation",
            "game sound design",
        ),
        "weak": (
            "interactive sound",
            "audio middleware games",
        ),
    },
    "sound_design": {
        "strong": (
            "sound designer",
            "sound design",
            "foley",
            "audio designer",
            "sound artist",
            "sound creator",
            "audio identity",
            "sonic branding",
            "sound effects",
            "soundscapes",
            "sound design engineer",
        ),
        "weak": (
            "sonic",
            "audio branding",
        ),
    },
    "sales_marketing_cs": {
        "strong": (
            "partnerships manager",
            "customer success",
            "account executive",
            "brand strategy",
            "brand manager",
            "sales director",
            "product marketing",
            "demand generation",
            "go-to-market",
            "go to market",
            "channel partnerships",
            "creator program",
            "artist partnerships",
            "songwriting camp",
            "emerging creator",
            "editorial & curation",
            "director of sales",
        ),
        "weak": (),
    },
    "audiology_hearing": {
        "strong": (
            "audiologist",
            "audiology",
            "hearing instrument specialist",
            "hearing aid",
            "cochlear implant",
            "tinnitus",
            "audiometry",
            "hearing screening",
            "real ear measurement",
            "hearing care practitioner",
            "hearing care professional",
            "doctor of audiology",
            "hearing wellness",
            "hearing loss",
            "hearing evaluation",
            "hearing clinic",
        ),
        "weak": (
            "patient care coordinator",
            "hearing care",
            "aud fitting",
            "hearing test",
            "ent practice",
            "audiology support",
        ),
    },
    "audio_product_mechanical": {
        "strong": (
            "mechanical design engineer",
            "product design epm",
            "product design producer",
            "audio product design",
            "audio pd engineer",
            "audio pd",
            "product design engineer - audio",
            "product design engineer, audio",
            "advanced manufacturing engineer - audio",
            "advanced manufacturing engineer, audio",
            "audio fit",
            "acoustic fit",
            "audio nvh",
            "acoustic enclosure design",
            "transducer packaging",
            "audio mechanical engineer",
            "mechanical engineer, audio",
            "npi engineer, audio",
            "audio npi",
            "audio new product introduction",
        ),
        "weak": (
            "product design engineer",
            "mechanical engineer",
            "advanced manufacturing engineer",
            "new product introduction",
            "enclosure design",
            "housing design",
            "dfm",
            "tooling engineer",
        ),
    },
    "acoustics_consulting": {
        "strong": (
            "acoustic consultant",
            "acoustical consultant",
            "noise consultant",
            "building acoustics",
            "room acoustics",
            "architectural acoustics",
            "environmental acoustics",
            "noise control",
            "sound isolation",
            "reverberation control",
            "noise assessment",
            "acoustic consultancy",
            "acoustic design consultant",
            "noise and vibration consultant",
        ),
        "weak": (
            "acoustic consulting",
            "noise study",
            "reverberation",
        ),
    },
}

ANCHORED_CATEGORIES = {
    "test_measurement_qa",
    "audio_software",
    "audio_dsp_embedded",
    "audio_aiml",
    "audio_research",
    "audio_ee",
    "audio_product_mechanical",
}

AUDIO_ANCHOR = re.compile(
    r"\b(audio\w*|acoustic\w*|sound\w*|speech\w*|voice\w*|hearing|loudspeaker\w*|"
    r"speaker\w*|microphone\w*|transducer\w*|headphone\w*|earbud\w*|music\w*|sonic\w*|"
    r"psychoacoustic\w*|dsp)\b",
    re.IGNORECASE,
)

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
    (r"\bfull[- ]?time\b|permanent", "full-time"),
    (r"\bpart[- ]?time\b", "part-time"),
    (
        r"\bcontract (?:position|role|opportunity|job|employment|work|eng)\b"
        r"|\bcontractor\b|\bfreelance\b|c2h|corp[- ]to[- ]corp",
        "contract",
    ),
    (r"\bintern(ship)?\b|\bco[- ]?op\b", "internship"),
    (r"\btemporary\b|temp[- ]to[- ]perm|seasonal", "temporary"),
    (r"\bvolunteer\b", "volunteer"),
]

REMOTE_PATTERNS = re.compile(
    r"\b(remote|work from home|wfh|work anywhere|distributed team|telecommut)",
    re.IGNORECASE,
)

AUDIO_TITLE_STRONG = re.compile(
    r"\b(audio|sound|acoustic[s]?|dsp|signal processing|transducer|loudspeaker|"
    r"microphone|hearing aid|audiolog\w*|audiologist|live sound|foh|"
    r"front of house|mixing|mastering|game audio|sound design|voice|speech|"
    r"sonar|a/v|audio-?visual)\b",
    re.IGNORECASE,
)

AUDIO_TITLE_WEAK = re.compile(
    r"\b(music\w*|midi|synth\w*|studio\w*|daw|vinyl|guitar\w*|drum\w*|hearing|"
    r"listening|psychoacoustic|speaker\w*|noise|vibration|nvh)\b",
    re.IGNORECASE,
)

AUDIO_DESC_STRONG = re.compile(
    r"\b(audio|acoustic[s]?|dsp|loudspeaker|microphone|transducer|"
    r"audiolog\w*|audiologist|hearing aid|hearing instrument|hearing science|"
    r"beamforming|noise cancellation|echo cancellation|active noise|"
    r"spatial audio|spatial sound|psychoacoustic|hrtf|audio signal|"
    r"audio system|audio processing|audio quality|audio performance|"
    r"audio hardware|audio firmware|audio software|audio algorithm|"
    r"audio measurement|audio test|audio tuning|audio capture|"
    r"audio product|audio device|audio engineering|audio design)\b",
    re.IGNORECASE,
)

AUDIO_DESC_WEAK = re.compile(
    r"\b(sound|voice|speech|hearing|listening|music\w*|recording studio|"
    r"studio monitor|studio engineer|mixing studio|mastering studio|"
    r"mixing|mastering|daw|noisy|noise|vibration|nvh|speaker)\b",
    re.IGNORECASE,
)

NEGATIVE_SIGNALS = re.compile(
    r"(architect of record|interior design|building design|k-12 education|"
    r"higher education studio|entertainment release|linear channel)",
    re.IGNORECASE,
)

NEGATIVE_SIGNAL_PENALTY = 45

CORPORATE_ROLE = re.compile(
    r"\b(accountant|accounts? payable|accounts? receivable|paralegal|attorney|"
    r"counsel|recruiter|human resources|hr generalist|people operations|payroll|"
    r"barista|warehouse|forklift|delivery driver|truck driver|driver|real estate|"
    r"facilities|janitor|security guard|receptionist|data entry|call center|"
    r"insurance underwriter|tax|procurement|logistics|supply chain|help desk|"
    r"fp&a|financial analyst|finance analyst|revenue manager|revenue analyst|"
    r"revenue analytics|"
    r"internal audit|legal counsel|legal innovation|"
    r"office assistant|administrative|library|plumber|electrician|carpenter|"
    r"groundskeeper|custodian|housekeeper|mailroom|switchboard|"
    r"volleyball|athletic|coach|sports|intramural|"
    r"lecturer|instructor|teaching assistant|adjunct|professor of|"
    r"director of development|director of admissions|financial aid|"
    r"student affairs|student engagement|registrar|enrollment|"
    r"admissions|bursar|treasurer|controller|"
    r"network engineer|linux administrator|systems administrator|"
    r"database administrator|network architect|it support|it assistant|"
    r"desktop support|helpdesk|soc analyst|security analyst|"
    r"event coordinator|"
    r"talent acquisition|talent sourcer|onboarding specialist|"
    r"compensation|benefits manager|hr business partner|"
    r"project manager|project lead|program manager|"
    r"business analyst|real time analyst|"
    r"product designer|"
    r"it security|information security|"
    r"course technician|animal care|veterinary|"
    r"ecommerce|merchandising|commercial finance|"
    r"communications lead|corporate communications|"
    r"infrastructure architect|sourcing manager|"
    r"portfolio strategy|contact center|"
    r"customer enablement|strategic transformation|"
    r"vertical ai|alliances|"
    r"workforce management|pooling|"
    r"business development|"
    r"account manager|account management|"
    r"sales operations|sales enablement|sales manager|"
    r"marketing manager|marketing director|"
    r"growth manager|digital marketing|"
    r"community manager|"
    r"social media|content manager|"
    r"creative operations|"
    r"creative director|"
    r"conversion rate|"
    r"credit collections?|trade compliance|customs broker|"
    r"buyer|incoming inspection|incoming auditor|incentive plan|"
    r"office coordinator)\b",
    re.IGNORECASE,
)

PARTIAL_SCOPE_CATEGORIES = {
    "Automotive OEMs",
    "Consumer Electronics & Tech",
    "Streaming & Music Services",
    "Audio IP & Licensing",
    "Audio Retailers & Distributors",
    "Music Education Technology",
}

SCOPE_THRESHOLDS = {"native": 45, "partial": 50, "all": 55}


SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)

BLOCK_TAG_RE = re.compile(
    r"</?(p|div|br|li|ul|ol|h[1-6]|section|article|tr|table|thead|tbody|blockquote|hr)"
    r"[^>]*>",
    re.IGNORECASE,
)

TAG_RE = re.compile(r"<[^>]+>")

INLINE_WHITESPACE_RE = re.compile(r"[ \t\xa0]+")

LINE_WHITESPACE_RE = re.compile(r"[ \t]*\n[ \t]*")

EXTRA_NEWLINES_RE = re.compile(r"\n{3,}")

ROLE_START_MARKERS: tuple[str, ...] = (
    "what you'll do",
    "what you will do",
    "responsibilities",
    "about the role",
    "the role",
    "your role",
    "in this role",
    "requirements",
    "qualifications",
    "what we're looking for",
    "your impact",
    "key qualifications",
    "minimum qualifications",
    "who you are",
    "the opportunity",
    "job description",
    "duties",
)

TRAILING_BOILERPLATE_MARKERS: tuple[str, ...] = (
    "equal opportunity employer",
    "we are an equal",
    "eeo",
    "benefits include",
    "our benefits",
    "compensation and benefits",
    "privacy policy",
)


def category_to_scope(category: str) -> str:
    return "partial" if category in PARTIAL_SCOPE_CATEGORIES else "native"


def clean_description(raw: str | None) -> Optional[str]:
    if not raw:
        return None
    text = raw
    while True:
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped
    text = SCRIPT_STYLE_RE.sub(" ", text)
    text = BLOCK_TAG_RE.sub("\n", text)
    text = TAG_RE.sub(" ", text)
    text = INLINE_WHITESPACE_RE.sub(" ", text)
    text = LINE_WHITESPACE_RE.sub("\n", text)
    text = EXTRA_NEWLINES_RE.sub("\n\n", text)
    text = text.strip()
    return text or None


def _strip_trailing_boilerplate(text: str) -> str:
    length = len(text)
    if length == 0:
        return text
    zone_start = int(length * 0.6)
    lowered = text.lower()
    cut_at: Optional[int] = None
    for marker in TRAILING_BOILERPLATE_MARKERS:
        idx = lowered.find(marker, zone_start)
        if idx != -1 and (cut_at is None or idx < cut_at):
            cut_at = idx
    if cut_at is not None:
        return text[:cut_at].rstrip()
    return text


def extract_role_text(description: str | None) -> str:
    cleaned = clean_description(description)
    if not cleaned:
        return ""

    normalized = cleaned.replace("’", "'").replace("‘", "'")
    lowered = normalized.lower()

    marker_idx: Optional[int] = None
    for marker in ROLE_START_MARKERS:
        pos = lowered.find(marker)
        if pos != -1 and (marker_idx is None or pos < marker_idx):
            marker_idx = pos

    if marker_idx is not None:
        role_text = cleaned[marker_idx:]
    else:
        boundary = cleaned.find("\n\n")
        if boundary == -1:
            boundary = len(cleaned)
        cutoff = min(boundary, 600)
        role_text = cleaned[cutoff:].lstrip()

    role_text = _strip_trailing_boilerplate(role_text)

    if len(role_text) < 200:
        return cleaned
    return role_text


def score_relevance(
    title: str,
    description: str | None,
    job_categories: list[str],
    audio_scope: str = "native",
) -> tuple[int, bool]:
    score = 0

    title_strong = bool(AUDIO_TITLE_STRONG.search(title))
    title_weak = bool(AUDIO_TITLE_WEAK.search(title))

    if title_strong:
        score += 60
    elif title_weak:
        score += 30

    cleaned_description = clean_description(description) or ""
    role_text = extract_role_text(description)
    role_lower = role_text.lower()[:8000]

    strong_mentions = len(AUDIO_DESC_STRONG.findall(role_lower))
    weak_mentions = len(AUDIO_DESC_WEAK.findall(role_lower))
    if strong_mentions >= 3:
        score += 35
    elif strong_mentions >= 1:
        score += 20
    elif weak_mentions >= 3:
        score += 15

    if job_categories:
        if audio_scope == "native":
            score += 35
        else:
            score += 25

    negative_context = f"{title}\n{cleaned_description}".lower()
    negative = bool(NEGATIVE_SIGNALS.search(negative_context))
    corporate = bool(CORPORATE_ROLE.search(title))

    if audio_scope == "native" and score > 0:
        score += 10

    if negative:
        score -= NEGATIVE_SIGNAL_PENALTY

    if corporate and not title_strong:
        score -= 70

    if score <= 0:
        return 0, False

    threshold = SCOPE_THRESHOLDS.get(audio_scope, 55)
    if not title_strong and not title_weak and audio_scope != "native":
        threshold += 15
    return score, score >= threshold


CURRENCY_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR"}

SALARY_RANGE_RE = re.compile(
    r"(?P<cur1>[$£€]|USD|EUR|GBP|CAD|AUD|CHF|SEK|NOK|DKK)?\s*"
    r"(?P<a>\d{1,3}(?:[,.]\d{3})+|\d+(?:\.\d+)?)\s*(?P<amult>[kK])?\s*"
    r"(?:[-–—~]|\bto\b|\band\b)\s*"
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


def _keyword_pattern(keywords: tuple[str, ...]) -> Optional[re.Pattern[str]]:
    if not keywords:
        return None
    escaped = sorted((re.escape(k) for k in keywords), key=len, reverse=True)
    joined = "|".join(escaped)
    return re.compile(rf"(?<!\w)(?:{joined})(?:s|es)?(?!\w)", re.IGNORECASE)


def _compile_category_patterns() -> dict[str, dict[str, Optional[re.Pattern[str]]]]:
    patterns: dict[str, dict[str, Optional[re.Pattern[str]]]] = {}
    for category_id, tiers in CATEGORY_KEYWORDS.items():
        patterns[category_id] = {
            "strong": _keyword_pattern(tiers.get("strong", ())),
            "weak": _keyword_pattern(tiers.get("weak", ())),
        }
    return patterns


CATEGORY_PATTERNS = _compile_category_patterns()

CATEGORY_DOMINANCE: dict[str, tuple[str, ...]] = {
    "audio_software": (
        "music_production_recording",
        "music_technology",
        "audio_systems",
        "sound_design",
    ),
    "audio_dsp_embedded": (
        "music_production_recording",
        "audio_systems",
    ),
    "audio_ee": (
        "audio_systems",
    ),
    "transducers": (
        "audio_systems",
    ),
    "microphones_recording": (
        "audio_systems",
    ),
    "audio_research": (
        "audio_systems",
    ),
    "audio_aiml": (
        "audio_research",
    ),
    "test_measurement_qa": (
        "audio_systems",
    ),
}

COMPANY_FALLBACK_HARDWARE = "hardware"
COMPANY_FALLBACK_SOFTWARE = "software"

COMPANY_CATEGORY_FALLBACK: dict[str, tuple[frozenset, Optional[str]]] = {
    "Professional Audio & Live Sound": (frozenset({COMPANY_FALLBACK_HARDWARE}), None),
    "Headphones & Personal Audio": (frozenset({COMPANY_FALLBACK_HARDWARE}), None),
    "Hi-Fi & Consumer Speakers": (frozenset({COMPANY_FALLBACK_HARDWARE}), None),
    "Transducer & Driver Manufacturers": (
        frozenset({COMPANY_FALLBACK_HARDWARE}),
        "transducers",
    ),
    "Electronic Musical Instruments": (
        frozenset({COMPANY_FALLBACK_HARDWARE, COMPANY_FALLBACK_SOFTWARE}),
        "music_technology",
    ),
    "DJ Equipment": (
        frozenset({COMPANY_FALLBACK_HARDWARE, COMPANY_FALLBACK_SOFTWARE}),
        "music_technology",
    ),
    "Car Audio": (frozenset({COMPANY_FALLBACK_HARDWARE}), "automotive_audio"),
    "Audio Interfaces & Converters": (frozenset({COMPANY_FALLBACK_HARDWARE}), None),
    "Hearing Aid & Hearing Tech": (
        frozenset({COMPANY_FALLBACK_HARDWARE}),
        "audiology_hearing",
    ),
    "Audio Plugins & Virtual Instruments": (
        frozenset({COMPANY_FALLBACK_HARDWARE, COMPANY_FALLBACK_SOFTWARE}),
        None,
    ),
    "DAW & Music Production Software": (
        frozenset({COMPANY_FALLBACK_HARDWARE, COMPANY_FALLBACK_SOFTWARE}),
        None,
    ),
    "Audio Middleware & SDK": (
        frozenset({COMPANY_FALLBACK_HARDWARE, COMPANY_FALLBACK_SOFTWARE}),
        None,
    ),
    "Smart Home & IoT Audio": (frozenset({COMPANY_FALLBACK_HARDWARE}), None),
}

FALLBACK_ROLE_CATEGORIES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            r"\b(test|testing|validation|verification|quality|reliability|qa|"
            r"metrology|calibration)\b",
            re.IGNORECASE,
        ),
        "test_measurement_qa",
        COMPANY_FALLBACK_HARDWARE,
    ),
    (
        re.compile(r"\b(firmware|embedded|dsp|signal processing)\b", re.IGNORECASE),
        "audio_dsp_embedded",
        COMPANY_FALLBACK_HARDWARE,
    ),
    (
        re.compile(
            r"\b(electrical|electronics?|analog|analogue|rf|hardware|pcb)\b",
            re.IGNORECASE,
        ),
        "audio_ee",
        COMPANY_FALLBACK_HARDWARE,
    ),
    (
        re.compile(
            r"\b(mechanical|industrial design|manufacturing|tooling|packaging)\b",
            re.IGNORECASE,
        ),
        "audio_product_mechanical",
        COMPANY_FALLBACK_HARDWARE,
    ),
    (
        re.compile(r"\b(software|developer|programmer|c\+\+)\b", re.IGNORECASE),
        "audio_software",
        COMPANY_FALLBACK_SOFTWARE,
    ),
]

FALLBACK_ROLE_HEAD = re.compile(
    r"\b(engineer|engineering|developer|scientist|technician|technologist|"
    r"architect|designer)\b",
    re.IGNORECASE,
)

FALLBACK_ROLE_EXCLUSIONS = re.compile(
    r"\b(civil|structural|architectural|building|facade|geotechnical|hvac|plumbing|"
    r"data|analytics|devops|site reliability|cloud|network|networking|infrastructure|"
    r"security|web|frontend|front[- ]end|backend|back[- ]end|full[- ]stack|salesforce|"
    r"sales|solutions|presales|support|field|release|erp|sap|"
    r"developer relations|developer advocate|evangelist|devrel|"
    r"machine learning|computer vision|llm|search|growth|marketing|platform|storage)\b",
    re.IGNORECASE,
)


def _company_fallback_categories(title: str, company_category: str | None) -> list[str]:
    if not company_category:
        return []
    gate = COMPANY_CATEGORY_FALLBACK.get(company_category)
    if gate is None:
        return []
    allowed, domain = gate
    if not FALLBACK_ROLE_HEAD.search(title):
        return []
    if FALLBACK_ROLE_EXCLUSIONS.search(title) or CORPORATE_ROLE.search(title):
        return []
    for pattern, category_id, kind in FALLBACK_ROLE_CATEGORIES:
        if kind in allowed and pattern.search(title):
            found = {category_id}
            if domain:
                found.add(domain)
            return sorted(found)
    return []


def _distinct_keyword_hits(
    text: str, pattern: Optional[re.Pattern[str]], require_anchor: bool
) -> set[str]:
    hits: set[str] = set()
    if pattern is None:
        return hits
    for m in pattern.finditer(text):
        keyword = m.group(0).lower()
        if keyword in hits:
            continue
        if require_anchor:
            window_start = max(0, m.start() - 200)
            window_end = m.end() + 200
            if not AUDIO_ANCHOR.search(text[window_start:window_end]):
                continue
        hits.add(keyword)
    return hits


def _score_category(
    category_id: str, title_lower: str, role_lower: str
) -> tuple[int, bool]:
    tiers = CATEGORY_PATTERNS[category_id]
    strong_pattern = tiers["strong"]
    weak_pattern = tiers["weak"]
    anchored = category_id in ANCHORED_CATEGORIES
    title_only = category_id == "sales_marketing_cs"

    score = 0
    title_hit = False

    title_anchored = anchored and bool(AUDIO_ANCHOR.search(title_lower))

    if strong_pattern is not None and strong_pattern.search(title_lower):
        score += 6
        title_hit = True
    if weak_pattern is not None and weak_pattern.search(title_lower):
        score += 6 if title_anchored else 3
        title_hit = True

    if not title_only:
        strong_hits = _distinct_keyword_hits(role_lower, strong_pattern, anchored)
        if strong_hits:
            score += min(3 + (len(strong_hits) - 1), 5)

        weak_hits = _distinct_keyword_hits(role_lower, weak_pattern, anchored)
        if weak_hits:
            score += min(len(weak_hits), 2)

    return score, title_hit


def classify_categories(
    title: str, description: str | None, company_category: str | None = None
) -> list[str]:
    title_lower = title.lower()
    role_lower = extract_role_text(description).lower()[:6000]

    scored: dict[str, int] = {}
    title_hits: dict[str, bool] = {}

    for category_id in CATEGORY_KEYWORDS:
        score, title_hit = _score_category(category_id, title_lower, role_lower)
        if score >= 5:
            scored[category_id] = score
            title_hits[category_id] = title_hit

    _apply_software_override(title_lower, scored, title_hits)
    _apply_test_override(title_lower, scored, title_hits)

    for dominant, subordinates in CATEGORY_DOMINANCE.items():
        if title_hits.get(dominant):
            for sub in subordinates:
                if sub in scored and not title_hits.get(sub):
                    scored.pop(sub, None)
                    title_hits.pop(sub, None)

    ranked = sorted(
        scored.items(),
        key=lambda item: (-item[1], 0 if title_hits.get(item[0]) else 1, item[0]),
    )
    top = ranked[:3]
    result = sorted(category_id for category_id, _ in top)
    if result:
        return result
    return _company_fallback_categories(title, company_category)


SOFTWARE_TITLE_RE = re.compile(
    r"\b(software engineer|software development|software developer|"
    r"software programming|firmware engineer)\b",
    re.IGNORECASE,
)


def _apply_software_override(
    title_lower: str, scored: dict[str, int], title_hits: dict[str, bool]
) -> None:
    if not SOFTWARE_TITLE_RE.search(title_lower):
        return
    replaced = False
    for cat in ("music_production_recording", "music_technology"):
        if cat in scored:
            scored.pop(cat)
            title_hits.pop(cat, None)
            replaced = True
    inverted = not scored and bool(AUDIO_ANCHOR.search(title_lower))
    if replaced or inverted:
        scored["audio_software"] = max(scored.get("audio_software", 0), 6)
        title_hits["audio_software"] = True


TEST_ROLE_SUBJECT = (
    r"test|testing|qa|quality|validation|verification|metrology|calibration|reliability"
)

TEST_ROLE_HOLDER = (
    r"engineer|engineering|technician|manager|specialist|analyst|lead|developer|"
    r"scientist|architect|director"
)

TEST_ROLE_TITLE_RE = re.compile(
    rf"\b(?:{TEST_ROLE_SUBJECT})\b[\w\s/&,()+-]{{0,40}}?\b(?:{TEST_ROLE_HOLDER})\b"
    rf"|\b(?:{TEST_ROLE_HOLDER})\b[\w\s/&,()+-]{{0,40}}?\b(?:{TEST_ROLE_SUBJECT})\b",
    re.IGNORECASE,
)


def _apply_test_override(
    title_lower: str, scored: dict[str, int], title_hits: dict[str, bool]
) -> None:
    if not scored:
        return
    if not TEST_ROLE_TITLE_RE.search(title_lower):
        return
    scored["test_measurement_qa"] = max(scored.get("test_measurement_qa", 0), 6)
    title_hits["test_measurement_qa"] = True


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

    def normalize(
        self,
        raw: RawJob,
        audio_scope: str = "native",
        company_category: str | None = None,
    ) -> NormalizedJob:
        salary_text = " ".join(
            part for part in (raw.title, raw.description) if part
        )
        salary_min, salary_max, salary_currency = parse_salary(salary_text)

        categories = classify_categories(raw.title, raw.description, company_category)
        if self.valid_ids is not None:
            categories = [c for c in categories if c in self.valid_ids]

        relevance_score, is_audio_related = score_relevance(
            raw.title, raw.description, categories, audio_scope
        )

        job_type = normalize_job_type(raw.job_type)
        if job_type is None:
            job_type = normalize_job_type(raw.title)
        if job_type is None and raw.description:
            job_type = normalize_job_type(raw.description[:500])

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
