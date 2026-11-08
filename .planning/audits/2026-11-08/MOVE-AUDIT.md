# MOVE engine audit (Prism, HackUTD 2026 Goldman DealPilot)

Scope: `prism/move/*`, `config/move.yaml`, `prism/engine/run.py`, `prism/contract.py`, against `data/participant/rules/stages.json`, `contacts/teams.json`, `sim/assignments.json`, `docs/DETAILS_CHECKLIST.md` (J1-J22), `docs/CREDIT_MEMO_TEMPLATE.md`, `docs/MESSAGE_TEMPLATES.md`, `eval/gold.json`. Read-only on the repo. All scripts and outputs are in this scratch folder (`harness.py`, `exp1..exp7.py`, `sim_*.json`).

## Test and run results

- `.venv/bin/python -m pytest -q`: **354 passed**, 1 warning (starlette/httpx deprecation). Nothing skipped.
- `python -m prism run` on the real sample (all four personas, no Read): 13 deals, 173 files, 0 errors, valid. Self-score is 12/117 because `prism/read/*` (18-25 line stubs) and `prism/fraud/decide.py` (46 lines) are still stubs in this tree. Every deal stops at Intake waiting for `legal_name`.
- To exercise real Move on real rules I wrote `harness.py`. It monkeypatches Read to return `eval/gold.json` facts and issues, and fraud to return gold flags, then runs the real `run_sim` on the real folder, arrivals and rules.
  - Fast persona: route **52/52**, stage **13/13**, flag/held 13/13, output validates. Move's own logic reproduces the gold routing: Dana's backup marcus.lee for Priya's, priscilla.nguyen under $250k, harold.benson for Harbor Tea and Okafor, and the right RM, closer and fraud analyst.
  - Slow, ooo and never personas: 9/13 stages, all valid. That is expected, because those deals wait on humans.
  - Two runs of the same input are byte-identical (determinism OK).
  - Caveat: this oracle is circular for Read and fraud, so it proves Move logic only, not the end-to-end pipeline.

---

## Findings, ranked by score impact

### F1. HIGH: Move fails open or silent whenever Read/Fraud do not supply the exact keys it expects

Move's exit conditions are mostly delegated to Read's `issues` and to undocumented `features["profile"]` keys. Several gaps were **verified by running** (exp5, exp7):

| Rule in stages.json | What Move does | Gap |
|---|---|---|
| Product: "vendor identity and remit account verified against known vendors" | Blocks only if `profile["vendor_verified"] is False` (`stage.py:185-191`) | **`None` or missing passes.** Equipment loan went Product to Closed with `vendor_verified` unset (E19). A Read miss means an unverified vendor is funded. Should fail closed: require `True` for products in `vendor_check_products`. |
| Closed: "disbursement account verified (borrower's own account or verified vendor)" | **No gate at all.** `messages.pay_to_text` (`messages.py:308-320`) prints "verified vendor ..." for any `kind == "vendor"` | Nothing enforced. The funding message claims verification. |
| Closed: "final fraud screen clear" | `_exit_stage` refuses entry and exit if `fraud.held`, `fraud.flagged` or any open issue (`stage.py:267-269`) | Good. But `funding_release_message` prints "Final fraud screen: clear as of ..." unconditionally. |
| Credit: "known-fraud checks run" | Only blocks if an `OLD_TRICK:*` issue exists (`config/move.yaml:26,30,32,35`) | No attestation that the checks ran. `credit_decision_message` states "the bank's 5 known-fraud checks pass" unconditionally. |
| Credit: "tax return OR Form 7004 if < 2 years old" | Entirely Read's job (Move never checks business age) | Move relies on `MISSING_DOC:tax_return` being right. |
| J17: OLD_TRICK means flagged plus `fraud_hold` request | Move only freezes when `fraud.flagged/held` is set (`stage.py:359-365`) | **Verified (E18):** a deal with `OLD_TRICK:STMT_TAMPER` and a silent fraud module sits at Intake forever. It sends no `fraud_hold` request to Fraud Ops and only produces ordinary "stuck" ladder alerts to the intake specialist. Because `decide.py` is a stub, this is the live state of the tree. Granite Bay (the standalone-trick deal) depends on it. |
| Deal missing from `assignments.json` | `_send_gate` silently returns False (`stage.py:130-133`, `routing.py:122-153`) | **Verified (E12):** a deal not in assignments reaches Credit and then gets no `credit_decision` and no 100% alert (owner and RM are both None). It gets only 150% and 200% escalations to lauren.kim. The weekend drop or hidden set may bring new deals, so a fallback is needed (default officer by round-robin over the Credit team, or lauren.kim). |

