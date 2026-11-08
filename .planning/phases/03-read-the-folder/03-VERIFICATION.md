---
phase: 03-read-the-folder
verified: 2026-11-08T07:47:20Z
status: gaps_found
score: 22/24 truths verified (1 FAILED blocker, 1 UNCERTAIN warning)
behavior_unverified: 0
overrides_applied: 0
covered_files: [".gitattributes", ".planning/phases/03-read-the-folder/03-01-PLAN.md", ".planning/phases/03-read-the-folder/03-01-SUMMARY.md", ".planning/phases/03-read-the-folder/03-02-PLAN.md", ".planning/phases/03-read-the-folder/03-02-SUMMARY.md", ".planning/phases/03-read-the-folder/03-03-PLAN.md", ".planning/phases/03-read-the-folder/03-03-SUMMARY.md", ".planning/phases/03-read-the-folder/03-04-PLAN.md", ".planning/phases/03-read-the-folder/03-04-SUMMARY.md", "config/read.yaml", "config/read_issues.yaml", "eval/holdout.json", "prism/engine/run.py", "prism/read/classify.py", "prism/read/compare.py", "prism/read/docmodel.py", "prism/read/entities.py", "prism/read/extract.py", "prism/read/features.py", "prism/read/history.py", "prism/read/issues.py", "prism/read/labels.py", "prism/read/normalize.py", "prism/read/ocr.py", "prism/read/old_tricks.py", "prism/read/parse_application.py", "prism/read/parse_forms.py", "prism/read/requirements.py", "prism/read/settings.py", "prism/read/statements.py", "prism/read/text.py", "prism/read/vl.py", "pyproject.toml", "scripts/gate.sh", "scripts/read_report.py", "scripts/score_split.py", "scripts/vl_smoke.py", "tests/conftest.py", "tests/pdfgen.py", "tests/read_fixtures.py", "tests/real_data.py", "tests/statement_fixtures.py", "tests/test_engine.py", "tests/test_read_application.py", "tests/test_read_classify.py", "tests/test_read_classify_refine.py", "tests/test_read_compare.py", "tests/test_read_engine.py", "tests/test_read_entities.py", "tests/test_read_extract.py", "tests/test_read_features.py", "tests/test_read_forms.py", "tests/test_read_guards.py", "tests/test_read_integration.py", "tests/test_read_issues.py", "tests/test_read_labels.py", "tests/test_read_normalize.py", "tests/test_read_old_tricks.py", "tests/test_read_score_split.py", "tests/test_read_statements.py", "tests/test_read_text.py", "tests/test_read_tracer.py", "tests/test_read_vl.py"]
covered_digest: "v4:sha256:b642495017c6162273b444443b1644185dd6adba08eec5098d0cdfb73a621bd4"
gaps:
  - truth: "STMT_TAMPER runs the footing check (listed transactions add up to the summary totals, to the cent) and the month-chain check on complete statements, as rules/known_fraud_checks.md requires"
    status: failed
    reason: "A statement in which any transaction's printed amount disagrees with its running-balance change is marked untrusted (signs_verified False). Footing and chain are then skipped and no OLD_TRICK:STMT_TAMPER is raised. Reproduced on a synthetic statement: one debit amount edited with the balance column untouched gives no tamper; the same statement with an edited printed total is caught."
    artifacts:
      - path: "prism/read/statements.py"
        issue: "_find_rows sets ok = False when abs(delta) != amount (about line 159); signs_verified then gates trusted() and footing_errors()"
      - path: "prism/read/old_tricks.py"
        issue: "stmt_tamper_reasons only examines trusted statements, so an untrusted statement silently yields no reason"
    missing:
      - "Report a row-level amount disagreement as a footing failure (STMT_TAMPER) rather than treating the whole statement as unverified; keep 'unverified' only for genuinely ambiguous sign or parse cases"
      - "Add a test in tests/test_read_old_tricks.py that edits one transaction amount with the balance column untouched and expects OLD_TRICK:STMT_TAMPER; add a control that an unedited statement raises nothing"
      - "Re-run bash scripts/gate.sh --final: tuning issues must stay 10/10 with fp 0, because a looser footing rule can create false alarms on messy real statements"
