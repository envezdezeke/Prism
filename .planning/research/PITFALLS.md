# Pitfalls Research

**Domain:** Deterministic loan-pipeline + cross-deal fraud engine, replayed on a sim clock against a hidden grader (HackUTD 2026, Goldman "DealPilot" + NVIDIA Nemotron track)
**Researched:** 2026-11-07
**Confidence:** HIGH for data-derived findings (I parsed every PDF, CSV and history table in `data/participant/`), MEDIUM for how the grader scores ambiguous cases (rubric is not published), LOW for Nemotron API behavior (not verified against the live endpoint)

**Phase labels used below** (map to the roadmap as you see fit):
P0 Foundations (env, sim-clock-gated data layer, schema validator, determinism harness) / P1 Ingest and Extract / P2 Issue engine (MISSING, MISMATCH, old tricks) / P3 Pipeline, routing, SLA, human loop / P4 Fraud graph / P5 Nemotron agents / P6 UI and demo / P7 Hardening, self-score, replay on new drop.

---

## What the data actually contains (ground truth by inspection)

Derived by reading every document. Not confirmed by the organizers, so treat it as a **self-score oracle seed** (MEDIUM), and keep the reasoning next to each expected value. Several of these are NOT in the README's trap list. Some of the README's "traps" also contain a real issue (Westfield).

| Folder | Expected by inspection | Evidence |
|---|---|---|
| Garza Family Pharmacy | No issues, no fraud. Returning customer (matches H-2511-002 on EIN, name, DOB, DL, address). | Statements are 3 PDF pages for "Page x of 2". One Saturday deposit per month. All amounts equal the $1,920,000 history. |
| tyler loopwise loan stuff | `MISSING_DOC:bank_statement_2026-06` only. No tax return needed (7004 is correct: formed 2025-03-10). No fraud. | App note: "June missing, will send." No `export_june_2026.csv` exists. Revenue is "approx 400-500k"; annualized CSV credits are $466,616. |
| Oakline Auto | `MISSING_PAGE:bank_statement_2026-08`. Nothing else. | Aug statement says "Page 1 of 2" and the file has no page 2. Only 13 of ~25 transactions are present. App says "Bob Kline"; ID, cert and letter say "Robert Allen Kline" (nickname, not a mismatch). Vendor Metroplex Equipment Supply, **Inc.**, acct 9902, is the known good one. |
| Bluebonnet Landscape | `MISMATCH:amount_requested` (app $250,000.00 vs request letter $205,000.00) and `MISSING_DOC:equipment_quote` (Equipment Loan, no quote file). | App amount sits exactly on the committee boundary. Statements are named "may/jun/jul/aug/sep/oct statement.pdf". |
| LSFD_docs | `MISSING_DOC:tax_return` and `MISSING_DOC:equipment_quote`. | 12 `SCAN_*.pdf` = app, ID, cert, EIN, financials, letter plus 6 statements. No tax return and no 7004 (formed 2017). Equipment Loan with no quote. Arrival order is scrambled relative to filename order. |
| Granite Bay Building Supply | `OLD_TRICK:STMT_TAMPER` and `OLD_TRICK:REV_INFLATION`. Fraud flag (old trick). | Aug statement summary: 79,275.96 + 83,594.59 - 71,330.37 = 91,540.18, but the printed closing is 139,740.18. The last transaction balance is 91,540.18 and Sep opens at 91,540.18. Stated revenue $3.1M vs annualized deposits about $1.014M (3.06x; threshold 1.5x). YTD P&L revenue is $845K. |
| Westfield Print & Sign | `MISMATCH:ein` (app `74-3169524` vs EIN letter and tax return `74-3196524`, a digit transposition). **Not fraud.** | New vendor Lone Star Graphic Systems (Prairie National ...5530) is normal. Its address 1200 Commerce St Ste 120 is the same building as the ring's agent (Ste 410) but unrelated. |
| Priya's Bakery | No issues. Legal name is **Sunrise Rasoi Bakery LLC**. `needed_by` = `2026-11-06T15:00-06:00`. `purpose_category` = `payroll`. Credit routes to marcus.lee, not dana. Returning customer (H-2512-005). | "Friday 2026-11-06 by 3:00 PM (payroll)". Product is Working Capital Loan, but history maps this exact deal to payroll. |
| Okafor Advisory - James | No issues. Chair routing ($1.2M). Returning (H-2601-006, $900K then). | Foreign-currency contract summary (GBP, EUR, SGD, AED). Only 3-5 large deposits a month; 2/3, 2/3, 1/5, 2/5 are round hundreds. Deposits in Aug land only Mon/Thu. |
| Harbor Tea Co | No issues. Chair routing ($320K). | Business address equals the registered agent's office (5950 Berkshire Ln Ste 1000, Northstar). 15 history deals sit there and 14 are not fraud. |
| Pecan Grove / Ridgeway Freight / Summit Peak | New-trick ring. Hold request and mutual `linked_deals`. History links: H-2608-002 and H-2609-008 only. | See P4 pitfalls. No OLD_TRICK code applies. |

Other checkable facts: every P&L "Cash" value is within $1 of the October closing balance (Pecan 98,068 vs 98,067.50), so a bank_balance mismatch needs a $1 tolerance. No current EIN collides with history except the three returning customers, which have identical names.

---

## Critical Pitfalls

### Pitfall 1: Reading future files (sim-clock leakage)

**What goes wrong:** All 173 files already sit in `shared_folder/` at t=0. Code that globs the folder, builds the entity graph over everything, or lets an agent tool query "all deals" will see Ridgeway, Pecan and Summit before they arrive. The output then shows `flagged_at` earlier than the files that justify it, or a cross-deal link to a deal that has not landed.

**Why it happens:** Batch-pipeline habit. `clock.py sync` exists, but nothing forces you to use it. Precomputed caches and the Nemotron investigator's graph tools are the usual leaks.

**How to avoid:**
- One data-access layer, `visible_files(now)`, that filters `arrivals.jsonl` by `arrive_at <= now`. Nothing else may touch the disk.
- Sort arrivals by (`arrive_at`, path) so ties are deterministic. Okafor's `09_Contract_Summary.pdf` and the Oct statement share `15:50`.
- Process events in time order: arrivals, human answers, SLA thresholds.
- Give every Nemotron tool a `now` parameter, enforced in the tool, not the prompt.
- Add a metamorphic test: delete every file with `arrive_at > T`, rerun to T, and assert the output is identical.
- The clock's `sync` skips files whose destination already exists. A corrected file with the same path in the weekend drop will silently not copy. Key files by (path, content hash), and do not rely on `sync`.

**Warning signs:** Any `flagged_at` earlier than the arrival of its evidence. A Ridgeway fraud reason that names Pecan or Summit when Ridgeway is first flagged. Results differ when a future file is deleted.

**Phase to address:** P0, then re-verify in P4 and P5.

---

