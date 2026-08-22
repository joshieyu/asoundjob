# ASoundJob - Project Architecture Plan

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Scraper | Python + Playwright + requests | Already installed, data exists |
| API | Python FastAPI | Same language as scraper, async, lightweight, auto-docs |
| Frontend | SvelteKit | Supported by impeccable skill, SSR for SEO, smallest JS bundle |
| Database | PostgreSQL (prod) / SQLite (dev) | Relational, good for job listings + company directory |
| Task Queue | Redis + RQ (Redis Queue) | Python-native, simple, runs scraper on schedule |
| Web Server | nginx reverse proxy | Serves SvelteKit SSR + proxies API |
| Hosting | Hetzner CX22 (~$5/mo) | 4GB RAM, enough for everything |

## Project Structure

```
audiojobs/
├── data/                          # Existing company directory
│   ├── audio_companies_final.json
│   ├── schema.json
│   └── README.md
├── scraper/                       # Python scraper package
│   ├── pyproject.toml
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── main.py                # Entry point: orchestrates scrape cycle
│   │   ├── config.py              # Settings (DB URL, concurrency, timeouts)
│   │   ├── models.py              # SQLAlchemy models (Job, Company, ScrapeLog, JobSubmission)
│   │   ├── database.py            # DB connection + session management
│   │   ├── company_loader.py      # Loads audio_companies_final.json into DB
│   │   ├── scrapers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # BaseScraper abstract class
│   │   │   ├── http_scraper.py     # requests + BeautifulSoup scraper
│   │   │   ├── playwright_scraper.py # Playwright scraper for JS sites
│   │   │   ├── ats/               # ATS-specific parsers (structured job extraction)
│   │   │   │   ├── greenhouse.py
│   │   │   │   ├── lever.py
│   │   │   │   ├── workday.py
│   │   │   │   ├── workable.py
│   │   │   │   ├── ashby.py
│   │   │   │   ├── smartrecruiters.py
│   │   │   │   ├── icims.py
│   │   │   │   ├── recruitee.py
│   │   │   │   └── generic.py     # Fallback: parse any careers page
│   │   │   └── job_boards/        # External job board scrapers
│   │   │       ├── linkedin.py
│   │   │       ├── indeed.py
│   │   │       └── glassdoor.py
│   │   ├── normalizer.py          # Normalize job data (title, location, etc.)
│   │   ├── deduplicator.py        # Dedupe jobs across sources
│   │   └── scheduler.py           # RQ job scheduling
│   └── tests/
├── api/                           # FastAPI backend
│   ├── pyproject.toml
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app
│   │   ├── config.py
│   │   ├── database.py            # Shared DB connection
│   │   ├── models.py              # Shared SQLAlchemy models
│   │   ├── schemas.py             # Pydantic response/request schemas
│   │   ├── auth.py                # Admin authentication (JWT or session)
│   │   └── routers/
│   │       ├── jobs.py            # GET /api/jobs, /api/jobs/{id}, POST /api/jobs/submit
│   │       ├── companies.py       # GET /api/companies, /api/companies/{slug}
│   │       ├── categories.py      # GET /api/categories
│   │       ├── search.py          # GET /api/search?q=...
│   │       ├── resources.py       # GET /api/resources, /api/resources/{slug}
│   │       └── admin.py           # Scrape control + job submission approval + company management
│   └── tests/
├── web/                           # SvelteKit frontend
│   ├── package.json
│   ├── svelte.config.js
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +layout.svelte      # Global layout (nav, footer)
│   │   │   ├── +page.svelte        # Homepage
│   │   │   ├── jobs/
│   │   │   │   ├── +page.svelte        # Job listings (filters + pagination)
│   │   │   │   ├── [id]/+page.svelte    # Job detail page (SEO critical)
│   │   │   │   └── submit/+page.svelte  # Community job submission form
│   │   │   ├── companies/
│   │   │   │   ├── +page.svelte        # Company directory (browse by category)
│   │   │   │   └── [slug]/+page.svelte # Company profile + their open jobs
│   │   │   ├── resources/
│   │   │   │   ├── +page.svelte        # Career resources hub
│   │   │   │   ├── interview-prep/
│   │   │   │   │   ├── +page.svelte        # Interview prep guide landing
│   │   │   │   │   └── [slug]/+page.svelte  # Individual prep article
│   │   │   │   └── [slug]/+page.svelte    # Other resource articles
│   │   │   ├── admin/
│   │   │   │   ├── +layout.svelte           # Admin layout (auth guard)
│   │   │   │   ├── +page.svelte             # Admin dashboard
│   │   │   │   ├── submissions/
│   │   │   │   │   └── +page.svelte          # Job submission approval queue
│   │   │   │   ├── companies/
│   │   │   │   │   └── +page.svelte          # Company management
│   │   │   │   └── scraper/
│   │   │   │       └── +page.svelte          # Scraper monitoring + trigger
│   │   │   └── about/+page.svelte      # About page
│   │   ├── lib/
│   │   │   ├── api.ts              # API client functions
│   │   │   ├── components/         # Reusable UI components
│   │   │   └── stores/            # Svelte stores (filters, search, auth)
│   │   └── app.css                # Global styles + design tokens
│   └── static/
│       ├── robots.txt
│       └── sitemap.xml             # Generated at build time
├── docker-compose.yml             # PostgreSQL + Redis for dev
├── Dockerfile                     # Production container
└── AGENTS.md                      # Build instructions for AI agents
```

