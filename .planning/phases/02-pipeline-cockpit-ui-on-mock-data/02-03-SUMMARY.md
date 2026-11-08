---
phase: 02-pipeline-cockpit-ui-on-mock-data
plan: 03
subsystem: ui
tags: [react, typescript, zustand, tanstack-query, node-test, hash-routing, audit]

requires:
  - phase: 02-pipeline-cockpit-ui-on-mock-data
    provides: plan 02 board, clock, primitives, badges, format helpers and the audit gate
provides:
  - Plain-words label module (issues, request types, options, fact fields and values, alert levels)
  - Role-label people module with an empty DIRECTORY (D-22) and the raw id only in tooltips
  - Encoding-safe hash route (#/deals/{folder}) and a zustand store synced to the URL hash
  - Deal detail screen: header, summary, sourced facts, issues, stage log, requests, alerts, sober fraud panel
  - Pure clock-gated views stageLogAt, requestsAt and a generalised alertsAt
  - One-item left rail with the Prism wordmark
affects: [02-04, phase-07-live-switch]

actuals:
  tokens: 12500
  tasks: 3
  commits: 4
plan_head_before: 1e8d0ff162edd922ef7dbc42198e6e9aaf3a2a13
plan_head_after: 9ee86e083dfda2911f53af20b2e1e7bbcba92340

tech-stack:
  added: []
  patterns:
    - "Screens are pure functions of (fetched detail, clock now): DealDetailView reuses boardAt, so board and detail agree at every clock time"
    - "Deal links are same-app hash anchors built only from encodeURIComponent(folder); the hashchange listener moves the route"
    - "Open stage-log entries hide exit, decision and the exit's why until the clock reaches the exit"

key-files:
  created:
    - ui/src/labels.ts
    - ui/src/labels.test.ts
    - ui/src/people.ts
    - ui/src/people.test.ts
    - ui/src/route.ts
    - ui/src/route.test.ts
    - ui/src/state/uiStore.ts
    - ui/src/state/uiStore.test.ts
    - ui/src/components/app/DealDetail.tsx
    - ui/src/data/queries.ts (first time tracked, see deviation 9)
  modified:
    - ui/src/App.tsx
    - ui/src/components/app/Board.tsx
    - ui/src/components/app/Primitives.tsx
    - ui/src/time/timeview.ts
    - ui/src/time/timeview.test.ts
    - .gitignore

key-decisions:
  - "02-UI-SPEC copy and layout won over the plan wherever they differ (see deviations)"
  - "Linked deals and board cards are hash anchors, not buttons, so Back, middle-click and keyboard work natively"
  - "The why of a stage entry that exits later is treated as future information and hidden until the exit"

requirements-completed: [UI-04]

duration: ~2h wall clock including a rate-limit pause
completed: 2026-11-08
status: complete
---

# Phase 2 Plan 03: Deal detail, navigation and plain-words labels Summary

**Clicking a board card opens a hash-addressable deal page (`#/deals/{folder}`) showing sourced facts, open and resolved issues in plain words, the clock-gated stage log with each why, human requests, alerts and a sober fraud panel, with staff shown as role labels and the raw id only in tooltips.**

## Commits

| Task | Commit | What |
|------|--------|------|
| 1 | 331697a | labels.ts, people.ts, route.ts and their tests, tests first (RED confirmed on missing modules) |
| fix | 9a27fb0 | Track `ui/src/data/queries.ts` and anchor the `data/` ignore rule to the repo root; adds `useDealDetail` |
| 2 | 8899d29 | uiStore, rail with Prism wordmark, board cards as links, DealDetail header, summary and facts |
| 3 | 9ee86e0 | `stageLogAt`, `requestsAt`, generalised `alertsAt` (tests first, RED confirmed), issues, stage log, requests, alerts, fraud panel |

`commits: 4` is measured from the ledger. The plan's first three commits were rebased onto Ezekiel's newer main after a rate-limit interruption (hashes changed from 71fdc06, d0739d9, c2519b1), so the ledger base was reset to the parent of the first plan commit (1e8d0ff).

## Results (mock API on :8000 and Vite dev on :5173 left running)

- `npm --prefix ui test`: `ℹ tests 66 / ℹ pass 66 / ℹ fail 0` (plan 02's 35, plus 31 new: labels 11, people 7, route 4, uiStore 5, timeview 5, with the earlier alertsAt feed test unchanged).
- `npm --prefix ui run build`: `built in 113ms`, no `error TS`.
- `npm --prefix ui run lint`: exit 0, only the two accepted react-refresh warnings in components/ui.
- `npm --prefix ui run audit`: `AUDIT OK files=36 dist=14`.
- `npm --prefix ui run smoke`: `SMOKE OK deals=5 clock=2026-11-04T18:00-06:00`.
- `curl localhost:5173/src/components/app/DealDetail.tsx`: 200 (Vite compiles it).
- `grep -rn "data/" ui/src/people.ts`: no output. `grep -c DIRECTORY ui/src/people.ts`: 3.
- Real `DealDetailView` rendered server-side (Vite SSR) against live API data:
  - Lone Star Dental: nine fact rows, chips `certificate_of_formation.pdf` etc., confidence `98%`, `90%`, `88%`; summary Stage Credit, Time in stage `28h 00m`, SLA `58% of 48h`, Needed by `Fri 11/06 3:00 PM CT · At risk`; Relationship manager reads "Relationship manager".
  - Bayou Bistro & Grill at `2026-11-03T11:00`: Fraud status "No hold or watch flag.", Decision `—`, Why `—`, "No requests on this deal as of Tue 11/03 11:00 AM CT.", SLA 38% of 8h. At `11:35`: `Held: fraud review`, "Frozen at Intake as of Tue 11/03 11:30 AM CT", the reason, Linked `Juniper Creek Nursery`, Decision `Held`, the `Fraud hold` request to Fraud Operations (Pending), SLA 44% frozen. At `07:00`: "Bayou Bistro & Grill LLC has not arrived as of Tue 11/03 7:00 AM CT." with Back to pipeline.
  - Juniper Creek Nursery: `Bayou Bistro & Grill` is `<a href="#/deals/Bayou%20Bistro%20%26%20Grill">`, `H-0000-001` is plain text.
  - Mama Rosa's Kitchen at the end: `Missing page: bank statement, Sep 2026` under Resolved, "No open issues.", Approve answer in `text-ok`, Escalation row with `border-risk` and "Escalation contact". At `11:00`: only Intake exited, Credit Current with Open for `1h 00m`, the credit_decision request Pending.
  - Cedar Ridge Welding: `Missing document: EIN letter · MISSING_DOC:ein_letter`, neutral `Watch`, "Shown for review. Not held." with the "As of end of run" caption and no reason.
  - Colour classes seen per page: `text-navy` on links everywhere; `bg-hold-soft`/`text-hold` only on the Held badge pages; `text-ok` only on the Approve answer; `border-risk`/`text-risk` only on escalation edge, at-risk needed-by and SLA over 100%.
  - Visible staff ids outside title attributes: none, except `committee.osei` inside an engine-written escalation message (see Known Issues).

## Deferred visual check

No Chrome or Playwright here, so no screenshots at 1440x900 and 1280x800 and no live click-through of: clicking a board card and reloading on `#/deals/...`, browser Back, focus rings on the new links, the sticky side column, the escalation edge rendering in the collapsed-border table, and the loading and error states of `DealDetail` (a server-side render of the stateful component failed on a duplicate React Query instance under Vite SSR; those branches are simple and use the same primitives as the board, but were not executed). The hash store is covered by five tests with a stubbed `location`. Jesse can confirm on :5173; plan 04's human check should include it.

## Deviations from Plan

1. **[Design contract] 02-UI-SPEC over plan copy and layout**, as the plan header instructs:
   - Route is `#/deals/{folder}` (plan said `#/deal/`), anchors with the encoded folder.
   - Breadcrumb `Pipeline / {legal name}` with a navy link, not a back button with an ArrowLeft icon (the UI-SPEC icon list excludes it).
   - Confidence is a whole percent, never a word (UI-SPEC row 5); `confidenceWord` is unused by this screen.
   - No Credit officer summary row (UI-SPEC row 10), so the acceptance line about it does not apply.
   - Stage log shows "Current" and "Open for {duration}" (plan: "In stage"); requests are a Sent/Type/To/Message/Answer table with "Pending" or `{option} · {time}`; alerts are oldest first with columns Time, Level, To, Message.
   - Empty copy: "No resolved issues." (plan "None."), "No requests on this deal as of {time}.", "No alerts on this deal as of {time}."; subheading "Resolved".
   - Issue wording: "Known-fraud check failed: shell address check" and `EIN letter` / `guarantor ID` (plan used longer descriptive phrases and "IRS EIN letter"). Documents with no label in the UI-SPEC (application, tax return, financial statements, equipment quote, certificate of formation) show their code with underscores as spaces, adding no words the contract does not carry.
   - Fraud panel copy: "Frozen at {stage} as of {time}", reason, "Linked"; neutral outline `Flagged` badge for flagged-not-held; "No hold or watch flag." otherwise (plan had separate Stage at flag and Flagged rows).
   - Section headings are 14px weight 600 (plan said 16px).
2. **[Design contract] Roles and tooltips**: `roleForAlert(level)` returns "Stage owner" for an alert and "Escalation contact" for an escalation (plan: stage owner role by stage); `personLabel` title is "Staff id {id}" (UI-SPEC tooltip copy); `isClearedAnswer` is true for `approve` only (UI-SPEC: green is approvals only), not `release_hold`; `DIRECTORY` is empty (D-22), so the plan's "16 entries" test became "empty". `personLabel` takes an optional directory argument so the name branch is tested with a throwaway map holding no real names. `stageOwnerRole` is exported as the plan lists it but this screen does not use it.
3. **[Design contract] Linked deals and board cards are anchors** to the hash route, not buttons (UI-SPEC allows same-app hash routes built from encoded folder names; the coordinator asked for links). The plan's `openDeal` key link is therefore satisfied by the hashchange listener; `openDeal` and `showPipeline` exist on the store and are used by the Back to pipeline button.
4. **[Rule 1 - Bug] Stage-log `why` leaked the future**: fixtures write each entry's `why` as the reason it exits, so Bayou at 11:00 would have shown "fraud hold: rare entities shared..." before any hold. `stageLogAt` now hides `why` for an entry that exits after the clock time (it keeps the `why` of an entry that never exits, which describes the current state). Test-pinned; the screen shows `—` with the tooltip "Recorded when the stage exits".
5. **[Rule 3 - Blocking] `alertsAt` signature**: it takes an optional third argument `'newest' | 'oldest'` (default newest) so the detail list can be oldest first without reversing arrays.
6. **[Plan error] "Mama Rosa's Intake and Credit exited at 11:00"** is false in the fixture (Credit exits 12:00). Tests assert the real behaviour: at 10:30 and 11:00 Intake is exited and Credit is open.
7. **[Rule 2] Document title** is set to the page name (`Pipeline · Prism`, `{legal name} · Prism`) per UI-SPEC; the plan did not list it.
8. **Extra file `uiStore.test.ts`** (5 cases) beyond the plan, to prove the hash synchronisation without a browser.
9. **[Rule 1 - Bug, pre-existing from plan 01] `ui/src/data/queries.ts` was never committed.** The root `.gitignore` rule `data/` also matched `ui/src/data/`, so a fresh clone could not build. Changed to `/data/` (the participant data folder is the root `data/`, which stays ignored; verified `git status` shows no new untracked files) and committed `queries.ts` in 9a27fb0.

## Auth gates

None.

## Known Stubs

None. Every rendered value comes from engine data or a pure derivation. Inbox answer overlays are plan 04's job and the requests table reads the fetched answers only.

## Known Issues

- Engine-written message text is shown as given (D-01), so the fixture escalation message "...no response from committee.osei. Please step in." shows a raw staff id as visible text inside the message body. All structured recipient fields use role labels. This disappears when the live engine writes names (Phase 7) and was not altered in the UI.
- The fixtures' unlabelled document and mismatch codes show with underscores replaced by spaces; confirm the wording with Jesse if a fuller label is preferred.

## Threat Flags

None. T-02-09 to T-02-11 are implemented: all engine strings render as React text (the audit rejects the raw-HTML prop); the only hrefs are `#/pipeline` and `#/deals/` plus an `encodeURIComponent`-ed folder; `parseHash` decodes inside a try and falls back to the pipeline (test-pinned with `%E0%A4%A`); `DIRECTORY` is empty and `people.test.ts` asserts it and that `people.ts` has no data path or contact detail.

## Notes for plan 04

- **Rail:** `NAV_ITEMS` in `App.tsx` holds only Pipeline; add Inbox and Alerts when those screens exist. The rail's active test is `isActive(item, currentView)`; extend `Route` in `route.ts` (`parseHash` and `buildHash` are the only places to touch) with `#/inbox` and `#/alerts`, and the `App` view switch.
- **Overlay hooks:** `RequestsSection` in `DealDetail.tsx` renders `requestsAt(deal.human_requests, now)`; apply the overlay answer before that call (join on deal, type, at) so Answer shows `Pending` or the option and time. The fraud panel needs the UI-SPEC caption "Release recorded in this session. The mock data does not change the hold." under the Held badge when the overlay holds a `release_hold` for the deal. Pass the overlay's `answered_at` strings as `extra` to `nextEventAfter` in `ClockBar`.
- **Reusable:** `DealLink`, `PipelineLink`, `LINK_CLASS` in Primitives (use `DealLink` for the Deal column in the inbox and alerts feed); `requestTypeLabel`, `optionLabel`, `alertLevelLabel`, `personLabel`, `roleForRequest`, `roleForAlert`, `isClearedAnswer`; `alertsAt(items, t)` is newest first for the feed.
- **Audit allow-lists:** green is allowed in DealDetail.tsx and Inbox.tsx; it is used once, on the Approve answer.
- **`.gitignore`:** `data/` is now `/data/`; any new folder named `data` inside `ui/` is tracked.
- **Visual check owed** (see above) now covers the board cards as links, the detail page at 1280px and the escalation row edge.

## Self-Check: PASSED

Files verified present: labels.ts, labels.test.ts, people.ts, people.test.ts, route.ts, route.test.ts, state/uiStore.ts, state/uiStore.test.ts, components/app/DealDetail.tsx, data/queries.ts. Commits 331697a, 9a27fb0, 8899d29 and 9ee86e0 verified as ancestors of HEAD.