### Pitfall 2: Crashing or emitting a partial file on the hidden set

**What goes wrong:** One unreadable PDF, an unexpected doc type, a folder name with `'` or `&`, or a null where you expected a string raises an exception. No submission JSON gets written and the whole hidden set scores zero.

**Why it happens:** The sample is clean, so the happy path gets all the testing. The hidden set has a different trick and probably different document shapes.

**How to avoid:**
- Wrap every deal and every document in try/except. On failure, record the error in an extra key and continue with `null` fields.
- Always write the JSON, even for an empty run.
- Keep a validator against `SUBMISSION_FORMAT.md`: enum values, ISO times with offset, keys equal to the exact folder name, and `issues` limited to the allowed `KIND:target` grammar.
- Folder keys to test: `Priya's Bakery`, `Okafor Advisory - James`, `Westfield Print & Sign`, `tyler loopwise loan stuff`.
- Take `--folder`, `--arrivals`, `--history`, `--teams`, `--stages` and `--out` as parameters. Never hard-code the folder names, May to Oct, or `2026-11-02`.
- Hidden `teams.json` and `assignments.json` may differ from the sample.

**Warning signs:** The engine passes on the sample but fails on a synthetic folder with an unknown doc type, a missing app, or a doc with no text layer.

**Phase to address:** P0 (validator and harness), P7 (fuzz run on synthetic drops).

---

### Pitfall 3: Classifying documents by keyword or filename

**What goes wrong:**
- Tyler's `IRS 7004 extension.pdf` has the title "Form 7004 - **Application** for Automatic Extension". A keyword classifier reads it as a second loan application.
- "Statement" appears in both "Business Checking **Statement**" and "Financial **Statements**".
- `state filing.pdf` contains "state". `P&L and balance sheet.pdf` is the financial statements.
- `SCAN_20261103_*.pdf` filenames carry no type.
- Priya's and Bluebonnet's statements sort alphabetically as aug, jul, jun, may, oct, sep.
- The weekend drop adds "corrections, addenda, bank notices" (Collections), which fall through to an unknown type.

**Why it happens:** Filename heuristics work on the tidy folders (`01_Loan_Application.pdf`) and silently break on the messy ones.

**How to avoid:**
- Classify by the first title line plus anchor phrases, in a fixed order of specificity: "Small Business Loan Application", "Texas Driver License", "Certificate of Formation", "IRS Notice CP 575", "Business Checking Statement", "Financial Statements", "U.S. Income Tax Return", "Form 7004", "Re: Loan request", "Quotation", and so on. Anything else is `other`, never an exception.
- Take the statement month from the in-document "Statement period", never the filename (hidden set: `Bank_Statement_2026-05.pdf` could be mislabeled).
- Sort statements by period before any continuity check. On the sample, a filename sort manufactures five false opening-vs-closing breaks for each of Priya and Bluebonnet.
- Route unknown docs (Collections notice) by EIN, name or guarantor to existing deals or history, not by folder.
- A JPG has no text layer. Classify images as "photo ID (unverified)" from extension and folder context if OCR or VL fails. Do not raise `MISSING_DOC:guarantor_id` for it.

**Warning signs:** A deal shows two applications, zero financial statements, or six statements with a "break" between months.

**Phase to address:** P1.

---

### Pitfall 4: Parsing the bank statement wrongly (columns, pages, CSVs)

**What goes wrong:**
- pypdf text extraction drops the Credit/Debit column. Each row yields date, description, one amount and the balance. You must infer the direction from the running-balance delta, or deposits and withdrawals are conflated.
- "Page X of N" sits at the end of each transaction page. The first PDF page is a summary page with no marker. PDF page count is not N: Garza, Harbor and Priya have 3 PDF pages for "of 2". Bluebonnet May and Granite Oct have a blank trailing PDF page for "of 1".
- Tyler's CSVs have no summary block. A first line `Frost-Hill Bank - acct ...7720 - Loopwise Labs Inc.` precedes the header, dates are `8/3/26`, and a positive `STRIPE REFUND REVERSAL` is a credit.

**Why it happens:** Treating PDF page count as the page count, and treating CSV exports as "bad PDFs".

**How to avoid:**
- Parse rows as (date, desc, amount, balance) and set direction by `balance_prev +/- amount == balance`.
- `MISSING_PAGE` = the set of X markers is not exactly {1..N}, including gaps and a missing first page. Oakline Aug shows only "Page 1 of 2". Never use PDF page count.
- Statement-period completeness is a separate check (`MISSING_DOC:bank_statement_YYYY-MM`).
- Support CSV: derive opening from the first balance minus the first amount, use the running balance, and parse M/D/YY.
- Test fixtures to build now: Oakline Aug (missing page), Tyler (CSV, missing month), Granite Aug (tamper).

**Warning signs:** Oakline gets `STMT_TAMPER` (Pitfall 5). Garza gets `MISSING_PAGE`. Tyler's CSV months report zero deposits.

**Phase to address:** P1 (parser), P2 (checks).

---

### Pitfall 5: False STMT_TAMPER (missing page, missing month, bad sort) and missed STMT_TAMPER

**What goes wrong:**
- Oakline Aug has 13 of ~25 transactions. Credits sum to 58,658.84 against a summary of 91,158.72. A sum check alone says "tampered". The truth is a missing page. Sep opens at 95,286.57 = Aug closing, so continuity is fine.
- Tyler is missing June. July opens at 28,134.91 vs May close 20,245.10. A naive continuity check across the gap says "tampered". Jul to Oct are internally consistent.
- Filename-order chains produce false breaks (Pitfall 3).
- The real tamper (Granite Aug) is only caught by **footing** the summary (open + deposits - withdrawals vs closing) and by the **Sep opening vs Aug closing** break. Transaction sums alone do not catch it, because the transactions are intact.

**How to avoid:**
- Three independent checks per statement: (a) summary footing, (b) transactions sum to summary (skipped if pages are missing), (c) opening equals the previous month's closing (skipped across a missing month).
- Emit `OLD_TRICK:STMT_TAMPER` only when a check that is valid for that statement fails. If a page is missing, emit `MISSING_PAGE` and say why the sum check was skipped.
- Use cent-exact Decimal arithmetic.

**Warning signs:** Oakline or Tyler carry `STMT_TAMPER`. Granite Bay does not.

**Phase to address:** P2.

---

### Pitfall 6: Wrong "6 most recent full months" and wrong annualization

**What goes wrong:** Hard-coding May to Oct. Counting November as a month. Annualizing Tyler's five CSV months as sum x 2 (gives $388,847; the right answer is average x 12 = $466,616). Treating a 7th statement as a requirement.

**How to avoid:** Compute the six calendar months before the month of the reference date (application date or sim now). Annualize as (sum / months present) x 12. When a month is missing, compute REV_INFLATION on the months you have and say so. Extra months are ignored, never "missing". On this sample the two methods differ by about 20%, which matters if Tyler's range is near the 1.5x line.

