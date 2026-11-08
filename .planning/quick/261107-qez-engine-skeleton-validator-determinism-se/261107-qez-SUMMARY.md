---
phase: 261107-qez-engine-skeleton-validator-determinism
plan: 01
subsystem: engine
tags: [engine, visibility, validator, scorer, cli, contract]
requires: []
provides:
  - arrival-gated deterministic engine skeleton (prism.engine)
  - stub entry points for prism.read, prism.move, prism.fraud
  - python -m prism run | validate | score
  - config/fraud.yaml
affects: [phase-3-read, phase-4-move, phase-5-fraud]
tech-stack:
  added: [pyyaml]
  patterns: [module-attribute calls for monkeypatchable steps, per-deal crash isolation, canonical JSON]
key-files:
  created:
    - config/fraud.yaml
    - prism/cli.py
    - prism/__main__.py
    - prism/engine/{visibility,money,config,state,writer,run,validate,score}.py
    - prism/read/{classify,extract,issues}.py
    - prism/move/{stage,routing,sla}.py
    - prism/fraud/{baseline,graph,signals,decide}.py
    - tests/{conftest,test_visibility,test_engine,test_validate,test_score}.py
  modified:
    - prism/contract.py
    - prism/api/app.py
    - docs/CONTRACT.md
    - tests/test_contract.py
    - pyproject.toml
decisions:
  - "Stub fraud.decide.evaluate already composes build_graph -> compute_signals -> decide, so Phase 5 fills the three bodies only."
  - "Config warnings (missing optional data-pack files) are written to the top-level _errors list, not raised."
  - "Dot-directories are ignored when deriving deals from the shared folder (shared helper run.deal_dirs, also used by validate --folder)."
metrics:
  commits: 3
  plan_head_before: 602f406b217e1f2d50624be6e5f28474b880c478
  plan_head_after: 7838de310ce4aa68cef7ba340da67af18b842583
  tests: "167 passed, 1 skipped (tzset on Windows)"
status: complete
actuals:
  tasks: 3
  commits: 3
---

# Phase 261107-qez Plan 01: Engine skeleton, validator, determinism, self-score Summary

Arrival-gated, deterministic engine skeleton that always writes a contract-valid submission, with the validator, CLI, self-score script and the Q14/Q15 contract fixes.

## Commits

- f47ac0d feat: arrival-gated engine skeleton, config as data, hand-off stubs (Task 1, tracer)
- 0a8034c feat: CLI run/validate, submission validator, determinism and crash-isolation tests (Task 2)
- 7838de3 feat: self-score script against eval/gold.json, Q14 and Q15 contract fixes (Task 3)

(`git rev-list --count 602f406..HEAD` reads 4 because a teammate docs commit b7f87e7 landed on origin and was rebased in between; ours are 3.)

## CLI

```
PYTHONUTF8=1 py -3.13 -m prism run --folder data/participant/shared_folder --arrivals data/participant/sim/arrivals.jsonl --out out/submission.json
PYTHONUTF8=1 py -3.13 -m prism validate out/submission.json --folder data/participant/shared_folder
PYTHONUTF8=1 py -3.13 -m prism score out/submission.json --gold eval/gold.json
```

Results on data/participant: run -> `13 deals, 173 files, 172 ticks, 0 errors`, exit 0; validate -> `valid`, exit 0; score (stub engine, all null/empty) -> `TOTAL (13 deals) 12/117 tp0 fn9 fp0 route 36/52 stage 0/13 flag 9/13 held 9/13 links 10/13`, history_flags missed=2.

## Deviations from Plan

None of substance. Notes: the `score` subcommand was added to cli.py in Task 2 (the plan lists cli.py under Task 3); `run` warns instead of failing when `--folder` is missing (deals then come from arrivals only); `ValidationResult` gained an `io_error` flag so the CLI can return exit 2 for unreadable files and exit 1 for bad JSON.

## Known Stubs

prism/read, prism/move and prism/fraud bodies are intentional stubs (return empty results); Phases 3, 4 and 5 replace them. No UI-facing stubs.

## Threat Flags

None.

## Self-Check: PASSED

Files and commits verified (f47ac0d, 0a8034c, 7838de3 are ancestors of HEAD; fixtures/ untouched; full suite 167 passed).
