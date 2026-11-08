---
phase: 03-read-the-folder
plan: 03
subsystem: read
tags: [issues, missing-doc, missing-page, mismatch, old-tricks, bank-statements, quiet-rule]

requires:
  - phase: 03-read-the-folder
    provides: docmodel registry, classifier with page markers and statement periods, per-tick issue refresh (03-01); parsers for the eight other classes, history index (03-02)
provides:
  - detect_issues with MISSING_DOC, MISSING_PAGE, MISMATCH and all five OLD_TRICK codes, quiet rule inside Read (sticky, inclusive)
  - PDF and CSV bank statement parser registered for bank_statement
  - mismatch_evidence hook for the borrower messages
affects: [03-04 holdout check, Move (blocking issues), Fraud Ops (OLD_TRICK deals)]

actuals:
  tokens: 32500
  tasks: 3
  commits: 3
plan_head_before: 4c1b5ffe6f298e9b5d68644975a9a382326980aa
plan_head_after: 128e6eff231ceb078b6fea50bc62cd3b324b4472

tech-stack:
  added: []
  patterns:
    - "rule groups isolated by try/except in detect_issues; each returns plain KIND:target strings filtered by ISSUE_RE"
    - "requirement list lives in config/read_issues.yaml as a label mapping of the stages.json prose"
    - "one computation (compare.find_mismatches) feeds both the MISMATCH issues and the evidence hook"
    - "untrusted statements (incomplete or unverified rows) are skipped, never reported as tampering"

key-files:
  created:
    - config/read_issues.yaml
    - prism/read/requirements.py
    - prism/read/statements.py
    - prism/read/compare.py
    - prism/read/old_tricks.py
    - tests/statement_fixtures.py
    - tests/test_read_issues.py
    - tests/test_read_statements.py
    - tests/test_read_compare.py
    - tests/test_read_old_tricks.py
  modified:
    - prism/read/issues.py
    - tests/test_engine.py

key-decisions:
  - "Quiet rule: a MISSING_DOC or MISSING_PAGE label is reported once now - last_arrival_at >= quiet_minutes (inclusive) or when it is already in state.issues (sticky); MISMATCH and OLD_TRICK are never gated"
  - "ID disagreement interpretation (J6): it raises OLD_TRICK:ID_MISMATCH only; MISMATCH:guarantor_name/dob/address are raised in addition only when config/read_issues.yaml id_disagreement_also_mismatch is true (default false); a date of birth is never put in evidence"
  - "OCR-sourced ID needs 2 disagreeing fields (ocr_min_disagreeing_fields); names are compared space-insensitively with nickname aliases, addresses glued and abbreviation-folded"
  - "Revenue is compared only for the calendar year before the reference date, only for a plain figure, only when the formation date shows the business existed the whole year (revenue_year_offset: 1)"
  - "STMT_TAMPER uses the latest-arrived COMPLETE copy of each month; the chain check runs only between consecutive months that are both complete and sign-verified"
  - "REV_INFLATION takes the higher of application revenue and (full-year) tax gross receipts against 12/6 times the six window months' credits, strictly greater than 1.5 as an exact Fraction"

requirements-completed: [READ-05, READ-06, READ-07, READ-08]

