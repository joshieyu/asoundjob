# ASoundJob — Handoff Brief

## Project

ASoundJob is an audio industry job board + career resource site. It scrapes
audio companies' careers pages, aggregates job listings, and presents them with
filtering, search, and SEO-optimized detail pages. Built for the Young Audio
Professionals (YAP) organization.

## Quick Start

```bash
# Activate venv (Python 3.9.6 — write 3.9-compatible code)
cd scraper && source ../venv/bin/activate

# Run migrations
alembic upgrade head

# Load companies from JSON into DB
python -m scraper.company_loader

# Scrape (smoke test: 5 companies)
python -m scraper.main --once --limit 5 --verbose

# Full scrape (timeout ~10min, only ATS companies fast)
python -m scraper.main --once --skip-load

# Re-score relevance after category/keyword changes
python -m scraper.backfill_relevance

# Tests + lint + typecheck
python -m unittest discover -s tests && ruff check . && mypy scraper

# Start API
cd ../api && ../venv/bin/uvicorn api.main:app --port 8000

# Start frontend (separate terminal)
cd ../web && npm run dev -- --port 5173

# Demo is now at http://localhost:5173
# API docs at http://localhost:8000/docs
```

## Architecture

- **Scraper**: Python, Playwright, requests, BeautifulSoup, SQLAlchemy
- **API**: Python, FastAPI, SQLAlchemy, Pydantic
- **Frontend**: SvelteKit (TypeScript, Svelte 5, Tailwind CSS)
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Repo**: github.com/joshieyu/asoundjob

### Key directories
- `scraper/scraper/` — scraper package (models, normalizer, pipeline, ATS parsers)
- `scraper/scraper/normalizer.py` — **THE most important file**: category keywords,
  relevance scoring, seniority detection, job type parsing, salary parsing
- `scraper/scraper/scrapers/ats/` — ATS parsers (greenhouse, lever, workable, ashby,
  smartrecruiters, recruitee, bamboohr, workday, pinpoint, apple)
- `scraper/scraper/scrapers/ats_discovery.py` — detects ATS embeds in HTML
- `scraper/scraper/scrapers/pipeline.py` — fallback chain: ATS → HTTP → Playwright → stealth
- `data/audio_companies_final.json` — 1,385 companies (seed truth, never modify from scraper)
- `data/audio_job_categories.json` — 17 job categories (source of truth for categories)
- `api/api/` — FastAPI app (routers: jobs, companies, categories, admin, search, resources)
- `web/src/` — SvelteKit frontend

### Database
- `asoundjob.db` (SQLite, gitignored) — lives in repo root
- Tables: companies, jobs, job_submissions, scrape_log, career_resources
- Companies have: `ats_type`, `ats_slug` (discovered ATS routing), `audio_scope`
  (native/partial/all — affects relevance threshold)
- Jobs have: `job_categories` (JSON array of category IDs), `is_audio_related`
  (bool — only true jobs show on public board), `relevance_score`, `seniority`,
  `salary_min/max/currency`, `job_type`

## Current State (as of 2026-08-28)

### What works
- 10 ATS parsers covering 64 companies, all scraping successfully
- ATS discovery system detects hidden ATS embeds in HTML, persists for next cycle
- JSON-LD JobPosting extraction on generic pages
- Apple scraper (parses embedded hydration data, 231 audio jobs)
- Deduplication: shared careers URLs only scraped once (inMusic 9 labels → 1 fetch)
- Community job submission form with admin approval queue
- Full SvelteKit frontend with filter sidebar, job detail pages, SEO/JSON-LD
- YAP branding: "ASoundJob" + "by Young Audio Professionals" (mono font) + logo

### Current metrics (partial scrape — 64 of 739 verified companies)
- 3,816 total active jobs in DB
- 406 audio-related (after stricter relevance gating)
- 54 contributing companies
- 94 audio-related jobs have NO categories (need keyword improvement)
- 43 audio-related jobs have NO descriptions

### Category distribution (406 audio-related jobs)
| Category | Count |
|---|---|
| sales_marketing_cs | 99 |
| audio_software | 88 |
| audio_dsp_embedded | 80 |
| audio_aiml | 63 |
| audio_ee | 20 |
| music_technology | 20 |
| transducers | 13 |
| audio_systems | 12 |
| audio_research | 11 |
| game_audio_interactive | 4 |
| live_sound_events | 3 |
| sound_design | 1 |
| psychoacoustics_perception | 1 |
| microphones_recording | 1 |

## Pain Points Still to Fix

### 1. Category parsing still has false positives/negatives (HIGHEST PRIORITY)

The categorization system in `scraper/normalizer.py` uses keyword matching
against title + description. It has been improved with exclusivity rules
(title-matched categories dominate description-only categories), but issues remain:

**94 audio-related jobs have NO categories at all.** These are jobs that
passed the relevance filter (have audio signals) but didn't match any category
keywords. The keyword lists in `CATEGORY_KEYWORDS` need expansion to cover
more job titles and description patterns. To find these jobs:

