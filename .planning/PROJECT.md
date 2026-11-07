# DealPilot (team Goldman-I)

## What This Is

DealPilot is our HackUTD 2026 entry for the Goldman Sachs challenge, also entered in the NVIDIA Nemotron prize track. It reads a bank's shared loan folder and pulls out the deal facts. It moves each deal through the six-stage lending pipeline on a simulated clock, asks the right person at every sign-off, and raises alerts and escalations when a deal is stuck. Its core job is catching fake deals by looking **across** deals: an entity graph of deals and the parties, documents and accounts they share. A deterministic Python engine produces every scored output. Nemotron agents investigate, red-team and read hard documents around it. A clean fintech web UI shows the pipeline and the fraud graph.

## Core Value

**Catch the cross-deal fraud ring before money goes out, without blocking good deals, using a method that still works on the hidden set's different trick.** If everything else fails, the submission JSON must hold the right deals and leave the good ones alone. That means early holds, linked deals, history flags and zero false flags.

## Requirements

### Validated

(None yet; ship to validate)

### Active

**Scored engine (Goldman track: READ / MOVE / FRAUD)**
- [ ] Ingest only the files whose `arrive_at` the sim clock has passed. Identify each document by its content, not its filename (`SCAN_*.pdf`, `loan app FINAL.pdf`, CSV exports, JPG).
- [ ] Extract legal_name, EIN, amount, purpose_category, product, term, guarantor, stated revenue and needed_by, with a source document and confidence for each field.
- [ ] Detect `MISSING_DOC` / `MISSING_PAGE` ("Page X of N") / `MISMATCH:<field>` across documents. No false alarms on messy-but-real borrowers (Tyler).
- [ ] Run the five OLD_TRICK checks (STMT_TAMPER, REV_INFLATION, ID_MISMATCH, DUP_EIN, SHELL_ADDRESS) exactly as `rules/known_fraud_checks.md` defines them.
- [ ] Stage machine: Intake → Credit → Committee → Product → Committed → Closed. Enforce exit requirements and never advance a deal that is waiting on a document. Log what was seen, decided and why at each step.
- [ ] Human gates with correct routing: credit officer (backup if OOO, e.g. dana.whitfield is out 11/03–11/06), delegated approver vs. committee chair by the $250k threshold, the deal's RM, tasha.reed for funding, victor.hale/monica.salas for fraud holds.
- [ ] SLA engine: alert at 100%, escalate at 150%, second escalation at 200% to lauren.kim. Messages say whose deal, which stage, how long, what it's waiting on and what unblocks it. Unanswered human requests escalate too.
- [ ] Respect "funds needed by" dates and prioritise deals with deadlines (Priya needs her money by Friday).
- [ ] Cross-deal fraud detection. Build a graph of deals ↔ shared entities (preparer, preparer phone, registered agent, vendor name + remit account, PDF producer/creator, address, bank, guarantor). Score each shared entity by how rare it is against the history baseline, combined with document-forensics and deposit-pattern anomaly signals. Flag a cluster only when several independent signals agree. Request the fraud hold before Closed, as early as possible.
- [ ] "Find the rest": link flagged current deals to each other and to `H-…` history deals, and fill `history_flags`.
- [ ] Write the submission JSON in exactly the format of `SUBMISSION_FORMAT.md`, keyed by folder name.
- [ ] Re-runnable on a new drop: point the engine at a new `shared_folder` + `arrivals.jsonl` (the weekend drop, the hidden set) with no code changes, including new papers that arrive on deals already in flight.
- [ ] Human-response layer: an interactive inbox, plus a scripted responder policy for headless runs (fast, OOO, and never-answers personas).

**Nemotron (NVIDIA track: agentic, beyond a chatbot)**
- [ ] Fraud investigator agent (ReAct + tool calls). Given a flagged cluster, it queries the graph, pulls documents, compares vendors and accounts, searches history and writes an evidence case for Fraud Ops.
- [ ] Red-team scenario generator. Nemotron invents new fraud tricks and synthesizes deals that use them. We measure whether the graph detector catches them, as evidence that it generalizes to the hidden set.
- [ ] Fallback document reader (Nemotron VL). Reads documents the deterministic parser can't (JPG ID photo, unknown layouts). Its output is validated by the deterministic engine.
- [ ] Nemotron-written plain-words messages (credit memo, sign-off requests, alerts), with deterministic templates as a fallback. Parse free-text human replies into actions.

