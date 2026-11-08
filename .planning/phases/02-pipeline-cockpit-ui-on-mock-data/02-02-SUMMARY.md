---
phase: 02-pipeline-cockpit-ui-on-mock-data
plan: 02
subsystem: ui
tags: [react, typescript, zustand, tanstack-query, node-test, audit]

requires:
  - phase: 02-pipeline-cockpit-ui-on-mock-data
    provides: plan 01 tracer (tokens, timeview.ts, client, clock store, tracer board, smoke script)
provides:
  - Complete formatting module (fmtHours, fmtPct, fmtSla, fmtSimDay, confidence helpers, DASH, NULL_TOOLTIP)
  - Pure time functions msToSim, clampMs, nextEventAfter (with extra timestamps), sortBoardRows, SLA stop at stage exit
  - Shared primitives (PageTitle, Caption, NullValue, LoadingState, EmptyState, ErrorState) and Badges (StatusBadge, NeededByBadge, SlaBar)
  - Full pipeline board with held-first sorting and SLA bars
  - Sim clock bar and client-held clock actions (setNow, advanceHours, goTo, replay, play, pause) with debounced absolute-target sync
  - npm run audit design and safety gate that demonstrably fails
affects: [02-03, 02-04, phase-07-live-switch]

actuals:
  tokens: 14800
  tasks: 3
  commits: 4
plan_head_before: e287af8853ac1e01cb9d4142d32dbe23c3980485
plan_head_after: a64e0c9e13fc7209b0aae37382d7e559e7ecda78

tech-stack:
  added: []
  patterns:
    - "Pure view helpers in timeview.ts (no imports) feed every screen; React components only render"
    - "Clock writes are absolute ({to}) or {}, debounced 300 ms, never reverting the local clock; timers at module level"
    - "audit.ts is the mechanical check for the design rules; later plans add files under its allow-lists"

key-files:
  created:
    - ui/src/lib/format.test.ts
    - ui/src/components/app/Primitives.tsx
    - ui/src/components/app/Badges.tsx
    - ui/src/components/app/ClockBar.tsx
    - ui/src/api/client.test.ts
    - ui/src/state/clockStore.test.ts
    - ui/scripts/audit.ts
  modified:
    - ui/src/lib/format.ts
    - ui/src/time/timeview.ts
    - ui/src/time/timeview.test.ts
    - ui/src/components/app/Board.tsx
    - ui/src/App.tsx
    - ui/src/api/client.ts
    - ui/src/state/clockStore.ts
    - ui/package.json
    - ui/src/index.css
    - ui/src/components/ui/button.tsx

key-decisions:
  - "02-UI-SPEC copy and layout won over the plan where they differ (see deviations)"
  - "Play/Pause and Replay from start are separate controls, as the UI-SPEC lists them"
  - "Stage limit in a column header is shown only when every deal in the column shares it"
  - "User controls stop playback; Pause syncs the current value once"

requirements-completed: [UI-02, UI-03]

duration: 6min
completed: 2026-11-08
status: complete
---

# Phase 2 Plan 02: Board, clock and audit gate Summary

**Full pipeline board (badges, SLA text and 2px bar, held-first sort) driven by a browser-held sim clock with advance, next event, go-to and replay, plus an `npm run audit` gate that proves the colour and safety rules and can fail.**

## Commits

| Task | Commit | What |
|------|--------|------|
| 1 | d0169fb | Formatters and pure time functions, tests first (RED confirmed: both test files failed on missing exports before implementation) |
| 2 | c54dd14 | Primitives, Badges, full Board, audit gate, `audit` script, button.tsx comment reworded |
| 3 | a64e0c9 | client `postAdvance`/`postReplay`, clock store actions, ClockBar, App layout, client and store tests |

`commits: 4` is the measured count from the ledger. One of the four, 8da03cc (`HANDOFF.md` only), is Ezekiel's commit that landed on main during this plan and is not part of the work above.

## Results (mock API on :8000, Vite dev server on :5173 left running)

