# Phase 4: Move the Deal - Research

**Researched:** 2026-11-08 (Sun 01:40 CT; hard deadline Sun 12:00 CT, submit target 11:40)
**Domain:** Deterministic stage machine, sign-off routing, SLA ladder, needed-by dates, human requests, credit memo, and the live API that serves them (Python 3.13, Pydantic v2, FastAPI)
**Confidence:** HIGH for in-repo state, the tuning-set analysis and the measured runs (all read or re-run this session). MEDIUM for the live-API design and the schedule estimates (not built, one design pass).

## Summary

Most of Phase 4 is already built and tested on `main` (HEAD `ad06f49`). The Move core from quick task 261107-qx3 implements the six-stage machine, data-driven routing, the exactly-once 100/150/200% ladder, the fraud freeze and chase, the credit memo, deadline-risk alerts, and one reply path (`inbox.record_reply`) that personas and a future API share.

On the 10 tuning deals every Move-owned score is already at its ceiling. All 8 route misses and both stage misses sit on two deals (Pecan Grove, Ridgeway) that the engine never flags. Those are Fraud (Phase 5) misses, not Move misses. Phase 4 cannot raise the tuning line on its own.

What is still open is what the scorer does not see:
1. The live API is not built. With `MOCK=0` every `/api` route returns 503. This is the H10 hand-off (I3) and success criterion 5.
2. The default run ends 30 minutes after the last arrival (Wed 11/04 15:10 for the sample). The sim week runs to Fri 11/06 18:00. Under the default end, the 150% and 200% ladder steps for stuck Credit deals are never emitted, which breaks success criterion 3 in a default run.
3. Two deadline messages print times that are already in the past (Priya's deal, verified on the tuning output).
4. OLD_TRICK issues block a deal but never send a `fraud_hold` request, so the alert tells Fraud Ops to act on a request that does not exist. The rules say an old-trick hit goes straight to Fraud Operations.
5. Several wording deviations from `docs/MESSAGE_TEMPLATES.md`. The credit-decision message says "File is complete" while a Product-stage document can still be open.

**Primary recommendation:** Build the engine-backed live API read path first, because it blocks Jesse's I3 switch. Then build the reply path. Then fix the run-end policy, the two deadline-time defects, and the OLD_TRICK-to-Fraud Ops boundary. Treat wording deviations as cheap follow-ups. Phase 5 owns setting `fraud.flagged`, `flagged_at`, `stage_at_flag` and `held`. Move already freezes from those fields and must not set them itself.

**Schedule input:** The Phase 4 window (H5 to H7.5) has passed, and the H10 freeze (Sun 01:55 CT) is now. Fraud `decide()` is still a stub (`prism/fraud/decide.py:36-37`). Size the remaining Phase 4 work to roughly 3 hours and put the live API and the run-end policy first.

## Project Constraints (from `.claude/CLAUDE.md` and `AGENTS.md`)

- No Claude or Anthropic models in the product. Use Nemotron plus deterministic code. [CITED: .claude/CLAUDE.md, "No Claude in product"]
- Determinism: every scored field comes from deterministic code. Nemotron output is advisory, or validated before it can affect a score. [CITED: .claude/CLAUDE.md, "Determinism"]
- No sample-specific literals in detection or Move logic: no folder names, company names, or person ids in engine code. Enforced by `tests/test_engine.py::test_no_sample_literals_in_code` and by a person-name grep recorded in the quick-task summary. [VERIFIED: tests/test_engine.py, test name listed by grep this session]
- Time: sim time in America/Chicago with a fixed `-06:00` offset. SLA timers run in wall-clock sim hours. A file is visible only after its `arrive_at`. [CITED: .claude/CLAUDE.md, "Time semantics"]
- Confidentiality: challenge statement and raw data stay out of git (`data/` is gitignored, `.gitignore` line `/data/`). Never print `.env` or the NVIDIA key. [CITED: .claude/CLAUDE.md; VERIFIED: .gitignore]
- Python: `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe`, with `PYTHONUTF8=1`. Plain `python` is the Microsoft Store stub. [CITED: .claude/CLAUDE.md]
- Gate before every commit: pytest, run, validate, score. Scores must not go down. Report before and after numbers. [CITED: AGENTS.md]
- Do not edit `ui/` (Jesse's). [CITED: AGENTS.md]
- Function signatures are pinned by tests. Do not change a pinned signature or delete a test to make it pass. [CITED: AGENTS.md]
- Holdout discipline (D-02): tune only on the 10 tuning deals. Holdout numbers appear only as the one aggregate line in the final gate. [CITED: .planning/phases/03-read-the-folder/03-CONTEXT.md:20]

## User Constraints

No `CONTEXT.md` exists for Phase 4 (the user chose to plan without discuss-phase). The binding inputs are the owner decisions already in the repo.

### Locked (owner decisions already in the repo)
- `docs/DETAILS_CHECKLIST.md` §8, judgment calls J1 to J22 (Jesse, 2026-11-07). Items marked "Vijay?" are not yet confirmed by the organizers: J5, J10, J14, J20.
- `docs/MODEL_DESIGN.md` M8: "OLD_TRICK → Fraud Ops (bank policy)". M17: hold "the moment the rule is met (even at Intake)"; holds are sticky.
- `docs/MESSAGE_TEMPLATES.md` for all wording (MOVE-11). `docs/CREDIT_MEMO_TEMPLATE.md` for grades and the short version (MOVE-10).
- Challenge rules in `data/participant/rules/stages.json`, `contacts/teams.json`, `sim/assignments.json`, `rules/known_fraud_checks.md`, `SUBMISSION_FORMAT.md`.

### Open (the planner must decide; see Open Questions)
- Judged run end. Who answers during judging (J20). Credit gate versus J11. Deadline wording when the latest time has passed. Flags raised after a deal is Closed. Authentication on the live reply endpoint.

### Out of scope for Phase 4
- Auth, a database, pricing and covenants, e-signature, real email/Slack (REQUIREMENTS.md Out of Scope; V2-03).
- Nemotron polish of memo and message text (MOVE-10 allows it only as prose polish; NEM-06 is Phase 6).
- The fraud hold decision itself (Phase 5 `prism/fraud/decide.py`), the graph endpoint, the investigator and the red-team.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stage machine, gates, exits, `stage_log` | Engine (`prism/move/stage.py`) | — | Deterministic event loop per deal |
| Routing to people (OOO, backups, $250k split, round-robin) | Engine (`prism/move/routing.py`) | Data (`teams.json`, `assignments.json`) | No person id in code; all from data |
| Stuck-deal ladder, alerts, escalation | Engine (`prism/move/sla.py`) | UI displays `sla_pct` | Exactly-once thresholds need one owner |
| Fraud hold decision (`flagged`, `held`, `stage_at_flag`) | Engine Fraud (`prism/fraud/decide.py`, Phase 5) | Move consumes | Move never sets or clears `held` |
| Freeze, `fraud_hold` request, chase | Engine (`prism/move/stage.py`) | — | Freeze is Move's job once flags exist |
| Credit memo, short version | Engine (`prism/move/credit_memo.py`) | API exposes; Nemotron may polish prose (Phase 6) | Grade is deterministic |
| Message wording | Engine (`prism/move/messages.py`) | Nemotron polish optional | Templates are the fallback and the spec |
| Human replies (judges or scripted) | API (`prism/api/app.py`) | Engine `inbox.record_reply` | One reply path for personas and API |
| Clock advance and replay | API or UI | Engine tick loop | Decision A vs B below |
| Time view (stage, SLA, held, inbox at clock time) | UI (`ui/src/time/timeview.ts`) | API serves full-run records | UI already filters by time |

## Standard Stack

No new packages. Everything Phase 4 needs is already a dependency.

| Library | Source | Use in Phase 4 |
|---------|--------|----------------|
| Python 3.13 | CLAUDE.md path | Runtime |
| pydantic >= 2 | `pyproject.toml` `"pydantic>=2"` | Contract models in `prism/contract.py` |
| fastapi (unpinned) | `pyproject.toml` `"fastapi"` | Live API in `prism/api/app.py` |
| pyyaml | `pyproject.toml` `"pyyaml"` | `config/move.yaml` via `yaml.safe_load` only |
| uvicorn | `pyproject.toml` `"uvicorn"` | Serve the API |
| pytest, httpx | `pyproject.toml` `[project.optional-dependencies] dev` | Tests, including FastAPI TestClient |

Commands (Windows, Git Bash):

```bash
PY=/c/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe
export PYTHONUTF8=1
$PY -m pytest -q                                   # full suite, about 2 minutes (03-04-SUMMARY)
$PY -m prism run --folder data/participant/shared_folder --arrivals data/participant/sim/arrivals.jsonl --out out/submission.json
$PY -m prism validate out/submission.json --folder data/participant/shared_folder
bash scripts/gate.sh                               # pytest, run, validate, tuning-only score (D-02)
MOCK=0 $PY -m uvicorn prism.api.app:app --port 8000
$PY -m prism.derive                                # regenerate derived fixtures after a contract change (docs/CONTRACT.md)
```

Measured this session: one full sample run takes 21.6 s and is byte-identical to `out/submission.json` (the gate output). [VERIFIED: run this session with `--out` to the scratchpad, then `cmp`]

Package legitimacy audit: not required, because Phase 4 adds no external packages.

## Architecture Patterns

### Per-tick data flow (current code)

```
arrivals.jsonl ──visible_files(now)──► Read: classify, extract facts, issues (prism/read)
                                              │
                                              ▼
                       Fraud: decide.evaluate → flagged, held, flagged_at  (STUB today)
                                              │
                                              ▼
 human answers (persona via due time, or API via record_reply)
        │                                     ▼
        └──► Move.step_deal(now): freeze → info_request → required facts → blocking issues
                                   → human gate → exit → ladder alerts → deadline-risk alert
                                              │
                    stage_log · human_requests · alerts · fraud  →  submission JSON and API
```

Evidence: per-tick order in `prism/engine/run.py:171-216` and in the header of `prism/engine/state.py:3-15`. [VERIFIED: read this session]

### Move's event loop
`step_deal` (stage.py:611-628) catches up everything between the previous call and `now`. Pass 1 replays events strictly before `now` with the previous view of Read's issues. Pass 2 replays events up to and including `now` with the current view. Events are ordered by `(time, priority, seq)`, with priorities `P_START, P_FREEZE, P_LADDER, P_CHASE, P_ANSWER, P_EVAL = 0, 1, 2, 3, 4, 5` (stage.py:29). [VERIFIED: stage.py read this session]

### Live API: two designs (decision needed)

- **Option A, precomputed run.** Run the sim once and serve deals, detail, alerts and submission from that run. The clock is UI-side, which matches what `ui/src/time/timeview.ts` already does (`stageAt`, `slaPctAt`, `heldAt`, `inboxAt` filter full-run records by time). A reply re-runs the sim with a reply log. Measured cost is about 22 s per reply. No refactor is needed, but reply latency is poor.
- **Option B, incremental.** Factor the per-tick body of `run_sim` (run.py:171-216) into a function that keeps `states` between calls. `advance(now)` runs every tick at or before `now`. A reply is `inbox.record_reply(state, rules, idx, option, now)` followed by `move_stage.step_deal(state, rules, now)`. [ASSUMED: the second `step_deal` at the same `now` applies the newly recorded answer. Test it before relying on it.] The refactor touches `run.py`, which is committed on main now (`9ac7498` wired VL into `run_sim`). Check `git status` before editing.

**Recommendation:** Option B if the refactor fits in about 90 minutes. Otherwise Option A, with the reply re-run, and state the latency in the handoff to Jesse.

## Current State: What Move Already Does

Status key: **Built** = implemented and covered by a test. **Partial** = implemented with a gap. **Missing** = not implemented.

| Req | Status | Evidence (file:line) | Gap to close |
|-----|--------|----------------------|--------------|
| MOVE-01 order, never advance while waiting | Built | `stage.py:211-244` `_evaluate`; `stage.py:263-283` `_exit_stage`; `config/move.yaml:13-39` | OLD_TRICK never freezes the deal (see OLD_TRICK section). Credit does not block on Product-stage items (J11; see Open Q3) |
| MOVE-02 `stage_log` with seen, decided, why | Partial | `stage.py:86-89` `_log_enter`; `stage.py:204-208` `_exit_why`. Tuning output: "Checked: ... All required items are present and consistent with the application. Moving to Credit." | "What was seen" is the static `required_to_exit` checklist plus the decision. No per-fact evidence. Acceptable under J9/J11; enrich only if time |
| MOVE-03 routing | Built | `routing.py:122-153` `_primary`; `routing.py:108-119` `committee_delegated` (integer cents); `routing.py:88-97` `available`. Tuning output: Priya credit to marcus.lee with "You are covering for Dana Whitfield"; Garza committee to priscilla.nguyen | Fraud-hold routing is untested on real data (no flags yet). Add a unit check that `victor.hale` is the first id parsed from `stages.json` `who_decides` |
| MOVE-04 ladder 100/150/200, exactly once | Built | `sla.py:25-29` `_LADDER`; `sla.py:71-82` `next_threshold`; `sla.py:93-117` `ladder_alerts`. Tuning output (Bluebonnet): alerts 17:31, 21:31, 01:31 = 8, 12, 16 h | Run end truncates later steps (see Run end) |
| MOVE-05 unanswered reroutes to backup | Built per J21 | `inbox.py:132-147` `send_reminder_and_copy` (reminder plus backup copy at 100%, first answer wins via `record_reply` superseding); 150/200% are alerts (`sla.py:93-117`) | "Re-routed" is implemented as a copy to the backup, not a moved request. Accepted by J21 and MESSAGE_TEMPLATES §2. Confirm wording with the user |
| MOVE-06 needed-by priority and deadline alert | Partial | Projection `deadline.py:81-92`; deadline-risk once per deal `stage.py:565-588`; `needed_by_badge` `deadline.py:118-129`; `priority_key` `deadline.py:132-135`. Tuning output: Priya's deadline-risk alert fires at first arrival | `priority_key` and `needed_by_badge` have no caller outside tests and the contract (grep). No ordering in `/api/deals` or `/api/inbox`. Latest-time defects D1 and D2 |
| MOVE-07 borrower info request; no `credit_decision` on incomplete file | Partial | Borrower request `stage.py:254-257`, `messages.py:180-188`; Credit blocking `config/move.yaml:27-30` | A missing Product-stage item (for example `equipment_quote`) does not block Credit, yet the message says "File is complete" (`messages.py:237`). Decision needed (Open Q3) |
| MOVE-08 personas or inbox via API | Personas built; API missing | Personas `config/move.yaml:74-89`; `inbox.py:37-52`. API: `prism/api/app.py:43-45` `require_mock` 503s every route; `app.py:56` router dependency | Build the live read path and the reply path |
| MOVE-09 new paper on an in-flight deal | Partial, untested | Re-evaluation on view change `stage.py:46-58` `_view`, `stage.py:622-623`; late-arrival resolution covered by `tests/test_move_stage.py::test_late_arrival_clears_the_issue_and_credit_decision_goes_out_after` | No test where a new paper raises a new issue on an in-flight deal. `requested_issues` never clears (`runtime.py:53`), so a re-raised identical issue is not re-requested. No backward moves (see MOVE-09 section) |
| MOVE-10 credit memo on Committee | Built | `credit_memo.py:163` `build_credit_memo`; written on entering Committee `stage.py:115-118`; exit blocked without it `stage.py:286-289`. Tuning output: Garza grade 1 (Strong), Priya grade 2 (Satisfactory) | Not in the API: `DealDetail` has no `credit_memo` (`contract.py:229-236`). The committee message says "Full memo on the deal page", so the field is needed. Deadline clause defect D2 |
| MOVE-11 deterministic wording | Mostly built | `messages.py` throughout | Deviations D3 to D5 below |

## Tuning-Set Analysis (D-02: tuning deals only)

Baseline line, reproduced this session with `scripts/score_split.py out/submission.json`:

`TUNING facts 90/90 issues_exact 10/10 tp7 fn0 fp0 route 32/40 stage 8/10 flag 7/10 held 7/10 links 8/10`

[VERIFIED: script run this session on the existing `out/submission.json`]

Per-deal decomposition (tuning deals only, from the submission's `stage_log`, `human_requests`, `fraud` and the gold labels in `eval/gold.json`):

| Tuning deal | Route | Stage | Fraud | Cause |
|-------------|-------|-------|-------|-------|
| Pecan Grove Catering | 0/4 | Closed (gold Intake) | MISSED | Not flagged, so Move ran all four sign-offs. Gold: flagged and held at Intake. **Fraud-owned** |
| Ridgeway Freight Logistics | 0/4 | Closed (gold Intake) | MISSED | Same. **Fraud-owned** |
| Granite Bay Building Supply | 4/4 | Intake (ok) | MISSED | OLD_TRICK issues raised (`STMT_TAMPER`, `REV_INFLATION`) and they block Intake. No flag and no `fraud_hold` request (J17). **Fraud and Move gap** |
| Garza, Okafor, Priya | 4/4 | Closed (ok) | ok | Full path |
| Bluebonnet, Oakline, Westfield, tyler | 4/4 | ok | ok | Correctly stopped at Intake or Credit with requests |

Findings:
- **Route 32/40 and stage 8/10 are entirely the two ring deals.** Every route miss and both stage misses come from them. Move-owned columns are at 8/8 and 10/10 for the other deals.
- **Timing constraint for Phase 5.** Without a flag, Ridgeway's Intake exits at `2026-11-02T14:40-06:00` and Pecan Grove's at `2026-11-03T12:00-06:00` (submission `stage_log`). A flag that lands after those times produces Credit routing and a `final_stage` miss, because the scorer takes the furthest stage in `stage_log` (`score.py:58-64`). The Phase 5 target in ROADMAP (Ridgeway held Monday about 14:10) lands before the 14:40 exit, which is consistent with the gold.
- **The scored columns pull in different directions.** Gold `final_stage` is `Intake` for both ring deals, which requires the hold before Intake exits. Gold `fraud.latest_ok_stage` is `Committed`, which tolerates a later hold. Prefer earliness (M17, DETAILS §6). This is a Phase 5 decision, not a Move change.
- **Granite Bay needs only the flag.** Its routing and stage already match gold because the OLD_TRICK issue blocks Intake.
- **Phase 4 can only hold the Move-owned columns steady.** Any gain on route or stage comes from Phase 5 flags landing in time.

Caution (D-02): `out/gate_score.txt` and `scripts/gate.sh --final` print every deal, including the three holdout deals. Do not use them for Phase 4 tuning. The `history_flags` line in those outputs is Fraud-owned.

## Live API: Current Gap and Contract Shapes

What exists: `prism/api/app.py` serves fixtures only. `require_mock` raises 503 with `detail="engine not wired yet"` (app.py:43-45) and the router depends on it (app.py:56). `POST /api/inbox/{item_id}/reply` returns a fixture and stores nothing (app.py:115-128).

Shapes the engine must produce (the contract, verified this session):
- `DealSummary` (contract.py:205-223): `stage_entered_at: SimTime` on line 209 is required and not optional. `sla_hours: float = Field(gt=0)`. `needed_by_badge` is a `Literal["none", "ok", "at_risk", "overdue"]`.
- `DealDetail` (contract.py:229-249): validators reject `fraud.held` without `fraud.flagged`, and `fraud.flagged` without `flagged_at` and `stage_at_flag`. No `credit_memo` field.
- `InboxItem` (contract.py:277-298): `answer` must be one of `options` when `status` is answered. Required `options` list with `min_length=1`.
- `Alert` (contract.py:144-149) has no kind field, so a deadline-risk alert and a stuck-deal alert look alike in the feed. The message text differs ("Deadline at risk:" versus "has been in ... past its ... limit").

Pitfalls for the live API:
1. **Unstarted deals cannot be serialized.** A folder with no visible document has `stage_entered_at = None` (`state.py:71`), which fails `DealSummary`. Filter unstarted deals, or change the contract (regenerate fixtures and tell Jesse).
2. **Flagged deals fail until Phase 5 sets `stage_at_flag`.** Nothing in `prism/` sets `stage_at_flag` today (verified by grep). Guard serialization or wait for Phase 5.
3. **Superseded copies break `InboxItem`.** `record_reply` sets `o_req.answer = label` on the other requests in the group (`inbox.py:111-118`). `pending_requests` already excludes them (`inbox.py:82-90`). `GET /api/inbox?status=answered` must exclude them too.
4. **Item ids.** The fixtures use `inbox-001`. A stable id built from (folder, request index) keeps replies deterministic. [ASSUMED: design choice]
5. **Reply errors map to HTTP.** `record_reply` raises `ReplyError` (`inbox.py:24`) for an unknown or non-pending request (map to 409) and for an unknown option (map to 422). CONTRACT.md line 30 specifies 404 unknown, 409 already answered, 422 bad option.
6. **Persona default hides the inbox.** Default persona is `fast` (`config/move.yaml:75` `default: fast`; `:79` `fast: {wall_hours: 0, business_minutes: 15}`). Each request is answered by a persona after 15 business minutes, so a judge will rarely see a pending item. The inbox is only exercised with `slow`, `never`, or `by_person` settings. That is J20, the top open question.
7. **Priority ordering.** MOVE-06 needs `/api/deals` and `/api/inbox` sorted by `deadline.priority_key` (`deadline.py:132-135`), which has no caller today.
8. **Full-run payload for the UI.** The UI expects `stage_log`, `human_requests` and `alerts` with `at` and `answered_at`, so it can filter by clock time (Option A).

Reply path (proposed; the functions exist and are verified, the composition is [ASSUMED] until tested):

```python
# prism/api/app.py (proposed shape, not yet written)
from prism.move import inbox, stage as move_stage

def reply(item_id: str, body: InboxReply):
    folder, idx = parse_item_id(item_id)          # reject unknown forms with 404
    state = states[folder]                        # unknown folder -> 404
    inbox.record_reply(state, rules, idx, body.option, now)   # ReplyError -> 409/422
    move_stage.step_deal(state, rules, now)       # applies the recorded answer at `now`
    return inbox_item_for(state, idx)
```

Verified signatures: `record_reply(state, rules, idx, option, at)` (`inbox.py:93`), `step_deal(state, rules, now)` (`stage.py:611`), `ReplyError(ValueError)` (`inbox.py:24`), `pending_requests(state)` returns `(idx, HumanRequest)` pairs (`inbox.py:82`).

## Run End and Acceptance Runs

- Default end is last arrival plus 30 minutes: `end = max(arrival_times) + timedelta(minutes=end_grace_minutes)` (`run.py:159-160`, default 30 at `run.py:135`). The CLI passes `--end-grace-minutes` (default 30, `cli.py:35-36`) and `--end` (`cli.py:33-34`). [VERIFIED: read this session]
- Sample last arrival: `2026-11-04T14:40-06:00` (max of 173 arrivals in `data/participant/sim/arrivals.jsonl`). Default end is therefore Wed 11/04 15:10. [VERIFIED: computed this session]
- Sim week: `Sim time runs **Mon 2026-11-02 08:00 → Fri 2026-11-06 18:00 CT**.` [VERIFIED: data/participant/README.md:32]. The UI fixture clock has `"end": "2026-11-06T18:00-06:00"` [VERIFIED: fixtures/clock.json].
- Measured, tuning deals only, with `PRISM_MOVE_PERSONA=never` (run this session, output in the scratchpad):
  - Default end (Wed 11/04 15:10): Credit deals show only the 100% pair (two alerts). Garza, Oakline and tyler have no 150% or 200% entry. Pecan Grove has no alerts at all, because its 48-hour Credit limit is not reached before the end.
  - `--end 2026-11-06T18:00-06:00`: each stuck Credit deal has the 100% pair plus one 150% and one 200% entry. Each threshold is emitted once, and the last one is at or before Fri 18:00.
- **Recommendation:** run the criterion-3 acceptance with `--end 2026-11-06T18:00-06:00` and `PRISM_MOVE_PERSONA=never`. Confirm the judged end with the organizers (HANDOFF open question 9; ROADMAP note "The judged end time is unconfirmed"). Do not change the `run_sim` default without that decision.

## Defects Found in Move Output (verified on the tuning output)

**D1. Latest time for an intake sign-off is in the past.** Priya's deadline-risk alert (2026-11-03T08:46-06:00, to elena.ruiz and jordan.webb) reads: "To make it: Jordan Webb needs to finish Intake by Wed 10/28 12:09 PM CT." The sim starts Mon 11/02 08:00, so 10/28 is before the deal arrived. Cause: `deadline.latest_exit` (`deadline.py:100-109`) back-subtracts typical hours from `needed_by` without checking against `now`. The at-risk alert itself is correct: history medians (computed this session from `data/participant/history/stage_events.csv`) are Intake 4.0 h, Credit 22.35 h, Committee 13.5 h, Product 7.7 h, Committed 21.75 h and Closed 11.4 h. Those make about 7 business days of remaining work from Tuesday, which projects to Fri 11/13. Only the "latest" time is wrong.

**D2. Committee approval deadline is before the request.** Priya's committee request (sent 2026-11-03T09:50-06:00, per her Committee `stage_log` entry) reads: "Please approve or decline by Tue 11/03 4:09 AM CT." `deadline.answer_by` (`deadline.py:112-115`) returns `latest_exit(Committee)`. CREDIT_MEMO_TEMPLATE.md:138 defines the clause as "the latest time this approval can come and still fund by `needed_by`" and is silent on the case where that time has already passed.

**D3. "File is complete" is hard-coded.** `messages.py:237` writes `File is complete:` and `the bank's 5 known-fraud checks pass.` regardless of open items. [CITED: docs/MESSAGE_TEMPLATES.md:90 uses the same wording]. Interacts with MOVE-07 (Open Q3).

**D4. Wording deviations from `docs/MESSAGE_TEMPLATES.md`.** [VERIFIED: template lines and code lines read this session]
- Missing-page bullet. Template: `the complete {Month YYYY} statement: we received page 1 of {N} only` (MESSAGE_TEMPLATES.md:139). Code: `the complete {month} statement: one or more pages are missing from the copy we received` (messages.py:161). Verified in the Oakline output. Page counts are available from the Read page markers (`prism/read/text.py`, `page_markers`).
- Waiting-on for a missing page. Template: `page {x} of the {month} bank statement` (MESSAGE_TEMPLATES.md:51). Code: `a missing page of the {month} bank statement` (messages.py:398).
- Tax-return bullet. Template: `(for example, your {year} business tax return)` (MESSAGE_TEMPLATES.md:137). Code: `(for example, your latest year's business tax return)` (messages.py:156).
- Money. House style: `Money as "$248,000"` (MESSAGE_TEMPLATES.md:12). Credit decision shows cents, for example `$1,971,501.14` (`cents_text`, messages.py:87-88; Garza output).

**D5. Old-trick alerts point at a request that was never sent.** Granite Bay's Intake alert reads: "It is waiting on Fraud Operations to review the failed known-fraud check REV INFLATION. To unblock it: Fraud Ops places or releases the hold." The deal has no `fraud_hold` request (its `human_requests` is empty). Code: `messages.py:411-412` (`target.replace("_", " ")` also drops the underscore from the code name).

## OLD_TRICK: What the Rules Imply Move Should Do

- Rules: "A deal that trips one goes straight to Fraud Operations." [VERIFIED: data/participant/rules/known_fraud_checks.md:4]. DETAILS §2 line 62: "A deal that trips any of these goes **straight to Fraud Operations**." J17 (line 160): "`flagged: true` plus a `fraud_hold` request to Fraud Ops". M8: "OLD_TRICK → Fraud Ops (bank policy)" (MODEL_DESIGN.md:15).
- Current Move behavior: OLD_TRICK blocks every stage (`config/move.yaml:26` Intake, `:30` Credit, `:32` Committee, `:35` Product, and `.+` at `:37` Committed and `:39` Closed). Move sets no flag, no freeze and no `fraud_hold` request. The deal waits at its stage with alerts. The Granite Bay output confirms it.
- Move cannot own the flag: `held` is only set by Fraud (`grep` finds no assignment outside tests). Move never sets `held` (`stage.py:480` only writes the decision text).
- **Recommended boundary:** Phase 5 owns the flag. Any OLD_TRICK issue sets `flagged=true`, `held=true`, `flagged_at` equal to the issue's evidence arrival, `stage_at_flag` from `stage_log` at that time, and a plain-words `reason` that cites the code. Move then does the rest: freeze (`stage.py:359-366`), `fraud_hold` to victor.hale (`stage.py:475-486`), and the chase (2 h copy to monica.salas, 4 h escalation, `stage.py:500-518`, config `move.yaml:91-93`).
- Phase 4 work: keep the OLD_TRICK blocking lists. Add an end-to-end test with a synthetic OLD_TRICK-flagged deal at Intake and at Credit (the existing `test_old_trick_hold_names_the_failed_check` covers the message only). Re-check the Granite-style alert once the flag exists.

## Flags After a Deal Is Closed

`_candidates` returns no events when `rt.terminal` is set (`stage.py:316-317`). A flag raised on a Closed deal therefore produces no freeze, no request, no alert and no log entry. DETAILS §6 line 127 requires the weekend drop to re-check funded deals ("funded ones included. A Collections notice on a funded deal → trace its links."). Fraud would set `flagged` and Move would ignore it silently. Decide the behavior (Open Q5).

## MOVE-09: New Papers on an In-Flight Deal

- Code path: `_view` diffs issues and facts each tick (`stage.py:46-58`). A change sets `eval_pending` (`stage.py:622-623`). Late arrivals resolve issues (existing test).
- Not covered: a new paper that raises a new issue mid-run; a re-raised identical issue (`requested_issues` persists, `runtime.py:53`).
- No backward moves. An issue raised after its stage was passed does not reopen that stage. It blocks only the next money-out gate, because `_exit_stage` refuses to enter Closed while any issue is open (`stage.py:267-271`). That is safe and should be documented.
- Acceptance: add a test where a synthetic paper arrives mid-run on a deal at Credit and raises a new `MISMATCH` or `MISSING_PAGE`.

## Deadlines (MOVE-06): What Is Built and Missing

- Built: typical-duration projection (`deadline.py:81-92`); deadline-risk alert once per deal to the RM and owner (`stage.py:565-588`, `rt.emitted` key `deadline_risk`); `needed_by_badge` (`deadline.py:118-129`); `priority_key` (`deadline.py:132-135`).
- Not wired: `priority_key` and `needed_by_badge` have no caller outside tests and the contract (grep this session).
- Not built: DETAILS §5 "Sign-off requests for deadline deals go out early in business hours." `send_request` (`inbox.py:55-72`) writes at evaluation time with no business-hours shift.

## Recommended Plan Decomposition (planner decides)

| Priority | Item | Why | Rough size |
|----------|------|-----|------------|
| P0 | Live API read path: deals, detail, clock, alerts, submission from the engine; `MOCK=0` works; filter unstarted deals | Blocks I3 (Jesse's switch) | 60–90 min |
| P0 | Live reply path with `record_reply` and `step_deal`; superseded filtered; ids stable; 409/422 mapping | Success criterion 5; I3 | 45–60 min |
| P0 | Run-end policy for acceptance runs (explicit `--end`), and the decision on the default | Criterion 3 cannot be shown in a default run | 15 min plus organizer answer |
| P0 | D1 and D2: never emit a latest time at or before the request time; say the deadline cannot be met at typical speed | Visible, wrong times in judged messages | 30 min |
| P1 | OLD_TRICK end-to-end test with a synthetic flag (Phase 5 sets the flag) | Protects the freeze path before Phase 5 lands | 30 min |
| P1 | Credit-gate decision (Open Q3) and D3 wording | MOVE-07 | 20–30 min |
| P1 | Flags after Closed (Open Q5) | Silent drop today | 20 min |
| P1 | MOVE-09 test; priority ordering in `/api/deals` and `/api/inbox` | Criteria 4 and 5 | 30–45 min |
| P1 | Add `credit_memo` to `DealDetail`; regenerate fixtures; tell Jesse | Memo text says "on the deal page" | 20 min |
| P2 | D4 wording deviations; business-hours shift for deadline sign-offs; richer `stage_log` evidence | Polish | 60 min total |

Suggested order: API read path, reply path, run-end and D1/D2, then the P1 items. Each item needs the full gate (pytest, run, validate, tuning score) before commit.

## Phase 5 Interface (what must be true for the freeze to work)

Fraud must set these fields on `DealState.fraud` (`contract.py:152-158`):
- `flagged` and `held`: `held` is set by Fraud only (J5). Sticky (M17).
- `flagged_at`: the evidence arrival time, a `-06:00` sim time. Never earlier than the evidence it cites (DETAILS §6 line 124).
- `stage_at_flag`: the Move stage in force at `flagged_at`. Derive it from `stage_log`, not from `state.stage` after this tick's Move step. The validator warns when `stage_at_flag` is missing (`validate.py:87-88`).
- `reason`: plain words. Move's fraud message reads codes from this text with the regex `_CODE_RE` (`messages.py:464`) and from OLD_TRICK issues.
- `linked_deals`: current folder names and `H-` history ids.

Move then freezes at `flagged_at` clamped to the watermark (`stage.py:359-366`). Freeze events sort before evaluation events at the same time (`P_FREEZE=1 < P_EVAL=5`, `stage.py:29`), so a freeze at a tick stops that tick's exit. Move resumes only when both `held` and `flagged` are false (`stage.py:595-609`).

## Pitfalls

- **Determinism.** No wall clock, no unsorted set iteration. `run_sim` iterates `sorted(states)` each tick (run.py:187, 206). Keep it that way. `test_engine_has_no_wall_clock_or_randomness` guards the engine.
- **Tick set.** Ticks are arrival times, quiet-expiry times (`_quiet_expiry_ticks`, run.py:104-125) and `end`. Move catches up between ticks through its event loop, so an alert between two ticks is still emitted at its exact time.
- **Quiet rule.** Evaluation waits until `last_arrival + quiet_minutes` (`stage.py:302-310`; `config/move.yaml:4` `quiet_minutes: 30`).
- **SLA clock.** `sla_pct` is elapsed hours minus `frozen_total`, divided by the limit (`sla.py:120-133`). Ladder crossing times are `limit × pct + frozen_total` rounded half-up to whole minutes (`sla.py:57-60`). Business hours apply only to persona timing and gate due times (J16), never to the SLA clock.
- **Pinned state.** `DealState` fields are pinned by `test_deal_state_fields_pinned` (tests/test_engine.py). Move keeps its runtime on `state._move` (`runtime.py:76-81`). Do not add a field without updating the pinned test.
- **Per-Rules cache.** Round-robin order is stored on the `Rules` object (`routing.py:188-196`). Reuse one `Rules` per process in the API, or the intake order resets.
- **Event cap.** `MAX_EVENTS = 10_000` per call (`stage.py:27`). A runaway deal freezes only itself.
- **Message building.** Text uses f-strings and concatenation, never `str.format` on document-derived text (`messages.py:3-5`). A legal name with braces must pass through (test exists).
- **Holdout.** Do not analyze or tune on the three holdout deals (D-02). Criterion 6 in ROADMAP mentions a holdout deal's memo grade; check it only through the final aggregate line.

## Code Examples

Verified: the Move event ordering and the freeze constants.

```python
# prism/move/stage.py:29 (verified)
P_START, P_FREEZE, P_LADDER, P_CHASE, P_ANSWER, P_EVAL = 0, 1, 2, 3, 4, 5
```

Verified: the Fraud model that Phase 5 fills.

```python
# prism/contract.py:152-158 (verified)
class Fraud(ContractModel):
    flagged: bool = False
    held: bool = False
    flagged_at: Optional[SimTime] = None
    stage_at_flag: Optional[Stage] = None
    reason: Optional[str] = None
    linked_deals: list[str] = Field(default_factory=list)
```

Verified: the consistency rules the live API will enforce on `DealDetail`.

```python
# prism/contract.py:241-248 (verified)
if f.held and not f.flagged:
    raise ValueError("fraud.held requires fraud.flagged")
if f.flagged and (f.flagged_at is None or f.stage_at_flag is None):
    raise ValueError("fraud.flagged requires flagged_at and stage_at_flag")
```

## Open Questions

1. **J20: who answers during judging.** The default persona (`fast`, 15 business minutes, `config/move.yaml:79`) decides what judges see in the inbox. [CITED: docs/DETAILS_CHECKLIST.md:163, "Vijay? (top priority)"]. Recommendation: keep `fast` for the headless gate; default the live demo to `slow` or `never` for requests a human should answer. Confirm with the user.
2. **Judged run end.** Sim-week end `2026-11-06T18:00-06:00` (README:32; clock fixture) versus the engine default (last arrival plus 30 minutes). Affects criterion 3 and the late ladder steps. Recommendation: explicit end in acceptance runs, and confirm the default with the organizers.
3. **Credit gate: J11 or MOVE-07?** J11 says "block only at the stage that needs it" (DETAILS line 154). MOVE-07 and DETAILS §3 line 80 say "No `credit_decision` request on an incomplete file." Recommendation: keep J11 (the quote is a Product-stage requirement in `stages.json`) and change the credit-decision wording to list any open later-stage items instead of "File is complete". Needs the user's decision because the judges read this text.
4. **Deadline wording when the latest time has passed (D1, D2).** Omit the clause and say the deadline cannot be met at typical speed, or keep the time? Recommendation: say so explicitly; the template does not cover this case. [ASSUMED: wording]
5. **Flags raised after a deal is Closed.** Log only, or an alert to Fraud Ops for post-disbursement review (a new message template is needed)? Recommendation: a single alert to Fraud Ops, with wording agreed by the user. [ASSUMED]
6. **Authentication on the live reply endpoint.** Once live, any caller can place or release a hold or release funds through `POST /api/inbox/{id}/reply`. Accept for the hackathon (auth is out of scope in PROJECT.md), or add a shared token? Decide before the API is exposed.
7. **`DealSummary.stage_entered_at` for unstarted deals.** Filter them out, or make the field optional (contract change; regenerate fixtures; tell Jesse)? Recommendation: filter, to avoid a contract change this late.

## Security Domain

Security enforcement is on (`.planning/config.json` `"security_enforcement": true`, `"security_asvs_level": 1`, `"security_block_on": "high"`). [VERIFIED: .planning/config.json]

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No (auth is out of scope, PROJECT.md) | — |
| V3 Session Management | No | — |
| V4 Access Control | Yes, partially | `record_reply` validates the option and the pending state (`inbox.py:104-109`). No actor identity. See Open Q6 |
| V5 Input Validation | Yes | Option validated by `record_reply`; `item_id` parsing rejects unknown forms (404); folder names are looked up in the state map, never used as paths. Folder names contain apostrophes and ampersands (CONTRACT.md line 41) |
| V6 Cryptography | No | — |
| V7 Error handling and logging | Yes | Do not log `.env` or the NVIDIA key. Return fixed error messages (`ReplyError` text is safe) |

Known threat patterns for this phase:

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Forged or unauthenticated reply moves funds or lifts a hold | Spoofing, Elevation | Open Q6. Pending and option checks in `record_reply`; localhost binding or shared token |
| Reply to a superseded or answered request | Tampering | `record_reply` rejects non-pending requests (`inbox.py:102-103`) |
| Path traversal through folder names in `/api/deals/{folder}` | Tampering | Lookup in the state map only; 404 otherwise |

## Environment Availability

Skipped: Phase 4 adds no external dependencies. The Python 3.13 interpreter, the participant data pack and the test suite were all confirmed working this session (sample run in 21.6 s).

## Validation Architecture

Skipped: `workflow.nyquist_validation` is false in `.planning/config.json`. The test additions the planner needs are listed below instead.

## Recommended New Tests

- API (TestClient, `MOCK=0`): `GET /api/deals` returns the started deals from the engine; a reply via the API produces the same `stage_log` as the matching persona run; superseded copies never appear in `/api/inbox`; a second reply returns 409; a bad option returns 422.
- Run end: explicit `end` run emits each Credit threshold exactly once through Friday (criterion 3). A tuning-deal check only.
- Deadline guard: a synthetic deal whose latest time precedes its request never prints that time (D1, D2).
- Credit wording: a deal with an open Product-stage item does not say "File is complete" (or the gate blocks, per Open Q3).
- OLD_TRICK: a synthetic flagged deal at Intake freezes, sends `fraud_hold` to `victor.hale`, copies `monica.salas` at 2 hours, and never reaches Closed. Extend the existing test to Intake and check the alert wording.
- Flag after Closed: behavior as decided in Open Q5.
- MOVE-09: a new paper raises a new issue on an in-flight deal mid-run.
- Priority order: `/api/deals` and `/api/inbox` sorted by `priority_key`.
- Missing-page wording: includes the page count from the Read markers (D4).

## Sources

### Primary (read this session)
- `prism/move/stage.py` (full), `routing.py` (full), `sla.py` (full), `inbox.py` (full), `deadline.py` (full), `messages.py` (full), `credit_memo.py` (full), `runtime.py` (full), `settings.py` (lines 1-293), `timeutil.py` (full)
- `prism/engine/run.py` (full), `state.py` (full), `config.py` (full), `score.py` (full), `validate.py` (lines 1-111), `contract.py` (full), `cli.py` (lines 25-70)
- `prism/api/app.py` (full), `prism/fraud/decide.py` (full)
- `config/move.yaml` (full)
- `data/participant/rules/stages.json`, `contacts/teams.json`, `sim/assignments.json`, `rules/known_fraud_checks.md`, `SUBMISSION_FORMAT.md`, `README.md`, `history/stage_events.csv` (medians computed by script)
- `docs/DETAILS_CHECKLIST.md` §2 to §8, `docs/MESSAGE_TEMPLATES.md`, `docs/CREDIT_MEMO_TEMPLATE.md` (lines 1-160), `docs/CONTRACT.md`, `docs/MODEL_DESIGN.md`, `docs/SESSION_HANDOFF.md`
- `eval/README.md`, `scripts/score_split.py`, `scripts/gate.sh`
- `ui/src/time/timeview.ts` (lines 1-130), `ui/src/api/client.ts` (grep)
- `fixtures/clock.json`, `fixtures/inbox.json`, `fixtures/deals.json` (keys only)
- `.planning/ROADMAP.md` Phase 4 and Phase 5 sections; `.planning/REQUIREMENTS.md` MOVE-01 to MOVE-11; `.planning/quick/261107-qx3-*/261107-qx3-SUMMARY.md`; `.planning/phases/03-read-the-folder/03-01..03-04-SUMMARY.md`
- Tests (names only, by grep): `tests/test_move_*.py`, `tests/test_engine.py`, `tests/test_read_engine.py`

### Commands run this session (outputs in the scratchpad, not in the repo)
- `scripts/score_split.py out/submission.json` (tuning-only table and summary line)
- Tuning-only view scripts over `eval/gold.json` and `out/submission.json` (holdout entries filtered out before printing)
- `prism run` with `--out` to scratchpad: one default run (21.6 s, byte-identical to the gate output), one `PRISM_MOVE_PERSONA=never` run with the default end, and one with `--end 2026-11-06T18:00-06:00`
- Median hours per stage from `history/stage_events.csv`

### Secondary (MEDIUM)
- Phase 3 summaries (03-01 to 03-04) for Read hand-offs and the 18.6 s run figure (superseded by the measurement above)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Option B (incremental stepping) fits in about 90 minutes | Architecture Patterns | Fall back to Option A with 22 s reply latency |
| A2 | A second `step_deal` at the same `now` applies a newly recorded reply | Live API, reply path | Replies silently ignored or delayed a tick; needs a test before relying on it |
| A3 | Item id built from (folder, request index) is stable across runs | Live API pitfall 4 | Replies could target the wrong request after a re-run |
| A4 | Judges need `slow` or `never` persona to see inbox items | Live API pitfall 6 | Wrong persona choice leaves the inbox empty during the demo |
| A5 | Deadline clause should say "cannot be met at typical speed" when the latest time has passed | Defects D1, D2 | A different wording choice; the user decides |
| A6 | The judged run end is the sim-week end, Fri 11/06 18:00 | Run End | Acceptance runs cut at the wrong time; organizers unconfirmed |
| A7 | Ridgeway and Pecan Grove flagged before their Intake exits would match gold routing and stage | Tuning analysis | Logic-derived, not run; check after Phase 5 lands |
| A8 | `stage_at_flag` derived from `stage_log` at `flagged_at` is the correct value | Phase 5 interface | Wrong stage on a hold; scorer `latest_ok_stage` check fails |
| A9 | Hour estimates for the plan table | Plan decomposition | Schedule overrun on P0 items |
| A10 | Recorded behavior of the `fast` default persona during judging (J20 unknown) | Open Q1 | Demo shows an empty inbox |

**If this table is empty:** not applicable. Items A1 to A10 need the user's confirmation or a test before they become decisions.

## Metadata

**Confidence breakdown:**
- In-repo state and tuning-set analysis: HIGH. Read or re-run this session.
- Measured runs and run-end effect: HIGH. Measured this session.
- Live API design: MEDIUM. One design pass, nothing built.
- Schedule estimates: MEDIUM. Single-pass estimates.

**Research date:** 2026-11-08
**Valid until:** 2026-11-08 (deadline day). Re-check after any change to `prism/move/`, `prism/contract.py`, `prism/api/app.py` or `config/move.yaml`.
