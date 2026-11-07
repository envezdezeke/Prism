# Feature Research

**Domain:** Commercial-loan origination / deal-pipeline automation with cross-deal fraud-ring detection (hackathon build, judged by a Goldman rubric and the NVIDIA Nemotron track)
**Researched:** 2026-11-07
**Confidence:** MEDIUM overall. The rubric-driven prioritisation comes from PROJECT.md and is HIGH confidence. General LOS and link-analysis feature landscape is MEDIUM: I read vendor and practitioner pages, not product docs, and web searches returned nothing nCino-, Quantexa- or Linkurious-specific on stage gating, SLA or entity resolution. Fraud-signal catalogue is MEDIUM: practitioner claims, no peer-reviewed sources.

## How to read this file

"Table stakes" here means **a rubric line or hard constraint fails without it**, not "commercial LOS vendors have it". Real LOS suites (nCino, Blend, LendPipe, Newgen) ship hundreds of features (pricing, covenants, collateral, portals, e-sign, servicing). Almost none score in a 21h, 2-person build. Complexity is in hours of work for this team: LOW is under 1.5h, MED is 1.5-4h, HIGH is over 4h.

Governing constraints from PROJECT.md that shape every call below:
- Every scored output is deterministic. Nemotron is advisory or validated.
- False flags cost a lot, so a single weird signal must never trigger a hold.
- The hidden set uses a different trick, so no sample literals in detection logic.
- Priority when cutting: Goldman score > Nemotron > UI.

## Feature Landscape

### Table Stakes (rubric fails or constraint breaks without these)

#### A. Document intake (READ)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Arrival-gated ingest (only files whose `arrive_at` has passed) | Sim-clock semantics; peeking ahead is a correctness bug and breaks "re-runnable on a new drop" | LOW | One filter on `arrivals.jsonl` vs sim clock. Fold new papers on in-flight deals into the existing deal state. |
| Content-based document classification (not filename) | Rubric names `SCAN_*.pdf`, `loan app FINAL.pdf`, CSV exports, JPG. Commercial LOS vendors all advertise AI doc categorisation | MED | Deterministic cascade: file type, then PDF text keyword and layout signatures (e.g. "Statement Period", "Form 1120", "Page X of N"), then CSV header sniffing, then image goes to VL fallback. Return `(doc_type, confidence, evidence_snippet)`. |
| Field extraction with source doc and confidence per field | PROJECT.md requires it. Judges grade READ on facts, and provenance is what makes a flag explainable | MED | Fields: legal_name, EIN, amount, purpose_category, product, term, guarantor, stated revenue, needed_by. Regex plus label-proximity first. Store `{value, source_doc, page, confidence, method}`. |
| Completeness check: `MISSING_DOC` | Core READ requirement | LOW | Required-doc matrix per product and stage from `rules/stages.json` vs classified docs. |
| Page-completeness check: `MISSING_PAGE` ("Page X of N") | Named in rubric | LOW | Parse the "Page X of N" footer across files in a doc set. Report which page is absent. |
| Cross-document consistency: `MISMATCH:<field>` | Named in rubric | MED | Normalise before comparing (case, punctuation, "LLC" vs "L.L.C.", $ formatting, date formats) or you create false alarms. Compare name, EIN, amount, address, guarantor across app, tax docs, statements, ID. |
| Messy-but-real tolerance (Tyler, Okafor, LSFD scans) | "No false alarms" is graded. Missing a Form 7004 extension, a self-prepared return or a JPG ID must not flag | MED | Treat as a test fixture. Distinguish "unreadable" (low-confidence, ask a human) from "contradictory" (mismatch). Never emit MISMATCH on a low-confidence extraction. |
| The five OLD_TRICK checks exactly per `rules/known_fraud_checks.md` (STMT_TAMPER, REV_INFLATION, ID_MISMATCH, DUP_EIN, SHELL_ADDRESS) | Explicit scored FRAUD lines and the labelled history lets us self-validate | MED | Implement as rule-faithful functions. They are a regression baseline, separate from the new cross-deal graph signals. |