**UI (best-design ambition)**
- [ ] Clean, light fintech web UI. Pipeline board per deal, sim clock controls (advance/scrub), human inbox, alert feed, deal detail with extracted facts, issues and stage log.
- [ ] Interactive fraud graph as the hero visual: the ring "lights up" as shared rare entities connect deals, with the evidence for each edge shown.

### Out of Scope

- Claude / Anthropic models anywhere in the product: the team chose Nemotron (via build.nvidia.com / Brev) and deterministic code.
- A supervised classifier trained on `fraud_label`: the old tricks are labeled but the new trick is not, so it wouldn't carry over to the hidden set.
- Hard-coding sample-specific signals (the literal "DocuForge", "Delacroix" or account 4471): the hidden set uses a different trick. Signals must be generic (rarity, lookalikes, forensics, distributional anomalies).
- Real auth, multi-user accounts, persistence beyond local files: this is a hackathon demo.
- Committing the data pack or challenge PDF to git: the challenge statement is for participants only. `data/` is gitignored.

## Context

**Event.** HackUTD 2026, Goldman Sachs "DealPilot — Move the Deal. Stop the Fraud." challenge, stacked with the NVIDIA Nemotron prize track. 2 people (Ezekiel: quant/engine/pipeline; teammate: finance/UI/pitch), ~21 hours left as of 2026-11-07. Repo: github.com/envezdezeke/Goldman-I (remote already has one commit, so pull before the first push).

**Judging (Goldman).** READ = correct facts plus spotting what's missing or doesn't match, with no false alarms. MOVE = stages in order, the right human asked, alerts and escalations, no advancing while waiting on docs, needed-by dates met. FRAUD = held before Closed (earlier scores more), pattern spotted in the first few deals, each false flag costs a lot, linked deals and history found. A **hidden set with a different trick** is run too: "build for the idea, not the examples."

**Judging (NVIDIA).** The project must use Nemotron beyond a chatbot: multi-step workflows, agents that plan and execute, tool integration, real-world use. The track rewards multi-agent systems, ReAct, tool calling, multi-modal (VL) work and agent simulation/eval. $60 of Brev credits per team. API is OpenAI-compatible at `integrate.api.nvidia.com/v1`. Live model IDs (verified 2026-11-07): `nvidia/nemotron-3-super-120b-a12b` (agents), `nvidia/nemotron-nano-3-30b-a3b` (fast text), `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` (VL). Keep IDs in env vars.

**Data pack (`data/participant/`, gitignored).**
- 13 borrower folders in `shared_folder/`.
- 257 history deals (Nov 2025 – Oct 2026; 12 fraud_confirmed under old tricks).
- Monthly deposit summaries and stage events (12.6% of stages breached SLA; median hours run well under SLA).
- `rules/stages.json`, `contacts/teams.json`, `sim/clock.py` (CLI + HTTP API), `arrivals.jsonl` (173 file arrivals, Mon 11/02 08:00 → Fri 11/06 18:00 CT), `assignments.json`.

**The sample week's new trick (from our analysis on 2026-11-07).**
- **Current ring:** Pecan Grove Catering, Ridgeway Freight Logistics, Summit Peak Flooring.
- **What they share:**
  - Every PDF has Producer `DocuForge 2.1 (Windows)` / Creator `DocuForge Templates`, even the bank statements. Every genuine statement in the folder is `FIS Statement Services 9.2`.
  - Same preparer: "K. Delacroix, Delacroix Bookkeeping Services · 214-555-0187". This preparer never appears in history before Aug 2026.
  - Registered agent Commerce Street Agent Services (5 uses in all of history).
  - Lookalike vendor "Metroplex Equipment Supply **LLC**" with remit First Lakes Bank …4471. The real, frequent vendor is "Metroplex Equipment Supply, **Inc.**" remitting to …9902.
  - Young LLCs (formed in 2025).
  - Equipment loans just under the $250k full-committee threshold (e.g. $246,000), so they get single delegated approval.
  - "No specific date" for funds needed.
- **History members:** H-2608-002 (Trinity Bend Plumbing, funded, 30 days past due) and H-2609-008 (Mesquite Ridge Signs, funded, current). Both have the same preparer, vendor, account and producer, `fraud_label=none`, and deposits that are 100% multiples of $100 landing only Mon/Thu, vs. a history median of 8%. These are the `history_flags` targets.
- **Weaker links to check, not to hard-code:** H-2511-010 and H-2601-022 used DocuForge with an ordinary preparer and repaid normally, so the producer alone is not proof. This is why we need several independent signals agreeing.

