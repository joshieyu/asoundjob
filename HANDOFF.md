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

As of the 2026-11-16 cycle:

| | |
| --- | --- |
| companies in the seed / DB | 1,441 (772 verified, 74 `source: manual`, 15 `scrape_blocked`) |
| scrape population (verified, unblocked, has URL) | a cycle scrapes ~718 after shared-URL dedup |
| cycle | ~26–36 min on a good connection; ok 382 / failed 344 — ~50% failure is normal |
| job rows / active / board-eligible | ~35,900 / ~11,000 / 1,160 |
| **publicly listed** | **1,151** (9 hidden as stale: IK Multimedia 4, Otter.ai, XLN Audio, Fairphone, Valcom, CereProc 1 each) |
| companies contributing to the board | 145; top: Shure 103, Apple 84, Cirrus Logic 68, Bose 65, Qualcomm 54, Amazon 50 |

**Running locally:** the app's preview launcher cannot start the API — macOS
blocks it from reading `venv/pyvenv.cfg` (`Operation not permitted`; the
CommandLineTools Python is its own app bundle), though it starts the web server
fine. Start the API from a terminal as the README says.

**All seed edits through 2026-11-10 are committed** (OpenAI, Meta, Rockford Fosgate rename, Cisco, Ramboll scoping, Sesame, Quippy, Laran, Stryker, Anaheim Ducks, Sonova repoint, Advanced Bionics unverified; §7).

**Eight owner-pinned jobs live only in the DB** (`is_audio_related_override = True`):
Muse Group CPO (36373), L-Acoustics Exec. Director of Product
Management (12328), Splice Senior Brand Marketing Manager (37097), DistroKid Growth
PM (834), ai-coustics Head of Marketing (36410), Anthropic AV Production Specialist
(36483), all 2026-11-04; Sonova/Advanced Bionics Sr. Research Engineer, Valencia
(39980, 2026-11-10 — cochlear-implant signal processing, scores 30). The owner
wanted these listed; the scorer holds them back (15–35). Plus Microsoft Principal Applied
Scientist – ML & Deep Learning (40440, 2026-11-14, Teams audio ML, scores 20). Pin and unpin
at `/admin/jobs` (search by title, company or a pasted job URL); a fresh DB loses them.
| health grades (scraped, 2026-09-22) | healthy 96, idle 149, failing 348, furniture 46, silent 32, thin 61; unscraped 680 |

**GN's careers site is offline until early November** (§5): GN Store Nord, Jabra
and SteelSeries lost their 31 board rows on 2026-10-01, most of that cycle's drop
of 36 from 1,040 listed; the rest is Qualcomm's fallback rows clearing.

**Not launched.** No Dockerfile, compose file or nginx config; nothing has ever
run on PostgreSQL (none installed locally, nor Docker). **`main` was
fast-forwarded to `redesign-type-specimen` on 2026-11-10**, so a fresh clone of
`main` is the current code; README "First-time setup" covers a clean machine.

Where to look: `README.md` (running, gates, data flow, every tool),
`AGENTS.md` (original build plan and rules), `TRIAGE.md` (seed-URL worklist),
`PRODUCT.md` / `REDESIGN-BRIEF.md` / `DESIGN.md` (product and design authority).

## 2. Decisions waiting on the owner

1. ~~SQLite or PostgreSQL~~ — **decided 2026-11-16: SQLite** (WAL mode), on one
   Hetzner server with systemd and Caddy, no Docker. See `DEPLOY.md`.
2. ~~Domain~~ — **decided 2026-11-16: `asoundjob.com`**, `www` redirects to it.
3. ~~Launch scope~~ — **decided 2026-11-16:** `/resources` and
   `/resources/interview-prep` stay up but are dropped from the header, footer and
   sitemap until they are written. Company edits live on the server; a daily timer
   pushes `data/audio_companies_final.json` to `main`.
4. **How to merge** this branch into `main`.
5. ~~Who the board is for~~ — **decided 2026-11-12:** commercial roles (sales,
   marketing, customer success) belong, but only when the job itself carries an
   audio signal; they are tagged `sales_marketing_cs` so seekers can filter them.
   This reverses the 2026-09-18 sales cut. Hearing-aid retail and clinical roles
   stay cut. See §4.5.
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
  time-bounded against `per_company_timeout` (90s; 180s for `priority` boards) or
  it cancels the company. **A paginated ATS scraper must build its result in a
  `listing()` list** (`scrapers/base.py`) so a timeout keeps what it already read.
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
  awsm (WP Job Openings), bamboohr, eightfold, gibson, greenhouse, haileyhr, icims, jibe,
  jobsyn, lever, oracle, paylocity, pinpoint, recruitee, sigma, smartrecruiters, successfactors,
  taleo, teamtailor (`/jobs.rss`; a custom domain needs `ats_type: teamtailor`), ultipro,
  workable, workday.
- ATS results are `trust_empty` (empty means no jobs); generic results never are.
  If a dedicated parser claimed a board and failed, the fallback result is
  `partial` so it cannot deactivate what it did not see.
- **A stored or claiming ATS that times out or is rate-limited skips the generic
  fallback entirely** (2026-11-12, `_timed_out_result` / `_rate_limited_result`):
  the company fails that cycle, keeps its rows, and counts toward the 3-failure
  staleness bound. Before, a timeout fell back to malformed generic rows that
  reset the failure count and churned on every ATS success. Other ATS errors (404,
  parse failure) still fall back, so a stale binding can be rescued. "Timed out"
  covers both the 90 s company budget and an HTTP read/connect timeout inside the
  scraper (`base.is_timeout`, 2026-11-13; it walks the exception chain). A DNS
  failure or refused connection is *not* a timeout — urllib3 v2 makes
  `NewConnectionError` subclass `ConnectTimeoutError`, so match on `requests`'
  own `Timeout`/urllib3 `ReadTimeoutError`, never urllib3's base `TimeoutError`.
- **A board cut short keeps what it read** (2026-11-13). Paginated ATS scrapers
  (Apple, Workday, Eightfold, SuccessFactors, iCIMS, Jibe, Amazon, ADP, UltiPro,
  SmartRecruiters, Hailey HR) collect jobs page by page into `listing()`. If the
  company times out or a page fails after at least one page was read, the jobs
  read so far are posted as a *partial success*: new jobs go up, nothing is
  deactivated, the failure count resets, and `scrape_log.error_message` says
  `listing cut short, kept N jobs read so far: …` (the cycle summary counts these
  as `cut_short=`). A board that is cut short every cycle never retires its
  closed jobs — check `cut_short` companies if a board's count only ever grows.
  Apple and UltiPro list newest first, so a cut-short Apple listing
  loses its oldest jobs, not its new ones. Every request through `fetch.py`, and
  Workday's listing POST, is retried once on a timeout (`retry_on_timeout`).
- **A job that comes back without a description keeps its stored one**
  (`keep_stored_descriptions` in `main.py`, 2026-11-13). Before, a job past an
  enrichment budget or cap was saved with no description and re-scored on its
  title alone, which could drop a listed job off the board for a cycle.
- **`priority` boards** (seed flag, admin "Priority" toggle, 2026-11-13): twice
  the per-company budget (also scales the enrichment and multi-URL budgets) and
  scraped first in the cycle. Set on Apple, Shure, Cirrus Logic, Bose, Qualcomm
  and Amazon — the boards contributing 40+ listed jobs.
- **A multi-URL company is partial if any URL was partial** (2026-11-13). Before,
  a URL that fell back to a generic first-page read still counted as complete,
  so a company whose every URL fell back could deactivate jobs it never saw.