---

# Phase 3: Read the Folder - Verification Report

**Phase Goal:** Every arriving document is identified by what it says, not what it is called. Its facts are extracted with source and confidence, and the engine reports exactly the missing, mismatched and tampered items, with no false alarms on messy-but-real borrowers.
**Verified:** 2026-11-08T07:47:20Z
**Status:** gaps_found
**Re-verification:** No (initial verification; no prior VERIFICATION.md)

## Summary

The Read layer is substantially built and wired. The full suite passes (823 passed, 1 skipped), the phase gate exits 0, the tuning deals score 90/90 facts and 10/10 issues exact with zero false alarms, and the downstream consumers (Move's profile keys, Fraud's deposit features and entities) are fed. Independent probes confirmed the classifier, the real OCR read of the tuning ID photo, and the entity and profile output on the tuning deals.

Two findings keep the phase from passing:

1. **BLOCKER.** STMT_TAMPER silently skips any statement in which a single transaction amount disagrees with its running-balance change. The rule requires the listed transactions to add up to the summary totals, so an edited transaction is a tamper that the check never reports. Reproduced (see P15).
2. **WARNING, decision needed.** One of 27 holdout facts does not match the golden labels (aggregate 26/27). Roadmap success criterion 2 says all facts match. The plan's holdout threshold allowed up to three misses. The cause cannot be attributed without reading holdout gold, which the holdout protocol (D-02) reserves to the orchestrator.

## Goal Achievement

### Roadmap Success Criteria

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| RS1 | Every sample file gets a content-based class without a crash; Form 7004 is an extension, not a second application; unrecognized becomes `other` | VERIFIED | Tuning deal probe: the 7004 file classes as `form_7004` (score 5.5, runner-up 0), the IRS letter as `ein_letter`, the request letter as `request_letter`, the photo as `guarantor_id`, the five CSV exports as `bank_statement` with periods 2026-05 to 2026-10 read from content. `classify` never raises (test_never_raises_on_bad_files); `other` below min score (test_below_min_score_is_other_with_meta). Scanned-sample classes are evidenced only through the holdout aggregate (see decision D-1). |
| RS2a | The 10 submission facts per deal match golden labels, each with source and confidence; `needed_by` ISO or null | UNCERTAIN (WARNING) | Tuning: 90/90 facts (gate). Holdout: 26/27 (gate aggregate). One holdout fact unmatched and unexplained (03-04 SUMMARY: "not investigated"). Roadmap says "10 facts"; REQUIREMENTS READ-02 and the gate score 9 per deal (see Info). |
| RS2b | Graph attributes extracted for every deal; Tyler's ID read by OCR or marked present-but-unverified | VERIFIED | Entity probe over all 10 tuning deals: the union covers preparer, phone, registered_agent, address, bank, guarantor, pdf_producer on every deal (phone absent on one deal), plus vendor and remit_account on the four deals with an equipment quote; deposit_months has 5 to 6 rows per deal. OCR probe on the tuning photo: readable=True, via_ocr=True, name/DOB/DL parsed, class guarantor_id, unverified=False. |
| RS3 | Engine issues match golden expectations (Westfield MISMATCH:ein, Bluebonnet, LSFD, Oakline MISSING_PAGE not STMT_TAMPER, Tyler bank_statement_2026-06, Granite Bay STMT_TAMPER and REV_INFLATION) | VERIFIED | Gate: tuning issues_exact 10/10, tp 7, fn 0, fp 0; holdout issues_exact 3/3, fp 0, fn 0 (aggregate). Integration test test_tuning_issues_equal_the_answer_key_with_zero_false_alarms passes. |
| RS4 | Clean trap deals get zero issues; no MISSING_DOC while a folder is still landing (30 sim-minutes quiet first) | VERIFIED | Gate: fp 0 on tuning and holdout. Tests: test_quiet_boundary_is_inclusive, test_reported_issue_is_sticky_through_later_arrivals, test_run_sim_reports_a_missing_statement_exactly_at_quiet_expiry, test_missing_doc_never_appears_before_the_folder_has_been_quiet_30_minutes. `quiet_minutes: 30` in config/read.yaml. |

