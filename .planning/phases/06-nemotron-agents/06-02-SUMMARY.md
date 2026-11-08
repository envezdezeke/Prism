---
phase: 06-nemotron-agents
plan: 02
subsystem: agents
tags: [nemotron, investigator, tool-loop, replay]
requires: [06-01]
provides: [prism.agents.investigator, prism.agents.tools, prism.agents.routes, eval/nemotron_replay/investigator]
affects: [prism/api/app.py]
key-files:
  created: [prism/agents/tools.py, prism/agents/investigator.py, prism/agents/routes.py, tests/test_agents_investigator.py, eval/nemotron_replay/investigator/]
  modified: [prism/api/app.py]
decisions:
  - "/api/investigator and /api/redteam live in prism/agents/routes.py; do not re-add them to the mock-only router in app.py (Phase 4 rewire must keep the include_router line)"
status: complete
actuals:
  tasks: 3
  commits: 3
---

# Phase 6 Plan 02: NEM-03 fraud investigator Summary

An OpenAI-format tool loop runs on ChatClient with 5 read-only tools (cluster_summary, deal_entities, entity_deals, history_deal, deal_documents). It takes at most 8 steps and at most 5 clusters, and reads text-JSON tool calls when the model gives no native ones. When Nemotron is off, fails or misses the replay cache, it falls back to the template case, built from the engine's own evidence. The trace is served on /api/investigator/{id} under MOCK=0.

## Commits
- f27c5fa feat(06-02): agent routes and the app.py include
- 64166d9 feat(06-02): tools, investigator loop, CLI and tests (Tasks 1 and 2 code)
- a171fa1 chore(06-02): recorded replay cache (8 files)

## Verification
- test_agents_investigator, test_contract, test_api_graph and test_agents_client: 114 passed. The wider scoped run (engine, VL, contract, agents): 242 passed. test_two_runs_are_byte_identical passes.
- Sample CLI in off mode: TRACES_OK 2.
- Live recording **succeeded**: 2 hold clusters (C-002 and C-004, the engine clusters from Phase 5), 8 live calls.
  - C-002: 5 steps, the case is written by Nemotron.
  - C-004: 8 steps (hit the cap). The final no-tools call returned nothing usable, so the case is the template text and the 8 Nemotron-chosen steps are kept.
- Replay: live calls 0, cache hits 8, REPLAY_MATCHES 2. No cache file contains a key.

## Re-record (required once Phase 5 lands)
When this was recorded, prism/fraud had uncommitted Phase 5 changes (baseline.py, rarity.py, signals.py). Changed evidence changes the messages, so replay would miss and fall back to template cases. Re-record with:

    NEMOTRON_MODE=live python -m prism.agents.investigator --folder data/participant/shared_folder --arrivals data/participant/sim/arrivals.jsonl --out out/agents/investigator.json
    git add eval/nemotron_replay/investigator

Stale cache files can be deleted first.

## Serve it
    NEMOTRON_MODE=replay python -m prism.agents.investigator --folder data/participant/shared_folder --arrivals data/participant/sim/arrivals.jsonl
    MOCK=0 uvicorn prism.api.app:app   ->  GET /api/investigator/C-002

The cluster ids on the sample are C-002 and C-004, not C-001. The UI must take ids from the graph's clusters.

## Deviations
- The Task 1 and Task 2 code was written in one pass and committed as routes/app (f27c5fa) plus tools/investigator/tests (64166d9). It was not split by task.
- test_step_cap: its second sub-case points PRISM_AGENT_CACHE_DIR at a fresh dir so it does not replay the first sub-case.
- entity_deals history ids = graph carriers ∪ baseline.deals_with(kind, value).

## Self-Check: PASSED
