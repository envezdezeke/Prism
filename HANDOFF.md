# Prism — Session Handoff (Jesse's side)

> **Source of truth is [`.planning/PROJECT.md`](.planning/PROJECT.md)** (Zeke's plan: stack, requirements, decisions, sample-trick analysis). This file doesn't repeat it. It adds the context, strategy and checklists from Jesse's planning session that PROJECT.md doesn't cover yet. If the two conflict, PROJECT.md wins; flag the conflict to the team.
> Prism is our build of the Goldman Sachs "DealPilot" challenge. Hard deadline **Sun 2026-11-08 12:00 CT** (submit 11:40); gates per ROADMAP.md: H10 engine frozen (Sun 01:55), H15.5 Nemotron (07:25), H18 feature freeze (09:55).
> **Every scored rule, as a pass/fail list, plus the open judgment calls: [`docs/DETAILS_CHECKLIST.md`](docs/DETAILS_CHECKLIST.md).**
> Last updated: Sat 2026-11-07 ~17:45 CT, HackUTD 2026.
> **Confidential:** the repo must stay **private** (it was briefly public on 11/07 and was switched to private). Never commit the data pack or the challenge PDF.

---

## 1. Team and tracks

| | |
|---|---|
| Team | **Ezekiel "Zeke"** (GitHub `envezdezeke`; quant, engine, pipeline) + **Jesse** (GitHub `FroyoMojo`; finance, UI, pitch) |
| Tracks | Goldman Sachs **DealPilot** (primary) + **NVIDIA Nemotron** (secondary). Priority when cutting: Goldman score > Nemotron > UI. |
| Dropped, deliberately | Capital One/Nessie (felt tacked on), PNC "360° Financial Health Navigator" (consumer-focused, crowded), Toyota Financial Services, 8090.AI (legacy modernization), NMC² (data centers), Spacetime (needs their database plus a **public** repo; ours must stay private). Don't spread effort. |
| Goldman's own one-liner (kickoff slide) | *"Build 'DealPilot' – a comprehensive platform that automates and secures the entire lifecycle of commercial loan processing, leveraging AI/ML capabilities to detect hidden, cross-deal fraud patterns and achieve operational excellence."* Prizes: AirPods Max 2 / HomePod Mini 2 / $50 Grubhub. |
| NVIDIA's 4 must-haves (kickoff slide) | **Beyond a chatbot** (not just answering prompts) → investigator, red-team. **Multi-step workflows** (agents that plan and execute) → investigator's ReAct loop. **Tool integration** ("using external APIs and services intelligently") → see §9 item 12. **Real-world applicability** → loan-fraud ops. Prizes: 1st 2× RTX 5080 + $200 Brev; 2nd 1× RTX 5080 + $200 Brev. |
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
5. **False positives on real good deals: the key metric.** The "good set" is history deals that are `funded`, `fraud_label=none` and `current`/`paid_off`. Every flag on one gets a **written finance review**: either a hidden scheme member, with evidence, or a false positive. Report both counts. (The labels can't see the new trick: `fraud_label=none` means "no known trick found", not "proven clean" (SCHEMA.md), so a flag there isn't automatically wrong. One of the sample's history targets is exactly such a deal.) Also check the persona traps from PROJECT.md: Tyler, James, Maria, Priya, Westfield, Harbor Tea, LSFD_docs, Oakline Auto.
6. **Freeze thresholds before the Saturday drop** and treat the drop as a blind test. **Run the frozen engine on the drop and record that first score (with the commit) before anyone opens the drop's files.** After that, log the score before and after any change; the pitch quotes the first-run number.
7. **Report:**
   - false flags on good deals
   - fakes held before Closed
   - first-flag position in a scheme
   - linking recall (current + `H-…`)
   - READ field accuracy vs. `eval/gold.json`

Pitch line: *"Tested on fraud types it never saw and on real history it was never told about. Caught X, with Y false alarms."*

**Decided 2026-11-07 (Jesse; Zeke to confirm):**
- Pitch centerpiece = **measured validation**. Banks trust a model with a measured false-flag rate, and teams that prompt their way through won't have one.
- Headline number = the **blind weekend-drop result**. History replay (false-flag rate on the good set) and the synthetic tricks back it up. If the drop arrives too late, the history replay becomes the headline.
- **Accuracy and sturdiness beat looks** on the Goldman track: judges grade the output file against a rubric. Screens matter for the NVIDIA track and the pitch, not the Goldman score.
- Double-pledge / collateral-registry checks are out of scope (no asset IDs or lien registry in the data; see PROJECT.md).

## 4. Execution checklist (where points are usually lost)

Short version below. The full rule-by-rule list is [`docs/DETAILS_CHECKLIST.md`](docs/DETAILS_CHECKLIST.md).

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

## 5. Open questions for Vijay (the one list; post in the GS channel ASAP)

Owner: Jesse. Record each answer in PROJECT.md Key Decisions. Ordered by how much score rides on the answer.

1. **During judging, how do the "staff" answer our sign-off requests:** our UI, chat, email, a file, or an API they call? (Our build supports an inbox screen and scripted answers; the answer decides which to polish.)
2. **How is the hidden set run, and how do the drop and the hidden set arrive?** Do we hand over code or run it live? Is it a new zip with its own `arrivals.jsonl`, or files added to the same folder?
3. **Is `issues` scored on the end state of the run, or on every issue ever raised?** (We chose end state; checklist J14.)
4. **If we request a fraud hold and Fraud Ops never answers, does the deal count as held?** (We chose yes; J5.)
5. **Commitment letter:** is the RM's sign-off enough, or must the borrower's signature be a separate request? (We chose the RM confirms; J10.)
6. **Is "flag earlier" measured in sim time or by stage?** What are the score weights? Is there a live demo or presentation besides the JSON score?
7. **Does submission require a public GitHub repo,** given the data is confidential?
8. **What team name goes in the output file's `team` field?**

NVIDIA table: confirm which Nemotron model they recommend for tool calling and for vision (VL), the rate limits, and how the Brev credits work.

## 6. Pitch: making finance depth land with engineer judges

Judges are likely engineers, and compliance terms sound like bloat to them. Rules:
- **Sell the consequence, not the control.** Lead with what it caught or saved; keep the technical name as a small label.
- **Speak engineer:** lending rules are unit tests on a deal; the audit trail is an append-only event log; gates are authorization; evidence on every flag is traceability.
- **Show, don't tell:**
  - side by side, the old checks approve the ring and Prism holds it
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

1. ✅ **Done Sat 18:29.** **Answer key `eval/gold.json`** for all 13 sample folders: the true extracted fields plus the true `issues`. This is the highest-value finance task; every READ result gets scored against it.
2. Domain rules: per-field mismatch tolerances and the nickname list; required docs per stage; vendor and disbursement verification; the 7004 rule (business under 2 years old). **Done:** `docs/DETAILS_CHECKLIST.md` (rules plus judgment calls J1–J22, all decided; J5, J10, J14, J20 still marked "Vijay?").
3. ✅ **Done Sat ~18:40:** [`docs/CREDIT_MEMO_TEMPLATE.md`](docs/CREDIT_MEMO_TEMPLATE.md). Credit memo (Committee requires one): 5 Cs, rule-based 1–5 risk grade, assumed 9.0% rate, conditional recommendation, approval conditions, a 4-line version for the committee request, and test cases. Numbers, grade and recommendation are deterministic; Nemotron may only polish prose. **Zeke: add `credit_memo` to `DealDetail`.**
4. ✅ **Done Sat ~18:45:** [`docs/MESSAGE_TEMPLATES.md`](docs/MESSAGE_TEMPLATES.md). Plain-English templates for SLA alerts (100/150/200%), follow-ups and backup reroutes (J21), the fraud-hold chase (J22), all 7 request types, borrower info requests and the deadline-risk alert. Each alert says whose deal + RM, stage + duration, waiting on, and what unblocks it.
5. UI per PROJECT.md (pipeline board, inbox, alert feed, deal detail, fraud graph), and the pitch and Devpost. **Phase 2 planned and design contract written (Sat ~19:35); execution next.**
6. **Trick menu `eval/trick_menu.yaml`** (`docs/MODEL_DESIGN.md` M5/M15/M16): 6–8 fraud trick families with strength ranges and 1–2 honest look-alike twins each, used to build synthetic test deals. **Must be committed before Zeke's first synthetic calibration run.** Not needed by quick task 261107-qx4 (it calibrates on real clean history).

## 8. History of this handoff

- Jesse's earlier local session built a generic finance/actuarial Streamlit starter (VaR/CVaR, Monte Carlo, credit loss), written before the tracks were known. It's **not** in this repo (it conflicts with the FastAPI/React stack and the no-Claude rule) and lives only on Jesse's machine (local branch `starter-local`). Ignore it unless a specific function is useful.
- That session went through several red-team passes. The conclusions are captured above and agree with PROJECT.md's key decisions: the deterministic engine owns the score, multi-signal agreement before a hold, nothing sample-specific hard-coded, and the data stays out of git.

## 9. Open items for Jesse + Zeke (updated Sat 18:50 CT)

Settle these together; each blocks clean hand-offs.

| # | Item | Why it matters | Proposed answer |
|---|---|---|---|
| 1 | ~~Contract + mock data~~ | | **Resolved:** delivered by Zeke Sat evening (`docs/CONTRACT.md`, `fixtures/`, `prism/`; 76 tests pass on Mac) |
| 2 | ~~Answer key not started; shape undefined~~ | | **Resolved Sat 18:29:** Zeke's template (`eval/README.md`), all 13 deals `done`, pushed before the 20:00 deadline |
| 3 | ~~Answer key must be labelled blind~~ | | **Done:** labelled from raw files, then diffed against the research: zero disagreements on issues, holds or links |
| 4 | ~~Jesse's role vs. ~8h of UI coding~~ | | **Resolved Sat ~18:45:** Jesse keeps the UI role (Phase 2 + 7), building with Claude Code; finance items (checklist, answer key, memo, messages) already delivered first |
| 5 | ~~Finance items not in the ROADMAP~~ | | **Resolved:** delivered: `docs/DETAILS_CHECKLIST.md`, `eval/gold.json`, `docs/CREDIT_MEMO_TEMPLATE.md`, `docs/MESSAGE_TEMPLATES.md` |
| 6 | ~~Judgment calls J1–J20~~ | | **Locked** by Jesse; Zeke confirmed in STATE.md |
| 7 | **Organizer questions** were in two places; now merged into §5 here, owned by Jesse | Who answers human requests during judging, and how `issues` is scored, both change the build | Jesse owns asking Vijay; record the answers in PROJECT.md Key Decisions |
| 8 | ~~Mac setup~~ | | **Resolved:** Mac steps in ONBOARDING §4; Zeke's tests pass on Jesse's Mac |
| 9 | ~~Push access for Jesse~~ | | **Resolved 17:50:** Jesse pushed successfully |
| 10 | ~~"Aiming for best design" vs. Goldman > Nemotron > UI~~ | | **Fixed:** ONBOARDING §7 and PROJECT.md now say accuracy first |
| 11 | **Drop-day fixes vs. the blind headline.** ROADMAP's drop slot allows generic fixes, then a re-tagged baseline | Fixing before recording makes the "blind" number not blind | Record the first-run score and commit first (§3 item 6), then fix |
| 12 | **NVIDIA asks for "external APIs and services"**; our agent's tools are engine functions inside our own program | Judges may read internal function calls as weak tool use | Have the agent call real HTTP services: our own API endpoints and the sim clock's API (`/now`, `/inbox`), and say so in the pitch |
| 13 | **Goldman's slide says "leveraging AI/ML"**; our docs say "not a trained classifier" | A judge could hear "no ML" | Pitch wording: "unsupervised anomaly detection that learns what normal looks like from a year of history" (rarity scoring and deposit-pattern statistics *are* ML); "no classifier" is our reason it carries over to new tricks |
| 14 | **Does submission require a public repo?** Spacetime's track does; the Goldman data is confidential, so ours is private | A required public link would force a scrubbed public copy | Ask Vijay / HackUTD; if needed, publish code only (no data, no challenge text) |
| 15 | ~~Fraud-rule blind spot (F1 mandatory)~~ | Hidden-set risk if a trick shares no rare entity | **Decided by Zeke, Sat 19:05** (`docs/MODEL_DESIGN.md` M2): F1 stays mandatory as a deliberate bet that the hidden trick is still cross-deal; a ring that shares nothing visible lands on the watch tier at best. Fallback playbooks M10–M12. Accepted risk unless Jesse objects |
| 16 | ~~Credit memo + message templates had no requirement in Phase 4~~ (only NEM-06 in Phase 6, which is on the cut list), yet Committee can't exit without a memo | | **Fixed:** added MOVE-10 (memo) and MOVE-11 (messages), deterministic, to REQUIREMENTS and ROADMAP Phase 4 |
| 17 | **Nobody watches for the weekend drop**, and the blind-test headline needs a first-run score before anyone opens it | 🟠 Lose the headline number | Jesse watches the GS channel and `github.com/SushmaEati/HackUTD/tree/main/datasets` (last upload Fri 18:12 CT = the original pack; no drop as of Sat 18:50). On arrival: ping Zeke, don't open the files |
| 18 | **Schedule slip at Sat 18:50 (H2.9).** Phase 1's validator, determinism harness, CLI and self-score script aren't on GitHub yet, and Phase 3 (due H2–H5) hasn't started there. Jesse's Phase 2 UI (H1–H9) hasn't started | 🟠 H10 engine freeze at risk | Zeke: push work in progress so we can see it. Jesse: start Phase 2 now (`/gsd-plan-phase 2`) |
