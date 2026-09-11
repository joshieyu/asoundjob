# Redesign brief — ASoundJob → The Type Specimen

Shape output. No code written. Supersedes the incumbent "Channel Strip" world.
Branch: `redesign-type-specimen`.

---

## 1. Job and audience

People working in audio, any level, looking for their next role — engineering
largest (DSP, audio software, embedded, EE, acoustics, transducers, T&M) but the
board is the industry's, not engineering-only. They arrive because generic boards
flatten a DSP role, a FOH gig and a transducer job into one keyword soup.

**Visitor mode: Operate.** They came to complete a task — find roles worth
applying to and filter 1,038 of them down to a shortlist. Scanability and state
legibility outrank expression. Brand lives in precise details, not in ornament.

Secondary: posters using the submit form (moderated); admins working the queues.

## 2. Outcome and proof

Primary action: filter the board down and open a listing at source.

Success: a visitor with a specialty in mind reaches a relevant, current shortlist
in under a minute, and trusts that what they see is actually open.

Product-specific truth the design must carry — all of it real, none invented:
- 1,038 active audio-related roles, re-read nightly from verified companies.
- A listing that disappears at source disappears here.
- 21 audio specialties, the field's own taxonomy.
- Free, no pay-to-post, no recruiter gatekeeping.
- Coverage gaps are disclosed, not hidden (the two accordions).

## 3. Selected direction

**The Type Specimen**, locked from the bolder hand after a re-roll. Foreign form,
full commitment.

Thesis: filters are axis sliders that continuously remap the whole board; the
board reports its own coordinates; hierarchy comes from scale contrast alone.

Two disciplines donated by declined hands, both binding:
- **One shared graticule** (from the oscilloscope) — every value measured against
  the same grid, never its own private scale.
- **Structural voids** (from the cloud quarry) — deep gaps carry section breaks;
  no rules, no boxes.

### Type: one family, axes do the work

`@fontsource-variable/recursive` — import **`recursive/mono.css`**, not `index.css`
and not `full.css`. Replaces Archivo + Spline Sans Mono.

Measured, because the obvious import is the wrong one:

| build | latin payload | axes |
|---|---|---|
| `index.css` / `wght.css` | 54 KB | wght only — no MONO, unusable here |
| **`mono.css`** | **70 KB** | **MONO 0–1 + wght 300–1000** |
| `full.css` | **297 KB** | adds CASL, CRSV, slnt — none of which this spec uses |

Incumbent for comparison: Archivo 36 KB + Spline Sans Mono 36 KB = 72 KB. So the
one-family system is payload-neutral (70 vs 72 KB); `full.css` would have been a
4× regression buying axes nothing needs.

Axis behaviour verified in-browser, not assumed: at MONO 0 `iiiiiiii`=112px and
`mmmmmmmm`=272px (proportional); at MONO 1 both measure 192px (equal advances).
Caution for anyone re-testing: the string `iiiimmmm0123` measures 288px in BOTH
modes by coincidence and will appear to prove the axis is broken. Test `i` against
`m` separately.

So "monospace only for live readouts" is an axis move, not a font swap — the
thesis expressed by the type system itself.

| Role | Axes |
|---|---|
| Specimen / display | MONO 0, CASL 0, wght 300, tracking -0.03em |
| Body | MONO 0, CASL 0, wght 400 |
| Readout / axis label | MONO 1, wght 500 |
| Emphasis | wght 700 — never color, never italic |

Replaces the ~30 verbatim repetitions of
`font-mono text-[10px] tracking-[0.14em] text-ink-soft uppercase` and the 11 bare
`<legend>` elements that hand-copy it. ~85 of 111 current `font-mono` uses are
decorative and lose the mono axis; ~14 true readouts keep it.

### Color

| token | value | contrast | role |
|---|---|---|---|
| `--color-ground` | `#F9F9F8` | — | paper; neutral, deliberately not cream |
| `--color-ink` | `#0D0D0F` | 18.43:1 | all text and structure |
| `--color-muted` | `#6B6B70` | 5.03:1 | secondary floor — no lighter |
| `--color-accent` | `#0033FF` | 6.83:1 | the single foundry accent |
| `--color-accent-inv` | `#5C7BFF` | 5.30:1 on ink | inverted moment only |
| `--color-rule` | `#DEDEDC` | 1.28:1 | decorative only, may never carry meaning |

Every text pair clears WCAG 2.1 AA body (4.5:1). This is a correction, not a
preference: the incumbent `.btn-primary` is white on `#d96c2c` at **3.42:1** and
**fails AA today**, as does `.btn-latch.is-on` and `text-lit` on panel. The
recorded AA commitment is currently violated by the shipping design.

