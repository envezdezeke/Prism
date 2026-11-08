---
phase: 05-catch-the-fakes
plan: 02
subsystem: fraud
tags: [calibration, F3, F5, red-team-R2, red-team-R4, red-team-R8]
requires: []
provides:
  - "data-relative calibration with a theoretical tau floor (calibrate.py)"
  - "F3 categorical lookalike with a stable-account rule; shared f5_bits helper (signals.py)"
  - "rank-based measurement split with --holdout-fraction (eval_baseline.py)"
affects: [05-03, 05-04, 05-05]
tech-stack:
  added: []
  patterns: ["documented module constants instead of config keys (MIN_CLEAN, F3_STABLE_ACCOUNT_SHARE)"]
key-files:
  created: [tests/test_fraud_signals.py]
  modified:
    - prism/fraud/calibrate.py
    - prism/fraud/signals.py
    - prism/fraud/eval_baseline.py
    - tests/test_fraud_eval.py
    - tests/test_fraud_baseline.py
decisions:
  - "A tau is max(empirical percentile, -log2(1 - q)); an empty clean set still gives F3 the floor"
  - "F5 = max(round, min(conc, kl)) in one helper used by the live score and the clean-set percentile"
status: complete
commits: 3
plan_head_before: 99e8460
plan_head_after: 6507792
actuals:
  tokens: 45000
  tasks: 3
  commits: 3
---

# Phase 5 Plan 02: Calibration, F3 and F5 Summary

Calibration now comes from the history that ships (no config dates, every tau floored at the theoretical value), F3 stops firing on honest vendors that carry a different last four on each deal, and F5 needs a high round share or a weekday pattern that is both concentrated and unlike history.

## What changed per task

1. **Calibration (7ca9f09).** `clean_ids` returns every funded, label-none, current or paid-off deal of any date; with fewer than `MIN_CLEAN = 20` it falls back to every label-none deal. `compute_thresholds(..., as_of=None)` keeps its type; `as_of` is measurement only. `tau = max(percentile, floor_bits(q))`; F3 with an empty clean set is the floor (4.3219 at q 0.95), F5 stays None only without a reference sample. `train_end`, `test_start`, `test_end` are no longer read by any real-run path.
2. **F3 and F5 (653ab7d).** F3 fires on a name or legal-suffix variant of a frequent history vendor; a remit-account change counts only where the group's accounts are stable (`F3_STABLE_ACCOUNT_SHARE = 0.8` over at least `min_vendor_deals` accounts), both for the incoming vendor and for counting history variants. `f5_bits(stats, reference)` returns `max(round, min(conc, kl))` and the winning component; `score_f5` and `calibrate` both use it; `F5Result.stat` is "round" or "weekday".
3. **Rank split (6507792).** `build_report(..., holdout_fraction=0.36)` splits by rank (train = first `ceil((1 - f) * N)` in (date, id) order), thresholds from the train baseline with no date filter; meta carries `holdout_fraction`, `n_train_deals`, `n_test_deals`, `train_cutoff`. CLI `--holdout-fraction` must be in (0, 1) else exit 2. Date-shift identity, rank split and validation tests added.

## Numbers, before and after

Whole shipped history (257 deals), `build_baseline(...).calibration`:

| | n_clean | tau F3 | tau F5 | fire rate clean F1 / F3 / F5 |
|---|---|---|---|---|
| before | 104 | 4.4263 | 5.0670 | 38.5% / 12.5% / 5.8% |
| after | 176 | 4.3219 | 4.3219 (floor) | 38.6% / 2.3% / 4.5% |

Synthetic bench, proxy mode (`--menus core,redteam`), before (SHARED section 5) and after:

| | before | after |
|---|---|---|
| ring deals held | 26.5% (281/1060) | 34.1% (361/1060) |
| twins held | 0.08% (1/1200) | 0.0% (0/1200) |
| twin watch friction | 50.8% | 49.5% |
| background held | 0/10300 | 0/10300 |
| R4 date-shifted history | 0% | 100% |
| R1 / R2 / R3 | 0 / 75 / 100 | 0 / 75 / 100 |
| T1 / T2 | 44.4 / 50.8 | 44.4 / 50.8 |
| T3 to T8 | 0 | 0 |

No per-trick number went down. The 70% ring bar is not reached yet (F2, F4 and the cluster rule are other plans); twins stay well under 5%.

