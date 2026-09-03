# ASoundJob — Handoff Brief

## Project

> **Read this first.** The document is chronological and some early sections are
> explicitly marked SUPERSEDED. For the current picture read, in this order:
> "Session update (2026-08-31)", "Session update (2026-08-30)", "Session update
> (2026-08-29, night)", "Session update (2026-08-29, late)", "Session update
> (2026-08-29, evening)" and the final "Next steps, in priority order (as of
> 2026-08-31)". Earlier "Next steps" sections are a record of
> completed work and rejected experiments — valuable for the reasoning and the
> DO-NOT-REPEAT entries, but not a to-do list. "Conventions" and "Key Files to
> Know" are always current.
>
> **The board is current as of 2026-08-31.** Live: the Test, Measurement & QA
> category, country filtering, and the Workday/`<base href>` link repairs.
> Board is 470 with 0 known-broken links. Read
> "Session update (2026-08-29, night)" for the numbers that supersede the
> metrics table.
>
> **The audience is audio engineers.** DSP, audio systems, EE, embedded and
> acoustics roles are the point; live sound and sound design are not the
> priority. An earlier version of this document assumed otherwise.

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

# What would this careers URL give the board? (read-only, writes nothing)
python -m scraper.check_url "https://job-boards.greenhouse.io/acme" --name "Acme"

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
  smartrecruiters, recruitee, bamboohr, workday, pinpoint, apple, icims, adp)
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

## Current State (as of 2026-08-28) — SUPERSEDED

> **This section and "Pain Points Still to Fix" below are the original brief and
> are now out of date.** They predate the full scrapes and describe a 64-company
> partial scrape, 406 audio-related jobs, 17 categories and "full scrape not yet
> run". Read "Session update (2026-08-29)" for the current picture; these are
> kept only for the original diagnosis and intent. **"Conventions" and "Key
> Files to Know" further down are still current.**

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

## Pain Points Still to Fix (2026-08-28) — SUPERSEDED, see session update

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
| `data/audio_job_categories.json` | 21 category definitions (source of truth) |
| `scraper/scraper/countries.py` | Location string -> ISO country code |
| `api/api/routers/countries.py` | Country list + counts for the board filter |
| `scraper/scraper/diagnose_failures.py` | Read-only: why a careers page yields no jobs |
| `scraper/scraper/discover_careers_urls.py` | Read-only: proposes corrected careers URLs |
| `scraper/scraper/check_url.py` | Read-only: what a candidate careers URL would yield |
| `scraper/scraper/scrapers/ats/icims.py` | iCIMS; listings only exist under `in_iframe=1` |
| `scraper/scraper/scrapers/ats/adp.py` | ADP WorkforceNow; public JSON API keyed on `cid` |
| `api/api/query.py` | Job filtering logic, `is_audio_related` default filter |
| `api/api/routers/categories.py` | API endpoint for categories + counts |
| `web/src/routes/jobs/+page.svelte` | Job board filter UI |
| `web/src/routes/+page.svelte` | Homepage with specialty links |
| `web/src/lib/components/Header.svelte` | Logo/branding |
| `web/src/lib/components/JobStrip.svelte` | Job card with category badges |

---

# Session update (2026-08-29) — categorization rewrite

PR: https://github.com/joshieyu/asoundjob/pull/1 (branch `improve-categorization-and-parsing`, 5 commits, open)

## Current metrics (after the 2026-08-29 evening full scrape) — SUPERSEDED

> Superseded by the table in "Session update (2026-08-29, night)". Kept for the
> reasoning underneath it, which is still current.

| Metric | Value |
|---|---|
| Total job rows | 7,363 |
| Active | 4,207 |
| Audio-related (the public board) | 390 |
| Board jobs carrying a real description | 333 (85%) |
| Uncategorized audio jobs | 104 (27%) — see the trade below |
| Companies appearing on the board | 64 |
| Companies contributing active jobs | 380 |
| Tests | 389 pass; ruff, mypy, `npm run check` clean |

**These predate the HTTP-scraper consistency fix (647b721).** The next full
scrape will move roughly 101 companies from "success with zero jobs" to failed
and lengthen the run, because more of them reach Playwright. No jobs are lost.

The board reads 385 against an earlier 340, and the 340 counted duplicates that
are now collapsed, so the like-for-like gain is larger than it looks.
Description coverage rose 80% -> 85%. The uncategorized share rose 21% -> 27%
as a deliberate trade in favour of recall; see the section on it below. **The duplicate rows described in the paragraph below are
now collapsed** — Apple/Beats, TrueFire and the Sega trio no longer double-count.

Two consecutive full scrapes were needed: the first discovers or corrects
`ats_type`, the second routes through the ATS parser and gets descriptions.
Workday routes went 17 to 25 between the runs.

**Duplicate rows are still stored and clear on the next full scrape.**
Apple and Beats by Dre both scraped the same Apple board through different URLs
(137 duplicate board entries); TrueFire served Toyota's board; Creative Assembly
and Sports Interactive each hold a copy of Sega's 25 jobs, because a
single-company run bypasses deduplication. Board-identity deduplication
(commit 828fa48) collapses all of these on the next full run. The 340 figure
already excludes them; the raw stored count is higher.

The like-for-like progression this session is **291 -> 322 -> 340**.

At 0: `game_audio_interactive`, `psychoacoustics_perception`.

## What the board size is actually limited by

Not scoring strictness. **Most excluded jobs have no description at all.** The
ATS parsers return full descriptions; the generic HTTP/Playwright path returns
titles and URLs only. With no description the only signal is the title, so a job
is excluded unless its title literally contains an audio word. This is why only
64 of 380 contributing companies reach the board — in practice the board is the
ATS-covered companies plus anyone whose titles say "audio".

That is the argument for writing ATS parsers over improving generic extraction,
and it held up: icims and adp (commit a4944e2) added 87 jobs at 100% description
coverage, and the Lever `lists` fix (8eb7f54) raised existing Lever descriptions
from ~1,300 characters to 4,500-9,600.

Last full scrape: 698 companies, 434 ok, 264 failed, almost all with "page loaded
but no job links found". Sampling 35 of those failures and comparing the old vs
new extractor showed only one recovered, so those pages genuinely yield nothing
to HTML anchor scraping.

## DO NOT REPEAT: the reverted company-nativeness experiment

To recover technical roles at audio companies with generic titles ("Firmware
Engineer" @ Blue Microphones, "Embedded Software Engineer II" @ Audix), a
`NATIVE_TECHNICAL_BONUS` was added to `score_relevance` — a flat score bonus for
native-scope companies whose title matched a TECHNICAL_ROLE pattern. **It was
tried, measured, and reverted.** Two variants, both bad:

1. Broad TECHNICAL_ROLE regex (included data/analyst/design/ai/ml): 646
   audio-related, **463 uncategorized**.
2. Narrowed regex + requiring 2+ audio mentions in the full (unstripped)
   description: 401 audio-related, **218 uncategorized**, and it readmitted
   Take-Two's Spark data engineer while still missing Blue Microphones.

Root cause: a blanket per-company bonus cannot distinguish "audio company doing
audio work" from "audio company doing generic engineering", because ~739
companies are native scope including Sky Studios and RingCentral. Do not retry
this shape. The correct fix is company-category threading (below).

## Next steps, in order

### 1. Company-category threading — DONE (commit 2407b62)

`classify_categories(title, description, company_category=None)`. Fires only
when keyword matching returns nothing, so it cannot reopen boilerplate false
positives. Threaded through all 5 call sites.

The shape that works: **the company category gates whether the role counts as
audio work; the role title decides which category.** Mapping a company category
straight to a job category (as originally sketched below) was measured and
rejected — it labelled every SSL test engineer `live_sound_events` and every
Suno platform engineer `audio_aiml`.

Gate is restricted to manufacturers whose entire product is audio:
Professional Audio & Live Sound, Headphones & Personal Audio, Hi-Fi & Consumer
Speakers, Transducer & Driver Manufacturers, Electronic Musical Instruments,
DJ Equipment, Car Audio, Audio Interfaces & Converters, Hearing Aid & Hearing
Tech, Audio Plugins & Virtual Instruments, DAW & Music Production Software,
Audio Middleware & SDK, Smart Home & IoT Audio. Three of those also contribute
a domain category (Car Audio -> `automotive_audio`, Hearing Aid ->
`audiology_hearing`, instruments/DJ -> `music_technology`).

**DO NOT add the broad categories to the gate.** Measured against the live
corpus, the first draft included them and admitted 125 jobs at roughly 50%
precision: Valve's Steam engineer and Niantic's Pokemon GO team
(Gaming, VR & Immersive Audio), Suno's Trust & Safety and Hugging Face's Xet
Storage engineers (AI/ML Audio), Cisco Webex RTL design and Otter.ai search
(Voice & Speech Technology), Sky Studios' software engineer and Warner
Chappell's distribution team (Recording Studios & Post Houses), and DLR Group's
building services engineers (Acoustic Consulting & Engineering). Restricting
the gate cut it to 32 admitted at near-100% precision.

Software roles are only allowed where the company's product is software
(plugins, DAWs, middleware, instruments). At hardware companies a
"Senior Software Engineer" is ambiguous (Bose mobile apps, Razer's Golang
roles), so hardware categories accept only hardware-flavoured titles.

Result on the active corpus: **259 -> 291 audio-related, 61 -> 58
uncategorized.** `music_technology` (4) and `automotive_audio` (1) are off
zero; `game_audio_interactive` and `psychoacoustics_perception` remain at 0 by
design. Recovers exactly the roles this was built for — Audix and Blue
Microphones firmware/EE/mechanical, Teenage Engineering's mechanical engineer,
Elektron's firmware engineer, Shure's embedded systems engineer, SSL's test
engineers, Kicker's electrical design engineer.


### 2. Diagnose the hard failures — DONE (commits 57c9e5e, 22a9297, 3d4f58d)

Tool: `scraper/scraper/diagnose_failures.py`, read-only. Probes each failing
careers page with Playwright, capturing rendered HTML, navigation status,
outbound links and job-shaped XHR responses, then classifies the page.
Classification is pure and unit-tested. `--html-cache DIR` saves every probe;
`--from-cache DIR` reclassifies offline with no network, which is what makes
iterating on the heuristics cheap (a live run is ~9 minutes).

Result over all 279 companies whose most recent scrape failed:

    unknown            59  21.1%    dead_url           23   8.2%
    json_endpoint      41  14.7%    offsite_careers    22   7.9%
    storefront         32  11.5%    no_openings        19   6.8%
    careers_landing    18   6.5%    js_rendered        17   6.1%
    extractor_gap      12   4.3%    blocked            12   4.3%
    ats_discoverable   10   3.6%    ats_unsupported     9   3.2%
    unreachable         5   1.8%

**Trust these numbers only after reading the next paragraph.** The first run
reported 160/279 "blocked" — 154 of which returned HTTP 200. The marker
"cloudflare" matches any site merely served through Cloudflare's CDN and
"captcha" matches any embedded reCAPTCHA widget. "wp-content/plugins" likewise
labelled every WordPress site a JS app, and cookie-consent JSON counted as a job
endpoint. All fixed. The lesson generalises: **a marker that names a vendor is
not evidence of that vendor's behaviour.** Require interstitial-specific
markers on a small page.

#### The cheapest win: run ATS discovery on failure

`pipeline._try_discovery` is only called when `result.success`. A page that
loads fine but defeats link extraction never gets its `ats_type` recorded, so it
fails identically on every future run. **10 of the 279 embed an ATS the project
already parses** and would yield full descriptions immediately: Audinate and
Stem (lever), Arturia (recruitee), DSP Concepts, Fender Play and Ooma
(greenhouse), Brüel & Kjær, Bonneville, Fisker, Full Sail University (workday).
Call `_try_discovery` on the failure path too, before returning.

A further 9 sit on ATS platforms with no parser: icims and dayforce (2 each),
rippling, personio, teamtailor, oraclecloud, paylocity (1 each) — Pandora
(SiriusXM), Corsair, Rode Microphones, Slate Digital, EarthQuaker Devices,
Natus Medical, Navistar, Pelican Cases. icims and dayforce first if anyone
builds more parsers.

#### What this means for detail-page fetching (#3 below)

The diagnostic reframes it. `careers_landing` (18) plus a large share of
`unknown` are overview pages whose listings sit one click deeper, so the generic
path needs a **follow-one-link step before it needs detail-page fetching** — a
page with no listings to enrich gains nothing from per-job enrichment. Build the
one-level-deep follow first and re-measure.

`storefront` (32), `offsite_careers` (22), `dead_url` (23) and `unreachable` (5)
are **82 companies with bad seed data, not scraper limitations** — the URL
points at a product page, a marketing campaign, a 404, or a board that lives on
another host entirely. No amount of scraper work fixes these; they need seed URL
corrections. This is the single largest actionable group and by far the cheapest
per company.

`extractor_gap` (12) are pages where extraction now finds links but the stored
failure says none: Songtradr, Audio Ltd, THX, Wheatstone, Bandcamp, Cadence,
Epic Games, Allen & Heath, Genius and others. These predate the
`link_extraction.py` fixes — they should simply succeed on the next full scrape.


### 3. Follow-one-link — MEASURED AND REJECTED (do not build)

After the two full scrapes the diagnostic was re-run over the 278 still-failing
companies. Buckets were essentially unchanged, which is the expected result:
this session's fixes helped companies that were already succeeding but
returning too little, not the hard failures.

    unknown         58   json_endpoint  42   storefront       32
    offsite_careers 23   dead_url       23   no_openings      19
    careers_landing 18   js_rendered    17   blocked          13
    extractor_gap   12   ats_unsupported 9   ats_discoverable  7
    unreachable      5

The plan was to follow one link from a careers overview page to its listing
page, on the theory that discovery would then see an ATS embed and the company
would convert to full descriptions — the same mechanism that took Bose from 13
title-only jobs to 40 with descriptions.

**The theory is wrong.** Of the 125 pages in the target buckets
(careers_landing, unknown, js_rendered, storefront) only 25 have a followable
link at all. Fetching all 25:

    a supported ATS embed :  0
    job links, no ATS     :  7
    still nothing         : 18

and 3 of the 7 are the same Sega board reached from Creative Assembly, Sega and
Sports Interactive, which board-identity dedup would collapse anyway. Net yield
is about two distinct boards. Not worth building. The measurement script is
`followlink.py`; re-run it against a fresh cache before revisiting.

### 3b. Seed URL quality is the dominant remaining lever

Bigger than the 82-company figure suggests, because it is not limited to
companies that fail. **BMG Production Music's careers_url points at
`careers.smartrecruiters.com/Bertelsmann-Jobs`** — the whole parent
conglomerate. It scrapes 954 jobs of warehouse, SAP and logistics roles, which
is 19% of every active row in the database. Relevance scoring correctly keeps
all but 3 off the board, so the damage is wasted effort and a misleading active
count rather than a polluted board. TrueFire serving Toyota's board was the
same class of problem.

So the work is two-sided: correcting URLs for companies that yield nothing, and
finding companies that "succeed" against the wrong board. The second kind is
detectable — an outlier job count against company size, or a board identity
whose slug bears no relation to the company name.

Proposed approach: generate candidate URLs per company (`/careers`, `/jobs`,
`/about/careers`, any ATS host linked from the page), fetch each, score whether
it yields real job links, and emit a ranked shortlist for human approval.
Corrections belong in `data/audio_companies_final.json`, which is seed truth
and must never be written by the scraper.

### 3c. Detail-page fetching — population is smaller than it looks

3,215 active jobs carry no real description across 309 companies. But 954 are
the Bertelsmann mis-seed above, and roughly 300 more are Workday companies at
partial scope, where `_fetch_descriptions` deliberately fetches details only for
titles already matching an audio pattern. Re-measure the true target after the
seed URLs are corrected, not before.

### 3d. 646 companies have never been scraped

`_load_companies` selects `Company.verified.is_(True)`, and 646 of the 1,386
companies are unverified — 47% of the database, never scraped once. They all
carry a careers_url, almost all of the form `{domain}/careers`, which suggests
the URLs were generated by convention rather than checked.

Sampling 60 of them confirms it:

    careers_url reachable          2 (3%)   of which 1 yielded job links
    http error (mostly 404)       40 (67%)
    dns / connection failure      10 (17%)
    ssl failure                    7 (12%)

**96% of the seeded careers URLs are dead.** The `verified` flag is doing its
job; these were correctly excluded.

The companies, however, are mostly real. Testing the root domains of the same
60: **36 (60%) return HTTP 200** — a live company site with a fabricated
`/careers` path. Among them Electronic Arts, Libratone, Westone Audio, Eighteen
Sound, Audax, Roger Linn Design, The Village Studios. Extrapolated, roughly 390
real companies are sitting unscraped behind a bad URL.

So this is not a verification task, it is a rediscovery task, and it is the
same machinery as 3b: generate candidate URLs, fetch, score, shortlist for
human approval. The population is simply five times larger than the 82 failing
verified companies.

Temper the expectation: coverage will improve more than job count. Many of
these are small firms with no current openings. The board currently shows 57
companies, so the coverage gain is the point.

### 3e. Careers URL rediscovery tool — BUILT (commits 662889c..e4b8652)

`scraper/scraper/discover_careers_urls.py`. Read-only; proposes a corrected
careers_url per company with evidence and writes a review markdown for a human.
It never touches the database or `data/audio_companies_final.json`.

    python -m scraper.discover_careers_urls --population both \
        --output-json careers_url_proposals.json \
        --output-review careers_url_proposals.md

Candidates are tried in yield order: current URL, links harvested from the
company home page, ATS board URLs built from plausible slugs, guessed paths
last. Guessed paths were the original strategy and are worthless — every guess
404s.

**Result over 922 companies: 13 actionable proposals.** 250 domain dead, 334
live sites with no careers link anywhere on them, 86 blocked, 160 already
pointing at the best URL found. The population is mostly companies that do not
publish jobs, not companies we are failing to reach.

#### The lesson: a signal is only evidence in context

This tool produced four rounds of plausible-looking garbage — 532 proposals,
then 27, then 13 — and every round failed the same way, by treating a signal as
evidence without asking how it was obtained. All four are now guarded by tests.

1. **Recruitee 301s any nonexistent subdomain** to its marketing page, which
   reads as a recruitee board with six job links, scores 84 and short-circuits.
   Guard: reject a candidate when a redirect drops the identity token requested
   (`8x8.recruitee.com` -> `recruitee.com`), while allowing
   `boards.greenhouse.io/acme` -> `job-boards.greenhouse.io/acme`.
2. **Ashby answers 200 with careers vocabulary for any slug**, and Workable's
   unknown-slug page carries Workable branding that `discover()` reads as a
   workable embed. This produced 436 ashby and 42 workable proposals including
   Best Buy, AMD and Bioware. Guard: candidates carry provenance, and a
   **guessed** URL must produce real job links to score at all. An ATS signature
   is evidence only on a page the company actually published.
3. **Home-page harvesting followed off-site links** to news and social sites —
   Zoom was proposed as a fortune.com article, scoring high because the page
   mentions Workday. Guard: a noise-host denylist. Off-site links are still
   allowed, since Audison's real board is at its parent Elettromedia.
4. **Slugs derived from a third-party careers_url.** Powersoft is seeded with a
   LinkedIn page, so the slug became "linkedin" and the tool proposed
   `jobs.lever.co/linkedin` — LinkedIn's own board, real, six jobs, high
   confidence. Guard: never derive a slug from a noise host.

Also: careers vocabulary alone is not evidence. A proposal now requires an ATS
signature or real job links, which removed fifteen matches that were a Discord
invite, a Telegram group, four affiliate signup pages, a Patreon and a mailing
list.

#### Corrections applied (commit 319ca7c)

Eleven URLs corrected in the seed file. Five companies (Vonage, BYD, Integra,
Acer, Audison) were also `verified: false` and were flipped — the scraper only
queries verified rows, so the URL change alone would have done nothing.

Scraping the nine boards found two things the tool could not see:

- **Sega, Creative Assembly and Sports Interactive were pinned to
  `scrape_method: "playwright"`**, which makes the pipeline skip the HTTP path,
  and the HTTP path is where all 25 jobs are. Set to `http`. **When a page loads
  but yields nothing, check `scrape_method` before blaming extraction.**
- **Genius was a bad proposal.** `genius.com/jobs` is a landing page whose only
  "job link" is labelled "our open roles". Real board:
  `job-boards.greenhouse.io/geniusjobs`.

Yield: 173 jobs across nine companies, 18 audio-related. Vonage, BYD, Integra,
Brain.fm and Genius arrive through ATS parsers with full descriptions.

Still needing a manual careers URL: **Powersoft** and **Cross DJ (Mixvibes)**,
both seeded with a LinkedIn company page.

### Smaller known issues

- Native Instruments' 5 "jobs" are language-switcher links (Deutsch, Espanol,
  Francais, ...) — single short words that slip past the furniture rules.
