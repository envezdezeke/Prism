# Requirements: DealPilot

**Defined:** 2026-11-07
**Core Value:** Catch the cross-deal fraud ring before money goes out, without blocking good deals, using a method that carries over to the hidden set's different trick.

Owner key: **E** = Ezekiel (engine, fraud, Nemotron) · **J** = Jesse (labels, UI, pitch).

## v1 Requirements

### Foundations (FND)

- [ ] **FND-01**: Engine only sees a file once the sim clock has passed its `arrive_at` (single `visible_files(now)` layer; ties sorted by path). (E)
- [ ] **FND-02**: All times are emitted as fixed `-06:00` ISO strings; money is handled as integer cents. (E)
- [ ] **FND-03**: Rules load as data from `stages.json`, `teams.json`, `config/fraud.yaml`. The engine contains no folder names, company names or trick literals. (E)
- [ ] **FND-04**: The same input produces byte-identical submission JSON on two runs (determinism test). (E)
- [ ] **FND-05**: CLI runs a full sim on any `--folder` + `--arrivals` (sample, weekend drop, hidden set) with no code changes and writes `out/submission.json`. (E)
- [ ] **FND-06**: Submission validator rejects output that breaks `SUBMISSION_FORMAT.md` (keys, enums, `KIND:target` issues). A crash on one deal never prevents the file being written. (E)
- [ ] **FND-07**: Pydantic API contract + JSON fixtures exist so the UI can be built against `MOCK=1` before the engine is done. (E→J)
- [ ] **FND-08**: Hand-labelled golden expectations for the 13 sample deals (`eval/gold.json`) and a self-score script compare engine output against them. (J, script E)

### Read the folder (READ)

- [ ] **READ-01**: Each PDF/CSV/JPG is classified by content (application, guarantor ID, certificate of formation, EIN letter, bank statement + month, financial statements, tax return, Form 7004, request letter, equipment quote, other). The classifier never uses the filename and never crashes. (E)
- [ ] **READ-02**: Extract legal_name, EIN, amount_requested, purpose_category, product, term_months, guarantor_name, annual_revenue_stated, needed_by (ISO or null), each with source doc and confidence. (E)
- [ ] **READ-03**: Extract graph attributes: preparer name/firm/phone, registered agent + address, vendor name + remit bank/account, PDF producer/creator, business address, bank, guarantor DOB/DL, deposit features. (E)
- [ ] **READ-04**: Tyler's JPG ID is read by OCR (RapidOCR). An unreadable image counts as present-but-unverified, never as a mismatch. (E)
- [ ] **READ-05**: `MISSING_DOC:<doc>` uses the requirements for the stage, the product and the business's age (Form 7004 accepted only for businesses under 2 years old; bank statements cover the 6 most recent full months). It fires only after 30 sim-minutes of quiet. (E)
- [ ] **READ-06**: `MISSING_PAGE:<doc>` comes from the "Page X of N" markers, never from the PDF's page count. (E)
- [ ] **READ-07**: `MISMATCH:<field>` uses normalization (exact EIN string, nickname tolerance, name-suffix stripping, $1 balance tolerance), with no false alarms on the trap deals. (E)
- [ ] **READ-08**: The five OLD_TRICK checks run exactly as `rules/known_fraud_checks.md` states (STMT_TAMPER, REV_INFLATION, ID_MISMATCH, DUP_EIN, SHELL_ADDRESS). A missing page is not treated as tampering. (E)

### Move the deal (MOVE)