### Plan Must-Have Truths

| # | Truth (condensed) | Status | Evidence |
|---|-------------------|--------|----------|
| P1 | 03-01: synthetic application PDF through run_sim gives the 9 facts with source_doc and confidence; submission validates | VERIFIED | test_read_tracer, test_read_application (test_all_nine_facts); gate validate valid, errors 0. |
| P2 | 03-01: classify never raises, returns the same Doc, never reads Doc.name, records class_score and class_runner_up | VERIFIED | classify.py: no Doc.name read (grep); whole body in try/except; meta records score and runner-up. Tests test_file_name_is_never_consulted, test_returns_same_doc_and_records_score. |
| P3 | 03-01/02: form_7004 and request_letter added; a 7004 is never application or tax_return; unreadable image is guarantor_id with unverified=True | VERIFIED | DOC_CLASSES contains both (classify.py); Tyler probe classes the 7004 as form_7004; test_image_unreadable_is_unverified_guarantor_id. |
| P4 | 03-01: run_sim refreshes issues every tick for every deal with docs; resolved_issues kept; features merged, not replaced; quiet-expiry ticks added | VERIFIED | run.py: `_refresh_issues` per live deal per tick (a2), `_quiet_expiry_ticks`, `state.features.update(features)`. test_read_engine; test_engine tick count change is the approved D-16 change. |
| P5 | 03-01: no sample literal in prism/read, config/read*.yaml, tests/test_read*.py or tests/pdfgen.py | VERIFIED | test_no_sample_literals_in_read_code_config_or_tests passes in the 823-test suite. |
| P6 | 03-01/04: scripts/score_split.py and gate.sh are holdout-safe; holdout aggregate only with --final | VERIFIED | score_split.py has no option printing holdout rows or names (argparse read); gate output printed tuning rows and one aggregate holdout line. |
| P7 | 03-02: 8 non-application parsers registered; ISO dates; integer cents; unusable OCR gives ParsedId.readable False | VERIFIED | PARSER_MODULES includes parse_forms; parse_forms.py registers the parsers; test_every_class_except_other_has_a_registered_parser passes; readable False tests in test_read_forms. |
| P8 | 03-02: D-15 EIN rule (IRS letter wins, application fallback); application amount and guarantor kept (J15, J6) | VERIFIED | extract.py; gate 90/90 tuning facts; test_read_extract. |
| P9 | 03-02 (READ-03): entities use canon_value; hygiene; remit last four only; no DOB, DL or SSN entities; agree with history | VERIFIED | entities.py calls canon_value (line 56); probe shows the kinds above; test_emitted_values_agree_with_history_canonical_forms passes. |
| P10 | 03-02 (READ-03): profile carries every key Move reads, money in integer cents, fraud_watch never set; deposit_months in history units | VERIFIED | Key diff: all 14 keys Move reads (application_date, cash_cents, dba, deposits_annualized_cents, formation_date, net_income_fy_cents, net_income_ytd_cents, quote, relationship, statement_months, tax_doc, vendor_past_loans, vendor_verified, ytd_months) are written by features.build_profile; fraud_watch appears only in comments; fraud/signals.py consumes deposit_months. |
| P11 | 03-03 (READ-05): MISSING_DOC from config requirement list; 7004 only for businesses under 2 years; six full months before the application month; anchor on last arrival when no date | VERIFIED | requirements.py `required_labels` and `business_age_ok_for_7004`; config/read_issues.yaml; tests test_7004_satisfies_a_business_under_two_years, test_window_anchors_on_last_arrival_when_no_application_date. |
| P12 | 03-03 (READ-05): quiet rule inside Read, inclusive, sticky, late arrival resolves; tested through run_sim | VERIFIED | issues.py `detect_issues` (`>=` quiet, `previous` sticky); tests test_quiet_boundary_is_inclusive, test_reported_issue_is_sticky_through_later_arrivals, test_late_arrival_resolves_the_issue, test_run_sim_resolves_the_issue_when_the_statement_arrives_late. The end-of-run grace tick coincides with the quiet-expiry tick at the default grace (30 min). |
| P13 | 03-03 (READ-06): MISSING_PAGE from "Page X of N" markers only; a gap month is excluded from footing and chain | VERIFIED | statements.py: `pages_total` comes from `_page_numbers(markers)`, not the PDF page count; `missing_pages`, `marker_gap`; tests test_a_statement_with_a_missing_page_is_excluded_from_footing_and_chain, test_a_complete_second_copy_clears_the_page_gap. |
| P14 | 03-03 (READ-07): MISMATCH under J13 tolerances (EIN exact, names and nicknames, addresses, cents, $1 bank balance, 1% revenue same year only); evidence hook for the borrower message | VERIFIED | compare.py `find_mismatches`, `_RULES`; `mismatch_evidence` in issues.py; test_read_compare (named tests in the file); gold MISMATCH:ein and MISMATCH:amount_requested found with fp 0 (gate). |
| P15 | 03-03 (READ-08): the five OLD_TRICK checks run exactly as rules/known_fraud_checks.md states; STMT_TAMPER footing and chain apply to every complete statement | FAILED (BLOCKER) | See finding B-1 below. The other four checks (REV_INFLATION, ID_MISMATCH, DUP_EIN, SHELL_ADDRESS) are VERIFIED by code and named tests (1.5x strictly greater; name, DOB and address rules with OCR needing two fields; history EIN under another base name; PMB and mailbox patterns, never suite markers). |
| P16 | 03-03: tests/test_engine.py changed only in the approved D-12 assertion and the n_ticks count | VERIFIED | `git diff 6a86e58 HEAD -- tests/test_engine.py` shows exactly two hunks: n_ticks 5 to 6 with comment, and the zero-byte issues assertion with comment. No other assertion or signature changed. |
| P17 | 03-04: VL fills only parser-null fields, format-checked and sibling-agreed, tagged, never an issue, mismatch, hold or fraud signal; no VL classification | VERIFIED | VL consumers are only extract.py (fill_nulls, fills_for) and run.py (reset); no import from issues, compare, old_tricks or fraud. Fills tagged in features["vl_fills"]. |
| P18 | 03-04: modes off/replay/live from NEMOTRON_MODE; 30-call budget; no key means off; model IDs from env only; key never printed or cached; off/replay/live give identical sample output | VERIFIED | config/read.yaml `vl.max_calls: 30`; vl.py reads NEMOTRON_VL_MODEL and NEMOTRON_VL_FALLBACK_MODEL from env; the key is used only in the Authorization header (vl.py line ~187); test_read_vl and the wiring tests in test_read_integration pass. Sample VL fill count 0 (03-04 SUMMARY). |
| P19 | 03-01/02 (READ-04): real RapidOCR reads the tuning ID photo; unreadable is present-but-unverified, never a mismatch | VERIFIED | Live probe: ocr.available True; read_image_text returned 10 lines; ParsedId readable True, via_ocr True, name/DOB/DL present; class guarantor_id, unverified False. Failure path test_id_image_with_no_ocr_text_is_unreadable passes. |