#### B. Pipeline and workflow (MOVE)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Six-stage state machine (Intake, Credit, Committee, Product, Committed, Closed) with exit requirements | Rubric: "stages in order" | MED | Data-driven from `rules/stages.json`. Guard function `can_exit(stage, deal)` returns `(ok, blockers[])`. |
| Hard block: never advance while a doc or human answer is outstanding | Named in rubric | LOW | Falls out of the guard above. The blocker list feeds alert text. |
| Human-gate routing | Rubric: "right human asked" | MED | Rules: credit officer with backup when OOO (dana.whitfield out 11/03-11/06), delegated approver vs committee chair at $250k, deal's RM, tasha.reed for funding, victor.hale or monica.salas for fraud holds. Read from `contacts/teams.json` plus OOO windows. |
| OOO / backup resolution | Priya's Bakery trap | LOW | `resolve_assignee(role, sim_time)`. Log "primary OOO, routed to backup X". |
| SLA timers (alert at 100%, escalate at 150%, second escalation at 200% to lauren.kim) | Explicit in PROJECT.md | MED | Sim-hours per stage from stages.json. Idempotent, so re-running a tick never double-fires. Escalate unanswered human requests on the same ladder. |
| Alert and escalation messages that say whose deal, which stage, how long, what it waits on, what unblocks it | Rubric grades message content | LOW | Deterministic templates with those five slots. Nemotron prose is optional polish. |
| Deadline prioritisation ("funds needed by") | Priya needs money Friday; rubric names needed-by dates | LOW | Compute slack = needed_by minus (now + remaining stage SLAs). Sort inbox and board by slack. Treat "no specific date" as a weak risk signal, not a deadline. |
| Audit trail: what was seen, decided and why, per step | PROJECT.md requires it. The team's prior RowdyHacks win rested on an auditable deterministic engine | LOW | Append-only JSONL `{sim_time, deal, stage, seen[], decision, reason, rule_id}`. Render in deal detail. |
| Human-response layer: interactive inbox plus scripted responder personas (fast, OOO, never-answers) | Unknown how judges will respond (live or headless) | MED | Same message bus both ways. Headless policy file picks persona per contact. Never-answers must trigger the escalation ladder. |
| Sim clock control (advance/scrub) | Judges drive time | LOW | Wrap `sim/clock.py` HTTP API. |

