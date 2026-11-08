# Credit Memo Template

> Owner: Jesse (finance). Locked 2026-11-07. Builder: Ezekiel.
> The Committee stage cannot exit without a credit memo: "system-written summary of what was seen, decided and why" (`rules/stages.json`).
> **Every number, the grade and the recommendation come from deterministic code.** Nemotron may smooth the prose of the summary sentences (NEM-06), never a number, grade or recommendation. If Nemotron is off or fails, the template text below is the memo.

## Where it lives

1. **Full memo** on the deal page. Contract change for Zeke: add `credit_memo: CreditMemo | None` to `DealDetail` (fields below), regenerate the fixture, run `pytest`.
2. **Short version** (4 lines) as the `message` of the `committee_approval` request to priscilla.nguyen or harold.benson.
3. Written when the deal **enters Committee**. A deal that never reaches Committee (missing docs, mismatch, hold) gets no memo.

## The numbers (exact definitions)

| Item | Definition |
|---|---|
| **Assumed rate** | **9.0% a year**, one rate for every deal. Grounded in the data: this bank's existing line for a sample borrower charges $412.50/month on $55,000 = 9.0%. Always printed as "indicative, at an assumed 9.0%". Lives in config, not code. |
| **Yearly payment (debt service)** | Revolving Line of Credit: interest only on the **full** line = amount × 9.0% (conservative: assumes fully drawn). Term, Equipment and Working Capital loans: standard amortizing payment over `term_months` at 9.0%/12, × 12. |
| **Net income (annualized)** | YTD net income from the P&L × 12 / months in the YTD period (Jan–Oct = 10). Use FY net income only if there is no YTD column. |
| **Debt coverage** | Net income (annualized) ÷ yearly payment. Label: "net-income coverage of the new loan; ignores other debt". |
| **Revenue support** | Stated annual revenue ÷ annualized bank-statement deposits (sum of months present ÷ months × 12). Same figure the REV_INFLATION check uses. |
| **Cash cover** | Balance-sheet cash ÷ monthly payment, in months. |
| **Time in business** | Years from formation date to the application date. |
| **Relationship** | From history by EIN: returning with all prior loans current/paid off; new; or returning with any past-due/charged-off loan. |

## Risk rating (1 = best, 5 = worst)

Points, lower is better:

| Test | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| Debt coverage | ≥ 2.0x | 1.5–2.0x | 1.25–1.5x | 1.0–1.25x | < 1.0x or negative income |
| Revenue support | ≤ 1.1x | > 1.1x to 1.5x | | | |
| Time in business | ≥ 5 yrs | 2–5 yrs | < 2 yrs | | |
| Relationship | returning, clean | new borrower | returning, past-due or charged-off | | |

Boundaries: a value exactly on a line takes the better band (e.g. 2.0x = 0 points, 1.5x = 1 point).

| Points | Grade |
|---|---|
| 0 | **1 Strong** |
| 1–2 | **2 Satisfactory** |
| 3–4 | **3 Acceptable** |
| 5–6 | **4 Watch** |
| 7+ | **5 Weak** |

**Overrides:**
- Fraud **watch** tier (1–2 signal families, not held): grade is at least 3, plus the condition "Fraud Ops review before funding".
- Revenue support > 1.5x is OLD_TRICK:REV_INFLATION. The deal goes to Fraud Ops and never reaches Committee, so no memo.

**Recommendation:**
- Grades 1–3: **"Recommend approval, subject to the conditions below."**
- Grade 4: **"Not recommended as submitted."** Name the test that drove it and what would fix it (e.g. "coverage 1.1x: a longer term or a smaller amount would bring it above 1.25x").
- Grade 5: **"Not recommended."** Give the reasons.

The committee still decides. The memo advises.

## Conditions of approval

**Always:**
1. Commitment letter signed by the RM and countersigned by the borrower (RM confirms, J10).
2. Funds go only to the borrower's own account or a verified vendor's remit account.
3. Final fraud screen clear immediately before funding.
4. Personal guarantee from each guarantor.

**When they apply:**
| Trigger | Condition |
|---|---|
| Revolving Line of Credit | Annual review and renewal; line may be drawn only while the borrower is current |
| Equipment Loan | First lien on the financed equipment (UCC filing); vendor identity and remit account verified against known vendors |
| Vendor not in history | Verify vendor and remit account by an independent phone callback before funding |
| `needed_by` set | Fund before the deadline: state it ("funds required by Fri 2026-11-06 15:00") |
| Revenue support 1.1–1.5x | Borrower to explain the gap between stated revenue and deposits |
| Debt coverage under 1.25x | Committee to consider a longer term, a smaller amount or extra collateral |
| Fraud watch tier | Fraud Ops review before funding |

## Full memo: the template

