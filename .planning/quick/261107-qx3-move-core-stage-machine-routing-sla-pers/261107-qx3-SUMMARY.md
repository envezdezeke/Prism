---
phase: 261107-qx3-move-core-stage-machine-routing-sla-pers
plan: 01
subsystem: move
tags: [stage-machine, routing, sla, ladder, fraud-freeze, deadline, credit-memo, personas, inbox]
requires:
  - phase: 261107-qez (engine skeleton, pinned entry points, loaders)
provides:
  - "prism.move.stage.step_deal: two-pass catch-up loop for the six-stage machine"
  - "prism.move.routing: route_gate, stage_owner, OOO windows, integer-cents committee split"
  - "prism.move.sla: sla_pct, sla_alerts, ladder crossing times, stage_limit_hours"
  - "prism.move.inbox: send_request, record_reply (single reply path), personas, reminders, fraud chase"
  - "prism.move.credit_memo: deterministic memo, grade, short version, get_credit_memo"
  - "prism.move.deadline: typical durations, project_finish, answer_by, needed_by_badge, priority_key"
  - "config/move.yaml: every Move rule value"
affects: [phase-3-read, phase-5-fraud, api, ui]
tech-stack:
  added: []
  patterns:
    - "per-deal runtime attached as state._move (DealState is pinned by a test)"
    - "event loop with priority sources, run in two passes (previous view, then current view)"
    - "single reply path: personas and the future API both call inbox.record_reply"
key-files:
  created:
    - config/move.yaml
    - prism/move/settings.py
    - prism/move/timeutil.py
    - prism/move/runtime.py
    - prism/move/messages.py
    - prism/move/inbox.py
    - prism/move/credit_memo.py
    - prism/move/deadline.py
    - tests/test_move_support.py
    - tests/test_move_routing.py
    - tests/test_move_stage.py
    - tests/test_move_pipeline.py
    - tests/test_move_memo.py
    - tests/test_move_sla.py
    - tests/test_move_fraud_deadline.py
    - tests/test_move_engine.py
    - tests/test_move_settings.py
  modified:
    - prism/move/routing.py
    - prism/move/sla.py
    - prism/move/stage.py
decisions:
  - "Exit decision text: auto stages 'advanced'; gate stages the answer option (approve, confirm, release); Product 'standard pricing for <product>' (J9)"
  - "Move resumes a frozen deal only when the fraud flag itself is cleared; the frozen interval is excluded from the stage clock (frozen_total) so ladder crossings shift by it"
  - "Reminder plus backup copy always fire at 100% for an unanswered gate (J21), regardless of persona, so a slow persona also draws them"
  - "The borrower info_request lists every requestable issue; mismatches go out immediately, missing items after the 30 minute quiet period"
metrics:
  duration: "about 1h30"
  completed: 2026-11-07
status: complete
commits: 3
plan_head_before: cea844b50ae55eec2284f780aaaed83401c48ef4
plan_head_after: 7af8cf5a51800eba0792c18e3019757da694b980
actuals:
  tokens: 50300
  tasks: 3
  commits: 3
---

# Phase 261107-qx3 Plan 01: Move core Summary

**Deterministic six-stage machine (Intake to Closed) with data-driven routing, an exactly-once 100/150/200 percent ladder, fraud freeze and chase, a credit memo that gates Committee, deadline-risk alerts, and one reply path shared by scripted personas and the future inbox API.**

Branch `worktree-agent-a793ffef9d4847311`, three task commits plus this summary commit. Everything is built and tested on synthetic rules and synthetic facts; Read and fraud are still stubs in this tree.

## Commits

| Task | Commit | What |
|------|--------|------|
| 1 tracer | 9124e12 | config/move.yaml, settings, timeutil, runtime, routing, messages (tracer subset), inbox send/record, stage loop with START/EVAL/IMMEDIATE, routing and tracer tests |
| 2 | 414d2ee | ANSWER source and personas, record_reply stage effects (advance, stop, request_info), committee memo (credit_memo.py), commitment and funding messages, Product vendor check, Closed guards, pipeline and memo tests |
| 3 | 7af8cf5 | SLA ladder, reminder plus backup copy, FREEZE and CHASE, deadline.py, deadline-risk, engine and settings tests |

## Verification

