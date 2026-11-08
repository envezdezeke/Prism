---
phase: 02-pipeline-cockpit-ui-on-mock-data
plan: 05
subsystem: ui
status: complete
completed: 2026-11-08
branch: ui/hero
commits: [b19a0b3, 2086ae0, a21f575]
requirements-completed: [UI-06 (early, on mock data)]
tech-stack:
  added: [react-force-graph-2d 1.29.2]
---

# Plan 02-05 Summary: Fraud graph hero view

## Built
- Routes `#/graph`, `#/graph/{clusterId}`; rail item "Fraud graph".
- `src/graph/graphview.ts` (pure, 7 tests on the fixtures): clock-gated nodes and edges, ring + one-hop focus, lit ring entities (shared by 2+ ring deals, rarity >= 0.5: preparer, phone, PDF producer; the common bank stays neutral), background deals, cluster hold time (first `flagged_at`), latest hold, red-team totals.
- Dark investigation scope in `index.css` under `:root[data-view='investigate']`, switched on by `FraudGraph.tsx`; canvas colours read from CSS variables in `palette.ts`.
- `GraphCanvas.tsx`: stable layout objects (`layoutCache.ts`, deterministic seeding), centre gravity, weight-driven edges, "kind · rarity" labels, canvas halo on lit ring only, 600ms fade-in for newly visible edges, Focus ring / Whole graph, refit when new nodes appear. Force-graph hover tooltips disabled (they inject HTML).
- `EvidenceDrawer.tsx`: edge and node evidence, sharers list (click to jump), six families with evidence; Investigator tab with an Advisory badge and the trace steps; red-team chip "5 bypasses / 30 attempts" (computed from the fixture, not the hoped-for "0 bypasses").
- Audit gate updated (new bans: animation libs, other graph/chart libs, innerHTML, rgb/hsl literals, other data-view scopes, colours near #7399C6). One graph tint was moved because the new rule caught it.
- `/api/graph` already existed in the mock; added `tests/test_api_graph.py` (4 tests).

## Visual check
Rendered against the mock API (port 8011) with Vite dev in Chrome at 1440x900: ring view at Wed 6 PM (held, red), Tue 10 AM (forming, neutral), edge and node drawer, Investigator tab, Whole graph. Not checked at 1280x800 and no Playwright run.

## Cut or caveats
- Source document and page per edge: the contract's `GraphEdge` has no such fields, so the drawer shows the evidence sentence only.
- Families come from the end-of-run cluster (captioned so); the mock has no time-stamped family state.
- The force layout is not pixel-stable between reloads; labels can overlap when Bayou and Juniper settle close together.
- One lint warning remains (setState in the layout effect that reads the palette after the dark switch).
