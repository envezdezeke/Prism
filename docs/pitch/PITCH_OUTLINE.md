# Prism: 3-Minute Pitch Outline

> Owner: Jesse (pitch), Zeke (Q&A on the engine). Draft, Sat 2026-11-07.
> Tracks: Goldman Sachs "DealPilot — Move the Deal. Stop the Fraud." (primary) and NVIDIA Nemotron (secondary).
> Sources: `HANDOFF.md` §3 and §6, `docs/MODEL_DESIGN.md`, `docs/model/prism_model.tex`, `docs/UI_PLAYBOOK.md`.

## Rules for this deck

- **Every result number comes from a committed scorecard** (`eval/scorecard.md`, MODEL_DESIGN M21). Anything in `[[double brackets]]` is a placeholder. Fill it from the scorecard or cut the line. Never round up and never estimate.
- **Headline = the first blind run on the weekend drop**, recorded with its commit before anyone opened the files (HANDOFF §3 item 6). If the drop arrives too late, the held-out history replay becomes the headline and slide 5 swaps its order.
- **Confidentiality:** no borrower or business names, tax IDs, history deal IDs, staff names, folder names or dollar figures from the data pack, and no challenge text beyond the public title. Say "a 13-deal sample" and "a year of the bank's loan history".
- **Sell the consequence, not the control.** Lead with what was caught; keep the technical name as a small label. Save the math for Q&A.
- Plain, calm delivery. No superlatives.

## Timing

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

Slide 7 is short on purpose: one sentence, then it stays up for Q&A alongside slide 8.

---

## Slide 1: Hold the ring before the money goes out

**Bullets**
- Prism runs a commercial lending desk end to end: reads the loan folder, moves each deal through six stages, asks the right person at every sign-off.
- Its main job: catch coordinated fake loan applications before disbursement, without blocking honest borrowers.
- First blind run on the organizers' new data: [[BLIND DROP: x of y fake deals held before Closed, z false flags]].

**Speaker notes**
We built Prism, a lending desk that reads a bank's loan folder and moves every deal from intake to funding. Its real job is fraud. Fraud rings send several fake applications that each look fine on their own. On data we had never seen, Prism held [[x of y]] fake deals before any money went out, and flagged [[z]] good ones by mistake.

**Visual**
Pipeline board (UI-02) with one held deal's red "Held: fraud review" badge visible. Headline number overlaid in large tabular type at the top.

---

## Slide 2: One fake deal looks clean. The ring does not.

**Bullets**
- Each fake application passes the bank's existing known-fraud checks on its own.
- Rings are cheap because they reuse resources: one bookkeeper, one payment account, one document generator, one deposit pattern.
- Every reuse leaves a trace that is rare in the bank's own history and shared across deals.

**Speaker notes**
If you look at one application at a time, the fakes pass every check the bank already runs. What gives a ring away is that it is built on the cheap. The same person prepares the books for companies that claim to be unrelated. Equipment money is headed to a lookalike copy of a real vendor's bank account. The bank statements came out of a document generator, not a bank. Each of those traces is rare in a year of honest history, and each one is shared across deals. So Prism compares deals with each other, not one at a time.

**Visual**
Side by side: on the left, the old checks with every fake deal passing in green; on the right, the same deals connected in the fraud graph (UI-06) by thick edges to a few shared entities. No names on screen, entity types only.

---

## Slide 3: How Prism decides: three kinds of evidence must agree

**Bullets**
- Every signal is measured in one unit: bits of surprise against a year of clean history. A rare shared entity scores high, a common one scores near zero.
- Six evidence families: shared rare entity, sudden new activity, lookalike counterparty, document fingerprint, deposit pattern, and loan terms (shown, never votes).
- Hold only when a shared rare entity is present and at least two other families agree. One or two families gives a visible watch list, not a hold.
- Thresholds come from false-alarm rates on clean deals only. They are never fitted to fraud examples.

