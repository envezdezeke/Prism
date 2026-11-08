---
phase: 03-read-the-folder
plan: 04
subsystem: read
tags: [integration-gate, holdout, determinism, nemotron-vl, record-replay, null-fill]
status: complete

requires:
  - phase: 03-read-the-folder
    provides: classifier, parsers, statements, issues, old tricks, compare (03-01, 03-02, 03-03)
provides:
  - tests/test_read_integration.py (12 post-merge checks, synthetic seams plus real tuning deals)
  - recorded Phase 3 deterministic Read baseline and the aggregate holdout verdict
  - prism/read/vl.py Nemotron VL null-fill (modes, record/replay cache, 30-call budget, validators, safe transport), wired behind off/replay/live
  - scripts/vl_smoke.py optional live smoke
affects: [Phase 4/5 (fraud consumption of OLD_TRICK), Phase 6 (NEM-01 general Nemotron client can absorb vl.py), H10 freeze]

actuals:
  tokens: 16200
  tasks: 3
  commits: 4
plan_head_before: f0bb210d7fae8d265304246c2b06a5b2521a3168
plan_head_after: 9ac74987b000d0e7a5828fb03874eb4b8a87488f

tech-stack:
  added: []
  patterns:
    - "VL is self-contained in one module, reached only through read_vl.fill_nulls/fills_for/reset (monkeypatchable), guarded by try/except at the call site"
    - "transport is a module-level function tests replace; the key is read inside it and nowhere else"
    - "conftest autouse fixture keeps NEMOTRON_MODE=off, PRISM_ENV_FILE absent and the cache in a tmp dir for every test"

key-files:
  created:
    - tests/test_read_integration.py
    - prism/read/vl.py
    - tests/test_read_vl.py
    - scripts/vl_smoke.py
  modified:
    - config/read.yaml
    - prism/read/extract.py
    - prism/engine/run.py
    - tests/conftest.py

key-decisions:
  - "VL tag lives in state.features['vl_fills'] (Fact has no source field and the contract forbids extras); Fact.source_doc stays the real application path. Showing 'read by Nemotron VL' in the UI needs an optional Fact.source field, which is Jesse's contract call and was not made."
  - "A retry and a fallback-model attempt each cost one call of the 30-call budget (retry loop lives in vl.py, not the transport), so the cap is a true cap on HTTP requests."
  - "A reply with any key that was not requested is rejected as a whole (prompt-injection hardening); a question that failed once is not repeated in the same run."
  - "conftest forces VL off in every test so a developer's real .env can never cause a network call in the suite."

requirements-completed: [READ-02, READ-04]

coverage:
  - id: D1
    description: "Phase 3 integration gate on the merged tree: tuning issues exact fp 0, statement features real, MISMATCH evidence reaches Move, quiet rule, determinism"
    requirement: READ-04
    verification:
      - kind: integration
        ref: "tests/test_read_integration.py"
        status: pass
      - kind: integration
        ref: "bash scripts/gate.sh --final"
        status: pass
    human_judgment: false
  - id: D2
    description: "VL null-fill fills only parser-null, missing, non-declared-none fields after format and sibling agreement; modes, cache, budget, failure and key hygiene"
    requirement: READ-02
    verification:
      - kind: unit
        ref: "tests/test_read_vl.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "off, replay (empty cache) and live (nothing to fill) give byte-identical scored output on the sample"
    requirement: READ-02
    verification:
      - kind: integration
        ref: "cmp out/vl_off.json out/vl_replay.json out/sub_a.json (identical)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Live Nemotron VL behaviour on real application text"
    requirement: READ-02
    verification:
      - kind: other
        ref: "scripts/vl_smoke.py (2 tuning applications, mask-in-memory)"
        status: pass
    human_judgment: true
    rationale: "A 2-application smoke is a sanity check, not an accuracy measurement; the sample has no field the parsers leave null, so the live path is untested on a real gap beyond this masked smoke"
