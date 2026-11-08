# Project Research Summary

**Project:** DealPilot (team Goldman-I), HackUTD 2026
**Domain:** Commercial-loan deal pipeline automation with cross-deal fraud-ring detection (hackathon, about 21 hours, 2 people)
**Researched:** 2026-11-07
**Confidence:** MEDIUM overall. HIGH on the engine shape, PDF/OCR choices and data-derived expectations. MEDIUM on how the Goldman grader scores ambiguous cases. LOW on Nemotron hosted tool calling and rate limits until the smoke test runs.

## Executive Summary

DealPilot reads a loan folder as its documents arrive on a simulated clock, extracts facts with provenance, moves each deal through six stages with the right human sign-off, and holds deals that look like a coordinated fraud ring. The research agrees on the shape of a correct build: a single-process, deterministic, event-sourced engine where every scored output is a pure function of the visible inputs and the rules files. The fraud component is link analysis over shared entities (preparer, agent, vendor and remit account, PDF producer, address, guarantor), weighted by how rare each entity is against the 257-deal history. It is not a trained classifier, because the labelled history contains only 12 old-trick positives and the hidden set uses a different trick.

The recommended stack is Python 3.13 (explicit path, not the Store stub) with pypdf, pdfplumber, RapidOCR for the one JPG, pandas, networkx and rapidfuzz, behind FastAPI. The frontend is React 19 with Vite, Tailwind, shadcn/ui and react-force-graph-2d. Nemotron runs through the hosted OpenAI-compatible endpoint (`https://integrate.api.nvidia.com/v1`) and sits entirely off the scored path: an investigator agent, a red-team generator, a VL reader for the ID photo, and message polish. Each Nemotron output is cached, validated, and advisory unless it passes a deterministic gate. The fraud rule is "a rare shared entity plus at least two more independent signal families agree", never a single signal.

The main risks are, in order: (1) sim-clock leakage, where the engine sees files before their `arrive_at` and produces early or impossible flag times; (2) false flags on strange-but-real borrowers (Tyler, Okafor, Harbor Tea, Westfield, Garza, Priya, Oakline, Bluebonnet), which the rubric penalizes heavily; (3) an unhandled exception on an unseen document shape, which can zero the whole hidden-set run; (4) hard-coding sample literals, which scores zero on the hidden trick; and (5) Nemotron availability, since the hosted endpoint is a trial service with a community-reported 40 requests per minute and unverified tool calling. Mitigations are a gated data layer, a zero-false-flag regression across all 13 folders and 257 history rows, never-crash wrappers with a submission validator, and a Nemotron-off run that must produce byte-identical output.

## Key Findings

### Recommended Stack

Core engine and API, all verified installed or installable on this machine for cp313 Windows: Python 3.13, FastAPI, uvicorn, pydantic 2, pandas 3, python-dotenv (installed); networkx, openai SDK, pdfplumber, pypdfium2, rapidfuzz, rapidocr with onnxruntime, tenacity and pytest (to install). pypdf layout mode keeps statement columns aligned and reads all 167 sample PDFs in about 2.4 seconds. RapidOCR read the ID photo correctly in a fresh venv with no system installs. PyMuPDF is excluded because of AGPL licensing.

Frontend: React 19.3, Vite 8.3 (Node 24 is fine), `@vitejs/plugin-react` 6, Tailwind 4.3 with the Vite plugin (CSS-only config), shadcn/ui on Base UI (do not paste Radix snippets from older blogs), react-force-graph-2d 1.29 (canvas, custom node and link drawing, light-theme safe), TanStack Query, zustand. TypeScript 7 removed `baseUrl`, so use only `paths`. Skip dark mode and chart libraries.

