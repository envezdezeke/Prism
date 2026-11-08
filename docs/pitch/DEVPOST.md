# Prism: Devpost Submission (draft)

> Owner: Jesse. Draft Sat 2026-11-07; revised Sun 2026-11-08 (plan 07-09) to match `docs/pitch/PITCH_OUTLINE.md`. Paste each section into the matching Devpost field.
> **This page is public.** Before pasting, check: no borrower, business or staff names, no tax IDs, no history deal IDs, no folder names, no dollar figures from the data pack, and no challenge text beyond the public title. Describe the data only as "a 13-deal sample" and "a year of the bank's loan history".
> Anything in `[[double brackets]]` is a placeholder. Fill it from its committed source (the table at the bottom of `PITCH_OUTLINE.md` names the file for each; `eval/scorecard.md` for most) and name the commit, or delete the sentence. Never estimate or round up. No result number is filled as of Sun 02:30 CT because no committed record exists yet.
> Use "an honest borrower with a messy file", never a name. Screenshots come from the mock data. The organizer questions will not be asked (PROJECT.md, Sun 02:45), so public video, slides and this page use generic labels with no sample names (assumed answer 10, D-49); a video that shows live sample deal names stays unlisted.
> **Build status check.** The audits of Sun 02:30 CT found READ extraction and the fraud decision still stubs, no Nemotron code, and the fraud graph, investigation and red-team screens not built (plans 07-01, 07-03, 07-04, 07-05). Sentences tagged `[pending ...]` describe those. 07-10 keeps a tagged sentence only if the feature ships, then deletes the tag; any other sentence that is not true of the build at submission is cut as well.

**Tagline (one line):** Prism catches coordinated loan fraud before the money goes out, without blocking honest borrowers, and shows its evidence for every decision.

**Tracks:** Goldman Sachs "DealPilot — Move the Deal. Stop the Fraud." · NVIDIA Nemotron

---

## Inspiration

We are a finance and quant team. One of us comes from lending, the other from modelling. We picked the DealPilot challenge because it asks for something banks actually struggle with. A single fake loan application is built to pass every check. What gives a fraud ring away is that it is made on the cheap: the same bookkeeper, the same payment account and the same document template, reused across applications that claim to be unrelated. You only see that by looking across deals.

We also knew what makes a bank trust a fraud model, and it is not a demo of one catch. It is a measured false-alarm rate. A false hold on an honest borrower costs real money and a client relationship. So we set ourselves one rule from the start: every number we claim must come from a test we did not tune on.

## What it does

Prism runs a commercial lending desk on a simulated clock:

- **Reads** each borrower's loan folder (PDFs, spreadsheet exports, a phone photo) and identifies each document by its content, not its filename. It extracts the deal facts, with the source document and a confidence level for each one, and flags documents or pages that are missing or facts that disagree between documents. It does not raise false alarms on messy but honest paperwork.
- **Moves** each deal through six stages, from Intake to Closed (where money goes out). It enforces each stage's exit requirements and never advances a deal that is waiting on a document. Sign-off requests go to the right person, with a backup when someone is out of office. When a stage runs past its time limit, Prism alerts and then escalates in plain English: whose deal it is, how long it has been stuck, what it is waiting on and what unblocks it. Deals with a funding deadline get priority.
- **Writes a credit memo** at Committee [pending: live engine run, MOVE-10]: debt coverage, revenue support, time in business, relationship history, a rule-based 1 to 5 risk grade, a recommendation and conditions of approval. Every number is computed. None of it is generated text. Its four-line version is the Committee approval request in the sign-off inbox; there is no separate memo screen.
- **Catches fraud rings.** Prism builds a graph of deals and everything they share: preparers, phone numbers, registered agents, vendors and their payment accounts, document software, addresses, banks and guarantors. It scores each shared entity by how rare it is in a year of the bank's own history. It then puts the deal on hold as soon as enough independent evidence agrees, often at Intake, and before Closed. It also links the held deals to earlier loans in history that were built from the same kit, including ones already funded.
- **Shows its work.** A clean web cockpit has a pipeline board on a simulated clock (Next event and Replay from start), a sign-off inbox, an alert feed, and a deal page that shows the source document and confidence for every fact. A fraud graph replays with the clock as the ring connects, and each link carries a plain-English evidence sentence [pending 07-01/07-03].

## How we built it

**The fraud model is anomaly detection measured in one unit: bits of surprise.** For every observation we estimate how likely it is under a year of clean history and score it as `-log2 P`, with smoothing so nothing is ever infinitely surprising. A bookkeeper seen on one in two hundred honest deals scores high. An address shared by many deals that repaid scores near zero. Evidence falls into six families:

