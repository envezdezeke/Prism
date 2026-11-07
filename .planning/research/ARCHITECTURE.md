# Architecture Patterns

**Domain:** Event-driven commercial-loan pipeline copilot with cross-deal fraud detection (DealPilot, HackUTD 2026, Goldman + NVIDIA Nemotron tracks)
**Researched:** 2026-11-07
**Overall confidence:** HIGH on engine / data-flow design (grounded in the real data pack: `stages.json`, `teams.json`, `clock.py`, `arrivals.jsonl`, `SUBMISSION_FORMAT.md`, sample PDFs). MEDIUM on fraud thresholds (must be tuned on the sample ring, then red-teamed). LOW on Nemotron model IDs / native tool-calling behaviour (only third-party gateway pages found; verify on build.nvidia.com in the first 30 min of the Nemotron phase).

## What the real inputs tell us (architecture-driving facts)

| Fact (from the data pack) | Architectural consequence |
|---|---|
| Each borrower folder lands in ~20 min (e.g. Pecan Grove 11:11 to 11:30), files trickle in one at a time. | Fraud scoring and intake gating must be **incremental per file**. "Missing doc" cannot be judged at first arrival; needs a quiescence rule. |
| Deal identity = **folder name** (`LSFD_docs`, `tyler loopwise loan stuff`); borrower name lives only in the content. | Deal key = folder. Content names are *facts to cross-check*, never the key. A doc whose entity disagrees with the folder's other docs is a `MISMATCH`, not a new deal. |
| Doc types are guessable only from content + PDF `Title` metadata (`Business Checking Statement`, `Small Business Loan Application`); PDFs are label/value-on-alternate-lines text with mojibake (`�` for dashes); some statements are CSV; one ID is a JPG. | Classifier = signature-phrase scoring on page-1 text + metadata + extension. Extractor = generic label/value pair parser, not per-filename regex. JPG is classified from context and read only via VL fallback. |
| PDF metadata `Producer`/`Creator`/`CreationDate` is real data (all Pecan Grove docs incl. bank statements say `DocuForge 2.1`; genuine statements say `FIS Statement Services 9.2`). | Forensics are a first-class signal family, extracted at ingest and stored on every Doc. |
| `history/deals.csv` has a `pdf_producer` column, preparer name/firm/phone, registered agent, vendor + `vendor_remit_acct_last4`, bank; `monthly_deposits.csv` has `pct_deposits_multiple_of_100`, `deposit_weekdays`. | The history baseline is an **inverted index** built once at startup: attribute value → set of history deals, plus deposit-feature distributions. Rarity = computed, never hard-coded. |
| `stages.json` holds SLAs, thresholds (`delegated_max_amount`), gates, routing, escalation percentages; `teams.json` holds backups, `escalates_to`, and OOO as free text in `notes`. | **All rules are data loaded at runtime.** The just-under-$250k signal reads the threshold from `stages.json`. OOO is parsed from `notes` (regex) with an `overrides/ooo.json` fallback. |
| `arrivals.jsonl` is `{path, arrive_at}`; weekend drop adds new folders AND new files in existing folders plus a Collections notice. | A file arriving in an existing folder is an event on an in-flight deal (re-extract, re-check, re-score). A file that doesn't fit any deal (notice) becomes an *unattached doc* matched by entity (EIN / name / account), never a crash. |
| Stage SLAs are wall-clock sim hours, alerts "may be sent any time", humans work Mon to Fri 08:00 to 18:00. | Scheduler uses wall-clock sim hours for SLA timers; the scripted responder models business hours for human latency. |
| Sample ring member Ridgeway arrives *first* (11/02 13:51), before any other ring deal. | Flag-on-first-deal must be possible from **history links alone** (history is the baseline), not only from within-batch sharing. |

## Recommended Architecture

One in-process, single-writer, **event-sourced discrete-event engine**. Everything scored is a deterministic fold over an append-only event log. Everything else (Nemotron, UI, API) sits on the outside and either reads engine state or feeds events in through the same front door the file watcher uses.

```
                          +-----------------------------------------------------+
                          |                 OUTSIDE (non-scored)                |
   React UI  <--REST/SSE--+  FastAPI (api/)   Nemotron sidecars (nemotron/)      |
   (ui/)                  |      |  reads + commands    | read-only tools,       |
                          +------|----------------------|------ cached, validated+
                                 v                      v
+--------------------------------------------------------------------------------+
|                 ENGINE (deterministic, scored path)  engine/core.py            |
|                                                                                |
|  SimClock ──> EventQueue (heap: time, prio, seq) <───────────────┐            |
|     ^            |                                               |            |
|     |            v                                               |            |
|  ArrivalSource  FILE_ARRIVED ──> Ingest ──> Deal Facts ──┬─> Checks ──> Issues |
|  (folder +      (hash, parse,    (classify,  (candidates  |   (completeness,   |
|   arrivals)      metadata)        extract)    + provenance)|    consistency,    |
|                                                            |    old tricks)     |
|                                                            v                    |
|                                    Fraud Graph (incremental)  <── History index |
|                                    signals -> families -> cluster decision      |
|                                                            |                    |
|                                                            v                    |
|   Stage Machine <── gate evaluation <── Issues + FraudDecision                  |
|     |  (exit reqs, human gates, freeze on hold)                                 |
|     v                                                                           |
|   HumanRequestManager ──> Router (OOO/backup) ──> Responder (pluggable) ─┐     |
|     ^                                                                    |     |
|     └────────── HUMAN_REPLY / REPLY_TIMEOUT events <────────────────────┘     |
|   SLA Scheduler (100/150/200%) + Deadline planner ──> Alerts                    |
|                                                                                |
|   EventLog (JSONL, append-only)  ──fold──>  EngineState  ──>  SubmissionWriter |
+--------------------------------------------------------------------------------+
```

