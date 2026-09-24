# ASoundJob — Handoff

Rewritten 2026-09-24 from a 7,910-line chronological log. **The full log is in
git:** `git show 0286282:HANDOFF.md` (grep it for the history behind any decision
below). Keep this file topical: fold anything durable into the sections, and add
only short dated entries to the Log at the bottom.

## 1. Where things stand

An audio-industry job board for Young Audio Professionals (YAP). A scraper visits
the careers pages of seeded companies, a relevance model decides which jobs reach
the public board, and a SvelteKit site serves them. Branch
`redesign-type-specimen`.

As of the 2026-09-22 cycle:

| | |
| --- | --- |
| companies in the seed / DB | 1,412 (745 verified, 30 `source: manual`, 15 `scrape_blocked`) |
| scrape population (verified, unblocked, has URL) | 732; a cycle scrapes ~710 after shared-URL dedup |
| cycle | ~26 min; ok 364 / failed 346 — ~50% failure is normal |
| job rows / active / board-eligible | 20,474 / 12,308 / 1,014 |
| **publicly listed** | **997** (17 hidden as stale: Ramboll 16, Fairphone 1) |
| companies contributing to the board | 136; top: Shure ~101, Apple 70, Qualcomm 61, Cirrus Logic 59, Amazon 56, Bose 38 |
| health grades (scraped) | healthy 96, idle 149, failing 348, furniture 46, silent 32, thin 61; unscraped 680 |

**Not launched.** No Dockerfile, compose file or nginx config; nothing has ever
run on PostgreSQL (none installed locally, nor Docker). **~355 commits on this
branch are not on `main`** (last touched 2026-08-28); PR #1 from 2026-08-29 is
open and stale.

Where to look: `README.md` (running, gates, data flow, every tool),
`AGENTS.md` (original build plan and rules), `TRIAGE.md` (seed-URL worklist),
`PRODUCT.md` / `REDESIGN-BRIEF.md` / `DESIGN.md` (product and design authority).

## 2. Decisions waiting on the owner

1. **SQLite or PostgreSQL in production.** Recommended SQLite for launch: one
   machine, one nightly writer, ~20k rows, backup is a file copy, and it removes
   the dialect bug in §5 entirely. AGENTS.md says PostgreSQL.
2. **Domain** — `SITE_URL`, canonicals and the sitemap depend on it.
3. **Launch scope** — `/resources` and `/resources/interview-prep` still render
   `Wip.svelte` (AGENTS.md originally planned to ship them that way).
4. **How to merge** this branch into `main`.
5. **Who the board is for.** `PRODUCT.md` (2026-09-11) says everyone working in
   audio — "sales/marketing/CS roles at audio companies all belong" — and says it
   supersedes "the audience is audio engineers". The owner's later calls went the
   other way: all sales titles cut (2026-09-18), hearing-aid retail and clinical
   roles cut (2026-09-20). The relevance model follows the later calls. One of the
   two needs updating.
6. **Wordmark stroke weight** (10 vs 12) is undecided, and
   `assets/logo/kernels.py` is out of sync with the shipped `asj-edited.svg`.
7. Whether to delete the stale files in §8.

## 3. Standing rules

- **Gates, all must pass before any commit:**
  `cd scraper && source ../venv/bin/activate && python -m unittest discover -s tests && ruff check . && mypy scraper`,
  the same in `api/` with `mypy api`, and `npm --prefix web run check`.
- **Commit per phase, push per group.** **No code comments.** **Python 3.9** —
  `from __future__ import annotations`, `Optional[X]`, never 3.10 syntax.
  **Every regex quantifier bounded** (an unbounded one once took 57s on one page).
- **Implementation work goes to subagents on cheaper models.** Every subagent spec
  must forbid `git checkout`/`restore`/`stash`/`reset`/`clean` on
  `data/audio_companies_final.json`, say that a modified seed in `git status` is
  expected and not theirs, forbid `git add -A`, and forbid creating, overwriting or
  deleting anything under `/private/tmp/claude-501/**/scratchpad/`.
- **The seed file is hand-maintained and often carries uncommitted owner work.**
  Never run those git commands on it; stage it by name only. A subagent once
  discarded real edits this way and invented an explanation.
