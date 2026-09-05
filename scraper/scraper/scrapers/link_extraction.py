from __future__ import annotations

import json
import re
from datetime import date
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from scraper.scrapers.base import RawJob

JOB_HINT = re.compile(
    r"(job|jobs|career|careers|position|opening|vacanc|opportunit|hiring|"
    r"apply/|/apply|employment|roles)",
    re.IGNORECASE,
)

NON_JOB_URL = re.compile(
    r"(mailto:|tel:|javascript:|^#$|^$)",
    re.IGNORECASE,
)

SOCIAL_DOMAIN = re.compile(
    r"(linkedin\.com|facebook\.com/(share|sharer)|twitter\.com/(intent|share)|"
    r"x\.com/intent|instagram\.com|youtube\.com|wa\.me|whatsapp\.com|t\.me/|"
    r"glassdoor|indeed\.com|mailchi|us\d+\.list-manage|google\.com/maps)",
    re.IGNORECASE,
)

NON_JOB_TEXT = {
    "learn more",
    "read more",
    "about us",
    "contact",
    "contact us",
    "press",
    "blog",
    "news",
    "home",
    "back",
    "submit",
    "search",
    "sign in",
    "log in",
    "login",
    "sign up",
    "apply",
    "apply now",
    "view job",
    "see details",
    "view all jobs",
    "see all jobs",
    "all jobs",
    "view all openings",
    "join us",
    "join our team",
    "benefits",
    "culture",
    "diversity",
    "privacy policy",
    "terms of service",
    "cookie policy",
    "faq",
    "apply for financing",
    "follow this link",
    "keep reading",
    "0 jobs",
    "search jobs",
    "jobs & career",
    "sign up for job alerts.",
    "sign up for job alerts",
    "powered by jobvite",
    "job alerts",

    "lire la suite",
    "en savoir plus",
    "voir plus",
    "voir l'offre",
    "voir les offres",
    "toutes nos offres",
    "nos offres",
    "nos offres d'emploi",
    "postuler",
    "candidature spontanée",
    "candidature spontanee",
    "retour",
    "accueil",
    "nous contacter",
    "mehr erfahren",
    "weiterlesen",
    "mehr",
    "jetzt bewerben",
    "bewerben",
    "initiativbewerbung",
    "alle jobs",
    "alle stellen",
    "alle stellenangebote",
    "stellenangebote",
    "zur stellenanzeige",
    "offene stellen",
    "startseite",
    "zurück",
    "zurueck",
    "kontakt",
    "impressum",
    "datenschutz",
    "leer más",
    "leer mas",
    "más información",
    "mas informacion",
    "ver más",
    "ver mas",
    "solicitar",
    "todas las ofertas",
    "ofertas de empleo",
    "inicio",
    "contacto",
    "volver",
    "leggi di più",
    "leggi di piu",
    "scopri di più",
    "scopri di piu",
    "candidati",
    "tutte le offerte",
    "posizioni aperte",
    "contatti",
    "indietro",
    "lees meer",
    "meer informatie",
    "solliciteer",
    "alle vacatures",
    "terug",
    "läs mer",
    "las mer",
    "ansök",
    "ansok",
    "alla jobb",
    "lediga jobb",
    "lediga tjänster",
    "tillbaka",
    "læs mere",
    "laes mere",
    "ansøg",
    "ansog",
    "alle job",
    "ledige stillinger",
    "tilbage",
    "les mer",
    "søk",
    "sok",
    "alle stillinger",
    "tilbake",
    "lue lisää",
    "lue lisaa",
    "avoimet työpaikat",
    "kaikki työpaikat",
    "takaisin",
    "saiba mais",
    "ler mais",
    "candidatar-se",
    "todas as vagas",
    "voltar",
}

FURNITURE_PHRASES = (
    "apply for financing",
    "follow this link",
    "keep reading",
    "reach out to",
    "find out how",
    "we are committed to",
    "a brief description",
    "view all job",
    "see all job",
    "browse all job",
    "search all job",
    "view open positions",
    "see open positions",
    "view open roles",
    "cookie settings",
)

LISTING_POINTER_PHRASES = (
    "view all job",
    "see all job",
    "browse all job",
    "search all job",
    "view open positions",
    "see open positions",
    "view open roles",
    "view all openings",
    "see all openings",
)