- `npm --prefix ui test`: `ℹ tests 35 / ℹ pass 35 / ℹ fail 0` (plan 01's 11, plus 11 new timeview and format cases, 7 client cases, 6 clock store cases). Run three times in a row for stability.
- `npm --prefix ui run build`: exit 0, `built in 109ms`, no `error TS`.
- `npm --prefix ui run lint`: exit 0, the same two accepted react-refresh warnings in button.tsx and badge.tsx.
- `npm --prefix ui run audit`: `AUDIT OK files=27 dist=14`, exit 0. With `src/probe.ts` containing `"bg-red-500"`: `AUDIT FAIL src/probe.ts:1 Tailwind default-palette colour class`, exit 1. A second probe tripped emoji, raw hex, hold colour outside Badges, blur, shadow-lg, Goldman and VITE_ at once. Probe deleted; `git status` shows no probe; audit back to `AUDIT OK`, exit 0.
- `npm --prefix ui run smoke`: `SMOKE OK deals=5 clock=2026-11-04T18:00-06:00`.
- `grep -c "^import"`: timeview.ts 0, format.ts 1 (ends in `.ts`). `getClock` appears only in client.ts and clockStore.ts.
- Real `BoardView` rendered server-side against live API data (through Vite SSR):
  - `2026-11-02T08:00`: "No deals have arrived yet." plus all six column headers with "No deals in X as of Mon 11/02 8:00 AM CT."
  - `2026-11-02T08:30`: 1 deal, Intake `1 · 48h`: Mama Rosa's Kitchen Inc, $410,000, `0h 00m / 48h · 0%`.
  - `2026-11-04T18:00`: Intake `3 · 8h` ordered Bayou (Held, 44%), Juniper (Held, 75%), Cedar Ridge (Watch, 75%); Credit `1 · 48h` Lone Star Dental (`At risk: needed by Fri 11/06 3:00 PM CT`, `28h 00m / 48h · 58%`); Committee `1 · 48h` Mama Rosa's (`54h 00m / 48h · 113%`). The `text-risk` class is present only on the at-risk badge and Mama Rosa's SLA text. Counts Intake 3, Credit 1, Committee 1 match SC2.
- Real `ClockBar` rendered server-side with live data: at the start every control is enabled, input `min="2026-11-02T08:00" max="2026-11-06T18:00" value="2026-11-02T08:00"`; at the end `+1h`, `+6h`, `+1 day`, `Next event` and `Play` are `disabled` and "No later event" shows; with `syncError` set the neutral "The clock could not be set on the server. The screen shows Fri 11/06 6:00 PM CT." appears.
- Proxy writes against the mock: a backward `to` returns `422 'to' is earlier than the current clock...`; `to` = end returns 200; replay `{}` returns 200; GET `/api/clock` still returns the fixture 11/04 6:00 PM (stateless), confirming the client clock must stay authoritative.

## Deferred visual check

No Chrome or Playwright on this machine, so no screenshots at 1440x900 and 1280x800 and no live click-through of Replay playback, Pause, Go and tab-switch behaviour in a browser. Covered instead by the store tests (fake timers: one sim hour per second, ticks never write, debounce, clamp, pause sync, failed write keeps the local clock) and server-side renders. Jesse is looking at :5173 now and can confirm; plan 04's human check should include it.

## Deviations from Plan

1. **[Design contract] UI-SPEC copy and layout over plan copy**, as the plan header instructs. Buttons read `+1h`, `+6h`, `+1 day`, `Next event`, `Play`/`Pause`, `Replay from start`, `Go` (plan: `+1 h`, Replay turning into Pause/Resume). Messages: "No later event", "Enter a time between {start} and {end}." (an out-of-range or empty Go value shows this instead of being silently ignored), "The clock could not be set on the server. The screen shows {time}." (the `describeError` text is in its title attribute and in `syncError`). Board empty state is heading plus body ("No deals have arrived yet." / "...as of {time}. Advance the clock to bring files in."), per-column "No deals in {Stage} as of {time}." instead of "None", board caption "As of end of run: amount, needed-by and Watch". The needed-by element shows the full time ("Needed by Fri 11/06 3:00 PM CT"), not only the day, and a `none` badge with a date shows neutral. Column minimum width is 160px, not 200px. SLA text goes amber when the displayed (rounded) value exceeds 100.
2. **[Design contract] Column limit shown only when every deal in the column shares it** (UI-SPEC row 8), not a min-to-max spread. At the snapshot the headers still read 8h and 48h.
3. **Closed-stage `Cleared` badge** added to `StatusBadge` through an optional `cleared` prop (UI-SPEC card item 5). Held > Watch > Cleared.
4. **`nextEventAfter` also reads stage `exited_at`** (UI-SPEC Time View Rule 11) and takes an optional `extra` timestamp list for plan 03's in-session answers; the plan's list omitted both.
5. **`describeError` network text** is the UI-SPEC wording "The API is not reachable. Start the mock server on port 8000." (the plan test text was the shorter sentence, which plan 01 already replaced). A raw `TypeError` now also maps to it.
6. **`ok` token allow-list in the audit includes `components/ui/`** because the shadcn `badge.tsx` (cleared variant) uses it. Shadow-size and drop-shadow patterns ignore `--shadow-*` and `--drop-shadow-*` theme resets in index.css (variables, not utility classes). The hold-colour rule also passes with no hold utility in Badges.tsx because the Held badge uses the Badge `hold` variant.
7. **[Rule 1 - Hygiene] Comments reworded to pass the audit**: the "destructive variant" comment in button.tsx (flagged in the plan 01 notes) and a "shadow-lg" example in an index.css comment.
8. **Extra file `clockStore.test.ts`** (6 cases) beyond the plan's file list, to prove the debounce, clamp, sync failure and playback rules the acceptance criteria describe, since no browser is available.
9. **App.tsx loading and error handling** moved into the top bar (`ClockBar` shows `LoadingState` or `ErrorState` with Retry), so the clock is never a page that renders without it. Board mounts only when the clock is ready.
10. **Board columns scroll vertically** (`max-h-[70vh] overflow-y-auto`) as the UI-SPEC asks; the shadcn ScrollArea was not needed.

## Auth gates

None.

## Known Stubs

None. Every rendered value comes from engine data or a pure derivation. The board cards are not links yet, on purpose: deal detail arrives in plan 03 and there is no navigation to an unbuilt view (D-11).

## Threat Flags

None. T-02-05 to T-02-08 are implemented: Go-to input is shape-validated and range-checked, the store clamps and sends only `{to}` (test-pinned); timers are module-level, play clears any prior interval, the interval stops at the end, writes are debounced to one per 300 ms; board strings render as text with the hold reason only in a `title` attribute and no `href` from engine data (the audit rejects the raw-HTML prop); `ErrorState` shows only `describeError` text (test-pinned, raw 500 bodies never render).

## Notes for plans 03 and 04

- **Clock sync noise with the mock:** the mock's fixture clock is fixed at 11/04 6:00 PM, so any Pause, Go or +1h to an earlier time posts a backward `to` and gets 422. The UI then shows the neutral "could not be set on the server" line. This is expected until the live engine; do not treat it as a bug. Replay (`{}`) always succeeds.
- **`nextEventAfter(details, t, extra)`**: pass the overlay's `answered_at` strings as `extra` when the Inbox answer overlay exists, so Next event stops at in-session answers (UI-SPEC rule 11). ClockBar currently calls it without extras; wire the overlay in plan 03.
- **Audit allow-lists** are in `ui/scripts/audit.ts` (`allow` arrays): the ok (green) token may be used in Badges.tsx, Inbox.tsx, DealDetail.tsx and components/ui/; `font-display` and `text-tertiary` only in Primitives.tsx and index.css; red tokens only in Badges.tsx, components/ui/ and index.css. Use `NullValue`, `PageTitle` and the `hold`/`cleared` Badge variants instead of the raw utilities. Run `npm --prefix ui run audit` after every UI change; the plan 04 token audit can simply call it.
- **Reusable primitives:** `PageTitle`, `Caption`, `NullValue(title?)`, `LoadingState`, `EmptyState(heading?, children)`, `ErrorState(heading?, message, onRetry?)`, `StatusBadge`, `NeededByBadge`, `SlaBar`, plus `HELD_LABEL`. `NullValue` takes a `title` for the "No date in the documents" tooltip on needed-by.
- **Board is not a link yet.** Plan 03 should wrap each card in the hash route link to `#/deals/{encodeURIComponent(folder)}` and add the rail; the board currently owns its `PageTitle` (App.tsx has no heading), so plan 03 should keep one page title per view.
- **Visual check still owed** (see Deferred visual check): playback feel, focus rings and 1280px column fit.

## Self-Check: PASSED

Files verified present: ui/src/lib/format.test.ts, ui/src/components/app/Primitives.tsx, Badges.tsx, ClockBar.tsx, ui/src/api/client.test.ts, ui/src/state/clockStore.test.ts, ui/scripts/audit.ts. Commits d0169fb, c54dd14 and a64e0c9 verified as ancestors of HEAD.
