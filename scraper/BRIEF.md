# SCRAPER IMPROVEMENT BRIEF — execute top to bottom

<!-- Self-contained working brief. Written 2026-08-26 after Phase 1-3 post-mortem.
     Update the STATUS boxes as work completes. Commit after each phase. -->

## STATUS

- [ ] Phase A: JSON ATS parsers (Workable, Ashby, SmartRecruiters, Recruitee, BambooHR)
- [ ] Phase B: ATS discovery (detect embeds in HTML, persist ats_type/ats_slug, route first)
- [ ] Phase C: Workday API handler (18 companies incl. Samsung/Sonos/Jabra/Logitech)
- [ ] Phase D: JSON-LD JobPosting extraction on generic pages
- [ ] Phase E: ADP / Pinpoint / Apple handlers (research-heavy)
- [ ] Phase F: Dead-domain cleanup + unverified-coverage pass (writes via JSON, not DB)
- [ ] Phase G: Re-backfill relevance/categories, measure acceptance targets, final report

## WHY (post-mortem numbers, 2026-08-26)

Funnel: 1,385 companies → 742 verified/attempted → 476 scraped OK → **344 contribute jobs**.
266 hard failures + 132 JS-SPA "successes" with zero extraction (Apple among them:
`apple.com/careers` is a JS shell). 149 companies contribute only 1–2 jobs.
Only ~55 jobs carry audio categories because generic scrapers extract **titles + URLs
only — no descriptions** — so the keyword classifier starves. Salaries/locations mostly
missing for the same reason. Relevance gating (see below) hides 1,094 conglomerate
corporate roles; board shows 1,953.

## WHERE THINGS LIVE

- Repo root: `/Users/joshuayu/Documents/Coding/audiojobs`. DB: `asoundjob.db` (SQLite, gitignored).
- Activate venv FIRST: `source ../venv/bin/activate` from `scraper/` (Python 3.9.6 — write
  3.9-compatible code, `from __future__ import annotations`, `Optional[X]` in FastAPI deps).
- Scraper package: `scraper/scraper/` — `models.py` (Company/Job/JobSubmission/ScrapeLog/
  CareerResource), `database.py` (session_scope; sqlite URL resolved against REPO_ROOT),
  `config.py` (Settings: http_concurrency 50, playwright_concurrency 5, timeouts),
  `company_loader.py` (JSON→DB upsert; manual-source protection), `normalizer.py`
  (seniority, categories via CATEGORY_KEYWORDS/CATEGORY_PATTERNS, salary parse,
  `score_relevance()` + `category_to_scope()`), `deduplicator.py` (identity
  `ext:{external_id}` else `url:{normalized}`; deactivation only when
  `trust_empty or len(fetched)>0`; never touches non-scraper sources),
  `scrapers/` (`base.py` RawJob/ScrapeResult/BaseScraper — `scrape()` returns
  ScrapeResult{success, jobs, method, trust_empty}; `fetch.py` thread-local requests
  session + fetch_json/fetch_html/parse_date; `pipeline.py` ScrapePipeline fallback
  chain: ATS match → http (unless scrape_method=playwright) → playwright → stealth,
  semaphores per class; `link_extraction.py` anchor heuristics; `playwright_scraper.py`
  shared browser, stealth init script; `ats/greenhouse.py`, `ats/lever.py` — copy their
  shape: URL_PATTERN, can_handle, extract_slug, fetch via asyncio.to_thread, parse fn),
  `main.py` (orchestrator; `persist_result` re-fetches Company row and normalizes with
  `managed.audio_scope`; `--once --limit N --company slug --skip-load --verbose`),
  `backfill_relevance.py` (syncs company scopes from category + re-scores jobs).
- Migrations: `scraper/migrations/` (alembic; run `alembic upgrade head` from `scraper/`;
  SQLite needs server_default on NOT NULL adds; ruff excludes migrations dir).
- Tests: `scraper/tests/` — unittest (NOT pytest), fixtures inline, live-API smoke via
  `python -c` one-offs. `python -m unittest discover -s tests`.
- Lint/type: `ruff check .` + `mypy scraper` from `scraper/` (both must pass; line ≤100).
- API: `api/api/` FastAPI — `query.py apply_job_filters` already filters
  `is_audio_related` by default (`include_unrelated` param), `routers/jobs.py`,
  `companies.py` (company pages filter related), `admin.py` (audio_scope PUT re-scores).