def is_listing_pointer(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in LISTING_POINTER_PHRASES)

COOKIE_NOTICE_RE = re.compile(r"\bcookies?\b", re.IGNORECASE)

PAGINATION_CHEVRON_RE = r"(?:«|‹|»|›|<<|>>|<|>)"
PAGINATION_WORD_RE = r"(?:next|prev|previous|first|last)"

PAGINATION_CONTROL_RE = re.compile(
    rf"^(?:{PAGINATION_CHEVRON_RE}\s*)?"
    rf"(?:{PAGINATION_WORD_RE}|page\s+\d{{1,4}}|\d{{1,4}})"
    rf"(?:\s*{PAGINATION_CHEVRON_RE})?$"
    rf"|^{PAGINATION_CHEVRON_RE}$",
    re.IGNORECASE,
)

LANGUAGE_ENDONYM_ALTERNATION_RE = (
    r"(?:deutsch|français|francais|español|espanol|italiano|português|portugues|"
    r"nederlands|svenska|norsk|dansk|suomi|polski|magyar|română|türkçe|"
    r"čeština(?:,\s*český\s+jazyk)?|english|日本語|한국어|简体中文|繁體中文|中文|"
    r"русский|العربية|ไทย|tiếng\s+việt|bahasa\s+indonesia)"
)

LANGUAGE_SWITCHER_RE = re.compile(
    rf"^{LANGUAGE_ENDONYM_ALTERNATION_RE}(?:\s*[-–—]\s*[A-Za-zÀ-ÿ]{{2,5}})?$",
    re.IGNORECASE,
)

JOBS_COUNT_RE = re.compile(r"\b\d{1,3}\s+jobs?\b", re.IGNORECASE)
SENTENCE_BREAK_WORD_RE = re.compile(r"([A-Za-z]+)\.\s+(\S)")
EXCLAIM_QUESTION_BREAK_RE = re.compile(r"[!?]\s+\S")

ABBREVIATIONS = {
    "sr",
    "jr",
    "dr",
    "mr",
    "mrs",
    "ms",
    "st",
    "inc",
    "corp",
    "ltd",
    "co",
    "vs",
    "etc",
    "no",
    "dept",
    "assoc",
    "univ",
    "prof",
    "capt",
    "gen",
    "col",
    "sgt",
    "lt",
    "gov",
    "rep",
    "sen",
}


TEMPLATE_PLACEHOLDER_RE = re.compile(r"%[A-Z0-9_]+%|\{\{[^}]*\}\}|\$\{[^}]*\}")

SENTENCE_BREAK_MIN_WORDS = 7


def _has_sentence_break(title: str) -> bool:
    if EXCLAIM_QUESTION_BREAK_RE.search(title):
        return True
    if len(title.split()) < SENTENCE_BREAK_MIN_WORDS:
        return False
    for match in SENTENCE_BREAK_WORD_RE.finditer(title):
        word = match.group(1)
        if len(word) <= 2 or word.lower() in ABBREVIATIONS:
            continue
        return True
    return False

GENERIC_LISTING_SEGMENTS = {
    "jobs",
    "careers",
    "openings",
    "all",
    "search",
    "apply",
    "teams",
    "locations",
    "benefits",
    "culture",
    "students",
    "internships",
    "departments",
}

SEP = r"[\s,;:|/\-–—]"

POSTED_AGO_RE = re.compile(
    SEP + r"+Posted\s+\d+\+?\s*(?:day|days|hour|hours|week|weeks|month|months)\s+ago\s*$",
    re.IGNORECASE,
)

CTA_SUFFIX_RE = re.compile(
    SEP + r"+(?:Apply\s*Now|Apply|Read\s*More|Learn\s*More|View\s*Job|See\s*Details)\s*$",
    re.IGNORECASE,
)

TRAILING_DECORATION_CHARS = ">»›→▸▶←‹«"

TRAILING_DECORATION_RE = re.compile(
    r"\s*(?:-->|->|&gt;|[" + TRAILING_DECORATION_CHARS + r"]){1,3}\s*$"
)

EMPLOYMENT_SUFFIX_RE = re.compile(
    r"(?<=\S)" + SEP + r"+(?P<emp>Full[- ]?Time|Part[- ]?Time|Permanent|"
    r"Temporary|Contract)\s*$",
    re.IGNORECASE,
)

