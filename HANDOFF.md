# DealPilot — Session Handoff (Jesse's side)

> **Source of truth is [`.planning/PROJECT.md`](.planning/PROJECT.md)** (Zeke's plan: stack, requirements, decisions, sample-trick analysis). This file doesn't repeat it. It adds the context, strategy and checklists from Jesse's planning session that PROJECT.md doesn't cover yet. If the two conflict, PROJECT.md wins; flag the conflict to the team.
> Last updated: Sat 2026-11-07, HackUTD 2026.
> **Confidential:** the repo must stay **private** (it was briefly public on 11/07 and was switched to private). Never commit the data pack or the challenge PDF.

---

## 1. Team and tracks

| | |
|---|---|
| Team | **Ezekiel "Zeke"** (GitHub `envezdezeke`; quant, engine, pipeline) + **Jesse** (GitHub `FroyoMojo`; finance, UI, pitch) |
| Tracks | Goldman Sachs **DealPilot** (primary) + **NVIDIA Nemotron** (secondary). Priority when cutting: Goldman score > Nemotron > UI. |
| Dropped, deliberately | Capital One/Nessie (felt tacked on), PNC (consumer-focused, crowded), all other tracks. Don't spread effort. |
| Edge | Finance/quant depth plus careful execution. Most GS teams will build a similar design. Ranking comes down to execution details and false-flag discipline, not UI flash. |
| Stack (per PROJECT.md) | Python engine (pandas, networkx, pypdf) behind FastAPI · React + Vite + Tailwind + force-graph · Nemotron via `integrate.api.nvidia.com/v1` (OpenAI-compatible). **No Claude/Anthropic in the product.** |
| Data | `data/participant/` (gitignored). Source: `github.com/SushmaEati/HackUTD` → `datasets/participant.zip`. Unzip, delete `__MACOSX/`. Treat the zip as untrusted: it ships `sim/clock.py`, so read it before running and run it as a separate process. |

## 2. Fast summary of the challenge (in our words)

The agent reads each borrower folder, moves deals `Intake → Credit → Committee → Product → Committed → Closed` (Closed = money out), asks humans at gates, alerts and escalates stuck deals (100/150/200% of SLA), and catches a **new** cross-deal fraud trick that passes the 5 known checks. Scoring:
- **READ:** facts plus missing/mismatch, no false alarms.
- **MOVE:** order, gates, alerts, needed-by dates.
- **FRAUD:** held before Closed, earlier is better, false flags cost a lot, linking to history.

Saturday brings a **drop** (new deals, new papers on existing deals, a Collections notice). Final scoring runs on a **hidden set with a different trick**. Vijay Kumar (GS) answers questions in the event channel. Full rules: `data/participant/README.md`, `SCHEMA.md`, `SUBMISSION_FORMAT.md`, `rules/stages.json`, `contacts/teams.json`.

## 3. Validation protocol (fills a gap in PROJECT.md)

The sample trick is already analyzed (PROJECT.md → Context), so the sample is now **contaminated as a fraud test**. Proving the detector generalizes needs a stricter protocol than "it catches the sample":

1. **Leave one trick out, not random rows.** The red-team generator (Nemotron, plus a seeded deterministic version for reproducibility) produces several trick *families*. Tune on all but one, test on the held-out family, rotate. A random row split only tests the same trick again.
2. **Write the trick menu before tuning**, and randomize strength and fields. Otherwise the generator only plants what the detector already looks for. Examples:
   - shared hidden party in different roles
   - repeated number style (round deposits, fixed weekdays, cents patterns)
   - document-template fingerprint (producer, layout, fonts)
   - lookalike counterparty (vendor or agent name, or remit account)
   - threshold gaming (amounts just under an approval limit)
   - timing burst
3. **Real-data blind checks.** Without coding DUP_EIN/SHELL_ADDRESS as rules, does the generic detector still surface those labeled history deals as cross-deal anomalies?
4. **Replay history in time order.** Measure how many deals into a scheme the first flag fires. Never use a random split, because it leaks the future.
5. **False positives on real good deals: the key metric.** Flags on history deals that are `funded`, `fraud_label=none` and `current`/`paid_off` are near-certain false positives. Also check the persona traps from PROJECT.md: Tyler, James, Maria, Priya, Westfield, Harbor Tea, LSFD_docs, Oakline Auto.
6. **Freeze thresholds before the Saturday drop** and treat the drop as a blind test. Log the score before and after any change.
7. **Report:**
   - false flags on good deals
   - fakes held before Closed
   - first-flag position in a scheme
   - linking recall (current + `H-…`)
   - READ field accuracy vs. `eval/gold.json`

Pitch line: *"Tested on fraud types it never saw and on real history it was never told about. Caught X, with Y false alarms."*

## 4. Execution checklist (where points are usually lost)

- [ ] Only see files after `arrive_at` (read time from the clock / `GET /now`).
- [ ] The clock can jump 6h+ at once. Emit **every** crossed SLA threshold (100/150/200%) with correct timestamps.
- [ ] Out-of-office → backup. Unanswered human requests: follow up, then escalate. Never wait forever.
- [ ] Committee routing: ≤ $249,999.99 → delegated (priscilla.nguyen, 24h SLA); above → harold.benson.
- [ ] Never advance while waiting on a doc. Send `info_request` to `"borrower"` immediately.
- [ ] Prioritize by `needed_by`. Humans work Mon–Fri 08:00–18:00 CT but SLAs run around the clock, so send gate requests early in business hours (Priya, Friday).
- [ ] Statements = 6 most recent **full** months (May–Oct 2026). Check `Page X of N` for missing pages.
- [ ] Normalize before comparing: EIN formats, "$1.2M", dates, nicknames (Bob = Robert is NOT a mismatch), LLC/Inc suffixes. Every mismatch must be real.
- [ ] Equipment loans: vendor and remit account verified against known vendors. Before Closed: disbursement goes to the borrower's own account or a verified vendor.
- [ ] Re-ingest on new files: facts carry versions, corrections override earlier values, and **all** deals are re-checked, including funded ones. A Collections notice on a funded deal → trace links ("find the rest").
- [ ] Two-tier fraud response: a soft concern → verification step + `info_request`, `fraud.flagged` stays false. Only multi-signal evidence → `fraud_hold` request.
- [ ] Timezone is **−06:00** everywhere (DST ended Nov 1 2026). Never use system local time.
- [ ] One-command run with `--folder/--arrivals`. State persisted so a restart can resume. Falls back to deterministic templates if Nemotron is down or rate-limited.
- [ ] Output JSON validates against `SUBMISSION_FORMAT.md` (keys = folder names, allowed enum values only).
- [ ] Rehearse the drop: delete some arrivals, re-sync, confirm zero manual steps.

## 5. Open questions for Vijay (post in the GS channel ASAP)

1. How is the hidden set run: do we hand over code, or run it live in front of judges?
2. During judging, how do organizers answer our human requests: through our UI, chat, email, a file? (PROJECT.md supports both an inbox UI and scripted personas; the answer decides which to polish.)
3. Is there a live demo/presentation in addition to the JSON score? What are the score weights?
4. Is "flag earlier" measured in sim time or by stage?

NVIDIA table: confirm which Nemotron model they recommend for tool calling and for vision (VL), the rate limits, and how the Brev credits work.

## 6. Pitch: making finance depth land with engineer judges

Judges are likely engineers, and compliance terms sound like bloat to them. Rules:
- **Sell the consequence, not the control.** Lead with what it caught or saved; keep the technical name as a small label.
- **Speak engineer:** lending rules are unit tests on a deal; the audit trail is an append-only event log; gates are authorization; evidence on every flag is traceability.
- **Show, don't tell:**
  - side by side, the old checks approve the ring and DealPilot holds it
  - "try to fool it": let a judge edit a deal to hide fraud
  - one honest score line (§3)
- **Show detail on demand:** the first screen shows the verdict, 3 plain-English reasons and dollars at risk. A click shows the math.
- **Lead with 3 catches** in the pitch; save the depth for Q&A, which is where the finance background wins.

| Built | Say |
|---|---|
| Lookalike vendor + remit account | "The equipment money was headed to a fake copy of a real vendor's bank account." |
| Shared hidden preparer across unrelated deals | "Three 'unrelated' companies were secretly built by the same person." |
| Document fingerprint | "Their 'bank statements' came out of a document generator, not the bank." |
| Deposit style | "Every deposit is a round number landing on the same weekdays. Real businesses don't look like that." |
| Threshold gaming | "Each loan is sized just under the limit that needs full committee review." |
| History linking | "We found two earlier loans from the same ring, already funded, one already past due." |
| Gates + audit log | "No single person can push a loan through, and every decision is explained in one click." |
| False-flag discipline | "Tyler's paperwork is a mess, and we still don't flag him. Strange isn't fake." |

## 7. Jesse's work items (finance)

1. **Answer key `eval/gold.json`** for all 13 sample folders: the true extracted fields plus the true `issues`. This is the highest-value finance task; every READ result gets scored against it.
2. Domain rules: per-field mismatch tolerances and the nickname list; required docs per stage; vendor and disbursement verification; the 7004 rule (business under 2 years old).
3. Credit memo template (Committee requires one): the 5 Cs, risk rating, flags with evidence, approval conditions. Nemotron fills it; deterministic facts only.
4. Plain-English templates for human requests and SLA alerts (each must say: whose deal + RM, stage + duration, waiting on, what unblocks it).
5. UI per PROJECT.md (pipeline board, inbox, alert feed, deal detail, fraud graph), and the pitch and Devpost.

## 8. History of this handoff

- Jesse's earlier local session built a generic finance/actuarial Streamlit starter (VaR/CVaR, Monte Carlo, credit loss), written before the tracks were known. It's **not** in this repo (it conflicts with the FastAPI/React stack and the no-Claude rule) and lives only on Jesse's machine (local branch `starter-local`). Ignore it unless a specific function is useful.
- That session went through several red-team passes. The conclusions are captured above and agree with PROJECT.md's key decisions: the deterministic engine owns the score, multi-signal agreement before a hold, nothing sample-specific hard-coded, and the data stays out of git.
