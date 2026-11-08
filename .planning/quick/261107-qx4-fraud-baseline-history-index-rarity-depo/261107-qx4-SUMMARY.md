---
phase: 261107-qx4-fraud-baseline-history-index
plan: 01
subsystem: fraud
tags: [fraud, baseline, rarity, F1, F3, F5, calibration, time-split]
requires:
  - phase: 01-engine-skeleton
    provides: pinned stubs for build_baseline, build_graph, compute_signals, FraudConfig
provides:
  - history index with leave-one-out queries (FRD-01)
  - entity graph with canonical keys and rarity weights (FRD-02)
  - F1, F3, F5 signal math in bits (FRD-03 groundwork only)
  - startup calibration of tau_F3 and tau_F5 on Baseline.calibration
  - python -m prism.fraud.eval_baseline time-split report
affects: [phase-5-fraud-decide, phase-3-read-integration]
tech-stack:
  added: []
  patterns: [stdlib csv plus difflib only, leave-one-out via id sets, never-raise loaders with warning strings]
key-files:
  created:
    - prism/fraud/canon.py
    - prism/fraud/rarity.py
    - prism/fraud/calibrate.py
    - prism/fraud/eval_baseline.py
    - tests/test_fraud_synth.py
    - tests/test_fraud_math.py
    - tests/test_fraud_baseline.py
    - tests/test_fraud_eval.py
  modified:
    - prism/fraud/baseline.py
    - prism/fraud/graph.py
    - prism/fraud/signals.py
    - prism/fraud/__init__.py
    - config/fraud.yaml
key-decisions:
  - "F1 fires on any strong shared entity (no percentile); its misfire rate is measured, not tuned"
  - "tau comes from percentiles in config, computed at startup, stored only on Baseline.calibration"
  - "Additive config keys are read from cfg.raw by FraudParams.from_config; config.py untouched"
requirements-completed: [FRD-01, FRD-02]
status: complete
duration: ~75 min
completed: 2026-11-07
commits: 3
plan_head_before: 51d376b824e54f40b9f33fc9d5aba15e77eeb023
plan_head_after: e440e2ce696266f86a5b81da890f5e839794ca17
actuals:
  tokens: 26000
  tasks: 3
  commits: 3
---

# Phase qx4 Plan 01: Fraud baseline, history index, rarity, deposit features and calibration Summary

**History-only Phase 5 half: canonical history index, entity graph with rarity weights, F1/F3/F5 in bits of surprise, startup percentile calibration, and a byte-reproducible time-split report (stdlib plus PyYAML only).**

The `commits: 3` above counts the three task commits; this SUMMARY is a fourth commit on top.

## What was built

**Task 1 (tracer, commit 68f6e8d): F1 end to end.**
- `canon.py`: idempotent per-kind canonical keys (casefold, periods and apostrophes dropped, "&" to "and", phone digits, order-insensitive expanded addresses, alphanumeric accounts, name split into base plus one legal suffix).
- `rarity.py`: `FraudParams.from_config` (typed fields plus additive keys from `cfg.raw`, `ConfigError` on bad values) and `p_hat`, `surprisal`, `is_strong`, `outcome_discount`.
- `baseline.py`: CSV to canonical index, `df`, `n_effective`, `deals_with`, `entity_stats`, `value_counts`, `producer_counts`, `ordered_ids`, `from_rows`; every loader problem is a warning, never an exception.
- `graph.py`: re-canonicalizes every `EntityRef`; `profiles`, `entity_deals`, `entity_weights` (df, links, bits, strong).
- `signals.py`: `score_f1` (pair score `w * omega * I`, max over partners) and `compute_signals`.

**Task 2 (commit df6f882): F3, F5, deposit features, shared math.**
- `rarity.py`: `percentile`, `upper_tail_bits`, `fit_beta_mom`, `shrunk_share`, `entropy_bits`, `kl_bits`, `parse_weekdays`, `edit_distance`, `token_set_similarity`, cached `base_similar`.
- `baseline.py`: `DepositFeatures`, `deposit_features`, vendor groups (frequent bases, modal form, similar-base observations), `Calibration`, leave-one-out round shares and pooled weekday mass.
- `signals.py`: `score_f3` (bits `-log2((n_pat+1)/(n_vend+1))`), `f5_statistics` (round, conc, kl), `score_f5`; `compute_signals` emits F1, F3, F5 sorted by (folder, family). `fired` for F3/F5 is `bits > 0 and tau is not None and bits >= tau`.

