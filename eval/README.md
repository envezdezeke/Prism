# Golden labels (`eval/gold.json`)

The answer key for the 13 sample deals. The self-score script compares the engine's `out/submission.json` against it, field by field. **Owner: Jesse. Due Sat 20:00 CT.** Push partial work as you go and set each deal's `status`.

## Label blind

Label from the raw files in `data/participant/shared_folder/` (plus `sim/assignments.json`, `contacts/teams.json`, `rules/`). **Do not read** the expected issues in `.planning/ROADMAP.md` (Phase 3 success criteria) or `.planning/PROJECT.md`'s ring analysis first. Otherwise the score checks our research against itself. Afterwards we diff your labels against the research and talk through every disagreement.

Use the judgment calls in `docs/DETAILS_CHECKLIST.md` §8 (J1–J20) wherever they apply.

## Shape, per deal

The deal keys are the exact folder names; they're already in the file. Don't rename them.

| Key | What to write | How it is scored |
|---|---|---|
| `status` | `todo` → `draft` → `done` | Only `draft`/`done` deals are scored |
| `extracted` | The 9 facts, exactly as `SUBMISSION_FORMAT.md` wants them: `ein` as `12-3456789`, money as a plain number (`246000`), `needed_by` as `2026-11-06T15:00-06:00` or `null` | Exact match after trimming and case-folding strings. Numbers are exact |
| `extracted_accept` | Optional. `{"field": [other acceptable values]}` when there is more than one fair answer (e.g. a revenue range, J7) | A match on any listed value counts |
| `sources` | Optional. `{"field": "file name it came from"}` | Not scored; helps debugging |
| `issues` | Every issue that should be **open at the end of the sample week** (J14), using only the allowed labels (`MISSING_DOC:…`, `MISSING_PAGE:…`, `MISMATCH:…`, `OLD_TRICK:…`) | Set comparison: each missing one is a miss, each extra one is a false alarm |
| `issues_optional` | Issues where raising or not raising both seem defensible | Neither counted nor penalized |
| `routing` | Who each sign-off goes to (a `teams.json` id). Use `null` for a gate the deal should never reach (held, declined, stuck on a missing doc) | Exact match per gate |
| `final_stage` | The furthest stage the deal should reach by end of week **if every human approves promptly** | Exact match |
| `fraud.flagged` / `fraud.held` | `true` only for deals that should be held (ring members, OLD_TRICK hits per J17) | Most heavily weighted: a false flag costs a lot |
| `fraud.latest_ok_stage` | The latest stage at which a hold still counts as on time. `null` if not flagged | The engine's `stage_at_flag` must be at or before it |
| `fraud.linked_deals` | Other current folders and `H-…` history ids in the same scheme | Set comparison |
| `notes` | Anything a reviewer should know ("Bob = Robert on the ID, not a mismatch") | Not scored |

## Top level

| Key | What to write |
|---|---|
| `history_flags` | `H-…` ids of history deals in the same scheme as the current ring |
| `history_must_not_flag` | History ids that look suspicious but are clean: the false-flag traps. Flagging any of them is penalized |

## Valid values (copied from `SUBMISSION_FORMAT.md`)

- **stage:** `Intake`, `Credit`, `Committee`, `Product`, `Committed`, `Closed`
- **purpose_category:** `working_capital`, `equipment`, `inventory`, `payroll`, `expansion`, `refinance`
- **product:** `Term Loan`, `Equipment Loan`, `Revolving Line of Credit`, `Working Capital Loan`
- **issue docs:** `application`, `guarantor_id`, `certificate_of_formation`, `ein_letter`, `bank_statement_YYYY-MM`, `financial_statements`, `tax_return`, `equipment_quote`
- **mismatch fields:** `legal_name`, `ein`, `amount_requested`, `guarantor_name`, `guarantor_dob`, `guarantor_address`, `annual_revenue`, `bank_balance`
- **old tricks:** `STMT_TAMPER`, `REV_INFLATION`, `ID_MISMATCH`, `DUP_EIN`, `SHELL_ADDRESS`

