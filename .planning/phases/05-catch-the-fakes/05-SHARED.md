# Phase 5 shared notes: Catch the Fakes

Every Phase 5 plan lists this file in its context. It holds what more than one plan needs: environment, the shared-tree rules, the interfaces that must not move, the planning decisions (P5-xx) the plans implement, the measured baseline, the standard verification protocol and the source audit. Locked design is `docs/MODEL_DESIGN.md` (M1 to M21) and `docs/DETAILS_CHECKLIST.md` (J-calls). Where a P5 decision refines an M item it says so; no M item is reversed.

## 1. Environment

- Python: `.venv/bin/python` on Jesse's Mac (3.12). Ezekiel's Windows path is in `.claude/CLAUDE.md`. Always `PYTHONUTF8=1`.
- `data/participant/` (gitignored) is present on this machine. Tests that need it must skip when it is absent (follow `tests/test_fraud_eval.py::test_smoke_on_real_history`).
- Nothing under `data/`, no PDF, no `.env` is ever committed. No new package is installed in this phase (stdlib, PyYAML and pydantic only).
- Commits: one atomic commit per task, after that task's verify passes, with the attribution trailer the orchestrator gives you. Stage files one by one. Never stage `.planning/state.json`. Do not push.

## 2. Shared working tree rules (plans in one wave run concurrently)

- Edit only the files in your plan's `files_modified`. Another plan in your wave is editing the others right now.
- `tests/test_fraud_baseline.py` is the one shared file in wave 1 (05-01 and 05-02) and is owned by 05-03 in wave 2. In wave 1 each plan edits ONLY the test functions named in its own task, with a scoped `Edit` (never a whole-file `Write`), re-reading the file just before editing.
- If `pytest` shows a failure in a test file you do not own, or an import error in a module you do not own, wait one minute and run it again. Never "fix" another plan's file. If it still fails, record it in your SUMMARY under "Cross-plan failures" and carry on with your own verify.
- `prism/read/` and `ui/` are being edited by Ezekiel and Jesse and are off limits. `prism/engine/run.py` is not touched by any plan in this phase (see the note in 05-01 about why it does not need to be).

## 3. Interfaces that must not move (pinned by `tests/test_engine.py`)

- `prism.fraud.decide.evaluate(states, baseline, cfg, now) -> FraudOutcome` and `decide(signals, graph, states, baseline, cfg, now)`. `run.py` calls `evaluate` once per tick, after ingest and before move, then writes `outcome.per_deal[name]` over `states[name].fraud` and keeps `outcome.history_flags`. It overwrites, so stickiness has to live inside `decide`.
- `FraudOutcome` fields: `per_deal: dict[str, Fraud]`, `history_flags: list[str]`, `clusters: list[Cluster]`. Fields may be added with defaults. `Fraud`, `Cluster`, `FamilyResult` are the `prism.contract` models (all six families F1..F6 in every Cluster, tier `hold`, `watch` or `none`).
- Move already freezes a deal when `state.fraud.held or state.fraud.flagged`, takes `flagged_at` as the freeze time, and sends the `fraud_hold` request (victor.hale, backup monica.salas) with `Fraud.reason` and `Fraud.linked_deals` in the text. Nothing in Phase 5 touches `prism/move/`.
- Read hands over (unchanged, may still be a stub): `state.entities: list[EntityRef(kind, value, source_doc)]` with kinds from `prism.contract.EntityKind`; `state.features["deposit_months"]`: a list of rows with the history column names (`deposit_count`, `pct_deposits_multiple_of_100`, `deposit_weekdays`, ...); `state.docs[i].doc_class` and `state.docs[i].meta["producer"]` (document class and PDF producer); `state.issues` containing `OLD_TRICK:<CODE>`; `state.facts`. Fraud code must treat every one of these as possibly absent.
- `tests/test_engine.py` pins `config/fraud.yaml` values: percentiles exactly F2..F5 at 0.95, `rarity_fraction` 0.02, `min_linked_deals` 2, hold rule `F1` plus `F2..F5` with `min_additional` 2, `history_flags.min_links` 2, and the three calibration dates. No plan changes these. New knobs go in NEW keys; code reads them from `cfg.raw` with documented defaults.
- Determinism: no wall clock, no `random`/`uuid`/`secrets` imports in `prism/` (AST-tested), sorted iteration everywhere, ties broken lexicographically. No sample literal (deal, company, person, vendor, account, producer name; `H-` plus digits) in `prism/` or `config/`. Tests use only fake values.

## 4. Planning decisions (planner discretion unless an M or J number is cited)

