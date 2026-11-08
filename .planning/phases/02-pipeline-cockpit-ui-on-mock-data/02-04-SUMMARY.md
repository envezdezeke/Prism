---
phase: 02-pipeline-cockpit-ui-on-mock-data
plan: 04
subsystem: ui
tags: [react, typescript, zustand, tanstack-query, inbox, alerts, session-overlay]

requires:
  - phase: 02-pipeline-cockpit-ui-on-mock-data
    provides: plan 03 deal detail, hash routes, labels, role-label people
provides:
  - In-memory session-answer overlay (answersStore) with pendingCount and requestsWithOverlay
  - postReply client pinned to the contract body shape (option, optional trimmed note up to 500 characters)
  - Inbox screen with Pending and Answered segments, request pane, option buttons, inline confirmations
  - Alerts feed screen
  - Rail with Pipeline, Inbox (pending count) and Alerts
  - Session answers on the deal page's Human requests, release-hold caption on the fraud panel
affects: [phase-07-live-switch]

actuals:
  tokens: 30000
  tasks: 3
  commits: 4
plan_head_before: 6a86e58f25307042e0806e3dab61c80f33971a5f
plan_head_after: 8215fe564f2d8ad8dd9cf5129514262bf749a817

tech-stack:
  added: []
  patterns:
    - "Session answers live in a zustand store and are applied by pure functions (inboxAt, requestsWithOverlay) before the status filter, never written into the query cache"
    - "At most one reply per item per session: an in-flight ref plus the overlay entry; a failed send writes nothing"
    - "Next event includes overlay answered_at times through the extra argument of nextEventAfter"

key-files:
  created:
    - ui/src/state/answersStore.ts
    - ui/src/components/app/Inbox.tsx
    - ui/src/components/app/AlertsFeed.tsx
  modified:
    - ui/src/time/timeview.ts
    - ui/src/time/timeview.test.ts
    - ui/src/api/client.ts
    - ui/src/api/client.test.ts
    - ui/src/route.ts
    - ui/src/route.test.ts
    - ui/src/state/uiStore.ts
    - ui/src/data/queries.ts
    - ui/src/App.tsx
    - ui/src/components/app/ClockBar.tsx
    - ui/src/components/app/DealDetail.tsx

key-decisions:
  - "02-UI-SPEC won over the plan where they differ: Pending/Answered segmented control, input (not textarea) for the note, inline confirmations for decline and release hold, 409 text with 'The list has been refreshed.' plus a refetch, 422 text, green Approved badge, both escalation kinds with an amber border"
  - "The overlay answered time is the UI clock at the click, not any time the API echoes"
  - "The Answered list gets an extra Answer column so the answer and its time are visible without opening the pane"

requirements-completed: [UI-01, UI-04, UI-05]

completed: 2026-11-08
status: complete
---

# Phase 2 Plan 04: Inbox, alerts feed and session answers Summary

**Staff can answer sign-off requests from an inbox in the exact contract shape, see answers stick through an in-memory overlay (rail count drops, deal page updates, clock scrubbing respected), and read an alerts feed with amber borders on escalations only.**

## Commits

| Task | Commit | What |
|------|--------|------|
| 1 | d19a41d | Overlay logic (inboxAt with answers, pendingCount, requestsWithOverlay), answersStore, postReply/getInbox/getAlerts, tests first |
| 2 (WIP) | 907b560 | Routes `#/inbox` and `#/alerts`, uiStore showInbox/showAlerts, useInbox/useAlerts (saved at a rate limit) |
| 2 | d90a4b4 | Inbox screen, clock bar passes session answer times to nextEventAfter |
| 3 | 8215fe5 | Alerts feed, rail entries and pending count, document titles, deal detail overlay and release-hold caption |

`commits: 4` is measured as `git rev-list --count 6a86e58..HEAD -- ui/`. Two unrelated docs commits (07 draft plan, 02 pause handoff) sit inside the plain range and are excluded by the path filter.

## Gate results (mock API on :8000, Vite dev on :5173)

- `npm --prefix ui test`: tests 85, pass 85, fail 0.
- `npm --prefix ui run build`: exit 0, no `error TS`.
- `npm --prefix ui run lint`: warnings only (react-refresh in components/ui, accepted); no errors.
- `npm --prefix ui run audit`: `AUDIT OK files=40 dist=14`.
- `npm --prefix ui run smoke`: `SMOKE OK deals=5 clock=2026-11-04T18:00-06:00`.
- Mock reply check: POST `{"option":"approve"}` to `/api/inbox/inbox-001/reply` returned 200. Dev proxy returns clock and deals JSON.
- `grep -rn "localStorage\|sessionStorage" ui/src`: no output. `grep -c "^import" ui/src/time/timeview.ts`: 0.
- Server-side render of the real Inbox and Alerts components against live mock data:
  - Wed 11/04 6:00 PM: Pending 4, Answered 1; pending rows oldest first (Mama Rosa's committee approval 53h 45m, Bayou fraud hold, Lone Star credit decision, Juniper fraud hold). With an overlay answer for inbox-001 at that time: Pending 3, Answered 2.
  - Mon 11/02 12:00 PM: Pending 0, Answered 1 (inbox-005); 8:00 AM: "No requests have been sent as of Mon 11/02 8:00 AM CT."
  - Alerts at 6:00 PM: Lone Star alert 5:00 PM, Mama Rosa's escalation 4:00 PM (Escalation contact), Mama Rosa's alert 12:00 PM (Stage owner); at 1:00 PM only the 12:00 PM alert; at 11/02 8:00 AM the empty state.

## Deviations from Plan

**1. [UI-SPEC over plan] Copy and layout.** Segmented Pending/Answered control instead of one list with an Answered subheading; note is an `input` with maxlength 500 labelled "Note (optional)"; decline and release hold use the UI-SPEC inline confirmation copy; 409 reads "This request was already answered. The list has been refreshed." and refetches the inbox; 422 reads "The server rejected that option: {detail}"; Approved shown as the green badge; the alerts empty state uses the UI-SPEC copy; Retry appears on network failures only.

**2. [Rule 2 - small addition] Answer column.** The Answered segment adds an Answer column (label and time) so answers are visible in the list.

**3. Commit trailer.** Commits in this resume carry `Co-Authored-By: Claude Sonnet 5.5` (the attribution given for this session) rather than the `Claude Opus 5.5` line the caller specified.

**4. Task 2/3 commit split.** App.tsx needs AlertsFeed to compile, so the Inbox screen and clock bar were committed first (d90a4b4) and App.tsx, the alerts feed and deal detail second (8215fe5). The rail therefore gains Inbox and Alerts in one commit.

## Known Stubs

None.

## Threat Flags

None. Reply options come only from the item's options array (T-02-13); the body is exactly option plus an optional trimmed note (T-02-15); answers and notes stay in memory and are never logged (T-02-16); engine strings render as text only (T-02-17).

## Human check (pending, Jesse)

Not run: no browser available to the executor. The five numbered items of the plan's human-check are listed in the hand-off message and are recorded here as **not yet checked**.

1. Clock/board states: not checked
2. Tue 11/03 3:05 PM hold and inbox fraud-hold request: not checked
3. Inbox answer flow, Network body, rail count, reload restores pending: not checked
4. Deal pages by board click and URL hash, Bayou SLA 44%: not checked
5. Playbook section 6 visual checklist at 1440x900 and 1280x800: not checked

## Self-Check: PASSED

Files exist (Inbox.tsx, AlertsFeed.tsx, answersStore.ts); commits d19a41d, 907b560, d90a4b4, 8215fe5 are on main.