Recommended fix, in order:
1. Fail closed on `vendor_verified`.
2. Add a Move-side fallback for J17: an `OLD_TRICK:*` issue with no fraud flag synthesizes the freeze and `fraud_hold` request (deterministic, a few lines in `_src_freeze`).
3. Add an unassigned-deal fallback.
4. Gate Closed on `disbursement` being present and verified.
5. Drop the unconditional "checks pass" phrases or tie them to a real signal.

### F2. MEDIUM-HIGH: Deadline logic (MOVE-06) has unit and sign errors; the alert fires at deal entry with impossible targets

Verified with exp4 and the Priya's Bakery message in the sim output.

- **Unit error.** `history/stage_events.csv` `hours_in_stage` is elapsed wall-clock time (for example 09:00 to 21:12 is 12.2h). `deadline.py:64-67` treats it as business hours for gated stages (`business_add(cur, hours*60)`), so nights and weekends are counted twice. For Priya's (entered Tue 08:46, needed by Fri 15:00) the code projects **Fri 11/13 09:28**. The plain sum of the wall medians (80.7h) gives Fri 11/06 17:28.
- **Impossible dates.** `latest_exit` for Intake is **Wed 10/28** (6 days before the deal arrived). The alert says "Jordan Webb needs to finish Intake by Wed 10/28 12:09 PM CT". The committee request says "Please approve or decline by Tue 11/03 4:09 AM CT", which is **before the request was sent (Tue 09:50)** and at night. This is §9 item 23, still open, and worse than described: the target can be in the past. When `latest_exit < now` the message should say "cannot be met at typical speed; expedite".
- **False positive at entry.** The sum of the history medians exceeds roughly 3 business days. Any deal with `needed_by` within about a week alerts at Intake entry, even when a fast approver closes it in 2 hours (Priya's fast run funds Tue 10:35 yet carries the "Deadline at risk" alert). Whether extra alerts cost points is unknown (Jesse's ask to Vijay).
- **No acceleration for at-risk deals.** The J21 reminder and backup copy only fire at 100% of the stage SLA (`stage.py:_h_ladder`, `idx == 0` only). For a deadline deal that is already late at 48h of Credit, the reminder arrives far too late. Under the slow persona Priya's misses Fri 15:00 (Committee still open at 11/06 09:35) and nothing nudged earlier.
- **Prioritisation is a no-op.** `deadline.priority_key` and `needed_by_badge` are not called by `run.py` or the stage machine. Deals are processed in name order, and the "worked first" and "sign-off early in business hours" checklist items (DETAILS_CHECKLIST §5) are not implemented. `answer_by` is only text.

Fix:
1. Use wall-clock medians directly (or convert the history to business hours before use).
2. Clamp `latest_exit` and `answer_by` to a business-hours moment `>= now` and snap with `_prev_close` (§9-23).
3. Make the risk test compare against remaining time rather than firing at entry (for example, fire only if projected finish exceeds `needed_by` by more than the stage SLA slack).
4. Add a deadline-aware reminder time: `min(100% SLA, latest_exit(stage))`.

### F3. MEDIUM: A funded or terminal deal that is flagged later (the weekend drop, J19) produces no Move output

Verified (E15). After `rt.terminal`, `_candidates` returns `[]` (`stage.py:~320`). A Closed deal flagged by a Collections notice gets no `fraud_hold` request to victor.hale, no log note and no alert, although MOVE-09 says new papers are "re-checked". The checklist says Fraud Ops is asked (J17). Either emit the `fraud_hold` request and a log annotation for terminal deals (without changing stage), or accept that the fraud section alone carries it.

### F4. MEDIUM: Hold and decline representation in the stage log (known UI issue; your point 6)