**Speaker notes**
Everything is scored in one unit, bits of surprise. If a bookkeeper appears on one in two hundred honest deals, seeing them on three new deals at once is very surprising. If an address is shared by dozens of deals that mostly repaid, it is not. We group the evidence into six independent families. A deal is held only when it shares something rare with another deal and at least two other families agree. We set each family to misfire on about one in twenty clean deals, using clean history only. Requiring three to agree is what keeps good borrowers out of the fraud queue. Every held deal gets a plain-English reason and a one-click view of the evidence.

**Visual**
Deal detail fraud panel (UI-04, right column): families F1 to F6 listed in order, each with bits against its threshold, F6 marked "evidence only", a "3 of 4 voting families agree" header.

---

## Slide 4: Live demo (60 seconds)

**Bullets**
- Pipeline board on the simulated clock.
- A held deal and its reasons.
- The fraud graph replaying as the ring connects.
- The credit memo and sign-off inbox for a good deal.

**Speaker notes**
See the demo script below. If the live app fails, switch to the recorded demo video at the same timestamp and keep talking. Nemotron runs in replay mode, so the demo needs no network.

**Visual**
The running app (Nemotron in replay mode). Backup: the recorded demo video, [[DEMO VIDEO URL]].

---

## Slide 5: Measured, not claimed

**Bullets**
- Blind weekend drop, frozen engine, first run recorded before anyone opened the files: [[BLIND DROP: x/y holds, z false flags, first hold at stage S, commit abc1234]].
- A year of history replayed in time order, last four months never used for tuning: [[HISTORY REPLAY: f flags among n good deals; after written review, a scheme members and b false positives]]; first flag at deal [[k]] of the scheme.
- Fraud types it never saw: synthetic tricks with honest lookalike twins, one family held out at a time: [[SYNTHETIC: x% of ring deals held, y% of twins flagged]]. Target was at least 70% held, at most 5% flagged.
- Sample week: ring held before funding, earlier funded members linked, zero false holds on the deliberately odd honest borrowers: [[SAMPLE: held at stage S, history links x/y, false holds 0/n]].

**Speaker notes**
Banks trust a fraud model when its false-alarm rate is measured, so we measured it. We froze the engine before the organizers' weekend data arrived and recorded the first run before anyone looked at the files. That run held [[x of y]] fake deals with [[z]] false flags. Then we replayed a year of the bank's history in time order. The last four months were never used to set anything. Prism flagged [[f]] good deals there. We reviewed each one in writing: [[a]] turned out to belong to the scheme, and [[b]] were real false positives. On synthetic fraud families it was never tuned on, it held [[x]] percent of ring deals and flagged [[y]] percent of the honest twins.

**Visual**
A single scorecard table rendered from `eval/scorecard.md`: set, size, tuned on it (yes/no), result. Tuned-on column makes the point: only one row says yes. Commit hash in small type at the bottom.

---

## Slide 6: Nemotron works around the engine, not inside the score

**Bullets**
- Investigator agent: plans, calls our live HTTP API and the bank's clock service, and writes a cited evidence case for each held or watched cluster.
- Prosecutor and defender: two briefs on the same evidence, so Fraud Ops sees the innocent explanation too. The rule still decides.
- Adaptive red team: Nemotron invents new fraud tricks, sees only which ones were caught, and evolves them over generations: [[RED-TEAM: n tricks invented, catch rate gen1/gen2/gen3]].
- Vision reader for documents the parser cannot read, validated before it can fill any field. The scored output is byte-identical with Nemotron on or off.

**Speaker notes**
Nemotron does the work code cannot: reasoning over messy evidence, and attacking our own detector. The investigator plans its steps, calls our real API and the clock service, and every claim it writes must cite an evidence ID. A deterministic check marks anything uncited. The red team tries to beat the detector, sees only what was caught, and tries again. That is our hardest test. Nemotron never decides a hold. The scored file is the same with it switched off.

**Visual**
Investigator trace panel: the step list (plan, tool call to an HTTP endpoint, observation, cited claim) next to the red-team view (UI-07) with catch rate per generation.

---

## Slide 7: Built for the next trick, and where it stops