**The Single Ink Rule.** One accent, no second hue. Specialty, seniority and
status encode by position and scale, never by color. It is the only way 21
categories coexist without becoming badge soup.

**The Rule Rule.** No grey hairline on this ground reaches 3:1, so no rule may
carry meaning. Dividing is done by void and scale. If a divider seems necessary,
the gap was too small.

### The spine: recency, not salary

Revised against measured data. **80% of board jobs (829 of 1,038) have no salary
at all.** A spine absent on four rows in five is not a spine.

The shared graticule is a **recency axis** — always present (`posted_date ??
scraped_at` is never null), and it answers the board's real anxiety: is this
still open. It also states the product's own claim structurally rather than in
footer copy.

Salary becomes a coordinate plotted on the same grid where it exists, and an
honest empty coordinate where it does not — a specimen with an axis it does not
support. This is strictly better than the incumbent, which drops the meter rail
entirely on 80% of cards and leaves the grid ragged.

`LedMeter` does not survive. Beyond the metaphor, it scales each row against a
hardcoded `companyMaxSalary = 220000`, so two identical salaries render
differently and the bars are not comparable. Its `role="img"` + `aria-label`
naming is genuinely good and **must be re-provided** by whatever replaces it.

## 4. Scope and boundaries

**In scope:** every surface. 28 files, ~700 incumbent touchpoints. 13 `@theme`
tokens, 8 component classes, 2 keyframe sets, 4 orphan hardcoded colors
(`#d96c2c` inline, `#c45447`, `#d9a13b`, and a hand-copied ink rgb), the
`theme-color` meta, and the 21-line direction contract in `app.html`.

**Must remain untouched:**
- The URL/query-param contract — `ALLOWED` whitelist, page reset on filter
  change, CSV multi-category encoding, bare `/jobs` when empty. Shareable,
  bookmarkable, back-button correct.
- Progressive enhancement. The filter rack is a real GET form; results and
  pagination are plain links. Do not convert to JS-only filtering.
- Filter grouping and order (coarse to fine).
- The zero-count category discipline: hide empty specialties, keep a
  selected-but-empty one visible, offer explicit reveal.
- The country OR-null contract and both its explanations (caveat + in-list
  divider). Honest handling of dirty location data.
- Bookmarks as localStorage + `ids=` round-trip, with legacy-key migration.
- Both disclosure accordions, sited below results.
- JSON-LD, canonical and meta tags.
- Every factual claim; no new ones invented.

**Anti-goals:**
- No dark mode. Light is committed; the inverted specimen moment is a signature,
  not a theme, and doubling the palette doubles the audit.
- No category color-coding. See the Single Ink Rule.
- No cards. `.panel` and `.well` are deleted outright.
- No decorative monospace.
- No kicker/eyebrow labels above headings.
- Not a fix-everything pass. Pre-existing functional bugs are listed in §7 and
  tracked separately; the reskin neither fixes nor inherits them silently.

## 5. States and ranges — measured, not assumed

Board: 13,621 jobs total, 8,591 active, **1,038 active + audio-related = the
default board**. `include_unrelated=true` → 8,591 (8.3×). 52 pages at 20/page;
430 with non-audio.

| Field | Missing on the default board |
|---|---|
| any salary | **829 (80%)** |
| description | 290 (28%) |
| categories | 229 (22%) |
| country | 186 (18%) |
| location | 137 (13%) |
| company, seniority | 0 (always present) |

- Titles to 170 chars (avg 34.6) — currently unclamped; a long title blows card
  height. Company names to 39 chars. Longest specialty name 39 chars.
- Max 3 categories per job, min 0.
- Salary 10,000–500,000. Currencies USD, GBP, EUR, CAD **and empty string** —
  `formatSalary` maps only USD/EUR/GBP, so CAD renders with no symbol.
- `job_type = ''` on 10,134 rows board-wide; the detail page's `?? '—'` misses
  empty string where JobStrip's `{#if}` handles it. The two disagree.
- `source='community'` on exactly 1 row — the badge and moderator footnote are
  effectively untested paths.
- `expires_date` null on ~100%.
- 722 verified companies but the dropdown loads 100.

**States every surface must carry:** default, hover, focus-visible, active,
disabled, selected, loading, empty, error, partial data, overflow.