- [ ] **MOVE-01**: Deals go through Intake → Credit → Committee → Product → Committed → Closed in order. A deal never advances while waiting on a document, a human answer or an open fraud hold. (E)
- [ ] **MOVE-02**: Every stage writes a `stage_log` entry recording what was seen, what was decided and why. (E)
- [ ] **MOVE-03**: Human gates route correctly. Credit goes to the assigned officer, or their backup if OOO (dana.whitfield is out 11/03–11/06). Committee goes to priscilla.nguyen under $250k and to harold.benson at $250k or more. Commitment goes to the deal's RM, funding to tasha.reed, fraud holds to victor.hale then monica.salas. (E)
- [ ] **MOVE-04**: SLA alerts fire at 100% of the stage limit, escalations at 150% and the second escalation (to lauren.kim) at 200%, each exactly once. Messages say whose deal, which stage, how long, what it's waiting for and what would unblock it. (E)
- [ ] **MOVE-05**: Unanswered human requests are re-routed to the backup and escalate along the same 100/150/200% steps. (E)
- [ ] **MOVE-06**: Deals with a needed-by date are prioritised, and a deadline-risk alert fires before a good deal would miss its date. (E)
- [ ] **MOVE-07**: Borrower `info_request` is sent for missing items. No `credit_decision` request is sent on an incomplete file. (E)
- [ ] **MOVE-08**: Human responses come from scripted personas (fast, slow, OOO, never-answers) for headless runs, or from the interactive inbox via the API. (E)
- [ ] **MOVE-09**: New papers on an in-flight deal (the weekend drop) are absorbed, re-checked, and can resolve or raise issues. (E)

### Catch the fakes (FRAUD)

- [ ] **FRD-01**: A history baseline gives, for each attribute value, its document frequency, first-seen/last-seen dates and outcomes, plus distributions of deposit features and PDF producer per document class. (E)
- [ ] **FRD-02**: The graph links deals (current and history) to the canonicalized entities they share, and the score weights each entity by how rare it is. (E)
- [ ] **FRD-03**: Signal families are F1 shared rare entity (history matches count), F2 novelty/burst, F3 lookalike vendor/account, F4 document forensics, F5 deposit pattern (needs at least ~6 deposits), and F6 terms shape (weak). Each produces plain-words evidence. (E)
- [ ] **FRD-04**: A hold needs F1 plus at least 2 other families. 1–2 families puts the deal on the watch tier, shown but not held. An OLD_TRICK hit goes to Fraud Ops. (E)
- [ ] **FRD-05**: On a flag, the deal is frozen immediately with `held: true`, `stage_at_flag` and the reason, and `fraud_hold` is requested. A flagged deal never enters Closed. (E)
- [ ] **FRD-06**: `linked_deals` and `history_flags` are filled from clusters (history deals must share at least 2 families). On the sample, `history_flags` comes out as exactly H-2608-002 and H-2609-008. (E)
- [ ] **FRD-07**: Trap regression gives zero holds on Garza, Tyler, Priya, Okafor, Westfield, Harbor Tea, Oakline, LSFD and Bluebonnet, and zero history false flags (including H-2511-010, H-2601-022 and the 15 Berkshire deals). Ridgeway is flagged on Monday from history alone. (E)

### Nemotron agents (NEM)

- [ ] **NEM-01**: A Nemotron client with env-var model IDs, rate limiting, a record/replay cache and `off | replay | live` modes. With `off`, the scored JSON is byte-identical. (E)
- [ ] **NEM-02**: A smoke test proves a plain completion, a tool round trip and a VL read of the JPG on the hosted API. (E)
- [ ] **NEM-03**: A fraud investigator (ReAct, ≤8 steps) uses read-only engine tools (graph, docs, history, vendors) to write an evidence case for each flagged cluster, shown with its full trace. (E)
- [ ] **NEM-04**: A red-team generator proposes new fraud tricks. A deterministic synthesizer builds deals that use them and the engine scores them, producing a per-trick report of catch rate, time-to-hold and false flags. (E)
- [ ] **NEM-05**: A VL fallback reader handles images and unknown layouts. Its fields are validated and can only fill nulls, never raise a mismatch or a hold. (E)
- [ ] **NEM-06**: Nemotron writes plain-words credit memos, requests and alerts, with a template fallback, and parses free-text human replies into allowed options. (E)

### UI (UI)

- [ ] **UI-01**: A clean, light fintech design system (type scale, tabular money numerals, red reserved for holds). (J)
- [ ] **UI-02**: A pipeline board shows deals by stage with SLA timers and deadline badges. (J)
- [ ] **UI-03**: Sim clock controls: current time, advance, and replay from the start. (J)
- [ ] **UI-04**: Deal detail shows extracted facts with source chips, issues, stage log, human requests and alerts. (J)
- [ ] **UI-05**: A human inbox lets whoever plays the staff answer pending requests. (J)
- [ ] **UI-06**: The fraud graph hero view has edges encoded by rarity and replays as the clock advances ("ring lights up"), with an evidence panel, a signal-family checklist and the investigator trace. (J)
- [ ] **UI-07**: A red-team results view (per-trick catch rate). (J)

