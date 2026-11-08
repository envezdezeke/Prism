---
phase: 261107-pfc-api-contract-mock-fixtures
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - .gitignore
  - prism/__init__.py
  - prism/contract.py
  - prism/derive.py
  - prism/api/__init__.py
  - prism/api/app.py
  - fixtures/clock.json
  - fixtures/deal_detail.json
  - fixtures/deals.json
  - fixtures/submission.json
  - fixtures/alerts.json
  - fixtures/inbox.json
  - fixtures/graph.json
  - fixtures/investigator.json
  - fixtures/redteam.json
  - tests/test_contract.py
  - docs/CONTRACT.md
autonomous: true
requirements: [FND-07]
must_haves:
  truths:
    - "With MOCK=1 (or MOCK unset) every /api endpoint in the contract returns 200 and the body validates against its Pydantic response model; with MOCK=0 every /api endpoint returns 503 'engine not wired yet'."
    - "Every file in fixtures/ parses against its Pydantic model, and the committed derived fixtures (deals, submission, alerts) equal a fresh derivation from fixtures/deal_detail.json."
    - "Submission-facing models accept exactly what data/participant/SUBMISSION_FORMAT.md allows (stage, purpose_category, product, request type, alert level enums; the KIND:target issue grammar; sim times ending -06:00) and reject everything else."
    - "A deal folder name with a space, an apostrophe and an ampersand resolves at /api/deals/{folder} when URL-encoded."
    - "The fraud graph fixture has a hold cluster of 3 deals and a watch cluster, rarity-weighted edges with per-edge evidence and first_visible_at, and /api/graph?at= hides edges not yet visible."
    - "Jesse can open /docs for the OpenAPI schema and read docs/CONTRACT.md for the endpoint list, run command, and change rule."
  artifacts:
    - path: "prism/contract.py"
      provides: "All Pydantic v2 models and enums (submission-facing and UI-facing), SimTime and Issue validators, FAMILY_LABELS"
    - path: "prism/api/app.py"
      provides: "FastAPI app factory, CORS, MOCK guard, fixture loader, all 12 /api routes"
    - path: "prism/derive.py"
      provides: "Deterministic derivation of deals.json, submission.json, alerts.json from deal_detail.json (python -m prism.derive)"
    - path: "fixtures"
      provides: "9 JSON fixtures, one per endpoint response"
    - path: "tests/test_contract.py"
      provides: "Fixture validation, regex and sim-time tests, referential checks, TestClient endpoint tests"
    - path: "docs/CONTRACT.md"
      provides: "Endpoint list and conventions for Jesse"
  key_links:
    - from: "prism/api/app.py"
      to: "prism/contract.py"
      via: "response_model on every route, so a drifted fixture fails with a 500 in tests"
    - from: "tests/test_contract.py"
      to: "fixtures/*.json"
      via: "FIXTURE_MODELS mapping plus a completeness test (every fixture file is mapped)"
    - from: "prism/derive.py"
      to: "prism/contract.py"
      via: "DealDetail.summary() and DealDetail.to_submission_deal()"
---

<objective>
Ship the API contract and mock server for integration point I1 (FND-07): Pydantic v2 models for every UI endpoint, JSON fixtures with invented data, a FastAPI app that serves them when MOCK=1, a fixture-validation test suite, and a short contract doc for Jesse.

Purpose: Jesse builds the whole UI (Phase 2) against `MOCK=1` while the engine is built. The submission-facing models are also what the real engine's submission writer and validator reuse later, so they live in `prism/contract.py` and mirror SUBMISSION_FORMAT exactly.

Output: the files in `files_modified`. HARD DEADLINE: pushed by about 19:15 CT; the whole plan must execute in about 40 minutes by one executor. Write fixtures compactly (1 to 3 stage_log entries per deal, short messages). After Task 3 passes, the quick workflow commits and the orchestrator runs `git push origin main`. Pushing is not a task.

Locked decisions (from the planning context; cited as D-xx in the tasks):
- D-01 Layout: Python package `prism/` at repo root (`prism/__init__.py`, `prism/contract.py` with all models and enums, `prism/api/app.py`), `fixtures/*.json` one file per endpoint response, `tests/test_contract.py`, `docs/CONTRACT.md`, `pyproject.toml` (fastapi, pydantic>=2, uvicorn, pytest; requires-python >=3.11).
- D-02 Python is `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe` with `PYTHONUTF8=1` (plain `python` is a Store stub). Teammate is on a Mac, so keep everything cross-platform (no backslash paths, no shell-specific code in the package).
- D-03 `Submission` / `SubmissionDeal` models mirror SUBMISSION_FORMAT exactly: Literal enums for stage, purpose_category, product, request type, alert level; issues validated by the locked KIND:target regex; sim times are ISO strings ending -06:00.
- D-04 UI-facing models extend the submission data: DealSummary, DealDetail, Clock, ClockAdvance, InboxItem, InboxReply, alert feed item, FraudGraph (nodes, edges, clusters), InvestigatorTrace, RedTeamReport, with the exact fields given in the planning context.
- D-05 Endpoints (prefix /api): GET /deals, GET /deals/{folder}, GET /clock, POST /clock/advance, POST /clock/replay, GET /inbox, POST /inbox/{id}/reply, GET /alerts, GET /graph?at=, GET /investigator/{cluster_id}, GET /redteam, GET /submission. MOCK=1 serves fixtures (POSTs return a plausible fixture response, no state); MOCK=0 returns 503 "engine not wired yet". CORS allows http://localhost:5173. Folder names with spaces, apostrophes and ampersands work when URL-encoded.
- D-06 Fixtures: 5 invented deals, none reusing the organizers' sample folder names or ring entities. Must include a held deal, a watch-tier deal, a missing-doc deal, a needed_by deal, a stuck deal with alert plus escalation, and a 3-deal cluster with mixed rarity edges.
- D-07 Tests: every fixture validates against its model; issue regex accept/reject; TestClient hits every endpoint under MOCK=1 and gets 200, including a folder with a space and an apostrophe.
- D-08 No LLM-vendor references anywhere in product code, fixtures or docs (the product uses NVIDIA Nemotron plus deterministic code).