INTERNSHIP_DETECT_RE = re.compile(
    r"(?<=\S)" + SEP + r"+(?P<emp>Internship|Intern)\s*$",
    re.IGNORECASE,
)

REMOTE_DASH_PLACE_RE = re.compile(
    r"(?<=\S)\s+(?:Remote|Hybrid|On-?site)\s*[-–—]\s*[A-Za-z][A-Za-z .]*$",
    re.IGNORECASE,
)

REMOTE_BARE_RE = re.compile(
    r"(?<=\S)\s+(?:Remote|Hybrid|On-?site)\s*$",
    re.IGNORECASE,
)

TRAILING_STOPWORD_RE = re.compile(
    r"(?<=\S)\s+(?:or|and|in|at|on|for|to|of)\s*$",
    re.IGNORECASE,
)

TRAILING_STATE_CODE_RE = re.compile(r"(?<=\S),\s*[A-Z]{2}\s*$")

TITLE_CASE_WORD_RE = re.compile(r"^[A-Z][a-zA-Z]*$")

KNOWN_TWO_WORD_CITIES = {
    "mountain view",
    "new york",
    "san francisco",
    "san diego",
    "san jose",
    "san antonio",
    "san mateo",
    "santa clara",
    "santa monica",
    "palo alto",
    "menlo park",
    "redwood city",
    "salt lake",
    "las vegas",
    "kansas city",
    "oklahoma city",
    "sao paulo",
    "hong kong",
    "cape town",
    "tel aviv",
    "new delhi",
    "fort worth",
    "long beach",
    "los angeles",
}

ROLE_NOUN_ENDINGS = {
    "manager",
    "executive",
    "director",
    "engineer",
    "analyst",
    "specialist",
    "representative",
    "lead",
    "coordinator",
    "associate",
    "consultant",
    "officer",
    "administrator",
    "recruiter",
    "designer",
    "developer",
    "architect",
    "scientist",
    "strategist",
    "partner",
    "president",
    "controller",
    "accountant",
    "technician",
    "supervisor",
    "champion",
    "generalist",
    "producer",
    "planner",
    "buyer",
    "advisor",
    "sales",
    "marketing",
    "finance",
    "engineering",
    "product",
    "design",
    "legal",
    "people",
    "operations",
    "support",
    "success",
    "data",
    "research",
    "strategy",
    "growth",
    "revenue",
    "partnerships",
    "communications",
}

CITY_LIST_RE = re.compile(
    r"(?<=\S)\s+(?:[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)*\s*\([A-Za-z]+\)\s*,?\s*){1,}"
    r"or\s+fully\s+remote\s+from\s+eligible\s+countries\s*$"
)

EDGE_PUNCT = " \t-–—|,;:&"

MIN_TITLE_LEN = 3
MAX_TITLE_LEN = 90

QUESTION_MARK = "?"

ACRONYMS = {
    "AI",
    "DSP",
    "EE",
    "AV",
    "QA",
    "UX",
    "IT",
    "VP",
    "NPI",
    "HR",
    "FOH",
    "NVH",
    "MIDI",
    "VST",
}


def _titlecase_token(token: str) -> str:
    start = 0
    end = len(token)
    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1
    if start == end:
        return token

    prefix, core, suffix = token[:start], token[start:end], token[end:]
    if core.upper() in ACRONYMS:
        return prefix + core.upper() + suffix
    if "-" in core:
        parts = core.split("-")
        return prefix + "-".join(p.capitalize() if p else p for p in parts) + suffix
    return prefix + core.capitalize() + suffix


def _normalize_shouty_case(title: str) -> str:
    words = title.split(" ")
    if len(words) <= 4:
        return title
    has_upper = any(c.isupper() for c in title)
    has_lower = any(c.islower() for c in title)
    if has_upper == has_lower:
        return title
    return " ".join(_titlecase_token(w) for w in words)


