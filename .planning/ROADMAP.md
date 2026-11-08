# Roadmap: Prism

## Overview

Two people build Prism in 20 hours (Sat 15:55 → Sun 12:00 CT) on two parallel tracks. Ezekiel builds the deterministic engine in the order the data flows: foundations and the API contract first, then reading the folder, moving the deal and catching the fakes. That engine is frozen as the scored baseline at H10. He then adds the Nemotron agents around it, working by H15.5. Jesse writes the golden labels for the 13 sample deals by H2 and builds the pipeline cockpit UI against mock fixtures from H1, then builds the fraud-graph hero view and leads the demo and pitch. The tracks meet at fixed hand-offs: the contract at H1, the golden labels at H2, the switch from mock to live data at H10 and the agent endpoints at H15.5. After the H18 feature freeze, both run a dry run on a simulated weekend drop, record the demo and rehearse the pitch.

**Clock:** H0 = Sat 2026-11-07 15:55 CT. **Hard deadline Sun 2026-11-08 12:00 CT (H20.1).** Submit target is H19.75 (Sun 11:40), which leaves 20 minutes of buffer. Engine windows are unchanged from the first draft. The lost hour came out of Nemotron (−30 min) and the late reserve (−30 min), following Goldman > Nemotron > UI.

**Priority when cutting:** Goldman score > Nemotron > UI.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED), for example a drop-response phase if the weekend drop needs more than its 90-minute slot

Phase numbers follow start time. The two tracks run in parallel, so Phase 2 (Jesse) runs alongside Phases 3 to 5 (Ezekiel).

- [ ] **Phase 1: Foundations, Contract and Golden Labels** - Arrival-gated, deterministic engine skeleton that always writes valid submission JSON; contract and mock fixtures by H1; golden labels by H2 (Both, H0–H2)
- [ ] **Phase 2: Pipeline Cockpit UI on Mock Data** - Board, clock, deal detail and inbox in the light fintech design, built on fixtures only (Jesse, H1–H9)
- [ ] **Phase 3: Read the Folder** - Content-based classification, extraction with provenance, MISSING/MISMATCH/OLD_TRICK issues with no false alarms (Ezekiel, H2–H5)
- [ ] **Phase 4: Move the Deal** - Six-stage machine, sign-off routing, SLA ladder, deadlines, responder personas, live API (Ezekiel, H5–H7.5)
- [ ] **Phase 5: Catch the Fakes** - Rarity-weighted entity graph, multi-family hold rule, linked and history deals, trap suite; ends at the H10 baseline freeze (Ezekiel, H7.5–H10)
- [ ] **Phase 6: Nemotron Agents** - Record/replay client, investigator, red-team, VL reader, plain-words messages, all off the scored path; ends at the H15.5 gate (Ezekiel, H10.5–H15.5)
- [ ] **Phase 7: Fraud Graph, Dry Run and Pitch** - Live UI switch, "ring lights up" graph, red-team view, weekend-drop dry run, demo recording and pitch (Jesse lead, Ezekiel from H15.5, H9–H19.75)

## Who's doing what, when

