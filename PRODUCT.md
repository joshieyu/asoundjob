# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary audience at launch: **audio industry job seekers** — audio engineers, DSP
developers, acousticians, live sound engineers, audio software developers, and
students entering the field. They arrive looking for roles matched to their audio
specialty, often browsing on mobile. Secondary audiences: employers/companies who
post or are listed (via community submissions and the directory), and the YAP
community members who share opportunities. Homepage and navigation optimize for
seekers first.

## Product Purpose

ASoundJob is an audio-industry job board plus career resource hub. It aggregates
job listings scraped from ~1,385 audio companies' careers pages, accepts
community-submitted jobs (admin-approved), and presents them with audio-specific
filtering (14 specialty categories like Audio DSP, Live Sound, Acoustics,
Automotive Audio), seniority, salary, location, and remote filters. Success =
audio professionals finding relevant roles faster than on generic boards, and the
YAP community becoming the go-to hub for audio careers.

## Positioning

The only job board built specifically for the audio industry, run by Young Audio
Professionals (YAP) — a community organization, not a recruiter. A generic board
could not truthfully claim: curated 1,385-company audio directory, 14
audio-specialty job categories, interview prep written for audio roles, and
community-trusted moderation of every submitted listing.

## Operating Context

- Nightly scraper refreshes listings from verified company careers pages;
  deactivation only on confirmed removal.
- Community submissions flow through an admin approval queue before publishing.
- Content sections for Company Directory, Interview Prep Guide, and Career
  Resources launch as explicit "work in progress" placeholders.
- Admin dashboard (separate, auth-protected) manages approvals, scraper runs,
  and company data.

## Capabilities and Constraints

- SvelteKit SSR frontend (`web/`), FastAPI backend (`api/`), API base URL from
  `API_URL` env var.
- All job/company/resource pages server-side rendered for SEO; JSON-LD
  `JobPosting` on detail pages; sitemap.xml generated at build time.
- Production domain not yet chosen: use `SITE_URL` env var with a localhost dev
  default for canonicals/sitemap until launch.
- Discord invite link file (`assets/discord_link.txt`) currently empty — footer
  link must render conditionally when empty.
- Logo asset `assets/YAP_logo.png` is a placeholder to be replaced later.
- Community jobs expire after 30 days; approved jobs carry a "Community"
  distinction badge vs scraped jobs.
- Accessibility target: WCAG 2.1 AA.

## Brand Commitments

- Organization name: **Young Audio Professionals (YAP)** — appears in About and
  footer alongside ASoundJob branding.
- Voice: professional, trustworthy, audio-industry-native; community-driven, not
  corporate.
- Logo placeholder at `assets/YAP_logo.png`; Discord link from
  `assets/discord_link.txt`.

## Evidence on Hand

- Real seed data: 1,385 companies (`data/audio_companies_final.json`), 14 job
  categories (`data/audio_job_categories.json`).
- Live dev database with 3,000+ active scraped jobs across ~486 companies.
- No testimonials, press, benchmarks, or customer logos exist yet — do not
  fabricate any.

## Product Principles

1. Seeker speed to relevance: an audio professional should see jobs matching
   their specialty within one interaction of landing.
2. Trust through curation: never show stale or fake listings; label community
   content distinctly; WIP sections say so plainly.
3. Community over commerce: YAP's identity is a peer community, reflected in
   copy tone and the submit-a-job loop.
4. SEO is distribution: every public page must be server-rendered, indexable,
   and structured-data rich.
5. Mobile-first reality: job seekers browse on phones in studios and venues.

## Accessibility & Inclusion

WCAG 2.1 AA baseline: sufficient contrast, full keyboard operability, labeled
form controls, semantic landmarks, visible focus states. Mobile-first responsive
throughout.