- Frontend: `web/` SvelteKit — `/jobs` has the "Include non-audio roles" checkbox.
- Demo: API `cd api && ../venv/bin/uvicorn api.main:app --port 8000`; web
  `cd web && npm run preview -- --port 4173` (build first) with API_URL default 8000.
- AGENTS.md + ARCHITECTURE.md document conventions + relevance gating. Keep them truthful.

## INVARIANTS (do not regress)

1. Deactivation safety: jobs deactivate ONLY on confirmed fetch success; ATS JSON sets
   `trust_empty=True`; generic scrapers never do. A failed fetch must leave jobs active.
2. `data/audio_companies_final.json` is seed truth — never modify from the scraper.
   Manual entries (`source='manual'`) are never overwritten by the loader.
3. Playwright concurrency ≤5, HTTP ≤50 (Settings). One browser, shared, closed at end.
4. Community submissions are never re-scraped; dedup prefers scraped over community.
5. No code comments (unless asked). pyproject.toml config. Commit per phase, push per group.
6. Shared careers pages: several companies share one board (Focusrite/Ampify/Sonnox/
   Novation → workable/focusrite; Logitech/Ultimate Ears/Blue → logitech workday;
   inMusic's 9 labels → one pinpoint board). Cache/dedupe fetches per URL.

## PHASE A — JSON ATS parsers (mechanical, do first)

Copy the greenhouse.py/lever.py pattern into `scrapers/ats/`. Each: URL_PATTERN regex on
careers_url, `can_handle`, `extract_slug`, async fetch_json, `parse_*` pure function +
unittest with inline fixture. Add to pipeline's ATS list. Verify each live against the
named company before marking done.

- **Workable** (10 companies): slug from `apply.workable.com/{slug}` or `{slug}.workable.com`.
  Try GET `https://apply.workable.com/api/v2/accounts/{slug}/jobs?details=true`; if 404/empty
  try POST v3 `https://apply.workable.com/api/v3/accounts/{slug}/jobs` json body
  `{"page":1,"department":null,"location":null}`. Verify: focusrite, dunlop, huggingface, mixcloud-limited.
- **Ashby** (4): GET `https://api.ashbyhq.com/posting-api/job-board/{slug}` → `{jobs:[{id,title,location,descriptionHtml,...}]}` (also `jobBoard` key variant). Verify: suno, deepgram, epidemic-sound, modulate.
- **SmartRecruiters** (1): GET `https://api.smartrecruiters.com/v1/companies/{slug}/jobs` → `{content:[{id,name,location:{city,country},releasedDate,jobAd:{shortDescription},...}]}`. Verify: DONTNOD. Paginate `?limit=100&offset=`.
- **Recruitee** (0 in data but documented): GET `https://{slug}.recruitee.com/api/offers` → `{offers:[...]}`.
- **BambooHR** (4): GET `https://{sub}.bamboohr.com/careers/list` → `{result:{jobs:[{id,jobOpeningName,location:{city,state},...}]}}` (verify shape live: softube, cambridgeaudio, symphonicdist, moises).
- **Breezy** (1): research `flowkey.breezy.hr` — page embeds positions JSON or `/json` endpoint.

Map fields → RawJob(title, url, external_id, location, description, posted_date, job_type
from commitment/employment type). HTML descriptions pass through unchanged (normalizer
classifies from them). ATS results set `trust_empty=True` (already automatic for
`ats.*` names via pipeline — keep it that way).

## PHASE B — ATS discovery (unlocks companies whose careers_url hides the ATS)

1. Migration: `companies.ats_type TEXT NULL`, `companies.ats_slug TEXT NULL`
   (autogenerate + server_default NULL is fine). Loader must NOT touch these columns.
2. New module `scrapers/ats_discovery.py`: `discover(html, base_url) -> list[(ats_type, slug)]`
   — regex/link scan for: `boards.greenhouse.io/embed/job_board?for={slug}`,
   `job-boards.greenhouse.io/{slug}`, `jobs.lever.co/{slug}`, `apply.workable.com/{slug}`,
   `jobs.ashbyhq.com/{slug}`, `careers.smartrecruiters.com/{slug}`, `{slug}.recruitee.com`,
   `myworkdayjobs.com/{tenant}/{site}`, `{sub}.bamboohr.com`, `{sub}.breezy.hr`,
   `{sub}.pinpointhq.com`, `myjobs.adp.com/{cx}/`, `jobs.apple.com`. Unit-test with HTML
   snippets. Skip if company already has ats_type (first discovery wins; admin can clear).
3. Pipeline: check `company.ats_type/ats_slug` FIRST (route to parser with explicit slug,
   overriding URL pattern); after any successful HTML fetch (http or playwright), run
   discovery and persist findings (even when job extraction found nothing — that's how
   Apple-class zero-job pages become useful next cycle).
4. Note: greenhouse/lever URL-pattern matchers stay; discovered slugs take precedence.

## PHASE C — Workday (18 companies, biggest single win)

Known-good community API: POST `https://{tenant}.wd{n}.myworkdayjobs.com/wday/cxs/
{tenant}/{site}/jobs` body `{"appliedFacets":{},"limit":20,"offset":0,"searchText":""}`
→ `{total, jobPostings:[{title, externalPath, locationsText, postedOn, bulletFields}]}`.
Detail: GET `.../wday/cxs/{tenant}/{site}{externalPath}` → `{jobPostingInfo:{jobDescription,
startDate, ...}}`. Parse tenant/site from `*.wd{n}.myworkdayjobs.com/{site}` URLs
(Samsung: sec.wd3/Samsung_Careers; Sonos: sonos.wd1/Sonos; Logitech: logitech.wd5/Logitech —
note Ultimate Ears + Blue Microphones share it). Paginate offset until total. Fetch
descriptions from detail endpoint (rate-limit: these are 2 requests per job — consider
description fetch only when title has any audio signal OR company is native-scope, to cap
request volume; cache by externalPath). Handle `postedOn` relative strings ("Posted Today",
"Posted 3 Days Ago") → parse_date best effort. Verify: sonos, samsung, jabra.

## PHASE D — JSON-LD extraction on generic pages

In `link_extraction.py` (or new module), also parse `<script type="application/ld+json">`
blocks; for objects with `@type: JobPosting` emit RawJob(title, url=page URL or `url` prop,
description (html ok), location (address.addressLocality/region or jobLocation string),
posted_date=datePosted, external_id=identifier/uid when present). Merge with anchor
results by URL identity (JSON-LD wins — richer). Unit tests with fixture HTML. This alone
should lift categories/salaries on the 149 thin companies.

## PHASE E — ADP / Pinpoint / Apple (research-heavy; timebox)

- **ADP Workforce Now** (8: Meyer Sound, Casio, Harley-Davidson, IAC Acoustics, Knowles,
  Switchcraft, LiveWire, Triumph): the `recruitment.html` page XHRs a JSON endpoint under
  `/mascsr/default/career-center/public/...` — inspect network tab once via Playwright
  request interception and replicate; cid/ccId come from the careers_url querystring.
  `myjobs.adp.com/{cx}/cx` similar.
- **Pinpoint** (9 inMusic labels share one board): inspect `inmusicbrands.pinpointhq.com`
  — likely `__NEXT_DATA__`/JSON API (`/api/jobs` or sitemap). One board fetch covers all 9.
- **Apple**: `jobs.apple.com` search API (POST `/api/role/search` with pagination payload —
  verify). Careers URL in DB is the marketing page; hardcode route to the jobs API for
  company slug 'apple'. Also consider Teamtailor (`aes.careerwebsite.com` is YourMembership
  — research or skip).
- Timebox each; if an API can't be found in ~1h, leave for Playwright-with-scroll later.

## PHASE F — coverage pass

- Dead domains (hugedomains.com etc.): set verified=false **in the JSON** via
  `scripts/add_company.py --update` (JSON is truth; DB flips get overwritten by loader).
- 643 unverified companies: run a verification pass (scripts/verify_phase1.py exists) and
  merge results into JSON the same way; then normal scrape covers them.
- iCIMS entries (Rivian/SiriusXM/Keysight) have auth-wall URLs in seed — find real board
  URLs (`{co}.icims.com/jobs`) and update JSON.

## PHASE G — re-score + measure

1. `python -m scraper.main --once` full cycle (expect new ATS jobs with descriptions).
2. `python -m scraper.backfill_relevance`.
3. Acceptance targets: contributing companies 344 → **≥450**; jobs with audio category
   55 → **≥300**; jobs with description ≥1,500; total active jobs grows, noise ratio
   (hidden/total) stays ~1/3. All tests green, ruff+mypy clean, demo re-verified.
4. Report per-phase numbers in this file's STATUS section.

## QUICK SELF-CHECK COMMANDS

```
cd scraper && source ../venv/bin/activate
python -m unittest discover -s tests && ruff check . && mypy scraper
alembic upgrade head
python -m scraper.main --once --limit 5 --verbose      # smoke
python -m scraper.backfill_relevance --dry-run
cd ../api && ../venv/bin/uvicorn api.main:app --port 8000   # then curl /api/jobs?per_page=1
```