| Hours | Clock (CT) | Ezekiel (engine track) | Jesse (product track) | Hand-off / gate |
|-------|------------|------------------------|-----------------------|-----------------|
| H0–H1 | Sat 15:55–16:55 | Phase 1: repo skeleton, `visible_files(now)` gate, config loaders, Pydantic contract and mock fixtures | Phase 1: golden labels for the 13 sample deals (finance judgment) | **H1: contract + fixtures to Jesse (I1)** |
| H1–H2 | Sat 16:55–17:55 | Phase 1: submission validator, determinism harness, CLI, self-score script, RapidOCR spike, Nemotron smoke test | Phase 1: finish golden labels. Phase 2: frontend scaffold (Vite, Tailwind, shadcn, design tokens) runs alongside | **H2: golden labels to Ezekiel (I2)** |
| H2–H5 | Sat 17:55–20:55 | Phase 3: classify, extract, OCR, MISSING / MISMATCH / OLD_TRICK issues | Phase 2: design system, pipeline board, clock controls | |
| H5–H7.5 | Sat 20:55–23:25 | Phase 4: stage machine, routing, SLA ladder, deadlines, personas, live API | Phase 2: deal detail, inbox, alert feed | |
| H7.5–H9 | Sat 23:25 – Sun 00:55 | Phase 5: history baseline, entity graph, signal families F1–F6, hold rule | Phase 2: finish and design pass on mock data | H9: UI v1 done on mock |
| H9–H10 | Sun 00:55–01:55 | Phase 5: linked and history deals, trap suite, graph endpoint, freeze | Phase 7: fraud graph view on the mock graph fixture | **H10 gate: engine baseline frozen** |
| H10–H10.5 | Sun 01:55–02:25 | Pair on the switch: confirm the live API matches the contract | Phase 7: flip `MOCK=0`, report contract diffs | **I3 + I4: UI on live engine, live graph** |
| H10.5–H15.5 | Sun 02:25–07:25 | Phase 6: Nemotron client, investigator, red-team, VL reader, messages | Phase 7: graph replay with the clock, evidence panel, signal checklist, trace panel; pitch outline | **H15.5 gate; I5: trace + red-team endpoints live** |
| H15.5–H18 | Sun 07:25–09:55 | Phase 7: synthetic weekend drop, fuzz run, drop-response reserve, help wire agent endpoints | Phase 7: red-team view, clean-checkout run from the README, slides | **H18: feature freeze** |
| H18–H19 | Sun 09:55–10:55 | Phase 7: dry run on the simulated weekend drop, crash-only fixes | Phase 7: run the demo path on the dry-run output, note glitches | |
| H19–H19.75 | Sun 10:55–11:40 | Both: record the demo (Nemotron in replay mode), push the repo, submit | Both: rehearse the 3-minute pitch, final slides, Devpost | **H19.75 (11:40): submit** |
| H19.75–H20.1 | Sun 11:40–12:00 | Buffer only: resubmit if something broke | Buffer only | **12:00 hard deadline** |
| Any time | When the drop lands | Drop response (up to 90 min) | Label the drop's new deals and papers (up to 45 min) | See Drop response slot |

## Integration points

| # | What | From → To | Due | Done when |
|---|------|-----------|-----|-----------|
| I1 | API contract + mock fixtures (FND-07) | Ezekiel → Jesse | H1 (Sat 16:55) | Pydantic schemas and JSON fixtures cover deals, deal detail, clock (advance, replay), inbox (including the reply POST), alerts, graph (nodes, rarity-weighted edges, per-edge evidence, first-visible sim time), investigator trace and red-team report. `MOCK=1` serves them; OpenAPI at `/docs`. |
| I2 | Golden labels (FND-08) | Jesse → Ezekiel | H2 (Sat 17:55) | `eval/gold.json` covers all 13 deals and the self-score script runs against it |
| I3 | Switch the UI from mock to live (Phase 4 live API on the frozen Phase 5 engine) | Ezekiel → Jesse | H10 (Sun 01:55), switched by H10.5 | `MOCK=0` shows the real sample-week run with no UI change beyond the flag |
| I4 | Graph data endpoint, live | Ezekiel → Jesse | H10 (Sun 01:55) | Same shape as the I1 graph fixture, from the frozen engine, queryable at a sim time for the replay |
| I5 | Investigator trace + red-team report endpoints, live | Ezekiel → Jesse | H15.5 (Sun 07:25) | Same shapes as the I1 fixtures, and they work offline in replay mode |
| I6 | README clean-checkout run | Ezekiel → Jesse | H18 (Sun 09:55) | Jesse runs engine, API and UI from a fresh clone on Jesse's machine (DEMO-02) |

**Contract rule:** if a shape has to change, change the Pydantic schema and regenerate the fixture first, then tell the other person. The UI never reads a field the contract doesn't define.

## Gates

