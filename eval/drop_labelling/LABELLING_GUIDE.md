# Labelling the weekend drop, blind (45 minutes)

Every example below is made up (X- ids, 555-01xx phones). Rules come from `docs/DETAILS_CHECKLIST.md` (J1-J22), `data/participant/rules/stages.json` and `known_fraud_checks.md`.

## Before you start (3 min)

1. Confirm the seal commit exists (`git log --oneline -1 -- eval/blind_drop_record.json`). Do not label before it, and do not open `out/blind_drop/`.
2. `cp eval/drop_labelling/gold_drop.TEMPLATE.json eval/gold_drop.json`, delete the `X-Example Deal` entry.
3. One entry per new deal, plus any old deal that got new papers. Key = the exact folder name (apostrophes, ampersands, spaces). Documents are identified by what they say, not by file name.

## Time budget

| Block | Minutes |
|---|---|
| Setup | 3 |
| Per-deal pass, steps 1-8 (total across all deals, so about 30 / number of deals each) | 30 |
| Step 9: history flags | 7 |
| Step 10: run the checker, fix, commit | 5 |

Per deal, steps 1-3 get roughly 40% of the time, step 4 10%, step 5 25%, steps 6-8 25%. If you are behind, mark the deal `"status": "draft"`, keep moving, and come back. Skip, never guess: unknown fact = `null`.

## Per deal, in this order