```python
# Find audio-related jobs with no categories
from scraper.database import get_session_factory
from scraper.models import Job
from sqlalchemy import select
factory = get_session_factory()
with factory() as session:
    jobs = session.execute(
        select(Job).where(Job.is_active == True, Job.is_audio_related == True)
    ).scalars().all()
    no_cats = [j for j in jobs if not (j.job_categories or [])]
    for j in no_cats[:20]:
        print(f'{j.title} | desc={bool(j.description)}')
```

**Some categories are over/under-assigned.** The `sales_marketing_cs` category
has 99 jobs — some may be false positives where generic commercial roles
at audio companies match. The `microphones_recording` and `transducers`
categories are very low (1 and 13) — likely under-assigned because keywords
are too narrow. Review by sampling jobs per category:

```python
# Sample jobs per category
for cat_id in ['transducers', 'microphones_recording', 'sales_marketing_cs']:
    jobs_in_cat = [j for j in jobs if cat_id in (j.job_categories or [])]
    print(f'\n{cat_id}: {len(jobs_in_cat)} jobs')
    for j in jobs_in_cat[:5]:
        print(f'  {j.title} | cats={j.job_categories}')
```

**The exclusivity rules in `CATEGORY_DOMINANCE` may need tuning.** When a
title matches multiple categories, the dominance rules decide which
description-only categories get suppressed. If a legitimate secondary
category is being suppressed, jobs lose accurate categorization. Review
by checking jobs that have only 1 category when they should have 2+.

### 2. Full scrape not yet run

Only 64 ATS-matchable companies have been scraped. The remaining ~675 verified
companies need HTTP/Playwright fallback scraping, which is much slower. A full
scrape would:
- Increase contributing companies toward the 450 target
- Surface more jobs in under-represented categories (live_sound, nvh, etc.)
- Take 10+ minutes (Playwright is ~5s per company at concurrency 5)

```bash
# Full scrape (long-running)
python -m scraper.main --once --skip-load
# Then re-score
python -m scraper.backfill_relevance
```

### 3. `audio_systems` category is inherently fuzzy

"Audio systems" is a catch-all for integration/tuning/measurement roles.
It's hard to distinguish from `transducers` or `audio_dsp_embedded` without
being too generic. The current keywords have been pruned hard (101 → 12 jobs)
to avoid false positives, but may now be under-catching legitimate systems
roles. The right fix is probably more nuanced keyword matching (e.g.
requiring 2+ system-level keywords instead of 1 to assign the category).

### 4. Relevance scoring is strict but may be over-filtering

The current scoring requires actual audio signals in title/description/categories.
This correctly filters non-audio jobs (McGill lecturer, RingCentral network
engineer), but may also filter legitimate audio jobs that have generic titles
and no descriptions (2,588 jobs have no descriptions from the generic scraper).
A full scrape with descriptions (from ATS parsers) would help, but the
generic scraper still only gets titles + URLs for many companies.

### 5. Frontend polish needed

- The homepage "specialties" stat shows 17 (from API) but the homepage
  `topCategories` list only shows 10 in the specialty chips
- Some categories with 0 jobs (automotive_audio, nvh, music_production_recording)
  show in the filter dropdown with "(0)" — could be hidden or shown as disabled
- The job detail page category badges link to `/jobs?category={id}` which works
  but shows the raw category name in the filter chip instead of friendly name
  (this WAS fixed but verify it still works after latest changes)

## Conventions

- No code comments unless explicitly requested
- Use `pyproject.toml` not `setup.py`
- Use ruff for linting, mypy for type checking (both must pass)
- SQLAlchemy 2.0 typed declarative style
- `from __future__ import annotations` (Python 3.9 compat)
- Commit per phase, push per group
- `data/audio_companies_final.json` is seed truth — never modify from scraper
- Manual entries (`source='manual'`) never overwritten by loader
- Playwright concurrency ≤5, HTTP ≤50
- ATS JSON APIs set `trust_empty=True` (empty result = company has no jobs)
- Generic scrapers never set `trust_empty` (empty result might be parse failure)
- Job deactivation only on confirmed successful fetch (never on 403/timeout)
- Community submissions never re-scraped, auto-expire after 30 days
- Shared careers URLs: only first company scraped, duplicates deactivated

## Key Files to Know

| File | Purpose |
|---|---|
| `scraper/scraper/normalizer.py` | Category keywords, scoring, seniority, job type, salary |
| `scraper/scraper/scrapers/pipeline.py` | Fallback chain, ATS routing, discovery |
| `scraper/scraper/scrapers/ats_discovery.py` | Detects ATS embeds in HTML |
| `scraper/scraper/main.py` | Orchestrator, dedup by shared URL, persist |
| `scraper/scraper/backfill_relevance.py` | Re-score all jobs after changes |
| `data/audio_job_categories.json` | 17 category definitions (source of truth) |
| `api/api/query.py` | Job filtering logic, `is_audio_related` default filter |
| `api/api/routers/categories.py` | API endpoint for categories + counts |
| `web/src/routes/jobs/+page.svelte` | Job board filter UI |
| `web/src/routes/+page.svelte` | Homepage with specialty links |
| `web/src/lib/components/Header.svelte` | Logo/branding |
| `web/src/lib/components/JobStrip.svelte` | Job card with category badges |