| Gate | When (CT) | Pass condition | If it slips |
|------|-----------|----------------|-------------|
| **H10: Engine baseline frozen** | Sun 01:55 | The sample-week `submission.json` validates and is byte-identical across two runs. The READ trap checks (no false issues) and the FRAUD trap suite (no false holds, no history false flags) pass. The self-score against the golden labels is recorded and the baseline hash tagged. | Engine work continues until the trap suite passes; Phase 6 starts late and cut tiers 2–3 apply at once. Never start Nemotron on an engine that false-flags. |
| **H15.5: Nemotron investigator + red-team working** | Sun 07:25 | The investigator writes a traced case for the sample ring. The red-team report shows at least 3 tricks with catch rates. `NEMOTRON=off` output is byte-identical to the H10 baseline. The replay cache for the demo is recorded. | Cut the red-team (tier 3) and give the investigator until H16.5, then stop Nemotron work either way. |
| **H18: Feature freeze** | Sun 09:55 | Everything after this is a bug fix, the dry run, the recording or the pitch. No new features. No threshold change without re-running the trap suite. | Not allowed to slip. |
| **H19.75: Submit** | Sun 11:40 (hard deadline 12:00) | Repo pushed, README runs on a clean checkout, demo video and slides linked. | Not allowed to slip. |

## Drop response slot

The organizers' weekend drop (new `shared_folder` content and `arrivals.jsonl`, possibly with new papers on deals already in flight) arrives during the event at an unknown time. It gets a reserved slot instead of a phase.

- **Budget:** Ezekiel up to 90 minutes, Jesse up to 45 minutes.
- **Ezekiel:** put the drop under `data/` (gitignored) and run the CLI with `--folder` and `--arrivals`, with no code changes. Then run the validator, the determinism check and the trap suite. Triage crashes, unknown document classes, new issues, holds and missed holds. Fix only generic logic and never add drop-specific literals. Re-run the sample regression and re-tag the baseline.
- **Jesse:** label the drop's new deals and papers with finance judgment as a separate golden expectations file, so the self-score covers them.
- **Where the time comes from:**
  - Lands before H10: run it once on whatever engine exists, as a crash and false-flag check. Log the findings into the current phase and keep building. The full response happens right after the H10 freeze.
  - Lands H10–H15.5: pause Phase 6. If that puts the H15.5 gate at risk, apply cut tiers 2–3.
  - Lands H15.5–H18: use Ezekiel's H15.5–H18 reserve, which exists for this.
  - Lands after H18: it replaces the synthetic drop in the DEMO-01 dry run, and only crash fixes are allowed.
- If the response needs more than 90 minutes, insert it as a decimal phase (`/gsd-phase --insert`).

## Cut list

Cut in this order when a gate is at risk.

| Order | Cut | What stays |
|-------|-----|------------|
| 1 | UI polish: motion and transitions, extra deal-detail panels, styling beyond the design system. The ring replay stays but steps with the clock instead of animating. | Working board, clock, deal detail, inbox, graph with evidence |
| 2 | Nemotron extras: prose polish and reply parsing (NEM-06), VL fallback reader (NEM-05). Added from research; their fallbacks already ship. | Template messages, option-button replies, RapidOCR on the ID photo |
| 3 | Red-team generator and its view (NEM-04, UI-07) | The investigator stays as the agentic showcase |
| 4 | Investigator (NEM-03) | The deterministic evidence panel and signal checklist |
| Never | Engine (FND, READ, MOVE, FRD), submission validator, determinism harness, trap suite, golden self-score | |

## Phase Details

