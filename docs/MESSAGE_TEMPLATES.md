# Message Templates: alerts, sign-off requests, borrower requests

> Owner: Jesse (finance). Locked 2026-11-07. Builder: Ezekiel.
> These are the deterministic messages. Nemotron may smooth the wording (NEM-06), but it must keep every name, number, time and the "what unblocks it" line. If Nemotron is off or fails, these templates are the messages.
> Rules they implement: `rules/stages.json` ("alert_must_say", sign-off gates), `contacts/teams.json` (owners, backups, escalation), `docs/DETAILS_CHECKLIST.md` (J3, J4, J5, J10, J16, J18).

## House style

- **Plain words, 2–4 sentences.** Lead with what you need from the reader.
- **Names, not ids:** "Aisha Grant", not `aisha.grant` (the `to` field keeps the id).
- **Whose deal** = the borrower's legal name, plus the DBA if there is one, plus the RM: "Sunrise Rasoi Bakery LLC (Priya's Bakery), RM Elena Ruiz".
- **Times** in sim time, Central: "Tue 11/03 3:05 PM CT". **Durations** as "26h 10m". Money as "$248,000".
- **Never** a bare "please review." Every message says exactly what decision or document unblocks the deal.

## 1. Stuck-deal alerts (the 100 / 150 / 200% ladder)

Every alert must say **four things** (`stages.json`): (1) whose deal (borrower + RM), (2) which stage and for how long, (3) what it is waiting for, (4) what would unblock it.

| Level (`alerts.level`) | When | To (one entry per person, J3) |
|---|---|---|
| `alert` | 100% of the stage limit | Stage owner **and** the deal's RM |
| `escalation` | 150% | The owner's `escalates_to` (teams.json) |
| `escalation` | 200% (second escalation) | lauren.kim (sent even if she already got the 150% one, J4) |

**100%: alert**
```
{Borrower} ({DBA}), RM {RM name}, has been in {Stage} for {duration}, past its {limit}h limit.
It is waiting on {waiting_on}.
To unblock it: {unblock}.
```

**150%: escalation to the owner's manager**
```
Escalation: {Borrower} ({DBA}), RM {RM name}, has been in {Stage} for {duration}, 1.5x its {limit}h limit.
It is waiting on {waiting_on}; {owner name} was alerted {alert time} with no movement since.
To unblock it: {unblock}. Please step in or reassign.
```

**200%: second escalation to Lauren Kim**
```
Second escalation: {Borrower} ({DBA}), RM {RM name}, has been in {Stage} for {duration}, 2x its {limit}h limit.
It is waiting on {waiting_on}. Alerted {owner name} at {alert time}, escalated to {manager name} at {escalation time}.
To unblock it: {unblock}.{ Funds are needed by {needed_by}.}
```

### "Waiting on" and "to unblock it": the fixed list

| Situation | Waiting on | To unblock it |
|---|---|---|
| Missing document | "the borrower's {document}" | "the borrower sends {document} (requested {time})" |
| Missing statement page | "page {x} of the {month} bank statement" | "the borrower sends the complete {month} statement" |
| Mismatch | "the borrower to confirm the {field}: the application says {a}, the {doc} says {b}" | "the borrower confirms which is correct, with a corrected document" |
| Unanswered sign-off | "{person}'s {decision type} (sent {time})" | "{person} or backup {backup} answers approve / decline{ / request info}" |
| Fraud hold pending | "Fraud Operations to review the hold request (sent {time})" | "Fraud Ops places or releases the hold. Funding stays frozen until then" |
| Vendor not verified (Product) | "verification of vendor {vendor} and remit account …{last4}" | "a callback to {vendor} confirming the remit account" |
| Commitment letter | "the signed commitment letter" | "{RM name} confirms the borrower has countersigned" |

### Rules for Zeke

- **Exactly once** per deal × stage × level. If the clock jumps 6h+ at once, send **every** threshold crossed, each stamped with the time it was actually crossed.
- Timers are wall-clock sim hours; staff hours don't pause them (J16). Alerts go out at any hour.
- Committee limits differ by route: delegated 24h (alerts at 24/36/48h), chair 48h (48/72/96h).

## 2. Unanswered sign-off requests: follow-up and reroute

| When | What happens |
|---|---|
| Request sent | One request to the right person (backup immediately if they are out of office) |
| **100% of the stage limit, no answer** | Reminder to the person **and the same request sent to their backup**. First answer wins; the other copy is closed. The stage `alert` also fires |
| 150% | Stage `escalation` to the owner's manager (as above) |
| 200% | Second escalation to Lauren Kim |

**Reminder + backup copy**
```
Reminder: {Borrower} ({DBA}) still needs your {decision type}, sent {time} ({duration} ago).
{Backup name}, you are copied as backup: whichever of you answers first decides it.
{one-line ask, same as the original request}
```

