# Prism submission audit (read-only), 2026-11-08

## Results
- pytest: 354 passed. `npm --prefix ui test`: 97/97 pass. `npm run build` OK; oxlint only fast-refresh warnings.
- Engine on sample (173 files, 13 deals, 0 errors): validates ("valid"); two runs byte-identical (sha256 fbd42d73...fe75c).
- Self-score vs eval/gold.json: extraction 12/117 (READ), issues tp0 fn9 fp0, routing 36/52, final_stage 6/13 (MOVE), fraud flagged 9/13, held 9/13, latest_ok_stage 0/4, linked_deals 10/13, history_flags missed 2/2 (H-2608-002, H-2609-008), must_not_flagged 0 (FRAUD).
- Scratch outputs: sub1.json, sub2.json, score.json, eb/ in this directory.

## Findings (ranked)

### 1. CRITICAL: READ is a stub, so everything downstream is hollow (verified)
prism/read/extract.py `extract_facts` returns {} and `extract_entities` returns [] ("Stub: empty"); classify.py (25 lines) and issues.py (18 lines) are also stubs. Consequences: 12/117 facts; 9 of 9 expected issues missed; the cross-deal graph gets no entities, so the 3 ring deals (Pecan Grove, Ridgeway, Summit Peak) and Granite Bay are MISSED, linked_deals for the ring are -4 each, history flags 0/2. Stage movement is wrong (Intake stuck: "waiting on the application facts to be read"); 7 deals end at Intake instead of Closed/Credit, so alerts are spurious. Roadmap says H10 baseline freeze needed this; it is not met. Fix: build Phase 3 (pypdf/pdfplumber, rules/known_fraud_checks) and the F1/F3 entity extraction; nothing else moves the score as much.

### 2. HIGH: Phase 5 fraud engine cannot run end to end (verified)
Fraud baseline/rarity/signals exist and have tests, but F2 and F4 are not built (eval_baseline caveat). With F1,F3,F5 alone on history, 1 good test deal (H-2609-008) would already be flagged, and per gold H-2609-008 is a *history_flag* (real) so verify against gold before reading that as a false positive. Hold rule needs 3 families; with F2/F4 absent and entities empty no deal can be held. Fix: build F2/F4 and wire entities into prism/fraud/graph.py, then rerun trap suite.

### 3. HIGH: No Nemotron code exists; NEMOTRON=off determinism untestable (verified)
grep of prism/ for nemotron/openai finds nothing; only scripts/check_nvidia_key.py. No investigator, red-team, VL reader, record/replay client. Fixtures investigator.json/redteam.json are hand-written mock data. The H15.5 gate and the NVIDIA track are unmet. Determinism for scored fields currently holds trivially because there is no LLM. Cut tier per ROADMAP: Goldman score first.

### 4. HIGH: API serves only fixtures; MOCK=0 returns 503 on every /api route (verified)
prism/api/app.py: `require_mock` dependency; "engine not wired yet". Live switch (I3/I4) never happened. The UI therefore can only show fixture data, not engine output; GET /api/submission serves fixtures/submission.json, NOT the engine's output. POST reply/clock store nothing. A demo claiming "live engine" would be inaccurate.

### 5. HIGH: Clean-checkout instructions are broken (verified)
- No requirements.txt, though ONBOARDING.md says `pip install -r requirements.txt`; README has no run steps at all (I6/DEMO-02 undone). pyproject deps are fastapi, pydantic, pyyaml, uvicorn only; pandas/networkx/pypdf are not declared (and not installed in .venv), which will bite as soon as Phase 3/5 use them (CLAUDE.md names them).
- Documented command is `python -m prism run --folder ... --arrivals ...`; this isn't in README. No `ui` setup/run steps in README (npm install; npm run dev; proxy to :8000; port 5173 strict).
- CLAUDE.md pins Windows Python path and `py -3.13`; this Mac uses .venv python3.12 (pyproject requires >=3.11, fine). ONBOARDING says unzip to data/participant/ but the zip nests participant/participant: documented. Data dir must be supplied by the user (gitignored) so a fresh clone can't run engine without it; mock API and UI do work without data.
- Stale tracked artifacts: ui/package.json test script runs `node --test "src/**/*.test.ts"` (needs Node 22+ TypeScript stripping); document Node version.