### Phase 1: Foundations, Contract and Golden Labels
**Goal**: Both tracks have something solid to build against. There is an engine skeleton that only sees arrived files and always writes valid, deterministic submission JSON for any folder. There is a published API contract with mock fixtures, golden expectations for the 13 sample deals, and proof that the hosted Nemotron API does what Phase 6 needs.
**Depends on**: Nothing (first phase)
**Owner**: Ezekiel (engine skeleton, contract and fixtures, validator, self-score script, Nemotron smoke test); Jesse (golden labels)
**Window**: H0–H2 (Sat 15:55–17:55 CT). Contract and fixtures due H1; golden labels due H2.
**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06, FND-07, FND-08, NEM-02
**Success Criteria** (what must be TRUE):
  1. Running the CLI on the sample `--folder` and `--arrivals` writes `out/submission.json` with all 13 folder keys. It passes the validator, comes out byte-identical on a second run, and still gets written when one deal's documents are corrupted (the error is recorded for that deal). The validator rejects a hand-broken file (bad key, bad enum, bad `KIND:target`).
  2. Asked for files at sim time T, the engine returns only files with `arrive_at <= T` (ties sorted by path), and deleting every later file leaves the output up to T unchanged. All emitted times are fixed `-06:00` ISO strings and money is integer cents. Rules load from `stages.json`, `teams.json` and `config/fraud.yaml`, and a grep test finds no folder, company or trick names in engine code.
  3. By H1, with `MOCK=1`, the API serves every contract endpoint (deals, deal detail, clock, inbox, alerts, graph, investigator trace, red-team report) from JSON fixtures, and Jesse can load them in a browser.
  4. By H2, `eval/gold.json` holds Jesse's expected facts, issues, sign-off routing, hold or no hold, linked deals and `history_flags` for all 13 sample deals. The self-score script prints a per-deal, per-field score of engine output against it.
  5. A smoke script shows a plain completion, a tool-call round trip and a VL read of Tyler's JPG on the hosted Nemotron API. It records whether native tool calling works, which decides how Phase 6 builds its agent loop.
**Plans**: TBD
**Notes**: Also inventory `shared_folder` against `arrivals.jsonl` (research counts disagree: 167 vs 140 PDFs + 5 CSVs + 1 JPG; 173 arrivals vs 186 files) and spike RapidOCR on the JPG in a clean venv. NEM-02 sits here, not in Phase 6, so hosted tool calling is proven before anything depends on it.

### Phase 2: Pipeline Cockpit UI on Mock Data
**Goal**: Someone playing bank staff can watch every deal move through the pipeline, open any deal to see what the engine read and why it decided what it did, and answer sign-off requests. The UI is clean, light fintech design and runs entirely on mock fixtures.
**Depends on**: Phase 1 (only the API contract and mock fixtures, FND-07, due H1; does not wait on Phases 3–5)
**Owner**: Jesse
**Window**: H1–H9 (Sat 16:55 – Sun 00:55 CT). H1–H2 overlaps the golden labels: Claude scaffolds Vite, Tailwind and shadcn while Jesse finishes the labels by hand. The switch to live data happens at H10, in Phase 7.
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria** (what must be TRUE):
  1. With `MOCK=1`, the pipeline board shows all 13 sample deals in their stage columns, each with an SLA timer and, where the deal has one, a needed-by deadline badge.
  2. The user can see the current sim time, advance the clock and replay from the start, and the board, alerts and inbox change to match the fixture state at that time.
  3. Clicking a deal opens its detail page: extracted facts (each with a source-document chip and confidence), open issues, the stage log with its "why", human requests and alerts.
  4. The user can answer a pending request from the inbox, and the reply goes to the API in the contract shape.
  5. Every screen uses one type scale and tabular money numerals, and red appears only on fraud holds.
**Plans**: 2/4 plans executed
Plans:
- [x] 02-01-PLAN.md — Tracer: package checkpoint, scaffold, Playbook tokens, client-held clock and one live pipeline board path (UI-01, UI-02)
- [x] 02-02-PLAN.md — Full board rows, formatting module, sim-clock controls and replay, design audit gate (UI-01, UI-02, UI-03)
- [ ] 02-03-PLAN.md — App frame, deal detail (facts, issues, stage log, requests, alerts, fraud panel), labels and people map (UI-01, UI-04)
- [ ] 02-04-PLAN.md — Inbox with replies and overlay, alerts feed, phase gate and human-check (UI-01, UI-04, UI-05)
**UI hint**: yes