- **The scraper never writes the seed.** Only the admin panel (via the API) and
  human hand-edits do.
- **Diagnostic and proposal tools are strictly read-only** on the database and seed.
- **Concurrency:** Playwright ≤5, HTTP ≤50; per-job enrichment is always
  time-bounded against `per_company_timeout` (90s) or it cancels the company.
- **Recall over precision** on relevance. **Country parsing inverts it:** ambiguity
  resolves to NULL, because a wrong country hides a job worse than a missing one.
- Bare "acoustics" files to `audio_systems`. Bookmarks stay device-local
  (`localStorage` key `asj:bookmarks`), no accounts.
- **API tests never use `fastapi.testclient`** (no httpx); they call router/query
  functions against in-memory SQLite.
- **The admin panel is authoritative** — the owner wants it useful without running
  backend utilities once the site is live.
- **Kill servers by PID from `lsof -ti :<port>`, never `pkill -f uvicorn`** — that
  once killed the owner's API instead of the agent's own dead one.
- **Measure before acting.** Verify changes against the live database, by name
  rather than by count; run `check_url` before applying any URL; and before
  handing the owner any generated worklist, cross-check it against what they
  already know (what is on the board, what is `source: manual`).

## 4. How it works

### 4.1 The seed, the loader and the admin panel

- Flow: `data/audio_companies_final.json` → `company_loader` (start of every cycle)
  → `companies` → scrape → `jobs` → API → web.
- **The seed is truth.** DB-only edits drift or revert unless the row is manual; a
  company deleted from the DB but left in the seed comes back next cycle.
  `prune_orphans` (dry run by default, `--apply`) is the only thing that deletes
  companies; it matches by name, never treats manual rows as orphans, and skips
  rows carrying human work (overrides, submissions, feedback).
- **The admin panel writes the seed** through `api/api/seed_file.py`
  (create/edit/rename/delete; atomic temp-file + `os.replace`). It is inert until
  the served app calls `seed_file.enable()` in `api/api/main.py`'s lifespan —
  deliberately, because a test once wrote throwaway companies into the real file.
- Editing any of `LOADER_MANAGED_FIELDS` (name, category, careers_url,
  extra_careers_urls, verified) in the panel sets `source: manual`. The loader's
  guard is `existing.source == "manual" and source != "manual"` — protection lasts
  only while **the seed** also says manual.
- **Key-presence semantics** for `description`, `headquarters`, `founded`,
  `community_links`, `website_url`, `logo_url`, `ats_type`, `ats_slug`: absent
  key leaves the DB value alone, present key wins, explicit `null` clears. Never
  use truthiness on these.
- **Renaming in the seed JSON orphans the old row** (the loader matches by
  lower-cased name); renaming in the panel is safe (slug fallback for manual rows).
- Seed format must round-trip `json.dumps(data, indent=2, ensure_ascii=False) + "\n"`,
  sorted by name case-insensitively, keys in `order_seed_entry` order.
- `audio_scope` is derived from `category` (`category_to_scope`): recategorising
  *is* the scope change. `Staffing & Recruiting Agencies` → `all`.
- **`verified` means only that an earlier agent found the URL resolving.** It still
  gates four things: what `run_cycle` scrapes, the public company directory, which
  companies the diagnostics examine, and whether jobs survive —
  `_deactivate_unverified_jobs` deactivates an unverified company's jobs at the
  next load (reversible by re-verifying and rescraping).
- `website_url`, `description` and `headquarters` are empty for every seed entry.
- `extra_careers_urls` (up to `MAX_CAREERS_URLS = 6` including the primary) are
  all fetched, then **reconciled once** — per-URL reconciliation would deactivate
  what the previous URL found.
- `open_application` is a company boolean, not a job row.
  `export_seed_edits` diffs DB against seed read-only.

### 4.2 The scrape pipeline (`scraper/scraper/scrapers/pipeline.py`)