## Example (made up, not a sample deal)

```json
"Example Widgets": {
  "status": "done",
  "extracted": {
    "legal_name": "Example Widgets LLC", "ein": "12-3456789", "amount_requested": 120000,
    "purpose_category": "equipment", "product": "Equipment Loan", "term_months": 60,
    "guarantor_name": "Jane Q. Example", "annual_revenue_stated": 1500000, "needed_by": null
  },
  "extracted_accept": {"annual_revenue_stated": [1450000]},
  "sources": {"ein": "IRS letter CP575.pdf"},
  "issues": ["MISSING_DOC:bank_statement_2026-06"],
  "issues_optional": [],
  "routing": {"credit_decision": null, "committee_approval": null, "commitment_signoff": null, "funding_release": null},
  "final_stage": "Credit",
  "fraud": {"flagged": false, "held": false, "latest_ok_stage": null, "linked_deals": []},
  "notes": "Stuck at Credit until June statement arrives; no credit_decision on an incomplete file."
}
```

Check the file is valid JSON before pushing: `python3 -m json.tool eval/gold.json > /dev/null` (Mac) or paste it into any JSON validator.

## Synthetic fraud deals (`synth.py`, `run_synth.py`)

Eval tooling for the fraud model (MODEL_DESIGN M5, M15, M16, M21). Generates fake deals from `trick_menu.yaml` (8 trick families x 3 strengths, plus honest "twins") and measures how the fraud pipeline treats them. `trick_menu_redteam.yaml` adds four extra families from the red team (ring with no equipment vendor, a mule deal inside a ring, entity values typed differently, date-shifted history). Seeded and deterministic: same menu + same history = identical cases and an identical report. Only fake values are written (made-up names, `555-01xx` phones, `00-7…` EINs, `S-`/`X-` ids); the real history is read only for the clean base rows, the percentile anchors and a "never collide" list. Nothing here tunes a weight or threshold.

```
PYTHONUTF8=1 .venv/bin/python eval/run_synth.py                      # core menu, both measurements, ~15 s
PYTHONUTF8=1 .venv/bin/python eval/run_synth.py --menus core,redteam # add the red-team families
PYTHONUTF8=1 .venv/bin/python eval/run_synth.py --max-cases 2        # quick smoke run
PYTHONUTF8=1 .venv/bin/python eval/synth.py --out-dir out/synth      # just dump the fake history-schema CSVs
```

Options: `--mode engine|proxy|both`, `--history-dir DIR` (default `PRISM_HISTORY_DIR` or the data pack), `--out-dir` (default `out/`). Output: `out/synth_report.json` and `out/synth_report.md`.

**Bypassing Read.** Each fake deal is injected as `DealState.entities` (raw entity values) plus `features["deposit_months"]` (six monthly rows), which is exactly what `prism.read` will leave behind. Cases replay one arrival at a time on a simulated clock (each new arrival ages the earlier deals one stage, so "earliest hold stage" means something). Two measurements are reported side by side:

- **engine**: calls `prism.fraud.decide.evaluate(states, baseline, cfg, now)` and reads `FraudOutcome.per_deal[folder]` (`held`/`flagged`, `stage_at_flag`) and `FraudOutcome.clusters` (`tier == "watch"`). Holds are sticky across arrivals. While `decide()` is a stub this is ~0% everywhere. This is the number to re-run as `decide.py` is built.
- **proxy**: the documented hold rule (F1 plus `hold_min_additional` of the built families F3/F5) applied directly to the signal functions. A reference for what `decide()` should reach.

Per trick the report gives ring deals held %, watch %, held by strength, twin false-hold % (target <= 5%), twin watch % (friction), and the earliest hold stage. Blind-spot cells are listed but excluded from the 70% bar. Old-rule cells (T8) and `history_flags` are not measurable until the known-checks path and `decide()` exist. Tests: `tests/test_eval_synth.py`.
