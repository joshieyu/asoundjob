from __future__ import annotations

import re
import unicodedata
from typing import Optional

COUNTRY_NAMES: dict[str, str] = {
    "AE": "United Arab Emirates",
    "AR": "Argentina",
    "AT": "Austria",
    "AU": "Australia",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "BR": "Brazil",
    "CA": "Canada",
    "CH": "Switzerland",
    "CL": "Chile",
    "CN": "China",
    "CO": "Colombia",
    "CZ": "Czechia",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "EG": "Egypt",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GB": "United Kingdom",
    "GR": "Greece",
    "GT": "Guatemala",
    "HK": "Hong Kong",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IL": "Israel",
    "IN": "India",
    "IT": "Italy",
    "JP": "Japan",
    "KR": "South Korea",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MA": "Morocco",
    "MX": "Mexico",
    "MY": "Malaysia",
    "NL": "Netherlands",
    "NO": "Norway",
    "NZ": "New Zealand",
    "PA": "Panama",
    "PE": "Peru",
    "PH": "Philippines",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "SA": "Saudi Arabia",
    "SE": "Sweden",
    "SG": "Singapore",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "TH": "Thailand",
    "TR": "Turkey",
    "TW": "Taiwan",
    "UA": "Ukraine",
    "US": "United States",
    "VN": "Vietnam",
    "ZA": "South Africa",
}

COUNTRY_ALIASES: dict[str, str] = {
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "u s a": "US",
    "u s": "US",
    "us": "US",
    "america": "US",
    "united kingdom": "GB",
    "great britain": "GB",
    "uk": "GB",
    "u k": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "britain": "GB",
    "deutschland": "DE",
    "germany": "DE",
    "holland": "NL",
    "the netherlands": "NL",
    "netherlands": "NL",
    "pays bas": "NL",
    "republic of ireland": "IE",
    "ireland": "IE",
    "south korea": "KR",
    "republic of korea": "KR",
    "korea": "KR",
    "taiwan": "TW",
    "hong kong": "HK",
    "china": "CN",
    "prc": "CN",
    "mainland china": "CN",
    "japan": "JP",
    "india": "IN",
    "singapore": "SG",
    "philippines": "PH",
    "the philippines": "PH",
    "vietnam": "VN",
    "viet nam": "VN",
    "thailand": "TH",
    "malaysia": "MY",
    "indonesia": "ID",
    "australia": "AU",
    "new zealand": "NZ",
    "canada": "CA",
    "mexico": "MX",
    "mexico city": "MX",
    "brazil": "BR",
    "brasil": "BR",
    "argentina": "AR",
    "chile": "CL",
    "colombia": "CO",
    "peru": "PE",
    "france": "FR",
    "spain": "ES",
    "espana": "ES",
    "italy": "IT",
    "italia": "IT",
    "portugal": "PT",
    "belgium": "BE",
    "austria": "AT",
    "switzerland": "CH",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "poland": "PL",
    "polska": "PL",
    "czechia": "CZ",
    "czech republic": "CZ",
    "slovakia": "SK",
    "slovenia": "SI",
    "hungary": "HU",
    "romania": "RO",
    "bulgaria": "BG",
    "serbia": "RS",
    "greece": "GR",
    "guatemala": "GT",
    "panama": "PA",
    "turkey": "TR",
    "turkiye": "TR",
    "ukraine": "UA",
    "russia": "RU",
    "estonia": "EE",
    "latvia": "LV",
    "lithuania": "LT",
    "luxembourg": "LU",
    "israel": "IL",
    "united arab emirates": "AE",
    "uae": "AE",
    "saudi arabia": "SA",
    "egypt": "EG",
    "morocco": "MA",
    "south africa": "ZA",
}

US_STATE_NAMES: frozenset = frozenset({
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
    "district of columbia", "washington dc", "puerto rico",
})

US_STATE_CODES: frozenset = frozenset({
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy", "dc", "pr",
})

CA_PROVINCE_NAMES: frozenset = frozenset({
    "ontario", "quebec", "british columbia", "alberta", "manitoba",
    "saskatchewan", "nova scotia", "new brunswick", "newfoundland",
    "newfoundland and labrador", "prince edward island", "yukon",
    "northwest territories", "nunavut",
})

