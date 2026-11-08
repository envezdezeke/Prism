# Phase 2: Pipeline Cockpit UI on Mock Data - Research

**Researched:** 2026-11-07
**Domain:** React 19 + Vite 8 SPA over the Prism mock API (sim-clock time view, pipeline board, deal detail, inbox, alerts)
**Confidence:** HIGH on scaffold commands and API behavior (run locally against `MOCK=1`); HIGH on the time-view logic (9 fixture tests pass on Node 26); MEDIUM on palette hex values (Claude's discretion); LOW on anything that assumes the live engine (not in Phase 2).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (verbatim from 02-CONTEXT.md, Implementation Decisions)

- **D-01:** Accuracy and sturdiness over looks. The Goldman score is graded on the output file, so the UI must show the engine's data faithfully and never invent or reformat a value in a way that changes its meaning. Every screen handles loading, empty and error states.
- **D-02:** Jesse owns this phase and builds it with Claude Code. Keep the stack and structure simple enough for a non-developer to direct: no clever abstractions, no state libraries beyond what the stack research names.
- **D-03:** Clean, modern, institutional finance: the look of a bank's internal credit tool. A nod to Goldman Sachs, **not a copy**: do not use Goldman's sky blue (#7399C6), its logo, its fonts (Goldman Sans) or its name anywhere in the UI.
- **D-04:** Palette: warm off-white page background (e.g. #FAF9F7), white surfaces, a neutral warm-gray scale for text and borders, and **one** deep navy accent (e.g. #1B2A41) for primary actions, active nav and focus. No second accent color.
- **D-05:** Semantic color only for meaning: red **only** for fraud holds; amber only for SLA past 100% / deadline at risk; a muted green only for "cleared / approved". Nothing else is colored.
- **D-06:** Typography: a restrained serif for **page titles only** (e.g. Source Serif 4 or Newsreader), a clean sans for everything else (e.g. Inter or Geist). Tabular (fixed-width) numerals everywhere numbers appear. Money right-aligned in tables, formatted `$1,200,000`.
- **D-07:** Structure: hairline 1px borders instead of shadows; small corner radius (4-6px max); a 4px spacing grid; dense, aligned layouts; tables over card grids wherever data is compared.
- **D-08:** No gradients, glow, glassmorphism or blur. No drop shadows beyond a 1px hairline or the faintest elevation on popovers.
- **D-09:** No emoji anywhere. Icons from one line-icon set only (lucide), used sparingly and never decoratively.
- **D-10:** No purple/indigo/violet. No rainbow badge sets. No centered "hero" layouts or marketing copy. No large rounded "bubble" cards.
- **D-11:** No placeholder or filler text ("Lorem", "Coming soon", fake metrics). Every label uses real banking vocabulary (Intake, Credit, Committee, RM, SLA, needed-by).
- **D-12:** No default component-library look: restyle shadcn/Base UI defaults to the tokens above rather than shipping the stock theme.
- **D-13:** Times shown in sim time, Central: "Tue 11/03 3:05 PM CT"; durations as "26h 10m". Never the viewer's local time.
- **D-14:** Names, not ids, in the UI ("Aisha Grant", not `aisha.grant`); ids may appear in tooltips.
- **D-15:** Deal identity is the folder name plus the legal name; show the DBA when present.
- **D-16:** Fraud is shown soberly: a held deal gets a red "Held: fraud review" badge and its plain-words reason; a watch-tier deal gets a neutral "Watch" badge. No alarmist styling.

### Claude's Discretion
- Exact hex values within the palette above, spacing details, component choice within the stack, and layout of secondary panels, as long as D-03 to D-12 hold.

### Specific Ideas (CONTEXT.md)
- Reference feel: internal tooling of an investment bank or a modern credit platform: calm, precise, information-dense. "A credit officer would use this all day."
- Pipeline board: six stage columns (Intake to Closed) with compact rows showing legal name, amount, time in stage vs. SLA, needed-by badge, and hold/watch status.
- Deal detail: facts table with a source-document chip and confidence per fact; issues list; stage log with each "why"; human requests; alerts.
- Inbox: pending sign-off requests with the plain-words message and answer buttons limited to the request's allowed options.
- Copy follows `docs/MESSAGE_TEMPLATES.md`; the credit memo follows `docs/CREDIT_MEMO_TEMPLATE.md` (the contract has no `credit_memo` field yet, so no memo UI in this phase).

### Deferred Ideas (OUT OF SCOPE)
CONTEXT.md lists no separate deferred-ideas section. Its Phase Boundary puts these outside this phase: the fraud-graph hero view (UI-06), the red-team view (UI-07) and the live switch (Phase 7). Do not plan them here. `react-force-graph-2d` belongs to Phase 7 and should not be installed in Phase 2.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Clean, light fintech design system (type scale, tabular money numerals, red reserved for holds) | Design Tokens section (token block, contrast table, shadcn overrides); Scaffold section (the Vite template ships a purple accent and a dark theme to remove) |
| UI-02 | Pipeline board shows deals by stage with SLA timers and deadline badges | Time-view derivation (stageAt, slaPctAt); badge semantics in Contract Facts; verified fixture reproduction (5 of 5 SLA values) |
| UI-03 | Sim clock: current time, advance, replay from the start | Clock Architecture (advance with `to`, not `hours`); the mock clock is stateless (verified) |
| UI-04 | Deal detail: facts with source chips, issues, stage log, human requests, alerts | Join keys (inbox to requests, alerts feed to detail alerts); held-deal stage fallback; scrub policy for facts and issues |
| UI-05 | Human inbox lets whoever plays staff answer pending requests | Options come from `item.options` only; reply is not persisted by the mock, so a local overlay is required (verified) |
</phase_requirements>

## Summary

The phase is buildable as planned, but three mock-server behaviors change the design, and the planner must account for them. First, the clock is stateless in mock mode. `POST /api/clock/advance` with `hours` computes from `clock.json` on every call, and `GET /api/clock` always returns `2026-11-04T18:00-06:00` (verified with curl: advance by 1h returned 19:00, the next GET returned 18:00). Advancing with `to` (an absolute time) is the only form whose echo is correct, and the UI must own the clock in a store, never re-fetch it. Second, `/api/deals`, `/api/alerts` and `/api/inbox` ignore the clock entirely (verified: a 100-hour advance leaves every `sla_pct` unchanged). Success criterion 2 ("the board, alerts and inbox change to match the fixture state at that time") is therefore only achievable if the UI derives stage, SLA, inbox and alert visibility from timestamps already present in the fixtures. Third, the inbox reply stores nothing (verified: after replying to `inbox-001`, the pending list still returns it), so an in-memory overlay is required or the item reappears on the next refetch.

The derivation is well supported by the data. Every fixture value tested reproduces at the snapshot: stage, `stage_entered_at`, all five `sla_pct` values (including the freeze at the hold time for Bayou and Juniper), the inbox join keys, and the alert feed equal to the union of the detail alerts. I wrote the derivation as pure TypeScript and ran it under Node 26's built-in test runner against the real fixtures: 9 of 9 tests pass (see Code Examples).

The scaffold has several verified gotchas that change STACK.md's recipe. `create-vite` 9 now scaffolds Vite 8 with TypeScript 7 and `erasableSyntaxOnly`. `npx shadcn@latest init -d` forces the Next.js template, and `-p base-nova` is rejected; the working command is `init -t vite -b base -p nova -y`, which writes `"style": "base-nova"`. shadcn writes into a literal `./@/` folder unless the root `tsconfig.json` has `paths`. The template's `index.css` must be replaced with `@import "tailwindcss";` or init refuses to continue. With those fixed, `npm run build` passes with `noUnusedLocals` on, after one import is removed from `scroll-area.tsx`.

Several contract and content conflicts need a decision. The fixtures use five staff IDs that are not in the bank's directory (`credit.nakamura`, `committee.osei`, `fraudops.keller`, `mgr.ibarra`, `rm.alvarez`), so D-14 (names, not ids) cannot be satisfied from the data as shipped. The contract has no DBA field, so D-15's "show the DBA when present" cannot be satisfied. The fixture routes a $410,000 committee approval to `committee.osei`, while the rulebook routes amounts at or above $250,000 to `harold.benson`. D-01 (show error states) and D-05 (red only for fraud holds) also conflict on error banners unless errors are styled neutrally, which this research recommends.

**Primary recommendation:** Build a `ui/` app whose sim clock lives in a zustand store and advances with `POST /api/clock/advance {"to": ...}`. Derive every time-dependent view (stage, SLA, inbox, alerts) in a pure, tested module from fixture timestamps. Use server values as-is only where they carry no timestamp (names, amounts, facts), with a visible caveat. Restyle shadcn through tokens, not per-file edits.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sim clock state (now, start, end, playback) | Browser (zustand) | API (`/api/clock/advance` echo) | Mock clock is stateless; the browser must hold the authoritative value |
| Stage, SLA %, held state at time t | Browser (pure functions) | API (`stage_log`, `fraud.flagged_at` as inputs) | Mock lists are snapshots; derivation from timestamps is the only way to scrub |
| Inbox pending/answered at time t | Browser | API (`at`, `answered_at` inputs) | Same reason; overlay for answers made in the UI |
| Alerts visible at time t | Browser | API (`at` inputs) | Feed is a snapshot; filter by `at <= now` |
| Facts, issues, resolved issues, names, amounts | API (snapshot values) | Browser (display only) | Carry no timestamps; show engine values faithfully (D-01) |
| needed-by badge, SLA limit | API | Browser (display) | Server-computed (contract comment); not re-derived |
| Formatting (sim time, durations, money) | Browser | — | Fixed `-06:00` arithmetic; no viewer timezone (D-13) |
| Staff names | Browser (static map, if approved) or API (not in contract) | — | Directory is participant-only data; see Open Questions |
| Fonts and assets | Static bundle | — | Fontsource self-hosts Geist; no CDN dependency for a judged demo |

## Standard Stack

### Core

| Library | Version (registry, 2026-11-07) | Purpose | Why Standard | Legitimacy |
|---------|-------------------------------|---------|--------------|------------|
| react / react-dom | 19.3.1 | UI | Locked in STACK.md | SUS (too-new) |
| vite | 8.3.6 | Dev server, build, `/api` proxy | Template default; verified build | SUS (too-new) |
| @vitejs/plugin-react | 6.2.1 | React transform | Template default | SUS (too-new) |
| typescript | 7.0.2 | Typecheck (`tsc -b`) | Template default; `baseUrl` removed | OK |
| tailwindcss + @tailwindcss/vite | 4.3.5 | Styling (CSS-only config) | Locked in STACK.md | SUS (too-new) |
| shadcn (CLI, via npx) | 4.23.0 | Copies Base UI component source into `src/components/ui/` | Locked in STACK.md | SUS (too-new) |
| @base-ui/react | 1.9.0 | Primitives under shadcn `base-nova` | Installed by init | SUS (too-new) |
| lucide-react | 1.70.0 | The one icon set (D-09) | Installed by init | SUS (too-new) |
| cn | ^0.5.2 (pinned by shadcn) | Class merging; imported by every shadcn component | Official shadcn package (repo `shadcn-ui/cn`) | SUS (too-new) |
| class-variance-authority | 0.7.1 (installed) | Variants | Installed by init | OK |
| tw-animate-css | installed by init | Animation utilities used by shadcn | Installed by init | OK |
| @fontsource-variable/geist | 5.3.0 | Sans (D-06), self-hosted | Installed by init; woff2 bundled (verified) | OK |
| @tanstack/react-query | 5.107.1 | Fetch and cache; no clock in Query | Locked in STACK.md | SUS (too-new) |
| zustand | 5.1.0 | Sim clock and inbox overlay | Locked in STACK.md | SUS (too-new) |
| openapi-typescript (dev) | 7.13.0 | Generates `src/api/schema.ts` from `/openapi.json` | Verified generation | OK |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @fontsource-variable/source-serif-4 | 5.3.1 | Serif for page titles (D-06) | Only if the checkpoint clears; otherwise use the system serif stack (no install) |
| sonner + next-themes | 2.0.8 / 0.4.6 | Toasts | Recommended to omit (see Open Questions); both are pulled in only by the `sonner` shadcn component |
| oxlint | 1.92.0 (template) | Lint | Keep; `npm run lint` exits 0 with react-refresh warnings only |
| @types/react, @types/react-dom | 19.3.0 (template) | Types | Template default |
| @types/node | 24.19.2 (template) | Node types for `vite.config.ts` | Template default |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openapi-typescript types | Hand-written types | Hand-written types drift from the contract; generated types are the same cost to run once (recommended) |
| No router | react-router 8.5.1 (SUS, too-new) | Not named in STACK.md; D-02 forbids unnamed state or structure. Use a zustand `selectedFolder` plus an optional `location.hash` sync |
| Fontsource (self-hosted) | Google Fonts CDN | CDN fails on an offline judging laptop; Fontsource is bundled |
| Tiny own fetch wrapper | openapi-fetch 0.17.0 (OK) | Extra dependency for ~20 lines of code; not needed for D-02 |
| react-force-graph-2d | — | Phase 7 only; do not install now |

**Installation (Phase 2 only):**
```bash
# created by the scaffold (see Scaffold section): react, react-dom, vite, @vitejs/plugin-react, typescript, oxlint, @types/*
npm install -D tailwindcss @tailwindcss/vite
npx shadcn@latest init -t vite -b base -p nova -y     # adds @base-ui/react, class-variance-authority, cn, lucide-react, tw-animate-css, shadcn, @fontsource-variable/geist
npx shadcn@latest add card badge tabs table sheet scroll-area separator tooltip button input dialog -y
npm install @tanstack/react-query zustand
npm install -D openapi-typescript
```

**Version verification:** versions above were read from the npm registry on 2026-11-07 (`npm view <pkg> version`). Per the package-legitimacy protocol, only packages with a legitimacy verdict of OK earn a `[VERIFIED: npm registry]` tag. Every SUS package is tagged `[ASSUMED]` until the checkpoint in the audit below clears.

## Package Legitimacy Audit

> Run with `node ~/.claude/gsd-core/bin/gsd-tools.cjs query package-legitimacy check --ecosystem npm ...` on 2026-11-07.

| Package | Registry | Age (latest release) | Downloads (weekly) | Source Repo | Verdict | Disposition |
|---------|----------|----------------------|--------------------|-------------|---------|-------------|
| vite | npm | 2026-11-05 | 260.7M | github.com/vitejs/vite | SUS | Flagged: planner adds checkpoint:human-verify before install |
| @vitejs/plugin-react | npm | 2026-11-02 | 127.3M | github.com/vitejs/vite-plugin-react | SUS | Flagged: checkpoint |
| tailwindcss | npm | 2026-11-06 | 174.9M | github.com/tailwindlabs/tailwindcss | SUS | Flagged: checkpoint |
| @tailwindcss/vite | npm | 2026-11-06 | 59.5M | github.com/tailwindlabs/tailwindcss | SUS | Flagged: checkpoint |
| shadcn | npm | 2026-10-27 | 17.6M | github.com/shadcn-ui/ui | SUS | Flagged: checkpoint |
| @base-ui/react | npm | 2026-10-09 | 28.0M | github.com/mui/base-ui | SUS | Flagged: checkpoint |
| cn | npm | 2026-11-02 | 20.2M | github.com/shadcn-ui/cn | SUS | Flagged: checkpoint (pulled in by shadcn) |
| lucide-react | npm | 2026-11-06 | 129.9M | github.com/lucide-icons/lucide | SUS | Flagged: checkpoint |
| @tanstack/react-query | npm | 2026-11-06 | 83.4M | github.com/TanStack/query | SUS | Flagged: checkpoint |
| zustand | npm | 2026-11-06 | 91.8M | github.com/pmndrs/zustand | SUS | Flagged: checkpoint |
| react | npm | 2026-10-14 | 252.4M | github.com/react/react | SUS | Flagged: checkpoint |
| react-dom | npm | 2026-10-14 | 236.8M | github.com/react/react | SUS | Flagged: checkpoint |
| @types/node | npm | 2026-10-28 | 630.3M | DefinitelyTyped | SUS | Flagged: checkpoint |
| oxlint | npm | 2026-11-06 | 45.0M | github.com/oxc-project/oxc | SUS | Flagged: checkpoint |
| @fontsource-variable/source-serif-4 | npm | 2026-10-11 | 1.2M | github.com/fontsource/font-files | SUS | Flagged: checkpoint (only if serif is chosen) |
| typescript | npm | 2026-07-08 | 417.1M | github.com/microsoft/TypeScript | OK | Approved |
| @types/react | npm | 2026-09-09 | 226.1M | DefinitelyTyped | OK | Approved |
| @types/react-dom | npm | 2026-09-09 | 190.9M | DefinitelyTyped | OK | Approved |
| class-variance-authority | npm | 2024-11-26 | 80.5M | github.com/joe-bell/cva | OK | Approved |
| tw-animate-css | npm | 2025-09-24 | 47.2M | github.com/Wombosvideo/tw-animate-css | OK | Approved |
| @fontsource-variable/geist | npm | 2026-07-19 | 5.7M | github.com/fontsource/font-files | OK | Approved |
| openapi-typescript | npm | 2026-02-11 | 15.9M | github.com/openapi-ts/openapi-typescript | OK | Approved |
| sonner | npm | 2026-08-09 | 56.7M | github.com/emilkowalski/sonner | OK | Approved (optional) |
| next-themes | npm | 2025-03-11 | 33.8M | github.com/pacocoursey/next-themes | OK | Approved (only if sonner is kept) |
| react-router | npm | 2026-10-27 | 74.9M | github.com/remix-run/react-router | SUS | Not recommended for Phase 2 (not in stack) |
| react-force-graph-2d | npm | 2026-09-29 | 1.3M | github.com/vasturiano/react-force-graph | OK | Not in Phase 2 (Phase 7) |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** every SUS verdict above has the reason `too-new` only (the latest release is days old). No `postinstall` script was reported for any package. Each repository URL matches the project's official organization. The protocol still requires a `checkpoint:human-verify` before each install, so the planner should batch the flagged list into one checkpoint before the first `npm install`. Note that the first scaffold run printed `fsevents@2.3.3 (install: install scripts present)`; this is the optional macOS native module shipped with Vite and is expected.

*Packages discovered via WebSearch or training data that have not been verified against an authoritative source are tagged `[ASSUMED]`.* None were.

## Architecture Patterns

### System Architecture Diagram

```
  App start
     |
     +--> GET /api/clock (once) --------------------> clockStore {now, start, end}
     |                                                   |
     +--> GET /api/deals --------------------+           |
     +--> GET /api/deals/{folder} (per deal) +--> derive(now) ----> Pipeline board
     +--> GET /api/inbox ---------+          |   stageAt, slaPctAt   (6 columns, rows)
     +--> GET /api/alerts --------+          |   inboxAt, alertsAt --> Inbox, Alerts feed
                                  |          |                    --> Deal detail
                                  |          |
     Inbox answer button ----> POST /api/inbox/{id}/reply {option}
                                   |
                                   +--> answersStore overlay {id: {answer, answered_at = clock.now}}
                                        (applied inside derive(now); survives refetch)

     Clock bar: +1h / +6h / +1 day / next event / replay / scrub
        --> clockStore.now updates immediately (optimistic)
        --> POST /api/clock/advance {"to": "YYYY-MM-DDTHH:mm-06:00"}   (never "hours")
        --> POST /api/clock/replay {}  -> sets now = start, local playback timer
```

### Recommended Project Structure

```
ui/
├── index.html
├── vite.config.ts                 # react, tailwind, '@' alias, /api proxy
├── tsconfig.json                  # root: paths '@/*' (required by shadcn)
├── tsconfig.app.json              # paths '@/*'; no baseUrl
├── components.json                # style base-nova, iconLibrary lucide
└── src/
    ├── main.tsx
    ├── App.tsx                    # layout: top clock bar, left nav, content switch
    ├── index.css                  # tokens (Design Tokens section); no .dark block
    ├── api/
    │   ├── client.ts              # fetch wrapper; maps 404/409/422/503 to messages
    │   └── schema.ts              # GENERATED by openapi-typescript; do not edit
    ├── time/
    │   ├── simtime.ts             # simToMs, fmtSimTime, fmtDuration (fixed -06:00)
    │   ├── timeview.ts            # stageAt, slaPctAt, heldAt, inboxAt, alertsAt
    │   └── timeview.test.ts       # node --test (see Validation)
    ├── state/
    │   ├── clockStore.ts          # zustand: now, start, end, playing, speed
    │   └── answersStore.ts        # zustand: inbox overlay
    ├── data/
    │   └── queries.ts             # TanStack hooks: deals, details (useQueries), inbox, alerts
    ├── labels.ts                  # enum-to-plain-words maps (see Contract Facts)
    └── components/
        ├── ui/                    # shadcn output (restyled through tokens)
        └── app/                   # ClockBar, Board, DealDetail, Inbox, AlertsFeed, Badges, States
```

### Pattern 1: The clock owns time; the server only echoes it

**What:** `clockStore` holds `now`. Every change is applied locally first, then sent as an absolute target. The response is used only to confirm.
**Why:** The mock computes `now` from `clock.json` on each call, so `hours` drifts and GET returns the fixture value again. An absolute `to` produces the correct echo every time.

```ts
// Source: prism/api/app.py:63-72 (advance), 74-77 (replay); verified by curl 2026-11-07
await fetch('/api/clock/advance', {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ to: targetSimTime }),   // exactly one of hours/to; use to
});
await fetch('/api/clock/replay', {               // body "{}" also works; no body also works
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: '{}',
});
```

Clamp `targetSimTime` to `[start, end]` in the browser. The mock clamps the upper bound only (`now = min(now, end)`), and it accepts any `to`, including times before `start`.

### Pattern 2: Derive the time-dependent views from timestamps

**What:** `stageAt`, `slaPctAt`, `heldAt`, `inboxAt`, `alertsAt` are pure functions of `(detail, now)`. The board, inbox, alerts and detail all render from their output.
**Why:** Every time-dependent field in the fixtures has a timestamp (`stage_log[].entered_at`, `fraud.flagged_at`, `inbox.at`, `inbox.answered_at`, `alerts[].at`). Verified: derived values equal fixture values at the snapshot for every deal and item.

**Rules that the fixtures require:**
- **Arrival:** a deal is not visible before `stage_log[0].entered_at` (Mama Rosa's Kitchen arrives at `2026-11-02T08:30-06:00`).
- **Current stage:** the last `stage_log` entry whose `entered_at <= now`. Do not look for an entry with `exited_at == null`: a held deal (Bayou, Juniper) has no open entry, and its stage stays `Intake`.
- **SLA:** `(end - stage_entered_at) / sla_hours`, where `end = fraud.flagged_at` when `fraud.held` and `flagged_at <= now`, otherwise `now`. This reproduces the freeze (Bayou 0.4375, shown as 0.44).
- **Inbox:** visible when `at <= now`; answered only when `answered_at <= now`; the answer shows only at or after `answered_at`.
- **Alerts:** visible when `at <= now`; sorted newest first (the feed is newest first; detail alerts are oldest first).

### Pattern 3: Inbox answers are an overlay, not a server write

**What:** On a successful `POST /api/inbox/{id}/reply`, store `{answer, answered_at: clock.now}` in `answersStore`. `inboxAt` applies the overlay on top of the fetched item. Do not trust the response's `answered_at` for UI time, because the mock returns `clock.json`'s `now` (`app.py:119-120`).
**Why:** The mock does not store replies (verified). A refetch would bring `inbox-001` back as pending.
**Trade-off:** the overlay lives in memory, so a page reload restores the pending state in mock mode. Document this; it is acceptable for a mock.

### Pattern 4: Query policy

- All fetches use `staleTime: Infinity` and `refetchOnWindowFocus: false`, set once in the `QueryClient` defaults. Mock data does not change.
- The clock is never a Query. TanStack Query refetches on window focus by default, and `GET /api/clock` would snap the clock back to 18:00 on every tab switch.
- Load `GET /api/deals/{folder}` for each deal with `useQueries`. There is no bulk-detail endpoint, and the derivation needs each deal's `stage_log`.
- Live mode (Phase 7, not here) will want `refetchInterval`; add it behind a single constant then.

### Pattern 5: One view function feeds every screen

`viewAt(now, deals, details, inbox, alerts, answers)` returns the board columns, the inbox, the alerts feed and per-deal detail views. Screens never read raw fixtures. This keeps "the board changes when the clock moves" true by construction.

### Anti-Patterns to Avoid
- **`hours` in advance requests:** in mock mode it always returns `18:00 + hours` (verified: `hours: 1` then `GET` returned 18:00).
- **Polling `/api/clock`:** undoes every advance.
- **Trusting server `sla_pct` or `needed_by_badge` at a scrubbed time:** both are snapshot values at the fixture's `now` (contract.py:211, 213). They match at 18:00 and nowhere else.
- **`new Date("2026-11-03T15:05-06:00").toLocaleString()`:** formats in the viewer's timezone (D-13 forbids it). Use the fixed-offset arithmetic in the Code Examples.
- **Red for anything except fraud holds:** including error banners, toasts, `overdue` and `destructive` buttons (SC5 and D-05).
- **`dangerouslySetInnerHTML` for any engine string:** names, facts, messages and evidence come from documents and are untrusted (see Security).

## Scaffold (verified in a scratch project, 2026-11-07)

The reference scaffold built and linted on this Mac (Node v26.13.0, npm 11.20.0). It lives at `/private/tmp/claude-501/-Users-jes-Goldman-I/c14eddd9-8217-4cd4-a56b-9911e9a08267/scratchpad/scaffold-test/ui` and is outside the repo.

```bash
cd /Users/jes/Goldman-I
npm create vite@latest ui -- --template react-ts --no-interactive   # create-vite 9.3.4 -> Vite 8.3.6, TS 7.0.2, plugin-react 6.x, oxlint
cd ui && npm install
npm install -D tailwindcss @tailwindcss/vite
```

Then, in this order (each step was needed in the verified run):

1. **Root `tsconfig.json`** gets `compilerOptions.paths`. shadcn reads the root file, and without it writes to `./@/components/ui/`:
   ```json
   { "files": [], "compilerOptions": { "paths": { "@/*": ["./src/*"] } },
     "references": [ { "path": "./tsconfig.app.json" }, { "path": "./tsconfig.node.json" } ] }
   ```
2. **`tsconfig.app.json`** gets `"paths": { "@/*": ["./src/*"] }`. Do not add `baseUrl`; TS7 rejects it (TS5102).
3. **`vite.config.ts`**: plugins `react()` and `tailwindcss()`; alias `'@'` via `fileURLToPath(new URL('./src', import.meta.url))`; `server.proxy: { '/api': 'http://localhost:8000' }`. Vite's `preview.proxy` defaults to `server.proxy`, so the judged `vite preview` build keeps the proxy (CITED: vite.dev/config/preview-options).
4. **`src/index.css`** is replaced with `@import "tailwindcss";` as its first line. Without it, shadcn init stops with "No Tailwind CSS configuration found".
5. **Delete the template art and CSS:** `src/App.css`, `src/assets/*`, and the template `App.tsx` content (it imports `App.css`, so the build fails if the file is removed alone).
6. **Init shadcn:**
   ```bash
   npx shadcn@latest init -t vite -b base -p nova -y
   ```
   Do not use `-d`: its defaults are `--template=next --preset=base-nova`. Do not use `-p base-nova`: the CLI rejects it with `Invalid preset: base-nova. Available presets: nova, vega, maia, lyra, mira, luma, sera, rhea`. `-p nova` writes `"style": "base-nova"` into `components.json`.
7. **Add components:**
   ```bash
   npx shadcn@latest add card badge tabs table sheet scroll-area separator tooltip button input dialog -y
   ```
   Omit `sonner` unless toasts are approved (it adds `next-themes`).
8. **Fix the unused React import** in `src/components/ui/scroll-area.tsx` (delete `import * as React from "react"`). Under `noUnusedLocals: true` (template default) it raises `TS6133: 'React' is declared but its value is never read.` Keep `noUnusedLocals` on. This is the fix that passed the build.
9. **Generate types** with the mock running (`MOCK=1 .venv/bin/python -m uvicorn prism.api.app:app --port 8000`):
   ```bash
   npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.ts
   ```
   Verified: generates 989 lines; `Stage`, `RequestType`, `needed_by_badge` and `status` become string-literal unions; the project typechecks with the generated types imported.

**Verified results:** `npm run build` (`tsc -b && vite build`) passes after step 8 and emits the Geist woff2 files into `dist/`. `npm run lint` exits 0 with react-refresh warnings from shadcn's variant exports (`badge.tsx`, `button.tsx`, `tabs.tsx`). The proxy works end to end: `GET http://localhost:5173/api/clock` and a `POST` to `/api/clock/advance` through Vite both reach the mock. An encoded folder name returns 200: `/api/deals/Mama%20Rosa%27s%20Kitchen` and `/api/deals/Bayou%20Bistro%20%26%20Grill`.

**TS7 and template constraints the code must respect** (from the generated `tsconfig.app.json`): `verbatimModuleSyntax: true` (use `import type` for types), `erasableSyntaxOnly: true` (no `enum`, `namespace`, or constructor parameter properties), `noUnusedLocals: true`, `noUnusedParameters: true`.

## Design Tokens: the "Institutional" look

Restyle by overriding tokens, not by editing shadcn components. The nova defaults that must change: `--primary` is near-black (oklch 0.205, not navy); `--radius` is 0.625rem (10px), so `rounded-xl` cards are 14px; `.dark` contains a violet sidebar primary (`oklch(0.488 0.243 264.376)`, hue 264, which D-10 forbids); and the template CSS has a purple accent (`--accent: #aa3bff`). Delete the `.dark` block and the template CSS.

**Proposed `src/index.css` (values are Claude's discretion; contrast is computed):**

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";
@import "@fontsource-variable/geist";

@custom-variant dark (&:is(.dark *));   /* kept for shadcn; no dark theme is shipped */

:root {
  --background: #FAF9F7;          /* page: warm off-white (D-04) */
  --foreground: #1C1917;          /* ink: stone-900 */
  --card: #FFFFFF;  --card-foreground: #1C1917;
  --popover: #FFFFFF;  --popover-foreground: #1C1917;
  --primary: #1B2A41;             /* the one navy accent: buttons, active nav, focus (D-04) */
  --primary-foreground: #FFFFFF;
  --secondary: #F5F5F4;  --secondary-foreground: #1C1917;
  --muted: #F5F5F4;  --muted-foreground: #57534E;     /* stone-600 */
  --accent: #F5F5F4;  --accent-foreground: #1C1917;  /* hover fill only, neutral */
  --destructive: #B42318;         /* used ONLY for fraud-hold badge (D-05) */
  --border: #E7E5E4;              /* stone-200 hairline */
  --input: #78716C;               /* stone-500: input boundary needs 3:1 (WCAG 1.4.11) */
  --ring: #1B2A41;
  --sla: #B54708;  --sla-bg: #FFFAEB;       /* amber: SLA past 100%, deadline at risk only */
  --cleared: #067647;  --cleared-bg: #ECFDF3; /* muted green: cleared / approved only */
  --hold-bg: #FEF3F2;                         /* tint behind the red hold badge */
  --radius: 0.375rem;             /* 6px maximum (D-07) */
  --shadow-sm: none;
  --shadow-lg: 0 4px 12px rgb(28 25 23 / 0.06);   /* faintest popover elevation only (D-08) */
}

@theme inline {
  --font-sans: 'Geist Variable', ui-sans-serif, system-ui, sans-serif;
  --font-heading: var(--font-sans);                 /* card and dialog titles stay sans */
  --font-serif: 'Source Serif 4 Variable', ui-serif, Georgia, serif;  /* page H1 only */
  --color-sla: var(--sla);  --color-sla-bg: var(--sla-bg);
  --color-cleared: var(--cleared);  --color-cleared-bg: var(--cleared-bg);
  --color-hold-bg: var(--hold-bg);
  --radius-sm: 0.25rem;  --radius-md: 0.25rem;  --radius-lg: var(--radius);
  --radius-xl: var(--radius);  --radius-2xl: var(--radius);  --radius-3xl: var(--radius);  --radius-4xl: var(--radius);
  --text-xs: 0.75rem;  --text-sm: 0.8125rem;  --text-base: 0.875rem;   /* one scale: 12/13/14 body */
  --text-lg: 1rem;  --text-xl: 1.25rem;  --text-title: 1.75rem;       /* 16/20/28; titles serif */
}
```

Then delete the generated `.dark` block (it is replaced by the `:root` values above) and remove the `dark:` variants only if they cause any visible effect (they do not while `.dark` is absent).

**Contrast (computed WCAG ratios, 2026-11-07):**

| Pair | Ratio | Result |
|------|-------|--------|
| Ink `#1C1917` on page `#FAF9F7` | 16.62:1 | AA pass |
| Muted `#57534E` on page | 7.25:1 | AA pass |
| Navy `#1B2A41` background, white text | 14.44:1 | AA pass |
| Hold red `#B42318` on white | 6.57:1 | AA pass |
| SLA amber `#B54708` on white | 5.43:1 | AA pass |
| SLA amber on `#FFFAEB` | 5.20:1 | AA pass |
| Cleared green `#067647` on `#ECFDF3` | 5.40:1 | AA pass |
| Input border `#78716C` on white | 4.80:1 | passes 3:1 (non-text) |
| Input border `#A8A29E` on white | 2.52:1 | fails 3:1; do not use for inputs |
| Hairline `#E7E5E4` on white | 1.49:1 | decorative only (dividers, not controls) |

**Font decision:** Geist (sans) is already installed by `shadcn init` and works offline. For the serif, `@fontsource-variable/source-serif-4` is the choice closest to D-06, but it carries a SUS verdict. The system stack `ui-serif, Georgia` needs no install and is the fallback.

**Tabular numerals:** Tailwind v4's `tabular-nums` utility generates `font-variant-numeric: tabular-nums` (CITED: tailwindcss.com/docs/font-variant-numeric). Apply it to every money, percent, count and time cell. Whether Geist provides `tnum` glyphs was not verified (no font tools on this machine); see Assumptions A1.

**Shadcn components that need token-level attention:**
- `Card` uses `rounded-xl` and `ring-1 ring-foreground/10`. The radius token fixes the corners; the ring works as a hairline.
- `Badge` `destructive` variant is `bg-destructive/10 text-destructive`. Use it only for fraud holds. Use `outline` for Watch and `secondary` for neutral stage chips. Add small custom variants for `sla` and `cleared`.
- `Tabs` uses `shadow-sm` on the active tab; `--shadow-sm: none` removes it.
- `Sheet` uses `shadow-lg`; the faint token above is the only elevation allowed.
- `Button` default is `bg-primary`, which becomes navy. Keep secondary buttons outline-style; use no red buttons, including for "Confirm hold".

## Contract and Fixture Facts the UI Must Handle

Quoted values are verbatim from the source files read this session. Line numbers are from `cat -n` / `grep -n`.

| Fact | Source | UI rule |
|------|--------|---------|
| Stage enum: `Literal["Intake", "Credit", "Committee", "Product", "Committed", "Closed"]` | [VERIFIED: prism/contract.py:23] | Six board columns in this order |
| `sla_pct` comment: `# may exceed 1 for a stuck deal; freezes while held` | [VERIFIED: prism/contract.py:211] | Show values above 100% in amber; freeze while held |
| `needed_by_badge: Literal["none", "ok", "at_risk", "overdue"]  # server-computed` | [VERIFIED: prism/contract.py:213] | Values as given; see badge mapping below |
| `watch: bool  # UI-only, never in the submission` | [VERIFIED: prism/contract.py:216] | Neutral "Watch" badge; no timestamp exists, so show it as-is |
| `Fact.confidence: float = Field(ge=0, le=1)` | [VERIFIED: prism/contract.py:190] | Show as a whole percent; never color it |
| `Fact.value: Union[str, int, float]`; `source_doc: str` | [VERIFIED: prism/contract.py:188-189] | Format by field (money, months, enum label); `source_doc` is the chip text |
| `Fraud.reason`, `stage_at_flag`, `flagged_at`, `linked_deals` | [VERIFIED: prism/contract.py:152-158] | Held panel: reason, stage at flag, time; linked deals as links when present |
| `DealDetail.resolved_issues` separate from `issues` | [VERIFIED: prism/contract.py:225-226] | Show open and resolved lists separately (J14) |
| `ISSUE_RE` grammar: `MISSING_DOC|MISSING_PAGE:<doc>`, `MISMATCH:<field>`, `OLD_TRICK:<code>` | [VERIFIED: prism/contract.py:43-50] | Plain-words label map; unknown string falls back to the raw code |
| `RequestType` (7 values, e.g. `"credit_decision"`, `"fraud_hold"`, `"info_request"`) | [VERIFIED: prism/contract.py:30-38] | Plain-words label per type (below) |
| `FAMILY_LABELS` F1 "shared rare entity" ... F6 "terms shape" | [VERIFIED: prism/contract.py:301-308] | Not needed in Phase 2 (graph is Phase 7) |
| Inbox options: `["approve", "decline", "request_info"]` (credit), `["approve", "decline"]` (committee), `["confirm_hold", "release_hold"]` (fraud) | [VERIFIED: fixtures/inbox.json:9-13, 25-27, 40-43, 55-58] | Buttons come from `options`; labels are a display map only |
| `InboxReply: option: str; note: Optional[str]` with `extra="forbid"` | [VERIFIED: prism/contract.py:282-285] | Send `{"option": "<one of options>"}`; never extra keys |
| Clock fields `now`, `start`, `end` | [VERIFIED: fixtures/clock.json] | `now` = 2026-11-04T18:00-06:00, `start` = 2026-11-02T08:00-06:00, `end` = 2026-11-06T18:00-06:00 |
| Deal summary equals deal detail for all five deals (`legal_name`, `stage`, `sla_pct`, `held`, `watch`, etc.) | [VERIFIED: local comparison of fixtures/deals.json vs fixtures/deal_detail.json] | Either source is safe for summary fields |
| Held deals stay in `Intake`; last `stage_log` entry has `exited_at` and `decision: "held"` | [VERIFIED: fixtures/deal_detail.json, Bayou and Juniper `stage_log`] | Current stage = last entry with `entered_at <= now` |
| Inbox join key: `(deal, type, at)` matches `human_requests` for all five items | [VERIFIED: local join on fixtures] | Link inbox items to the detail's request rows |
| Alert feed equals the union of detail alerts (3 alerts; ids alert-001..003) | [VERIFIED: local comparison] | Feed newest first; dedupe key is `id` |
| Staff IDs in fixtures not in the directory: `credit.nakamura`, `committee.osei`, `fraudops.keller`, `mgr.ibarra`, `rm.alvarez`, `borrower` | [VERIFIED: data/participant/contacts/teams.json vs fixtures; the directory has 16 people, e.g. `"id": "victor.hale"` at line 162] | No name resolution for these; see Open Questions |
| Rulebook fraud owner is `victor.hale`, backup `monica.salas` | [VERIFIED: data/participant/rules/stages.json:98-99; teams.json:162, 174] | Fixture uses `fraudops.keller`; flag to Zeke |
| Rulebook committee routing: `delegated_max_amount: 249999.99`, chair at or above $250,000 | [VERIFIED: data/participant/rules/stages.json:49-52] | Fixture routes $410,000 to `committee.osei`; flag to Zeke |
| Stage limits: Intake 8, Credit 48, Committee 48 (24 delegated), Product 16, Committed 48, Closed 24 | [VERIFIED: data/participant/rules/stages.json "sla_hours" at lines 13, 29, 48, 65, 74, 85] | Fixture `sla_hours` matches (8, 48, 48, 8, 8) |
| House style: times `Tue 11/03 3:05 PM CT`, durations `26h 10m`, money `$248,000`, DBA in borrower text | [VERIFIED: docs/MESSAGE_TEMPLATES.md:10-12] | Matches D-13; DBA not available (see below) |
| Mock `GET /api/clock` ignores advances | [VERIFIED: curl, 2026-11-07; app.py:65-72, 74-77] | Use `to`; own the clock |
| Mock reply returns `answered_at` from `clock.json` | [VERIFIED: app.py:119-120; curl response `2026-11-04T18:00-06:00`] | Overlay with UI `now` |
| Unknown folder returns 404 `unknown deal`; bad option returns 422 with a message string; answered item returns 409 | [VERIFIED: app.py:88, 111-118; curl: 404 and 422 observed] | Map to inline messages; display the `detail` string |
| 503 `engine not wired yet` on every `/api` route when `MOCK=0` | [VERIFIED: app.py:43-45, 56] | Error state: "The engine is not connected." |
| Folder names contain `'`, `&` and spaces | [VERIFIED: fixtures/deal_detail.json keys] | `encodeURIComponent(folder)` in every path; verified 200 with `%27` and `%26` |
| Fixtures contain 5 deals; ROADMAP success criterion 1 says 13 | [VERIFIED: fixtures/deals.json] | Render any count; never hard-code 5 or 13 |

**Badge mapping (no source defines thresholds; the server owns the value):**

| Value | Display | Color (D-05) |
|-------|---------|--------------|
| `none` | no badge; needed-by date shown as "No date" only if the field is present | none |
| `ok` | neutral outline "Needed by {date}" | none (not green; green is for cleared) |
| `at_risk` | "At risk" | amber |
| `overdue` | "Overdue" | amber (never red, which is reserved for holds) |

**Plain-words labels (UI-only maps; the wire value never changes):**
- Request types: `credit_decision` = "Credit decision"; `committee_approval` = "Committee approval"; `commitment_signoff` = "Commitment sign-off"; `funding_release` = "Funding release"; `fraud_hold` = "Fraud hold"; `fraud_release` = "Fraud release"; `info_request` = "Borrower information request" (role "Borrower").
- Options: `approve` = "Approve"; `decline` = "Decline"; `request_info` = "Request more information"; `confirm_hold` = "Confirm hold"; `release_hold` = "Release hold".
- Recipient display (until names are approved): role from request type, with the id as a tooltip. `credit_decision` = "Credit officer"; `committee_approval` = "Committee approver"; `commitment_signoff` = "Relationship manager"; `funding_release` = "Closing and funding"; `fraud_hold` and `fraud_release` = "Fraud Operations"; `info_request` = "Borrower". Alerts have no request type; show the raw `to` id in a tooltip with "Escalation" or "Alert" as the label.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Server state and caching | Hand-rolled `useEffect` fetch and cache | TanStack Query (`useQuery`, `useQueries`) | Handles loading, error and caching; D-01 needs these states on every screen |
| API types | Hand-written interfaces | `openapi-typescript` output (`src/api/schema.ts`) | Drift-proof against the contract; the change rule requires regenerating anyway |
| Time zone conversion | `Date` plus `toLocaleString` | Fixed `-06:00` arithmetic (`simToMs`) | Sim times are wall-clock Central with a fixed offset; the viewer's zone must never leak in (D-13) |
| Money formatting | String concatenation | `Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2, minimumFractionDigits: 0 })` | Exact `$1,200,000` output; `en-US` pinned |
| Modal and sheet primitives | Custom overlays | shadcn `Dialog` / `Sheet` on Base UI | Focus trapping and keyboard support are not worth re-building |
| Icons | Emoji or SVGs by hand | `lucide-react` | D-09 names one icon set |
| Fonts | Google Fonts `<link>` | `@fontsource-variable/*` imports | Self-hosted; works offline on a judging laptop |
| Routing | A router library | One zustand `selectedFolder` plus an optional `location.hash` sync | D-02; react-router is not in the stack |
| Charts | A chart library | Plain divs for SLA bars | STACK.md ("the sim-clock timeline and SLA bars are plain divs") |

**Key insight:** the derivation is the only custom logic that matters. Everything else is standard, and it is small enough that a planner can keep it simple.

## Common Pitfalls

### Pitfall 1: The clock snaps back
**What goes wrong:** the clock resets to 18:00 after every advance, on tab switch or on poll.
**Why it happens:** advance with `hours` is computed from `clock.json`; `GET /api/clock` is stateless; TanStack Query refetches on focus by default.
**How to avoid:** `to` for advance; clock in zustand; `refetchOnWindowFocus: false`; never poll the clock.
**Warning signs:** the clock reads 18:00 again a second after advancing.

### Pitfall 2: The board does not move when the clock does
**What goes wrong:** success criterion 2 fails silently; scrubbing shows the same board.
**Why it happens:** `/api/deals`, `/api/inbox` and `/api/alerts` ignore the clock (verified).
**How to avoid:** all board, inbox and alert views go through `viewAt(now, ...)`.
**Warning signs:** advancing 100 hours leaves `sla_pct` at 1.13 for Mama Rosa's Kitchen.

### Pitfall 3: Replies disappear
**What goes wrong:** an answered inbox item reappears as pending after the next refetch.
**Why it happens:** the mock does not store replies (verified).
**How to avoid:** apply the overlay inside `inboxAt`; do not write the response into the Query cache.

### Pitfall 4: Held deals lose their stage or keep growing
**What goes wrong:** Bayou's column is empty, or its SLA keeps growing past the hold (it would show 425% at the snapshot instead of 44%).
**Why it happens:** looking for an open `stage_log` entry finds none for a held deal; computing SLA to `now` ignores the freeze.
**How to avoid:** `stageAt` uses the last entry with `entered_at <= now`; `slaPctAt` ends at `flagged_at` when held.
**Warning signs:** Bayou shows 425% or disappears from Intake.

### Pitfall 5: Timezone drift
**What goes wrong:** times display in the reviewer's zone (for example Pacific), and durations change near midnight.
**Why it happens:** `new Date(...)` with local-time methods.
**How to avoid:** `simToMs` and `fmtSimTime` as written in Code Examples; no `toLocale*` on sim times.

### Pitfall 6: Red leaks into the whole UI
**What goes wrong:** SC5 fails ("red appears only on fraud holds").
**Why it happens:** the shadcn `destructive` variant is used for error banners, `overdue`, form errors, or the sonner error style.
**How to avoid:** errors use neutral ink text with a hairline border and a lucide icon (no red). `overdue` is amber.

### Pitfall 7: Green on every OK
**What goes wrong:** D-05 fails: green appears on `needed_by_badge: ok` and on stage chips.
**How to avoid:** green only for cleared or approved outcomes (for example an answered `approve` on the inbox or a Closed deal).

### Pitfall 8: scaffold traps
- `npx shadcn@latest init -d` uses the Next.js template. Use `-t vite -b base -p nova`.
- Components land in `./@/` if the root `tsconfig.json` has no `paths`.
- `Tailwind` not detected without `@import "tailwindcss";` in the CSS file.
- `TS6133` from `scroll-area.tsx` under `noUnusedLocals`; delete the unused import, keep the flag.
- TS7 rejects `baseUrl` (TS5102). `verbatimModuleSyntax` requires `import type`. `erasableSyntaxOnly` forbids `enum`.
- Template purple accent and violet `.dark` sidebar primary; delete both.

### Pitfall 9: Folder names break URLs
**What goes wrong:** `Bayou Bistro & Grill` is read as a query-string split at `&`.
**How to avoid:** `encodeURIComponent(folder)` on every path segment (verified with `%26` and `%27`).

### Pitfall 10: Empty first screen
**What goes wrong:** at the clock start (2026-11-02 08:00) no deal has arrived, so the board is blank and looks broken.
**How to avoid:** an empty state with the clock time: "No deals have arrived as of Mon 11/02 8:00 AM CT." Mama Rosa's Kitchen appears at 8:30.

### Pitfall 11: Scrubbed badges and facts look current
**What goes wrong:** `needed_by_badge` and facts show end-of-run values while the clock reads 11/02.
**Why it happens:** no timestamp in the contract for either.
**How to avoid:** show the badge with a tooltip "Set by the engine at Wed 11/04 6:00 PM CT" when the clock is not at that time; show facts and issues with a caption "Engine values for the run" once the deal has arrived. Decision in Open Questions.

### Pitfall 12: Names that do not resolve
**What goes wrong:** `credit.nakamura` appears on screen, violating D-14.
**How to avoid:** role labels with the id in a tooltip, as described in Contract Facts. Do not invent names.

### Pitfall 13: `dangerouslySetInnerHTML`
**What goes wrong:** a legal name or message containing markup executes in the browser.
**How to avoid:** render every engine string as React text. Never create `href` values from document strings (check the scheme first if links are added).

### Pitfall 14: Money and dates that are wrong by one digit
**What goes wrong:** `$410,000` renders as `$410,000.00`, or `Tue 11/03 3:05 PM CT` renders as `Tue 11/03 03:05 PM CT`.
**How to avoid:** the formatters in Code Examples; money with `minimumFractionDigits: 0`.

### Pitfall 15: Five deals, not thirteen
**What goes wrong:** layouts or tests hard-code the sample count.
**How to avoid:** count columns from data; the ROADMAP's 13 is the real sample and will arrive from the engine later.

## Code Examples

The block below is a condensed copy of the derivation module. The exact code that passed is the reference file pair, and the block reproduces its logic (`stageAt`, `slaPctAt`, `inboxAt`, `alertsAt` are identical in both). `node --test` runs the reference file with type stripping on Node 26.13 and all 9 tests pass against the real fixtures (2026-11-07). Copy the reference files into `ui/src/time/` rather than retyping them.

Reference copies: `/private/tmp/claude-501/-Users-jes-Goldman-I/c14eddd9-8217-4cd4-a56b-9911e9a08267/scratchpad/derive-check/timeview.ts` and `.../timeview.test.ts`.

```ts
// Source: derived from prism/contract.py and fixtures/*.json; verified by node --test (9/9)
const SIM_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})-06:00$/
const HOUR_MS = 3600_000

export function simToMs(s: string): number {
  const m = SIM_RE.exec(s)
  if (!m) throw new Error(`not a -06:00 sim time: ${s}`)
  return Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) + 6 * HOUR_MS   // UTC = wall clock + 6h
}

const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
export function fmtSimTime(s: string): string {          // "Tue 11/03 3:05 PM CT"
  const m = SIM_RE.exec(s)!
  const [y, mo, d, h, mi] = [+m[1], +m[2], +m[3], +m[4], +m[5]]
  const dow = DOW[new Date(Date.UTC(y, mo - 1, d)).getUTCDay()]
  const h12 = ((h + 11) % 12) + 1
  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`)
  return `${dow} ${pad(mo)}/${pad(d)} ${h12}:${pad(mi)} ${h < 12 ? 'AM' : 'PM'} CT`
}

export function fmtDuration(ms: number): string {        // "26h 10m"
  const mins = Math.max(0, Math.round(ms / 60_000))
  return `${Math.floor(mins / 60)}h ${String(mins % 60).padStart(2, '0')}m`
}

// Last stage entry that has started by time t. null = not arrived yet.
// Held deals keep their stage: the last entry stays in force after its exit.
export function stageAt(log: StageLogEntry[], t: number): StageLogEntry | null {
  let cur: StageLogEntry | null = null
  for (const e of log) { if (simToMs(e.entered_at) <= t) cur = e; else break }
  return cur
}

// SLA freezes at flagged_at while held (contract: sla_pct freezes while held).
export function slaPctAt(deal: DetailLike, enteredAt: string, t: number): number {
  const f = deal.fraud
  const frozen = f.held && f.flagged_at !== null && simToMs(f.flagged_at) <= t
  const end = frozen ? simToMs(f.flagged_at as string) : t
  return (end - simToMs(enteredAt)) / HOUR_MS / deal.sla_hours
}
export const roundPct = (x: number) => Math.round(x * 100) / 100   // fixture rounding (1.125 -> 1.13)

export function inboxAt(items: InboxLike[], t: number): InboxLike[] {
  return items.filter((i) => simToMs(i.at) <= t).map((i) => {
    const answered = i.status === 'answered' && i.answered_at !== null && simToMs(i.answered_at) <= t
    return answered ? { ...i } : { ...i, status: 'pending' as const, answer: null, answered_at: null }
  })
}
export function alertsAt(items: AlertLike[], t: number): AlertLike[] {
  return items.filter((a) => simToMs(a.at) <= t).sort((a, b) => simToMs(b.at) - simToMs(a.at))
}
```

The three interfaces (`StageLogEntry`, `DetailLike`, `InboxLike`, `AlertLike`) are plain object types matching `prism/contract.py` (`StageLogEntry` at lines 127-132; `HumanRequest` at 135-141; `Alert` at 144-148). Declare them in `src/api/types.ts` with `import type` from `schema.ts`.

**Overlay application (answers made in the UI; not in the test file; the endpoint behavior was verified with curl, the function itself is untested):**

```ts
// Source: docs/CONTRACT.md (reply shape); app.py:107-120 (mock reply does not persist)
export async function reply(itemId: string, option: string): Promise<void> {
  const res = await fetch(`/api/inbox/${encodeURIComponent(itemId)}/reply`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ option }),              // InboxReply: only "option" (extra fields are rejected)
  })
  if (!res.ok) throw new Error((await res.json()).detail ?? `HTTP ${res.status}`)
  // Overlay with the UI's clock, not the response's answered_at (mock returns the fixture clock)
  answers.set(itemId, { answer: option, answered_at: clock.now })
}
```

**Snapshot test (what the planner should require):** at `2026-11-04T18:00-06:00` the derived SLA for all five deals equals the fixture's `sla_pct` after `roundPct`; the board has 3 Intake, 1 Credit, 1 Committee; `inboxAt(...)` at `2026-11-02T11:00-06:00` shows `inbox-005` pending and at `2026-11-02T12:00-06:00` shows it answered with `approve`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `shadcn init -d` for Vite | `init -t vite -b base -p nova -y` (`-d` implies Next.js) | shadcn CLI 4 | STACK.md's `init -d -y` would scaffold the wrong template in a Vite project |
| Preset `base-nova` | Preset `nova` writes style `base-nova` | shadcn CLI 4.23.0 | `-p base-nova` is rejected |
| `npm create vite` template with Radix/tailwind not installed | Template ships oxlint, TS 7 and `erasableSyntaxOnly`; Tailwind must be added | create-vite 9.3.4 | Extra steps listed in Scaffold |
| `baseUrl` for path aliases | `paths` only | TypeScript 7 | `baseUrl` raises TS5102 |
| Google Fonts link | Fontsource variable packages | ongoing | Offline-safe bundle |

**Deprecated or misleading in STACK.md:** the `-d -y` init line and the `-p base-nova` preset (both above); and the "Geist Variable (installed by the CLI)" note is correct and confirmed.

## Assumptions Log

> Planner and discuss-phase use this table to find decisions that need confirmation.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Geist provides tabular figures (`tnum`) so `tabular-nums` works | Design Tokens | Money columns misalign; fallback is Inter (also has `tnum`, not verified here either) |
| A2 | Palette hex values and radius/shadow overrides (Claude's discretion) | Design Tokens | Visual only; contrast is verified |
| A3 | Role labels for recipients (derived from rulebook request types) | Contract Facts | Labels may disagree with the team's wording; easy to change |
| A4 | The live engine will return snapshot values for `/api/deals` (not clock-aware) | Pattern 2 | If the engine becomes clock-aware, the derivation becomes redundant but harmless for summary fields |
| A5 | `answered_at` = UI clock is the right time for overlay answers | Pattern 3 | Could be confusing when scrubbing back; this is a replay, so consistent |
| A6 | Shadow token names (`--shadow-sm`, `--shadow-lg`) and `--radius-*` overrides apply as written in Tailwind v4 | Design Tokens | Visual only; the build will show it |
| A7 | Package legitimacy verdicts stay valid for the checkpoint date | Audit | Re-run the seam before install |

**If this table is empty:** not empty. A1 and A4 need confirmation before locking; A2 and A3 are discretion items.

## Open Questions

1. **Scrub policy for `needed_by_badge`, facts and issues.**
   - What we know: none of these carry a timestamp; the badge is computed at the fixture's `now` (contract.py:213).
   - What's unclear: whether to show them unchanged everywhere, or caveat them when scrubbed.
   - Recommendation: show as-is with the caveat described in Pitfall 11. Jesse to confirm.

2. **Names versus ids (D-14).**
   - What we know: the directory (`data/participant/contacts/teams.json`, 16 people) has real names; the fixture uses five IDs not in it. The directory is participant-only material (CLAUDE.md: raw data stays out of git).
   - What's unclear: whether copying 16 names into `ui/` breaks the confidentiality rule.
   - Recommendation: role labels with ids in tooltips for Phase 2. Ask Zeke to align fixture IDs with the directory (`victor.hale`, `harold.benson`, a real RM id such as `brian.foster` or `elena.ruiz`). Only then decide whether names ship.

3. **DBA (D-15).**
   - What we know: `DealSummary` and `DealDetail` have no DBA field (contract.py:205-230); the rulebook's legal name is "not the DBA".
   - Recommendation: show the folder name and legal name; omit the DBA. Confirm with Jesse, or request a `dba` field in the contract (a change Zeke would need to make).

4. **Error states and red (D-01 versus D-05).**
   - What we know: D-01 requires error states on every screen; D-05 allows red only for fraud holds.
   - Recommendation: neutral ink with a hairline border and a lucide alert icon. Confirm.

5. **Overdue and at-risk colors.**
   - Recommendation: both amber (D-05 allows amber for "deadline at risk"); "overdue" is not red.

6. **Confirm and release hold buttons.**
   - Recommendation: neutral outline buttons, not red, so red stays on the badge only. Confirm.

7. **Routing conflict with the fixture.**
   - Recommendation: flag to Zeke: `inbox-002` routes a $410,000 committee approval to `committee.osei`; the rulebook sends amounts at or above $250,000 to `harold.benson` (stages.json:49-52). `inbox-003` and `-004` use `fraudops.keller`; the rulebook names `victor.hale`. These are fixture fidelity issues; the UI displays the value it gets.

8. **Toasts.**
   - Recommendation: omit sonner; show the answer in the row (the answered state is visible). Saves a dependency and avoids a red-error toast by default.

9. **Serif choice.**
   - Recommendation: the system serif stack, to avoid a checkpoint for one font. Use Source Serif 4 only if Jesse approves the checkpoint.

10. **Playback controls.**
    - Recommendation: buttons for +1 h, +6 h, +1 day, Next event, Replay; playback at 1 sim hour per second (about 2 minutes for the full window) with pause. "Next event" is computed from `stage_log`, `human_requests`, `alerts` and `answered_at` timestamps greater than `now`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | Vite 8 (needs ^20.19 or >=22.12) | yes | v26.13.0 | — |
| npm | installs | yes | 11.20.0 | — |
| Python venv (`.venv`) | mock API | yes | fastapi 0.162.2, pydantic 2.14.3 | — |
| uvicorn | mock API (`.venv/bin/uvicorn`) | yes | version not captured | — |
| Ports 8000 and 5173 | API and Vite | free at check; started and stopped during this research | — | — |
| npm registry | scaffold and installs | reachable | — | — |
| Browser for a visual smoke test | UAT | not checked | — | manual check against the checklist below |
| Font tools (fontTools) | verifying `tnum` in Geist | no | — | verify by eye in the browser (A1) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** font tooling (verify tabular figures by eye).

## Validation Architecture

> Included because the user asked for a validation approach for this UI phase. `workflow.nyquist_validation` is `false` in `.planning/config.json`, so no Wave 0 test mapping is required.

**Test framework:** Node's built-in `node --test` (Node 26 runs `.ts` with type stripping; verified). No test-runner dependency.

| Gate | Command | Pass condition |
|------|---------|----------------|
| Build and types | `cd ui && npm run build` | `tsc -b` and `vite build` exit 0 |
| Lint | `npm run lint` | exit 0; no new warnings in project files (shadcn variant warnings are accepted) |
| Derivation | `node --test src/time/timeview.test.ts` | all tests pass (9 in the reference file) |
| Contract drift | `npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.ts && git diff --exit-code -- src/api/schema.ts` | no diff after regeneration |
| Proxy | start `MOCK=1 .venv/bin/python -m uvicorn prism.api.app:app --port 8000`, then `npm run dev` and `curl localhost:5173/api/clock` | returns the clock JSON |

**Manual smoke checklist (run before the demo):**
1. Board at the start time shows the empty state; advancing to `Tue 11/03 3:05 PM CT` shows Mama Rosa's Kitchen in Committee, Lone Star in Credit, and Bayou in Intake, held.
2. Advancing to `2026-11-03T15:05-06:00` shows `inbox-004` (Juniper hold request) and the Juniper deal as held.
3. Answering `inbox-001` with Approve sends `{"option":"approve"}`; the item moves to answered; a refresh shows it pending again (documented mock behavior).
4. Deal detail for `Mama Rosa's Kitchen` and `Bayou Bistro & Grill` opens by clicking; the Bayou SLA stays at 44% after the hold time.
5. No red anywhere except the held badge; no purple; no emoji; the only serif is the page title.
6. Stop the API: the UI shows the not-reachable state. Start with `MOCK=0`: the UI shows "The engine is not connected."