---

# Phase 3 Plan 04: Integration Gate and Nemotron VL Null-Fill Summary

**The merged deterministic Read layer is verified end to end (tuning facts 90/90, issues exact 10/10 with fp 0, byte-identical reruns, holdout PASSED), and a safe, budgeted, cached Nemotron VL null-fill is wired behind off/replay/live; it makes 0 fills on the sample because the parsers leave nothing null, and changes no byte of the scored output.**

## Final self-score (copied once, Task 3 step 5)

From `bash scripts/gate.sh --final` (exit 0):

```
TUNING facts 90/90 issues_exact 10/10 tp7 fn0 fp0 route 32/40 stage 8/10 flag 7/10 held 7/10 links 8/10
HOLDOUT facts 26/27 issues_exact 3/3 fp0 fn0
TOTAL (13 deals)             116/117 tp9 fn0 fp0 route 40/52 stage 10/13 flag 9/13 held 9/13 links 10/13
history_flags: MISMATCH missed=2 extra=0 must_not_flagged=0
```

pytest 823 passed, 1 skipped (200 s); run 13 deals, 173 files, 183 ticks, 0 errors; validate valid. Holdout is the aggregate only (D-02), read once in Task 1 and once here, identical both times.

## Tuning baseline, before and after (no column dropped)

| | facts | issues_exact | tp | fn | fp | route | stage | flag | held | links |
|---|---|---|---|---|---|---|---|---|---|---|
| Task 1 baseline | 90/90 | 10/10 | 7 | 0 | 0 | 32/40 | 8/10 | 7/10 | 7/10 | 8/10 |
| After Tasks 2-3 (final) | 90/90 | 10/10 | 7 | 0 | 0 | 32/40 | 8/10 | 7/10 | 7/10 | 8/10 |

## Task 1: integration gate (commit 3dff9fa)

- Gate green on the merged tree on the first run; no Read fix was needed (so none is attributed to 03-01, 03-02 or 03-03).
- `tests/test_read_integration.py`, 12 tests. Synthetic: every class except other has a registered parser; six generated statement months round-trip through `prism.fraud.baseline.deposit_features` (months_used equals row count), every `deposit_weekdays` label parses through `parse_weekdays`, annualized equals twice the six-month credit sum, five months give rows but no annualized figure; an EIN mismatch reaches `profile.mismatch_evidence` with a plain-words document label and the Move `info_request_message` carries "your application shows X ... your IRS EIN letter shows Y"; a clean synthetic deal raises no MISMATCH or OLD_TRICK. Real tuning deals only: issues equal the answer key with zero false alarms; ID_MISMATCH, DUP_EIN and SHELL_ADDRESS appear on no tuning deal (none has a gold case); every classified non-other tuning document has a parser result; statement features are real wherever statements exist; each gold MISMATCH deal has evidence for exactly its gold fields and the message carries both values; no MISSING_DOC or MISSING_PAGE is first reported before 30 sim-minutes of quiet (spy on `detect_issues`); two full runs give identical payloads.
- `scripts/read_report.py` on the tuning deals: `deposit_months` on 10 of 10, `deposits_annualized_cents` on 8 of 10 (the other two lack six complete months by design), `mismatch_evidence` on exactly the 2 gold MISMATCH deals.
- Two consecutive CLI runs byte-identical (`cmp`); `prism validate` valid.
- **HOLDOUT CHECK PASSED.** Aggregate: facts 26/27 (limit 3 missed), issues exact 3/3, 0 false alarms, 0 missed gold issues. The one missed fact was not investigated (D-02). fp 0 means none of MISMATCH, ID_MISMATCH, DUP_EIN or SHELL_ADDRESS fired falsely on the holdout deals.

## Task 2: VL module (commit 9e24f64)

