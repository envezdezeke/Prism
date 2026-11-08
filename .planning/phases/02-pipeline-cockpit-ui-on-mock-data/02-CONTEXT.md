# Phase 2: Pipeline Cockpit UI on Mock Data - Context

**Gathered:** 2026-11-07 (Jesse)
**Status:** Ready for planning

<domain>
## Phase Boundary

Someone playing bank staff can watch every deal move through the pipeline, open any deal to see what the engine read and why it decided what it did, and answer sign-off requests. Built entirely on Zeke's mock API (`MOCK=1`, `docs/CONTRACT.md`, `fixtures/`), so it never waits on the engine. Requirements UI-01 to UI-05. The live switch stays in Phase 7. Amended Sun 2026-11-08 (D-23 to D-32): the fraud-graph hero view (UI-06) and a red-team summary chip are pulled into Phase 2 on mock data.

</domain>

<decisions>
## Implementation Decisions

### Priority
- **D-01:** Accuracy and sturdiness over looks. The Goldman score is graded on the output file, so the UI must show the engine's data faithfully and never invent or reformat a value in a way that changes its meaning. Every screen handles loading, empty and error states.
- **D-02:** Jesse owns this phase and builds it with Claude Code. Keep the stack and structure simple enough for a non-developer to direct: no clever abstractions, no state libraries beyond what the stack research names.

