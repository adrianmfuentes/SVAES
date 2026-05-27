---
version: beta
name: SVAES
description: >
  Automatic Software Delivery Verification System.
  A technical operations platform for software teams.
  The visual language is honest about what the system is:
  infrastructure tooling, not a consumer product. The interface
  looks like something engineers built for engineers, with
  deliberate craft applied to the parts that matter operationally.

colors:
  # Core
  ink: "#0D0F12"
  ink-secondary: "#1C2027"
  paper: "#F6F4F0"
  paper-secondary: "#EDEAE4"

  # Accent
  accent: "#E8D5A3"          # warm gold — primary interactive accent
  accent-dark: "#B8A06A"     # darker variant for hover states

  # Semantic — verdict states (immutable)
  verdict-valid: "#2A6B3C"
  verdict-valid-bg: "#E8F5EC"
  verdict-valid-border: "#A8D5B5"
  verdict-warning: "#8B5E00"
  verdict-warning-bg: "#FDF3DC"
  verdict-warning-border: "#DFC070"
  verdict-invalid: "#8B1A1A"
  verdict-invalid-bg: "#FAEAEA"
  verdict-invalid-border: "#D88080"
  verdict-unevaluated: "#5A5E65"
  verdict-unevaluated-bg: "#EBEBEB"
  verdict-unevaluated-border: "#C0C0C0"

  # Chrome
  border: "#D4CFC7"
  border-strong: "#9E9890"
  muted: "#7A7670"
  surface-raised: "#FFFFFF"
  overlay: "rgba(13, 15, 18, 0.55)"

typography:
  # Display — section titles, page headings
  display:
    fontFamily: "DM Serif Display"
    fontSize: 2.25rem
    fontWeight: 400          # the weight IS the regular cut — already authoritative
    lineHeight: 1.1
    letterSpacing: "-0.02em"

  # Heading — card titles, view labels
  h2:
    fontFamily: "DM Serif Display"
    fontSize: 1.5rem
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: "-0.01em"

  h3:
    fontFamily: "IBM Plex Sans"
    fontSize: 1rem
    fontWeight: 600
    lineHeight: 1.4

  # Body — operational content
  body-md:
    fontFamily: "IBM Plex Sans"
    fontSize: 0.9375rem      # 15px — between 14 and 16, feels more considered
    fontWeight: 400
    lineHeight: 1.65

  body-sm:
    fontFamily: "IBM Plex Sans"
    fontSize: 0.8125rem      # 13px
    fontWeight: 400
    lineHeight: 1.55

  # Labels — table headers, nav items, filter chips
  label:
    fontFamily: "IBM Plex Sans"
    fontSize: 0.6875rem      # 11px
    fontWeight: 600
    letterSpacing: "0.08em"
    textTransform: uppercase

  # Code — UUIDs, rule IDs (RV-*), commit refs, JSONB, log fragments
  mono:
    fontFamily: "IBM Plex Mono"
    fontSize: 0.8125rem
    fontWeight: 400
    lineHeight: 1.6

  mono-sm:
    fontFamily: "IBM Plex Mono"
    fontSize: 0.6875rem
    fontWeight: 400
    lineHeight: 1.5

spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  xxl: 64px

rounded:
  none: 0px
  sm: 2px
  md: 4px
  lg: 6px
  full: 9999px

# IBM Plex is the system of choice precisely because it ships
# a matched trio (Sans, Serif, Mono) designed by the same hand.
# DM Serif Display adds editorial weight to headings without
# colliding with the technical prose set in Plex.
# Using Inter here would be the obvious choice — avoided on purpose.