**1. Identity facts (extracted, 9 fields).** Read the application. Write: `legal_name` (legal, not the DBA), `ein` as `12-3456789`, `amount_requested` as a plain number (`120000`), `purpose_category`, `product` (what the borrower asked for), `term_months`, `guarantor_name` (the application's version, J6), `annual_revenue_stated` (what they stated; a range is the midpoint, J7), `needed_by` (`2026-11-06T15:00-06:00` or `null`; "No specific date" is `null`, J8). If two answers are fair, put the alternative in `extracted_accept`.
- `purpose_category`: working_capital, equipment, inventory, payroll, expansion, refinance
- `product`: Term Loan, Equipment Loan, Revolving Line of Credit, Working Capital Loan

**2. Required documents (stages.json).** Missing means missing after the folder goes quiet (J11). Report everything missing at once, including later-stage papers.
- Intake: signed application; photo ID for each guarantor; certificate of formation; IRS EIN letter.
- Credit: bank statements for the 6 full calendar months before the application date (J12), every page; P&L and balance sheet (`financial_statements`); latest tax return, or Form 7004 only if the business is under 2 years old.
- Product: equipment loans need a vendor quote (`equipment_quote`).
- Page count comes from the "Page X of N" markers printed on the statement. A missing page is `MISSING_PAGE`, never tampering.

**3. Mismatches (application vs documents; J13).** Compare: legal name (application vs formation certificate and EIN letter), EIN (application vs EIN letter), amount (application vs request letter, J15: the application's amount is the one reported), guarantor name / date of birth / address (application vs photo ID), revenue (application vs tax return and P&L: same year and source type only, within 1%), ending bank balance (application vs statement, within $1). Not mismatches: nicknames (Bob/Robert), LLC vs L.L.C., case, Ave vs Avenue, Ste vs #, ZIP+4. EIN and DOB are exact.

**4. Known-fraud checks (known_fraud_checks.md).** Any hit is `OLD_TRICK:...` and an automatic hold (J17).
- `STMT_TAMPER`: opening balance not equal to prior closing balance, or listed transactions do not add to the summary.
- `REV_INFLATION`: stated revenue more than 1.5x annualized deposits.
- `ID_MISMATCH`: ID name, DOB or address disagrees beyond nicknames.
- `DUP_EIN`: same EIN used by a different legal name in history.
- `SHELL_ADDRESS`: mailbox store / PMB address.

**5. Cross-deal links (the new trick is not on the list above).** Look across deals and history for the same rare thing appearing on a different deal: remit-to / bank account, document preparer or producer, registered agent, phone (e.g. 555-0142), guarantor, vendor with a near-identical name but different account, deposit habits (all round hundreds, same weekdays), amount just under an approval line ($250,000 line, see stages.json). Strong: account, preparer, agent, phone, guarantor, producer. Weak: address, bank.
- Do NOT link on: big banks, shared buildings or office-park addresses, returning customers with a clean repaid record, a single shared document tool.
- Write each partner into `fraud.linked_deals` (current folder name or `H-...` id). Every linked current deal needs its own entry, and links go both ways.
- One shared thing alone = watch (J-rule: soft concern is an `info_request`, `flagged` stays false). Model rule: a hold needs one strong shared rare entity plus at least two other independent signs (MODEL_DESIGN M8).

**6. Hold / watch / clear.**
- Hold: `flagged: true`, `held: true` (J5, J17). For an old trick, or a ring member with a strong link plus two more signs.
- Watch: `flagged: false`, `held: false`, `linked_deals: []`, say why in `notes`.
- Clear: both false, `latest_ok_stage: null`.

**7. Latest acceptable hold stage.** For a hold, the last stage at which a hold still counts as on time. Money goes out on entering Closed (J5), so the latest is the stage before it: normally `Committed`. If the damning evidence only arrives later, name the stage where it first arrives. Never `Closed`. Not held: `null`.

**8. Expected final stage and routing.** `final_stage` is how far the deal gets this week if every human says yes promptly: stops at Intake with missing Intake papers or an unresolved amount mismatch (J15), at Credit with missing Credit papers, at Product with a missing equipment quote, and stays where it is held. Routing ids come from `contacts/teams.json`: credit_decision (assigned credit officer), committee_approval (`priscilla.nguyen` under $250,000, `harold.benson` at $250,000 or more), commitment_signoff (the deal's RM), funding_release (`tasha.reed`). Use `null` for any gate the deal never reaches.

## Issue-code grammar (exact; the checker enforces it)

- `MISSING_DOC:<doc>` and `MISSING_PAGE:<doc>`, doc in: `application`, `guarantor_id`, `certificate_of_formation`, `ein_letter`, `bank_statement_YYYY-MM` (e.g. `bank_statement_2026-06`), `financial_statements`, `tax_return`, `equipment_quote`
- `MISMATCH:<field>`, field in: `legal_name`, `ein`, `amount_requested`, `guarantor_name`, `guarantor_dob`, `guarantor_address`, `annual_revenue`, `bank_balance`
- `OLD_TRICK:<code>`, code in: `STMT_TAMPER`, `REV_INFLATION`, `ID_MISMATCH`, `DUP_EIN`, `SHELL_ADDRESS`
- `issues` = still open at the end of the week (J14). Genuinely arguable ones go in `issues_optional`.
- Stages: `Intake`, `Credit`, `Committee`, `Product`, `Committed`, `Closed`.
- Time: `YYYY-MM-DDTHH:MM-06:00`, Chicago sim time, always ending `-06:00` (e.g. `2026-11-06T15:00-06:00`).

## 9. History flags (7 min)

For each history deal near a held cluster: add to `history_flags` only with **two or more independent links** to the cluster (for example the same account and the same preparer, or the same account and the same deposit pattern). One shared sign is not enough (J19; MODEL_DESIGN M18). Anything that looks suspicious but has one link, is a big bank, a shared building, or is a clean returning customer goes in `history_must_not_flag`. Also write which ids and which links in `_meta.history_notes`.

## 10. Check and commit (5 min)

```
PYTHONUTF8=1 .venv/bin/python eval/drop_labelling/check_labels.py eval/gold_drop.json
```
Fix every PROBLEM line. Then set each deal `"status": "done"`, and commit `eval/gold_drop.json` only, message `docs(07-07): blind labels for the weekend drop`. Do not change the engine afterwards before scoring.

## Judgment calls you will use most

J5/J17 hold means flagged and held; J6 application name wins; J7 range midpoint; J8 no date is null; J11 wait for the folder to go quiet; J12 six full months before the application date; J13 tolerances; J14 open issues at week end; J15 amount mismatch keeps the deal in Intake; J19 history flags need several signs, never one.