### 6. MEDIUM: Real sample data content is committed (verified)
Not tracked: data/, any PDFs, .env, the challenge statement (git ls-files and `git log --all --name-only` show only docs/model/prism_model.pdf as a PDF; it has no sample names). BUT tracked files contain real pack content: eval/gold.json (names, EINs-like figures, ring, history ids H-2608-002/H-2609-008), fixtures/deal_detail.json + submission.json (EIN-shaped values, deal names), docs/ONBOARDING.md (K. Delacroix phone, vendor names, account suffixes), .planning/*, docs/DETAILS_CHECKLIST.md. HANDOFF.md states the repo was briefly public on 11/07 and then made private. docs/pitch/ is clean (PITCH_OUTLINE forbids names; no sample names found by grep). Risks: if a public repo is required for submission (HANDOFF Q14), these must be scrubbed from the public copy (and history, since it was public once). Fix: submit a code-only export or `git filter-repo`; replace fixtures with synthetic data.

### 7. MEDIUM: Secrets (verified, no leak found)
.env is gitignored (.gitignore:2) and never in `git ls-files`. `git log --all -S'nvapi-'` hits only commit c80ac3e, whose value is the 16-char placeholder `nvapi-REPLACE_ME` in .env.example. No real key in history. The `.env` file locally was not read (hook-blocked). .env.example has NEMOTRON_MODE=live default: if code later uses it, NEMOTRON=off must be forced for the scored run.

### 8. MEDIUM: Hard constraints (verified)
- No Claude/Anthropic/PyMuPDF/fitz/openai references in prism/, config/, pyproject. (Commit trailers say Co-Authored-By Claude; that's metadata, not product code. Planning docs mention Claude; fine.)
- No sample literals in prism/ or config/ (grep for deal names, Delacroix, 4471/9902, DocuForge, H-26xx returned nothing).
- Determinism: no datetime.now/time.time/random/uuid in prism/; set uses are sorted before output in the paths inspected (run.py doc claim and byte-identical double run). Not exhaustively audited for fraud/move set iteration; the 2-run test only covers the sample and a stub READ path, so the guarantee is weak until real extraction lands.
- Out of date: committed docs/CONTRACT.md claims `MOCK` unset = mock; ok.

### 9. LOW/MEDIUM: Time gate (verified for the code path; inferred for future code)
prism/engine/visibility.py `ArrivalLog.visible_files(now)` filters arrive_at <= now; arrivals paths reject absolute, drive letters and `..` (traversal-safe). tests/test_visibility.py covers it. run.py reads via the log. Risk: the Phase 3 reader must open files only from visible_files; currently no reader reads files (stub), so no bypass exists today but there is nothing to enforce it. history/ is loaded whole by fraud baseline (baseline.py:351) by design (history is prior data); calibrate/test split does use "strictly earlier" logic.

### 10. LOW: API hardening (verified by TestClient)
- CORS allows only http://localhost:5173 and 127.0.0.1:5173 (evil origin preflight gets 400, no ACAO). Methods/headers wildcard, fine.
- Path traversal: `/api/deals/{folder}` is a dict-key lookup on fixtures (404 for ../ forms); no file is opened by user input. No static mount; /data/... returns 404. /docs is open (Swagger) even with MOCK=0.
- Validation: reply `option` checked against item options (422); `note` has no max length (unbounded body; harmless locally). Clock advance: hours accepts any float (1e308 handled via OverflowError -> clamp to end); negative hours accepted -> clamped to start, so a negative advance can rewind (contract says never rewinds; to-earlier is a 422 but hours<0 is not: verified 200 with -5). Inconsistency, trivial.
- MOCK mode state is not persisted, so replies "answered" aren't visible on refresh, expected.

### 11. LOW: Git state
Local main equals origin/main now (0 ahead, 0 behind; the 14-ahead snapshot is stale, someone pushed). Uncommitted: .planning/STATE.md, 07-01-PLAN.md modified; 07-02..07-07 plans and .planning/state.json untracked. out/ is gitignored so out/submission.json is stale vs a fresh run (alerts differ). Many leftover branches (worktree-agent-*, synth-gen). Nothing pushed by this audit.

## Which scored fields come from stubs
extracted (all 9 facts), issues (all), fraud.flagged/held/stage_at_flag/linked_deals/history_flags for real rings (entities empty), routing for held/missing-doc deals and final_stage (depend on facts). Not stubbed: stage machine, SLA/alerts, routing table, validator, writer, scorer.

## Verified vs inferred
Verified by running: tests, engine, validate, determinism, score, API probes, git/grep checks. Inferred: future bypass of the time gate; completeness of set-iteration audit; the hidden-set generalization.
