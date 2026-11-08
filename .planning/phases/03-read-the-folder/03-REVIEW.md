---
phase: 03-read-the-folder
reviewed: 2026-11-08T07:47:16Z
depth: standard
diff_base: 6a86e58
files_reviewed: 26
files_reviewed_list:
  - prism/engine/run.py
  - prism/read/classify.py
  - prism/read/compare.py
  - prism/read/docmodel.py
  - prism/read/entities.py
  - prism/read/extract.py
  - prism/read/features.py
  - prism/read/history.py
  - prism/read/issues.py
  - prism/read/labels.py
  - prism/read/normalize.py
  - prism/read/ocr.py
  - prism/read/old_tricks.py
  - prism/read/parse_application.py
  - prism/read/parse_forms.py
  - prism/read/requirements.py
  - prism/read/settings.py
  - prism/read/statements.py
  - prism/read/text.py
  - prism/read/vl.py
  - config/read.yaml
  - config/read_issues.yaml
  - scripts/gate.sh
  - scripts/read_report.py
  - scripts/score_split.py
  - scripts/vl_smoke.py
findings:
  critical: 1
  high: 6
  medium: 10
  low: 9
  total: 26
  necessity: 0
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-11-08T07:47:16Z
**Depth:** standard (with targeted cross-module tracing of the issue and VL paths)
**Files Reviewed:** 26 source files (`git diff 6a86e58..HEAD -- prism scripts config`). Test files were checked only where they affect isolation (`tests/conftest.py` VL fixture, `tests/test_engine.py`).
**Status:** issues_found

## Summary

The Read layer is defensive and mostly deterministic. There is no wall-clock use: only `time.sleep` appears, and only in the VL retry path. Iteration is sorted, caches are keyed by `(path, mtime_ns, size)`, sim time is always `-06:00`, and every rule group, parser and Read entry point is wrapped so that an exception cannot freeze a deal. The visibility rule holds. Read only touches `state.docs` (the arrived files) plus `history/`, and nothing in `prism/read` lists the deal folder. Secret handling in `prism/read/vl.py` is sound. The key only goes into the `Authorization` header. Transport errors are reduced to `"http <code>"` / type names with `from None`, the cache stores only `{model, fields, answer}`, and `.env` parsing keeps only the prefixed keys. No leak of the key was found.

The main risks are **generalization and false alarms on the hidden set**. Each of the issues below was confirmed by running the real functions on small synthetic inputs:

- A PDF bank statement whose transaction rows do not parse but whose summary block does is marked "verified" with zero rows, and it then raises **OLD_TRICK:STMT_TAMPER on a clean statement** (CR-01).
- The statement month only comes from ISO dates. `Statement period: 05/01/2026 - 05/31/2026` or `May 1, 2026 - May 31, 2026` gives no period, so the deal gets **a false MISSING_DOC for that month** (HI-01).
- Classification depends on exact title phrases. An application titled "Business Loan Application", a Form 1065 or a Debit/Credit CSV statement falls to `other` (HI-02).
- A request letter that says "we are requesting 36 months..." is read as **$36**, which raises MISMATCH:amount_requested (HI-04).
- The VL null-fill turns on live mode by default when a key exists. It accepts "N/A" / "Not provided" as a legal or guarantor name. Its "whole reply rejected on unrequested keys" hardening can be bypassed with a nested object (HI-05, HI-06, ME-01).

The sample self-score (90/90, 10/10, holdout passed) does not cover these cases, because the sample layouts happen to avoid them.

## Critical Issues

### CR-01: A clean PDF statement with unparsed rows but a parsed summary raises STMT_TAMPER

