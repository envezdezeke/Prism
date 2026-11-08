---
phase: 02-pipeline-cockpit-ui-on-mock-data
plan: 01
subsystem: ui
tags: [react, vite, typescript, tailwind, shadcn, base-ui, zustand, tanstack-query, openapi-typescript]

requires:
  - phase: 01-contract-and-mock-api
    provides: mock API (MOCK=1) on :8000, prism/contract.py models, fixtures/
provides:
  - ui/ app (Vite 8, React 19, TypeScript 7) that builds, lints and tests clean
  - 02-UI-SPEC design tokens in src/index.css, restyled shadcn components (button, badge, table, tooltip, input, separator, scroll-area)
  - Tested pure sim-time derivation (timeview.ts) plus boardAt
  - Typed API client with URL-encoded folders and neutral error mapping; Vite proxy /api to :8000
  - Client-held sim clock (zustand), loaded once (D-21)
  - Pipeline board derived from stage_log at the clock time, with held badge, SLA percent, loading and error states
  - Repeatable smoke script (npm --prefix ui run smoke) that Phase 7 reuses
affects: [02-02, 02-03, 02-04, phase-07-live-switch]

actuals:
  tokens: 10871
  tasks: 2
  commits: 1
plan_head_before: 09207010d6faaa7283551d2d008a1b2fbbe3bbc5
plan_head_after: b12359b7f21c8764a9bcb291346d9e43f8407489

tech-stack:
  added: [react 19, vite 8, typescript 7, tailwindcss 4 + @tailwindcss/vite, shadcn CLI + @base-ui/react, lucide-react, cn, class-variance-authority, tw-animate-css, @tanstack/react-query, zustand, @fontsource-variable/geist, @fontsource-variable/source-serif-4, oxlint]
  patterns:
    - "Clock lives in the browser; every time-dependent view derived from timestamps in a pure module"
    - "timeview.ts and client.ts import nothing except relative .ts files, so Node can run them (tests, smoke)"
    - "Tokens only in components; Tailwind default palette, sizes and shadows reset so stray utilities cannot compile"
    - "Pure BoardView separated from the hook-driven Board so the view can be rendered with plain data"

key-files:
  created:
    - ui/package.json
    - ui/vite.config.ts
    - ui/src/index.css
    - ui/src/time/timeview.ts
    - ui/src/time/timeview.test.ts
    - ui/src/api/client.ts
    - ui/src/api/types.ts
    - ui/src/api/schema.ts
    - ui/src/state/clockStore.ts
    - ui/src/data/queries.ts
    - ui/src/lib/format.ts
    - ui/src/components/app/Board.tsx
    - ui/scripts/smoke.ts
    - ui/CLAUDE.md
  modified: []

key-decisions:
  - "openapi-typescript runs through npx with its own TypeScript 5, not as a local dependency (TS 7 has no JS compiler API)"
  - "UI-SPEC copy and tokens win over the plan where they differ (network error text, Retry button, four type sizes, no ink-3)"
  - "Badge variants are secondary, outline, hold, cleared, chip; there is no destructive variant, so red exists only through the hold tokens"
  - "PRISM_API (not a VITE_ variable) overrides the proxy target purely to exercise error states"

requirements-completed: [UI-01, UI-02]

duration: 8min
completed: 2026-11-08
status: complete
---

# Phase 2 Plan 01: Tracer slice Summary

**Vite/React cockpit with the 02-UI-SPEC tokens and a pipeline board derived client-side from stage_log at a browser-held sim clock, proven against the live mock API by a repeatable smoke script.**

## Task 1: package approval (checkpoint, cleared)

Jesse replied "Approve all" in the orchestrator session. All 15 flagged packages were approved, including `@fontsource-variable/source-serif-4`. The orchestrator verified each on npm: official repository organizations, weekly downloads from 1.2M to 630M. No install command ran before the approval. Packages dropped on purpose and not installed: sonner, next-themes, react-router, react-force-graph-2d, motion.

## Task 2: tracer slice (commit b12359b)

Scaffolded `ui/`, wrote the tokens, restyled seven shadcn components, ported the verified time module and tests, built the client, clock store, queries, formatters, board and smoke script.

### Results (mock API running on :8000)