#### C. Fraud (FRAUD)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Entity graph: deals linked to shared entities | Core method (Neo4j, Linkurious and Quantexa all centre on shared-attribute links across applicants) | MED | Bipartite deal-to-entity graph in networkx. Node types: preparer, preparer phone, registered agent, vendor name, remit account, PDF producer, PDF creator, address, bank, guarantor, EIN, signer. Include history deals so current deals link back to `H-...`. |
| Entity normalisation (light entity resolution) | Without it, "214-555-0187" vs "(214) 555-0187" never link. Real tools treat fuzzy entity resolution as the foundation | LOW-MED | Normalise phones, addresses, names (strip suffix punctuation, case-fold) and accounts (last 4 plus bank). Keep raw value for evidence display. |
| Rarity / IDF weighting of shared entities against history baseline | The thing that separates Harbor Tea's 15-deal address (benign) from a 5-use registered agent. Required to hold false flags down | MED | `w(e) = log(N_hist / (1 + df(e)))`. Plus a recency factor, such as "first seen in history only in Aug 2026". Common entities (FIS Statement Services producer, Northstar's address) get near-zero weight automatically. |
| Document-forensics signals: PDF Producer/Creator, creation vs mod date, doc-class vs producer mismatch | Practitioner sources agree metadata is a triage signal. Here it is the sample ring's shared tell | LOW-MED | pypdf `metadata`. Compute per-doc-class producer distribution from history and flag producer rarity within class (a bank statement not produced by the bank's usual system). Never hard-code "DocuForge". |
| Deposit-pattern anomaly signals | Sample history members share 100%-round-$100 deposits on Mon/Thu vs history median 8% | MED | Features: share of deposits that are multiples of 100 (or 1000), weekday entropy or concentration, optionally Benford first-digit chi-square. Score each as a z-score or percentile against history, not an absolute threshold. |
| Lookalike detection for vendors and accounts | Sample trick: "Metroplex Equipment Supply LLC" vs the real ", Inc." with different remit account | MED | Normalised-name similarity (token-set ratio / Jaro-Winkler or difflib, no new deps) between a new vendor and frequent historical vendors. Flag when similar name but different remit account. Same for near-identical names or EINs. |
| Multi-signal agreement gate | PROJECT.md: false flags cost a lot, so require several independent signals | MED | Group signals into independent families (shared-identity-entity, doc-forensics, deposit-behaviour, vendor-lookalike, structuring such as amount just under $250k, entity youth). Hold only if at least 2-3 families fire above their thresholds on the same cluster. A single family goes to "watch", not "hold". |
| Cluster formation and scoring | Need a unit to flag and to link | MED | Connected components over only the edges that pass a rarity threshold, not over all edges. Otherwise common entities fuse the whole graph. |
| Explainable score: per-signal contributions with evidence | Fraud Ops and judges need "why". Also required for the audit trail | LOW-MED | Return `{deal, score, signals:[{family, entity, weight, evidence_docs[]}]}`. |
| Early warning: hold as early as possible, ideally in the first few deals | Rubric: earlier is scored higher, and "pattern spotted in the first few deals" | MED | Re-score on every arrival, not at the end of the week. Hold request fires the first tick the agreement gate passes. Build incrementally: signals that need no cluster (producer rarity, deposit anomaly, vendor lookalike) can accumulate on one deal and become decisive when a second deal shares an entity. |
| Request fraud hold before Closed to victor.hale / monica.salas | Rubric: held before Closed | LOW | A hold is a human-gate request plus a stage block. Gate in the state machine. |
| Link-back to history (`history_flags`) and to other current deals | "Find the rest" is scored | LOW-MED | For each flagged cluster, list history deals sharing at least 1 rare entity plus at least 1 additional anomalous family. Do not flag history deals on a single shared entity. |
| Trap suite as regression tests: Tyler, Okafor, Garza, Priya, Westfield, Harbor Tea, LSFD, Oakline | Zero false flags is the make-or-break metric | LOW-MED | One assertion per trap: "not held". Run on every change. This is the cheapest insurance in the project. |
| Submission JSON in `SUBMISSION_FORMAT.md` format, keyed by folder name | Scored artifact | LOW | Write a validator against the format doc early. |
| Re-runnable with `--folder` / `--arrivals` and no code changes | Weekend drop and hidden set | LOW | Argument plumbing only. Make sure no path or name is hard-coded. |

#### D. Demo and UI (minimum bar)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Pipeline board with deals by stage, status chips (waiting on / held / escalated) | Judges need to see MOVE | MED | Kanban columns by stage, deadline badge, SLA progress bar. |
| Deal detail: extracted facts with source and confidence, issues, stage log, next action | READ plus audit trail visible | MED | Facts table with click-to-source doc name. |
| Inbox and alert feed | Shows right-human routing and escalation | LOW-MED | One list. Items show who, why, what unblocks. |
| Fraud graph view | Hero visual for the track | MED | See differentiators for the version that wins. Minimum is a force graph with deal nodes and entity nodes plus edge tooltips. |

### Differentiators (competitive advantage)

Ordered by value for the rubric (Goldman first, then Nemotron, then UI).