**Core invariants (these are what make the hidden-set run safe):**

1. **Rules and data are inputs, not code.** `Engine(folder, arrivals, history_dir, rules_dir, contacts, assignments, responder, config)`. The weekend drop and hidden set are `--folder X --arrivals Y [--assignments Z]`. No path, folder name, company name, account number or trick name appears in `dealpilot/`.
2. **Time is injected.** No `datetime.now()` anywhere in the engine. Only `SimClock`.
3. **One front door.** Files (from the arrival source), human replies, timeouts and SLA timers are all *events on one queue*. The UI "advance clock" button, the headless batch run, the red-team harness and the replay tool call the same `engine.advance_to(t)`.
4. **Event-sourced.** State = fold(log). Scrubbing the clock backwards = rebuild from the log up to `t` (173 small files, parse results cached on disk by content hash, so this is sub-second). Interactive human answers are logged as events with their sim time, so a replay reproduces them.
5. **Idempotent outputs.** Every alert/request/timer has a deterministic key (`deal|stage|level`, `deal|type|attempt`); re-evaluation never double-sends.
6. **Scored path never imports `nemotron/`.** The submission writer reads `EngineState` only. Sidecar output lands in separate stores and is surfaced under extra keys (ignored by the judge) or via a validator.

### Component Boundaries

