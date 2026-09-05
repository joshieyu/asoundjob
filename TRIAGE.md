# Triage: which non-contributing companies are worth fixing

645 of 728 verified companies put nothing on the board. This ranks the ones
worth a human's time, by judgement rather than by row counts, because the row
counts do not distinguish Knowles from a cable distributor.

## What the population actually is

| | companies |
|---|---|
| hard failures (`page loaded but no job link found`) | 299 |
| stored rows, all of it navigation or non-job text | 230 |
| **combined pool** | **529** |
| genuinely have jobs, none of them audio | ~110 |

296 of the 299 failures carry the *same* error. The failures and the junk-row
companies are one defect wearing two masks: the generic extractor cannot read
the page, and depending on what is on it, that surfaces as nothing found or as
"Careers" stored as a job.

By what the seeded URL points at:

- **49** point at a bare homepage with no path. Obvious seed errors.
- **85** point at a real job-board host and still fail. Mostly custom
  JavaScript career portals, not a missing parser.
- **395** point at some other page on the company's own site. The classic
  wrong-careers-URL case, and human work.
- **8** are on an ATS platform with no parser. Small, but see Knowles below.

There is no systemic win hiding here. The remaining ATS platforms are one or
two companies apiece, which the handoff already established. This is a
worklist, not a refactor.

## How this is ordered

Three things, weighted together:

1. **Does the company employ audio engineers at depth** — DSP, acoustics,
   transducers, embedded audio, audio ML. Not "is it an audio brand".
2. **Will there be open reqs on any given day.** A 12-person boutique posts
   twice a year; Demant posts continuously.
3. **Does it matter to a young audio professional** that the name is on the
   board.

Deliberately down-weighted, against their raw size: the 34 automotive OEMs and
23 game studios in the junk-row bucket. Game studios hire sound designers, and
the owner has ruled sound design out of scope. Automotive audio headcount is
thin relative to total headcount, NVH aside.

## Tier 1 — fix these first

| Company | Why it earns the top | Fix |
|---|---|---|
| **Fraunhofer IIS** | Invented mp3 and AAC. The most prestigious audio research employer in Europe, hiring DSP and audio-coding researchers continuously. | Seed. `iis.fraunhofer.de/de/jobs.html` |
| **Audio-Technica** | Global transducer manufacturer at scale. | Seed. |
| **Texas Instruments** | Audio amplifier and codec silicon. Partial scope, huge headcount. | Seed **plus a scoping query** — this is the Qualcomm play. |
| **MediaTek** | Audio DSP inside the SoCs in most non-Apple phones. Same play. | Seed plus query. |
| **CEVA** | Licenses audio and voice DSP IP. Precisely the DSP audience. | **Seed. URL is the homepage,** `ceva-ip.com/`. |
| **KEF** | Loudspeaker acoustics R&D under GP Acoustics. | **Seed. URL is the shop homepage,** `us.kef.com/`. |
| **Klippel** | The reference name in transducer measurement. Small, but every role is the audience's field. | Seed. |
| **Steinberg** | Cubase and Nuendo. Audio software engineering at depth. | Seed. |
| **Genelec** | Finnish studio-monitor maker; DSP, acoustics and transducer work, and the name every young engineer knows from the control room. **Not in the seed at all.** | Add. `genelec.com/jobs-careers` is the careers page but yields 1 junk row and no ATS host — a human needs to find where the openings actually live. |
Adobe, DPA, B&K, Sigma, LTTS/Intelliswift

## MEASURED AND REJECTED: Knowles, and the myjobs.adp.com surface

Knowles led this list on the reasoning that it makes the MEMS microphones and
balanced-armature drivers inside most hearing aids and earbuds. **That
reasoning did not survive contact with its job board.** Do not retry it.

`myjobs.adp.com` is a different ADP product from the `workforcenow.adp.com`
one the ADP parser reads: a client alias rather than a cid, and an Angular
front end behind a privacy gate. Its API is reachable without the gate:

```
GET https://myjobs.adp.com/public/staffing/v1/career-site/<alias>
    -> .id (the cid) and .orgoid
GET https://myjobs.adp.com/public/staffing/v1/job-requisitions?cid=<id>&$top=100&$skip=0
    header: orgoid: <orgoid>
```

Recorded so nobody re-derives it. But the parser is not worth building:

- **Only 2 seed companies are on this surface**, Knowles and Switchcraft.
- **Knowles returns 47 open roles and none of them are audio.** They are
  capacitors, ceramics, RF and production: "Applications Engineer - Single
  Layer Capacitors", "Sr. Ceramic Process Engineer", "Microwave Regional Sales
  Manager", "IMPREG OPERATOR", "Welder". Scored through the real Normalizer at
  native scope — more permissive than the partial scope Knowles actually
  carries — the board yield is **0 of 47**. The openings are all from the
  precision-components side of the company, not the audio side.