Score: 22 verified of 24 rows. Rows not verified: RS2a (UNCERTAIN, WARNING) and P15 (FAILED, BLOCKER).

### Deferred Items

None. The STMT_TAMPER gap is not addressed by Phase 4 or 5 (their OLD_TRICK work is about Fraud consuming `OLD_TRICK:*`, not about the statement check).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| prism/read/text.py | shared text layer, OCR fallback | VERIFIED | Exists, substantive (272 lines), wired via classify and statements. |
| prism/read/docmodel.py | Parsed* types and registry | VERIFIED | Exists (248 lines); PARSER_MODULES lazy-registers three modules. |
| prism/read/classify.py | content classifier, 11 classes | VERIFIED | Exists (181 lines); called from run.py `_ingest`. |
| prism/read/parse_application.py, parse_forms.py, statements.py | parsers | VERIFIED | Exist; registered and exercised by the gate. |
| prism/read/extract.py | facts, entities, features | VERIFIED | Exists (157 lines); called from run.py `_ingest`; calls vl.fill_nulls inside try. |
| prism/read/entities.py, features.py, history.py | graph entities, profile, history index | VERIFIED | Exist; probe confirms output. |
| prism/read/issues.py, requirements.py, compare.py, old_tricks.py | issues | VERIFIED (old_tricks: see P15) | Exist; called from run.py `_refresh_issues`. |
| prism/read/vl.py | Nemotron VL null-fill | VERIFIED | Exists (532 lines); wired behind modes; 0 fills on sample. |
| prism/read/ocr.py | lazy RapidOCR | VERIFIED | Exists; live probe succeeded. |
| config/read.yaml, config/read_issues.yaml | rules config | VERIFIED | Exist; no sample literals (guard test). |
| scripts/gate.sh, scripts/score_split.py | holdout-safe gate | VERIFIED | Exist; gate ran exit 0. |
| pyproject.toml | pdfplumber, rapidocr-onnxruntime, onnxruntime as core deps | VERIFIED | Lines 14-17 list all three (D-13). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| prism/engine/run.py | prism/read/issues.py detect_issues | module-attribute call each tick | WIRED | run.py line 95 in `_refresh_issues`, called in tick loop (a2) for every deal with docs. The plan's own key-link tool failed on the parenthetical in the `from:` field, not on the code. |
| prism/engine/run.py | prism/read/extract.py extract_features | module-attribute call in `_ingest` | WIRED | run.py lines 88-90 merge with `update`. |
| prism/read/docmodel.py (PARSER_MODULES) | prism/read/parse_forms.py | lazy import | WIRED | PARSER_MODULES line 24 lists parse_forms; registration verified by test. Tool failure is the same formatting issue as above. |
| prism/read/issues.py | prism/read/docmodel.py parsed_all | typed parsed objects | WIRED (transitive) | issues.py does not name `parsed_all`; it reaches it through compare, old_tricks and requirements, which all call docmodel.parsed_all. The plan's literal key-link pattern is absent, but the data path is live. |
| prism/read/entities.py | prism/fraud/canon.py | canon_value | WIRED | entities.py line 16 imports canon_value, line 56 calls it. |
| prism/read/extract.py | prism/read/vl.py | fill_nulls inside try | WIRED | extract.py lines 119 and 152. |
| prism/read/features.py profile | prism/move (credit_memo, messages) | state.features["profile"] | WIRED | All 14 Move-read keys are written by Read (see P10). |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Produces Real Data | Status |
|----------|------|--------|--------------------|--------|
| Facts (9) | legal_name, EIN, amount, ... | parsed application and IRS letter text | Yes (tuning 90/90) | FLOWING |
| Issues | MISSING_DOC, MISMATCH, OLD_TRICK | parsed docs and history | Yes (tuning 10/10 exact) | FLOWING (STMT_TAMPER row-edit path: see P15) |
| Entities | preparer, vendor, remit_account, ... | parsed docs canonicalized | Yes (probe) | FLOWING |
| features.profile | cash, net income, relationship | parsed financials, history | Yes (probe, 15 to 18 keys per tuning deal) | FLOWING |