#### Goldman-scored differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Generic signal families defined over distributions, not values (the hidden-set insurance) | Directly attacks "different trick". Each signal is "this attribute is rare vs history within its class" or "this deal's behaviour is an outlier vs history", which works for any trick that reuses some attribute | MED | Define the attribute-extraction layer widely (every PDF metadata key, every named party, every phone, address, account, signer, email domain, template fingerprint) and let IDF decide what matters. Candidates the hidden trick may use: shared phone or email, same notary or signer, identical document layout hash, same statement balances reused with new names, near-duplicate EINs, shared guarantor across LLCs, shared IP or upload metadata, address reuse with different suite numbers. |
| Template fingerprint: structural hash of a PDF (page size, fonts, producer, object count, layout of text blocks) | Catches a ring that spoofs the Producer string (a known limitation of metadata-only checks) but reuses a generator | MED-HIGH | Cheap version: tuple of (page size, font set, producer, creator, text-line count bucket). Compare across docs of the same class. Rarity-weight the tuple. Do this after the basic metadata signal works. |
| Statement-vs-deposit-summary reconciliation | The data pack ships monthly deposit summaries. A stated-revenue or statement mismatch against them is a strong, independent family | MED | Overlaps REV_INFLATION. Reuse its code. |
| Youth-of-entity and just-under-threshold structuring signals | Weak alone, strong in combination. "$246,000 vs a $250k committee threshold" is a classic threshold-avoidance tell, and it generalises to any delegated limit | LOW | Amount within X% below any approval threshold from `stages.json`. Entity age vs the history distribution. Weight these as soft evidence, never sufficient. |
| "First seen" temporal novelty: a preparer, agent or producer that is absent from history until recently, then appears in several current deals | Explains why the ring is a ring and not a coincidence. Very compelling to narrate | LOW | `first_seen_in_history` per entity from the history deals. Feed it into rarity weight. |
| Counterfactual explanation: "if we remove signal X, the cluster is still flagged" | Shows the multi-signal gate is robust and not hanging on one tell. Addresses the false-flag worry in the pitch | LOW | Compute leave-one-family-out score for each flagged cluster. Show in evidence. |
| Self-evaluation harness on history: precision/recall of the detector on the 12 labelled `fraud_confirmed` plus the unlabelled ring members | Judges (like the RowdyHacks ones) reward audit and backtest. Gives the numbers for the pitch, and detects over-flagging before it happens | MED | Leave-one-out style: score each history deal as if it arrived in sequence. Report false-flag rate on the 257. |
| Watch tier (soft flag) vs hold tier | Handles "strange is not fake" in the product, not only in code. The Harbor Tea case becomes "watched" rather than "held" | LOW | Maps to the explainable score. Only the hold tier affects the submission's fraud list. |

#### Nemotron-track differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| ReAct fraud-investigator agent with tools | Matches "agents that plan and execute, tool integration". Judges can watch a visible thought, tool, observation trace | MED-HIGH | Tools (thin wrappers over the engine, read-only): `graph_neighbors(entity)`, `get_doc_metadata(deal)`, `compare_vendors(a,b)`, `history_search(entity)`, `deposit_stats(deal)`, `get_extracted_fields(deal)`. Output: a structured evidence case (cluster, ranked evidence, recommended action, caveats) for Fraud Ops. Cap steps (6-8) and set timeouts. Advisory only: cannot change a hold. Cache traces so the demo is deterministic. |
| Red-team scenario generator plus detector evaluation | The strongest "agent simulation and eval" story, and directly evidences generalisation to the hidden set. The pitch becomes "we measured what we catch" | HIGH | Nemotron proposes new trick specs as JSON (which attribute is shared, how many deals, noise level, camouflage). A deterministic synthesiser injects those into copies of the sample folder/history. Run the detector, report per-trick catch rate, time to hold, and false flags on the unchanged benign deals. Include a few adversarial variants (spoofed producer, rounded deposits only in some deals). Use findings to tune thresholds once. Constrain generator output to a schema so a bad LLM output cannot crash the run. |
| VL fallback document reader | Multi-modal checkbox. Handles the JPG ID and unknown layouts | MED | Nemotron VL reads the image, then deterministic validators (EIN checksum or format, date parse, name matches app) accept or reject. Mark as "VL-extracted, validated" in provenance. Never let it alone create a MISMATCH. |
| Nemotron-written plain-words messages with deterministic template fallback; free-text reply parser | "Real-world use" and a natural human-loop story | LOW-MED | Reply parser maps free text to an enum (`approve`, `reject`, `need_info`, `delegate`, `ooo`) with a confidence. Anything under the threshold re-asks. Messages must still carry the five slots. |
| Multi-agent framing: Intake reader, Pipeline conductor, Fraud investigator, Red-team (distinct roles on a shared event bus) | The track names multi-agent systems. Mostly framing around components that already exist | LOW (framing) | Do not build an orchestration framework. Name the roles in the UI trace and the README only where they genuinely map to code. |

#### UI differentiators (fraud graph as the hero)