Verified (E6, E7, E11, and `Pecan Grove Catering` in `sim_fast.json`).

- `_h_freeze` (`stage.py:475-483`) sets `decision="held"` on the open entry and **appends** prose to `why`. `_maybe_unfreeze` (`stage.py:595-609`) clears the decision and appends again. `_apply_answer` for the fraud gate also appends (`stage.py:408-411`). The result is one open entry with `exited_at=None` and a growing narrative: "Entered Intake: first document arrived Tue 11/03 11:11 AM CT Frozen Tue 11/03 11:30 AM CT: ... Victor Hale answered place hold on ...". Note the missing period after "CT".
- `_stop_deal` (`stage.py:414-424`) for decline or stop also leaves `exited_at=None`, with `decision="decline"` (the history vocabulary is "declined"). The UI therefore sees a declined deal as the current stage forever.
- The SLA percentage is not recorded anywhere in the log; `sla_pct` is computed live and only for the current stage.

Recommended contract-level fix (`StageLogEntry`, `prism/contract.py:~111`). Extras are allowed by the organizers' format; our own `ContractModel` is `extra="forbid"`, so add them as optional fields and regenerate fixtures:
- `outcome: Optional[Literal["advanced","held","declined","stopped","closed"]]`. Keeps `decision` free text for the grader. Use history vocabulary in `decision`: `declined`, `fraud hold` (history has "fraud hold -> confirmed").
- `sla_hours: Optional[float]`, which also fixes the delegated 24 vs 48 ambiguity (the UI cannot derive it from the stage name; the CR-01 fix in the UI measures against "that stage's own limit" and cannot know the delegated limit).
- `held_at: Optional[SimTime]` and `resumed_at: Optional[SimTime]`, or a list of `{from, to}` holds, so frozen time is explicit.
- Keep `why` immutable after entry. Put the hold narrative in `decision` text plus a separate `notes: list[str]`, not string concatenation.
- Set `exited_at` on decline and stop (the deal left the pipeline there). Leave it null only while held (still in the stage).

### F5. MEDIUM: Out-of-office handled at request time only; alerts and pending requests go to an officer who has since gone out

Verified (E3, E4). A deal entering Credit Mon 11/02 16:30 gets its `credit_decision` sent to dana.whitfield (in office), who is out from Tue 08:00. `rt.owner` is frozen at stage entry (`stage.py:95`).
- The 100% alert goes to dana (OOO) and brian/elena, not to marcus.lee, who covers her.
- The backup copy only arrives at 100% (48h).
- The slow persona makes dana "answer" while OOO.

Fix: re-resolve `rt.owner` and the request target at alert time (`routing.available`), and re-route a pending request when the primary's OOO window starts (or at the first business open after it). OOO start and end are inclusive (`routing.py:77-81`); at exactly Fri 11/06 18:00 she is still out, and 18:01 is back (verified, E2). That matches "through Fri 18:00".

### F6. MEDIUM-LOW: Human reply semantics (J20 is unknown)

Verified (E9, E10, E11).
- A `release_hold` reply from Fraud Ops is **recorded but ignored**; the deal stays frozen (`stage.py:437-443`). Rulebook: "a human places or releases it". The `fraud_release` request type exists in the contract but Move never emits it.
- `commitment_signoff: not_yet` and `funding_release: hold` leave the deal waiting forever with no re-ask. The request is answered, so no later `confirm` is accepted (`record_reply` rejects non-pending), and nothing is re-sent (`stage.py:_apply_answer` final `else`). A funding `hold` still produces the 100/150/200% alerts, which is fine.
- The option vocabulary for four of five gates is invented. The rulebook gives options only for `credit_decision`; the others are our choices. Document this.
- After `request_info`, the reminder group key repeats (`"Credit:credit_decision"`), so the second round never gets a J21 backup copy (`inbox.py:139`).

Fix: on `release_hold`, set `fraud.held=False` and resume while keeping `flagged`; on `not_yet` or `hold`, re-ask after a delay or on a new answer.

### F7. LOW-MEDIUM: Late-arriving issues do not block mid-pipeline stages; memo is never refreshed