## Database Schema

### companies table
```sql
CREATE TABLE companies (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,       -- URL-friendly name
    category    TEXT NOT NULL,
    careers_url TEXT,
    website_url TEXT,                      -- Optional: main company website
    verified    BOOLEAN DEFAULT FALSE,
    source      TEXT DEFAULT 'auto',       -- 'manual' or 'auto'
    scrape_method TEXT DEFAULT 'http',     -- 'http' or 'playwright'
    logo_url    TEXT,                      -- Optional
    description TEXT,                      -- Optional
    headquarters TEXT,                     -- Optional: e.g. "San Francisco, CA"
    founded     INTEGER,                    -- Optional: founding year
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### jobs table
```sql
CREATE TABLE jobs (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES companies(id),
    title         TEXT NOT NULL,
    description   TEXT,                    -- Full job description (HTML or text)
    url           TEXT NOT NULL,           -- Direct link to apply
    location      TEXT,                   -- e.g. "San Francisco, CA" or "Remote"
    remote        BOOLEAN DEFAULT FALSE,
    job_type      TEXT,                   -- 'full-time', 'part-time', 'contract', 'internship'
    salary_min    INTEGER,                -- Optional
    salary_max    INTEGER,
    salary_currency TEXT,                 -- e.g. 'USD', 'EUR'
    experience_level TEXT,                -- e.g. 'entry', 'mid', 'senior', 'lead'
    audio_domain  TEXT,                   -- e.g. 'DSP', 'Acoustics', 'Live Sound'
    posted_date   DATE,
    scraped_date  TIMESTAMPTZ DEFAULT NOW(),
    expires_date  DATE,                   -- For community jobs: set to now()+30d on insert.
                                           -- For scraped jobs: NULL (deactivation is driven by
                                           --   the scraper detecting the job is gone, not by date).
                                           -- For job board jobs: set to now()+14d.
    is_active     BOOLEAN DEFAULT TRUE,     -- Flipped to false by scraper when job disappears
                                           --   from the source page (scraped jobs) or by
                                           --   expiration date (community/board jobs).
    external_id   TEXT,                   -- ID from the ATS/board for dedup
    source        TEXT,                   -- 'scraper', 'community', 'manual'
    UNIQUE(company_id, external_id)       -- Prevent duplicate jobs from same source
);
```

### job_submissions table (community-sourced jobs pending approval)
```sql
CREATE TABLE job_submissions (
    id            SERIAL PRIMARY KEY,
    company_name  TEXT NOT NULL,          -- Submitter enters company name (may not be in DB)
    company_id    INTEGER REFERENCES companies(id), -- Linked if company exists in DB
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    url           TEXT NOT NULL,           -- Link to apply / job posting
    location      TEXT,
    remote        BOOLEAN DEFAULT FALSE,
    job_type      TEXT,
    salary_range  TEXT,                    -- Free text, e.g. "$80k-$120k"
    experience_level TEXT,
    audio_domain  TEXT,
    submitter_name TEXT,                   -- Name of person submitting
    submitter_email TEXT,                  -- For spam tracking, not published
    status        TEXT DEFAULT 'pending',   -- 'pending', 'approved', 'rejected'
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at  TIMESTAMPTZ,
    reviewed_by  TEXT,                     -- Admin who approved/rejected
    reject_reason TEXT,                    -- If rejected, why
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

### scrape_log table
```sql
CREATE TABLE scrape_log (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES companies(id),
    started_at    TIMESTAMPTZ DEFAULT NOW(),
    finished_at   TIMESTAMPTZ,
    status        TEXT,                    -- 'success', 'failed', 'partial'
    jobs_found    INTEGER DEFAULT 0,
    error_message TEXT,
    scrape_method TEXT                     -- 'http', 'playwright'
);
```

### career_resources table
```sql
CREATE TABLE career_resources (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    summary     TEXT,                     -- Short description for listing pages
    body        TEXT NOT NULL,             -- Markdown
    category    TEXT NOT NULL,            -- 'interview-prep', 'resume', 'skills', 'career-path', 'salary', 'freelance'
    sort_order  INTEGER DEFAULT 0,
    read_time   INTEGER,                   -- Estimated read time in minutes
    published   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

## API Design

### Public endpoints

| Method | Path | Description | Query params |
|---|---|---|---|
| GET | `/api/jobs` | Paginated job listings | `page`, `per_page`, `category`, `location`, `remote`, `job_type`, `audio_domain`, `company_id`, `search`, `sort` |
| GET | `/api/jobs/{id}` | Single job detail | — |
| POST | `/api/jobs/submit` | Community job submission | Body: title, company_name, url, location, etc. |
| GET | `/api/companies` | Company directory | `page`, `per_page`, `category`, `search`, `verified_only` |
| GET | `/api/companies/{slug}` | Company profile + their active jobs | — |
| GET | `/api/categories` | All categories with job counts | — |
| GET | `/api/search?q=` | Full-text search across jobs | `q`, `page`, `per_page` |
| GET | `/api/resources` | Career resources list | `category` |
| GET | `/api/resources/{slug}` | Single resource article | — |
| GET | `/api/resources/interview-prep` | Interview prep articles only | `page`, `per_page` |

### Admin endpoints (auth required)

| Method | Path | Description |
|---|---|---|
| POST | `/api/admin/scrape` | Trigger a scrape cycle |
| GET | `/api/admin/scrape/status` | Current scrape status |
| GET | `/api/admin/scrape/log` | Scrape history (paginated) |
| GET | `/api/admin/companies` | All companies (including unverified) |
| PUT | `/api/admin/companies/{id}` | Update company (fix URL, verify, etc.) |
| POST | `/api/admin/companies` | Add new company manually |
| GET | `/api/admin/submissions` | Job submission approval queue (`status=pending` by default) |
| POST | `/api/admin/submissions/{id}/approve` | Approve a submission → becomes active job |
| POST | `/api/admin/submissions/{id}/reject` | Reject a submission (with reason) |
| GET | `/api/admin/stats` | Dashboard stats (total jobs, companies, pending submissions) |

## Scraper Architecture

### Scrape Cycle Flow

```
1. Load companies from DB where verified=true
2. Group by scrape_method (http vs playwright)
3. Enqueue each company as a job in Redis/RQ
4. Workers pick up jobs:
   a. Check ATS domain → use ATS-specific parser if matched
   b. Otherwise use generic HTML parser
   c. Extract: title, location, description, URL, job_type, posted_date
5. Normalize extracted jobs (standardize fields)
6. Deduplicate against existing jobs (by external_id + company_id)
7. Job lifecycle management (see below)
8. Log results to scrape_log
```

### Job Lifecycle & Deactivation

The scraper runs nightly and re-visits every verified company's careers page.
On each cycle, it compares what it finds against what's already in the DB:

**For scraped jobs (source='scraper'):**
```
Fetched page successfully?
├── YES
│   ├── Job in DB AND still on page → leave active, update scraped_date
│   ├── Job in DB but NOT on page → deactivate (is_active=false)
│   └── Job on page but NOT in DB → insert as new job
└── NO (403, timeout, network error)
    └── DO NOT deactivate any jobs for this company
        (we can't confirm they're gone — the page was just unreachable)
```

**For community-submitted jobs (source='community'):**
```
NEVER re-scrape these. They follow a separate lifecycle:
├── Auto-expire after 30 days (configurable) unless renewed
├── Admin can manually deactivate at any time
└── Admin can renew (extend expiration) if the job is still open
```

**For job board listings (source='linkedin', 'indeed', etc.) — Phase 5:**
```
Shorter expiration window (14 days) since these listings rotate frequently.
Same deactivation logic as scraped jobs, but with faster expiry.
```

### Implementation Details

The deactivation logic in the scraper should work as follows:

```python
# After fetching jobs for a company:
if scrape_succeeded(company):
    current_job_ids = {job.external_id for job in fetched_jobs}
    existing_active_jobs = db.query(Job).filter(
        Job.company_id == company.id,
        Job.is_active == True,
        Job.source == 'scraper'  # only scraper jobs, not community
    )
    for job in existing_active_jobs:
        if job.external_id not in current_job_ids:
            job.is_active = False
            job.updated_at = now()
    # Insert new jobs (dedup handles duplicates)
elif scrape_failed(company):
    pass  # do NOT touch any jobs — page was unreachable
```

**Edge cases to handle:**
- ATS changed the job ID for the same role → treat as new job (showing it
  twice is better than missing it; the old one will deactivate on next cycle)
- Company removed ALL jobs (e.g. hiring freeze) → all jobs deactivate,
  which is correct behavior
- Playwright worker crashes mid-scrape → treat as failed, don't deactivate
- Community jobs that match a scraped job at the same company → dedup
  should prefer the scraped version, mark the community one as superseded

### ATS Parser Priority

When a company's careers_url is on a known ATS platform, use the
ATS-specific parser instead of generic HTML parsing:

| ATS Domain Pattern | Parser | Method |
|---|---|---|
| `boards.greenhouse.io/{slug}` | greenhouse.py | HTTP (JSON API available) |
| `job-boards.greenhouse.io/{slug}` | greenhouse.py | HTTP (JSON API available) |
| `jobs.lever.co/{slug}` | lever.py | HTTP (JSON API available) |
| `apply.workable.com/{slug}` | workable.py | HTTP (JSON API available) |
| `*.workdayjobs.com` | workday.py | Playwright (JS-rendered) |
| `*.myworkdayjobs.com` | workday.py | Playwright (JS-rendered) |
| `app.ashbyhq.com/{slug}` | ashby.py | HTTP (JSON API available) |
| `jobs.smartrecruiters.com/{slug}` | smartrecruiters.py | HTTP (JSON API available) |
| `*.icims.com` | icims.py | Playwright (JS-rendered) |
| `*.recruitee.com` | recruitee.py | HTTP (JSON API available) |
| Other | generic.py | HTTP or Playwright based on scrape_method |

Key insight: Greenhouse, Lever, Workable, Ashby, SmartRecruiters, and Recruitee
all have **JSON APIs** that return job listings without needing to parse HTML.
This makes ~84 companies in our list scrapable with a simple HTTP GET to the
right API endpoint. The ATS parsers should use the API, not HTML scraping.

### ATS API Endpoints (known)

| ATS | API URL Pattern | Format |
|---|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs` | JSON |
| Lever | `api.lever.co/v0/postings/{slug}?mode=json` | JSON |
| Workable | `apply.workable.com/api/v3/accounts/{slug}/jobs` | JSON |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{slug}` | JSON |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{slug}/jobs` | JSON |
| Recruitee | `recruitee.com/api/offers/{slug}` | JSON |

### Job Board Scraping (external to company list)

Job boards (LinkedIn, Indeed, Glassdoor) require separate scrapers with
search queries like "audio engineer", "DSP engineer", "acoustics".
These are the hardest to maintain due to anti-bot measures.
Start with Indeed (most permissive) and add others later.

## Frontend Pages

### Pages and Modes

| Page | Mode | SEO Priority | Description |
|---|---|---|---|
| `/` | Persuade | High | Hero, search bar, featured jobs, categories, submit CTA |
| `/jobs` | Operate | High | Filterable job listings with pagination |
| `/jobs/[id]` | Read | Critical | Individual job posting (must be indexable by Google) |
| `/jobs/submit` | Operate | Medium | Community job submission form |
| `/companies` | Operate | High | Company directory — browse 1,385 companies by category, search |
| `/companies/[slug]` | Read | High | Company profile: description, logo, open jobs, link to careers page |
| `/resources` | Read | Medium | Career development resources hub |
| `/resources/interview-prep` | Read | High | Interview prep guide — structured, multi-article |
| `/resources/interview-prep/[slug]` | Read | High | Individual interview prep article |
| `/resources/[slug]` | Read | Medium | Other resource articles (resume, salary, career path) |
| `/admin` | Operate | None | Admin dashboard (auth required, not indexed) |
| `/admin/submissions` | Operate | None | Job submission approval queue |
| `/admin/companies` | Operate | None | Company management (edit, verify, add) |
| `/admin/scraper` | Operate | None | Scraper monitoring + manual trigger |
| `/about` | Read | Low | About ASoundJob |

### Site Sections

#### 1. Job Board (`/jobs`)
- Filterable listings: category, location, remote/onsite, job type, experience level, audio domain
- Server-side filtered via API, SSR for SEO
- Each job detail page has JSON-LD JobPosting structured data
- "Submit a Job" CTA prominent on this page and homepage

#### 2. Community Job Submissions (`/jobs/submit`)
- Public form: job title, company name, URL, location, remote, job type, salary, description
- Submitter name + email (for spam tracking, never published)
- Optional: link to existing company in directory if matched
- On submit: creates `job_submissions` row with `status='pending'`
- No login required (lower friction = more submissions)
- Rate limiting by IP to prevent spam

#### 3. Admin Approval Queue (`/admin/submissions`)
- Auth-protected admin dashboard
- Shows pending submissions with all details
- Approve → creates a job in `jobs` table with `source='community'`, marks submission `approved`
- Reject → marks submission `rejected` with reason
- Shows count badge in admin nav

#### 4. Company Directory (`/companies`)
- Browse all 1,385 companies (including unverified ones — they're still valid directory entries)
- Filter by category (27 categories)
- Search by name
- Company profile pages (`/companies/[slug]`):
  - Company name, logo, description, category, headquarters
  - Link to their careers page
  - Active job listings at that company
  - "No open positions" state if no active jobs
- This is a key SEO asset — 1,385 company pages, each indexable

#### 5. Interview Prep Guide (`/resources/interview-prep`)
- Dedicated section within career resources
- Structured as a series of articles, organized by topic:
  - Common audio engineering interview questions
  - DSP concepts you should know
  - Acoustics fundamentals for interviews
  - Live sound practical assessments
  - Coding/algorithm questions for audio software roles
  - Portfolio/preparation tips
  - Salary negotiation for audio roles
  - What to expect at major companies (Apple, Bose, Harman, etc.)
- Each article is a Markdown document in the `career_resources` table
- Seeded with initial content, expandable over time

#### 6. Career Resources (`/resources`)
- Broader category including:
  - Interview prep (link to `/resources/interview-prep`)
  - Resume/CV writing for audio engineers
  - Skills development guides
  - Career path trajectories in audio
  - Salary guides by region/role
  - Freelancing in audio

### Key Frontend Features

1. **Job search + filters**: Category, location, remote/onsite, job type,
   experience level, audio domain. Server-side filtered via API.
2. **SEO**: SvelteKit SSR renders full HTML. Each job page needs:
   - `<title>`: "{Job Title} at {Company} | ASoundJob"
   - `<meta name="description">`: First 160 chars of job description
   - JSON-LD structured data (JobPosting schema)
   - Canonical URL
   - sitemap.xml generated at build time with all job/company/resource URLs
3. **Community submissions**: Low-friction form, no login required, IP rate-limited
4. **Admin dashboard**: Simple, functional. Approval queue, scraper monitoring, company management
5. **Saved searches / alerts**: Optional, email notifications (phase 2)
6. **Responsive**: Mobile-first, must work well on phone (most job seekers browse on mobile)

## Deployment

### Development
```
docker-compose up -d     # PostgreSQL + Redis
cd api && uvicorn api.main:app --reload
cd web && npm run dev
cd scraper && python -m scraper.main --once   # Run one scrape cycle
```

### Production (single Hetzner VPS)
```
nginx
├── / → SvelteKit (Node, port 3000)
└── /api → FastAPI (Uvicorn, port 8000)
PostgreSQL (port 5432, local only)
Redis (port 6379, local only)
RQ Worker (background process, managed by systemd)
Scraper scheduler (cron: 0 2 * * * → trigger nightly scrape)
```

### Dockerfile
Single container running:
- nginx (reverse proxy)
- SvelteKit (Node adapter)
- FastAPI (Uvicorn)
- RQ worker
- PostgreSQL + Redis (or separate containers)

## Build Order

### Phase 1: Scraper Core (do this first — it produces the data the site needs)
1. Set up Python project structure (`scraper/` with pyproject.toml)
2. Database models + migration (SQLAlchemy + Alembic)
3. Company loader (import `audio_companies_final.json` into DB)
4. Base scraper class + HTTP scraper
5. ATS parsers (start with Greenhouse + Lever — covers the most companies)
6. Playwright scraper (for non-ATS sites)
7. Job normalizer + deduplicator
8. Run first full scrape cycle, verify data quality

### Phase 2: API
1. FastAPI project structure
2. Database connection (shared models with scraper)
3. Jobs endpoint with filters + pagination
4. Companies endpoint (directory + detail)
5. Search endpoint
6. Resources endpoint
7. Community submission endpoint (POST /api/jobs/submit)
8. Admin auth + endpoints (scrape control, submission approval, company management)
9. Run: `uvicorn api.main:app --reload` and test endpoints

### Phase 3: Frontend (use impeccable skill — see workflow below)
1. SvelteKit project setup + Tailwind CSS
2. **Run `/impeccable init`** to capture product vision in PRODUCT.md
3. **Run `/impeccable shape`** to design the visual system and page UX
4. Build pages following the shape output, in order:
   a. Homepage with search + featured jobs + submit CTA
   b. Job listings page with filters
   c. Job detail page with SEO + JSON-LD
   d. Community job submission form
   e. Company directory + company detail pages
   f. Interview prep guide section
   g. Career resources hub
   h. Admin dashboard (submission queue, scraper monitor, company management)
   i. About page
5. Add SEO: meta tags, JSON-LD, sitemap.xml, robots.txt
6. **Run `/impeccable audit`** to check quality (a11y, responsive, performance)
7. **Run `/impeccable polish`** for final quality pass
8. Build + preview: `npm run build && npm run preview`

### Phase 4: Deployment
1. Dockerfile + docker-compose for production
2. nginx config
3. Deploy to Hetzner
4. Set up cron for nightly scrape
5. Set up backups (pg_dump cron)

### Phase 5: Enhancement
1. Job board scrapers (Indeed, LinkedIn)
2. Email job alerts
3. Analytics
4. User accounts (saved jobs, application tracking)
5. Company claim/edit (companies manage their own profiles)

## Impeccable Skill Workflow

The impeccable skill (installed at `.opencode/skills/impeccable/`) should be used
during Phase 3 (Frontend). Follow this sequence exactly:

### Step 1: Init (capture product context)
```
/impeccable init
```
This creates `PRODUCT.md` and `DESIGN.md` with the product vision, target users,
brand personality, and visual direction. Run this ONCE at the start of Phase 3.
Answer the prompts about:
- Product: audio industry job board + career resources
- Users: audio engineers, DSP developers, acousticians, live sound engineers
- Brand: professional, trustworthy, audio-industry-native
- Mode: Persuade (homepage), Operate (job board), Read (resources/articles)

### Step 2: Shape (plan UX before coding)
```
/impeccable shape
```
This plans the visual system (colors, typography, spacing, components) and the
UX flow for each page. Run this BEFORE writing any frontend code. It produces
a design specification that the cheaper model can follow when building pages.

### Step 3: Build pages
Use the cheaper model to build pages following the shape output.
The impeccable skill's design tokens and component patterns should be
followed exactly.

### Step 4: Audit (quality check)
```
/impeccable audit
```
After all pages are built, run this to check accessibility, performance,
and responsive behavior. Fix any issues found.

### Step 5: Polish (final pass)
```
/impeccable polish
```
Final quality pass before deployment. Catches visual inconsistencies,
edge cases, and micro-interactions.

### When NOT to use impeccable
- During Phase 1 (scraper) — no UI involved
- During Phase 2 (API) — no UI involved
- For admin pages — these are functional, not customer-facing (build simple,
  use impeccable only if you want them to look great too)

## Prerequisites to Install

Before starting any build phase, install these on your development machine:

### Already installed (from data collection phase)
- Python 3.9+ (system)
- Playwright + Chromium (pip --user)
- requests, beautifulsoup4, urllib3 (pip --user)

### Needed for Phase 1 (Scraper)
```bash
# Create a proper virtual environment for the project
python3 -m venv venv
source venv/bin/activate

# Install scraper dependencies
pip install sqlalchemy[asyncio] aiosqlite psycopg2-binary rq redis \
    alembic pydantic ruff mypy

# Playwright is already installed, but ensure browsers are present
python -m playwright install chromium
```

### Needed for Phase 2 (API)
```bash
# In the same venv:
pip install fastapi uvicorn[standard] python-jose[cryptography] \
    passlib[bcrypt] python-multipart
```

### Needed for Phase 3 (Frontend)
```bash
# Node.js 18+ (if not already installed)
# macOS: brew install node@18

# Create SvelteKit project
npm create svelte@latest web
cd web && npm install

# Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init

# Impeccable skill dependencies (it uses npx internally)
# The skill is already installed at .opencode/skills/impeccable/
# It requires Node.js (installed above) — no additional install needed
```

### Needed for Phase 4 (Deployment)
```bash
# Docker (if not already installed)
# macOS: brew install --cask docker

# Docker Compose (comes with Docker Desktop on macOS)
```

### Optional: opencode skills to consider
- **impeccable** (already installed) — for all frontend design work
- No other skills are strictly needed. The impeccable skill handles
  design, audit, and polish. Backend work is standard Python that
  doesn't benefit from specialized skills.

## How to Switch Models for Implementation

After this plan is in place, you can switch to a cheaper/faster model (e.g. Claude Sonnet, GPT-4o-mini, or similar) for implementation. The model should be given:

1. This file (`ARCHITECTURE.md`) for the big picture
2. `AGENTS.md` (next file) for specific build instructions and conventions
3. The relevant section of the codebase to work on

The expensive model (this one) is best used for:
- Architecture decisions
- Complex debugging
- Code review
- Design decisions (with impeccable skill)

The cheaper model is fine for:
- Writing boilerplate (models, schemas, routes)
- Implementing ATS parsers (well-defined patterns)
- Frontend components (following the design system)
- Tests

## Cost Estimate

| Item | Cost |
|---|---|
| Hetzner CX22 (4GB RAM) | ~$5/month |
| Domain name | ~$10/year |
| PostgreSQL | Included (self-hosted) |
| Redis | Included (self-hosted) |
| Playwright browsers | Included (self-hosted) |
| Email sending (alerts) | Free tier (Resend, Brevo) |
| **Total** | **~$6/month** |
