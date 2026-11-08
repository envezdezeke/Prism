# Prism: 3-Minute Pitch Outline

> Owner: Jesse (pitch), Zeke (Q&A on the engine). Draft Sat 2026-11-07; cut to 3 minutes and re-pointed at built screens Sun 2026-11-08 (plan 07-09).
> Tracks: Goldman Sachs "DealPilot — Move the Deal. Stop the Fraud." (primary) and NVIDIA Nemotron (secondary).
> Sources: `HANDOFF.md` §3 and §6, `docs/MODEL_DESIGN.md`, `docs/model/prism_model.tex`, `docs/UI_PLAYBOOK.md`.

## Rules for this deck

- **Every result number comes from a committed record** (`eval/scorecard.md` and the files named in the placeholder table at the bottom; MODEL_DESIGN M21, D-26). Anything in `[[double brackets]]` is a placeholder. Fill it from its committed source and name the commit, or cut the line. Never round up and never estimate. As of Sun 02:30 CT none of those records exists, so no result number is filled.
- **Headline = the first blind run on the weekend drop**, recorded with its commit before anyone opened the files (HANDOFF §3 item 6). **Fallback:** if `eval/blind_drop_record.json` does not exist by H18 (Sun 09:55 CT), slide 5 leads with the held-out history replay and slide 1's headline uses it (D-24).
- **Confidentiality (D-49):** no borrower or business names, tax IDs, history deal IDs, staff names, folder names or dollar figures from the data pack, and no challenge text beyond the public title. Say "a 13-deal sample" and "a year of the bank's loan history". For the strange-is-not-fake line say "an honest borrower with a messy file", never a name. Screenshots come from the mock data (made-up names), never from the live sample run.
- **Never show a screen that is not built.** Lines tagged `[pending 07-xx]` describe a screen from a later plan. Say them only once that plan has shipped; otherwise use the fallback beside them.
- **Method language (D-29):** "unsupervised anomaly detection that learns what normal looks like from a year of history". The agents' tools are real HTTP calls to our API and the sim clock. Nemotron advises and the rule engine decides (D-28).
- **Sell the consequence, not the control.** Lead with what was caught; keep the technical name as a small label. Save the math for Q&A.
- Plain, calm delivery. No superlatives.

## Timing

Spoken slides (1, 2, 3, 5, 6, 7) run 2:00 at 150 words a minute, so their speaker notes total at most 300 words. The demo runs 1:00, so its Say column totals at most 150 words.

| # | Slide | Time |
|---|---|---|
| 1 | Hold the ring before the money goes out | 0:00–0:20 |
| 2 | One fake deal looks clean. The ring does not. | 0:20–0:45 |
| 3 | How Prism decides: three kinds of evidence must agree | 0:45–1:10 |
| 4 | Live demo | 1:10–2:10 |
| 5 | Measured, not claimed | 2:10–2:35 |
| 6 | Nemotron works around the engine, not inside the score | 2:35–2:50 |
| 7 | Built for the next trick, and where it stops | 2:50–3:00 |
| 8 | Close (on screen during Q&A) | Q&A |

Slide 7 is short on purpose: two sentences, then it stays up for Q&A alongside slide 8.

---

## Slide 1: Hold the ring before the money goes out

**Bullets**
- Prism runs a commercial lending desk end to end: reads the loan folder, moves each deal through six stages, asks the right person at every sign-off.
- Its main job: catch coordinated fake loan applications before disbursement, without blocking honest borrowers.
- First blind run on the organizers' new data: [[BLIND_HELD]] of [[BLIND_TOTAL]] fake deals held before Closed, [[BLIND_FALSE_FLAGS]] false flags.

**Speaker notes**
Prism is a lending desk that reads a bank's loan folder and moves every deal from intake to funding. Its real job is fraud. On new data, it held [[BLIND_HELD]] of [[BLIND_TOTAL]] fake deals before any money went out, and wrongly flagged [[BLIND_FALSE_FLAGS]] good ones.

**Visual**
Pipeline board with one held deal's red "Held: fraud review" badge visible (built; mock-data screenshot). Headline number overlaid in large tabular type at the top.

---

## Slide 2: One fake deal looks clean. The ring does not.