**Traps ("strange is not fake").**
- Tyler (messy CSVs, JPG ID, Form 7004 extension, self-prepared).
- James / Okafor Advisory (big, international).
- Maria / Garza Family Pharmacy (returning customer with a stable baseline in history; a change would stand out).
- Priya's Bakery (deadline-sensitive; her credit officer dana.whitfield is OOO, so route to her backup).
- Westfield (a new vendor not in history, but a normal vendor profile).
- Harbor Tea (Northstar agent at 5950 Berkshire Ln, an address used by 15 history deals that mostly repaid fine).
- LSFD_docs (scanned filenames only).
- Equipment deals on the real Metroplex vendor (Oakline Auto, …9902).

**Prior team experience.** Won 1st place at RowdyHacks (UTSA Investment Society track) with a FastAPI + deterministic quant pipeline, judged by replaying the model against a rubric. Same discipline applies here: a deterministic, auditable engine, then self-score against the format.

## Constraints

- **Timeline**: ~21 hours, 2 people. Priority order when cutting: Goldman score > Nemotron > UI.
- **Tech stack**: Python (pandas, networkx, pypdf) engine behind FastAPI; React + Vite + Tailwind frontend with a force-graph library. Nemotron via the build.nvidia.com API / Brev. Python at `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe` (plain `python` is the Microsoft Store stub).
- **No Claude in product**: the team chose Nemotron + deterministic code.
- **Determinism**: every scored field in the submission JSON must come from deterministic code. Nemotron output is advisory or validated before it can affect a score (a hold, an extraction, a linked deal).
- **Generalization**: no sample-specific literals in detection logic. The hidden set uses a different trick.
- **Time semantics**: the system only sees files after their `arrive_at`. All times are sim time, America/Chicago (−06:00). SLA timers are wall-clock sim hours.
- **Confidentiality**: the challenge statement is for participants only. Raw data and PDFs stay out of git.
- **Secrets**: the NVIDIA API key lives in `.env` (gitignored). Never commit or print it.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Deterministic engine owns all scored outputs; Nemotron is advisory/validated | Reproducible scoring, explainable flags, no LLM variance on a heavily penalized false-flag metric | — Pending |
| Fraud = entity graph + rarity-vs-history scoring + forensic/deposit anomalies, multi-signal agreement before a hold | Carries over to an unseen trick; false flags cost a lot, so one weird signal ≠ fraud | — Pending |
| Nemotron used for investigator agent, red-team generator, VL fallback reader, comms/reply parsing | Meets "beyond a chatbot" (agents, tools, multi-modal, sim/eval) without risking the scored path | — Pending |
| FastAPI + React/Vite, clean light fintech design | Matches team experience; splits cleanly between 2 people; competes for best design | — Pending |
| Human loop = interactive inbox UI + scripted responder personas | How judges answer during judging is unknown; supports both live and headless runs | — Pending |
| Engine takes `--folder` / `--arrivals` so new drops run with no code changes | Weekend drop and hidden set arrive late | — Pending |
| Data pack gitignored under `data/` | Challenge material is participant-only | ✓ Good |
| Engine freezes a deal the moment it flags, sends `fraud_hold` to victor.hale (backup monica.salas); resumes only on `fraud_release` | Some judges never answer; fakes reaching Closed is the costliest error | — Pending |
| Hold = F1 shared-rare entity (history matches count) + ≥2 other families; 1–2 families = watch tier; OLD_TRICK → Fraud Ops | Ridgeway lands first and must flag from history alone; false flags cost a lot | — Pending |
| Ezekiel owns engine + Nemotron; Jesse owns golden labels, UI, pitch | Agents depend on the engine tool API; finance judgment fits labels/pitch | — Pending |
| Hosted build.nvidia.com API with record/replay cache; Brev break-glass only | Super needs 8×H100; demo can't depend on live API | — Pending |
| 30-sim-minute quiescence before MISSING_DOC / info_request; advance immediately when requirements met | Files trickle in over ~20 min per folder | — Pending |
| `issues` = open at end of run; resolved go in `resolved_issues` | Format is ambiguous; extra keys ignored | — Pending |
| Missing statement at Credit → `info_request` first; no `credit_decision` on an incomplete file | Rule: never advance while waiting on a document | — Pending |
| Ask organizers now how human answers and drops arrive; build inbox + scripted personas meanwhile | Unknown judging mechanics | — Pending |
| Hard gates: H10 engine baseline frozen, H16 Nemotron agents working, H19 feature freeze; cut UI first | 21h budget, Goldman > Nemotron > UI | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check: still the right priority?
3. Audit Out of Scope: reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-07 after initialization*
