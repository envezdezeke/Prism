# Prism fraud detection red-team (read-only audit, 2026-11-08)

Repo state audited: `main` at dc4b821. Scripts and outputs: `/private/tmp/claude-501/-Users-jes-Goldman-I/c24be65f-9ce6-4015-9d75-c8a0512b091e/scratchpad/redteam/` (`harness.py`, `e1`..`e17`). Everything run with `.venv/bin/python`, `PYTHONUTF8=1`. No repo file touched.

Harness: real `build_baseline`-equivalent over the 257 history deals (`Baseline.from_rows` + `compute_thresholds`), synthetic current `DealState`s with `EntityRef`s and `features["deposit_months"]`, run through the real `build_graph` + `compute_signals`. The hold verdict in the scripts is my implementation of the stated rule (F1 fired AND >=2 of F2..F5 fired; only F3/F5 exist), because `decide()` is a stub.

---

## 0. Bottom line

The signal math (F1, F3, F5) is real, deterministic and generic. **The product does not detect anything yet**: `decide()` returns an empty outcome and the whole Read side (`extract_entities`, `features["deposit_months"]`, `detect_issues`/OLD_TRICK) is a stub. On top of that, the design as built has four structural weaknesses that will cost score on a different hidden trick: the hold needs F3 (an equipment-vendor-specific signal), F1 is non-specific (37% of history, every returning customer), the calibration is wired to sample dates, and entity matching is brittle.

---

## 1. Findings, ranked by expected score impact

### R1 (CRITICAL) Nothing is wired: the shipped run flags nothing
- Evidence: `prism/fraud/decide.py:25-34` (`decide` returns `FraudOutcome()`); `prism/read/extract.py` (`extract_entities` returns `[]`, `extract_facts` returns `{}`); `prism/read/issues.py` (returns `[]`); `prism/read/classify.py` (unchanged doc). Nobody writes `state.features["deposit_months"]` (grep: only `signals.py` reads it).
- Proof: `python -m prism run ... --out sub.json` on the sample: 13 deals, `history_flags == []`, every deal `flagged False, held False`, every deal sits in a single stage_log entry. Against `eval/gold.json` that is 3 ring deals missed, Granite Bay (old trick, gold flagged+held) missed, `linked_deals` all empty, `history_flags` missed.
- Also absent: OLD_TRICK path (J17, Granite Bay), M13 audit write-out of computed thresholds, M14 verification request, cluster p-value/PMI, F2, F4, F6.
- `pyproject.toml` dependencies are `fastapi, pydantic, pyyaml, uvicorn`; `pypdf` is not installed in `.venv` (import fails). Read cannot even open a PDF in a fresh environment.
- Fix (minimum, in score order): (1) Read: entities + `deposit_months` rows + per-document producer; (2) `decide()` with the rule, stickiness, `flagged_at`, `stage_at_flag`, `reason`, `linked_deals`, `history_flags`; (3) OLD_TRICK path to Fraud Ops; (4) declare pypdf/pdfplumber in pyproject.