- `_scrape_one`: stored ATS binding → any ATS parser whose `can_handle` matches
  the careers URL (SuccessFactors registered last, since it matches any host with
  a `/search` path) → `http` (skipped when `scrape_method == "playwright"`) →
  `playwright` → `playwright_stealth`. After each generic attempt,
  `_try_discovery` guesses an `(ats_type, slug)` from the HTML, probes it, and
  persists it only on success.
- **`ats_type` is a routing cache, not the mechanism** — every parser also matches
  on URL shape.
- ATS parsers (`scrapers/ats/`): adp (Workforce Now only), amazon, apple, ashby,
  bamboohr, eightfold, gibson, greenhouse, icims, jibe, lever, pinpoint,
  recruitee, sigma, smartrecruiters, successfactors, ultipro, workable, workday.
- ATS results are `trust_empty` (empty means no jobs); generic results never are.
  If a dedicated parser claimed a board and failed, the fallback result is
  `partial` so it cannot deactivate what it did not see.
- **Errors:** Playwright now records the page's HTTP status and reports
  `HTTP {status} for {url}` when nothing was found and status ≥ 400 (ignored when
  jobs are found — some SPAs 404 and still render a board). A failed stored or
  claiming ATS attempt is kept as `{ats} binding failed: …; careers page: …`.
  Discovery guesses are deliberately excluded — they are guesses, not bindings.
- **An http scrape that returns only nav chrome still counts as success** and
  never falls through to Playwright (Garmin, ByteDance, Tensor). When a company
  returns furniture, check `scrape_method` first.
- `_dedupe_shared_urls`: when companies share a board, only the first
  (alphabetical, case-sensitive) scrapes it, silently. Fix the losing sub-brand
  with `verified: false`. A company claims a stored ATS identity only if
  `discover()` on its own careers URL resolves to it.
- Pagination: generic `find_next_page` (same host, same-or-deeper path, differing
  query; ignores `<link rel=next>`), `MAX_PAGES = 10`; a verb-or-count
  "show more" pager. ATS caps: Workday 50 pages × 20 (limit >20 is rejected),
  Eightfold 20, UltiPro 10. `detect_truncation` models ATS caps only.
- **Query scoping is a per-company measurement, never a recipe.** "dsp" is signal
  at Qualcomm and Infineon, Delivery Service Partner at Amazon, an ad product at
  Adobe. Workday `?q=` maps to `searchText`; SmartRecruiters ORs two terms, ANDs
  three or more, and keeps quoted phrases literal; Radancy ranks the whole corpus
  rather than filtering; Amazon must carry `base_query`. Pick terms by scraping
  unfiltered once and keeping only terms that recover board rows others miss.
- Location comes only from an element labelled as location, never blind card
  text; multi-location cards join with `"; "`. JSON-LD `jobLocation` may be an
  array. `resolve_document_base()` applies wherever relative URLs are resolved.
- `--limit 0` means no limit. `--company <slug>` scrapes one company and bypasses
  `scrape_blocked`. `scrape_blocked` is honoured by `run_cycle`
  (`blocked_skipped=` in the summary).

### 4.3 Link extraction (`scrapers/link_extraction.py`)

- `LISTING_LABELS` (link text naming a list, e.g. "View Jobs") are dropped with no
  structural rescue; generic labels in `NON_JOB_TEXT` keep the rescue. Adding a
  label family to `NON_JOB_TEXT` made things worse once, because the rescue then
  substituted a plausible department name.
- `is_generic_listing_title` drops listing suffixes (≤5 words), CTA lead-ins (≤6)
  and saved/alerts titles (≤6), each only when no role noun is present. Checks run
  again **after** a structural rescue, and a rescued `#fragment` title must carry a
  role noun (MED-EL).
- A same-page `#frag` is a job only if it resolves to a named `<a name>` on a
  job-hinted page, and such jobs need a title-slug `external_id` or N jobs
  collapse onto one immortal row.
- `SLUG_BOARD_HOSTS` is an allowlist for slug-shaped job URLs; `linkedin.com` is
  rejected wholesale; `LANGUAGE_SWITCHER_RE`, `is_listing_pointer` and the
  structural fallbacks (accordions, ARIA tabs — only when zero jobs found) each
  exist because of a real page. Measure any change's blast radius on live pages.