Coverage audit (GOAL / REQ / CONTEXT; no RESEARCH.md exists for a quick task): GOAL (contract + fixtures + MOCK server + test + doc) is covered by Tasks 1 to 3. REQ FND-07 is covered by all three. D-01 and D-02 by Task 1; D-03 and the deals/submission/alerts part of D-04, D-05, D-06 by Task 2; the inbox, graph, investigator and red-team part of D-04, D-05, D-06, and D-07 completion by Task 3. Nothing is deferred or missing.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@data/participant/SUBMISSION_FORMAT.md

Source-of-truth notes (read once, do not re-read):
- `data/` is gitignored. Copy only the enum lists and the issue grammar from SUBMISSION_FORMAT into code; never copy its prose, folder names or data into committed files.
- Sim times are America/Chicago and always written with offset `-06:00` at minute resolution, for example `2026-11-04T18:00-06:00`.
- Stage SLAs in the fixtures: Intake 8 hours, Credit 48, Committee 48.
- Hold rule (FRD-04): a hold needs F1 plus at least 2 other families; 1 to 2 families is the watch tier (shown, not held). `watch` is a UI-only flag and is never part of the submission (a watch deal has `fraud.flagged` false).

<fixture_spec>
Clock: start `2026-11-02T08:00-06:00`, end `2026-11-06T18:00-06:00`, now `2026-11-04T18:00-06:00`.
Personas (all invented): rm.alvarez (RM on every deal), credit.nakamura, committee.osei, fraudops.keller, mgr.ibarra, and `borrower`.

| Folder | legal_name | stage | stage_entered_at | sla_hours | sla_pct | needed_by (badge) | amount | purpose / product / term | guarantor | revenue | held / watch | issues | resolved_issues |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lone Star Dental | Lone Star Dental PLLC | Credit | 2026-11-03T14:00-06:00 | 48 | 0.58 | 2026-11-06T15:00-06:00 (at_risk) | 85000 | equipment / Equipment Loan / 60 | Dr. Alma Reyes | 940000 | no / no | none | none |
| Cedar Ridge Welding | Cedar Ridge Welding LLC | Intake | 2026-11-04T12:00-06:00 | 8 | 0.75 | null (none) | 62000 | working_capital / Working Capital Loan / 36 | Tomas Brandt | 410000 | no / yes | MISSING_DOC:ein_letter | none |
| Mama Rosa's Kitchen | Mama Rosa's Kitchen Inc | Committee | 2026-11-02T12:00-06:00 | 48 | 1.13 | null (none) | 410000 | expansion / Term Loan / 84 | Rosa Delgado | 1850000 | no / no | none | MISSING_PAGE:bank_statement_2026-09 |
| Bayou Bistro & Grill | Bayou Bistro & Grill LLC | Intake | 2026-11-03T08:00-06:00 | 8 | 0.44 (frozen at hold) | null (none) | 150000 | inventory / Revolving Line of Credit / 24 | Colette Marchand | 720000 | yes / no | OLD_TRICK:SHELL_ADDRESS, MISMATCH:guarantor_address | none |
| Juniper Creek Nursery | Juniper Creek Nursery LLC | Intake | 2026-11-03T09:00-06:00 | 8 | 0.75 (frozen at hold) | null (none) | 98000 | working_capital / Term Loan / 36 | Wade Hollister | 530000 | yes / no | MISMATCH:guarantor_address | none |

Use obviously fake EINs (for example `12-0000001`, `12-0000002`, increment per deal). Each fact is `{value, source_doc, confidence}` with source_doc a filename such as `application.pdf`, `ein_letter.pdf`, `certificate_of_formation.pdf`, `financial_statements.pdf`; confidence between 0.80 and 0.99. Cedar Ridge has no `ein_letter.pdf`, so its ein fact sources from `application.pdf` with lower confidence (0.80). A fact the engine cannot find is `null` for the whole fact (for example Cedar Ridge `needed_by`).

stage_log (decision values: `advanced` or `held`, or null while the deal is still in the stage):
- Lone Star Dental: Intake 2026-11-03T08:30 to 2026-11-03T14:00 advanced "all intake docs present; facts consistent"; Credit entered 2026-11-03T14:00, exited null, decision null, why "waiting on credit officer decision".
- Cedar Ridge Welding: Intake entered 2026-11-04T12:00, exited null, decision null, why "EIN letter missing; asked the borrower".
- Mama Rosa's Kitchen: Intake 2026-11-02T08:30 to 10:00 advanced; Credit 2026-11-02T10:00 to 12:00 advanced "credit approved; statements complete after the missing page arrived"; Committee entered 2026-11-02T12:00, exited null, decision null, why "waiting on full committee approval (amount above the delegated limit)".
- Bayou Bistro & Grill: Intake 2026-11-03T08:00 to 11:30 decision `held`, why "fraud hold: rare entities shared with Juniper Creek Nursery and a prior deal".
- Juniper Creek Nursery: Intake 2026-11-03T09:00 to 15:00 decision `held`, why "fraud hold: rare entities shared with Bayou Bistro & Grill and a prior deal".