Verified (E17). Blocking patterns (`config/move.yaml:22-39`):
- Committee blocks only `OLD_TRICK`.
- Product blocks only a missing equipment quote and `OLD_TRICK`.
- Credit does not block a new `MISMATCH:ein/legal_name/amount_requested/guarantor_name`.

A `MISMATCH:annual_revenue` raised while the committee request is outstanding does not stop the committee exit (approved, moved to Committed, and only blocked there by `.+`). The memo is built once (`stage.py:_on_enter`, `credit_memo is None` guard) and is stale after weekend-drop papers. For MOVE-09, use `'.+'` for Committee and Product, and rebuild the memo (and re-ask) if a blocking issue appears after the memo was written.

### F8. LOW: The §9 items (HANDOFF.md)

| # | Status | Evidence |
|---|---|---|
| 21 memo anniversary | **NOT fixed** | `credit_memo.py:229` still `days / 36525*100`. Verified: formed 2021-11-02, applied 2026-11-02 gives 1826 days = 4.9993 yrs, so 1 point (spec 0), displayed "4 years" (`:253,:335,:410,:421`). 2024-11-02 to 2026-11-02 gives 1.9986, so 2 points (spec 1). Fix with calendar-year comparison. Make Read's "under 2 years old" (7004) test use the same function. |
| 22 watch override dormant | **NOT fixed** | `fraud_watch` is read at `credit_memo.py:264` and set only in `tests/test_move_memo.py:112`; `prism/fraud/decide.py` is a stub. |
| 23 night-time `answer_by` | **NOT fixed, worse** | See F2: `latest_exit` also returns dates before the deal exists. |

Also: `DealDetail` still has no `credit_memo` field (`grep credit_memo prism/contract.py` is empty), so the "full memo on the deal page" (MOVE-10) cannot be served.

### F9. LOW: SLA ladder (verified correct, with edge notes)

Verified against the real stages.json and teams.json (sim_*.json, exp2, exp3):
- Crossing times exact: Intake 8/12/16h, Credit 48/72/96 (LSFD entered Tue 14:05, alert Thu 14:05), delegated Committee 24/36/48, chair 48/72/96. Crossing time is rounded half-up to whole minutes (`sla.py:crossing_time`).
- Recipients: owner plus RM at 100% (deduped when the owner is the RM); `escalates_to` of the owner at 150% (marcus to susan.ortiz); lauren.kim at 200% (always sent, J4; Product/Committed/Closed show two lauren entries).
- A single large clock jump equals incremental ticks (E5, identical JSON for never/slow/fast).
- Alerts stop on decline, close and freeze (`sla.py:129`, `_src_ladder`, `_candidates`). The frozen interval is excluded and later crossings shift (`frozen_total`; sla_pct 3.5/48 at the freeze verified).
- Each alert is emitted exactly once (the `emitted` key is `stage:pct`).
- Content has all four elements (whose deal plus RM, stage and duration, waiting on, what unblocks).
- Edge: the ladder event (priority 2) sorts before an answer at the same instant (priority 4). An approval at exactly the 100% minute yields an alert for a deal that just left the stage (E14, alert at 09:30 and exit at 09:30). Swap priorities (answer before ladder) at equal times.
- Held deals: the ladder is silent and the clock frozen. Defensible ("simply stops"), but a deal held for days produces only the J22 chase (+2h to the backup, +6h an escalation to lauren.kim). Confirm intent.

### F10. LOW: Time edge cases

- **DST:** `SIM_TZ` is a fixed -06:00 (`visibility.py:16`). US DST ended Sun 2026-11-01, so the sample week and the Nov 7-8 drop are CST and correct. A hidden set that spans a DST change would be off by an hour, but the format mandates `-06:00`. No action.
- **Nights and weekends:** SLA timers are wall-clock (correct). Personas answer only Mon-Fri 08:00-18:00 and `next_open`/`business_add`/`business_sub` are correct. There are no holidays; `config/move.yaml` hours are not read from `teams.json`'s `hours` string.
- **Quiet window:** inclusive (a second file at exactly +30 min extends the quiet by 30; evaluation fires at last arrival + 30 exactly; E13 verified).
- **Simultaneous arrivals:** the intake round-robin is by first-seen order and ties within a tick break by folder name (`run.py` sorted order), not by arrival order within the minute. Rare; J2 says arrival order. I verified the owner sequence alternates olivia, jordan in arrival order on the sample.
- **Retroactive checks:** `_exit_stage` consults the current `fraud.flagged` while replaying earlier events (`stage.py:263-269`), so an exit that was legal at T1 can be refused retroactively. This only errs toward holding, so it is safe.
- **Request ordering:** `_drain` orders by (time, priority, seq), deterministic.