- **Extra careers URLs use their own ATS slug** (2026-11-12, `_slug_for_url`): an
  extra URL on a different board of the same ATS (Sony's `SonyJapanCareers`)
  used to inherit the stored binding and silently re-scrape the primary board.
- **Errors:** Playwright now records the page's HTTP status and reports
  `HTTP {status} for {url}` when nothing was found and status ≥ 400 (ignored when
  jobs are found — some SPAs 404 and still render a board). A failed stored or
  claiming ATS attempt is kept as `{ats} binding failed: …; careers page: …`.
  Discovery guesses are deliberately excluded — they are guesses, not bindings.
- **A scrape that returns only nav chrome still counts as success** — http or
  Playwright. Being a trusted success it resets the failure count and deactivates
  every job it did not see: on 2026-09-29 Zoom's 60 real jobs were replaced by
  "Continue Reading" and "Career Search Tips". An http result of this kind also
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
- **Call-to-action prefixes are stripped from titles** (`CTA_PREFIX_RE`,
  2026-11-12): "View posting : X", "Apply now – X", "View job: X". A dash only
  counts with spaces around it, so "Read-Out IC Design Engineer" survives. It
  matters because the longest link text to a URL wins the title.
- **Links resolve against the URL the page was actually served from**, after
  redirects (2026-11-11). `collect_paginated`'s fetch may return `(html,
  final_url)`; `HttpScraper` uses `fetch_page` (requests' `response.url`) and
  Playwright `page.url`. The same-host checks and http enrichment use the final
  host too. Expect a one-time swap of rows (new URLs in, old out) at any company
  whose careers page redirects across hosts, on its first scrape after this.
- Location comes only from an element labelled as location, never blind card
  text; multi-location cards join with `"; "`. JSON-LD `jobLocation` may be an
  array. `resolve_document_base()` applies wherever relative URLs are resolved.
- **PDF job links** (`scrapers/pdf_description.py`, http and Playwright): a job whose
  URL path ends `.pdf` gets its description from the PDF text (`pypdf`, first 10
  pages, ≤ 5 MB, ≤ 25 per company, inside the 85% enrichment budget). Titles that
  read as brochures, applications, benefits or policy/EEO notices are skipped, so
  furniture PDFs never gain audio-heavy text. Scanned (image-only) PDFs yield
  nothing and keep a title-only score (Rockford's Quality Engineer).
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
- **The staleness bound cannot see a claimed-ATS fallback.** When a dedicated
  parser claims a board and fails, the generic fallback's result is `partial`
  (no deactivation) but `persist_result` still logs `status=success` with no
  error and resets `consecutive_failures` to 0 (`scraper/main.py:121`). A company
  whose ATS fails every cycle therefore keeps its last-known ATS rows on the
  board indefinitely, and neither `scrape_log` nor the admin panel shows the ATS
  failure — only the cycle log's `claimed this board but failed` lines do. See §5.
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
- **`AUDIO_REQUIREMENT` (+45, 2026-11-14)**: the role text asks for audio
  experience — "experience/knowledge/background… in/with/of" or "N+ years of"
  followed within three plain words by an audio term (`AUDIO_DOMAIN`: audio,
  acoustic*, microphone, loudspeaker, transducer, hearing aid, speech enhancement,
  noise/echo cancellation). No commas or and/or in the gap, so media lists ("text,
  image, video, or audio") do not count; RF `beamforming` and `speech recognition`
  were dropped after Amazon's stock applied-scientist line and 5G jobs matched.
  Measured: 77 jobs joined, none left; ~8 are borderline (Sony 3D designer, Treble
  office coordinator, Penn State/UT part-time support) — hide them at `/admin/jobs`.
  The same day `acoustic[s]?` became `acoustic(?:s|al)?` in the title and
  description terms (Ramboll "Consultant, Acoustical" was hidden).
- Short-circuits to `(0, False)` before scoring: `TALENT_POOL_TITLE` (talent pools,
  speculative applications — chosen over title-collapse dedup, which would have
  deleted 161 real jobs), and `is_clinical_hearing_title` (hearing-aid retail and
  clinical roles, with `CLINICAL_EXEMPT` for engineering words — it protects zero
  rows today and stays so the next term cannot sweep up "Research Audiologist").
  2026-11-12 added `audiologista`, `audionom`, `h[öo]r…akustiker` (Hörsystem-,
  Hörgeräteakustiker — the same dispensing trade; an older test that expected
  them to score as audio was reversed) and bare "Hearing Specialist".
  `CORPORATE_ROLE` gained client-service administrator, call centre (British) and
  French `administratif`; it mainly stops clinic rows a full-board scrape would
  bring back.
- `CORPORATE_ROLE` (−70) is gated on `not title_strong`, and `AUDIO_TITLE_STRONG`
  matches `audiolog`, which is why it could not remove clinical roles. It holds
  back-office titles only (finance, HR, legal, IT, facilities, accounting, sales
  ops). **Sales, account, business-development and marketing titles left it on
  2026-11-12** (owner: commercial roles belong). Extend it only after measuring the
  live board; the bar is zero legitimate losses.
- **`sales_marketing_cs` is label-only** (`LABEL_ONLY_CATEGORIES`, 2026-11-12): it
  is assigned from the title alone (any "sales", "marketing", account manager/
  executive, business development, customer success/service, GTM, partnerships…)
  so every commercial job can be filtered, but it adds nothing to the relevance
  score. A commercial job reaches the board only on its own audio signal — title
  or description, or another category. Measured: letting the tag score as well
  would have grown the board 1,079 → 1,518 with ~520 commercial rows (Logitech
  54, Twilio 36, Razer 30 including store associates); the owner chose this
  selective version (~87 commercial rows). Generic account executives at voice-AI
  companies (Decagon, Dialpad) stay off; L-Acoustics' and Cochlear's regional
  sales managers are on.
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

- **Featured jobs** (2026-11-16): `jobs.featured_at/featured_until/featured_note`.
  `GET /api/jobs/featured` (max 12, newest feature first, active + listable; audio
  relevance is not required — the admin's pick wins). Admins feature from
  `/admin/jobs` (days, default 30, or "No end date", plus an optional public note —
  contact, urgency); `featured_until` NULL means indefinite. Unfeature there too
  (Featured filter → Unfeature). Visitors use "Request a feature" on a job page,
  which files a `feature_request` in the job-feedback queue with their own length
  (days or until filled → `job_feedback.feature_days`, NULL = indefinite) and a
  suggested note (`feature_note`); `/admin/feedback` shows both as editable fields,
  and approving applies the edited terms (migration `f2c6a9d1b384`). The submit-a-job
  form has the same request (`job_submissions.feature_requested/feature_days/
  feature_note`, migration `b5e3d8a1c602`); `/admin/submissions` shows a "Feature on
  approval" toggle prefilled from it, and approving features the published job. A
  feature on a community job still ends when the listing expires. The
  homepage shows a Featured section above "Fresh on the board" only when something
  is featured, and the fresh list excludes featured ids. Features lapse on their
  own; `prune_orphans` will not delete a featured job.

- `ASOUNDJOB_ENV=production` refuses to start while `ADMIN_PASSWORD` or
  `ADMIN_SECRET_KEY` is unset, the dev default, or under 12 / 32 characters.
- Free-text search works: the jobs loader maps `q` to `search` via
  `API_PARAM_ALIASES`, guarded by `test_search_is_the_name_sent_for_free_text`.
  **Curling `/api/jobs?q=` proves nothing about the site** — it made this look
  broken twice.
- **Date sorts use the date the card shows** (`SEEN_DATE` in `api/api/query.py`,
  2026-11-11): `posted_date`, else the day the row was first seen
  (`created_at`). **Not `scraped_at`** — it has `onupdate=func.now()`, so it moves
  whenever any column of the row changes; the 11-11 version used it and 129
  undated board rows sorted (and showed "seen") by their last change. Fixed
  2026-11-12: the API now returns `created_at`, and the job strip, job page and
  company page use it. Before, undated rows (274 of 1,079 board
  rows — Harman, Meta, Sivantos, Demant…) sorted after every dated row, so a job
  found today could sit below month-old postings while its card said "seen today".
- **Search rules** (`search_terms` / `search_clause` / `search_rank` in
  `api/api/query.py`, since 2026-11-10): the query splits into words and every word
  must match the title, the **company name** or the description. Words of ≤ 4
  characters match whole words only ("meta" ≠ metal/metadata, "dsp", "c++");
  longer words match word starts ("acoust" → acoustics). Title/company matches rank
  above description-only ones, then the chosen sort. Implemented with
  `regexp_match` and an inline `(?i)` — SQLAlchemy drops `flags=` on SQLite, and
  `(?i)` plus `[^a-z0-9]` boundaries also work in PostgreSQL's regex dialect (`\b`
  would not). Before this, "meta" returned 47 metal/metadata rows and none of
  Meta's 21 (Meta's rows have no descriptions and its titles never say "Meta").
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
- Done 2026-11-16: deploy artifacts are in `deploy/` (Caddyfile, systemd services
  and timers for the API, website, nightly scrape, backups and the company-list
  push, `update.sh`), with every step in `DEPLOY.md`. Live since 2026-11-16.
- Done 2026-11-12: the web app builds with `@sveltejs/adapter-node` 5.5.7 (6.x
  needs SvelteKit 3) — `node web/build`, set `ORIGIN`; and rate limits key on
  `client_ip()`, which trusts `X-Forwarded-For` only from `TRUSTED_PROXIES`
  (default loopback). In Docker, set it to the compose network's CIDR and have
  nginx send `X-Forwarded-For`, or every visitor shares one quota.
  `SUBMISSIONS_PER_IP_PER_DAY` is now actually read. Limits are in-memory, so run
  the API as a single worker.
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
- **Zoom's careers URL is dead, and the scrape wiped its board (2026-09-29).**
  `careers.zoom.us/jobs/search` now 404s (`careers.zoom.us/` redirects to
  `www.careers.zoom.us/`; `zoom.com/en/careers/` also 404s). During the cycle
  Playwright reached a page carrying only "Continue Reading" and "Career Search
  Tips"; that counted as success and deactivated all 60 real jobs (1 was on the
  board). Those two links are now Zoom's only active rows (off the board — they
  score 0). `check_url` afterwards fails on a navigation timeout. Needs a new URL
  (seed edit, owner's call); the underlying gap is in "Scraper and relevance".
- **GN's careers site is offline until early November.** On 2026-10-01 the
  `gn.wd3` Workday tenant returned `total: 0` (HTTP 200, no facets) for all three
  seeded sites — `GN-Careers` (GN Store Nord), `JabraCareers`, `SteelSeriesCareers`
  — and, being a trusted ATS empty, deactivated their 31 board rows (24 + 6 + 1).
  The page itself says the site is "temporarily offline as we prepare for the sale
  of our Hearing business to Amplifon S.p.A." and points applicants to LinkedIn
  until it returns. The deactivation is correct by the rules; the rows reactivate
  on the first scrape that sees them again, if their `external_id`s survive.
  Nothing to do now. When it returns, check whether ReSound/Beltone hearing roles
  have moved to Amplifon's board (Amplifon and Audigy are in the seed).
- **Amplitude's Greenhouse board is gone (2026-09-29).** Both
  `boards-api.greenhouse.io/v1/boards/amplitude` and
  `job-boards.greenhouse.io/amplitude` 404; it had 38 jobs every prior cycle,
  none on the board. Repoint or unverify.
- **CD Baby's Greenhouse board is gone (2026-10-04).** `cdbabyjobs` now 404s on
  the API (the board page 500s); it had returned zero jobs for weeks before that.
  No board rows. Repoint or unverify.
- **IK Multimedia moved its careers page (2026-10-12).** `ikmultimedia.com/careers/`
  now 404s; the homepage links `/pages/careers`, which lists 10 jobs (Modena and
  Sunrise FL), including all 4 on our board. But they are expandable entries with
  no links, so `check_url` on the new URL finds nothing. Repointing alone will not
  help — it needs the URL change plus parser work for that layout. Its 4 board
  rows (still genuinely open) have been hidden as stale since 2026-10-15.
- **Otter.ai's careers page stopped rendering job links (2026-10-14).** Its 3
  board rows have been hidden as stale since 2026-10-17. The jobs live on a public
  Greenhouse board: `check_url https://job-boards.greenhouse.io/otterai` (run
  2026-10-15) → greenhouse success, 25 jobs, **5 board rows** (Senior Applied
  Scientist, Speech; two ML engineers; and two marketing/customer-success roles
  that score 45 at native scope — see §2.5). A ready seed edit, owner's call.
- **XLN Audio has no openings.** Its Teamtailor page says "No open positions
  right now"; the closed C++ Developer row stayed listed until its third failure
  hid it on 2026-10-17, because an empty generic page is a failure,
  never a trusted empty board. A Teamtailor-specific empty state (it is
  recognisable) could be trusted.
- **Valcom** has failed three cycles with "no job links found" after five with one
  job; its single board row is hidden as stale. Most likely the job closed and an
  empty generic page counts as a failure, not as an empty board — correct, and
  the row stays hidden.
- **Switchcraft's URL is HEICO's aerospace board** (`myjobs.adp.com/heico/…`, the
  keyword is ignored server-side). Unverify or repoint.
- **Ramboll Group — fixed 2026-11-10 by scoping.** Its whole SmartRecruiters board
  (~1,000 jobs) kept exceeding the 90 s budget (12 failures in 18 runs, hidden as
  stale more often than not). The seed now reads `?q=acoustics%20noise` (54 jobs,
  all described). Measured the same day: the unscoped board put 21 jobs on the
  board and the scoped one 21, but the unscoped run described only 27 of 998 jobs.
  The first scoped scrape deactivated ~1,100 non-acoustic Ramboll rows, as intended.
- ~6 iframe-embedded boards could be read with a bounded fetch of the iframe
  `src`: DSP Concepts (TriNet Hire), Earlens (hrmdirect), Line 6 (appone),
  MTX Audio, Slate Digital (Personio), Dynaudio Automotive.
