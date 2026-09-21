# ASoundJob

An audio industry job board for Young Audio Professionals (YAP).
A scraper visits the careers pages of ~1,400 audio companies, a relevance model
decides which of the jobs it finds belong in front of an audio engineer, and a
SvelteKit site serves what survives.

As of 2026-09-18: **1,413 companies, 19,271 job rows, 1,260 on the public board.**

The audience is audio engineers. DSP, audio systems, EE, embedded and acoustics
roles are the priority, and most of the judgement calls in the relevance code
resolve toward that.

## Running it locally

Two processes, two terminal tabs.

```bash
cd api && ../venv/bin/uvicorn api.main:app --port 8000 --reload
```

```bash
cd web && npm run dev -- --port 5173
```

Then open http://localhost:5173. The admin panel is at `/admin`, and the dev
credentials are `admin` / `asoundjob-dev` unless `ADMIN_USERNAME` and
`ADMIN_PASSWORD` say otherwise.

**Keep `--reload` on the API.** Without it, uvicorn serves stale Python for the
whole session while the web dev server hot-reloads. The two drift apart and a
schema change shows up as a 422 that looks like a bug in whatever you just
wrote.

**Stop them with Ctrl-C, or by PID from `lsof -ti :8000`.** Never
`pkill -f uvicorn` — if your own throwaway server failed to bind and exited, the
pattern matches only the real one, and you will spend a while wondering why the
demo shows zero roles.

## The gates

Everything must pass before a commit.

```bash
cd scraper && source ../venv/bin/activate && python -m unittest discover -s tests && ruff check . && mypy scraper
```

```bash
cd api && source ../venv/bin/activate && python -m unittest discover -s tests && ruff check . && mypy api
```

```bash
npm --prefix web run check
```

The API tests deliberately do **not** use `fastapi.testclient` — there is no
httpx dependency. They call router functions directly against an in-memory
SQLite database.

## How data moves

```
data/audio_companies_final.json   the seed: company names, careers URLs, flags
        │  company_loader (runs at the start of every scrape cycle)
        ▼
    companies table  ──scrape──▶  jobs table  ──▶  API  ──▶  web
        ▲
        │  api/api/seed_file.py
   admin panel edits
```

**The seed is truth.** The loader reads it at the start of every cycle and
reconciles the companies table against it. A company deleted from the database
but left in the seed comes straight back on the next run.

**Key presence matters in the seed.** For `description`, `headquarters`,
`founded`, `community_links`, `ats_type`, `ats_slug`, `website_url` and
`logo_url`: an absent key leaves the database value alone, a present key wins,
and an explicit `null` clears it.

**The admin panel writes the seed.** Since 2026-09-17, creating, editing or
deleting a company in `/admin/companies` updates `audio_companies_final.json`
through `api/api/seed_file.py`, so the panel is authoritative with no CLI step.
The scraper still never writes the seed. The sync is off until the served app
calls `seed_file.enable()` in its lifespan, which is what keeps test fixtures
out of the real file.

**Editing a company in the panel flips its `source` to `manual`**, which is what
protects it from being overwritten by the loader. That protection holds only
while the *seed* also says `manual`.

## Running the scraper

```bash
cd scraper && source ../venv/bin/activate && python -m scraper.main --once
```

A full cycle takes about 26 minutes and scrapes the verified, unblocked
companies that have a careers URL — currently 711 of 1,413.

| flag | effect |
| --- | --- |
| `--once` | a single cycle (the default) |
| `--limit N` | scrape at most N companies |
| `--company <slug>` | one company, **and this bypasses `scrape_blocked`** so you can test whether a block can be lifted |
| `--skip-load` | skip the seed sync at the start |
| `--verbose` | debug logging |

The summary line at the end reads:

```
companies=711 ok=364 failed=347 blocked_skipped=13 jobs_found=8368 | db: inserted=585
updated=7783 reactivated=35 deactivated=306 deactivation_skips=7 expired=0 | via ...
```

A failure rate near 50% is normal and always has been. Many seeded companies
publish nothing a parser can read.

Concurrency is bounded: Playwright at 5, HTTP at 50, and per-job enrichment is
always time-limited. Raise those with `PLAYWRIGHT_CONCURRENCY` and
`HTTP_CONCURRENCY` only if you mean it.

## Diagnostics, all read-only

None of these touch the database or the seed. Most write a markdown report and
take `--output`; `check_url` and `check_links` print to stdout and take `--json`
instead. Run any of them with `--help` for the rest. From `scraper/` with the
venv active:

| command | what it answers |
| --- | --- |
| `python -m scraper.check_url <url> --name <company>` | what would this careers URL yield if I seeded it? Shows board rows first. |
| `python -m scraper.detect_landing_pages` | whose `careers_url` points at a page *about* careers instead of the job board? |
| `python -m scraper.detect_nonjob_rows` | whose stored rows are navigation chrome rather than jobs? |
| `python -m scraper.detect_truncation` | who hit their parser's page cap and is only showing you page one? |
| `python -m scraper.diagnose_failures` | why did these scrapes come back empty? |
| `python -m scraper.audit_seed_urls` | which seeded URLs are error pages, parked domains or the wrong company, judged from the URL alone — the same judgement also shows per company on the admin health page |
| `python -m scraper.check_links` | which published job URLs are dead? |
| `python -m scraper.export_seed_edits` | what would the seed look like if it caught up with admin edits? |
| `python -m scraper.propose_ats_bindings` | which stored `ats_type`/`ats_slug` bindings are wrong? `--verify` actually runs them. |
| `python -m scraper.propose_companies` | which companies show up in jobspy results that we do not have? |
| `python -m scraper.propose_demotions` | which verified companies are no longer earning their place? |
| `python -m scraper.propose_open_applications` | who invites speculative applications? |