### Visual direction: "Institutional" (locked)
- **D-03:** Clean, modern, institutional finance: the look of a bank's internal credit tool. A nod to Goldman Sachs, **not a copy**: do not use Goldman's sky blue (#7399C6), its logo, its fonts (Goldman Sans) or its name anywhere in the UI.
- **D-04:** Palette: warm off-white page background (e.g. #FAF9F7), white surfaces, a neutral warm-gray scale for text and borders, and **one** deep navy accent (e.g. #1B2A41) for primary actions, active nav and focus. No second accent color.
- **D-05:** Semantic color only for meaning: red **only** for fraud holds; amber only for SLA past 100% / deadline at risk; a muted green only for "cleared / approved". Nothing else is colored.
- **D-06:** Typography: a restrained serif for **page titles only** (e.g. Source Serif 4 or Newsreader), a clean sans for everything else (e.g. Inter or Geist). Tabular (fixed-width) numerals everywhere numbers appear. Money right-aligned in tables, formatted `$1,200,000`.
- **D-07:** Structure: hairline 1px borders instead of shadows; small corner radius (4–6px max); a 4px spacing grid; dense, aligned layouts; tables over card grids wherever data is compared.

### "Must not look vibe-coded" (hard prohibitions)
- **D-08:** No gradients, glow, glassmorphism or blur. No drop shadows beyond a 1px hairline or the faintest elevation on popovers.
- **D-09:** No emoji anywhere. Icons from one line-icon set only (lucide), used sparingly and never decoratively.
- **D-10:** No purple/indigo/violet. No rainbow badge sets. No centered "hero" layouts or marketing copy. No large rounded "bubble" cards.
- **D-11:** No placeholder or filler text ("Lorem", "Coming soon", fake metrics). Every label uses real banking vocabulary (Intake, Credit, Committee, RM, SLA, needed-by).
- **D-12:** No default component-library look: restyle shadcn/Base UI defaults to the tokens above rather than shipping the stock theme.

### Content rules
- **D-13:** Times shown in sim time, Central: "Tue 11/03 3:05 PM CT"; durations as "26h 10m". Never the viewer's local time.
- **D-14:** Names, not ids, in the UI ("Aisha Grant", not `aisha.grant`); ids may appear in tooltips.
- **D-15:** Deal identity is the folder name plus the legal name; show the DBA when present.
- **D-16:** Fraud is shown soberly: a held deal gets a red "Held: fraud review" badge and its plain-words reason; a watch-tier deal gets a neutral "Watch" badge. No alarmist styling.

### Decisions after research (Jesse, 2026-11-07 19:05)
- **D-17:** Mock-data mismatches (staff ids not in `contacts/teams.json`, $410k committee routed to `committee.osei`, fraud holds to `fraudops.keller`, no DBA field) are **worked around in the UI only**; do not ask Zeke to change fixtures. The UI shows a person's real name when the id is in `contacts/teams.json`, otherwise a role label derived from the request type/stage (e.g. "Committee", "Fraud Operations"), with the raw id in a tooltip. D-14 and D-15 apply when the data allows (DBA shown only if a future contract field provides it).
- **D-18:** Time-travel: board, alerts and inbox are derived client-side for the UI clock (the mock clock is stateless and lists ignore it: see RESEARCH). Facts, issues and the needed-by badge have no timestamps, so they always show the end-of-run view with a quiet "as of end of run" label.
- **D-19:** Page-title serif is **Source Serif 4, bundled** via `@fontsource-variable/source-serif-4` (one human-verify checkpoint before installing, per the package-legitimacy check). Sans is Geist (bundled).
- **D-20:** Error states use neutral gray (red stays reserved for holds). All action buttons use the navy accent, including fraud-hold actions. No toast pop-ups: confirmations appear inline.
- **D-21:** Clock controls: show current sim time, advance (by hours or to a time) and replay from start. Keep the clock in client state; never refetch `/api/clock` after load (it would snap back). Inbox replies are kept in a client overlay because the mock doesn't persist them.
- **D-22 (Jesse, Sat 19:40):** Staff are shown as role labels ("Credit officer", "Committee", "Fraud Operations") with the raw id in a tooltip. No names map in the UI and no staff names in git; real names come from the engine at the Phase 7 live switch. Supersedes the name part of D-14/D-17 for Phase 2.

### Hero-flow amendment (grilling session with Zeke, Sun 2026-11-08)
The demo is the product: a judge must see a cross-deal fraud ring caught before money goes out, then see why. These decisions relax D-08, D-10 and the "no graph, no motion, no dark" rules **only** as stated; every other ban stays (gradients, blur, glassmorphism, purple/indigo/violet, emoji, toasts, Goldman #7399C6, large shadows).
- **D-23:** One graph library is allowed: `react-force-graph-2d@1.29.2` (MIT, ships types, pinned exact). No other graph, chart or animation library.
- **D-24:** CSS-only motion is allowed: transitions and `@keyframes` declared in `index.css`. Motion is one-shot and short (hold pulse 1.6s, drawer 200ms, fade 300ms, edge fade-in 600ms on canvas), never looping, and `prefers-reduced-motion` switches it off.
- **D-25:** The fraud graph is a deliberate dark investigation view. While `#/graph` is open, `<html data-view="investigate">` swaps the same token names to a dark set: page `#0C0A09`, surface `#1C1917` (the light ink), subtle `#292524`, ink `#F5F5F4`, ink-2 `#A8A29E`, line `#44403C`, navy lifted to `#A9B7CC` for selection and focus, alarm red `#F04438`, amber `#F79009`, green `#47CD89`. The board stays light. There is no general dark theme.
- **D-26:** Hero = the fraud graph, reached from the board. Routes `#/graph` (first held cluster) and `#/graph/{clusterId}`; a permanent "Fraud graph" rail item; "Investigate ring →" on a held card, in the clock-bar hold line and in the deal page's fraud panel. This delivers Phase 7 UI-06 early.
- **D-27:** Default graph view: the flagged cluster plus one hop. Edges into an entity shared by two or more ring deals and at least 0.5 rare are lit alarm red once the cluster is held (display rule; the engine's counting is in the families). Edges carry "kind · rarity" labels. Deals outside the ring are drawn dim and named under the canvas ("not linked, not held"): the visible proof of no false flags.
- **D-28:** Canvas colours are read from CSS custom properties at runtime (`src/graph/palette.ts`), so tokens stay single-source. Graph-only tokens: deal and history stone `#A8A29E`, edge `#57534E`, entity tints by kind group (document `#A18A62`, identity `#6E7A8C`, money `#6F8F7B`). A canvas-only halo is allowed on lit ring elements and nowhere else.
- **D-29:** The graph obeys the sim clock: an edge exists from `first_visible_at`, a node from its first visible edge (or a deal's arrival), and the cluster turns red at the first `flagged_at` of a held ring deal. The existing clock bar replays it forming; new edges fade in.
- **D-30:** Clicking a node or edge opens a 320px dark evidence drawer: shared value, the evidence sentence, rarity, weight, visible-from time, every deal sharing the value, and F1 to F6 in plain words in contract order (fired ones in weight 600 with the engine's evidence, captioned "as of end of run"). An "Investigator" tab renders the agent trace labelled **Advisory**, beside but never mixed with deterministic evidence. A "Red-team: N bypasses / M attempts" chip is computed from `/api/redteam` (sums over tricks; shown as the data says).
- **D-31:** Hold beat on the board: when a deal becomes held while the board is open, its card pulses red once, sorts to the top of its column (already the sort rule), gets a red left edge and a "Linked to N deals" footer, and one hold line appears in the clock bar for the latest hold in the last sim day. Red is still only for a fraud hold.
- **D-32:** 02-04 shrinks: the Alerts feed is built in full (newest first, amber edge on escalations); the Inbox is a minimal list with reply buttons from each item's options to `POST /api/inbox/{id}/reply`, with the in-memory overlay. The rail gets Inbox (pending count) and Alerts.

### Claude's Discretion
- Exact hex values within the palette above, spacing details, component choice within the stack, and layout of secondary panels, as long as D-03 to D-12 hold.

</decisions>

<specifics>
## Specific Ideas

- Reference feel: the internal tooling of an investment bank or a modern credit platform: calm, precise, information-dense, trustworthy. Think "a credit officer would use this all day."
- Pipeline board: six stage columns (Intake → Closed) with compact deal rows/cards showing legal name, amount, time in stage vs. SLA, needed-by badge, and hold/watch status.
- Deal detail: facts table with a source-document chip and confidence per fact; issues list; stage log with each "why"; human requests; alerts.
- Inbox: pending sign-off requests with the plain-words message and answer buttons limited to the request's allowed options.
- Copy and messages follow `docs/MESSAGE_TEMPLATES.md` wording; the credit memo (when the contract adds `credit_memo`) follows `docs/CREDIT_MEMO_TEMPLATE.md`.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `docs/CONTRACT.md`: API endpoints, conventions (sim times, nulls), mock server run instructions
- `prism/contract.py`: Pydantic models (source of truth for every field the UI may read; the UI never reads a field the contract doesn't define)
- `fixtures/*.json`: mock data the UI is built against (made-up deals)
- `.planning/research/STACK.md`: frontend stack and versions (React 19, Vite 8, Tailwind 4, shadcn on Base UI, TanStack Query, zustand), TypeScript 7 `baseUrl` gotcha
- `docs/MESSAGE_TEMPLATES.md`, `docs/CREDIT_MEMO_TEMPLATE.md`: wording rules
- `docs/DETAILS_CHECKLIST.md` §3–§5: stage, SLA and deadline rules the board visualizes
- `docs/UI_PLAYBOOK.md` (Zeke, Sat 19:05): exact design tokens (§2), formatting rules (§3), screen recipes (§4), verification checklist (§6). **Precedence:** this CONTEXT (D-01..D-21) > 02-RESEARCH.md > UI_PLAYBOOK. Overrides: fonts per D-19 (bundled Source Serif 4 + Geist), names per D-17, clock per D-21, no toasts per D-20; playbook §5 extras are stretch only.

</canonical_refs>

<environment>
## Environment notes

- Jesse builds on macOS: Node 26.13, npm 11.20, Python venv at `.venv/` (Zeke's mock API runs with `MOCK=1 .venv/bin/python -m uvicorn prism.api.app:app --port 8000`). Zeke is on Windows, so scripts must be cross-platform.
- UI lives in `ui/` (per ONBOARDING). The Vite dev proxy sends `/api` to `http://localhost:8000`.

</environment>