- Absent from the seed: Genelec, Soundboks, AIAIAI, Urbanista, Jays, Sudio,
  Propellerhead. Makeshift Software unadded (GoHire's title shape needs cleaning).

### Scraper and relevance
- **Fixed 2026-11-04 (`30c7b15`) — iCIMS stopped after a short first page.**
  `_fetch_all` broke on any page under 20 rows; Shure's page 0 shows 19 of ~130,
  so 2026-10-26 and 10-28 were trusted at 19 and 94 open board rows were
  deactivated. Pagination now stops only on an empty page or no new ids. A
  Shure-only scrape found 126 and reactivated 103 (104 board rows). The detail
  cap is now 250 with an 85% time budget (2026-11-12): all 123 Shure jobs get a
  description, 111 board rows.
- **Claimed-ATS timeouts under cycle load — addressed 2026-11-12.** The four
  repeat offenders were narrowed with search terms so their boards finish in
  4–14 s (Demant, Analog Devices, Samsung, Belden; §7), and an ATS timeout no
  longer falls back (§4.2). Watch the next cycles for occasional timeouts at
  Apple, HP, Logitech, Razer, Dolby: they now show as failures, not fallbacks,
  unless at least one listing page was read — then they post what they read
  (`cut_short`, §4.2).
  History: Every cycle 7–8 large ATS boards exceed the 90 s `per_company_timeout`
  and fall back to the generic scrapers with deactivation suppressed:
  - 2026-09-25: DLR Group (Greenhouse ReadTimeout), Belden and Demant
    (SuccessFactors), Analog Devices, Logitech and McGill (Workday), HP (Eightfold).
  - 2026-09-29: Shure (iCIMS), Samsung and Analog Devices (Workday), Demant and
    Belden (SuccessFactors), Twilio Voice (Eightfold); Qualcomm got HTTP 429 from
    Eightfold (its 63 board rows were unaffected).

  The suppression works — nothing was wrongly deactivated. Three things follow:
  1. **Fallback rows are malformed, and some reach the public board:** Shure
     titles prefixed "Job Title …" ("Job Title Intern, DSP"), Qualcomm titles with
     location and department glued on plus a duplicate under an `apply?pid=` URL,
     Twilio "Senior Manager, Customer Success Customer Success". Their
     `external_id`s differ from the ATS rows', so the next ATS success deactivates
     them and re-inserts — the churn behind Samsung 751 ↔ 23, Logitech 218 ↔ 21,
     McGill 272 ↔ 17, Nissan 233 ↔ 1, HP 200 ↔ 7, and most of 2026-09-29's 945
     deactivations.
  2. **The staleness bound never fires for these** (§4.4). Demant's SuccessFactors
     board (~300 jobs) last succeeded 2026-09-11; every cycle since has fallen
     back to ~10 rows while its 26 board rows sit unconfirmed and will never be
     hidden. Analog Devices' Workday board (~840) succeeded once in the last six
     cycles, Belden's SuccessFactors once.
  3. **It is invisible** in `scrape_log` and the admin panel.

  Chosen 2026-11-12 (first option, for timeouts only). Options were: when a claimed ATS fails, persist nothing and count a
  failure (keeps last-known rows, lets the staleness bound work, ends the churn;
  a genuinely broken binding already surfaces as `{ats} binding failed`); give
  ATS-claimed companies a longer timeout, or run the large boards early or apart
  from the Playwright load. Measure first whether Demant's SuccessFactors walk
  completes when run alone (`--company`), since Ramboll's does. Measured: alone,
  Demant's full board takes 40 s (309 jobs, 18 board rows; the extra rows over
  the narrowed URLs were all clinic titles).
- **The same churn happens without an ATS: Rohde & Schwarz.** Its seeded method is
  `http` (Avature `/en_US/careers/JobDetail/…`, ~59 rows). When that attempt times
  out or raises, the scrape falls through to Playwright, which renders the country
  selector plus `/uk/career/jobs/…` pages (~77 rows, ~40 of them one link per
  country). Both count as full successes, so every switch deactivates the other
  shape's rows — 12 board rows out, 3 in on 2026-10-07. Playwright won 8 of the
  last 12 runs, with 6 switches between the two. That the http attempt timed out
  or raised is inferred: it left no warning in the log (next item). A fallback
  past a seeded `http` method
  arguably deserves the same `partial` treatment as one past a claimed ATS.
- **`_attempt` does not log timeouts or exceptions**
  (`scrapers/pipeline.py:116–125`): they go only into `self.attempts`, so a
  generic stage that times out leaves no line in the cycle log. Rohde & Schwarz's
  http failures above are invisible for this reason; only the `scrape_method`
  recorded in `scrape_log` gives them away.
- **Eightfold 429s — fixed 2026-11-09, confirm over the next cycles.** Qualcomm and
  Microsoft drew 429s on most cycles (Eightfold appears to limit by client IP across
  tenants). Now: one `EightfoldScraper` instance holds shared slots — 2 search, 6
  detail requests at once across all Eightfold companies (was up to 50 per company);
  a 429 on a search page retries after 5 s and 15 s, then raises
  `RateLimitedError`; a 429 on a detail fetch stops that company's enrichment
  (jobs kept). A rate-limited ATS result **skips the generic fallback** (pipeline
  `_rate_limited_result`), so no more malformed duplicate rows — the company simply
  fails that cycle and keeps its jobs. Trade-off: repeated 429s now count toward the
  3-failure staleness bound instead of being masked by a partial fallback success.
  Solo re-scrapes after the fix: Microsoft 14 s (cleared 16 fallback rows),
  Qualcomm 41 s at 4 detail slots — raised to 6 so two concurrent Eightfold
  companies still finish enrichment inside the 76 s budget. **First cycle with the
  fix (2026-11-10):** Qualcomm clean; Microsoft's `audio` URL still drew a 429 on
  its second search page after both retries, but its `speech` URL succeeded, so
  the result was partial (no deactivation, failure count stays 0) and no fallback
  rows appeared. If Microsoft keeps 429ing, lengthen the backoff or drop to one
  search slot before anything cleverer. **2026-11-11:** no Eightfold 429s at all,
  but Microsoft's `audio` URL hit the 90 s company timeout: enrichment got a fixed
  76 s *after* a search slowed by the shared slots. Enrichment now gets only what is
  left of 85% of the budget measured from the start of `fetch_jobs`.
- **A navigation-only result is a trusted success** (§4.2) and can deactivate a
  real board (Zoom, 2026-09-29). A result whose every row is non-job furniture
  should count as failed, or at least `partial`. Measure first: 46 companies were
  graded `furniture` on 2026-09-22, and some may be genuinely empty boards.
- 276 board rows carry no job category; never investigated.
- Board concentration: Shure alone is ~10%, the top five ~34% — a grouping or
  default-sort question for the API/frontend.
- MED-EL's board rows are bare requisition codes (`IT_12503`); ON Semiconductor's
  leftovers are a benefits/policy family. Both need their own handling.
- Generic pager `MAX_PAGES = 10` caps Sivantos at ~180–200 of 243;
  `detect_truncation` cannot see generic-pager truncation.
- HP Inc. wants Bosch-style `?q=` narrowing; needs a harness that sets `ats_type`.
  **Measured 2026-10-14 why it matters:** HP's Eightfold board is larger than the
  parser's cap (`MAX_PAGES = 20` → 200 rows), and the 200 returned differ almost
  entirely between cycles (`sort_by=timestamp` in the seed URL notwithstanding).
  Each successful cycle deactivates 87–192 HP rows and reactivates a similar
  number; HP's few board rows flicker on and off. `detect_truncation` should
  flag it.
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
- Selecting a job type (2026-11-12, owner's call): jobs with no `job_type` (~60% of
  the board) follow the matches under a "Job type not listed" divider and are not
  counted in `total`; the API's `pages` covers both (`untyped_last` in
  `api/api/query.py`, `page_envelope(trailing=)`). `/api/search` stays strict.
- Theme toggle is binary with no "system" option; specialty chips are not links;
  pagination is a fixed ±2 window, with First/Last buttons since 2026-11-12 (icon-only on phones).

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
- **Meta rate-limits hard** (~8 probes in 20 min → a 429 for ~2.5 h, measured in
  an earlier session). Since 2026-11-08 a Meta scrape is ~12 page loads (8 pages of
  `q=audio`, 4 of `q=sound`); ~25 loads in 10 min that day drew no 429. Watch
  `scrape_log` for Meta 429s; if they start, drop the `sound` query first. A 429 on
  a later page now fails the scrape (no deactivation) rather than truncating it.
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
- **A big swing in a company's `jobs_found` is usually a claimed-ATS timeout
  falling back, not a board change.** Grep the cycle log for
  `claimed this board but failed` before investigating the board itself.
- **A bad connection shows up as page-load timeouts, not as network errors.** A
  normal cycle has ~4 `Page.goto: Timeout 25000ms exceeded`; on 2026-10-09 there
  were 141, spread evenly through the run, on a network that dropped all ICMP
  and could not open TCP to some hosts (Calrec, ESS). Count that string before
  trusting a cycle's failures; `net::ERR_NETWORK_CHANGED` marks only a brief
  interface change. A connectivity probe that passes proves little.
- **Counting a cycle's deactivations by `updated_at` overcounts.** The shared-URL
  dedup re-stamps already-inactive sub-brand rows at the start of every cycle
  (Sonnox, Novation DJ): 900 by timestamp on 2026-09-25 against the summary's 754.
  Use the summary's `deactivated=`, or exclude rows stamped at the cycle's start.

## 7. Company notes