def _clean_text(text: object) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def _clean_job_title_and_type(text: str) -> tuple[str, Optional[str]]:
    title = _clean_text(TEMPLATE_PLACEHOLDER_RE.sub(" ", str(text or "")))
    job_type: Optional[str] = None

    for _ in range(8):
        new_title = POSTED_AGO_RE.sub("", title)
        if new_title == title:
            new_title = CTA_SUFFIX_RE.sub("", title)
        if new_title == title:
            match = EMPLOYMENT_SUFFIX_RE.search(title)
            if match:
                job_type = match.group("emp")
                new_title = EMPLOYMENT_SUFFIX_RE.sub("", title)
            elif job_type is None:
                intern_match = INTERNSHIP_DETECT_RE.search(title)
                if intern_match:
                    job_type = intern_match.group("emp")
        if new_title == title:
            new_title = CITY_LIST_RE.sub("", title)
        if new_title == title:
            new_title = REMOTE_DASH_PLACE_RE.sub("", title)
        if new_title == title:
            new_title = _strip_city_state(title)
        if new_title == title:
            new_title = REMOTE_BARE_RE.sub("", title)
        if new_title == title:
            new_title = TRAILING_STOPWORD_RE.sub("", title)
        if new_title == title:
            new_title = TRAILING_DECORATION_RE.sub("", title)

        new_title = _clean_text(new_title).strip(EDGE_PUNCT).strip()
        if new_title == title:
            break
        title = new_title

    title = _normalize_shouty_case(title)
    return title, job_type


def _strip_city_state(title: str) -> str:
    match = TRAILING_STATE_CODE_RE.search(title)
    if not match:
        return title
    prefix = title[: match.start()]
    words = prefix.split(" ")
    last = words[-1]
    if not last or not TITLE_CASE_WORD_RE.match(last) or last.lower() in ROLE_NOUN_ENDINGS:
        return title

    if len(words) >= 2:
        second_last = words[-2]
        if (
            TITLE_CASE_WORD_RE.match(second_last)
            and second_last.lower() not in ROLE_NOUN_ENDINGS
            and f"{second_last} {last}".lower() in KNOWN_TWO_WORD_CITIES
        ):
            return " ".join(words[:-2]).rstrip()

    return " ".join(words[:-1]).rstrip()


def clean_job_title(text: str) -> str:
    title, _ = _clean_job_title_and_type(text)
    return title


def is_furniture_title(title: str) -> bool:
    lowered = title.lower()
    words = title.split()
    if len(words) > 12:
        return True
    if _has_sentence_break(title):
        return True
    if title.endswith("...") or title.endswith("…"):
        return True
    if JOBS_COUNT_RE.search(title):
        return True
    if any(phrase in lowered for phrase in FURNITURE_PHRASES):
        return True
    if COOKIE_NOTICE_RE.search(lowered):
        return True
    if PAGINATION_CONTROL_RE.match(title):
        return True
    if LANGUAGE_SWITCHER_RE.match(title.strip()):
        return True
    return False


JOB_ID_QUERY_RE = re.compile(
    r"(?:^|&)(?:[\w\-]*(?:job|req|posting|vacancy|position|gh_jid|jid))[\w\-]*="
    r"[^&]*\d",
    re.IGNORECASE,
)


HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

MAX_ANCESTOR_WALK = 3


def _heading_text(node: Tag) -> Optional[str]:
    heading = node.find(HEADING_TAGS)
    if heading is None:
        return None
    text = _clean_text(heading.get_text(" ", strip=True))
    return text or None


def _has_single_job_anchor(node: Tag, anchor: Tag) -> bool:
    candidates = [
        candidate
        for candidate in node.find_all("a", href=True)
        if _clean_text(candidate.get("href"))
        and not _clean_text(candidate.get("href")).startswith("#")
    ]
    return len(candidates) == 1 and candidates[0] is anchor


def _structural_title(anchor: Tag) -> Optional[str]:
    inside = _heading_text(anchor)
    if inside:
        return inside

    node: Tag = anchor
    for _ in range(MAX_ANCESTOR_WALK):
        parent = node.parent
        if not isinstance(parent, Tag) or parent.name in ("body", "html"):
            break
        node = parent
        heading = _heading_text(node)
        if heading and _has_single_job_anchor(node, anchor):
            return heading
    return None


LOCATION_ATTR_KEYS = ("class", "id", "aria-label", "title", "data-label", "itemprop")

LOCATION_ATTR_RE = re.compile(r"(?:^|[-_\s])locations?(?:[-_\s]|$)", re.IGNORECASE)

LOCATION_LABEL_RE = re.compile(r"^\s{0,4}locations?\s{0,4}[:\-–—]?\s{0,4}", re.IGNORECASE)

