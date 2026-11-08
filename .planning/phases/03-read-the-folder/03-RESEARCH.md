# Phase 3: Read the Folder - Research

**Researched:** 2026-11-07
**Domain:** Local PDF/CSV/JPG parsing for a loan file, plus deterministic document checks (missing, mismatch, known-fraud)
**Confidence:** MEDIUM. The layouts of the 10 tuning folders are verified by direct reads. OCR is not yet run in this session. The holdout (3 deals) is untouched by design.

<user_constraints>
## User Constraints (from CONTEXT.md)

Copied verbatim from `03-CONTEXT.md`. The planner must honor these.

### Locked Decisions
- **D-01:** Extraction is **label-anchored and generic**: find each value by its label text ("Legal name", "EIN", "Amount requested", ...) with synonyms kept in a config file (e.g. `config/read.yaml`), plus pdfplumber tables for bank statements and financials. **No** parsers fitted to one sample template's coordinates or exact layout. Reason: the hidden set uses a different trick and may use different layouts. Sample company names, people, amounts never appear in code or config (project rule).
- **D-02:** **Holdout for parser tuning: tune on 10 deals, check on 3.** Held out: `LSFD_docs` (scanned, filenames meaningless), `Harbor Tea Co` (clean trap, must get zero issues), `Summit Peak Flooring`. Executors must not look at holdout PDFs/gold entries while tuning synonyms or thresholds; they report holdout accuracy separately in the SUMMARY (facts correct / total, issues exact match). The planner may swap one holdout deal only with a written reason. After the holdout check passes, all 13 deals count for the final self-score.
- **D-03:** **Best guess with a minimum score.** The classifier scores each class from content signals (keywords/phrases, form numbers, table headers), picks the top class if it clears a minimum score, and records the score and the runner-up in `doc.meta`; below the minimum, the class is `other`. Reason: a false MISSING_DOC costs points, so an odd-but-real document should still count. The filename is never read (READ-01).
- **D-04:** Add the missing classes to `DOC_CLASSES`: `form_7004` (tax-extension, distinct from tax_return and never a second application) and `request_letter`. Keep `other`. A guarantor ID can be a JPG (OCR text) or PDF.
- **D-05:** **RapidOCR is core**, in the main plans (READ-04). Add `rapidocr-onnxruntime` as a core dependency in `pyproject.toml`. If the import or the read fails, the ID is present-but-unverified: never a crash, never a mismatch, never ID_MISMATCH.
- **D-06:** **The Nemotron VL null-fill is the LAST plan in Phase 3**, built only after the deterministic parsers have been scored against gold, and it's the **first thing cut** if time runs short. Limits from MODEL_DESIGN N2/N10: it fills only fields the parser left null, the value must pass a format check and cross-document agreement where available, `source: "nemotron_vl"`, <= 30 calls per run, record/replay cache (live|replay|off; with no key it runs as off), and it **never** creates an issue, mismatch or hold. The model ID comes from env vars (`.env.example`). Never print the key.
- **D-07:** **Tracer first, then 2 parallel executors, then VL.**
  1. **Plan 1 (tracer, sequential):** shared PDF/CSV/JPG text-extraction helper + normalization helpers (names, EIN, money, dates, addresses per J13) + classify for the application + the 9 facts from the application, end to end through `python -m prism run`, then validate, then score. Establishes the shared helpers the parallel plans import.
  2. **Plans 2a and 2b (parallel, worktree executors, after Plan 1 is merged and pushed):**
     - 2a: full classify (all classes) + all facts + entities (EntityRef kinds in `prism.contract.EntityKind`) + features (`deposit_months`, `profile`).
     - 2b: `detect_issues`: MISSING_DOC (stage/product/business-age rules, 6 full months before the application date, J11 30-minute quiet, J12), MISSING_PAGE (from "Page X of N" markers), MISMATCH (J13 tolerances), and the 5 OLD_TRICK checks exactly per `rules/known_fraud_checks.md`.
     - The two must not edit the same files. Shared-helper changes go through Plan 1, or one owner is named in the plan.
  3. **Plan 3:** VL null-fill (D-06).
- **D-08:** Every plan ends with the gate in `AGENTS.md`: pytest green, then real run, validate, score. The self-score must not drop, and holdout numbers are reported (D-02).
- **D-09:** Move needs `facts.legal_name` + `facts.amount_requested` (otherwise Intake never exits), and `state.features["profile"]` with money in **integer cents**. Full key list: `.planning/quick/261107-qx3-*/261107-qx3-SUMMARY.md` item 7. That covers dba, formation_date, application_date, preparer, statement_months, tax_doc, net income, deposits_annualized_cents, cash_cents, relationship, quote, vendor_verified, disbursement, mismatch_evidence, and more. An unknown value is omitted (the memo prints "not provided"). It is never guessed.
- **D-10:** Fraud needs `state.features["deposit_months"]` = list of per-month rows with `deposit_count`, `pct_deposits_multiple_of_100` and `deposit_weekdays` (same names as `history/monthly_deposits.csv`; consumed by `prism/fraud/baseline.py::deposit_features`). It also needs EntityRefs for `vendor` and `remit_account` (plus preparer, phone, registered_agent, address, pdf_producer, bank and guarantor), with canonicalized values via `prism/fraud/canon.py`. Jesse's HANDOFF §9 item 20: PDF producer/creator is an entity.

### Claude's Discretion
- Confidence-score scheme (e.g. label match 0.95, table 0.9, OCR 0.6, inferred 0.5), as long as it's deterministic and maps to the UI's High/Medium/Low.
- Caching parsed text per file (by path + mtime) so re-ingest each tick stays fast.
- Exact class scoring weights and the minimum score. Tune on the 10 tuning deals only.
- Module layout inside `prism/read/` (e.g. `text.py`, `normalize.py`, `fields.py`, `statements.py`, `ocr.py`).

### Deferred Ideas (OUT OF SCOPE)
- New paper types from the weekend drop (MOVE-09)
- Fraud fixes from the baseline findings (guarantor across different businesses only, drop vendor name from F1, F3 floor): Phase 5
- VL for classification (VL only fills null fields per N2)