| company | what matters |
| --- | --- |
| Adobe | Renamed from "Adobe Audition"; whole-company Workday board scoped with `?q=audio`, partial scope. |
| Advanced Bionics | A Sonova brand sharing `sonova.com/careers/`, so it was the company scraping Sonova's jobs (91 rows, no descriptions). Set `verified: false` 2026-11-10; Sonova now scrapes `jobs.sonova.com` itself. |
| Amazon | amazon.jobs `search.json` needs `base_query` (audio, speech, signal processing); "dsp" is a trap here. |
| Anaheim Ducks | Added 2026-11-10 (owner). Workday site `Linkedin` scoped `?q=audio`; 3 jobs, 1 board row (Lead Audio Engineer). Category `Professional Audio & Live Sound` for lack of a sports one. |
| Analog Devices | Workday `analogdevices.wd1/External`, narrowed 2026-11-12 to `?q=audio` + `?q=dsp` (104 jobs, 14 s; unscoped ~805 timed out 3 cycles in 5). Both searches together cover all 4 board rows. |
| Amplitude | `verified: false` 2026-11-12: a product-analytics company, not audio, and its Greenhouse board 404s. |
| Apple | Parser reads `?search=` from seed URLs so `extra_careers_urls` can scope it; Beats by Dre was deleted after an empty-slug Apple binding scraped 245 Apple rows. |
| Arup | Avature facet derivation ends at a stable `/jobs/search/<id>`; never seed the session-stateful `/add/category/<id>` URL (same for Hoare Lea, Ramboll, Stantec, Sweco). Reposts roles under new requisition numbers; the superseded rows stay listed as duplicates while either of its two URLs fails (a partial result), then clear (11 on 2026-10-04). |
| Audible | Deleted from seed and DB; 112 jobs, 1 misattributed board row. Do not re-add without measuring. |
| Audio Precision | Native `Audio Testing & Measurement`; no `open_application` on purpose (page refuses unsolicited CVs). |
| Bang & Olufsen | SAP DWR board, unfetchable; `verified: false` by design. |
| Beltone | Retail dispensing chain; 0 board rows since the clinical filter — correct, not a bug. |
| Belden | SuccessFactors `?q=engineer` since 2026-11-12 (53 jobs, 4 s) to stop a 90 s timeout. 0 board rows under every term tried (audio, broadcast, engineer) — a candidate for `verified: false`. |
| Beyerdynamic | No scrapable listings; NA page is `open_application` + `scrape_blocked`. |
| BMG Production Music | Points at its own (empty) SmartRecruiters board, not Bertelsmann's 955-job one. |
| Bosch Group | Six curated SmartRecruiters searches cut 4,836 rows to 107 with all board rows kept; Bosch Security deleted. |
| ByteDance | Blocked; entries for TikTok Audio and Resso deleted as dead duplicates. |
| Calrec | `careers.calrec.com`, works; no longer blocked. |
| Cinder | Blocked on purpose (Wellfound/Compas behind Cloudflare; the Wix page renders no list). Owner asked for one job 2026-11-10: route it through community submission, not evasion. |
| Cirrus Logic | Lever EU tenant (`api.eu.lever.co`); `api_url_for` derives the host from the careers URL. Category `Audio Semiconductors` (native). |
| Cisco Webex | Repointed 2026-11-09 from the Phenom landing page (scraped only nav links) to Cisco's Workday board `cisco.wd5…/Cisco_Careers?q=audio`; recategorised `Consumer Electronics & Tech` (partial) because native scope let 5 sales/CS roles onto the board. "speech" query added nothing. 22 jobs, 2 board rows. |
| CD Baby | `verified: false` 2026-11-12: Greenhouse board gone; careers now redirects to Universal Music. |
| Cochlear | Native hearing tech; many board rows are clinical/commercial via the category bonus — accepted trade-off. |
| Delart | Embed-only Greenhouse board; do not repoint to delartech.com. Agency scope. |
| Demant | SuccessFactors `careers.demant.com/search/`, narrowed 2026-11-12 to `?q=engineer` plus `test`, `dsp`, `acoustic` (manual): ~19 s instead of a timeout every cycle since 2026-09-11. That retired 24 unconfirmed board rows, nearly all clinic/admin. `?q=developer`/`software` mostly add clinic roles (the search matches "développement"). `careers.demant.com/` (marketing) and `careers.us.demant.com/jobs` (clinic hiring) are traps. 9 board rows. |
| DiGiCo | `digico.biz/recruitment/`, healthy. |
| Dirac Research | Re-verified 2026-11-12 (owner). Swedish audio DSP licensed to car and device makers; moved from Consumer Electronics (partial) to Audio Middleware & SDK (native), which keeps its Home & Pro developer role (score 80; 45 under partial). Jobs are on Hailey HR (`dirac.careers.haileyhr.app`, `scrapers/ats/haileyhr.py`): listing cards put location and department chips before an `<h3>` title, and descriptions are Markdown inside the Next.js `self.__next_f` stream (`<id>:T<hex bytes>,` text chunk), not the HTML. 4 board rows. |
| Dolby | Eightfold `/api/pcsx/search`, `domain=dolby.com`; new Eightfold companies need two cycles (slug derived). |
| ElevenLabs | Bound to Ashby `elevenlabs` 2026-11-24 (owner), `partial` scope set in the DB. Earlier it was left off on purpose (52 of 54 board rows would have been sales); the 2026-11-24 measurement was 9 rows at native (5 commercial) and 2 at partial (Audio Engineering (Freelance), Android Engineer – Creative App). Its engineering titles are generic, so few score. Before this the seeded `elevenlabs.io/careers` page failed 42 cycles. |
| Fender / inMusic / Logitech | Each board was being claimed by a sub-brand via shared-URL dedup; sub-brands are `verified: false`. |
| Focusrite / Music Tribe | One board per group (Workable; Jobvite `musictribe`); brand entries retired. Check footers for umbrella owners. |
| Garmin | Jibe JSON API via `JIBE_HOSTS` allowlist. |
| GN Store Nord / Jabra / SteelSeries | One Workday tenant (`gn.wd3`), three sites. Offline from 2026-10-01 until early November for the sale of GN Hearing to Amplifon; 31 board rows deactivated (§5). |
| Gibson | Own scraper — the public ADP endpoint withholds 17 of 36 requisitions. MESA/Boogie retired into it. |
| Google | `?q=audio`, `scrape_method: http`; needed `<base href>` handling and pagination. |
| Harman | Several `extra_careers_urls` queries; no Avature parser needed. |
| HP IQ | Added 2026-11-12 (owner). HP's AI/Poly unit, separate from HP Inc.'s Eightfold site: its `hp-iq.com/join-us/<id>?board=hp` pages are the Greenhouse board `hp` (bound `greenhouse`/`hp`). 26 jobs, 3 board rows (Senior Acoustic Engineer, Audio Hardware Engineer, Senior Audio Software Development Engineer); the rest are agentic-AI and Poly firmware roles. |
| **Knowles Corporation** | ADP **MyJobs**, which the `adp` parser (Workforce Now) does not speak. **Do not build a MyJobs parser:** Knowles yields 0 audio jobs even at native scope, and the only other MyJobs company is Switchcraft (whose URL is HEICO's). The API recipe is in the old log (`DO NOT REPEAT: Knowles`). It has no stored ATS binding; 404s against Workforce Now are discovery guesses. |
| IAG (International Audio Group) | Added 2026-11-17 (owner). Parent of Wharfedale, Quad, Audiolab, Mission, Leak, Castle, Luxman and Wharfedale Pro; every brand posts on `iaggroup.com/jobs/` (WordPress "WP Job Openings" plugin). `scrapers/ats/awsm.py` reads `/wp-json/wp/v2/awsm_job_openings`; location and employment type come from `class_list` slugs (`location-*`, `employment-type-*`). The brands' `/jobs/current-vacancies/` URL was an empty page, so Audiolab, Quad Electronics and Wharfedale are now `verified: false`. |
| Laran | Added 2026-11-10 (owner). Custom page, http; titles carried "→ Los Angeles, ITAR-Eligible", stripped by `ARROW_SUFFIX_RE`. 3 jobs, all on the board (two founding roles at the 45 line). |
| Lockheed Martin | Added 2026-11-14 (owner). Eightfold `lockheedmartin.eightfold.ai`, `ats_slug` `lockheedmartin.com` (the host's own domain is eightfold.ai), scoped like Northrop: `?query=acoustic` + `?query=sonar`. 67 jobs, 7 board rows (Sonar/Acoustic Engineer, Acoustics Mechanical lead, signal-processing roles). |
| Meta | Repointed 2026-11-08 (owner-requested, `source: manual`): `metacareers.com/jobsearch/?q=audio` + extra `?q=sound`. The pager is JS buttons, so it was read one page deep for months (14 rows, 10 on the board, of 75 audio results). `PAGE_PARAM_HOSTS` in `pagination.py` now walks `?page=N` until a page brings no new jobs; titles come from the card `<h3>` (`INNER_HEADING_TITLE_HOSTS`). 103 rows, 21 on the board. "Project Manager, Organic Content Integrity Operations - Speech Problems" scores on and is not audio work. 400s on job links are bot defence, whitelisted in `check_links`. See the rate-limit trap in §6. |
| OpenAI | Added 2026-11-08 at the owner's request ("Audio Engineer, Live Video"). Ashby `openai`, 816 jobs; `Consumer Electronics & Tech` for partial scope, like Anthropic. 2 board rows. |
| Anthropic | Added 2026-11-04 at the owner's request for one AV Production Specialist role (pinned). Greenhouse, 682 jobs; category `Consumer Electronics & Tech` so scope is partial — native scope put 22 rows on the board including Customer Success Managers. 0 scored board rows; the AV Engineer roles score 60, under partial's 65. |
| ai-coustics | Added 2026-11-04. `join.com/companies/ai-coustics`; join.com job URLs are bare slugs, so `join.com` is in `SLUG_BOARD_HOSTS` and `INNER_HEADING_TITLE_HOSTS` (card text otherwise carries location and department). 5 jobs, none scored onto the board; Head of Marketing pinned. |
| Holoplot | Added 2026-11-04. Personio `holoplot.jobs.personio.de`, generic http; Personio hosts read the title from the card's `<h3>` (`INNER_HEADING_TITLE_SUFFIXES`) — before that the title carried "Berlin Full-time Permanent employee". Personio also serves `/xml` if a dedicated parser is ever wanted. 7 of 8 on the board. |
| JAM Industries | Added 2026-11-04 (Canadian distributor; owns Ashly Audio). Dayforce `jobs.dayforcehcm.com/en-US/jam/CANDIDATEPORTAL`, Playwright only (http finds no links). Partial scope; 2 board rows (Ashly DSP and Embedded engineers). |
| Muse Group | Added 2026-11-04 (MuseScore, Audacity, Ultimate Guitar). `www.mu.se/positions`, http, 26 jobs; 1 scored board row (Full Stack Producer, Audio ML) plus the pinned CPO. |
| Music-tech sheet batch | Added 2026-11-16 (owner) from a public music-tech tools sheet (129 rows; ~21 already in the seed). 12 added, all verified by an offline trial scrape: Too Lost (Lever, 4), Trolley (Greenhouse, 15), Laylo (YC, 7), Vydia (page, 1), Orfium (Workable, 8), Elastic Stage (Workable, 7), BMAT (Workable, 2), Luminate (Greenhouse, 3), Wavo (BambooHR, 1), ONErpm (Rippling page, 7; 1 board row), Cyanite and Loudly (JOIN, 0 open today). Music-business tools use Streaming & Music Services or Audio IP & Licensing (partial scope), so only their audio roles reach the board. Not added: no careers page at all for most of the ~95 small startups; Notion careers pages (RouteNote, Infinite Catalog) answer our scraper 429; Chartmetric, Feature.fm, SongVest, Pex (now Vobile), MusiMap, Fanify pages list no readable jobs; Viberate's page parses as junk; name collisions to avoid: Gateless (mortgage), Instrumental (manufacturing AI), greenhouse `symphony` (Symphony Communication), JOIN `royal`/`figaro`/`stan`. Already covered under another name: Suno, Logic (Apple), Pro Tools (Avid), Max (Cycling '74), Reaper (Cockos), Music AI (Moises), Musiio (SoundCloud), SoundBetter (Spotify), SoundOn (ByteDance). |
| AIAIAI Audio | Added 2026-11-16 (owner). Copenhagen headphone maker; Headphones & Personal Audio (native). JOIN board `join.com/companies/aiaiaidk`, read by the generic http scraper like ai-coustics: 3 jobs with full descriptions, all scoring as audio (VP Commercial & Brand Growth NA, Head of Finance, Community & Music Creator Assistant). Locations are not parsed off JOIN pages. |
| Pocket | Added 2026-11-14 (owner). YC W26 AI voice recorder; Voice & Speech Technology. Careers page is its YC Work at a Startup board (`ycombinator.com/companies/pocket/jobs`), read by the generic http scraper: 15 jobs, 1 board row (Research Engineer – Voice Intelligence). Locations are not parsed off YC pages. |
| Quippy | Added 2026-11-10 (owner). Ashby; 7 jobs, 1 board row (Realtime Voice Engineer). |
| Rockford Fosgate | Was "Rockford Marine" until 2026-11-09 (renamed in seed and DB together, now manual). Careers page lists each job as a card linking a PDF; descriptions come from the PDFs. 5 of 9 on the board; Quality Engineer's PDF is a scan. |
| Sesame | Added 2026-11-10 (owner). Ashby; 18 jobs, 3 board rows (Audio Systems, Speaker Systems, HW Test Automation at 45). |
| Sonova (Phonak/Unitron) | Repointed 2026-11-10 to SuccessFactors `jobs.sonova.com/search/?q=engineer` plus `q=audio`, `q=acoustic`. Unscoped it has 384 jobs, but only 150 get descriptions (`MAX_DETAIL_FETCHES`), so the rest score on title alone. Scoped: 116 jobs, all described, 32 board rows; clinical audiologist listings mostly drop out. |
| Stantec | Fixed 2026-11-16 (owner). Jobs live on `stantec.jobs`, a DirectEmployers .jobs site whose listings come from `prod-search-api.jobsyn.org/api/v1/google-talent/search` (needs an `x-origin: stantec.jobs` header). `scrapers/ats/jobsyn.py`, allowlist `JOBSYN_HOSTS`, runs every `q=` in the careers URL (`acoustic`, `acoustical`, `audiovisual`: ~150 listings vs 7,219 unfiltered) and merges per-location listings into one job per `reqid`. Scope set to `partial` in the DB (row is manual): `native` let ICT consultant and scheduler roles through at score 45. 5 board rows; "AV Designer" does not pass. |
| Stryker | Added 2026-11-10 (owner). Workday `StrykerCareers?q=acoustic` (`Stryker_Careers` 404s); 2 jobs, both on the board. Partial scope. |
| Syntiant | Added 2026-11-04. Workable `syntiant`, `Audio Semiconductors`; 8 of 12 on the board. |
| Splice | Repointed 2026-11-04 from `splice.com/careers` (22 consecutive failures) to `job-boards.greenhouse.io/splice`; 6 jobs, none scored on, Senior Brand Marketing Manager pinned. |
| Microsoft | Repointed 2026-10-17 (owner-approved, `source: manual`): Eightfold `apply.careers.microsoft.com/careers?query=audio` + `?query=speech`, `ats_type: eightfold`, `ats_slug: microsoft.com`. The old URL was the marketing homepage, which only ever yielded "Hiring tips" and "Contractor roles". The unfiltered board is ~2,490 jobs, far past the 200 cap, so it must stay query-scoped. 6 board rows (Audio and Acoustics research intern, Azure Speech, Voice Agent roles). Custom-domain Eightfold needs the stored binding — `check_url` cannot test it (it builds the company with no `ats_type`); a harness that sets it is the only way to measure first. Xbox Game Studios and Playground Games still point at the old homepage (2 furniture rows, never on the board); unverify or repoint them. |
| Native Instruments | JS SPA with no ATS link; blocked-list. |
| Northrop Grumman | Eightfold needs `domain=ngc.com`. |
| Perkins&Will | Real board on UltiPro (152 jobs, none audio); kept for its acoustics practice. |
| Qualcomm / Infineon | `extra_careers_urls` for audio + dsp (+ acoustic) because Eightfold capped at 120; "dsp" admits some NPU/modem noise, accepted. |
| Ramboll Group | See §5. Talent-pool "Rail Power Supply" rows fixed by `TALENT_POOL_TITLE`, not dedup. |
| Rohde & Schwarz | `jobs.rohde-schwarz.com` now redirects to `www.rohde-schwarz.com/uk/career/jobs/career-jobboard_251573.html`, and http cannot reach the `jobs.` host at all, so Playwright scrapes it every run. Until 2026-11-11 its relative job links were resolved against the requested `jobs.` host, which 404s for job pages — every R&S link on the board was dead. Fixed by resolving against the final URL (§4.3); 8 board rows. ~39 rows are country-selector links (`career-jobboard…?change_c=XX`), all off the board. |
| Samsung | Workday `sec.wd3/Samsung_Careers?q=audio` since 2026-11-12 (manual), 66 jobs in 7 s; the unscoped ~650 timed out most cycles. `?q=acoustic` finds nothing. 2 board rows, both sales directors for TV & audio. |
| Sigma Connectivity | Group JSON API filtered client-side via `company_startswith`; do not "fix" it to the server's exact-match `?company=`. |
| Sony | Workday `sonyglobal`, both `SonyGlobalCareers` and `SonyJapanCareers` with `?q=audio` (manual, 2026-11-12). The Japan board was never actually scraped before: the extra URL inherited the global binding (§4.2). Now 5 board rows, all Japan audio-AI research. |
| Starkey | UltiPro `LoadSearchResults` API. |
| Tymphany | Replaced Peerless; `open_application`, manual; contact form only, so failing is correct. |
| Vifa | Still points at `dst.dk`; `verified: false` on purpose. |
| Waymo | Search param is `query`; alphabetical pagination needs several narrow queries. |
| Wienburg | Added 2026-11-12 (owner). Düsseldorf real-time audio for defence/security, "redefining hearing in critical scenarios" — Hearing Aid & Hearing Tech (owner's call; was Headphones); one-page jobs list at `wienburg.io/jobs/`. Its "View posting" button carries screen-reader text ": Founding Engineer", which was the longest link text and won the title until `CTA_PREFIX_RE` (§4.2). The "Download PDF · 3 pages" link is stored but scores 0. |
| Zoom | `careers.zoom.us/jobs/search` dead since 2026-09-29; its 60 jobs were deactivated by a navigation-only scrape (§5). Needs a new URL. |
| Zoom | Repointed 2026-11-17 (owner) from `careers.zoom.us/jobs/search` (found 2 stray rows) to Workday `zoom.wd5.myworkdayjobs.com/Zoom`, unfiltered (70 jobs, all get descriptions). Scope `partial`: `native` let an AI Deployment Strategist through at 45. |

## 8. Stale files in the repo

- `SEED_WORKLIST.md`, `careers_url_proposals.md` (both 2026-08-29) and
  `seed_url_audit.md` (2026-09-10) are old worklists superseded by `TRIAGE.md`.
  They are tracked; a fresh session may trust the wrong one. Owner to decide on
  deletion.
- `scraper/BRIEF.md` is complete and historical.
- `README.md`'s headline numbers are from 2026-09-18 (1,413 companies, 1,260 on
  the board), and its "The audience is audio engineers" paragraph is one side of
  the open question in §2.5.
- `web/asoundjob.db` is a stray empty file; the real database is `asoundjob.db` at
  the repo root (relative SQLite URLs are anchored to the repo root by
  `resolve_database_url`, so running from `scraper/` is fine).

## 9. Log (newest first, keep entries short)

- **2026-11-24, scrape audit, part 2** — `diagnose_failures` over all 377 failing companies:
  75 unknown, 52 JSON endpoints (almost all site chrome, not jobs), 46 storefronts, 36 dead
  URLs, 33 careers hosted elsewhere, 31 on an ATS we lacked or had not bound, 29 careers
  landing pages, 17 JS-rendered, 16 that say they have no openings, 13 bot-blocked.
  Repointed: Electro-Voice (its URL was a car dealer; now Keenfinity's SmartRecruiters board,
  `?q=audio`, 12 board rows), Cadence (Workday `?q=audio`, 2 Tensilica DSP rows at partial
  scope), CEVA (regional career pages, 3 audio DSP rows), Audiokinetic (Greenhouse
  `audiokinetic-en`), Resident Advisor (Workable), Deezer (`/en/jobs`), McIntosh Automotive
  (Bose's McIntosh board, 1 row), Paradox Interactive, Antares (BambooHR, empty), Valcom
  (Paycom), DEWESoft. Unverified: EPOS (jobs are on Demant's board), Bandcamp (Songtradr's),
  Plantronics (HP), Middle Atlantic (Legrand AV's), Peavey (careers page redirects to
  Contact Us), Stem (homepage; Lever board gone), Radial Engineering (a product page).
  Slate Digital's Personio board is empty, which a generic scrape reports as a failure; a
  Personio XML parser would make it trusted, but only three companies use Personio.
  Nothing's Greenhouse EU embed points at a board that 404s; DSP Concepts' too.
  Verified on prod the same day: 43 of the 45 repointed companies scrape successfully (part 1
  and 2), adding 50 board rows (Electro-Voice 12, TI 11, HDR 8 once its third URL ran, CEVA 4,
  Cundall 3, Cadence 2, Kirkegaard 2, and singles). Still failing: Slate Digital (empty
  Personio) and Valcom (its Paycom board renders 10 jobs in local Playwright but not on the
  server). Of ~75 notable unverified companies checked as seeded, none had a working URL
  that is not already covered by a parent (Wharfedale's job is on IAG's board).

- **2026-11-24, scrape audit, part 1** — Of 1,472 companies, 345 verified ones had failed 3+
  cycles (269 "no job links", 39 HTTP 403, 24 HTTP 404). Probed every failing or unverified
  company against nine ATS APIs by name and scanned their pages for ATS links; most name
  matches were other companies (Pinpoint's demo boards answer to any name). New `teamtailor`
  scraper (RSS feed, a trusted empty): Neural DSP, Elektron, XLN Audio, Amuse, Tracklib,
  Resolution Games (all empty today, so their stale rows now close properly) and Finders
  Seekers. Paylocity and Taleo detail fetches stop at a deadline (Gentex was timing out at
  90 s; HDR's third URL was skipped). Repointed: Texas Instruments, Legrand AV, Harmonic
  (Oracle), Keysight and Navistar (Jibe; both left iCIMS), Otter.ai, TCL North America, LG
  Electronics US, Baidu USA (Greenhouse), Kawasaki (UKG), Mackie (Paylocity), Kinetics Noise
  Control (SmartRecruiters), Firelight/FMOD, GungHo America, Kirkegaard (BambooHR), Fairphone,
  Slate Digital (Personio), Skullcandy, Earlens, Grass Valley, CereProc, Spatial, Cundall
  (iCIMS); Aston Martin to http (PageUp lists 12 jobs over http, none on playwright).
  Unverified: Native Instruments (now inMusic's Pinpoint board, like Akai) and Sleep Cycle
  (no careers page left). Waves, Audio-Technica (Indeed only) and most small makers simply
  have no openings; an empty generic page stays a failure by design.

- **2026-11-24, Nintendo** — In the seed since the first commit and failing every cycle since
  2026-09-17 (`careers.nintendo.com/` has no job links). The site is a front end for
  Greenhouse board `nintendo` (76 jobs); bound to it. 4 board rows: two NTD audio software
  roles, the Retro Studios Audio & Localization Producer, and Retro's "Technology Engineer"
  (engine generalist; scores on "audio" in a list of engine areas, borderline).
  Greenhouse's `absolute_url` (`careers.nintendo.com/?gh_jid=…`) opens the careers home page,
  not the job, so `GH_JID_JOB_PAGES` in `greenhouse.py` rewrites it to `/jobs/{id}/`.

- **2026-11-24, Oracle Recruiting Cloud, INL, Langan** — New `oracle` scraper for Oracle
  HCM Candidate Experience sites (`*.fa.*.oraclecloud.com/hcmUI/CandidateExperience/.../sites/
  {site}`): the public `recruitingCEJobRequisitions` finder (honours `?keyword=`) plus
  `recruitingCEJobRequisitionDetails` for descriptions; no login. Added Idaho National
  Laboratory (professional site CX_1001 and intern site CX_1002, keyword "acoustic") and
  Langan (Greenhouse; 576 jobs, only its two noise practice-leader roles score on). Corsair,
  failing 55 cycles on playwright, now reads its 61 jobs; it moved from Headphones to Consumer
  Electronics & Tech (partial), which keeps the 3 audio roles and drops 11 generic QA and
  engineering roles. Modeltalker's URL is a Nemours hospital job page; the whole board is 471
  clinical jobs, so it is scoped to `?keyword=ModelTalker` (0 today). Handshake links need a
  login and cannot be scraped.

- **2026-11-23, Songtradr, RS&H, Finders Seekers** — Songtradr repointed to its BambooHR
  board (`songtradr`); the old `songtradr.com/careers` page has no job links. Bandcamp still
  points at that page and has failed 54 cycles. RS&H added (iCIMS, 266 jobs, mostly
  architecture; its Noise Specialist is the one board row). Finders Seekers added as a
  recruiting agency (Teamtailor career site, generic http, agency scope): it posted
  Songtradr's Senior ML Engineer, Audio/Music Processing. `acoustics_consulting` gained
  "noise specialist", "traffic noise", "highway noise" (strong) and "noise studies" (weak):
  no board flips, one tag added, golden unchanged. Rex.zone was not added: its "Audio
  Engineer Jobs Los Angeles" page is a templated AI data-labeling recruiting page, not an
  opening.

- **2026-11-21, nine engineering and AV employers** — SuccessFactors sites built on the newer
  React career-site template (no `jobTitle-link` anchors; the page loads
  `reactWidgetLoader.js`) are now read from `POST /services/recruiting/v1/jobs`. That fixed
  CNH, which had failed since September; it is now keyword-scoped (NVH, acoustic, audio).
  Detail pages there carry several `itemprop="description"` nodes, and the longest one is used.
  UltiPro now accepts the new `*.rec.pro.ukg.net` hosts. Added Kimley-Horn (Jibe), thyssenkrupp
  (playwright, `?search=`), SSR (UKG), Black & Veatch, Alvine (Trakstar), University of Oregon
  (PageUp), PMY Group (its own careers page; the Gusto board is behind Cloudflare) and NDM
  Hospitality (ApplicantPro, playwright). Kimley-Horn and NDM were set to `partial` in the DB:
  Kimley-Horn's keyword search returns about 290 mostly land-development jobs.
  thyssenkrupp was then moved from Automotive OEMs to Acoustic Consulting & Engineering
  (it is a conglomerate; a car category would tag a Marine Systems sonar job automotive) and
  kept `partial` in the DB. Its search is client-rendered, so it stays on playwright, but its
  job pages carry JSON-LD: `JSONLD_DETAIL_HOSTS` in `playwright_scraper.py` fetches those over
  HTTP for descriptions. Tried and rejected: requiring `ROLE_START_MARKERS` at line start (a
  mid-sentence "Preferred qualifications" cuts the thyssenkrupp Acoustic Engineer's role text
  to its tail) moved 20 jobs on and 12 off, mostly Amazon Music/Deepgram marketing on, and
  dropped golden precision 96.2% to 95.7%.
  On the first scrape, `_try_discovery` found a Workday link on thyssenkrupp's search page,
  verified it and stored `workday/thyssenkruppmaterialsna.wd12/1`. That is the steel
  distribution board, which ignores the search, so the next cycle replaced the 3 NVH jobs with
  198 warehouse jobs (none listed). Discovery now skips any careers URL with a query string,
  since a found board would drop the scoping. Checked every scoped company's stored binding;
  thyssenkrupp was the only mismatch, and its binding was cleared in the DB.

- **2026-11-20, company-type tags and relevance false positives** — Jobs at car companies
  (Automotive OEMs, Car Audio) now always carry `automotive_audio`, and jobs at music-tech
  companies (instruments, DJ, plugins, DAWs, audio interfaces) carry `music_technology`, via
  `with_company_domain`. The tag is added after scoring so it never lifts a job onto the board,
  and business/sales-only roles are skipped. Relevance now ignores the company's own name
  ("L-Acoustics" is not an audio mention), cuts trailing "Who we are"/"About us" sections, and
  drops "Voice of Customer", venue names like "Music Hall", and DSP next to LiDAR/radar/RF/video
  in titles. Effect on the live board: 41 jobs off (mostly Shure IT, L-Acoustics corporate,
  Live Nation lighting), none added, 52 tags added. New Taleo and Paylocity scrapers; HDR,
  Salas O'Brien, ME Engineers, Gentex, Leonardo DRS, RWDI, Hexany Audio added. Gentex,
  Leonardo DRS and ME Engineers were set to `partial` scope in the database (whole-board
  scrapes); that lives in the DB, not the seed.

- **2026-11-18, Meta failing only in the nightly run** — Meta scraped fine by hand but failed
  both 08:00 timer runs ("page loaded but no job links found"). Under nightly load the
  `networkidle` wait times out, and the `domcontentloaded` fallback read the page after 500 ms,
  before the JS job list rendered. The fallback now calls `settle_links`, which waits until the
  link count holds steady for 3 s (capped at the page timeout). Reproduce the fallback path with
  `PAGE_LOAD_TIMEOUT=3 python -m scraper.check_url <url>`; before the fix Meta gave 14 of 75.

- **2026-11-18, categorization audit** — Hand-labelled 211 board jobs into
  `scraper/tests/fixtures/category_golden.json` (acceptable categories per job). Score with
  `python -m scraper.category_eval [--misses]`; `tests/test_category_golden.py` fails if hit rate
  drops below 85%, all-right below 80% or label precision below 95%. Before → after: hit 67.8% →
  86.3%, all right 63.0% → 82.5%, precision 92.5% → 96.1%. Changes: two new categories,
  `av_systems_integration` (AV design, integration, control programming, PA/voice alarm) and
  `business_operations` (label-only; a fallback for business titles with no other category and no
  engineering word in the title); titles at "Acoustic Consulting & Engineering" companies go to
  acoustics_consulting instead of audio_systems (consult/acoustical titles, or acoustic titles
  without "engineer"); a title-only "audio engineer" no longer keeps audio_systems when a studio,
  stage or AV category also fits; music production gained post-production vocabulary. Board:
  uncategorized 322 → 192, acoustics 21 → 50, music production 4 → 19, audio systems 155 → 112.
  Keyword changes risk pulling non-audio jobs onto the board (a new category lifts relevance), so
  diff `is_audio_related` across a prod snapshot before deploying, as was done here.

- **2026-11-17, live venue audio roles** — Live Nation's "Audio Engineer"/"Audio Tech" jobs had no
  Live Sound category. Two causes: the keyword list lacked venue vocabulary, and
  `extract_role_text` started at "requirements" inside the EEO paragraph, so it read only legal
  text. Role markers after an "Equal Employment Opportunity" statement (past 30% of the text) are
  now ignored. A line-start-heading rule was tried and rejected: it changed ~40 unrelated jobs for
  the worse. Added "house audio", "head audio", "foh", "front-of-house", "monitor mix" as strong
  keywords; venue words ("venue", "concert", "stage", "stage production", "load-in") count only
  when the title says audio or sound (`LIVE_VENUE_PATTERN`), because unrestricted they made
  stagehands, Niantic "Live Events" marketers and a Full Sail faculty post audio-related. Board
  effect: 22 jobs gain Live Sound, none lose one. Reading real role text also made 3 jobs
  audio-related (Audible content acquisition 13806, Live Nation stagehands 42282/42288).

- **2026-11-17, game studios and SoundLister finds** — The Gaming category was mostly dead links
  (Larian pointed at a board-game merch page). Repointed to their ATS boards: Epic, Riot, Roblox,
  Discord, Insomniac, Naughty Dog, Ubisoft, CD Projekt Red, Larian, Bungie, Rockstar, and
  NBCUniversal Audio (SmartRecruiters `?q=audio`). Added 2K, Krafton, Remedy, Supercell,
  thatgamecompany, Mob Entertainment, Housemarque, Sphere Entertainment, Live Nation (Workday
  `?q=audio`, venue sound engineers) and Vox Media. Big studios set to `partial`. Not done: EA,
  Blizzard, Gearbox (no readable board found), SiriusXM (moved off iCIMS), Soundtoys (job pages have
  no job-shaped URLs).
  Audio-titled roles at Gaming-category companies now also get `game_audio_interactive`
  (`is_game_studio_audio_role`); /jobs/game-audio went 4 → 25.

- **2026-11-17, specialty landing pages** — `/jobs/<slug>` for each of the 21 categories
  (`web/src/lib/specialties.ts`: slug, heading, lead; route matcher `src/params/specialty.ts`), for
  searches like "game audio jobs". The board moved to `lib/components/JobBoard.svelte` and its loader
  to `lib/server/board.ts`; both routes render it. Filter changes leave for `/jobs?category=…`
  (canonical `/jobs`), so combinations are never indexed. Pages with categories in the sitemap;
  homepage, job pages and the board link to them; empty ones are `noindex`. A new category in
  `audio_job_categories.json` needs an entry in `specialties.ts` (a test enforces it).

- **2026-11-17, remote flag and more scope fixes** — `detect_remote` flagged any job whose
  description said "remote" anywhere (remote support, "not a remote role", Shure's internship
  boilerplate), and the job page put that in Google's JobPosting data as TELECOMMUTE. The
  description now counts only role statements (`describes_remote_role`), skipping sentences with
  not/no/never/variety. Existing jobs fixed by a one-off pass: board remote 114 → 53. Known miss:
  Muse Group pages that say only a bare "Remote". Also set to `partial`: Activision Blizzard,
  Disney, Twilio Voice, Penn State, UT Austin, Liquid AI.

- **2026-11-17, Zoom and IAG** — Zoom repointed to its Workday board (see §7). IAG added as the
  parent for its brands with a new `awsm` parser; Audiolab, Quad and Wharfedale unverified.

- **2026-11-17, scope fixes for big generalist companies** — Logitech, Razer, Rohde & Schwarz,
  Northrop Grumman and Lockheed Martin set to `partial` (now manual) through `admin_update_company`.
  Under `native` every generic engineering job got the +10 native bonus and landed on exactly 45,
  the cutoff: board went 29→4, 13→3, 6→1, 19→7, 9→8. Hearing-aid makers (Sivantos etc.) stay
  `native` on purpose: their hardware roles build hearing aids. New `is_shift_work_dsp_title` drops
  Bosch's West Memphis warehouse "DSP (1st Shift)" jobs, where DSP is a department. To find more
  of these, rank `native` companies by active jobs and preview them as `partial` before switching.

- **2026-11-16, Stantec scrape fixed** — had failed 33 cycles on its marketing careers page. New
  `jobsyn` parser for DirectEmployers .jobs sites (see §7 Stantec). Brings in the Acoustics Intern
  (Summer 2027) the owner found, plus the acoustical consultant, designer and noise analyst roles.

- **2026-11-16, launched at https://asoundjob.com** — Hetzner Cloud, Helsinki, 4 GB
  x86, Ubuntu 24.04, set up exactly per `DEPLOY.md` (no deviations needed). The dev
  database was copied up (1,441 companies), so production starts with the same
  featured job, pins and history. The nightly scrape runs at 03:00 New York time;
  test scrapes over a job-board API (Cirrus Logic) and the headless browser (Sandy
  Brown Associates) both succeeded from the server. **From now on the live
  database is the real one**; the local `asoundjob.db` is a stale copy for
  development, and production changes ship with `deploy/update.sh`.

- **2026-11-16, deploy prep** — `deploy/` and `DEPLOY.md` (systemd + Caddy + SQLite,
  no Docker). SQLite now runs in WAL mode with a 30 s busy timeout
  (`scraper/database.py`), which fixes "database is locked" during scrapes. The
  scraper takes `.scrape.lock` so two cycles never overlap (exit 75). `robots.txt`
  is generated from `SITE_URL`; Resources and Interview prep are out of the nav
  and sitemap.

- **2026-11-16, crowd seed edits + scrape status** — company suggestions now take a
  careers URL, website and category (plus comment-only reports); the admin queue
  shows current → suggested, and approving writes the seed (via `sync_company`) and
  clears `ats_type`/`ats_slug` when the careers URL changes, so the next scrape
  re-detects the board. Directory cards gained a suggest-edit pencil. Public company
  responses carry `scrape_status` (`tracked` = verified, has a careers URL, last
  scrape clean; `failing` = recent failures; `untracked` = everything else) shown on
  company pages and cards. Migration `c8a4e2f7b915` applied to the dev DB. Counts
  today: 387 tracked, 162 failing, 892 untracked.

- **2026-11-16, feature requests on Submit a job** — submitters can ask for a feature
  (days or until filled, plus a note); admins edit or decline it in the submission
  queue. Migration `b5e3d8a1c602` applied to the dev DB.

- **2026-11-16, feature-request terms** — requesters pick days or "until filled" and
  suggest a note; admins edit both before approving; admins can feature with no end
  date. Migration `f2c6a9d1b384` applied to the dev DB.

- **2026-11-16, featured jobs + homepage trim** — featured jobs with an admin note
  (§4.7), migration `e8b1f4c2a7d3` applied to the dev DB. Removed the homepage's
  three-column "Refreshed / specialties / community" block and the "Hiring in
  audio?" CTA (Submit a job stays in the header). Job cards gained a bottom-right
  external-link icon; pagination is now 1 … n-1 n n+1 … last.

- **2026-11-14, admin job pinning** — new `/admin/jobs` page with
  `GET /api/admin/jobs` (search incl. pasted URLs; `show=all|hidden|overridden`) and
  `PUT /api/admin/jobs/{id}/audio` (`true` pin on, `false` hide, `null` back to score,
  which re-scores the job). Pinned Microsoft 40440. A scoring rule for "asks for audio
  experience" was adopted the same day (§4.5).

- **2026-11-16, cycle** — 726 companies, 382 ok, ~29 min; inserted 89, reactivated 44,
  deactivated 199. Workday recovered from the 11-14 outage (38 boards ok via workday).
  `cut_short=5`: Logitech 140, McGill 140, Nissan 160, Lockheed Martin 30, Acer 24;
  Apple finished its full listing inside the 180 s priority budget (235 jobs). Afterwards
  the 13 new companies (AIAIAI + the music-tech sheet batch, §7) were synced and scraped
  one by one: 58 jobs, 4 board rows. Listed 1,148 → 1,151.
- **2026-11-14, cycle** — 726 companies, 366 ok, ~29 min; inserted 144,
  reactivated 60, deactivated 168. First cycle with partial listings kept
  (`cut_short=6`): Apple 235 jobs at its 180 s priority budget, Nissan 200,
  McGill 180 (first full-ish read in weeks), Sonova 71, HP 20, Microsoft 10 —
  all would have been failures before. **Workday had a service outage on the
  wd1/wd5 hosts** during the run: the CXS API answered 200 with an HTML "Workday
  is currently unavailable" page, so 16 Workday boards failed (Sonos, Sony,
  Logitech, Adobe, Analog Devices, Cisco Webex, Stryker, Activision, Belkin,
  iHeartRadio, …). Their fallbacks read the same page and found nothing — no rows
  added or deactivated, existing jobs stay listed; wd3/wd12 tenants (Bose,
  Samsung, Razer, Toyota, HBK) were fine. One more such cycle is harmless; three
  in a row would hide them. Two 429s. **Board-eligible 1,083 → 1,079, publicly
  listed 1,073 → 1,070.**

- **2026-11-14, Lockheed Martin + Pocket** — added at the owner's request (§7); 8 board rows between them.

- **2026-11-13, keep what was read + priority boards** — a timeout or a failing
  page no longer throws away the listing pages already read (§4.2); timeouts get
  one retry; `priority` flag (2× budget, scraped first) on Apple, Shure, Cirrus
  Logic, Bose, Qualcomm, Amazon; jobs without a fresh description keep their
  stored one. Live Apple run on a very slow jobs.apple.com (dozens of 15 s read
  timeouts): the `audio` search kept 234 of ~316 jobs at the 180 s budget, 317
  jobs in all, 2 new — the old rule would have fallen back to ~7. Apple 76 listed.

- **2026-11-13, read timeouts skip the fallback** — Apple and Full Sail fell back
  in the 11-13 cycle because a `requests` ReadTimeout from a single fetch was
  treated as an ordinary error; it now counts as a timeout (§4.2). Acer's
  SuccessFactors 404 still falls back by design.

- **2026-11-13, cycle** — 724 companies, 371 ok, ~31 min; deactivated 267,
  inserted 235, reactivated 61, 7 deactivation skips. First cycle with ATS
  timeouts skipping the generic fallback: Logitech, McGill, iHeartRadio, Nissan,
  HP Inc., Twilio Voice, Microsoft and Apple timed out cleanly (no
  partial/fallback rows). Still falling back: Apple and Full Sail on a `requests`
  ReadTimeout (not an `asyncio` timeout) and Acer on a SuccessFactors 404. The
  narrowed boards all succeeded (Analog Devices 102, Samsung 66, Demant 65,
  Belden 52, Sony 32); Dirac 5 via haileyhr. Zero 429s. **Board-eligible
  1,087 → 1,074, publicly listed 1,066** (83 tagged commercial). Demo servers
  had died again and were restarted.

- **2026-11-12, commercial roles** — owner decided sales/marketing/CS roles
  belong (§2 item 5): sales titles out of `CORPORATE_ROLE`, `sales_marketing_cs`
  made label-only with a full title vocabulary, re-scored. Board 1,070 → 1,079
  listed; 87 tagged commercial. 39 commercial rows with an audio signal came on;
  32 left — customer-success and partnerships rows whose only support was the tag
  (Epidemic Sound, Twilio, RingCentral CSMs) plus two Shure accounting interns.

- **2026-11-12, job-type filter + Dirac** — untyped jobs listed after job-type
  matches (§5 Frontend); new Hailey HR parser; Dirac Research re-verified on it
  (4 board rows); Wienburg moved to Hearing Aid & Hearing Tech. Demo servers had
  died again and were restarted. **Publicly listed 1,070.**

- **2026-11-12, deploy prep + timeouts + small items** — adapter-node and
  proxy-aware rate limits (§5). Narrowed the repeat-timeout boards with search
  terms (Demant, Analog Devices, Samsung, Belden; Sony scoped and its Japan board
  scraped for the first time) and made ATS timeouts skip the generic fallback
  (§4.2). Amplitude and CD Baby set unverified. iCIMS detail cap 100 → 250 (Shure
  104 → 111 board rows). Clinic/front-office titles in other languages filtered
  (§4.5) and the board re-scored with `backfill_relevance`. Near-miss review
  (84 rows within 10 points of the cutoff): nearly all correctly excluded, cutoff
  left alone. Added Wienburg (owner). **Board-eligible 1,076, publicly listed
  1,066** (Demant −24 stale clinic rows, Sony +5, Shure +7, HP IQ +3, Wienburg +1).

- **2026-11-12, cycle + first-seen date fix** — 723 companies, 375 ok, ~29 min
  (13:15–13:44 UTC); deactivated 359, inserted 221, reactivated 144. No Eightfold
  429s for the second cycle running (Microsoft 50 jobs, Qualcomm 274). R&S clean
  via Playwright with `www.` links (76 jobs). Bose stayed on Workday (103 jobs).
  The redirect fix (§4.3) caused no visible swap elsewhere. Only 429s: JLab and
  Vintage King product pages (Shopify, non-job links). Found that `scraped_at`
  moves on every row change, so the 11-11 date sort was wrong for 129 undated
  rows; switched to `created_at` (§4.7). **Board-eligible 1,085, publicly listed
  1,075** (same 10 hidden).

- **2026-11-11, dead Rohde & Schwarz links** — owner found every R&S link 404ed:
  relative links were resolved against the pre-redirect host (§4.3). Fixed for
  http and Playwright; R&S re-scraped (76 jobs, 8 board rows, links verified).
  Also sorted undated jobs by first-seen day (§4.7).

- **2026-11-11, cycle** — 723 companies, 378 ok, 1,727 s, no page-load timeouts;
  deactivated 455, inserted 381. No Eightfold 429s (first clean cycle for them);
  Microsoft timed out instead and the enrichment budget was fixed (§5), then a
  solo re-scrape was clean (7 s, 6 board rows). Dolby's 11-10 fallback rows
  cleared on a clean Eightfold scrape (7 board rows). Ramboll, Sonova, Cisco,
  Meta and Qualcomm all clean. **Board-eligible 1,089, publicly listed 1,079**
  (10 hidden: IK 4, Otter 3, XLN 1, Valcom 1, Fairphone 1).

- **2026-11-10, cycle + Ramboll + owner additions + main fast-forward** — cycle:
  718 companies, 370 ok, 1,794 s, no page-load timeouts; deactivated 1,701 (≈1,100
  of them Ramboll's non-acoustic rows after scoping, §5), inserted 308. Ramboll
  back on the board (21 rows). Eightfold: Qualcomm clean, Microsoft partial (§5).
  Bose flipped Workday → own site → Workday across 11-08/09/10 and each flip
  retires the other URL family (75 this cycle) — the claimed-ATS fallback item.
  Owner's 11 links: Nudge, Meyer Sound (ADP), Syntiant (via Adzuna) were already on
  the board; added Sesame, Quippy, Laran, Stryker, Anaheim Ducks; Sonova repointed
  and its Valencia Sr. Research Engineer pinned; Cinder (blocked) and A2Z ProHire
  (PeoplePilot IT agency, 33 non-audio jobs) left for community submission.
  **Board-eligible 1,081, publicly listed 1,071.** README gained first-time setup;
  `main` fast-forwarded to this branch. Then the owner found search for "meta"
  returned no Meta jobs; search now matches company names and whole words (§4.7).

- **2026-11-09, cycle + Eightfold fix + Cisco** — cycle: 718 companies, 372 ok,
  1,774 s, no page-load timeouts; deactivated 167, inserted 261, reactivated 127.
  Microsoft drew an Eightfold 429 again (old code); Qualcomm did not. Built the
  Eightfold throttle/retry/no-fallback fix (§5) and re-scraped both cleanly
  (Microsoft 7 board rows, Qualcomm 52). Cisco repointed to Workday (§7): the
  owner's Audio Signal Processing Engineer is on the board; Cochlear's Senior
  Firmware (Audio & Signal Processing) role was already there. Ramboll still
  hidden. **Board-eligible 1,073, publicly listed 1,046** (27 hidden: Ramboll 17,
  IK 4, Otter 3, XLN 1, Valcom 1, Fairphone 1). `test_diagnose_failures`'s
  timing test flakes while a cycle loads the CPU.

- **2026-11-09, PDF job descriptions** — owner asked about Rockford Fosgate, whose
  jobs are PDF links. It was already scraped (as "Rockford Marine", renamed) but
  descriptions were empty for every PDF job site-wide. Added PDF text extraction
  (§4.2). Re-scraped the 16 companies with PDF job links: Rockford 3 → 5 board
  rows, Kicker 1 → 2 (Graphic Artist, borderline at 45); GRAS and RF Venue
  unchanged but now described; no furniture PDF gained board status. **Publicly
  listed 1,003.** Titles now drop file annotations like "(PDF, 124 KB)" /
  "[220KB]" (`FILE_ANNOTATION_RE`), which Kicker carried. Seed edits (OpenAI,
  Meta, Rockford rename) committed at the owner's say-so.

- **2026-11-08, cycle + OpenAI + Meta** — cycle: 717 companies, 368 ok, 1,720 s,
  4 page-load timeouts; deactivated 526, inserted 392. **Ramboll crossed the
  staleness bound** (SmartRecruiters timed out a third time) and its 17 board rows
  are hidden — narrowing its board is the fix. Microsoft and Qualcomm drew Eightfold
  429s again; company-only re-scrapes after the cycle were clean (8 and 52 board
  rows). Then added OpenAI (2 board rows) and walked Meta's pager (10 → 21 board
  rows), both owner-requested, with a Playwright guard so a 4xx on a later page
  fails the scrape instead of truncating it. **Board-eligible 1,026, publicly
  listed 999.** Seed edits for OpenAI and Meta are uncommitted until the owner says.

- **2026-11-05, cycle** — 717 companies (the six new ones included), 369 ok,
  1,962 s; 7 page-load timeouts; deactivated 1,247, inserted 630. The owner
  closed the laptop lid from ~13:09 to 13:42: macOS dark-woke for under a minute
  at a time, so the cycle crawled but did not fail en masse (failed scrapes never
  deactivate). Keep the lid open during a cycle. Microsoft and Qualcomm both drew
  Eightfold 429s in the cycle's first two minutes and left fallback rows;
  company-only re-scrapes right after the cycle were clean (Microsoft 9 board
  rows, Qualcomm 52). **Board-eligible 1,029, publicly listed 1,019 (from
  1,012).** Bose churned (15 in, 10 out). All six owner pins still listed; the
  new companies held (Syntiant 8, Holoplot 7, Muse 4, JAM 2). Sonnox/Novation's
  "lost 12" is the `updated_at` overcount trap — those rows were already inactive.

- **2026-11-04, owner's ten listings** — all ten publicly listed (board 1,012).
  Four scored on once their companies existed (Syntiant, BandLab already there,
  Holoplot, JAM/Ashly); six pinned in the DB (§1). Added six companies, repointed
  Splice. join.com and Personio title fix in `link_extraction.py`.

- **2026-11-04, iCIMS fix + cycle** — fixed the iCIMS short-page break (§5) and
  re-scraped Shure (126 found, 104 board rows). Cycle: healthy network (3
  page-load timeouts), 711 companies, 360 ok, 2,175 s (slower; part is iCIMS now
  paging and enriching fully); deactivated 1,007, inserted 891. **Board-eligible
  996, publicly listed 986 (from 895).** Microsoft drew an Eightfold 429 and
  left fallback duplicates again; a Microsoft-only re-scrape ~40 min later was
  clean (52 found, 9 board rows). Qualcomm succeeded (279; 52 board rows, window
  rotated: 14 out, 5 in). GN back (26 found, 9 board rows). Ramboll failed
  (SmartRecruiters timeout); HP timed out to fallback. Sonnox and Novation DJ
  (12 rows) were duplicates of Focusrite's shared Workable board and cleared;
  Focusrite keeps 15. Both dev servers had stopped (their terminal tabs were
  closed); restarted in new tabs.

- **2026-10-28, cycle** — healthy network (0 page-load timeouts): 711 companies,
  360 ok, 1,709 s; deactivated 715, inserted 611. Board-eligible 905, publicly
  listed 895. Shure's first iCIMS page still shows 19, so it again stopped at 19
  (still unfixed, §5). Microsoft's Eightfold succeeded and cleared its fallback
  duplicates (7 board rows, now including the Germany audio and speech intern); Qualcomm drew 429 a sixth time. Ramboll succeeded
  again (1,128). Rohde & Schwarz swapped (5 board rows out).

- **2026-10-26, cycle** — healthy network (0 page-load timeouts): 711 companies,
  365 ok, 1,608 s; deactivated 809, inserted 503. **Board-eligible 913, publicly
  listed 903 (from 980)**: Shure's iCIMS scrape stopped after a 19-row first page
  and deactivated 94 open board rows (§5, urgent). Ramboll succeeded (1,168) and
  its 17 rows are back. Microsoft and Qualcomm drew Eightfold 429 again
  (Microsoft 10 board rows for 7 jobs). Rohde & Schwarz swapped back to http.

- **2026-10-23, cycle** — servers relaunched first (nothing held 8000/5173; both
  had stopped; API started from a terminal, see §1). Healthy network (16
  page-load timeouts; the one connection error was GAC Group's dead SSL domain):
  711 companies, 365 ok, 1,939 s; deactivated 1,429, inserted 1,176 — mostly
  Analog Devices' first Workday success since 09-24 (522 out, 290 in), with
  McGill and Nissan also recovering. Board-eligible 1,007, publicly listed 980.
  Microsoft and Qualcomm both drew Eightfold 429 within a minute (§5) and fell
  back; Ramboll failed a fourth straight time and stays hidden.

- **2026-10-19, cycle** — healthy network (3 page-load timeouts): 711 companies,
  368 ok, 1,657 s; deactivated 344, inserted 191, reactivated 53. Board-eligible
  1,005, **publicly listed 978**: Ramboll's third straight failure hid its 17
  rows again. Microsoft and Qualcomm both scraped cleanly on Eightfold (no 429);
  Microsoft 47 jobs, 6 board rows. Treble Technologies' BambooHR board dropped to
  only "Open Application" — its 5 roles closed (4 board rows, verified live).
  Demant's SuccessFactors failed on a ConnectionError rather than its usual
  timeout. Claimed-ATS fallbacks otherwise as usual.

- **2026-10-17** — Microsoft repointed to its Eightfold board at the owner's
  request, to list "Research Intern - Audio and Acoustics"; measured first with a
  harness that sets the binding (`check_url` cannot), applied via `seed_file`'s
  writer after a byte-identical round-trip check, scraped with `--company`: 6
  board rows. Full cycle, healthy network (5 page-load timeouts): 711 companies,
  368 ok, 1,608 s; deactivated 815, inserted 371. Microsoft's Eightfold drew a 429
  during the cycle and its fallback put two malformed duplicates up; a second
  single-company scrape cleared them. Otter.ai (3) and XLN Audio (1) now hidden;
  Ramboll at 2. Board-eligible 1,016, publicly listed 1,006.

- **2026-10-15, cycle** — healthy network (9 page-load timeouts): 710 companies,
  366 ok, 1,656 s; deactivated 337, inserted 277, reactivated 95. Board-eligible
  1,004, publicly listed 998. IK Multimedia's 4 rows now hidden; Otter.ai (with a
  verified Greenhouse replacement) and XLN Audio (no openings) one failure from
  hidden (§5). Ramboll failed again (1, rows still listed). Rohde & Schwarz
  swapped back to Playwright (6 out, 3 in). Ten claimed-ATS fallbacks, the most
  yet: Logitech and HP timed out alongside the usual set, and Qualcomm got
  Eightfold 429 a third time.

- **2026-10-14, cycle** — healthy network (6 page-load timeouts): 710 companies,
  365 ok, 1,651 s; deactivated 887, inserted 722, reactivated 286. Board-eligible
  1,007, **publicly listed 1,005** (from 974): Ramboll succeeded (1,112 jobs) and
  its 17 rows are back. Churn sources: HP's rotating 200-row Eightfold window
  (192, §5), McGill clearing fallback rows (124), Rohde & Schwarz swapping back
  to http (79), Ramboll closures since 10-04 (67). Amplifon recovered; Calrec
  reached 3 (no board rows); IK Multimedia at 2 (4 board rows hide next
  failure); Otter.ai (3) and XLN Audio (1) took first failures on "no job links".
  Zoom's dead URL now times out. Qualcomm got Eightfold 429 again.

- **2026-10-12, cycle** — on a healthy network (3 page-load timeouts): 710
  companies, 367 ok, 1,598 s; deactivated 399, inserted 264, reactivated 141.
  Board-eligible 993, publicly listed 974. 18 of the 20 companies that took an
  unearned failure on 10-09 recovered; Calrec and Amplifon now load but show "no
  job links" (2 failures each, no board rows — worth a look, since the Calrec
  note below says it works and Amplifon matters for GN). Ramboll failed a fourth time and stays
  hidden; Valcom reached 3 (1 row hidden); IK Multimedia's careers URL now 404s
  (§5). Claimed-ATS fallbacks unchanged: Ramboll, Demant, Belden, Samsung,
  Analog Devices, McGill (timeouts); Amplitude, CD Baby (404).

- **2026-10-09, cycle — degraded network** — 710 companies, 350 ok, **2,740 s**
  (vs ~1,700); deactivated 341, inserted 314. 141 Playwright page-load timeouts
  (4 the day before), evenly spread: the machine's network (gateway 10.33.64.1)
  dropped all ICMP and could not connect to some hosts. 20 companies that
  succeeded on 10-08 failed, 18 on page-load timeouts — unearned, all at
  `consecutive_failures` 1, nothing hidden: Advanced Bionics (7 board rows),
  xMEMS 3, ESS 2, HEAD acoustics 2, SoundSense 2, SAE 1. **Ramboll reached 3
  and its 17 rows are hidden** (its usual SmartRecruiters timeout, though the
  slow network cannot have helped). Board-eligible 989, publicly listed 971.
  Run the next cycle on a good connection; two more like this would hide the
  companies above too.

- **2026-10-08, cycle** — 710 companies, 368 ok, 1,727 s; deactivated 376,
  inserted 357, reactivated 143. Board-eligible 994, publicly listed 993 —
  quiet, only small closures. Ramboll failed again (2 in a row). Meta failed on
  HTTP 503 (1; 5 board rows) and Valcom on an empty page (1; 1 board row). A
  one-second connection change at 14:54:49 shows as `net::ERR_NETWORK_CHANGED`;
  it cost nothing (Royal Enfield recovered on its stealth attempt, GungHo always
  fails) — grep for that string to spot a dropout's victims. Claimed-ATS
  fallbacks: Ramboll, Demant, Belden, Samsung, Analog Devices, McGill
  (timeouts); Amplitude, CD Baby (404). Rohde & Schwarz stayed on Playwright (no
  swap). GN still offline.

- **2026-10-07, cycle** — a first run was stopped at 293/710 because the owner's
  connection was unreliable (results kept; no network errors among its
  failures). The full cycle then ran: 710 companies, 372 ok, 1,815 s;
  deactivated 447, inserted 299, reactivated 175. Board-eligible 996, publicly
  listed 995. Rohde & Schwarz swapped 12 board rows for 3 (§5, new finding);
  HP's Eightfold recovered (3 → 200). Claimed-ATS fallbacks: Ramboll, Demant,
  Samsung, Analog Devices, McGill (timeouts); Amplitude, CD Baby (404). GN still
  offline. Run cycles on a stable connection: a dropout records unearned failures.

- **2026-10-05, cycle** — 710 companies, 366 ok, 1,607 s; deactivated 281,
  inserted 260, reactivated 46 — the quietest cycle in this run. Board-eligible
  1,000, publicly listed 999. Ramboll failed again (timeout, fallback empty);
  Qualcomm's malformed fallback rows, revived by 10-04's fallback, cleared again.
  Claimed-ATS fallbacks: Ramboll, Demant, Analog Devices, McGill, HP, Samsung
  (timeouts); Amplitude and CD Baby (404). GN still offline.

- **2026-10-04, cycle** — 710 companies, 369 ok, 1,533 s; deactivated 866,
  inserted 672, reactivated 97. Board-eligible 1,004, publicly listed 1,003 —
  steady. Arup cleared 11 superseded reposts; GN still offline. Claimed-ATS
  fallbacks: Demant, Qualcomm, Analog Devices, McGill, HP (timeouts); Amplitude
  and CD Baby (Greenhouse 404).

- **2026-10-01, cycle** — 710 companies, 369 ok, 1,609 s; deactivated 923,
  inserted 835, reactivated 88. Board-eligible 1,005, publicly listed 1,004 (from
  1,040): GN's careers site went offline (−31, §5), and 09-29's malformed fallback
  rows cleared as predicted (Shure's four "Job Title …", Qualcomm's five).
  Claimed-ATS fallbacks this time: Demant, Belden, Twilio Voice, iHeartRadio,
  Samsung, Analog Devices (timeouts); Sigma Connectivity (connection reset);
  Amplitude (404).

- **2026-09-29, cycle** — 710 companies, 367 ok, 1,862 s; deactivated 945,
  inserted 859, reactivated 150. Board-eligible 1,041, publicly listed 1,040
  (Fairphone hidden). Found: Zoom's board wiped by a navigation-only scrape, and
  claimed-ATS timeouts churning large boards and hiding Demant's staleness (§5).
  Amplitude's Greenhouse board 404s.
- **2026-09-25, cycle** — 710 companies, 366 ok, 1,872 s; deactivated 754 (Ramboll
  362 on its first success since 09-17, Samsung 133). Board-eligible 1,022,
  publicly listed 1,021; Ramboll's 16 rows listed again. Seven claimed ATS boards
  timed out and fell back (§5). The seed carries an uncommitted owner deletion of
  Sound Sleep; its DB row was already gone.

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