**File:** `prism/read/statements.py:227-245`, `prism/read/statements.py:357-385`
**Issue:** In `_parse_pdf`, if neither `_find_rows` nor the pdfplumber fallback finds any rows, the code sets `ok = True` (line 230). `signs_verified` then becomes `bool(ok and (rows or summary_seen))`, which is True. The statement is now `trusted()` with **zero transactions**. `footing_errors` computes `credits = debits = 0` from the empty `txns` and compares them with the printed `Total deposits` / `Total withdrawals`. The result is `credits_sum` and `debits_sum`, which raises `OLD_TRICK:STMT_TAMPER`.
Rows fail to parse whenever a statement's row dates carry no year (`05/03`, `May 03`, `03-May`) or its amounts use a `CR`/`DR` suffix or a trailing currency code. That is a very likely layout change in the hidden set. Reproduced: a statement with summary totals and rows `05/03 Deposit 500.00 1,500.00` gives `rows 0 verified True trusted True footing ['credits_sum', 'debits_sum']`. This is a false OLD_TRICK on a good deal: it costs points and, through Fraud, can hold a clean deal.
**Fix:** Never treat a statement with no parsed rows as row-verified. Only check the summary arithmetic in that case:
```python
# _parse_pdf
if not rows:
    rows, ok = _table_rows(getattr(doc, "abs_path", None), cfg, opening)
signs_verified = bool(ok and rows)
# footing_errors: skip the row-sum checks when there are no rows
if not txns:
    if None not in (ps.opening_cents, ps.total_credits_cents, ps.total_debits_cents, ps.closing_cents) \
            and ps.opening_cents + ps.total_credits_cents - ps.total_debits_cents != ps.closing_cents:
        return ["summary_closing"]
    return []
```
Add a regression test for "summary parsed, rows unparsed, totals correct → no STMT_TAMPER".

## High

### HI-01: The statement period accepts only ISO dates, so clean statements produce false MISSING_DOC:bank_statement_<month>

**File:** `prism/read/classify.py:133-140`, `prism/read/requirements.py:351`
**Issue:** `statement_period` keeps only `_ISO_DATE` matches from the period label value. If there are none, it falls back to dates at the **start of a line** in `M/D/YYYY` form. Reproduced:
- `Statement period: 05/01/2026 - 05/31/2026` → `None`
- `Statement period: May 1, 2026 - May 31, 2026` → `None`
- only `2026-05-01 to 2026-05-31` works

