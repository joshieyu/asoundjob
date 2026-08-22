# AGENTS.md - Build Instructions for ASoundJob

## Project Overview
ASoundJob is an audio industry job board + career resource site. It scrapes
audio companies' careers pages, aggregates job listings, and presents them
with filtering, search, and SEO-optimized detail pages. It also includes
a community job submission system (admin-approved), an audio company
directory, and an interview prep guide.

## Key Files
- `ARCHITECTURE.md` — full architecture plan, database schema, API design, build order
- `data/audio_companies_final.json` — 1,385 companies with careers URLs (source of truth)
- `data/schema.json` — JSON schema for the company data
- `data/README.md` — data workflow documentation
- `requirements.txt` — Python dependencies for data collection tooling

## Tech Stack
- **Scraper**: Python, Playwright, requests, BeautifulSoup, SQLAlchemy, RQ
- **API**: Python, FastAPI, SQLAlchemy, Pydantic
- **Frontend**: SvelteKit (TypeScript, Svelte 5)
- **Database**: PostgreSQL (prod), SQLite (dev)
- **Queue**: Redis + RQ
- **Hosting**: Hetzner VPS, nginx, Docker

## Site Sections
1. **Job Board** — scraped + community-submitted job listings with filters
2. **Community Job Submissions** — public form, admin approval queue
3. **Company Directory** — 1,385 audio companies, browseable by category
4. **Interview Prep Guide** — structured multi-article guide for audio eng interviews
5. **Career Resources** — resume, salary, career path, freelancing articles
6. **Admin Dashboard** — submission approval, scraper monitoring, company management

## Build Conventions

### General
- Use Python 3.11+ for scraper and API
- Use TypeScript everywhere in the frontend
- Keep scraper and API in separate packages but share database models
- Write tests for ATS parsers (they have predictable output)
- No comments in code unless explicitly requested

### Python (scraper + api)
- Use `pyproject.toml` for package config, NOT `setup.py`
- Use `ruff` for linting, `mypy` for type checking
- Use SQLAlchemy 2.0 style (typed declarative)
- Use Pydantic v2 for API schemas
- Use `asyncio` for API, `multiprocessing`/`concurrent.futures` for scraper workers

### Frontend (SvelteKit)
- Use Svelte 5 runes ($state, $derived, $effect)
- Use Tailwind CSS for styling
- Server-side render all job/company/resource pages for SEO
- Use `+page.server.ts` load functions to fetch from API
- API base URL from environment variable: `API_URL`
- Use impeccable skill design tokens (from `/impeccable shape` output)

### Database
- Use Alembic for migrations
- Snake_case for columns, PascalCase for models
- Always include `created_at` and `updated_at` timestamps
- Use `slug` fields for URL-friendly identifiers

## Build Order (follow strictly)

### Phase 1: Scraper — START HERE
1. Create `scraper/` directory with `pyproject.toml`
2. Install: `sqlalchemy[asyncio], aiosqlite, psycopg2-binary, rq, redis, requests, beautifulsoup4, playwright, alembic, pydantic, ruff, mypy`
3. Create `scraper/models.py` with SQLAlchemy models (see ARCHITECTURE.md for schema)
   - Companies, Jobs, JobSubmissions, ScrapeLog, CareerResources tables
4. Create `scraper/database.py` with engine + session factory
5. Create Alembic migration setup
6. Create `scraper/company_loader.py` — reads `data/audio_companies_final.json`, inserts into companies table
7. Create `scraper/scrapers/base.py` — abstract BaseScraper with interface:
   - `async def scrape(company) -> list[RawJob]`
   - Handles errors, timeouts, logging
8. Create `scraper/scrapers/ats/greenhouse.py` — fetches `boards-api.greenhouse.io/v1/boards/{slug}/jobs`
9. Create `scraper/scrapers/ats/lever.py` — fetches `api.lever.co/v0/postings/{slug}?mode=json`
10. Create `scraper/scrapers/http_scraper.py` — generic HTML parser using BeautifulSoup
11. Create `scraper/scrapers/playwright_scraper.py` — browser-based scraper
12. Create `scraper/normalizer.py` — standardize job fields
13. Create `scraper/deduplicator.py` — dedupe by (company_id, external_id)
14. Create `scraper/main.py` — orchestrates: load companies → enqueue → workers → normalize → dedupe → insert
15. Run: `python -m scraper.main --once` and verify jobs are scraped

### Phase 2: API
1. Create `api/` directory with `pyproject.toml`
2. Create `api/main.py` — FastAPI app with CORS, router includes
3. Create `api/database.py` — shared DB connection
4. Create `api/schemas.py` — Pydantic models for JobResponse, CompanyResponse, JobSubmissionRequest, etc.
5. Create `api/auth.py` — admin authentication (JWT or simple session)
6. Create `api/routers/jobs.py` — GET /api/jobs with filters + pagination, POST /api/jobs/submit
7. Create `api/routers/companies.py` — GET /api/companies, /api/companies/{slug}
8. Create `api/routers/categories.py` — GET /api/categories
9. Create `api/routers/search.py` — full-text search
10. Create `api/routers/resources.py` — GET /api/resources, /api/resources/{slug}
11. Create `api/routers/admin.py` — scrape control, submission approval, company management
12. Run: `uvicorn api.main:app --reload` and test endpoints