### R2 (CRITICAL) The only buildable hold today is F1 AND F3 AND F5, and F3 is an equipment-vendor signal
- Evidence (e10, current code, no history ring involved, vendor = lookalike of a different frequent vendor):
  - Full kit shared (preparer, phone, agent, producer) + manufactured deposits, ring of 3, lookalike vendor: **watch [F1,F5], never hold**.
  - Same with non-equipment loan (no vendor): **watch**. Same with new non-imitating vendor: **watch**.
  - Shared kit, careful (normal-looking) deposits: **watch [F1]**.
  - Single deal with everything wrong but nothing shared: **watch [F5]** (by design M2).
  - Sample-like ring (e1, uses the sample's own vendor string): HOLD. Drop the vendor: **watch [F1,F5]** (e1 "no vendor").
- So any hidden trick that is not "equipment vendor imitation + manufactured deposits" tops out at watch. Until F2/F4 exist there is no second path.
- **F3 is much weaker than described.** (e4, e11, e12) F3 "remit account differs from the vendor's modal account" accounts for 26 of 31 historical firings. Honest history vendors each carry a different last-4 per deal, so F3 fires on **31 of 86 (36%) historical equipment loans** (28 of the 70 that belong to a frequent-vendor group), i.e. it is "equipment loan from a repeated vendor", not "lookalike". All three difference kinds (suffix swap, exact name + new account, 1-edit typo) get identical bits per group.
- **F3 has a knife-edge threshold** (e11): tau 4.43; groups score 3.86/4.12/4.44/4.86 purely from group size. Riverbend (6 deals), Lakeside, Northgate, Pecan, Trinity cannot fire on a suffix swap (5 of 12 groups); Cedar, Coit, Heritage, Magnolia, Metroplex, Oak Cliff, Sunset can. One extra history deal flips it.
- **Design-level risk when F2/F4 land (inferred, not runnable yet):** F2 ("entity new to history") is true by construction for any F1-linked brand-new entity, so F1+F2 is one fact counted twice. Likewise F1 `pdf_producer` and F4 "producer rare for class" are the same fact; F1 `vendor` and F3 are the same vendor group. Honest case: three siblings share a new bookkeeper (T1-B1) + one equipment loan from a recurring vendor with a new account => F1 + F2 + F3 = hold with no deposit or forensic evidence. Hold = "F1 + >=2 families" is really a count of correlated votes.
- Fix (generic): count independent evidence SOURCES, not families. Define groups: {link evidence: F1+F2}, {document forensics: F4}, {money flow: F3 payee}, {deposits: F5}, {terms: F6 as a weak vote}. Hold = link evidence + >=2 other groups, or a single very strong group (e.g. F4 + F5 both extreme). Compute F2 on features excluding the entities that created the F1 link.

### R3 (HIGH) Hold is per deal; a "mule" deal in a held ring stays at watch
- Evidence (e13): R1,R2 (shared kit, bad deposits, equipment loan) => both HOLD at R2's arrival; R3 with the same kit but normal deposits and no vendor stays `watch ['F1']`. `compute_signals` emits F3/F5 as `deals=(folder,)` only, F1 as group.
- Gold expects every ring member held (`eval/gold.json`).
- Fix: evaluate the rule per strong-edge connected component (cluster), count family evidence over the whole cluster, hold every member (sticky), then keep per-deal evidence for the reason string.

### R4 (HIGH) Calibration is wired to sample dates and is unstable on small or zero-inflated samples
- Evidence: `config/fraud.yaml:52-54` literal `train_end: "2026-06-30"`, `test_*`; `calibrate.clean_ids` filters `applied <= train_end` in REAL runs too (design M13 says real runs use all history).
- Proof (e5): shift all history dates +1 year => `n_clean 0, tau {F3: None, F5: None}`; `_fires` returns False for a family with `tau is None`; the sample-like ring drops to `watch [F1]`. A hidden history with a different window (or no row before the cutoff) silently disables F3 and F5, i.e. all holds.
- Proof (e17, 40 random 80% subsamples of history): tau F3 ranges **0.000 to 4.644**, tau F5 4.36 to 4.87, F1 clean fire rate 28% to 43%, F3 clean fire 2% to 11%. `qx4-SUMMARY` reports tau F3 = 0.0 (fires on any lookalike) on the train-only baseline while a real run (full 257-deal baseline) computes 4.43: the scorecard does not describe the shipped configuration. A "95th percentile" of a mostly-zero variable is 0 or a lump.
- Proof (e8): F5 reference is 104 deals => minimum non-zero bits log2(105)=6.71; F5 saturates and cannot rank.
- Fix: no date literals: derive the calibration set from the data (all clean deals, leave-one-out) or split by rank (earliest 64% of rows by date). Use rank p-values with a floor (e.g. fire only if bits >= max(percentile, minimum real signal)); for zero-inflated F3 fire on the categorical condition, not a percentile. Write the computed tau plus n_clean to the run output (M13).

### R5 (HIGH) F1 rarity cliff and history-only rarity
- Cliff (e16): plant k prior ring members in history sharing the ring's preparer+phone. Fires for k<=5; **k>=6 (df/n >= 2%) => F1 does not fire at all** for the two new ring deals. A ring that is already established in history (or a more prolific one) becomes "common". The sample works only because the preparer df is 2 and agent df is 5 (5/257 = 1.95%; the 6th would kill it). Also DocuForge df=4.
- Rarity uses `df/n` over history only (`graph.py`, `rarity.is_strong`). An entity absent from history that appears on many honest CURRENT deals is "strong" as soon as two deals share it (e9): unseen bank ("Chase", "Wells Fargo"), placeholder strings ("N/A", "None", "Self", "Owner", "TBD", "Same as applicant", "000-000-0000"), unseen producer ("Microsoft Word"), all link two unrelated deals. Placeholders already in history ("Self-prepared" df 28, "(owner)" df 61) are fine only because the history happens to contain them.
- Nothing raises the weight of entities whose history deals defaulted or were fraud-confirmed; `outcome_discount` only discounts (omega = 1 - 0.5*(repaid+1)/(df+2); df=0 already gets 0.75). `repaid` counts `current` as repaid, so a young ring that is still performing earns a discount (H-2609-008 is `current`).
- Fix: rarity on pooled history + current batch ((df + current_count)/(n + n_current)); graded strength instead of a 2% cliff; taint propagation (entity used by a charged-off/past-due/fraud_confirmed history deal is strong regardless of df); count only `paid_off` as repaid; generic placeholder suppression (value shared by many unrelated borrowers in the batch, or very short/non-identifying token) rather than a word list.

### R6 (HIGH) F1 is not specific; returning customers always fire it; partner lists contain the decoys
- Evidence (e3): LOO over all 257 history deals: F1 fires on **37%** (vendor 58, guarantor 45, agent 5, remit 4, producer 4, phone 2, preparer 2). F1&F3 fires on 30 deals, **F1&F3&F5 on three: the two ring deals and H-2604-013 (a declined, non-fraud deal)**. Time-forward replay (existing `eval_baseline`) also lists only H-2609-008 as a "false flag" because its label is `current`.
- Returning customers (e15): every one of Garza, Sunrise Rasoi, Okafor, cloned as a new application, links to its own old deal on address+guarantor (F1 5.8 bits). Self-links are not excluded (no EIN/legal-name/guarantor+address identity test).
- Partner lists: for H-2608-002 the F1 partner set is `H-2511-010, H-2601-022, H-2602-005, H-2603-004, H-2604-007, H-2609-008` (e3/e14). H-2511-010, H-2601-022 and H-2604-007 are exactly gold `history_must_not_flag`. Using F1 partners as `linked_deals`/`history_flags` would flag 3 decoys. Gold compares `linked_deals` as an exact set (`score.py:109-110`, extras fail).
- M18 hazard: "a strong type" + "a second strong type" lets preparer and phone count as two links although the phone is the preparer's phone (same fact). Same for agent and agent address.
- F1 `fired` ignores weight: a 0.25-weight bank link fires F1 exactly like a preparer link.
- Fix: F1 fires only if pair score >= a floor expressed in bits (percentile of clean pair scores), or >= 2 independent link kinds; independence table (preparer~phone, agent~agent address, vendor~remit account within one vendor group collapse to one link); self-link exclusion by identity key; `linked_deals` = partners with >=2 independent links (M18), never raw F1 partners.

### R7 (MEDIUM-HIGH) Entity normalization is brittle (evasion by formatting, typos, order)
Test: two unrelated-by-name deals, each carrying a variant of the same rare entity, through `canon_value` + `build_graph` + F1 (e2). LINKED means F1 linked them.

| kind | A | B | result |
|---|---|---|---|
| phone | (469) 555-0111 / 469.555.0111 / +1 / 1-469 / "(cell)" | | linked |
| phone | 469-555-0111 | 469-555-0111 x12 | **miss** (extension digits appended) |
| account | 4471 | ****4471, 44-71 | linked |
| account | 4471 | xxxx4471, Acct #4471, ending in 4471, 0004471, full number vs last 4 | **miss** (only `*` is stripped; letters kept) |
| preparer | K. Zorn | K Zorn | linked |
| preparer | K. Zorn | Zorn, K. / Karl Zorn / K. Zorn, CPA / KARL ZORN vs "Karl Zorn, EA" / Jr. / typo Zorm / "& Associates" | **miss** (name order, initials, credentials, typos) |
| agent | Quux Agent Services | Svcs / +LLC / The ... / ... Inc | **miss** (no abbreviation or suffix handling for agents) |
| address | Ste 100 | Suite 100, Street | linked |
| address | Ste 100 | `#100`, ZIP+4, N/North, Pkwy/Parkway, Ste 200 | **miss** |
| address | 12 Elm St Ste 100 | 100 Elm St Ste 12 | **false MERGE** (address is a sorted token set: number order lost) |
| vendor | Zeta Works LLC | Zeta Works, Inc. / Zeta Wrks | **miss in F1** (full key includes suffix; typo not fuzzy). F3 only compares against history groups, not current deals to each other (qx4 hand-off note 7) |
| producer | FakeForge 3.1 | 3.2 | miss (version bump) |
| guarantor | Maria Q Lopez | Lopez, Maria Q. / Jon vs Jonathan | miss |
| bank | Zed National Bank | Zed Natl Bank | miss |

Not indexed at all (`baseline.HISTORY_COLUMN_KINDS`, contract `EntityKind`): `preparer_firm`, `registered_agent_address`, EIN, guarantor DOB/SSN-last4/DL (T4 "careful" identity reuse is only visible through these), vendor phone/address on the quote, remit-to bank and routing number, borrower contact e-mail/phone, formation file number/organizer. In the sample the ring's letterhead is "Delacroix Bookkeeping Services" and the equipment quote says `Remit to: First Lakes Bank`, which is also the ring's own operating bank: neither is an entity.
- Fix: per-kind canonicalizers: person names (strip credentials CPA/EA/Jr, token-sort, initial matching, Jaro-Winkler/edit<=1 with a blocking key), org names (suffix strip applied to agents and banks too, stopwords "the", Svcs/Services), account (digits only, last 4), phone (strip extension), address (parse number/street/unit/zip5, keep order). Add the unindexed identifiers as entity kinds with their own weights. Add fuzzy matching only as a second tier (weaker edge) so exact matches keep their strength.

### R8 (MEDIUM) F5 vocabulary and power gaps
- Honest false fires (e8): reference is dominated by three labels (Mon-Fri 972, Mon-Sat 528, all days 30). Any other honest weekday label gives 6.71 bits (max) and **fires**: Tue-Sun, Mon-Thu, Mon-Wed, Thu-Sat, Sat,Sun, Mon-Fri,Sun. Tue-Sat, "daily" do not. A restaurant, church or market in the hidden set fires F5. How Read derives the label from transaction dates is undefined (the history column is "days deposits usually land").
- Evasion (e7): at Mon-Fri, round share 0.5 gives 4.1 bits (< tau 5.07); a fraudster who spreads deposits Mon-Fri and keeps round share < ~0.6 never fires F5; only round share >= 0.7 or unusual weekdays fire. Count of deposits per month, amount distribution (Benford), largest deposit, balance dynamics and cross-statement reconciliation are not used.
- Partial months (e6): 1-3 months fire less often (2.3-2.8% vs 5.7%) because of shrinkage: safe for sticky holds, but also less sensitive early.
- Calibration set includes H-2609-008 (a ring deal labeled `current`) as "clean".
- Fix: score the weekday pattern as a distribution over observed deposit dates, not a label; shrink F5 stats toward the pooled reference; add transaction-level features Read already sees (repeating amounts, same-day-of-week clustering, round amounts in dollars); drop contaminated clean-set members (anything linked to a held cluster).

### R9 (MEDIUM) F4 cannot be calibrated from history and the best single-deal tell is unused
- History has only the application-packet producer (`HISTORY_PRODUCER_CLASS = "application"`), so "producer rare for that document class" has no class-level baseline for bank statements.
- In the sample (raw PDF metadata, `strings` scan): all 60 honest bank statements (10 deals) have Producer "FIS Statement Services"; the 3 ring deals' statements are "DocuForge 2.1 (Windows)", the same tool that produced their tax return, EIN letter, financial statements and quote. Honest packets mix origins (bank statement producer differs from the borrower's packet tool); the ring has one producer for every origin. This is a **single-deal** signal that needs no cross-deal link and no history.
- Fix: derive the per-class producer distribution from the CURRENT batch plus history; add "statement producer equals non-bank document producer in the same packet" and "statement producer not a statement system (never seen on statements elsewhere)". Let a strong F4 count for two groups when paired with F5 so a ring of 1-2 with no shared entity can reach hold.