- `PYTHONUTF8=1 py -3.13 -m pytest -q`: **295 passed, 5 skipped, 1 warning** (baseline in this worktree was 163 passed, 5 skipped; the 5 skips are the data/-dependent tests because data/ is gitignored and absent here).
- Person-name guard grep over `prism/move` and `config/move.yaml`: no matches.
- Sample-literal scan (all 13 shared-folder names, `H-\d{4}`) over every `prism/**/*.py`, `config/fraud.yaml`, `config/move.yaml`: no offenders (run by script against the main checkout's data, read-only).
- Scope check (`git diff --name-only origin/main...HEAD` minus the allowed paths): empty. Only `prism/move/`, `tests/test_move*.py`, `config/move.yaml` and this plan's folder changed.
- Real-data smoke, no fakes (`python -m prism run` on the main checkout's `data/participant`, output to scratchpad): 13 deals, 173 files, 172 ticks, 0 errors; `python -m prism validate ... --folder ...` exits 0 (**valid**). Read is a stub, so every deal enters Intake on its first document and waits for facts, as expected.
- Extra real-rules smoke (not a gate): real stages.json, teams.json, assignments.json and history, real arrivals, Read monkeypatched to fake facts and no issues, end 2026-11-20. Fast persona: all 13 deals reach Closed with 6 log entries and 4 requests each, output validates. Never persona: all 13 sit at Credit with the credit_decision, reminder and backup copy, and 4 ladder alerts each (owner, RM, owner's manager, second escalation person), output validates. Real names and routes resolved from the data (Dana's out-of-office window, Priscilla below $250,000, round-robin intake).

## What was built (key behaviors, all covered by tests)

- **Stage machine**: first document starts Intake (J1); nothing is judged until the folder is quiet 30 sim-minutes (J11); borrower `info_request` first, listing everything missing at once, and never a `credit_decision` on an incomplete file; mismatches get an immediate request and keep the deal in Intake (J15); every stage writes entered/exited/decision/why; waiting on a document, a human answer or a hold means no advance.
- **Routing**: no person id in code. Credit officer or backup inside the teams.json out-of-office window (both edges inclusive), committee delegated approver at 24,999,999 cents or less and chair above (float, int and string amounts), RM, funding owner, fraud analyst then backup, round-robin intake by first-seen order. Proven by a test that renames every person.
- **Ladder**: 100% to owner and RM (two entries, J3), 150% to the owner's escalates_to, 200% to the second-escalation person (always sent, J4); exact crossing times across 20+ hour jumps; exactly once; delegated committee 24/36/48h, chair 48/72/96h.
- **Reminders (J21)**: at 100%, reminder to the same person plus the same request to their available backup, same group, first answer wins and the rest are marked `superseded`.
- **Fraud (J5, J22, J17)**: flagged or held freezes at `flagged_at`, log says "awaiting Fraud Ops", SLA frozen, one `fraud_hold` request to the analyst, copy to the backup after 2h, escalation alert to the backup's escalates_to 4h later; never reaches Closed.
- **Personas**: fast, slow, ooo, never; answers only in business hours (J16); config-selected by default, by person or by type; `PRISM_MOVE_PERSONA` overrides the default.
- **Credit memo**: built once on entering Committee, 9.0 percent assumed rate from config, exact Fraction/Decimal arithmetic, grade bands and boundary rules from the template; reproduces the template's worked example (27,411 a year, 2.71x, grade 2) and the four sample cases (5,400; 108,000; 36,730; 61,782; grades 1, 1, 2, 2). The 4-line short version is the committee request message plus the delegated-limit sentence on the delegated route. Committee cannot exit without the stored memo.
- **Deadline (J18)**: one risk alert to RM and stage owner as soon as the typical-duration projection (history median, SLA hours fallback, business hours for sign-offs) passes `needed_by`; `answer_by` clause on the committee message for deadline deals only; `needed_by_badge`; `priority_key`.

## Deviations from Plan

### Auto-fixed / judgment calls

**1. [Rule 1 - Bug] EVAL order: borrower requests before the required-facts check**
- **Found during:** Task 1 design
- **Issue:** The plan's step order (1 facts, 2 requests) means a deal whose application is missing has no `legal_name` or amount, waits at step 1 forever, and the borrower is never asked for the missing application.
- **Fix:** requestable issues are sent first, then required facts, blocking issues, gate, exit.
- **Files:** prism/move/stage.py. **Commit:** 9124e12

**2. [Rule 2 - Missing functionality] Move resumes when the fraud flag is cleared**
- **Found during:** Task 3
- **Issue:** The plan says "Closed ... after release the deal is terminal" but also "Move never unfreezes". A cleared flag (by the fraud module or a human) with a permanently frozen runtime would strand the deal.
- **Fix:** Move never releases a hold itself (a `release_hold` reply is only logged); it resumes only when `fraud.held` and `fraud.flagged` are both false. `frozen_total` keeps the frozen interval out of `sla_pct` and shifts ladder crossing times by it. The freeze note is kept on the stage's exit text.
- **Files:** prism/move/stage.py, sla.py, runtime.py. **Commit:** 7af8cf5

**3. [Rule 3 - Blocking] Real-data copy into the worktree was denied**
- **Issue:** Task 3 step 7 says to copy `data/participant` into the worktree for the engine's data-dependent tests. The sandbox blocked the copy (brief also says never copy data into the tree).
- **Fix:** The 5 data-dependent tests stay skipped in this tree (they were skipped at baseline too). The same checks were run read-only against the main checkout: CLI smoke on the real files, sample-literal scan, and the person-name grep. Results above.

**4. Smaller departures (no behavior risk)**
- Added a ninth test file, `tests/test_move_settings.py` (config validation, env selection, event cap), inside the allowed `tests/test_move*.py` glob.
- Code the plan assigned to later tasks landed earlier where it was small and shared (`record_reply` and persona due times in task 1's inbox.py, the generic gate message in task 1's messages.py); each is tested in the task that owns its behavior.
- The tracer test and the never-persona test were re-timed in task 3 because the 100% reminder and backup copy (J21) now correctly appear once a request is older than the stage limit.
- A few contract literals appear in code because they are fixed by `prism.contract` (the `Product` stage name for the vendor check, the "Revolving Line of Credit" product for interest-only payment, the five OLD_TRICK codes in the fraud-hold wording, the `H-` history prefix for linked past loans). No person id, folder name or history id literal exists.

## Known Stubs

None in Move. (Read facts and fraud decisions are not Move's; see hand-off notes.)

## Threat Flags

None. No new endpoint, auth path or file access beyond reading `history/stage_events.csv` with the `csv` module (T-qx3-04), which the threat model already covers.

## Hand-off notes

**For the orchestrator / merge**
1. Nothing outside `prism/move/`, `tests/test_move*.py`, `config/move.yaml` and this folder changed, so the branch should merge cleanly against the Read and fraud workstreams. Merge order does not matter.
2. After the merge run the full suite once with `data/participant` present so the 5 skipped data tests run (CLI smoke and the sample-literal scan).

**For the engine owner**
3. `run_sim` only ticks at arrival times and `--end`. The CLI default `end` is None, so nothing after the last arrival (answers, ladder alerts, deadline risk) reaches the submission. Recommend a final tick at a clock end or last arrival plus a horizon (`end` works today: `run_sim(..., end=...)`).
4. `DealState` has no Move field; the runtime hangs off `state._move` (`prism.move.runtime.get_runtime`). A first-class field would be cleaner but needs an engine change and a pinned-test update.

**For Read (Phase 3)**
5. Report open `issues` on every tick regardless of the quiet period (Move owns the 30 minute gate via `last_arrival_at`).
6. Fill `legal_name` and `amount_requested` (Intake will not exit without them), plus `product`, `term_months`, `purpose_category`, `annual_revenue_stated`, `needed_by`.
7. Fill `state.features["profile"]` for the memo and messages (money in integer cents): dba, ownership, formation_date, application_date, preparer, use_of_proceeds, collateral, statement_months, tax_doc ("tax_return" or "form_7004"), net_income_ytd_cents with ytd_months (or net_income_fy_cents), deposits_annualized_cents, cash_cents, receivables_cents, liabilities_cents, relationship {status: new | returning_clean | returning_past_due, since_year}, quote {number, vendor, total_cents, remit_last4}, vendor_verified (an explicit False blocks Product for equipment loans), vendor_past_loans, disbursement {kind: borrower | vendor, bank, last4, vendor, past_loans}, mismatch_evidence {field: {application, document, value}}. A missing value prints "not provided" and the memo scores that test conservatively with a confidence line. Also `features["fraud_watch"]` (reason string) for the watch tier.

**For fraud (Phase 5)**
8. Move turns `fraud.flagged or fraud.held` into the freeze and the `fraud_hold` request. Set `flagged_at` (Move clamps it to the processing window), `reason` and `linked_deals` (current deals by folder name, past loans start with `H-`). Move never sets or clears `held` itself, so the fraud module must set `held: true` when it requests a hold (J5) and keep it sticky; Move resumes only if you clear both flags.
9. An OLD_TRICK issue blocks every stage until fraud flags the deal.

**For the API (the live inbox, ROADMAP SC5)**
10. Use `inbox.pending_requests(state)` (list of `(index, HumanRequest)`), `inbox.gate_options(type)` for the buttons, and `inbox.record_reply(state, rules, idx, option, at)` to answer. It raises `inbox.ReplyError` (a `ValueError`) for an unknown request or option or a request that is not pending. The next `step_deal` applies the answer. Superseded copies carry the label `superseded` as their `answer` (config `responder.superseded_label`), which `InboxItem` validation rejects unless the API filters them out.
11. `deadline.needed_by_badge(state, rules, now)` and `deadline.priority_key(state)` are ready for the summary payload and inbox ordering.
12. `credit_memo.get_credit_memo(state)` and `credit_memo.credit_memo_to_dict(memo)` are ready for a `credit_memo` field on `DealDetail` (contract change, outside the fence).

**Decisions you may want to revisit**
13. Default persona is `fast` (15 business minutes), which makes every deal sail through on a real run. The judges' answering mechanism is open (J20); switch with `PRISM_MOVE_PERSONA` or `config/move.yaml`.
14. Round-robin intake order is first-seen per `Rules` object, correct under `run_sim` because ticks are arrival times and each tick steps deals in folder-name order.
15. Not claimed: MOVE-09 (new paper on an in-flight deal). Move re-evaluates from the current issue list on every call, which supports it, but no test or requirement claim is made here.

## Self-Check: PASSED

- Files exist: config/move.yaml, prism/move/{settings,timeutil,runtime,messages,inbox,credit_memo,deadline}.py, tests/test_move_{support,routing,stage,pipeline,memo,sla,fraud_deadline,engine,settings}.py.
- Commits reachable from HEAD: 9124e12, 414d2ee, 7af8cf5.
- Full suite green (295 passed, 5 skipped).