**Task 3 (commit e440e2c): calibration and report.**
- `calibrate.py`: `clean_ids`, `compute_thresholds` (two passes, leave-one-out, interpolated percentile from config, clean-set fire rates); `build_baseline` attaches the result via a lazy import.
- `eval_baseline.py`: `python -m prism.fraud.eval_baseline` replays Jul to Oct 2026 in (date, id) order against strictly earlier deals, tau and F5 reference from the train period only, writes `baseline_eval.json` and `baseline_eval.md` (sorted keys, LF, no timestamps), optional `--gold` scheme-link check, returns 2 on a missing history dir.

## Verification

- Full suite: `215 passed, 6 skipped` (baseline at planning: 167 passed, 1 skipped; this worktree has no `data/`, so data-dependent tests skip, plus the real-history smoke test when `PRISM_HISTORY_DIR` is unset).
- `tests/test_engine.py` pinned surface, determinism/AST guard and literal guard pass; `decide()` untouched, `evaluate` still returns an empty `FraudOutcome`.
- Literal gate: no `H-` plus 4 digits anywhere in `prism/fraud` or the new tests. Scope gate: only `prism/fraud/`, `tests/test_fraud_*.py`, `config/fraud.yaml` and this quick dir changed since 51d376b.
- `python -m prism run` on the sample (using the main checkout's data) completes: 13 deals, 0 errors, so the real history now loads and calibrates inside `run_sim` without crashing.

## Real-history smoke (aggregates only, Jul to Oct 2026 replay)

Read-only on the participant history; the per-deal report with ids stayed in the scratchpad, not in git. Two runs produced byte-identical JSON and markdown.

| item | value |
|---|---|
| history deals / train deals (to train_end) | 257 / 164 |
| load warnings | 0 |
| clean calibration deals (n_clean) | 104 |
| tau F3 (95th pct) | 0.0 bits (3 of 104 clean deals have a lookalike, all 4.17 bits, so the interpolated 95th percentile is 0 and F3 fires on any lookalike with bits > 0) |
| tau F5 (95th pct) | 5.067 bits |
| F5 reference sample sizes (round, conc, kl) | 104 each |
| fire rate on clean set, F1 / F3 / F5 | 29.8% / 2.9% / 5.8% |
| test deals / good test deals | 93 / 72 |
| fired among good test deals, F1 / F3 / F5 | 24 (33.3%) / 8 (11.1%) / 3 (4.2%) |
| good test deals with at least one family fired | 25 |
| false flags among good (F1 and F3 and F5 all fired; lower bound, F2 and F4 missing) | 1 of 72 |
| non-good test deals (21) with at least one of the three fired | 7 (F1 7, F3 4, F5 2 firings) |
| test deals that have an F1 partner among earlier deals | 31 |

Where F1 fires on clean deals (strong entities counted, train baseline): guarantor 12, vendor 17, phone 3, preparer 3, remit account 2, producer 2, registered agent 1. Guarantor repeats and shared equipment vendors dominate: honest repeat borrowers and vendors are the F1 false-positive source. F3 firings on clean history are mostly remit-account variants of a frequent vendor.

## Discretion choices

- F1 type weights: remit_account, preparer, registered_agent, phone, guarantor 1.0; vendor and pdf_producer 0.5; address and bank 0.25. `outcome_beta` 0.5. Default weight for an unlisted kind 1.0.
- F1 has no percentile: it fires on any strong shared entity (rho under 2 percent, links at least 2), because `tests/test_engine.py` pins `FraudConfig.percentiles` to F2..F5 and F1 is mandatory for a hold.
- Ampersand becomes the word "and" in canonical text, so "A & B" equals "A and B".
- F3: `min_vendor_deals` 3, `min_similarity` 0.8, `max_edit_distance` 2. A lookalike differs in base spelling, suffix, or a non-empty remit account; an empty account never counts as different. `n_vend` is all history vendor observations.
- F5: `dirichlet_alpha` 0.5; prior-strength fallback `PRIOR_STRENGTH = 10` (a documented module constant, not a bit threshold) when the method-of-moments fit is degenerate; bits are the maximum over round, conc, kl.
- Deposit features need `n > 0` and at least one usable month, else None.
- Not indexed: `preparer_firm`, `registered_agent_address`, `ein`, SSN and licence columns.

## Deviations from Plan

**1. [Rule 1 - Bug in plan arithmetic] Tracer history size 150, not about 40.**
- **Found during:** Task 1 test run.
- **Issue:** with N = 40 a df-2 entity is 5%, above the 2% rarity fraction, so it is not strong; the plan's tracer could never fire F1 as specified.
- **Fix:** the tracer history is 150 deals (2/150 is 1.3%, under rho); the common preparer still has 30 of 150 users and stays non-strong. Hand-computed expectations updated to `log2(151/3)` and `log2(151)`.
- **Files modified:** tests/test_fraud_baseline.py
- **Commit:** 68f6e8d

**2. [Interface detail] F5Result fields.** The plan names `F5Result(bits, stat, round, conc, kl, z, evidence)`; implemented as `bits, stat, stat_bits (dict), z (dict), evidence`, same information, dict-valued.

**3. [Test location] Percentile-moves-tau test** uses `dataclasses.replace(params, percentiles=...)` instead of writing a temporary yaml copy; equivalent coverage, no temp config file.

No other deviations. No package installs. No auth gates.

## Known Stubs

None. `decide()` remains the pre-existing stub by design (Phase 5 proper).

## Hand-off notes (work this plan was not allowed to do)

1. Phase 3 (Read) must put a list of mappings with keys `deposit_count`, `pct_deposits_multiple_of_100`, `deposit_weekdays` into `DealState.features["deposit_months"]` (or the integrator writes an adapter). `EntityRef` values need not be pre-canonicalized because `build_graph` re-canonicalizes them; kinds must be `prism.contract.EntityKind` values (`vendor` and `remit_account` are needed for F3).
2. `decide()` is still a stub: the hold rule (F1 plus at least 2 of F2 to F5), stickiness, clusters, `history_flags`, `linked_deals` and evidence-to-Fraud-block mapping are Phase 5 proper. `compute_signals` already returns F1, F3, F5 signals with `fired` set. Before wiring the hold rule, read the smoke table: F1 alone fires on about 30 percent of clean deals (guarantor and vendor repeats), so the "F1 plus two more" structure is carrying the specificity, and a tighter F1 (for example a pair-score floor, or dropping vendor and guarantor from the strong set) is a Phase 5 design decision that needs F2 and F4 numbers first.
3. M13 asks for computed thresholds to be written into the run output for audit: that needs an engine change (run.py or writer.py); the data is ready on `baseline.calibration` (tau, reference sizes, clean-set fire rates, percentiles).
4. `FraudConfig` in prism/engine/config.py does not expose the new additive keys as typed fields (they are read from `cfg.raw` by `FraudParams.from_config`); a typed loader is an optional engine-side tidy-up. Invalid additive values raise `ConfigError` at `build_baseline` time, i.e. at run startup.
5. A `prism eval-baseline` subcommand in prism/cli.py delegating to `prism.fraud.eval_baseline.main` was not added (cli.py out of scope); until then run `python -m prism.fraud.eval_baseline`.
6. pandas is not declared in pyproject.toml; nothing here needs it, and PyYAML is the only third-party import used.
7. `compute_signals` evaluates F1 against history plus the other current deals, but F3 and F5 have no current-deal linkage; F3 `deals` is just the folder. If Phase 5 wants F3 clusters across current deals, that is new work.
8. Startup cost: `build_baseline` now calibrates (leave-one-out over about 100 clean deals); on the participant history the whole report runs in a few seconds and `run_sim` startup is not noticeably slower.

## Threat Flags

None. No new network endpoints, auth paths or schema changes; `eval_baseline` only writes two fixed filenames inside the user-supplied `--out-dir`.

## Self-Check: PASSED

All created files exist, commits 68f6e8d, df6f882 and e440e2c are ancestors of HEAD, and `pytest -q` passes (215 passed, 6 skipped).