coverage:
  - id: D1
    description: "MISSING_DOC from the config requirement list, with Form 7004 age rule, one ID per guarantor, equipment quote, P&L plus balance sheet"
    requirement: READ-05
    verification:
      - kind: unit
        ref: "tests/test_read_issues.py"
        status: pass
      - kind: integration
        ref: "bash scripts/gate.sh (tuning gold MISSING_DOC issues found, fp 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "J11 quiet rule inside Read, inclusive, sticky, visible to Move at the exact expiry tick"
    requirement: READ-05
    verification:
      - kind: integration
        ref: "tests/test_read_issues.py::test_run_sim_reports_a_missing_statement_exactly_at_quiet_expiry, test_run_sim_resolves_the_issue_when_the_statement_arrives_late"
        status: pass
    human_judgment: false
  - id: D3
    description: "MISSING_PAGE from Page X of N markers only; incomplete statements excluded from footing and chain"
    requirement: READ-06
    verification:
      - kind: unit
        ref: "tests/test_read_statements.py, tests/test_read_old_tricks.py"
        status: pass
      - kind: integration
        ref: "bash scripts/gate.sh (gold MISSING_PAGE found, no tamper on that deal)"
        status: pass
    human_judgment: false
  - id: D4
    description: "MISMATCH under J13 tolerances plus the evidence hook"
    requirement: READ-07
    verification:
      - kind: unit
        ref: "tests/test_read_compare.py"
        status: pass
      - kind: integration
        ref: "bash scripts/gate.sh (gold MISMATCH:ein and MISMATCH:amount_requested found)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Five OLD_TRICK checks per rules/known_fraud_checks.md"
    requirement: READ-08
    verification:
      - kind: unit
        ref: "tests/test_read_old_tricks.py"
        status: pass
      - kind: integration
        ref: "bash scripts/gate.sh (gold STMT_TAMPER and REV_INFLATION found, fp 0)"
        status: pass
    human_judgment: true
    rationale: "ID_MISMATCH, DUP_EIN and SHELL_ADDRESS have no tuning gold case, only synthetic tests and a no-false-alarm check on the 10 clean-or-other tuning deals; the hidden set will exercise them for the first time"
---

# Phase 3 Plan 03: Issues, Statements and Old Tricks Summary

**detect_issues now returns exactly the golden issue set on the 10 tuning deals (issues exact 10/10, tp 7, fn 0, fp 0): MISSING_DOC with the quiet rule inside Read, MISSING_PAGE from page markers, MISMATCH under the J13 tolerances, and all five OLD_TRICK checks on a new PDF/CSV statement parser.**

## Performance

- **Tasks:** 3, one commit each (see TDD note below)
- **Files:** 12 changed (10 created, 2 modified), 2808 insertions
- **Verification:** `bash scripts/gate.sh` exits 0: 732 passed 1 skipped, run valid, validate valid

## Tuning summary line, before and after (D-02, D-18; no holdout number printed or reported)

| | facts | issues_exact | tp | fn | fp | route | stage | flag | held | links |
|---|---|---|---|---|---|---|---|---|---|---|
| BEFORE (start of this plan) | 90/90 | 5/10 | 0 | 7 | 0 | 15/40 | 3/10 | 7/10 | 7/10 | 8/10 |
| after Task 1 | 90/90 | 6/10 | 2 | 5 | 0 | 21/40 | 4/10 | 7/10 | 7/10 | 8/10 |
| after Task 2 | 90/90 | 8/10 | 5 | 2 | 0 | 29/40 | 6/10 | 7/10 | 7/10 | 8/10 |
| AFTER (final) | 90/90 | 10/10 | 7 | 0 | 0 | 32/40 | 8/10 | 7/10 | 7/10 | 8/10 |

