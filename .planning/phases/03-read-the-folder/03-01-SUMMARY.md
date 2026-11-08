---
phase: 03-read-the-folder
plan: 01
subsystem: read
tags: [pypdf, pdfplumber, rapidocr, label-extraction, classifier, run_sim, holdout]

requires:
  - phase: 02-engine-skeleton
    provides: pinned DealState/Doc signatures, run_sim loop, score.py, Move and Fraud consumers
provides:
  - shared reading layer (text cache, label engine, normalization, docmodel registry, content classifier for 11 classes)
  - full application parser and all 9 submission facts
  - run_sim per-tick issue refresh, features merge, quiet-expiry ticks
  - holdout split tooling (score_split.py) and the AGENTS.md gate in one holdout-safe script (gate.sh)
affects: [03-02 forms entities features, 03-03 issues statements, 03-04 VL null-fill, Move, Fraud]

actuals:
  tokens: 35000
  tasks: 3
  commits: 5
plan_head_before: 6a86e58f25307042e0806e3dab61c80f33971a5f
plan_head_after: b4962f83592f1e11c7fe9bece0b54c9a508341a4

tech-stack:
  added: [pypdf 6.21.x, pdfplumber 0.11.x, rapidocr-onnxruntime 1.2.x, onnxruntime]
  patterns:
    - "label-anchored extraction with synonyms in config/read.yaml (D-01)"
    - "content-scored classification with minimum score and runner-up in doc.meta (D-03)"
    - "parser registry: docmodel.register(doc_class, fn(dt, doc)) with lazy PARSER_MODULES"
    - "PDFs generated at test time (tests/pdfgen.py), never committed"

key-files:
  created:
    - config/read.yaml
    - eval/holdout.json
    - scripts/score_split.py
    - scripts/gate.sh
    - prism/read/settings.py
    - prism/read/text.py
    - prism/read/ocr.py
    - prism/read/labels.py
    - prism/read/normalize.py
    - prism/read/docmodel.py
    - prism/read/parse_application.py
    - tests/pdfgen.py
    - tests/real_data.py
  modified:
    - pyproject.toml
    - prism/read/classify.py
    - prism/read/extract.py
    - prism/read/issues.py
    - prism/engine/run.py
    - tests/test_engine.py

key-decisions:
  - "Task 1 config carries every application label from the start so wrapped values stop at the next label"
  - "docmodel tuple fields default to () rather than None (falsy either way; avoids 'or ()' at every call site)"
  - "Parser signature is fn(dt: DocText, doc: Doc) -> Parsed*"
  - "A guarantor Name block is built by sequential label scan, scoped to the guarantor section when a heading exists"
  - "OCR accepts a path or raw bytes (embedded PDF images are passed as bytes)"
  - "An image whose OCR text does not clear min_score is still guarantor_id with unverified=True (never other)"

requirements-completed: [READ-01, READ-02, READ-04]

coverage:
  - id: D1
    description: "Application PDF to the 9 facts through run, validate and score, with source_doc and label confidence"
    requirement: READ-02
    verification:
      - kind: unit
        ref: "tests/test_read_tracer.py, tests/test_read_application.py#test_all_nine_facts"
        status: pass
      - kind: integration
        ref: "bash scripts/gate.sh (TUNING facts 90/90)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Content classifier for 11 classes; never raises; image fallback unverified; statement period"
    requirement: READ-01
    verification:
      - kind: unit
        ref: "tests/test_read_classify.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "OCR for ID photos is lazy and failure-safe (present-but-unverified); real RapidOCR read quality not exercised here"
    requirement: READ-04
    verification:
      - kind: unit
        ref: "tests/test_read_classify.py#test_image_unreadable_is_unverified_guarantor_id"
        status: pass
    human_judgment: true
    rationale: "Tests monkeypatch OCR; actual recognition quality on the ID photo is checked with data in later plans"
  - id: D4
    description: "Engine loop: per-tick issue refresh, features merge, quiet-expiry ticks"
    verification:
      - kind: unit
        ref: "tests/test_read_engine.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "Holdout tooling: score_split never prints holdout rows; gate.sh keeps deal names in files"
    verification:
      - kind: unit
        ref: "tests/test_read_score_split.py"
        status: pass
    human_judgment: false

duration: multiple sessions (stalled twice, resumed)
completed: 2026-11-08
status: complete
---

# Phase 3 Plan 01: Read the Folder, Shared Layer and Tracer Summary

**Content-scored PDF/CSV/image reading layer (pypdf, pdfplumber, lazy RapidOCR) with a label-anchored application parser that extracts all 9 facts at 90/90 on the tuning deals, plus per-tick issue refresh and quiet-expiry ticks in run_sim.**

## Performance

