---
phase: 02-pipeline-cockpit-ui-on-mock-data
reviewed: 2026-11-08T06:30:00Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - ui/src/App.tsx
  - ui/src/main.tsx
  - ui/src/index.css
  - ui/src/labels.ts
  - ui/src/people.ts
  - ui/src/route.ts
  - ui/src/api/client.ts
  - ui/src/api/types.ts
  - ui/src/data/queries.ts
  - ui/src/lib/format.ts
  - ui/src/lib/utils.ts
  - ui/src/state/answersStore.ts
  - ui/src/state/clockStore.ts
  - ui/src/state/uiStore.ts
  - ui/src/time/timeview.ts
  - ui/src/components/app/AlertsFeed.tsx
  - ui/src/components/app/Badges.tsx
  - ui/src/components/app/Board.tsx
  - ui/src/components/app/ClockBar.tsx
  - ui/src/components/app/DealDetail.tsx
  - ui/src/components/app/Inbox.tsx
  - ui/src/components/app/Primitives.tsx
  - ui/src/components/ui/button.tsx
  - ui/src/components/ui/input.tsx
  - ui/src/components/ui/badge.tsx
  - ui/src/components/ui/table.tsx
  - ui/scripts/audit.ts
  - ui/scripts/smoke.ts
  - prism/api/app.py
  - prism/contract.py
  - fixtures/deals.json
  - fixtures/deal_detail.json
  - fixtures/inbox.json
findings:
  critical: 1
  warning: 10
  info: 11
  total: 22
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-11-08
**Depth:** standard (read-only; test, build and audit re-run)
**Files Reviewed:** 33 (the last 5 are the contract and fixtures read to check the UI against)
**Status:** issues_found

## Summary

`npm --prefix ui test` passes (85/85), `npm --prefix ui run build` succeeds, `npm --prefix ui run audit` prints `AUDIT OK files=40 dist=14`. The code is tidy and the time-view layer is well tested. The weak spots are the cases the fixtures do not exercise: scrubbing the clock back into an earlier stage, and the real engine's data shapes (held, declined and re-released deals). Several of those would show a wrong number or a future fact in the demo.

I traced the engine source (`prism/move/stage.py`, `prism/move/sla.py`) to confirm how the live engine shapes data. Findings that depend on that live shape are marked "live shape". The necessity pass (`necessity-review.md`) was not run.

Contrast was computed from the tokens in `index.css`. Text on navy and sky passes AA at rest: navy on sky is 5.03:1, sky on navy is 5.03:1, white at 75% on navy is 8.9:1. Two exceptions are listed under IN-08.

## Critical Issues

### CR-01: SLA percent and limit for an earlier stage use the end-of-run stage's `sla_hours`

**File:** `ui/src/time/timeview.ts:117`, `ui/src/components/app/Board.tsx:20,62-66`, `ui/src/components/app/DealDetail.tsx:55`
**Issue:** `DealSummary.sla_hours` is one number per deal, and it is the limit of the deal's final stage. `slaPctAt` divides the dwell in whatever stage the clock is showing by that same number. When the clock is scrubbed back to an earlier stage, the limit is wrong. In the fixtures, Lone Star Dental has `sla_hours = 48` (Credit). Its Intake entry runs 08:30 to 14:00 on 11/03, and the Intake limit is 8h (Cedar Ridge Welding, an Intake deal, has 8). At 11/03 12:00 CT the UI shows Lone Star in Intake as "3h 30m / 48h · 7%". The true value is 3h 30m of 8h, which is 44%. The same happens to Mama Rosa's Kitchen, which sits at Committee (48h) at end of run and was in Intake and Credit earlier. A deal that really is over its Intake limit then shows no amber, so the figure does not match the alerts (the alert fires at 100% of the stage limit).

The Board column header has the same flaw. `stageLimit` shows "Intake · 48h" when the only Intake card is Lone Star at that time, which states a limit that does not exist. 02-UI-SPEC row 8 ("each card always shows its own limit") assumed the limit is per deal. It is per stage entry. The default demo clock is the end-of-run snapshot, where the numbers are right, so this only appears on Replay, Play and Go to. Those are the controls a judge will use.

