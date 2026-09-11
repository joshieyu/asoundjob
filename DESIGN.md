---
name: ASoundJob
description: A type-specimen job board where filters are axis sliders and the board reports its own coordinates.
colors:
  ground: "#f9f9f8"
  ground-tint: "#f1f1ef"
  ink: "#0d0d0f"
  muted: "#6b6b70"
  accent: "#0033ff"
  accent-inv: "#5c7bff"
  rule: "#dededc"
typography:
  specimen:
    fontFamily: "'Recursive Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(3rem, 9vw, 6rem)"
    fontWeight: 300
    lineHeight: 0.86
    letterSpacing: "-0.03em"
    fontVariation: "'MONO' 0"
    fontFeature: "tabular-nums"
  display:
    fontFamily: "'Recursive Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(1.75rem, 4.5vw, 2.75rem)"
    fontWeight: 300
    lineHeight: 1.25
    letterSpacing: "normal"
    fontVariation: "'MONO' 0"
  title:
    fontFamily: "'Recursive Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "normal"
    fontVariation: "'MONO' 0"
  body:
    fontFamily: "'Recursive Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
    fontVariation: "'MONO' 0"
  meta:
    fontFamily: "'Recursive Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
    fontVariation: "'MONO' 0"
  coord:
    fontFamily: "'Recursive Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0"
    fontVariation: "'MONO' 1"
    fontFeature: "tabular-nums"
  label:
    fontFamily: "'Recursive Variable', ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.01em"
    fontVariation: "'MONO' 1"
rounded:
  none: "0"
spacing:
  tight: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  row: "28px"
  void-sm: "40px"
  void: "64px"
  void-lg: "80px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.ground}"
    typography: "{typography.meta}"
    rounded: "{rounded.none}"
    padding: "8px 14px"
  button-primary-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.meta}"
    rounded: "{rounded.none}"
    padding: "8px 14px"
  button-quiet-hover:
    backgroundColor: "{colors.ground-tint}"
    textColor: "{colors.ink}"
  button-quiet-pressed:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
  button-disabled:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
  field:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.meta}"
    rounded: "{rounded.none}"
    padding: "7px 2px"
    width: "100%"
  field-focus:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    padding: "7px 2px 6px"
  field-disabled:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
  axis-slider:
    backgroundColor: "transparent"
    rounded: "{rounded.none}"
    height: "24px"
    width: "100%"
  link:
    backgroundColor: "transparent"
    textColor: "{colors.accent}"
  link-hover:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
  icon-toggle:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.none}"
    height: "32px"
    width: "32px"
  icon-toggle-pressed:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
---

# Design System: ASoundJob

## Overview

**Creative North Star: "The Type Specimen"**

ASoundJob is laid out the way a foundry lays out a type specimen sheet: one family, one ink, enormous scale contrast, and nothing decorative between the reader and the data. The thesis is that the board reports its own coordinates back to you and that hierarchy comes from scale contrast alone. Axis sliders were originally the whole filter language; one survives (salary), because most of the board's filters turned out to be sets rather than positions. The home page opens with the live job count set at `clamp(3rem, 9vw, 6rem)` in weight 300 against a near-white ground — a number, not a headline — and everything below it is a smaller reading of the same instrument. The page never decorates; it registers.

The family is Recursive Variable, loaded once, and its MONO axis carries the whole sans-to-mono relationship. Readouts are not a font swap to a second family; they are an axis move from `'MONO' 0` (body) to `'MONO' 1` (`.coord`, `.axis-label`). Only the `mono.css` slice ships (MONO 0–1, wght 300–1000, ~70 KB); the 297 KB `full.css` was rejected because the CASL, CRSV and slnt axes are unused. That single-family economy is why a board with 21 specialty categories can stay legible without a second voice.