`eval_baseline` on the shipped history (default holdout 0.36): cut date 2026-07-01 (165 train, 92 test deals); tau F3 4.3219, F5 4.3219 (floor); clean-set fire rates F1 29.5%, F3 0.0%, F5 4.8%; test-period good deals 71, fired F1 24, F3 1 (1.4%), F5 2 (2.8%); `false_flag_ids` = [H-2609-008] (a ring member labelled current, which is in `history_flags`); scheme link 1 of 1. Before (date-bound split, 164 train, 93 test): F1 29.8%, F3 2.9%, F5 5.8% on clean; test F3 8 fired (11.1%), F5 3, false flags 1 of 72. These are not the same population (rank split versus date split, different clean set size and floor), so the rows are not a like-for-like comparison. Two runs are byte-identical (`cmp`).

V3 signal-level trap: none of the 20 `history_must_not_flag` ids reaches F1+F3+F5 (2 of them are in the test period). Decide-level assertion arrives with 05-04.

V4 gate (run + validate + score on the sample): valid; fraud columns flagged 9/13, held 9/13, links 10/13, history_flags missed 2, must_not_flagged 0. Same as the baseline in SHARED section 5 (Read is still a stub / in flux), so the score did not go down.

Tests: the plan-owned files pass (fraud_eval 28, fraud_signals 12, fraud_baseline, fraud_math, engine, fraud_decide: 115 passed together).

## Deviations from Plan

**1. [Finding, not fixed] Sat,Sun and Mon-Thu still fire F5 through the weekday component.**
The plan's truth says merely-rare labels Tue-Sun, Mon-Thu, Sat,Sun and Mon-Fri,Sun with ordinary round share do not fire. With the prescribed statistic `max(round, min(conc, kl))` only the spread-out labels (Tue-Sun, Mon-Fri,Sun) stop firing (conc bits 0). Sat,Sun is a two-day pattern, structurally the same as the Mon,Thu ring pattern, and Mon-Thu is also more concentrated than any Mon-Fri / Mon-Sat deal, so both fire (about 5.9 bits against tau 4.32 on a 60-deal reference). No weekday statistic can separate "honest weekend market" from "two-day ring pattern" using a label alone. I did not invent a different statistic. Tests assert what holds (Tue-Sun and Mon-Fri,Sun stay quiet, Mon,Thu and Sat,Sun fire through the weekday part, Mon-Fri at round 1.0 fires through round alone). Mitigation belongs with the R8 fix of reading real deposit dates (Read) and with F5 only voting as one of several families.

**2. [Rule 1 - test semantics] `test_empty_clean_set_gives_no_tau`** used a charged-off label-none deal; under the specified fallback that deal now counts, so the test uses an `old_trick` label instead.

**3. [Process] Shared-tree incident during `git pull --rebase --autostash`.** Origin carried 48 commits and a tracked `.planning/state.json` that blocked the pull; I moved the local copy aside, pulled, and restored it. The autostash then conflicted on `prism/fraud/decide.py` (05-01's work in progress). I restored 05-01's `decide.py` and `config/fraud.yaml` byte-for-byte from the stash (`git checkout stash@{0} -- ...`, then unstaged); the stash entry `stash@{0}` is still there for 05-01/the orchestrator to drop. My commit 653ab7d also picked up one hunk in `tests/test_fraud_baseline.py` that is 05-01's (`test_engine_output_unchanged_decide_is_stub` renamed to `test_engine_output_lone_shared_account_is_watch_only`), because it was already in the working tree when I staged that file. It passes and is harmless. I did not pull again before the last commit (3 more upstream commits touching only planning files and `tests/test_fraud_sample.py`), to avoid another stash round trip on the shared tree.

## Cross-plan failures

Full `pytest -q` at the end: 4 failures in `tests/test_fraud_sample.py` and about 120 in `tests/test_read_*.py` (Read tuning/extraction, for example `KeyError: 'legal_name'`). The `test_fraud_sample.py` failures reproduce with my F3/F5/calibration changes removed, so they are not from this plan; Read is being edited by Ezekiel. Upstream has since changed `tests/test_fraud_sample.py`.

## Known Stubs

None added.

## Threat Flags

None.

## Self-Check: PASSED

Commits 7ca9f09, 653ab7d, 6507792 are on main; `tests/test_fraud_signals.py` exists; no config file edited by this plan; `.planning/state.json` never staged.