human_requests (answer and answered_at null unless stated):
- Lone Star Dental: credit_decision to credit.nakamura at 2026-11-03T14:15.
- Cedar Ridge Welding: info_request to borrower at 2026-11-04T12:30 ("please send the IRS EIN letter").
- Mama Rosa's Kitchen: credit_decision to credit.nakamura at 2026-11-02T10:15, answer `approve`, answered_at 2026-11-02T11:50; committee_approval to committee.osei at 2026-11-02T12:15, unanswered.
- Bayou Bistro & Grill: fraud_hold to fraudops.keller at 2026-11-03T11:35.
- Juniper Creek Nursery: fraud_hold to fraudops.keller at 2026-11-03T15:05.

alerts (message names whose deal, waiting on what, for how long, what unblocks it):
- Lone Star Dental: 2026-11-04T17:00, stage Credit, level alert, to credit.nakamura, needed-by deadline Nov 6 3:00 PM at risk, credit decision waiting 27 hours.
- Mama Rosa's Kitchen: 2026-11-04T12:00, stage Committee, level alert, to committee.osei, waiting 48 hours on committee approval; 2026-11-04T16:00, stage Committee, level escalation, to mgr.ibarra, waiting 52 hours.

fraud block: held deals have flagged true, held true, flagged_at (Bayou 2026-11-03T11:30, Juniper 2026-11-03T15:00), stage_at_flag Intake, a plain-words reason, and linked_deals naming the other held deal plus `H-0000-001`. The other three deals: flagged false, held false, reason null, linked_deals empty, flagged_at and stage_at_flag null.

Inbox (staff only; borrower requests are not inbox items): inbox-001 Lone Star Dental credit_decision to credit.nakamura pending, options approve / decline / request_info; inbox-002 Mama Rosa's Kitchen committee_approval to committee.osei pending, options approve / decline; inbox-003 Bayou Bistro & Grill fraud_hold to fraudops.keller pending, options confirm_hold / release_hold; inbox-004 Juniper Creek Nursery fraud_hold to fraudops.keller pending, same options; inbox-005 Mama Rosa's Kitchen credit_decision to credit.nakamura answered `approve` at 2026-11-02T11:50. Each item's (deal, type, to, at, answer, answered_at) must equal the matching human_request in deal_detail.json.

Graph (12 nodes, 12 edges). Deal nodes (type `deal`, id = folder name): the 5 deals. History nodes (type `history_deal`): `H-0000-001`, `H-0000-002`. Entity nodes (type `entity`, with kind): ent-preparer-01 preparer "Northpoint Tax & Bookkeeping"; ent-phone-01 phone "(210) 555-0142"; ent-pdfprod-01 pdf_producer "SwiftDocs PDF Engine 2.1"; ent-bank-01 bank "First Prairie Bank"; ent-vendor-01 vendor "Ace Fabrication Supply". Edges are deal-or-history source to entity target, `weight` = 3 x rarity rounded to 2 decimals, `evidence` one plain-words sentence each:

| entity | rarity | sources (first_visible_at) |
|---|---|---|
| ent-preparer-01 | 0.96 | H-0000-001 (2026-11-02T08:00-06:00), Bayou Bistro & Grill (2026-11-03T08:20-06:00), Juniper Creek Nursery (2026-11-03T09:15-06:00) |
| ent-phone-01 | 0.90 | Bayou Bistro & Grill (2026-11-03T08:20-06:00), Juniper Creek Nursery (2026-11-03T09:15-06:00) |
| ent-pdfprod-01 | 0.80 | Bayou Bistro & Grill (2026-11-03T08:25-06:00), Juniper Creek Nursery (2026-11-03T09:20-06:00) |
| ent-bank-01 | 0.12 | H-0000-001 (2026-11-02T08:00-06:00), Bayou Bistro & Grill (2026-11-03T08:20-06:00), Juniper Creek Nursery (2026-11-03T09:15-06:00) |
| ent-vendor-01 | 0.35 | H-0000-002 (2026-11-02T08:00-06:00), Cedar Ridge Welding (2026-11-04T12:10-06:00) |

Clusters: C-001 deals [Bayou Bistro & Grill, Juniper Creek Nursery, H-0000-001], tier `hold`, families F1 fired (preparer shared by 3 deals, phone by 2), F2 fired (two applications opened one hour apart), F4 fired (same PDF producer string on both applications), F3 / F5 / F6 not fired (F5 evidence: fewer than 6 deposits, family needs at least 6). C-002 deals [Cedar Ridge Welding, H-0000-002], tier `watch`, only F1 fired (shared vendor, moderately common, not enough alone), F2 to F6 not fired. Every cluster lists all six family keys, each `{fired, evidence}`.