1. **Shared rare entity:** deal-to-deal links weighted by the rarity of what they share (a rarity-weighted Adamic–Adar index), discounted when an entity's history deals mostly repaid.
2. **Novelty and burst:** an entity that is new, or suddenly used far above its long-run rate (Poisson tail).
3. **Lookalike counterparty:** a vendor whose name nearly matches a well-known vendor but whose legal suffix or payment account differs.
4. **Document fingerprint:** software that is rare for that kind of document, for example a bank statement that was not produced by a statement system.
5. **Deposit pattern:** round-number share and weekday concentration against the history distribution (entropy and KL divergence), with beta-binomial shrinkage so a few large deposits do not look suspicious by accident.
6. **Loan terms:** amounts just under an approval limit, young entity, no funding date. This family is shown as context and never votes, because these traits are common among honest small businesses.

**The decision rule:** hold a deal only when it shares a rare entity with another deal *and* at least two other families agree. One or two families put it on a visible watch list instead. Each voting family's threshold is the 95th percentile of its score on clean, repaid history deals, so each misfires on about 5% of good deals by construction. Thresholds are never fitted to fraud examples. The configuration stores percentiles, not values, so every threshold recomputes from whatever history ships with a new dataset. Holds are recomputed on every file arrival and stay in place until Fraud Ops releases them.

**Validation was designed before tuning.** Data was split by time, never at random, because a random split leaks the future:

| Test set | Used for tuning? |
|---|---|
| Clean, repaid history deals, any dates (thresholds, never below a 1-in-20 floor) | Yes, the only set we tuned on |
| Later months of history, replayed forward in time | No: false flags on good deals, and how early a scheme is caught |
| Labelled old-trick fraud in history, with the known-trick checks switched off | No |
| The 13-deal sample, including deliberately odd but honest borrowers | No: regression and false-alarm traps |
| Synthetic fraud families with honest lookalike twins, one family held out at a time | No: sanity check only |
| Fraud tricks invented by Nemotron | Never: the final exam |
| The organizers' weekend data drop | Never: run once on the frozen engine, recorded before anyone opened the files |

Every flag on a good history deal got a written finance review, because "no known fraud" in the labels is not the same as "proven clean".

**Nemotron agents work around the engine, never inside the score.**

- An **investigator** (ReAct loop) calls five read-only tools over the deal graph, the deals' documents and the loan history over up to eight steps. It writes a cited evidence case for each held or watched cluster. Nemotron advises; the rule engine decides.
- A **vision reader** handles documents the parser cannot read. It may fill a field only when the parser left it empty, the value passes a format check and a second document agrees. It can never raise an issue or a hold.
- Every call goes through a record-and-replay cache keyed on the full request, so runs replay exactly. The scored output is byte-identical with Nemotron on, in replay, or off.

**Stack:** a Python engine (pandas, networkx, pypdf, pdfplumber, RapidOCR) behind FastAPI, with Pydantic models as the contract between engine and UI. The front end is React, Vite, Tailwind and shadcn with a force-directed graph. Nemotron runs through the hosted NVIDIA API (OpenAI-compatible) with a plain tool-calling loop and no agent framework.

## Challenges we ran into

- **Strange is not fake.** The sample includes honest borrowers who look odd: messy spreadsheets, a phone photo of an ID, an international business, an address shared with many other companies. An honest borrower with a messy file must not be flagged. Most single signals fire on someone honest. That is why we require three independent families to agree, and why the loan-terms family cannot vote.
- **Proving generalization when the test trick is hidden.** Once we had studied the sample's trick, the sample was no longer a fair fraud test. We had to build a separate validation ladder: a time-ordered history replay, held-out synthetic families and a blind run on new data.
- **Time.** Files only become visible when they arrive. The clock can jump six hours at once, and every missed alert in between still has to be raised with the right timestamp. Staff work business hours, but time limits run around the clock.
- **Keeping a language model away from the score.** We wanted Nemotron doing real work, but a fraud hold has to be explainable and reproducible. The answer was strict boundaries: read-only tools, required citations, validation before any field fill, and a replay cache.
- **Twenty hours, two people.** We split on a fixed API contract with mock data, so the UI never waited on the engine, and we froze the engine at fixed gates.

## Accomplishments that we're proud of

