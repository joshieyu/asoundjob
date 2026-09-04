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
| **Demant (Oticon)** | One of the largest hearing groups on earth. Deep DSP, acoustics and audio-ML hiring. | Scraper. `careers.demant.com` is a genuine board. |
| **Cochlear** | Implants: embedded audio, DSP, psychoacoustics. Large and always hiring. | Seed/scraper. |
| **Starkey** | Large US hearing manufacturer with a serious audio-ML group. | Seed. |
| **L-Acoustics** | Top-tier loudspeaker R&D — DSP, transducers, acoustics, in France and the US. | **Seed. The URL is the homepage,** `l-acoustics.com/`. |
| **Audio-Technica** | Global transducer manufacturer at scale. | Seed. |
| **Texas Instruments** | Audio amplifier and codec silicon. Partial scope, huge headcount. | Seed **plus a scoping query** — this is the Qualcomm play. |
| **MediaTek** | Audio DSP inside the SoCs in most non-Apple phones. Same play. | Seed plus query. |
| **CEVA** | Licenses audio and voice DSP IP. Precisely the DSP audience. | **Seed. URL is the homepage,** `ceva-ip.com/`. |
| **ElevenLabs** | The highest-pull audio-AI name for this audience right now. | Seed. |
| **Bang & Olufsen** | Audio-first, real acoustics and DSP R&D. | Seed. |
| **KEF** | Loudspeaker acoustics R&D under GP Acoustics. | **Seed. URL is the shop homepage,** `us.kef.com/`. |
| **Klippel** | The reference name in transducer measurement. Small, but every role is the audience's field. | Seed. |
| **Steinberg** | Cubase and Nuendo. Audio software engineering at depth. | Seed. |

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

Transducers and drivers: **Celestion**, **B&C Speakers**, **Beyma**,
**Peerless**, **Warwick Acoustics**.

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

High-end audio with genuine DSP work: **dCS**, **Naim Audio**, **Focal**,
**Beyerdynamic**. Note dCS and Naim are both seeded to their homepages.

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