### 4.4 Deactivation, staleness and overrides

- A successful scrape deactivates active jobs it no longer sees. **A failed scrape
  never deactivates** (CRITICAL rule in AGENTS.md), and neither does a `partial`
  one. Nothing in the pipeline deletes job rows.
- **Staleness bound (2026-09-22):** `companies.consecutive_failures` is maintained
  by `persist_result`. At `STALE_AFTER_FAILURES` (3) a company's jobs stay active
  but drop off every public listing and count via `listable_clause()` in
  `api/api/query.py`, reappearing on its next clean scrape. Community jobs,
  admin-pinned jobs (`is_active_override = True`) and admin views are exempt.
  **Any new public job query must use `listable_clause()`.**
- `is_active_override`, `categories_override` and `is_audio_related_override` are
  read through `scraper/overrides.py` (`effective_*`). Every write site that
  recomputes a job must honour them, or corrections revert next cycle.
- Community jobs expire (`COMMUNITY_JOB_TTL_DAYS` 30, max 365); re-approving a live
  one refreshes it in place so bookmarked ids survive.
- **`updated_at` and `scraped_at` are not freshness signals** — SQLAlchemy skips the
  UPDATE when refound values are unchanged. Use `scrape_log`.

### 4.5 Relevance and categories (`scraper/normalizer.py`)

- `score_relevance(title, description, job_categories, audio_scope)`. Thresholds
  `SCOPE_THRESHOLDS = {native: 45, partial: 50, all: 55}`, +15 when there is no
  title signal outside native scope. Native adds +10; categories add +35 native /
  +25 otherwise.
- Short-circuits to `(0, False)` before scoring: `TALENT_POOL_TITLE` (talent pools,
  speculative applications — chosen over title-collapse dedup, which would have
  deleted 161 real jobs), and `is_clinical_hearing_title` (hearing-aid retail and
  clinical roles, with `CLINICAL_EXEMPT` for engineering words — it protects zero
  rows today and stays so the next term cannot sweep up "Research Audiologist").
- `CORPORATE_ROLE` (−70) is gated on `not title_strong`, and `AUDIO_TITLE_STRONG`
  matches `audiolog`, which is why it could not remove clinical roles. It now
  includes sales titles (the owner chose to cut all of them). Extend it only after
  measuring the live board; the bar is zero legitimate losses.