### Phase 3: Read the Folder
**Goal**: Every arriving document is identified by what it says, not what it is called. Its facts are extracted with source and confidence, and the engine reports exactly the missing, mismatched and tampered items, with no false alarms on messy-but-real borrowers.
**Depends on**: Phase 1 (visibility gate, config loaders, validator, golden labels for self-scoring)
**Owner**: Ezekiel
**Window**: H2–H5 (Sat 17:55–20:55 CT)
**Requirements**: READ-01, READ-02, READ-03, READ-04, READ-05, READ-06, READ-07, READ-08
**Success Criteria** (what must be TRUE):
  1. Every sample PDF, CSV and JPG gets a content-based class without a crash. Tyler's Form 7004 is classed as an extension, not a second application. LSFD's scanned filenames are classed from their contents. Anything unrecognized becomes `other`.
  2. The 10 submission facts for each of the 13 deals match the golden labels, each with source document and confidence, and `needed_by` is an ISO time or null (never "No specific date"). Graph attributes (preparer, agent, vendor and remit account, PDF producer/creator, address, bank, guarantor ID, deposit features) are extracted for every deal. Tyler's ID photo is read by OCR or marked present-but-unverified.
  3. The engine's issues match the golden expectations: Westfield `MISMATCH:ein`; Bluebonnet `MISMATCH:amount_requested` and `MISSING_DOC:equipment_quote`; LSFD `MISSING_DOC:tax_return` and `MISSING_DOC:equipment_quote`; Oakline `MISSING_PAGE` (not `STMT_TAMPER`); Tyler `MISSING_DOC:bank_statement_2026-06`; Granite Bay `OLD_TRICK:STMT_TAMPER` and `OLD_TRICK:REV_INFLATION`.
  4. Garza, Priya, Okafor, Harbor Tea and Tyler's non-June items get zero issues, and no `MISSING_DOC` fires while a folder is still landing (30 sim-minutes of quiet first).
**Plans**: TBD
**Notes**: Read `rules/known_fraud_checks.md` verbatim for the OLD_TRICK thresholds. Review the low-confidence classifications (`may statement.pdf`, Form 7004 vs tax return, LSFD scans). Where the golden labels and these research expectations disagree, discuss before coding; the golden file is the oracle.

### Phase 4: Move the Deal
**Goal**: Every deal moves through the six stages on the sim clock. It asks the right person at each sign-off, alerts and escalates when stuck, meets needed-by dates, and never advances while it is waiting on anything.
**Depends on**: Phase 3 (stage guards read the issue list)
**Owner**: Ezekiel
**Window**: H5–H7.5 (Sat 20:55–23:25 CT)
**Requirements**: MOVE-01, MOVE-02, MOVE-03, MOVE-04, MOVE-05, MOVE-06, MOVE-07, MOVE-08, MOVE-09, MOVE-10, MOVE-11
**Success Criteria** (what must be TRUE):
  1. A headless sample-week run with scripted personas takes clean deals through Intake, Credit, Committee, Product, Committed and Closed in order, and each stage writes a `stage_log` entry with what was seen, what was decided and why. No deal advances while it waits on a document, a human answer or a hold. An incomplete file gets a borrower `info_request`, never a `credit_decision` request.
  2. Sign-off requests go to the right person. Priya's credit request goes to marcus.lee because dana.whitfield is out. Committee goes to priscilla.nguyen under $250k and to harold.benson at $250k or more. Commitment goes to the deal's RM, funding to tasha.reed, and fraud-hold requests to victor.hale with monica.salas as backup.
  3. Under the never-answers persona, each stuck deal gets an alert at 100%, an escalation at 150% and a second escalation to lauren.kim at 200%, each exactly once, and unanswered requests reroute to the backup. Every message says whose deal, which stage, how long, what it is waiting on and what would unblock it.
  4. Priya's deal is prioritised, and a deadline-risk alert fires before her needed-by date would be missed.
  5. A reply posted through the live API inbox moves a deal exactly as the matching scripted reply would. A new paper added to an in-flight deal mid-run is absorbed and re-checked, and it resolves or raises issues.
**Plans**: TBD
  6. Every deal entering Committee gets the deterministic credit memo; the four sample deals that reach Committee grade as in `docs/CREDIT_MEMO_TEMPLATE.md` (Garza 1, Okafor 1, Priya 2, Harbor Tea 2). Every alert and request matches `docs/MESSAGE_TEMPLATES.md`.