### Requirements Coverage

| Requirement | Source Plan(s) | Description (short) | Status | Evidence |
|-------------|----------------|---------------------|--------|----------|
| READ-01 | 03-01, 03-02 | Classify by content, never filename, never crash | SATISFIED | P2, P3, RS1 |
| READ-02 | 03-01, 03-02, 03-04 | Nine facts with source and confidence | SATISFIED (tuning); holdout caveat | RS2a (WARNING) |
| READ-03 | 03-02 | Graph attributes extracted | SATISFIED | P9, P10, RS2b |
| READ-04 | 03-01, 03-02, 03-04 | Tyler's ID by OCR; unreadable is unverified | SATISFIED | P19, P3 |
| READ-05 | 03-03 | MISSING_DOC rules and 30-minute quiet | SATISFIED | P11, P12, RS4 |
| READ-06 | 03-03 | MISSING_PAGE from markers only | SATISFIED | P13 |
| READ-07 | 03-03 | MISMATCH with J13 tolerances, no false alarms | SATISFIED | P14, RS3 |
| READ-08 | 03-03 | Five OLD_TRICK checks run exactly as rules state | BLOCKED (partial) | P15: STMT_TAMPER skips edited-transaction statements |

Requirement accounting: the PLAN frontmatter requirement lists (03-01: READ-01, READ-02, READ-04; 03-02: READ-01 to READ-04; 03-03: READ-05 to READ-08; 03-04: READ-02, READ-04) cover all eight Phase 3 requirements. REQUIREMENTS.md traceability maps READ-01 to READ-08 to Phase 3 and has no orphans.