**Sampling:** after each task, run the build and the derivation tests; before the phase gate, run the full table and the manual checklist.

## Security Domain

> Required: `security_enforcement` is `true` (absent or enabled). ASVS level 1.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Mock has no login; Phase 2 does not authenticate |
| V3 Session Management | no | No sessions |
| V4 Access Control | no (client-only) | The UI does not enforce who may answer; the API does not either in mock mode. Note this in the pitch, not as a control |
| V5 Input Validation | yes | Reply `option` restricted to `item.options` in the UI, and validated by the server (422). Never send extra keys (`extra="forbid"`) |
| V6 Cryptography | no | No secrets or crypto in the UI |
| V7 Error Handling | yes | Show the API's `detail` string or a fixed message; no stack traces, no raw bodies |
| V13 API | yes | Use the Vite `/api` proxy; the mock's CORS allow-list (`localhost:5173`, `127.0.0.1:5173`) covers direct calls; do not widen it |
| V14 Configuration | yes | No secrets in the bundle. Any `VITE_`-prefixed variable is public; never prefix the NVIDIA key |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stored or reflected XSS through document-derived names, facts, messages and evidence | Tampering | React text rendering only; no `dangerouslySetInnerHTML`; no `href` from engine strings without a scheme check |
| Open redirect or `javascript:` link from `linked_deals` or `source_doc` | Tampering | Render as text or as same-app routes only |
| Participant material leaking into the bundle (`data/`, PDFs, `teams.json`) | Information Disclosure | Import only fixture-shaped data and the generated schema; keep `data/` out of `ui/`; check `dist/` contains no PDFs or names from the directory |
| Clickjacking on the demo | — | Not in scope for a local demo; note only |

