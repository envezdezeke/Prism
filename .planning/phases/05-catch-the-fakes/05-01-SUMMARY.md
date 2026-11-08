---
phase: 05-catch-the-fakes
plan: 01
subsystem: fraud
status: complete
tags: [fraud, hold-rule, sticky-holds, old-trick]
requires: [F1/F3/F5 signals (prism/fraud/signals.py), Move freeze + fraud_hold request (prism/move)]
provides: [decide() hold rule, OLD_TRICK path, sticky Fraud blocks, flagged_at, stage_at_flag, plain-words reason, current-deal linked_deals]
affects: [prism/engine/run.py fraud step (unchanged call site), Move freeze/request via Fraud.flagged/held]
tech-stack:
  added: []
  patterns: [stickiness carried in states[folder].fraud (no module state), config-driven hold rule]
key-files:
  created: [tests/test_fraud_decide.py, tests/test_fraud_sample.py]
  modified: [prism/fraud/decide.py, prism/fraud/signals.py]
decisions:
  - "Reason wording: OLD_TRICK sentence first ('Known-fraud check X and Y failed on this deal's own documents, so it goes straight to Fraud Operations under bank policy.'), then 'Held by the cross-deal fraud screen.' plus one '<Family label>: <evidence>.' sentence per fired voting family; F1 evidence cut at LINK_MARK so no partner id appears."
  - "A sticky (already flagged) deal grows linked_deals only on a tick where the hold rule is met, so an OLD_TRICK-only deal never gains links from a lone F1."
  - "Partners for linked_deals come from the cfg.hold_required families' signals (F1 in config), filtered to current deals; history ids wait for Plan 02."
requirements: [FRD-04, FRD-05, FRD-07]  # FRD-05 complete; FRD-04 (watch tier) and FRD-07 (holdout + history half) finish in Plan 02
metrics:
  duration: ~35 min
  completed: 2026-11-08
estimate:
  tokens: 60000
  tasks: 3
actuals:
  tokens: 4900   # chars/4 over the realized diff (19647 chars)
  tasks: 3
  commits: 3
plan_head_before: 45d8039852745183152ed3917157a2214392aab6
plan_head_after: 39e4e78e261f9896f3d7d5a44bc07b4c552d34a3
---

# Phase 5 Plan 01: Hold rule and OLD_TRICK path Summary

`decide()` now applies the config hold rule (F1 plus two more voting families) tick by tick, flags any deal with an open OLD_TRICK check on its own, and keeps every hold sticky. On the tuning deals, route, stage, flag and held all reach their maximum, and none of the seven good deals is flagged.

## Gate (tuning only)

- Before (Phase 4 research baseline): `TUNING facts 90/90 issues_exact 10/10 tp7 fn0 fp0 route 32/40 stage 8/10 flag 7/10 held 7/10 links 8/10`
- After: `TUNING facts 90/90 issues_exact 10/10 tp7 fn0 fp0 route 40/40 stage 10/10 flag 10/10 held 10/10 links 8/10`
- pytest 888 passed, 1 skipped; run 13 deals, 0 errors; validate valid, errors=0, warns=0 (no flagged deal is missing flagged_at or stage_at_flag).
- Byte-identical: a second `python -m prism run` into the scratchpad matches out/submission.json exactly (cmp). tests/test_fraud_sample.py also checks that two run_sim calls give the same output.
- Links stay at 8/10 because the two ring deals' gold links include history ids. Plan 02 handles that.

## Flagged tuning deals

| deal | path | flagged_at | stage_at_flag | linked_deals |
|------|------|------------|---------------|--------------|
| Ridgeway Freight Logistics | hold rule (F1+F3+F5) | 2026-11-02T14:05-06:00 | Intake | 2 current partners |
| Pecan Grove Catering | hold rule (F1+F3+F5) | 2026-11-03T11:25-06:00 | Intake | 2 current partners |
| Granite Bay Building Supply | OLD_TRICK:STMT_TAMPER | 2026-11-03T16:08-06:00 | Intake | [] |

Each one is frozen at Intake: one stage_log entry with decision "held" and no exit, one fraud_hold request to the first fraud decider at flagged_at, and no Closed entry.

## Tasks

| # | Task | Commit |
|---|------|--------|
| 1 | Tracer: hold rule, sticky blocks, stage_in_force, reason, current-deal links | c4ea2b3 |
| 2 | OLD_TRICK path flags a deal by itself | a7b76d1 |
| 3 | Sample gate: Move freezes and sends the request, good deals untouched, determinism | 39e4e78 |

## Files

- prism/fraud/decide.py: decide(), _hold_met, _current_partners, stage_in_force, old_trick_codes, build_reason
- prism/fraud/signals.py: the LINK_MARK constant, which _f1_evidence now uses (output is unchanged)
- tests/test_fraud_decide.py: 14 unit tests on synthetic states
- tests/test_fraud_sample.py: 8 tuning-only sample tests (skipped without data)

Nothing changed under prism/read, prism/move, prism/api, prism/engine/run.py or ui/ (checked with git diff).

## Deviations from Plan

1. **[Rule 1 - Bug] A sticky deal adds links only from a tick that met the rule.** The plan said to union the previous and current partners on every sticky tick. That would let the OLD_TRICK-only deal pick up partners from a lone F1 signal, and gold lists no links for that deal. Now partners are added only when the hold rule is met on that tick. A test covers this case.
2. **The test asserts the fraud decider without naming it.** The plan said to assert `victor.hale`. The test reads the first id from `stages.fraud_hold.who_decides` through `prism.move.routing.ids_in` instead, so no sample literal is needed. On the sample this resolves to the same person.
3. **The sample tests for Task 1 cover only the ring deals.** The full flag/held match against gold needs the OLD_TRICK path from Task 2, so that assertion went into the Task 2 commit.

## Hand-off notes for Phase 4

None. The run.py call site, Move's freeze and the fraud_hold message all work unchanged with the new Fraud blocks.

## Known Stubs

history_flags and clusters stay empty on purpose. Plan 02 owns them.

## Self-Check: PASSED

- FOUND: prism/fraud/decide.py, prism/fraud/signals.py, tests/test_fraud_decide.py, tests/test_fraud_sample.py
- FOUND commits: c4ea2b3, a7b76d1, 39e4e78