Two gaps to close rather than reproduce:
- **No loading state exists anywhere.** No skeletons, no spinners, no `aria-busy`.
- **No error state exists on `/jobs`.** Every fetch is `.catch(() => null)`, so a
  backend outage renders as "no roles match this filter setting" — the UI states
  something false. Same on `/companies/blocked`, where an outage renders "every
  company we track is readable right now."

## 6. Interaction and layout

- **Axis sliders** for genuinely ordinal filters: seniority (entry→manager),
  salary, recency. Dragging remaps the board continuously.
- **Category is a set, not an axis** — it stays multi-select, rendered as the
  specimen's glyph grid. Honest fusion: do not force a set into a slider.
- **The axis readout** is the signature: a persistent line reporting board state
  (`1038 OPEN · CAT 6/21 · SAL 80–160K · REMOTE · SORT NEW`). Useful because
  active filters currently scroll out of view, and it is the world's own voice.
- Hierarchy by scale contrast alone. Sections separated by voids on a 4px
  baseline grid.
- One authored motion moment, exponential ease-out from an already-visible
  default. Reduced-motion coverage widened — the current guard names only two
  selectors and misses 8 component transitions plus `animate-pulse`.
- Focus-visible must be re-provided globally; it is currently one rule in
  `app.css` and the hero search input kills it with `outline-none`.
- Form controls need real states. `.well` is currently the entire input
  affordance with **no focus, invalid, or disabled styling at all**.

## 7. Constraints and open decisions

**Binding:** WCAG 2.1 AA including admin. SvelteKit 2 / Svelte 5 runes /
Tailwind v4 `@theme`. SSR for SEO. No YAP logo. Free/no-pay-to-post.

**Pre-existing defects — flagged, tracked separately, not silently inherited:**
1. JSON-LD script-tag injection via unsanitized scraped titles. *(chip)*
2. Free-text search sends `q`, backend expects `search` — search does nothing
   while the UI shows a "Search:" chip. *(chip)*
3. Three canonical URLs hardcoded to `http://localhost:5173`.
4. Company dropdown caps at 100 of 722.
5. Pagination ±2 window, no first/last, on a 52-page board.
6. Duplicate `id="feedback-dialog-title"` across simultaneously-mounted dialogs.
7. Bookmark state client-only → visible hydration flip.
8. Admin: dead limit control on the scraper page; double-fetch on every
   keystroke; no session-expiry path.
9. `1,385` hardcoded in 3 places while a live count renders on the same page.
10. `web/static/yap-logo.png` — 5.8 MB, unreferenced, still publicly served.

**Resolved 2026-09-10:**
- Orphan assets removed. The 5.8 MB `yap-logo.png` is out of `web/static/`, and
  the unreferenced stock Svelte `favicon.svg` is deleted.
- **Favicon: the YAP logo, as a placeholder.** Derived to `favicon-32.png` (2.8 KB)
  and `favicon-180.png` (71 KB) and wired in `app.html`. This is the single
  permitted use of the mark — it stays out of the header and every other surface.
  A future mark replaces it. `theme-color` in `app.html` still carries the
  incumbent `#e9e7e1` and must move to `--color-ground` with the token layer.
- **Admin is deliberately plainer.** It shares the token layer — one type family,
  one palette, the same AA floor and the same form-control states — but spends
  none of the specimen grammar on itself: no axis sliders, no coordinate readout,
  no specimen-scale display type. Density and legibility only. The public board
  carries the world; the console carries the work. This also keeps the two
  highest-risk admin surfaces (the 1152px-min company table, the 5-second scraper
  poll) out of the expressive layer entirely.

## 8. Sequence

Ordered by blast radius, atom-first so the shared primitives settle before the
pages that consume them.

1. `app.css` — tokens frozen first; everything downstream depends on the names.
2. `JobStrip` + retire `LedMeter` — the board's atom, and the graticule decision.
3. `Header` / `Footer` — site chrome, highest override density.
4. `routes/+page.svelte` — the metaphor's showcase; re-conceived, not re-skinned.
5. `jobs/+page.svelte` — 127 touchpoints, the filter rack.
6. `jobs/[id]` + `FeedbackDialog` + `Accordion`.
7. `jobs/submit` — repetitive once the form primitive exists.
8. `about` / `blocked` / `Wip` (+ the 4 stub routes).
9. Admin — 5 files, plain treatment, highly repetitive.
10. `app.html` `theme-color` + orphan cleanup. *(Favicon already done.)*

The four WIP sections (company directory, company detail, interview prep, career
resources) are confirmed as shipping. They are **not** in this reskin, but the
token layer and page templates must accommodate them: a faceted directory of
~1,394 companies, a per-company profile with open roles, and a multi-article
guide index plus article template.
