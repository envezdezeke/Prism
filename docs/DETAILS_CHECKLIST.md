# Details Checklist (every rule that earns or loses points)

> Owner: Jesse (finance). Built 2026-11-07 from the bank's rulebook: challenge statement, `README.md`, `SUBMISSION_FORMAT.md`, `SCHEMA.md`, `rules/stages.json`, `rules/known_fraud_checks.md`, `contacts/teams.json`, `sim/assignments.json`.
> **How to use it:** each line is a pass/fail test, like a controls audit. Zeke builds to it, the answer sheet (`eval/gold.json`) is scored against it, and nothing ships on "it probably works."
> Source tags: **[S]** stages.json · **[T]** teams.json · **[F]** SUBMISSION_FORMAT · **[K]** known_fraud_checks · **[R]** README / challenge statement · **[SC]** SCHEMA.
> Items marked **→ J#** depend on a judgment call in the last section.

## 0. Ground rules (apply to everything)

- [ ] The app only sees a document after its arrival time. No decision may cite a document that hadn't arrived yet. [R][SC]
- [ ] Every time is Chicago sim time, written with `-06:00`. Never the computer's own clock. [SC]
- [ ] Documents are identified by **what they say**, never by file name ("SCAN_2026…pdf" can be the application). [R]
- [ ] One unreadable or strange document never stops the run. The output file is **always** written. [F]
- [ ] Runs on a new folder (weekend drop, hidden set) with no changes by us. [R]
- [ ] Nothing about the sample's specific companies, people or tricks is written into the rules. [R]

## 1. READ: the facts

For every deal, these 9 fields. Anything we can't determine = `null`, never a guess. [F]

| Field | Rule |
|---|---|
| legal_name | The legal name (not the DBA / trade name) |
| ein | Format `12-3456789` |
| amount_requested | A number in dollars, not text |
| purpose_category | One of: working_capital, equipment, inventory, payroll, expansion, refinance |
| product | As **requested by the borrower**, one of: Term Loan, Equipment Loan, Revolving Line of Credit, Working Capital Loan |
| term_months | A number |
| guarantor_name | The guarantor on the application → J6 for nicknames |
| annual_revenue_stated | What the borrower **stated**, not what we calculated → J7 for ranges |
| needed_by | A full date and time with `-06:00`, or `null`. Never the words "No specific date" → J8 |

## 2. READ: missing, mismatched and tampered

**Allowed issue labels only** [F]:
- `MISSING_DOC:<doc>` / `MISSING_PAGE:<doc>`, where doc is one of: application, guarantor_id, certificate_of_formation, ein_letter, bank_statement_YYYY-MM, financial_statements, tax_return, equipment_quote
- `MISMATCH:<field>`, where field is one of: legal_name, ein, amount_requested, guarantor_name, guarantor_dob, guarantor_address, annual_revenue, bank_balance
- `OLD_TRICK:<code>`, where code is one of the 5 below

**Missing documents**
- [ ] Intake needs: signed application, a photo ID for **each** guarantor, certificate of formation, IRS EIN letter. [S]
- [ ] Credit needs: bank statements for the **6 most recent full months**, all pages (→ J12); P&L **and** balance sheet; the most recent business tax return, **or** a Form 7004 extension **only if the business is under 2 years old**. [S]
- [ ] Equipment loans need a vendor quote. [S] (When to report it → J11)
- [ ] A missing statement month is named by month: `MISSING_DOC:bank_statement_2026-06`. [F]
- [ ] A document still arriving is not "missing". Wait for the folder to go quiet first. → J11

**Missing pages**
- [ ] Judged from the "Page X of N" markers printed on the statement, not from how many pages the file has. [SC]
- [ ] A missing page is `MISSING_PAGE`, **not** tampering. [K]

**Mismatches** (every mismatch must be real) → J13
- [ ] Bob = Robert is **not** a mismatch. Neither are LLC vs. L.L.C., upper vs. lower case, or Ave vs. Avenue. [K]
- [ ] Different EIN digits **are** a mismatch.
- [ ] Revenue is compared on the same basis (same year, same source type).

**The 5 old tricks, exactly as the bank defines them** [K]
- [ ] **STMT_TAMPER:** each month's opening balance equals the prior month's closing balance, and listed transactions add up to the summary totals.
- [ ] **REV_INFLATION:** stated annual revenue (application or tax return) is **more than 1.5x** the annualized deposits in the bank statements.
- [ ] **ID_MISMATCH:** name, date of birth or address on the photo ID disagrees with the application, beyond common nicknames.
- [ ] **DUP_EIN:** the EIN was already used by a **different** legal name in history.
- [ ] **SHELL_ADDRESS:** the business address is a mailbox store / PMB.
- [ ] A deal that trips any of these goes **straight to Fraud Operations**. [K] → J17