Facts and issues (Read-owned) did not drop: facts 90/90, issues fn 7 to 0, fp stays 0. Route and stage recover and pass their pre-facts levels (28/40 and 5/10 mentioned in the hand-off) now that issues are real. Remaining route misses (two equipment deals, 0/4 each) and the flag, held and links misses are Fraud-owned (Phase 5). Note for the orchestrator: the old-trick tuning deal now carries its OLD_TRICK issues but still scores fraud MISSED, because nothing in `prism/fraud` reads `state.issues` for `OLD_TRICK:*` (only Move's config and message code do). Whether a Read-reported old trick should set `fraud.flagged`/`held` is a Fraud/Move decision, not made here.

## What was built

- **config/read_issues.yaml**: the requirement list (label mapping of the stages.json prose), windows, thresholds, statement labels and CSV words, page-gap classes, shell patterns, document labels, the ID flag.
- **requirements.py**: config loader (cached by mtime, `PRISM_READ_ISSUES_CONFIG`), `reference_date` (application date, signature date, last arrival date), `statement_window`, `business_age_ok_for_7004`, `formation_date` (application, else certificate), `required_labels`.
- **statements.py**: PDF parser (summary values by label; rows are date-first lines ending in amount and running balance; sign from the balance change cross-checked against the printed amount; pdfplumber table fallback) and CSV parser (banner sniff, header columns, newest-first rows reversed, implied opening). Helpers `missing_pages`, `marker_gap`, `is_complete`, `trusted`, `footing_errors`, `implied_opening`, `closing`, `missing_page_labels`.
- **old_tricks.py**: `stmt_tamper`, `rev_inflation`, `id_mismatch`, `dup_ein` (own stdlib csv loader), `shell_address`; reason helpers return codes and month labels only.
- **compare.py**: `find_mismatches`, `id_disagreements`, `raising_id_results`, `Mismatch` evidence record.
- **issues.py**: `detect_issues` (nine isolated rule groups, ISSUE_RE filter, quiet gate) and `mismatch_evidence`. The module docstring is unchanged.
- **tests**: 4 new test files plus `tests/statement_fixtures.py`; one approved assertion change in `tests/test_engine.py` (D-12).

## Checks required by the plan

**Application-date check (Task 1 step 6, tuning applications only):** 0 of 10 tuning applications show an explicit application-date label; all 10 show a signature date. So the signature date equals the explicit date in 0 cases (no pair exists) and `reference_date` used the **signature date** on all 10; no disagreement of any kind. Signature dates fall one or two days before the last arrival, so every window is 2026-05 to 2026-10. The code prefers an explicit application date whenever one parses.

**Statement parse (Task 2 step 5, tuning deals only):** 59 statements across 10 deals (54 PDF including the one partial-page copy, 5 CSV). **Unverified-statement count: 0 of 59** (every row of every statement verified). Footing was clean on every statement except the gold tamper deal's one month (printed closing does not equal opening plus credits minus debits).

**Chain (opening equals prior closing), run in chronological order on EVERY tuning deal:** 46 consecutive-month pairs checked (5 on each of eight deals, 3 on the deal with a page gap, 3 on the CSV deal that lacks June). **1 break**, on the gold tamper deal (its August closing against September opening). No false chain break on any other deal (assumption A3 from research held on all ten, not only the seven PDF folders it was checked on).

**Gold cases:** the page-gap deal gives MISSING_PAGE for its August statement and no tamper and no REV_INFLATION (an incomplete month blocks both); the CSV deal gives MISSING_DOC for its June statement and no tamper and no REV_INFLATION; the tamper deal gives STMT_TAMPER and REV_INFLATION (ratio 3.06); clean deals' stated revenue to annualized deposits ratio is between 0.87 and 1.01.

**Partial-year revenue (P8):** two tuning deals formed mid-2025 state revenue about twice their 2025 tax return; the full-year rule (formation before January 1 of the tax year) keeps both silent, as the gold expects.

**Tuning deals whose issues awaited a 03-02 parser:** none now. 03-02 was already in this tree (sequential run), so the EIN mismatch deal and the amount mismatch deal were confirmed on real data here: MISMATCH:ein and MISMATCH:amount_requested are both found, fp 0. 03-04 Task 1 still re-checks them after the holdout run.

**Features unblocked by statements (spot check, tuning deals):** `statement_months` present on 10 of 10, `deposit_months` rows 10 of 10, `deposits_annualized_cents` 8 of 10 (the page-gap deal and the CSV deal lack six complete months, by design), `mismatch_evidence` on exactly the 2 deals with a gold MISMATCH.

## ID-disagreement interpretation chosen (J6)

An ID that disagrees with the application raises `OLD_TRICK:ID_MISMATCH` and nothing else. The flag `id_disagreement_also_mismatch` in `config/read_issues.yaml` (default `false`) additionally raises `MISMATCH:guarantor_name`, `guarantor_dob` and `guarantor_address` for the same disagreements; flipping it is one line and is covered by a test. Per J6 and T-03-13 the evidence for a date of birth is a fixed phrase, never the date.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] New shared test helper file**
- **Found during:** Task 1 (the run_sim tests need generated statements before the statement tests exist)
- **Fix:** created `tests/statement_fixtures.py` (PDF and CSV statement builders), a new file owned by this plan and not in `files_modified`. It is under the guard test's glob only if named `test_read*`, so it carries no sample literals by construction (all text invented).
- **Committed in:** fd3567e