- **Switchcraft's seed URL is worse than useless.** It points at
  `myjobs.adp.com/heico/cx/job-listing?keyword=Switchcraft`, which is parent
  company HEICO's entire board — 279 requisitions — and the API ignores the
  keyword. Not one title even mentions Switchcraft. Parsing it would import
  279 aerospace machinist and inspector jobs under Switchcraft's name.

So the surface costs a parser, an orgoid-header code path and two seed fixes,
and returns nothing. Switchcraft's seed URL should be corrected or the company
set `verified: false`.

The general lesson, which applies to the rest of this file: **brand prestige
is a hypothesis about a company's job board, not a measurement of it.** Check
the board before spending the effort.

## Tier 2 — high value, narrower or smaller

Measurement and simulation, which feed the thinnest board categories:
**Polytec**, **National Instruments**, **Keysight**, **DEWESoft**, **ANSYS
(Acoustics)**, **LMS (Siemens)**, **Actran (MSC)**, **Free Field
Technologies**, **Crystal Instruments**.

Hearing, after the tier-1 three: **Sivantos**, **MED-EL**, **Amplifon**,
**Eargo**, **Earlens**, **Natus Medical**.

Transducers and drivers: **Celestion**, **B&C Speakers**, **Beyma**, **Warwick Acoustics**.

Pro audio with real R&D: **Calrec Audio**, **Lawo**, **AMS Neve**, **Allen &
Heath**, **Biamp Systems**, **Rode Microphones**, **Schoeps**,
**Lectrosonics**, **Zaxcom**, **Nagra**, **RCF**, **DAS Audio**, **EAW**.

Audio software and AI: **Neural DSP**, **Bitwig**, **Antelope Audio**,
**Speechmatics**, **CereProc**, **SoapBox Labs**, **IK Multimedia**,
**Audiokinetic (Wwise)**, **Firelight (FMOD)**.

Research and standards: **Fraunhofer IDMT**, **IRCAM**, **AES**, **THX**,
**Alliance for Open Media**.

Acoustic consulting, where **Arup** leads the field: **Hoare Lea**,
**Ramboll**, **Stantec**, **Sweco**, **Thornton Tomasetti**, **WSDG**.

High-end audio with genuine DSP work: **dCS**, **Naim Audio**. Both are
seeded to their homepages. Focal and Beyerdynamic came off this list on
2026-09-05 — Focal is fixed and on the board, Beyerdynamic is a recorded
non-build (see the handoff).

## The Nordic gap — measured 2026-09-05

Raised after European language support shipped. **The language layer no longer
blocks these companies; every one of the problems below is upstream of it.**
For contrast, the Nordic companies that do work: GN Store Nord 74 active / 29
board, Jabra 12/4, Sigma Connectivity 14/5, Teenage Engineering 3/1,
Elektron 2/1.

**Absent from the seed entirely.** Genelec is promoted to tier 1 above. The
rest are consumer-brand tier 3 at best: **Soundboks**, **AIAIAI**,
**Urbanista**, **Jays**, **Sudio**, **Audio Pro**. (Propellerhead is already
seeded under its current name, Reason Studios.)

**Verified, scraping "successfully", contributing nothing.** All three checked
with `check_url`; all three fail with the canonical *page loaded but no job
links found*, and the causes are all different:

| Company | What is actually there | Fix |
|---|---|---|
| **Dynaudio Automotive** | `job.dynaudio.com` is the right URL and renders "Vacant positions" with **nothing under it**. Genuinely empty right now. | None. Recheck later; do not chase this as a parser defect. |
| **DALI Speakers** | The seeded URL *is* the real careers page — its own "Job Openings" link points back at itself. No vacancies in the HTML. | None, unless the openings turn out to be JS-loaded. Verify before spending time. |
| **Nagra** | **Misidentified company.** `careers.nagra.com` is the **Kudelski Group** — digital security, cybersecurity, IoT. This is not Nagra Audio, the Swiss high-end recorder brand. It is filed under `Professional Audio & Live Sound`. | Reseed to Audio Technology Switzerland, or set `verified: false`. It will never yield an audio role as seeded. |

**Unverified with 0 rows**, in rough order of whether they are worth a human:

- **Dirac Research** — `dirac.com/careers`. Swedish room-correction and
  spatial-audio DSP house. **The standout here**; precisely the audience.
- **SEAS** — `seas.no/careers`. Norwegian driver manufacturer, a transducer
  name that matters.
