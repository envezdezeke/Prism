# Phase 7: Fraud Graph, Dry Run and Pitch - Context

**Gathered:** 2026-11-07, by the planner. Draft for Jesse's review. No discuss-phase was run.
**Status:** Eleven plans written (07-01 to 07-11). Every decision marked **ASSUMED** waits for Jesse to confirm or change it. Decisions without that mark are carried from documents already agreed, or were locked by Jesse. Updated 2026-11-08 ~01:00 CT: D-03 and D-04 amended by Jesse (navy and sky palette), D-35 re-coloured to match, the deal-page mirror moved to its own plan 07-11, and the execution map and cut line rewritten for the full plan set.

<domain>
## Phase Boundary

Judges watch the fraud ring light up as the sim clock advances. They see why each link matters and what the agents found, and they see Prism handle a fresh drop of files with no code changes. All of it ends in a recorded demo and a 3-minute pitch submitted by Sun 11:40 CT.

In scope (requirements UI-06, UI-07, DEMO-01, DEMO-02, DEMO-03):
- The fraud graph view: first on `fixtures/graph.json` (mock), then on the live engine.
- The switch of the whole Phase 2 cockpit from mock to live data (`MOCK=0`) at H10 to H10.5.
- The signal-family checklist, the evidence panel and the investigator trace (UI-06).
- The red-team results view (UI-07).
- The dry run: the sample week with the self-score, a synthetic weekend drop and a fuzz run (DEMO-01).
- The sealed record of the blind weekend-drop first run (HANDOFF §3 item 6).
- The clean-checkout run on Jesse's Mac (DEMO-02).
- The pitch, the demo script, the slides, the recording and the Devpost submission (DEMO-03).

Out of scope: any change to the scored engine, the thresholds or the Nemotron agents (Phases 3 to 6). The pipeline board stays the ordered six-column board from Phase 2; the graph does not replace it (D-30).

Clock: H0 = Sat 2026-11-07 15:55 CT. Phase 7 window H9 to H19.75 (Sun 00:55 to 11:40 CT). Gates: H10 engine frozen (01:55), H10.5 UI on live data (02:25), H15.5 agents live (07:25), **H18 feature freeze (09:55)**, H19.75 submit (11:40). Hard deadline 12:00.

</domain>

<decisions>
## Implementation Decisions

### Carried from Phase 2 (all apply; full text in `.planning/phases/02-pipeline-cockpit-ui-on-mock-data/02-CONTEXT.md`)

Precedence for every UI plan here: this file, then 02-CONTEXT.md, then 02-UI-SPEC.md, then 02-RESEARCH.md, then docs/UI_PLAYBOOK.md.