Note: REQUIREMENTS.md still marks READ-08 `[x]` Complete. That is contradicted by P15. Revert the checkbox to pending until the STMT_TAMPER fix lands.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| prism/read/statements.py | ~159 | Ambiguity handling treats a row-level amount mismatch as a reason to discard the whole statement | BLOCKER | Silent false negative on STMT_TAMPER (P15) |
| tests/test_read_old_tricks.py | 101 | The "edited amount" test edits printed totals, not a transaction row | WARNING | The row-level tamper case has no test, so the gap is invisible to the suite |
| prism/read/vl.py | config default | Mode is live whenever NVIDIA_API_KEY is set | WARNING (decision D-2) | A hidden-set run with a key would send application text to the hosted API and could fill null facts |

Debt-marker gate (TBD, FIXME, XXX in phase-modified files): no hits in code or config. The only matches are test-data strings (for example "TBD" as an input to the needed-by parser test, and masked SSN fixtures). No debt-marker blocker.

No stubs found: extract_entities, extract_features, detect_issues and mismatch_evidence all have bodies. The 03-01 SUMMARY's "known stubs" are all filled by 03-02 and 03-03.

### Behavioral Spot-Checks

| Behavior | Command or method | Result | Status |
|----------|-------------------|--------|--------|
| Full phase gate, final flag | bash scripts/gate.sh --final | pytest 823 passed, 1 skipped; run 13 deals, 0 errors; validate valid; score exit 0 | PASS |
| Tuning score | scripts/score_split.py (gate output) | facts 90/90; issues_exact 10/10; fp 0 | PASS |
| Holdout aggregate | gate output (aggregate line only) | facts 26/27; issues_exact 3/3; fp 0 | PASS on issues; facts see D-1 |
| Real OCR on tuning ID photo | ocr_probe (scratch) | readable True, via_ocr True, class guarantor_id | PASS |
| Content classes on a tuning deal | tyler_classify_probe (scratch) | all 12 files classed as expected | PASS |
| Entities and profile per tuning deal | entity_probe (scratch), one run_sim | 9 entity kinds across tuning deals; 14 of 14 Move keys | PASS |
| Edited transaction amount, balance untouched | row_edit_probe (scratch), synthetic statement | stmt_tamper_reasons = [] (signs_verified False) | FAIL |
| Edited printed totals | row_edit_probe (scratch), synthetic statement | ['2026-05:debits_sum', '2026-05:summary_closing'] | PASS (control) |
| Unedited statement | row_edit_probe (scratch) | [] | PASS (control) |

Probe scripts are in the orchestrator's scratch directory (`.../scratchpad/verify03/`). They print booleans, counts and kind names only, and never print holdout deal data.

### Probe Execution