`prism/read/vl.py` plus a `vl:` section in `config/read.yaml` (max_calls 30, timeout, retries, caps, ordered `fillable` list; model ids deliberately not in config) and the autouse isolation fixture in `tests/conftest.py`.

- **Targets:** a field is sent only if it is absent from the deterministic facts AND in `ParsedApplication.missing` AND not in `declared_none`; a parser-filled value is never touched; no application means no call. The default generated form says "No specific date", so `needed_by` is never targeted.
- **Input:** application text (capped at 12000 chars) when present, else the image file or up to 3 embedded PDF page images (each at most 4 MB, PNG/JPEG signatures only) as data URLs; neither means no call.
- **Output handling:** strict JSON object (code fences and prose tolerated); a key that was not requested rejects the whole reply. Validators: names 2 to 120 chars no newline, EIN NN-NNNNNNN, amount greater than 0 and at most 1e9, purpose_category and product enum members, term 1 to 600, revenue at least 0, needed_by a real ISO time ending -06:00.
- **Agreement:** legal_name base equals the IRS letter or certificate name; ein equals every IRS/tax/7004 EIN; amount equals the request letter exactly; guarantor_name matches an ID name by the person rule; disagreement rejects that field; no sibling means format alone decides.
- **Modes:** `off` (no call), `replay` (cache only), `live` (cache first, call on a miss, record). Live without a usable key, or with a REPLACE_ME key, is off; unset mode is live with a key else off; env is read at call time (process env first, then the gitignored `.env`, overridable with `PRISM_ENV_FILE`).
- **Budget and failure:** 30 live attempts per run (retries and fallback attempts count), the 31st is skipped; `reset()` restores it; a cache hit is free; a question that failed is not asked again in the same run. HTTP errors, 429 after bounded retries (fixed 2 s then 5 s sleeps), timeouts, empty or malformed replies, and any exception give no fill, never a raise. The primary model falls back once to `NEMOTRON_VL_FALLBACK_MODEL`.
- **Cache:** JSON files under `PRISM_NEMOTRON_CACHE_DIR` (default `out/nemotron_cache`, gitignored), key = sha256 of model, prompt, input digest and sorted fields; stored answers are re-validated at use, so a poisoned entry is ignored.
- **Key hygiene:** the key is read inside `_transport` only and goes only into the Authorization header; errors are reduced to `http 429`, `timeout`, `network URLError` and similar (no headers, no body, no `str(e)`, exception chain suppressed). The sentinel-key test searches logs, stdout, stderr, returned facts, fill tags, exception text and every cache file.
- 79 tests in `tests/test_read_vl.py`; none touches the network.

## Task 3: wiring, gate and smoke (commit 9ac7498)