components:

  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    border: "1px solid {colors.ink}"
    rounded: "{rounded.md}"
    padding: "9px 18px"
    font: "{typography.label}"

  button-primary-hover:
    backgroundColor: "{colors.ink-secondary}"

  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    border: "1px solid {colors.border-strong}"
    rounded: "{rounded.md}"
    padding: "9px 18px"
    font: "{typography.label}"

  button-secondary-hover:
    backgroundColor: "{colors.paper-secondary}"

  button-accent:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.ink}"
    border: "1px solid {colors.accent-dark}"
    rounded: "{rounded.md}"
    padding: "9px 18px"
    font: "{typography.label}"

  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.verdict-invalid}"
    border: "1px solid {colors.verdict-invalid-border}"
    rounded: "{rounded.md}"
    padding: "9px 18px"
    font: "{typography.label}"

  badge-valid:
    backgroundColor: "{colors.verdict-valid-bg}"
    textColor: "{colors.verdict-valid}"
    border: "1px solid {colors.verdict-valid-border}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
    font: "{typography.label}"

  badge-warning:
    backgroundColor: "{colors.verdict-warning-bg}"
    textColor: "{colors.verdict-warning}"
    border: "1px solid {colors.verdict-warning-border}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
    font: "{typography.label}"

  badge-invalid:
    backgroundColor: "{colors.verdict-invalid-bg}"
    textColor: "{colors.verdict-invalid}"
    border: "1px solid {colors.verdict-invalid-border}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
    font: "{typography.label}"

  badge-unevaluated:
    backgroundColor: "{colors.verdict-unevaluated-bg}"
    textColor: "{colors.verdict-unevaluated}"
    border: "1px solid {colors.verdict-unevaluated-border}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
    font: "{typography.label}"

  card:
    backgroundColor: "{colors.surface-raised}"
    border: "1px solid {colors.border}"
    rounded: "{rounded.lg}"
    padding: "24px"
    boxShadow: "none"

  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    border: "1px solid {colors.border-strong}"
    rounded: "{rounded.md}"
    padding: "9px 12px"
    font: "{typography.body-md}"

  nav-item:
    textColor: "rgba(246, 244, 240, 0.55)"
    rounded: "{rounded.md}"
    padding: "7px 12px"

  nav-item-active:
    backgroundColor: "rgba(246, 244, 240, 0.10)"
    textColor: "{colors.paper}"
    borderLeft: "2px solid {colors.accent}"
---

## Overview

SVAES is tooling, not a product. The interface reflects that distinction at every
level: tight information density, no illustrations, no gradient backgrounds, no
decorative iconography serving marketing purposes. What you see on screen maps
directly to system state.

The central design question for every view is: **does the operator understand
what happened and what to do next, in under three seconds?** Every layout
decision follows from that constraint.

The visual identity is warm-industrial. A parchment-toned paper background
(`#F6F4F0`) replaces the cold white common in SaaS dashboards, reducing eye
fatigue during long sessions on dim monitors. DM Serif Display adds editorial
authority to headings without the stiffness of geometric sans-serif titles.
IBM Plex Sans and IBM Plex Mono carry all operational text — they share a
design DNA, so mixed-weight paragraphs with embedded code never look
typographically inconsistent.

The result should feel closer to a well-designed technical handbook than to
a cloud dashboard template.

---

## Color

The palette is deliberately **paper-and-ink**, not blue-and-white.

- **Ink (`#0D0F12`):** Near-black with a slight blue cast. Used for the sidebar
  background, primary buttons, and all text on light surfaces. Not pure black —
  pure black on warm paper looks harsh.

- **Paper (`#F6F4F0`):** Warm off-white. Application background. Softer than
  `#FFFFFF` on low-brightness screens; the warmth pairs with DM Serif Display
  without the cold tension that a neutral white creates.

- **Paper-secondary (`#EDEAE4`):** Hover states on light backgrounds, table
  row alternation, disabled input fields.

- **Accent (`#E8D5A3`):** Warm gold. Used sparingly: the active nav indicator,
  the primary CTA button on certain views, and the highlight state of the
  global verdict banner when the result is valid. One accent, used twice per
  screen maximum.

- **Border (`#D4CFC7`) / Border-strong (`#9E9890`):** Two border weights avoid
  the visual noise of a single border value applied everywhere. Card outlines use
  `border`; input fields and interactive containers use `border-strong`.

- **Muted (`#7A7670`):** Timestamps, secondary identifiers, help text. Warm
  grey, not cool grey — stays consistent with the paper background.

### Verdict Semantic Colors

Fixed. Never reassigned. Each uses a background, text, and border token so
components can use any combination without inventing new values.

| State | Text | Background | Border |
|---|---|---|---|
| VALID | `#2A6B3C` | `#E8F5EC` | `#A8D5B5` |
| WITH_WARNINGS | `#8B5E00` | `#FDF3DC` | `#DFC070` |
| INVALID | `#8B1A1A` | `#FAEAEA` | `#D88080` |
| NOT_EVALUATED | `#5A5E65` | `#EBEBEB` | `#C0C0C0` |

The desaturated, earthy versions of green/amber/red (vs. the saturated `#27AE60`
style common in SaaS) read as more credible in a technical context. A saturated
green next to monospace text feels like a notification; a muted forest green
feels like a status.