- `npm --prefix ui run build`: exit 0, `built in 124ms`, no `error TS`, noUnusedLocals and noUnusedParameters on. 11 woff2 files bundled (Geist and Source Serif 4), no CDN.
- `npm --prefix ui test`: `tests 11 / pass 11 / fail 0` (9 reference tests plus 2 `boardAt` tests). Fixtures path is repo-relative.
- `npm --prefix ui run smoke`: `SMOKE OK deals=5 clock=2026-11-04T18:00-06:00`. With `SMOKE_BASE=http://localhost:9` it prints `SMOKE FAIL request failed: network` and exits 1.
- `npm --prefix ui run lint`: exit 0, two accepted react-refresh warnings (variant exports in button.tsx and badge.tsx).
- Dev proxy: `/api/clock` returned `{"now":"2026-11-04T18:00-06:00","start":"2026-11-02T08:00-06:00","end":"2026-11-06T18:00-06:00"}`; `/api/deals` returned a list of 5 (Lone Star Dental, Cedar Ridge Welding, Mama Rosa's Kitchen, Bayou Bistro & Grill, Juniper Creek Nursery). Encoded apostrophe and ampersand folder paths returned 200.
- Board at 2026-11-04 6:00 PM CT (real `BoardView` rendered server-side with live API data): Intake 3 (Bayou 44%, Juniper 75%, Cedar Ridge 75%), Credit 1 (Lone Star Dental 58%), Committee 1 (Mama Rosa's 113%), other columns 0. "Held: fraud review" on exactly 2 rows, hold tokens only. At the clock start: "No deals have arrived yet."
- Error states through the real client and proxy: dead backend (502) gives "The API is not reachable. Start the mock server on port 8000."; MOCK=0 (503) gives "The engine is not connected." Both render neutral.
- Greps: `1B2A41` and `FAF9F7` present once each; `^.dark` 0; `aa3bff` 0; no `baseUrl`; `getClock` only in client.ts, clockStore.ts, scripts/smoke.ts; `font-display` only on the App.tsx h1; no `dangerouslySetInnerHTML`; no raw hex outside index.css; no gradient, blur, glow, purple, indigo, violet, `toLocale`, `VITE_`, Goldman.
- Visual confirmation at 1440x900 is deferred to the plan 04 human-check: no Chrome or Playwright is installed on this machine.

## Deviations from Plan

1. **[Rule 3 - Blocking] openapi-typescript not a local dependency.** `npm install -D` failed with ERESOLVE (peer `typescript ^5`, template ships TS 7). Forcing it with `--legacy-peer-deps` installed but crashed at runtime (`ts.factory` undefined, since TS 7 has no JS compiler API). `api:types` now runs `npx --yes --package=openapi-typescript@7.13.0 --package=typescript@5 openapi-typescript ...`. Output is byte-identical to the RESEARCH scratch schema (989 lines). Both packages were already approved or OK in the audit. Noted in ui/CLAUDE.md.
2. **[Rule 3 - Blocking] `PRISM_API` override in vite.config.ts** (default `http://localhost:8000`, not a `VITE_` variable). It exists only so the stopped-API and MOCK=0 acceptance criteria could be tested without stopping the mock.
3. **tsconfig.node.json includes `scripts`**, so smoke.ts is type-checked by `tsc -b`.
4. **Board is tracer scope.** Name, amount, SLA percent, held badge, column counts, empty lines. No SLA bar, needed-by element or sort order yet (plan 02). SLA percent is rounded locally as `Math.round(roundPct(x) * 100)`; plan 02's `fmtPct` should replace it.
5. **UI-SPEC copy over plan copy.** Network error includes "Start the mock server on port 8000."; the error block has a neutral Retry button.
6. **[Rule 1 - Bug] timeview.ts interfaces relaxed.** `exited_at`, `decision`, `flagged_at`, `answer`, `answered_at` are optional (the plan allowed this), and the `!== null` guards became `!= null` so `undefined` cannot throw. Reference tests unchanged and passing.
7. **shadcn restyle.** Button has no destructive variant; Badge variants are secondary, outline, hold, cleared, chip. Tooltip is a light popover with the single `shadow-tooltip` token and no arrow. index.css resets Tailwind's default palette, sizes and shadows. Removed an unused React import in scroll-area.tsx (anticipated by the plan) and the `"use client"` directives.
8. **Template cleanup beyond the plan.** Also deleted ui/public/ (favicon.svg, icons.svg) and ui/README.md.

## Notes for plans 02 to 04

- **Plans 02 and 03 (clock):** `POST /api/clock/advance` with a `to` earlier than the mock's fixed `now` (11/04 6:00 PM) returns 422 (CONTRACT.md: it never rewinds). A scrub backward or "Go to" an earlier time will hit it. Follow UI-SPEC: keep the client time and show the neutral inline sync message.
- **Plan 04 audit grep:** "destructive only in the Held badge" currently finds no `destructive` use in components, since the Held badge uses the `hold` tokens. Adjust the grep to match.
- **Plan 04 audit grep:** `ui/src/components/ui/button.tsx` contains the word "destructive" in a comment ("There is no destructive variant"). A literal grep will flag it; reword the comment or exempt it.

## Known Stubs

None. The board renders only engine data. Retry and empty-state copy are real states, not placeholders.

## Threat Flags

None. No new endpoints, auth paths or file access beyond the plan's threat model. T-02-01 (text-only rendering), T-02-02 (no VITE_ variables, no data/ imports) and T-02-03 (describeError shows fixed text or the API detail string) are implemented and grep-checked.

## Self-Check: PASSED

Files verified present (ui/src/index.css, time/timeview.ts, api/client.ts, state/clockStore.ts, components/app/Board.tsx, scripts/smoke.ts, CLAUDE.md); commit b12359b verified as an ancestor of HEAD.