**Notes**: The live API (same contract as the Phase 1 fixtures) ships here, so the H10 switch is a flag flip. Add `credit_memo` to `DealDetail` in the contract for MOVE-10.

### Phase 5: Catch the Fakes
**Goal**: The engine holds the cross-deal fraud ring before money goes out, as early as the evidence allows. It finds the ring's linked current and history deals and leaves every good deal alone, using rarity-weighted shared entities plus multi-signal agreement that carries over to an unseen trick.
**Depends on**: Phase 3 and Phase 4 (graph attributes from Phase 3; freeze and `fraud_hold` go through the Phase 4 stage machine and request manager; FRD-01/FRD-02 need only Phase 3 and can start alongside Phase 4)
**Owner**: Ezekiel
**Window**: H7.5–H10 (Sat 23:25 – Sun 01:55 CT). Ends at the **H10 gate**.
**Requirements**: FRD-01, FRD-02, FRD-03, FRD-04, FRD-05, FRD-06, FRD-07
**Success Criteria** (what must be TRUE):
  1. Ridgeway is held on Monday (target about 14:10 sim time) from history links alone, before Pecan Grove and Summit Peak arrive, and those two are held at Intake or Credit. Each held deal shows `held: true`, `stage_at_flag` and a plain-words reason, has a `fraud_hold` request out to victor.hale (backup monica.salas), and never enters Closed.
  2. `linked_deals` ties the three ring deals together, and `history_flags` is exactly H-2608-002 and H-2609-008.
  3. The trap suite passes: zero holds on Garza, Tyler, Priya, Okafor, Westfield, Harbor Tea, Oakline, LSFD and Bluebonnet, and zero history false flags (including H-2511-010, H-2601-022 and the 15 Berkshire Ln deals). Granite Bay's OLD_TRICK goes to Fraud Ops.
  4. Every held or watched deal shows evidence for each signal family (F1–F6) that fired, with each shared entity's rarity against history. A deal with only 1–2 families appears on the watch tier and is not held.
  5. At H10 the sample-week submission validates, is byte-identical across two runs, passes both trap suites (no false issues, no false holds), has its self-score against the golden labels recorded, and is tagged as the frozen baseline. The live graph endpoint serves nodes, rarity-weighted edges, family evidence and each edge's first-visible sim time.
**Plans**: TBD
**Notes**: The deepest risk in the project. Thresholds live in `config/fraud.yaml` and are not fitted to the sample. No sample literals ("DocuForge", "Delacroix", 4471, "Metroplex", "Commerce Street") appear in detection code. The sample is already analyzed, so it can't serve as a blind fraud test. Follow Jesse's validation protocol (`HANDOFF.md` §3):
- Replay history in time order and report how many deals into a scheme the first flag fires.
- Run blind checks: without the DUP_EIN/SHELL_ADDRESS rules, does the generic detector still surface those labeled history deals?
- Measure false positives on history deals that are `funded`, `fraud_label=none` and `current`/`paid_off`. This is the key metric.
- Freeze thresholds before the organizers' drop and treat the drop as a blind test.

### Phase 6: Nemotron Agents
**Goal**: Nemotron agents investigate each flagged cluster, attack the detector with invented fraud tricks, read the documents the parser can't, and write the plain-words messages. All of it sits off the scored path, so switching Nemotron off changes nothing that is scored.
**Depends on**: Phase 5 (the frozen engine and its read-only query surface are the agents' tools; Phase 1's smoke test sets the tool-calling style)
**Owner**: Ezekiel
**Window**: H10.5–H15.5 (Sun 02:25–07:25 CT). Ends at the **H15.5 gate**.
**Requirements**: NEM-01, NEM-03, NEM-04, NEM-05, NEM-06
**Success Criteria** (what must be TRUE):
  1. The scored submission JSON is byte-identical with `NEMOTRON=off`, `replay` and `live`, and replay mode runs the full demo without network access.
  2. For each flagged cluster, the investigator (ReAct, at most 8 steps, read-only engine tools) writes an evidence case for Fraud Ops, and its full tool-call trace is served on the trace endpoint.
  3. The red-team run proposes 3–5 new fraud tricks, a deterministic synthesizer builds deals for each, and a report on the red-team endpoint shows per-trick catch rate, time-to-hold and false flags.
  4. The VL reader reads Tyler's JPG ID and an unfamiliar layout. Its fields only fill nulls and never create a mismatch or a hold.
  5. Credit memos, sign-off requests and alerts read as plain words from Nemotron and fall back to templates when the API fails. A free-text human reply is parsed into one of the request's allowed options.