- **Tasks:** 3 (Task 2 as RED then GREEN commits)
- **Files:** 31 changed (13 created source/config/tooling files, 12 test files)
- **Verification:** `bash scripts/gate.sh` exits 0, 475 passed, 1 skipped (baseline 353)

## Accomplishments

- Text layer (`text.py`): kind by magic bytes only, pypdf plain and layout per page, CSV rows, lazy OCR, pdfplumber and embedded-image fallbacks, `pdf_tables`, cache by (path, mtime_ns, size), never raises.
- Label engine, normalization (money, ranges, dates, needed-by, EIN, names with nickname groups, addresses), docmodel dataclasses and registry, content classifier with 11 classes.
- Application parser and `extract_facts` for all 9 fields: purpose via an ordered keyword table (0.6) with product fallback (0.5), range revenue to midpoint (0.5), needed-by null unless date and time.
- Engine: `_refresh_issues` for every live deal every tick, guarded `extract_features` merge, quiet-expiry ticks (D-11, D-14, D-16).
- `scripts/score_split.py` and `scripts/gate.sh` (holdout-safe), guard tests against sample literals.

## Tuning summary line, before and after (D-02, D-18; no holdout number printed or reported)

| | facts | issues_exact | tp | fn | fp | route | stage | flag | held | links |
|---|---|---|---|---|---|---|---|---|---|---|
| BEFORE (stub engine) | 9/90 | 5/10 | 0 | 7 | 0 | 28/40 | 5/10 | 7/10 | 7/10 | 8/10 |
| After Task 1 | 29/90 | 5/10 | 0 | 7 | 0 | 15/40 | 3/10 | 7/10 | 7/10 | 8/10 |
| After Task 2 | 90/90 | 5/10 | 0 | 7 | 0 | 15/40 | 3/10 | 7/10 | 7/10 | 8/10 |
| After Task 3 (final) | 90/90 | 5/10 | 0 | 7 | 0 | 15/40 | 3/10 | 7/10 | 7/10 | 8/10 |

Read-owned columns (facts, issues) did not drop: facts 9 to 90 of 90, issues unchanged (detect_issues is still a stub; 03-03 owns it). Move-owned columns changed (routing 28 to 15 of 40, final_stage 5 to 3 of 10) because Move now receives legal_name and amount_requested, so Intake exits and every deal advances through the pipeline (most to Closed) while no issues are reported yet. Before, Intake never exited, so most deals sat at Intake and null routing matched gold by accident. These recover when 03-03 reports MISSING_DOC and MISMATCH issues. Fraud columns are unchanged.

## Facts missed on the tuning deals