- **Scan-Speak** — `scan-speak.com/careers`. Danish drivers, same argument.
- **Reason Studios** — `reasonstudios.se/careers`. DAW engineering.
- **Libratone** — `libratone.com/careers`.
- **Lyngdorf Audio** and **Steinway Lyngdorf** — two separate seed entries,
  both unverified, `lyngdorf.com` and `steinwaylyngdorf.com`.
- **Jamo Speakers** — seeded to `careers.klipsch.com`, i.e. the parent. Check
  whether that board carries anything Jamo-specific before verifying, or it
  becomes another Switchcraft.

Apply the file's own standard before promoting any of these: the seeded URL is
a hypothesis. Run `check_url` and read the sample titles first.

## The Audiotonix group — measured 2026-09-05

Allen & Heath's `current-vacancies` page links to the careers pages of eight
sister brands, which is a useful shortcut for finding the group. Seeded state
after working through it:

| Brand | State |
|---|---|
| **DiGiCo** | Already seeded and working, 5 active / 4 board. |
| **Solid State Logic** | Already seeded and working, 5 active / 4 board. |
| **Calrec Audio** | Already seeded, 3 active / 0 board, on `careers.calrec.com`. The group page points at `calrec.com/careers/` instead — worth comparing. |
| **Slate Digital**, **sonible** | Already seeded, 0 rows each. |
| **DiGiGrid** | **Added.** `digigrid.net/recruitment` fetches fine and currently says "no positions available". |
| **Sound Devices** | **Added.** Four real openings including Embedded Software Engineer and Senior Software Engineer, both audience roles. **Cloudflare-blocked, see below.** |
| **Group One Limited** | **Deliberately not added.** It is Audiotonix's US distribution arm — sales, marketing, demo suites and warehousing, no engineering. It has no current openings, and its page yields one row reading "Providing entertainment services across the USA" that scores 45 at native scope. Adding it would put a marketing tagline on the board. |

### DO NOT REPEAT: Allen & Heath and Sound Devices are Cloudflare-blocked

Both return **HTTP 403** to plain requests and serve a challenge or block page
to Playwright, **including the stealth scraper**. Confirmed with three user
agents (Chrome/Windows, Safari/macOS, curl) — it is not a UA problem. Only a
real browser session gets through.

Allen & Heath's seed URL was corrected to
`allen-heath.com/about/careers/current-vacancies/`, which is the right page and
lists three vacancies — Product Specialist MI, Embedded Software Engineer,
High Level Software Engineer — but it will keep failing until the block lifts.
Sound Devices behaves identically. Both are left `verified: true` because the
boards are real; that is a yield problem, not a seed error.

Their WordPress REST APIs are also closed (`itsec_rest_api_access_restricted`),
so that route is out too.

### MEASURED AND REJECTED: relaxing the job-link URL gate

While chasing the above I found that `extract_job_links` rejects these pages'
job links for an unrelated reason worth recording. Both sites are WordPress and
link to job posts whose slug *is* the title —
`/embedded-software-engineer-madison-wi/` — which contains none of the words
`JOB_HINT` looks for, so `looks_like_job` drops them even when the anchor text
is a clean job title.

A relaxation was prototyped: accept a same-host link from a job-hinted listing
page when the slugified anchor text matches the final path segment and the
title contains a role head noun. **Measured across 52 live careers pages: 10
new rows, 4 real (GripWorks) and 6 junk**, and the junk included
"Audio engineering Mix, master, and repair" at Native Instruments, which scores
**70** and would land on the board. Requiring the links to appear as a sibling
cluster of two or more removed all six junk rows and kept all four real ones —
but the two companies that motivated the work are blocked anyway, so it went
unbuilt. **If this is picked up later, use the sibling-cluster form; the bare
slug-match form is not safe.**

## Tier 3 — do these only when tier 1 and 2 are exhausted

Guitar and studio boutiques (**Walrus Audio**, **EarthQuaker Devices**,
**Empress**, **Two Notes**, **Goodhertz**), accessory and cable brands,
retailers and distributors, music-education institutions, most streaming
services.

## Tier 4 — consider setting `verified: false` instead

Companies with no job board at all. The loader deactivates their stale rows,
which removes them from the scrape budget and stops them reporting a
success that means nothing. The 15 error, for-sale and press-release URLs in
`audit_seed_urls`' bucket D belong here unless a real board is found.

## Working method

Per company: `python -m scraper.check_url "<url>" --name "<Company>"` first —
read the sample titles it prints, not only the counts. Then edit
`careers_url` in `data/audio_companies_final.json` by hand. Re-run
`python -m scraper.detect_nonjob_rows` afterwards to confirm the company left
the list.
