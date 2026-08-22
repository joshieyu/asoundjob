#!/usr/bin/env python3
"""Clean up audio_companies_final.json:
  1. Remove non-companies (YouTubers, blogs, magazines, generic platforms)
  2. Identify and re-verify suspicious verified URLs
  3. Mark bad verified URLs as unverified
"""

import json
import re
from urllib.parse import urlparse


# --- Non-companies to remove ---
# YouTubers / solo personalities with no real hiring
YOUTUBERS = {
    "andy guitar", "rick beato", "marty music", "justinguitar",
    "produce like a pro", "recording revolution", "mixbustv",
}

# Blogs / magazines / forums / media (not companies that hire audio engineers)
BLOGS_MEDIA = {
    "tape op", "premier guitar", "sonic scoop", "pro audio files",
    "sound on sound", "mix magazine", "audio technology",
    "electronic musician", "kvr audio", "dont crack", "don't crack",
    "plugin boutique",
}

# Generic education platforms (not audio companies)
GENERIC_PLATFORMS = {
    "coursera music", "udemy music", "lynda music (linkedin)",
    "skillshare music", "masterclass music", "kadenze",
    "edx audio", "udacity audio",
}

# Solo projects / too small / not real companies
SOLO_SMALL = {
    "lightnote", "musictheory.net", "teoria", "modacity",
    "a soft murmur", "mynoise", "defonic", "noisli", "noisefy",
    "audiosauna", "online sequencer", "pattern sketch", "audiomass",
    "ambient mixer", "tidepool", "mubuta", "pacifical",
}

# Fake / placeholder entries that snuck in
FAKE = {
    ".msoe", "audio acoustic", "game audio", "game dial",
    "audio future", "wysiwyg audio", "sound stacks",
    "tawki entertainment", "iosno", "trellis sound",
    "pantomime", "echo interaction", "soundscape",
    "smomid", "zen micro key", "sl apps",
    "nightradio", "madwish", "socasynth",
    "bitterspring audio", "rift audio", "capsule audio",
    "loom audio", "sonic anomaly", "brute force audio",
    "mogami ai", "vibe ai", "naturalsoft",
    "ear technologies", "innerscope", "nanox",
    "ear buddy", "audiodome", "audionova international",
    "accusonic speakers", "continuous acoustics",
    "acoustic consulting", "acoustic consulting group",
    "acoustical consultants", "acoustical consultants inc",
    "acoustical design collaborative", "acoustical design group",
    "acoustical engineering", "acoustical engineering associates",
    "acoustic design", "acoustics design", "acoustic design lab",
    "acoustic alliance", "proacoustics", "sound acoustics",
    "new acoustics", "new acoustics llc", "listen acoustics",
    "acoustic studio", "acousta", "acoustic engineering solutions",
    "sound consulting", "sound technology", "sound control",
    "sound & vibration solutions", "firm acoustics",
    "valerie acoustics", "valerie acoustics llc",
    "dicker acoustics", "advantacoustics", "swift acoustics",
    "noise control", "noise consultants",
}

ALL_REMOVE = YOUTUBERS | BLOGS_MEDIA | GENERIC_PLATFORMS | SOLO_SMALL | FAKE


# --- Suspicious URL patterns ---
# URLs that are clearly not careers pages
BAD_URL_PATTERNS = [
    "search",           # search pages
    "/blog",            # blog posts
    "/blogs/",          # blog posts
    "/videos/",         # video pages
    "/user-comments",   # comment pages
    "/usage-tips",      # tip pages
    "/produkte/",       # product pages (German)
    "/shop/",           # shop pages
    "/store.",          # store pages
    "/sign-in",         # login pages
    "/contact",         # contact pages
    "/our-team",        # team pages (not job listings)
    "/instruments/",    # product pages
    "/promos/",         # promo pages
    "/messageboard",    # forums
    "/randolph",        # clearly wrong content
    "binjaratraders",   # wrong site
    "empowertribe",     # wrong site
    "forbidden",        # blocked pages
    "block.charter",    # ISP block pages
    "domaincontactservice",  # domain parking
    "capacity.com",     # wrong site
    "select_consultant",  # consultant directory, not careers
    "partners-in-hearing",  # partner page, not careers
    "submit-form",      # generic form
]


def is_bad_url(url):
    """Check if URL looks like a non-careers page."""
    url_lower = url.lower()
    for pattern in BAD_URL_PATTERNS:
        if pattern in url_lower:
            return True
    return False


def main():
    with open("data/audio_companies_final.json", "r") as f:
        data = json.load(f)

    print(f"Starting with {len(data)} entries")

    # --- Pass 1: Remove non-companies ---
    removed = []
    kept = []
    for entry in data:
        name_lower = entry["name"].lower().strip()
        if name_lower in ALL_REMOVE:
            removed.append(entry)
        else:
            kept.append(entry)

    print(f"\nPass 1 - Removed {len(removed)} non-companies:")
    for e in sorted(removed, key=lambda x: x["name"].lower()):
        print(f"  {e['name']:35s} [{e['category']}]")

    # --- Pass 2: Mark suspicious verified URLs as unverified ---
    demoted = []
    for entry in kept:
        if entry["verified"] and is_bad_url(entry["careers_url"]):
            entry["verified"] = False
            demoted.append(entry)

    print(f"\nPass 2 - Demoted {len(demoted)} suspicious verified URLs to unverified:")
    for e in sorted(demoted, key=lambda x: x["name"].lower()):
        print(f"  {e['name']:35s} -> {e['careers_url'][:65]}")

    # --- Save ---
    kept.sort(key=lambda e: e["name"].lower())
    with open("data/audio_companies_final.json", "w", encoding="utf-8") as f:
        json.dump(kept, f, indent=2, ensure_ascii=False)

    verified = sum(1 for e in kept if e["verified"])
    unverified = sum(1 for e in kept if not e["verified"])
    print(f"\nFinal: {len(kept)} entries ({verified} verified, {unverified} unverified)")


if __name__ == "__main__":
    main()