**Plans**: TBD
**Notes**: Hosted build.nvidia.com API with the record/replay cache; Brev is break-glass only. Model IDs live in env vars. A plain OpenAI-SDK tool loop, no agent framework.
- **Red-team protocol (`HANDOFF.md` §3):** write the trick menu before any tuning, with randomized strength and fields: a shared hidden party in different roles, number style, template fingerprint, a lookalike counterparty, threshold gaming and a timing burst.
- Evaluate by leaving one trick family out at a time, never with a random row split.
- Keep a seeded deterministic generator next to Nemotron's so the results reproduce.
- The report feeds the pitch line: "Tested on fraud types it never saw … caught X, with Y false alarms."

### Phase 7: Fraud Graph, Dry Run and Pitch
**Goal**: Judges watch the fraud ring light up as the clock advances, see why each link matters and what the agents found, and see Prism handle a fresh drop with no code changes. All of it is captured in a recorded demo and a 3-minute pitch.
**Depends on**: Phase 2, Phase 5 and Phase 6 (the graph view starts on Phase 1's mock graph fixture at H9; live engine and graph data from Phase 5 at H10; trace and red-team endpoints from Phase 6 at H15.5)
**Owner**: Jesse lead (graph view, red-team view, clean checkout, demo, pitch); Ezekiel at the H10 switch and from H15.5 (synthetic weekend drop, dry run)
**Window**: H9–H19.75 (Sun 00:55–11:40 CT). Mock-to-live switch H10–H10.5; feature freeze H18; dry run, recording and pitch H18–H19.75; buffer to the 12:00 deadline.
**Requirements**: UI-06, UI-07, DEMO-01, DEMO-02, DEMO-03
**Success Criteria** (what must be TRUE):
  1. With `MOCK=0`, the Phase 2 board, deal detail, inbox and clock show the frozen engine's live sample-week run (switched by H10.5), so the demo runs on real output.
  2. The fraud graph replays with the sim clock: the ring's deals connect as shared rare entities arrive, edges are weighted by rarity, clicking an edge shows its evidence, and each cluster shows its signal-family checklist and the investigator trace.
  3. A red-team view shows per-trick catch rate, time-to-hold and false flags.
  4. A synthetic weekend drop (new deals plus new papers on in-flight deals) runs end to end with no code changes and passes the validator, the determinism check and the trap suite. A clean checkout following the README runs on Jesse's machine.
  5. By H19.75 (Sun 11:40) there is a recorded demo path with Nemotron in replay mode, a 3-minute pitch and slides.
**Plans**: TBD
**UI hint**: yes
**Notes**: Ezekiel can build the synthetic drop with Phase 6's deterministic synthesizer (or a small script if the red-team was cut). If the real weekend drop has already arrived, the dry run uses it instead.

## Progress

**Execution order:** two tracks run in parallel. Ezekiel: 1 → 3 → 4 → 5 → 6 → 7. Jesse: 1 → 2 → 7.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundations, Contract and Golden Labels | 0/0 | Not started | - |
| 2. Pipeline Cockpit UI on Mock Data | 2/4 | In Progress | - |
| 3. Read the Folder | 0/0 | Not started | - |
| 4. Move the Deal | 0/0 | Not started | - |
| 5. Catch the Fakes | 0/0 | Not started | - |
| 6. Nemotron Agents | 0/0 | Not started | - |
| 7. Fraud Graph, Dry Run and Pitch | 0/0 | Not started | - |
