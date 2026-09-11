# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: people working in audio, at any level, looking for their next role.
Engineering is the largest slice — DSP, audio software, embedded, EE,
acoustics, transducers, test & measurement — but the board is the industry's
job board, not an engineering-only one: live sound, sound design, game audio,
music production, product, and sales/marketing/CS roles at audio companies all
belong. This supersedes the narrower "the audience is audio engineers" framing
in `HANDOFF.md`.

A seeker arrives because generic job boards fail them: audio roles are
scattered across hundreds of company careers pages and, when they do appear on
an aggregator, a DSP role, a FOH gig, and a transducer engineering job are
flattened into the same keyword soup.

Secondary: anyone with an audio role to post — companies and community members
— who submits through the public form. Their submissions pass through human
moderation before going live.

Third: the site's own admins, who work the submission queue, monitor scraper
health, and correct company records through the admin dashboard.

## Product Purpose

ASoundJob aggregates audio industry jobs into a single board that understands
audio work, and pairs it with career resources for the field.

It scrapes the careers pages of a curated directory of audio companies nightly,
normalizes what it finds, classifies each listing against audio-specific
categories, and presents the result with filtering, search, and SEO-oriented
detail pages. Community-submitted jobs enter the same board through an
admin-approved queue.

Current state: **pre-launch.** Success right now is being genuinely ready for
public traffic — coverage is close enough, so the remaining work is resolving
the sections still behind WIP placeholders and finishing the surfaces.

## Positioning

The board is built on a hand-curated directory of audio companies rather than
on keyword search over a general job index. That is the mechanism a general
aggregator cannot truthfully copy: coverage comes from knowing which companies
make audio, and relevance comes from classifying against audio's own taxonomy
(21 categories, from psychoacoustics to NVH to transducers) instead of matching
the word "audio" in a description.

Two consequences follow that reinforce it: listings reflect what is actually
open, because a job that disappears from its source disappears here; and the
board surfaces companies that no aggregator indexes, because they were found by
people who work in the industry.

## Operating Context

- Nightly scrape cycle over verified companies' careers pages. Fallback chain:
  ATS JSON API → HTTP → Playwright → Playwright with stealth. Ten ATS parsers
  (Greenhouse, Lever, Workable, Ashby, SmartRecruiters, Recruitee, iCIMS, ADP,
  Workday, and others), plus JSON-LD `JobPosting` extraction on generic pages
  and detection of hidden ATS embeds.
- `data/audio_companies_final.json` (1,394 companies) is seed truth and flows
  one way into the database. It is reloaded at the start of every cycle unless
  `--skip-load`; nothing writes back to it. Rows marked `source="manual"` are
  hand-verified and never overwritten. Deletions are not protected — they must
  be applied to the seed by hand via `scraper.export_seed_edits`. Tooling
  proposes, humans apply.
- Job deactivation happens only on a confirmed successful fetch. A 403,
  timeout, or network error never deactivates a job — the board may not claim a
  role is gone unless it saw the page without it.
- Community submissions are never re-scraped and auto-expire after 30 days.
- Admin dashboard covers the submission queue, scraper monitoring, company
  management, and feedback.
- A body of read-only diagnostic tooling exists (`check_url`,
  `detect_nonjob_rows`, `detect_truncation`, `audit_seed_urls`,
  `diagnose_failures`, `discover_careers_urls`) and is part of how the board is
  maintained.

## Capabilities and Constraints

**Shipped:** job board with filtering (category, seniority, job type, salary,
company, location, country, remote, sort) and search; job detail pages with SEO
metadata and JSON-LD; community submission form with admin approval; homepage;
about page; admin dashboard; sitemap and robots.

**Behind WIP placeholders, and confirmed as real planned sections:** company
directory, company detail, interview prep guide, career resources hub. These
ship — they are not features to quietly drop.

**Audio relevance gating:** the public board shows only jobs scored
`is_audio_related = true`. The API and the `/jobs` toggle accept
`include_unrelated=true` to reveal non-audio roles at audio companies. Scoring
combines title/description signals with the company's `audio_scope`
(`native` | `partial` | `all`), which admins can override.

**Taxonomy:** 21 audio job categories in `data/audio_job_categories.json` are
the source of truth for classification and filtering. A deliberate trade favors
recall over precision, so a share of audio-related jobs carry no category.

**Vocabulary that matters:** `is_audio_related`, `audio_scope`,
`relevance_score`, `trust_empty`, seed truth, ATS discovery.

**Technical constraints:** Python 3.9 for the scraper and API (write
3.9-compatible code); Playwright concurrency ≤5, HTTP ≤50; PostgreSQL in
production, SQLite in development; SSR for every job, company, and resource
page, for SEO.

**Undecided:** production domain (canonical URLs still point at localhost) and
launch date.

## Brand Commitments

- **Name:** ASoundJob, "by Young Audio Professionals" — YAP is the peer
  community that maintains it.
- **Free, never pay-to-post.** No paid ranking, no recruiter gatekeeping, no
  cut of anything. Binding on all future product and monetization decisions.
- **The YAP logo is not part of the visual identity.** It must not appear in the
  header, nav, or any surface where it would read as the brand mark; identity is
  the text wordmark. One narrow exception, set 2026-09-10: it serves as the
  favicon for now, derived to `web/static/favicon-32.png` and `favicon-180.png`.
  The 2048px source was not kept in the repo. A future mark replaces the favicon.
- **Voice:** plainspoken, technical, unhyped. It addresses people who know the
  field and does not explain audio to them.

## Evidence on Hand

- `data/audio_companies_final.json` — 1,394 curated audio companies with
  careers URLs; the seed and the coverage claim.
- `data/audio_job_categories.json` — 21 category definitions.
- Live board data in the database, with the scrape log as its provenance.
- YAP Discord invite: `web/src/lib/data/discord-link.txt` (populated), also at
  `assets/discord_link.txt`.
- Favicon: `web/static/favicon-32.png`, `favicon-180.png`, derived from the YAP
  logo as a placeholder. No other mark or identity asset exists.

**Absences future work must not fabricate:** no testimonials, no case studies,
no press, no user counts, no placement or hiring-outcome numbers, no pricing,
no partner or customer logos. Company counts and category counts are real and
should be read from the data rather than hardcoded.

## Product Principles

1. **Curation is the product.** Coverage comes from a hand-reviewed company
   directory; anything that dilutes it into general keyword aggregation removes
   the reason to use this board.
2. **Never claim more than the scrape saw.** A failed fetch is not evidence a
   job is gone. Accuracy about what is actually open outranks board size.
3. **Speak audio's own taxonomy.** Categories, seniority, and filters use the
   field's vocabulary, because that is what generic boards flatten away.
4. **Free and ungatekept.** No paid placement, no recruiter tolls — the board
   serves seekers first.
5. **Tooling proposes, humans apply.** Automated systems surface candidates and
   diagnoses; a person confirms them into seed truth.

## Accessibility & Inclusion

**WCAG 2.1 AA** is a stated requirement, not best-effort. Applies to all
surfaces, including the admin dashboard.