Fill `{…}` from engine facts. Leave out a section's optional lines when they don't apply. Never leave a `{…}` in the output: if a value is missing, write "not provided" and lower the confidence note.

```
CREDIT MEMO: {legal_name}{ (DBA {dba})}
Prepared {sim_time} by Prism for {committee_approver_name} ({Delegated approver | Committee chair})
RM: {rm_name} · Credit officer: {credit_officer_name}{ (backup for {primary}, out of office)} · Credit decision: {approve} on {date}

REQUEST
{amount} {product}, {term_months} months, for {purpose_category}: "{use_of_proceeds}"
Collateral offered: {collateral}. Funds needed by: {needed_by | no specific date}.

RISK GRADE {grade} ({grade_name}). {recommendation}
{one-sentence reason: the two tests that most drove the grade}

CHARACTER
{years} years in business (formed {formation_date}). {ownership}.
Relationship: {returning customer since {year}; prior loans {list with outcomes} | new borrower}.
Financials prepared by {preparer}.

CAPACITY  (indicative, at an assumed 9.0%)
Yearly payment on this loan: {debt_service} ({interest-only on the full line | {term}-month amortizing}).
Net income: {ni_ytd} for {ytd_period}, about {ni_annual} a year. Coverage {coverage}x.
Revenue: stated {stated}; bank statements support about {deposits_annual} a year ({revenue_support}x).
Note: net-income coverage of the new loan only; other debt is not included.

CAPITAL
Cash {cash} (covers {cash_months} months of payments) · Receivables {ar} · Liabilities {liabilities}.

COLLATERAL
{collateral}. {Equipment: quote {quote_no} from {vendor}, total {quote_total}; vendor and remit account ...{last4} {verified: seen in {n} past loans | NOT in history: callback required}.}

CONDITIONS
{purpose and context; deadline pressure; unusual-but-explained items, e.g. "international receivables in 4 currencies, matched to named client wires"}

CHECKS PERFORMED
Documents: all required documents present{, statement pages complete}.
Statements: {n} months, all foot to their summaries and chain month to month.
Bank's known-fraud checks (5): all pass.
Cross-deal fraud screen: {no shared rare entities | watch: {reason}}.
Open issues: none.

CONDITIONS OF APPROVAL
1. … (the "always" list, then the triggered ones)

SOURCES
{each number → the document it came from}
```

## Short version (the committee request message)

Four lines, plain words, in this order:

```
{legal_name} requests {amount} {product} over {term} months for {purpose}. Risk grade {grade} ({grade_name}): {recommendation}
Coverage {coverage}x at an assumed 9.0%; revenue supported {revenue_support}x by bank deposits; {years} years in business; {relationship}.
All documents and checks clear{; needed by {needed_by}}.
Full memo on the deal page. Please approve or decline{ by {needed_by - lead time}}.
```

## Worked example (made-up deal, not from the sample)

Cedar Lane Bakery LLC, $50,000 Working Capital Loan, 24 months, est. 2017, new borrower, YTD Jan–Oct net income $62,000, stated revenue $700,000, deposits annualized $680,000, cash $70,000.

- Yearly payment: amortizing $50,000 over 24 months at 0.75%/month = $2,284.24 × 12 = **$27,411**
- Net income annualized: 62,000 × 12/10 = **$74,400** → coverage 74,400 / 27,411 = **2.71x** → 0 pts
- Revenue support: 700,000 / 680,000 = **1.03x** → 0 pts
- Time in business: 9 years → 0 pts
- Relationship: new borrower → 1 pt
- **Total 1 pt → Grade 2 Satisfactory → "Recommend approval, subject to the conditions below."**
- Cash cover: 70,000 / 2,284 = **31 months**

Short message:
```
Cedar Lane Bakery LLC requests $50,000 Working Capital Loan over 24 months for working capital. Risk grade 2 (Satisfactory): recommend approval, subject to conditions.
Coverage 2.71x at an assumed 9.0%; revenue supported 1.03x by bank deposits; 9 years in business; new borrower.
All documents and checks clear.
Full memo on the deal page. Please approve or decline.
```

## Test cases for Zeke

The rating must reproduce these on the sample deals that reach Committee (from `eval/gold.json` routing). Recompute from the documents; these are Jesse's expected outputs:

| Deal | Yearly payment | Coverage | Points | Grade |
|---|---|---|---|---|
| Garza Family Pharmacy | $5,400 (interest only) | 25.6x | 0 | 1 Strong |
| Okafor Advisory - James | $108,000 (interest only) | 14.5x | 0 | 1 Strong |
| Priya's Bakery | $36,730 (12-mo amortizing) | 1.48x | 2 | 2 Satisfactory |
| Harbor Tea Co | $61,782 (84-mo amortizing) | 5.5x | 1 (new borrower) | 2 Satisfactory |