**Bullets**
- Each fake application passes the bank's existing known-fraud checks on its own.
- Rings are cheap because they reuse resources: one bookkeeper, one payment account, the same document software.
- Every reuse leaves a trace that is rare in the bank's own history and shared across deals.

**Speaker notes**
Alone, each fake passes every check the bank runs. But rings are built cheaply. One person prepares the books for companies that claim to be unrelated. Equipment money heads to a lookalike of a real vendor's account. Their bank statements come out of the same document software. Each trace is rare in honest history, so Prism compares deals.

**Visual**
`[pending 07-01/07-03]` The fraud graph with the ring's deals joined by thick edges to a few shared entities; entity types only, no names. Fallback until it ships: text only, three plain-language catches in a row (hidden preparer, lookalike payment account, shared document software).

---

## Slide 3: How Prism decides: three kinds of evidence must agree

**Bullets**
- Unsupervised anomaly detection: every signal is surprise measured against a year of clean history. A rare shared entity scores high, a common one scores near zero.
- Six evidence families: shared rare entity, sudden new activity, lookalike counterparty, document fingerprint, deposit pattern, and loan terms (shown, never votes).
- Hold only when a shared rare entity is present and at least two other families agree. One or two families gives a visible watch list, not a hold.
- Thresholds come from false-alarm rates on clean deals only. They are never fitted to fraud examples.

**Speaker notes**
Every signal is scored as surprise against a year of clean history. We hold a deal only when it shares something rare with another deal and two more kinds of evidence agree. Fewer means a watch list. Strange isn't fake: an honest borrower with a messy file stays out.

**Visual**
`[pending 07-03]` The cluster panel's family checklist: F1 to F6 in order, each marked Fired or Not fired in words with its evidence sentence, F6 marked "Evidence only. Never votes.", and a header counting how many of the four voting families fired. No numbers against thresholds. Fallback until it ships: the deal page's fraud panel (built), which shows the plain-English reason and linked deals.

---

## Slide 4: Live demo (60 seconds)

**Bullets**
- Pipeline board on the simulated clock: Next event and Replay from start.
- A held deal, its reason and its linked deals.
- `[pending 07-01/07-03]` The fraud graph replaying as the ring connects, with the evidence sentence for each link.
- Inbox: the Committee approval request, then Approve.

**Speaker notes**
See the demo script below. If the live app fails, switch to the recorded demo video at the same timestamp and keep talking. Nemotron runs in replay mode, so the demo needs no network.

**Visual**
The running app (Nemotron in replay mode). Backup: the recorded demo video, [[DEMO_VIDEO_URL]].

---

## Slide 5: Measured, not claimed

**Bullets**
- Blind weekend drop, frozen engine, first run recorded before anyone opened the files: [[BLIND_HELD]] of [[BLIND_TOTAL]] held, [[BLIND_FALSE_FLAGS]] false flags, first hold at stage [[BLIND_FIRST_STAGE]], commit [[BLIND_COMMIT]].
- A year of history replayed in time order, last four months never used for tuning: [[HIST_FLAGS]] flags among [[HIST_GOOD_N]] good deals; after written review, [[HIST_SCHEME]] scheme members and [[HIST_FALSE_POS]] false positives; first flag at deal [[HIST_FIRST_DEAL]] of the scheme.
- Synthetic tricks (one hold-rule setting was chosen on this bench, Sun 09:00; say so if asked) with honest lookalike twins, one family held out at a time: [[SYN_HELD_PCT]] of ring deals held, [[SYN_TWIN_PCT]] of twins flagged. Target was at least 70% held, at most 5% flagged.
- Sample week: ring held before funding, earlier funded members linked, zero false holds on the deliberately odd honest borrowers: held at stage [[SAMPLE_STAGE]], history links [[SAMPLE_LINKS]], false holds [[SAMPLE_FALSE_HOLDS]].

**Speaker notes**
Banks trust a fraud model when its false-alarm rate is measured. We froze the engine before the weekend data arrived and recorded the first run before anyone opened the files. Replaying a year of history in time order, with the last four months held out, it flagged [[HIST_FLAGS]] good deals. After written review, [[HIST_FALSE_POS]] were real false positives.

**Visual**
A single scorecard table rendered from `eval/scorecard.md`: set, size, tuned on it (yes/no), result. The tuned-on column makes the point: only one row says yes. Scorecard commit hash in small type at the bottom.