**2. [Rule 1 - Bug, test fixture] The shared 03-02 ID fixture disagrees with the shared application fixture**
- **Found during:** Task 3 gate run (two run_sim tests started returning OLD_TRICK:ID_MISMATCH)
- **Issue:** `tests/test_read_forms.ID_ROWS` shows house number 10 while `application_lines` shows 20 for the guarantor home address. The new ID check correctly reports that disagreement.
- **Fix:** my run_sim test builds its own ID rows with the matching address; the 03-02 fixture files are untouched.
- **Committed in:** 128e6ef

**Total deviations:** 2 (both test-side), no scope change.

### TDD note

The plan marks all tasks `tdd="true"` but the plan type is `execute` and asks for one commit per task. Tests were written before implementation in each task and were run to confirm failure, but the failure was a missing-module collection error (new modules), which the TDD reference classes as INVALID_RED, and `gsd_run check tdd-red-evidence` was not run (not required for a non-`tdd` plan). There are no separate `test(...)` commits; each task commit contains tests and implementation together.

## Tasks that were not built

None cut. SHELL_ADDRESS, DUP_EIN, ID_MISMATCH and the evidence hook were all built.

## Hand-off notes

- **03-04 Task 1:** re-check on the holdout run, once, that no false alarm appears from ID_MISMATCH, DUP_EIN, SHELL_ADDRESS and MISMATCH (the three have no tuning gold, so the holdout is their first real test beyond no-false-alarm). Config levers if one fires wrongly: `thresholds.ocr_min_disagreeing_fields`, `shell_address_patterns`, `id_disagreement_also_mismatch`, `revenue_year_offset`.
- **Known limitation, cautious by design:** a PDF row whose printed amount disagrees with the balance change marks the statement unverified, so STMT_TAMPER is not raised for it (the plan's "unverified never raises"). A tamper that edits only a row amount without the totals would be missed; one that breaks the printed totals, the closing balance or the month chain is caught. If the hidden set tampers that way, the lever is `statements._find_rows` (treat a magnitude mismatch as a footing error rather than unverified).
- **CSV statements** carry no printed totals: they are checked only by the running-balance rule and the month chain (opening is implied by the first row).
- **Bank-balance mismatch** needs a statement whose printed period end equals the balance-sheet date; CSV exports end on their last posted day, so they usually skip it.
- **03-01 / 03-02 files:** no bug found in any of their files. One fixture inconsistency noted above (ID vs application house number in tests only).
- **Quiet-rule dependency on run.py:** correctness relies on 03-01's extra tick exactly at last arrival plus `quiet_minutes`; `test_run_sim_reports_a_missing_statement_exactly_at_quiet_expiry` pins it.

## Known Stubs

None. `mismatch_evidence` is no longer a stub.

## Threat Flags

None. Mitigations applied: bounded line parser with a row cap and a line-length cap (T-03-10); every rule group isolated, unreadable or unparsed documents skipped, OCR ID needs two fields, tamper only on complete verified statements, zero tuning false alarms (T-03-11); log lines carry rule names only (T-03-12); no SSN, date of birth or licence number in evidence (T-03-13). No packages installed.

## Self-Check: PASSED

All created files exist; commits `fd3567e`, `f5ee1ca`, `128e6ef` are ancestors of HEAD; `git rev-list --count 4c1b5ff..HEAD` is 3; `bash scripts/gate.sh` exits 0.

---
*Phase: 03-read-the-folder*
*Completed: 2026-11-08*
