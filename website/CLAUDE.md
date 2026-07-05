# Cortex Landing Page — Brand & Build Guidelines

This folder is the **marketing website** for Cortex. It is a separate Vite app from
`../frontend/` (the product dashboard). Do not import code across the two.

## What Cortex Is

Cortex extracts tribal knowledge from company tools (Slack, GitHub, Discord, Jira,
file uploads), synthesizes it into structured executable workflows called **skills**,
and serves them via API so AI agents can execute company processes.

## Key Message (hero — use verbatim, updated 2026-07-05)

> The AI that knows how your company actually works.

Subheading:

> Cortex turns your team's knowledge into workflows your agents can run.

Never pair the name with a tagline (no "Cortex — Company Brain"). The wordmark is
just lowercase "cortex".

## Colors

| Token | Hex | Use |
|---|---|---|
| `bg` | `#06060B` | Page background (near-black) |
| `surface` | `#0E0E16` | Cards |
| `border` | `#1A1A28` | 1px card borders |
| `primary` | `#6C5CE7` | Electric purple — CTAs and highlights ONLY, use sparingly |
| `secondary` | `#00D2FF` | Cyan — accent for connections / data-flow |
| `text` | `#E8E8ED` | Primary text |
| `text-dim` | `#8888A0` | Secondary text |

Tokens are defined in `src/index.css` via Tailwind v4 `@theme` — use classes like
`bg-bg`, `bg-surface`, `border-border`, `text-text`, `text-text-dim`, `bg-primary`,
`text-secondary`.

**Never** use cream/beige/warm palettes or newspaper layouts.

## Typography

- Font: **Inter** (Google Fonts, loaded in `index.html`)

## Wordmark

- Inter, weight 500, `letter-spacing: -1.5px`
- Always lowercase `cortex` (never "Cortex" or "CORTEX" in lockups)
- White text on dark bg, with the final `x` in `#6C5CE7` purple
- Sizes: navbar 24px, hero 48–64px
- Use `src/components/Wordmark.jsx` — do not hand-roll the styling

## Logo — circuit pathways

Four circuit paths converging into a center node, inside a rounded-rect outline.
Purple (#6C5CE7) = the brain, cyan (#00D2FF) = the connections. Bottom paths/nodes
at reduced opacity (0.55 / 0.65).

Canonical geometry (36px grid): see `src/components/Logo.jsx` here, or
`../frontend/src/components/Logo.jsx` / `../docs/assets/logo.svg`. Reuse this
geometry — do not redraw the mark.

## Design Direction

Dark, minimal, premium dev-tool aesthetic (Linear meets Vercel — not a copy).
- Generous whitespace; content breathes
- Subtle radial purple glow behind hero only
- Cards: `#0E0E16`, 1px `#1A1A28` border, 12px radius; hover = faint purple border glow
- Scroll animations: fade-in on `useInView` (Framer Motion). Subtle, not flashy
- NO parallax, NO particles, NO 3D, no stock images
- Mobile responsive; page under 500KB excluding screenshots

## Tech

- Vite + React (single page, scroll-based — all sections composed in `App.jsx`)
- Tailwind CSS v4 via `@tailwindcss/vite` plugin (no tailwind.config.js)
- Framer Motion for the How It Works stepper and scroll reveals
- Components in `src/components/`

## Facts (keep accurate)

- 206 automated tests, 10 LLM failure modes handled, 32ms avg query response,
  454 documents → 28 skills extracted
- GitHub repo: https://github.com/agrawal-2005/Cortex
- Built by Prashant Agrawal