### R10 (MEDIUM) Failure modes in the run loop
- `run.py:150-153`: any exception in the fraud pass is caught once per tick and disables fraud for ALL deals that tick; `NotImplementedError` is swallowed silently. Wrap per cluster/per deal and fall back to "watch only".
- `run.py:149`: `states[name].fraud = outcome.per_deal[name]` overwrites. Stickiness (M17) must therefore live in `decide` (it has `states`), and a watch result must never replace a held block.
- `graph.build_graph` skips deals with `state.error`: a ring deal whose Read crashes is invisible to fraud and frozen.
- F5 relies on a features key no one writes; there is no "F5 unavailable on a deal with 6 statements" warning. Add a self-check that logs when a deal has statements but no deposit features.
- `FraudParams.from_config` raises `ConfigError` at startup (sample dates in config would be a landmine if someone edits them).

### R11 (LOW-MEDIUM) Stage timing and earliness
- Gate is correct: `run.py` takes only `alog.visible_files(now)`; fraud runs after ingest on every arrival tick; `move` runs after fraud, so a hold set at a tick precedes that tick's stage logic. `_exit_stage` refuses to enter/finish the last stage while `held or flagged`; `_src_freeze` freezes at `flagged_at`. A flag arriving after Closed is too late by construction: a late cluster partner whose first member already Closed cannot be un-closed (the engine records `flagged_at` after `Closed`; "held before Closed" is lost). Mitigation: hold on single-deal evidence (R9) and when a deal is one step from the last stage with open F1 watch evidence.
- Earliness on the sample (arrivals): the ring's first deal (Ridgeway, Nov 2 13:51) completes at 14:10. Entities (financial statements, doc 5, 13:58) are visible early, but a hold needs F3 (equipment quote, doc 8, 14:04) and F5 (first statement, doc 9, 14:05). Under the "earlier scores more" rule the earliest possible hold is ~14:05, which the existing signals support (e1: 1 month of deposits is enough). Good, provided Read ingests documents incrementally and re-evaluates per arrival.
- Fraud pass recomputes everything every tick (173 ticks, 13 deals fine); O(deals x ticks x vendor groups) will matter if the hidden set is much larger.