**Untrusted-input boundary:** every string from `fixtures/` in this phase, and every string the live engine will later return, is treated as data, never as instructions. The fixtures themselves contain no injected instructions (checked by reading them).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH for versions and the verified scaffold; flagged packages carry the checkpoint.
- Architecture (clock and derivation): HIGH; verified against the fixtures and the running mock.
- Design tokens: MEDIUM (discretion values); contrast is computed.
- Pitfalls: HIGH for the mock behavior (each verified with curl or the test run); MEDIUM for live-engine behavior (not available).

**Research date:** 2026-11-07
**Valid until:** 2026-11-14 (7 days; every package in the stack was published within the last month, and the shadcn CLI changed its preset names within the last two releases).

## Sources

### Primary (HIGH confidence)
- `docs/CONTRACT.md` (endpoints, conventions, mock run instructions) [VERIFIED: local file read]
- `prism/contract.py` (all models and line numbers cited above) [VERIFIED: local file read]
- `prism/api/app.py` (mock behavior: stateless clock, non-persisting reply, `require_mock`) [VERIFIED: local file read; behavior confirmed with curl]
- `fixtures/clock.json`, `deals.json`, `deal_detail.json`, `inbox.json`, `alerts.json` [VERIFIED: local file read and cross-checks]
- `data/participant/rules/stages.json`, `data/participant/contacts/teams.json` (participant material; not committed) [VERIFIED: local file read]
- `docs/DETAILS_CHECKLIST.md` (J1-J22, stage and SLA rules) and `docs/MESSAGE_TEMPLATES.md` (house style, lines 4-12) [VERIFIED: local file read]
- Live mock API probes on port 8000 and 8765, 2026-11-07 (clock stateless, reply not stored, 404/422, folder encoding, openapi.json) [VERIFIED: local run]
- Scaffold runs in `scratchpad/scaffold-test/ui` (create-vite 9.3.4, shadcn 4.23.0 `init` and `add` output, build and lint results) [VERIFIED: local run]
- Derivation tests in `scratchpad/derive-check` (`node --test`, 9/9 pass) [VERIFIED: local run]
- npm registry versions and download counts (`npm view`; `gsd-tools query package-legitimacy check`), 2026-11-07 [VERIFIED: npm registry for OK packages; SUS packages tagged ASSUMED per the protocol]

