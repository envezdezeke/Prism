---
phase: 02-pipeline-cockpit-ui-on-mock-data
plan: 04
subsystem: ui
status: complete (trimmed scope, D-32)
completed: 2026-11-08
branch: ui/hero
commits: [e4c6506]
requirements-completed: [UI-05]
---

# Plan 02-04 Summary: Alerts feed and minimal inbox

## Built
- `AlertsFeed.tsx`: newest-first table at the clock time; Level label from `alertLevelLabel`; amber 2px left edge and amber level text on escalations; deal links; empty/error states.
- `Inbox.tsx`: Pending (oldest first) and Answered lists at the clock time; full message, sent time, role label, waiting time; reply buttons from `options` (first navy, rest outline); inline confirm for `decline` and `release_hold`; 409 refetches the inbox, 422 shows the server detail.
- `answersStore.ts` (in-memory overlay) and pure `inboxWithOverlayAt` in `timeview.ts` with a test; `pendingCount.ts` feeds the rail count.
- `postReply` sends exactly `{option}` (note only when non-empty, but the UI has no note field).

## Cut (honest)
- Two-pane inbox layout, segmented Pending/Answered control, optional note input.
- The deal detail's human-request table does not yet show in-session answers (overlay join not wired).
- The 02-04 commit does not build on its own: the client functions it calls landed in the next commit (2086ae0).

## Verify
Part of the branch-wide gates: test 75/75, lint 0 errors, audit OK, build OK.
