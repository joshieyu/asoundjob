#!/usr/bin/env python3
"""Validate audio_companies_final.json against the schema.

Checks:
  1. Valid JSON syntax
  2. All required fields present (name, careers_url, category, verified, source)
  3. No empty strings for name or careers_url
  4. URLs start with http:// or https://
  5. category is from the allowed enum
  6. source is "manual" or "auto"
  7. scrape_method (if present) is "http" or "playwright"
  8. verified is a boolean
  9. No duplicate company names (case-insensitive)
  10. No additional unexpected fields
  11. Entries are sorted alphabetically by name

Usage:
  python3 scripts/validate_companies.py            # validate only
  python3 scripts/validate_companies.py --fix       # validate + auto-fix sorting
  python3 scripts/validate_companies.py --quiet     # only print errors
"""

import json
import sys
import os
from urllib.parse import urlparse

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "audio_companies_final.json")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "schema.json")

VALID_CATEGORIES = {
    "AI/ML Audio",
    "Acoustic Consulting & Engineering",
    "Audio Accessories & Cables",
    "Audio Health & Wellness",
    "Audio IP & Licensing",
    "Audio Interfaces & Converters",
    "Audio Middleware & SDK",
    "Audio Plugins & Virtual Instruments",
    "Audio Retailers & Distributors",
    "Audio Testing & Measurement",
    "Automotive OEMs",
    "Car Audio",
    "Consumer Electronics & Tech",
    "DAW & Music Production Software",
    "DJ Equipment",
    "Electronic Musical Instruments",
    "Gaming, VR & Immersive Audio",
    "Headphones & Personal Audio",
    "Hearing Aid & Hearing Tech",
    "Hi-Fi & Consumer Speakers",
    "Music Education Technology",
    "Professional Audio & Live Sound",
    "Recording Studios & Post Houses",
    "Smart Home & IoT Audio",
    "Streaming & Music Services",
    "Transducer & Driver Manufacturers",
    "Voice & Speech Technology",
}

REQUIRED_FIELDS = {"name", "careers_url", "category", "verified", "source"}
OPTIONAL_FIELDS = {"scrape_method", "notes"}
ALL_ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


def validate(data, quiet=False):
    errors = []
    warnings = []
    info = []

    # --- Check it's a list ---
    if not isinstance(data, list):
        errors.append("Root element must be an array")
        return errors, warnings, info

    info.append(f"Total entries: {len(data)}")

    # --- Track names for duplicates ---
    seen_names = {}
    seen_urls = {}

    for i, entry in enumerate(data):
        prefix = f"Entry {i}"
        name = entry.get("name", "???")
        prefix = f"Entry {i} ({name})"

        # --- Check it's a dict ---
        if not isinstance(entry, dict):
            errors.append(f"{prefix}: not an object")
            continue

        # --- Check required fields ---
        for field in REQUIRED_FIELDS:
            if field not in entry:
                errors.append(f"{prefix}: missing required field '{field}'")

        # --- Check for unexpected fields ---
        for key in entry:
            if key not in ALL_ALLOWED_FIELDS:
                warnings.append(f"{prefix}: unexpected field '{key}'")

        # --- Validate name ---
        if "name" in entry:
            if not isinstance(entry["name"], str) or not entry["name"].strip():
                errors.append(f"{prefix}: name is empty or not a string")
            else:
                name_lower = entry["name"].lower().strip()
                if name_lower in seen_names:
                    errors.append(
                        f"{prefix}: duplicate name '{entry['name']}' "
                        f"(also at entry {seen_names[name_lower]})"
                    )
                else:
                    seen_names[name_lower] = i

        # --- Validate careers_url ---
        if "careers_url" in entry:
            url = entry["careers_url"]
            if not isinstance(url, str) or not url.strip():
                errors.append(f"{prefix}: careers_url is empty or not a string")
            elif not url.startswith(("http://", "https://")):
                errors.append(f"{prefix}: careers_url must start with http:// or https://, got '{url[:30]}'")
            else:
                # Check URL is parseable
                try:
                    parsed = urlparse(url)
                    if not parsed.netloc:
                        errors.append(f"{prefix}: careers_url has no domain: '{url[:50]}'")
                except Exception:
                    errors.append(f"{prefix}: careers_url is malformed: '{url[:50]}'")

                # Check for duplicate URLs (warning, not error — brands can share a URL)
                url_lower = url.lower().rstrip("/")
                if url_lower in seen_urls:
                    warnings.append(
                        f"{prefix}: duplicate URL '{url[:50]}' "
                        f"(also used by entry {seen_urls[url_lower]})"
                    )
                else:
                    seen_urls[url_lower] = i

        # --- Validate category ---
        if "category" in entry:
            if entry["category"] not in VALID_CATEGORIES:
                errors.append(
                    f"{prefix}: invalid category '{entry['category']}'. "
                    f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
                )

        # --- Validate verified ---
        if "verified" in entry:
            if not isinstance(entry["verified"], bool):
                errors.append(f"{prefix}: verified must be true or false, got {type(entry['verified']).__name__}")

        # --- Validate source ---
        if "source" in entry:
            if entry["source"] not in ("manual", "auto"):
                errors.append(f"{prefix}: source must be 'manual' or 'auto', got '{entry['source']}'")

        # --- Validate scrape_method ---
        if "scrape_method" in entry:
            if entry["scrape_method"] not in ("http", "playwright"):
                errors.append(f"{prefix}: scrape_method must be 'http' or 'playwright', got '{entry['scrape_method']}'")

    # --- Check sorting ---
    names = [e.get("name", "") for e in data]
    sorted_names = sorted(names, key=str.lower)
    if names != sorted_names:
        warnings.append("Entries are not sorted alphabetically by name (run with --fix to auto-sort)")

    # --- Summary stats ---
    verified = sum(1 for e in data if e.get("verified") is True)
    unverified = sum(1 for e in data if e.get("verified") is False)
    manual = sum(1 for e in data if e.get("source") == "manual")
    auto = sum(1 for e in data if e.get("source") == "auto")
    http_count = sum(1 for e in data if e.get("scrape_method") == "http")
    pw_count = sum(1 for e in data if e.get("scrape_method") == "playwright")

    info.append(f"Verified: {verified} | Unverified: {unverified}")
    info.append(f"Source: {manual} manual | {auto} auto")
    info.append(f"Scrape method: {http_count} http | {pw_count} playwright")

    return errors, warnings, info


def main():
    fix = "--fix" in sys.argv
    quiet = "--quiet" in sys.argv

    # Resolve paths
    data_path = os.path.abspath(DATA_FILE)
    schema_path = os.path.abspath(SCHEMA_FILE)

    # --- Load JSON ---
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            raw = f.read()
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON syntax: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"ERROR: File not found: {data_path}")
        sys.exit(1)

    # --- Validate ---
    errors, warnings, info = validate(data, quiet=quiet)

    # --- Auto-fix: sorting ---
    if fix and warnings:
        data.sort(key=lambda e: e.get("name", "").lower())
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Auto-fixed: sorted entries alphabetically")
        # Re-validate after fix
        errors, warnings, info = validate(data, quiet=quiet)
        # Remove the sorting warning if it's gone
        warnings = [w for w in warnings if "not sorted" not in w]

    # --- Print results ---
    if not quiet:
        for line in info:
            print(f"  {line}")
        print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ✗ {e}")
        print()

    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠ {w}")
        print()

    if not errors and not warnings:
        print("✓ All checks passed")
    elif not errors:
        print(f"✓ No errors ({len(warnings)} warnings)")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