**Bullets**
- Nothing sample-specific in the detector: no names, no software strings, no account numbers. Thresholds re-derive from whatever history ships with a new dataset.
- Deliberate bet: the hidden trick is still a ring, so it must share something. A trick that shares no visible entity lands on the watch list, not on hold.

**Speaker notes**
Because the detector learns what normal looks like and never memorizes a trick, it should carry over to the hidden set. Our one known blind spot is a fraud that shares nothing across deals. We chose to accept that, because the cost of a false hold on a good borrower is high.

**Visual**
Fraud graph zoomed out, with common entities drawn faint ("used by many deals, mostly repaid") and rare ones thick.

---

## Slide 8: Close

**Bullets**
- Prism: catches the ring before the money goes out, leaves honest borrowers alone, and shows its work.
- Deterministic engine for every scored decision; Nemotron agents to investigate, argue both sides and attack it.
- Team Prism: finance and quant. [[REPO URL]] · [[DEMO VIDEO URL]]

**Speaker notes**
Not spoken unless there is time. Stays up during questions.

**Visual**
Wordmark, the headline number again, and the scorecard commit hash.

---

## 60-second live-demo script

Setup before the talk: engine run finished on the sample week, API and UI running, Nemotron in replay mode, browser at 1440x900 on the Pipeline board, sim clock at the start of the week. Keep the recorded video open in a second tab.

| Time | Screen | Action | Say |
|---|---|---|---|
| 0:00–0:12 | Pipeline board | Press "Advance to next arrival" twice, then drag the clock scrubber forward. | "This is the bank's pipeline on a simulated week. Files arrive, deals move through six stages, and this thin bar is each stage's time limit. Amber means a deal is overdue, and the right person has already been alerted." |
| 0:12–0:25 | Pipeline board → held deal | Point at the red "Held: fraud review" badge. Open the deal. | "This deal was held at [[stage at flag]], before any money went out. Here are the three plain-English reasons, and here is the evidence: each family, its bits of surprise, and its threshold." |
| 0:25–0:42 | Fraud graph | Click Fraud graph in the left rail. Replay from the start of the week. | "Watch the ring connect as files arrive. Thick edges are rare shared entities. Faint ones are common and are ignored. Three applications that claim to be unrelated share a bookkeeper, a payment account and a document fingerprint. And Prism found [[HISTORY LINKS: n]] earlier, already-funded loans in history built from the same kit." Click one edge to show its evidence sheet. |
| 0:42–0:52 | Deal detail, good deal | Open a clean deal at Committee. Scroll to the credit memo. | "Good deals keep moving. At Committee, Prism writes the credit memo: debt coverage, revenue support, a 1 to 5 risk grade and conditions. All of it is computed, none of it is generated text." |
| 0:52–1:00 | Inbox | Open the Inbox, select the committee approval request, click Approve. | "And every sign-off goes to the right person, with a backup when someone is out. No single person can push a loan through." |

If something breaks: say "let me switch to the recording", jump to the same step in the video, and keep the script.

---

## Judge Q&A

**1. "Isn't this just rules?"**
The final hold is a rule, on purpose: Fraud Ops and auditors need to know exactly why a deal was stopped, and the output has to be reproducible. The inputs to the rule are learned from data. Each signal is a probability estimated from a year of clean history, rarity of an entity, how often a document producer shows up for that kind of document, how a deposit pattern compares with the history distribution. Change the history and every threshold moves with it. That is unsupervised anomaly detection, not a hand-written list of bad things.

**2. "Why not train a classifier?"**
Because the labels describe old tricks, and the hidden set uses a new one. A classifier trained on known fraud learns those tricks and misses the next one. We model what normal looks like instead, so anything abnormal and shared across deals stands out. A second reason: with only a handful of labelled fraud deals, a classifier's false-alarm rate cannot be estimated reliably. Ours is set directly, family by family, on clean deals.

**3. "How do you know it generalizes?"**
Four tests, none of which we tuned on. The blind weekend drop, run once on a frozen engine before anyone looked: [[BLIND DROP: x/y, z false flags]]. History replayed in time order with the last four months held out: [[HISTORY REPLAY: f flags, b false positives]]. Synthetic fraud families with one family left out at a time: [[SYNTHETIC: x% held, y% twins flagged]]. And Nemotron's red team, which invents tricks we did not write: [[RED-TEAM: catch rate]]. The sample week is not on that list, because we studied its trick and it is no longer a fair test.