None: 90/90. (The one EIN transposition deal matches through the answer key's accepted alternative, the application value; the IRS-letter replacement is 03-02, D-15.)

## Task Commits

1. **Task 1: Tracer, application PDF to legal_name and amount_requested** - `33599ec` (feat)
2. **Task 2 RED: failing tests for normalization and the application parser** - `e22ec7c` (test)
3. **Task 2 GREEN: normalization, full application parser, 9 facts** - `c8b9073` (feat)
4. **Task 3: classifier for all classes, fallbacks, engine loop, guards** - `b4962f8` (feat)

`commits: 5` in the frontmatter is the measured count of `plan_head_before..plan_head_after`; it includes the orchestrator's pause commit `8183ff3`. Task 1 and Task 3 were committed as one commit each per the plan's one-commit-per-task rule (tests and code together, tree green); only Task 2 has a separate RED commit, which was committed with the tree intentionally red for those tests.

## Interface names as built

- `prism/read/text.py`: `DocText`, `load_text`, `page_markers`, `pdf_tables` (tuple of tables), `clear_cache`.
- `prism/read/ocr.py`: `read_image_text(path_or_bytes)`, `available()`.
- `prism/read/settings.py`: `ReadConfig` (`quiet_minutes`, `limits`, `confidence`, `classify`, `labels`, `class_signals`, `raw`), `get_config()`, `load_read_config(path=None)`. Extra config sections used so far: `stops`, `sections`, `none_markers`, `signature`, `product_synonyms`, `purpose_keywords`, `term_units`, `nicknames`, `classify.period`, `limits.max_images`, `confidence.keyword`.
- `prism/read/labels.py`: `extract_labeled`, `extract_labeled_all(text, labels, field, stops, max_lines)`, `scan_labeled`, `split_sections`. Stops accept `text*` as a prefix.
- `prism/read/normalize.py`: `money_to_cents`, `money_range_to_cents`, `parse_date`, `needed_by_iso`, `norm_ein`, `last4`, `strip_none`, `name_base`, `legal_names_match`, `person_names_match`, `address_key`, `addresses_match`.
- `prism/read/docmodel.py`: all Parsed* dataclasses per the spec, `register(doc_class, fn(dt, doc))`, `parsed`, `parsed_all`, `clear_cache`, `PARSER_MODULES` (3). Tuple fields default to `()`.
- `prism/read/classify.py`: `DOC_CLASSES` (11), `classify`, `score_classes`, `statement_period`.
- `prism/read/parse_application.py`: `parse_application`, `term_to_months`, `product_from_text`.
- `prism/read/extract.py`: `extract_facts` (9 facts), `extract_entities` (stub), `extract_features` (stub, 03-02). `prism/read/issues.py`: `mismatch_evidence` stub (03-03 fills it).
- `prism/engine/run.py`: `_refresh_issues`, `_quiet_expiry_ticks`; `extract_features` merged into `state.features`.

## Decisions Made

See key-decisions. The three layout variants of the application are normalised by trying plain and layout text and keeping the richer guarantor parse.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Directory path read as an empty file**
- **Found during:** Task 1 (test_zero_byte_random_and_truncated_never_raise)
- **Issue:** on Windows a directory has `st_size == 0`, so `load_text(dir)` returned kind empty instead of error.
- **Fix:** `stat.S_ISREG` check returns kind error.
- **Files modified:** prism/read/text.py
- **Committed in:** 33599ec

**2. [Rule 3 - Blocking] Task 1 facts need all application labels in config**
- **Found during:** Task 1 (tracer)
- **Issue:** with only two labels configured, a value ran on into the next unknown label's lines.
- **Fix:** the full application label table went into config/read.yaml in Task 1 (the plan lists it in Task 2).
- **Committed in:** 33599ec

**3. [Rule 1 - Bug] Plan histogram count for equipment quotes**
- **Found during:** Task 3 (real-data class histogram)
- **Issue:** 03-RESEARCH S1 and the plan say 5 equipment quotes; the 10 tuning folders hold 134 files and 4 quotes. Every other class count matches the table exactly and the total equals the files on disk, so the classifier is right and the table was off by one.
- **Fix:** the test asserts 4, with a comment.
- **Committed in:** b4962f8

**4. [Rule 2 - Missing Critical] `.gitattributes` for gate.sh**
- **Issue:** git warned LF would become CRLF on this machine, which would break `bash scripts/gate.sh`.
- **Fix:** `.gitattributes` with `*.sh text eol=lf`.
- **Committed in:** b4962f8

**5. Test-name guard hit** - a test fixture name collided with one gold literal; renamed (the guard never prints the matched value, so the literal was not read).

**Plan-listed items not done:** `tests/test_read_normalize.py` etc. are separate files as planned; `prism/read/extract.py` needed no Task 3 change; the 6th tick expiry comment in `tests/test_engine.py` is the only edit to that file (verified by diff: the n_ticks number and its comment).

**Total deviations:** 4 auto-fixed (2 bugs, 1 blocking, 1 missing critical) plus 1 plan-data correction. **Impact:** none on scope.

## TDD notes

Tasks are `tdd="true"` inside a non-TDD-typed plan whose explicit rule is one commit per task. RED was observed for each task (Task 2: collection error on missing `prism.read.normalize`, committed as `e22ec7c`). This is a strict-classifier INVALID_RED style failure (module missing), recorded honestly. Task 1 and Task 3 RED runs were not committed separately.

## Issues Encountered

- Two session stalls (600 s, API rate limit); work resumed from uncommitted files without loss.
- Bash heredocs through the tool collapsed `\b` and `\n` escapes in a few generated files; fixed by character-level replacement and tests.
- Real RapidOCR recognition was not run in this plan (OCR is monkeypatched in tests); the lazy engine and failure path are covered.

## Known Stubs

- `prism/read/extract.py::extract_entities` returns `[]` and `extract_features` returns `{}` (intentional, 03-02 fills both).
- `prism/read/issues.py::detect_issues` and `mismatch_evidence` are stubs (03-03).
No stub prevents this plan's goal (facts for Move).

## Threat Flags

None. Mitigations applied per the threat register: try/except around every parse with size, page and char caps (T-03-01); `yaml.safe_load` and escaped label tokens only, regexes only from config (T-03-02); OCR text never logged, SSN never parsed or stored, guard test never prints matched values (T-03-03); holdout never printed (T-03-05).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

03-02 (forms, entities, features) and 03-03 (issues, statements) can branch from `b4962f8`: they import text, labels, normalize, docmodel, classify and settings without editing them. Move-owned score columns will recover once 03-03 reports issues.

## Self-Check: PASSED

All created files exist; commits `33599ec`, `e22ec7c`, `c8b9073`, `b4962f8` are ancestors of HEAD; `tests/test_engine.py` differs from the plan base only in the n_ticks number and its comment.

---
*Phase: 03-read-the-folder*
*Completed: 2026-11-08*