- **D-01:** Accuracy and sturdiness over looks. Show engine data faithfully, never change a value's meaning, and give every view loading, empty and error states.
- **D-02:** Jesse directs the build with Claude Code. Keep it simple: no clever abstractions, no extra state libraries.
- **D-03 (amended by Jesse, 2026-11-08):** Institutional finance look in a bolder sponsor-palette: deep navy `--color-navy` (#0E2846) and sky `--color-sky` (#7399C6, allowed only as a token in `ui/src/index.css`), a solid navy rail and clock bar with a sky rule, navy table header bands, bold navy section headings with a sky left bar. The sponsor's name, logo and fonts stay banned (audit rule "forbidden brand name").
- **D-04 (amended with D-03):** Warm off-white page, white surfaces, warm-gray text and lines, navy as the main colour (rail, clock bar, table bands, headings, actions, focus) with sky as its highlight; no dark theme.
- **D-05:** Red only for fraud holds. Amber only for SLA past 100% and deadlines at risk. Muted green only for cleared or approved.
- **D-06:** Serif for page titles only; sans everywhere else; tabular numerals; money right-aligned.
- **D-07:** Hairline borders, radius at most 6px, 4px grid, dense tables.
- **D-08:** No gradients, glow, glassmorphism, blur or real shadows.
- **D-09:** No emoji; lucide icons only, used sparingly.
- **D-10:** No purple, indigo or violet; no rainbow badges; no hero layouts; no bubble cards.
- **D-11:** No filler text; real banking vocabulary; no navigation to unbuilt screens.
- **D-12:** Restyle shadcn and Base UI to the tokens; never ship the stock theme.
- **D-13:** Sim time in Central, "Tue 11/03 3:05 PM CT"; durations "26h 10m"; never the viewer's time zone.
- **D-14:** Names, not ids, where a name is known; ids in tooltips (superseded for now by D-22).
- **D-15:** Deal identity is legal name plus folder name.
- **D-16:** Fraud shown soberly: red "Held: fraud review" badge with its reason, neutral "Watch" badge.
- **D-17:** Fixture quirks are worked around in the UI, never by asking for fixture changes.
- **D-18:** Board, alerts and inbox are derived on the client from timestamps; values with no timestamp show the end-of-run view with the caption "As of end of run".
- **D-19:** Bundled Source Serif 4 (titles) and Geist (everything else).
- **D-20:** Neutral error states; navy buttons, fraud actions included; no toasts.
- **D-21:** The clock lives in the browser and is read from the API once; inbox replies sit in a client overlay.
- **D-22:** Staff shown as role labels with the raw id in a tooltip; real names were meant to arrive from the engine at the live switch (see D-44).

02-UI-SPEC.md values also carry over: type sizes 12, 13, 14 and a 28px serif title only; the RESEARCH colour values (ink #1C1917, green #067647); no ink-3; no new icons beyond the Phase 2 set. Where 02-UI-SPEC limits navy to actions and the active rail item, the built app follows `ui/src/index.css` and the amended D-03 (navy bands and headings, sky highlights). The one exception is motion on the graph canvas, which D-30 and D-34 now allow.

### Carried from agreed project documents (locked)

- **D-23 (HANDOFF §3, ROADMAP cut list):** Goldman score > Nemotron > UI. Accuracy and sturdiness beat looks. When a gate is at risk, cut in the ROADMAP order: UI polish, then Nemotron extras, then the red-team generator and its view, then the investigator. Never cut the engine, validator, determinism harness, trap suite or self-score.
- **D-24 (HANDOFF §3, decided by Jesse 2026-11-07):** The pitch centerpiece is measured validation. The headline number is the blind weekend-drop first run. If the drop lands too late, the held-out history replay (false flags on good history deals) becomes the headline.
- **D-25 (HANDOFF §3 item 6, §9 item 11; MODEL_DESIGN M20):** On the drop, run the frozen engine and record that first result with its commit before anyone opens the drop's files. Then Jesse labels the drop blind. Only then may anyone fix code, and each later run is logged before and after.
- **D-26 (MODEL_DESIGN M21):** Every number in the pitch, slides, video and Devpost comes from a committed record and names its commit.
- **D-27 (MODEL_DESIGN N8; ROADMAP Phase 7 criterion 5):** The demo runs Nemotron in replay mode (`NEMOTRON_MODE=replay`, the name in `.env.example`) and works with the network off.
- **D-28 (MODEL_DESIGN M2, M8, N1):** Agents advise and never decide. A hold needs F1 plus at least 2 of F2 to F5. F6 is evidence only and never votes. The UI must never suggest an agent made a hold.
- **D-29 (HANDOFF §6 and §9 items 12 and 13):** Pitch language: lead with the consequence, three catches, "strange isn't fake"; describe the method as "unsupervised anomaly detection that learns what normal looks like from a year of history"; say that the agents' tools are real HTTP calls to our API and the sim clock.
- **D-30 (Jesse, Sat ~20:45, locked):** The fraud graph has an **Obsidian-style look**: a free-floating force-directed network with nodes spread out and dispersed, not a left-to-right layout. Deals and entities are both nodes. The fraud ring visibly pulls into a tight cluster while honest deals scatter. Edge width and opacity follow rarity (UI_PLAYBOOK §4). The layout is seeded and deterministic so it never jumps, and it replays on the sim clock. It stays inside the Phase 2 institutional tokens: navy and neutrals, red only for held deals, no glow, no gradients, no dark neon theme. "Obsidian" means the layout and feel, not the colours. **The pipeline board stays the ordered six-column board. Do not plan a graph replacement for it.**

### New decisions (ASSUMED, Jesse to confirm; each has the planner's recommendation)

- **D-31 (ASSUMED, Jesse to confirm): Graph libraries.** `react-force-graph-2d` draws the canvas and handles zoom, pan and clicks (the STACK.md pick). `d3-force` computes the seeded layout off-screen so it is deterministic. Both are installed only after a blocking package check (see Package Legitimacy Audit; `d3-force`'s newest release is 4 days old, so pin the last release that is at least 30 days old). Engine strings never go into the renderer's built-in hover labels, because those render HTML. Recommendation: approve.
- **D-32 (ASSUMED, Jesse to confirm): Replay is computed in the browser.** The UI fetches the full graph once (`GET /api/graph`, no `at`). It shows each edge when the client clock reaches the edge's `first_visible_at`, using the same rule as `GET /api/graph?at=`. A smoke check proves the two agree at every edge time. Reason: playback at 1 sim hour per second would otherwise send a request per tick, and D-21 keeps the clock in the browser. Recommendation: approve.
- **D-33 (ASSUMED, Jesse to confirm): Which nodes are visible at a time.** A current deal appears at its arrival (its first stage-log entry, the Phase 2 rule) or at its first visible edge, whichever is earlier. A history deal or an entity appears with its first visible edge. A current deal with no links still shows as a lone node, so honest deals visibly sit apart. Recommendation: approve.
- **D-34 (ASSUMED, Jesse to confirm): How the seeded layout moves (implements D-30).** There is one layout "keyframe" per moment the graph changes (an edge appears or a deal arrives). Each keyframe starts from the previous one's positions and runs a fixed number of steps with a seeded random source. The positions at any clock time are the last keyframe at or before that time. Scrubbing backwards therefore gives the same picture as playing forwards, and nothing moves between events. Forces: rare links pull hard and short, common links pull weakly and long, all nodes push each other apart, and weak gravity keeps the network on screen. So the ring knots together while honest deals drift apart. Between keyframes, nodes ease to their new positions over 600 ms. This is the only motion in the app, and it is off under prefers-reduced-motion. If time is short (cut tier 1), the ease is dropped and keyframes snap. User dragging is off so the layout cannot be disturbed. Recommendation: approve.
- **D-35 (ASSUMED, Jesse to confirm): What the graph looks like.**
  - The canvas is the light page colour (`--color-page`). A current deal is a filled navy circle. A deal held at the clock time gets the hold-red ring (the only red). A watch deal gets a gray (tertiary) ring.
  - A history deal is a smaller hollow circle with a navy outline, labelled with its H-id.
  - An entity is a small sky-filled square with a navy outline, labelled with its kind ("Preparer", "Remit account").
  - Edges are navy. Width scales with `weight` relative to the largest weight in the graph. Opacity is 0.15 + 0.85 × `rarity`.
  - The selected node or edge gets a solid sky ring or underlay stroke (no blur).
  - Labels are 12px Geist in ink. No glow, shadows or gradients. All colours are read from the `index.css` tokens, never written as literals.
  - A history deal listed in `history_flags` is named in the side panel, not coloured, because it is not a hold.
  - Recommendation: approve.
- **D-36 (ASSUMED, Jesse to confirm): The cluster panel and family checklist.**
  - A cluster reads "Held" only once one of its current deals is held at the clock time (from `fraud.flagged_at`). Before that it reads "Not held as of {time}", with the end-of-run tier beside it under the caption "End of run".
  - The checklist lists F1 to F6 with the contract labels, "Fired" or "Not fired" in words, and the full evidence text. F6 is marked "Evidence only. Never votes."
  - The header reads "F1 fired · {k} of 4 voting families (F2 to F5) fired". It shows no threshold, because the threshold could change under the M11 playbook.
  - No p-value and no bits until CR-01 and CR-02 land.
  - The family checklist is shown as the end-of-run view, captioned (D-18).
  - Recommendation: approve.
- **D-37 (ASSUMED, Jesse to confirm): Entity link count.** An entity shows "Linked to {n} deals in this graph", counted from the visible edges. It does not show the Playbook's "used by 15 deals", which needs a history count the contract lacks (CR-03). Recommendation: approve.
- **D-38 (ASSUMED, Jesse to confirm): Graph page layout.**
  - Page title "Fraud graph".
  - A row of cluster buttons: held clusters first, each showing its id, tier and member count. The default selection is the first held cluster.
  - The canvas fills the main column (at least 480px tall).
  - A 320px right panel shows the cluster panel and then the evidence panel for the selected edge or node.
  - Below the canvas: a "Links visible as of {time}" table (the readable text version of the canvas), then the investigation trace (07-04).
  - Selecting a cluster fits the view to its nodes with no animation and fades non-members to 35% opacity.
  - Rail item "Fraud graph", placed after Alerts.
  - Recommendation: approve.
- **D-39 (ASSUMED, Jesse to confirm): "Next event" also stops at every edge time,** so stepping through the week lights the ring one link at a time. Recommendation: approve.
- **D-40 (ASSUMED, Jesse to confirm): Deal page.** The deal page's fraud panel shows the family checklist for the deal's cluster and an "Open in fraud graph" button. This fills the gap 02-UI-SPEC row 12 deferred to Phase 7. It counts as an extra deal-detail panel, so it is **cut tier 1** and lives in its own plan, 07-11, which runs last. Recommendation: approve.
- **D-41 (ASSUMED, Jesse to confirm): Investigation trace.**
  - Titled "Investigation (Nemotron, advisory)".
  - The steps are listed in order: step number, thought, tool, arguments as "key: value" text, then the result. The case summary follows.
  - A mode label reads "Recorded replay", "Live" or "Agents off".
  - A fixed caption reads "Advisory. The hold comes from the rule engine, not from this agent." (D-28)
  - A 404 shows "No investigation was run for this cluster."
  - A prosecutor and defender pair (MODEL_DESIGN N4) is shown only if CR-10 lands.
  - **Cut tier 4** together with NEM-03.
  - Recommendation: approve.
- **D-42 (ASSUMED, Jesse to confirm): Red-team view.**
  - Its own route and rail item "Red team"; page title "Red-team results".
  - One row per trick: Trick, What it does, Test deals, Caught, Catch rate (whole percent of the engine's `catch_rate`), Median time to hold (as a duration, or a dash), False flags.
  - A summary line adds up the rows: "Caught {x} of {y} test deals across {n} tricks. False flags: {z}."
  - A caption names `generated_by`.
  - No colour on rates (D-05).
  - **Cut tier 3** together with NEM-04.
  - Recommendation: approve.
- **D-43 (ASSUMED, Jesse to confirm): The live switch.**
  - `MOCK=0` serves the frozen engine's completed sample-week run. The UI keeps its browser clock and derived views.
  - After every successful clock change or inbox reply, the UI refetches its data (never the clock). An engine that tracks its own clock therefore stays in step too.
  - Going back in time sends replay and then advance, because the server rejects an earlier `to` (MODEL_DESIGN Q15).
  - If the live API is not ready by H10.5, stay on `MOCK=1`, keep building the graph, and retry every 30 minutes.
  - Recommendation: approve.
- **D-44 (ASSUMED, Jesse to confirm): Staff names at the switch.** Role labels stay until the contract offers names (CR-06). Then a quick task wires names into the existing Phase 2 people module. D-22 expected names "from the engine at the live switch", but no contract field carries them, so this is missing information, not a scope cut. Recommendation: approve, and ask Ezekiel for CR-06.
- **D-45 (ASSUMED, Jesse to confirm; Ezekiel owns): How the synthetic weekend drop is built.**
  - A committed script builds a new arrivals file from the sample week. It moves the last-arriving deals (whole deals: "new deals") and the last paper of several in-flight deals ("new papers on deals in flight") into a later drop window. Files on disk are untouched.
  - The golden labels still apply, so the dry run can be scored.
  - A fuzz copy adds a few truncated or empty files to prove the engine never crashes.
  - If Phase 6's deterministic synthesizer writes complete deal folders, Ezekiel may add its deals.
  - If the real weekend drop has already been sealed (07-07), the dry run uses it too.
  - Recommendation: approve.
- **D-46 (ASSUMED, Jesse to confirm): The sealed first run (refines D-25).** The blind record commits only the commit hash, a SHA-256 of the first-run output and aggregate counts (deals, errors, holds, validator and determinism verdicts). The per-deal output stays in the gitignored `out/blind_drop/` until Jesse's labels are committed, so the labels stay blind. Recommendation: approve.
- **D-47 (ASSUMED, Jesse to confirm): Slides.** One self-contained HTML deck, `docs/pitch/slides.html`. It follows the eight slides already drafted in `docs/pitch/PITCH_OUTLINE.md` (on main since Sat evening, pending Jesse's review). It uses no new packages, prints to PDF, and uses the UI tokens (serif titles, navy accent, red only on the held ring). Jesse may rebuild it in Google Slides if he prefers. The existing drafts (`PITCH_OUTLINE.md`, `DEVPOST.md`) are revised in place, not rewritten. Their demo steps that rely on unbuilt features (clock scrubber, bits against threshold, a credit-memo panel) are re-pointed at what Phase 7 actually builds. Recommendation: approve.
- **D-48 (ASSUMED, Jesse to confirm): The recording.**
  - Recorded on Jesse's Mac with the built-in screen recorder, 3 minutes or less.
  - Wi-Fi is off during the UI segment, to prove replay mode.
  - The sample week shows the ring lighting up. A terminal segment shows the drop run with no code changes.
  - The video is uploaded unlisted.
  - Recommendation: approve.
- **D-49 (ASSUMED, Jesse to confirm): Public exposure.**
  - Slides and Devpost text follow the confidentiality rules already written in `PITCH_OUTLINE.md` and `DEVPOST.md`: no borrower, business, staff or folder names, tax IDs, history ids or data-pack dollar figures, and no challenge text beyond the public title.
  - The video shows no PDF pages. It shows the running UI, which does display sample deal names, so it is uploaded unlisted until Vijay answers open question 1.
  - The repo stays private unless the organizers require a public link. Publishing a code-only copy cannot be undone, so it is gated by a decision checkpoint in 07-09.
  - Recommendation: approve, and ask Vijay (open question below).
- **D-50 (ASSUMED, Jesse to confirm): Who runs which plan.** Jesse runs 07-01 to 07-05, 07-08, 07-09 and 07-11 with Claude Code on his Mac. Ezekiel runs 07-06 and the engine steps of 07-07 (Jesse labels the drop in 07-07 Task 3), and writes the README that 07-08 tests. 07-02 Task 3 is a paired session; 07-10 is both. Run plans individually by owner rather than letting one machine pick up the other person's wave. Recommendation: approve.

### Claude's Discretion
Exact force strengths, tick counts and label placement inside D-34 and D-35. Spacing and secondary layout inside D-04 to D-12. Wording of empty states, in real banking vocabulary.

</decisions>

<cut_line>
## H18 Feature Freeze and Cut Order

After H18 (Sun 09:55) only bug fixes, the dry run, the recording and the pitch happen. No new features, and no threshold change without re-running the trap suite.

Tier numbers are the ROADMAP cut list's. Cuttable work sits in the later waves, so the cut line falls on whole plans where it can.

| ROADMAP tier | What is cut | Plans or tasks | What stays |
|--------------|-------------|----------------|------------|
| 1 (first) | UI polish: the 600 ms ease between layout keyframes (keyframes snap instead), and the extra deal-page panel | 07-01 Task 3, the ease step only; **07-11 whole plan** (wave 5) | Graph with keyframe replay, evidence panel, cluster checklist on the graph page |
| 2 | Nemotron prose polish and the VL fallback (NEM-05, NEM-06) | No Phase 7 UI plan; their fallbacks already ship (template messages, option buttons, OCR) | Everything in Phase 7 |
| 3 | Red-team view (UI-07), cut with NEM-04 | **07-05 whole plan** (wave 4) | Everything else |
| 4 | Investigation trace panel, cut with NEM-03 | **07-04 whole plan** (wave 3) | Deterministic evidence panel and family checklist |
| Never | Graph tracer, live switch, graph evidence and checklist, dry run, sealed blind record (when the drop lands), clean checkout, pitch, recording, submission | 07-01, 07-02, 07-03, 07-06, 07-07, 07-08, 07-09, 07-10 | |

For Jesse's time between H15.5 and H18, finish 07-08 (clean checkout, a submission requirement) before 07-05, and run 07-11 only if time remains. Labelling the drop (07-07 Task 3, up to 45 minutes) takes priority over any UI plan the moment the drop lands.

</cut_line>

<execution_map>
## Execution Map (owner, window, wave)

| Plan | Owner | Window (CT) | Wave | depends_on | Cut tier |
|------|-------|-------------|------|------------|----------|
| 07-01 Graph tracer on the mock | Jesse | H9 to H10 (00:55 to 01:55) | 1 | none | never (ease: tier 1) |
| 07-06 Synthetic drop and dry run | Ezekiel | H15.5 to H19 (build early, run after the freeze) | 1 | none (engine preconditions) | never |
| 07-07 Sealed blind drop record | Ezekiel seals, Jesse labels | Whenever the drop lands (script now) | 1 | none (an event) | never |
| 07-02 Live switch (I3, I4) | Jesse + Ezekiel | H10 to H10.5 (01:55 to 02:25) | 2 | 07-01 | never |
| 07-03 Replay, evidence, family checklist | Jesse | H10.5 to about H13 | 2 | 07-01 | never |
| 07-04 Investigation trace (I5) | Jesse | about H13 to H15.5, live check at H15.5 | 3 | 07-02, 07-03 | 4 |
| 07-08 Clean checkout (I6) | Jesse | H15.5 to H18 | 3 | 07-02 | never |
| 07-09 Pitch, demo script, slides, repo decision | Jesse | H10.5 to H18 (alongside UI) | 3 | 07-03 | never |
| 07-05 Red-team view (I5) | Jesse | H15.5 to H18 | 4 | 07-02, 07-04 | 3 |
| 07-10 Verify, record, submit | Both | H18 to H19.75 | 4 | 07-06, 07-08, 07-09 | never |
| 07-11 Deal-page checklist mirror | Jesse | last, before H18 if time allows | 5 | 07-03, 07-05 (cut-order ordering) | 1 |

Waves show dependencies and file ownership only. Jesse's UI plans run one at a time in plan order (07-01, 07-02, 07-03, 07-09 alongside, 07-04, 07-08, 07-05, 07-11). 07-10 starts after H18, whatever state 07-04, 07-05 and 07-11 are in (its first task checks which exist). 07-02 and 07-03 are in the same wave and both need an API on port 8000; each starts its own (07-03 on the mock), so their order does not matter.

Phase 2 status on main at the time of this update (Sun ~01:00): 02-01 to 02-04 are complete (02-04's human visual check is pending), and the look was restyled in the navy and sky palette. `MOCK=0` still answers 503, so 07-02 Task 3 waits on Ezekiel's live wiring and falls back to the mock (D-43).
</execution_map>

<contract_requests>
## Contract Requests for Ezekiel (the UI reads only `prism/contract.py`)

None of these blocks a plan; each has a fallback that ships. Change rule (docs/CONTRACT.md): Ezekiel changes the Pydantic model, regenerates the fixture, runs pytest, and tells Jesse. Jesse then runs `npm --prefix ui run api:types`.

| # | Request | Why (source) | Fallback without it |
|---|---------|--------------|---------------------|
| CR-01 | `FamilyResult.bits` and `FamilyResult.threshold_bits` (number or null) | UI_PLAYBOOK §4 "bits vs threshold"; MODEL_DESIGN M1, M7 | Checklist shows fired or not fired plus the evidence sentence |
| CR-02 | `Cluster.p_value` (permutation-test p-value, number or null) | UI_PLAYBOOK §4 cluster header; MODEL_DESIGN "Cluster = connected components ... permutation-test p-value" | Header shows family counts only |
| CR-03 | `GraphNode.history_deal_count` (int or null, entity nodes only) | UI_PLAYBOOK §4 label "used by 15 deals" | "Linked to {n} deals in this graph" (D-37) |
| CR-04 | `Cluster.held_at` (sim time or null); optionally `FamilyResult.first_fired_at` | Replaying the cluster tier and checklist on the clock | Held time taken from member deals' `fraud.flagged_at`; checklist captioned "End of run" |
| CR-05 | Family labels served by the API (for example `FamilyResult.label`) | docs/CONTRACT.md says labels live in `FAMILY_LABELS` so the UI does not hard-code them, but a Python dict is not in the OpenAPI schema | The UI mirrors the six labels, and a test reads `prism/contract.py` and fails if they drift |
| CR-06 | `GET /api/people` returning `{id, name, role}` from the data pack at run time (names never in git) | D-22 says names come from the engine at the live switch | Role labels with the id in a tooltip (D-44) |
| CR-07 | Confirm in docs/CONTRACT.md that a graph `deal` node's `id` equals the deal folder name | Joining graph nodes to deal details for held state and the "Open deal" button | The fixture already follows this; 07-02 checks it on live data and reports a mismatch |
| CR-08 | State which history deals and entities the live `/api/graph` includes (recommended: entities shared by at least 2 deals with at least one current deal, plus their history deals), and that `/api/graph` with no `at` returns the end-of-run graph | A full 257-deal history graph would bury the ring | Rarity encoding keeps common links faint; 07-02 reports the node count |
| CR-09 | State whether `MOCK=0` serves the completed run (end-of-run data with every timestamp) or a state that follows the server clock | Decides whether the client derivation alone is enough | D-43's refetch-after-change works for both |
| CR-10 | If the prosecutor and defender pair (MODEL_DESIGN N4) ships: `InvestigatorTrace.role` or a list of traces per cluster; for N11, `TraceStep.evidence_ids` or an `uncited` flag | Contract has one trace per cluster and no citations | One trace per cluster, as the contract defines |
| CR-11 | `TrickResult.generation` (int or null), a held-out flag, and the benign-twin count behind `false_flags` | MODEL_DESIGN N3 adaptive generations; HANDOFF §3 report | Flat trick table; false flags as a count |
| CR-12 | Let the live API choose its folder and arrivals through environment variables | Showing the drop run in the UI with no code change | The drop is shown through the CLI and validator output in a terminal |
| CR-13 | `DealDetail.credit_memo` (the MOVE-10 memo; Ezekiel's own qx3 hand-off note already lists it) | The pitch outline's demo shows the memo at Committee | The demo shows the committee approval request, whose message is the memo's 4-line short version (MOVE-10) |

</contract_requests>

<package_audit>
## Package Legitimacy Audit

Run on 2026-11-07 with `gsd-tools query package-legitimacy check --ecosystem npm`. Phase 2 RESEARCH also rated `react-force-graph-2d` OK on the same day.

| Package | Latest release | Weekly downloads | Source repo | Verdict | Disposition |
|---------|----------------|------------------|-------------|---------|-------------|
| react-force-graph-2d | 2026-09-29 | 1.30M | github.com/vasturiano/react-force-graph | OK | Install after the 07-01 blocking checkpoint (no RESEARCH.md exists for this phase, so the planner treats every package as ASSUMED) |
| force-graph (pulled in by the line above) | 2026-09-28 | 1.47M | github.com/vasturiano/force-graph | OK | Same checkpoint |
| d3-force | 2026-11-03 | 36.7M | github.com/d3/d3-force | SUS (too new) | Same checkpoint; pin the last release at least 30 days old |
| @types/d3-force (dev) | 2024-06-17 | 32.7M | DefinitelyTyped | OK | Same checkpoint |

No other package is installed in Phase 7. No `[SLOP]` verdicts.

</package_audit>

<canonical_refs>
## Canonical References

Downstream agents MUST read these before planning or implementing.

- `prism/contract.py`: source of truth for every field (FraudGraph, GraphNode, GraphEdge, Cluster, FamilyResult, InvestigatorTrace, TraceStep, RedTeamReport, TrickResult, Submission.history_flags, DealDetail). The UI never reads a field this file does not define.
- `docs/CONTRACT.md`: endpoints and graph conventions (edges run deal to entity; `?at=` hides edges not yet visible and entity nodes left with no edge; deal and history nodes and clusters are always returned; mock cluster tier is end of run).
- `fixtures/graph.json`, `fixtures/investigator.json`, `fixtures/redteam.json`, `fixtures/deal_detail.json`: the mock data the graph, trace and red-team views are built on.
- `docs/UI_PLAYBOOK.md` §4 (fraud graph recipe), §6 (verification checklist).
- `.planning/phases/02-pipeline-cockpit-ui-on-mock-data/02-CONTEXT.md`, `02-UI-SPEC.md`, `02-RESEARCH.md`, and the 02-01 to 02-04 PLAN and SUMMARY files: the `ui/` app, its files, tokens, time module, clock store, smoke and audit scripts.
- `docs/MODEL_DESIGN.md`: fraud model (M1 to M21) and Nemotron design (N1 to N13).
- `HANDOFF.md` §3 (validation protocol), §5 (questions for Vijay), §6 (pitch), §9 (open items).
- `.planning/ROADMAP.md` Phase 7, Gates, Drop response slot, Cut list.
- `eval/README.md` and `eval/gold.json`: the golden label format reused for `eval/gold_drop.json`.
- `.planning/research/STACK.md`: the react-force-graph-2d decision.
- `docs/pitch/PITCH_OUTLINE.md` and `docs/pitch/DEVPOST.md` (drafts on main, pending Jesse's review): the 8-slide outline, the 60-second demo table, the judge Q&A, the `[[placeholder]]` table and the confidentiality rules for public material. 07-09 and 07-10 revise these in place.
- `AGENTS.md` and `docs/SESSION_HANDOFF.md` (main): the engine gate commands (pytest, run, validate, score), and the rule that agents other than Jesse's do not edit `ui/`.
- The `ui/` app as built on main: hash routes use the prefix `#/deals/` (`ui/src/route.ts`); `nextEventAfter(details, t, extra)` already takes extra timestamps (`ui/src/time/timeview.ts`); `apiGet` in `ui/src/api/client.ts` is not exported yet; the audit (`ui/scripts/audit.ts`) limits hold-colour utility classes to `Badges.tsx`, `components/ui/` and `index.css`.

</canonical_refs>

<specifics>
## Specific Ideas

- The demo's best moment: press Replay, step "Next event", and watch the ring's links appear one by one and knot together, until the hold-red ring lands on the first deal while honest deals float apart.
- The graph is a picture of evidence, not a verdict. Every link opens its plain sentence of evidence, and the checklist says which families fired.
- Pitch lines come from HANDOFF §6: "Three 'unrelated' companies were secretly built by the same person"; "Tyler's paperwork is a mess, and we still don't flag him. Strange isn't fake."

</specifics>

<deferred>
## Deferred Ideas (not planned in Phase 7)

- The clock scrubber with arrival and hold ticks (UI_PLAYBOOK §5.2); "Next event" and playback cover the replay.
- Keyboard shortcuts, the density toggle, the printable credit memo and the mismatch side-by-side view (UI_PLAYBOOK §5).
- The credit memo panel on the deal page: the contract has no `credit_memo` field yet (CR-13).
- The document-snippet side sheet: no snippet field.
- A dark theme, or any graph replacement of the pipeline board (D-30).

</deferred>

<open_questions>
## Open Questions (for Jesse to add to HANDOFF §5 and post to Vijay)

1. May the public demo video and Devpost page show sample deal names and engine outputs from the UI (no PDF pages, no challenge text)? (Decides D-49.)
2. Existing HANDOFF §5 Q7: does submission require a public repo? (07-09 Task 3 decision.)
3. Existing HANDOFF §5 Q2: how does the drop arrive (its own zip and arrivals, or files added to the sample)? 07-07 handles both.
4. Is the Nemotron replay cache committed to git? It holds model text derived from the data pack (a confidentiality question), but a clean checkout and the offline demo need it (07-08 Task 2). Ezekiel and Jesse to decide; the README must say where it lives.
5. HANDOFF §6 names a borrower in a pitch line ("Tyler's paperwork is a mess"). The public rules forbid borrower names, so 07-09 uses "an honest borrower with a messy file" in slides, Devpost text and the spoken pitch unless Jesse says otherwise.
6. When does Ezekiel's live wiring land? `MOCK=0` answers 503 today. 07-02 Task 3 needs the exact start command and answers to CR-07 to CR-09; until then the demo data stays on the mock (D-43).

</open_questions>

<environment>
## Environment Notes

- Python commands reuse the form from earlier plans: `PYTHONUTF8=1 ${PY:-py -3.13} -m prism ...`. On Jesse's Mac set `PY=.venv/bin/python`; on Ezekiel's Windows machine the default `py -3.13` works.
- Sample run: `--folder data/participant/shared_folder --arrivals data/participant/sim/arrivals.jsonl`. `out/` and `data/` are gitignored.
- Mock API: `MOCK=1 .venv/bin/python -m uvicorn prism.api.app:app --port 8000`. Live API: the same with `MOCK=0`, once Ezekiel's README says how the live run is selected.
- UI gates inherited from Phase 2: `npm --prefix ui run build`, `npm --prefix ui test`, `npm --prefix ui run smoke` (mock or live API on port 8000), `npm --prefix ui run audit`, `npm --prefix ui run lint`.
- Repo: github.com/envezdezeke/Prism (private). `main` must always run.

</environment>

<coverage_audit>
## Coverage Audit (planner)

| Source | ID | Item | Plan | Status |
|--------|----|------|------|--------|
| GOAL | - | Ring lights up on the clock; why each link matters; what agents found; fresh drop with no code changes; recorded demo and 3-minute pitch | 07-01 to 07-10 | COVERED |
| REQ | UI-06 | Graph with rarity edges, clock replay, evidence panel, family checklist, investigator trace | 07-01, 07-02, 07-03, 07-04, 07-11 | COVERED |
| REQ | UI-07 | Red-team results view | 07-05 | COVERED (cut tier 3 allowed by ROADMAP) |
| REQ | DEMO-01 | Drop dry run with no code changes | 07-06, 07-07 | COVERED |
| REQ | DEMO-02 | Clean checkout on Jesse's machine | 07-08 | COVERED |
| REQ | DEMO-03 | Recorded demo in replay mode, 3-minute pitch, slides | 07-07 (headline record), 07-09, 07-10 (live data via 07-02) | COVERED |
| ROADMAP | SC1 | Phase 2 cockpit on live data by H10.5 | 07-02 | COVERED |
| RESEARCH (Phase 2) | Pattern 4 | Live mode needs refetching behind one switch | 07-02 | COVERED |
| UI-SPEC (Phase 2) | Unresolved rows | Needed-by badge timing and the SLA-stops-at-exit rule, to confirm at the live switch | 07-02 | COVERED |
| CONTEXT | D-01 to D-21 | Carried UI rules | 07-01 to 07-05 | COVERED |
| CONTEXT | D-22 | Role labels now; names at the live switch | 07-02 (role labels kept) | PARTIAL: names need CR-06 (missing information, not a scope cut) |
| CONTEXT | D-23 to D-29 | Priority, headline, blind protocol, sourced numbers, replay mode, advisory agents, pitch language | 07-06, 07-07, 07-09, 07-10 | COVERED |
| CONTEXT | D-30 | Obsidian-style seeded force layout; board unchanged | 07-01 (tracer), 07-03 | COVERED |
| CONTEXT | D-31 to D-50 | New decisions | 07-01 to 07-10 | COVERED |

</coverage_audit>

---

*Phase: 07-fraud-graph-dry-run-and-pitch*
*Context drafted by the planner: 2026-11-07, pending Jesse's review*