### Settled before discussion (do not re-ask)
Field rules and null-not-guess: `docs/DETAILS_CHECKLIST.md` §1. Issue labels: §2. Judgment calls J6 (application's guarantor name), J7 (revenue range -> midpoint, low confidence), J8 (no specific date -> null), J11 (30-minute quiet, report all missing at once, late arrival resolves), J12 (6 full months before application date), J13 (tolerances), J15 (application amount wins and raises MISMATCH). Signatures in `prism/engine/state.py` and `tests/test_engine.py` are pinned. Replace bodies only. `classify` never raises. `extract_*` are full recomputes. `detect_issues` returns the sorted full open set.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| READ-01 | Classify each PDF/CSV/JPG by content; never filename; never crash | Class signatures verified on 136 files (Survey S1-S3). Classification traps listed in Pitfalls P1-P4 |
| READ-02 | legal_name, EIN, amount, purpose, product, term, guarantor, stated revenue, needed_by, each with source and confidence | Label-anchored extraction validated on all 10 application forms (Survey S4); 3 gaps need parsers (free-text date, revenue range, EIN transposition) |
| READ-03 | Graph attributes: preparer, phone, registered agent, vendor, remit account, producer, address, bank, guarantor, deposit features | Canonical forms must match history CSV exactly (Rules R7); remit account is last-4 only |
| READ-04 | JPG ID via RapidOCR; unreadable = present-but-unverified | Package decision open (Conflict C3); ID layout verified visually (Survey S6) |
| READ-05 | MISSING_DOC by stage, product, business age (7004 only if < 2 years); 6 full months; 30-minute quiet | Rules R1-R3; quiet-gate location is a conflict (C1) |
| READ-06 | MISSING_PAGE from "Page X of N" markers, not PDF page count | Verified marker pattern across all 54 PDF statements (Survey S5) |
| READ-07 | MISMATCH with EIN exact, nickname tolerance, suffix stripping, $1 balance tolerance; no false alarms | Rules R4; all 10 tuning deals cross-checked (Survey S7) |
| READ-08 | 5 OLD_TRICK checks exactly per rules; missing page is not tampering | Rules R5; STMT_TAMPER/REV_INFLATION verified on tuning deals (Survey S5, S8) |

---

## Summary

Phase 3 replaces three stub bodies in `prism/read/` and adds one feature call to `prism/engine/run.py::_ingest`. The sample is small (10 tuning folders, 136 files) and the layouts are regular: every application uses the same label/value form, every bank statement uses the same table, and the five OLD_TRICK checks each reproduce the answer key when computed directly from the files. The hard part is not parsing. It is avoiding false alarms on the messy-but-real deals (a nickname, a partial-year tax return, a missing-page statement that must not count as tampering, a request letter with a different amount, a range revenue) and staying generic enough for a different hidden layout.

Verified this session with throwaway scripts in the scratchpad (no repo files touched): pypdf text and layout extraction parse every statement and application; running-balance deltas recover credit and debit signs; "Page X of N" markers identify the missing page on the one statement that has one; label-anchored extraction hits all 24 labels on all 10 applications; cross-document identity, EIN, address, bank-balance and revenue checks reproduce the answer key's issue set on all 10 tuning deals (Survey S7-S8).

**Primary recommendation:** Build Plan 1 around a single cached text layer per file (pypdf plain + layout, metadata, page markers), label-anchored field extraction driven by `config/read.yaml`, and balance-delta statement parsing. Make `detect_issues` a pure function of the visible documents (no `now` gating) and let Move keep owning the 30-minute quiet gate. Resolve Conflicts C1-C4 before Plan 1 starts.

## Conflicts and Decisions Needed Before Planning

| # | Conflict or risk | Evidence | Recommended resolution |
|---|---|---|---|
| C1 | **Quiet-period rule has no working location.** `detect_issues` is documented as applying the 30-minute quiet rule (`prism/read/issues.py:4`), but `detect_issues` runs only inside `_ingest` (`prism/engine/run.py:86`), and `_ingest` runs only for deals with newly visible files (`run.py:144-147`). A quiet-gated "missing" decision made at a deal's last arrival is never re-evaluated when the quiet period expires, because the end-of-run tick adds no files. A tuning deal whose June statement never arrives would end with no MISSING_DOC. The earlier Move hand-off (`261107-qx3-SUMMARY.md` hand-off item 5) says the opposite: Read reports on every tick and Move owns the gate via `last_arrival_at`. Move's gate exists: `prism/move/stage.py:300-310` (`_eval_time`). | run.py:72-88, 144-147; issues.py:4; qx3 SUMMARY item 5 | `detect_issues` returns issues from visible documents at any `now` (no quiet logic). Move delays requests and exits by the 30 minutes (stage.py `_eval_time`). Issue sets then depend only on documents, so the last ingest is always correct. **User decision needed:** confirm this reading of J11 and update the `issues.py` docstring. |
| C2 | **Tracer test assumes stub behavior.** `test_tracer_tiny_set_to_valid_submission` asserts `deal["issues"] == []` (`tests/test_engine.py:268`) for deals whose files are zero-byte PDFs (`tests/conftest.py:30`, `p.write_bytes(b"")`). Once classify is real, zero-byte files become `other`, so MISSING_DOC fires and the assertion fails. AGENTS.md forbids deleting a test to make it pass. | test_engine.py:255-268; conftest.py:30 | Options: (a) change the test's expected issues to the documented MISSING_DOC set with a written reason; (b) generate minimal text PDFs in the fixture (no PDFs in git; generate at test time with pypdf/hand-written PDF bytes). Recommend (a) plus a new Read-specific test. **User sign-off needed** because it changes an existing assertion. |
| C3 | **OCR package name.** D-05 names `rapidocr-onnxruntime`. STACK.md (line 18, 110) reports a local run of `rapidocr` 3.10.0 + `onnxruntime` on the ID image, with HIGH confidence in the team's notes. The `rapidocr-onnxruntime` line's latest release is 1.2.3 (2025-01-17). | CONTEXT D-05; STACK.md:18,110 | Keep the locked name unless a 2-minute smoke test on the ID photo fails in a scratch venv. If it fails, switch to `rapidocr` 3.10.0 and record a decision. Either way the install needs a human-verify checkpoint (see Package Legitimacy). |
| C4 | **`state.features` is never set.** `_ingest` fills facts, entities and issues only (`run.py:80-88`). Move and Fraud read `features["profile"]`, `features["deposit_months"]`, `features["fraud_watch"]`. `DealState.features` is a pinned field (`prism/engine/state.py:67`). | run.py:80-88; state.py:67 | Add `read_extract.extract_features(state, rules) -> dict`, called through the module and guarded like the others. Merge into `state.features` (update, not replace). Move's monkeypatched tests (`tests/test_move_engine.py:40-60`) write `features["profile"]` from a fake `extract_facts`, so a replacing write would break them. |
| C5 | **Owner of `fraud_watch`.** Move reads `features["fraud_watch"]` (`prism/move/credit_memo.py:264`); the hand-off lists it under Read; the watch tier is a Fraud output. | credit_memo.py:264; qx3 SUMMARY item 7 | Read does not set it. Assign to Phase 5 and have Move treat absence as no watch. Confirm in planning. |
| C6 | **Unknown-vendor semantics for `vendor_verified`.** Move blocks only on an explicit `False` (`prism/move/stage.py:191`). | stage.py:191 | `True` = vendor in history with the same remit last-4. `False` = lookalike (same base, different suffix or remit) or known vendor with a different remit. Absent (`None`) = vendor not in history, so it does not block. Confirm. |
| C7 | **Date-only needed-by.** DETAILS_CHECKLIST §1 requires "a full date and time with `-06:00`, or `null`". No sample has a date without a time. | DETAILS_CHECKLIST §1 | Emit `null` for a date without a time; record in Assumptions. Confirm. |
| C8 | **EIN disagreement on one tuning deal.** Application and IRS letter differ by a transposition. The answer key's fact is the IRS value, and it accepts the application value as an alternative. | gold `extracted_accept` for that deal | Emit the IRS-letter EIN as the fact (matches the key; the scorer also accepts the application value) and keep both in evidence. The issue is raised either way. |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Text extraction and caching (PDF, CSV, JPG) | Engine (`prism/read/text.py`) | Filesystem cache | Deterministic, offline, one parse per file version |
| Classification by content | Engine (`prism/read/classify.py`) | Config (`config/read.yaml` signals) | Pure function of content; no filenames |
| Fields, entities, features | Engine (`prism/read/extract.py`) | Rules (`stages.json`, `teams.json`, history CSVs) | Full recompute from visible docs each ingest |
| Issue rules | Engine (`prism/read/issues.py`) | Config (`config/read.yaml` thresholds) | Pure function of documents; quiet gate lives in Move |
| Quiet gate, requests, exits | Move (`prism/move/stage.py`) | — | Already implemented (`_eval_time`) |
| Hold decision | Fraud (`prism/fraud/decide.py`) | — | Out of scope for Read (Phase 5) |

---

## Standard Stack

### Core (in use or required by D-01..D-05)

| Library | Version | Purpose | Why Standard | Status |
|---------|---------|---------|--------------|--------|
| pypdf | 6.21.1 | Plain and layout text, metadata (Producer, Creator, CreationDate), page count | Already installed in the repo's Python; BSD-3; no AGPL | Installed [VERIFIED: `importlib.metadata` in the Python 3.13.5 env, this session]. Package verdict: see audit |
| pyyaml | (declared) | Load `config/read.yaml` with `safe_load` | Already used by `prism/engine/config.py` | In use |
| rapidocr-onnxruntime | 1.2.3 | OCR of the guarantor ID photo (D-05) | Named by locked decision | Wheel verified: `rapidocr_onnxruntime-1.2.3-py3-none-any.whl` downloaded for `--python-version 3.13 --platform win_amd64` [VERIFIED: pip download, this session]. Declares onnxruntime, opencv-python, numpy, six, Shapely, PyYAML, Pillow, pyclipper [VERIFIED: wheel METADATA]. Runtime on 3.13 NOT run. [ASSUMED] until smoke test |
| onnxruntime | 1.31.1 | OCR runtime | Dependency of both RapidOCR lines | cp313 win_amd64 wheel verified [VERIFIED: pip download]. Install NOT run |
| stdlib `csv`, `re`, `datetime`, `decimal`, `fractions` | — | CSV exports, regexes, dates, exact money | No dependency | Built-in |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pdfplumber | 0.11.10 | Table extraction for statements if layout regex fails on a hidden layout | Only when needed; not installed here [VERIFIED: `pip index versions pdfplumber`, latest 0.11.10]. Its wheel is `py3-none-any` [VERIFIED: pip download]. Lazy-import it |
| rapidocr | 3.10.0 | Maintained RapidOCR line, the one STACK.md reports as tested on the ID image | Fallback if C3 smoke test fails [CITED: STACK.md:18, local run] |
| pytest | 9.1.1 | Test runner | Already installed [VERIFIED: `pytest --version`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pypdf layout mode | pdfplumber words with x-coordinates | More precise columns, slower (STACK.md:17 reports 14 s for 167 files with tables; pypdf layout 2.2 s [CITED: STACK.md:14-16]). Use only if statements break |
| Balance-delta sign rule | Column x-position from header | Balance delta needs no column geometry and cross-checks the printed amount |
| PyMuPDF | — | Forbidden: AGPL (STACK.md:200, CLAUDE.md) |

**Installation (only after C3 and the checkpoint):**
```bash
PY=/c/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe
PYTHONUTF8=1 $PY -m pip install rapidocr-onnxruntime   # per D-05; see C3 and the audit
PYTHONUTF8=1 $PY -m pip install pdfplumber              # only if a layout needs tables
```

**Version verification:** pypdf and the RapidOCR/onnxruntime versions above were checked against the PyPI index this session (`pip index versions`, `pip download --only-binary`). Training-data versions are not used.

---

## Package Legitimacy Audit

Gate run this session: `node ~/.claude/gsd-core/bin/gsd-tools.cjs query package-legitimacy check --ecosystem pypi <pkgs>`, and cp313 wheel checks with `pip download --no-deps --only-binary=:all: --python-version 3.13 --platform win_amd64`.

| Package | Registry | Age (latest release) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|----------------------|-----------|-------------|---------|-------------|
| rapidocr-onnxruntime 1.2.3 | PyPI | 2025-01-17 | not reported | github.com/RapidAI/RapidOCR | [WARNING: flagged as suspicious (reasons: unknown-downloads) — verify before using.] | Keep (locked by D-05). Planner must add `checkpoint:human-verify` before install |
| rapidocr 3.10.0 | PyPI | 2026-10-08 | not reported | none listed | [WARNING: flagged as suspicious (reasons: unknown-downloads, no-repository) — verify before using.] | Fallback only (C3). Checkpoint before install |
| onnxruntime 1.31.1 | PyPI | 2026-10-26 | not reported | onnxruntime.ai | [WARNING: flagged as suspicious (reasons: too-new, unknown-downloads) — verify before using.] | Dependency. Checkpoint before install |
| pdfplumber 0.11.10 | PyPI | 2026-06-15 | not reported | github.com/jsvine/pdfplumber | [WARNING: flagged as suspicious (reasons: unknown-downloads) — verify before using.] | Optional. Checkpoint before install |
| pypdf 6.21.1 (installed) | PyPI | latest 2026-11-06 (7.x) | not reported | github.com/py-pdf/pypdf | [WARNING: flagged as suspicious (reasons: too-new, unknown-downloads) — verify before using.] | Already installed at 6.21.1 (the flagged release is newer). Pin 6.21.1; no new install |
| pypdfium2 | PyPI | 2026-11-07 | not reported | github.com/pypdfium2-team/pypdfium2 | [WARNING: flagged as suspicious (reasons: too-new) — verify before using.] | Not needed in Phase 3 (VL fallback only, Plan 3) |

The verdicts rest on missing download metadata (`weeklyDownloads: null` for every package) and recency, not on evidence of a bad package. The protocol still applies: each new install is gated by one `checkpoint:human-verify`.

**Packages removed due to SLOP verdict:** none.
**Packages flagged SUS:** all listed above. Planner inserts one checkpoint before the first install of rapidocr-onnxruntime (plus onnxruntime, which it pulls in), and one before pdfplumber if used.

*Package names in this document come from the team's STACK.md and CONTEXT D-05 (in-repo, team-verified). The import name `rapidocr_onnxruntime` comes from the downloaded wheel's top-level listing [VERIFIED].*

---

## Architecture Patterns

### Recommended module layout (inside `prism/read/`)

```
prism/read/
  text.py        # per-file cache: pypdf plain + layout pages, metadata, page markers, CSV rows, OCR text
  normalize.py   # names, EIN, money, dates (ISO and M/D/YY), addresses, phones, DL numbers (keep leading zeros)
  classify.py    # DOC_CLASSES + weighted signals from config/read.yaml; never raises
  fields.py      # label-anchored application/ID/IRS/cert/tax/P&L extraction
  statements.py  # statement and CSV parsing, footing, chain, page markers, deposit rows
  ocr.py         # RapidOCR wrapper; lazy import; any failure -> None (present-but-unverified)
  extract.py     # extract_facts, extract_entities, extract_features (full recomputes)
  issues.py      # detect_issues (pure over visible docs)
config/read.yaml # synonyms, nicknames, purpose keywords, class signals and weights, minimum score,
                 # placeholder values, mailbox markers, OCR settings; no sample names
```

Config loading: add a loader next to `load_fraud_config` in `prism/engine/config.py` (new function; pinned names untouched). Default path `REPO_ROOT / "config" / "read.yaml"` (mirrors `DEFAULT_FRAUD_PATH`, config.py line 16-17 region).

### Per-tick data flow (existing, `prism/engine/run.py:72-88`)

```
new visible Docs for this deal
  -> classify(doc)                      per new doc, never raises
  -> extract_facts(state, rules)        full recompute over state.docs; replaces state.facts
  -> extract_entities(state, rules)     full recompute; replaces state.entities
  -> extract_features(state, rules)     NEW (C4); merged into state.features
  -> detect_issues(state, rules, now)   full open set; sorted; run.py computes resolved_issues
```

### Pattern: parse once, derive many
Full recomputes call every extractor over all docs at every ingest. Without a cache, a 173-file run re-parses far more PDFs than it has files. Cache per `(abs path, mtime_ns, size)` in a module-level dict. `os.path.getmtime` is allowed (the AST test bans `time`, `now`, `today`, `random`, `uuid`, `secrets` in engine/read/move/fraud sources, `tests/test_engine.py:402-416`).

### Pattern: a document is a bag of labeled values plus a class
Each class has a label list. A value is the text after a label line, up to the next label or section header, joined with spaces (values wrap, e.g. a use-of-proceeds sentence spans two lines). This is the Plain-text form in Survey S4.

### Anti-patterns to avoid
- **Page-count markers:** never derive MISSING_PAGE from `len(reader.pages)`. Marker pages are not physical pages (S5).
- **Filename hints:** never read the filename, even as a tie-breaker (READ-01).
- **Replacing `features`:** merge only (C4).
- **Quiet logic in `detect_issues`:** see C1.
- **Hard-coded field positions:** label anchoring only (D-01).

---

## Document Survey (10 tuning folders, 136 files)

Coverage: the 10 tuning folders only (D-02). The three holdout folders were excluded by name from every script and their files were never opened. The answer key was read for the 10 tuning entries only. Names, EINs, addresses and amounts are described generically.

### S1. Content signatures (first lines of page 1, verbatim titles)

| Class | Verbatim signature (page 1) | Counts | Notes |
|-------|-----------------------------|--------|-------|
| application | line 2: `Small Business Loan Application` (line 1 is the bank's header, `<bank> — Commercial Lending`) | 10 | Also contains `Section A — Business`, `Section B — Loan request`, `Section C — Owner / guarantor` |
| guarantor_id | `Texas Driver License — Copy` (line 1) | 9 PDF + 1 JPG | JPG shows `TEXAS DRIVER LICENSE` (S6) |
| certificate_of_formation | `Certificate of Formation — Filing Acknowledgment` | 10 | Line 2: `Office of the Secretary of State (synthetic record)` |
| ein_letter | `IRS Notice CP 575 — EIN Assigned (copy)` | 10 | Name line uppercase |
| tax_return | `U.S. Income Tax Return for an S Corporation / Partnership` then `— Summary (Tax Year 2025)` | 9 | No "Tax Return" text in the 7004 |
| financial_statements | `<firm or owner name> — Financial Statements` on line 1 or 2; body has `Profit & Loss` and `Balance sheet as of` | 10 | Firm names vary: a CPA, an enrolled agent, a bookkeeping service, or `Self-prepared` (P2) |
| form_7004 | `Form 7004 — Application for Automatic Extension (copy)` | 1 | Has `Status` and `Extended due date` lines |
| request_letter | `Re: Loan request` then `To: <bank> Commercial Lending` | 10 | Contains a requested amount sentence |
| equipment_quote | `Quotation <number>` then `<vendor> · <address> · <phone>` and `Remit to:` | 5 | Only on equipment deals |
| other | `Active Client Contracts — Summary` (a contract table) | 1 | Numbered `09_` with no `08_` present: numbering gaps are not evidence |
| bank_statement (PDF) | line 1 is the bank name; line 2: `Business Checking Statement` | 54 | Bank name varies by deal (S5) |
| bank_statement (CSV) | line 1: `<bank> - acct ...NNNN - <owner>`; line 2 header: `Posted Date,Details,Amount,Running Bal` | 5 (one deal) | Two-line header; dates `M/D/YY` |

### S2. Metadata (pypdf `reader.metadata`)

- Producer is per-source, not per-deal. Common values: `FIS Statement Services 9.2` on most bank statements; `Skia/PDF m124`, `iLovePDF`, `Microsoft: Print To PDF`, `macOS Version 14.5 ... Quartz PDFContext`, `Adobe PDF Library 17.0`, `QuickBooks Online PDF`. `DocuForge 2.1 (Windows)` appears on the application and on every statement and quote in two deals (Creator `DocuForge Templates`).
- CreationDate is in the file metadata (`D:YYYYMMDDHHMMSS-06'00'`). Not used for any rule.
- Producer of the application packet is the history-comparable `pdf_producer` (`prism/fraud/baseline.py:42`, `HISTORY_PRODUCER_CLASS = "application"`). Producer of statements is a Phase 5 F4 input. Store it on every doc's `meta`.

### S3. Label wording (application form, verbatim, one label per line)

`Legal business name` · `DBA / trade name` · `Federal EIN` · `Entity type / state` · `Date business established` · `Business address` · `Business phone / email` · `Industry (NAICS)` · `Number of employees` · `Annual revenue (most recent year)` · `Primary bank / account` · `Amount requested` · `Product` · `Use of proceeds` · `Requested term` · `Collateral offered` · `Funds needed by` · `Name` · `Title / ownership` · `Date of birth` · `SSN` · `Home address` · `Driver license` · `Affiliated businesses`. Signature line: `/s/ <name> Date: YYYY-MM-DD`.

Other forms: ID (`Name`, `Address`, `Date of birth`, `DL number`, `Class`, `Issued`, `Expires`); IRS (`Name of business`, `Employer Identification Number`, `Date of notice`); certificate (`Entity name`, `Entity type`, `File number`, `Effective date`, `Principal office`, `Registered agent`, `Registered office`, `Organizer`); tax (`Name`, `EIN`, `Gross receipts or sales`, `Ordinary business income`, `Paid preparer`, `Preparer PTIN`, `Date filed`); 7004 (`Name`, `EIN`, `Tax year`, `Extended due date`, `Status`); letter (`We are requesting <amount>`); P&L (`Prepared by:`, table rows `Revenue`, `Net income`, two value columns `FY 2025` and `YTD Jan–Oct 2026`, `Balance sheet as of YYYY-MM-DD`, rows `Cash`, `Accounts receivable`, `Equipment, net`, `Total liabilities`).

### S4. Application extraction, validated against the answer key (10 forms)

- All 24 labels hit on all 10 forms (label-anchored, plain extraction).
- Exact match to the answer key for legal_name, EIN (9 of 10; see C8), amount, product, term, guarantor and stated revenue (where the value is a plain dollar figure).
- Misses that need a parser: (a) `Funds needed by` free text `Friday YYYY-MM-DD by H:MM PM (payroll)` (key shape: `YYYY-MM-DDT15:00-06:00`); (b) revenue as a range `approx 400-500k (annualized, ...)` (key: midpoint 450000, low confidence, J7); (c) EIN transposition (C8).
- `Funds needed by` is `No specific date` on 9 of 10 forms: null (J8).
- Signature date `Date: YYYY-MM-DD` is the application date for J12. It falls on 2026-11-01 to 2026-11-03 across the sample, so the 6-month window is the same for all of them: the six full months May to October 2026.
- `Primary bank / account` has the form `<bank name> ...NNNN`. The bank name is the part before ` ...`. The last four digits are the borrower's account.
- Driver license on the form is `TX <number>`. The number keeps leading zeros on some IDs; never cast it to int.

### S5. Bank statements (PDF, 54 files; CSV, 5 files)

Page structure (all 54):
- Page 1 has no marker in the 3-page statements; the summary block (`Opening balance`, `Total deposits & credits`, `Total withdrawals & debits`, `Closing balance`, `Statement period YYYY-MM-DD to YYYY-MM-DD`, `Account holder`, `Account`) and the first transactions are on it.
- Numbered pages carry `Page X of N` at the bottom. In every multi-page statement, N counts the numbered pages, not the physical pages: a 3-physical-page statement shows `Page 1 of 2` and `Page 2 of 2`; a 2-physical-page statement shows only `Page 1 of 1`.
- One statement shows a single physical page carrying `Page 1 of 2`: the second page is absent. This is the MISSING_PAGE case.

Column layout: plain extraction puts `Date`, `Description`, `Credit`, `Debit`, `Balance` in separate lines and loses which column an amount is in. Layout extraction keeps the columns aligned. Sign rule: `delta = balance_i - balance_(i-1)`, with `balance_0 = Opening balance`. Credit if delta > 0, debit otherwise. Cross-check: `|delta|` equals the one non-balance amount on the line (true on all 54 PDF statements).

Footing (all 54): credits sum to `Total deposits & credits`, debits to `Total withdrawals & debits`, and `Opening + credits - debits = Closing`, to the cent, on every complete statement. The exceptions:
- One complete statement (a deal the answer key marks STMT_TAMPER) has a stated closing about 48 thousand above the footed closing (footed value differs; the transactions and balance chain are internally consistent).
- The missing-page statement fails footing by a large margin because its page 2 is absent. It must not count as tampering.

Chain (opening equals prior closing), verified in chronological order on seven of the nine PDF-statement folders (June to October): every link holds except the tampered statement's successor. Not verified in chronological order on the other two folders; the executor must check them.

CSV exports (one deal, 5 files, months May, July, August, September, October; June absent):
- Line 1: `<bank> - acct ...NNNN - <owner>`. Line 2: header `Posted Date,Details,Amount,Running Bal`. Amounts are signed (`-` for debits). Dates are `M/D/YY` (2-digit year; `%m/%d/%y`). Month period is the dominant posted month (content, not filename).
- Running balance chain holds within each file. Between consecutive present months, the implied opening equals the prior closing (verified for Aug, Sep, Oct). The June gap breaks the chain at July: that is a missing month, not tampering.
- No summary totals: STMT_TAMPER can use the running-balance chain only.

### S6. Guarantor ID (JPG, one deal) and PDFs (9 deals)

- PDF IDs: label lines `Name`, `Address`, `Date of birth`, `DL number`. Values match the application in every tuning deal.
- JPG (phone photo, about 3 degrees rotated, glare-free, uppercase): `TEXAS DRIVER LICENSE` header; `DL <8 digits>`; name uppercase; address in uppercase on two lines (street, then `CITY,  TX ZIP` with a double space); `DOB YYYY-MM-DD`; `EXP YYYY-MM-DD  CLASS C`; `SYNTHETIC SPECIMEN` footer. OCR must strip the `DL ` prefix and collapse spaces. Its address and name match the application once normalized.
- Not run in this session. STACK.md:18 reports a local RapidOCR run that read the name, DL number, DOB and expiry correctly [CITED: STACK.md:18, team's local run]. Treat OCR as present-but-unverified until the smoke test in C3 passes.

### S7. Cross-document checks (answer-key-independent, all 10 tuning deals)

| Check | Result on the 10 tuning deals | Rule implication |
|-------|-------------------------------|------------------|
| Legal name app vs IRS letter vs certificate | Equal after case folding in all 10 (IRS letter is uppercase) | Case-insensitive compare; no false alarm |
| Guarantor name app vs ID | Equal in 9; in 1 the application uses a nickname and the ID has the full legal name plus a middle name | Nickname table + token-subset rule (R4) |
| Guarantor DOB app vs ID | Equal in all 10 | Exact |
| Home address app vs ID | Equal in all 10 (the JPG is normalized to this) | Canonical address compare (R4) |
| DL number app vs ID | Equal in all 10 after dropping `TX ` (leading zeros present on some) | String compare |
| EIN app vs IRS letter vs tax return | Equal in 9; in 1 (a transposition) app differs from both the IRS letter and the tax return | Exact string EIN compare (R4); C8 |
| Business address app vs certificate principal office | Equal in all 10 | Canonical compare |
| Amount app vs request letter | Equal in 9; in 1 the request letter states a different amount | MISMATCH:amount_requested; the application's amount is the fact (J15) |
| Revenue app vs tax gross receipts vs FY P&L | Equal where the business existed for the full tax year. In 2 deals the return and P&L cover a partial year (business formed during that year), so they differ by about half. In 1 deal the application states a range | Compare only when formation date is before the tax year start (R4); never compare ranges |
| Bank balance: P&L `Cash` vs latest statement closing | Within $0.50 in all 10 (balance sheet date equals the October statement end) | MISMATCH:bank_balance with $1.00 tolerance is correct: 0 false alarms |
| Preparer across forms | See S8 table (formats) | Normalize (P3) |

Business age: `Date business established` equals the certificate's `Effective date` in all 10. The form_7004 deal was formed less than two years before its application date, so the 7004 is accepted (R2).

### S8. Preparer, vendor and quote formats

- Tax return `Paid preparer`: `<Name>, <Credential> (<Firm>)` or `<Name> (<Firm>)`. Name is the part before ` (`.
- P&L `Prepared by:`: `<Name>, <Credential>, <Firm> · <phone>` or `<Name>, <Firm> · <phone>` or `Self-prepared, (owner)`. Name is the first two comma parts when the second is a credential (`CPA`, `EA`), else the first part. Prefer the tax-return name when both exist.
- History encodes self-prepared as `Self-prepared` (no owner suffix) and a registered agent placeholder as `(owner)` (`history/deals.csv`, verified). Read must normalize `Self-prepared, (owner)` to `Self-prepared` to match.
- Equipment quote: line 1 `Quotation <number>`; vendor is the text before ` · ` on line 2; `Remit to: <bank> · Routing <9 digits> · Account ending <NNNN>`. The remit account is the four digits after `Account ending`. The 9-digit routing number must never be read as an account.
- Quote total is the value after `TOTAL` ($ with cents). Quote date is ISO.
- Vendor lookalikes in the sample differ from a known vendor only by legal suffix (`LLC` versus `, Inc.`) and remit last-4. Both sit in the answer key as HOLD-level fraud signals (Phase 5), but Read must record the vendor and remit exactly.

### S9. Deposits (for `deposit_months` and REV_INFLATION)

- Round-amount share (`pct_deposits_multiple_of_100`) = share of credits whose amount is an integer multiple of 100 (cents zero). Verified: one folder 52 of 52 round across six months, one folder 7 of 22 round (matches the answer key's note). Use a fraction 0 to 1 (history range 0.0 to 1.0, `history/monthly_deposits.csv`).
- `deposit_weekdays` vocabulary (history, verbatim values): `Mon-Fri` (972 rows), `Mon-Sat` (528), `all days` (30), `Mon,Thu` (12). `parse_weekdays` (`prism/fraud/rarity.py:198`) reads these. Generate labels from the set of weekdays with credits: all seven -> `all days`; Mon-Fri set -> `Mon-Fri`; Mon-Sat set -> `Mon-Sat`; otherwise a comma list in Mon-Sun order.
- `deposit_count` = number of credits in the month. `total_deposits` = sum of credits. `largest_deposit` = max credit. `month_end_balance` = balance after the last transaction of the month.
- Annualized deposits = sum of credits over six full months x 2 (verified against the key's annualized figures for several deals).

### S10. Arrivals (timing)

- Each tuning deal's files arrive within about 20 to 40 sim-minutes of its first file; no gap of 30 minutes or more between consecutive files of the same deal. Quiet-period effects therefore matter mainly for files that never arrive (missing June CSV; missing equipment quote).
- Arrivals are about 173 in total, one per file on disk (no extras, no drop files).

---

## Rules

### R1. Required documents by stage and product (`rules/stages.json`, `docs/DETAILS_CHECKLIST.md` §2)

Verbatim requirements (stages.json):
- Intake `required_to_exit`: `loan application (signed)`, `government photo ID for each guarantor`, `certificate of formation`, `IRS EIN letter`.
- Credit `required_to_exit`: `bank statements for the 6 most recent full months (all pages)`, `financial statements (P&L + balance sheet)`, `most recent business tax return — OR — IRS extension (Form 7004) if the business is < 2 years old`, `known-fraud checks run (rules/known_fraud_checks.md)`.
- Product `required_to_exit`: `equipment loans: vendor quote present; vendor identity and remit-to account verified against known vendors`.

Mapping to issue labels (ISSUE_RE, `prism/contract.py:43`):
- `MISSING_DOC:application` when no signed application (no `/s/` signature line with a Date).
- `MISSING_DOC:guarantor_id` when IDs (PDF or JPG) are fewer than guarantors. The label has no per-person target, so one label covers any shortfall. Sample has one guarantor per form.
- `MISSING_DOC:certificate_of_formation`, `MISSING_DOC:ein_letter`: class absent.
- `MISSING_DOC:bank_statement_YYYY-MM` for each month in the window with no statement (PDF or CSV). Window: the six months before the application month, i.e. months `M-6` to `M-1` where `M` is the application signature month. Verified for application dates 2026-11-01 to 2026-11-03: May to October 2026.
- `MISSING_DOC:financial_statements`: no financial statement doc with both `Profit & Loss` and `Balance sheet`.
- `MISSING_DOC:tax_return`: no tax return, and no form_7004 when the business is under two years old. A form_7004 for a business two years old or more is `MISSING_DOC:tax_return`.
- `MISSING_DOC:equipment_quote`: product is `Equipment Loan` and no equipment quote. Keyed to the product, not to the purpose.

### R2. Business age (form_7004)

`age_years` = application date minus formation date (`Date business established`, falling back to the certificate's `Effective date`). Under two years means formation date after the application date minus two calendar years. Sample: one 7004 deal formed about 1.6 years before application (accepted); two deals with full tax returns formed in mid-2025 (no 7004 needed).

### R3. Quiet period and late arrivals (J11)

Report everything missing at once; late arrivals resolve the issue (`run.py` records `resolved_issues`). The quiet gate itself belongs to Move (`prism/move/stage.py:300-310`, 30 minutes from `last_arrival_at`). See C1.

### R4. MISMATCH rules (READ-07, J13, DETAILS_CHECKLIST §2)

| Field | Compare | Rule |
|-------|---------|------|
| legal_name | application vs IRS letter, certificate, tax return | Casefold; remove periods, commas, apostrophes; `&` becomes `and`; strip one trailing legal suffix (`prism/fraud/canon.py` `split_legal_suffix`); compare base name only (READ-07 "name-suffix stripping"). Open question: a suffix swap (LLC to Inc) is silent under this rule |
| ein | application vs IRS letter, tax return, 7004 | Exact string after strip; format `\d{2}-\d{7}` |
| amount_requested | application vs request letter | Exact to the cent; `$1.2M` reads as 1200000 (J13). Application value is the fact (J15) |
| guarantor_name | application vs ID | Nickname table (config: Bob/Robert, Bill/William, ...); the application name's tokens must match the ID name's tokens, with the ID allowed extra middle names. Application name stays the fact (J6) |
| guarantor_dob | application vs ID | Exact |
| guarantor_address | application home vs ID | Canonical address (`canon_address`: abbreviations Ave/Avenue, Ste/Suite/#, ZIP+4 ignored) |
| annual_revenue | application stated vs tax gross receipts vs FY P&L revenue | Only when application revenue is a plain dollar figure AND the business existed for the full tax year (formation before the tax year start). Within 1 percent. Never compare ranges. Different years never compared |
| bank_balance | P&L `Cash` (balance sheet date) vs latest statement closing | Within $1.00 |

### R5. OLD_TRICK checks (`rules/known_fraud_checks.md`, verbatim definitions)

Verbatim from the bank's file:
- `STMT_TAMPER`: "Each month's opening balance must equal the prior month's closing balance; listed transactions must add up to the summary totals."
- `REV_INFLATION`: "Stated annual revenue (application / tax return) more than 1.5x the annualized deposits in the bank statements."
- `ID_MISMATCH`: "Name, date of birth or address on the photo ID disagrees with the application (beyond common nicknames)."
- `DUP_EIN`: "EIN already used by a different legal name in history."
- `SHELL_ADDRESS`: "Business address is a mailbox store / PMB."

Implementation:
- **STMT_TAMPER:** evaluate only complete statements (page markers complete, no missing page). Footing to the cent. Chain (opening equals prior closing) only between two consecutive months that are both present. A missing month or missing page never triggers it. Tuning result: one deal triggers via footing and chain; the missing-page deal does not trigger.
- **REV_INFLATION:** stated revenue (application value or range midpoint) > 1.5 x (six-month credits x 2). Compute only when all six months are present and complete; with a missing month, do not raise. Tuning results: one deal ~3.1x (triggers); others 0.87x to 1.11x (no trigger). Strict `>`. Do not use a partial-year tax return's gross receipts.
- **ID_MISMATCH:** name (nickname-tolerant token rule from R4), DOB (exact), address (canonical). OCR-unreadable ID yields no ID_MISMATCH (READ-04). Tuning result: none.
- **DUP_EIN:** application EIN appears in history under a different canonical legal name (`canon_text` of `legal_name`, with the suffix rule). History contains two EINs each under two names (one row per pair labelled DUP_EIN). Tuning result: none (all tuning EINs with a history match carry the same name).
- **SHELL_ADDRESS:** business address contains the token `PMB` (word boundary, case-insensitive), or a mailbox marker from config (`Box`, `Mailbox`, a known pack-and-ship chain name). Suite markers `Ste`, `Suite`, `#`, `Apt`, `Unit` never trigger. History: the two SHELL_ADDRESS rows both carry `PMB`; one history address with a `Ste` suite is shared by 15 deals, 14 of them clean. Tuning result: none.

### R6. Facts (READ-02): where each value comes from

| Field | Source (preferred) | Normalization | Confidence (suggested) |
|-------|--------------------|---------------|-----------------------|
| legal_name | Application `Legal business name` (J6 keeps application version) | Verbatim (keep punctuation such as `Inc.`; the scorer compares casefold/trim, so `Inc.` matters) | 0.95 |
| ein | IRS letter `Employer Identification Number` if present, else application `Federal EIN` (C8) | `\d{2}-\d{7}` | 0.95 |
| amount_requested | Application `Amount requested` (J15) | Money to number (`prism/engine/money.py:11` `to_cents`; keep as int or float) | 0.95 |
| purpose_category | Keyword table on `Use of proceeds` (config), product fallback `Equipment Loan` -> `equipment` | Enum only; unknown -> null (never guess) | 0.5 to 0.7 |
| product | Application `Product` | Exact enum (`Term Loan`, `Equipment Loan`, `Revolving Line of Credit`, `Working Capital Loan`); synonyms in config | 0.95 |
| term_months | Application `Requested term` | First integer | 0.95 |
| guarantor_name | Application `Name` in Section C (J6) | Verbatim | 0.95 |
| annual_revenue_stated | Application `Annual revenue (most recent year)` | Money; range `A-B` -> midpoint (J7), evidence keeps the original wording, confidence 0.5 | 0.95 (plain) / 0.5 (range) |
| needed_by | Application `Funds needed by` | `No specific date` -> null (J8). Date + time with `by H:MM AM/PM` -> `YYYY-MM-DDTHH:MM-06:00` (`format_sim_time` shape). Date only -> null (C7) | 0.9 |

Purpose keyword table (config only; generic words, no sample phrases): payroll words (`payroll`, `wages`, `salar`), refinance (`refinanc`, `pay off`, `consolidat`), equipment nouns and verbs (`equipment`, `vehicle`, `truck`, `trailer`, `tractor`, `van`, `printer`, `lift`, `machine`, `oven`, `cooler`, `mower`), expansion (`expan`, `hire`, `pilot`, `launch`, `new location`), inventory (`inventory`, `stock`), working capital (`receivable`, `working capital`, `bridge`, `operating`). Order matters: payroll, refinance, equipment, expansion, inventory, working capital. Tuning check: all examples map to the key's category or an accepted alternative once the order is fixed. Keep the table in config (D-01); do not put sample wording in code.

Source chip: `source_doc` is the `Doc.path` (`prism/engine/state.py:58`, `source_doc: str  # Doc.path`).

### R7. Entities (READ-03, D-10): canonical forms that must match history

Each entity value is re-canonicalized by `prism/fraud/graph.py` via `canon_value(kind, value)` (`prism/fraud/canon.py:73`). Read must emit values whose canonical form equals the history row's canonical form.

| EntityKind (`prism/contract.py:308`) | Source in this deal | Emit | Why |
|---|---|---|---|
| `preparer` | Tax `Paid preparer` name part (or P&L name), normalized (S8) | e.g. `<Name>, CPA` (credential kept, firm dropped) | History `preparer_name` has the credential suffix |
| `phone` | Preparer phone on the P&L `· <phone>` (not the business phone) | digits (canon strips to digits) | History `preparer_phone` only |
| `registered_agent` | Certificate `Registered agent` | verbatim | History `registered_agent` |
| `address` | Application `Business address` | verbatim (canon expands `St`/`Ave`/`Ste`) | History `business_address` |
| `vendor` | Quote vendor name before ` · ` | verbatim (canon splits legal suffix) | History `equipment_vendor` |
| `remit_account` | Quote `Account ending NNNN` | **last 4 digits only** | History `vendor_remit_acct_last4`. A full number or the routing number will not match |
| `pdf_producer` | Application `Doc.meta` producer | verbatim | History `pdf_producer` is the application packet |
| `bank` | Application `Primary bank / account`, name part only | strip ` ...NNNN` | History `bank_name` is the bank name only |
| `guarantor` | Application `Name` | verbatim | History `guarantor_name` |

Placeholder values: `Self-prepared` is emitted as-is (history uses it verbatim); rarity weighting keeps common placeholders from linking. Do not emit `(owner)`, `N/A`, `—`, or `—`-like strings as entities.

Business phone (application) is NOT an entity of kind `phone`: history indexes preparer phones only.

### R8. Features (D-09, D-10): exact keys

`state.features["deposit_months"]`: list of dicts, one per statement month, with the history column names (`prism/fraud/baseline.py:65`, `deposit_features`): `month` (`YYYY-MM`), `total_deposits`, `deposit_count`, `pct_deposits_multiple_of_100` (fraction), `deposit_weekdays` (vocabulary in S9), `largest_deposit`, `month_end_balance`.

`state.features["profile"]` (read by Move through `prism/move/messages.py:51-53` `profile(state)`): keys from qx3 SUMMARY item 7 (verbatim key names): `dba` (null when the form shows a dash), `formation_date` (ISO), `application_date` (signature date, ISO), `preparer`, `use_of_proceeds` (verbatim), `collateral`, `ownership` (from `Title / ownership`), `statement_months` (int, months present), `tax_doc` (`"tax_return"` | `"form_7004"`), `net_income_fy_cents` (int), `net_income_ytd_cents` and `ytd_months` (from the `YTD Jan–Oct` header: 10), `deposits_annualized_cents` (int), `cash_cents`, `receivables_cents`, `liabilities_cents` (from balance sheet), `relationship` (`{"status": "new"|"returning_clean"|"returning_past_due", "since_year": int|None}`), `quote` (`{"number", "vendor", "total_cents", "remit_last4"}`), `vendor_verified` (True | False | absent; C6), `vendor_past_loans` (int, history deals with that vendor and remit), `disbursement` (`{"kind": "borrower"|"vendor", "bank", "last4", ...}`), `mismatch_evidence` (`{field: {"application": str, "document": str, "value": str}}`).

Move-read keys confirmed in the code this session: `dba`, `statement_months`, `tax_doc`, `formation_date`, `application_date`, `deposits_annualized_cents`, `cash_cents`, `relationship` (`status`, `since_year`), `quote` (`vendor`, `remit_last4`), `vendor_verified`, `vendor_past_loans`, `disbursement` (`kind`, `bank`, `last4`, `vendor`, `past_loans`), `mismatch_evidence`, `net_income_ytd_cents`, `ytd_months`, `net_income_fy_cents`. Money keys must be ints (`_int_or_none` in credit_memo; `cents_text` checks `isinstance(..., int)`).

Relationship from history: match the application EIN to a history row. `final_status == funded` and `repayment_status` in `current` or `paid_off`, and `fraud_label == none` -> `returning_clean`. `30_days_past_due` or `charged_off` -> `returning_past_due`. No match -> `new`. `relationship_since` gives `since_year`. Verified: three tuning deals have one history match each with those values.

Fraud watch: not set by Read (C5).

### R9. Issue set on the tuning deals (predicted from the rules above; compare with the key)

| Deal | Expected issues (from answer key) | Triggering rule |
|------|-----------------------------------|-----------------|
| Deal 1 (equipment, letter differs) | `MISMATCH:amount_requested`, `MISSING_DOC:equipment_quote` | R4 amount, R1 equipment |
| Deal 2 (clean, returning) | none | all rules clean |
| Deal 3 (tampered statement) | `OLD_TRICK:STMT_TAMPER`, `OLD_TRICK:REV_INFLATION` | R5 footing and chain; revenue ratio ~3.1x |
| Deal 4 (one page missing) | `MISSING_PAGE:bank_statement_2026-08` | R5 markers (page 1 of 2 only); no STMT_TAMPER |
| Deal 5 (non-form document) | none | contract summary is `other`; no requirement |
| Deal 6 (partial-year return, round deposits) | none | partial-year tax return skipped (R4); ratio ~1.0 |
| Deal 7 (free-text needed-by, preparer name) | none | needed-by parsed; no mismatch |
| Deal 8 (partial-year return, round deposits) | none | partial-year skip; ratio ~1.0 |
| Deal 9 (EIN transposition) | `MISMATCH:ein` | R4 EIN exact |
| Deal 10 (CSV exports, June missing, 7004) | `MISSING_DOC:bank_statement_2026-06` | R1 window month absent; 7004 accepted (R2); range revenue -> midpoint (no mismatch) |

Deal numbers are local to this document. The answer key identifies them for the executor (tuning deals only).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Money text (`$1,234.00`, `-$12.40`, `$1.2M`) | regex money parser per field | `prism/engine/money.py:11` `to_cents` (accepts `"$1,234.50"`, `"1,000"`; rejects bool, nan, inf, garbage) | Already tested (`tests/test_engine.py` money test) |
| Canonical entity keys | new normalizer | `prism/fraud/canon.py` `canon_value` / `split_legal_suffix` / `canon_address` / `canon_account` | Fraud and Read must agree |
| Sim time strings | string building | `prism/contract.py` `format_sim_time` and `parse_sim_time` (must end `-06:00`) | Contract validator rejects other forms |
| PDF text and metadata | custom PDF parser | pypdf `extract_text(extraction_mode="layout")` and `reader.metadata` | Verified on all 136 files |
| Weekday label parsing | new parser | `prism/fraud/rarity.py:198` `parse_weekdays` | Matches history vocabulary |
| Deposit feature math | new code | `prism/fraud/baseline.py:65` `deposit_features` (consumes the rows; do not reimplement) | Fraud owns it |
| OCR | own OCR | RapidOCR (locked) | — |
| Nickname matching | fuzzy distance | explicit nickname table in config | Predictable; no false alarms; fuzzy matching would merge different people |

**Key insight:** every value that crosses into Fraud is already a canonical string produced by `canon.py`. Read's job is to hand over the raw value; `graph.py` re-canonicalizes. The one exception is `remit_account`, where the raw value itself must be the last four digits, because `canon_account` keeps all alphanumerics.

---

## Common Pitfalls

### P1. Filename-keyed classification
**What goes wrong:** Classifier leans on `loan app`, `statement`, `taxes`, `ein`. Named files are right, but files named `aug statement` or `P&L and balance sheet` still need content.
**Prevention:** Content signatures only (S1). Filenames are never read (READ-01).

### P2. Accountant and firm names trigger the wrong class
**What goes wrong:** A financial statement carries an accounting firm whose name contains `Tax` on its first line; the word `Tax` routes it to tax_return. A request letter has `<bank> Commercial Lending` in its address block; `Commercial Lending` routes it to application.
**Prevention:** Require the full form titles: `Small Business Loan Application`, `Income Tax Return ... Summary`, `Financial Statements` plus `Profit & Loss`, `Re: Loan request`. Weight title phrases above bare keywords.

### P3. Preparer string mismatches history
**What goes wrong:** Taking `Self-prepared, (owner)` or `Name, Firm · phone` whole gives a different canonical key than history, silently breaking F1 links.
**Prevention:** Normalize per S8; map self-prepared to `Self-prepared`.

### P4. Form 7004 is not a tax return and not an application
**What goes wrong:** Its text lacks `Tax Return`, so it falls to `other` and tax_return goes MISSING.
**Prevention:** `form_7004` class on its title; the R1/R2 rule accepts it only under two years.

### P5. Missing-page vs tampering
**What goes wrong:** A single-page PDF with `Page 1 of 2` fails footing; the naive tamper check fires.
**Prevention:** Footing and chain run only on complete statements; missing page yields MISSING_PAGE only (READ-08).

### P6. Physical page count used for markers
**What goes wrong:** Comparing PDF page count with the marker N gives false MISSING_PAGE on the 3-physical-page statements (the header page has no marker) and on the 2-physical-page statement with `Page 1 of 1`.
**Prevention:** Missing = `{1..N} − {X found}` over marker values only.

### P7. Balance-column confusion in plain text
**What goes wrong:** Plain extraction loses credit versus debit; deposits are summed wrongly; REV_INFLATION and deposit features are wrong.
**Prevention:** Layout extraction, sign from running-balance delta, cross-check against the printed amount.

### P8. Partial-year tax returns compared to annual revenue
**What goes wrong:** Two tuning deals' tax returns cover about six months; a naive MISMATCH:annual_revenue fires on both (about 50 percent gap).
**Prevention:** Skip revenue comparison when formation is in or after the tax year (R4).

### P9. Round-number and placeholder traps
**What goes wrong:** Amounts just under a committee threshold are data, not errors. Placeholder `Self-prepared` creates links if normalized inconsistently.
**Prevention:** Keep values verbatim; normalization only where R4/R7 says.

### P10. Nicknames and middle names
**What goes wrong:** A nickname on the application (`Bob`) versus the ID's full legal name (`Robert Allen`) gives MISMATCH or ID_MISMATCH.
**Prevention:** Nickname table plus token rule (R4). Application name stays the fact (J6).

### P11. Leading zeros and text numbers
**What goes wrong:** DL numbers with a leading zero become shorter when cast to int; EIN with `-` cast fails.
**Prevention:** Keep identifiers as strings.

### P12. Dates
**What goes wrong:** CSV dates are `M/D/YY` (`5/1/26`); statement dates are `MM/DD/YYYY`; forms are ISO; `needed_by` mixes a weekday word with a date and a 12-hour time. Naive parsing picks the wrong century or drops the PM.
**Prevention:** Explicit formats per source; `Friday` is informational, the ISO date wins; `3:00 PM` becomes `15:00`; always write `-06:00`.

### P13. Statement window when a month is absent
**What goes wrong:** The six-month window is computed from present files, so a missing month shifts the window and the missing one disappears.
**Prevention:** Window is calendar months from the application month (R1). Absent months are listed.

### P14. REV_INFLATION with incomplete months
**What goes wrong:** Annualizing 5 months ×12/5 (as in some estimates) or using the partial month makes the ratio wrong.
**Prevention:** Only with six complete months (R5).

### P15. Vendor remit account format
**What goes wrong:** `Account ending NNNN` stored whole, or the routing number read as the account. Neither matches history's last-4.
**Prevention:** Regex `Account ending (\d{4})` only.

### P16. Bank name with account suffix
**What goes wrong:** `<Bank> ...NNNN` canonicalizes as `<bank> nnnn`, not matching history's bank name.
**Prevention:** Strip ` ...NNNN`.

### P17. Multi-guarantor forms (hidden set)
**What goes wrong:** Only one guarantor exists in the sample, so a single-name parse is untested for two names.
**Prevention:** Parse every `Name` block in Section C; MISSING_DOC:guarantor_id if IDs < names; facts take the first guarantor (Assumption A6).

### P18. OCR noise
**What goes wrong:** Skew, glare, `DL` prefix, double spaces in the city line; a bad OCR read could create an ID_MISMATCH.
**Prevention:** Normalize; any OCR failure or low-confidence field -> no ID_MISMATCH, no MISMATCH (READ-04).

### P19. Sample literal leakage
**What goes wrong:** Adding a sample name to `config/read.yaml` or `prism/read/*.py` (for example a folder name in a comment) fails `tests/test_engine.py:419` (`test_no_sample_literals_in_code`), which scans `prism/**/*.py` and `config/fraud.yaml` (extend to `config/read.yaml`), and the `H-\d{4}` scan.
**Prevention:** Generic words only; test it.

### P20. Read-side timing and `state` mutation
**What goes wrong:** Classify mutates `Doc`; `classify` must return the doc, never raise, and never call wall-clock or randomness (AST test `tests/test_engine.py:402`).
**Prevention:** `os.path.getmtime` for cache keys; no `time`, `datetime.now`, `random`.

---

## Code Examples

Shapes only (not final code). Each uses values verified in this session.

```python
# Sign from balance delta (statements.py). Verified on all 54 PDF statements.
delta = round(balance - prev_balance, 2)
is_credit = delta > 0
assert abs(abs(delta) - printed_amount) < 0.005   # cross-check; a failure marks the statement untrusted
```

```python
# Missing pages from markers only (statements.py). Verified: the 1-of-2 single-page case.
import re
MARK = re.compile(r"Page\s+(\d+)\s+of\s+(\d+)", re.I)
found = {int(x) for x, _ in MARK.findall(text_all_pages)}
n = max((int(n) for _, n in MARK.findall(text_all_pages)), default=0)
missing = sorted(set(range(1, n + 1)) - found)   # non-empty -> MISSING_PAGE:bank_statement_YYYY-MM
```

```python
# Remit account, last four only (fields.py). Verified on the quote form.
m = re.search(r"Account ending\s+(\d{4})", quote_text)   # never the 9-digit routing number
remit_last4 = m.group(1) if m else None
```

```python
# Bank name without the account suffix (fields.py). Verified on the application form.
bank = re.sub(r"\s*\.{3}\d{4}$", "", value).strip()     # "<Bank> ...NNNN" -> "<Bank>"
```

```python
# Needed-by free text (fields.py). Verified on the free-text form.
m = re.search(r"(\d{4}-\d{2}-\d{2}).*?by\s+(\d{1,2}):(\d{2})\s*(AM|PM)", value, re.I)
if m:
    h = int(m.group(2)) % 12 + (12 if m.group(4).upper() == "PM" else 0)
    needed_by = f"{m.group(1)}T{h:02d}:{m.group(3)}-06:00"  # "YYYY-MM-DDT15:00-06:00"
```

```python
# Credits-only deposit row (features). Keys match history columns.
row = {"month": "2026-05", "total_deposits": total, "deposit_count": n,
       "pct_deposits_multiple_of_100": round_count / n, "deposit_weekdays": label,
       "largest_deposit": largest, "month_end_balance": closing}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Coordinate-based template parsers | Label-anchored extraction with config synonyms | Phase 3 decision D-01 | Survives layout changes in the hidden set |
| PyMuPDF for PDFs | pypdf (+ pdfplumber if needed) | STACK decision | AGPL avoided |
| RapidOCR 1.x (`rapidocr-onnxruntime`) | RapidOCR 3.x (`rapidocr`) | 3.x line (latest 3.10.0) | Maintained line; C3 |

**Deprecated/outdated:** a plain-text read of statements (loses credit/debit columns); page-count-based missing-page checks.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | all Read code | ✓ | 3.13.5 at `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe` | — |
| pypdf | text, metadata, markers | ✓ | 6.21.1 | — |
| pyyaml | config/read.yaml | ✓ (declared; tests import it) | — | — |
| pytest | gate | ✓ | 9.1.1 | — |
| pdfplumber | optional tables | ✗ | index has 0.11.10 | pypdf layout (default path) |
| rapidocr-onnxruntime | READ-04 | ✗ (not installed) | 1.2.3 (wheel verified) | rapidocr 3.10.0 (C3) |
| onnxruntime | OCR | ✗ | 1.31.1 cp313 wheel verified | — |
| node/npm | not used in Phase 3 | — | — | — |
| `~/.claude/gsd-core/bin/gsd-tools.cjs` | legitimacy seam | ✓ | — | — |

**Missing dependencies with no fallback:** none blocking Plan 1 (pypdf is present).
**Missing with fallback:** OCR (fallback: present-but-unverified, READ-04; the pipeline runs without it).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths `tests`, pythonpath `.`) |
| Quick run | `PYTHONUTF8=1 py -3.13 -m pytest -q tests/test_engine.py` |
| Full suite | `PYTHONUTF8=1 py -3.13 -m pytest -q` (353 passing at phase start per CONTEXT) |

### Phase Requirements -> Test Map
| Req | Behavior | Test type | Command | Exists? |
|-----|----------|-----------|---------|---------|
| READ-01 | classify by content; never raises | unit on text fixtures | `pytest tests/test_read_classify.py -x` | ❌ Wave 0 |
| READ-02 | label extraction incl. free-text needed-by, range revenue | unit | `pytest tests/test_read_fields.py -x` | ❌ Wave 0 |
| READ-03 | entity canonical forms equal history canon | unit + history check | `pytest tests/test_read_entities.py -x` | ❌ Wave 0 |
| READ-04 | OCR failure -> present-but-unverified | unit (monkeypatched OCR) | `pytest tests/test_read_ocr.py -x` | ❌ Wave 0 |
| READ-05 | MISSING_DOC window, 7004 age, equipment | unit | `pytest tests/test_read_issues.py -x` | ❌ Wave 0 |
| READ-06 | markers, not page count | unit | `pytest tests/test_read_statements.py -x` | ❌ Wave 0 |
| READ-07 | MISMATCH tolerances, no false alarms | unit | `pytest tests/test_read_issues.py -x` | ❌ Wave 0 |
| READ-08 | 5 OLD_TRICK checks, missing page not tamper | unit | `pytest tests/test_read_issues.py -x` | ❌ Wave 0 |
| all | answer-key score not down | self-score | `python -m prism score ...` (AGENTS gate) | ✅ |

### Sampling Rate
- Per task commit: quick test file(s) for the touched module.
- Per wave merge: full suite.
- Phase gate: full suite + real run + validate + score (AGENTS.md gate).

### Wave 0 Gaps
- [ ] `tests/test_read_*.py` text-level tests: build statement/form text as strings; **no PDFs committed** (the repo gitignores `data/` and keeps raw PDFs out).
- [ ] Extend `test_no_sample_literals_in_code` to scan `config/read.yaml`.
- [ ] C2 decision on the tracer test.
- [ ] Monkeypatch OCR in tests (no model load in unit tests).

---

## Security Domain

Applicable ASVS categories for this phase: V5 (input validation: every PDF, CSV, JPG is untrusted; parse errors must become `other` or a skipped value, never a crash or an eval); V6 (no cryptography in Read); V2/V3/V4 not applicable (local batch engine, no sessions). Known threats: malicious PDF (pypdf is pure Python; wrap every parse in try/except and cap text size); CSV injection (values are never executed, only parsed); config injection (`yaml.safe_load` only, as in `load_fraud_config`); path traversal from arrivals (already rejected by `ArrivalLog._clean_path`). Secrets: none read by Read. Do not print OCR text of IDs into logs; the submission carries only the fields the contract allows.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | RapidOCR 1.2.3 runs on Python 3.13 | Standard Stack | OCR fails; fall back to rapidocr 3.10.0 (C3) |
| A2 | OCR reads the ID photo correctly (name, DL, DOB, address) in this environment | Survey S6 | Guarantor ID stays present-but-unverified; no ID_MISMATCH (safe) |
| A3 | Statement chains hold chronologically on the two folders not yet checked in order | Survey S5 | A false STMT_TAMPER would show in the real run; executor verifies |
| A4 | Confidence values 0.95 / 0.9 / 0.5 are acceptable to the UI | R6 | UI maps by thresholds (`ui/src/lib/format.ts` confidenceWord: High >= 0.9, Medium >= 0.6); values chosen to land in the intended bin |
| A5 | Purpose keyword table reproduces the key's categories (or accepted alternatives) on all 10 tuning deals | R6 | Purpose misses on hidden set (acceptable: null over guess) |
| A6 | Sample has one guarantor per form, so the multi-name path is untested | P17 | Hidden set may have two guarantors |
| A7 | The 6-month window uses the signature month of the application | R1 | Off-by-one on a boundary date in hidden set |
| A8 | `Self-prepared` as an entity is safe because rarity weighting handles common values | R7 | F1 false link if rarity is misconfigured (Phase 5) |

**If this table is empty:** all claims verified. (It is not empty: A1-A8 need confirmation before the executor treats them as facts.)

---

## Open Questions

1. **Quiet gate location (C1).** Need a decision. Recommendation: `detect_issues` ignores `now`; Move owns the 30-minute gate.
2. **Tracer test (C2).** Need sign-off on updating the expectation, with a reason.
3. **OCR package (C3).** Need smoke-test result or decision to use rapidocr 3.x.
4. **Unknown vendor (C6).** Recommendation: `vendor_verified` absent (not False).
5. **Date-only needed-by (C7).** Recommendation: null.
6. **Suffix swap in legal names (R4).** Compare base names only, or flag a suffix difference as a mismatch? Recommendation: base names only (READ-07 wording), noted as a residual risk.
7. **Holdout reporting.** D-02 requires holdout numbers in the SUMMARY. Holdout has not been opened in this research and must not be opened to answer this.

---

## Sources

### Primary (HIGH confidence)
- In-repo, read this session: `prism/read/classify.py` (DOC_CLASSES at line 10; classify at 23-25), `prism/read/extract.py` (FACT_FIELDS line 13; extract_facts 16; extract_entities 21), `prism/read/issues.py` (docstring line 4, detect_issues 16), `prism/engine/run.py` (_ingest 72, calls 80-86, fresh loop 144-147), `prism/engine/state.py` (Doc 44, EntityRef 55, DealState 62, features 67), `prism/contract.py` (Stage 23, Product 27, ISSUE_RE 43, Extracted 115, Fact 187, EntityKind 308), `prism/fraud/baseline.py` (HISTORY_COLUMN_KINDS 29, HISTORY_PRODUCER_CLASS 42, deposit_features 65), `prism/fraud/canon.py` (ADDRESS_ABBREVIATIONS 24, canon_account 69, canon_value 73), `prism/fraud/rarity.py` (parse_weekdays 198), `prism/engine/money.py` (to_cents 11), `prism/engine/config.py` (load_fraud_config 170, load_rules 246), `prism/move/messages.py` (profile 51), `prism/move/stage.py` (_eval_time ~300-310, Closed guard ~266-270, vendor check 191), `prism/move/credit_memo.py` (fraud_watch 264), `config/move.yaml` (required_facts line 13-14; blocking Intake 23, Committed 36, Closed 38), `tests/test_engine.py` (test_doc_classes_and_fact_fields 243; test_tracer 255; issues assert 268; AST test 402; sample-literal test 419), `tests/conftest.py` (write_bytes 30), `tests/test_move_engine.py` (monkeypatch 40-60), `data/participant/rules/stages.json` (required_to_exit lines 15, 31, 56), `data/participant/rules/known_fraud_checks.md` (table lines 8-12), `data/participant/SCHEMA.md`, `data/participant/SUBMISSION_FORMAT.md`, `docs/DETAILS_CHECKLIST.md` §1-§2 and §8 (J6-J15), `.planning/quick/261107-qx3-*/261107-qx3-SUMMARY.md` (item 7 and hand-off items 5-8).
- Answer key (`eval/gold.json`): read for the 10 tuning deals only, for expected issues and extracted values. Holdout entries and holdout names are not used.
- Survey runs (throwaway scripts in the scratchpad; no repo writes): pypdf plain and layout extraction, metadata, marker map, statement footing and chain, CSV parse, label extraction, cross-document comparisons, history checks (`history/deals.csv`, `history/monthly_deposits.csv`).
- PyPI index and wheel checks (this session): `pip index versions` for rapidocr-onnxruntime, rapidocr, onnxruntime, pdfplumber; `pip download --only-binary=:all: --python-version 3.13 --platform win_amd64` for rapidocr-onnxruntime 1.2.3, onnxruntime 1.31.1, rapidocr 3.10.0, pdfplumber 0.11.10.
- Legitimacy seam: `gsd-tools.cjs query package-legitimacy check --ecosystem pypi` (rapidocr-onnxruntime, rapidocr, onnxruntime, pdfplumber, pypdfium2, pypdf).

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md` lines 14-18, 107-110, 165-168, 200, 210, 245-258: prior local measurements (pypdf speed; pdfplumber table timing; RapidOCR local run on the ID photo) and the decision never to use PyMuPDF.
- `ui/src/lib/format.ts` (confidenceWord thresholds) for the confidence bins used in A4.

### Tertiary (LOW confidence)
- None used for claims in this document.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM. pypdf installed and verified; RapidOCR version choice unresolved (C3); OCR runtime unverified (A1).
- Architecture: HIGH. Read from the code this session.
- Document layouts and rules: HIGH for the 10 tuning deals (direct reads and cross-checks); MEDIUM for hidden-set generality (by design, unverifiable here).
- Pitfalls: HIGH for each one observed in the survey; MEDIUM for the rest.

**Research date:** 2026-11-07
**Valid until:** 2026-11-08 (deadline-driven; re-verify after any data-pack change)