**Fix:** Preferred: add `sla_hours` to `StageLogEntry` in `prism/contract.py`, regenerate fixtures, and use `entry.sla_hours` in `slaPctAt`. If the contract cannot change this phase, show only "Time in stage" (which is correct, because it is a duration) and hide the limit and percent whenever `row.stage !== deal.stage`:
```ts
const sameStage = row.stage === deal.stage   // limit is only known for the final stage
// Board card and SummaryPanel: render fmtDuration(...) alone when !sameStage
// stageLimit(): ignore rows where r.stage !== r.deal.stage
```

## Warnings

### WR-01: Live shape: an open stage-log entry shows its full `why` before the hold or decision happened

**File:** `ui/src/time/timeview.ts:197-206`
**Issue:** `stageLogAt` keeps `why` whenever `exited_at == null`, on the assumption that such an entry "describes where the deal stands". The engine does not keep `why` that simple. `stage.py:477-481` appends "Frozen {time}: a fraud hold was requested..." to the open entry's `why` when a deal is frozen, and `stage.py:450` appends the Fraud Ops answer with its time. Neither sets `exited_at`. For a held deal in live mode, scrubbing to a time before the freeze therefore shows the hold text in the stage log before `flagged_at`. The mock hides this because its Bayou and Juniper entries carry `exited_at` plus `decision: "held"`, a shape the engine does not produce.
**Fix:** Do not show an open entry's `why` that was rewritten after entry. Either have the engine keep the entry-time reason in a separate field (for example `why_entered`) or show only the entry-time prefix. At minimum, blank the hold sentence before `fraud.flagged_at`.

### WR-02: Live shape: declined or stopped deals hide the decision forever and keep accruing SLA; released holds are not subtracted

**File:** `ui/src/time/timeview.ts:108-118,203`
**Issue:** `stage.py:417-424` ends a deal on a decline with `entry.decision = m.option` and `rt.terminal_at = at`, but leaves `exited_at = None`. Two things go wrong in the UI.
1. `stageLogAt` hides `decision` for every entry with `exited_at == null`. The decline never appears, and the screen reads "Decision: no decision recorded yet" for a deal that was declined.
2. `slaPctAt` only stops the clock at the last entry's `exited_at`. The engine (`sla.py:129-136`) also stops it at `terminal_at` and subtracts `frozen_total`, which covers a released hold (`stage.py:602` clears `frozen_at`). The UI keeps counting, so a declined deal turns amber and climbs past 100%. A deal whose hold was released shows an inflated percent. `smoke.ts` would flag both, but it only runs at the end-of-run clock.

The contract gives the UI no `terminal_at` and no frozen total, so a client-side re-derivation cannot be exact.
**Fix:** Take SLA stop points from the data. Either add `sla_stopped_at` and `sla_frozen_hours` to the detail contract, or have the engine write the decline time into `exited_at` (and a distinct `decision`). In `stageLogAt`, show `decision` when it is non-null and the entry's decision time has passed.

### WR-03: An item answered in the fixture but earlier than its answer time looks answerable, and every click ends in a 409 dead end

