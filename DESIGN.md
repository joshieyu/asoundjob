---
name: ASoundJob
description: Audio industry job board styled as a light mixing console
colors:
  panel: "#e9e7e1"
  panel-raised: "#f5f3ef"
  panel-recessed: "#dedcd4"
  ink: "#23262b"
  ink-soft: "#575b61"
  seam: "#c9c6bd"
  fader: "#d96c2c"
  fader-deep: "#a84e1c"
  lit: "#2f8f57"
  led-0: "#cdcdc6"
typography:
  display:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2.25rem, 5vw, 3.5rem)"
    fontWeight: 900
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.25
  body:
    fontFamily: "Archivo Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Spline Sans Mono Variable, ui-monospace, monospace"
    fontSize: "0.6875rem"
    fontWeight: 600
    letterSpacing: "0.14em"
    lineHeight: 1.4
  readout:
    fontFamily: "Spline Sans Mono Variable, ui-monospace, monospace"
    fontSize: "1.25rem"
    fontWeight: 600
    letterSpacing: "-0.01em"
rounded:
  sm: "2px"
  md: "6px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.fader}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "10px 20px"
  button-latch:
    backgroundColor: "{colors.panel-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "8px 14px"
  input-well:
    backgroundColor: "{colors.panel-recessed}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  card-panel:
    backgroundColor: "{colors.panel-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "16px"
---

# Design System: ASoundJob

## Overview

**Creative North Star: "The Session Console"**

ASoundJob's interface is a light mixing console: warm silver panels, recessed
wells for inputs, raised caps for controls, and one fader-cap orange that lights
up when something is live. The world is hardware-flat — bevels are single-pixel
top highlights, never gradients or gloss — because the reference object is a
brushed-light desk under studio daylight, not a skeuomorphic render. Every
scannable number (job counts, salaries, timestamps) sets in a tabular monospace
readout, the way meters and counters do on real gear. Density is calm: generous
panel padding, hairline seams, no decorative noise.

**Key Characteristics:**
- Light hardware world; dark appears only inside "display windows" (the hero
  readout), never as page themes
- One interactive hue (fader orange); state is shown by illumination, not hue
  proliferation
- Mono type carries data and machine labels; Archivo carries voice
- Depth = affordance: wells sink, caps rise

## Colors

A warm neutral hardware palette with a single saturated interactive accent and
one luminous signal green reserved for data.