| Component | Responsibility | Inputs | Outputs | Talks To |
|---|---|---|---|---|
| `sim/SimClock` + `ArrivalSource` | In-memory sim time; yields arrivals with `arrive_at <= now`; supports `advance_to`, `set`, `reset`. Reads `arrivals.jsonl`; does NOT depend on `clock.py`'s state file (shape-compatible `/now /inbox /advance` only if the organizers' tooling needs it). | folder, arrivals | `FILE_ARRIVED` events | EventQueue |
| `sim/EventQueue` | Heap ordered by `(time, priority, seq)`. Deterministic tie-break: SLA timers < arrivals < replies at equal time is NOT assumed; use explicit priority constants. | events | next event | Engine core |
| `ingest/` | `loader` (sha256, size, mtime-free), `pdftext` (pypdf text per page + metadata), `csvstmt`, `classify` (signature scoring, returns type + confidence), `extract/*` (per-type field extraction via a generic label/value parser), `normalize` (name/EIN/address/phone/money canonicalizers). Parse cache keyed by content hash. | file bytes | `Doc` (type, pages, page markers `X of N`, metadata, fields with provenance) | Facts, VL fallback (via router) |
| `facts/DealFacts` | Holds **candidates** per field `{value, doc_id, page, confidence, source=det|vl, verified}`; resolves the canonical value by an authority table (application for the request; EIN letter for EIN/legal name; ID for guarantor DOB/address); newer `correction` docs supersede with provenance. | Docs | `extracted{}` and consistency graph | Checks |
| `checks/` | Pure functions `(DealFacts, Docs, stage, history) -> issues`. `completeness` (required docs per stage, 6 most-recent full months, page continuity), `consistency` (cross-doc `MISMATCH:*` with fuzzy normalization so Tyler's messy-but-real file does not trip), `known_fraud` (five OLD_TRICK codes exactly as `known_fraud_checks.md`). | facts, docs, history | `Issue{kind,target,first_seen_at,evidence}` | Stage machine, Fraud |
| `fraud/` | See "Fraud scorer" below. Maintains the bipartite graph, history index, signals, cluster decisions, cases. | Doc attributes, facts, deposit features | `FraudDecision{deal, flagged, families, score, evidence, linked_deals, history_links}` | Stage machine, Humans, API, sidecars (read-only) |
| `stages/machine` | Per-deal state machine `Intake -> Credit -> Committee -> Product -> Committed -> Closed`. Evaluates exit requirements on every relevant event; advances only if requirements met AND no open hold AND no unanswered gate. Writes the stage log with a plain-words `why`. | issues, fraud decision, human replies | stage transitions, `HumanRequest`s, SLA timers | Humans, SLA |
| `stages/routing` | `route(role, deal, now)`: primary (assigned credit officer / RM / intake round-robin / amount-based committee / `tasha.reed` / `victor.hale`); if primary OOO then `backup` (chain with cycle guard, so `dana.whitfield -> marcus.lee`). | contacts, assignments | person id | Humans |
| `stages/sla` + `deadlines` | Timer per (deal, stage) at 100%/150%/200% of the stage SLA (`sla_hours_delegated` for delegated committee); alert to stage owner + RM, escalation to owner's `escalates_to`, second to `lauren.kim`. Deadline planner: `needed_by - now` vs. sum of **history-median** remaining stage hours (from `stage_events.csv`) to raise an at-risk alert and priority-order work. Suspended on hold/decline/close. | stage entries, clock | `Alert`s | Humans (message builder) |
| `humans/` | `HumanRequestManager` (create, dedupe, track, reply-timeout reroute to backup, then escalation via SLA); `Responder` protocol; `ScriptedResponder` (personas: fast / slow / OOO / never-answers, business-hours aware, seeded); `InteractiveResponder` (parks requests in the UI inbox); `comms` (deterministic message templates that always carry the required facts); `reply_parse` (keyword parser, Nemotron fallback, validated against allowed options). | requests, replies | `HUMAN_REPLY` events | Stage machine, API |
| `engine/core` | Owns queue, log, state, dispatch table `kind -> handler`. Handlers return new events/commands; only `apply()` mutates state. | everything | state, log | all |
| `engine/submission` | Pure projection `EngineState -> SubmissionFormat.json` keyed by folder; JSON-schema/enum validator (stage names, `purpose_category`, `product`, issue `KIND:target` grammar, ISO-8601 with `-06:00`, `null` for unknown). Refuses to write invalid output. | state | `submission.json`, validation report | CLI, API |
| `nemotron/` | OpenAI-compatible client with record/replay cache and circuit breaker; investigator agent; red-team generator + evaluator; VL extractor; prose polisher. | read-only `EngineQuery` API; raw files | advisory artifacts; validated fields | API (artifact retrieval), Engine only through the **validated-field gate** |
| `api/` | FastAPI; Pydantic schemas are the single contract source; SSE stream of event seq; engine lock (single writer). | engine | JSON | UI |
| `ui/` | React/Vite/Tailwind; force-graph for fraud graph. | API | pixels | human |

### Data Flow

**Per file arrival (the hot path, fully incremental):**

```
FILE_ARRIVED(deal=folder, path, t)
  1. loader: sha256 -> parse cache hit? else pypdf/csv parse -> raw text + metadata + page markers
  2. classify -> doc_type (+ confidence). Unknown/low confidence -> router: VL fallback (cached, validated) else type="other"
  3. extract -> fields with provenance; attributes for graph (preparer, phone, agent, vendor, remit acct,
     producer, creator, address, bank, guarantor id, EIN) + forensic features + deposit features (statements)
  4. DealFacts.update -> re-resolve canonical fields; re-run consistency + old-trick checks (cheap, pure)
  5. FraudGraph.add_edges(deal, attrs) -> returns affected attribute nodes -> re-score only their
     connected components + the arriving deal
  6. FraudDecision changed? -> if newly flagged: freeze deal, create fraud_hold request (to victor.hale
     via router), create/refresh FraudCase, set linked_deals/history_flags
  7. StageMachine.evaluate(deal): if exit requirements met and not frozen -> advance (log decision+why),
     enter next stage (start SLA timers, create human request if the new stage has a gate)
  8. schedule COMPLETENESS_CHECK at (last_arrival + quiescence Q) for this deal (replaces any earlier one)
```

**Quiescence rule (avoids false `MISSING_DOC`):** the stage machine advances *immediately* when every required doc is present (no waiting). But `MISSING_DOC`/`MISSING_PAGE` issues and the borrower `info_request` are only raised at `COMPLETENESS_CHECK`, i.e. Q sim-minutes (default 30; `config`) after the folder's last arrival. On the sample, folders finish in ~20 min, so Q = 30 min cleanly separates "still uploading" from "actually missing", and a late weekend paper on an in-flight deal simply re-opens evaluation.

**Timer / human loop:**

```
stage entered -> (gate? create HumanRequest to routed person) -> Responder.on_request(req, now)
   scripted: returns scheduled HUMAN_REPLY event (or none for never-answers/OOO persona)
   interactive: parked in inbox until POST /api/inbox/{id}/answer -> logged as HUMAN_REPLY at current sim time
REPLY_TIMEOUT (config: fraction of SLA, e.g. 25%, floor 2h) -> reroute: new request to person.backup (original stays in the list, unanswered)
SLA 100% -> alert; 150% -> escalation (escalates_to); 200% -> second escalation (lauren.kim)
HUMAN_REPLY: approve -> advance; decline -> stop with decision="declined"; request_info -> info_request to borrower, deal waits (timers continue)
```

**Output:** `SubmissionWriter` is called at any time (UI "download", end of batch run). `held` = the engine froze the deal and requested a hold (a human "places" it; the freeze is what guarantees "before Closed" even if Fraud Ops never answers). `fraud.reason` is the deterministic evidence string; investigator memo goes under extra key `fraud.investigator_memo` (ignored by the judge, shown in the UI).

### Stage machine semantics (decisions the roadmap should lock early)

| Question | Decision | Why |
|---|---|---|
| Missing statement at Credit entry: still send `credit_decision` request? | **No.** Send `info_request` (to borrower) and wait; send `credit_decision` once the packet is complete. | Rubric: "not pushing a deal forward while it waits on a document". Stage SLA timer keeps running, so a stuck deal still alerts/escalates. |
| `MISMATCH` found at Intake | Don't advance; `info_request` to borrower; issue stays open until a corrected doc resolves it. Fuzzy-equal (nickname, suffix, case, punctuation, "Ave"/"Avenue") is NOT a mismatch. | Tyler/Okafor are traps: strange is not fake. |
| Fraud flag raised at any stage | Freeze immediately (no stage exit), send `fraud_hold` request to Fraud Ops. `fraud_release` reply unfreezes; no reply keeps it frozen and escalates to `monica.salas` then `lauren.kim`. | A false flag costs a lot, but a hold request is reversible; the freeze is what protects the score. |
| `Closed` entry | Requires `funding_release` reply from `tasha.reed` AND no open flag AND disbursement account verification (equipment: vendor + remit acct recognized in history baseline or flagged). Final fraud re-screen runs on entry. | Matches `stages.json`; this is the last safety net. |
| Delegated vs chair | `amount <= delegated_max_amount` (249,999.99 read from `stages.json`) -> `priscilla.nguyen`, SLA 24h; else `harold.benson`, SLA 48h. | Data-driven. |
| `needed_by` | Parsed to ISO or `null` (`No specific date`). Deadline planner promotes deals with a date (priority = slack hours). Missed-date risk raises an `alert` to RM/stage owner. | "A good deal that misses its date is a failure too." |

## The Fraud Scorer

Principle: **rarity vs history x independent evidence families x agreement threshold**. No literal from the sample appears in code. The "idea" it encodes: *coordinated fakes reuse a small set of production resources (a preparer, an agent, a vendor/account, a document generator, a deposit-shaping script) that are rare in the bank's own history, and those resources co-occur.*

### Data structures

- **Bipartite graph** (networkx): deal nodes (current + history) and attribute nodes typed `preparer`, `preparer_phone`, `registered_agent`, `vendor`, `vendor_remit_acct`, `pdf_producer`, `pdf_creator`, `business_address`, `bank`, `guarantor_id` (DOB+DL / SSN4), `ein`, `account`. Edge = `(deal, attr, doc_id, confidence)`.
- **Canonicalization (`fraud/canon.py`)** is where generalization lives: casefold, strip punctuation, strip entity suffixes (`LLC/Inc/Co/Corp`) into a separate `suffix` field, normalize phones to digits, addresses to token sets. An attribute node has `base_key` (suffix-stripped) and `full_key`. Lookalikes = same `base_key` (or token-set Jaccard >= 0.8 / edit distance <= 2) but different `full_key` or different remit account.
- **History index (`fraud/baseline.py`)**, built once: `attr_value -> {history deal ids}`, per-type document-frequency, first-seen/last-seen dates (for novelty/burst), deposit feature distributions (percentile tables for `pct_multiple_of_100`, weekday concentration, count), and per-type "dominant value" shares (so the producer family knows FIS-like dominance exists for statements).

### Signal families (agreement is counted over families, not signals)

| Family | Signals (all generic, each returns a score in [0,1] plus a plain-words evidence string) | Independence note |
|---|---|---|
| **F1 Shared-rare entity** | For each attr node shared by >=2 deals (current or history): `rarity = -log((df_hist + 1)/(N + 1))` normalized; weighted by type (preparer, remit account, registered agent strong; bank, address weak). Common values (a registered agent used by 15 mostly-repaid deals, the dominant statement producer) get near-zero weight automatically. | Cross-deal, graph-derived. **Required** for any flag. |
| **F2 Novelty / burst** | Attr value absent from history before a date, or usage rate in the trailing window >> long-run rate (Poisson-style surprise). | Time-based; independent of F1 counts. |
| **F3 Lookalike** | Vendor/payee whose `base_key` matches a frequent history vendor while `full_key`/remit account differs; borrower name near-duplicates; remit account shared by a "vendor" with different legal-suffix. | Identity-based. |
| **F4 Document forensics** | Producer/creator rarity vs history `pdf_producer` column; **intra-deal anomaly** (bank statements carrying a template-tool producer instead of the dominant statement-generator producer observed across the batch); uniform CreationDate bursts; metadata/filename-class mismatch. | Metadata-based. |
| **F5 Deposit pattern** | Feature vector from statements (PDF transactions + CSV exports): `pct_multiple_of_100`, weekday concentration (entropy), count regularity; scored as percentile vs the history distribution (e.g. 100% vs median 8%). | Behavioral; computed on the same feature set as `monthly_deposits.csv`, so history deals are directly comparable. |
| **F6 Terms shape** | Amount just under an approval threshold read from `stages.json` (within ~2% below), young entity (formation < 24 months, same threshold as `stages.json`'s 7004 rule), "no specific date", round-number amounts. | Weak alone; only counts as corroboration. |

### Decision rule

```
For deal d (re-evaluated for every deal in the touched components):
  fam_hit[f] = max signal score in family f >= tau_f            (tau tuned per family on sample)
  flag(d)    = F1 hit  AND  count(fam_hit over F2..F6) >= 2      (>= 3 families total incl. F1)
               OR  any OLD_TRICK check fired                     (bank policy: straight to Fraud Ops)
  cluster    = connected component over strong F1 edges (rarity >= rho)
  score(d)   = noisy-OR over family maxima, reported 0..1 (UI only; the flag is the rule above)
Linking:
  linked_deals  = other current deals in d's cluster that satisfy flag-level evidence themselves
  history_flags = history deals sharing >= 2 independent families with the cluster
                  (e.g. preparer + remit account + deposit fingerprint), regardless of fraud_label
Hard exclusion: a deal whose only cross-deal evidence is ONE common/forgiven attribute never flags.
```

Why this holds on the traps: Harbor Tea shares a high-df address with mostly-repaid history deals, so F1 weight ~0 and nothing else fires. H-2511-010/H-2601-022 share only the producer (one family) so they are excluded from `history_flags`. Tyler's anomalies are strange but not shared and not rare-shared. Oakline shares the *real* high-frequency vendor and account: F1 near zero and no lookalike. Ridgeway (first ring deal) flags off history links (F1 with two history deals), F3 lookalike, F5 deposits, F4 forensics once the statements arrive. That is the "pattern spotted in the first few deals" behavior.

**Incrementality:** on each arrival only the touched attribute nodes and their component are re-scored; the decision records `flagged_at` = the sim time of the arrival that first crossed the threshold, and `stage_at_flag`. Signals are monotone in evidence except F1 weights, which depend on current-batch df; recompute is cheap (13 deals + 257 history).

**Explainability:** every `FraudDecision` carries `evidence[]` = list of `{family, signal, attr, value, rarity, deals[], doc_ids[]}`. The UI edge tooltip, the plain-words `reason`, and the investigator agent's tools all read this one structure.

**Red-team generalization hooks:** thresholds `tau_f`, `rho`, weights live in `config/fraud.yaml`, never in code. The red-team harness may *report* proposed tuning; humans apply it.

## Human-Response Layer

```python
class Responder(Protocol):
    def on_request(self, req: HumanRequest, now: datetime) -> Optional[ScheduledReply]: ...
    # ScheduledReply(at: datetime, answer: str, text: str|None)  -> becomes a HUMAN_REPLY event

class ScriptedResponder:   # headless, deterministic, seeded
    personas: dict[person_id, Persona]   # latency_dist(business-hours aware), policy(answer by type), p_no_answer
    # Defaults: fast = 5-30 min; slow = 3-6 h; ooo = never (until return); silent = never
class InteractiveResponder: # returns None; the UI inbox answers via POST -> HUMAN_REPLY at current sim time
```

- **OOO is two-layer:** (a) *static* routing: `route()` consults parsed `notes` OOO windows and skips to `backup` before sending (Priya's deal goes to `marcus.lee`, not `dana.whitfield`); (b) *dynamic*: judges' "no answer" is handled by `REPLY_TIMEOUT` re-route to backup, then SLA escalation. Both must exist because OOO is announced in the data but silence at judging is not.
- Replies can be free text (judges may type). `reply_parse` maps text to `approve|decline|request_info|place_hold|release|...` by keywords first; Nemotron fallback; result must be one of the gate's `options` or the reply is treated as unparsed (request stays open, a clarification is logged).
- Every request and reply is an event in the log, so replay reproduces interactive sessions.
- Persona set is a config file (`config/personas.json`); the red-team harness runs deals under all personas, which doubles as the MOVE-score regression suite (OOO, never-answers).

## Nemotron Sidecars (OFF the scored path)

All Nemotron calls go through `nemotron/client.py`: OpenAI-compatible (`base_url=https://integrate.api.nvidia.com/v1`), **record/replay cache keyed by `sha256(model, messages, tools, params)`**, hard timeout (<= 20s), circuit breaker (3 consecutive failures disables for the session), `temperature=0`. Config `nemotron_mode = off | replay | live`. A scored run in `off` or `replay` mode must produce the identical submission; CI/self-score runs use `off`.

| Sidecar | Reads | Writes | How it stays off the scored path |
|---|---|---|---|
| **Investigator (ReAct, native tool calling)** | `EngineQuery` read-only API: `get_case(id)`, `graph_neighbors(attr_or_deal)`, `get_doc_text(deal, doc)`, `compare_vendors(a,b)`, `search_history(field, value)`, `deposit_stats(deal)`, `rarity(attr)`. Same functions back the UI detail views. | `cases/<id>.json`: steps (thought/tool/observation), evidence summary, recommended action; surfaced as `fraud.investigator_memo` + UI "Case" tab. | Triggered by `FRAUD_FLAGGED` event as an async job after the flag is already emitted. Cannot call any mutating API. Its verdict is displayed, never used to set `flagged/held/linked`. Bounded steps (<= 8), JSON-validated tool args. Prompt-injection note: document text is untrusted data; tools return it fenced, and the agent has no write tools. |
| **Red-team generator + evaluator** | A trick *spec* schema: which attributes to reuse, forensic fingerprint, deposit shape, terms shape, camouflage level. Nemotron proposes specs (and flavor text); deterministic `synth.py` renders PDFs/CSVs (reportlab/fpdf + `pypdf` metadata) + `arrivals.jsonl` + ground-truth labels, mixing in benign decoys (messy-but-real, common-agent, big-international). | `runs/redteam/<id>/` with folder, arrivals, labels, and a report (detected?, time-to-flag, stage-at-flag, false flags, which families fired). | Never touches production state; evaluator runs a *fresh* Engine instance on the synthetic folder (the same `--folder/--arrivals` interface as the hidden set, which also proves the zero-code-change claim). Output is evidence for the pitch and for tuning `config/fraud.yaml` by hand. |
| **VL fallback extractor** | JPG/unknown layouts the router could not read deterministically. | A `VLProposal{field, value, confidence}` that goes through the **validated-field gate**. | Gate rules: schema and format check (EIN regex, date parse, money parse); **corroboration** against other docs' deterministic fields (name/DOB/license number appear in the application) -> `verified=true`; uncorroborated -> `verified=false`: may fill `extracted` only where it would otherwise be `null`, and can **never** raise a `MISMATCH`, a fraud signal, or a hold. Output cached by file hash so replays are offline and deterministic. The JPG is classified `guarantor_id` from context (single image in a folder lacking a PDF ID) so a failed VL call cannot create a false `MISSING_DOC:guarantor_id`. |
| **Prose polisher + reply parser** | Deterministic message templates; free-text replies. | Polished text only if it passes the validator (must contain borrower, RM, stage, duration, waiting-on, unblock action: regex/slot check); else template. | Templates already satisfy the rubric; polish is cosmetic. Reply parsing falls back to Nemotron only after keywords fail and must output an allowed option. |

Verify before building (LOW confidence today): exact model IDs for the text model and the VL model on build.nvidia.com, and whether native `tools=[...]` calling is reliable on Nano 9B v2 through that endpoint. If native tool calling is flaky, implement ReAct as a JSON-action loop (`{"action": ..., "args": ...}` parsed and validated) behind the same `EngineQuery` tools. The architecture is unaffected.

## FastAPI Surface and UI Data Needs

Pydantic models in `api/schemas.py` are the single source of truth. Generate `contracts/openapi.json`, TS types via `openapi-typescript`, and `contracts/fixtures/*.json` (real engine output from the sample week, snapshotted at 5 clock times). `MOCK=1` serves the fixtures so the UI never blocks on the engine.

| UI surface | Endpoints | Payload highlights |
|---|---|---|
| Header + clock controls | `GET /api/clock`; `POST /api/clock/advance {by:"4h"}`, `/set {t}`, `/reset`, `/play {speed}`, `/run-to-end` | `now`, `next_event_at`, `end_at`, play state. `/set` backwards triggers log-replay rebuild. |
| Live updates | `GET /api/stream` (SSE) | `{seq, kinds[]}` pings; UI refetches affected resources by `?since=seq` instead of the server pushing full state. |
| Pipeline board | `GET /api/deals` | per deal: `folder`, `legal_name`, `stage`, `status` (active/held/declined/closed), `entered_at`, `sla_pct`, `waiting_on`, `needed_by`, `priority`, `fraud{flagged,score}`, `open_issue_count`, `rm`, `owner`. |
| Deal detail | `GET /api/deals/{id}`; `GET /api/deals/{id}/docs/{doc_id}/file` | `extracted` with per-field `{value, doc, page, confidence, verified, source}`; `docs[]` with classified type + metadata; `issues[]` with evidence; `stage_log[]`; `human_requests[]`; `alerts[]`; `timeline[]` (event feed); `fraud` block incl. signal breakdown by family. |
| Inbox | `GET /api/inbox?status=pending`; `POST /api/inbox/{req_id}/answer {answer, text?}`; `GET/PUT /api/responder {mode, personas}` | request message, `to`, deal, options, age, routing note ("routed to Marcus Lee: Dana OOO"). Mode toggle interactive/scripted. |
| Alert feed | `GET /api/alerts` | level, to, stage, message, deal, at. |
| Fraud graph (hero) | `GET /api/fraud/graph?at=&cluster=` | `nodes[{id,type,label,rarity,df_hist,df_cur,flagged}]`, `edges[{deal,attr,doc,weight,evidence}]`, `clusters[]`; layout done client-side; evidence on edge click. Supports "light up as arrivals happen" because the graph is keyed by `first_added_at` per edge. |
| Cases | `GET /api/fraud/cases`, `/cases/{id}`, `POST /api/fraud/cases/{id}/investigate` | deterministic evidence + optional investigator steps (streamed or polled). |
| Submission | `GET /api/submission`; `POST /api/submission/write`; `GET /api/submission/validation` | live JSON, validation errors. |
| Drops | `POST /api/load {folder, arrivals, assignments?, set_name}` | Builds a fresh Engine (weekend drop, hidden set, red-team folders). |
| Nemotron | `GET /api/nemotron/status`, `POST /api/redteam/run`, `GET /api/redteam/report` | job status, report table. |

All mutating endpoints serialize through one engine lock. All reads are cheap projections of `EngineState`.

## Recommended Project Structure

```
Goldman-I/
  pyproject.toml
  .env.example                    # NVIDIA_API_KEY (real .env gitignored)
  config/
    engine.yaml                   # quiescence Q, reply timeouts, nemotron_mode, horizon
    fraud.yaml                    # family thresholds, weights, rho
    personas.json                 # scripted responder personas
    overrides/ooo.json            # optional OOO overrides if notes parsing misses
  dealpilot/
    domain/        models.py, enums.py, timeutil.py
    sim/           clock.py, source.py, queue.py
    ingest/        loader.py, pdftext.py, csvstmt.py, classify.py, kv.py, normalize.py, extract/{application,statement,formation,ein,id,financials,tax,quote,letter,other}.py
    facts/         deal_facts.py, authority.py
    checks/        completeness.py, consistency.py, known_fraud.py
    fraud/         canon.py, baseline.py, graph.py, signals/{shared,novelty,lookalike,forensic,deposit,terms}.py, scoring.py, clusters.py, cases.py
    stages/        machine.py, gates.py, routing.py, sla.py, deadlines.py, memo.py
    humans/        requests.py, responder.py, scripted.py, interactive.py, comms.py, reply_parse.py
    engine/        core.py, log.py, runner.py (CLI), submission.py, query.py (read-only EngineQuery)
    nemotron/      client.py, cache.py, investigator/{agent,tools}.py, redteam/{spec,synth,evaluate}.py, vl.py, prose.py
    api/           app.py, schemas.py, routes_*.py, mock.py
  ui/                             # Vite + React + Tailwind + force-graph
  contracts/       openapi.json, fixtures/
  tests/
    golden/        expected_sample.json   # hand-labeled READ ground truth (13 folders)
    test_determinism.py            # run twice -> identical submission hash; replay(log) == live
    test_traps.py                  # Tyler/Okafor/Garza/Harbor/Westfield/Oakline/LSFD -> zero false flags
    test_generalization.py         # red-team synthetic folders -> detection, no sample literals
  scripts/         selfscore.py, validate_submission.py, snapshot_fixtures.py
  data/            (gitignored: participant pack)
  runs/            (gitignored: event logs, nemotron cache, submissions, redteam output)
```

CLI contract (must work for the hidden set with no code edits):
`python -m dealpilot.engine.runner --folder <shared_folder> --arrivals <arrivals.jsonl> --history <history_dir> --rules <rules_dir> --assignments <json> --responder scripted --set sample --out runs/submission.json`

Use `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe` explicitly on this machine (plain `python` is the Store stub).

## Patterns to Follow

### Pattern 1: Event-sourced reducer with idempotent keys
**What:** `handle(event) -> list[Command]`; `apply(command) -> list[Event]`; state mutates only inside `apply`. Alerts/requests carry deterministic keys.
**When:** All engine behavior. Gives replay, scrubbing, determinism tests, and safe re-evaluation on late papers.
```python
@dataclass(order=True)
class Event:
    t: datetime; prio: int; seq: int
    kind: str = field(compare=False); payload: dict = field(compare=False)

def advance_to(self, t):
    while self.q and self.q[0].t <= t:
        ev = heapq.heappop(self.q)
        self.clock.set(ev.t)                 # clock moves with the event
        for cmd in self.handlers[ev.kind](self.state, ev):
            for new in self.apply(cmd):      # apply logs + mutates
                heapq.heappush(self.q, new)
    self.clock.set(t)
```

### Pattern 2: Rules-as-data
**What:** Load `stages.json` / `teams.json` / `known_fraud_checks` params once into typed config objects; engine code references `rules.stage("Credit").sla_hours`, `rules.delegated_max_amount`.
**When:** Always. A changed threshold or new person in the hidden set requires zero code changes.

### Pattern 3: Candidates-with-provenance for every extracted field
**What:** Never store a bare value. `Candidate{value, doc_id, page, confidence, source}`; canonical = authority rule; mismatches = disagreeing normalized candidates.
**When:** All `extracted.*`. Powers READ accuracy, `MISMATCH` detection, UI provenance chips and the VL validated-field gate with one mechanism.

### Pattern 4: Validated-field gate for anything non-deterministic
**What:** `gate(proposal) -> Accepted(verified|unverified) | Rejected(reason)`. Only `Accepted(verified)` may influence issues, fraud or stage decisions.
**When:** VL extraction, reply parsing, polished prose.

### Pattern 5: Record/replay for every LLM call
**What:** Cache by request hash; replay mode never touches the network.
**When:** All Nemotron calls. Makes demos and judge replays deterministic and offline-safe.

### Pattern 6: Contract-first with fixtures
**What:** Pydantic schemas -> OpenAPI -> TS types + fixtures; `MOCK=1` serves fixtures.
**When:** From hour 1, so the UI developer and the engine developer never wait on each other.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Keying by company name or filename
**What:** Using the extracted legal name or `01_Loan_Application.pdf` patterns to decide identity/type.
**Why bad:** `LSFD_docs/SCAN_*.pdf` and `loan app FINAL.pdf` break it; the hidden set will have new naming styles.
**Instead:** Deal = folder; type = content classifier.

### Anti-Pattern 2: Single-signal fraud flags
**What:** Flagging on "unusual producer" or "shared address".
**Why bad:** Harbor Tea's 15-deal address and the two benign DocuForge history deals are the exact false-flag traps; "each false flag costs a lot".
**Instead:** Family-agreement rule with a required cross-deal family.

### Anti-Pattern 3: Hard-coded sample literals
**What:** `if producer == "DocuForge"` or account `4471`.
**Why bad:** Hidden set uses a different trick; also fails the "no sample-specific literals" constraint.
**Instead:** Rarity, lookalike, forensic distribution, deposit percentile, all against the history baseline.

### Anti-Pattern 4: LLM in the scored path
**What:** Letting an agent decide a flag, a field, or a linked deal.
**Why bad:** Nondeterminism on a heavily penalized metric.
**Instead:** Sidecars write advisory artifacts; only the validated-field gate can feed back, and only verified, corroborated fields.

### Anti-Pattern 5: Advancing on first arrival, flagging "missing" on first arrival
**What:** Treating the folder as complete when the first file lands.
**Why bad:** Files trickle in over ~20 min; a premature `MISSING_DOC` is a false alarm (READ penalty) and a premature borrower `info_request` is noise.
**Instead:** Quiescence-gated completeness checks; immediate advance only when requirements are positively met.

### Anti-Pattern 6: Wall-clock anywhere
**What:** `datetime.now()`, `time.sleep()` pacing, or mtime-dependent logic.
**Why bad:** Breaks replay/scrub/determinism and hides SLA bugs.
**Instead:** Injected `SimClock`; UI "play" is just repeated `advance_to`.

### Anti-Pattern 7: Mutable shared state between API and engine
**What:** Route handlers poking at state.
**Why bad:** Races between SSE, play loop and interactive answers.
**Instead:** One engine lock; commands in, projections out.

## Scalability Considerations

This is a hackathon demo; the real concern is *hidden-set size and replay speed*, not users.

| Concern | Sample (13 deals, 173 files) | Hidden set (maybe 20 to 40 deals) | 1000s of deals (not needed) |
|---|---|---|---|
| Parse | pypdf per file, cached by sha256; seconds | same, cache cold on first run (budget a warm-up pass before judging) | process pool |
| Fraud re-score | incremental component rescoring; ms | same | same; history index already inverted |
| Replay/scrub | rebuild from log, parse cache warm; < 1 s | < 2 s | snapshots every N events |
| Nemotron | investigator per flagged case only; red-team offline | same, replay cache | queue |

## Suggested Build Order (priority: Goldman score > Nemotron > UI)

Dependencies drive order: you cannot score fraud before facts exist, cannot gate stages before issues exist, and the submission writer is the earliest end-to-end proof. Build a **thin vertical slice first, then deepen**.

| # | Component | Depends on | Deliverable / exit check | Owner |
|---|---|---|---|---|
| 0 | Contract: `schemas.py`, `submission` schema/validator, fixtures stub, repo skeleton, `.env`, rules loaders | none | `contracts/openapi.json` + 3 fixture snapshots committed; `MOCK=1` API runs. Unblocks UI immediately. | A (30-60 min), then B starts UI |
| 1 | `sim` (clock, queue, source) + `engine/core` + event log + submission writer (empty deals) | 0 | `runner` replays arrivals, writes a valid-but-sparse `submission.json` | A |
| 2 | `ingest`: loader, pdftext, classify, kv extractor, normalize | 1 | 13 folders classified correctly; `extracted` matches `golden/expected_sample.json` (hand-labeled by B in parallel) | A (+B golden labels) |
| 3 | `facts` + `checks` (completeness incl. 6-month window and "Page X of N", consistency with fuzzy norm, 5 OLD_TRICK) | 2 | issues correct on sample, **zero issues on trap deals** | A |
| 4 | `stages` machine + routing (OOO/backup) + `humans` (manager, scripted responder, templates) | 3 | stage_log, human_requests with right `to`; Priya routed to backup; never advances while waiting | A |
| 5 | `stages/sla` + `deadlines` + alerts/escalations | 4 | alerts at 100/150/200 with all four required message facts; needed_by priority | A |
| 6 | `fraud/`: baseline index, graph, signal families, decision rule, linking, `history_flags` | 2 (needs attrs + forensics + deposit features; can start in parallel with 3-5 once 2 lands) | Ring flagged at earliest arrival; Ridgeway first; both history deals linked; Harbor/Tyler/Oakline/Westfield/Garza unflagged | A (this is the critical path for FRAUD score; consider B pairing on F4/F5 signal feature extraction) |
| 7 | Self-score harness + determinism/trap tests; first full sample run; **freeze a scoring baseline** | 1-6 | `selfscore.py` report; hash-stable submission across two runs | A+B |
| 8 | `api/` real engine routes + SSE + interactive responder | 1, 4 | UI switches from mock to live by flipping one env var | A (with 4 done) |
| 9 | UI v1: board, clock controls, inbox, alerts, deal detail | 0 (mock), 8 (live) | usable end-to-end demo | B (parallel from hour ~1) |
| 10 | Nemotron client + record/replay cache + VL fallback + validated-field gate | 2 | JPG ID read & corroborated; engine unchanged in `off` mode | B (switch from UI once board/inbox are usable) |
| 11 | Investigator agent over `EngineQuery` | 6, 10 | Evidence case on the ring, shown in UI Case tab | B |
| 12 | Red-team generator + synth + evaluator | 6, 10 | Report: N synthetic tricks, detection rate, time-to-flag, false flags | B (Ezekiel reviews thresholds) |
| 13 | UI v2: fraud graph hero (light-up animation, edge evidence), polish | 6, 9 | demo-grade | B |
| 14 | Weekend-drop dry run: new folder + new papers on in-flight deals + Collections notice via `/api/load` or CLI | 7 | zero code edits needed; regressions caught by golden/trap tests | A+B |

**Critical path to the Goldman score:** 0 -> 1 -> 2 -> 3 -> 4 -> 5 and 6 in parallel with 3-5 -> 7. Nemotron (10 to 12) and UI v2 (13) are cut-able; the vertical slice at step 7 must exist by roughly hour 10 to 11 of 21 so the remaining time is hardening, Nemotron and demo.

**Work split with a mocked contract (2 people):**

- **Person A (Ezekiel: quant/engine):** steps 0-8, owner of determinism and `fraud/`. Starts by publishing the contract so B is never blocked.
- **Person B (finance/UI/pitch):** hour 0-2 hand-label `golden/expected_sample.json` and trap expectations (finance judgment on what "real" mismatches are; also review message templates, persona scripts, domain wording) while scaffolding Vite + Tailwind against fixtures; hours 2-9 UI v1 against the mock; hours 9+ Nemotron sidecars (10-12) and UI v2/graph; pitch throughout. Interface between them is only `contracts/` (OpenAPI + fixtures) and `config/*.yaml|json`.
- **Merge discipline:** repo already has a remote commit, pull first. Disjoint directories (`dealpilot/{ingest..stages,fraud,engine}` vs `ui/` + `dealpilot/nemotron`), contract changes go through PR-sized commits to `schemas.py` announced in chat.

## Research Flags for Phases

| Phase topic | Flag |
|---|---|
| Ingest / extraction (2) | Likely needs a quick data survey: run the classifier over all 186 files and eyeball low-confidence ones (statements named `may statement.pdf`, tax-return vs 7004, JPG, `LSFD` scans); page markers format (`Page X of N`) and CSV statement variants. |
| Fraud scoring (6) | Deepest risk. Needs a threshold-tuning pass on the sample and a hold-out sanity check via red-team before trusting it on the hidden set. |
| Nemotron integration (10-12) | Verify model IDs, tool-calling reliability, rate limits and Brev credits ($60) before committing to native tool calls vs JSON-action ReAct. |
| UI graph (13) | Standard patterns (react-force-graph); no research needed beyond choosing 2D vs 3D (choose 2D). |
| Stage machine / SLA (4-5) | Standard; the open questions are rubric interpretations listed in the decision table. |

## Open Questions

- How does the judge consume "answered" for `fraud_hold`: does a never-answering Fraud Ops still count as `held: true` if we froze the deal? (Plan: yes, report `held` as "engine froze and requested"; verify wording in the challenge statement, which is participant-only.)
- Whether `issues` in the submission is scored on end-state or on ever-raised. (Plan: emit open issues at end-of-run; keep resolved ones in an extra key.)
- Whether the weekend "notice from Collections" is a file inside an existing folder or standalone; the architecture handles both (unattached-doc matching by EIN/name/account), but the matching rule should be tested when the drop lands.
- Quiescence Q (30 min) and reply-timeout fractions are assumptions; tune against MOVE self-score.

## Sources

- Local, HIGH confidence: `data/participant/{README.md, SCHEMA.md, SUBMISSION_FORMAT.md}`, `rules/stages.json`, `contacts/teams.json`, `sim/clock.py`, `sim/arrivals.jsonl`, `sim/assignments.json`, `history/*.csv` headers, `rules/known_fraud_checks.md`, sample PDF text and metadata (Pecan Grove application and statement, LSFD scan).
- `.planning/PROJECT.md` (requirements, constraints, sample-ring analysis).
- Nemotron model facts, LOW confidence (third-party gateways only; not verified against NVIDIA): [Vercel AI Gateway: nemotron-nano-9b-v2](https://vercel.com/ai-gateway/models/nemotron-nano-9b-v2/api), [AIML API: nemotron nano 9b v2](https://docs.aimlapi.com/api-references/text-models-llm/nvidia/nemotron-nano-9b-v2), [Eden AI](https://www.edenai.co/models/nemotron-nano-9b-v2).