### F11. LOW: Hardcoded or sample-coupled items (generalization)

No person ids, folder names or sample dates in `prism/move/*.py`. The qx3 literal scan holds. Remaining coupling:
- OOO parsing depends on one notes format, `OUT OF OFFICE <date> [time] through <date> [time]` (`routing.py:19-22`). A differently worded note in the hidden pack silently disables backup routing.
- `config/move.yaml` hard-codes the doc-name regexes (these equal the contract enum, which is fine), the products for the vendor check, 08:00-18:00, the 9.0% rate, the persona times, quiet 30 min and chase 2h/4h (J-calls, documented).
- The contract literals `"Product"`, `"Revolving Line of Credit"`, `H-` prefix and the five OLD_TRICK codes in message wording are acceptable.
- `credit_memo.py` conditions text and band tables are from the template, in config.

### F12. INFO: Stage order and gates (verified OK)

- Order is enforced by the pipeline list in stages.json (`stage.py:_next_stage`); no stage is skipped, and a "Product" stage of 0 minutes is logged with "standard pricing for <product>" (J9).
- Committee boundary: 249,999.99 gives priscilla.nguyen and 24h; 250,000, 250,000.0, "$250,000.00" and 250,000.01 give harold.benson and 48h; the string "249,999.99" gives priscilla. 249,999.995 rounds half-up to 250,000.00 and goes to the chair, which is acceptable (E1). Integer cents, not floats.
- Credit gate: the assigned officer; Dana's OOO window gives marcus.lee at 11/03 08:00 through 11/06 18:00 inclusive; if marcus is out too the chain continues (`routing.available`). RM, closer and fraud analyst plus backup resolve from data.
- Credit decision options are exactly `approve | decline | request_info` (`config/move.yaml:50-54`). `decline` ends the deal ("declined"); `request_info` sends a borrower `info_request` and re-asks after a later arrival (E8); `approve` advances. No credit_decision on an incomplete file (verified: LSFD, Oakline, tyler stop at Credit with only `info_request`).
- Nothing advances while waiting: no `credit_decision` until the gate, no exit before the answer, no Closed entry while held, flagged or any issue open (`stage.py:267-269`).
- Borrower `info_request`: mismatches go immediately, missing items after the 30 min quiet; for Bluebonnet this produces two separate info_requests (09:50 and 10:20) rather than one. J11 says "all at once" for the missing items only, so this is acceptable but could be merged.

---

## Verified by running vs inferred

Verified by running: the test suite (354 pass); the real-data CLI run on all four personas; the gold-oracle sim (route 52/52, stage 13/13, valid, deterministic); amount boundaries; OOO boundaries; the alert ladder times and recipients; jump-vs-incremental equivalence; hold, resume and SLA freeze; decline; `request_info`; `not_yet`; funding `hold`; `release_hold` being ignored; the unassigned-deal stall; the OLD_TRICK-with-silent-fraud stall; `vendor_verified=None` passing; the funded-deal-flagged silence; the late MISMATCH at Committee; the deadline projection and impossible dates; the anniversary arithmetic; quiet-window and exact-crossing edge cases.

Inferred from the code only: the hidden-set OOO note format risk; the holiday gap; the intake round-robin tie order by folder name; the `reminded` group reuse after `request_info`; the retroactive-fraud check; whether graders penalise extra deadline-risk alerts or ladder silence on held deals.

## Suggested order of fixes (time-boxed)

1. F1 (fail-closed vendor, OLD_TRICK fallback hold, unassigned-deal fallback). About 30 minutes.
2. F4 (stage-log contract fields and cleaner hold/decline entries). Touches the UI.
3. F2 (deadline units, sign, night snap, reminder timing).
4. F5 (re-resolve OOO owner at alert time).
5. F8 anniversary, F3, F6, F7 as time allows.