- **Blind result:** [[BLIND_HELD]] of [[BLIND_TOTAL]] fake deals held before Closed, [[BLIND_FALSE_FLAGS]] false flags on good deals, first hold at stage [[BLIND_FIRST_STAGE]], recorded from a frozen engine before anyone opened the files (commit [[BLIND_COMMIT]]). If the blind record does not exist by H18, lead with the held-out history result below instead (D-24).
- **Held-out history:** [[HIST_FLAGS]] flags among [[HIST_GOOD_N]] good deals; after written review, [[HIST_SCHEME]] were scheme members and [[HIST_FALSE_POS]] were false positives; first flag at deal [[HIST_FIRST_DEAL]] of the scheme.
- **Synthetic fraud types** (one hold-rule setting was chosen on this bench; a second, separate set of trick designs was not tuned on): [[SYN_HELD_PCT]] of ring deals held and [[SYN_TWIN_PCT]] of honest twins flagged, per held-out family, against our pre-set bar of at least 70% held and at most 5% flagged.
- **Sample week:** the ring held at stage [[SAMPLE_STAGE]], before any money went out, earlier funded members found in history ([[SAMPLE_LINKS]]), and [[SAMPLE_FALSE_HOLDS]] false holds across [[TRAP_N]] odd-but-honest borrowers.
- **Reading accuracy:** [[READ_ACCURACY]] of fields correct against our hand-labelled answer key.
- A fraud model whose every hold carries a plain-English reason and the evidence sentence behind each link [pending 07-03].

## What we learned

- A fraud model is only as trustworthy as its measured false-alarm rate. Building the validation plan first changed how we built everything else.
- Modelling "normal" carries over to new tricks better than learning "bad" from a few labelled examples.
- Independence matters more than the number of signals. Five signals that move together are one signal.
- Language models are most useful where code is weakest: arguing both sides of messy evidence, reading odd documents, and attacking our own detector. They are least useful as the decision-maker.
- Finance vocabulary needs translating for engineers, and the reverse. Lending rules are unit tests on a deal; an audit trail is an append-only event log; sign-off gates are authorization.

## What's next for Prism

- **External registries:** a lien (UCC-1) search with Secretary of State data, matched on serial number or VIN, to catch the same collateral pledged twice, plus business-registry checks on formation dates and registered agents.
- **Bank-account verification** for vendor payment accounts before disbursement.
- **Signals that need no shared entity,** such as timing and writing-style fingerprints. These would close our accepted blind spot, a ring that shares nothing visible, without loosening the hold rule.
- **A feedback loop:** Fraud Ops decisions feed the outcome discount, so entities linked to confirmed fraud gain weight and cleared ones lose it.
- **Production hardening:** authentication, role-based sign-off, persistent storage and a full audit export.

## Built with

Python · pandas · NetworkX · pypdf · pdfplumber · RapidOCR · FastAPI · Pydantic · React · Vite · TypeScript · Tailwind CSS · shadcn/ui · react-force-graph · NVIDIA Nemotron (super-vl, lightning, nano-omni reasoning) · NVIDIA API (build.nvidia.com) · OpenAI Python SDK

---

## For the Goldman Sachs track (DealPilot)

Prism covers the full commercial loan lifecycle the track asks for. **Read:** content-based document identification, fact extraction with provenance, and missing or mismatched information, with no false alarms on messy but honest files. **Move:** six stages in order, exit requirements enforced, sign-offs routed to the right person or their backup, alerts and escalations as stages run over, and funding deadlines respected. **Fraud:** coordinated rings held before Closed, as early as the evidence allows, with linked current deals and earlier history deals found. Its fraud detection is unsupervised anomaly detection learned from the bank's own history, so it is built for the idea rather than the example. No sample-specific value appears anywhere in the detector. Every threshold recomputes from new data. Our pitch number is the first blind run on new data: [[BLIND_HELD]] of [[BLIND_TOTAL]] held, [[BLIND_FALSE_FLAGS]] false flags. Every scored field comes from deterministic, reproducible code.

## For the NVIDIA Nemotron track

Nemotron does agent work, not chat. **Beyond a chatbot:** the investigator runs on its own for each held or watched cluster, without a user prompting it. **Multi-step workflows:** the investigator plans, calls tools, observes the results and revises over up to eight steps. **Tool use:** the investigator calls five read-only tools over the deal graph, the deals' documents and the loan history (cluster summary, deal entities, deals sharing an entity, history deal, deal documents); none can change state or a scored field, and every step is shown in the UI as an advisory trace, replayed over the fraud graph. Nemotron's vision model reads documents the parser cannot. **Real-world impact:** loan-fraud operations at a bank, where agent output must be cited and checked before anyone acts on it. Agents run on `nemotron-3.5-super-vl-120b` (agents, vision), `nemotron-3.5-lightning-30b` (fast text) and `nemotron-3-nano-omni-30b` reasoning (vision fallback), with a record-and-replay cache so the demo runs offline.

## Links

- Repository: [[REPO_URL]] (code only; the challenge data is not included; depends on the repository decision, 07-09 Task 3)
- Demo video: [[DEMO_VIDEO_URL]]
- Model specification: `docs/model/prism_model.pdf`