- Korg's entire board is Japanese (電子設計, 機構設計, 生産技術). All keyword lists
  are English-only, so these can never match. Same for other non-English boards.
- `music_technology` is 0 because no job in the corpus has music-tech vocabulary
  in its title; the one that does is "High-End Guitar Sales Expert" at a
  retailer. Widening keywords will not help — the text isn't there.

## Regression to remember

**A discovered `ats_type` is written once and never corrected.**
`_persist_ats_discovery` guards with `where(Company.ats_type.is_(None))`, and
every ATS parser prefers `company.ats_slug` over re-deriving it from the URL. So
a wrong slug is permanent: the company routes to a parser that 404s, falls
through to the generic path, and is never re-discovered. Verify slug extraction
against real pages before any change that causes discovery to run on more of
them. Discovery on the failure path (commit 9303f43) exposed three such bugs at
once — greenhouse's `/js?for=` embed, workday's tenant-in-host, and a recruitee
analytics subdomain (commit b15721c).

**This now self-heals (commit 50c8e2e), but only under two conditions:** the
stored route was tried and failed in this run, and a fresh discovery from the
page disagrees with the stored value. A transient ATS outage therefore cannot
clobber a good slug, and rediscovering the same value writes nothing. What it
cannot repair is a slug that is wrong but still *works* — that would need a
manual database edit. Audit with:

    select name, ats_type, ats_slug from companies where ats_type is not null;

**Workday slugs must read `tenant.wdN/site`** — for example
`boseallaboutme.wd503/Bose_Careers`. A bare segment such as `Bose_Careers`,
`External` or `en` is broken, and so is `tenant/site` without the data centre.
The audit that prompted this found 9 broken rows including all 7 workday ones;
Bose had 13 active jobs and zero descriptions.

The data centre matters and is not derivable (commit 3070091). A Workday tenant
answers only at its own numbered host — Bose is on wd503, Adobe and GoTo on wd5,
Nissan on `alliance.wd3`, Toyota on `toyota.wd503`. Requesting
`boseallaboutme.wd1.myworkdayjobs.com` returns HTTP 422; wd503 returns 200 with
76 jobs. `_build_base` still falls back to wd1 when a slug carries no data
centre, so legacy values resolve to something, fail, and get corrected by
discovery.

End to end on Bose from a cleared `ats_type`: run one discovers
`boseallaboutme.wd503/Bose_Careers`, run two routes through Workday and returns
40 jobs, all 40 with full descriptions, 21 audio-related — against 13
title-only jobs before.


**Never put an unbounded quantifier before a literal in a page-scale regex.**
`ats_discovery.PATTERNS` had four of the form `(?P<slug>[a-z0-9-]+)\.recruitee\.com`.
The engine consumes the run, fails the literal, backs off one character, and
retries from every offset — quadratic in page size. A single inline base64
image took `discover()` **57 seconds**, and it runs on every successful scrape
against a 90s per-company timeout. Bounding the quantifiers to the 63-character
DNS label limit preserves every match and takes the same page to 0.15s
(commit 22a9297). `tests/test_ats_discovery.py` guards it.

Apple's detail fetch nearly shipped a total-failure bug: ~226 detail requests at
~2.8s each vs a 90s `per_company_timeout` would have cancelled the whole scrape
and dropped Apple to zero jobs. Any per-job enrichment MUST be time-bounded.

The full scrape also caught three live-only bugs in `link_extraction.py` that
fixtures missed (query-string job ids, non-English abbreviations, template
placeholders). **Run a full scrape before merging changes to that file.**

## Session update (2026-08-29, evening)

Items 1-4 of the previous priority list are all done. What changed:

**BMG Production Music (was the largest data problem).** It pointed at
`careers.smartrecruiters.com/Bertelsmann-Jobs`, Bertelsmann's entire corporate
board. Verified rather than assumed: all 955 postings were pulled and exactly 3
mention BMG. The reporting units are Arvato (395), Riverty (123), Arvato Systems
(143), RTL and Penguin Random House. BMG's own SmartRecruiters site
(`careers.smartrecruiters.com/BMG`, title "Careers at BMG") exists and currently
has **no open postings**, which is the honest count. The seed now points there.
A SmartRecruiters board with zero postings returns success with `trust_empty`,
so the 951 stale rows deactivated cleanly.

**Powersoft and Cross DJ (Mixvibes)** have no scrapable board at all. Powersoft's
own site links out to LinkedIn as its careers destination, and it is already
`verified: false` so it costs nothing. Mixvibes has no careers page; its LinkedIn
seed produced browse furniture ("Offres d'emploi Analyste 3 411 postes"). Cross
DJ is now `verified: false`.

That exposed a real gap: **demoting a company to unverified left its jobs active
forever**, because the scrape query filters on `verified` and never revisits
them. `company_loader` now deactivates them and reports
`deactivated_unverified`.

### icims and adp parsers — BUILT (commit a4944e2)

The previous list said "icims and dayforce". Two corrections, both from reading
the seed rather than the diagnostic's classifier:

- **There is no dayforce company in the seed at all.**
- **ADP WorkforceNow is the largest unsupported platform at 8 companies**, not
  icims at 3. It covers Meyer Sound and IAC Acoustics.

**Why iCIMS boards were failing.** The careers page is an empty shell: every
listing lives in an iframe and only appears under `in_iframe=1`. Without it the
page yields zero job links, which is exactly the "page loaded but no job links
found" error these companies logged. Listings are at
`https://{slug}.icims.com/jobs/search?ss=1&in_iframe=1&pr={page}`, 20 per page.
Job links may point at a **different subdomain** than the one requested
(`careershub-shure` returns links on `careers-shure`); use the href as given.
Detail pages carry JSON-LD, so `extract_jsonld_jobs` supplies descriptions.

**ADP** serves a public JSON API needing no auth, keyed on the `cid` GUID from
the careers URL's query string, with `requisitionDescription` on the per-job
endpoint. A bogus cid 404s and a real empty board returns
`{"jobRequisitions":[]}`, so empty is distinguishable from broken. ADP truncates
`requisitionTitle` to ~45 characters; that is a platform limit, not a bug.

Measured live: Shure 64 jobs / 64 descriptions, IAC Acoustics 19/19, Meyer Sound
4/4, Harley-Davidson 5/5, LiveWire 5/5, Triumph 4/4. HTC Vive's board is
genuinely empty and returns cleanly. **Keysight has migrated off iCIMS** — its
board answers with a 142-byte script redirecting to `jobs.keysight.com`, which
runs iCIMS's Jibe product; its API at `/api/jobs?page=1&limit=N` returns titles
and full descriptions inline, so a `jibe` parser is feasible if more companies
turn up on it. The seed now points at the new board.

**An unrecognised iCIMS page must not look like an empty board.** Zero parsed
links returns success with `trust_empty`, which would deactivate every job the
company has — a markup change would have silently wiped all 64 Shure rows and
looked like a clean run. Page 0 now demands an explicit empty-board marker or
raises. Apply the same reasoning to any future HTML-scraping ATS parser.

### The precision bug the descriptions exposed (commits c7e70d8, cc63fc6)

Giving Shure real descriptions put **60 of its 64 jobs on the board**, including
Senior Credit Collections Specialist, Buyer I Tactical, Auditor Incoming
Inspection and Associate Director Trade Compliance.

Every one scored exactly 45:

    title (no audio word)  +0
    description mentions   +35
    native scope bonus     +10
    ---------------------------
                            45   = the native threshold

The +15 threshold bump for a title with no audio signal was explicitly waived
for native scope, so **company boilerplate alone was sufficient** — Shure's
blurb mentions microphones in every posting. It stayed hidden for as long as
those companies produced title-only rows, which score zero.

**The project's stated preference is recall over precision:** a junk listing a
reader skips past in a second is cheaper than a real job that never appears.
Two candidate fixes were measured against the live board and both rejected:

- Raising the native threshold dropped 135 of 391 rows, 74 of them real,
  including Electrical Engineer at Audix and Senior PCB Layout Designer at
  Lectrosonics. At a microphone company those *are* audio jobs.
- Requiring a category or a title signal (the first attempt, c7e70d8) dropped
  61. Only a minority were junk — Senior Systems Engineer at Bose, Sr. NPI
  Engineer, Metrology and Process Engineer at Shure, Field Sales Engineer at
  Brüel & Kjær all belong on the board.

The lever that worked is **`CORPORATE_ROLE`**, which already exists to demote
corporate-function titles and carries a -70 penalty. It gained credit
collections, trade compliance, customs broker, buyer, incoming inspection,
incoming auditor and incentive plan. Every term was checked against the live
board first: **zero currently-listed jobs lost their place.**

Terms were deliberately left out where the role is arguable rather than clearly
non-audio — demand generation, marketing operations, sales development, market
development and event management would each have cost real listings. Three
Demand Generation roles at WellSaid, Otter.ai and Deepgram sit on the board
under `sales_marketing_cs`, and event management at a pro-audio company can mean
live sound. **When extending `CORPORATE_ROLE`, measure the collateral against
the live board before committing; the bar is zero legitimate losses.**

Two tests in `test_relevance.py` pin both directions so this cannot drift:
back-office titles stay out, technical titles carried only by company context
stay in.

### Uncategorized is now 27%, and that is the accepted trade

All 55 restored rows lack categories, which is the entire 15% -> 27% move; no
categorization logic changed. Categories are how a reader filters past the junk,
so closing this gap is worthwhile — but note that **a large share of the 105 is
a pre-existing keyword gap, not a consequence of the recall change**: "Embedded
Software Engineer, Audio & Media Tech" at Apple, "Applications Engineer:
Acoustics" at Comsol, "Senior Applied Scientist, Speech" at Otter.ai and
"Project Manager - Audio Technology" at Focusrite all carry an obvious audio
word and still match nothing. That is the original pain point #1 and it is
independent of scoring.

For the restored Shure roles specifically, the lever is
`FALLBACK_ROLE_CATEGORIES` — it has no pattern for `systems`, `process`,
`metrology`, `npi` or `maintenance`, so those titles fall through even though
the company gate admits them.

**Title anchoring (commit cbe38fc) closed part of this.** A weak keyword in the
title scored 3 against a cutoff of 5, so a title naming its own category via a
weak term got nothing — Apple's "Embedded Software Engineer, Audio & Media
Technologies" and Otter.ai's "Senior Applied Scientist, Speech" both sat
uncategorized. `AUDIO_ANCHOR` already existed for exactly this but was only
applied to description text. A weak title keyword now scores 6 when the title
also names audio. Six rows gained categories, three gained a missing second,
none lost any.

**Do not extend that past `ANCHORED_CATEGORIES`** — it was measured and
rejected. `audio_systems` has weak keywords generic enough that any "Audio
Technology" title matches, which turned "Sr. Director of Finance, Audio
Technology" into an `audio_systems` role. A test pins this.

**RESOLVED 2026-09-02 (commit 4cabea3): bare "acoustics" belongs to
`audio_systems`.** The owner made the call. Previously every acoustics keyword
in the file was a multi-word phrase ("acoustic engineer", "room acoustics"), so
"Applications Engineer: Acoustics" at Comsol and "Working Student Acoustics" at
Neumann scored zero everywhere. Longer keywords sort first within a category, so
`acoustics_consulting` still wins "room acoustics" and "building acoustics" — a
test pins that.