Compelling graph demos share these traits (practitioner consensus across link-analysis vendors, MEDIUM confidence): few nodes, obvious colour semantics, and a visible narrative of "how did we get here".

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Edge-by-edge "ring lights up" replay driven by the sim clock | Shows early warning visually: nodes appear as papers arrive, the cluster turns red at the moment of the hold | MED | Graph state is a pure function of (sim_time, engine events). Scrubbing the clock re-renders. This is the single best demo moment. |
| Rarity-encoded edges: thickness or colour by IDF weight; common shared entities (FIS, Northstar) drawn faint or collapsed | Visually answers "why not flag Harbor Tea?" | LOW-MED | Faint grey edge, with label "used by 15 deals, 93% repaid". |
| Click an edge to see evidence: field values side by side, doc and page, and rarity stat ("5 uses in all history") | Explainability on screen | MED | Side panel. This is where judges read the proof. |
| Distinct node shapes and colours: current deals, history deals (hollow, with repayment status), entities by type | Reads at a glance, and shows the history link-back | LOW | Past-due history deal in amber. Funded and current in neutral. |
| Signal-family checklist per cluster ("4 of 5 independent signals agree") | Makes multi-signal logic visible and defends against false flags | LOW | Small pill row: Shared preparer, Producer rarity, Vendor lookalike, Deposit pattern, Structuring. |
| Investigator trace panel beside the graph | Ties Nemotron track to the hero visual | MED | Stream steps as a timeline. Pre-record on the demo path in case the API is slow. |
| Light fintech design system: neutral off-white background, single accent, tabular numerals for money, restrained status colours (red only for holds), generous whitespace, consistent chips | Targets best-design ambition. Light, trustworthy, not dashboard-cluttered | MED | Tailwind tokens defined once. Use real data throughout the demo, no lorem ipsum. |

### Anti-Features (do not build)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Supervised fraud classifier on `fraud_label` | "ML sounds credible" | Only 12 positives, old tricks only, and the sample ring is labelled `none` in history. It will not carry to a new trick and raises false flags | Rarity plus anomaly families with an agreement gate, validated on history |
| Hard-coded sample literals (DocuForge, Delacroix, 4471, Metroplex) | Fastest way to catch the sample ring | Zero value on the hidden set, and it breaks the stated generalisation constraint and the judges' "idea, not examples" bar | Generic rarity, lookalike, forensic and distributional signals |
| Let an LLM decide holds, extractions or links | Looks agentic | Variance on a heavily penalised false-flag metric. Breaks the determinism constraint | LLM proposes, deterministic engine validates, then acts |
| Single-signal hold (e.g. "DocuForge producer, so hold") | Early warning scores more | H-2511-010 and H-2601-022 used the same producer and repaid normally. This is the exact false-flag trap | Watch tier for one family. Hold needs 2-3 independent families |
| Flag every history deal that touches a shared entity | Maximises "find the rest" recall | Harbor Tea's 15-deal address would flag 15 good deals | Link-back requires a rare entity plus a second anomalous family |
| Community detection (Louvain/Leiden), GNNs, graph embeddings | Standard in fraud-ring literature | The data is small (about 270 deals). Components over rarity-filtered edges are enough, explainable and fast. Embeddings are not explainable to a judge | Connected components on filtered edges, optionally with Louvain only if one component is oversized |
| Full commercial-LOS scope: pricing engine, covenants, collateral, spreading, borrower portal, e-sign, servicing | Real suites (nCino etc.) have them | Not in the rubric and eats the budget | Stay on READ, MOVE, FRAUD |
| Full financial spreading and credit-memo scoring (DSCR, ratios, risk rating) | "Real lenders do it" | Not scored, and invites wrong-number risk | Extract stated facts only. Optional Nemotron credit-memo text from already extracted facts |
| Real auth, multi-user, DB, RBAC | "Production-ready" | PROJECT.md out of scope | Local files and a persona selector |
| Real email, Slack or SMS integrations | Realistic notifications | Setup time, nothing to score | In-app inbox only |
| Real-time streaming or websockets everywhere | Polished feel | Sim clock is discrete. Polling the API is enough | Poll after each clock tick |
| Heavyweight graph DB (Neo4j) | Industry standard for rings | Setup and deployment risk at 21h for under 300 deals | networkx in-process, export JSON for the front end |
| Generic OCR pipeline for every document | "Handles anything" | Most documents are text PDFs. OCR stack is slow and brittle | Text-layer parse first, Nemotron VL only for the images and scans that fail |
| Fully free-form chat assistant | Easy to demo | Reads as "a chatbot", which the NVIDIA track explicitly discounts | Agents with tools and structured outputs |
| Fancy 3D or physics-heavy graph effects | Looks impressive | Slow, hard to read, hides evidence | 2D force layout, pinned positions per cluster, readable labels |
| Auto-closing deals without confirmation | Faster MOVE | Violates the human-gate model and loses "right human asked" credit | Always route committed and funding steps through the gate |

