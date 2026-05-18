---
version: alpha
name: SVAES
description: >
  Automatic Software Delivery Verification System.
  Technical administration platform oriented toward software team
  operators and managers. The visual identity prioritizes clarity of the
  verification verdict over any other element on screen.
 
colors:
  primary: "#1E3A5F"
  on-primary: "#FFFFFF"
  secondary: "#2D6A4F"
  on-secondary: "#FFFFFF"
  tertiary: "#C0392B"
  on-tertiary: "#FFFFFF"
  neutral: "#F4F6F8"
  on-neutral: "#1A1A2E"
  surface: "#FFFFFF"
  on-surface: "#1A1A2E"
  border: "#D1D9E0"
  muted: "#6C757D"
  verdict-valid: "#2D6A4F"
  verdict-valid-bg: "#EAF5EE"
  verdict-warning: "#B8860B"
  verdict-warning-bg: "#FDF8E1"
  verdict-invalid: "#C0392B"
  verdict-invalid-bg: "#FDECEC"
  verdict-unevaluated: "#6C757D"
  verdict-unevaluated-bg: "#F0F0F0"

typography:
  h1:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: 700
    lineHeight: 1.2
  h2:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: 600
    lineHeight: 1.3
  h3:
    fontFamily: Inter
    fontSize: 1.125rem
    fontWeight: 600
    lineHeight: 1.4
  body-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.6
  body-sm:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.5
  label-caps:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: 600
    letterSpacing: 0.05em
  mono:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.6

rounded:
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px

spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: 10px 20px

  button-primary-hover:
    backgroundColor: "#16304F"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"

  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 10px 20px

  button-danger:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.md}"
    padding: 10px 20px

  badge-valid:
    backgroundColor: "{colors.verdict-valid-bg}"
    textColor: "{colors.verdict-valid}"
    rounded: "{rounded.full}"
    padding: 2px 10px

  badge-warning:
    backgroundColor: "{colors.verdict-warning-bg}"
    textColor: "{colors.verdict-warning}"
    rounded: "{rounded.full}"
    padding: 2px 10px

  badge-invalid:
    backgroundColor: "{colors.verdict-invalid-bg}"
    textColor: "{colors.verdict-invalid}"
    rounded: "{rounded.full}"
    padding: 2px 10px

  badge-unevaluated:
    backgroundColor: "{colors.verdict-unevaluated-bg}"
    textColor: "{colors.verdict-unevaluated}"
    rounded: "{rounded.full}"
    padding: 2px 10px

  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: 24px

  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    padding: 10px 14px

  nav-item-active:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"

  nav-item:
    backgroundColor: transparent
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
---

## Overview

SVAES is a work tool for technical teams, not a consumer
application. The design reflects this: functional, information-dense, without unnecessary
ornaments. The visual hierarchy serves a single question:
**is this release valid?**

The verification verdict is always the most prominent element on screen.
Everything else — navigation, filters, metadata — occupies a deliberately secondary plane.

The visual language is inspired by CI/CD tool dashboards and infrastructure
monitors: high contrast, legible typography on low DPI screens,
semantic colors with unambiguous meaning (green = valid, red = invalid, always).

## Colors

The palette combines an institutional navy blue with a confirmation green and an alert
red. The warm neutral (`#F4F6F8`) acts as the application background to
reduce visual fatigue in long sessions.

- **Primary (`#1E3A5F`):** Navy blue. Side navigation bar, primary
  buttons, section headers. Conveys reliability and institutionality.

- **Secondary (`#2D6A4F`):** Forest green. Used exclusively for the
  `VALID` verdict and success states. Must not be used for other purposes to preserve
  its semantic meaning.

- **Tertiary (`#C0392B`):** Signal red. Reserved for the `INVALID` verdict,
  connector errors, and destructive actions ("Reject release" button).

- **Neutral (`#F4F6F8`):** Application background and active sidebar menu.
  Softer than pure white for extended work environments.

- **Muted (`#6C757D`):** Secondary metadata, dates, identifiers, help text.
  Never for action text or primary operational content.

