# Phase 2: Pipeline Cockpit UI on Mock Data - Context

**Gathered:** 2026-11-07 (Jesse)
**Status:** Ready for planning

<domain>
## Phase Boundary

Someone playing bank staff can watch every deal move through the pipeline, open any deal to see what the engine read and why it decided what it did, and answer sign-off requests. Built entirely on Zeke's mock API (`MOCK=1`, `docs/CONTRACT.md`, `fixtures/`), so it never waits on the engine. Requirements UI-01 to UI-05. The fraud-graph hero view, red-team view and live switch are Phase 7, not here.

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

</canonical_refs>

<environment>
## Environment notes

- Jesse builds on macOS: Node 26.13, npm 11.20, Python venv at `.venv/` (Zeke's mock API runs with `MOCK=1 .venv/bin/python -m uvicorn prism.api.app:app --port 8000`). Zeke is on Windows, so scripts must be cross-platform.
- UI lives in `ui/` (per ONBOARDING). The Vite dev proxy sends `/api` to `http://localhost:8000`.

</environment>
