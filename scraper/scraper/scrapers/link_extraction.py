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
    r"(linkedin\.com/share|facebook\.com/(share|sharer)|twitter\.com/(intent|share)|"
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
    "cookie settings",
)

COOKIE_NOTICE_RE = re.compile(r"\bcookies?\b", re.IGNORECASE)

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


def extract_job_links(html: str, base_url: str) -> list[RawJob]:
    soup = BeautifulSoup(html, "html.parser")
    best_by_url: dict[str, tuple[str, str, Optional[str]]] = {}
    base_parsed = urlparse(base_url)
    base_path = base_parsed.path.rstrip("/").lower()
    base_netloc = base_parsed.netloc.lower()
    base_has_job_hint = bool(JOB_HINT.search(base_path))

    for anchor in soup.find_all("a", href=True):
        href = _clean_text(anchor.get("href"))
        if not href or NON_JOB_URL.search(href):
            continue
        absolute = urljoin(base_url, href)
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

        looks_like_job = bool(
            (JOB_HINT.search(path) and _looks_like_job_detail_path(path, parsed.query))
            or (text and JOB_HINT.search(text))
            or (title_attr and JOB_HINT.search(title_attr))
            or structural_job_hint
        )
        if not looks_like_job:
            continue
        if path == base_path or path == "":
            continue

        existing = best_by_url.get(absolute)
        if existing is None or len(candidate_title) > len(existing[0]):
            best_by_url[absolute] = (candidate_title, path, job_type)

    return [
        RawJob(title=title, url=absolute, job_type=job_type)
        for absolute, (title, _, job_type) in sorted(best_by_url.items())
    ]


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


def _parse_jsonld_location(loc: object) -> str | None:
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
        parts = [p for p in (locality, region, country) if p]
        if parts:
            return ", ".join(str(p) for p in parts)
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