### Verdict Semantic Colors

The four verification states have fixed colors that cannot be reassigned
to other uses within the interface:

| State | Text Color | Background Color |
|---|---|---|
| VALID | `#2D6A4F` | `#EAF5EE` |
| WITH_WARNINGS | `#B8860B` | `#FDF8E1` |
| INVALID | `#C0392B` | `#FDECEC` |
| NOT_EVALUATED | `#6C757D` | `#F0F0F0` |

## Typography

**Inter** is used for the entire interface: a sans-serif font designed specifically
for screen readability at small sizes, with full Latin character support
(accents, tildes).

**JetBrains Mono** is used exclusively for technical identifiers: release
UUIDs, commit references, rule names (RV-01…RV-10), JSONB configuration
values, and log fragments. Never for generic interface text.

The typographic hierarchy in most views uses three levels: section title
(`h2`), element name (`h3`), and operational data (`body-md` / `body-sm`).
Table labels use `label-caps` to distinguish them from content without
resorting to bold.

## Layout

The application uses a two-column layout:

- **Fixed sidebar (240 px):** main navigation with `primary` background.
  Item text in `on-primary` at 60% opacity; active item with
  `neutral` background and `primary` text.

- **Main content area:** `neutral` background, central container of maximum
  `1200 px` with `spacing.xl` (32 px) padding.

Cards (`card`) are the main composition unit. A typical view
contains a header card with the global verdict and secondary cards
with rule-by-rule detail.

Forms use a two-column grid on screens ≥ 1024 px and a single column
on mobile. Maximum width for text fields: `480 px`.

## Elevation & Depth

The interface is deliberately flat. Only two elevation levels:

- **Level 0:** application background (`neutral`).
- **Level 1:** cards and panels (`surface`, `box-shadow: 0 1px 3px rgba(0,0,0,0.08)`).

Modals add an overlay `rgba(0,0,0,0.4)` over the content.
No pronounced shadows or additional depth effects are used.

## Shapes

- `rounded.sm` (4 px): badges, filter chips, status labels.
- `rounded.md` (8 px): buttons, inputs, tooltips.
- `rounded.lg` (12 px): cards, panels, modals.
- `rounded.full` (9999 px): verdict badges in compact mode.

## Components

### Verdict Badges

They are the most critical component of the interface. They always accompany an icon and
are never used without one:

- ✅ `badge-valid` → VALID
- ⚠️ `badge-warning` → WITH_WARNINGS
- ❌ `badge-invalid` → INVALID
- — `badge-unevaluated` → NOT_EVALUATED

The `_WITH_INCIDENTS` suffix is rendered as a secondary indicator in `body-sm`
`muted` color, adjacent to the main badge, never inside it.

### Verification Rule Table

Columns: identifier (`mono`), name (`body-md`), queried connector
(`body-sm`), result (badge), evidence (expandable text in `body-sm`).
The rule identifier always uses `mono` to facilitate visual search.

### Inputs and Forms

- Normal state: border `1px solid {colors.border}`.
- Focus state: border `2px solid {colors.primary}`.
- Error state: `{colors.tertiary}` border + message below in `body-sm` `tertiary` color.

There is always a visible label (`label-caps`) above the input.
Placeholders are not used as the only field indication.

Loading states use skeleton screens, not blocking spinners,
because verifications are asynchronous and may take several seconds.

## Do's and Don'ts

**Do:**
- Always show the global verdict at the top of the release detail
  view, before any other data.
- Use `mono` for all technical identifiers (UUIDs, RV-*, commits).
- Keep verdict semantic colors consistent throughout the application.
- Use skeleton screens for verification result loading states.

**Don't:**
- Do not reuse the `secondary` color (green) for anything other than the
  `VALID` verdict or explicit success states.
- Do not use the `tertiary` color (red) for routine destructive actions
  like "cancel" or "back"; only for irreversible actions on the release.
- Do not truncate the evidence field of a failed rule: it is the most important data
  when the user needs to debug an `INVALID` result.
- Do not hide the `_WITH_INCIDENTS` suffix for aesthetic reasons.