- `NEGATIVE_SIGNALS` (−45) barely fires; measured and settled, not worth tuning.
- `classify_categories` cutoff is 5 and shared by every category — do not move it
  lightly (it is why ElevenLabs' research roles score 4 and miss). The
  company-category gate fires only for audio-native manufacturer categories;
  broad gating measured ~50% precision. Rule: **the company decides whether it is
  audio work, the title decides which category.** `ANCHORED_CATEGORIES` must not be
  extended to `audio_systems`. `_apply_test_override` only re-files scored rows.
  Dual-listing a keyword across categories is intentional.
- **`NATIVE_TECHNICAL_BONUS` (a flat per-company bonus) was reverted twice. Do not
  retry that shape.**
- International titles are handled (gender markers, compounds, `_INTL`
  vocabularies, false friends like `Ultraschall`, `Stage`, `chef`); description and
  category vocabularies stay English-only by measurement.
  `tools/jobspy_fetch/terms-*.txt` must survive the classifier
  (`test_intl_search_terms`): do not search for jobs you would discard.
- After a scoring change: `python -m scraper.backfill_relevance --dry-run`, then
  without `--dry-run`. Regression set to keep passing: Valve "Audio Software
  Engineer" and Apple "Core Audio Software Engineer" → `audio_software`; Apple
  "Audio Machine Learning Engineer" → `audio_aiml`; Softube "DSP Developer" →
  `audio_dsp_embedded`; "Acoustic Test Engineer II" → `test_measurement_qa`;
  bare Test/QA Engineer stays off-board; DLR "Studio Leader", Sky Studios "CDN
  Engineer" and RingCentral "Senior Finance Analyst" are not audio; Starkey
  "Audio Technician" must not read as "Audiology Technician" (tested).

### 4.6 Health, URL shape and diagnostics

- `company_health.grade_company` (shared by `/admin/health` and
  `propose_demotions`): `unscraped` → `failing` → `silent` (scrape ok, zero rows)
  → `furniture` → `thin` → `idle` (rows, none audio) → `healthy`. `scraped` comes
  from `in_scrape_population()`, the same condition `run_cycle` uses.
- `scraper/url_shape.py` `classify_careers_url`: `ats_board` / `careers_shaped` /
  `not_careers` / `bad_page` / `missing`, judged from the URL alone. Measured
  healthy rates: 44.6% / 8.9% / 1.7% / 0%. False negatives: `recruit` and
  `opportunit` match any path. Shown as a column and filter on `/admin/health`,
  alongside a "hidden from board" marker.
- Every tool is listed in the README. Caveats that cost time:
  `check_url` builds a fresh company without `ats_type`/`ats_slug`, so it
  under-measures companies with a stored binding and never exercises that path;
  `discover_careers_urls`' high-confidence tier has run about 2 in 6 real, and a
  wrong proposal that *scrapes successfully* is the dangerous kind; its
  `domain_dead` means our fetch failed, not that the company is gone.
- **Measured and settled, do not redo:** fixing a wrong URL usually adds nothing
  (8 of 10 verified replacements yielded zero audio jobs); a homepage
  classifier for "is this an audio company" has no input (`website_url` empty) and
  no signal (JS shells score zero, e.g. Teenage Engineering); iframe-embedded
  boards are ~6 companies, not a systemic cause.

### 4.7 API and frontend

- `ASOUNDJOB_ENV=production` refuses to start while `ADMIN_PASSWORD` or
  `ADMIN_SECRET_KEY` is unset, the dev default, or under 12 / 32 characters.
- Free-text search works: the jobs loader maps `q` to `search` via
  `API_PARAM_ALIASES`, guarded by `test_search_is_the_name_sent_for_free_text`.
  **Curling `/api/jobs?q=` proves nothing about the site** — it made this look
  broken twice.
- Public pages show board counts, never active counts. New `/companies/…`
  sub-routes register above `/{slug}`. The sitemap reads `/api/jobs`; page caps
  are named constants (a silent 422 once lost 1,074 URLs). `.gitignore` covers
  `*.db-wal`/`-shm`/`-journal` (the WAL can hold submitter emails).
- Design system "The Type Specimen": one accent colour (position and scale carry
  meaning, never a second hue), radius 0, one font loaded from
  `recursive/mono.css` only, `--color-rule` decorative only. The admin UI is
  deliberately plainer. Owner's taste: artistry, not the AI-default look.
- Svelte 5: a `Set` in `$state` is not reactive (use a proxied array); any grid or
  flex child with truncated text needs `min-w-0` (recurred four times);
  `<fieldset>` needs `min-inline-size: 0`. Never regex computed Tailwind colours
  (`oklab()`), and never audit contrast mid-transition or in a hidden tab.

## 5. Open work

### Before launch
- Deploy artifacts: Dockerfile, compose, nginx, a nightly scrape job; the API
  needs write access to `data/`; set `ASOUNDJOB_ENV=production`, real secrets, and
  `STALE_AFTER_FAILURES` if not 3.
- **If PostgreSQL is chosen:** the category filter in `api/api/query.py`
  (`Job.job_categories.cast(String).like('%"cat"%')`) matches SQLite's JSON text
  and will match nothing against PostgreSQL's `{a,b}` array text. Unverified —
  there is no PostgreSQL here.
- `asoundjob-backup-20260922.db` (repo root, gitignored) can be deleted: the
  2026-09-24 cycle ran cleanly after migration `b539a9545442`.

### Seed URLs and data quality — start with `TRIAGE.md`
- `TRIAGE.md` (rebuilt 2026-09-22, cross-checked): **A. 16 dead careers URLs,
  re-checked live** (Audeze, Ortofon, Danley, Talaske, Thorens, Blackmagic,
  Roland/Boss…); B. 5 manual companies still failing (Rivian, Keysight, McIntosh
  Automotive, Tymphany, DiGiGrid); C/D. not a careers page; E. stores navigation;
  F. careers-looking but failing (mostly parser problems); 46 correctly say there
  are no openings.
- **Switchcraft's URL is HEICO's aerospace board** (`myjobs.adp.com/heico/…`, the
  keyword is ignored server-side). Unverify or repoint.
- **Ramboll Group times out.** The 2026-09-24 cycle stored
  `smartrecruiters binding failed: timeout after 90.0s` — the ~1,000-job walk
  exceeds `per_company_timeout` under cycle load, while `check_url` (running
  alone) succeeds. Not rate limiting. Likely fix: Bosch-style query-scoped
  `extra_careers_urls` (acoustics etc.) instead of walking the whole board — a
  seed edit, owner's call. 4 failures; its 16 board rows are hidden as stale.
- ~6 iframe-embedded boards could be read with a bounded fetch of the iframe
  `src`: DSP Concepts (TriNet Hire), Earlens (hrmdirect), Line 6 (appone),
  MTX Audio, Slate Digital (Personio), Dynaudio Automotive.
- Absent from the seed: Genelec, Soundboks, AIAIAI, Urbanista, Jays, Sudio,
  Propellerhead. Makeshift Software unadded (GoHire's title shape needs cleaning).

### Scraper and relevance
- 276 board rows carry no job category; never investigated.
- Board concentration: Shure alone is ~10%, the top five ~34% — a grouping or
  default-sort question for the API/frontend.
- MED-EL's board rows are bare requisition codes (`IT_12503`); ON Semiconductor's
  leftovers are a benefits/policy family. Both need their own handling.
- Generic pager `MAX_PAGES = 10` caps Sivantos at ~180–200 of 243;
  `detect_truncation` cannot see generic-pager truncation.
- HP Inc. wants Bosch-style `?q=` narrowing; needs a harness that sets `ats_type`.
- `COMPANY_CATEGORY_FALLBACK` lacks `Acoustic Consulting & Engineering` and
  `Audio Testing & Measurement` (measured +22 rows, ~6 junk; left undone).
  `sound_design` fires on about one row. `amplif*` is deliberately absent (6 false
  positives per true one).
- `discover_careers_urls` does not reject SiteGround captcha paths
  (`/.well-known/`, `sgcaptcha`); it once wrote them into the seed for 8 companies.
- LinkedIn fetcher in `tools/jobspy_fetch/` (own venv, Python ≥3.10) is built but
  never run — needs residential proxies. JobSpy is company *discovery* only.

### Frontend
- `/resources` and `/resources/interview-prep` are placeholders (AGENTS.md lists
  the eight interview-prep articles to seed).
- Selecting a job type hides rows with no `job_type` (NULL fails `IN`).
- Theme toggle is binary with no "system" option; specialty chips are not links;
  pagination is a fixed ±2 window with no first/last.

## 6. Traps — do not repeat

- **A successful scrape is not evidence of a right URL.** Peerless and Vifa scraped
  Danmarks Statistik for cycles; furniture scores 0 and hides. Read titles.
- **A tool's headline can answer a different question than its sample** — sort
  samples to match the claim (`check_url` board rows first).
- **Generated worklists must be cross-checked against known truth before handing
  over.** The 2026-09-21/22 `TRIAGE.md` listed healthy companies (DiGiCo, Valve,
  Naim Audio) and the owner's own manual URLs as broken.
- **"Harmless today" needs checking against `scrape_log`** — the SuccessFactors
  host-wildcard bug had already wiped ByteDance's board when it was called
  harmless.
- **Don't call a failure "transient" until it fails to recur** (Ramboll).
- **Price any dedup rule against real data first** (title-collapse: 161 real jobs).
- **Hand-picked fixtures passing proves little**; it happened three times in one
  session. Probe real data.
- **A token-subset name matcher without a ≥2-token guard** let "Audio Ltd" swallow
  523 names; a false "known" hides a discovery forever.
- **Blocked means blocked:** Tesla (Akamai), Neural DSP (Cloudflare behind a
  JS-set iframe), Frontier Audio and Cinder (Wellfound/Compas behind Cloudflare),
  Allen & Heath, Sound Devices, Synaptics (edge). Do not build evasion.
- **Meta rate-limits hard** (~8 probes in 20 min → a 429 for ~2.5 h). Its board
  ceiling is 3 audio jobs; a GraphQL parser was measured and not worth it.
- **A vendor name in markup is not evidence of that vendor's behaviour**
  ("cloudflare", "captcha" in a script tag).
- **Follow-one-link-to-find-an-ATS was measured and rejected** (~2 boards from 125
  pages). Pagination within a working listing is a different thing and is fine.
- **Relaxing the job-link gate** to slug-matches-title anchors was 60% junk;
  widening the card boundary stapled one job's city onto another.
- **New keywords must be tested as bare substrings against the whole active-title
  corpus**; extending fallback lists without measuring pulled in junk.
- **Tympany (hearing diagnostics) and Tymphany (transducers) are different
  companies**, as are **Treble** (hearing) and **Treble Technologies** (acoustic
  simulation).
- **The HTTP scraper once returned `[]` as success** — a stage returning nothing
  must never look like a genuinely empty board.

## 7. Company notes

| company | what matters |
| --- | --- |
| Adobe | Renamed from "Adobe Audition"; whole-company Workday board scoped with `?q=audio`, partial scope. |
| Amazon | amazon.jobs `search.json` needs `base_query` (audio, speech, signal processing); "dsp" is a trap here. |
| Apple | Parser reads `?search=` from seed URLs so `extra_careers_urls` can scope it; Beats by Dre was deleted after an empty-slug Apple binding scraped 245 Apple rows. |
| Arup | Avature facet derivation ends at a stable `/jobs/search/<id>`; never seed the session-stateful `/add/category/<id>` URL (same for Hoare Lea, Ramboll, Stantec, Sweco). |
| Audible | Deleted from seed and DB; 112 jobs, 1 misattributed board row. Do not re-add without measuring. |
| Audio Precision | Native `Audio Testing & Measurement`; no `open_application` on purpose (page refuses unsolicited CVs). |
| Bang & Olufsen | SAP DWR board, unfetchable; `verified: false` by design. |
| Beltone | Retail dispensing chain; 0 board rows since the clinical filter — correct, not a bug. |
| Beyerdynamic | No scrapable listings; NA page is `open_application` + `scrape_blocked`. |
| BMG Production Music | Points at its own (empty) SmartRecruiters board, not Bertelsmann's 955-job one. |
| Bosch Group | Six curated SmartRecruiters searches cut 4,836 rows to 107 with all board rows kept; Bosch Security deleted. |
| ByteDance | Blocked; entries for TikTok Audio and Resso deleted as dead duplicates. |
| Calrec | `careers.calrec.com`, works; no longer blocked. |
| Cirrus Logic | Lever EU tenant (`api.eu.lever.co`); `api_url_for` derives the host from the careers URL. Category `Audio Semiconductors` (native). |
| Cochlear | Native hearing tech; many board rows are clinical/commercial via the category bonus — accepted trade-off. |
| Delart | Embed-only Greenhouse board; do not repoint to delartech.com. Agency scope. |
| Demant | Correct URL `careers.demant.com/search/`; `careers.demant.com/` (marketing) and `careers.us.demant.com/jobs` (clinic hiring) are both traps. |
| DiGiCo | `digico.biz/recruitment/`, healthy. |
| Dolby | Eightfold `/api/pcsx/search`, `domain=dolby.com`; new Eightfold companies need two cycles (slug derived). |
| ElevenLabs | Not seeded on purpose: 52 of 54 reachable board rows would be sales; research roles score 4 against the cutoff of 5. |
| Fender / inMusic / Logitech | Each board was being claimed by a sub-brand via shared-URL dedup; sub-brands are `verified: false`. |
| Focusrite / Music Tribe | One board per group (Workable; Jobvite `musictribe`); brand entries retired. Check footers for umbrella owners. |
| Garmin | Jibe JSON API via `JIBE_HOSTS` allowlist. |
| Gibson | Own scraper — the public ADP endpoint withholds 17 of 36 requisitions. MESA/Boogie retired into it. |
| Google | `?q=audio`, `scrape_method: http`; needed `<base href>` handling and pagination. |
| Harman | Several `extra_careers_urls` queries; no Avature parser needed. |
| **Knowles Corporation** | ADP **MyJobs**, which the `adp` parser (Workforce Now) does not speak. **Do not build a MyJobs parser:** Knowles yields 0 audio jobs even at native scope, and the only other MyJobs company is Switchcraft (whose URL is HEICO's). The API recipe is in the old log (`DO NOT REPEAT: Knowles`). It has no stored ATS binding; 404s against Workforce Now are discovery guesses. |
| Meta | Playwright; 400s on job links are bot defence, whitelisted in `check_links`; ceiling 3 board jobs. |
| Native Instruments | JS SPA with no ATS link; blocked-list. |
| Northrop Grumman | Eightfold needs `domain=ngc.com`. |
| Perkins&Will | Real board on UltiPro (152 jobs, none audio); kept for its acoustics practice. |
| Qualcomm / Infineon | `extra_careers_urls` for audio + dsp (+ acoustic) because Eightfold capped at 120; "dsp" admits some NPU/modem noise, accepted. |
| Ramboll Group | See §5. Talent-pool "Rail Power Supply" rows fixed by `TALENT_POOL_TITLE`, not dedup. |
| Rohde & Schwarz | Avature board, `http` method (Playwright rendered a country selector). |
| Sigma Connectivity | Group JSON API filtered client-side via `company_startswith`; do not "fix" it to the server's exact-match `?company=`. |
| Sony | Workday `sonyglobal`; only Europe/US/China/Japan sites exist; global contributes 0 board rows correctly. |
| Starkey | UltiPro `LoadSearchResults` API. |
| Tymphany | Replaced Peerless; `open_application`, manual; contact form only, so failing is correct. |
| Vifa | Still points at `dst.dk`; `verified: false` on purpose. |
| Waymo | Search param is `query`; alphabetical pagination needs several narrow queries. |

## 8. Stale files in the repo

- `SEED_WORKLIST.md`, `careers_url_proposals.md` (both 2026-08-29) and
  `seed_url_audit.md` (2026-09-10) are old worklists superseded by `TRIAGE.md`.
  They are tracked; a fresh session may trust the wrong one. Owner to decide on
  deletion.
- `scraper/BRIEF.md` is complete and historical.
- `web/asoundjob.db` is a stray empty file; the real database is `asoundjob.db` at
  the repo root (relative SQLite URLs are anchored to the repo root by
  `resolve_database_url`, so running from `scraper/` is fine).

## 9. Log (newest first, keep entries short)

- **2026-09-24, cycle** — 710 companies, 366 ok, 1,601 s; board-eligible 1,025,
  publicly listed 1,008. First cycle on the new error reporting: 61 failures
  stored a real HTTP status (32× 403, 26× 404 — 9 of those from Playwright-only
  companies no tool could see before), and Ramboll's cause surfaced as a
  SmartRecruiters timeout. Failure counters live: Audison recovered to 0.
- **2026-09-24** — Handoff rewritten from the 7,910-line log (full text at
  `0286282`). Corrected on the way: the Sep 22 claim that Knowles needs a MyJobs
  parser (the original Sep 4 finding — don't build it — stands); the old open item
  "company dropdown shows 100 of 722" (closed long ago by a free-text filter); and
  AGENTS.md's "Discord link empty" (it is filled and used).
- **2026-09-22** — `TRIAGE.md` rebuilt after the owner spotted working companies
  in it. Production refuses dev credentials; Playwright reports HTTP status;
  stale companies hidden from the board after 3 failed cycles (migration
  `b539a9545442`); AGENTS.md corrected. Cycle: 710 companies, 364 ok, 1,572 s.
- **2026-09-20** — Clinical hearing roles removed (board 1,243 → 1,016);
  `idle` split into `silent` / `unscraped` / `idle`; `url_shape` added to the
  admin panel.
- **2026-09-18** — `scrape_blocked` honoured by the cycle; talent-pool
  short-circuit; all sales titles cut; three dead entries deleted.
- **2026-09-17** — The admin panel became the authority over the seed.