**File:** `ui/src/time/timeview.ts:154-160`, `ui/src/components/app/Inbox.tsx:109,122-125,176-201`
**Issue:** `inboxAt` rewrites a fixture-answered item to `status: 'pending'` when `answered_at > t` and drops the raw status. In the fixtures, `inbox-005` (Mama Rosa's credit decision, sent 11/02 10:15, answered 11/02 11:50) is answered at end of run. Scrub the clock to 11/02 11:00: the item appears in Pending with Approve, Decline and Request more information buttons. Every click calls the mock, which replies 409 "already answered". The pane then says "This request was already answered. The list has been refreshed." The refetch returns the same data, so the buttons stay, and nothing is recorded. The user is stuck in a loop on a button that cannot work. A 409 never writes to the overlay, even though the server has just said the request is answered.
**Fix:** Keep the raw status on the view (`serverAnswered: boolean`) and treat `serverAnswered` as not answerable (show "Answered later in the run" instead of buttons). On 409, record a session overlay entry for the item (answer unknown) or hide the buttons, so a second click cannot happen.

### WR-04: Moving the clock backwards always fails the sync call, so a persistent "clock could not be set" banner appears

**File:** `ui/src/state/clockStore.ts:61-68,141-145`, `prism/api/app.py:74-78`
**Issue:** Every clock change calls `postAdvance(now)` with an absolute target. The API (mock and, per the contract comment, presumably live) answers 422 for any `to` earlier than the server's current clock: "use /api/clock/replay to go back". The mock clock is fixed at 11/04 18:00. So Go to a time before 11/04 18:00, Next event after a scrub back, or Pause during a Replay (which restarts at 11/02 08:00) all produce the 422. The UI then shows "The clock could not be set on the server. The screen shows ...". In the demo this reads like a failure during the main replay flow.
**Fix:** For a backwards move, call `postReplay()` first and then `postAdvance(target)`; or track the last server-confirmed time and use replay when `target < lastSynced`. Do not show `syncError` for the mock's stateless clock (treat 422 from `advance` as "server clock is ahead", not an error).

### WR-05: Duplicate React keys for alerts and requests that the live engine emits

**File:** `ui/src/components/app/DealDetail.tsx:245,296,182`
**Issue:** Row keys are `${r.type}-${r.at}` for requests, `${a.at}-${a.level}` for alerts and `${e.stage}-${e.entered_at}` for stage entries. `sla.py:ladder_alerts` (about line 100) emits the stage alert as separate entries for the owner and the RM (same `at`, same `level`, different `to`). The mock has one recipient per alert, so it never collides. In live mode the alerts table gets duplicate keys, which React warns about, and updates can drop or duplicate a row when the clock moves. The same can happen for two requests of one type at the same minute.
**Fix:** Include the recipient and message in the key, or the index after a stable sort: `key={`${a.at}-${a.level}-${a.to}`}` and `key={`${r.type}-${r.at}-${r.to}`}`. The detail alerts have no `id`, so a compound key is the only option.

### WR-06: Keyboard focus ring is invisible on the navy clock bar

**File:** `ui/src/index.css:142-145`, `ui/src/components/ui/button.tsx:8-20`, `ui/src/components/ui/input.tsx:8`, `ui/src/components/app/ClockBar.tsx:14,77-124`
**Issue:** The only focus style is the global `:focus-visible { outline: 2px solid var(--color-navy); outline-offset: 2px }`. `button.tsx` and `input.tsx` add no focus classes. On the bar that rule draws a navy ring 2px outside a white button onto a navy background (contrast 1.00:1). Seven buttons and the Go to input are therefore invisible when focused by keyboard (WCAG 2.4.7). Only the Replay button (`focus-visible:outline-sky`) and the rail links are fixed. The restyle commits added the navy bar without adjusting the global ring.
**Fix:** Scope a sky ring to the bar: add `[&_button:focus-visible]:outline-sky [&_input:focus-visible]:outline-sky` to `navyBarClass`, or use `outline-sky` as the global ring colour with a navy inner ring (`box-shadow`).

### WR-07: One contract-valid time string the UI cannot parse blanks the whole app

**File:** `ui/src/time/timeview.ts:53-61,76-78`, `ui/src/components/app/Badges.tsx:43-44`, `ui/src/components/app/ClockBar.tsx:46`, `ui/src/main.tsx:14-20`
**Issue:** The UI accepts only `YYYY-MM-DDTHH:mm-06:00`. The contract validator (`parse_sim_time`, `contract.py:64-72`) accepts any ISO string that contains `T` and ends in `-06:00`, including seconds. The engine's own writer emits minutes only, but extracted values flow through unchanged (for example `needed_by` taken from a document). `simToMs` and `fmtSimTime` throw, and several render paths call them with no guard (`NeededByBadge`, the Summary panel, `ClockBar`, `boardAt`). There is no error boundary, so a single deal with `needed_by: "2026-11-06T15:00:00-06:00"` unmounts the whole React tree. `sortBoardRows`, `nextEventAfter` and `factValueText` already guard with `SIM_RE`, so the pattern is known but not applied everywhere. (Likelihood in live mode is uncertain; the failure is total.)
**Fix:** Accept optional seconds in `SIM_RE` (`(?::\d{2}(?:\.\d+)?)?`) and add a top-level error boundary that renders a neutral "Could not display this screen" with a Retry, so one bad value cannot blank the app.

### WR-08: Pending count differs between the rail badge and the Pending tab

**File:** `ui/src/components/app/Inbox.tsx:326-332,361`, `ui/src/time/timeview.ts:166-168`, `ui/src/App.tsx:40`
**Issue:** The rail badge uses `pendingCount`, which excludes items answered in this session. The Pending tab count uses `splitInbox`, which filters on `status === 'pending'` only. After answering an item and scrubbing the clock back before the answer, the rail says 3 and the tab says 4, and the item sits in the tab with a "answered in this session" note. Two numbers for the same thing on one screen misstate the queue.
**Fix:** Pick one rule. Either filter `!i.answeredInSession` in `splitInbox` (and show those items under Answered with their note), or make `pendingCount` count them.

### WR-09: The in-flight guard lives in the pane, so switching items mid-request allows a second submit

**File:** `ui/src/components/app/Inbox.tsx:106,108-110,389-397`
**Issue:** `inFlight` is a `useRef` inside `Pane`, and `Pane` is keyed by `selected.id`. Click Approve on item A, then select item B before the response, then reselect A. The old pane unmounted with its ref, and the new pane has `inFlight = false`. The item is not yet in the answers store, so the buttons are enabled and a second POST goes out. The mock does not care. A live engine answers the second POST with 409, which then shows the confusing 409 text from WR-03 while the first request succeeds and records the answer.
**Fix:** Hold in-flight ids in the answers store (or a module-level `Set`) and check it in `send`: `if (inflightIds.has(item.id)) return`.

### WR-10: Percent rounding is not half-up for exact halves, and money shows `$1,234.5`

**File:** `ui/src/lib/format.ts:15,28`
**Issue:** `fmtPct` is `Math.round(fraction * 100)`. The fraction is built by float division, so exact halves land just below .5. I swept SLA limits of 1.5, 4, 8, 24, 48 and 72h at every whole minute: 26 values show one point low, for example a 4h limit at 138 minutes (57.5%) shows 57% and the server's half-up rule gives 58%; an 8h limit at 276 minutes shows 57% instead of 58%. The same inexactness makes `scripts/smoke.ts:30` report a false mismatch against `sla_pct`. Separately, `fmtMoney(1234.5)` gives `$1,234.5` because `minimumFractionDigits: 0` with `maximumFractionDigits: 2` prints one decimal; a currency amount with cents should always show two decimals.
**Fix:** Compute in minutes with integer maths: `Math.floor((2 * minutes * 100 + limitMinutes) / (2 * limitMinutes))`. For money use two formatters: whole dollars with 0 digits, otherwise `minimumFractionDigits: 2`.

## Info

### IN-01: Fraud panel shows "Flagged, not held" regardless of the clock

**File:** `ui/src/components/app/DealDetail.tsx:369-373`
**Issue:** The `f.flagged && !f.held` branch has no time check, unlike the held branch, so it shows a flag before `flagged_at`. No fixture reaches it (a flagged deal in the fixtures is also held).
**Fix:** Gate it: `f.flagged && f.flagged_at != null && simToMs(f.flagged_at) <= simToMs(now)`.

### IN-02: A deal that has not arrived still shows its legal name

**File:** `ui/src/components/app/DealDetail.tsx:397-412`, `ui/src/components/app/DealDetail.tsx:457-459`
**Issue:** Opening `#/deals/<folder>` before the deal's first stage entry renders the legal name in the breadcrumb, the heading and the document title. The folder is in the URL anyway, but the legal name comes from the future.
**Fix:** Show the folder only for a not-yet-arrived deal.

### IN-03: "Open for ..." keeps counting on a held deal while the SLA row is frozen; held deals never show "Current"

**File:** `ui/src/components/app/DealDetail.tsx:187-192`, `ui/src/time/timeview.ts:201`
**Issue:** The stage log prints `nowMs - entered_at` for an open entry. For a held deal Summary "Time in stage" is frozen at the hold while the log's "Open for" keeps growing, so the two numbers on one screen disagree. In the mock, a held deal's entry has an `exited_at`, so it shows "Exited" and no "Current" tag for a deal that is still sitting in that stage.
**Fix:** Use `fmtDuration(row.slaFraction * deal.sla_hours * HOUR_MS)` for the current entry and tag the last entry "Current" when the deal is held.

### IN-04: Confirmation copy and a caption hard-code "mock data"

**File:** `ui/src/components/app/Inbox.tsx:67`, `ui/src/components/app/DealDetail.tsx:345`
**Issue:** "The deal stays frozen in the mock data." and "The mock data does not change the hold." become false statements at the live switch, and nothing flags them for Phase 7.
**Fix:** Drive the wording from one `MOCK_MODE` constant, or word it for both ("Releasing here does not change the engine's hold yet").

### IN-05: "Everything is waiting on borrowers or the clock" shows when every request is answered

**File:** `ui/src/components/app/Inbox.tsx:376-379`
**Issue:** The empty Pending body appears whenever requests are visible but none is pending, including the case where all were answered. The sentence is in 02-UI-SPEC, so the build matches the spec, but the claim is untrue for that case.
**Fix:** Use "All requests sent so far have been answered" when `answered.length === view.length`.

### IN-06: `audit.ts` does not enforce the amber rule and misses several red/utility paths

**File:** `ui/scripts/audit.ts:26-40`, `ui/src/components/app/Board.tsx:50`
**Issue:** Red is policed (`hold` and `destructive` only in Badges, `components/ui/` and `index.css`). Amber is not policed at all: there is no rule for the `risk` token, so any file can use `text-risk` or `bg-risk-soft` and the audit stays green. Today every use is legitimate (SLA over 100%, needed-by at risk or overdue, escalation edge). The red regex also skips `accent-`, `decoration-`, `caret-`, `from-/to-/via-` and arbitrary values such as `bg-[var(--color-hold)]`. Class names assembled at run time and inline `style={{ color }}` are invisible to a line regex. The mention of sky ("highlight on navy only") is enforced as a hex ban, not as a usage rule.
**Fix:** Add `risk` (amber) to a rule with an allowlist (`Badges.tsx`, `Board.tsx`, `DealDetail.tsx`, `AlertsFeed.tsx`), extend the red utility list, and add rules for `style={{` colour keys and `var(--color-hold|risk)`.

### IN-07: Dead code

**File:** `ui/src/lib/format.ts:36-50`, `ui/src/labels.ts:141-152`, `ui/src/state/uiStore.ts:7-10`, `ui/src/state/answersStore.ts:6,18`
**Issue:** `fmtSimDay`, `confidenceWord`, `confidenceTitle` and `stageOwnerRole` are never used outside their tests. `openDeal`, `showInbox` and `showAlerts` are used only by `uiStore.test.ts` (components navigate through `<a href>`). `SessionAnswer.note` is stored but never displayed, though the store comment says it is kept "so it can be shown back".
**Fix:** Delete them, or render the note in the pane's answered line.

### IN-08: Contrast and affordance on the navy bar

**File:** `ui/src/components/app/ClockBar.tsx:106`, `ui/src/components/ui/button.tsx:15,22`
**Issue:** On hover the Replay button is `bg-sky/85` over the navy bar, which blends to about #648BB3; navy text on it is 4.05:1, below AA for 14px bold. Separately, a disabled outline button on the bar is a white pill with grey text, almost identical to an enabled one, so "+1h" at end of run looks clickable.
**Fix:** Use `hover:bg-sky` (no alpha) or `hover:brightness`; give disabled bar buttons a visibly different fill (`disabled:bg-surface/60`).

### IN-09: Transport edge cases

**File:** `ui/src/api/client.ts:35-57`, `ui/src/main.tsx:10`
**Issue:** A real 500 with an empty body is reported as "The API is not reachable" (`client.ts:52`). There is no fetch timeout or abort, so a hung engine leaves "Loading" forever. `retry: 1` also retries 404 and 503 responses, which delays the error by the back-off for no benefit.
**Fix:** Only map 502, 503 and 504 with empty bodies to the unreachable message; add `AbortSignal.timeout(15000)`; set `retry: (n, e) => !(e instanceof ApiError && e.status < 500) && n < 1`.

### IN-10: `smoke.ts` can pass vacuously and stops on the first bad deal

**File:** `ui/scripts/smoke.ts:20-36`
**Issue:** Zero deals prints `SMOKE OK deals=0`. A single `getDeal` failure jumps to the outer catch and skips every other deal. It compares only at the live clock, so it cannot see CR-01 or WR-02 (both appear only at earlier clock times). It compares rounded floats (see WR-10).
**Fix:** Fail when `deals.length === 0`; wrap each `getDeal` in its own try; also sample a few times per deal (for example each `entered_at`) against a server that accepts `?at=`.

### IN-11: Accessibility details

**File:** `ui/src/components/app/Inbox.tsx:114,166-174`, `ui/src/components/app/ClockBar.tsx:110-124`, `ui/src/App.tsx:61`, `ui/src/components/app/Primitives.tsx:38-44`
**Issue:** Focus is lost after Send and Confirm (the confirmation or buttons unmount and nothing receives focus). The "Answered: ..." line is `role="status"` but is inserted with its content already present, which many screen readers do not announce. Enter in the Go to field does nothing because the control is not a `<form>`. `aria-label` on the plain pending-count `<span>` in the rail is ignored by most assistive tech (the visible number is read, without "pending"). `NullValue` is an em dash with only a `title` tooltip, which is not exposed on touch or by all screen readers.
**Fix:** Move focus to the answer line (`tabIndex={-1}` plus `.focus()`) after a send; wrap Go to in a `<form onSubmit>`; add `<span className="sr-only">Not found in documents</span>` inside `NullValue`; use `role="status"` on a container that already exists before the text changes.

---

_Reviewed: 2026-11-08T06:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

## Fix status

Applied 2026-11-08 by gsd-code-fixer, in the main checkout (the UI gates need `node_modules` and the running mock API, which a fresh worktree does not have). Tests: 85 before, 97 after. Build, audit, lint (only the two known react-refresh warnings) and smoke pass after each fix.

| Finding | Status | Commit |
|---------|--------|--------|
| CR-01 | fixed | c7b4feb |
| WR-04 | fixed | cb8f674 |
| WR-03 | fixed | 605307b |
| WR-09 | fixed | 605307b |
| WR-06 | fixed | 2a4d74d |
| IN-08 | fixed | 2a4d74d |
| WR-07 | fixed | ed3cd06 |

- **CR-01.** The contract has no per-stage limit and `StageLogEntry` has no `sla_hours`, so the preferred fix (a contract change) was not made. A stage's limit is now taken from the deals that end in that stage, only when they all agree (Intake 8h, Credit 48h, Committee 48h in the fixtures). A deal's own final stage always uses its own `sla_hours`. If a past stage has no such deal, or the deals disagree (delegated committee limit), the SLA shows a dash and the column header drops the limit. Time in stage is now a plain duration. Lone Star Dental at Intake on Tue 11/03 12:00 CT reads 3h 30m / 8h, 44%. Needs human verification: the inferred limit is only as good as the "deals ending in a stage share its limit" assumption, so a contract field (`sla_hours` per stage log entry) is still the clean fix for Ezekiel.
- **WR-04.** No Python change. The mock clock is stateless, so replay-then-advance alone would still 422 against its fixed fixture time. The store therefore tracks the server clock it last saw, replays first on a backward move, sends the same absolute target (D-21 kept), and treats a 422 from advance as "server clock is ahead", not an error. Other failures still show the banner.
- **WR-03 / WR-09.** One commit, since both touch `Inbox.tsx` and the answers store. Items the server has already answered no longer show buttons before their answer time ("answered later in the run"); a 409 is remembered so the buttons stay hidden. The in-flight guard is now per item id in the answers store.
- **WR-06 / IN-08.** Sky focus ring and a dimmed, unfilled disabled look on the navy bar.
- **WR-07.** Seconds (and fractions) now parse; a neutral error boundary wraps the main view. The boundary itself has no automated test (no DOM test harness in the project).

Not touched, as instructed: WR-01, WR-02 (need Ezekiel) and every other finding.
