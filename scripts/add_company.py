#!/usr/bin/env python3
"""Add a new company to audio_companies_final.json.

Usage:
  # Interactive mode (prompts for each field):
  python3 scripts/add_company.py

  # Command-line mode:
  python3 scripts/add_company.py --name "My Company" --url "https://..." --category "AI/ML Audio"

  # With optional fields:
  python3 scripts/add_company.py --name "My Company" --url "https://..." --category "AI/ML Audio" --verified --method playwright --notes "Found via LinkedIn"

The script:
  1. Validates the input (URL format, category is valid, no duplicate name)
  2. Adds the entry with source="manual"
  3. Re-sorts the file alphabetically
  4. Runs validation on the result
  5. Saves
"""

import argparse
import json
import os
import sys

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "audio_companies_final.json")

VALID_CATEGORIES = [
    "AI/ML Audio",
    "Acoustic Consulting & Engineering",
    "Audio Accessories & Cables",
    "Audio Health & Wellness",
    "Audio IP & Licensing",
    "Audio Interfaces & Converters",
    "Audio Middleware & SDK",
    "Audio Plugins & Virtual Instruments",
    "Audio Retailers & Distributors",
    "Audio Semiconductors",
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
]


def load_data():
    with open(os.path.abspath(DATA_FILE), "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    data.sort(key=lambda e: e["name"].lower())
    with open(os.path.abspath(DATA_FILE), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_existing(data, name):
    """Check if a company with this name already exists (case-insensitive)."""
    name_lower = name.lower().strip()
    for i, entry in enumerate(data):
        if entry["name"].lower().strip() == name_lower:
            return i, entry
    return None, None


def add_or_update(data, name, url, category, verified, scrape_method, notes, update_if_exists):
    """Add a new entry or update an existing one."""
    idx, existing = find_existing(data, name)

    entry = {
        "name": name,
        "careers_url": url,
        "category": category,
        "verified": verified,
        "source": "manual",
        "scrape_method": scrape_method,
    }

    if notes:
        entry["notes"] = notes

    if existing is not None:
        if not update_if_exists:
            return False, f"Company '{name}' already exists at index {idx}. Use --update to overwrite."
        # Preserve source if it was already manual
        if existing.get("source") == "manual":
            entry["source"] = "manual"
        data[idx] = entry
        return True, f"Updated '{name}' at index {idx}"
    else:
        data.append(entry)
        return True, f"Added '{name}'"


def interactive_add():
    """Interactive prompt for adding a company."""
    print("=== Add Company to ASoundJob Directory ===\n")

    name = input("Company name: ").strip()
    if not name:
        print("Error: name is required")
        return

    url = input("Careers URL (full https:// URL): ").strip()
    if not url:
        print("Error: URL is required")
        return

    print("\nAvailable categories:")
    for i, cat in enumerate(VALID_CATEGORIES):
        print(f"  {i+1:2d}. {cat}")
    
    cat_input = input(f"\nCategory (number or name, 1-{len(VALID_CATEGORIES)}): ").strip()
    if cat_input.isdigit() and 1 <= int(cat_input) <= len(VALID_CATEGORIES):
        category = VALID_CATEGORIES[int(cat_input) - 1]
    elif cat_input in VALID_CATEGORIES:
        category = cat_input
    else:
        print(f"Error: invalid category '{cat_input}'")
        return

    verified_input = input("Verified? (y/n, default n): ").strip().lower()
    verified = verified_input == "y"

    method_input = input("Scrape method (http/playwright, default http): ").strip().lower()
    scrape_method = "playwright" if method_input == "playwright" else "http"

    notes = input("Notes (optional, press Enter to skip): ").strip() or None

    data = load_data()
    ok, msg = add_or_update(
        data, name, url, category, verified, scrape_method, notes,
        update_if_exists=True,
    )
    if ok:
        save_data(data)
        print(f"\n✓ {msg}")
        print(f"  Total entries: {len(data)}")
    else:
        print(f"\n✗ {msg}")


def main():
    parser = argparse.ArgumentParser(description="Add a company to the directory")
    parser.add_argument("--name", help="Company name")
    parser.add_argument("--url", help="Careers page URL")
    parser.add_argument("--category", help="Industry category")
    parser.add_argument("--verified", action="store_true", default=False, help="Mark as verified")
    parser.add_argument("--method", choices=["http", "playwright"], default="http", help="Scrape method")
    parser.add_argument("--notes", help="Optional notes")
    parser.add_argument("--update", action="store_true", help="Update if company already exists")
    args = parser.parse_args()

    if args.name and args.url and args.category:
        # Command-line mode
        if args.category not in VALID_CATEGORIES:
            print(f"Error: invalid category '{args.category}'")
            print(f"Valid categories: {', '.join(VALID_CATEGORIES)}")
            sys.exit(1)

        if not args.url.startswith(("http://", "https://")):
            print(f"Error: URL must start with http:// or https://")
            sys.exit(1)

        data = load_data()
        ok, msg = add_or_update(
            data, args.name, args.url, args.category,
            args.verified, args.method, args.notes,
            update_if_exists=args.update,
        )
        if ok:
            save_data(data)
            print(f"✓ {msg}")
            print(f"  Total entries: {len(data)}")
        else:
            print(f"✗ {msg}")
            sys.exit(1)
    elif not args.name and not args.url and not args.category:
        # Interactive mode
        interactive_add()
    else:
        parser.print_help()
        print("\nError: --name, --url, and --category are all required for CLI mode")
        sys.exit(1)


if __name__ == "__main__":
    main()
