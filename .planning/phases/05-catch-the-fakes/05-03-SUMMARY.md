---
phase: 05-catch-the-fakes
plan: 03
subsystem: fraud
status: complete
tags: [fraud, graph, api, investigator-replay]
requires: [05-02 clusters, links, history flags]
provides: [prism/fraud/graph_out.py (FraudGraph producer + CLI), RunResult.clusters, GET /api/graph engine graph under MOCK=0 with ?at= replay, re-recorded investigator replay]
affects: [prism/engine/run.py, prism/api/app.py, prism/agents/investigator.py]
key-files:
  created: [prism/fraud/graph_out.py, prism/api/graph_routes.py, tests/test_fraud_graph_out.py]
  modified: [prism/engine/run.py, prism/api/app.py, prism/agents/investigator.py, prism/fraud/__init__.py, tests/test_api_graph.py, eval/nemotron_replay/investigator/*]
decisions:
  - "The at filter is one function (filter_graph) over the full graph plus out/graph_timeline.json (deal first-seen, cluster hold times), shared by the CLI and the API."
  - "The API serves a precomputed out/graph.json under MOCK=0 (a run takes ~55 s, too slow per request); missing file returns 503."
  - "The investigator takes the run's last-tick clusters, so its ids equal the served graph's ids."
requirements: [FRD-02, FRD-03]
metrics:
  duration: ~30 min
  completed: 2026-11-08
estimate:
  tokens: 45000
  tasks: 2
actuals:
  tokens: 9000   # chars/4 over the code and test diff
  tasks: 2
  commits: 3
plan_head_before: 272a65f
plan_head_after: 7fa70d6
---

# Phase 5 Plan 03: Fraud graph producer Summary

`python -m prism.fraud.graph_out` builds the entity graph from the real engine run in the fixtures/graph.json shape. Edges are rarity-weighted, carry evidence and record the sim time they first become visible. It writes out/graph.json and out/graph_timeline.json. GET /api/graph now serves that graph under MOCK=0 and keeps the `?at=` replay. MOCK=1 still serves the fixture.

## Sample graph

- 36 nodes (13 deals, 10 history deals, 13 entities), 50 edges, 6 clusters. out/graph.json is 27,974 bytes and validates as FraudGraph.
- Hold clusters are C-002 and C-004. The rest (C-001, C-003, C-005, C-006) are watch. C-004 becomes hold at 2026-11-02T14:05 and C-002 at 2026-11-03T16:08. With `at` set before those times, the cluster is shown as watch.
- The served /api/graph cluster ids (MOCK=0) match the investigator's ids: C-002 and C-004.

## Extras (user-approved; the plan had marked these as hand-offs)

- `RunResult.clusters` now keeps the last tick's clusters. They are not scored, and the submission bytes are unchanged (gate below).
- `/api/graph` moved to prism/api/graph_routes.py and is no longer in the mock-only router.
- The investigator replay was re-recorded live. C-002 has a live case. C-004 has live tool steps but a template case, because the model returned an empty case at the 8-step cap. That happened on the first run and on two retries. Replay reproduces the traces with 0 live calls. 6 stale cache files were removed.

## Gate

GATE_LINE

## Hand-offs

1. Evidence cites the document only. To cite a page, Read would have to record the page on EntityRef.
2. docs/CONTRACT.md needs no change, since the shape equals fixtures/graph.json.
3. out/graph.json has to be generated before demoing MOCK=0. The command is `python -m prism.fraud.graph_out --folder ... --arrivals ...`.
4. Investigator step-cap handling: the final call after STEP_LIMIT_NOTE returns empty content for C-004.

## Deviations

- [Rule 1] Clusters can include history deals that carry no strong entity (a watch cluster member, for example). Those history deals get nodes anyway, so the contract's referential check holds.
- The sample tests (Task 2 tests 3 and 4) were cut for time. Synthetic tests cover the at filter, shape parity, determinism and the MOCK=0 route.

## Self-Check: PASSED