### Demo and delivery (DEMO)

- [ ] **DEMO-01**: A weekend-drop dry run on a synthetic new folder + arrivals passes with no code changes. (E)
- [ ] **DEMO-02**: A clean-checkout run following the README works on Jesse's machine. (J)
- [ ] **DEMO-03**: A recorded demo path (Nemotron in replay mode), a 3-minute pitch and slides. (J)

## v2 Requirements

- **V2-01**: Full template structural fingerprinting (fonts, layout hashes).
- **V2-02**: Brev self-hosted Nemotron.
- **V2-03**: Real email/Slack delivery of alerts.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Claude/Anthropic models in product | Team chose Nemotron + deterministic code |
| Supervised classifier on `fraud_label` | 12 old-trick positives; hidden trick is different |
| Sample literals in detection logic | Hidden set uses a different trick |
| LLM deciding holds/extractions/links | Scored path must be deterministic |
| GNNs, embeddings, community detection | Unexplainable, unnecessary at ~270 deals |
| Auth, database, pricing/covenants/e-sign | Not scored; hackathon scope |
| Committing data pack / challenge PDF | Participant-only material |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 1 | Pending |
| FND-02 | Phase 1 | Pending |
| FND-03 | Phase 1 | Pending |
| FND-04 | Phase 1 | Pending |
| FND-05 | Phase 1 | Pending |
| FND-06 | Phase 1 | Pending |
| FND-07 | Phase 1 | Pending |
| FND-08 | Phase 1 | Pending |
| NEM-02 | Phase 1 | Pending |
| UI-01 | Phase 2 | Pending |
| UI-02 | Phase 2 | Pending |
| UI-03 | Phase 2 | Pending |
| UI-04 | Phase 2 | Pending |
| UI-05 | Phase 2 | Pending |
| READ-01 | Phase 3 | Pending |
| READ-02 | Phase 3 | Pending |
| READ-03 | Phase 3 | Pending |
| READ-04 | Phase 3 | Pending |
| READ-05 | Phase 3 | Pending |
| READ-06 | Phase 3 | Pending |
| READ-07 | Phase 3 | Pending |
| READ-08 | Phase 3 | Pending |
| MOVE-01 | Phase 4 | Pending |
| MOVE-02 | Phase 4 | Pending |
| MOVE-03 | Phase 4 | Pending |
| MOVE-04 | Phase 4 | Pending |
| MOVE-05 | Phase 4 | Pending |
| MOVE-06 | Phase 4 | Pending |
| MOVE-07 | Phase 4 | Pending |
| MOVE-08 | Phase 4 | Pending |
| MOVE-09 | Phase 4 | Pending |
| FRD-01 | Phase 5 | Pending |
| FRD-02 | Phase 5 | Pending |
| FRD-03 | Phase 5 | Pending |
| FRD-04 | Phase 5 | Pending |
| FRD-05 | Phase 5 | Pending |
| FRD-06 | Phase 5 | Pending |
| FRD-07 | Phase 5 | Pending |
| NEM-01 | Phase 6 | Pending |
| NEM-03 | Phase 6 | Pending |
| NEM-04 | Phase 6 | Pending |
| NEM-05 | Phase 6 | Pending |
| NEM-06 | Phase 6 | Pending |
| UI-06 | Phase 7 | Pending |
| UI-07 | Phase 7 | Pending |
| DEMO-01 | Phase 7 | Pending |
| DEMO-02 | Phase 7 | Pending |
| DEMO-03 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 48 total
- Mapped to phases: 48
- Unmapped: 0

**By phase:** Phase 1: 9 (Both) · Phase 2: 5 (Jesse) · Phase 3: 8 (Ezekiel) · Phase 4: 9 (Ezekiel) · Phase 5: 7 (Ezekiel) · Phase 6: 5 (Ezekiel) · Phase 7: 5 (Jesse lead, DEMO-01 Ezekiel). Owners per requirement are the E/J tags above.

NEM-02 (Nemotron smoke test) maps to Phase 1 instead of Phase 6, so hosted tool calling is proven before the agent phase depends on it.

---
*Requirements defined: 2026-11-07*
*Last updated: 2026-11-07 after roadmap creation (traceability filled)*