**4. "What if the hidden trick shares no entity across deals?"**
Then Prism will not hold it. Those deals would show on the watch list with their evidence, and a human would decide. This is a deliberate trade. Requiring a shared rare entity is what keeps honest but unusual borrowers out of the fraud queue, and false holds are expensive for the bank and the borrower. Our bet is that a ring, by definition, reuses something. The bank's existing single-deal checks still run alongside.

**5. "How many false alarms will this produce in production?"**
By design, each voting family misfires on about 5% of clean deals, and a hold needs the mandatory family plus two of four others. If the families were independent, that is under one false hold per thousand deals. They are not fully independent, so we treat that as a target and measure the real rate: [[HISTORY REPLAY: b false positives among n good deals]] on held-out history, and [[TRAP SUITE: 0 false holds on n odd-but-honest sample borrowers]].

**6. "What does Nemotron actually do, and why trust it near fraud decisions?"**
It never makes one. The investigator, prosecutor and defender read the evidence through read-only HTTP tools and write briefs that must cite evidence IDs; uncited claims are marked by code, [[CITATION: uncited claim rate]]. The red team attacks the detector to test it. The vision reader can only fill a field the parser left empty, after a format check and agreement with a second document, and it can never raise an issue or a hold. Every call is cached, so the run replays exactly, and the scored file is byte-identical with Nemotron off.

**7. "How early does it catch the ring?"**
Scores are recomputed on every file arrival, and the hold fires on the first arrival that meets the rule, even at Intake. Holds are sticky until Fraud Ops releases them. On the blind drop the first hold came at [[BLIND DROP: stage S, n hours after the deal's first file]]; in the history replay, the first flag came at deal [[k]] of the scheme.

**8. "What happens on the hidden set if your API key isn't there or the API is down?"**
Nothing changes in the score. Prism checks for the key at startup; without it, Nemotron is switched off and the deterministic engine writes the same file. Any single failed call also falls back to off. The engine takes the folder and arrival log as arguments, so a new dataset runs with no code changes, and its thresholds recompute from whatever history ships with it.

**Spare questions, if time allows**
- *"Why bits?"* One unit lets six different signals be compared and summed for display, and it reads naturally: 10 bits means about one in a thousand by chance under clean history. The hold decision never uses the sum, only the rule.
- *"Why does the loan-terms family not vote?"* Young companies, round amounts and amounts just under an approval limit are common among honest small businesses, and they move together. Letting them vote would double-count and push good borrowers into holds.
- *"Is this AI/ML?"* Yes: unsupervised anomaly detection that learns what normal looks like from a year of history, plus Nemotron agents. "No classifier" is our reason it carries over to a new trick, not a lack of machine learning.

---

## Placeholders to fill before the talk

| Placeholder | Source |
|---|---|
| `[[BLIND DROP: x/y holds, z false flags, first hold stage S, commit]]` | First recorded scorecard on the weekend drop (`eval/scorecard.md` + tag) |
| `[[HISTORY REPLAY: f flags among n good deals; a scheme members, b false positives; first flag at deal k]]` | Held-out history section of the scorecard + Jesse's written reviews |
| `[[SYNTHETIC: x% held, y% twins flagged]]` | Leave-one-family-out section of the scorecard |
| `[[SAMPLE: stage held, history links x/y, false holds 0/n]]` | Sample regression + trap suite |
| `[[TRAP SUITE: 0 false holds on n]]` | Trap suite |
| `[[RED-TEAM: n tricks, catch rate per generation]]` | Red-team report endpoint |
| `[[CITATION: uncited claim rate]]` | Scorecard, Nemotron section (N11) |
| `[[HISTORY LINKS: n]]` | Sample run `history_flags` count |
| `[[stage at flag]]` | Demo run output for the held deal shown |
| `[[DEMO VIDEO URL]]`, `[[REPO URL]]` | Submission links |
