from __future__ import annotations

import html
import re
from typing import Optional

from scraper.countries import detect_country

MAX_TEXT_CHARS = 30000
MAX_VALUE_WORDS = 7

BLOCK_TAG_RE = re.compile(r"<(?:br|/p|/li|/div|/h[1-6]|/tr|/td)\b[^>]{0,200}>", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]{0,2000}>")
PAREN_RE = re.compile(r"\([^)]{0,40}\)")
TOKEN_RE = re.compile(r"(\s+)")
DIGIT_RE = re.compile(r"\b\d{1,10}\b")
POSSESSIVE_RE = re.compile(r"[’'][sS]$")

LABEL_RE = re.compile(
    r"(?im)^[ \t*•\-]{0,4}(?:job |work |primary |office |position )?"
    r"(?:location|locations|standort|arbeitsort|einsatzort|lieu de travail|"
    r"ubicaci[oó]n|sede di lavoro|sede|place of work|plaats)\b"
    r"[ \t]{0,3}[:\-–]?[ \t]{0,3}(?P<value>[^\n]{0,120})"
    r"(?:\n[ \t]{0,6}(?P<next>[^\n]{1,120}))?"
)
PROSE_RE = re.compile(
    r"(?i)\b(?:based (?:in|out of)|located (?:in|at)|on-?site (?:in|at)|"
    r"position is in|role is in|work from our|join (?:us|our team) in)[ \t]{1,3}"
    r"(?:our |the |beautiful |sunny |downtown )?(?P<value>[A-Z][^.;|\n()]{1,70})"
)
OFFICE_LIST_RE = re.compile(
    r"(?i)\boffices? (?:in|across)\b|\bfollowing (?:cities|studios|locations|offices)\b"
    r"|\b(?:one|any) of our\b"
)
TRAILING_CLAUSE_RE = re.compile(
    r"(?i)\s(?:with|and|or|where|which|to|for|that|who|as|is|are|office|offices|"
    r"headquarters|campus|area|region|location)\b.{0,200}$"
)
CONNECTORS = frozenset(
    {"de", "di", "del", "la", "le", "am", "an", "der", "upon", "on", "sur", "im", "en", "y", "of"}
)


def location_from_text(description: str | None) -> Optional[str]:
    if not description:
        return None
    text = _plain_text(description[:MAX_TEXT_CHARS])
    labelled = _labelled(text)
    prose = _prose(text)
    countries = {detect_country(value) for value in labelled + prose}
    if len(countries) != 1:
        return None
    return (labelled or prose)[0]


def _plain_text(description: str) -> str:
    if "&lt;" in description:
        description = html.unescape(description)
    if "<" in description:
        description = TAG_RE.sub("", BLOCK_TAG_RE.sub("\n", description))
    return html.unescape(description).replace("\xa0", " ")


def _labelled(text: str) -> list[str]:
    found: list[str] = []
    for match in LABEL_RE.finditer(text):
        for raw in (match.group("value"), match.group("next")):
            value = _place(raw or "")
            if value:
                found.append(value)
                break
    return found


def _prose(text: str) -> list[str]:
    found: list[str] = []
    for match in PROSE_RE.finditer(text):
        if OFFICE_LIST_RE.search(text[max(0, match.start() - 40):match.end()]):
            continue
        value = _place(TRAILING_CLAUSE_RE.sub("", match.group("value")))
        if value:
            found.append(value)
    return found


def _place(raw: str) -> Optional[str]:
    value = PAREN_RE.sub(" ", raw).strip(" :\t-–,")
    kept: list[str] = []
    for token in TOKEN_RE.split(value):
        if not token.strip():
            kept.append(token)
            continue
        core = token.strip(",")
        if not core:
            kept.append(token)
            continue
        if not (core[0].isupper() or core[0].isdigit() or core.lower() in CONNECTORS):
            break
        possessive = POSSESSIVE_RE.search(core)
        if possessive:
            kept.append(core[:possessive.start()])
            break
        kept.append(token.rstrip("!?"))
        if token.endswith((".", ";", "!", "?")):
            break
    words = "".join(kept).strip(" ,.;-–").split()
    while words and words[-1].lower() in CONNECTORS:
        words.pop()
    if not words or len(words) > MAX_VALUE_WORDS:
        return None
    return _shortest(" ".join(words))


def _shortest(value: str) -> Optional[str]:
    country = detect_country(value)
    if country is None:
        return None
    value = _without_address(value, country)
    words = value.split()
    needs_comma = "," in value
    for end in range(1, len(words) + 1):
        prefix = " ".join(words[:end]).strip(" ,")
        if needs_comma and "," not in prefix:
            continue
        if detect_country(prefix) == country:
            return prefix
    return value


def _without_address(value: str, country: str) -> str:
    segments = [part.strip() for part in value.split(",")]
    while len(segments) > 1 and DIGIT_RE.search(segments[0]):
        rest = segments[1:]
        rest[0] = DIGIT_RE.sub("", rest[0]).strip()
        if not rest[0] or detect_country(", ".join(rest)) != country:
            break
        segments = rest
    return ", ".join(segments)