**Fraud hold (no stage limit in the rulebook):**
- No answer from Victor Hale in **2 hours** → send the hold request to **Monica Salas** (his backup and manager).
- No answer from her in **another 4 hours** → escalate to Lauren Kim (Monica's `escalates_to`).
- The deal stays frozen the whole time and is reported `held: true` (J5).

## 3. Sign-off requests (`human_requests.message`)

**`credit_decision`** → assigned credit officer (backup if out of office)
```
Credit decision needed: {Borrower} ({DBA}), RM {RM name}, requests {amount} {product} over {term} months for {purpose}.
File is complete: {n} months of statements, financials, {tax return | Form 7004 extension (business under 2 years old)}; the bank's 5 known-fraud checks pass.
Stated revenue {stated} vs. about {deposits_annual} a year in deposits. {Returning customer since {year}, prior loans repaid | New borrower}.
Please reply approve, decline or request info.{ Funds are needed by {needed_by}.}
```
If routed to a backup: add "You are covering for {primary}, who is out of office until {date}."

**`committee_approval`** → priscilla.nguyen (under $250,000) or harold.benson ($250,000 and up)
Use the 4-line short memo from `docs/CREDIT_MEMO_TEMPLATE.md`. Add for the delegated route: "Under the $250,000 delegated limit."

**`commitment_signoff`** → the deal's RM
```
Commitment ready: {Borrower} ({DBA}), {amount} {product} over {term} months, approved by {committee approver} on {date}.
Please sign the commitment letter and confirm the borrower has countersigned.{ Funds are needed by {needed_by}.}
```

**`funding_release`** → tasha.reed
```
Funding release: {amount} to {Borrower} ({DBA}), RM {RM name}.
Pay to: {borrower's own account at {bank} …{last4} | verified vendor {vendor}, {bank} …{last4} ({n} past loans paid to this account)}.
Final fraud screen: clear as of {time}. Commitment signed {date}.
Please release or hold.{ Funds are needed by {needed_by}.}
```

**`fraud_hold`** → victor.hale (backup monica.salas)
```
Fraud hold requested: {Borrower} ({DBA}), RM {RM name}, {amount} {product}, frozen at {Stage} as of {time}. No money has gone out.
Why: {n} independent warning signs agree: {sign 1}; {sign 2}; {sign 3}{; …}.
Linked: {current deals}{ and past loans {H-ids} ({status, e.g. funded, 30 days past due})}.
Please place or release the hold. The deal stays frozen until you do.
```
Old trick (J17): "Why: the bank's known-fraud check {code} failed: {plain-words evidence, e.g. 'August closing balance is $48,200 higher than its own transactions'}."

**`fraud_release`**: only when new evidence clears a deal Prism asked to hold. The same fields as `fraud_hold`, with "Why we now think it is clear: {evidence}." Prism never releases a hold itself.

## 4. Borrower requests (`info_request`, `"to": "borrower"`)

Polite, specific, one list. Sent as soon as the folder has been quiet 30 sim-minutes (J11), or as soon as a mismatch is found.

```
Thank you for your application for {amount} {product}. To keep it moving we need:
- {item 1}
- {item 2}
Once we have these, your loan moves to the next step.{ You told us you need the funds by {needed_by}, so please send them as soon as you can.}
```

| Situation | Bullet wording |
|---|---|
| Missing document | "{document} (for example, your {year} business tax return)" |
| Missing statement month | "your bank statement for {Month YYYY}" |
| Missing page | "the complete {Month YYYY} statement: we received page 1 of {N} only" |
| Mismatch | "confirmation of your {field}: your application shows {a}, but your {doc} shows {b}" |
| Equipment quote | "the vendor's quote for the equipment, showing the vendor's remit-to bank account" |

## 5. Deadline-risk alert (J18)

Fires once, to the RM and the current stage owner, as soon as the remaining stages can't finish before `needed_by` at the bank's typical stage durations (from `history/stage_events.csv`), counting business hours for sign-offs.
```
Deadline at risk: {Borrower} ({DBA}), RM {RM name}, needs {amount} by {needed_by}.
It is in {Stage}; at typical speed the remaining steps ({list}) finish around {projected time}, after the deadline.
To make it: {next person} needs to answer {decision} by {latest time}.
```

## 6. Worked examples (made-up deals, not from the sample)

**100% alert, missing document** (Credit, 48h limit), to the credit officer and the RM:
```
Cedar Lane Bakery LLC, RM Brian Foster, has been in Credit for 48h 0m, past its 48h limit.
It is waiting on the borrower's 2025 business tax return.
To unblock it: the borrower sends the 2025 tax return (requested Mon 11/02 10:30 AM CT).
```

**150% escalation, unanswered sign-off** (Committee, delegated 24h route), to Susan Ortiz:
```
Escalation: Cedar Lane Bakery LLC, RM Brian Foster, has been in Committee for 36h 0m, 1.5x its 24h limit.
It is waiting on Priscilla Nguyen's committee approval (sent Tue 11/03 9:00 AM CT); Priscilla Nguyen was alerted Wed 11/04 9:00 AM CT with no movement since.
To unblock it: Priscilla Nguyen or backup Susan Ortiz answers approve / decline. Please step in or reassign.
```

**Fraud hold request:**
```
Fraud hold requested: Example Freight LLC, RM Elena Ruiz, $245,000 Equipment Loan, frozen at Intake as of Mon 11/02 2:10 PM CT. No money has gone out.
Why: 3 independent warning signs agree: its bookkeeper appears on only two other loans, both in the last 3 months; the vendor's payment account differs from the established vendor with the same name; every deposit is a round hundred, landing only on two weekdays.
Linked: past loans H-0000-001 (funded, 30 days past due) and H-0000-002 (funded, current).
Please place or release the hold. The deal stays frozen until you do.
```