## 3. MOVE: the stages

Order is fixed: Intake → Credit → Committee → Product → Committed → Closed. **Entering Closed = money goes out.** [S]

| Stage | Time limit | Must have to move on | Who signs | Request type |
|---|---|---|---|---|
| Intake | 8h | The 4 intake docs; facts extracted; application matches supporting docs (name, EIN, amount, guarantor) | Nobody | — |
| Credit | 48h | 6 full months of statements (all pages), P&L + balance sheet, tax return or 7004 (if under 2 yrs), 5 old-trick checks run | Assigned credit officer; **backup if out of office** | `credit_decision` (approve / decline / request_info) |
| Committee | 24h if delegated, 48h if chair | Credit memo (what was seen, decided and why) | Under $250,000 → priscilla.nguyen. $250,000 and up → harold.benson | `committee_approval` |
| Product | 16h | Product and pricing chosen, matching the request (→ J9); equipment loans: quote present, **vendor and the account the money goes to verified against known vendors** | Nobody | — |
| Committed | 48h | Commitment letter signed by the RM **and** the borrower (→ J10) | The deal's relationship manager | `commitment_signoff` |
| Closed | 24h | Final fraud screen clear; money goes only to the borrower's own account or a verified vendor (→ J5) | tasha.reed | `funding_release` |

- [ ] Every stage writes a log line: entered at, exited at, decision, and **why**. [F][R]
- [ ] Never move forward while waiting on a document, a person's answer or a fraud hold. [R]
- [ ] Missing items → `info_request` to `"borrower"` right away. [F]
- [ ] No `credit_decision` request on an incomplete file.
- [ ] A held, declined or withdrawn deal simply stops, and the log says why. [F]
- [ ] Every request is written in plain words and states the decision being asked for. [R]
- [ ] The $250,000 line: **$249,999.99 → priscilla.nguyen; $250,000.00 → harold.benson.** [S][T]
- [ ] Out of office: **dana.whitfield is out Tue 11/03 08:00 – Fri 11/06 18:00** → her deals go to marcus.lee. She is **in** on Monday 11/02. [T]
- [ ] Intake specialist is assigned round-robin (olivia.chen / jordan.webb). [T] → J2

## 4. MOVE: stuck deals (the alert ladder)

The timer starts when the deal **enters** the stage. [S] (When a deal "enters" Intake → J1)
At 100% of the limit: alert the stage owner **and the deal's RM**. At 150%: escalate to the owner's manager. At 200%: second escalation to lauren.kim. [S] → J3, J4

| Stage | Owner (100%) | 150% goes to | 200% goes to | Fires at (hours in stage) |
|---|---|---|---|---|
| Intake | olivia.chen or jordan.webb | raj.patel | lauren.kim | 8 / 12 / 16 |
| Credit | assigned credit officer (or backup) | susan.ortiz | lauren.kim | 48 / 72 / 96 |
| Committee, delegated | priscilla.nguyen | susan.ortiz | lauren.kim | 24 / 36 / 48 |
| Committee, chair | harold.benson | susan.ortiz | lauren.kim | 48 / 72 / 96 |
| Product | kevin.alvarez | lauren.kim | lauren.kim → J4 | 16 / 24 / 32 |
| Committed | deal's RM | lauren.kim | lauren.kim → J4 | 48 / 72 / 96 |
| Closed | tasha.reed | lauren.kim | lauren.kim → J4 | 24 / 36 / 48 |

- [ ] Every alert says **all four**: whose deal (borrower + RM), which stage and for how long, what it's waiting for, what would unblock it. [S]
- [ ] If the clock jumps 6+ hours at once, **every** threshold crossed is still sent, each with its correct time.
- [ ] Each alert fires **once**, never duplicated.
- [ ] Unanswered requests: follow up, reroute to the backup, then escalate. Never wait forever. [R]
- [ ] Staff work Mon–Fri 08:00–18:00, but alerts can go out any time and timers run around the clock. [T] → J16

## 5. MOVE: deadlines

- [ ] "A good deal that misses its date is a failure too." [S]
- [ ] Deals with a needed-by date get worked first.
- [ ] Sign-off requests for deadline deals go out early in business hours.
- [ ] A deadline-risk alert fires before the date would be missed. → J18

## 6. FRAUD