- **P5-01 Qualifying link.** Two deals are linked when they share a strong entity (rare against history, links at least 2 deals, as built in `graph.py`) whose kind is not weak (`address`, `bank`). The link qualifies when one shared kind is a solo kind (`preparer`, `phone`, `registered_agent`, `remit_account`) or the shared kinds cover at least 2 independent groups. Guarantor alone, vendor alone, producer alone, address and bank never qualify. This is where "returning customer" (same guarantor and address as its own old deal) stops being a ring signal (red-team R6).
- **P5-02 Independence groups (M18 hazard, R6).** `contact` = preparer + phone (a phone follows its preparer, one fact); `agent` = registered agent; `payee` = vendor + remit account; `tooling` = PDF producer; `identity` = guarantor. Counting links means counting distinct groups.
- **P5-03 Cluster = connected components of the current deals over direct qualifying links (M8 "clusters over strong F1 edges").** History deals attach to a component but never bridge two current deals.
- **P5-04 Hold per cluster (M8, R3).** F1 fired (the component has at least one qualifying link, to a current or a history deal) plus at least `hold_rule.min_additional` distinct fired families among `additional_from`, counted over the component's current members. F6 never votes.
- **P5-05 Inherit rule.** A member of a hold-ready cluster is held when it already was held, or it fired a family of its own, or its qualifying links to the other members span at least `inherit_min_groups` (2) groups. A mule deal with normal deposits is held when it shares the kit across two groups; a deal that only shares one agent with the ring is not.
- **P5-06 Stickiness lives in `decide` (M17).** A held or flagged block read from `states[d].fraud` is returned again unchanged (`flagged_at`, `stage_at_flag`, `reason`), except that `linked_deals` may grow. Weaker later evidence never un-flags.
- **P5-07 OLD_TRICK path (J17, M8).** Any `OLD_TRICK:<CODE>` in `state.issues` flags and holds the deal with a reason that names the code, whatever F1 says.
- **P5-08 `history_flags` (M18).** A history deal is flagged when it shares strong, non-weak entities with a hold cluster across at least `history_flags.min_links` (2) independent groups. M18 link types (c) "same F3 pattern" and (e) "matching deposit fingerprint" are not built; (a), (b) and (d) are.
- **P5-09 Calibration is relative to the data (M13, R4).** Real runs calibrate on every clean history deal, leave-one-out. No date from `config/fraud.yaml` is used outside the measurement-only report. A tau is never lower than the theoretical `-log2(1 - q)`.
- **P5-10 F3 is a categorical lookalike, F5 needs weekday AND unusualness (R2, R8).** See 05-02.
- **P5-11 Entity hygiene (R5, R7).** Per-kind canonical keys, placeholders and low-information values produce no entity, and outcomes weight rarity (distress up-weights, only `paid_off` counts as repaid). See 05-03.
- **P5-12 F4 and F1 may not double count (R2, R9).** A family signal carries a `basis` (entity kinds it was derived from). A signal whose basis lies entirely inside the cluster's qualifying-link kinds does not count toward the hold. See 05-05.

## 5. Measured baseline (commit f432288, planning time)

- `pytest -q`: 401 passed.
- `PYTHONUTF8=1 .venv/bin/python eval/run_synth.py --menus core,redteam --mode both`:
  - engine mode (decide is a stub): ring deals held 0.0% (0 of 1060), twins held 0.0% (0 of 1200).
  - proxy mode (F1 + F3 + F5 on the signal functions): ring deals held 26.5% (281 of 1060), twins held 0.08% (1 of 1200), twin watch friction 50.8%, background deals held 0 of 10300. Per trick ring held: R1 0%, R2 75%, R3 100%, R4 0%, T1 44.4%, T2 50.8%, T3 to T8 0%.
  - computed thresholds on the shipped history: tau F3 4.4263, tau F5 5.067, 104 clean calibration deals.
- Sample run (`python -m prism run` on `data/participant`): Read is a stub, so every deal has `flagged false`, `history_flags` is empty, and the self-score fraud columns read: flagged 9/13, held 9/13, linked_deals 10/13, history_flags missed 2/2.

## 6. Standard verification protocol (every plan records its numbers in its SUMMARY, before and after)