---

## Typography

Three fonts. One purpose each.

**DM Serif Display** is used only for page titles and card section headings. It is
a high-contrast, slightly condensed serif with ink-trap details visible at display
sizes — a choice that signals editorial craft rather than SaaS default. At `400`
weight the regular cut is already visually dominant; no bold variant needed or used.

**IBM Plex Sans** handles all operational text: labels, body copy, nav items,
table content, button text. It is a corporate grotesque with slightly wider
letterforms than Neue Haas or DIN, which improves readability in dense tables.
At `11px` uppercase with `0.08em` tracking it makes a clean table header without
needing a separate typeface.

**IBM Plex Mono** carries all technical identifiers: release UUIDs, rule names
(`RV-01`…`RV-10`), commit refs, JSONB values, log fragments. Using the Mono from
the same family as the Sans means mixed text (e.g., "Release `a3f2c1d` was
rejected by rule `RV-05`") does not produce typographic collisions in size,
weight, or vertical rhythm.

**Scale:**
- `2.25rem` / `DM Serif Display` — page title
- `1.5rem` / `DM Serif Display` — card section heading
- `1rem 600` / `IBM Plex Sans` — subheading, strong label
- `0.9375rem` / `IBM Plex Sans` — body text (15px, not 16 — intentional)
- `0.8125rem` / `IBM Plex Sans` — secondary text, table cells (13px)
- `0.6875rem 600 caps` / `IBM Plex Sans` — column headers, nav labels (11px)
- `0.8125rem` / `IBM Plex Mono` — inline code, identifiers
- `0.6875rem` / `IBM Plex Mono` — compact identifiers in tables

---

## Layout

The application is two-column:

**Sidebar (220px, fixed):** `ink` background. The narrower 220px (vs. the
industry-default 240-260px) is intentional — it slightly compresses the nav to
shift visual weight toward the content area. Navigation items use 11px uppercase
labels, not 14px normal-weight text. Active items get a 2px `accent` left
border, not a filled background pill.

**Content area:** `paper` background. Max-width `1120px`, centered, `40px`
horizontal padding. Not `1200px` — the 80px difference at 1280px screen width
produces a column that feels like it has breathing room rather than filling
the viewport edge-to-edge.

**Page structure within the content area:**
```
Page header (title + primary action)
────────────────────────────────────
Verdict banner (full width, prominent — only on release detail)
────────────────────────────────────
Content cards (1 or 2 columns depending on view)
```

The **verdict banner** on the release detail view is a horizontal band spanning
the full content width — 56px tall, left-bordered with a 4px verdict-colored
stripe, containing the badge, release ID in mono, and timestamp. It occupies
its own row before the card grid. It is never inside a card.

**Card grid:**
- Release detail: 1 column (verification is a linear read)
- Dashboard: 2×2 KPI cards + full-width chart card
- Connectors/Profiles: 1 column list with inline expand
- Admin: 2-column form layout

---

## Elevation

Flat. Two levels only.

- **Level 0:** `paper` background.
- **Level 1:** cards — `surface-raised` (`#FFFFFF`) with `1px solid border`.
  No `box-shadow` on cards. The contrast between `#FFFFFF` and `#F6F4F0` at
  that scale is enough separation. Shadow here would feel like a consumer product.

Modals: `surface-raised` card, `rounded.lg`, `overlay` backdrop. No drop shadow
on the modal itself — the backdrop provides sufficient separation.

---

## Shapes

Minimal rounding. This is tooling, not a consumer app.

- `2px` — badges, status chips, filter tags
- `4px` — buttons, inputs, tooltips, inline code blocks
- `6px` — cards, panels, modals
- `9999px` — the only pill shape allowed is the verdict badge in compact table
  rows where a rectangular badge would create visual noise in a tight column

No `border-radius: 12px` or higher anywhere. Generous rounding signals
approachability; this system should signal precision.

---

## Components

### Verdict Banner (release detail — primary component)

Full-width row above the card grid. Not a card. Specs:

```
height: 56px
background: {verdict-*-bg}
border-left: 4px solid {verdict-*} (the text color token)
border: 1px solid {verdict-*-border}
border-radius: 4px
padding: 0 24px
display: flex; align-items: center; gap: 12px
```

Left to right: icon (16px, SVG, same color as text token) → badge → release
ID in `mono` → separator → timestamp in `body-sm muted`. The verdict badge
inside the banner uses `rounded.sm`, not `rounded.full`.

### Verdict Badges

Used in tables, lists, and the banner. Always accompanied by an icon. The icon
and text share the same color token — never use a different color for the icon.

```
badge-valid      →  ✓  VALID
badge-warning    →  ⚠  WITH_WARNINGS
badge-invalid    →  ✕  INVALID
badge-unevaluated →  —  NOT_EVALUATED
```

The `_WITH_INCIDENTS` suffix renders as a separate `body-sm muted` text
immediately to the right of the badge, outside the badge container. Never
truncated, never inside the badge.

### Verification Rule Table

This table is the primary information delivery mechanism of the entire system.
It receives the most typographic care.

Column order and specs:
```
ID         | 80px  | mono-sm         | "RV-05"
Rule name  | flex  | body-sm         | "Artifact count"
Connector  | 140px | body-sm muted   | "GitLab"
Result     | 120px | badge component | INVALID
Evidence   | flex  | body-sm         | expandable on click
```

Row height: `44px` collapsed, unlimited expanded.
Row separator: `1px solid border` (not zebra stripes — zebra stripes look dated).
Hover state: `paper-secondary` background.
The evidence cell, when expanded, shows a `mono` preformatted block with
`paper` background and `border` outline — never a plain string.

### Inputs

Three states, no others:

```
Default:  border: 1px solid border-strong;  background: paper
Focus:    border: 1px solid ink;  background: white;  outline: 3px solid accent at 40% opacity
Error:    border: 1px solid verdict-invalid-border;  background: verdict-invalid-bg
```

Labels always use `label` typography (11px uppercase), positioned above the
input, not floating. Placeholder text is allowed as a format hint (e.g.,
`e.g. 2024-Q3`) but never as a substitute for the label.

### Loading States

Skeleton screens only. No spinners blocking the layout. Verification results
are asynchronous and may take 5-15 seconds — a spinner over a blank area forces
the user to wait without knowing what is coming. A skeleton preserves the
layout and communicates that content is loading into a specific region.

Skeleton color: `paper-secondary` animated with a left-to-right shimmer at
`1.6s linear infinite`.

### Navigation

Nav items in the sidebar are 36px tall, `body-sm` text, `label` font for the
section dividers. No icons unless they add disambiguation (avoid icon-only nav).
Active state: left 2px border in `accent`, background `rgba(paper, 0.10)`.
Hover state: background `rgba(paper, 0.06)`.

Section dividers between nav groups: `label` size, `muted` color, no separator
line — the uppercase label is enough visual separation.

---

## Do's

- Show the global verdict as a banner above all other content on the release
  detail view, before the card grid starts.
- Use `mono` for every technical identifier: UUIDs, rule IDs (RV-*), commit
  hashes, connector instance names, JSONB keys.
- Keep verdict semantic tokens consistent. The green for VALID must be the
  same green everywhere — in the banner, in the table badge, in the dashboard KPI.
- Use skeleton screens for any content that loads asynchronously.
- Use the `accent` gold sparingly. One or two uses per screen. More than that
  and it stops being an accent.
- Prefer `border-strong` for interactive components (inputs, buttons) and
  `border` for structural components (cards, dividers).

## Don'ts

- No gradient backgrounds anywhere. Not on the sidebar, not on cards, not on
  the hero area of the login screen.
- No purple. No blue gradient on white. No frosted glass. These are the visual
  signatures of AI-generated SaaS templates.
- Do not use `border-radius` above `6px` on any component.
- Do not use the `secondary` (valid green) for anything except the VALID
  verdict and explicit success confirmations.
- Do not use the `tertiary` (invalid red) for routine destructive actions like
  "Cancel" or "Go back." Reserve it for `button-danger` only: irreversible
  release-level actions ("Reject release," "Revoke API key").
- Do not truncate the evidence field of a failed rule. The evidence is the
  most important piece of data when a user is debugging an INVALID result. If
  the table column is too narrow, expand the row — never clip the text.
- Do not hide the `_WITH_INCIDENTS` suffix. It carries operational meaning.
- Do not use `box-shadow` on cards. The background contrast handles separation.
- Do not use `Inter`. The choice of IBM Plex is intentional; substitute with
  an equivalent grotesque (Suisse Int'l, Aktiv Grotesk) only if licensing
  requires it.