Investigator trace for C-001 (mode `replay`, 4 steps, tools named `graph_neighbors`, `history_search`, `doc_forensics`, `deposit_pattern`, each step with a short thought and result_summary that agree with the graph above, plus a 2 to 3 sentence case_summary). Red-team report (`generated_by` "fixture (synthetic)"): three tricks, for example "Shared preparer ring" (12 deals, 11 caught, 0.92, median 3.5 hours, 0 false flags), "Statement tampering" (10, 9, 0.90, 6.0, 0), "Lookalike vendor account" (8, 5, 0.63, 14.0, 1), with a one-sentence description each.
</fixture_spec>
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Tracer, GET/POST /api/clock end to end (scaffold, primitives, Clock models, fixture, CORS, MOCK guard, tests)</name>
  <files>pyproject.toml, .gitignore, prism/__init__.py, prism/api/__init__.py, prism/contract.py, prism/api/app.py, fixtures/clock.json, tests/test_contract.py</files>
  <precondition>Running the D-02 Python with `-c "import fastapi, pydantic, httpx, pytest, uvicorn"` exits 0 (all five are already installed locally).</precondition>
  <action>
Wire ONE vertical path through every layer (packaging, contract model, fixture, API, test), production quality, so every later task only adds models, fixtures and routes.