## Feature Dependencies

```
Arrival-gated ingest
    └──requires──> sim clock wrapper
    └──enables──> Content-based classification
                      └──enables──> Field extraction (provenance, confidence)
                                        ├──enables──> Completeness (MISSING_DOC / MISSING_PAGE)
                                        ├──enables──> Cross-doc MISMATCH
                                        ├──enables──> OLD_TRICK 5 checks
                                        └──enables──> Entity extraction for graph

Entity extraction + normalisation
    └──requires──> Field extraction + PDF metadata + vendor/remit parsing
    └──enables──> Entity graph (current + history)
                      └──enables──> Rarity (IDF) weights  <──requires── history baselines
                                        └──enables──> Cluster formation
                                                          └──enables──> Multi-signal agreement gate
                                                                            ├──enables──> Hold request  ──requires──> Human-gate routing
                                                                            ├──enables──> history_flags + current-deal linking
                                                                            └──enables──> Explainable score + counterfactual

Doc-forensics, deposit-anomaly, vendor-lookalike, structuring signals
    └──require──> history distributions (per doc class, per month)
    └──feed──> Multi-signal agreement gate

State machine + stage guards
    └──requires──> Field extraction + completeness checks (blockers)
    └──enables──> Human-gate routing + OOO backup
                      └──enables──> SLA timers → alerts → escalations
                      └──enables──> Deadline prioritisation
    All of the above ──write to──> Audit trail

Submission JSON  ──requires──> state machine log + fraud gate + link-back + validator
Re-runnable CLI  ──requires──> no hard-coded paths or literals anywhere above

Investigator agent   ──requires──> graph + tools API + cluster output   (enhances explainable score, advisory only)
Red-team generator   ──requires──> synthesiser + whole detector run + history harness  (enhances threshold tuning)
VL reader            ──requires──> classification fallback hook + deterministic validators
LLM messages/reply parsing ──requires──> template messages + human-response layer

UI board / deal detail / inbox ──require──> engine REST endpoints
Graph hero view ──requires──> graph JSON with edge weights + evidence + sim-clock-driven state
Graph replay ──requires──> engine event log with timestamps

Single-signal hold ──conflicts──> Zero false flags
Hard-coded literals ──conflicts──> Hidden-set generalisation
LLM-decides-hold ──conflicts──> Determinism constraint
```

### Dependency Notes

- **Entity graph requires extraction and metadata:** if the preparer, vendor and remit-account fields are poorly extracted, nothing downstream links. Extraction of those specific fields (not only the loan-application fields) is on the critical path for FRAUD. Add them to the extraction spec explicitly.
- **Rarity requires history baselines:** build the history feature tables (entity document frequency with first-seen date, per-doc-class producer distribution, deposit-pattern distributions) once, before any signal. Everything else reads from them.
- **Agreement gate precedes hold, linking and explanation:** these three are cheap once the gate returns structured evidence. Design the gate's return type first.
- **SLA, escalation and prioritisation all depend on state machine plus routing:** build them in that order, not in parallel.
- **Red-team generator depends on a stable detector:** do it last among engine features. It consumes everything and its main value is evidence plus one tuning pass.
- **Investigator agent is independent of the scored path:** it can be developed in parallel by one person once the tools API exists, with no risk to the submission JSON.
- **Graph replay requires a timestamped event log:** if the engine only emits final state, the best demo moment is impossible. Log events with sim_time from day one.

## MVP Definition

### Launch With (v1: the scored path, roughly the first 12-14h)

- [ ] Arrival-gated ingest, content classification, field extraction with provenance (including preparer, vendor, remit account, PDF metadata) — everything downstream reads it
- [ ] MISSING_DOC / MISSING_PAGE / MISMATCH with normalisation, validated on the trap folders — READ points without false alarms
- [ ] OLD_TRICK five checks — explicit FRAUD lines, and the history labels give a test set
- [ ] State machine with guards, routing with OOO, SLA ladder, deadline prioritisation, audit log — all of MOVE
- [ ] History baselines, entity graph, rarity weights, forensic, deposit and lookalike signals, agreement gate, hold request, link-back — the FRAUD core
- [ ] Trap regression suite and history self-evaluation — protects the false-flag metric
- [ ] Submission JSON writer plus format validator, `--folder`/`--arrivals` CLI, scripted responder personas — the scored artifact
- [ ] Minimal UI: board, deal detail, inbox, basic force graph with edge evidence tooltips — enough to demo