### Secondary (MEDIUM confidence)
- https://vite.dev/config/preview-options: `preview.proxy` defaults to `server.proxy`; `preview.port` defaults to 4173 [CITED]
- https://tailwindcss.com/docs/font-variant-numeric: `tabular-nums` generates `font-variant-numeric: tabular-nums` (Tailwind v4 docs) [CITED]

### Tertiary (LOW confidence)
- Geist tabular-figure support (A1): not verified. [ASSUMED]
- Tailwind v4 `--shadow-*` theme key naming (A6): from training knowledge; the build will confirm. [ASSUMED]

## Project Constraints (from CLAUDE.md)

Directives from `/Users/jes/Goldman-I/.claude/CLAUDE.md` that apply to the UI phase:
- **No Claude or Anthropic models in the product.** The UI calls no LLM.
- **Determinism:** every scored field comes from deterministic code. The UI never computes or changes a score, hold or link; it displays engine values, and its derivation is presentation only.
- **Time semantics:** all times are sim time, America/Chicago, `-06:00`. The UI never uses the viewer's local time, and SLA timers are sim hours.
- **Confidentiality:** raw data and PDFs stay out of git. Do not copy directory names, contacts, PDFs or `data/` content into `ui/`.
- **Secrets:** no NVIDIA key in the UI or in `VITE_*` variables.
- **GSD workflow:** edits happen through the GSD commands (`/gsd-execute-phase` for planned work).
- **No project skills:** `.claude/skills/` and `.agents/skills/` do not exist in this repo.

## RESEARCH COMPLETE

Summary for the planner:
- Plan the clock, the derivation module and the overlay first; they carry success criteria 2 and 4.
- Use the verified scaffold steps exactly, including `-t vite -b base -p nova`, the root `tsconfig.json` paths and the scroll-area fix.
- Add one `checkpoint:human-verify` before the first install covering the SUS packages in the audit table.
- Resolve Open Questions 1, 2, 3 and 4 with Jesse before writing the UI tasks that depend on them.