- **V1 tests:** `PYTHONUTF8=1 .venv/bin/python -m pytest -q` is green. Report the passed count.
- **V2 synthetic bench:** `PYTHONUTF8=1 .venv/bin/python eval/run_synth.py --menus core,redteam --mode both --out-dir out/synth_<plan id>` (about 20 s; `out/` is gitignored). Record, for engine and proxy: ring deals held %, twin deals held %, twin watch %, background held, and the per-trick ring held. Bars (MODEL_DESIGN M6.4): ring held at least 70%, twins held at most 5%. Plans before the families are complete are not expected to reach 70%; a twin hold rate above 5% is never acceptable and stops the plan (report, do not tune).
- **V3 trap checks (ROADMAP success criterion 3):** zero holds on the nine trap deals (Garza, Tyler, Priya, Okafor, Westfield, Harbor Tea, Oakline, LSFD, Bluebonnet) and zero history false flags, read from `eval/gold.json` (`deals[*].fraud`, `history_must_not_flag`). While Read is a stub the nine-deal check is vacuous (no entities); record the self-score fraud columns anyway. The history check is real: the plan's named real-data tests, and from 05-04 on `python -m prism.fraud.trap`.
- **V4 gate (AGENTS.md):** `.venv/bin/python -m prism run --folder data/participant/shared_folder --arrivals data/participant/sim/arrivals.jsonl --out out/submission.json`, then `-m prism validate out/submission.json --folder data/participant/shared_folder`, then `-m prism score out/submission.json --gold eval/gold.json`. The score must not go down. Read is changing in parallel, so attribute only the fraud columns (flagged, held, linked_deals, history_flags, must_not_flagged) to your plan.

## 7. Source audit (GOAL, REQ, CONTEXT = locked M/J decisions; no RESEARCH.md exists for this phase)

| Source | ID | Item | Plan | Status |
|---|---|---|---|---|
| GOAL | - | Hold the ring before money goes out, find linked and history deals, leave good deals alone, carry over to an unseen trick | 05-01 to 05-09 | COVERED |
| REQ | FRD-01 | History baseline (frequencies, dates, outcomes, producer per class, deposit distributions) | 05-02, 05-03, 05-05 | COVERED |
| REQ | FRD-02 | Graph of deals and canonical shared entities, rarity weights | 05-03, 05-06 | COVERED |
| REQ | FRD-03 | Families F1 to F6 with plain-words evidence | 05-02, 05-05, 05-07 | COVERED |
| REQ | FRD-04 | Hold rule, watch tier, OLD_TRICK to Fraud Ops | 05-01 | COVERED |
| REQ | FRD-05 | Freeze on flag, `held`, `stage_at_flag`, reason, `fraud_hold` request | 05-01 (Move already consumes the block) | COVERED |
| REQ | FRD-06 | `linked_deals`, `history_flags` | 05-01, 05-04 | COVERED |
| REQ | FRD-07 | Trap regression, Ridgeway held from history alone | 05-04, 05-09 | COVERED |
| CONTEXT | M1, M7, M8 | Bits of surprise, 95th percentile, hold rule | 05-01, 05-02, 05-05, 05-07 | COVERED |
| CONTEXT | M13 | Percentiles in config, thresholds recomputed and written out for audit | 05-02 (compute), 05-08 (audit file) | COVERED |
| CONTEXT | M17, M18 | Re-score every arrival, sticky holds, history flags need 2 independent links | 05-01 | COVERED, M18 types (c) and (e) not built (P5-08) |
| CONTEXT | M10, M11, M12 | Failure playbooks, build order F1 F3 F5 F4 F2 | 05-09, wave order | COVERED |
| CONTEXT | permutation p-value, PMI | Cluster evidence | 05-08 (cuttable) | COVERED |
| CONTEXT | M14 | Verification `info_request` to the borrower when F3 is in the watch evidence | none | OPEN: needs a `prism/move/` change. Jesse to decide (see the hand-off report). |
| CONTEXT | M17 | Human `fraud_release` clears a hold | none | OPEN: no release path exists anywhere in the repo; sticky forever satisfies J5 |
| CONTEXT | M19 | `docs/AUDIT.md` line per post-freeze change | 05-09 creates the file with the pre-freeze entries | COVERED |

## 8. Cut list for this phase (cut in this order, never cut the first four plans)

1. 05-08 permutation p-value, PMI, audit file (evidence only, no score effect).
2. 05-05 Task 3 (F6 terms shape, evidence only).
3. 05-07 F2 burst (costs recall on two trick families, T6 and T7; nothing else depends on it).
4. 05-06 graph view builder (needed only when the UI leaves the mock; Phase 7 07-02 will report the gap).
5. 05-03 Task 3 (outcome-aware weights); keep Tasks 1 and 2.
Never cut: 05-01, 05-02, 05-04, 05-09, 05-03 Tasks 1 and 2, 05-05 Tasks 1 and 2.
