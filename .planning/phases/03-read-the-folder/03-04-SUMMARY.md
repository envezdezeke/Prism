---
phase: 03-read-the-folder
plan: 04
subsystem: read
tags: [integration-gate, holdout, determinism, nemotron-vl]
status: partial   # Task 1 (integration gate) done; Tasks 2 and 3 (Nemotron VL null-fill) NOT started, awaiting the orchestrator go/no-go

requires:
  - phase: 03-read-the-folder
    provides: classifier, parsers, statements, issues, old tricks, compare (03-01, 03-02, 03-03)
provides:
  - tests/test_read_integration.py (12 post-merge checks, synthetic seams plus real tuning deals)
  - recorded Phase 3 deterministic Read baseline and the one-time aggregate holdout verdict
affects: [Phase 4/5 (fraud consumption of OLD_TRICK), 03-04 Tasks 2-3 if the orchestrator runs them]

actuals:
  tokens: 2700
  tasks: 1
  commits: 1
plan_head_before: f0bb210d7fae8d265304246c2b06a5b2521a3168
plan_head_after: 3dff9fa93187c6ea3de25e9693cbda7cfb6a50d2

key-files:
  created:
    - tests/test_read_integration.py
  modified: []

key-decisions:
  - "Tasks 2 and 3 (VL) were not started: the plan's go/no-go clause says the executor returns TASK 1 DONE and starts VL only when the orchestrator's invocation says to continue; this invocation did not say so and called Tasks 2-3 first-to-cut."

requirements-completed: []
---

# Phase 3 Plan 04: Integration Gate on the Merged Read Tree Summary

**Task 1 is done: the merged deterministic Read layer scores facts 90/90 and issues exact 10/10 (tp7 fn0 fp0) on the tuning deals, two runs are byte-identical, validate passes, and the one-time aggregate holdout check PASSED. No Read code needed a fix. Tasks 2 and 3 (Nemotron VL) are not started.**

TASK 1 DONE. Tasks 2 and 3: VL first cut: not wired (see "Tasks not run").

## Read baseline (tuning only, D-02, D-18)

`TUNING facts 90/90 issues_exact 10/10 tp7 fn0 fp0 route 32/40 stage 8/10 flag 7/10 held 7/10 links 8/10`

Same line before and after Task 1 (nothing in prism/read changed). `history_flags: MISMATCH missed=2 extra=0 must_not_flagged=0` (a Fraud-owned column, not Read).

`bash scripts/gate.sh` exits 0: pytest 744 passed, 1 skipped (732 earlier plus the 12 new tests); run 13 deals, 173 files, 183 ticks, 0 errors; validate valid, 0 errors, 0 warnings.

## Step results

1. **Gate on the merged tree:** green on the first run, no failure to fix.
2. **tests/test_read_integration.py:** 12 tests. Synthetic: parser registered for every class except other; six generated statement months round-trip through `prism.fraud.baseline.deposit_features` (months_used equals row count), every `deposit_weekdays` label parses through `parse_weekdays`, annualized equals twice the six-month credit sum; five months give rows but no annualized figure; an EIN mismatch (application versus IRS letter) reaches `profile.mismatch_evidence` with a plain-words document label and the Move `info_request_message` carries "your application shows X ... your IRS EIN letter shows Y"; a clean synthetic deal raises no MISMATCH or OLD_TRICK. Real tuning deals only: issues equal the answer key with zero false alarms and no deal error; ID_MISMATCH, DUP_EIN and SHELL_ADDRESS appear on no tuning deal (none has a gold case); every classified non-other tuning document has a parser result; statement features are real on every tuning deal that has statements (annualized present iff six complete months); each gold MISMATCH deal has evidence for exactly its gold fields and the borrower message contains the application value and the document value; no MISSING_DOC or MISSING_PAGE is first reported before 30 sim-minutes of quiet (spy on `detect_issues`, early ticks observed); two full runs produce identical submission payloads.
3. **Checks wave 2 could not do (tuning deals):** `scripts/read_report.py`: deposit_months present on 10 of 10 deals; `deposits_annualized_cents` present on 8 of 10 (the two without have fewer than six complete months, by design: the page-gap deal and the CSV deal lacking a month); `mismatch_evidence` present on exactly 2 of 10 (the EIN-mismatch deal and the amount-mismatch deal); MISMATCH:ein and MISMATCH:amount_requested are both raised on their tuning deals now that the 03-02 parsers are merged; ID_MISMATCH, DUP_EIN, SHELL_ADDRESS silent on all 10.
4. **Determinism and validity:** `cmp` of two consecutive CLI runs: BYTE_IDENTICAL; a third run also ran in 18.6 s; `python -m prism validate` says `valid`.
5. **D-02 holdout check (aggregate only, run once):** `HOLDOUT facts 26/27 issues_exact 3/3 fp0 fn0`.