---

## Slide 6: Nemotron works around the engine, not inside the score

> **Sun 09:00 CT:** the investigator and vision reader shipped (06-01, 06-02). The red team (06-03) was cut and no prosecutor/defender code exists, so neither is on the slide; do not mention them.

**Bullets**
- Investigator agent: plans, calls our live HTTP API and the bank's clock service, and writes a cited evidence case for each held or watched cluster.
- Vision reader for documents the parser cannot read, validated before it can fill any field. The scored output is byte-identical with Nemotron on or off.

**Speaker notes**
Nemotron works around the engine, not inside the score. An investigator calls our real API and the sim clock over HTTP and builds a cited case. Nemotron advises; the rule engine decides.

**Visual**
`[pending 07-04/07-05]` The investigation panel (labelled advisory) beside the red-team results table; show only the part that has shipped. Fallback until either ships: text only.

---

## Slide 7: Built for the next trick, and where it stops

**Bullets**
- Nothing sample-specific in the detector: no names, no software strings, no account numbers. Thresholds re-derive from whatever history ships with a new dataset.
- Deliberate bet: the hidden trick is still a ring, so it must share something. A trick that shares no visible entity lands on the watch list, not on hold.

**Speaker notes**
It is unsupervised anomaly detection that learns what normal looks like from a year of history, so nothing is sample-specific. Our one blind spot is a fraud that shares nothing across deals. We accept it: a false hold on a good borrower is expensive.

**Visual**
`[pending 07-01/07-03]` The fraud graph zoomed out, with common entities drawn faint ("used by many deals, mostly repaid") and rare ones thick. Fallback until it ships: text only.

---

## Slide 8: Close

**Bullets**
- Prism: catches the ring before the money goes out, leaves honest borrowers alone, and shows its work.
- Deterministic engine for every scored decision; a Nemotron agent investigates each held ring and a vision model reads hard documents, never inside the score.
- Team Prism: finance and quant. [[REPO_URL]] · [[DEMO_VIDEO_URL]]

**Speaker notes**
Not spoken unless there is time. Stays up during questions.

**Visual**
Wordmark, the headline number again ([[BLIND_HELD]] of [[BLIND_TOTAL]] held, [[BLIND_FALSE_FLAGS]] false flags), and the scorecard commit [[SCORECARD_COMMIT]].

---

## 60-second live-demo script

Setup before the talk: engine run finished on the sample week, API and UI running, Nemotron in replay mode, browser at 1440x900 on the Pipeline board, sim clock at the start of the week. Keep the recorded video open in a second tab. The Wi-Fi is off for this segment to prove replay mode.

| Time | Screen | Action | Say |
|---|---|---|---|
| 0:00–0:12 | Pipeline board | Press "Replay from start", then "Next event" twice. | "This is the bank's pipeline on a simulated week. Files arrive, deals move through six stages, and each stage has a time limit. Amber means overdue, and the right person is already alerted." |
| 0:12–0:25 | Pipeline board, held deal | Point at the red "Held: fraud review" badge. Open the deal and show the fraud panel. | "This deal was held at [[STAGE_AT_FLAG]], before any money went out. Here is the plain-English reason, and the deals it links to." |
| 0:25–0:45 | Fraud graph `[pending 07-01/07-03]` | Click Fraud graph in the rail. Press "Replay from start", then "Next event" and watch links appear. Click one link and read its evidence sentence. When the clock reaches the hold, the cluster panel turns Held. End on the held deal's red badge and the investigation panel, labelled advisory `[pending 07-04]`. | "Watch the ring connect as files arrive. Three applications that claim to be unrelated share a bookkeeper, a payment account and the same document software. Prism also found [[HISTORY_LINKS]] earlier funded loans from the same kit. The agent's note is advice. The rule engine decides." |
| 0:45–1:00 | Inbox | Open the Inbox, select the Committee approval request, click Approve. | "Good deals keep moving. Every sign-off goes to the right person, with a backup when someone is out. No single person can push a loan through." |

If something breaks: say "let me switch to the recording", jump to the same step in the video, and keep the script.