**Nemotron model IDs (use these, from the live `/v1/models` catalog):**
> **Superseded 2026-11-07:** `nemotron-3-super-120b-a12b` and `nemotron-nano-3-30b-a3b` return 404 on our key's tier. Use the IDs in `.env.example` / PROJECT.md (`nemotron-3.5-super-vl-120b-a12b`, `nemotron-3.5-lightning-30b-a3b`, `nemotron-3-nano-omni-30b-a3b-reasoning`).
- Agents and red-team: `nvidia/nemotron-3-super-120b-a12b` (temperature 1.0, top_p 0.95 per the model card)
- Fast text and JSON jobs: `nvidia/nemotron-nano-3-30b-a3b` (reasoning off)
- VL reader: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` (base64 `image_url`; PDFs must be rasterized first)
- Fallback when Super fails: `nvidia/nemotron-3-ultra-550b-a55b`
- Do not use `nvidia/nemotron-nano-9b-v2`. It is no longer in the catalog.
- Put every ID in an env var (`NEMOTRON_AGENT_MODEL`, `NEMOTRON_FAST_MODEL`, `NEMOTRON_VL_MODEL`).

**Agent framework:** a plain OpenAI-SDK tool-calling loop of about 80 lines, capped at 8 steps, with pydantic argument validation, tool errors returned as text, and a final "write the case" turn with tools omitted. Do not use LangGraph or NeMo Agent Toolkit. The agent proposes and deterministic code disposes.

**Hosted, not Brev:** Super needs 8x H100 for BF16, and the $60 Brev credit cannot sustain it. Keep Brev as a break-glass option for a small model only. The single OpenAI-compatible seam means only `base_url` changes.

### Expected Features

**Must have (rubric lines or hard constraints fail without these):**
- READ: arrival-gated ingest; content-based document classification (never filename); field extraction with source document, page and confidence; MISSING_DOC; MISSING_PAGE ("Page X of N"); MISMATCH:<field> with normalization; the five OLD_TRICK checks (STMT_TAMPER, REV_INFLATION, ID_MISMATCH, DUP_EIN, SHELL_ADDRESS) implemented exactly as `rules/known_fraud_checks.md` states.
- MOVE: six-stage state machine with guards that return blockers; hard block while a document or human answer is outstanding; human-gate routing with OOO backup (dana.whitfield out 11/03 to 11/06, so Priya goes to marcus.lee); delegated versus chair routing at the $250k line; SLA ladder at 100%, 150% and 200% (second escalation to lauren.kim); unanswered requests escalate on the same ladder; deadline prioritisation from `needed_by`; append-only audit log of what was seen, decided and why; scripted responder personas (fast, OOO, never-answers) plus an interactive inbox; sim clock advance and scrub.
- FRAUD: deal-to-entity graph built over current and history deals; entity normalization (phones, addresses, suffixes, account last-4); rarity weighting `w(e) = log(N_hist / (1 + df(e)))` with a recency factor; PDF forensics (producer and creator rarity within document class); deposit-pattern anomaly scored as a percentile against history; vendor lookalike detection (same base name, different remit account); multi-signal agreement gate; connected components over rarity-filtered edges only; explainable per-signal score; early hold request to victor.hale (backup monica.salas) before Closed; history link-back that requires a rare entity plus a second anomalous family; trap regression suite; submission JSON writer and validator keyed by folder name; re-runnable CLI with `--folder` and `--arrivals`.
- UI minimum: pipeline board, deal detail with facts and sources, inbox and alert feed, a basic force graph with edge evidence.

**Should have (differentiators, ordered Goldman first):**
- Generic signal families defined over distributions, not values (the hidden-set insurance).
- Statement-versus-deposit-summary reconciliation (reuses the REV_INFLATION code).
- Threshold-proximity signal (amount just under the delegated limit) and entity-youth signal. Weak alone, corroboration only.
- "First seen" novelty for entities absent from history until recently.
- Counterfactual leave-one-family-out explanation and a watch tier (one family = watch, never hold).
- Self-evaluation on history with the false-flag rate reported.
- Cheap template fingerprint (page size, fonts, producer, creator, line-count bucket).
- Nemotron: ReAct investigator with a visible trace; red-team generator with a detector evaluation on 3 to 5 tricks; VL fallback for the JPG; plain-words messages with template fallback; free-text reply parser.
- UI: sim-clock "ring lights up" replay (the single best demo moment); rarity-encoded edges; evidence side panel; signal-family checklist per cluster; investigator trace panel.

**Defer or do not build:**
- Supervised classifier on `fraud_label` (12 positives, old tricks only).
- Any sample literal in detection logic ("DocuForge", "Delacroix", 4471, "Metroplex", "Commerce Street").
- An LLM deciding holds, extractions or links.
- Single-signal holds (for example "DocuForge producer, so hold"). H-2511-010 and H-2601-022 used that producer and repaid normally.
- Flagging every history deal that touches a shared entity (Harbor Tea's address is used by 15 deals, 14 of them clean).
- Community detection, GNNs and embeddings (not explainable, and unnecessary at about 270 deals).
- Full LOS scope (pricing, covenants, spreading, e-sign, portal), real auth, a database, real email or Slack, Neo4j, 3D graphs, auto-closing.

### Architecture Approach

One in-process, single-writer, event-sourced discrete-event engine. A SimClock and an EventQueue ordered by (time, priority, seq) feed ingest, then facts, checks, the fraud graph, the stage machine, human requests and the SLA scheduler. Every change is appended to a JSONL event log. State is a fold over that log, so scrubbing the clock is a rebuild, and the submission writer is a pure projection of state. Nemotron, the UI and the API sit outside the engine and read it through an `EngineQuery` read-only surface. API mutations go through one engine lock.

**Core invariants:**
1. Rules and data are inputs (`stages.json`, `teams.json`, `config/fraud.yaml`). No path, folder name, company name or trick name appears in the engine.
2. Time is injected. No `datetime.now()` and no sleep-based pacing anywhere in the engine.
3. One front door: file arrivals, human replies, timeouts and SLA timers are all events on one queue.
4. Idempotent outputs: alerts and requests carry deterministic keys (`deal|stage|level`, `deal|type|attempt`).
5. The scored path never imports `nemotron/`. A run with Nemotron off must produce identical output.

**Major components:**
1. `sim/` (clock, queue, arrival source): exposes only files with `arrive_at <= now`.
2. `ingest/` (loader, pdftext, csvstmt, classify, extract, normalize): produces typed documents with provenance. Parse cache keyed by content hash.
3. `facts/`: candidate values per field with an authority table (application for the request, EIN letter for EIN and legal name, ID for guarantor DOB and address).
4. `checks/` (completeness, consistency, known_fraud): pure functions returning issues from an enum builder, never from free text.
5. `fraud/` (canon, baseline, graph, signal families F1 to F6, decision rule, cases).
6. `stages/` (machine, gates, routing, SLA, deadlines): advances only when requirements are met, no hold is open, and no gate is unanswered.
7. `humans/` (request manager, responder protocol, scripted and interactive responders, templates, reply parser).
8. `engine/submission`: projection plus schema and enum validator. Refuses to write invalid output.
9. `nemotron/`: record/replay client, investigator, red-team, VL gate, prose polish.
10. `api/` and `ui/`: FastAPI with Pydantic schemas as the contract source; `MOCK=1` serves fixtures so the UI never blocks on the engine.

**Stage semantics to lock early:**
- Missing statement at Credit entry: send `info_request` to the borrower and wait. Do not send `credit_decision` on an incomplete file.
- MISMATCH at Intake: do not advance. Fuzzy-equal names (nickname, suffix, case, "Ave" versus "Avenue") are not mismatches.
- Fraud flag at any stage: freeze the deal at once, send `fraud_hold`, and never enter Closed while flagged.
- Closed requires a `funding_release` reply from tasha.reed, no open flag, and disbursement account verification.
- Delegated limit is 249,999.99 from `stages.json`. Use integer cents: `cents >= 25_000_000` routes to harold.benson (chair, SLA 48h); otherwise priscilla.nguyen (delegated, SLA 24h).
- `needed_by` becomes an ISO timestamp or `null`. Never emit "No specific date".
- Quiescence: `COMPLETENESS_CHECK` runs 30 sim-minutes after a folder's last arrival, so folders still landing do not produce false `MISSING_DOC`. Advancement is immediate when requirements are positively met.

**Fraud decision rule (adopt this version):**
- Families: F1 shared rare entity (required, counting history matches); F2 novelty or burst; F3 lookalike; F4 document forensics; F5 deposit pattern (min n ≈ 6 deposits); F6 terms shape (weak, corroboration only).
- `flag(d)` = F1 hit AND at least two of F2 to F6 hit (three families total), OR any OLD_TRICK check fired.
- Cluster = connected components over strong F1 edges only.
- `history_flags` = history deals sharing at least two independent families with the cluster. Do not put returning customers (H-2511-002, H-2512-005, H-2601-006) in it.
- Thresholds live in `config/fraud.yaml`. Do not fit them to the sample.

### Critical Pitfalls

1. **Sim-clock leakage.** All 173 files sit in the folder at t=0. Prevention: one `visible_files(now)` data layer that filters `arrivals.jsonl`; sort arrivals by (`arrive_at`, path) for deterministic ties; add a metamorphic test that deletes files with `arrive_at > T` and asserts identical output. Verify with the log: no `flagged_at` may precede the evidence it cites.
2. **Crash voids the hidden set.** One unreadable PDF or unexpected type can yield no output at all. Prevention: try/except per deal and per document, with the error recorded in an extra key; always write the JSON; validate against `SUBMISSION_FORMAT.md`; test folder names such as `Priya's Bakery`, `Okafor Advisory - James` and `Westfield Print & Sign`.
3. **Filename or keyword classification.** Tyler's `IRS 7004 extension.pdf` is titled "Form 7004 - Application for Automatic Extension" and would be read as a second loan application. Prevention: anchor phrases ordered by specificity; statement period from document text, never the filename; `other` as the default, never an exception.
4. **False flags on strange-but-real borrowers.** Naive rules fire on Tyler's "#210" suite, Okafor's round-hundred deposits (3 to 5 wires a month), Westfield's new vendor, and Harbor Tea's shared address. Prevention: a shared entity counts only if it links at least two deals; rarity weighting; the multi-family rule; a zero-false-flag regression over all 13 folders and 257 history rows; `history_flags` on the sample must be exactly H-2608-002 and H-2609-008.
5. **Money, boundary and statement errors.** Use integer cents throughout. Oakline's August statement is missing page 2, so emit `MISSING_PAGE`, not `STMT_TAMPER`. Tyler is missing June only. Granite Bay gets `STMT_TAMPER` through footing and the September-opening break. Annualize as (sum / months present) x 12. Westfield's EIN transposition (`74-3169524` versus `74-3196524`) is a real MISMATCH. Bluebonnet's amount mismatch ($250,000.00 versus $205,000.00) holds routing until resolved.
6. **Determinism leaks and Nemotron on the scored path.** Prevention: `PYTHONHASHSEED=0`; explicit sort keys everywhere; no wall clock; cents money; a run-twice-and-compare hash test; `NEMOTRON=off` must reproduce the scored output byte for byte.