`required_labels` builds `have` from `Doc.period` (classify's value) and ignores `ParsedStatement.period` / `period_end`. `statements._dates_in` would have parsed the US form, but its result is never used for the requirement. Every statement month in a hidden-set layout with non-ISO period dates becomes `MISSING_DOC:bank_statement_YYYY-MM`. It is also dropped from MISSING_PAGE grouping (`doc.period` is falsy) and from REV_INFLATION.
**Fix:** Parse every date token in the label value with `parse_date` (ISO, US, "Month D, YYYY", "D Mon YYYY"), for example by reusing a month-name-aware tokenizer. In `required_labels`, fall back to the parsed statement: `period = d.period or getattr(docmodel.parsed(d), "period", None)`.

### HI-02: Classification is gated on exact sample title phrases; real variants fall to `other`

**File:** `config/read.yaml:37-92` (used by `prism/read/classify.py:66-98`, `min_score: 3.0`)
**Issue:** For several classes, the only signal worth 3.0 is one exact title phrase. The other signals add up to less than `min_score`. Reproduced with `score_classes`:
- `"Business Loan Application"` with "Legal business name" and "Amount requested" → application 2.0 → **other**. The deal then has *no facts at all* (Move never leaves Intake) and gets `MISSING_DOC:application`.
- A Form 1065 (`"U.S. Return of Partnership Income"`) with gross receipts, ordinary business income and paid preparer → tax_return 2.5 → **other** → false `MISSING_DOC:tax_return`. Schedule C / 1040 returns fail the same way.
- A CSV statement with `Date,Description,Debit,Credit,Balance` columns → bank_statement 0.0, because `csv_headers` requires an `amount` token. `_csv_columns` would also reject it. The result is a false MISSING_DOC for that month.
- `request_letter` needs `^re: loan request`; without it the maximum score is 1.0.
- `guarantor_id` needs "driver license"; a state ID card or passport PDF gives other → MISSING_DOC:guarantor_id.

The hidden set "uses a different trick" and may use other templates, and a false MISSING_DOC costs points (D-03).
**Fix:**
- Add generic title signals: `loan application`, `credit application`, `u.s. return of partnership income`, `profit or loss from business`, `identification card`, `passport`.
- Add a second `csv_headers` signal `[date, credit, debit, bal]` and teach `_csv_columns` about split debit/credit columns.
- Add a fallback: when nothing reaches `min_score` but the top class has ≥ 2.0 from at least two distinct body signals and a clear margin over the runner-up, accept it and record low confidence in `meta`.

### HI-03: Editing one PDF row amount suppresses both STMT_TAMPER and REV_INFLATION

**File:** `prism/read/statements.py:157-160`, `prism/read/statements.py:352-359`, `prism/read/old_tricks.py:393-395`
**Issue:** `_find_rows` sets `ok = False` whenever `abs(delta) != amount`. So a row whose printed amount does not match its running-balance change (the classic edited deposit) makes the statement **unverified**. `footing_errors` and the chain check then return nothing for it, and `annualized_deposits_cents` returns None, so REV_INFLATION cannot run either. Reproduced: a deposit inflated from 500.00 to 5,000.00 with the balance column unchanged gives `verified False footing []`. 03-03-SUMMARY documents this as a "known limitation", but it is the most common way to tamper with a statement, and the hidden set's trick is unknown.
**Fix:** Separate *parse confidence* from *footing*. If every row parsed (date, amount and balance all present) and the running-balance column is internally consistent, a row with `abs(delta) != amount` is a footing error (`row_amount`), not "unverified". Keep "unverified" for rows that fail to parse or for a missing opening balance.

### HI-04: The request-letter amount regex takes any bare number ("36 months" → $36), raising a false MISMATCH:amount_requested

**File:** `config/read.yaml:182-184`, `prism/read/parse_forms.py:285-294`, `prism/read/compare.py:106-112`
**Issue:** Both `request_amount` patterns make the `$` optional and accept any digit run. When `\s?m` would run into a word, the regex backtracks off the suffix, so `"36 m|onths"` becomes `36`. Reproduced: `"We are requesting 36 months of working capital, $250,000 in total."` → `ParsedLetter(amount_cents=3600)`. The same happens for `"seeking 2 trucks"`, `"loan of 5 years"` and `"request for 2026 expansion"`. `compare._amount` then raises `MISMATCH:amount_requested` against the application. The pattern also misses `"We are requesting a $250,000 term loan"`, which returns None.
**Fix:** Require money evidence: a leading `$`, a scale suffix (`k|m|mm|thousand|million`) followed by a word boundary, or a thousands-grouped number (`\d{1,3}(,\d{3})+`). Reject matches followed by a unit word (`months|years|yrs|%|pieces|trucks|units`). Allow up to ~4 filler words between the verb and the amount, for example `(?:\w+\s+){0,4}?\$\d...`.

### HI-05: Live VL mode is the default whenever a key exists; scored output then depends on network timing and the call budget

**File:** `prism/read/vl.py:118-127`, `prism/read/vl.py:165-166`, `prism/read/vl.py:438-479`
**Issue:** If `NEMOTRON_MODE` is unset and `NVIDIA_API_KEY` is set (it is in the team's `.env`), `mode()` returns `live`. A plain `python -m prism run` then makes network calls that can change scored `extracted` fields.
- **Run to run:** run 1 can time out or get a 429 (no fill, and the key is added to `_RUN.failed`). Run 2 hits the network successfully or reads the cache written by another run, and fills the field. The outputs differ.
- **Budget order:** deals are processed in sorted order, and a cache miss uses up the 30-call budget. In run 1 late deals can be starved. In run 2 the early deals hit the cache for free, so later deals now get calls. This breaks the project's "identical output across runs" constraint and the CLAUDE.md rule that "every scored field ... must come from deterministic code".
**Fix:** Make the default `replay`, or `off`, when the mode is unset. Allow `live` only with an explicit `NEMOTRON_MODE=live`, and have `gate.sh` / the submission run pin `NEMOTRON_MODE=replay` against a committed or frozen cache. Log (without values) the number of cache misses in replay mode so gaps are visible.

### HI-06: VL validators accept placeholder and ungrounded strings as legal_name / guarantor_name

**File:** `prism/read/vl.py:280-284`, `prism/read/vl.py:352-369`
**Issue:** `_valid_name` only checks for a 2–120 character single-line string. Verified: `"N/A"`, `"Not provided"`, `"unknown"` and `"Not stated in document"` all pass for both `legal_name` and `guarantor_name`. If no sibling document exists, `agrees()` returns True, because with no sibling the format check alone decides. Models often answer with such phrases instead of `null`. The phrase becomes a scored fact, and Move leaves Intake because `legal_name` is now set. Nothing ties a name to the document either. A hallucinated name, or a name planted by a prompt injection in the document text, is accepted as long as it is well formed. This is the T-03-16 threat, only partly mitigated.
**Fix:** Run `strip_none()` and the `entities.placeholders` list over every string reply, and reject values with no alphabetic token of three or more letters. For text inputs, require grounding: the whitespace- and case-normalized value must appear in the document text that was sent. For image inputs, require a sibling-document match before filling a name.

## Medium

### ME-01: `parse_answer` accepts a nested or later JSON object, so the "whole reply rejected on unrequested keys" hardening can be bypassed

**File:** `prism/read/vl.py:257-270`
**Issue:** The loop tries `raw_decode` at **every** `{`. When the top-level object has an extra key, it is skipped and the scan goes on into its children or into later objects. Verified:
- `{"legal_name": null, "note": {"amount_requested": 9999999}}` → `{'amount_requested': 9999999}`
- `'Example: {"amount_requested": 1} Answer: {"amount_requested": 50000}'` → the example value `1`

03-04-SUMMARY says a reply with unrequested keys "is rejected as a whole". It is not.
**Fix:** Strip code fences, `raw_decode` only the first top-level `{`, and return None if that object has any key outside `fields`. Do not continue scanning after a rejected object. Also reject a reply that contains more than one top-level object.

### ME-02: Address comparison treats swapped numbers and digit-prefix addresses as equal, so ID_MISMATCH is missed

**File:** `prism/read/normalize.py:436-445`, `prism/read/compare.py:190-200`
**Issue:** `address_key` returns `sorted(set(tokens))`, which drops both order and duplicates. Verified: `"100 Main St Suite 200 ..."` matches `"200 Main St Suite 100 ..."`. `_address_agrees` also accepts raw substring containment of the glued forms, even for non-OCR IDs: `"12 Main St ..."` agrees with `"112 Main St ..."` (verified). An ID address that differs only in the house number or unit, which is a typical synthetic-identity edit, never raises OLD_TRICK:ID_MISMATCH.
**Fix:** Keep the token order (canonicalize abbreviations and the suite marker, but do not sort). Compare the house number and the unit as separate exact fields. Allow substring containment only when `ocr` is True, and only on token boundaries.

### ME-03: The name substring fallback applies to non-OCR IDs and to short aliases, so ID_MISMATCH is missed

**File:** `prism/read/compare.py:163-187`
**Issue:** The `ocr` argument of `_name_agrees` is never used, so the glued-substring fallback runs for clean text IDs too. Aliases such as `al`, `ed`, `dan` and `jo` are substrings of many names. Verified: `_name_agrees("Dan Lee", "Danielle Leeson", False)` → True. Also, `person_names_match("Smith", "John Smith")` is True, so a one-token application name agrees with any ID that shares the surname.
**Fix:** Use the glued fallback only `if ocr`, only for aliases of three or more characters, and require the matches in order. For non-OCR IDs, rely on `person_names_match` alone.

### ME-04: Two-digit years always map to 20YY; a DOB of "03/14/68" becomes 2068 and raises a false ID_MISMATCH

**File:** `prism/read/normalize.py:304-308`, `prism/read/compare.py:203-205`, `prism/read/parse_forms.py:146-197`
**Issue:** `parse_date("03/14/68")` → `2068-03-14` (verified). A text ID or OCR read that prints a two-digit birth year disagrees with the application's `03/14/1968`. On a non-OCR ID, that single field is enough to raise `OLD_TRICK:ID_MISMATCH` (`raising_id_results`, which needs only one field when not OCR).
**Fix:** Pivot two-digit years against the sim reference year: `yy > (ref_year % 100) → 19yy`. Alternatively, in `_dob_agrees`, compare only month, day and the last two digits of the year when either side was written with a two-digit year.

### ME-05: MISSING_PAGE grouping by class hides real gaps

**File:** `prism/read/statements.py:97-115`, `prism/read/statements.py:405-408`
**Issue:** For `page_gap_classes`, every doc of a class is merged into one group. `marker_gap` returns `()` as soon as any copy is complete, or as soon as any copy has no markers. So:
- two guarantor IDs, one complete and one missing page 2, give no MISSING_PAGE:guarantor_id;
- a P&L file (`Page 1 of 2` only) next to a separate balance-sheet file (`Page 1 of 1`) gives no MISSING_PAGE:financial_statements;
- a marker-less JPG ID next to a gapped PDF ID gives nothing.
**Fix:** Evaluate each document on its own. Merge copies only when they are the same logical document: the same statement month, or the same class with the same `N` and the same parsed identity (name or EIN). Ignore copies without markers instead of letting them veto the group.

### ME-06: A title line that mentions "Balance Sheet" wipes out P&L extraction

**File:** `prism/read/parse_forms.py:382-389`, `prism/read/parse_forms.py:426-458`
**Issue:** `_split_statements` splits at the **first** line that contains a balance-sheet phrase. For a cover or title line such as `"Financial Statements - Profit & Loss and Balance Sheet"`, `pl_text` is empty and both revenue and net income come out None (verified: `fin rev None ni None`). This silently disables the revenue MISMATCH and REV_INFLATION support, and drops `net_income_*` from the Move profile.
**Fix:** Skip lines that contain both a P&L phrase and a BS phrase, or lines inside the first `title_lines`. Alternatively, split at the BS phrase that comes after the first P&L row (Revenue/Net income) has been seen.

### ME-07: Purpose keywords are fitted to the sample deals

**File:** `config/read.yaml:253-259`, `prism/read/extract.py:24-36`
**Issue:** The equipment and expansion word lists (`mower`, `oven`, `cooler`, `forklift`, `printer`, `press`, `lift`, `truck/trailer/tractor`, `pilot`) line up with the sample folders' businesses: landscaping, catering, print shop, auto, freight, building supply. This is fitting to the samples, which the project rule forbids in spirit. A hidden-set purpose such as "excavator", "espresso machine", "dental chair", "HVAC unit" or "POS system" only resolves through the product fallback (`Equipment Loan` → equipment). On a non-equipment product it gives `purpose_category = None`. Matching is also order-dependent (payroll > refinance > equipment > expansion), so "hire staff to open a new location and cover payroll" → payroll.
**Fix:** Use generic category words (`equipment|machine|machinery|vehicle|tools|purchase of`, ...). Pick the category with the most hits instead of the first hit. Treat a tie as None. Write down the rationale for each word in the config.

### ME-08: "equipment" matches before "term loan" in product_synonyms

**File:** `config/read.yaml:240-251`, `prism/read/parse_application.py:50-57`
**Issue:** The first matching phrase wins, and the bare word `equipment` comes before `term loan`. Verified: `product_from_text("Term loan for equipment purchase")` → `Equipment Loan`. The wrong product is a wrong scored fact, and it also triggers the `product_quote` requirement, which gives a false `MISSING_DOC:equipment_quote`. `loc` and `term` are similarly loose.
**Fix:** Match the four full product names first, in any position, and use the fragment synonyms (`equipment`, `term`, `revolving`, `loc`) only when no full name matched. Prefer the longest match.

### ME-09: The features merge never removes keys, so `vl_fills` and other Read-owned keys go stale

**File:** `prism/engine/run.py:88-90`, `prism/read/extract.py:137-157`
**Issue:** `state.features.update(features)` adds and overwrites keys but never deletes them. `extract_features` omits `vl_fills` when it is empty. If a VL fill is withdrawn on a later ingest, `features["vl_fills"]` still claims the fill while `state.facts` no longer has it. That happens when a sibling document that disagrees arrives and `agrees()` now fails, or when the deterministic parser now finds the value. The same applies to `deposit_months` if it ever becomes empty, for example when a later copy turns out incomplete.
**Fix:** Have `extract_features` always return the keys it owns (`vl_fills: {}`, `deposit_months: []`). Alternatively, have `_ingest` pop Read-owned keys before merging.

### ME-10: Statement selection differs between the profile, Fraud's deposit_months and REV_INFLATION

**File:** `prism/read/features.py:29-38`, `prism/read/features.py:131-144`, `prism/read/old_tricks.py:329-338`, `prism/read/old_tricks.py:384-400`, `prism/read/statements.py:153-155`
**Issue:**
- `features.complete_months` prefers `ps.period` over `doc.period` and ignores `signs_verified`. `old_tricks.latest_complete_statements` prefers `doc.period`.
- `_deposits_annualized` uses the *latest six complete months available*, regardless of the reference-date window. `annualized_deposits_cents` uses the window and requires trusted statements. The memo's "deposits annualized" can therefore disagree with whether REV_INFLATION fired.
- With no parsed opening balance, `_find_rows` signs the first row as a credit even when it is a debit (`signed = amount`). That inflates `deposit_count`, `total_deposits` and `pct_deposits_multiple_of_100`, which Fraud's baseline uses.
**Fix:** Add one shared `statement_months(state, *, trusted_only, window)` helper in `old_tricks` or `statements`, and use it in both places. Leave the first row's sign unknown (exclude it from credit features) when the opening balance is unknown.

## Low

### LO-01: The OCR noise list contains sample-specific words

**File:** `config/read.yaml:210`
**Issue:** `noise` includes `texas`, `synthetic` and `specimen`, which come from the sample ID images. On an ID from another state, a line holding only the state name (`CALIFORNIA`) passes `is_name()` and can become the guarantor name on the ID. That gives a name disagreement, though an OCR ID still needs two disagreeing fields.
**Fix:** Use a generic list of the 50 state names and abbreviations plus generic ID words, and drop `synthetic` / `specimen`.

### LO-02: `NVIDIA_BASE_URL` is not checked for https

**File:** `prism/read/vl.py:181-188`
**Issue:** If the env or `.env` sets an `http://` or foreign host, the bearer key is sent to it in clear text. The risk is limited to whoever controls the environment, but it is cheap to close.
**Fix:** Require `urlparse(base).scheme == "https"` (and optionally an allowlisted host). Otherwise treat the mode as `off`.

### LO-03: Parsing has no time bound; one pathological PDF can hang the whole run

**File:** `prism/read/text.py:104-170`, `prism/read/text.py:176-201`, `prism/read/ocr.py:426-441`
**Issue:** Exceptions are isolated per deal, but hangs are not. pypdf, pdfplumber (`extract_text(layout=True)`, `extract_tables`) and RapidOCR run inline with no timeout. A crafted or corrupt PDF in one folder can stall every deal, and the submission never gets written.
**Fix:** Run text extraction in a worker with a per-file timeout, for example `concurrent.futures.ProcessPoolExecutor` with `result(timeout=...)`. On timeout return `DocText(kind="error", error="timeout")`.

### LO-04: `docmodel.parsed` assumes `abs_path` is a `Path`

**File:** `prism/read/docmodel.py:223-224`
**Issue:** `doc.abs_path.resolve()` raises `AttributeError` for a `str`. The outer `except` swallows it and every document silently parses to None. `text.py` and `vl.py` both wrap the value in `Path(...)`. Today the engine always passes a `Path`, but scripts and tests that build `Doc` by hand can hit this.
**Fix:** `p = Path(doc.abs_path); st = os.stat(p); key = (str(p.resolve()), ...)`.

### LO-05: Image OCR re-opens the file by path instead of passing the bytes already read

**File:** `prism/read/text.py:245-248`
**Issue:** `_ocr.read_image_text(str(path))` re-reads the file. Some RapidOCR / OpenCV backends fail on Windows paths with non-ASCII characters (`cv2.imread`), which leaves the ID unverified. The bytes are already in `data`.
**Fix:** `_ocr.read_image_text(data)`.

### LO-06: Quote vendor and number come from fixed line positions

**File:** `prism/read/parse_forms.py:304-312`
**Issue:** `number` is read from `lines[0]` and `vendor` is the first segment of `lines[1]`. This is position-based extraction, against D-01. `vendor` feeds the Fraud `vendor` entity and `vendor_verified`, so a layout with a logo line or address first produces a wrong vendor and wrong lookalike results.
**Fix:** Try labeled fields first (`Vendor`, `From`, `Seller`, `Supplier`, `Remit to` name). Fall back to the position-based guess only when none is found, at lower confidence.

### LO-07: purpose_category can be null without being "missing", so VL can never fill it

**File:** `prism/read/parse_application.py:167`, `prism/read/vl.py:484-488`
**Issue:** `classify("purpose_category", "purpose", purpose)` uses the raw purpose *text*. When the text exists but no keyword matches, the field is neither missing nor declared none, so `_targets` excludes it even though the fact is null. Free-text categorization is the case VL would help most.
**Fix:** Pass the derived category (`_purpose_category(...)[0]`) as `parsed`, so an unclassifiable purpose counts as missing.

### LO-08: Every unreadable image counts as a guarantor ID

**File:** `prism/read/classify.py:164-167`, `prism/read/requirements.py:345-347`
**Issue:** Any JPG/PNG below `min_score` becomes `guarantor_id` and counts toward `len(present)`. A photo of an invoice, or the front and back of the same ID, can satisfy a two-guarantor requirement and hide `MISSING_DOC:guarantor_id` for the second guarantor.
**Fix:** Count unverified images at most once, and match readable IDs to distinct guarantors by name when counting.

### LO-09: Caches keyed by `id()` of config objects can serve stale data

**File:** `prism/read/normalize.py:387-397`, `prism/read/old_tricks.py:504-519`
**Issue:** `_nick_index` and `_shell_patterns` key their caches on `id(list)`. After a config reload, which is mtime based, a new list can reuse a freed id, and the old index is returned. This only matters for long-lived processes or tests that rewrite the config.
**Fix:** Key on the settings cache key `(path, mtime_ns)`, or store the compiled data on the frozen config object.

---

_Reviewed: 2026-11-08T07:47:16Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
