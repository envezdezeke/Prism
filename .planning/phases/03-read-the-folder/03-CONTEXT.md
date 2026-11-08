# Phase 3: Read the Folder - Context

**Gathered:** 2026-11-07 (~20:55 CT, H5)
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the stub bodies in `prism/read/` (`classify.py`, `extract.py`, `issues.py`) so every arriving PDF/CSV/JPG is classified by content, the 9 submission facts plus graph attributes and features are extracted with source + confidence, and `detect_issues` returns exactly the MISSING_DOC / MISSING_PAGE / MISMATCH / OLD_TRICK set the golden labels expect, with zero false alarms on the clean trap deals. Requirements READ-01..READ-08; success criteria in `.planning/ROADMAP.md` Phase 3. Also fill the hand-off fields Move (Phase 4, merged) and Fraud (Phase 5 baseline, merged) already read. Last plan in the phase: Nemotron VL null-fill (N2/N10).

Not in scope: fraud decide/hold rule, clusters, history_flags, F2/F4 (Phase 5); weekend-drop new paper types (MOVE-09); UI.

</domain>

<decisions>
## Implementation Decisions

### Parser generality
- **D-01:** Extraction is **label-anchored and generic**: find each value by its label text ("Legal name", "EIN", "Amount requested", ...) with synonyms kept in a config file (e.g. `config/read.yaml`), plus pdfplumber tables for bank statements and financials. **No** parsers fitted to one sample template's coordinates or exact layout. Reason: the hidden set uses a different trick and may use different layouts. Sample company names, people, amounts never appear in code or config (project rule).
- **D-02:** **Holdout for parser tuning: tune on 10 deals, check on 3.** Held out: `LSFD_docs` (scanned, filenames meaningless), `Harbor Tea Co` (clean trap, must get zero issues), `Summit Peak Flooring`. Executors must not look at holdout PDFs/gold entries while tuning synonyms or thresholds; they report holdout accuracy separately in the SUMMARY (facts correct / total, issues exact match). The planner may swap one holdout deal only with a written reason. After the holdout check passes, all 13 deals count for the final self-score.

### Classification
- **D-03:** **Best guess with a minimum score.** The classifier scores each class from content signals (keywords/phrases, form numbers, table headers), picks the top class if it clears a minimum score, and records the score and the runner-up in `doc.meta`; below the minimum, the class is `other`. Reason: a false MISSING_DOC costs points, so an odd-but-real document should still count. The filename is never read (READ-01).
- **D-04:** Add the missing classes to `DOC_CLASSES`: `form_7004` (tax-extension, distinct from tax_return and never a second application) and `request_letter`. Keep `other`. A guarantor ID can be a JPG (OCR text) or PDF.

### VL + OCR
- **D-05:** **RapidOCR is core**, in the main plans (READ-04). Add `rapidocr-onnxruntime` as a core dependency in `pyproject.toml`. If the import or the read fails, the ID is present-but-unverified: never a crash, never a mismatch, never ID_MISMATCH.
- **D-06:** **The Nemotron VL null-fill is the LAST plan in Phase 3**, built only after the deterministic parsers have been scored against gold, and it's the **first thing cut** if time runs short. Limits from MODEL_DESIGN N2/N10: it fills only fields the parser left null, the value must pass a format check and cross-document agreement where available, `source: "nemotron_vl"`, ≤ 30 calls per run, record/replay cache (live|replay|off; with no key it runs as off), and it **never** creates an issue, mismatch or hold. The model ID comes from env vars (`.env.example`). Never print the key.

### Build order
- **D-07:** **Tracer first, then 2 parallel executors, then VL.**
  1. **Plan 1 (tracer, sequential):** shared PDF/CSV/JPG text-extraction helper + normalization helpers (names, EIN, money, dates, addresses per J13) + classify for the application + the 9 facts from the application, end to end through `python -m prism run`, then validate, then score. Establishes the shared helpers the parallel plans import.
  2. **Plans 2a and 2b (parallel, worktree executors, after Plan 1 is merged and pushed):**
     - 2a: full classify (all classes) + all facts + entities (EntityRef kinds in `prism.contract.EntityKind`) + features (`deposit_months`, `profile`).
     - 2b: `detect_issues`: MISSING_DOC (stage/product/business-age rules, 6 full months before the application date, J11 30-minute quiet, J12), MISSING_PAGE (from "Page X of N" markers), MISMATCH (J13 tolerances), and the 5 OLD_TRICK checks exactly per `rules/known_fraud_checks.md`.
     - The two must not edit the same files. Shared-helper changes go through Plan 1, or one owner is named in the plan.
  3. **Plan 3:** VL null-fill (D-06).
- **D-08:** Every plan ends with the gate in `AGENTS.md`: pytest green, then real run, validate, score. The self-score must not drop, and holdout numbers are reported (D-02).

### Hand-off fields that must be filled (consumers already merged)
- **D-09:** Move needs `facts.legal_name` + `facts.amount_requested` (otherwise Intake never exits), and `state.features["profile"]` with money in **integer cents**. Full key list: `.planning/quick/261107-qx3-*/261107-qx3-SUMMARY.md` item 7. That covers dba, formation_date, application_date, preparer, statement_months, tax_doc, net income, deposits_annualized_cents, cash_cents, relationship, quote, vendor_verified, disbursement, mismatch_evidence, and more. An unknown value is omitted (the memo prints "not provided"). It is never guessed.
- **D-10:** Fraud needs `state.features["deposit_months"]` = list of per-month rows with `deposit_count`, `pct_deposits_multiple_of_100` and `deposit_weekdays` (same names as `history/monthly_deposits.csv`; consumed by `prism/fraud/baseline.py::deposit_features`). It also needs EntityRefs for `vendor` and `remit_account` (plus preparer, phone, registered_agent, address, pdf_producer, bank and guarantor), with canonicalized values via `prism/fraud/canon.py`. Jesse's HANDOFF §9 item 20: PDF producer/creator is an entity.