**Warning signs:** A hidden-set drop dated in a different month yields wrong requirements. REV_INFLATION ratios differ between the 5-month and 6-month cases.

**Phase to address:** P2.

---

### Pitfall 7: Revenue comparisons that false-alarm on young businesses and ranges

**What goes wrong:**
- Ring apps state $980,000, $1,120,000 and $1,040,000 vs 2025 tax revenue $470,400, $470,400 and $374,400. A naive `MISMATCH:annual_revenue` (app vs tax) fires on all three. The firms were formed in Jun, Jul and Aug 2025, so FY2025 is a partial year. The apps match annualized deposits (Ridgeway deposits $1.109M vs stated $1.12M) and the annualized Jan-Oct P&L.
- Tyler's "approx 400-500k (annualized, we are growing fast)" is not a number. FY2025 is $310K (10 months since March).
- Okafor's contract summary is in four currencies. Summing it against revenue is meaningless.

**How to avoid:**
- Compare like with like: stated vs annualized deposits (the rule in `known_fraud_checks.md`), and tax vs P&L FY2025 as same-period figures. Prorate when formation falls within the tax year, and use a tolerance.
- Parse ranges explicitly. Decide the extraction convention once (midpoint $450,000 with the raw range kept in a note is my recommendation, LOW confidence on the grader's expectation).
- Never read the contract summary as a revenue source.
- Remember the REV_INFLATION rule in the bank's file is vs **deposits**, and history confirms a clean split: legitimate ratios 0.93-1.06, REV_INFLATION 2.83-3.16.

**Warning signs:** All three ring deals carry a MISMATCH on revenue. Tyler is listed as a revenue-inflation case.

**Phase to address:** P2.

---

### Pitfall 8: MISMATCH false alarms (names, nicknames, formatting, rounding) and missed real mismatches

**What goes wrong:**
- False alarms: EIN letters are uppercase (`GARZA FAMILY PHARMACY LLC` vs `Garza Family Pharmacy LLC`). Priya's folder name and DBA differ from her legal name. Oakline's guarantor is "Bob Kline" vs "Robert Allen Kline". Tyler's ID is an upside-down-ish JPG with uppercase, split lines. Cash `$98,068` vs closing `$98,067.50`. "$250,000.00" vs "$250000".
- Missed real mismatches (over-correcting after reading the README's trap list):
  - Westfield's EIN transposition, `74-3169524` vs `74-3196524`. Do not compare EINs by digit set, sorted digits or fuzzy ratio. Compare the exact digit string.
  - Bluebonnet's request letter says $205,000.00 while the app says $250,000.00. This is a one-digit-swap family mistake that also straddles the routing threshold.

**How to avoid:**
- Normalize names by casefold, punctuation and suffix (LLC, L.L.C., Inc, Inc., Co, Company, and "&"/"and"), then compare. A different base name is a real mismatch.
- Nickname table plus middle-name and initial tolerance for people. DOB and address are compared exactly after normalization of case, "Dr/Drive", "Apt", and line breaks.
- EIN is an exact string compare after stripping the hyphen. Amounts are exact in cents with the same tolerance only for formatting. Bank balance has a $1 tolerance.
- Extracted `legal_name` comes from the application's "Legal business name", never the folder or DBA.
- Make a deliberate list of "documented traps that contain a real issue": Westfield EIN.

**Warning signs:** Garza, Priya, Okafor or Oakline show any MISMATCH. Westfield or Bluebonnet show none.

**Phase to address:** P2.

---

### Pitfall 9: ID_MISMATCH and the JPG (no OCR installed)

**What goes wrong:** The environment has pypdf, Pillow, pandas and FastAPI, but **no OCR** (no tesseract, easyocr, cv2) and no `networkx`, `rapidfuzz`, `pdfplumber` or `openai` package. Tyler's `IMG_2291.jpg` (914x582, slightly rotated, text rendered as pixels) can only be read by a VL model or a newly installed OCR. If the VL call fails or hallucinates, you either raise a false `MISSING_DOC:guarantor_id` or a false ID_MISMATCH on the messy-but-real borrower.

**Facts:** The JPG reads: DL 34871190, TYLER JAMES BROOKS, 845 LAKESIDE CIR APT 3104, RICHARDSON TX 75082, DOB 1996-02-14. All of it matches the app.

**How to avoid:**
- Install what you need in P0: `pip install rapidocr-onnxruntime` (or similar) plus `networkx`, `rapidfuzz`, `pdfplumber`. Test on this exact JPG.
- Treat unreadable as "present, unverified, route to human", never as a mismatch.
- Require two agreeing reads (VL plus OCR, or VL twice) before an image-derived value can produce `MISMATCH:*` or `OLD_TRICK:ID_MISMATCH`. A single VL read may not trip a fraud flag.
- Tyler's DOB, DL and address in the application should be the extraction source for fields. The JPG is only a cross-check.

**Warning signs:** Tyler shows `MISSING_DOC:guarantor_id`, any ID mismatch, or a fraud flag.

**Phase to address:** P0 (install, 30-minute spike), P1.

---

### Pitfall 10: Missing-document logic (equipment quotes, tax returns, 7004, timing)

**What goes wrong:**
- Two equipment-loan deals have no quote: Bluebonnet and LSFD. The quote is only a hard exit requirement at Product, so a stage-based check will not surface it until late.
- LSFD has neither a tax return nor a 7004 (formed 2017, so 7004 would not satisfy it anyway).
- Tyler's 7004 is correct only because the business is under 2 years old. Applying "7004 OR return" without the age rule either false-alarms Tyler or lets a 5-year-old business off with a 7004.
- A `MISSING_DOC` raised while the folder is still arriving is a false alarm. Folders land over about 20 minutes (Garza 09:21 to 09:40; the app arrives first, the EIN letter at 09:25).

**How to avoid:**
- Required-doc set = f(product, business age, reference date). Equipment loans need the quote. <2 years: return OR 7004. >=2 years: return only.
- Age rule must be date-precise (a business formed exactly two years ago is not "<2 years"; history has a 2024-11-02 formation).
- Evaluate "missing" at a stage gate after a quiet window (for example 30 sim-minutes after the last arrival), or when the stage deadline requires the doc. Emit the issue in the final JSON, but do not send borrower info requests while a folder is still landing.
- Surface known-missing docs at the earliest defensible point (Credit entry for statements and returns, Intake time for quote), but never advance past the stage that requires them.
- Tyler's 7004 shows "Extended due date 2026-09-15, return not yet filed". That date has passed. It is not in the rules, so do not flag it.

**Warning signs:** Missing docs appear and then disappear within the same arrival window. LSFD or Bluebonnet get zero issues.

**Phase to address:** P2, P3.

---

### Pitfall 11: Advancing while waiting (or on nobody's answer), and reopening

**What goes wrong:**
- Tyler has June missing, Oakline has a missing page, Bluebonnet and LSFD have missing docs. Credit's exit requires all of them. If the engine advances anyway, the MOVE score loses points.
- Stages advance without the human answer, or a late-answered request is back-dated.
- A doc arrives after the deal already advanced (weekend drop adds papers to existing deals). The engine cannot rewrite earlier `stage_log` entries.

**How to avoid:**
- Stage exit = (required docs present) AND (no open MISMATCH or MISSING that blocks) AND (human gate answered with approve). Evaluate in that order and log the reason in `why`.
- While blocked: send `info_request` to `"borrower"`, keep alert timers running (alerts must say what is awaited and what unblocks it), and **do not send `credit_decision` until the file is complete**. Sending a decision on an incomplete file is the same sin as advancing.
- The stage log is append-only. New papers after the fact add an entry and may reopen the deal if it has not reached Closed (a correction that changes the amount re-routes the approver). If a deal is already Closed, record a late finding and a fraud hold request, and do not pretend to undo.
- Idempotency: key alerts, requests and issues by (deal, stage, kind). Re-running on the same input gives byte-identical output.

**Warning signs:** `exited_at` before the arrival of the last required doc. Tyler leaves Credit before the weekend drop.

**Phase to address:** P3.

---

### Pitfall 12: Wrong approver at the $250,000 boundary (and an ambiguous amount)

**What goes wrong:** `stages.json` says delegated max 249,999.99, while `teams.json` says "< 250,000 delegated, >= 250,000 chair". Float parsing or a `>` instead of `>=` sends exactly $250,000 to Priscilla. Bluebonnet is exactly $250,000.00 on the app and $205,000.00 on the letter.

**Evidence:** In history, H-2603-017 at exactly $250,000 has a Committee SLA of 48 h (chair route), confirming `>=`. Committee SLA is **24 h delegated, 48 h chair**, so alert, 150% and 200% thresholds also differ by route (24/36/48 vs 48/72/96).

**How to avoid:**
- Money as integer cents. Route: `cents >= 25_000_000` -> harold.benson, else priscilla.nguyen.
- With an unresolved `MISMATCH:amount_requested` (Bluebonnet), do not route or send a committee request on either amount. Hold, request clarification, and route once resolved. Re-route if a correction changes the side of the line.
- The three ring deals ($246,000, $247,500, $248,000) all route to the delegated approver. This is part of the trick. It is not a reason to change the rule.
- SLA clock per stage uses the route-specific value.

**Warning signs:** Bluebonnet's `committee_approval` goes to priscilla.nguyen. Any Committee alert at 100% for a chair-route deal fires at 24 h.

**Phase to address:** P3.

---

### Pitfall 13: OOO backup routing and time-dependent contacts

**What goes wrong:**
- Dana Whitfield's only assigned deal is Priya's Bakery. Dana is out 2026-11-03 08:00 through 2026-11-06 18:00. Priya's files land 11-03 08:46 to 09:05, so the Credit request must go to **marcus.lee**. The OOO window is stored only as free text in `notes`.
- Alerts must also go to the effective owner (marcus), not dana.
- The hidden `teams.json` likely has different OOO people (approvers, RMs, fraud analysts).
- Marcus is also assigned seven other deals. Backup of a backup (aisha.grant) is needed if he is out.

**How to avoid:**
- Parse `OUT OF OFFICE <start> through <end>` with a regex into structured windows, in the sim timezone. Evaluate at the request time `at`, not once globally. If the note says OOO but does not parse, treat that person as OOO for the whole run and log a warning.
- Effective owner = person, else `backup`, else backup's `backup`. Use it for requests, alerts and the escalation chain.
- Fraud: victor.hale, backup monica.salas. Funding: tasha.reed, backup kevin.alvarez. RMs: brian.foster / elena.ruiz are each other's backups. Intake is round-robin olivia.chen / jordan.webb (no assignment list exists, so make it deterministic by arrival order).

**Warning signs:** Any request or alert `to` = dana.whitfield on 11-03 onward.

**Phase to address:** P3.

---

### Pitfall 14: SLA clock semantics (wall-clock, thresholds, spam, horizon)

**What goes wrong:**
- `contacts/teams.json` mentions Mon-Fri 08:00-18:00 hours. SLA is wall-clock: in `history/stage_events.csv`, `hours_in_stage` equals the timestamp difference exactly (max diff 0.0) and stages enter and exit at night and on weekends. Applying business-hour math under-alerts.
- Alert threshold semantics: in history, `breached` means hours > SLA, `escalated` is true exactly when ratio >= 1.5 (min escalated 1.51, max non-escalated 1.48), and every ratio >= 2.0 is escalated.
- Ticks that round alerts to the hour, repeated alerts every tick, and second escalation to `lauren.kim` when the escalator already is lauren (Product, Committed, Closed): still send it, once.
- Horizon: a Credit stage entered Tue 09:30 has its 200% mark at Sat 09:30, after the sim week ends (Fri 18:00). Engines that stop at Friday never emit it.

**How to avoid:**
- Event-driven timeline: schedule alert at `entered + 1.0 x SLA`, escalation at `1.5 x`, second at `2.0 x`, each at the exact instant, each exactly once per (deal, stage).
- Alerts only go "to owner (and RM)"; escalation to the owner's `escalates_to`; second to lauren.kim. Messages must name borrower plus RM, stage, elapsed hours, what it waits on, and what unblocks it. Use templates, validated by a checker.
- Make the run horizon a parameter and run to quiescence (all deals terminal or blocked), not to Friday 18:00. Business hours affect only when humans answer, not when the clock runs.

**Warning signs:** An alert timestamp that is not a clean multiple of SLA from stage entry. Two identical alerts for one (deal, stage).

**Phase to address:** P3.

---

### Pitfall 15: Unanswered human requests, deadlines, and the "needed_by" path

**What goes wrong:**
- Judges answer as the humans: some fast, some OOO, some never. A system that waits silently scores nothing on "escalating unanswered requests".
- Priya needs funds by Fri 15:00 CT. Summing stage SLAs (8+48+24+16+48+24 = 168 h) is far more than her 78 h window (Tue 09:05 to Fri 15:00). History shows the same borrower was funded in 2 days last time, so the whole pipeline must run at human-response speed, not at SLA speed.
- `needed_by` parsing: "No specific date" on 12 of 13 deals must give `null` (do not invent a date, do not emit the string). Priya's "Friday 2026-11-06 by 3:00 PM (payroll)" -> `2026-11-06T15:00-06:00` (ISO date present, so ignore the weekday word). Hidden-set phrases like "end of month", "ASAP" and "next Tuesday" need deterministic handling relative to the application date. Never guess; use `null`.

**How to avoid:**
- Treat an unanswered request as part of the stage timer: it escalates through the same 100/150/200% ladder, and on the escalation you re-address the request to the escalation target (log a new `human_requests` entry).
- Priority queue: deals with `needed_by` get their requests first and their credit memo and Committee package prepared in advance. Add a deadline-risk alert (level `alert`) when time-to-deadline is shorter than the remaining stages' minimum plausible time. Keep the message distinct from SLA alerts.
- Cut the human-response gap: pre-draft each next request so it goes out in the same tick as the previous answer.

**Warning signs:** Priya's `funding_release` request goes out after Thu 18:00. No request on an unanswered gate gets re-sent.

**Phase to address:** P3, P6 (demo shows the Priya path).

---

### Pitfall 16: Time zones and timestamps

**What goes wrong:**
- Aware vs naive datetimes raise `TypeError` in sorts.
- Using `zoneinfo("America/Chicago")`: real Chicago was UTC-5 (CDT) until 2026-11-01, but the data and PDF timestamps are labeled `-06:00` all year, including history from July. Converting would shift apparent times by an hour and misorder evidence against `arrive_at`.
- ISO strings written without the offset, or with seconds when the examples have none, may fail a strict parser.

**How to avoid:** One fixed `timezone(timedelta(hours=-6))`, exactly as `clock.py` does. Parse every timestamp into it. Emit `YYYY-MM-DDTHH:MM-06:00`. PDF `CreationDate` is a weak signal anyway (below), never a clock.

**Warning signs:** Any timestamp with `-05:00`. Sorting errors on mixed types.

**Phase to address:** P0.

---

### Pitfall 17: Determinism leaks

**What goes wrong:** `os.listdir` order, set and dict iteration of strings (PYTHONHASHSEED), graph cluster tie-breaking, `datetime.now()`, floats, uuid4, pandas sort stability, and any LLM text on the scored path. Two runs of the same input give different JSON, so a flag appears or disappears between your self-score and the judge's run.

**How to avoid:** Sort everything with explicit keys. Set `PYTHONHASHSEED=0`. Use Decimal or integer cents. Derive IDs from content. No wall-clock calls in the engine (inject the sim clock). Add a CI-style test: run twice, compare file hashes. Gate Nemotron behind a flag, and make the scored output identical with the flag off.

**Warning signs:** `diff` of two successive output files is not empty.

**Phase to address:** P0 (harness), checked in every phase.

---

### Pitfall 18: False fraud flags on strange-but-real borrowers (the expensive error)

**What goes wrong, with concrete cases from the data:**

| Borrower | Naive signal that false-fires | Why it is actually fine |
|---|---|---|
| Tyler | "#" in `1600 N Collins Blvd #210` read as a mailbox store (`SHELL_ADDRESS`); Adobe PDF Library producer; self-prepared; CSV statements; Form 7004; 6 employees vs $150K ask; JPG ID | `#210` is a suite. Adobe is the second most common history producer (43 deals). Self-prepared is 28 history deals. Statements reconcile. |
| Okafor (James) | 2/3 deposits are round hundreds; Aug deposits only Mon/Thu; huge amounts; foreign contracts | 3-5 wires a month. History's own Okafor deal (H-2601-006) shows 0.54-0.84 round pct with 3-5 deposits. A deposit-pattern signal without a minimum count and size-conditioned baseline fires here. |
| Westfield | New vendor and remit account not in history; Commerce Street address; First Lakes Bank; preparer Owen Price shares a surname with ring guarantor Devon Price | "New" is not "rare among bad". Its address is a different suite in the agent's building. First Lakes Bank has 37 history deals. |
| Harbor Tea | Business address equals the registered agent's office; address shared by 15 history deals; Northstar agent (27 history deals) | 14 of the 15 are not fraud. One is H-2603-020 (REV_INFLATION) and one is H-2603-004 (declined, Commerce Street agent), so even that hub is mixed. It is also the one deal whose address is a legitimate "hub". |
| Garza, Priya, Okafor | Same EIN, DL, DOB, guarantor and address as a history deal | They are returning customers. DUP_EIN fires only for the same EIN with a **different** legal name. |
| Bluebonnet | Name token overlaps `Bluebonnet Ramirez Cafe` (a DUP_EIN fraud victim in history); amount exactly $250,000 | Name-token similarity is not identity. Amount at the boundary is not structuring. |
| Granite Bay, Bluebonnet, Priya | Same preparer Rosa Benavides (59 history deals) | Ubiquitous preparer. Do not link Bluebonnet or Priya to Granite Bay's real old-trick fraud. |
| Garza, Oakline, Okafor | PDF `CreationDate` earlier than the statement period end (Oct statement "created" 10-29 or 10-30, period ends 10-31) | Same artifact in the ring and the legit deals, so it separates nothing. Do not use it. |

**How to avoid:**
- Principle: a shared entity counts only if it links >=2 distinct deals (current or history). "Unseen in history" with a single deal is zero evidence.
- Weight every shared entity by rarity (inverse document frequency) and by history outcome, and skip entities that are ubiquitous.
- Require agreement of >=2 independent signal families (identity, document forensics, financial behavior, vendor/payee) before a hold request. One weak signal produces at most an internal "watch" with no `flagged: true`.
- Add a **zero-false-flag regression**: run the detector over all 13 current folders and the 257 history rows. Required result: ring flagged, no legit deal flagged, including H-2511-010 and H-2601-022 (DocuForge, repaid), the 15 Berkshire deals, and the 24 "Metroplex Equipment Supply, Inc." deals.
- Do not use `fraud_label=none` as "clean": the README warns that it means "no known trick found".

**Warning signs:** Any of Tyler, Okafor, Westfield, Harbor Tea, Garza, Priya, Oakline or Bluebonnet gets `flagged: true`. `history_flags` contains anything other than ring members.

**Phase to address:** P4 (regression gate), P7.

---

### Pitfall 19: Overfitting to the sample literals, or to the sample's single trick

**What goes wrong:** The hidden set has a different trick. Rules that read `DocuForge`, `Delacroix`, `4471`, `Commerce Street` or "Mon/Thu" score zero there. The opposite failure is a detector so generic it only fires on string rarity and never explains itself.

**What the sample ring shares (all generic, none a literal to code):**
- Same preparer firm, phone and PTIN (K. Delacroix, 214-555-0187, P01874422) in all three plus two history deals. History's biggest preparer has 71 deals; this one has 2 before the ring.
- Same registered agent (Commerce Street, 5 history uses of which 2 are the ring's relatives).
- Same vendor name and remit account, a lookalike (`Metroplex Equipment Supply LLC` ...4471 vs the real `..., Inc.` ...9902 with 24 history deals). Detect lookalikes by normalized-name similarity against a known vendor **plus** a different account.
- Every PDF, including bank statements, has producer `DocuForge 2.1 (Windows)` and creator `DocuForge Templates`. Genuine statements everywhere else are `FIS Statement Services 9.2`. The generic signal is "the bank statement was not produced by the bank's statement system, and producer is uniform across all docs of the deal".
- Deposits: 100% round hundreds (8/8, 9/9), only Mon/Thu, 8-9 per month, balances ending in .00 or .50, near-linear monthly growth. The history baseline median is about 8% round.
- Duplicated financial content: Pecan and Ridgeway have **identical** FY2025 P&L lines ($470,400 revenue, $244,608 COGS, $84,672 net). Summit's differ only by a scale factor.
- Near-sequential guarantor DL numbers: 41872219, 41872231, 41872246 (and history H-2608-002 41872188, H-2609-008 41872203). Guarantor DLs issued 2025 shortly before formation while everyone else shows 2021-04-11.
- Young LLCs (2025 formation), equipment loans at $246,000-$248,000 just under the $250K line, all First Lakes Bank.

**How to avoid:**
- Build features as families: identity-sharing (preparer, phone, agent, address, DL proximity, guarantor), template and metadata forensics (producer uniformity, producer vs expected issuer), financial behavior (round-number share, weekday concentration, cents-less balances), payee (vendor lookalike plus account), and cross-deal duplication (identical numbers across deals).
- Treat every literal above as a test fixture, not a rule. The red-team generator (P5) should invent tricks outside these families (shared phone numbers, address clusters, duplicated EIN digits, reused signature, shared bank account across borrowers), and the detector's coverage is reported honestly, noting the circularity of a Nemotron-written test set.
- Explainability: every flag lists its signals, entities, and history matches.

**Warning signs:** The string "DocuForge" or "Delacroix" appears in detection code. A synthetic variant of the ring (change producer, preparer and account) goes undetected, and no other family fires.

**Phase to address:** P4, P5 (red-team eval).

---

### Pitfall 20: Single weak signals and threshold calibration with tiny positives

**What goes wrong:**
- DocuForge alone: also on H-2511-010 (Young Scott Labs, $792,000, `paid_off`) and H-2601-022 (Oak Cliff Kitchen, $15,000, current). Commerce Street agent alone: also on H-2602-005 (REV_INFLATION fraud), H-2603-004 (declined), H-2604-007 (funded, current). 5950 Berkshire address alone: 15 deals.
- There are only 2 positive history deals for the new trick (plus 3 current), and 12 for old tricks. You cannot fit a threshold; any fitted value just memorizes the sample.
- A round-share threshold chosen from the sample (say 0.5) false-fires on large-ticket businesses (history rows with 3-5 deposits and 0.5-0.85 round).

**How to avoid:**
- Use principled, documented thresholds, not fitted ones: a binomial or Wilson test on "k of n deposits are round" with n >= 6 and a baseline conditioned on deposit size; a log-rarity budget per family; and >=2 families.
- The deposit signal must be consistent across months (6 of 6 months for the ring; Okafor fails this).
- Report all signals for every deal on a dashboard, so you can see near-misses (Okafor, Westfield, Harbor Tea) and prove they were considered and declined.
- Use history outcomes only as a tie-breaker (13 deals 30 days past due, 3 charged off), not as a classifier.

**Warning signs:** The threshold has a three-decimal value you found by looking at the sample.

**Phase to address:** P4.

---

### Pitfall 21: Flag timing and the first-deal problem

**What goes wrong:** FRAUD pays more for earlier holds and for "spotting the pattern in the first few deals". The ring's first member, Ridgeway, is the **4th deal to land** (Garza 09:21, Tyler 10:06, Oakline 11:41, Ridgeway 13:51 on Mon 11/02), well before Pecan (Tue 11:11) and Summit (Wed 10:26). A cross-current-deal detector cannot fire on Ridgeway. If you wait for the cluster, Ridgeway is flagged on Tuesday or Wednesday, and Wednesday is late. If you flag too eagerly, you risk false flags.

**How to avoid:**
- Ridgeway must be flagged on its own against **history**: it shares preparer, phone, PTIN, agent, vendor lookalike plus account 4471, and producer with H-2608-002 (30 days past due) and H-2609-008, and its statements show the deposit anomaly. That is >=3 families at Intake time (last doc 14:10 Mon).
- Flag at the first moment >=2 independent families agree, which for Ridgeway is when its last required doc has arrived. The vendor quote arrives with the packet (14:04), so do not wait for the Product stage to look at remit accounts.
- Retroactive linking: when Pecan and Summit land, they link to Ridgeway, and Ridgeway's `linked_deals` must be updated (final JSON is written at the end, so make linking symmetric). `flagged_at` for each deal stays at its own earliest defensible time.
- Send the `fraud_hold` request to victor.hale (backup monica.salas) immediately. If it is unanswered, escalate the same way as any request. A flagged deal must never enter Closed. Do not start working it past the stage unless a human releases it (`fraud_release`).

**Warning signs:** `flagged_at` for Ridgeway is later than 14:10 Mon, or `stage_at_flag` is later than Intake/Credit.

**Phase to address:** P4, P3 (hold semantics).

---

### Pitfall 22: History linking precision (`linked_deals`, `history_flags`)

**What goes wrong:** Flagging all history deals that share any entity with the ring. That would include H-2511-010 and H-2601-022 (DocuForge only), H-2602-005, H-2603-004, H-2604-007 (Commerce Street only), and every Hartwell or Benavides client. "Find the rest" is scored, and false flags cost.

**How to avoid:** History member = shares >=2 independent families with the cluster. On the sample, exactly H-2608-002 (Trinity Bend Plumbing) and H-2609-008 (Mesquite Ridge Signs): same preparer, phone, vendor, account, agent, producer, DL-number block, and 100% round Mon/Thu deposits for six months. Do not put returning customers (H-2511-002, H-2512-005, H-2601-006) in `history_flags`. Also output evidence per link. `linked_deals` for the three ring folders = the other two ring folders plus the two history IDs.

**Warning signs:** `history_flags` length > 2 on the sample.

**Phase to address:** P4.

---

### Pitfall 23: Nemotron nondeterminism, hallucination and latency on the scored path

**What goes wrong:**
- Nano-class models emit a reasoning trace before the answer. If `max_tokens` is consumed by reasoning, `content` can come back empty. Temperature 0 is not bit-reproducible on a hosted endpoint, and a seed may not be honored. (LOW: from general vendor behavior and discussion threads, not verified against the live endpoint. Check on day one.)
- Hallucinated extractions: wrong EIN digits, wrong amounts, invented fields, particularly from the VL read of the JPG.
- Tool calling: the hosted 9B may emit malformed JSON, parallel or unknown tool calls. Open vLLM work around its tool parser suggests this is a rough edge (LOW).
- Trial-tier rate limits and cold-start latency during live judging. The $60 Brev credit is finite.
- Prompt injection: borrower PDFs are untrusted text. None of the 173 sample files contain instruction-like strings (I searched), but the hidden set might.
- The investigator agent's tools can read the future (Pitfall 1).
- The red-team generator is circular: the detector is tuned against tricks the same ecosystem invented.

**How to avoid:**
- Nemotron never writes to a scored field. Extraction, issues, stage logs, routing, alerts, holds and links are pure Python. The submission must be byte-identical with `NEMOTRON=off`.
- Per-call wrappers: timeout, bounded retry, JSON-schema validation, disk cache keyed by hash(prompt) plus a record-and-replay mode so the demo and the judges' run do not depend on live API health.
- Validate any LLM output (VL extraction or message text) against the deterministic facts (names, amounts, hours) and drop it if inconsistent. Messages that carry scored alerts use deterministic templates.
- Bounded ReAct loop (max steps), read-only tools, sim-time gated, no tool that can place or release a hold.
- Spike on day one: confirm the model IDs available on the key (text and VL), measure latency and RPM, and check the reasoning toggle. Do not design around unverified limits.
- The agent writes an evidence case. It cannot raise or lower the hold decision.

**Warning signs:** Different output with the cache cleared. An agent trace that cites a deal not yet arrived.

**Phase to address:** P5 (and P0 for the on/off flag and the wrapper).

---

### Pitfall 24: Environment traps on this machine

**What goes wrong:** Plain `python` is the Microsoft Store stub. Windows console encoding (cp1252) crashes on the em dashes, middle dots and arrows in the PDFs and history text. No `networkx`, `rapidfuzz`, OCR or `openai` package is installed. Data lives under `data/` (gitignored) so a clean checkout has no data. Running scripts inside the data folder lets a stray module shadow the stdlib.

**How to avoid:** Use `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe` with `-I` for anything touching the data. Set `PYTHONUTF8=1` and write files with explicit `encoding="utf-8"`. Install and pin deps in P0, and test from a clean venv. Make the CLI take data paths. Rehearse a clean-checkout run with the data pointed in from outside the repo.

**Warning signs:** `UnicodeEncodeError` when printing a doc. `ModuleNotFoundError` on the demo laptop.

**Phase to address:** P0, P6.

---

### Pitfall 25: Output-format traps that cost points quietly

**What goes wrong:**
- Inventing `issues` strings outside the allowed grammar (for example `MISMATCH:vendor`, or `OLD_TRICK:SHARED_PREPARER`). The ring is not on the old-trick list. Fraud evidence goes into `fraud.reason`.
- Putting `"No specific date"` or a free string in `needed_by`.
- `purpose_category` from keywords. "Hardware kits" (Tyler) hits "inventory"; Priya's product is `Working Capital Loan` but her purpose is `payroll`.
- A held deal that keeps getting stage log entries after the hold.
- `human_requests.answer` filled in by your own scripted responder in the final file for the judge's run. Keep the scripted personas out of the submission, or label them clearly.

**How to avoid:**
- Purpose mapping uses the closed set and the history product-to-purpose prior (Equipment->equipment; Revolving->inventory or working_capital; Term->expansion, payroll or refinance; Working Capital->working_capital or payroll). By deal: Garza and Granite Bay inventory; Okafor working_capital (history H-2601-006 says so); Priya payroll (H-2512-005 says so); Harbor Tea expansion; Tyler is ambiguous (expansion most likely, LOW).
- `issues` come only from an enum builder, never from f-strings of free text.
- Final validator (Pitfall 2) in CI.

**Warning signs:** `issues` contains something the validator rejects.

**Phase to address:** P1, P2, P7.

---

## Moderate Pitfalls

### Pitfall 26: guarantor_name when app and ID differ

**What goes wrong:** Oakline: app "Bob Kline", ID, certificate organizer and request letter "Robert Allen Kline". It is unknown which one the grader expects in `extracted.guarantor_name`.
**Prevention:** Use the application value as primary (the field is "as applied"), keep the ID name as `guarantor_name_on_id` in an extra key, and never emit a mismatch for a nickname. Mark it in the oracle as unresolved (LOW).

### Pitfall 27: Weekend-drop handling

**What goes wrong:** New folders keyed by an existing name (a returning borrower) merge into the old deal. A full snapshot re-drops old files. A Collections notice names a guarantor or EIN, not a folder. Corrections change the facts.
**Prevention:** Key documents by (path, hash). Link by EIN/name/guarantor. A correction supersedes an older value, is logged, and re-runs the checks (it can clear a `MISMATCH`, never silently). Rerun on the new drop must not need a code change; use a fixture drop with a corrected app and a late statement.

### Pitfall 28: Misusing PDF metadata

**What goes wrong:** `ModDate` equals `CreationDate` on every file (no edit signal). `CreationDate` precedes the signature date on legit and ring deals alike (Garza, Oakline and Okafor Oct statements are "created" before October ended). Producer alone is weak (Pitfall 20).
**Prevention:** Use producer and creator only as one family member, never creation-date logic.

### Pitfall 29: Mixed owners for stage alerts

**What goes wrong:** Alerts go to the wrong person: Intake alerts to a manager, Product to the specialist's own escalation target, Committee to the wrong route.
**Prevention:** Table-drive from `teams.json` and `stages.json`. Committee owner = route-specific approver. Credit owner = effective credit officer. Unit-test a chain per stage.

### Pitfall 30: Using history data beyond its limits

**What goes wrong:** `monthly_deposits.csv` has summaries only (no transactions), so STMT_TAMPER and ID_MISMATCH cannot be validated on history. `repayment_status` is as of 2026-10-31.
**Prevention:** Validate REV_INFLATION (clean 1.5x separation), DUP_EIN, SHELL_ADDRESS (PMB regex, 2 labeled deals) on history. Validate STMT_TAMPER on Granite Bay and Oakline only, and treat these as fixtures.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hard-coding the ring literals | Fast 100% on the sample | Zero on the hidden set; reads as overfitting to judges | Never in detection; fine in tests |
| Filename-based doc typing | Works on tidy folders | Breaks on SCAN_*, "loan app FINAL", the weekend drop | Never |
| Float money | Less code | Boundary and tolerance bugs at $250,000 | Never |
| One big pass over all files | Simple | Leaks the future, wrong `flagged_at` | Never |
| LLM text in scored alerts | Nicer wording | Nondeterminism, hallucinated numbers | Only as an optional display layer |
| Skipping the validator | Saves 30 minutes | A schema error voids a run | Never |
| UI-first | Demo looks good | Goldman score is priority 1 | Only after the engine passes the oracle |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `sim/clock.py` | Using `sync` and expecting overwrites; `set` refuses to go backwards without `--force`; state file persists | Read `arrivals.jsonl` directly via your own gated layer; `reset` before every run; pass `--arrivals/--folder` for the drop |
| NVIDIA hosted API | Assuming limits and model IDs; unbounded waits | Day-one spike; timeout, retry, cache, replay; flag to disable |
| Nemotron VL | Trusting its single read | Two agreeing reads before a score impact |
| `teams.json` notes | Reading OOO as prose | Regex into windows, evaluate per request time |
| Cloud demo | Live dependency on API or network | Pre-recorded run plus local replay |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Re-parsing every PDF on every tick | Minutes per run | Parse each file once at its arrival, cache by hash | Hidden set with more deals |
| O(n^2) graph over 257 history x deals | Slow replay | Index entities by value | Larger hidden history |
| Per-tick LLM calls | Rate limits, long runs | Call only on flagged clusters, cached | Live judging |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Feeding raw doc text to an LLM that can act | Prompt injection changes a decision | LLM output is advisory only, tools are read-only, no hold or release tool |
| Printing or committing the NVIDIA key or the data pack | Key leak; challenge statement is participant-only | `.env` gitignored; `data/` gitignored; scrub logs |
| Logging SSN last 4 and DOB into the UI | PII on a projector | Mask in the demo (data is fictional, but show good habits) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Fraud graph shows only the final state | Judges miss the "spotted early" story | Time scrubber: ring lights up as each deal lands, with the evidence per edge |
| Alerts without who/what/how long | Fails the rubric's alert-must-say list | Template with all four fields, validated |
| UI blocks on human answers | Headless judge run hangs | Non-blocking inbox plus scripted responder personas |
| Showing near-miss deals as fraud | Looks like false flags | Show Okafor, Westfield and Harbor Tea as "considered, cleared" with reasons |

## "Looks Done But Isn't" Checklist

- [ ] **Sim clock:** output unchanged when future files are deleted (Pitfall 1).
- [ ] **READ:** Garza, Priya, Okafor, Harbor Tea, Tyler show no false MISMATCH/MISSING; Westfield EIN and Bluebonnet amount are caught.
- [ ] **Statements:** Oakline gets MISSING_PAGE (not tamper); Granite Bay gets STMT_TAMPER; Tyler gets MISSING_DOC for June only.
- [ ] **Routing:** Bluebonnet is held on the amount mismatch; Priya's credit request goes to marcus.lee; Harbor Tea, Granite Bay and Okafor go to harold.benson; the ring goes to priscilla.nguyen.
- [ ] **Fraud:** ring flagged at Intake or Credit, Ridgeway on Monday; `history_flags` = exactly H-2608-002 and H-2609-008; zero legit deals flagged.
- [ ] **Alerts:** exact 100/150/200% instants, once each, to the effective owner, full message.
- [ ] **Unanswered requests:** a never-answers persona produces re-addressed requests and escalations.
- [ ] **Determinism:** two runs give identical bytes, also with Nemotron off.
- [ ] **Validator:** passes on the sample and on a synthetic drop with an unknown doc type.
- [ ] **Clean checkout:** runs from a new venv with data pointed in.

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1 Future leakage | P0 | Metamorphic delete-future test |
| 2 Crash on hidden set | P0, P7 | Fuzz drop, validator |
| 3 Doc classification | P1 | Fixture per doc type including 7004 and SCAN_* |
| 4, 5 Statement parsing and tamper | P1, P2 | Oakline, Tyler, Granite fixtures |
| 6, 7 Months and revenue | P2 | Tyler 5-month annualization, ring revenue not mismatched |
| 8, 9 Mismatch, ID, JPG | P1, P2 | Westfield, Bluebonnet, Oakline, Tyler fixtures |
| 10, 11 Missing docs and advancing | P2, P3 | Gate tests per stage |
| 12, 13, 14, 15 Routing, OOO, SLA, deadlines | P3 | Table-driven tests, Priya path |
| 16, 17 Time zone, determinism | P0 | Hash-compare runs |
| 18-22 Fraud | P4 | Zero-false-flag regression over 270 deals |
| 23 Nemotron | P5 | NEMOTRON=off identical output |
| 24 Environment | P0 | Clean venv run |
| 25 Format | P1, P2, P7 | Validator in CI |

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| P0 Foundations | Reading the folder directly | Gated data layer first, before any parser |
| P1 Ingest | Keyword typing, pypdf column loss, no OCR for JPG | Anchor-phrase classifier, balance-delta direction, install OCR now |
| P2 Issues | False MISMATCH/STMT_TAMPER, revenue on young firms | Valid-check-only emission; like-for-like comparisons |
| P3 Pipeline | Advancing on gaps, wrong approver at 250K, OOO text | Cents arithmetic; OOO regex; exit gate order |
| P4 Fraud | One weak signal, tiny-n deposit stats, first-deal timing | >=2 families, binomial with min n, history-based first flag |
| P5 Nemotron | Scored-path dependence, future-reading tools, circular red team | Flag off identical, sim-gated tools, honest coverage report |
| P6 UI/Demo | Live API dependence, no data on demo machine | Replay mode, rehearsed clean run, cut UI before engine |
| P7 Hardening | Unseen doc shapes in the weekend drop and hidden set | Fuzz drops, never-crash wrappers, oracle self-score |

## Open decisions to take early (ambiguities the data cannot resolve)

1. Tyler `annual_revenue_stated`: midpoint $450,000 (recommended) vs `null`.
2. Oakline `guarantor_name`: application "Bob Kline" (recommended) vs ID "Robert Allen Kline".
3. Whether `MISSING_DOC:equipment_quote` should be reported at Intake or only when Product is reached. Recommendation: report in the final `issues` either way, and hold at Product.
4. Whether to send a `credit_decision` request on an incomplete file. Recommendation: no, send `info_request` to the borrower and hold.
5. Whether Granite Bay (old tricks) is a fraud flag as well as two OLD_TRICK issues. The bank's rule says old-trick deals go straight to Fraud Operations, so yes.

## Sources

- `data/participant/README.md`, `SCHEMA.md`, `SUBMISSION_FORMAT.md`, `rules/stages.json`, `rules/known_fraud_checks.md`, `contacts/teams.json`, `sim/clock.py`, `sim/arrivals.jsonl`, `sim/assignments.json` (HIGH, primary)
- `shared_folder/*` (all 13 borrower folders: 140 PDFs, 5 CSVs, 1 JPG), parsed with pypdf and Pillow (HIGH, primary)
- `history/deals.csv`, `monthly_deposits.csv`, `stage_events.csv` (HIGH, primary; computed statistics quoted above)
- NVIDIA model and API behavior: [build.nvidia.com Nemotron Nano 9B v2 listing](https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2), [vLLM recipe for NVIDIA-Nemotron-Nano-9B-v2](https://recipes.vllm.ai/nvidia/NVIDIA-Nemotron-Nano-9B-v2), [HF discussion #37 on the tool parser](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2/discussions/37). Rate limits and reasoning-toggle details were not found in the sources (LOW; verify with a live call).
- Grader behavior for ambiguous cases is inferred, not published (MEDIUM/LOW).

---
*Pitfalls research for: DealPilot (HackUTD 2026, Goldman + NVIDIA tracks)*
*Researched: 2026-11-07*
