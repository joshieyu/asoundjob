---
version: 1
slug: "src-routes-page-svelte"
primary_target: "src/routes/+page.svelte"
related_targets: []
---

# Surface brief: Homepage (/)

## Scope & mode
Persuade. First surface for everyone; seekers-first per PRODUCT.md.

## Audience, job, action
Audio professional arriving cold (often mobile): needs to grasp what makes this
board different within seconds, then either search or filter by their specialty.
Primary actions: search jobs, open specialty filter, browse featured listings,
submit a job (community loop).

## Proof/content
Real numbers only: live active-job count from API, real category counts feeding
the response-curve/meter visual, real featured listings (newest 6-8). No
testimonials or invented claims. WIP sections labeled plainly.

## Chosen direction
The Channel Strip (console world, LIGHT rendition): bright brushed-panel
hardware, deep charcoal hardware ink, single fader-cap orange carrying
interactive elements. Hero = master section: monumental live count readout
(tabular mono), search drawn as the master input, specialty categories as
backlit latching buttons that illuminate when active. Signature interaction:
filter/search changes animate a segmented LED result-count meter — the console
responds to input. Featured jobs rendered as channel strips (meter strip =
salary range, spec block = location/type/seniority, flag control persists via
localStorage).

## Constraints
Calm/trustworthy tone (no hype/gamification); WCAG 2.1 AA; mobile-first;
SSR via +page.server.ts against API_URL; Discord footer link conditional on
assets/discord_link.txt being non-empty; YAP logo placeholder in nav.

## Unresolved decisions
None binding; exact token values set during build in app.css @theme.