**Also critical:** Ridgeway, the first ring deal to land (Mon 11/02 13:51), must be flagged on its own from history links by about Mon 14:10. It cannot wait for the cluster, which forms only when Pecan and Summit arrive on Tuesday and Wednesday.

## Implications for Roadmap

The engine's vertical slice should exist by about hour 10 to 11 of 21, leaving the rest for hardening, Nemotron and demo.

### Phase 1: Foundations and Contract
**Rationale:** Every later phase reads from the gated data layer; the determinism harness and validator must exist before features. Publishing the contract early unblocks the UI.
**Delivers:** Repo skeleton; `visible_files(now)` gate; typed config loaders; fixed `-06:00` offset; cents money; submission schema and validator; determinism harness; OpenAPI and fixture stubs with `MOCK=1`; clean-venv install of pinned deps; RapidOCR spike on `IMG_2291.jpg`; Nemotron smoke test; inventory of `shared_folder` and `arrivals.jsonl`.

### Phase 2: Ingest and Extraction (READ, part 1)
**Rationale:** All checks, graph attributes and forensic signals derive from parsed facts with provenance.
**Delivers:** Loader with sha256 and parse cache; pypdf layout text and metadata; `Page X of N` markers; CSV statement parser; anchor-phrase classifier; field extraction; graph attribute extraction (preparer, phone, agent, vendor, remit account, producer, creator, address, bank, guarantor ID, EIN, deposit features); RapidOCR lazy-loaded for images.