### Settled before this discussion (do not re-ask)
- Field rules and null-not-guess: `docs/DETAILS_CHECKLIST.md` §1. Issue labels: §2. Judgment calls J6 (application's guarantor name), J7 (revenue range → midpoint, low confidence), J8 (no specific date → null), J11 (30-minute quiet, report all missing at once, late arrival resolves), J12 (6 full months before application date), J13 (tolerances), J15 (application amount wins and raises MISMATCH).
- Signatures in `prism/engine/state.py` and `tests/test_engine.py` are pinned. Replace bodies only. `classify` never raises. `extract_*` are full recomputes. `detect_issues` returns the sorted full open set.

### Claude's Discretion
- Confidence-score scheme (e.g. label match 0.95, table 0.9, OCR 0.6, inferred 0.5), as long as it's deterministic and maps to the UI's High/Medium/Low.
- Caching parsed text per file (by path + mtime) so re-ingest each tick stays fast.
- Exact class scoring weights and the minimum score. Tune on the 10 tuning deals only.
- Module layout inside `prism/read/` (e.g. `text.py`, `normalize.py`, `fields.py`, `statements.py`, `ocr.py`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Rules and requirements
- `.planning/REQUIREMENTS.md`: READ-01..READ-08
- `.planning/ROADMAP.md` § Phase 3: success criteria (golden issue expectations per deal)
- `docs/DETAILS_CHECKLIST.md` §0–2 and §8 (J6–J15): every pass/fail rule for facts and issues
- `data/participant/SUBMISSION_FORMAT.md`, `data/participant/SCHEMA.md`, `data/participant/README.md`: output format and data semantics (local only, not in git)
- `data/participant/rules/stages.json`: per-stage document requirements
- `data/participant/rules/known_fraud_checks.md`: the 5 OLD_TRICK definitions, exactly
- `eval/gold.json` + `eval/README.md`: the answer key (respect the D-02 holdout)

### Engine contract
- `prism/engine/state.py`: Doc / EntityRef / DealState and the per-tick hand-off table
- `prism/engine/run.py`: how ingest calls classify, extract and issues each tick
- `prism/contract.py`: `Extracted`, `Fact`, `ISSUE_RE`, `EntityKind`
- `tests/test_engine.py`: pinned signatures

### Consumers of Read's output
- `.planning/quick/261107-qx3-*/261107-qx3-SUMMARY.md` item 7: the `features["profile"]` keys Move needs
- `prism/move/credit_memo.py`, `prism/move/messages.py`, `prism/move/stage.py`: read profile / vendor_verified
- `prism/fraud/baseline.py::deposit_features`, `prism/fraud/signals.py`, `prism/fraud/canon.py`: read deposit_months and entities
- `HANDOFF.md` §9 items 19–20: returning-customer F1 false link; pdf_producer as an F1 party

### Nemotron (Plan 3 only)
- `docs/MODEL_DESIGN.md` N2, N10, N11, N13: VL limits, cache, cut order
- `.env.example`: model ID env vars

### Working method
- `AGENTS.md`: the gate (pytest, run, validate, score), commit rules
- `.planning/research/STACK.md`: pypdf + pdfplumber + RapidOCR; **never PyMuPDF** (AGPL)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `prism/fraud/canon.py`: canonicalization for names, phones and addresses. Reuse it for entity values and for MISMATCH normalization where it fits J13.
- `prism/engine/visibility.py::parse_time`, `prism.contract.parse_sim_time`: sim-time parsing (−06:00)
- `prism/engine/config.py::Rules`: loaded stages.json, teams, history paths, fraud config; `rules.history_dir` for DUP_EIN
- `prism/engine/score.py` + `python -m prism score`: per-field self-score against gold

### Established Patterns
- Config in YAML under `config/` (fraud.yaml, move.yaml). Read synonyms go in `config/read.yaml`.
- Deterministic: no wall clock, no randomness, sorted iteration.
- A crash in one deal freezes only that deal (`_guard`). Read must still never raise from `classify`.
- Quick-task/phase plans + SUMMARY with before/after scores; parallel executors via Agent `isolation: "worktree"` after the PLAN is pushed.

### Integration Points
- `run.py::_ingest` calls `read_classify.classify(doc)` per new doc, then the extract_facts / extract_entities / detect_issues full recomputes. `state.features` isn't set by `_ingest` today. Plan 2a must fill it, either inside `extract_entities` or through a small, test-covered addition to `_ingest` (a new call such as `read_extract.extract_features`, guarded like the others).
- Current baseline: 353 tests passing; the real run validates; empty-engine self-score is 12/117 facts.

</code_context>

<specifics>
## Specific Ideas

- The ROADMAP success criteria name the exact expected issues per deal. Use them as acceptance tests (from gold), not as literals in code.
- Tyler's Form 7004 → `form_7004` class, accepted for the tax-return requirement only if the business is under 2 years old.
- Oakline: a missing page → `MISSING_PAGE`, never STMT_TAMPER.

</specifics>

<deferred>
## Deferred Ideas

- New paper types from the weekend drop (MOVE-09)
- Fraud fixes from the baseline findings (guarantor across different businesses only, drop vendor name from F1, F3 floor): Phase 5
- VL for classification (VL only fills null fields per N2)

</deferred>