Two disciplines were donated from directions that lost. **One shared graticule** — every value measured against the same grid, never its own private maximum — was retired on 2026-09-11 when the board went two-up (see *Amendments*); its surviving trace is that coordinate values still read in a consistent order across rows. **Structural voids** — division by deep gaps (40–80px) — still governs the page, but no longer governs the board itself, which is now a grid of bordered cards. Where a hairline appears it is a decorative register mark and carries no meaning. The confirmed visual anti-reference is the incumbent mixing-console world this replaced in full — panels, wells, latch buttons, bevel and recess shadows, LED meters, decorative monospace, and all-caps micro-labels are all rejected, not softened.

**Key Characteristics:**
- One typeface (Recursive Variable), one accent (#0033FF), zero secondary hues.
- Zero radius, zero shadow. Cards exist on the board and nowhere else.
- Hierarchy by scale contrast: an 8x jump from coordinate readout to specimen numeral.
- Recency, not salary, is the spine — now read as text rather than plotted.
- Deep structural voids divide the page; the board divides with 1px card borders.
- Light and dark are one palette in two settings; seven tokens carry both.
- Monospace is an axis move (`'MONO' 1`), reserved for live data and small labels.
- WCAG 2.1 AA is binding on every surface, admin included.

## Colors

A near-white paper ground, near-black ink, one grey for secondary text, and exactly one saturated foundry blue — the palette of a specimen sheet, not of an interface chrome kit.

Since 2026-09-11 the same seven tokens carry a second setting. Every value below is the light setting; the dark setting is in **Dark Mode** at the end of this section. No component names a colour outside these seven, which is the only reason a second setting was seven lines of CSS instead of a sweep.

### Primary
- **Foundry Blue** (`{colors.accent}`): The single accent. It is the caret colour, the focus-ring colour, the selection highlight, the link colour, the primary button fill, the checkbox `accent-color`, and the hover colour for interactive text. Measured 6.83:1 against the ground and 6.83:1 for ground-on-accent, so it is safe for both button fill and body-size link text. It is never used to classify — a community-submitted listing is the one place it labels anything, and it labels provenance, not category.
- **Inverted Foundry Blue** (`{colors.accent-inv}`): Exists for one reason. Foundry Blue on ink measures 2.70:1 and fails; this lighter cast measures 5.30:1. Use it only where accent sits on an ink-filled surface, never on the ground.

### Neutral
- **Paper Ground** (`{colors.ground}`): The page. Warm near-white, also the browser theme colour and the scrollbar track. The sticky header sits on it at 95% with a backdrop blur.
- **Tinted Paper** (`{colors.ground-tint}`): One half-step down from the ground. The only fill used for a hover wash on quiet buttons and for the inline notice block. It is a tonal shift, never a card.
- **Ink** (`{colors.ink}`): All primary text, the pressed/selected fill for toggles and the current pagination page, and the axis-slider thumb. 18.43:1 on ground.
- **Muted Ink** (`{colors.muted}`): Secondary text, placeholders, axis labels, inactive nav, and the resting underline of a field. 5.03:1 on ground — the lightest ink permitted to carry meaning.
- **Register Rule** (`{colors.rule}`): The hairline. Header and footer boundaries, job-card and chip frames, the scrollbar thumb. 1.28:1 against the ground.

### Dark Mode
One palette, two settings — not a second design. The tokens take these values under `:root[data-theme='dark']`, and under `@media (prefers-color-scheme: dark)` guarded by `:not([data-theme='light'])` so a reader with no JS still gets it and an explicit choice still wins. The two blocks are duplicated on purpose: CSS cannot share a declaration block across a media query. Edit them together.

| Token | Light | Dark | Dark contrast |
| --- | --- | --- | --- |
| `ground` | `#f9f9f8` | `#131314` | — |
| `ground-tint` | `#f1f1ef` | `#1c1c1e` | — |
| `ink` | `#0d0d0f` | `#f2f2f0` | 16.8:1 on ground |
| `muted` | `#6b6b70` | `#9c9ca2` | 6.9:1 on ground, 6.6:1 on tint |
| `accent` | `#0033ff` | `#5c7bff` | 5.1:1 on ground |
| `accent-inv` | `#5c7bff` | `#0033ff` | for ink-filled surfaces |
| `rule` | `#dededc` | `#2e2e30` | 1.39:1 — decorative, as intended |

The accents **trade places**. Foundry Blue measures 2.6:1 on the dark ground and is unusable there. `color-scheme` is declared with each setting so native selects, checkboxes, range inputs and scrollbars follow without extra styling.

### Named Rules
**The Single Ink Rule.** One accent, no second hue, ever. Specialty, seniority, job type and status encode by position and scale, never by colour. This is what lets 21 categories coexist on one board without becoming badge soup. If a new surface needs to distinguish two things, move one of them or resize it — do not tint it.

**The Rule Rule.** `{colors.rule}` measures 1.28:1 against the ground, far under any legibility threshold, so it may never carry meaning. It is decorative register only: dividers, tracks, frames. Anything meaning-bearing — a value, a state, a plotted position — uses `{colors.muted}` (5.03:1) or `{colors.ink}` (18.43:1).

**The Inverted Accent Rule.** Foundry Blue is forbidden on ink (2.70:1). On any ink-filled surface the accent is `{colors.accent-inv}` or it is not accent at all. This holds in both settings without amendment — in dark, ink is simply the light colour and the two accent tokens have swapped to match.

**The Two-Setting Rule.** A colour may only enter this system as one of the seven tokens, because every one of them has to answer in both settings. A raw hex, a `gray-*` utility or a `bg-white` is a light-mode-only decision and will be wrong in dark; there are currently zero of them in the components and that is the number to keep.

## Typography

**Display Font:** Recursive Variable (with `ui-sans-serif, system-ui, sans-serif`)
**Body Font:** Recursive Variable — the same family at `'MONO' 0`
**Label/Mono Font:** Recursive Variable at `'MONO' 1` — an axis move, not a second family

**Character:** One variable family does everything. Recursive at weight 300 and negative tracking reads as a cool, wide-set specimen numeral; at 600 it reads as a working UI label; at `'MONO' 1` it snaps to a fixed-pitch readout without changing skeleton. The pairing feels like one instrument with a switch on it, because it is. Only the `mono.css` build ships: MONO 0–1 and wght 300–1000 at roughly 70 KB, imported once in the root layout.

### Hierarchy
- **Specimen** (300, `clamp(3rem, 9vw, 6rem)`, line-height 0.86, tracking -0.03em, tabular figures): The single largest object on a page and effectively always a number — the live open-roles count on the home page, the status code on the error page. One per page, at most.
- **Display** (300, `clamp(1.75rem, 4.5vw, 2.75rem)`, tight leading): The sentence that explains the specimen numeral, and the result count on the board. Always light weight; the size does the work.
- **Title** (600, 1.375rem, tight leading): Job titles in a row, section headings, the wordmark, admin stat values.
- **Body** (400, 0.9375rem, 1.5): Default document text, set on `body`. Prose blocks are held to roughly `max-w-prose`/`max-w-xs` measures rather than running the full 6xl container.
- **Meta** (400–600, 0.8125rem): Company and location lines, specialty lists, footer links, nav links, all button and field text.
- **Coordinate** (`.coord`; 500, 0.75rem, `'MONO' 1`, tabular figures, tracking 0): Live data readouts only — salary, level, type, age, counts, pagination numbers, the footer status line. This is the board reporting its own coordinates.
- **Axis Label** (`.axis-label`; 500, 0.75rem, `'MONO' 1`, tracking 0.01em, muted): The name of an axis, not a value — filter legends, admin stat captions, form field labels, the divider caption on the board. Deliberately sentence case.

### Named Rules
**The Axis-Move Rule.** Monospace is a variation axis, never a font swap and never decoration. `'MONO' 1` is permitted on exactly two classes: `.coord` for live data readouts and `.axis-label` for the names of axes. Tailwind's `font-mono` is banned outright — it no longer resolves to the brand family and would introduce a second voice.

**The Sentence-Case Label Rule.** `.axis-label` is not uppercase and must not be made uppercase. The rejected console world's 10px all-caps mono micro-label was both a legibility failure and a screen-reader failure; sentence case at 0.75rem with muted ink is the replacement, and it is the rule.

**The Scale-Contrast Rule.** Hierarchy is produced by size and weight only. There is roughly an 8x range between coordinate and specimen; use it. Do not reach for colour, uppercase, a badge, or a rule to promote something — reach for the next step up the ramp.

## Layout

A single centred column, `max-w-6xl` (72rem), with `px-4` rising to `px-6` at the `sm` breakpoint and `pt-6 pb-16` on `main`. There is no page-level grid chrome; the container is the only frame.

Vertical rhythm is a 4px base with a deliberately bimodal distribution. Inside a block, spacing is small and even (4/8/12/16/24px — `mt-1` through `mt-6` carry most of the page). Between blocks, spacing jumps straight to a structural void (40/64/80px — `mt-10`, `mt-16`, `mt-20`). There is almost nothing in between, and that gap in the scale *is* the division system: sections on the home page are separated by 80px of nothing, not by a rule or a container. Job cards breathe on 16–20px of internal padding (`p-4 sm:p-5`) and are separated by a 12px grid gap plus their own 1px border.

The board is `lg:grid-cols-[17rem_1fr]` with a 24px gutter — a sticky filter rail at `lg:top-24` beside the results. The job list inside it is a **container query**, not a viewport one: `@container` on the wrapper, `@3xl:grid-cols-2` on the grid, so the list goes two-up whenever it personally clears 48rem. This is required, not stylistic — the same component renders beside the 17rem rail on `/jobs` and full-bleed on `/`, so a viewport breakpoint would be right on one page and wrong on the other. Full-width interruptions inside the grid (the "location not parsed" divider, empty and outage states) carry `col-span-full`. The header collapses its nav to a `Menu` toggle below `md`; the footer is 1 → 2 → 4 columns across `sm` and `lg`.

One global normalization is load-bearing: `fieldset { min-inline-size: 0 }`. Browsers give `fieldset` an implicit min-content floor that ignores grid track sizing, which broke the filter rail out of its 17rem column. Keep it.

### Named Rules
**The Structural Void Rule** *(amended 2026-09-11)*. Deep gaps divide **the page**. A section boundary is 64–80px of ground; if a boundary needs more emphasis than that, it needs more space, not a border. The board is the one exemption: job cards are boxes, by explicit product decision. The exemption does not generalise — nothing else in this system gets a card because the board has one.

**The One Graticule Rule** *(retired 2026-09-11)*. Superseded by the two-up board; see *Amendments*. The half of it worth keeping: no component may rescale itself against its own private maximum. That is why `LedMeter` was deleted and why nothing has replaced it.

**The Per-Record Scale Ban** *(the surviving half, binding)*. A component that measures a record against a maximum derived from that record's own group is not comparable across rows and does not ship.

## Elevation & Depth

There are no shadows anywhere in this system. Grep confirms it: not one `box-shadow`, not one `shadow-*` utility, in any stylesheet or component. Depth is conveyed by three things only — the half-step tonal shift from Paper Ground to Tinted Paper on hover, the register hairline, and empty space. The sticky header's only depth cue is a 95%-opacity ground with a backdrop blur, which reads as paper sliding under paper rather than as a floating plane.

Motion is equally thin: a 120ms ease on `background-color`, `border-color` and `color` on buttons, and 120ms on `border-color` for fields. Nothing moves position, scales, or lifts. A full `prefers-reduced-motion: reduce` block clamps every animation and transition to 0.01ms and disables smooth scrolling.

### Named Rules
**The No-Shadow Rule.** This system has no shadow vocabulary and must not acquire one. Bevels, recesses, inner glows and hard offset shadows are the rejected console world; a raised or inset surface is not available in this world at any size. Depth comes from tone, hairline, and void.

## Shapes

Radius is 0 throughout. The token layer defines exactly one radius value, `--radius-none: 0`, and every component sets `border-radius: 0` explicitly — buttons, fields, the icon toggles, the accordion summary. There is no radius scale to choose from and none should be invented.

The form language is a paper-and-rule vocabulary. Borders are 1px and do exactly three jobs: a full box around a button or an icon toggle, a single bottom edge under a field, and — since 2026-09-11 — a full box around a job card or a specialty chip. Fields remain underlines, not boxes: a stroke under the text, never a filled well with corners. Nothing is clipped, masked, or given a silhouette, and radius stays 0 on every one of those boxes, which is what keeps a card reading as a registered frame rather than a UI kit tile.

## Components

The character across the board is flat, square, and quiet at rest — nothing is styled to look pressable; it announces itself only when you touch it.

### Buttons
- **Shape:** Perfectly square corners (`border-radius: 0`), 1px border, inline-flex with an 8px gap between label and any glyph. Padding is 8px vertical / 14px horizontal, label at meta size (0.8125rem) weight 600.
- **Primary:** Foundry Blue fill with paper text and a matching border.
- **Hover / Focus:** Primary inverts to an ink fill and ink border over 120ms; focus is the global 2px Foundry Blue outline at 2px offset, never a colour-only cue.
- **Quiet:** Transparent with a Muted Ink border and ink label. Hover darkens the border to ink and washes the fill to Tinted Paper. This is the default for secondary and destructive-adjacent actions alike; there is no third button variant.
- **Pressed / On:** `aria-pressed="true"` or `.is-on` fills the quiet button with ink and flips the label to paper. Used for verified toggles in admin and for active filter chips on the board — state is carried by the ARIA attribute and the fill together.
- **Disabled:** Transparent fill, muted label, Register Rule border, and a line-through on the label. Cursor `not-allowed`. The strike is what makes disabled readable without relying on the low-contrast border.

### Inputs / Fields
- **Style:** A single 1px Muted Ink underline on a transparent ground, square, 7px/2px padding, meta size. The same class covers text inputs, search, number pairs, and selects — the rail's Level / Type / Country / Company controls are all `.field` selects.
- **Hover:** Underline darkens to ink.
- **Focus:** Underline thickens to 2px and turns Foundry Blue; bottom padding drops 1px so the baseline does not shift.
- **Error (`[aria-invalid="true"]`):** Underline becomes 2px *dotted* ink. Stroke style, not hue, carries the error.
- **Disabled:** Muted text and a *dashed* underline, cursor `not-allowed`.
- **Checkboxes:** Native 16px boxes with `accent-color` set to Foundry Blue — the one place the browser's own control is left intact.

### Axis Slider (`.axis`)
The literal form of the thesis: a filter that continuously remaps the board. A native `input[type=range]` stripped of its chrome down to two marks — a 1px Muted Ink track and a 2px by 14px ink hairline as the thumb, square, no fill, no radius, no shadow. Since the recency tick was removed this is the system's only remaining plotted mark, and it is the reference for any future one. Hover and `:focus-visible` turn the thumb Foundry Blue; nothing grows or lifts. It is 24px tall so the pointer target stays comfortable while the ink stays 1px.

**One** ships on the board rail: **Minimum salary** (0–300,000 in 10,000 steps). Level was the second until 2026-09-11, when it became a multi-select; see *Amendments*. Each is captioned by an `.axis-label` legend above and answers with a `.coord` readout below marked `aria-live="polite"` — the axis is set, the board reports back its new coordinate. The visible control carries a screen-reader-only `<label>` and an `aria-valuetext` that speaks the human value ("senior", "any level") rather than the raw index, and the Level axis ships a `<noscript>` `.field` select so the filter still works without JS. A slider is only correct for an ordered domain **and a single value**. Level is ordered but is now a set — a reader open to senior *or* manager but not lead cannot say so on an axis — so it is checkboxes. Specialty and job type are checkboxes for the same reason; country is a select; company is free text, because 722 verified companies is not a menu.

### Links
- **Style:** Foundry Blue with a persistent underline, offset 0.18em, thickness from the font's own metric.
- **Hover:** Colour resolves to ink; the underline stays. Inline links inside prose and list links in the footer both follow this.

### Navigation
- **Style:** A sticky 64px header on 95% ground with a backdrop blur and a Register Rule bottom hairline. Wordmark at title size weight 700 with a `.coord` sub-line under it.
- **States:** Inactive links are muted meta weight 600; the current page is ink with a 2px underline at 6px offset (`aria-current="page"` in the markup). Hover goes Foundry Blue.
- **Mobile:** Below `md` the links collapse behind a quiet `Menu` / `Close` button with `aria-expanded`/`aria-controls`; the panel is a plain bordered-top list, not an overlay. A skip link is the first focusable element on every page.

### Specimen Numeral (`.specimen`)
The one oversized object on a page, and effectively always a figure. Weight 300, tabular figures, 0.86 leading and -0.03em tracking so a long count sets as a solid block. It carries no label of its own; the Display line beneath it does the naming. Never set a word in it where a number would do, and never set two on a page.

### Coordinate Readout (`.coord`)
The board reporting its own position. `'MONO' 1`, 0.75rem, weight 500, tabular figures so digits stack into columns down a list. Used for salary/level/type in a job row, category counts, pagination numbers, timestamps, and the footer status line. Missing values render as an em dash in muted ink rather than being omitted — an empty coordinate is still a coordinate.

### Job Card (signature)
*Rebuilt 2026-09-11; was the borderless Job Strip.* A 1px Register Rule box on the ground, radius 0, `p-4 sm:p-5`, border going Muted Ink on hover. It is a `flex flex-col` so it can stretch to its grid row and bottom-align its chips, which is what makes a two-up row scan as a row rather than as two ragged columns.

Title at Title size links to the detail page, goes Foundry Blue with an underline on hover, and clamps to two lines. The action cluster — two 32px square icon buttons, bookmark and report, borders appearing only on hover, the bookmark carrying an ink fill and `aria-pressed` — sits inline with the title rather than in its own grid column. Company name in ink weight 600 sits inline with location and remote status at meta size in muted ink.

The coordinate row is a wrapping `<dl>` of labelled pairs: a sentence-case `.axis-label` key beside a `.coord` value. **Pairs a job doesn't have are omitted, not em-dashed** — 76% of the board carries no salary and 26% no specialty, so fixed columns were mostly plotting absence. `seen` always renders, so a card is never coordinate-less.

### Specialty Chip
*Added 2026-09-11.* A `<ul aria-label="Specialties">` of 1px-framed chips on Tinted Paper, `.coord` at 0.75rem in Muted Ink, `px-1.5 py-0.5`, radius 0. Measured 4.69:1 on its fill — AA at that size, with the least headroom of any pair in the system, so darkening the tint or lightening the muted token needs re-measuring. Chips are `mt-auto` so they sit on the card's bottom edge and align across a row. Monochrome by The Single Ink Rule: 21 specialties, none of them tinted, which is what keeps a chip row from becoming badge soup.

### Theme Toggle
*Added 2026-09-11.* A 32px icon button in the header, in the same vocabulary as the bookmark and report toggles — transparent border appearing on hover, `aria-pressed`, a label naming the destination rather than the state. The glyph is a half-filled disc: the tone axis at its two ends, deliberately not a sun and not a moon. It carries `.js-only`, which hides it with `visibility` — space reserved so hydration doesn't shift the header, and never focusable when the head script hasn't run. State lives in a shared module store because the header renders two of these, desktop and mobile.

### Recency Tick (removed 2026-09-11)
Deleted with the two-up rebuild; see *Amendments*. Recency is still the spine and still the default sort, but it now reads as a `.coord` value (`seen 3 days ago`) rather than a plotted position. Do not reinstate a per-row plot without re-reading The Per-Record Scale Ban.

### Admin (documented variation)
Admin shares the token layer exactly — same ground, same ink, same accent, same `.btn`, `.field`, `.axis-label`, same zero radius — and spends none of the specimen grammar. No axis sliders, no coordinate readouts on hero figures, no specimen-scale display type; admin stat figures top out at Title size in a `flex-col-reverse` pair with an axis label beneath. This is an explicit user decision and is correct, not drift. WCAG 2.1 AA remains binding here.

## Do's and Don'ts

### Do:
- **Do** set every surface in Recursive Variable and reach the mono voice through `font-variation-settings: 'MONO' 1`, never through a second family.
- **Do** divide page sections with 64–80px structural voids and let the ground do the work; the board's card borders are a scoped exemption, not a precedent.
- **Do** keep meaning-bearing values in `{colors.ink}` (18.43:1) or `{colors.muted}` (5.03:1), and keep `{colors.rule}` (1.28:1) purely decorative.
- **Do** refuse any component that scales a record against its own group's maximum; that is what got `LedMeter` deleted.
- **Do** answer both settings when adding any colour, and re-run the contrast audit in dark as well as light.
- **Do** reach for a container query when a component renders at two different widths on two pages — the board does, and a viewport breakpoint would be wrong on one of them.
- **Do** encode state with shape as well as colour: dotted underline for invalid, dashed underline for disabled, strike-through for a disabled button label.
- **Do** use `{colors.accent-inv}` (5.30:1) whenever accent must sit on an ink-filled surface.
- **Do** keep `fieldset { min-inline-size: 0 }` in the base layer; without it the filter rail escapes its grid track.
- **Do** pair every axis slider with an `.axis-label` legend above and an `aria-live="polite"` `.coord` readout below, plus `aria-valuetext` speaking the human value.
- **Do** give multi-select filters the same `aria-live` `.coord` readout an axis gets — the checkbox set answers back (`senior, lead`) exactly as the slider did.
- **Do** put `min-w-0` on every grid item that can contain a `truncate`d line; `min-width: auto` is the default and a nowrap child will set the whole track's minimum.
- **Do** state hierarchy with scale: a coordinate readout and a specimen numeral are the two ends of a single ramp roughly 8x apart.

### Don't:
- **Don't** introduce a second hue. Specialty, seniority and status encode by position and scale, never by colour.
- **Don't** use `font-mono` or any Tailwind mono utility; it no longer maps to the brand family.
- **Don't** use monospace decoratively — `'MONO' 1` belongs to live data readouts and axis labels only.
- **Don't** uppercase `.axis-label`; the all-caps micro-label was a legibility and screen-reader failure and was removed on purpose.
- **Don't** add a radius. Every corner in this system is square, cards and chips included, and there is no radius scale to pick from.
- **Don't** write a raw hex, a `gray-*`, a `bg-white` or a `text-black` into a component; it is a light-mode-only decision. There are zero today.
- **Don't** give anything outside the board a card. The exemption is scoped to the job list.
- **Don't** add shadows of any kind — ambient, offset, bevel, recess, or inner glow. There is no shadow vocabulary here.
- **Don't** build cards, panels, wells, latch buttons, or LED-style meters; that is the rejected console world in full.
- **Don't** let a component scale itself against its own private maximum. The retired per-company meter did exactly that and made rows non-comparable.
- **Don't** make salary the structural spine of any board view; 80% of rows have none.
- **Don't** put an unordered set on an axis slider; a slider implies a rank, so specialty, country and company stay as checkboxes and selects.
- **Don't** give a slider a filled track, a round thumb, or a value bubble — the thumb is a 1px ink hairline standing on a 1px track.
- **Don't** reach for a slider on a filter a reader may want more than one value from. That is a set, and sets are checkboxes.
- **Don't** rely on colour alone for any state — every state in this system has a second, non-chromatic cue.

## Amendments

This document records what ships. Where a later product decision overrode an
earlier rule, the rule is marked in place and the reasoning lives here, so a
reader can tell a deliberate override from drift.

### 2026-09-11 — two-up board, specialty chips, dark mode

**Requested by the user**, after living with the shipped redesign.

1. **Cards on the board.** *The Structural Void Rule* said "no rules, no boxes,
   no cards." The board now uses all three. The rule is amended rather than
   deleted: voids still divide the page, and the exemption is scoped to the job
   list. The user asked for chips-as-cards specifically for readability and
   supplied the pre-redesign board as the reference.

2. **The recency graticule is gone.** *The One Graticule Rule* is retired. It
   did not survive the halved column: a 38-character specialty chip, a two-line
   title and a plotted 7rem track could not share 400px without the card growing
   tall enough to defeat the point of going two-up. Recency survives as text.
   The half of the rule worth keeping — no per-record private scale — is
   restated as *The Per-Record Scale Ban* and is still binding.

3. **Uppercase labels were NOT reinstated.** The reference screenshot rendered
   its coordinate keys as `TYPE` / `LVL` / `SEEN`. *The Sentence-Case Label Rule*
   forbids it, that rule predates this change, and it was kept. This is the one
   place the new work deliberately departs from the reference.

4. **Dark mode.** No rule opposed it; the palette was already fully tokenised,
   which is why it cost seven variables rather than a sweep. The one structural
   consequence is *The Two-Setting Rule*: a colour now has to answer in two
   settings to be admissible at all.

**Verified at the time of the amendment:** 8 routes x 2 settings, 815 text nodes
measured for contrast, 0 AA failures, no horizontal overflow at 375px.

**A measurement trap worth repeating.** Tailwind v4 serialises computed colours
as `oklab(...)` and `color-mix(...)`. Regexing the numbers out of those strings
reads the L/a/b floats as RGB channels and reports confident nonsense — it
scored near-black for the header and produced 7 fabricated failures. The audit
paints each colour into a 1x1 canvas and reads the pixel back instead. Any
future contrast script must do the same.

### 2026-09-11 (later) — filters become sets, sort leaves the rail

**Requested by the user.** Four changes, one design consequence.

1. **Level is no longer an axis.** It is a checkbox set, because a reader open to
   senior *or* manager but not lead cannot express that as a position on a line.
   This leaves **one** axis slider on the board (salary), where the direction
   contract in `app.html` originally imagined filters as axis sliders generally.
   The contract is a historical record and is left as written; this document is
   the live one. What survives of the idea is the *readout*: every multi-select
   still answers back through an `aria-live` `.coord` line, so the board still
   reports its own coordinates.

2. **Job type is a checkbox set** for the same reason. It carries a warning the
   others do not need: 45% of listings have no `job_type` at all, so any
   selection hides them. The UI says so in place rather than letting a reader
   conclude the board is empty.

3. **Company is free text, not a select.** The dropdown only ever loaded 100 of
   722 verified companies, so 86% were unreachable. This needed a new `company`
   API filter — there was only `company_id` before.

4. **Sort moved out of the rail** to sit beside the result count, and is its own
   GET form. It therefore has to carry the active filters as hidden inputs, and
   the rail has to carry `sort` back, or each would clear the other.

**Salary ceiling removed** entirely; the floor axis remains.

**A layout bug this exposed, present since the redesign shipped:** the board's
two grid items had the default `min-width: auto`, so the nowrap coordinate
readout set the column's minimum and pushed the whole page wider than a phone
screen — `/jobs` had a horizontal scrollbar at 375px the whole time. Earlier
verification in this project reported "no horizontal overflow at 375px", and
that was wrong. The track is now `minmax(0,1fr)` with `min-w-0` on both items,
which is also what finally lets `truncate` on that line truncate.

**A third measurement trap.** Auditing contrast immediately after flipping
`data-theme` at runtime reported 52 failures that do not exist; the elements
were mid-transition. Measure after a real page load, not after a runtime flip.