### Phase 3: Issue Engine (READ, part 2)
**Delivers:** Completeness matrix by product, stage and business age (7004 rule); `MISSING_PAGE`; cross-document `MISMATCH` with normalization; like-for-like revenue; five OLD_TRICK checks verbatim; statement checks (footing, transaction sum, continuity) with skip-and-explain when pages are missing.
**Gate:** Zero issues on Garza, Priya, Okafor, Harbor Tea and Tyler's non-June items. Expected: Westfield `MISMATCH:ein`; Bluebonnet `MISMATCH:amount_requested` and `MISSING_DOC:equipment_quote`; LSFD `MISSING_DOC:tax_return` and `MISSING_DOC:equipment_quote`; Oakline `MISSING_PAGE`; Granite Bay `OLD_TRICK:STMT_TAMPER` and `OLD_TRICK:REV_INFLATION`; Tyler `MISSING_DOC:bank_statement_2026-06`.

### Phase 4: Pipeline, Routing and Human Loop (MOVE)
**Delivers:** Stage machine with logged `why`; OOO routing parsed from `notes` with backup chains; cents-based approver routing; SLA timers at exact 100/150/200% instants per route; reply-timeout reroute; scripted personas and interactive inbox; deadline priority and deadline-risk alerts; five-slot alert messages.
**Gate:** Priya's credit request goes to marcus.lee; Bluebonnet held on the amount mismatch; ring approval routes to priscilla.nguyen; never-answers persona produces reroutes and escalations.