**HOLDOUT CHECK PASSED.** Aggregate: facts 26 correct of 27 (1 missed, limit 3), issues exact on 3 of 3 deals, 0 false alarms, 0 missed gold issues. Because the holdout shows fp0, none of MISMATCH, ID_MISMATCH, DUP_EIN or SHELL_ADDRESS raised a false alarm on the holdout deals (the aggregate cannot say which fact is the one miss, and by D-02 it was not investigated or tuned against). The aggregate line was read once here; `gate.sh --final` will print it again.

## Deviations from Plan

None - plan executed exactly as written for Task 1. No generic Read fix was required, so no fix is attributed to 03-01, 03-02 or 03-03.

TDD note: the tests assert behaviour that already existed, so they passed on first run; there was no RED to observe (a RED commit would have been empty of value). One `test(03-04)` commit holds them.

## Tasks not run (orchestrator decision)

- **Task 2 (VL module) and Task 3 (VL wiring, smoke, `gate.sh --final`):** not started. Reason: the plan's time-box clause makes Task 1 the stopping point unless the invocation says to continue, and the hand-off marks both as first-to-cut. Preconditions to run them are met: tuning issues exact with fp 0, tuning facts 90/90 (at least 88), holdout PASSED. The NVIDIA key and the VL env names were not touched. Expected effect on the sample if built: 0 VL fills (the parsers fill every field), so the score would not move; the value is hidden-set robustness.
- `bash scripts/gate.sh --final` (all-13 TOTAL and history lines, "FINAL self-score for Phase 3") belongs to Task 3 step 5 and was not run; the baseline line above stands as the Phase 3 deterministic baseline for the H10 freeze.

## Hand-off notes

- **Phase 4/5 (not fixed here):** OLD_TRICK issues are not consumed by `prism/fraud`, so the tuning old-trick deal carries `OLD_TRICK:STMT_TAMPER` and `REV_INFLATION` but still scores fraud MISSED (one of the flag/held misses in the tuning line, which are Fraud-owned). Whether a Read-reported old trick should set `fraud.flagged`/`held` is a Fraud/Move decision.
- **Unseen levers for the hidden set:** ID_MISMATCH, DUP_EIN, SHELL_ADDRESS have only synthetic tests and the tuning/holdout no-false-alarm evidence. Levers if one fires wrongly: `thresholds.ocr_min_disagreeing_fields`, `shell_address_patterns`, `id_disagreement_also_mismatch`, `revenue_year_offset` in `config/read_issues.yaml`.
- The suite is now about 2 minutes (the integration file adds two full sample runs, ~35 s).

## Known Stubs

None.

## Threat Flags

None. No network, key or package was touched in this task.

## Self-Check: PASSED

`tests/test_read_integration.py` exists; commit `3dff9fa` is an ancestor of HEAD; `git rev-list --count f0bb210..HEAD` is 1 before this SUMMARY; `bash scripts/gate.sh` exits 0.
