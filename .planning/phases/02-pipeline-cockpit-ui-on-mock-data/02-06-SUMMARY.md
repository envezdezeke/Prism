---
phase: 02-pipeline-cockpit-ui-on-mock-data
plan: 06
subsystem: ui
status: complete
completed: 2026-11-08
branch: ui/hero
commits: [44a1793]
---

# Plan 02-06 Summary: Hold beat and polish

## Built
- Held board cards: 2px red left edge, footer "Linked to N deals" and "Investigate ring →" (cluster looked up from `/api/graph`).
- One-shot `hold-pulse` on a card that turns held while the board is open; it does not fire on first render and resets if the clock is scrubbed back before the hold.
- Clock bar: one line for the latest hold within 24 sim hours, on its own row, with an Investigate ring link.
- Deal page fraud panel: navy "Investigate ring →" for a deal in a cluster.
- CSS motion: fade-in (hold line, held badge, alert rows), drawer slide, body colour transition into the dark view; all off under reduced motion.

## Visual check
In Chrome at 1440x900: Go to Tue 11/03 11:00 AM, Play; Bayou and Juniper cards showed the red edge, footer and pulse, and the clock-bar line appeared.

## Caveats
- The pulse fires only if the board is mounted when the hold lands.
- At window widths under about 1250px the board scrolls sideways (unchanged 6 x 160px column minimum).
- The mock rejects clock writes earlier than its fixture time, so the existing "The clock could not be set on the server" caption shows whenever the clock goes back. This is old behaviour, not a regression.