pyproject.toml (D-01): setuptools build backend; project name `prism`, version `0.1.0`, requires-python `>=3.11`, dependencies `fastapi`, `pydantic>=2`, `uvicorn`; optional-dependencies group `dev` with `pytest` and `httpx` (Starlette's TestClient needs httpx; pytest is the D-01 test dep); setuptools packages find with include `prism*`; pytest config with `testpaths = ["tests"]` and `pythonpath = ["."]` so tests run from a fresh checkout without installing. Append `.pytest_cache/` and `*.egg-info/` to `.gitignore` with Edit (do not rewrite the file). `prism/__init__.py` and `prism/api/__init__.py` hold only a one-line docstring.

prism/contract.py (D-03, D-04), this task adds only the shared primitives and the clock models:
- `ContractModel` base: Pydantic v2 `BaseModel` with `ConfigDict(extra="forbid")`. All models in this file inherit it (strictness is intentional: the UI never reads a field the contract does not define, and a fixture typo must fail validation).
- Literal enums copied from SUBMISSION_FORMAT: `Stage` (Intake, Credit, Committee, Product, Committed, Closed), `PurposeCategory` (working_capital, equipment, inventory, payroll, expansion, refinance), `Product` (Term Loan, Equipment Loan, Revolving Line of Credit, Working Capital Loan), `RequestType` (credit_decision, committee_approval, commitment_signoff, funding_release, fraud_hold, fraud_release, info_request), `AlertLevel` (alert, escalation).
- `ISSUE_RE`: `re.compile` of the locked D-03 grammar, exactly this alternation: `^(MISSING_DOC|MISSING_PAGE):(application|guarantor_id|certificate_of_formation|ein_letter|bank_statement_\d{4}-\d{2}|financial_statements|tax_return|equipment_quote)$|^MISMATCH:(legal_name|ein|amount_requested|guarantor_name|guarantor_dob|guarantor_address|annual_revenue|bank_balance)$|^OLD_TRICK:(STMT_TAMPER|REV_INFLATION|ID_MISMATCH|DUP_EIN|SHELL_ADDRESS)$`, compiled with `re.ASCII`. `Issue = Annotated[str, AfterValidator(...)]` where the validator uses `ISSUE_RE.fullmatch` (fullmatch, so a trailing newline is rejected) and raises ValueError with the offending string.
- `parse_sim_time(s) -> datetime` and `format_sim_time(dt) -> str`; `SimTime = Annotated[str, AfterValidator(...)]` that requires: a `T` separator, `datetime.fromisoformat` parses it, the string ends with `-06:00`, and the parsed value is tz-aware. `format_sim_time` writes `isoformat(timespec="minutes")`, which yields the `-06:00` suffix for a fixed -6h offset. Both helpers are public because app.py, derive.py and tests reuse them.
- `Clock` (now, start, end: SimTime). `ClockAdvance` (hours: float > 0 or None; to: SimTime or None; a model validator requires exactly one of the two). `ClockReplay` (speed: float > 0, default 1.0).

prism/api/app.py (D-05): `FIXTURES` = repo-root `fixtures` directory resolved from `__file__` (`parents[2]`); `load_fixture(name)` reads UTF-8 JSON each call (no caching, so fixture edits show immediately); `mock_enabled()` reads env `MOCK` at call time and returns False only for `0` or `false` (so unset and `1` both serve fixtures; document the default in CONTRACT.md); `require_mock()` dependency raises `HTTPException(503, "engine not wired yet")` when mock is off; `create_app()` builds `FastAPI(title="Prism API")` with `CORSMiddleware` allowing exactly the origins `http://localhost:5173` and `http://127.0.0.1:5173` (explicit list, never `*`; any methods and headers), an `APIRouter(prefix="/api", dependencies=[Depends(require_mock)])`, and module-level `app = create_app()`. Docs and OpenAPI stay outside the router, so `/docs` and `/openapi.json` work in both modes. Routes in this task: `GET /api/clock` (response_model `Clock`, returns fixtures/clock.json); `POST /api/clock/advance` (body `ClockAdvance`, response `Clock`; stateless: now = fixture now plus `hours`, or the given `to`; clamp to the fixture `end`; return via `format_sim_time`); `POST /api/clock/replay` (optional body `ClockReplay`, response `Clock` with now equal to start). Use `response_model=` on every route so fixture drift surfaces as a 500 in tests.

fixtures/clock.json: the Clock values from the fixture_spec in context.

tests/test_contract.py: module-level `FIXTURE_MODELS` dict mapping fixture filename to a type (use `pydantic.TypeAdapter` so list and dict types work); this task registers `clock.json: Clock` and later tasks add entries. A parametrized `test_fixture_validates` loads each mapped fixture from the repo `fixtures/` directory. A `client` pytest fixture does `monkeypatch.setenv("MOCK", "1")` and returns `TestClient(create_app())`. Tests: sim-time accept (`2026-11-02T09:30-06:00`, `2026-11-02T09:30:00-06:00`) and reject (`2026-11-02T09:30Z`, `2026-11-02T09:30-05:00`, naive `2026-11-02T09:30`, space separator, `not-a-time-06:00`); issue regex parametrized accept (every doc type for MISSING_DOC, `MISSING_PAGE:bank_statement_2026-08`, every MISMATCH field, every OLD_TRICK code) and reject (`MISSING_DOC:passport`, `missing_doc:tax_return`, `MISMATCH:ein ` with trailing space, `MISSING_DOC:tax_return\n`, `MISSING_DOC:bank_statement_2026-5`, `OLD_TRICK:UNKNOWN`, `MISMATCH:ein|x`); `ClockAdvance` rejects both-or-neither of hours and to; `GET /api/clock` is 200 and equals the fixture; `POST /api/clock/advance` with `{"hours": 2}` returns now `2026-11-04T20:00-06:00` and with a huge value clamps to end; `POST /api/clock/replay` returns now equal to start; CORS preflight (`OPTIONS /api/clock` with `Origin: http://localhost:5173` and `Access-Control-Request-Method: GET`) returns that origin in `access-control-allow-origin`, and an unlisted origin gets no such header; with `MOCK=0` `GET /api/clock` is 503 with detail `engine not wired yet`; with `MOCK` deleted it is 200.
  </action>
  <verify>
    <automated>PYTHONUTF8=1 C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe -m pytest -q tests/test_contract.py</automated>
  </verify>
  <done>pytest passes on the clock path; `GET /api/clock` and both clock POSTs work under MOCK=1, return 503 under MOCK=0; CORS allows only the Vite origins; the SimTime and Issue validators accept and reject exactly the listed examples; the repo runs from a fresh checkout via `pythonpath` with no install.</done>
</task>

<task type="auto">
  <name>Task 2: Deals slice, submission models, deal detail, alerts feed, derived fixtures, routes and tests</name>
  <files>prism/contract.py, prism/derive.py, prism/api/app.py, fixtures/deal_detail.json, fixtures/deals.json, fixtures/submission.json, fixtures/alerts.json, tests/test_contract.py</files>
  <action>
Expand the proven path to the deals, submission and alerts endpoints.

prism/contract.py additions (D-03, D-04). Submission-facing models, field names and nullability exactly per SUBMISSION_FORMAT:
- `Extracted`: legal_name (str or None), ein (str or None), amount_requested (int or float or None), purpose_category (PurposeCategory or None), product (Product or None), term_months (int or None), guarantor_name (str or None), annual_revenue_stated (int or float or None), needed_by (SimTime or None); every field defaults to None.
- `StageLogEntry`: stage, entered_at (SimTime), exited_at (SimTime or None), decision (str or None), why (str).
- `HumanRequest`: type (RequestType), to (str), at (SimTime), message (str), answer (str or None), answered_at (SimTime or None); the two answer fields default to None.
- `Alert`: at, stage, level (AlertLevel), to, message.
- `Fraud`: flagged (bool), held (bool), flagged_at (SimTime or None), stage_at_flag (Stage or None), reason (str or None), linked_deals (list of str, default empty).
- `SubmissionDeal`: extracted, issues (list of Issue), stage_log, human_requests, alerts, fraud (default: not flagged, not held).
- `Submission`: team (str), `set` (str; field named `set`, so never use the builtin `set[...]` annotation inside this class body), deals (dict of folder name to SubmissionDeal), history_flags (list of str, each must start with `H-`).

UI-facing models (D-04):
- `Fact`: value (str or int or float), source_doc (str), confidence (float 0 to 1). `ExtractedFacts` has the same nine field names as `Extracted`, each `Fact | None` defaulting to None.
- `DealSummary`: folder, legal_name (str or None), stage (Stage), stage_entered_at (SimTime), sla_hours (float > 0), sla_pct (float >= 0; may exceed 1 for a stuck deal; freezes while held), needed_by (SimTime or None), needed_by_badge (Literal none, ok, at_risk, overdue; server-computed so the UI never re-derives it), amount_requested (number or None), held (bool), watch (bool, UI-only, never in the submission), rm (str or None).
- `DealDetail(DealSummary)` adds: facts (ExtractedFacts), issues (list of Issue), resolved_issues (list of Issue), stage_log, human_requests, alerts, fraud. Methods: `summary()` returns a `DealSummary` built from the inherited summary fields; `to_submission_deal()` returns a `SubmissionDeal` whose `extracted` takes each fact's `value` (None when the fact is None) and passes issues, stage_log, human_requests, alerts and fraud through (resolved_issues is UI-only and dropped).
- `AlertFeedItem(Alert)` adds id (str) and deal (str).

prism/derive.py: `derive(details: dict[str, DealDetail]) -> dict[str, Any]` returns JSON-ready content (`model_dump(mode="json")`) for `deals.json` (list of summaries in the key order of deal_detail.json), `submission.json` (`Submission` with team `Prism`, set `sample`, deals keyed by folder from `to_submission_deal()`, history_flags = sorted unique `H-` ids found in `fraud.linked_deals` of flagged deals) and `alerts.json` (every deal alert as an `AlertFeedItem`; ids `alert-001`, `alert-002`... assigned oldest first by parsed `at`, list returned newest first). `main()` loads fixtures/deal_detail.json, validates it as a dict of `DealDetail`, and writes the three files with `json.dumps(indent=2, ensure_ascii=False)` plus a trailing newline, UTF-8, `newline="\n"` (stable on Windows and Mac). Run as `python -m prism.derive`. This is the "regenerate the fixture first" step from the ROADMAP contract rule.

fixtures/deal_detail.json: a JSON object keyed by folder name, one `DealDetail` per deal, written by hand from the fixture_spec in context (the 5 deals, every value listed there; per D-06 use only these invented names, no sample folder names and no real ring entities). Then run `python -m prism.derive` to generate deals.json, submission.json and alerts.json; do not hand-write those three.

prism/api/app.py additions (D-05): `GET /api/deals` (list of DealSummary from deals.json); `GET /api/deals/{folder}` (DealDetail looked up by dict key in deal_detail.json, never by building a file path from the request; 404 with detail `unknown deal` when absent); `GET /api/alerts` (list of AlertFeedItem); `GET /api/submission` (Submission). Folder names with spaces, apostrophes and ampersands work through standard path decoding.

tests/test_contract.py additions (D-07): register `deals.json: list[DealSummary]`, `deal_detail.json: dict[str, DealDetail]`, `alerts.json: list[AlertFeedItem]`, `submission.json: Submission` in `FIXTURE_MODELS`. New tests: committed deals/submission/alerts equal `derive()` of the committed deal_detail (compare parsed JSON); each deal_detail key equals its `folder`; each summary's legal_name, amount_requested and needed_by agree with the matching facts; every fixture issue string matches `ISSUE_RE`; held deals have `fraud.held` true and `watch` deals have `fraud.flagged` false; required scenarios exist (at least one held, one watch, one deal with a `MISSING_DOC:` issue, one with needed_by, one deal whose alerts include both level `alert` and level `escalation`); `GET /api/deals` returns 5 items; `GET /api/deals/{folder}` is 200 for every folder both with the raw name (spaces and apostrophe, httpx encodes it) and with `urllib.parse.quote(folder, safe="")` (covers `%27` and `%26`); unknown folder is 404; `GET /api/alerts` is newest first; `GET /api/submission` is 200; with `MOCK=0` these four routes return 503; a test that skips when `data/participant/shared_folder` is absent and otherwise asserts no fixtures file contains any directory name found there (case-insensitive; names come from the directory listing at runtime, never hard-coded).
  </action>
  <verify>
    <automated>PYTHONUTF8=1 C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe -m pytest -q tests/test_contract.py && test -f fixtures/deal_detail.json && test -d prism && ! grep -rniE 'anthropic|claude' prism fixtures tests</automated>
  </verify>
  <done>Deals, deal detail, alerts and submission endpoints return 200 under MOCK=1 and 503 under MOCK=0; the derived fixtures equal a fresh derivation; the submission fixture validates as a `Submission` (so the same models can validate the real engine output); a folder named with a space, apostrophe and ampersand resolves; no vendor references.</done>
</task>

<task type="auto">
  <name>Task 3: Inbox, fraud graph, investigator and red-team slice plus docs/CONTRACT.md</name>
  <files>prism/contract.py, prism/api/app.py, fixtures/inbox.json, fixtures/graph.json, fixtures/investigator.json, fixtures/redteam.json, tests/test_contract.py, docs/CONTRACT.md</files>
  <action>
Add the remaining models, fixtures, routes, the contract doc, and the completeness checks.

prism/contract.py additions (D-04):
- Inbox: `InboxItem` (id, deal, type: RequestType, to, at: SimTime, message, options: list of str with at least one entry, status Literal pending or answered, answer: str or None, answered_at: SimTime or None; a model validator requires that an answered item has answer in options and an answered_at, and a pending item has neither). `InboxReply` (option: str, note: str or None).
- Graph: `EntityKind` Literal (preparer, phone, registered_agent, address, vendor, remit_account, pdf_producer, bank, guarantor); `GraphNode` (id, type Literal deal, history_deal, entity; label; kind: EntityKind or None, required exactly when type is entity); `GraphEdge` (source, target, entity_kind, rarity float 0 to 1, weight float >= 0, first_visible_at: SimTime, evidence: str); `FamilyId` Literal F1 to F6 and a public constant `FAMILY_LABELS` (F1 shared rare entity, F2 novelty or burst, F3 lookalike vendor or account, F4 document forensics, F5 deposit pattern, F6 terms shape) so the UI never hard-codes them; `FamilyResult` (fired: bool, evidence: str); `Cluster` (id, deals: list of str, families: dict of FamilyId to FamilyResult that must contain all six keys, tier Literal hold, watch, none); `FraudGraph` (nodes, edges, clusters) with a model validator that every edge source and target is a node id, each edge's entity_kind equals its target node's kind, and every cluster deal is a node id. Do not put the FRD-04 hold rule in the model: that logic belongs to the engine, and the test below checks it on the fixture only.
- `TraceStep` (step int >= 1, thought, tool, args: dict of str to Any, result_summary) and `InvestigatorTrace` (cluster_id, steps, case_summary, mode Literal off, replay, live).
- `TrickResult` (name, description, n_deals int >= 0, caught int >= 0, catch_rate float 0 to 1, median_time_to_hold_hours float or None, false_flags int >= 0; validator caught <= n_deals) and `RedTeamReport` (tricks, generated_by: str).

Fixtures: write inbox.json (list of InboxItem), graph.json (FraudGraph), investigator.json (one InvestigatorTrace) and redteam.json (RedTeamReport) by hand exactly per the fixture_spec in context and D-06: the 12 nodes, 12 edges with per-edge evidence and first_visible_at, clusters C-001 (hold, 3 deals) and C-002 (watch), mixed rarity from 0.12 to 0.96. Use only invented entity names; no sample folder names and no real ring entities.

prism/api/app.py additions (D-05):
- `GET /api/inbox` with optional query `status` (pending or answered, 422 otherwise) returning list of InboxItem.
- `POST /api/inbox/{item_id}/reply` (body `InboxReply`, response `InboxItem`): 404 `unknown inbox item` for an unknown id; 409 `already answered` when the fixture item is answered; 422 with detail listing the allowed options when `option` is not in the item's options; otherwise return a copy of the item with status answered, answer set to the option and answered_at set to the clock fixture's now. Stateless: nothing is stored.
- `GET /api/graph` with optional query `at` (a sim time; 422 when it is not a valid `-06:00` sim time, via `parse_sim_time`): returns the fixture graph; when `at` is given, keep only edges with `first_visible_at` <= at and drop entity nodes left with no edge; deal and history nodes and all clusters are always returned (cluster tier in the mock is the end-of-run state; documented in CONTRACT.md). Compare times as parsed datetimes, not strings.
- `GET /api/investigator/{cluster_id}`: the fixture trace when `cluster_id` equals its cluster_id, else 404 `unknown cluster`.
- `GET /api/redteam`: RedTeamReport.

tests/test_contract.py additions (D-07): register `inbox.json: list[InboxItem]`, `graph.json: FraudGraph`, `investigator.json: InvestigatorTrace`, `redteam.json: RedTeamReport` in `FIXTURE_MODELS`. New tests: a completeness test that the set of `fixtures/*.json` file names equals the keys of `FIXTURE_MODELS`; inbox items agree with deal_detail human_requests on (deal, type, to, at, answer, answered_at); graph deal nodes (type deal) are exactly the deal_detail folders, every `fraud.linked_deals` entry is a deal_detail folder or a graph history node, and every held deal is in a cluster with tier hold; FRD-04 check on the fixture clusters (tier hold implies F1 fired and at least 3 families fired; watch implies 1 or 2 fired; none implies 0); the graph has at least one hold cluster with 3 deals, edges spanning rarity below 0.2 and above 0.9; investigator cluster_id exists in the graph clusters; red-team catch_rate is within 0.01 of caught / n_deals; endpoint tests: `GET /api/inbox` 200 and `?status=pending` returns only pending, `?status=bogus` is 422; reply happy path (inbox-001 with option `approve` returns status answered), reply with a bad option is 422, unknown id is 404, replying to inbox-005 is 409; `GET /api/graph` is 200, with `at=2026-11-03T08:30-06:00` it returns fewer edges than without `at` and no edge with a later first_visible_at, with a malformed `at` it is 422; `GET /api/investigator/C-001` is 200 and `/api/investigator/nope` is 404; `GET /api/redteam` is 200; `GET /openapi.json` is 200 and contains all 12 contract paths (`/api/deals`, `/api/deals/{folder}`, `/api/clock`, `/api/clock/advance`, `/api/clock/replay`, `/api/inbox`, `/api/inbox/{item_id}/reply`, `/api/alerts`, `/api/graph`, `/api/investigator/{cluster_id}`, `/api/redteam`, `/api/submission`); `GET /docs` is 200; with `MOCK=0` every one of the 12 routes (use a representative path per route) is 503 while `/docs` stays 200.

docs/CONTRACT.md (short, for Jesse, plain sentences): purpose and the change rule from ROADMAP (change the Pydantic model, regenerate the fixture with `python -m prism.derive` where it is derived, then tell the other person; the UI never reads a field the contract does not define); how to run (`pip install -e ".[dev]"`, then `MOCK=1 python -m uvicorn prism.api.app:app --port 8000`; on Windows PowerShell `$env:MOCK=1` first; API at http://localhost:8000, Swagger at /docs, Vite origin http://localhost:5173 is allowed; `MOCK` unset behaves as `MOCK=1` until the engine is wired, `MOCK=0` returns 503 "engine not wired yet"); an endpoint table with method, path, request body, response model (the 12 routes, naming `{item_id}` for the inbox reply); conventions (sim times are ISO with `-06:00` at minute resolution; unknown values are `null`; folder name is the deal id and must be URL-encoded in paths, for example `encodeURIComponent`; `watch` is UI-only and not in the submission; inbox contains staff-addressed requests only, borrower requests appear in deal detail; `needed_by_badge` and `sla_pct` are server-computed; graph edge `rarity` is 0 to 1 with 1 the rarest, `weight` drives line thickness, `first_visible_at` drives the replay, `?at=` hides later edges; the six family ids and `FAMILY_LABELS`; cluster tiers hold, watch, none); a note that the submission models in `prism/contract.py` are the ones the real engine's writer and validator will reuse; an optional tip to generate TypeScript types from `/openapi.json`. D-08: no vendor references beyond Nemotron mentions where relevant.
  </action>
  <verify>
    <automated>PYTHONUTF8=1 C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe -m pytest -q && test -f docs/CONTRACT.md && test -d fixtures && ! grep -rniE 'anthropic|claude' prism fixtures tests docs/CONTRACT.md pyproject.toml && ! grep -rniE 'docuforge|delacroix|metroplex|4471|commerce street' prism fixtures tests docs/CONTRACT.md</automated>
  </verify>
  <done>All 12 endpoints return 200 under MOCK=1 and 503 under MOCK=0; every fixture validates and the completeness test passes; the graph fixture shows a 3-deal hold cluster and a watch cluster with mixed-rarity edges and `?at=` filtering; inbox replies enforce allowed options; /docs and /openapi.json list all routes; docs/CONTRACT.md exists; no vendor references and no real ring literals in committed code, fixtures or docs.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser (Vite dev server) to API | untrusted origin, path params (folder, cluster_id, item_id), query params (at, status) and JSON bodies cross here |
| repo (committed) to organizers' data | gitignored `data/` content must not leak into committed fixtures, code or docs |
| pip dependency install | declared packages are installed by the developer, not by this plan |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-pfc-01 | Spoofing / Tampering | CORS config in `create_app()` | medium | mitigate | explicit allow-list of the two Vite origins, never `*`; a test asserts an unlisted origin gets no `access-control-allow-origin` header |
| T-pfc-02 | Tampering | path params to fixture lookup (`/deals/{folder}`, `/investigator/{cluster_id}`, `/inbox/{item_id}/reply`) | high | mitigate | lookup by dict key or id comparison against already-loaded fixtures, never by building a file path from request input, so path traversal is impossible; unknown keys return 404 |
| T-pfc-03 | Tampering | request bodies and query params (`ClockAdvance`, `InboxReply`, `at`, `status`) | medium | mitigate | Pydantic validation with `extra="forbid"`; reply option checked against the item's allowed options (422); malformed `at` and `status` return 422 |
| T-pfc-04 | Information Disclosure | fixtures, code and docs copying the organizers' confidential data | high | mitigate | all fixture data invented; a runtime test (skips when `data/` is absent) asserts no fixture contains a sample folder name; verify greps for real ring literals; only enum lists and the issue grammar are copied from SUBMISSION_FORMAT |
| T-pfc-05 | Elevation of Privilege | MOCK flag exposing mock responses in production | low | accept | MOCK defaults to serving fixtures only until the engine exists; the I3 switch flips the default and `MOCK=0` returns 503; no auth surface exists yet |
| T-pfc-06 | Denial of Service | unauthenticated local API | low | accept | local hackathon dev server on localhost; no stateful writes, POSTs store nothing |
| T-pfc-SC | Tampering | npm/pip/cargo installs | high | accept | this plan runs no install step; fastapi, pydantic, uvicorn, pytest and httpx are mainstream packages already installed locally and only declared in pyproject.toml (Jesse installs with pip from PyPI); no package-legitimacy checkpoint needed because no new package is added by an install task |
</threat_model>

<verification>
Run from the repo root with the D-02 Python and `PYTHONUTF8=1`:
- `-m pytest -q` passes (all fixtures validate, completeness test passes, every endpoint 200 under MOCK=1 and 503 under MOCK=0).
- `-m prism.derive` leaves `git diff --stat fixtures/` empty after a clean run (derived fixtures are reproducible).
- `grep -rniE 'anthropic|claude'` over prism, fixtures, tests, docs/CONTRACT.md, pyproject.toml returns nothing; the ring-literal grep over the same paths returns nothing.
- Spot check: start `MOCK=1 python -m uvicorn prism.api.app:app --port 8000` is not required; TestClient covers every route.

Source coverage audit: GOAL covered (Tasks 1 to 3). REQ FND-07 covered (all tasks). CONTEXT D-01, D-02 (Task 1); D-03, D-04 deals/submission/alerts, D-05, D-06 (Task 2); D-04 inbox/graph/investigator/red-team, D-05, D-06, D-07 completion, docs (Task 3); D-08 enforced by greps in Tasks 2 and 3. RESEARCH: none (quick task). No unplanned items.
</verification>

<success_criteria>
- Integration point I1 "Done when" from ROADMAP.md is met: Pydantic schemas and JSON fixtures cover deals, deal detail, clock (advance, replay), inbox (including the reply POST), alerts, graph (nodes, rarity-weighted edges, per-edge evidence, first-visible sim time), investigator trace and red-team report; `MOCK=1` serves them; OpenAPI at `/docs`.
- Submission-facing fields match SUBMISSION_FORMAT exactly (enums, KIND:target issues, -06:00 times), validated by tests.
- `pytest -q` is green from a fresh checkout without installing the package.
- Executed within about 40 minutes; the quick workflow commits and the orchestrator pushes `main` before about 19:15 CT so Jesse can pull and start Phase 2.
</success_criteria>

<output>
Create `.planning/quick/261107-pfc-api-contract-mock-fixtures-fnd-07-i1/261107-pfc-SUMMARY.md` when done
</output>