### Add After Core Works (v1.x: roughly the next 5-6h, in this order)

- [ ] ReAct investigator agent with trace panel — highest-value Nemotron item for the least work, and it needs only the tools API
- [ ] Red-team generator and detector evaluation (limited to 3-5 tricks) — generalisation evidence, and a tuning pass
- [ ] Graph replay driven by sim clock and rarity-encoded edges — the hero demo moment
- [ ] VL fallback reader for the JPG ID — cheap multi-modal checkbox
- [ ] Nemotron message polish and free-text reply parser
- [ ] Counterfactual leave-one-family-out explanation and watch tier display

### Future Consideration (after the hackathon)

- [ ] Template structural fingerprinting beyond the cheap tuple — high value in production but time-risky now (include the cheap version in v1.x only if signals are idle)
- [ ] Louvain community detection for large graphs
- [ ] Real integrations (email, Slack, LOS APIs), persistence, auth
- [ ] Financial spreading and credit scoring

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Ingest + classification + extraction w/ provenance | HIGH | MEDIUM | P1 |
| MISSING_DOC / PAGE / MISMATCH with normalisation | HIGH | MEDIUM | P1 |
| OLD_TRICK five checks | HIGH | MEDIUM | P1 |
| State machine, guards, hard-block on waiting | HIGH | MEDIUM | P1 |
| Human-gate routing + OOO backup | HIGH | MEDIUM | P1 |
| SLA ladder + unanswered-request escalation | HIGH | MEDIUM | P1 |
| Deadline prioritisation | HIGH | LOW | P1 |
| Audit trail (seen / decided / why) | HIGH | LOW | P1 |
| History baselines (entity df, producer, deposit) | HIGH | MEDIUM | P1 |
| Entity graph + normalisation | HIGH | MEDIUM | P1 |
| Rarity (IDF) weighting | HIGH | MEDIUM | P1 |
| Forensics, deposit, lookalike signals | HIGH | MEDIUM | P1 |
| Multi-signal agreement gate + hold request | HIGH | MEDIUM | P1 |
| history_flags + current-deal linking | HIGH | LOW-MED | P1 |
| Trap regression suite + history self-eval | HIGH | LOW-MED | P1 |
| Submission JSON + validator + re-runnable CLI | HIGH | LOW | P1 |
| Scripted responder personas + inbox | HIGH | MEDIUM | P1 |
| Minimal UI (board, detail, inbox, graph) | MEDIUM | MEDIUM | P1 |
| ReAct investigator agent | HIGH (Nemotron) | MED-HIGH | P2 |
| Red-team generator + detector eval | HIGH (Nemotron, generalisation) | HIGH | P2 |
| Graph replay on sim clock | HIGH (demo) | MEDIUM | P2 |
| Rarity-encoded edges + evidence side panel | MEDIUM | LOW-MED | P2 |
| VL fallback reader | MEDIUM (Nemotron) | MEDIUM | P2 |
| Nemotron message writer + reply parser | MEDIUM | LOW-MED | P2 |
| Counterfactual explanation, watch tier | MEDIUM | LOW | P2 |
| Light fintech polish pass | MEDIUM | MEDIUM | P2 |
| Template structural fingerprint (full) | MEDIUM | MED-HIGH | P3 |
| Multi-agent role framing in docs and UI | LOW | LOW | P3 |

**Priority key:**
- P1: needed for rubric points or to protect the false-flag metric
- P2: Nemotron-track and demo value, add after P1 is stable
- P3: nice to have

## Competitor Feature Analysis

Reference points only; none are being cloned. Findings are from vendor and practitioner pages (MEDIUM/LOW confidence).

