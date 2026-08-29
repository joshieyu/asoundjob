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
| `data/audio_job_categories.json` | 20 category definitions (source of truth) |
| `scraper/scraper/diagnose_failures.py` | Read-only: why a careers page yields no jobs |
| `scraper/scraper/discover_careers_urls.py` | Read-only: proposes corrected careers URLs |
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

## Current metrics (after the 2026-08-29 evening full scrape)

| Metric | Value |
|---|---|
| Total job rows | 7,198 |
| Active | 4,085 |
| Audio-related (the public board) | 385 |
| Board jobs carrying a real description | 328 (85%) |
| Uncategorized audio jobs | 105 (27%) — see the trade below |
| Companies appearing on the board | 61 |
| Companies contributing active jobs | 373 |
| Tests | 362 pass; ruff, mypy clean |

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

Not scoring strictness. **63% of excluded jobs (2,146) have no description at
all.** The 10 ATS parsers return full descriptions; the generic HTTP/Playwright
path returns titles and URLs only. With no description the only signal is the
title, so a job is excluded unless its title literally contains an audio word.
This is why only 42 of 361 contributing companies reach the board — in practice
the board is the ATS-covered companies plus anyone whose titles say "audio".

Last scrape: 696 companies, 427 ok, 269 failed with "page loaded but no job
links found". Sampling 35 of those failures and comparing the old vs new
extractor showed only one recovered, so those pages genuinely yield nothing to
HTML anchor scraping.

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

## Next steps, in priority order (as of the evening of 2026-08-29)

1. **The generic path is now the whole game.** 264 of 698 companies still fail,
   overwhelmingly with "page loaded but no job links found", and `last_scraped_at`
   is written **only on success** — so a company showing "never scraped" has
   actually failed every attempt, it was not skipped. Do not read that column as
   omission.

2. **`json_endpoint` is the largest untried technical bucket** (41 of 279 in the
   diagnostic, ~15%). These are pages where a job-shaped XHR was actually
   observed, so the endpoint is already identified per company. That is a much
   better-evidenced starting point than the remaining ATS platforms, which are
   now down to 1-2 companies each (jobvite 2, oraclecloud 2, then ukg, paylocity,
   breezy, teamtailor, jazzhr at 1 apiece). Note `breezy` has 3 companies with a
   stored `ats_type` but **no parser exists**, so they fall through to HTTP.

3. **Seed URL quality remains the cheapest lever** — see 3b and 3e. Keysight is a
   worked example: the board had moved and no scraper change could have fixed it.

4. **Categorization, the original pain point #1.** 105 board rows carry no
   category. Two separable causes: titles with an obvious audio word that match
   no keyword (Apple, Comsol, Otter.ai, Focusrite — a `CATEGORY_KEYWORDS` gap),
   and technical titles admitted by company context whose role word is missing
   from `FALLBACK_ROLE_CATEGORIES` (`systems`, `process`, `metrology`, `npi`,
   `maintenance`). Worth doing because categories are how a reader filters past
   the junk the board now deliberately admits.

Explicitly NOT worth doing, both measured rather than assumed: follow-one-link
(section 3 above) and further sweeps of the unverified population (3d and 3e).

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
  `DSP Developer` @ Softube -> audio_dsp_embedded
- MUST NOT be audio-related: DLR Group "Studio Leader" jobs; Sky Studios
  "CDN Engineer"; RingCentral "Senior Finance Analyst"
- MUST NOT carry the listed category: Deepgram "Sales Development
  Representative" (not audio_aiml); Suno "Songwriting Camp Manager" (not
  audio_dsp_embedded); Akai "Copywriter" (not music_technology); Razer
  "Computer Vision Intern" (not audio_aiml)
