#!/usr/bin/env python3
"""Second-pass cleanup for audio_companies.json.

Handles cases the first pass missed:
  1. Entries with "(ParentCompany)" suffix -> remove if parent exists
  2. Obvious product names (codecs, model numbers) -> remove
  3. Division names that beat parent brand names -> fix
  4. Near-duplicate names across categories -> dedupe
"""

import json
import re
from collections import defaultdict


def load_data():
    with open("audio_companies.json", "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open("audio_companies.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def has_parent_in_group(name, url, all_by_url):
    """Check if name has a (Parent) suffix and parent exists in same URL group."""
    m = re.search(r'\(([^)]+)\)', name)
    if not m:
        return False
    parent_hint = m.group(1).lower().strip()
    # Check if any entry in the same URL group matches the parent hint
    for entry in all_by_url.get(url, []):
        if entry["name"].lower() == name.lower():
            continue
        ename = entry["name"].lower()
        # Direct match or parent_hint is contained in entry name
        if parent_hint in ename or ename in parent_hint:
            return True
    return False


def is_product_name(name):
    """Heuristic: does this look like a product rather than a company?"""
    nl = name.lower()
    # Contains model number pattern (letter+digits or digits at end)
    if re.search(r'\b[a-z]+\d{2,4}\b', nl):
        return True
    if re.search(r'\b\d{2,4}\b', nl) and not re.search(r'\b\d{1,4}(st|nd|rd|th)\b', nl):
        return True
    # Contains codec/format names
    codecs = {'aac', 'mp3', 'flac', 'opus', 'vorbis', 'speex', 'celt',
              'mpeg-h', 'av1', 'ldac', 'lhdc', 'llac', 'aptx', 'evs'}
    words = set(nl.split())
    if words & codecs:
        return True
    return False

# Manual blacklist of product names to remove (lowercase)
PRODUCT_BLACKLIST = {
    # NVIDIA products
    "audio2face (nvidia)", "broadcast suite (nvidia)",
    "maxine (nvidia)", "nemo (nvidia)", "riva (nvidia)",
    "triton (nvidia)",
    # Google products
    "deepmind audio (google)", "dialogflow (google)",
    "magenta (google)", "tensorflow audio (google)",
    "youtube audio (google)", "nest audio (google)",
    # Apple products
    "garageband", "homepod mini (apple)", "logic pro for ipad",
    # Amazon products
    "amazonbasics audio", "echo dot (amazon)", "polly (amazon)",
    # Microsoft products
    "azure speech (microsoft)", "skype (microsoft)",
    # Meta products
    "oculus audio sdk (meta)", "pytorch audio (meta)",
    "whatsapp voice (meta)", "miles sound system (rad game tools)",
    # NTi Audio products
    "dlx-1 (nti audio)", "minirator (nti audio)",
    "mnt-1 (nti audio)", "mr-pro (nti audio)", "supra (nti audio)",
    # Other obvious products
    "midas m32", "harman automotive", "harman karman",
    "mpc (akai)", "vocaloid (yamaha)",
    "ssl live", "steam audio (valve)",
    "easera (afmg)", "systune (afmg)",
    "analog lab (arturia)", "polybrute (arturia)",
    "instrument 1 (artiphon)", "orba (artiphon)",
    "m-tron pro (gforce)", "wurli (gforce)",
    "luminary lightpad", "seaboard (roli)",
    "samplitude pro x (magix)", "sequoia (magix)",
    "tdr nova", "melda audiodynamics",
    "f1 audio", "omnia (funktion one)",
    "ps-20 (cherry)", "neve (plugins)",
    "dts headphone:x", "dts:x",
    "dolby digital", "dolby.io",
    "squeezbox (logitech)", "lake processing",
    "cakewalk (bandlab)", "bias fx",
    "praesideo (bosch)", "mogami (canare)",
    "capital studios", "cerevoice",
    "chief (legrand)", "vdo (continental)",
    "continuum fingerboard", "maxon (cycling 74)",
    "dave smith instruments", "lyrebird ai (descript)",
    "djuced (hercules)", "mxr (dunlop)", "eqd pedals",
    "els studio (panasonic)", "fl studio cloud",
    "focal-jm lab", "power conditioners (furman)",
    "gn otometrics", "resound (gn)",
    "harrison mixbus", "mixbus (harrison)",
    "hbo post production", "warner bros post",
    "helix (audiotec fischer)", "match (audiotec fischer)",
    "ripx (hit'n'mix)", "homedics sound", "marpac (homedics)",
    "ideas (siemens)", "iheartmedia studios",
    "infected mushroom (wmd)", "lenire (neuromod)",
    "linn electronics", "linnstrument",
    "mark of the unicorn", "traktor (ni)",
    "otometrics (natus)", "tripod stands (on-stage)",
    "openai audio", "whisper (openai)",
    "th-u (overloud)", "p.audio bm-d", "ua volt",
    "studio one (presonus)", "fl studio mobile",
    "samplitude (magix)", "ecasera (afmg)",
    "audio technica wireless", "audio technica conferencing",
    "audio technica pro", "sennheiser wireless",
    "sennheiser conferencing", "shure wireless",
    "shure conferencing", "shure mxw",
    "beyerdynamic pro", "beyerdynamic conferencing",
    "earthworks conferences", "bridger audio",
    "glen sound", "professional wireless systems",
    "soundskapes", "audioarts engineering",
    "jbl consumer", "jbl car audio", "jbl professional",
    "akg automotive", "akg professional",
    "lexicon automotive", "lexicon (plugins)",
    "infinity car audio", "revel automotive",
    "harman karman",
    "sonos arc", "sonos beam", "sonos ray",
    "sonos era", "sonos move", "sonos roam",
    "echo link (amazon)", "echo show (amazon)",
    "nest mini (google)", "nest hub (google)",
    "bose smart speaker", "bose soundbar",
    "bose soundlink", "bose sleep",
    "bose noise cancelling", "samsung soundbar",
    "lg soundbar", "vizio soundbar",
    "tcl soundbar", "hisense soundbar",
    "polk magnifi", "klipsch cinema", "jbl bar",
    "yamaha musiccast 20", "yamaha musiccast 50",
    "denon home", "marantz sound",
    "wiim", "echo dot (amazon)", "echo studio (amazon)",
    "homepod mini (apple)", "pioneer ddj",
    "pioneer cdj", "pioneer djm",
    "denon dj sc", "denon dj prime",
    "rane seventy", "rane twelve",
    "numark mixtrack", "numark ns",
    "behringer crave", "behringer neutron",
    "behringer model d", "behringer pro-1",
    "behringer deepmind", "behringer poly d",
    "behringer x32", "behringer pedals",
    "midas m32", "turbo sound (music tribe)",
    "tannoy professional",
    "zoom livetrak", "zoom (interfaces)",
    "tascam (interfaces)", "roland (interfaces)",
    "mackie (interfaces)", "behringer (interfaces)",
    "roland (interfaces)", "apogee symphony",
    "apogee ensemble", "apogee duet", "apogee one",
    "ua apollo", "ua arrow", "ua volt",
    "antelope orion", "antelope goliath", "antelope zen",
    "lynx aurora", "lynx hilo", "burl b2", "burl b80",
    "prism sound atlas", "prism sound lyra",
    "prism sound titan", "merging hapi", "merging horus",
    "dad ax32", "dad dx32", "metric halo lio",
    "benchmark dac1", "grace m903",
    "mytek brooklyn", "mytek manhattan",
    "chord hugo", "chord dave", "chord qutest",
    "topping audio", "s.m.s.l audio", "sabaj audio",
    "geshelli labs", "schiit audio", "jds labs",
    "denafrips", "msb technology", "light harmonic",
    "singxer audio", "soncoz audio", "rockna audio",
    "holo audio", "goldring",
    "cableorganizer", "cable matters",
    "amazonbasics audio", "fiio cables",
    "geshelli cables", "ifi cables", "premium cables",
    "audio sensibility", "cable shield",
    "lehlé", "bento audio", "miniamp",
    "t-rex engineering", "visual sound",
    "cmatmods", "solidgoldfx",
    "caroline guitar", "keeley electronics",
    "xotic effects", "spaceman effects",
    "kokko audio", "mooer pedaling",
    "joyo audio", "donner audio", "rowin audio",
    "modtone pedals", "visual sound pedals",
    "ignited studios", "jaco studios",
    "wonder audio", "atomic amps",
    "hotone audio", "mooer audio",
    "a designs audio", "eminent audio",
    "tube audio", "audionet",
    "avm audio", "brinkmann audio",
    "kawai musical instruments",
    "suzuki musical instrument",
    "mezzo forte", "blipbox",
    "miselu c.24", "craspad",
    "reactable", "smomid",
    "zen micro key", "sl apps",
    "focal pro", "neumann monitors",
    "yamaha monitors", "mackie monitors",
    "presonus monitors", "krk systems",
    "avantone pro monitors", "avantone pro",
    "passive labs", "auratone",
    "korg pro audio", "korg dj", "korg inc",
    "korg kronos", "korg minilogue",
    "korg prologue", "korg wavestate",
    "korg opsix", "korg drumlogue",
    "korg volca", "korg electribe", "korg gadget",
    "roland pro audio", "roland aira",
    "roland boutique", "roland tr-8", "roland dj",
    "yamaha montage", "yamaha modx",
    "yamaha reface", "yamaha dx7",
    "yamaha commercial audio", "yamaha musiccast",
    "moog subharmonicon", "moog subsequent",
    "moog grandmother", "moog matriarch",
    "moog modular", "moog music inc",
    "sequential prophet", "sequential ob-6",
    "sequential take 5",
    "nord stage", "nord electro",
    "nord drum", "nord wave",
    "elektron digitakt", "elektron analog rytm",
    "elektron octatrack", "elektron analog four",
    "elektron syntakt", "elektron model:samples",
    "elektron model:cycles", "elektron dj",
    "waldorf quantum", "waldorf iridium",
    "waldorf blofeld", "modal argon", "modal cobalt",
    "access virus", "pioneer dj toraiz",
    "asm hydrasynth", "black corporation",
    "dreadbox erebus", "dreadbox nyx",
    "dreadbox hypnosis", "pittsburgh modular lifeforms",
    "buchla electronic musical instruments",
    "serge modular", "ciat-lonbarde",
    "medeli electronics", "casio music",
    "roli blocks", "artiphon",
    "joué modular", "sensel morph",
    "eigenharp (eigenlabs)", "haken audio",
    "polyend", "squarp instruments",
    "torso electronics",
    "kontakt (native instruments)",
    "komplete (native instruments)",
    " Massive (native instruments)",
    "massive (native instruments)",
    # Last stragglers
    "xtrax stems", "auro-3d", "mixmeister",
    "infinity speakers", "revel speakers",
}


def main():
    data = load_data()
    original_count = len(data)

    # Group by URL for parent checking
    by_url = defaultdict(list)
    for e in data:
        by_url[e["careers_url"]].append(e)

    # Pass 1: Remove blacklisted products
    cleaned = []
    removed_blacklist = 0
    for entry in data:
        nl = entry["name"].lower().strip()
        if nl in PRODUCT_BLACKLIST:
            removed_blacklist += 1
        else:
            cleaned.append(entry)

    # Rebuild by_url with cleaned data
    by_url = defaultdict(list)
    for e in cleaned:
        by_url[e["careers_url"]].append(e)

    # Pass 2: Remove entries with (Parent) suffix where parent exists
    removed_parent = 0
    pass2 = []
    for entry in cleaned:
        name = entry["name"]
        url = entry["careers_url"]
        if has_parent_in_group(name, url, by_url):
            removed_parent += 1
        else:
            pass2.append(entry)
    cleaned = pass2

    # Rebuild by_url
    by_url = defaultdict(list)
    for e in cleaned:
        by_url[e["careers_url"]].append(e)

    # Pass 3: Remove entries that look like products (model numbers, etc.)
    # but only if there's another entry with the same URL
    removed_product = 0
    pass3 = []
    for entry in cleaned:
        url = entry["careers_url"]
        if len(by_url[url]) > 1 and is_product_name(entry["name"]):
            removed_product += 1
        else:
            pass3.append(entry)
    cleaned = pass3

    # Pass 4: Cross-category dedup by normalized name
    removed_dup = 0
    seen = set()
    final = []
    for entry in sorted(cleaned, key=lambda e: e["name"].lower()):
        # Simple normalization for dedup
        key = entry["name"].lower().strip()
        # Remove parenthetical content for dedup key
        key = re.sub(r'\s*\([^)]*\)', '', key).strip()
        # Remove common suffixes
        for suffix in [" corporation", " corp", " inc", " ltd", " group",
                       " technologies", " technology", " electronics",
                       " international", " global", " systems", " audio"]:
            key = key.removesuffix(suffix).strip()
        if key not in seen:
            seen.add(key)
            final.append(entry)
        else:
            removed_dup += 1

    final.sort(key=lambda e: e["name"].lower())
    save_data(final)

    total_removed = original_count - len(final)
    print(f"Original:              {original_count}")
    print(f"Removed (blacklist):   {removed_blacklist}")
    print(f"Removed (parent ref):  {removed_parent}")
    print(f"Removed (product ptrn):{removed_product}")
    print(f"Removed (dedup):       {removed_dup}")
    print(f"Final:                 {len(final)}")
    print(f"Total removed:         {total_removed}")

    # Verify
    from collections import Counter
    cat_counts = Counter(e["category"] for e in final)
    print(f"\nCompanies per category:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Check remaining multi-entry URLs
    by_url2 = defaultdict(list)
    for e in final:
        by_url2[e["careers_url"]].append(e)
    multi = {u: v for u, v in by_url2.items() if len(v) > 1}
    print(f"\nURLs still with multiple entries: {len(multi)}")
    for url, entries in sorted(multi.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  {len(entries):2d} -> {url}")
        print(f"       {[e['name'] for e in entries]}")


if __name__ == "__main__":
    main()
