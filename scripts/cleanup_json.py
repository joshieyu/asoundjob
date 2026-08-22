#!/usr/bin/env python3
"""Clean up audio_companies.json by removing product-level entries.

Algorithm (per unique careers URL):
  1. Compute a "brand root" for each entry = first word of normalized name.
  2. Group entries by brand root.
  3. In each root-group, keep only the best representative (shortest
     normalized name, prefer no parentheses).
  4. Entries with unique roots are always kept.

This correctly handles:
  - "Soundtoys Decapitator" + "Soundtoys"        -> keep "Soundtoys"
  - "BSS AR133" + "BSS Audio"                     -> keep "BSS Audio"
  - "Lexicon (plugins)" + "Lexicon Pro" + "Lexicon Automotive" -> keep "Lexicon Pro"
  - "JBL" + "AKG" (same URL, different roots)      -> keep both
"""

import json
from collections import defaultdict, Counter


SUFFIXES = [
    " corporation", " corp", " inc", " llc", " ltd", " group",
    " labs", " laboratory", " audio", " electronics", " technology",
    " technologies", " music", " systems", " international", " global",
    " speakers", " speaker", " pro", " professional", " automotive",
    " consumer", " commercial", " wireless", " conferencing",
    " monitors", " monitor", " car audio", " digital", " usa",
    " us", " uk", " europe", " asia", " pro audio", "plugins",
    " (plugins)", " (inmusic)", " (inmusic brands)", " designs",
    " engineering", " instruments", " amplification", " amps",
    " effects", " pedals", " microphones", " microphone",
    " manufacturing", " industries", " products", " devices",
    " ventures", " studios", " research", " associates",
    " consulting", " solutions", " network", " networks",
    " software", " media", " labs inc", " sound",
]


def normalize(name: str) -> str:
    """Lowercase, strip common suffixes for comparison."""
    s = name.lower().strip()
    # Remove parenthetical content
    if "(" in s:
        s = s.split("(")[0].strip()
    # Iteratively remove suffixes (some may stack)
    changed = True
    while changed:
        changed = False
        for suffix in SUFFIXES:
            if s.endswith(suffix) and len(s) > len(suffix):
                s = s[: -len(suffix)].strip()
                changed = True
    return s.strip()


def brand_root(name: str) -> str:
    """Extract the root brand identifier (first significant word)."""
    n = normalize(name)
    # For multi-word roots like "bang & olufsen", "bowers & wilkins",
    # take everything up to "&" or the first word
    if "&" in n:
        # Take both words around &
        parts = n.split("&")
        root = parts[0].strip().split()[-1] if parts[0].strip() else ""
        return root
    # For names like "d&b audiotechnik", take first word
    return n.split()[0] if n.split() else n


def score_entry(entry) -> tuple:
    """Lower score = more likely to be the real company name."""
    name = entry["name"]
    n = normalize(name)
    has_parens = 1 if "(" in name else 0
    norm_len = len(n)
    # Prefer entries whose raw name length is close to normalized length
    # (i.e., not a product name with extra descriptors)
    return (has_parens, norm_len, len(name))


def main():
    with open("audio_companies.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    by_url = defaultdict(list)
    for e in data:
        by_url[e["careers_url"]].append(e)

    cleaned = []
    removed = 0

    for url, entries in by_url.items():
        # Group by brand root
        root_groups = defaultdict(list)
        for entry in entries:
            root = brand_root(entry["name"])
            root_groups[root].append(entry)

        for root, group in root_groups.items():
            if len(group) == 1:
                cleaned.append(group[0])
            else:
                # Sort by score (best representative first)
                group.sort(key=score_entry)
                best = group[0]
                cleaned.append(best)
                removed += len(group) - 1

    # Deduplicate by normalized name across the entire dataset
    # (catches companies that appear in multiple categories)
    seen = set()
    final = []
    for entry in sorted(cleaned, key=lambda e: e["name"].lower()):
        n = normalize(entry["name"])
        if n not in seen:
            seen.add(n)
            final.append(entry)
        else:
            removed += 1

    final.sort(key=lambda e: e["name"].lower())

    with open("audio_companies.json", "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"Original:  {len(data)} entries")
    print(f"Removed:   {removed} product/duplicate entries")
    print(f"Cleaned:   {len(final)} entries")

    cat_counts = Counter(e["category"] for e in final)
    print(f"\nCompanies per category:")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Verify problematic URLs
    print(f"\nVerification (problematic URLs):")
    by_url2 = defaultdict(list)
    for e in final:
        by_url2[e["careers_url"]].append(e)
    for url in [
        "https://careers.harman.com",
        "https://www.musictribe.com/careers",
        "https://www.inmusicbrands.com/careers",
        "https://www.apple.com/careers/",
        "https://www.yamaha.com/en/careers",
        "https://www.bose.com/en_us/careers.html",
        "https://www.moogmusic.com/careers",
    ]:
        entries = by_url2.get(url, [])
        print(f"  {len(entries):2d} -> {url}")
        print(f"       {[e['name'] for e in entries]}")


if __name__ == "__main__":
    main()