### Primary
- **Fader Cap Orange** (#d96c2c): every primary action, active latch, active
  pagination state, and section legend tick. Hover deepens to Fader Deep
  (#a84e1c). If orange appears on a non-interactive element, the design is wrong.

### Tertiary
- **Signal Green** (#2f8f57): LED meters, the hero readout, success states only.
  It means "signal/live", never decoration.

### Neutral
- **Panel Silver** (#e9e7e1): page ground.
- **Raised Cap** (#f5f3ef): panels, buttons, cards at rest.
- **Recessed Well** (#dedcd4): inputs, meter bays, inset surfaces.
- **Hardware Ink** (#23262b): all primary text; also the hero display window.
- **Ink Soft** (#575b61): secondary text, mono labels (≥4.5:1 on all grounds).
- **Seam** (#c9c6bd): 1px hairline borders between panels and sections.
- **LED Off** (#cdcdc6): unlit meter segments.

### Named Rules
**The One Fader Rule.** Orange marks interaction and nothing else. On any
screen it covers well under 10% of pixels; its scarcity is what makes live
controls findable.

**The Readout Rule.** Any number a user scans — counts, salary, posted time —
sets in Spline Sans Mono with tabular figures. Body prose never uses mono.

## Typography

**Display/UI Font:** Archivo Variable (with system sans fallback)
**Readout/Label Font:** Spline Sans Mono Variable (with system mono fallback)

**Character:** A workhorse grotesk for voice, an instrument mono for data — the
pairing of a console's printed legends and its LED counters.

### Hierarchy
- **Display** (900, clamp(2.25rem–3.5rem), 1.05, -0.02em): page titles and the
  hero job count only.
- **Headline** (700, 1.25rem, 1.25): job titles in strips, panel headings.
- **Title** (700, 1rem): inline emphasis, footer column heads.
- **Body** (400, 0.9375rem, 1.6): descriptions and prose, max 65–75ch.
- **Label** (600, 0.6875rem, 0.14em, UPPERCASE): section legends, spec labels
  (SAL / TYPE / LVL), form field labels.
- **Readout** (600, tabular): counts, salaries, timestamps, filter result meters.

### Named Rules
**The Spec Block Rule.** Job metadata renders as labeled mono pairs
(`SAL $80k–$110k`), never as prose sentences — listings are read like channel
strip data, not paragraphs.

## Layout

Single centered column, max-width 6rem-short of 72rem (max-w-6xl), 16/24px gutters.
Two-zone layouts use a 17rem sticky sidebar (filter rack, job detail aside) with
the content field flexing beside it; below `lg` the sidebar stacks first and
unsticks. Sections separate by 40–48px vertical rhythm; panel internals use
16–24px padding. Meter segments and LED columns use a strict 2–3px gap rhythm —
the only place sub-4px gaps are allowed.

## Elevation & Depth

Depth is mechanical, not atmospheric: two inset shadow tokens do all the work.

### Shadow Vocabulary
- **Cap** (`--shadow-cap`: inset 0 1px 0 rgb(255 255 255 / 0.75), inset 0 -1px 0 rgb(35 38 43 / 0.08), 0 1px 2px rgb(35 38 43 / 0.08)): raised controls and panels at rest.
- **Recessed** (`--shadow-recessed`: inset 0 2px 4px rgb(35 38 43 / 0.12), inset 0 -1px 0 rgb(255 255 255 / 0.6)): inputs and meter bays.

### Named Rules
**The Recess Rule.** Things you type into sink; things you press rise. If a
control casts an inset shadow it reads broken; if an input casts a cap shadow it
reads unclickable.

## Shapes

Small radii only: 2px on controls, meter segments, and chips; 6px on panels and
wells. Borders are 1px Seam hairlines everywhere. No pill shapes, no large
radius cards — the world is machined rectangles.

## Components

### Buttons
- **Shape:** 2px radius, uppercase 0.875rem/600 with +0.05em tracking.
- **Primary:** Fader Cap Orange fill, white text, 10px 20px padding.
- **Latch (secondary):** raised cap with seam border; active state
  (`aria-pressed="true"` or `.is-on`) fills orange with inset shadow — the
  backlit-latch metaphor. Hover shifts border to Fader Deep.

### Chips
- **Style:** recessed background, seam border, mono 10px labels; category tags
  link to filtered views on detail pages.

### Cards / Containers
- **Corner Style:** 6px radius, 1px seam border.
- **Background:** raised cap; job strips add a recessed meter bay column at left
  when salary data exists.
- **Shadow Strategy:** cap shadow at rest, soft ambient lift on hover only.

### Inputs / Fields
- **Style:** recessed well, no visible stroke beyond the seam border.
- **Focus:** 2px Hardware Ink outline with 2px offset (global `:focus-visible`).

### Navigation
- Sticky 56px panel bar, hairline bottom seam; links are unlatched buttons that
  fill orange when `aria-current`; mobile collapses to a Menu latch + stacked list.

### LED Meter (signature)
12–16 stacked segments (2px gaps, 2px radius) filling bottom-up from a value/max
ratio; lit segments run Signal Green, top segments shift amber/red; unlit is LED
Off. Result-count meters sweep in with a staggered 40ms-per-segment animation
(disabled under `prefers-reduced-motion`).

## Do's and Don'ts

### Do:
- **Do** set every scannable number in Spline Sans Mono tabular figures.
- **Do** express selected/active state by filling the control orange (backlit
  latch), paired with `aria-pressed` or `aria-current`.
- **Do** keep dark values inside display windows (hero readout); pages stay light.

### Don't:
- **Don't** introduce a second interactive hue; orange is the only "live" color.
- **Don't** use gradients, glass, or gloss — bevels are 1px inset highlights.
- **Don't** stack a legend label above a large display heading; a legend is
  itself the section heading.
- **Don't** render meter/LED decoration without real data behind it.