### R12 (LOW) Determinism and generalization audit: clean
- Hash-seed test (e: `PYTHONHASHSEED=0,1,7,12345` over the e10 and e3 scripts): byte-identical output. No `random`, `datetime.now`, `time`, or numpy in `prism/` (grep). Ties are broken lexicographically (`_modal_form`, F3 best selection). When the permutation test (M) is built, seed it from a stable hash of the cluster id, not `hash()`.
- Sample literals: `grep` of `prism/` and `config/` for names, accounts, amounts, vendors, agents, producers finds **none**. Exceptions: `config/fraud.yaml` `train_end/test_start/test_end` (R4), and dataset-shaped defaults: history column names, `HISTORY_PRODUCER_CLASS`, the F3 "equipment vendor" concept (generic to the schema, but the trick it targets is the sample's). `tests/test_engine.py::test_no_sample_literals_in_code` covers `H-####` and folder names only.

---

## 2. A. Evasion matrix (current code vs design)

"Now" = signals as built with an assumed correct Read (nothing runs today, R1). "Design" = MODEL_DESIGN as written (F2/F4 added).

| Trick | Now | Design | Why |
|---|---|---|---|
| Sample ring (shared kit + vendor imitation + Mon/Thu 100% round) | HOLD at first member (~14:05) given Read; first member linked via history ring, agent df 5, producer df 4 | HOLD | e1. Edge-case dependence on df<=5 |
| New ring, no history, vendor lookalike of a frequent vendor, bad deposits | HOLD at 2nd ring deal only if the vendor group can fire (7 of 12 groups) | HOLD | e10, e11 |
| Ring shares kit but non-equipment loan | watch | hold only if F4/F2 fire (F2 correlated, R2) | e10 C |
| Ring shares kit, deposits look normal | watch | watch/hold via F4 only | e10 D |
| Ring of 2 | works if links exist (min_linked 2); 1st deal alone cannot hold | same | e1/e13 |
| Ring sharing no visible entity (statement mill, T3) | watch at best (M2) | same | by design; still catchable by single-deal F4 (R9) |
| Entity variations (typo, name order, `xxxx4471`, ext, `#100`, suffix) | miss (R7 table) | miss | exact canonical keys |
| Staggered arrivals | OK, each arrival rescored; holds only at the later deal | same | e13 |
| Rotating preparers (same firm/phone) | caught via phone if phone shared; firm not indexed; letterhead firm "Delacroix Bookkeeping Services" ignored | | R7 |
| Fraud on a single deal (forged docs, no link) | never held (F1 mandatory) | never held | e10 G; an F4-only path is needed for "held before Closed" |
| Synthetic identity (reused DOB/SSN/DL with respelled name) | miss (unindexed) | T4 low = clear (documented blind spot) | R7 |
| Payment redirection late (corrected quote after approval, new remit account) | F3 only if group can fire; no F1 => watch; no re-evaluation trigger on "corrections" docs except recompute per tick | verification request (M14) if F3 in watch | `extract_entities` recomputed in full each tick; fine if Read re-parses |
| Established ring (>=6 prior history members) | F1 never fires | same | e16 |
| Bust-out / returning borrower | self-link F1, nothing else | blind spot (T5) | e15 |
| Fraud only after Product / just before Closed | hold works if flagged_at < Closed; late partner arrival after Closed cannot hold | same | R11 |

## 3. B. False-positive risks (honest deals)

| Scenario | Now | Evidence |
|---|---|---|
| Returning customer / family of businesses (shared guarantor+address) | F1 always; hold needs F3+F5 as well: low but non-zero (equipment loan ~36% F3 x 5-6% F5) | e15, e3 |
| Recurring local equipment vendor | F1(vendor) 58 deals + F3 36% of equipment loans | e3, e12 |
| Big bank / big accountant / franchise | Safe only if value in history with df>=2%; any bank or firm unseen in history links all honest deals | e9 |
| Round-amount honest cash business | F5 fires at 0.7+ round share (cash business twin T3-B1) | e7 |
| Non-standard deposit weekdays | F5 max for any label outside Mon-Fri/Mon-Sat/all days | e8 |
| Young business / thin history | F6 not built; thresholds instability on small n | e17 |
| Honest deal with F1+F3+F5 in history LOO | H-2604-013 (declined) would be held | e3 |
| Siblings sharing a new bookkeeper (T1-B1) once F2 exists | F1+F2 (+F3 if equipment) => hold without independent evidence | R2 (inferred) |

Small-sample behaviour: n_clean 104; 95th percentile tau varies 4.4-4.9 (F5) and 0-4.6 (F3) over 80% subsamples (e17). Over a ~13-30 deal hidden set, each extra percentage point of per-deal false hold costs roughly 0.13-0.30 expected false flags.

## 4. F. What is stubbed, minimum work to make the hold real (by score impact)

1. `decide()` (R1): per-cluster rule, sticky, build `Fraud(flagged, held, flagged_at=now tick, stage_at_flag=state.stage, reason, linked_deals)`. ~2 h. Prerequisite for any fraud points.
2. Read: `extract_entities` (preparer+firm, phone, agent, address, vendor, remit last4, producer per doc, bank, guarantor, plus DOB/SSN4/DL/EIN) and `features["deposit_months"]` rows with a fixed weekday vocabulary (R8).
3. `linked_deals` / `history_flags` from independent-link pairs only (R6), exact match to gold.
4. OLD_TRICK path (J17): STMT_TAMPER, REV_INFLATION, ID_MISMATCH, DUP_EIN, SHELL_ADDRESS => flagged + `fraud_hold` request; gold has Granite Bay.
5. Fix calibration wiring (R4), F3 threshold (R2), F1 floor and self-link (R6): small, high value for the hidden set.
6. F4 single-deal statement-producer path (R9): the only way to hold a trick with no shared entity.
7. Normalization upgrade and unindexed identifiers (R7).
8. F2 (decorrelated), F6, cluster permutation p-value (seeded, stable), PMI, M13 audit write-out.

## 5. Verified by running vs inferred

Verified by running (scripts in the scratch folder):
- Sample run flags nothing (R1) using `python -m prism run`; `pytest tests/test_fraud_*.py`: 53 passed.
- Calibration values on the full baseline: n_clean 104, tau F3 4.43, F5 5.07, F1 clean fire rate 38%.
- Sample-like ring holds under F1&F3&F5 for first member and second; dropping vendor or using normal deposits does not (e1, e10, e13).
- Entity normalization table (e2), placeholder links (e9), address false merge (e2), returning-customer self-link (e15).
- Date-shifted history disables F3/F5 (e5); subsample tau instability (e17); F3 per-group threshold (e11, e12); F5 label and power curves (e7, e8, e6).
- LOO full-history rates and the only three F1&F3&F5 deals (e3); F1 partner lists contain must-not-flag decoys (e3/e14).
- Rarity cliff at k>=6 prior ring members (e16).
- Determinism across hash seeds; no randomness/time use in `prism/`; no sample literals other than config dates.
- Raw PDF metadata producer scan of the 13 sample deals.

Inferred (not runnable yet):
- Behaviour of F2/F4/F6, cluster hold, M18 history_flags, permutation test, PMI.
- Whether Read's weekday labels, last-4 handling and per-document producers will match the baseline vocabulary.
- Stage timing past the first hold in a real end-to-end run (Read does not exist yet), and effect on `stage_at_flag`.
- Interaction of F2 with F1 (R2) and the expected hidden-set false-hold rate with all families present.