LOCATION_ICON_TEXT = frozenset(
    {"place", "location_on", "location_city", "pin_drop", "room"}
)

LOCATION_SKIP_TAGS = frozenset(
    {"select", "option", "input", "textarea", "button", "form", "label",
     "script", "style"}
)

LOCATION_REJECT_RE = re.compile(
    r"\b(?:jobs?|careers?|openings?|positions?|vacanc\w{0,4}|apply|browse|"
    r"filter|search|results?|sort|showing|select|choose|all)\b",
    re.IGNORECASE,
)

MIN_LOCATION_LEN = 2
MAX_LOCATION_LEN = 120
MAX_LOCATION_WORDS = 12
LOCATION_SCAN_LIMIT = 400
LOCATION_ENTRY_LIMIT = 12
LOCATION_FORM_ANCESTOR_WALK = 6


def _location_attr_hit(node: Tag) -> bool:
    for key in LOCATION_ATTR_KEYS:
        value = node.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            value = " ".join(value)
        if LOCATION_ATTR_RE.search(str(value)):
            return True
    return False


def _inside_form_control(node: Tag) -> bool:
    current: object = node
    for _ in range(LOCATION_FORM_ANCESTOR_WALK):
        if not isinstance(current, Tag):
            return False
        if current.name in LOCATION_SKIP_TAGS:
            return True
        current = current.parent
    return False


def clean_location_value(text: str) -> Optional[str]:
    value = _clean_text(LOCATION_LABEL_RE.sub("", text)).strip(EDGE_PUNCT).strip()
    value = _clean_text(value)
    if not value or not (MIN_LOCATION_LEN <= len(value) <= MAX_LOCATION_LEN):
        return None
    if len(value.split(" ")) > MAX_LOCATION_WORDS:
        return None
    if LOCATION_REJECT_RE.search(value):
        return None
    return value


def _location_node_text(node: Tag) -> str:
    items = node.find_all("li", limit=LOCATION_ENTRY_LIMIT)
    if len(items) > 1:
        parts = [item.get_text(" ", strip=True) for item in items]
        return "; ".join(part for part in parts if part)
    return node.get_text(" ", strip=True)


def card_location(card: Tag) -> Optional[str]:
    for node in card.find_all(True, limit=LOCATION_SCAN_LIMIT):
        if node.name in LOCATION_SKIP_TAGS or _inside_form_control(node):
            continue
        if _location_attr_hit(node):
            value = clean_location_value(_location_node_text(node))
            if value:
                return value
        elif _clean_text(node.get_text(" ", strip=True)).lower() in LOCATION_ICON_TEXT:
            sibling = node.find_next_sibling()
            if isinstance(sibling, Tag):
                value = clean_location_value(sibling.get_text(" ", strip=True))
                if value:
                    return value
    return None


def anchor_location(anchor: Tag) -> Optional[str]:
    node: Tag = anchor
    for _ in range(MAX_ANCESTOR_WALK):
        parent = node.parent
        if not isinstance(parent, Tag) or parent.name in ("body", "html"):
            break
        node = parent
        if not _has_single_job_anchor(node, anchor):
            break
        location = card_location(node)
        if location:
            return location
    return None


def _looks_like_job_detail_path(path: str, query: str = "") -> bool:
    if query and JOB_ID_QUERY_RE.search(query):
        return True
    segments = [s for s in path.split("/") if s]
    if not segments:
        return False
    last = segments[-1]
    if last in GENERIC_LISTING_SEGMENTS:
        return False
    return bool(re.search(r"\d", last) or "-" in last or len(last) > 12)


def resolve_document_base(soup: BeautifulSoup, base_url: str) -> str:
    tag = soup.find("base", href=True)
    if tag is None:
        return base_url
    href = _clean_text(tag.get("href"))
    if not href:
        return base_url
    resolved = urljoin(base_url, href)
    if urlparse(resolved).scheme not in ("http", "https"):
        return base_url
    return resolved