### Phase 5: Fraud Graph (FRAUD)
**Delivers:** Canonicalization; history baseline inverted index; signal families F1 to F6 with evidence; decision rule; freeze and `fraud_hold`; `linked_deals` and `history_flags`; watch tier; explainable evidence; counterfactual; trap suite and history self-evaluation.
**Target:** Ridgeway flagged by about Mon 14:10 from history links alone; ring flagged at Intake or Credit; `history_flags` exactly H-2608-002 and H-2609-008; zero legitimate deals flagged.

### Phase 6: Nemotron Sidecars (NVIDIA track)
**Delivers:** Record/replay client with `off | replay | live`; VL reader through validated-field gate; ReAct investigator over read-only `EngineQuery` tools (≤8 steps); red-team spec generator + deterministic synthesizer + fresh-engine evaluator (3–5 tricks); message polish with template fallback; reply parser.

### Phase 7: UI, Demo and Hardening
**Delivers:** UI v1 (board, clock, inbox, alerts, deal detail); UI v2 (force graph with sim-clock replay, rarity-encoded edges, evidence panel, signal checklist, investigator trace); weekend-drop dry run; fuzz run; clean-venv run; pre-recorded demo path; frozen scoring baseline hash.

### Phase Ordering Rationale
- Foundations first: determinism harness, visibility gate and validator protect every later result.
- Ingest before issues and graph: all consume facts with provenance.
- Routing and SLA after issues: stage guards read blockers.
- Fraud after ingest, parallel to pipeline work.
- Nemotron after the scored path is stable and off it by design.
- UI in parallel from the start against fixtures.

**Cut order (Goldman > Nemotron > UI):** drop motion and polish first; then the VL escalation model; then the red-team generator; then the investigator. Never cut the engine, validator, determinism harness or trap suite.

### Research Flags
- **Phase 2:** review low-confidence classifications (`may statement.pdf`, 7004 vs return, LSFD scans).
- **Phase 3:** read `rules/known_fraud_checks.md` verbatim for thresholds.
- **Phase 5:** deepest risk; threshold pass on history and trap suite; red-team sanity check.
- **Phase 6:** verify hosted tool calling, reasoning toggles and rate limits on the smoke test.
- Standard patterns (skip research): Phases 1, 4, 7.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH (Python/PDF/OCR/frontend); MEDIUM (Nemotron) | Verified locally; model IDs from live catalog; tool calling and rate limits untested |
| Features | MEDIUM | Priorities HIGH from rubric; signal catalogue from practitioner sources |
| Architecture | HIGH (engine/data flow); MEDIUM (thresholds); LOW (Nemotron specifics) | Grounded in the actual data pack |
| Pitfalls | HIGH (data-derived); MEDIUM (grader); LOW (Nemotron) | Every folder inspected; expected outcomes are an oracle seed |

**Overall confidence:** MEDIUM.

### Gaps to Address
- File counts disagree across research files (167 vs 140 PDFs + 5 CSVs + 1 JPG; 173 arrivals vs 186 files). Inventory in Phase 1.
- Fraud threshold: adopt F1 + ≥2 other families; confirm on the trap suite. Ridgeway's early flag depends on reaching 3 families at Intake using history matches.
- OCR: trust STACK (RapidOCR works); spike in a clean venv.
- Nemotron: use STACK IDs in env vars; smoke test decides native tools vs JSON-action ReAct.
- Timezone: fixed `-06:00` offset.
- Submission semantics: plan is open issues in `issues`, resolved in an extra key.
- Interpretation decisions: Tyler revenue midpoint $450,000; Oakline `guarantor_name` "Bob Kline" with ID name kept separately; `MISSING_DOC:equipment_quote` reported at Intake, held at Product; no `credit_decision` on an incomplete file; Granite Bay flagged (old trick → Fraud Ops); never-answering Fraud Ops still counts as held.
- Quiescence (30 min) and reply-timeout fractions are assumptions to tune.
- Brev is break-glass only.

## Sources

### Primary (HIGH)
- `.planning/PROJECT.md`; local data pack `data/participant/`; local runs of pypdf, pdfplumber, pypdfium2, RapidOCR; live `GET https://integrate.api.nvidia.com/v1/models` (2026-11-07); npm/PyPI checks; Nemotron-3-Super HF model card; shadcn Vite docs.

### Secondary (MEDIUM)
- build.nvidia.com model cards; Neo4j/Linkurious/Quantexa ring-detection material; Gartner LOS guide; PDF-forensics practitioner pages; NVIDIA forum threads on 40 RPM.

### Tertiary (LOW)
- Third-party gateway pages for Nemotron Nano 9B v2 (superseded); inferred grader behavior; Benford/round-number practice from general knowledge.

---
*Research completed: 2026-11-07*
*Ready for roadmap: yes*