CA_PROVINCE_CODES: frozenset = frozenset({
    "ab", "bc", "mb", "nb", "nl", "ns", "nt", "nu", "on", "pe", "qc", "sk",
    "yt",
})

CITY_COUNTRY: dict[str, str] = {
    "aachen": "DE",
    "agawam": "US",
    "alkmaar": "NL",
    "alpharetta": "US",
    "atlanta": "US",
    "ballerup": "DK",
    "bangsar south": "MY",
    "beaverton": "US",
    "bentonville": "US",
    "berkeley": "US",
    "bologna": "IT",
    "boulder": "US",
    "brighton": "GB",
    "bucharest": "RO",
    "cantabria": "ES",
    "charlotte": "US",
    "chengdu": "CN",
    "chiba": "JP",
    "columbus": "US",
    "culver city": "US",
    "east grinstead": "GB",
    "edina": "US",
    "el segundo": "US",
    "elancourt": "FR",
    "framingham": "US",
    "full sail": "US",
    "goleta": "US",
    "grand prairie": "US",
    "haifa": "IL",
    "hemel hempstead": "GB",
    "high wycombe": "GB",
    "houston": "US",
    "limerick": "IE",
    "linkoping": "SE",
    "minato": "JP",
    "mississauga": "CA",
    "montigny le bretonneux": "FR",
    "noida": "IN",
    "north aurora": "US",
    "opelika": "US",
    "osterley": "GB",
    "pasadena": "US",
    "pittsburgh": "US",
    "plano": "US",
    "pompano beach": "US",
    "rellingen": "DE",
    "saint albans": "GB",
    "shah alam": "MY",
    "somerville": "US",
    "spokane": "US",
    "suwanee": "US",
    "suzhou": "CN",
    "toluca": "MX",
    "valencia": "ES",
    "villeneuve d ascq": "FR",
    "warszawa": "PL",
    "wesseling": "DE",
    "amsterdam": "NL",
    "auckland": "NZ",
    "austin": "US",
    "bangalore": "IN",
    "bengaluru": "IN",
    "barcelona": "ES",
    "beijing": "CN",
    "belfast": "GB",
    "berlin": "DE",
    "bogota": "CO",
    "boston": "US",
    "brisbane": "AU",
    "brooklyn": "US",
    "brussels": "BE",
    "budapest": "HU",
    "buenos aires": "AR",
    "chennai": "IN",
    "chicago": "US",
    "cologne": "DE",
    "copenhagen": "DK",
    "cork": "IE",
    "cupertino": "US",
    "dallas": "US",
    "darmstadt": "DE",
    "delhi": "IN",
    "denver": "US",
    "dubai": "AE",
    "dublin": "IE",
    "dusseldorf": "DE",
    "edinburgh": "GB",
    "edmonton": "CA",
    "eindhoven": "NL",
    "frankfurt": "DE",
    "geneva": "CH",
    "glasgow": "GB",
    "gothenburg": "SE",
    "guangzhou": "CN",
    "hamburg": "DE",
    "hanoi": "VN",
    "helsinki": "FI",
    "herzliya": "IL",
    "ho chi minh city": "VN",
    "hsinchu": "TW",
    "hyderabad": "IN",
    "istanbul": "TR",
    "jakarta": "ID",
    "kuala lumpur": "MY",
    "kyoto": "JP",
    "lisbon": "PT",
    "london": "GB",
    "los angeles": "US",
    "lyon": "FR",
    "madrid": "ES",
    "manchester": "GB",
    "manila": "PH",
    "melbourne": "AU",
    "milan": "IT",
    "milano": "IT",
    "minneapolis": "US",
    "montreal": "CA",
    "mumbai": "IN",
    "munich": "DE",
    "muenchen": "DE",
    "nashville": "US",
    "new york": "US",
    "new york city": "US",
    "nyc": "US",
    "osaka": "JP",
    "oslo": "NO",
    "ottawa": "CA",
    "paris": "FR",
    "philadelphia": "US",
    "phoenix": "US",
    "portland": "US",
    "prague": "CZ",
    "pune": "IN",
    "rome": "IT",
    "rotterdam": "NL",
    "san diego": "US",
    "san francisco": "US",
    "san francisco bay area": "US",
    "san jose": "US",
    "santa clara": "US",
    "sao paulo": "BR",
    "seattle": "US",
    "seoul": "KR",
    "shanghai": "CN",
    "shenzhen": "CN",
    "sherbrooke": "CA",
    "stockholm": "SE",
    "stuttgart": "DE",
    "sunnyvale": "US",
    "sydney": "AU",
    "taipei": "TW",
    "tel aviv": "IL",
    "tokyo": "JP",
    "toronto": "CA",
    "vancouver": "CA",
    "vienna": "AT",
    "warsaw": "PL",
    "wroclaw": "PL",
    "zurich": "CH",
}