def extract_job_links(html: str, base_url: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "html.parser")
    link_base = resolve_document_base(soup, base_url)
    best_by_url: dict[str, tuple[str, str, Optional[str], Optional[str]]] = {}
    base_parsed = urlparse(base_url)
    base_path = base_parsed.path.rstrip("/").lower()
    base_netloc = base_parsed.netloc.lower()
    base_has_job_hint = bool(JOB_HINT.search(base_path))
    named_anchors = {
        _clean_text(tag.get("name"))
        for tag in soup.find_all("a", attrs={"name": True})
        if _clean_text(tag.get("name"))
    }

    for anchor in soup.find_all("a", href=True):
        href = _clean_text(anchor.get("href"))
        if not href or NON_JOB_URL.search(href):
            continue
        absolute = urljoin(link_base, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if SOCIAL_DOMAIN.search(absolute):
            continue

        path = parsed.path.rstrip("/").lower()
        text = _clean_text(anchor.get_text(" ", strip=True))
        title_attr = _clean_text(anchor.get("title"))
        raw_candidate = text or title_attr
        if raw_candidate:
            candidate_title, job_type = _clean_job_title_and_type(raw_candidate)
        else:
            candidate_title, job_type = "", None

        if raw_candidate and is_listing_pointer(raw_candidate):
            continue

        came_from_structure = False
        flat_unusable = (
            not candidate_title
            or candidate_title.lower() in NON_JOB_TEXT
            or len(candidate_title) > MAX_TITLE_LEN
            or is_furniture_title(candidate_title)
        )
        if flat_unusable:
            structural_raw = _structural_title(anchor)
            if structural_raw:
                candidate_title, job_type = _clean_job_title_and_type(structural_raw)
                came_from_structure = True

        if len(candidate_title) < MIN_TITLE_LEN or len(candidate_title) > MAX_TITLE_LEN:
            continue
        if candidate_title.lower() in NON_JOB_TEXT:
            continue
        if is_furniture_title(candidate_title):
            continue

        same_host = bool(base_netloc) and parsed.netloc.lower() == base_netloc
        structural_job_hint = came_from_structure and base_has_job_hint and same_host
        same_page_anchor = bool(
            parsed.fragment
            and same_host
            and path == base_path
            and parsed.fragment in named_anchors
        )

        looks_like_job = bool(
            (JOB_HINT.search(path) and _looks_like_job_detail_path(path, parsed.query))
            or (text and JOB_HINT.search(text))
            or (title_attr and JOB_HINT.search(title_attr))
            or structural_job_hint
            or (same_page_anchor and base_has_job_hint)
        )
        if not looks_like_job:
            continue
        if (path == base_path or path == "") and not same_page_anchor:
            continue

        existing = best_by_url.get(absolute)
        if existing is None or len(candidate_title) > len(existing[0]):
            best_by_url[absolute] = (
                candidate_title,
                path,
                job_type,
                anchor_location(anchor),
            )

    return [
        RawJob(title=title, url=absolute, job_type=job_type, location=location)
        for absolute, (title, _, job_type, location) in sorted(best_by_url.items())
    ]


ACCORDION_NAV_ANCESTOR_TAGS = frozenset({"nav", "header", "footer", "aside"})

ACCORDION_MAX_LINK_TEXT_RATIO = 0.30


def extract_accordion_jobs(html: str, base_url: str) -> list[RawJob]:
    base_parsed = urlparse(base_url)
    base_has_job_hint = bool(JOB_HINT.search(base_parsed.path.lower()))
    if not base_has_job_hint:
        return []

    soup = BeautifulSoup(html, "html.parser")
    base_without_fragment = base_url.split("#", 1)[0]

    jobs: list[RawJob] = []
    seen_urls: set[str] = set()

    for details in soup.find_all("details"):
        summary = details.find("summary", recursive=False)
        if summary is None:
            continue

        if any(
            isinstance(parent, Tag) and parent.name in ACCORDION_NAV_ANCESTOR_TAGS
            for parent in details.parents
        ):
            continue

        id_value = _clean_text(details.get("id"))
        ident = id_value.lstrip("#")
        if not ident:
            continue

        raw_title = _clean_text(summary.get_text(" ", strip=True))
        title, job_type = _clean_job_title_and_type(raw_title)

        if len(title) < MIN_TITLE_LEN or len(title) > MAX_TITLE_LEN:
            continue
        if title.lower() in NON_JOB_TEXT:
            continue
        if is_furniture_title(title):
            continue
        if title.rstrip().endswith(QUESTION_MARK):
            continue

        body_text = details.get_text(" ", strip=True)
        link_chars = sum(
            len(link.get_text(" ", strip=True)) for link in details.find_all("a")
        )
        if link_chars / max(len(body_text), 1) >= ACCORDION_MAX_LINK_TEXT_RATIO:
            continue

        url = f"{base_without_fragment}#{ident}"
        if url in seen_urls:
            continue
        seen_urls.add(url)

        details_copy = BeautifulSoup(str(details), "html.parser")
        summary_copy = details_copy.find("summary")
        if summary_copy is not None:
            summary_copy.decompose()
        description = details_copy.get_text(" ", strip=True)

        jobs.append(
            RawJob(
                title=title,
                url=url,
                description=description or None,
                job_type=job_type,
            )
        )

    return jobs


def extract_jsonld_jobs(html: str, base_url: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[RawJob] = []

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.text
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if _is_job_posting(item):
                job = _parse_jsonld_job(item, base_url)
                if job:
                    jobs.append(job)
    return jobs


def extract_jobs(html: str, base_url: str) -> list[RawJob]:
    anchor_jobs = extract_job_links(html, base_url)
    jsonld_jobs = extract_jsonld_jobs(html, base_url)

    by_url: dict[str, RawJob] = {}
    for job in anchor_jobs:
        by_url[job.url] = job
    for job in jsonld_jobs:
        existing = by_url.get(job.url)
        if existing is not None and not job.location:
            job.location = existing.location
        by_url[job.url] = job

    return sorted(by_url.values(), key=lambda j: j.url)


def _is_job_posting(item: dict) -> bool:
    item_type = item.get("@type", "")
    if isinstance(item_type, str):
        return item_type.lower() == "jobposting"
    if isinstance(item_type, list):
        return any(
            isinstance(t, str) and t.lower() == "jobposting" for t in item_type
        )
    return False


def _parse_jsonld_job(item: dict, base_url: str) -> RawJob | None:
    title = clean_job_title((item.get("title") or "").strip())
    if not title:
        return None

    url = item.get("url") or base_url
    if url != base_url:
        url = urljoin(base_url, url)

    description = item.get("description")
    location = _parse_jsonld_location(
        item.get("jobLocation") or item.get("location")
    )
    posted_date = _parse_jsonld_date(item.get("datePosted"))
    external_id = item.get("identifier") or item.get("uid")
    if external_id is not None:
        external_id = str(external_id)

    job_type = None
    emp_type = item.get("employmentType")
    if isinstance(emp_type, str):
        job_type = _normalize_employment_type(emp_type)
    elif isinstance(emp_type, list) and emp_type:
        job_type = _normalize_employment_type(emp_type[0])

    return RawJob(
        title=title,
        url=url,
        external_id=external_id,
        location=location,
        description=description,
        job_type=job_type,
        posted_date=posted_date,
    )


MAX_JSONLD_LOCATIONS = 10


def _parse_jsonld_location(loc: object) -> str | None:
    if isinstance(loc, list):
        seen: list[str] = []
        for entry in loc[:MAX_JSONLD_LOCATIONS]:
            parsed = _parse_jsonld_location(entry)
            if parsed and parsed not in seen:
                seen.append(parsed)
        return "; ".join(seen) or None
    if isinstance(loc, str):
        return loc.strip() or None
    if not isinstance(loc, dict):
        return None
    if "name" in loc:
        return str(loc["name"])
    address = loc.get("address")
    if isinstance(address, dict):
        locality = address.get("addressLocality")
        region = address.get("addressRegion")
        country = address.get("addressCountry")
        parts = [
            str(part)
            for part in (locality, region, country)
            if part and str(part).strip().upper() != "UNAVAILABLE"
        ]
        if parts:
            return ", ".join(parts)
    if "addressLocality" in loc:
        return str(loc["addressLocality"])
    return None


def _parse_jsonld_date(value: object) -> date | None:
    if not value or not isinstance(value, str):
        return None
    from scraper.scrapers.fetch import parse_date

    return parse_date(value)


def _normalize_employment_type(value: str) -> str | None:
    lower = value.lower().strip()
    mapping = {
        "full_time": "full-time",
        "full-time": "full-time",
        "part_time": "part-time",
        "part-time": "part-time",
        "contract": "contract",
        "contractor": "contract",
        "temporary": "contract",
        "intern": "internship",
        "internship": "internship",
    }
    return mapping.get(lower, lower.replace(" ", "-"))