**Pending steps and fallbacks (not spoken, not counted in the Say column).**
- Row 3 needs the fraud graph page (07-01, 07-03) and, for its last action, the investigation panel (07-04). If the graph page has not shipped by the H18 freeze, drop row 3 and say instead, over the Alerts feed: "When a deal is stuck, the alert says whose deal it is, how long it has waited and what unblocks it." (21 words, within row 3's budget). If only the investigation panel is missing, drop the last sentence of the Action and of the Say.
- Row 2 says "the deals it links to" from the built deal-page fraud panel. On mock data it shows the linked deals; on the live run it shows them only once the fraud decision is wired.
- Row 4: on the mock data the Committee approval request is a one-sentence message. It becomes the credit memo's four-line version (MOVE-10) only on the live engine run, so do not claim the memo on screen until the live switch (07-02) is confirmed. The deal page has no memo section; do not scroll for one.

---

## Judge Q&A

**1. "Isn't this just rules?"**
The final hold is a rule, on purpose: Fraud Ops and auditors need to know exactly why a deal was stopped, and the output has to be reproducible. The inputs to the rule are learned from data. Each signal is a probability estimated from a year of clean history, rarity of an entity, how often a document producer shows up for that kind of document, how a deposit pattern compares with the history distribution. Change the history and every threshold moves with it. That is unsupervised anomaly detection, not a hand-written list of bad things.

**2. "Why not train a classifier?"**
Because the labels describe old tricks, and the hidden set uses a new one. A classifier trained on known fraud learns those tricks and misses the next one. We model what normal looks like instead, so anything abnormal and shared across deals stands out. A second reason: with only a handful of labelled fraud deals, a classifier's false-alarm rate cannot be estimated reliably. Ours is set directly, family by family, on clean deals.

**3. "How do you know it generalizes?"**
Three tests, none of which we tuned on. The blind weekend drop, run once on a frozen engine before anyone looked: [[BLIND_HELD]] of [[BLIND_TOTAL]], [[BLIND_FALSE_FLAGS]] false flags. History replayed in time order with the last four months held out: [[HIST_FLAGS]] flags, [[HIST_FALSE_POS]] false positives. Synthetic fraud families with one family left out at a time (one hold-rule setting was chosen on these, so treat it as a check, not a blind test): [[SYN_HELD_PCT]] held, [[SYN_TWIN_PCT]] of twins flagged. The sample week is not on that list, because we studied its trick and it is no longer a fair test.

**4. "What if the hidden trick shares no entity across deals?"**
Then Prism will not hold it. Those deals would show on the watch list with their evidence, and a human would decide. This is a deliberate trade. Requiring a shared rare entity is what keeps honest but unusual borrowers out of the fraud queue, and false holds are expensive for the bank and the borrower. Our bet is that a ring, by definition, reuses something. The bank's existing single-deal checks still run alongside.

**5. "How many false alarms will this produce in production?"**
By design, each voting family misfires on about 5% of clean deals, and a hold needs the mandatory family plus two of four others. If the families were independent, that is under one false hold per thousand deals. They are not fully independent, so we treat that as a target and measure the real rate: [[HIST_FALSE_POS]] false positives among [[HIST_GOOD_N]] good deals on held-out history, and [[SAMPLE_FALSE_HOLDS]] false holds on [[TRAP_N]] odd-but-honest sample borrowers.

**6. "What does Nemotron actually do, and why trust it near fraud decisions?"**
It never makes one. The investigator reads the evidence through read-only HTTP tools, real calls to our API and the sim clock, and writes a case that must cite evidence IDs; uncited claims are marked by code, uncited rate [[UNCITED_RATE]]. The vision reader can only fill a field the parser left empty, after a format check and agreement with a second document, and it can never raise an issue or a hold. Every call is cached, so the run replays exactly, and the scored file is byte-identical with Nemotron off.

**7. "How early does it catch the ring?"**
Scores are recomputed on every file arrival, and the hold fires on the first arrival that meets the rule, even at Intake. Holds are sticky until Fraud Ops releases them. On the blind drop the first hold came at stage [[BLIND_FIRST_STAGE]]; in the history replay, the first flag came at deal [[HIST_FIRST_DEAL]] of the scheme.

**8. "What happens on the hidden set if your API key isn't there or the API is down?"**
Nothing changes in the score. Prism checks for the key at startup; without it, Nemotron is switched off and the deterministic engine writes the same file. Any single failed call also falls back to off. The engine takes the folder and arrival log as arguments, so a new dataset runs with no code changes, and its thresholds recompute from whatever history ships with it.

**Spare questions, if time allows**
- *"Why bits?"* One unit lets six different signals be compared and summed for display, and it reads naturally: 10 bits means about one in a thousand by chance under clean history. The hold decision never uses the sum, only the rule.
- *"Why does the loan-terms family not vote?"* Young companies, round amounts and amounts just under an approval limit are common among honest small businesses, and they move together. Letting them vote would double-count and push good borrowers into holds.
- *"Is this AI/ML?"* Yes: unsupervised anomaly detection that learns what normal looks like from a year of history, plus Nemotron agents. "No classifier" is our reason it carries over to a new trick, not a lack of machine learning.

---

## Placeholders to fill before the talk

Status at drafting (Sun 02:30 CT): none of the committed sources below exists yet, so every placeholder is still open. 07-10 fills them and names each commit. Fill a placeholder only from its committed source; if the source is missing at H18, cut the sentence. Fallback for the headline: if `eval/blind_drop_record.json` does not exist by H18 (Sun 09:55 CT), slide 5 leads with the held-out history replay and slide 1's headline uses it (D-24).

| Placeholder | What it is | Committed source |
|---|---|---|
| `[[BLIND_HELD]]`, `[[BLIND_TOTAL]]`, `[[BLIND_FALSE_FLAGS]]`, `[[BLIND_FIRST_STAGE]]` | Fake deals held, fake deals in the drop, false flags on good deals, stage of the first hold, all from the first blind run | `eval/blind_drop_score.json`; the commit it was run at is in `eval/blind_drop_record.json` |
| `[[BLIND_COMMIT]]` | Commit of the frozen engine for the first blind run | `eval/blind_drop_record.json` |
| `[[HIST_FLAGS]]`, `[[HIST_GOOD_N]]`, `[[HIST_SCHEME]]`, `[[HIST_FALSE_POS]]`, `[[HIST_FIRST_DEAL]]` | Held-out history replay: flags among good deals, size of the good set, flags that belong to the scheme after written review, real false positives, position of the first flag in the scheme | `eval/scorecard.md` (held-out history section) plus Jesse's written reviews (path to be named by 07-10) |
| `[[SYN_HELD_PCT]]`, `[[SYN_TWIN_PCT]]` | Synthetic leave-one-family-out: share of ring deals held, share of honest twins flagged | `eval/scorecard.md` (synthetic section) |
| `[[SAMPLE_STAGE]]`, `[[SAMPLE_LINKS]]`, `[[SAMPLE_FALSE_HOLDS]]`, `[[HISTORY_LINKS]]` | Sample week: stage at hold, history links found out of those expected, false holds, count of earlier funded loans linked | `eval/scorecard.md` (sample regression section); the dry-run claim may cite `eval/DRY_RUN.md` |
| `[[STAGE_AT_FLAG]]` | Stage at which the held deal in the demo was flagged | `eval/scorecard.md` (sample regression section), checked against the demo run on the same commit |
| `[[TRAP_N]]` | Number of odd-but-honest sample borrowers in the trap suite | `eval/scorecard.md` (trap suite section) |
| `[[RED_TRICKS]]`, `[[RED_CATCH_BY_GEN]]` | Tricks the red team invented, and catch rate by generation | `eval/redteam_report.json`, a snapshot of `GET /api/redteam` committed by 07-10 |
| `[[UNCITED_RATE]]`, `[[VL_FILL]]` | Share of investigator claims with no evidence ID; vision reader fill accuracy on masked documents | `eval/scorecard.md` (Nemotron section) |
| `[[READ_ACCURACY]]` | Share of fields correct against the hand-labelled answer key | `eval/scorecard.md` (READ self-score) |
| `[[SCORECARD_COMMIT]]` | Commit hash that produced the scorecard | `git log -1 -- eval/scorecard.md` after 07-10 commits it |
| `[[DEMO_VIDEO_URL]]`, `[[REPO_URL]]` | Submission links | The submission form; `[[REPO_URL]]` depends on Jesse's repository decision (07-09 Task 3) |
