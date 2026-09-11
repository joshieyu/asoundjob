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

ASoundJob is laid out the way a foundry lays out a type specimen sheet: one family, one ink, enormous scale contrast, and nothing decorative between the reader and the data. The thesis is that filters are axis sliders that continuously remap the board, that the board reports its own coordinates back to you, and that hierarchy comes from scale contrast alone. The home page opens with the live job count set at `clamp(3rem, 9vw, 6rem)` in weight 300 against a near-white ground — a number, not a headline — and everything below it is a smaller reading of the same instrument. The page never decorates; it registers.

The family is Recursive Variable, loaded once, and its MONO axis carries the whole sans-to-mono relationship. Readouts are not a font swap to a second family; they are an axis move from `'MONO' 0` (body) to `'MONO' 1` (`.coord`, `.axis-label`). Only the `mono.css` slice ships (MONO 0–1, wght 300–1000, ~70 KB); the 297 KB `full.css` was rejected because the CASL, CRSV and slnt axes are unused. That single-family economy is why a board with 21 specialty categories can stay legible without a second voice.

Two disciplines were donated from directions that lost and both are binding. **One shared graticule:** every value on the board is measured against the same grid, never against its own private maximum — the recency tick on every job row plots the same 0–90 day scale, so two rows are directly comparable at a glance. **Structural voids:** division is done with deep gaps (40–80px), not with rules, boxes, cards, or panels. Where a hairline does appear it is a decorative register mark and carries no meaning. The confirmed visual anti-reference is the incumbent mixing-console world this replaced in full — panels, wells, latch buttons, bevel and recess shadows, LED meters, decorative monospace, and all-caps micro-labels are all rejected, not softened.