| Feature | Commercial LOS (nCino, Blend, LendPipe, Newgen) | Link-analysis tools (Linkurious, Neo4j, Quantexa) | Our Approach |
|---------|------------------------------------------------|---------------------------------------------------|--------------|
| Doc intake | AI categorisation, field extraction, audit trails | n/a | Deterministic cascade plus VL fallback, provenance on every field |
| Workflow | Configurable stages, tasks, document checklists | n/a | Data-driven stages from `stages.json`, guards, SLA ladder, simulated humans |
| Fraud linking | Usually a separate module or a third-party integration | Shared-attribute graphs (phone, address, SSN across applicants), fuzzy entity resolution, community detection | Rarity-weighted shared-entity graph over current plus history, filtered components |
| Doc forensics | Third-party (metadata, fonts, template matching, cross-application reuse) | n/a | Producer/creator rarity within doc class, cheap structural tuple, deposit distributions |
| Explainability | Audit logs | Visual evidence on the graph | Per-signal contribution with evidence and counterfactual |
| Human-in-loop | Task assignment, approvals | Analyst triage | Routed requests with backup, scripted personas for headless runs |

## Sources

- PROJECT.md (`C:/Users/ezeki/hack/Goldman I/.planning/PROJECT.md`) — rubric, data pack, sample ring analysis, constraints. HIGH confidence for requirements and priorities.
- [Neo4j: Improving first-party bank fraud detection with graph databases](https://neo4j.com/blog/first-party-bank-fraud-detection-graph-databases) — ring structure and shared-contact-detail pattern. MEDIUM.
- [Neo4j white paper: Fraud detection with graph databases](https://go.neo4j.com/rs/710-RRC-335/images/Neo4j_WP-Fraud-Detection-with-Graph-Databases.pdf) — synthetic identity combinatorics. MEDIUM.
- [Linkurious: synthetic identity fraud](https://linkurious.com/blog/synthetic-identity-fraud/) — shared data points across applicants. MEDIUM.
- [Ewance challenge: detect coordinated fraud rings via link analysis](https://ewance.com/en/challenges/detect-coordinated-fraud-rings-via-link-analysis-at-a-neoban-data-mining-master/) — multi-relation graph plus community detection (considered, then deferred for scale reasons). LOW-MEDIUM.
- [Gartner commercial LOS market guide 2024 (via Nucleus)](https://www.nucleussoftware.com/resource/Gartner-Commerical-Loan-Origination-System-Markert-Guide-2024.pdf) — CLOS process stages. MEDIUM.
- [GetApp: commercial loan workflow management](https://www.getapp.com/finance-accounting-software/commercial-loan/f/workflow-management/?page=2) and [document management](https://www.getapp.com/finance-accounting-software/commercial-loan/f/document-management/?page=2) — commercial LOS feature lists. LOW-MEDIUM.
- [DocuClipper: bank statement fraud detection](https://www.docuclipper.com/docs/understanding-bank-statement-fraud-detection/), [Bectran: detect forged bank statements](https://bectran.com/post/detect-forged-bank-statements), [DEV: AI-generated fake documents, what PDF metadata can detect](https://dev.to/iurii_rogulia/ai-generated-fake-documents-what-pdf-metadata-can-detect-46e2), [DEV: KYC vs document forensics](https://dev.to/iurii_rogulia/kyc-vs-document-forensics-why-kyc-platforms-miss-pdf-fraud-2edn) — producer/creator checks, date gaps, template fingerprinting, cross-application document reuse, and the caveat that metadata is forgeable and best used as a triage signal. LOW-MEDIUM (vendor and practitioner claims).
- Benford, round-number and weekday-concentration signals: standard forensic-accounting practice, from general knowledge (not re-verified this session). The sample ring's own history gives the empirical baseline (8% median vs 100%).

## Gaps to flag for requirements and phase research

- Exact `SUBMISSION_FORMAT.md` field semantics (what "linked deals" and `history_flags` must contain, how hold timing is scored) were not available to me. Confirm before building the writer.
- `rules/known_fraud_checks.md` thresholds for the five OLD_TRICK checks must be implemented verbatim; they were not in my input.
- Nemotron endpoint latency and rate limits are unmeasured. The investigator and red-team features need a quick spike before commitment, with a cached-trace fallback for the demo.
- Agreement-gate thresholds (how many families, what weights) need tuning on history plus the trap suite. Budget a dedicated tuning hour.

---
*Feature research for: DealPilot (commercial-loan origination automation + cross-deal fraud-ring detection)*
*Researched: 2026-11-07*