COUNTRY_ALPHA3: dict[str, str] = {
    "are": "AE", "arg": "AR", "aus": "AU", "aut": "AT", "bel": "BE",
    "bgr": "BG", "bra": "BR", "can": "CA", "che": "CH", "chl": "CL",
    "chn": "CN", "col": "CO", "cze": "CZ", "deu": "DE", "dnk": "DK",
    "egy": "EG", "esp": "ES", "est": "EE", "fin": "FI", "fra": "FR",
    "gbr": "GB", "grc": "GR", "hkg": "HK", "hun": "HU", "idn": "ID",
    "ind": "IN", "irl": "IE", "isr": "IL", "ita": "IT", "jpn": "JP",
    "kor": "KR", "ltu": "LT", "lux": "LU", "lva": "LV", "mar": "MA",
    "mex": "MX", "mys": "MY", "nld": "NL", "nor": "NO", "nzl": "NZ",
    "per": "PE", "phl": "PH", "pol": "PL", "prt": "PT", "rou": "RO",
    "rus": "RU", "sau": "SA", "sgp": "SG", "srb": "RS", "svk": "SK",
    "svn": "SI", "swe": "SE", "tha": "TH", "tur": "TR", "twn": "TW",
    "ukr": "UA", "usa": "US", "vnm": "VN", "zaf": "ZA",
}

_SEGMENT_SPLIT_RE = re.compile(r"[,;|/:]|\s+-\s+|\s+[–—]\s+")
_PAREN_RE = re.compile(r"[()]")
_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")
_SPACE_RE = re.compile(r"\s+")
_MAX_LOCATION_LEN = 300


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = _PUNCT_RE.sub(" ", stripped.lower())
    return _SPACE_RE.sub(" ", lowered).strip()


MAX_PHRASE_WORDS = 3


def _segments(location: str) -> list[str]:
    unwrapped = _PAREN_RE.sub(",", location[:_MAX_LOCATION_LEN])
    parts = _SEGMENT_SPLIT_RE.split(unwrapped)
    return [folded for folded in (_fold(part) for part in parts) if folded]


def _phrases(segments: list[str]) -> list[str]:
    found: list[str] = []
    for segment in segments:
        found.append(segment)
        words = segment.split()
        if len(words) < 2:
            continue
        for size in range(1, MAX_PHRASE_WORDS + 1):
            for start in range(len(words) - size + 1):
                found.append(" ".join(words[start:start + size]))
    return found


def _sole(votes: set[str]) -> Optional[str]:
    return next(iter(votes)) if len(votes) == 1 else None


def detect_country(location: str | None) -> Optional[str]:
    if not location or not location.strip():
        return None
    segments = _segments(location)
    if not segments:
        return None
    phrases = _phrases(segments)

    named = {COUNTRY_ALIASES[phrase] for phrase in phrases if phrase in COUNTRY_ALIASES}
    resolved = _sole(named)
    if resolved is not None:
        return resolved
    if named:
        return None

    if any(phrase in US_STATE_NAMES for phrase in phrases):
        return "US"

    cities = {CITY_COUNTRY[phrase] for phrase in phrases if phrase in CITY_COUNTRY}
    resolved = _sole(cities)
    if resolved is not None:
        return resolved
    if cities:
        return None

    if any(seg in US_STATE_CODES for seg in segments):
        return "US"
    if any(
        phrase in CA_PROVINCE_NAMES or phrase in CA_PROVINCE_CODES
        for phrase in phrases
    ):
        return "CA"

    coded = {seg.upper() for seg in segments if seg.upper() in COUNTRY_NAMES}
    coded |= {COUNTRY_ALPHA3[seg] for seg in segments if seg in COUNTRY_ALPHA3}
    return _sole(coded)


def country_name(code: str | None) -> Optional[str]:
    if not code:
        return None
    return COUNTRY_NAMES.get(code.upper())