`check_url` is the one to reach for first. It runs the real pipeline against a
URL without persisting anything, and its sample shows board rows before skipped
ones, so `2 / 143` is backed by the two rows it means.

## Tools that write

| command | effect |
| --- | --- |
| `python -m scraper.backfill_relevance` | rescores existing job rows in place. `--dry-run` first. Use it after a relevance change instead of waiting for every company to be rescraped. |
| `python -m scraper.prune_orphans` | deletes companies that have fallen out of the seed, with their jobs and logs. Dry run by default; `--apply` to commit. `--file <path>` points it at a different seed, which makes it a general "delete these companies" tool. |

## Configuration

Everything has a working default; none of this is needed for local development.

**Scraper** — `DATABASE_URL` (defaults to `sqlite:///asoundjob.db`), `DATA_DIR`,
`SCRAPER_USER_AGENT`, `HTTP_CONCURRENCY` (50), `PLAYWRIGHT_CONCURRENCY` (5),
`REQUEST_TIMEOUT` (15s), `PAGE_LOAD_TIMEOUT` (25s), `PER_COMPANY_TIMEOUT` (90s).

**API** — `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_SECRET_KEY`,
`TOKEN_EXPIRE_MINUTES` (720), `CORS_ORIGINS`, `SUBMISSIONS_PER_IP_PER_DAY` (3),
`COMMUNITY_JOB_TTL_DAYS` (30).

In production the API process needs **write access to `data/`**, because that is
where admin edits land. This is a newer requirement than the rest of the deploy.

**Web** — `PUBLIC_API_URL` and `API_URL` both default to `http://127.0.0.1:8000`
(browser-side and server-side respectively), `SITE_URL` defaults to
`http://localhost:5173`.

## Repository layout

| path | |
| --- | --- |
| `scraper/` | the scraper package, its ATS parsers under `scrapers/ats/`, the relevance model in `normalizer.py`, and every diagnostic above |
| `api/` | FastAPI: public job and company endpoints, the admin panel's backend, and `seed_file.py` |
| `web/` | SvelteKit front end, Svelte 5 runes, Tailwind. Admin lives under `src/routes/admin/` |
| `data/` | the seed, the job category vocabulary, the JSON schema. See `data/README.md` |
| `tools/jobspy_fetch/` | a standalone LinkedIn/Indeed fetcher with its **own** venv, because `python-jobspy` needs Python ≥3.10 and pulls in numpy, neither of which may enter the scraper's 3.9 dependency tree. Built but never run — it needs residential proxies and refuses to start without them. |
| `scripts/` | one-off migration and crawl scripts from the initial build. Historical; not part of any current workflow |
| `HANDOFF.md` | the running engineering log. Long, chronological, and the place to look before assuming anything below is still true |
| `ARCHITECTURE.md`, `PRODUCT.md`, `DESIGN.md` | the plan, the product, the visual system |

## Things that will bite you

**`data/audio_companies_final.json` is hand-maintained and often has uncommitted
work in it.** Never run `git checkout`, `restore`, `stash`, `reset` or `clean`
against it, and never stage it with `git add -A` — stage it by name. It must
round-trip byte-identically through
`json.dumps(data, indent=2, ensure_ascii=False) + "\n"` and stay sorted by name,
case-insensitively. The canonical key order is `SEED_KEY_ORDER` in
`company_loader.py`; both writers go through `order_seed_entry()`.

**Nothing in the pipeline ever deletes a job row.** Rows are deactivated, never
removed. `deactivate_expired_jobs` only touches rows carrying an `expires_date`,
and almost none do. If you want rows gone, that is `prune_orphans`.

**A failed scrape preserves that company's existing rows.** Deactivation is
suppressed on failure and on partial multi-URL scrapes, so a company can sit on
stale rows indefinitely while its scrapes fail. This is deliberate — the
alternative is wiping a real board over one bad afternoon — but it means "the
fix didn't apply" is often really "that company failed".

**`updated_at` is not a freshness signal.** SQLAlchemy emits no UPDATE when a
re-found row's values are unchanged, so a row that is refound identically every
cycle keeps an old timestamp and looks stale. Measuring "what did the last cycle
actually produce" needs the scrape log, not the row.

**Recall beats precision on job relevance, and country parsing deliberately
inverts that** — an ambiguous location resolves to NULL rather than a guess.

**Every regex quantifier is bounded.** No bare `+` or `*` anywhere in the
matching code. Match the surrounding style.

**No code comments.** The codebase has none. Commit messages and `HANDOFF.md`
carry the reasoning instead.