### Phase 3: Frontend (use impeccable skill — see ARCHITECTURE.md for full workflow)
1. `npm create svelte@latest web` (SvelteKit, TypeScript)
2. Install Tailwind CSS
3. Run `/impeccable init` to capture product vision
4. Run `/impeccable shape` to design visual system
5. Create `src/lib/api.ts` — API client functions
6. Build pages in order: homepage → jobs list → job detail → submit form → companies → company detail → interview prep → resources → admin → about
7. Add SEO: meta tags, JSON-LD, sitemap.xml, robots.txt
8. Run `/impeccable audit` for quality check
9. Run `/impeccable polish` for final pass
10. Build + preview: `npm run build && npm run preview`

### Phase 4: Deploy
1. Write `Dockerfile` (multi-stage: build frontend, install Python deps, run everything)
2. Write `docker-compose.yml` (postgres, redis, app)
3. Write `nginx.conf` (reverse proxy: / → SvelteKit, /api → FastAPI)
4. Deploy to Hetzner VPS

## ATS API Reference

### Greenhouse
```
GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
Returns: { jobs: [{ id, title, location, absolute_url, updated_at, ... }] }
```

### Lever
```
GET https://api.lever.co/v0/postings/{slug}?mode=json
Returns: [{ id, text, descriptionPlain, location, commitment, url, ... }]
```

### Workable
```
GET https://apply.workable.com/api/v3/accounts/{slug}/jobs
Returns: { jobs: [{ id, title, location, full_description, url, ... }] }
```

### Ashby
```
GET https://api.ashbyhq.com/posting-api/job-board/{slug}
Returns: { jobs: [{ id, title, locationName, descriptionHtml, url, ... }] }
```

### SmartRecruiters
```
GET https://api.smartrecruiters.com/v1/companies/{slug}/jobs
Returns: { content: [{ id, name, location, jobAd, ... }] }
```

### Recruitee
```
GET https://{slug}.recruitee.com/api/offers
Returns: { offers: [{ id, title, description, location, url, ... }] }
```

## Important Notes

- The company JSON is the seed data. Do NOT modify it from the scraper.
  The scraper reads it once (via company_loader.py) and then works from the DB.
- Manual additions/fixes to the JSON should be done via `scripts/add_company.py`
  or `scripts/validate_companies.py`, then re-run company_loader.
- The `source: "manual"` flag in the JSON means the entry was hand-verified.
  Never overwrite or re-verify these from automated scripts.
- Playwright workers are expensive (~200MB RAM each). Limit to 5-10 concurrent.
  HTTP workers are cheap. Limit to 50 concurrent.
- ATS JSON APIs are the fast path — no browser needed, just HTTP GET.
  Always try ATS API first before falling back to HTML/Playwright scraping.

## Job Deactivation (critical to get right)

The scraper re-visits every verified company's careers page nightly. When it
fetches a page successfully and a previously-active job is no longer listed,
it deactivates that job (sets `is_active=false`).

**CRITICAL**: If the scraper FAILS to fetch a page (403, timeout, network error),
it must NOT deactivate any jobs for that company. We can only deactivate jobs
when we've confirmed the page loaded and the job is genuinely gone.

Community-submitted jobs (`source='community'`) are never re-scraped.
They auto-expire after 30 days (via `expires_date`) or are manually
deactivated by the admin.

See ARCHITECTURE.md "Job Lifecycle & Deactivation" section for the full
flow diagram and pseudocode.

## Community Job Submissions

The flow for community-sourced jobs:
1. Public user fills form at `/jobs/submit` (no login required)
2. API creates `job_submissions` row with `status='pending'`
3. Admin sees submission in `/admin/submissions` queue
4. Admin approves → job inserted into `jobs` table with `source='community'`
5. Admin rejects → submission marked `rejected` with reason
6. Approved jobs appear on the main job board alongside scraped jobs

Key implementation details:
- Rate limit by IP (e.g. 3 submissions per IP per day) to prevent spam
- Submitter email is stored but never displayed publicly
- If submitted company name matches an existing company in the directory,
  auto-link the `company_id` field
- Approved community jobs should be visually distinguished from scraped jobs
  (e.g. "Community submitted" badge) to maintain trust

## Interview Prep Guide Content

Seed the `career_resources` table with initial interview prep articles.
Suggested initial articles (category='interview-prep'):
1. "Common Audio Engineering Interview Questions" — general overview
2. "DSP Concepts You Should Know" — filters, FFT, convolution, sample rates
3. "Acoustics Fundamentals for Interviews" — wave propagation, room modes, decibels
4. "Live Sound Practical Assessments" — what to expect in hands-on tests
5. "Coding for Audio Software Roles" — C++, JUCE, plugin development questions
6. "Portfolio Preparation Tips" — what to bring, how to present work
7. "Salary Negotiation for Audio Engineers" — market rates, negotiation strategies
8. "What Major Companies Look For" — Apple, Bose, Harman, Sony, etc.

Each article is Markdown in the `body` field. The cheaper model can
generate initial draft content for these articles.
