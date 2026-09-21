from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

ATS_HOSTS = (
    "greenhouse.io", "lever.co", "workable.com", "ashbyhq.com", "smartrecruiters.com",
    "recruitee.com", "bamboohr.com", "myworkdayjobs.com", "workday.com", "icims.com",
    "taleo.net", "successfactors", "teamtailor.com", "personio", "jobvite.com",
    "pinpointhq.com", "adp.com", "oraclecloud.com", "paylocity.com", "breezy.hr",
    "jazzhr.com", "ultipro.com", "dayforcehcm.com", "eightfold.ai", "avature.net",
    "zenats.com", "applytojob.com", "paycomonline.net", "trakstar.com", "rippling.com",
    "phenompeople.com", "brassring.com", "silkroad", "careers-page.com", "join.com",
    "softgarden", "hrmdirect", "clearcompany.com", "paycor.com", "dayforce.com",
    "isolvedhire.com", "bullhorn", "myworkdaysite.com", "zohopublic", "recruitee",
    "jobs.gecareers", "eightfold", "hirehive", "workforcenow",
    "welcomekit.co", "welcometothejungle.com",
)

CAREERS_VOCAB = re.compile(
    r"career|job|vacan|recruit|join|hiring|hire|employment|opportunit|work-with|"
    r"workwith|work-for|working-at|life-at|lifeat|people|talent|stellen|emploi|"
    r"karriere|lavora|trabaja|empleo|saiyo|recruitment|recrut|carri[eè]re|"
    r"\bpositions?\b",
    re.IGNORECASE,
)

HARD_BAD = re.compile(
    r"accessdenied|/error|404|page-not-found|buy-domain|domain_profile|"
    r"press-releases?|/newsroom|\.pdf$|/password\b|aspxerrorpath",
    re.IGNORECASE,
)

URL_SHAPES: tuple[str, ...] = (
    "bad_page", "not_careers", "careers_shaped", "ats_board", "missing",
)


def host_of(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host.split(":")[0]


def is_ats_host(host: str) -> bool:
    return any(marker in host for marker in ATS_HOSTS)


def classify_careers_url(url: Optional[str]) -> str:
    url = (url or "").strip()
    if not url:
        return "missing"
    parsed = urlparse(url)
    host = host_of(url)
    if not host:
        return "missing"
    path = (parsed.path or "") + ("?" + parsed.query if parsed.query else "")
    if HARD_BAD.search(path):
        return "bad_page"
    if is_ats_host(host):
        return "ats_board"
    if CAREERS_VOCAB.search(path) or CAREERS_VOCAB.search(host):
        return "careers_shaped"
    return "not_careers"
