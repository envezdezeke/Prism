# Prism API contract

This is the contract between the engine (Ezekiel) and the UI (Jesse). Every UI endpoint has a Pydantic model in `prism/contract.py` and a JSON fixture in `fixtures/`. The UI builds against the mock server now and switches to the real engine later with no shape changes.

**Change rule:** change the Pydantic model in `prism/contract.py`, regenerate the fixture (run `python -m prism.derive` for the derived ones: `deals.json`, `submission.json`, `alerts.json`; edit the others by hand), run `pytest -q`, then tell the other person. The UI never reads a field the contract does not define. Models reject unknown fields on purpose.

## Run the mock API

```
pip install -e ".[dev]"
MOCK=1 python -m uvicorn prism.api.app:app --port 8000
```

On Windows PowerShell, set the variable first: `$env:MOCK=1`. The API is at http://localhost:8000, Swagger UI at http://localhost:8000/docs, and the schema at `/openapi.json`. The Vite dev origin http://localhost:5173 is allowed by CORS.

`MOCK` unset behaves as `MOCK=1` until the engine is wired. `MOCK=0` makes every `/api` route return 503 `engine not wired yet` (docs stay up). POSTs in mock mode return a plausible response and store nothing.

Tip: generate TypeScript types from `/openapi.json` (for example with `openapi-typescript`).

## Endpoints

| Method | Path | Request body | Response |
|---|---|---|---|
| GET | `/api/deals` | none | `list[DealSummary]` |
| GET | `/api/deals/{folder}` | none | `DealDetail` (404 `unknown deal`) |
| GET | `/api/clock` | none | `Clock` |
| POST | `/api/clock/advance` | `ClockAdvance` (exactly one of `hours` or `to`) | `Clock` (clamped to start..end) |
| POST | `/api/clock/replay` | optional `ClockReplay` (`speed`) | `Clock` (now = start) |
| GET | `/api/inbox?status=pending\|answered` | none | `list[InboxItem]` |
| POST | `/api/inbox/{item_id}/reply` | `InboxReply` (`option`, `note`) | `InboxItem` (404 unknown, 409 already answered, 422 bad option) |
| GET | `/api/alerts` | none | `list[AlertFeedItem]`, newest first |
| GET | `/api/graph?at=<sim time>` | none | `FraudGraph` |
| GET | `/api/investigator/{cluster_id}` | none | `InvestigatorTrace` (404 `unknown cluster`) |
| GET | `/api/redteam` | none | `RedTeamReport` |
| GET | `/api/submission` | none | `Submission` |

## Conventions

- Sim times are ISO strings in America/Chicago, always with the `-06:00` offset at minute resolution, for example `2026-11-04T18:00-06:00`. Anything else is rejected.
- Unknown values are `null`. A fact the engine cannot find is `null` for the whole fact.
- The folder name is the deal id. It can hold spaces, apostrophes and ampersands, so URL-encode it in paths (`encodeURIComponent(folder)`).
- `watch` is UI-only and is never in the submission. A watch deal has `fraud.flagged` false.
- The inbox holds staff-addressed requests only. Borrower requests (for example an info request) appear in the deal detail `human_requests`.
- `needed_by_badge` (`none`, `ok`, `at_risk`, `overdue`) and `sla_pct` are computed by the server. `sla_pct` can exceed 1 for a stuck deal and freezes while a deal is held.
- Graph edges: `rarity` is 0 to 1 with 1 the rarest, `weight` drives line thickness, `evidence` is one plain sentence, `first_visible_at` drives the replay. `GET /api/graph?at=` hides edges not yet visible (and entity nodes left with no edge). Deal and history nodes and all clusters are always returned. In the mock, cluster tier is the end-of-run state.
- Cluster `tier` is `hold`, `watch` or `none`. Every cluster lists all six families `F1` to `F6`, each `{fired, evidence}`. Labels live in `FAMILY_LABELS` in `prism/contract.py` so the UI does not hard-code them: F1 shared rare entity, F2 novelty or burst, F3 lookalike vendor or account, F4 document forensics, F5 deposit pattern, F6 terms shape.
- The investigator trace `mode` is `off`, `replay` or `live` (Nemotron agents; scored outputs always come from deterministic code).

## Submission models

`Submission`, `SubmissionDeal` and their parts in `prism/contract.py` mirror the organizers' submission format exactly (stage, purpose, product, request type and alert level enums; the `KIND:target` issue grammar; sim times ending `-06:00`). The real engine's submission writer and validator will reuse these same models, and `fixtures/submission.json` is derived from `fixtures/deal_detail.json` so the two cannot drift.