- `extract_facts` calls `read_vl.fill_nulls` inside try/except after the deterministic facts (any failure returns them unchanged); `extract_features` adds `vl_fills` only when non-empty; `run_sim` calls `read_vl.reset()` first.
- Wiring tests (fake transport through `run_sim`, generated application with the `Product` label removed): off gives no fill; replay with an empty cache gives the same bytes as off; live fills `product` and records; every other extracted field is identical to the off run; replay with the recorded cache and a live rerun give identical bytes with zero transport calls; a failing API (429) leaves the output byte-identical to off; `run_sim` restores an exhausted budget; a crashing VL module leaves `extract_facts` unchanged.
- **VL fill count on the sample: 0.** A dry run over all 13 sample deals with a recording transport saw no targeted field and made 0 calls, even in live mode with a key (the parsers fill every field the form states; the facts the form does not state, such as needed_by, are declared none). So VL cannot change the sample score, and the scored output is byte-identical in off, replay (empty cache) and the Task 1 baseline (`cmp`).
- **Live smoke** (`scripts/vl_smoke.py`, key present, auth worked, no rate-limit failures that blocked it): 2 tuning applications, label and value line of one field masked in memory (nothing written), live mode. Result by field name (correct / wrong / left null of 2 asked): legal_name 0/0/2, ein 0/0/2, amount_requested 0/0/2 (those values appear only in the masked line, so null is the correct answer), purpose_category 2/0/0, product 1/0/1, term_months 2/0/0, guarantor_name 2/0/0, annual_revenue_stated 2/0/0. **0 wrong fills.** The first smoke run made 18 live calls; a rerun after adding the wrong/null counters made 8 more (the first run's 18 included retries and failed attempts that left no cached answer), and the table above is from that rerun. This is a sanity check on 2 applications, not an accuracy estimate.
- **The key never appeared in any output:** not printed by the smoke or the dry run, not in the tests (sentinel search), not in the cache, not in git (`grep nvapi-` over prism, scripts, tests and config finds only the invented sentinel, the REPLACE_ME placeholder and a help string).

## Deviations from Plan

**1. [Rule 3 - Blocking] Test isolation fixture in `tests/conftest.py`**
- **Found during:** Task 2 (the repo `.env` holds a real key and `NEMOTRON_MODE=live`, so any test reaching `extract_facts` could have called the hosted API once Task 3 wired VL in).
- **Fix:** autouse fixture sets `NEMOTRON_MODE=off`, points `PRISM_ENV_FILE` at an absent file and the cache at a tmp dir, and resets the run state. `conftest.py` is not in `files_modified`; the change is test-support only.
- **Committed in:** 9e24f64

**2. [Rule 2 - Missing critical] Whole-reply rejection on unrequested keys, per-run failed-question memory**
- Added beyond the plan text as prompt-injection and budget hardening (T-03-16, T-03-17). **Committed in:** 9e24f64

**Total deviations:** 2 auto-fixed, no scope change. TDD note: the tests were written with the module and run together, one `feat` commit per task rather than separate RED/GREEN commits (the plan asks for one commit per task).

## Authentication gates

None. The live smoke authenticated with the existing `.env` key.

## Hand-off notes

- **Phase 4/5 (not fixed here):** OLD_TRICK issues are not consumed by `prism/fraud`, so the old-trick tuning deal carries `OLD_TRICK:STMT_TAMPER` and `REV_INFLATION` but still scores fraud MISSED. Whether a Read-reported old trick should set `fraud.flagged`/`held` is a Fraud/Move decision.
- **Levers if ID_MISMATCH, DUP_EIN, SHELL_ADDRESS or MISMATCH fire wrongly on the hidden set:** `thresholds.ocr_min_disagreeing_fields`, `shell_address_patterns`, `id_disagreement_also_mismatch`, `revenue_year_offset` in `config/read_issues.yaml`.
- **H10 freeze:** the baseline above is the Phase 3 Read baseline. On the hidden set, mode is `live` when the environment has `NVIDIA_API_KEY`, else silently `off`; a replay cache can be pre-recorded by running the smoke or a live run. Ask whoever runs the hidden set (N9) which of the two applies.
- **Phase 6:** `vl.py` is self-contained with the `.env.example` names so a general Nemotron client can absorb it; VL for classification stays deferred.
- **Suite time** is now about 2 to 3 minutes (the integration file runs the sample twice).

## Known Stubs

None.

## Threat Flags

None beyond the plan's register: T-03-14 (key) mitigated and tested, T-03-15 (documents to a hosted API) accepted as in the plan (zero calls on the sample), T-03-16 to T-03-18 mitigated (strict JSON and validators, hard call cap with timeout and bounded retries, cache re-validation). No packages installed (urllib only).

## Self-Check: PASSED

Created files exist (`prism/read/vl.py`, `tests/test_read_vl.py`, `tests/test_read_integration.py`, `scripts/vl_smoke.py`); commits `3dff9fa`, `9e24f64`, `9ac7498` are ancestors of HEAD; `git rev-list --count f0bb210..HEAD` was 4 when written (includes the interim Task 1 summary commit); `bash scripts/gate.sh --final` exits 0.