**Key Characteristics:**
- One typeface (Recursive Variable), one accent (#0033FF), zero secondary hues.
- Zero radius, zero shadow, zero cards — the page is flat paper with type on it.
- Hierarchy by scale contrast: an 8x jump from coordinate readout to specimen numeral.
- Recency, not salary, is the spine every row registers against.
- Deep structural voids divide; hairlines only decorate.
- Monospace is an axis move (`'MONO' 1`), reserved for live data and small labels.
- WCAG 2.1 AA is binding on every surface, admin included.

## Colors

A near-white paper ground, near-black ink, one grey for secondary text, and exactly one saturated foundry blue — the palette of a specimen sheet, not of an interface chrome kit.

### Primary
- **Foundry Blue** (`{colors.accent}`): The single accent. It is the caret colour, the focus-ring colour, the selection highlight, the link colour, the primary button fill, the checkbox `accent-color`, and the hover colour for interactive text. Measured 6.83:1 against the ground and 6.83:1 for ground-on-accent, so it is safe for both button fill and body-size link text. It is never used to classify — a community-submitted listing is the one place it labels anything, and it labels provenance, not category.
- **Inverted Foundry Blue** (`{colors.accent-inv}`): Exists for one reason. Foundry Blue on ink measures 2.70:1 and fails; this lighter cast measures 5.30:1. Use it only where accent sits on an ink-filled surface, never on the ground.

### Neutral
- **Paper Ground** (`{colors.ground}`): The page. Warm near-white, also the browser theme colour and the scrollbar track. The sticky header sits on it at 95% with a backdrop blur.
- **Tinted Paper** (`{colors.ground-tint}`): One half-step down from the ground. The only fill used for a hover wash on quiet buttons and for the inline notice block. It is a tonal shift, never a card.
- **Ink** (`{colors.ink}`): All primary text, the pressed/selected fill for toggles and the current pagination page, and the recency tick itself. 18.43:1 on ground.
- **Muted Ink** (`{colors.muted}`): Secondary text, placeholders, axis labels, inactive nav, and the resting underline of a field. 5.03:1 on ground — the lightest ink permitted to carry meaning.
- **Register Rule** (`{colors.rule}`): The hairline. Header and footer boundaries, row dividers, the recency track, the scrollbar thumb. 1.28:1 against the ground.

### Named Rules
**The Single Ink Rule.** One accent, no second hue, ever. Specialty, seniority, job type and status encode by position and scale, never by colour. This is what lets 21 categories coexist on one board without becoming badge soup. If a new surface needs to distinguish two things, move one of them or resize it — do not tint it.

**The Rule Rule.** `{colors.rule}` measures 1.28:1 against the ground, far under any legibility threshold, so it may never carry meaning. It is decorative register only: dividers, tracks, frames. Anything meaning-bearing — a value, a state, a plotted position — uses `{colors.muted}` (5.03:1) or `{colors.ink}` (18.43:1).

**The Inverted Accent Rule.** Foundry Blue is forbidden on ink (2.70:1). On any ink-filled surface the accent is `{colors.accent-inv}` (5.30:1) or it is not accent at all.

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

Vertical rhythm is a 4px base with a deliberately bimodal distribution. Inside a block, spacing is small and even (4/8/12/16/24px — `mt-1` through `mt-6` carry most of the page). Between blocks, spacing jumps straight to a structural void (40/64/80px — `mt-10`, `mt-16`, `mt-20`). There is almost nothing in between, and that gap in the scale *is* the division system: sections on the home page are separated by 80px of nothing, not by a rule or a container. Job rows breathe on 28px (`py-7`) and are separated by a single register hairline via `divide-y divide-rule`.

Two-column behaviour appears in exactly two places. The board is `lg:grid-cols-[17rem_1fr]` with a 24px gutter — a sticky filter rail at `lg:top-24` beside the results. Job rows are `grid-cols-[1fr_auto]`: content left, a fixed action cluster right. The coordinate row inside a job strip is itself a grid that grows a third column at `sm` (`minmax(0,9rem) minmax(0,6rem) minmax(0,1fr)`), so salary, level and type stay in the same vertical registers across every row on the board. The header collapses its nav to a `Menu` toggle below `md`; the footer is 1 → 2 → 4 columns across `sm` and `lg`.

One global normalization is load-bearing: `fieldset { min-inline-size: 0 }`. Browsers give `fieldset` an implicit min-content floor that ignores grid track sizing, which broke the filter rail out of its 17rem column. Keep it.

### Named Rules
**The Structural Void Rule.** Deep gaps divide. No rules, no boxes, no cards. A section boundary is 64–80px of ground; if a boundary needs more emphasis than that, it needs more space, not a border.

**The One Graticule Rule.** Every value is measured against the same grid, never its own private scale. Column positions in a job row are identical from row to row so the eye can read down a register, and the recency tick uses one board-wide 0–90 day domain. A component that rescales itself per record is not comparable and does not ship.

## Elevation & Depth

There are no shadows anywhere in this system. Grep confirms it: not one `box-shadow`, not one `shadow-*` utility, in any stylesheet or component. Depth is conveyed by three things only — the half-step tonal shift from Paper Ground to Tinted Paper on hover, the register hairline, and empty space. The sticky header's only depth cue is a 95%-opacity ground with a backdrop blur, which reads as paper sliding under paper rather than as a floating plane.

Motion is equally thin: a 120ms ease on `background-color`, `border-color` and `color` on buttons, and 120ms on `border-color` for fields. Nothing moves position, scales, or lifts. A full `prefers-reduced-motion: reduce` block clamps every animation and transition to 0.01ms and disables smooth scrolling.

### Named Rules
**The No-Shadow Rule.** This system has no shadow vocabulary and must not acquire one. Bevels, recesses, inner glows and hard offset shadows are the rejected console world; a raised or inset surface is not available in this world at any size. Depth comes from tone, hairline, and void.

## Shapes

Radius is 0 throughout. The token layer defines exactly one radius value, `--radius-none: 0`, and every component sets `border-radius: 0` explicitly — buttons, fields, the icon toggles, the accordion summary. There is no radius scale to choose from and none should be invented.

The form language is a paper-and-rule vocabulary. Borders are 1px and only ever do one of two jobs: a full 1px box around a button or an icon toggle, or a single 1px bottom edge under a field. Fields are underlines, not boxes — a stroke under the text, never a filled well with corners. Nothing is clipped, masked, or given a silhouette. The only recurring geometry beyond the rectangle is the recency tick: a 1px horizontal track with a 8px vertical hairline standing on it.

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
The literal form of the thesis: a filter that continuously remaps the board. A native `input[type=range]` stripped of its chrome down to the same two marks the recency tick uses — a 1px Muted Ink track and a 2px by 14px ink hairline as the thumb, square, no fill, no radius, no shadow. Hover and `:focus-visible` turn the thumb Foundry Blue; nothing grows or lifts. It is 24px tall so the pointer target stays comfortable while the ink stays 1px.

Two ship on the board rail: **Level** (a 0–5 integer index over entry/mid/senior/lead/manager) and **Minimum salary** (0–300,000 in 10,000 steps). Each is captioned by an `.axis-label` legend above and answers with a `.coord` readout below marked `aria-live="polite"` — the axis is set, the board reports back its new coordinate. The visible control carries a screen-reader-only `<label>` and an `aria-valuetext` that speaks the human value ("senior", "any level") rather than the raw index, and the Level axis ships a `<noscript>` `.field` select so the filter still works without JS. A slider is only correct for an ordered domain; unordered filters (specialty, country, company) stay as checkboxes and selects.

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

### Job Strip (signature)
A job listing as one register on the specimen sheet, not a card. No border, no fill, no radius: a `1fr auto` grid with 28px of vertical breathing room, separated from its neighbours by a single hairline. Title at Title size links to the detail page and goes Foundry Blue with an underline on hover, clamped to two lines. Company name in ink weight 600 sits inline with location and remote status at meta size in muted ink. Below that the coordinate row plots salary, level and type into fixed columns with screen-reader-only `<dt>` terms, so a sighted reader gets a graticule and a screen reader gets a definition list. Specialties are a middot-joined muted string — there are 21 of them, and under The Single Ink Rule none of them is a coloured badge. The right cluster is two 32px square transparent icon buttons (bookmark, report) whose borders appear only on hover, with the bookmark's pressed state carrying an ink fill and `aria-pressed`. Both SVGs are inline paths with real `aria-label`s.

### Recency Tick (signature)
The spine of the board. A 1px Register Rule track, 7rem wide, carrying one 8px ink hairline positioned by percentage: `days / maxDays` clamped to 0–100, with `maxDays` defaulting to 90 and passed identically to every row on a page. Recency, not salary, is the shared axis — 829 of 1,038 measured board rows carry no salary at all, so salary is a coordinate plotted where it exists and can never be the structure. The tick renders nothing when age is unknown rather than guessing a position. The track is decorative (Register Rule); the plotted mark is meaning-bearing and is therefore ink, per The Rule Rule.

### Admin (documented variation)
Admin shares the token layer exactly — same ground, same ink, same accent, same `.btn`, `.field`, `.axis-label`, same zero radius — and spends none of the specimen grammar. No axis sliders, no coordinate readouts on hero figures, no specimen-scale display type; admin stat figures top out at Title size in a `flex-col-reverse` pair with an axis label beneath. This is an explicit user decision and is correct, not drift. WCAG 2.1 AA remains binding here.

## Do's and Don'ts

### Do:
- **Do** set every surface in Recursive Variable and reach the mono voice through `font-variation-settings: 'MONO' 1`, never through a second family.
- **Do** divide sections with 64–80px structural voids and let the ground do the work.
- **Do** keep meaning-bearing values in `{colors.ink}` (18.43:1) or `{colors.muted}` (5.03:1), and keep `{colors.rule}` (1.28:1) purely decorative.
- **Do** plot every comparable value against one board-wide scale — the recency tick's 0–90 day domain is shared by every row on the page.
- **Do** encode state with shape as well as colour: dotted underline for invalid, dashed underline for disabled, strike-through for a disabled button label.
- **Do** use `{colors.accent-inv}` (5.30:1) whenever accent must sit on an ink-filled surface.
- **Do** keep `fieldset { min-inline-size: 0 }` in the base layer; without it the filter rail escapes its grid track.
- **Do** pair every axis slider with an `.axis-label` legend above and an `aria-live="polite"` `.coord` readout below, plus `aria-valuetext` speaking the human value.
- **Do** state hierarchy with scale: a coordinate readout and a specimen numeral are the two ends of a single ramp roughly 8x apart.

### Don't:
- **Don't** introduce a second hue. Specialty, seniority and status encode by position and scale, never by colour.
- **Don't** use `font-mono` or any Tailwind mono utility; it no longer maps to the brand family.
- **Don't** use monospace decoratively — `'MONO' 1` belongs to live data readouts and axis labels only.
- **Don't** uppercase `.axis-label`; the all-caps micro-label was a legibility and screen-reader failure and was removed on purpose.
- **Don't** add a radius. Every corner in this system is square and there is no radius scale to pick from.
- **Don't** add shadows of any kind — ambient, offset, bevel, recess, or inner glow. There is no shadow vocabulary here.
- **Don't** build cards, panels, wells, latch buttons, or LED-style meters; that is the rejected console world in full.
- **Don't** let a component scale itself against its own private maximum. The retired per-company meter did exactly that and made rows non-comparable.
- **Don't** make salary the structural spine of any board view; 80% of rows have none.
- **Don't** put an unordered set on an axis slider; a slider implies a rank, so specialty, country and company stay as checkboxes and selects.
- **Don't** give a slider a filled track, a round thumb, or a value bubble — the thumb is the same 1px ink hairline the recency tick uses.
- **Don't** rely on colour alone for any state — every state in this system has a second, non-chromatic cue.