- [ ] A suspicious deal is held **before it enters Closed**. Earlier earns more. A hold can happen at any stage. [S][R]
- [ ] The pattern is caught in the **first few deals**, not the last. [R]
- [ ] **No good deal blocked.** "Each false flag costs a lot." A strange deal is not a fake deal. [R]
- [ ] We **request** the hold, with evidence, from victor.hale (backup monica.salas). A person places or releases it. [S] → J5
- [ ] A flagged deal is frozen immediately and never enters Closed.
- [ ] One odd sign alone never triggers a hold. Several independent signs must agree.
- [ ] Output for each flagged deal: flagged, flagged_at, stage_at_flag, held, a plain-words reason, linked_deals. [F]
- [ ] flagged_at is never earlier than the arrival of the evidence it cites.
- [ ] "Find the rest": `linked_deals` lists related current deals (by folder name) and past deals (`H-…`). Top-level `history_flags` lists past deals in the same scheme. [F]
- [ ] Returning customers with a clean record are not added to history_flags just for being in history.
- [ ] Weekend drop: new papers re-check **every** deal, funded ones included. A Collections notice on a funded deal → trace its links. [R] → J19
- [ ] Soft concern (one sign) → verification step / `info_request`, with `flagged` staying false. Only multi-sign evidence → `fraud_hold`.

## 7. The output file

- [ ] One file per run. Deal keys are the **exact folder names**, including apostrophes, ampersands and spaces (e.g. `Priya's Bakery`, `Westfield Print & Sign`). [F]
- [ ] Top level has `team`, `set` (sample / drop / hidden), `deals` and `history_flags`. [F]
- [ ] Every deal has extracted, issues, stage_log, human_requests, alerts and fraud, even clean ones (`fraud.flagged: false`).
- [ ] Only the allowed values in every list (stages, purposes, products, request types, alert levels, issue labels). [F]
- [ ] Extra fields are allowed and ignored, so we can add evidence for the demo. [F]

## 8. Judgment calls (Jesse decides; Zeke builds to the answer)

Each has a recommended default so nobody guesses at 2am. Status: **open** until Jesse confirms.

| # | Question | Recommended default | Status |
|---|---|---|---|
| J1 | When does a deal "enter" Intake and start its 8h clock? | When the deal's first document arrives | open |
| J2 | Intake round-robin order? | Alternate by deal arrival order, olivia.chen first | open |
| J3 | Owner + RM at 100%: one alert or two? | Two alert entries, one to each | open |
| J4 | When the owner's manager is already lauren.kim (Product, Committed, Closed), what happens at 200%? | Still send the 200% second escalation to lauren.kim, labelled as the second escalation | open |
| J5 | Fraud Ops never answers our hold request: is the deal "held"? | Yes. We freeze it ourselves and money never goes out; `held: true`, and the log says we're awaiting Fraud Ops | open |
| J6 | Guarantor name: the application's version or the ID's? | The application's; ID differences beyond nicknames → ID_MISMATCH | open |
| J7 | Revenue stated as a range ("approx 400–500k")? | Midpoint, marked low confidence, with the original text kept as evidence | open |
| J8 | "No specific date" → ? | `null` | open |
| J9 | Product stage needs "pricing chosen", but we don't price loans | Log "standard pricing for <product>" as the decision; no pricing engine | open |
| J10 | The commitment letter needs the borrower's signature too | Send `commitment_signoff` to the RM plus an `info_request` to the borrower for the signed letter | open |
| J11 | When is a document reported missing? | After the folder has been quiet for 30 sim-minutes. The equipment quote is reported at Intake but only blocks at Product | open |
| J12 | "6 most recent full months" counted from when? | The 6 full calendar months before the application date | open |
| J13 | Mismatch tolerances | Names: ignore nicknames, suffixes, case and punctuation. Addresses: ignore Ave/Avenue, Ste/#. EIN: digits must match exactly. Amounts: exact to the cent. Bank balance: within $1 | open |
| J14 | `issues`: open at the end of the run, or everything ever raised? | Open at the end in `issues`, resolved ones in an extra `resolved_issues` field. **Ask organizers** | open |
| J15 | Application and request letter disagree on amount: which routes Committee? | Neither. Raise the mismatch, ask the borrower, route once resolved | open |
| J16 | Request goes out after 18:00 or on a weekend | Send anyway, expect the answer next business morning; the timer keeps running | open |
| J17 | Old-trick hit: flagged + hold request, or just a Fraud Ops notice? | `flagged: true` plus a `fraud_hold` request to Fraud Ops | open |
| J18 | When does a deadline-risk alert fire? | As soon as the remaining stages can't fit before needed_by at normal speed | open |
| J19 | A Collections notice on a funded deal | Re-check its links; add matching past deals to history_flags only if they share the scheme's multiple signs | open |
| J20 | Who answers human requests during judging (our screen, files, or their system)? | Unknown. Support both our inbox and scripted answers. **Ask organizers** | open |
