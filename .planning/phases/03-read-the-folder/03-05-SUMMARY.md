---
phase: 03-read-the-folder
plan: 05
subsystem: read
tags: [gap-closure, statements, stmt-tamper, vl, request-letter]
requirements: [READ-06, READ-07]
gap_closure: true
status: complete
---

# Phase 3 Plan 05: Gap closure Summary

Closes the 03-VERIFICATION blocker (an edited transaction row is now STMT_TAMPER) and four review findings that could cause false alarms on the hidden set. HI-02 was cut for time.

## Items

| # | Item | Status | Commit |
|---|------|--------|--------|
| 1 | VERIFICATION B-1 + HI-03: row amount vs running-balance change is a `row_amount` footing failure (STMT_TAMPER); `signs_verified` False only for ambiguous parses | fixed | ba57042 |
| 2 | CR-01: a PDF statement with no parsed rows is never row-verified, so no footing check runs against 0 rows | fixed | 62f3e3e |
| 3 | HI-04: request-letter amount needs `$`, a scale suffix or a grouped number; "36 months", "5 years", "7%" rejected; up to 5 filler words allowed | fixed | 8041f8e |
| 4 | HI-01: period dates in US numeric and month-name forms (`normalize.dates_in`); requirement check falls back to the statement parser's month | fixed | e869529 |
| 5a | HI-06: VL names must hold a real word, not be a placeholder, and appear in the sent text (images need a sibling); EIN grounded too | fixed | 610b5b6 |
| 5b | ME-01: `parse_answer` decides on the first object; nested values or a second object reject the reply | fixed | 610b5b6 |
| 5c | HI-02: classifier broadening | CUT (time box) | - |

5a and 5b share one commit because both are in `prism/read/vl.py`.

## Gate results

`bash scripts/gate.sh` exit 0 after each item; tuning line unchanged every time:
`TUNING facts 90/90 issues_exact 10/10 tp7 fn0 fp0 route 32/40 stage 8/10` (flag 7/10 held 7/10 links 8/10). Final pytest 862 passed, 1 skipped. Holdout was not reported beyond the gate's own pass/fail.

## Deviations

- Rule 3: added a `printed_amounts` option to `tests/statement_fixtures.py` to build a row-edit tamper statement.
- The old test `test_row_whose_amount_disagrees_with_the_balance_is_not_sign_verified` was replaced: the behaviour it pinned is the gap.
- Numeric VL fields (amount, revenue) are still format- and sibling-checked only, not text-grounded.

## Known remaining (not done)

HI-02 (title-phrase gating, Form 1065/1120S, Debit/Credit CSV), HI-05 (VL default mode), ME-02..ME-10, LO-*. Holdout fact 26/27 decision (D-1) is untouched.

## Self-Check: PASSED