### Step 1 of the seed plan: the proposal tool found almost nothing

`discover_careers_urls.py --population failing` over 267 companies produced
**one** replace proposal, and it was wrong (York's student careers service).
The guards added earlier — requiring an ATS signature or real job links — are
strict enough that this population yields nothing automatable. **The 82 in
SEED_WORKLIST.md need human research; there is no tool shortcut.** Do not
re-run it against this population expecting a different answer.

Its `domain_dead` bucket is a false-positive class and must not be acted on.
All seven were checked by hand: Theatre Projects and Spitch return HTTP 200
right now, Audinate returns 403 (bot block, and it has a live Lever board with
7 postings), and DiGiCo, Take-Two, GAC and Equator Sound are TLS failures —
expired certs, name mismatches, and protocol versions this machine's LibreSSL
cannot negotiate. `domain_dead` means *our fetch failed*, not that the company
is gone. Retiring those seven would have removed live companies.

The `ats_discoverable` bucket was worth more. Seven companies embed a supported
ATS; five now scrape directly from a seeded board URL, adding 125 jobs:
Audinate (lever), Fender and Ooma (greenhouse), Full Sail and Bonneville
(workday). Two do not: DSP Concepts still serves `for=dspconcepts` but
Greenhouse 404s that board, so it is deactivated on their side, and Fisker's
Workday returns 422 (the company is defunct). Bonneville runs four regional
Workday sites and the seed can only name one — BonSaltLake was chosen.

**YAP's audience is audio engineers**, so the categories worth filling are
audio_ee (12), audio_research (8), transducers (15), acoustics_consulting (4)
and nvh (2) — not live sound or sound design. The board's engineering half is
its strong half: DSP 48, audio_systems 47, audio_aiml 41, audio_software 29.
`SEED_WORKLIST.md` is ordered on that basis.

### Correcting a careers URL by hand

`SEED_WORKLIST.md` lists the 82, with slugs, ordered by engineering relevance.

Test a candidate before editing anything — this writes nothing:

```bash
cd scraper && source ../venv/bin/activate
python -m scraper.check_url "https://job-boards.greenhouse.io/acme" --name "Acme"
```

It reports the parser that handles the URL, jobs found, how many carry
descriptions, and how many would reach the board. If it prints
`ats discovered: greenhouse/acme`, the page embeds a board — **seed that board
URL directly rather than the company page**, since ATS parsers return full
descriptions and the generic path usually returns titles only.

Then edit `careers_url` in `data/audio_companies_final.json` (or set
`verified: false` if the company has no board at all), and:

```bash
python -m scraper.company_loader
python -m scraper.main --once --skip-load --company acme
```

**A run that fails once may succeed on the second attempt.** When the seeded page
embeds an ATS, the first pass discovers and stores it and the second routes
through the parser. Nothing, Stability AI and Dice FM all behaved this way. Do
not conclude the URL is wrong until the second run fails.

Two traps, both hit in practice: confirm the board belongs to *that* company —
Modal Electronics was pulling Modal Labs' cloud jobs and QSC is seeded with
`acuityinc.com` — and remember a TLS error or a 403 does not mean the site is
dead, since Audinate 403s but has a live Lever board.

### The HTTP scraper used to hide its failures (commit 647b721)

Only `PlaywrightScraper` raised when a page yielded no job links. `HttpScraper`
returned `[]`, which `base.scrape()` counts as success, and the pipeline's
`if result.success: return result` then short-circuited the rest of the chain.
**A JS-rendered page answering HTTP 200 never reached Playwright at all**, and
the company was recorded as a successful scrape holding zero jobs — 101 of them.

Measured before changing anything: Playwright was run by hand against Akustiks,
Connect Hearing, Blaupunkt and Baidu and found nothing on any. **This recovers no
jobs.** It is an observability fix — those companies are now honestly failed and
join the diagnostic's failure population. Expect the success count to fall and
full scrapes to take longer.

### When a company needs an ATS nobody else uses

Calrec Audio is the worked example. Its real careers site is
`careers.calrec.com`, a SPA whose job links are routes (`#/job/details/60`), and
its applications live on `livevacancies.co.uk` — the **hireful** ATS. Neither
HTTP nor Playwright extracts anything, because the extractor only understands
anchors. hireful publishes an `apiServerUrl` of
`http://hg-api.prod.hireful.aws:5250/`, an internal AWS host that does not
resolve publicly, so there is no clean API to target.

**No other company in the seed uses hireful.** A parser would serve one company
with one open role, so none was written. The seed points at the correct URL
anyway: a right URL that yields nothing beats a wrong one, and a future fix to
SPA link extraction picks it up for free.

Generalise this when working `SEED_WORKLIST.md`: if `check_url` reports
`ats discovered: none` **and** zero jobs on a SPA, grep the seed for that ATS
host before building anything. One company is not worth a parser; record the
correct URL and move on.

## Session update (2026-08-29, late) — four company case studies

The owner named four companies they expected to see on the board and did not:
Amplify Labs, Meta, Harman and Google. Diagnosing all four produced one scraper
fix, one categorizer fix, pagination, and four seed corrections.

| Company | Board before | After | What it needed |
|---|---|---|---|
| Amplify Labs | 0 | 2 | extractor fix only |
| Google | 0 | 10 | seed URL, then pagination |
| Harman | 0 | 16 | a company entry that did not exist |
| Meta | 0 | 3 | both, and it is the least reliable |

**The pattern worth remembering: only one of the four was a scraper bug.** The
other three were pointed at marketing landing pages, which scrape *successfully*
and return navigation furniture. Meta's seven rows were "Hiring Process" and
"Career profile"; Google's were a discrimination notice and a privacy link;
three Harman brands held seventeen category filter links each, stored three
times over. **A company reporting `success` with a healthy `jobs_found` can
still hold zero real jobs.** Nothing in the scrape log distinguishes this, and
counting rows will not find it — only reading titles will.

### Titles now come from structure, not flattened anchor text (commit 03a8d00)

Two layouts defeated the generic extractor. Meta nests the title in an `<h3>`
inside the anchor along with location and team chrome, giving 176 characters and
26 words, over both `MAX_TITLE_LEN` and the 12-word furniture rule. Amplify Labs
puts the title in a card `<h5>` and links from a bare "Learn More" button, which
is in `NON_JOB_TEXT` and carries no job hint.

Both now fall back to a heading: inside the anchor first, then in an enclosing
container. The container case only fires when that container holds exactly one
job anchor, which stops a heading being stamped onto every link in a list.
Structural titles are revalidated against the same length, furniture and
`NON_JOB_TEXT` checks as flat text.

Measured old against new over 111 cached careers pages: 498 rows to 518, **no
board job lost**, seven companies changed. Roughly half the gain is real
(Televic Conference 3 -> 13, all genuine postings); the rest is marketing cards
and blog posts that score 0 and never reach the board. Cookie banners were the
one recurring false positive the wider net introduced, so any title mentioning
cookies is now furniture — that also correctly dropped Thornton Tomasetti's sole
row, which was `Career Site Cookie Settings`.

### Pagination (commit 458ebd4) — NOT the rejected follow-one-link

**Do not confuse this with "Follow-one-link — MEASURED AND REJECTED" above.**
That was following a link from a careers overview *to a listing page*, hoping to
reach an ATS embed; it yielded about two distinct boards and remains rejected.
This follows *next-page links within a listing that is already working*, which is
a different mechanism with different evidence.

The evidence: Google's audio search runs to 132 jobs and we were keeping the
first alphabetical twenty. Harman's board is 362. Both expose an ordinary
next-page link.

**The detection rule was built by measurement and the naive version was
dangerous.** A first pass found next-links on 7 of 111 cached pages, but four
were false positives that would have made the crawler misbehave: Cary Audio's
`<link rel=next>` pointed into a WordPress blog archive, Kawasaki's aria-label
matched a photo carousel, Walrus Audio's "More" pointed at the page it was
already on. The shipped rule requires same host, same path, a non-empty query
string, and a URL different from the current page, and **ignores `<link
rel="next">` entirely** because that is the WordPress next-post convention. That
keeps all five genuine paginators and drops all four false positives, leaving 3
of 111 pages paginating — about 3% more requests, not the 10x feared.

Three guards bound the loop: a ten-page cap, a break as soon as a page
contributes no new job URL, and a visited-page set so cycles terminate. ATS
discovery still reads page one, not the last page.

Result: Google yields all **132 unique job ids with zero duplicates**, matching
Google's own counter, and one more board job — an acoustic engineer for
hearables that sat on a later page. Amplify Labs and Harman fit on one page and
take exactly one fetch, unchanged. Note 43 of Google's 175 rows are per-page
navigation furniture; all score 0.

**Meta gains nothing from this.** Its pagination is SPA-driven with no
next-page link in the DOM.

### Inverted audio software titles (commit 4dca4f0)

`CATEGORY_KEYWORDS` expects "audio software engineer". Google inverts it and
trails the domain: "Senior Staff Software Engineer, Audio". Nothing matched, so
those rows reached the board uncategorized. Now a title that reads as software
engineering, carries an audio anchor and matched **no category at all** is filed
`audio_software`. Requiring an empty result is what keeps it safe.

Measured over all 4,207 active rows: **2 newly categorized, 0 re-categorized.**
Both gains genuine. This is a narrow fix, not a solution to the 104 uncategorized
rows — "Supplier Development Engineer, Audio" and "Audio Experiences Lead" are
not software roles and were correctly left alone.

### Meta rate-limits hard, and the GitHub crawler does not help

Probing Meta perhaps eight times in twenty minutes earned a **429 that persisted
for roughly two and a half hours**, across six probes in two independent backoff
runs at 15/30/50 minutes. It eventually cleared. Treat Meta as the least
reliable company on the board and **do not iterate against it quickly.**

The pipeline hit Meta three times per run (http, playwright, stealth) and the
http attempt can only fail, because Meta rejects non-browser requests. Meta's
`scrape_method` is now `playwright`, which sets `skip_http` and cuts that to two.

The owner found `github.com/anon767/maangcrawler`. Its `Crawlers/Meta.py` uses
selenium-wire to load `metacareers.com/jobs/`, sleep 10s, then sniff the
response to `metacareers.com/graphql` and read `data.job_search`. **There is no
secret endpoint, no auth and no callable API — it still loads the page in a
browser, so it does nothing about the 429.** Reproduced with Playwright, which
intercepts responses natively and needs no new dependency: the payload is
`job_search_with_featured_jobs_v2`, carrying clean `id`/`title`/`locations`/
`teams`, and it returns **19 jobs where the DOM renders 10** — but the same 3
board jobs. The extra 9 are non-audio. **Not worth building a Meta-specific
GraphQL parser for zero board gain.** Revisit only if Meta's audio hiring grows
past one rendered page.

### Seed corrections (commits 394b5b7, f5d7778, 1313ab7)

- **Meta** -> `metacareers.com/jobs?q=audio`, `scrape_method: playwright`.
- **Google** -> `.../jobs/results/?q=audio`, `scrape_method: http`. The search
  page is server-rendered and readable over plain HTTP; Playwright is
  unnecessary.
- **Harman added** at `jobsearch.harman.com/en_US/careers/SearchJobs/?search=audio`.
  It had no entry at all — only 13 brands, ten of them pointing at
  `careers.harman.com`, **which does not resolve**. Avature, server-rendered,
  page size capped at 20 server-side. The board is 362 mostly-automotive roles,
  hence the audio query.
- **Bowers & Wilkins, Denon, Marantz** set unverified. They are legitimately
  Harman brands now, but brand-specific searches return nothing and all three
  shared one URL, tripling the same furniture rows.

**Scoping a huge partial-scope employer's seed to a search query is now the
established pattern** for Meta, Google and Harman. Caveat: Harman's search
matches tokens exactly, so `acoustic` and `acoustics` return different sets and
no single query is complete — the true union is 24 against `?search=audio`'s 16.

### The database is behind the code

**Every number in this section is a `check_url` projection, not a board count.**
The six commits changed the extractor, the categorizer and the seed; none of it
reaches the live board until:

```bash
cd scraper && source ../venv/bin/activate
python -m scraper.load_companies      # picks up Harman, the URL changes, the unverified three
python -m scraper.main --all          # long; longer now that pagination follows pages
python -m scraper.backfill_relevance  # re-score after the categorizer change
```

Expect the loader alone to deactivate the Bowers & Wilkins / Denon / Marantz
furniture rows. Expect the scrape to be slower than the last one for two
compounding reasons: commit 647b721 pushes ~101 companies through to Playwright,
and pagination adds pages for ~3% of the generic path.

## Session update (2026-08-29, night) — the scrape landed, and a new category

Two things happened: next-step 0 finally ran, and Test, Measurement & QA was
carved out of `audio_systems`.

### The full scrape ran (no commit — this is database state)

`python -m scraper.main --once` then `python -m scraper.backfill_relevance`.
698 companies, 384 ok, 314 failed, 4,546 jobs found, 1,556s. **Note the command
is `--once`, not the `--all` an earlier version of this document invented, and
the loader module is `scraper.company_loader`, not `scraper.load_companies`.**
The loader inserted Harman, updated five entries and deactivated six unverified.

| Metric | Before | After |
|---|---|---|
| Total job rows | 7,363 | 7,851 |
| Active | 4,207 | 4,693 |
| Audio-related (the public board) | 390 | **468** |
| Board jobs carrying a real description | 333 | 331 |
| Uncategorized board rows | 104 | 105 |
| Companies appearing on the board | 64 | 72 |
| Companies contributing active jobs | 380 | 399 |

**All four late-session case studies landed exactly as projected**: Harman 16,
Google 10, Meta 3, Amplify Labs 2. The projections from `check_url` were
accurate to the job, which is worth knowing next time a decision rests on one.

### Test, Measurement & QA (commits 56afbed, 41f3967)

The owner asked for it: audio measurement and QA roles were filing as
`audio_systems`. Two things were sending them there — measurement vocabulary in
`audio_systems`'s own keyword list, and a rule in `FALLBACK_ROLE_CATEGORIES`
mapping any test/validation/quality/QA title at a hardware company straight to
`audio_systems`. Both now point at `test_measurement_qa`, and that fallback rule
moved to the front of the list, so a title that says QA files as QA rather than
as the domain it happens to test ("Hardware QA Engineer" was `audio_ee`).

Three routes reach the category:

1. **Keywords**, strong and weak, in the new `CATEGORY_KEYWORDS` entry. Strong
   terms are all audio-specific compounds ("acoustic measurement", "anechoic
   chamber", "real ear", "ear simulator", "klippel"). Generic test vocabulary
   ("test engineer", "quality assurance", "metrology", "calibration") is **weak
   only** and the category is in `ANCHORED_CATEGORIES`, so description hits need
   an audio anchor within 200 characters.
2. **The company fallback**, for test-shaped titles at hardware companies.
3. **`_apply_test_override`**, a title-shape regex (`TEST_ROLE_TITLE_RE`) that
   files an already-audio row as test when the title reads as test, QA,
   metrology or verification. It matches the subject and the role word in either
   order, so "Technician II, Metrology" and "Test Engineer" both hit.

**The safety property that matters: the override returns early unless `scored`
is already non-empty.** Categorizing a row adds +35 to its relevance
(`score_relevance`), which is exactly how the rejected `FALLBACK_ROLE_CATEGORIES`
experiment in next-step 4 pulled junk onto the board. Requiring the row to
already be an audio job by other evidence means the override can re-file a row
but can never admit one.

Measured old against new over all 4,196 then-active rows: **35 rows re-filed, 32
of them on the board, `audio_systems` 47 -> 26, zero board jobs gained or
lost.** Live after the scrape and backfill: 34 board rows in the new category,
`audio_systems` down to 30. Bare "Test Engineer" / "QA Engineer" / "Metrology
Technician" with no audio context still score 0 and stay off the board — there
is a test asserting this.

The owner supplied a real listing (contract Acoustic Test Engineer II, wearable
audio, Redmond) as a fixture. It scores 19 against the cutoff of 5, files
`test_measurement_qa` alone, and reaches the board under every scope. It also
exposed lab vocabulary the first pass missed — real ear, insertion gain, ear
simulator, acoustic coupler, acoustic calibrator, measurement microphone — now
in the keyword list. A condensed version of it is the fixture in
`TestMeasurementAndQaCategory.test_measurement_description_carries_a_vague_title`.

**Two judgment calls made without the owner**, both worth revisiting if they
grate: putting the QA fallback rule first (so firmware and hardware QA roles
leave `audio_dsp_embedded` and `audio_ee`), and letting Shure's "Senior
Engineer, IT Quality Assurance" file here — it is IT QA, not audio test, but it
was `audio_systems` before, and it is on the board either way.

One thing deliberately **not** changed: that fixture does not also pick up
`audiology_hearing` despite its real-ear and hearing-device content. It scores 3
against the cutoff of 5. Moving it means touching the shared scoring curve,
which would ripple through every category.

### The About page was showing invented numbers (commit c59b976)

It hardcoded "1,385 companies" and "14 specialty categories". The company count
had drifted and the category count was six short before this branch made it
seven. Both now come from `/api/companies` and `/api/categories` through a new
`web/src/routes/about/+page.server.ts`. Nothing else in the frontend hardcodes a
category — the board, the homepage specialty picker and the sitemap are all
driven by the API, so **adding a category needs no frontend change at all.**

## Session update (2026-08-30) — country filtering

The owner asked to sort listings by country and expected that to be a
parsing problem. It was two problems, and parsing was the smaller one.

### Measure first: 41% of the board had no location at all

Before writing any parser, the split was worth knowing:

| Path | Rows missing a location |
|---|---|
| Workday, Apple, Lever, Ashby, Recruitee | 0% |
| Greenhouse | 5% |
| BambooHR | 17% |
| Generic HTTP/Playwright | 64% |
| iCIMS, ADP, Pinpoint | 100% |

**Every mature ATS parser already extracted location.** So no amount of
string parsing could reach the missing 41% — that was extraction, and the
two levers had to be built separately.

### The parser (commit c23f9ba)

`scraper/countries.py`, `detect_country()`, and a `jobs.country` column
holding an ISO alpha-2 code, set at normalize time and by
`backfill_relevance`.

**The design rule that matters, and it inverts the usual bias: ambiguity
resolves to NULL, never to a guess.** The board shows unresolved rows
under *every* country filter, so a wrong country hides a job from the
right filter while no country never does. Precision beats recall here,
which is the opposite of the standing preference everywhere else on this
project. "Cambridge" (UK or Massachusetts), "2 Locations", and any string
naming two countries all stay NULL.

Resolution is tiered, and the order was forced by real data:

1. **Country names** — outrank everything, because a two-letter prefix
   often collides with a US state. `CH - Shanghai, China` is China, not
   Switzerland. `CA - Canada` is Canada, not California. `IN - Bangalore,
   India` is India, not Indiana.
2. **US state names** → US.
3. **Known cities** — before bare codes, which is what makes
   `Darmstadt, DE` Germany rather than Delaware.
4. **US state codes** → US (`San Francisco, CA`).
5. **Canadian provinces** → CA.
6. **ISO alpha-2/alpha-3** (`Shanghai, CN`, `CHN, Shenzhen BOC`).

Phrase matching runs over 1-3 word n-grams inside each segment, which is
what catches `Stockholm HQ`, `Shanghai Metro Area` and `Navi Mumbai, Rupa
Renaissance`. `:` is a segment separator, which alone fixed every
`City, ST: street address, zip` row.

Resolves **92% of the 2,186 rows carrying a location**. Every remaining
miss genuinely names no place: `2 Locations`, `Remote`, `Worldwide`, and
McGill University building names like `Burnside Hall`.

### The extraction fix, worth more than the parser (commit e1142bf)

Shure had 64 jobs with 3-6k descriptions and **not one location** — the
single largest gap on the board. It routes through the iCIMS parser,
which reads location from the detail page's JSON-LD, so the description
arriving intact while location came back empty pointed at one function.

`schema.org` allows `jobLocation` to be an **array**, iCIMS uses that
form, and `_parse_jsonld_location` handled only `str` and `dict`. Every
array-valued posting silently lost its location. Lists are now unwrapped;
several places are joined with `; ` (and the country parser then
correctly refuses to guess between them). iCIMS also emits the literal
string `UNAVAILABLE` for absent address parts, now dropped instead of
displayed.

Shure went **0 of 64 located to 64, 63 resolving a country.** The fix is
not iCIMS-specific — it applies anywhere JSON-LD is read.

### The UI ranks, it does not filter (commits 86975fa, d5bf11d)

The owner's design: choosing a country puts those roles first and the
**unplaced ones after**, so nothing that might be in that country is
hidden. Implemented as `country=XX` on `/api/jobs`:

- rows in that country first,
- rows with `country IS NULL` after, behind a labelled divider,
- rows known to be elsewhere excluded.

`GET /api/countries` lists countries with counts plus `unknown_count`.
The job board shows a Country select, a chip, and the divider text
"Location not parsed — may still be in {country}".

**Do not "simplify" this into `WHERE country = ?`.** That drops every
unplaced row and would silently hide a large share of the board. There
are tests in `api/tests/` — the first ones in that package — asserting
the inclusion and the ordering.

Note `api/tests` needed `scraper` declared first-party for isort:
`api/__init__.py` puts the scraper directory on `sys.path`, so any module
importing `scraper` before `api` fails at runtime.

### Result after the 2026-08-30 scrape

| Metric | Before | After |
|---|---|---|
| Board rows carrying a location | 277 (59%) | **334 (71%)** |
| Board rows with a resolved country | 261 (56%) | **317 (68%)** |
| Shure board rows located | 0 of 54 | **54 of 54** |
| Countries represented on the board | 21 | 21 |
| Board total | 468 | 469 |

The remaining 152 unplaced board rows are overwhelmingly generic-path
rows that carry no location string at all, not parse failures. **The next
lever there is extraction, not the parser**: ADP (7 companies) and
Pinpoint (1) still return no location, and the generic anchor path can
only get one by fetching detail pages, which "Detail-page fetching" above
already measured as a small population.

## Session update (2026-08-31) — every Workday and Google link was a 404

### Board as it stands (2026-08-31, commit 7d76e61)

| Metric | Value |
|---|---|
| Total job rows | 8,060 |
| Active | 4,704 |
| Audio-related (the public board) | **470** |
| Board rows with a real description | 335 (71%) |
| Board rows with a location | 335 (71%) |
| Board rows with a resolved country | 318 (68%) |
| Uncategorized board rows | 106 |
| Companies appearing on the board | 73 |
| Companies contributing active jobs | 398 |
| Board links reachable | **467 of 470** (3 are Meta bot defence) |
| Tests | 454 scraper + 7 api; ruff, mypy, `npm run check` clean |

The owner reported that Workday links said "invalid link". Diagnosing that
found two unrelated URL bugs and cleared **851 broken rows**.

### Workday dropped the site segment (commit 667a14e)

The public URL was built as tenant origin + the API's `externalPath`, with
nothing between them. Workday needs the site:

```
https://boseallaboutme.wd503.myworkdayjobs.com/job/US-MA---Framingham/...       404
https://boseallaboutme.wd503.myworkdayjobs.com/Bose_Careers/job/US-MA---...     200
```

`_parse_list_item` now takes `site` and builds `{base}/{site}{external_path}`.
**`external_id` deliberately stays the bare `externalPath`**, so existing rows
update in place instead of being orphaned and reinserted.

**The first repair was incomplete, and this is the part to remember.** Fixing
the 8 companies with a stored `ats_type='workday'` covered 263 rows and looked
complete. But `WorkdayScraper.can_handle` also routes on `careers_url`, so **18
further companies with `ats_type=None` were on the same code path** —
RingCentral, Samsung, Razer, Sonos, Belkin, Full Sail, the whole GN family
(Beltone, Jabra, SteelSeries, GN Store Nord). Real total: **851 rows across 26
companies.**

> **Querying `ats_type` does not tell you which parser ran.** Several parsers
> route on `careers_url` through `can_handle`, so `ats_type IS NULL` does not
> mean "generic". To find every company a parser touches, match its
> `URL_PATTERN` against `careers_url` as well. This is the second time this
> session that an `ats_type` query understated a population.

### The generic scraper ignored `<base href>` (commit 6386618)

Google's careers page declares
`<base href="https://www.google.com/about/careers/applications/">` and links
its jobs relatively, so resolving against the page URL produced
`.../jobs/results/jobs/results/...` and all 10 Google links 404'd. Browsers
honour `<base>`; the extractor did not.

`resolve_document_base()` is now applied in **both** places that resolve
relative URLs — `extract_job_links` and `find_next_page` — because a base tag
governs the whole document. A relative base resolves against the page; a
non-http base is ignored. Google's 132 job ids and its pagination are
unchanged; only the host path is now correct.

Note this re-inserted Google's rows rather than updating them: generic-path
`external_id` is the URL, so a URL-shape fix is a new identity. 167 inserted,
175 deactivated. Expect that churn whenever a generic URL shape changes.

### Meta's 400s are bot protection, not broken links

Three Meta links return `400` to curl regardless of URL shape — `/jobs/{id}/`,
`/profile/job_details/{id}`, all of them. **Opened in a real browser they load
fine.** This is the same defence as the 429 in the late 2026-08-29 session.
**Do not "fix" the Meta URL format.** It is correct.

### Board-wide link check: the metric nobody had

Sweeping all 470 board links found the problem and confirmed the repair:

| | Before | After |
|---|---|---|
| Reachable (200/202) | 457 | **467** |
| 404 / 400 | 13 | 3 (all Meta bot protection) |
| Genuinely broken | **851 rows** | **0** |

**This class of bug is invisible to every metric the project tracks.** All 26
companies reported `success` with healthy `jobs_found` the whole time, kept
full descriptions, and scored normally — while every link 404'd. It is the same
shape as the marketing-landing-page finding: *counting rows cannot see it.*

There is still **no link checker in the repo.** The throwaway used here was a
`curl -sL -o /dev/null -w '%{http_code}'` sweep over the board at 10 workers,
following redirects with a browser User-Agent, treating 403/429/999 as "site
dislikes robots" rather than broken. Worth building as a periodic read-only
diagnostic alongside `diagnose_failures.py` — roughly 470 requests, a few
minutes. **Whitelist Meta**, or it will report three false failures forever.

### Uncommitted seed edits found in the working tree (2026-08-31)

`data/audio_companies_final.json` had **uncommitted manual edits** — not made by
this session, and matching `SEED_WORKLIST.md` entries, so they are the owner's
own worklist research. They are **still uncommitted and not in the database**;
the last full scrape predates them and the per-company reruns used
`--skip-load`. Tested read-only with `check_url`:

| Company | Edit | Result |
|---|---|---|
| DiGiCo | `digico.tv/app.php/...` -> `digico.biz/recruitment/` | **works — 5 jobs, 4 reach the board** |
| QSC | `acuityinc.com/careers` -> `qsccareersemea-qsc.icims.com/jobs/` | routes to iCIMS, **returns 0 jobs** |
| Arturia | `jobs.arturia.com/` -> `jobs.arturia.com/join-us` | **no job links found**, same as before |
| Extron, FBT, +2 | `verified: true` -> `false` | deactivates their stale rows, as intended |

**QSC needs care before it is committed.** iCIMS reporting `success` with zero
jobs sets `trust_empty`, which deactivates existing rows. QSC has none today so
nothing is lost, but the EMEA board genuinely looks empty — `qsccareers-qsc`
(no `emea`) also resolves and may be the right tenant.

Arturia's root and `/join-us` both return a page with 30 anchors and no job
links, so the board is almost certainly JS-rendered; neither URL is an
improvement yet.

To land these: `python -m scraper.company_loader` then a scrape.

## Session update (2026-08-31, later) — the link checker, and what it found

Board 465 jobs, 4,447 active rows, 78 contributing companies, 106 uncategorized,
321 with a country. All three gates green at 515 tests.

### The link checker exists now (commit f94492f)

`python -m scraper.check_links` sweeps every URL on the board, read-only,
deduplicating so one request covers every row sharing a page. Buckets are ok,
broken, bot_defence, server_error, other_status, error. Flags: `--all`,
`--company`, `--limit`, `--examples`, `--json`. Exit 1 if anything is broken.

**It caught a bug in itself on the first run,** which is the part worth
remembering. It reported all four Akai Professional rows as broken. They were
not: Pinpoint answers HEAD with 404 and GET with 200, and the original design
trusted a non-2xx HEAD as final. HEAD is now only an optimization — anything
non-2xx is re-verified with a GET before a URL is called broken. A checker
whose broken bucket cannot be trusted is worse than no checker.

Latest sweep: 459 URLs, 456 ok, 0 broken, 3 bot defence. The 3 are Meta, which
is whitelisted by host because it returns 400 to every non-browser client.

### Rohde & Schwarz: three bugs stacked behind one symptom

R&S was serving 77 rows of country-selector links and one real job. Unpicking it
found three separate faults, and the first two are general.

1. **The seed said `scrape_method: playwright`,** and `pipeline.py:163` reads
   `skip_http = company.scrape_method == "playwright"` — so the HTTP path is
   skipped outright. HTTP worked and returned real jobs; Playwright rendered the
   country selector. **When a company returns navigation furniture, check its
   `scrape_method` before blaming extraction.**
2. **Pagination could not leave the base path.** `find_next_page` required the
   next page to share the base URL's exact path. Avature paginates from
   `/en_US/careers` to `/en_US/careers/SearchJobs/?jobOffset=6`, so every
   candidate died on the path check. Now the next page may sit at the base path
   or beneath it, never elsewhere; an empty base path matches nothing, so a site
   seeded at its root still cannot follow arbitrary links (commit 7fb7be6).
3. **The next-page control is labelled `Next >>`,** which matched neither
   "exactly next" nor "exactly >>" in the text pattern, and was itself extracted
   as a job (commit dd20443).

Measured end to end: 6 jobs to 86, 4 board rows to 7, and `test_measurement_qa`
37 to 41.

**Note the correction:** dd20443's message claimed the text fix made Avature
boards paginate. It did not — fault 2 was still in the way, and R&S stopped at
page one until 7fb7be6. Do not trust that commit message on its own.

### The pagination fix is narrower than it looks

A full scrape after 7fb7be6 moved `jobs_found` 4,376 to 4,369 with 5 rows
inserted. It is a correctness fix with essentially one measured beneficiary, not
a coverage lever. **Harman is unchanged at 16 board rows,** which confirms what
next-step 9 already said: its scoped query fits on one page, so pagination was
never the constraint there.

### Furniture rejection: audited, zero false positives

`is_furniture_title` now rejects whole titles that are only a pagination
control, and the exact-match chrome set covers `search jobs`, `jobs & career`,
`sign up for job alerts`, `powered by jobvite` and `job alerts`. Run against all
3,710 distinct active titles, the pagination rule rejects **0** legitimate
titles. `Next.js Engineer`, `First Officer`, `Last Mile Operations Manager` and
`Page Layout Designer` are regression tests.

Still uncaught, and left deliberately: Crestron Electronics yields 12 rows of
`career areas`, `Administration & operations` and `CCPA/CPRA Notice`. That is
the `careers_landing` class, not a furniture-pattern gap — the page is a
category index, not a board. All score 0, so it costs active rows, not board
quality.

### Seed batch (commit 8aa4116), all measured with check_url first

Corrected: **Rohde & Schwarz** to the Avature board; **Music Tribe** to
`jobs.jobvite.com/musictribe` (eight seed entries shared the dead
`musictribe.com/careers`); **Spitfire Audio** to `apply.workable.com/
spitfire-audio` — a real Workable account, currently empty, which will now pick
up postings without another seed edit.

Retired: **Tannoy, TC Electronic, TC Helicon, Turbosound** (Music Tribe brands
with no separate board; pointing all four at Jobvite would duplicate the same
ten corporate roles); **Musi**, a music app pointed at **MUFG the bank** by slug
collision, 40 rows of SAP and banking; **Hulu Post**, pointed at the Disney
careers root, which returns department names; **Zynaptiq**, whose careers page
is a product page that put `audio applications` and `audio plug-ins` on the
public board.

**Niantic and Eventbrite look like the same class and are not.** Both companies'
own careers pages redirect to an acquirer's board — `nianticlabs.com/careers`
resolves to `careers.scopely.com`, Eventbrite's to `jobs.bendingspoons.com`. The
seeded URL is right and the noise is real. Left alone on purpose; do not
"fix" them.

### Two facts about the database worth knowing

- **`scraped_at` is never re-stamped on update.** A row showing an old
  `scraped_at` is not stale; it is being re-fetched every cycle and only its
  scored fields are rewritten. Do not read that column as freshness.
- Seed-to-database drift is currently **zero**. Verified by comparing every
  seed `careers_url` and `verified` flag against the companies table.

### Board composition, for the owner

`sales_marketing_cs` is 66 rows, second only to `audiology_hearing` at 67 and
ahead of every engineering category (`audio_dsp_embedded` 47, `audio_aiml` 42,
`audio_software` 41, `test_measurement_qa` 41). For an audience of audio
engineers that is worth a decision.

The obvious lever was measured and **rejected**: remapping
`Voice & Speech Technology` to partial scope drops 70 board rows, including 28
at Deepgram, to remove Zoom's 21 Account Executives. Scope is derived from
`category` in `company_loader`, not stored per company, so it cannot be tuned
for one company without moving the whole category.

### Leads found but not resolved

- **Calrec**'s real board is `calrecaudioltd.livevacancies.co.uk/jobsIframe`,
  reached from an iframe on `calrec.com/careers`. It fails TLS negotiation
  outright (`TLSV1_ALERT_PROTOCOL_VERSION`) and Playwright finds no links. Count
  how many seeded hosts fail the same way before treating it as one company.
- **Welcome to the Jungle** (`welcometothejungle.com/en/companies/<slug>/jobs`)
  is Devialet's board and is common across French audio firms. JS-rendered;
  yields only furniture. Count the bucket before calling it a lever.
- **Native Instruments** `/pages/careers` is a JS-rendered SPA with no ATS link
  in the HTML. `career-center` redirects to it.
- **Audio Precision** is part of Axiometrix Solutions with GRAS and imc; the
  board is `axiometrixsolutions.com/about-us/careers`, currently no openings and
  no extractable job links.
- **Fostex**'s `careers_url` is a 900-character tracking blob on
  `studiowatersolutions.com`, an unrelated domain. It yields 0 rows so it costs
  nothing today, but it is plainly wrong.
- Jobvite is a **3-company bucket** (Capcom, Devialet, Music Tribe) — no parser
  worth building. Devialet's seeded URL is a Jobvite *error* page
  (`?invalid=1`).

## Session update (2026-09-02) — Workable, Eightfold, and seed hygiene

Board 476. All gates green at 551 tests.

### Never run git checkout on data/audio_companies_final.json

A subagent discarded the owner's uncommitted seed edits with
`git checkout -- data/audio_companies_final.json`, having attributed the
change to "a test run with network side effects". **That diagnosis was wrong.**
The suite does not touch the file — verified by md5 across 511 passing tests.
The edits were the owner's own work, retiring Creek Audio and Fostex, and they
were unrecoverable because they had never been committed. Restored in 1cc5885.

Seed truth is edited by hand, outside this tooling, between sessions. Treat any
diff in it as the owner's until proven otherwise. Related: **stage seed edits
explicitly, never with `git add -A`** — the owner's Devialet correction was
swept into 905aae6, a commit whose message does not mention it.

### Every Workable link was serving raw markdown (commit 506f558)

The parser reads Workable's markdown index, whose `[View]` links point at
`/{account}/jobs/view/{code}.md`, and stored that path with `.md` stripped. The
stripped path is itself a machine-readable endpoint: Workable serves it as
`text/markdown`. Readers got the source of the page instead of the page. 26 rows
across 7 companies.

The human URL is `/{account}/j/{code}`, which is also Workable's declared
canonical. `parse_jobs_md` already took a `slug` it never used.

**The latent trap next to it:** `_fetch_descriptions` recovered the job id by
re-parsing the job URL, so changing the URL shape would have silently stopped
every Workable description being fetched — no error, just jobs quietly losing
descriptions and falling off the board. It reads `external_id` now. Same lesson
as Workday: **change the URL, never the identity**, or every row orphans.

### check_links now catches a 200 that serves the wrong document (commit 3c386d3)

The Workable bug walked straight past the link checker, because those URLs
really did return 200. A status-only sweep is blind to a server that returns
success and hands you the wrong document.

There is now a `wrong_content` bucket. HEAD short-circuits only when it reports
`text/html` itself; anything else on a 2xx falls through to the GET, so hosts
that omit or misreport the header are judged on what a reader receives. Content
type is consulted **only** inside the 2xx branch — a 404 serving JSON is still
broken, and the Meta whitelist still wins.

`application/pdf` counts as readable. The first sweep flagged Kicker's
"Electrical Design Engineer (PDF, 123 KB)", a real posting a reader can open.
The signal worth catching is machine-readable source where a human page was
expected, not any non-HTML document.

### Eightfold AI parser (commit 0bb4344), added for Dolby

Dolby's board is Eightfold. Playwright reached it but returned 12 rows with the
whole card flattened into the title — "Multimodal AI Researcher, Audio Atlanta,
Georgia,United States Hybrid Flexible Location" — and no descriptions, so
nothing it put on the board carried a category.

Three things to know if another Eightfold company appears:

1. **The obvious endpoint is a decoy.** `/api/apply/v2/jobs` returns 403 "Not
   authorized for PCSX". `/api/pcsx/search` is open and unauthenticated.
   `position_details` carries the full description.
2. **`domain` must be the registrable domain** — `dolby.com`, not the careers
   host `jobs.dolby.com`, which returns an HTML error page instead of JSON.
3. **The slug is not in the page markup.** Tenants use vanity hosts and the only
   marker names eightfold.ai, so discovery derives the slug from `base_url`, the
   way `SLUGLESS_ATS` handles a missing slug. **This means an Eightfold company
   needs two scrape cycles** — the first discovers, the second parses. A newly
   seeded one looking empty is expected, not broken.

Dolby: 62 jobs against the API's own count of 62, all with a description over
200 chars, a location and a posted date, 61 with a country across 8 countries.
9 reach the board. Filed as Consumer Electronics & Tech, not Audio IP &
Licensing — that category holds standards bodies (AES, MPEG, ITU-R, Bluetooth
SIG), which is why it is partial scope. Dolby's nearest peer is Fraunhofer IIS,
also Consumer Electronics & Tech. At native scope it would be 26 rather than 9,
the extra 17 scoring on Dolby's audio-saturated descriptions rather than being
audio work. **Measured: the `query=audio` scoping costs no recall** — 97 jobs
unscoped against 62 scoped, and every board-eligible job is inside the scoped
set at either scope.

### scrape_method is the first thing to check when a company returns navigation

This bit twice in one day, in opposite directions:

- **Rohde & Schwarz** had `playwright`, and `pipeline.py:163` sets
  `skip_http = company.scrape_method == "playwright"`, so the HTTP path was
  never tried. HTTP held the real jobs; Playwright rendered a country selector.
- **Devialet** had `http`, and its JS-rendered welcomekit board returned exactly
  one row, "Spontaneous Application" — the HTTP scraper reporting success on
  furniture, so the chain never escalated. Forcing `playwright` took it from
  1 row to 15, of which 2 reach the board.

### Tesla — blocked, do not re-investigate

**It was never scraped at all**: `verified:false`, and `main.py:125` only selects
verified companies, so it had no `last_scraped_at` and produced no failure log.
**An unverified company is silent, not failing** — distinct from the existing
warning that "never scraped" usually means "failed every attempt".

Fixing that would not help. Tesla sits behind Akamai bot management and refuses
every automated client: 403 to HTTP, Playwright blocked, Playwright stealth
blocked, and 403 on `robots.txt` and `sitemap.xml` too. A real browser session
gets the challenge page. `careers.tesla.com` does not resolve. Same class as
Meta, same answer: **do not build evasion.** The correct URL is recorded
(`/careers/search/`) with `verified:false` so one flag flips it if that changes.

### The Music Tribe family is now consolidated (commits 8aa4116, b6fb339)

Aston Microphones, Behringer, Bugera, Coolaudio, Klark Teknik, Lab.gruppen,
Midas, Tannoy, TC Electronic, TC Helicon and Turbosound are all **Music Tribe**
brands. Nine were seeded separately, eight of them against the dead
`musictribe.com/careers`. All are retired; Music Tribe carries the group's
hiring at `jobs.jobvite.com/musictribe` — 8 jobs, no pagination, of which
"Hardware Engineering Leader" reaches the board.

Midas and Coolaudio are **deliberately not seeded**. A brand entry can only
duplicate the same board and inflate the company count without adding a job.

**The umbrella is not discoverable from brand headers or about pages** — it is a
footer line, "Part of Music Tribe", with privacy and terms links to
`community.musictribe.com`. Worth checking the footer before treating sibling
brands as independent employers; the same pattern hid the Audiotonix family
(Calrec, DiGiCo, Solid State Logic, Sound Devices, Slate Digital).

### Other companies looked at, unresolved

- **d&b audiotechnik — FIXED (8043080).** Seeded at `db-audio.com`, which fails
  TLS with an invalid certificate authority. The real site is `dbaudio.com`, and
  its careers page links to a Workday board this project already parses,
  `dbaudio.wd103.myworkdayjobs.com`. One opening today, correctly filtered.
- **Eventide** — page loads, no job links. **RME** — Playwright succeeds but
  returns only "Skip navigation". Both still unverified.
- **Native Instruments**, **Welcome to the Jungle** (`welcometothejungle.com`,
  distinct from the `welcomekit.co` hosted boards, which do work under
  Playwright), **Calrec**'s `livevacancies.co.uk` TLS failure, and
  **Audio Precision**/Axiometrix all remain as recorded on 2026-08-31.

## Session update (2026-09-02, later) — the acoustics taxonomy call

### Bare "acoustics" now files under audio_systems (commit 4cabea3)

The owner resolved the taxonomy question that had blocked item 4 since
2026-08-30: bare **"acoustics" belongs to `audio_systems`**, not to
`transducers`, `audio_research` or `acoustics_consulting`.

`_keyword_pattern` sorts a category's keywords longest-first, so adding the bare
word does not shadow the phrases: `acoustics_consulting` still wins "room
acoustics", "building acoustics" and "architectural acoustics". A test pins it.

### Speaker-product roles now carry audio_systems as well as transducers

The owner also reported transducers rows that should carry `audio_systems` —
job 3461, ADAM Audio's "Technical Lead (Loudspeakers)". **The first hypothesis
was wrong and measuring killed it in one run.** `CATEGORY_DOMINANCE` lists
`audio_systems` as subordinate to `transducers`, which looked like the obvious
cause; removing it changed **zero** rows. `audio_systems` was never scoring on
these jobs at all, so there was nothing to suppress. Check that a category
actually scores before blaming dominance for its absence.

The real gap: `loudspeaker` and `studio monitor` lived only in `transducers`.
Both now sit in `audio_systems` too, so a whole-product speaker role carries
both tags. Component-level words — `transducer`, `voice coil`, `diaphragm`,
`driver design` — deliberately stay transducers-only, so Apple's "Acoustic
Transducer Engineer" is unchanged. A test pins both sides of that line.

This mirrors `acoustic engineer` / `acoustics engineer`, which have always sat
in both categories. **Dual-listing a keyword is an established move in this
file, not a hack** — it is how a role that is genuinely both gets filed as both.

### What it measured

Each word was measured on its own before anything was written, per the standing
rule from the rejected `FALLBACK_ROLE_CATEGORIES` bundle:

| addition | rows changed | from no category | off-board rows gaining |
| --- | --- | --- | --- |
| `acoustics` | 5 | 4 | 0 |
| `loudspeaker` | 6 | 2 | 0 |
| `studio monitor` | 2 | 0 | 0 |
| all three | 14 | 6 | 0 |

**No off-board row gained a category, so nothing new was admitted** and the
board held at 476 across the backfill. Uncategorized board rows 110 -> 104.
(Both figures predate the 2026-09-02 full cycle, which took the board to 512.)
One displacement: Bose's "Acoustical Engineer" hit the 3-category cap and
dropped `microphones_recording` for `audio_systems`, which is the better filing.

Beneficiaries: Neumann "Working Student Acoustics", Comsol "Applications
Engineer: Acoustics", two Bose "Systems Engineer" rows, the ADAM Audio
loudspeaker and studio-monitor roles, Akai's "Senior Product Manager - Alto
Professional".

### Focusrite and Ampify Music were the same board (commit 69a3495)

Found while auditing the change; the owner chose to keep Focusrite.
Company 59 (Ampify Music, `https://focusrite.workable.com/`) and company 469
(Focusrite, `https://apply.workable.com/focusrite/`) resolve to the same
Workable slug, so **all 6 of Focusrite's board rows appear twice** under
different employer names.

A URL-level sweep across the whole board found **this pair and nothing else** —
6 identical job URLs under two company ids, no other collisions. So the class is
bounded at one pair; this is not a general de-duplication problem. Ampify is a
Focusrite-owned brand, the same relationship as the Music Tribe family
consolidated earlier today.

Retired the established way: `verified` flipped to false, the entry kept so it
is not rediscovered, and `_deactivate_unverified_jobs` in `company_loader`
deactivates its jobs on the next sync.

**Why the existing guard missed it, which generalises.** `_dedupe_shared_urls`
in `main.py` already skips a company whose careers URL or `(ats_type, ats_slug)`
pair has been scraped, but it caught neither: the two URLs differ textually
(`focusrite.workable.com/` versus `apply.workable.com/focusrite/`) and **neither
company has an `ats_type` stored at all**. Only 56 of 728 verified companies do
(2026-09-02, after the full cycle; it was 52 before, so the number creeps up a
little each run). The board-identity half of that guard is therefore inert for
roughly 92% of the population — discovery resolves the ATS at scrape time but
the result is mostly not written back to the company row. Worth knowing before trusting the guard, or
before building anything else on stored `ats_type`.

### --limit 0 is not "load only" — it runs a full cycle

`main.py` tests `if limit:`, so `--limit 0` is falsy and means *no limit*. There
is no load-only entry point; `--company <slug>` against something cheap is the
closest thing. Running it by mistake started a real cycle that refreshed 101
companies before it was killed, leaving the database half-refreshed — the repair
was to finish the cycle rather than leave it split.

## Session update (2026-09-02, evening) — bookmarks, and a regression I caused

### The report button was inert on the home page (commit 4d8dc66)

**Two pages render `JobStrip`: `/jobs` and the home page.** The feedback dialog
was originally mounted inside the card, which worked everywhere. Lifting it to
the page — right, since a 20-job board would otherwise mount 20 modals — wired
only `/jobs`, so on the home page `onReport` was undefined and
`onReport?.(job)` did nothing. Optional chaining swallowed it silently: no
console error, no visual change, nothing to notice.

**If you add a third page that renders `JobStrip`, wire `onReport` or the
button is dead there too.** Grep for `JobStrip` before assuming a card control
works site-wide.

### The flag was ambiguous and did nothing (commit 2efb590)

The owner reported both the flag and the report button as broken. Only the
report button was; the flag was a different problem in two parts.

**Ambiguous.** A flag icon sitting next to a report control reads as "flag this
listing" — the owner read it exactly that way. It is now a bookmark: bookmark
icon, bookmark wording, `getBookmarks` / `toggleBookmark`.

**Inert.** `toggleFlag` wrote ids to `localStorage` and **the only reader was
the card itself**, deciding whether to draw the button filled. Nothing surfaced
the list. The control promised a save-for-later feature that had never been
built. There is now a "Bookmarked only" toggle in the filter rail with a live
count.

### Bookmarks are device-local by the owner's decision — do not "fix" this

Bookmark ids live in `localStorage` under `asj:bookmarks` and **never reach the
server** except as a query param when the reader actually filters. They do not
follow anyone to another browser or device. **This is deliberate**: the owner
chose it explicitly on 2026-09-02, in preference to user accounts. Do not treat
the missing sync as a gap and do not propose accounts to close it.

`getBookmarks` falls back to copying the old `asj:flags` value across on first
read, so bookmarks saved before the rename survive. That fallback can be
removed once no reader is plausibly still carrying the old key.

### The ids had to reach the server, and empty had to mean empty

Filtering client-side would only have shown bookmarks that happened to land on
the current page, so `/api/jobs` takes an `ids` CSV, parsed to ints and bounded
at 200 (`MAX_ID_FILTER`). It composes with the other filters — bookmarked plus
remote works — and pagination stays server-side.

**The trap: a bookmarked-only view with zero bookmarks must show nothing, not
the whole board.** An absent `ids` param means "no id filter", so the UI sends
`ids=0` instead, which matches no job. `_parse_ids("")` returns `[]` rather than
`None` for the same reason. Both are pinned by tests; a browser check confirmed
the empty state rather than 512 rows.

### Neural DSP — two walls, and the second one is fatal (2026-09-02)

Not on the board: **0 jobs, and `last_scraped_at` is NULL**, which means it has
failed every attempt rather than been skipped. `scrape_log` shows the same
error on every run back to 2026-08-30: `page loaded but no job links found`.

The seed URL is already correct. The failure is structural, in two layers.

**1. The board lives in an iframe, and the scraper never looks inside one.**
`https://careers.neuraldsp.com/` is an 8.9 KB shell with **zero anchors**. Its
only content is `<iframe id="careerWebsite">` — carrying **no `src` attribute at
all**. Inline JS assigns it at runtime:

    iframe.src = "https://revolutpeople.com" + "/neural-dsp" + "/public/careers/"

That explains why Playwright fails identically to plain HTTP: it renders the
parent document faithfully, and the parent genuinely has no job links. **Nothing
in the scraper descends into child frames** — the only `iframe` handling in the
codebase is iCIMS, which just appends `in_iframe=1` to a URL. So the generic
path cannot see an iframed board at all. This is a real class, not a Neural DSP
quirk; worth counting before building, per the usual rule.

**2. The ATS is behind Cloudflare, which kills the workaround.** Pointing the
seed straight at the iframe URL does not help, and this was measured rather than
assumed — `check_url` against
`https://revolutpeople.com/neural-dsp/public/careers/` returns HTTP 403, then
Playwright and Playwright stealth both land on the interstitial and report no
job links. **0 / 0 would reach the board.** A browser visit shows the Cloudflare
"Just a moment..." challenge.

**Do not re-investigate Neural DSP as a seed problem.** Same bucket as Tesla:
reachable by a human, not by this scraper. Fixing layer 1 alone buys nothing
here, though it may be worth doing for other iframed boards. Revisit only if
Revolut People exposes a JSON endpoint that is not challenged, or if the owner
decides the Cloudflare tier is worth engineering around.

**Meta is NOT in this bucket, despite the bot-defence notes elsewhere in this
document.** Meta scrapes successfully every cycle and holds 3 board rows (Audio
Systems Engineer, Audio Software Engineer / Applied Scientist, Research Acoustic
Systems Engineer — 20 rows total, 15 active, all scoring 85). What is limited at
Meta is narrower: its links fail the link checker because `metacareers.com` sits
in `BOT_DEFENCE_HOSTS`, and the rejected GraphQL experiment returned 19 jobs
against the DOM's 10 but **the same 3 board jobs**. That is a coverage ceiling,
not a failure. Do not conflate the two.

## Session update (2026-09-03) — the job card had the location all along

### The generic path never read a location (commits 8bdc635, 390d8a9)

157 of 512 board rows had no country and 138 carried no location string at
all. The handoff had this filed as "extraction, not parsing", which was
right, and as needing detail-page fetching, which was wrong.

`extract_job_links` built `RawJob(title=..., url=..., job_type=...)` and
never set `location`. The only location source on the generic path was
`_parse_jsonld_location`. So every card-based board lost it — the text was
sitting one or two ancestors above the anchor, unread.

Measured before building, across the 40 companies holding those 138 rows.
The four largest — Advanced Bionics 23, Harman 16, Zoom 12, Google 11 —
all carry it in the DOM. Result after re-scraping all 40 into a **copy** of
the database:

| Metric | Before | After |
|---|---|---|
| Board rows with a country | 355 of 512 (69%) | **434 of 525 (83%)** |
| Board rows with no location string | 138 | **72** |
| Countries represented | 21 | **26** |

Advanced Bionics, Harman, Zoom and Google each went to **zero** unlocated
board rows. The board grew 512 -> 525 because re-scraping brought fresh
rows with it.

### The signal is a semantic marker, and blind text scraping is a trap

The first prototype took the card's whole text and ran `detect_country` on
it. It produced a **wrong country** immediately: Google's language switcher
reads "Francais (Canada)" and resolved to CA. A wrong country is worse than
none here — it hides a job from the filter it belongs to, while no country
never does, which is the same reason `detect_country` resolves ambiguity to
NULL.

So the extractor keys on an element whose `class`, `id`, `aria-label`,
`title`, `data-label` or `itemprop` names "location", or on a Material icon
glyph (`place`, `location_on`) whose sibling holds the text. Real markup
found in the wild: `_sf_location`, `table__detail--location`,
`job-component-location`, `list-item-location`, `location_icon_text_<hash>`.

Three guards, each verified by sabotage rather than assumption — deleting
any one of them fails a test:

- **The scan never leaves the card.** It walks up only while the container
  still holds exactly one job anchor. Solid State Logic's board carries a
  Location dropdown offering UK and USA; scoped this way it is unreachable.
- **Form controls are skipped**, ancestors included.
- **Job-board vocabulary is rejected.** Without it AMX yielded "Browse Jobs"
  five times.

JSON-LD still wins where it has a location; the card only fills a gap.

A false-positive sweep over 60 sampled boards extracted 55 locations across
9 companies, **disagreed with JSON-LD 0 times**, and left the other 51
boards empty rather than guessing.

### Multiple locations need a real separator (commit 390d8a9)

A card listing several places was flattened with spaces. `detect_country`
matches 1-3 word n-grams inside each segment, so a space join lets a phrase
form across the seam between two entries that neither contains. Sibling list
items are now joined with `; `, matching what `_parse_jsonld_location`
already does. Zoom's Cork/Dublin/London role stores all three and resolves
to NULL rather than picking one.

### This only lands on a scrape

Location is written at normalize time from `RawJob`. `backfill_relevance`
recomputes country from the *stored* location, so it cannot help a row that
has no location string. **The 66-row gain arrives when the next full cycle
runs**, not before. Everything above was verified against a copy of the
database, never the live one.

### Cost

Linear and negligible: 71ms for a synthetic 500-card page, against network
time measured in seconds.

### A board claim needed corroboration (commit 4023298)

Chasing item 11 turned up a live defect rather than the missing feature.

`_dedupe_shared_urls` collapses two companies that share a stored
`(ats_type, ats_slug)` and deactivates the loser's jobs. Three companies
were being skipped that way, and only one was a real duplicate:

| Company | Stored identity | Claimed by | Correct? |
|---|---|---|---|
| Beats by Dre | `apple` / `""` | Apple | yes — Apple-owned, same board |
| Flowkey | `breezy` / `assets-cdn` | Dalet Digital Media | no |
| TrueFire | `workday` / `toyota.wd503/TMNA` | Toyota | no |

The two bad slugs came from HTML discovery reading things off the page
that were not the company's board — a CDN host, and Toyota's Workday
tenant found on a guitar-lesson site. **Their zero active jobs were the
guard's fingerprint, not an empty board.**

The separating fact is whether the company's own careers URL resolves to
the identity. `jobs.apple.com` does; `jobs.dalet.com` and
`careers.toyota.com` do not. A company now claims a board only when
`discover()` over its own careers URL agrees. An uncorroborated identity
can still *lose* a collision, which is what keeps Beats deduped.

**The empty slug is deliberate — do not "fix" it.** `apple` is in
`SLUGLESS_ATS` because its board really is global, and
`test_same_board_different_urls_is_deduped` pins that. An earlier attempt
here made blank slugs non-identifying and broke it.

### Two levers measured and closed

**Item 10, flattened titles: 14 rows of 4,615, 2 on the board, 11 of them
Devialet.** It costs no categories — all 9 uncategorized board rows whose
titles carry an employment word or trailing place have correct titles. A
naive strip would destroy "Aerospace, Full-Time Lecturer, Faculty".

**Item 11, `ats_type` persistence: measurement value only.** 81 companies
would newly resolve, but every real duplicate group already shares a
careers URL and is caught by the URL half of the guard.

## Session update (2026-09-03, later) — several careers URLs per company

### Why one URL was not enough

Harman's board only answers search queries and matches tokens exactly, so
`?search=audio` structurally cannot return a role titled "Acoustics Quality
Director". The same shape covers a company running separate regional
careers sites. `extra_careers_urls` on a seed entry now holds additional
URLs, merged into the company's single job set.

`careers_url` stays required and primary, so all 1,388 seed entries were
left untouched — only Harman gained the key.

### Reconciliation is the dangerous part, not fetching

`reconcile_company_jobs` deactivates every active row it does not find in
the fetched list. Scraping two URLs and reconciling twice would have the
second pass deactivate everything the first found. So **all URLs are
merged into one list and reconciled once.**

That leaves the partial case, which is the one to understand before
changing any of this. If a company lists four URLs and one fails, the jobs
behind the failed URL are missing through no fault of their own, and
deactivating them would silently empty part of that company's board.
`ScrapeResult.partial` now suppresses deactivation entirely — the same
caution `trust_empty` already applies to an empty fetch. Jobs go stale
rather than vanishing, and the next clean cycle reconciles them.

Verified for real, not just in tests: pointing one of Harman's extra URLs
at a 404 produced `jobs_found=24 deactivated=0 deactivation_skips=1` and
the board held at 26 rather than dropping to 24.

Merging de-duplicates on `identity_for_raw`, the identity reconciliation
itself uses, because query variants overlap heavily.

### Bounded, per the standing rule

At most `MAX_CAREERS_URLS` (6) URLs per company, and the whole company
shares a deadline of `per_company_timeout * 3`. URLs still unscraped when
it passes are recorded as errors and make the result partial rather than
being dropped silently. `_dedupe_shared_urls` also registers a company's
extra URLs, so another company naming one as its primary is skipped rather
than scraped into a second company row.

### Result

Harman 16 board rows -> **26**, `deactivated=0`, new rows categorising as
audio_systems, transducers and audio_dsp_embedded, countries DE/US/IN/PL/HU.
A second run inserts nothing and deactivates nothing.

### Adding more companies

Measure before editing the seed. Fetch each candidate URL, strip the
board's navigation anchors, and check the union actually grows — for
Harman, two of the eight queries tried returned nothing at all. Keep the
list short; the cap is 6 including the primary.

## Session update (2026-09-03, later still) — open applications, and two rejections

### Perennial "write to HR" companies (commits 7e7378a, b79ae9d, 107d0e7, 7c602a1)

Some companies post no roles but invite speculative applications.
`Company.open_application` marks them, and the board shows them in a
labelled section below the job list.

**Modelled as a company attribute, not a job row.** They have no title, no
posted date and no expiry, so a Job row would have to be exempted from
relevance scoring and from reconciliation — the deactivation hazard the
partial-fetch work had just exposed. Keeping them out of the `jobs` table
means they never touch pagination, filters, sorting or the result count.

**An invitation is not an empty board.** 17 diagnosed pages say the
opposite — "no open positions, check back" — and Ableton and Waves are
among them. Flagging those would invent an offer the company never made.
The detector treats a no-openings marker as disqualifying on its own, and
reports a page carrying both signals in a separate section for a human.

`python -m scraper.propose_open_applications --from-cache DIR` is
**read-only** and consumes the HTML cache from
`diagnose_failures --html-cache DIR`. It proposes; the seed decides. That
split matters: 3 of the 19 matches were junk from bad seed data rather
than bad detection.

15 of 19 were flagged after reading each page. Rejected, with reasons:

| Rejected | Why |
|---|---|
| World Wide Stereo | "See our open positions below… send your resume" is application instructions for listed roles. An extractor gap, not a perennial company. |
| Embracer Group | Invites applications for finance, governance and sustainability functions. |
| Energica Motor | Electric motorcycles. |
| Joué | **Its careers_url points at joueclub.fr, a French toy retailer**, not Joué the MIDI controller maker. Seed bug, still unfixed. |

Blocked pages are never proposed — Peavey matches the invitation regex
only because Cloudflare's block page is what gets fetched.

### Headings-as-jobs — MEASURED AND REJECTED, do not build

Yamaha's internship page lists six real roles as `<h3>` headings with no
links, which looked like a generic extraction gap. Across all 313
diagnosed pages, **only 6 have two or more role-like headings and no job
anchors, and 3 of those 6 are false positives**: SPL would post "Visit us
at beatcon and join the Hip-Hop Producer Contest", Arturia would post
hiring-process steps ("Application check by HR and manager"), Meridian
would post marketing copy. The three genuine ones yield about ten roles.
A 50% false-positive rate for ten roles is the same trade item 10 failed.

### Yamaha's internships are one community submission, not six

Approval de-duplicates community jobs by `(company, url)`, and Yamaha
publishes all six projects on one page. Six submissions would collapse
into one, each superseding the last. The tab anchors do not help: loading
`#_tab02-02` leaves that panel `display: none`, so a deep link lands the
reader on the wrong tab. Fabricating per-project fragments would invent
links that resolve nowhere useful.

So submission id 1 is one entry naming all six projects in its
description, which `/api/jobs` search still matches because it searches
description as well as title. **It is pending — it reaches the board only
when an admin approves it.** Applications open 28 Sept 2026, due 18 Nov
2026, term Summer–Autumn 2027.

### Route ordering

`/api/companies/open-applications` is registered **before** `/{slug}`.
FastAPI matches in declaration order, so behind the slug route it would be
read as a company named "open-applications" and 404. A test pins it.

## Session update (2026-09-03, evening) — the cycle, and a duplicate that was hiding

### The full cycle landed all three owed changes

See item 0 for the numbers. Country coverage went 69% -> 83% and the
prediction made on a copy (434/525) held on the live board (442/535).

### One job reached by two seeded queries was two jobs (commits f4b0115, 21ab204)

A board that answers a search query echoes that query back into every job
URL it returns, and job identity is the URL. So the same posting fetched
under `?q=audio` and `?q=dsp` merged as two jobs.

**Harman had this live and nobody had noticed.** Its "Create Account" link
was stored five times, once per seeded query. Every copy was below the
relevance cutoff, so no reader ever saw one — which is exactly why it
survived. Look for defects in the rows the board filters out, not only in
the rows it shows.

The first fix stripped the query keys that appear in the company's own
seeded URLs. **It was not enough, and the live database caught it, not the
tests.** Pagination echoes its own parameter too, so a job on page 1 of
`?q=audio` and page 2 of `?q=dsp` still merged as two: Google came back at
18 board rows instead of the measured 16, with two visible duplicates. The
ignore set now also covers `page`, `pg`, `offset` and `start`.

The stripping is deliberately narrow, because collapsing two real jobs is
worse than a duplicate:

- it applies only to companies with more than one seed URL, so a single-URL
  company is untouched;
- a job id carried in any other parameter still separates two postings
  (`?gh_jid=111` vs `?gh_jid=222`), and there is a test for exactly that;
- the tests were sabotage-verified — reverting the pipeline line fails them.

Stale rows self-heal: the next cycle for that company deactivates the
duplicates, which is what Google (36 deactivated) and Harman (4) did.

### Exact-duplicate stored rows exist but are not worth fixing

Two rows board-wide share a company and URL and are both active — reconcile
keys existing rows by identity, so a historical duplicate stays alive
forever. Both are below the relevance cutoff. Measured at 2 surplus rows, 0
on the board. Do not build anything for this.

### Diagnose can select successful companies (commit e402226)

`--status failed|success|all`. The open-application sweep could only ever
see the diagnosed failures because selection was hard-wired to the latest
log being `failed`. The query moved into `select_companies(session, status)`
so it is testable against an in-memory database.

### The Yamaha submission is still pending

Approve it at `/admin/submissions` in the web admin. Pre-checked with the
normalizer: it scores 140, files as `audio_aiml` + `audio_dsp_embedded` +
`audio_systems`, resolves to JP, and will reach the board. Note it gets a
30-day `expires_date` from `COMMUNITY_JOB_TTL_DAYS`, which is short for a
2027 internship. A cycle cannot touch it — reconcile only handles rows with
`source='scraper'`.

## Session update (2026-09-03, night) — submission duration, and admin usability

### How long a community job stays up (commit 9a88e11, migration d3f5a72e9c14)

`job_submissions.requested_days` holds what the submitter asked for; it is a
request, not a setting, and nothing is applied until approval. The approve
endpoint takes an optional body `{"expires_days": N}`. Precedence is
`resolve_expiry_days`: moderator, then submitter, then
`COMMUNITY_JOB_TTL_DAYS` (30). The response reports `expires_source` so the
console can say which one applied.

Range is 1 to `MAX_COMMUNITY_JOB_DAYS` (365, env-overridable), enforced at
the schema boundary **and** clamped again in `resolve_expiry_days`, because a
value stored today outlives any later change to the maximum.

**A blank duration field posts `duration_days: null`, it is not omitted.**
Verified in the browser by intercepting the request, not by reading the code.
Svelte's number binding yields null for an empty input, and the schema is
`Optional[int]`, so it lands as NULL and falls through to the default. If
anyone ever makes this field required, that null becomes a 422.

### Re-approving a submission refreshes the live job in place

The defect: approving a second submission whose URL already had a live
community job set `duplicate.is_active = False` and, because the insert sat
in the `else` branch, never added the replacement. The listing vanished and
the API still answered `approved`.

The owner chose refresh-in-place over supersede. `refresh_community_job`
updates the existing row — content, expiry, relevance — and returns its id.
**The deciding factor was bookmarks**, which are a `Set<number>` of job ids
in the reader's `localStorage` and device-local by the owner's decision.
Inserting a replacement row would issue a new id and silently orphan every
bookmark on that job, with no server-side way to repair it.

**This is the fourth write site for `job_categories` / `is_audio_related` on
an existing row**, so it consults `effective_categories` and
`effective_is_audio` like the other three. Sabotage-verified: dropping either
call fails two tests in `api/tests/test_reapproval.py`. If you add a fifth,
wire it in.

`find_live_community_job` also closed the mirror-image gap: the duplicate
lookup used to run only when `submission.company_id` was set, so repeat
submissions for a company absent from the seed stacked up as separate live
rows. It now matches on URL for those too, scoped to rows with no company so
an unmatched submission can never seize a known company's listing.

Community jobs now store `country`, which the insert path never set. The
Yamaha submission resolves to JP and would have landed with a NULL country
and no flag on the board.

### The admin company table shows scraped and board counts separately

**The "Open jobs" column never meant what it looked like.** It counted every
active row the scraper holds, junk included, and readers of that column —
including me, in this session — read it as board presence. Live numbers:
4,990 active rows against 540 on the board, and **319 of the 401 companies
with any rows contribute nothing to the board at all**. Niantic held 180 rows
and put 0 on the board; NVIDIA's 6 were "Find Your Next Job", "Applicant
Privacy Policy", "How We Hire" and three more of the same, because its seed
URL is a careers landing page rather than a board.

The table now has **Scraped** and **On board** as separate sortable columns,
both ordered in SQL. Sorting by board gives an entirely different top —
Shure 97, Apple 69, Beltone 38 — and reading the two side by side is the
fastest way to spot a seed URL pointed at the wrong page.

### Company admin sorts by job count and by verified

`companies_with_counts` takes `sort` (name/jobs/verified) and `direction`.
The count was already a joined SQL subquery, so this is an ORDER BY, not a
Python sort — it orders the whole table, not the current page. Every sort
except name falls back to name for ties, so paging is stable.

The route constrains both with a regex pattern, and the function falls back
to name/asc for anything unrecognised, so a bad value cannot reach the query
builder from either direction.

Headers are buttons carrying `aria-sort`. First click on Open jobs and
Verified sorts descending (most jobs, verified first), name sorts ascending.
Sorting resets to page 1, and search keeps the sort.

### Admin console (commit 8a7b9ed)

- The careers URL on `/admin/companies` is a real link that opens in a new
  tab, with a separate Edit button; the inline editor gained Cancel. It used
  to be a button that only started an edit, so reading a URL meant copying it
  out by hand.
- That page was capped at 50 rows with no way to page. It now has Prev/Next
  and a "Page X of Y - N companies" readout, and searching resets to page 1 —
  without that, a search from page 7 shows an empty table.
- `/admin/submissions` shows the requested duration per card and offers a
  per-card Days override. The override state is keyed by submission id, not a
  single shared variable, so two pending cards cannot overwrite each other.

Verified in the running app with `fetch` intercepted, so no submission was
approved and nothing reached the database: a filled field sends
`{"expires_days": 300}`, a blank one sends `{}`.

## Session update (2026-09-03, night) — Apple ignored its own seed URL

### The Apple parser hardcoded its search query

`AppleScraper.can_handle` matches on the `jobs.apple.com` host, and the
parser then fetched `?search=audio` regardless of what the seed said. The
seeded careers URL decided *which parser ran* and nothing else, so
`extra_careers_urls` could not reach Apple at all — every extra URL produced
the same audio search.

`search_term()` now reads `?search=` from the company's careers URL and falls
back to `audio`, so extras work through the existing multi-URL machinery. The
term is length-bounded at 40 characters and URL-encoded, so a term with a
space cannot break the request.

**Measured before seeding, the way Harman and Dolby were.** Fetching each
alternative query and running the real scorer over whatever the audio query
did not already return:

| Query | New rows | Would reach the board |
|---|---|---|
| speech | 41 | 7 |
| acoustic | 28 | 4 |
| dsp | 111 | 1 |
| sound | 105 | 1, and it duplicates acoustic's |

`speech` and `acoustic` were seeded. `dsp` and `sound` were rejected: Apple's
search matches loosely, so `sound` returns retail store managers and `dsp`
returns Bluetooth and RF firmware. 216 rows for one unique addition.

Result on the live board: **69 -> 76**, nine new rows in (Siri Speech, Noise
& Vibration Acoustics) and two stale ones deactivated. Apple sets
`external_id`, so identity never depended on the URL here and no duplicates
appeared. The predicted +11 came in at +7 because Apple's listings shift
between runs.

### What the admin "Scraped" column means for Apple

221 was never Apple's job count — it is how many results Apple's own search
returns for one word. The parser pages 20 at a time to a 20-page ceiling it
has never approached, then fetches each detail page for the full description
at 8 concurrent, bounded to 85% of `per_company_timeout`. A cycle that
exhausts that budget (196/221 last time) costs detail, not the description:
the search page itself supplies one, and Apple's shortest stored description
is 489 characters.

## Next steps, in priority order (as of 2026-08-31)

0b. **Run the API with reload, and watch both packages.** Without `--reload`
   the dev server serves stale code for days — it sat on three-day-old code on
   2026-09-02 and the new feedback routes 404'd until it was restarted.

   ```
   cd api && ../venv/bin/uvicorn api.main:app --port 8000 \
       --reload --reload-dir . --reload-dir ../scraper/scraper
   ```

   **The second `--reload-dir` is the one that matters.** Plain `--reload`
   watches only the working directory, so running from `api/` it watches
   `api/` alone. `api/__init__.py` puts the scraper directory on `sys.path`,
   so the API imports models from outside that tree — and the change that
   broke it on 2026-09-03 was in `scraper/scraper/models.py`. Plain `--reload`
   would have looked like it was working and still served stale code.

0. **The database is current with the code (2026-09-03, evening).** The cycle
   ran: 690 companies, 394 ok / 296 failed, 1,477s, jobs_found 4,900,
   inserted 591, updated 4,309, reactivated 21, deactivated 231,
   deactivation_skips 0. All three owed changes landed and were verified
   against the live database afterwards:

   | Measure | Before | After |
   |---|---|---|
   | board rows | 512 | 535 |
   | board rows with a country | 355 (69%) | 442 (83%) |
   | distinct countries | 21 | 29 |
   | Harman | 16 | 26 |
   | contributing companies | 80 | 82 |

   Google and Harman were re-scraped individually afterwards for the query
   identity fix, so their rows are newer than the rest.

   Two seed edits landed after that cycle and are **already synced** into the
   database by a `--limit 1` run (the loader syncs every company regardless of
   limit): Google's `?q=dsp` extra URL and 23 new `open_application` flags.
   Nothing else is owed.


1. **Company case studies — what the owner is doing next.** The owner works by
   naming companies they expect to see on the board and asking why they are
   missing. Four such studies on 2026-08-29 recovered 31 jobs; run the same play:

   - `python -m scraper.check_url "<url>" --name "<Company>"` — read-only,
     writes nothing, reports method, jobs found, and how many would reach the
     board. See "Correcting a careers URL by hand" above.
   - **Read the sample titles it prints; do not just read the counts.** Three of
     those four companies were reporting `success` with healthy `jobs_found`
     while holding nothing but navigation furniture.
   - **The prior is that it is a seed problem, not a scraper bug.** Of four
     studies, one was a scraper defect and three were wrong careers URLs.
   - For a huge partial-scope employer, **scope the seed to a search query** —
     the established pattern for Meta, Google and Harman (`?q=audio`,
     `?search=audio`).
   - When a study leads to a fix, check whether it generalises before declaring
     it done. Both bugs fixed on 2026-08-31 had populations several times larger
     than the first query suggested.

   `SEED_WORKLIST.md` holds the 82 companies whose failure is a wrong careers
   URL rather than a scraper limit, with slugs, ordered by engineering
   relevance. The proposal tool cannot help here — see "Step 1 of the seed
   plan" — so this is human work.

   Note `last_scraped_at` is written **only on success**, so a company showing
   "never scraped" has actually failed every attempt; it was not skipped. Do not
   read that column as omission. After commit 647b721 roughly 101 more companies
   report failure honestly rather than succeeding with zero jobs.

2. **`json_endpoint` is mostly a false-positive bucket — do not build a parser
   for it.** An earlier version of this document called it the largest untried
   technical lever at 42 companies. That was wrong, and reading the endpoints
   settles it. They are WooCommerce cart fragments (`?wc-ajax=get_refreshed_
   fragments` at Celestion, Make Noise, Tempo Semiconductor), a localisation CDN
   (Antares), an ad network (Last.fm/revcontent), product pages (iFi's
   `zen-dac-3.json`, Cycling '74's `products/max.json`), Wix tag manager (Geneva
   Lab, VPI), VK's help hints, Fox's DRM keygen, generic `wp-json` and
   `admin-ajax.php`. Roughly six look like real career APIs: Anghami (ZenATS),
   Neural DSP (Revolut People), Oppo, Smilegate, Firaxis (Nuxt `_payload.json`)
   and DALI (Gatsby `page-data.json`) — each a different vendor, so there is no
   shared parser to write.

   `is_job_endpoint` is firing on any JSON request from a page with careers
   vocabulary. This is the same failure the "cloudflare"/"captcha" markers had:
   **a request is not evidence of its content.** Tightening it is worthwhile so
   the bucket stops overstating itself, but the opportunity behind it is not
   there. The remaining ATS platforms are down to 1-2 companies each (jobvite 2,
   oraclecloud 2, then ukg, paylocity, breezy, teamtailor, jazzhr at 1 apiece).
   Note `breezy` has 3 companies with a stored `ats_type` but **no parser
   exists**, so they fall through to HTTP.

   The audit was not wasted: two of the 42 were classified there because the page
   fetched a *localisation file from greenhouse's CDN*, which exposed that
   Greenhouse's EU region hosts were undetectable (commit 88b498d). Worth
   re-reading the bucket for that kind of side evidence rather than for endpoints.

3. **Seed URL quality remains the cheapest lever** — see 3b and 3e. Keysight is a
   worked example: the board had moved and no scraper change could have fixed it.

4. **Categorization, the original pain point #1.** 126 board rows carry no
   category (2026-09-02, after the full cycle took the board to 512; it was 104
   of 476 before). Categories are how a reader filters
   past the junk the board now deliberately admits, so this is worth doing — but
   the obvious fix is already ruled out.

   **Shure alone accounts for roughly a third**, then Bose 8, Suno AI 7, Apple 7 —
   four companies hold half. But read the next paragraph before spending time on
   them.

   Note the Test, Measurement & QA work (night session) shows the shape of a
   safe fix here: gate any new categorization on the row **already** having
   scored an audio category, so it re-files rather than admits. That is what
   separates it from the rejected experiment below.

   **`metrology` alone was re-tested and shipped (commit below) — the rejection
   applies to the bundle, not to every word in it.** Adding `metrology` and
   `calibration` to the fallback rule re-categorized exactly 2 rows (Shure's two
   metrology roles), both already on the board, **0 newly admitted**. `systems`
   and `process` are the words that pulled junk in; they stay rejected. Measure
   words individually before treating the whole list as poisoned.

   **Also: "uncategorized" at a native-scope audio company is mostly a relevance
   symptom, not a categorization gap.** Of Shure's 34, the bulk are Security
   Operations, Market Development, Sales Development, Cloud Operations, Event
   Management and Pre-sales — roles with no audio category because none applies.
   They reach the board on 7,000-character descriptions saturated with audio
   words at a native-scope company. Reading them hunting for missing keywords is
   work in the wrong direction; the lever is relevance, or `CORPORATE_ROLE`
   coverage. Same at Suno AI and Bose.

   **REJECTED, do not retry:** extending `FALLBACK_ROLE_CATEGORIES` with
   `systems`, `process`, `metrology` and `npi`. Measured in commit 89ddf50 — it
   categorized 16 rows and would have put six on the board, four of them Modal
   Labs cloud jobs arriving through a since-fixed seed error. It also fails to
   reach the case that motivated it: Audinate's "Principal Engineer" contains no
   systems or process word either.

   **The bare "acoustics" gap is closed (commit 4cabea3).** The owner assigned
   it to `audio_systems`, and the same commit gave `loudspeaker` and
   `studio monitor` an `audio_systems` entry beside their transducers one. 14
   board rows changed, 6 of them from no category at all; uncategorized board
   rows went 110 -> 104. Nothing new was admitted. See the 2026-09-02 session
   update for the method, which is the one to copy for the rest of this item.

5. **User feedback — BUILT 2026-09-02 (commits 9dacaf2, 55c17ee, 04bf832).**
   The owner un-deferred it. What shipped is below; what remains is operational,
   not code.

   Two tables, not one: `job_feedback` (kinds `wrong_category`, `not_audio`,
   `broken_description`, `broken_link`) and `site_feedback` (kinds
   `company_suggestion`, `general`). A company suggestion has no `job_id`, so
   forcing both through one table would mean a nullable FK plus kind-dependent
   validation on every row.

   Entry points: job cards on `/jobs` (two kinds), the listing aside (all four),
   and the footer (site kinds) — the footer is in the root layout, so it reaches
   every page and passes `page_path`. One `FeedbackDialog` serves all three and
   lives on the page, never inside `JobStrip`; mounting it per card would put
   twenty modals on a default board page.

   Public POSTs are rate-limited by IP at 20/day, a separate limiter instance
   from the 3/day one on job submissions. Suggested category ids are validated
   against `data/audio_job_categories.json`.

   **The trap, and how it was closed.** Every scrape cycle re-normalizes and
   re-scores each job, and `backfill_relevance` rewrites `job_categories` and
   `is_audio_related` wholesale — so a hand-approved fix would live only until
   the next run and then vanish, with nothing in any log to explain it.

   `Job` now carries `categories_override` and `is_audio_related_override`, both
   nullable, and `scraper/scraper/overrides.py` is consulted at **all three**
   sites that write those columns on an existing row: the `deduplicator` update
   path, `backfill_relevance`, and `rescore_company_jobs` in the admin router.
   The insert paths are deliberately untouched — a new row cannot carry an
   override yet. **If you add a fourth write site, wire it in or corrections
   start silently reverting again.**

   `tests/test_overrides.py` runs the real `backfill()` and the real
   `reconcile_company_jobs`, not the helpers in isolation, and covers the
   direction that matters most: a job the scorer keeps admitting, held off the
   board by a `not_audio` override. One test asserts the fixture scores as audio
   *without* an override so the rest cannot pass vacuously. Removing either call
   site fails five of them — verified by sabotage, not by assumption.

   Approve semantics: `not_audio` sets the override false; `wrong_category`
   writes the suggested ids; `broken_link` and `broken_description` **never touch
   the job**, by the owner's decision — an anonymous report must not be able to
   hide a listing. Repairing those means fixing the seed URL or re-scraping by
   hand.

   Known small inconsistency: `rescore_company_jobs` recomputes `relevance_score`
   from the *computed* categories, not from `categories_override`, because
   `Normalizer.normalize` derives both together. `backfill_relevance` does feed
   the override in. The drift is cosmetic — the board gate is
   `is_audio_related`, which is overridden — and a backfill resolves it.

   Operational note: the API must be restarted to pick up the new routes.

   Second, larger payoff: **approved feedback is a measurement set.** Aggregated
   "wrong category" reports point straight at systematic keyword gaps — the
   acoustics gap is exactly the kind of thing a handful of reports would have
   surfaced without anyone reading 99 rows by hand. Worth reviewing periodically
   rather than only acting on individual rows.

6. **Known and deliberately not fixed.** XR audio roles at Google file as
   `game_audio_interactive`, which is wrong for headset platform work — it does
   not affect whether they reach the board, only how they are filed, and fixing
   it is the same taxonomy decision as bare "acoustics" in item 4. Hearing-device
   *measurement* roles score `audiology_hearing` at 3 against a cutoff of 5 and
   so file as test only; raising that means touching the shared scoring curve.
   The stray 0-byte `scraper/asoundjob.db` is **deleted (2026-09-02, commit
   72633a8)**. It could
   not recur: `resolve_database_url` in `database.py` already anchors a relative
   sqlite path to `REPO_ROOT`, so the working directory no longer decides which
   database you get. That behaviour had no test; it has four now
   (`tests/test_database_url.py`). The file was debris from before the fix.

7. **Link checker — BUILT (commit f94492f).** `python -m scraper.check_links`.
   It also detects a 2xx that serves the wrong document — see the 2026-09-02
   update. Latest sweep: 459 URLs, 452 ok, 0 broken, 0 wrong content.
   Worth re-running after any scrape and after any seed batch; it is read-only
   and takes about a minute. See the session update above for the HEAD-versus-GET
   trap it exposed.

8. **Location extraction — the listing-page lever is now spent (2026-09-03).**
   The generic anchor path reads location from the job card as of commits
   8bdc635 and 390d8a9. Re-scraping the 40 affected companies took the board
   from 355 of 512 rows with a country to **434 of 525**, 69% to 83%, and from
   21 countries to 26. See the 2026-09-03 session update for the method.

   **Two claims this item used to make were wrong; do not act on them.**

   - "ADP (7 companies) and Pinpoint (1) return none" was true when written on
     2026-08-30 and is stale. ADP now locates 27 of 33 active rows and Pinpoint
     40 of 40, fixed as a side effect of the JSON-LD array work (e1142bf).
   - "The generic anchor path would need detail-page fetching" was too
     pessimistic for the listing page itself. The location was in the DOM the
     whole time; nothing read it.

   What remains is genuinely harder, and was measured rather than assumed. Of
   the 32 companies still holding an unlocated board row, **28 have no location
   anywhere within six ancestors of the job anchor** — their listing pages do
   not publish it. Only detail-page fetching reaches those, which "Detail-page
   fetching" already sized as a small population. Shure's 9 are a separate
   case: its iCIMS detail pages carry no JSON-LD JobPosting at all, so the
   existing iCIMS location path has nothing to read.

   **REJECTED, measured 2026-09-03: widening the card boundary to tolerate a
   second anchor.** The card scan stops at any container holding another job
   anchor, so a card with a title link plus an Apply link yields nothing. That
   sounded like the next gap. It reaches 14 anchors across 3 companies, worth
   about 2 board rows, and two of the three are false positives — Riedel's
   container is a job *list*, so widening it would staple one job's city onto a
   different job. That is the wrong-country failure the whole design avoids.
   Not worth it at that price.

   The parser is still not the constraint. Of the board rows that carry a
   location but resolve to no country, nearly all are correct refusals:
   "2 Locations", "Remote", "EMEA | Remote", "Canada, United States". The only
   real parser gaps found were bare city names absent from `CITY_COUNTRY`
   (Cincinnati 4 rows, SLC Triad Center 6, Paddington 2) and none of them are
   on the board. Adding cities is cheap but buys nothing today.

9. **Harman — CLOSED 2026-09-03 (commits 0c445c9, e533ff3, e5aa78b).** The
   diagnosis was right: Harman's search matches tokens exactly, so no single
   query reaches every role. The fix was the several-seeded-queries option, and
   it needed `extra_careers_urls` to exist first.

   `?search=audio` returned 16 real jobs. Adding acoustic, dsp, transducer and
   sound takes it to **26**, above the 24 this item was aiming at, verified end
   to end against a copy. `speaker` was measured and left out — its only find
   is "Transducer & Lab Engineer Speaker", which the transducer query already
   returns. `noise` and `signal processing` return nothing.

   **The Avature parser was never needed.** Do not build it for this reason.
   Avature remains a thin bucket (Harman, plus Motorola Mobility's
   `jobs.lenovo.com/en_US/careers`), and the page-size cap of 20 no longer
   binds because each query fits well inside it.

10. **Flattened titles on JS-rendered boards — CLOSED by measurement
    2026-09-03. Do not build this.** The paragraphs below are kept because they
    describe the mechanism accurately; the conclusion they reach is wrong, and
    the count at the end of the item is the thing to act on.

    On boards whose listings are cards rather than anchors, the extractor pulls
    the whole card into the title. Live examples:

    - Devialet: `Senior Audio System Engineer Full-Time Shenzhen...` — both of
      its board rows carry job type and location glued on.
    - Dolby before the Eightfold parser: `Multimodal AI Researcher, Audio
      Atlanta, Georgia,United States Hybrid Flexible Location`.

    The reasoning used to run: a mangled title defeats `classify_categories`,
    so the rows reach the board with no category, and categories are how a
    reader filters. That was a fair inference from Dolby's five uncategorized
    Playwright rows. It did not survive being counted — see below.

    Commit 03a8d00 took titles from structure rather than flattened anchor text
    and fixed the anchor case. The card case is not covered. Note the Eightfold
    parser (0bb4344) **routed around this rather than fixing it** — a per-ATS
    parser sidesteps the generic extractor entirely, so the class survives
    wherever no parser exists.

    **COUNTED 2026-09-03, and the answer closes this item.** The precise
    signature — an employment-type word mid-title followed by a short tail —
    matches **14 rows out of 4,615 active, 2 of them on the board**, and 11 of
    the 14 are Devialet. Dolby, the other example above, was fixed by the
    Eightfold parser. `job_type` is already set correctly on 13 of the 14, so
    the parse is not failing, only the title is left dirty.

    The claim that it costs categories does not survive either. Of the 126
    uncategorized board rows, 9 have a title carrying an employment word or a
    trailing place, and **every one of the 9 is a correctly extracted title** —
    "Senior Pre-sales Solutions Engineer (Pro Audio) - Pennsylvania",
    "KSL TV Studio Tech / Audio Tech (Part-Time)". They are uncategorized
    because they are sales and IT roles, which is item 4's relevance point, not
    a title defect.

    **Do not build a generic repair for this.** A naive strip is actively
    dangerous: the same pattern matches "Aerospace, Full-Time Lecturer,
    Faculty" and "EPS PartTime Lecturers", where cutting at the employment word
    destroys a correct title. Guarding it needs a gazetteer that recognises
    Chatelet-En-Brie and Courbevoie, which `CITY_COUNTRY` does not. The cost is
    a real risk to 4,601 correct titles for a cosmetic gain on 14.

11. **`ats_type` is stored for only 56 of 728 verified companies.** The reason
    is specific and worth knowing: `_try_discovery` is called only on the
    generic http/playwright/stealth paths in `ScrapePipeline.scrape_company`.
    When an ATS parser succeeds via `can_handle`, the loop returns immediately
    and nothing is ever persisted. So the 56 are the ones discovered on the
    generic path, and every company scraped by a working ATS parser stays NULL.

    **Measured 2026-09-03. Persisting it buys measurement, and nothing else.**
    Running `discover()` over each careers URL resolves an ATS for 87 of the
    521 successfully scraped companies and would newly populate 81, taking
    coverage to about 137 of 728. But every real duplicate group it finds —
    inMusic's nine Pinpoint brands, Focusrite's three, Logitech's three,
    Harley/LiveWire on ADP — **shares one careers URL and is already deduped by
    the URL half of the guard**. Every collision that was not already a URL
    duplicate turned out to be false. So this is worth doing to make ATS
    coverage measurable, not to catch duplicates.

    **The guard itself had a defect, now fixed (commit 4023298).** Arming more
    of it would have made things worse, because a stored identity was trusted
    without any check that it belonged to the company. Flowkey was being
    skipped against a CDN host slug and TrueFire against Toyota's Workday
    tenant — both scraped off the page by HTML discovery. A board claim now
    requires the company's own careers URL to resolve to that identity.
    Anything persisted from HTML alone can still lose a collision but can no
    longer win one. See the 2026-09-03 session update.

    If you do persist from URLs, note it is *safer* than what is stored today:
    URL-derived slugs cannot pick up a third party's board the way HTML
    discovery did. Two stale bad rows remain in the database — Flowkey's
    `breezy/assets-cdn` (today's `NON_BOARD_SUBDOMAIN_RE` would reject it, so
    it predates that guard) and TrueFire's Toyota tenant. They are now
    harmless, but they are still wrong.

12. **The two curation levers, worked (2026-09-03, evening).** Both were
    swept. What is left is narrower than this item used to claim.

    **Multi-query is a three-company lever, and two of the three are
    rejected.** Only four seed boards are query-scoped at all: Harman,
    Google, Dolby and Meta (Belden and Canoo carry an empty `q=`, and
    Switchcraft's keyword board is dead). Measured with the real pipeline,
    not `check_url` — see the warning below:

    - **Google: seeded `?q=dsp`.** Of audio/acoustic/dsp/sound/speech, only
      dsp adds anything, and all five additions are DSP or embedded roles.
      Board 11 -> 16.
    - **Dolby: rejected.** Every query is a strict subset of `?query=audio`;
      Eightfold searches full text. acoustic returns 1 job, dsp 3, and both
      are already in the audio set.
    - **Meta: rejected, and for a reason worth remembering.** It serves the
      first query and blocks every one after it. Extra URLs would leave Meta
      permanently `partial`, and partial suppresses deactivation — so stale
      rows could never be removed. A silent failure, not a loud one.

    **`check_url` under-measures a company with a stored ATS identity.** It
    builds its Company from a name lookup that does not copy `ats_type` or
    `ats_slug`, so Dolby came back with 12 jobs where the live pipeline gets
    61. Measure query unions by constructing the Company the way `main.py`
    does, including the ATS columns.

    **Open applications: swept, 15 -> 38.** Probing the 438 companies whose
    last scrape succeeded found 31 pages inviting a speculative CV. 25 of
    them contribute nothing to the board despite scraping cleanly — those
    were flagged. The 6 that already show a listing were left alone rather
    than appear twice. Only 9 of the 31 matched on weak boilerplate, so the
    strong/weak marker split that looked necessary was not built.

    Audiolab, Quad Electronics and Wharfedale share one IAG Group careers
    page; only Audiolab is scraped, so it carries the flag for all three.

    **Still untouched: the regional careers site case.** There is no cheap
    signal for it. `companies.headquarters` is NULL for all 728 verified
    companies and the seed carries no country field, so a candidate list
    cannot be built from the database. It needs either the careers URL host
    TLD or human knowledge of which manufacturers run separate country
    sites.

13. **Seed careers URLs that are not careers pages — 38 entries, 32 verified
    (2026-09-03).** Item 12 used to ask whether Joué's wrong URL was unique.
    It is not. `python -m scraper.audit_seed_urls` (read-only, no network, no
    database) classifies them:

    - **15 are error, for-sale or press-release pages.** Cadence points at its
      own `accessdenied.html`, McIntosh at `Page-Not-Found`, Ubisoft and ZTE
      at `/404`, and Kush Audio, Powerbass and Vienna Acoustics at HugeDomains
      sale listings.
    - **23 point at an unrelated host.** Electro-Voice resolves to
      `ev.com/new-cars`, an electric-vehicle site that won the name collision;
      Roland points at a YouTube video; Metric Halo at an unrelated
      `mhsoftware.com` blog post.

    **`check_links` cannot catch these and never will** — they return HTTP
    200. Spot-checked: flik.com's page is titled "404 - page not found" and
    returns 200, HugeDomains returns 200 for a sale page. That is why the last
    link sweep reported 452 ok, 0 broken.

    The tool also reports a fourth bucket it deliberately does not list: 115
    entries whose host does not match the company name but whose URL is
    careers-shaped. Those are mostly correct parent-company boards (Beats ->
    apple.com, Audible -> amazon.jobs), which is why bucket A needs a human
    eye too — Soundtrap -> lifeatspotify.com is a correct URL the heuristic
    flags.

    Nothing here is fixed. The seed is hand-edited truth.


Explicitly NOT worth doing, all measured rather than assumed: follow-one-link
(section 3 above — note this is *not* the same as the pagination that shipped in
458ebd4), further sweeps of the unverified population (3d and 3e), a
`json_endpoint` parser (item 2), and a Meta GraphQL parser (see the late-session
section — it returns 19 jobs against the DOM's 10 but the same 3 board jobs).

## How to measure changes

Run the new logic over the live DB rather than trusting unit tests alone:

```python
import sqlite3, sys, collections
sys.path.insert(0, 'scraper')
from scraper.normalizer import classify_categories, score_relevance
db = sqlite3.connect('asoundjob.db')
rows = db.execute("""select j.title, j.description, c.name, c.audio_scope
                     from jobs j left join companies c on c.id=j.company_id
                     where j.is_active=1""").fetchall()
```

Regression set that must keep passing:

- MUST be categorized: `Audio Software Engineer` @ Valve -> audio_software;
  `Core Audio Software Engineer` @ Apple -> audio_software;
  `Audio Machine Learning Engineer` @ Apple -> audio_aiml;
  `DSP Developer` @ Softube -> audio_dsp_embedded;
  `Acoustic Test Engineer II` -> test_measurement_qa;
  `Test Engineer UK` @ SSL -> test_measurement_qa
- MUST stay uncategorized and off the board: bare `Test Engineer`, `QA
  Engineer`, `Quality Engineer`, `Metrology Technician` with no audio context
- MUST NOT be audio-related: DLR Group "Studio Leader" jobs; Sky Studios
  "CDN Engineer"; RingCentral "Senior Finance Analyst"
- MUST NOT carry the listed category: Deepgram "Sales Development
  Representative" (not audio_aiml); Suno "Songwriting Camp Manager" (not
  audio_dsp_embedded); Akai "Copywriter" (not music_technology); Razer
  "Computer Vision Intern" (not audio_aiml)