No probe-*.sh files are declared or present under scripts/*/tests/. Step 7c not applicable.

### Human Verification Required

None needed for the status. The items below are decisions for the orchestrator, not tests for the user.

## Decisions Requested

**D-1 (WARNING, UNCERTAIN): holdout fact miss against roadmap success criterion 2.**
- Observed: holdout facts 26/27 (aggregate). Tuning 90/90.
- Roadmap SC2 says every fact of every deal matches the golden labels. The plan's holdout threshold (03-04: up to 3 missed) allowed this.
- The verifier cannot tell whether the miss is a parser defect or a golden-label issue, because D-02 keeps holdout gold out of verifier reads.
- Choose: (a) accept 116/117 and record an override in this file with accepted_by and accepted_at, or (b) investigate under the holdout protocol and fix the parser.
- The same decision covers the scanned-sample classes, which are evidenced only through the holdout aggregate.

**D-2 (WARNING, decision): Nemotron VL default mode.**
- With NVIDIA_API_KEY set and NEMOTRON_MODE unset, VL runs live. A hidden-set run would send application text to the hosted API and could fill null facts, which changes scored output.
- This is not a Phase 3 must-have failure (P17 and P18 hold as written). It does bear on the H10 byte-identical promise. Pick the hidden-set mode explicitly (off or replay).

**D-3 (decision): first real exposure of three OLD_TRICK checks.**
- ID_MISMATCH, DUP_EIN and SHELL_ADDRESS have no tuning gold case. The no-false-alarm evidence is synthetic plus the tuning and holdout runs, which raise nothing for them. The hidden set will be their first real test. Levers are listed in the 03-03 and 03-04 SUMMARY hand-off notes.

## Gaps Summary

**B-1 (BLOCKER): STMT_TAMPER skips statements with an edited transaction amount.**

What the rule says: "Each month's opening balance must equal the prior month's closing balance; listed transactions must add up to the summary totals." Stated in rules/known_fraud_checks.md.

What the code does:
- `statements._find_rows` checks each row's printed amount against its running-balance change. On disagreement (`abs(delta) != amount`) it sets `ok = False`.
- That makes `signs_verified` False, so `trusted()` is False for the whole statement.
- `footing_errors` and the chain check both require `trusted`, so neither runs. `old_tricks.stmt_tamper_reasons` returns nothing.

Reproduction (synthetic statement from the test fixtures, one debit amount edited from 1,200.00 to 1,250.00 with the balance column untouched): `stmt_tamper_reasons` returns []. The unedited control returns []. Editing a printed total is caught.

Why it matters: an edited transaction is the most natural tamper. Under the rule, the listed transactions no longer add to the printed totals, and the check reports nothing. The 03-03 SUMMARY discloses this as a "known limitation, cautious by design", but READ-08 says the checks run exactly as the rules state. The tuning gold has no such tamper, so the gate passes.

Fix direction: report row-level disagreement as a footing failure, keep "unverified" for real parse ambiguity, add a test for an edited row, and re-run the gate with `--final` to confirm tuning stays 10/10 with zero false alarms.

**Info (not gaps):**
- Roadmap SC2 says "10 submission facts"; REQUIREMENTS READ-02 and the scorer use 9 application facts per deal. The roadmap wording looks stale.
- 03-01's must-have cites research S1 with 5 equipment quotes. The tuning deals contain 4 (the classifier's count; four tuning deals produce vendor entities, which corroborates it). The test asserts 4 with a comment. This is an accepted correction.
- Move-owned and Fraud-owned score columns (route 32/40, stage 8/10, flag 7/10, held 7/10, links 8/10 on tuning) are outside Phase 3. Two tuning deals show route 0/4 and "Closed/Intake" with fraud MISSED. That belongs to Phase 4 and Phase 5.
- OLD_TRICK issues are still not consumed by prism/fraud, as the orchestrator noted (Phase 4 and 5).

---

_Verified: 2026-11-08T07:47:20Z_
_Verifier: Claude (gsd-verifier)_
