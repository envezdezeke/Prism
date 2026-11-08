# Trick menu: review sheet (for Jesse)

> Companion to `eval/trick_menu.yaml`. Owner: Jesse. Status: **draft, waiting for your sign-off**.
> The menu must be committed **before** Zeke's first synthetic calibration run (MODEL_DESIGN M15/M16).

## What this is

A list of 8 ways a fraudster could try to get a loan through, each at three strengths (weak, medium, strong), plus honest borrowers who *look* similar ("twins"). We generate fake deals from it and check two things:

- **Catch rate:** how many fake deals get held before money goes out.
- **False-flag rate:** how many honest twins get held. This is the number that matters most. A good deal must never be blocked.

A **hold** needs the "shared rare party" signal (F1) **plus two more** of: new or bursting party (F2), lookalike vendor (F3), odd document software (F4), manufactured-looking deposits (F5). A **watch** is "one or two signs": shown on screen, not held. Terms like "just under the approval limit" (F6) are supporting evidence only and never count toward a hold.

Today only F1, F3 and F5 are built, so for now a hold needs all three. The YAML gives each expected result twice: for the finished design and for today's build.

## The menu

| # | Family | How the fraud works | What should catch it | Expected (weak / med / strong) | Twin and why it's honest |
|---|---|---|---|---|---|
| T1 | Shared-kit ring *(like the sample; control only)* | One organiser builds several "unrelated" borrowers with the same preparer, call-back phone, payout account and fake-looking deposits | F1 + F5 + F4 + F2 (+F3 if equipment) | watch / hold / hold | **Family bookkeeper:** siblings' businesses share a long-time bookkeeper with a clean repaid record (watch at most). **Big-firm preparer:** franchisees use a large accounting firm on many past deals, so nothing is rare (clear) |
| T2 | Vendor lookalike / payout swap | Equipment quote names a copy of a known dealer ("Inc" for "LLC", one letter off) or the real dealer with a new bank account. The loan pays the fraudster | F3, plus F1 when two deals share the fake account | watch / hold / hold | **Busy month at a big dealer:** four borrowers, the usual dealer name and account (clear). **Genuine sister dealer:** a real dealer with a similar name and its own repaid history (watch: we send a verification request, no hold) |
| T3 | Statement mill, nothing shared | Applicants buy fake statements from the same source: round deposits on the same two weekdays. Every name and number is different | F5 only | watch / watch / watch **(blind spot)** | **Cash business:** a laundromat really does deposit rounded cash twice a week (watch). **PDF software update:** five honest packets carry a brand-new version string (should be watch, **at risk of a false hold**, see decision 4) |
| T4 | Recycled guarantor | One identity guarantees several new, unrelated businesses. Careful versions respell the name (Bob vs Robert, middle initial) but keep the same birth date, SSN and licence | F1 (guarantor name) + F2 + F4 + F5 | clear **(blind spot)** / watch / hold | **Serial entrepreneur:** an owner guaranteeing her third business, the first two repaid (watch). **Two people, one common name:** different birth dates and SSNs (clear) |
| T5 | Bust-out | A clean returning borrower suddenly asks for 2.5x to 6x more. Revenue is inflated but kept under the bank's 1.5x check, and the last two months of deposits are pumped. Plan: take the money and default | F5 at most | watch / watch / watch **(blind spot)** | **Honest growth:** a returning customer asks for twice as much, with revenue matching deposits (should be clear; today it lands on watch, see decision 3) |
| T6 | Shell burst, shared agent | A batch of brand-new LLCs, all registered through one small, obscure agent, with loan sizes just under the committee limit | F1 (agent) + F2 + F4 + F5 | watch / hold / hold | **National agent service:** honest new LLCs using a big agent service seen on many deals (clear). **Small-town law firm:** agent for two related local businesses with repaid history (watch) |
| T7 | Velocity, shared contact | A burst of applications within days. Each has a different preparer, but they share the call-back phone and street address | F1 (phone, address) + F2 + F4 + F5 | watch / hold / hold | **Franchise week:** five franchisees apply through the franchisor's accounting firm, whose main line appears on many deals (clear). **Shared office building:** three unrelated tenants of one building (watch) |
| T8 | Paper revenue inflation *(old check)* | Stated revenue far above what the statements show. This tests the bank's existing check, and where it stops working | Bank's known-fraud check (straight to Fraud Ops) | clear **(blind spot, 1.4x)** / held / held | **Seasonal business:** full-year revenue against winter statements, 1.3x to 1.45x (clear). **One-off asset sale:** one large deposit in one month (clear) |

Counts: 20 fake cases per family per strength and 30 cases per twin, each with a fixed seed. That's about 900 cases, and the same file always gives the same cases.

## Decisions for Jesse

1. **Set strengths relative to the bank's own history, not as fixed dollar or percent values.** "Strong" round-number deposits means "rounder than 97% of good history deals", worked out from whatever history ships. **Recommend: yes.** It carries over to the hidden set, and no confidential numbers go into the file.
2. **Keep the blind-spot cells in the report.** These are T3, T4-weak, T5 and T8-weak. **Recommend: keep them all and show them in the pitch** ("here is what it can't catch, and why"). Don't count them in the 70% catch target, and never patch them with special cases. This honesty is part of the pitch.
3. **Returning customers link to their own past loan.** A borrower's earlier deal shares its preparer and guarantor, which are rare, so the "shared rare party" signal fires on every returning customer. On its own that's only a watch, but it adds noise and one step toward a false hold. **Recommend: ask Zeke for one generic fix.** Two deals with the same EIN *and* the same legal name are the same customer, not a ring, so don't count that link. This is not a sample-specific rule.
4. **The PDF tool counts as a "party".** Today the software that made the PDF counts as a shared entity for F1. When a popular tool ships a new version, honest packets can trigger F1 + F2 + F4 together and get **held** (twin T3-B2). **Recommend: remove the PDF tool from F1.** It's a tool, not a person. Keep it for F4 and for linking past deals. Second-best: strip version numbers before comparing.
5. **What counts as a false flag on a twin.** **Recommend:** only a hold counts (target 5% or less, per M6). Report watches separately as "friction", and count separately any watch that sends a vendor-verification request to an honest borrower. Today's twins expect watch in 7 of 15 cases, so friction will be visible, and that's fine.

## Known blind spots

The design deliberately bets that the hidden trick is still a cross-deal ring (MODEL_DESIGN M2). So any fraud that shares no rare party across deals can reach "watch" but never "hold". That covers four cells: a statement mill where every applicant uses different names and numbers (T3); a recycled identity whose name is respelled, because the engine matches guarantors by name and doesn't index birth date, SSN or licence (T4 weak); a bust-out by a single returning customer, because no rule compares a borrower with its own history (T5); and revenue inflation kept just under the bank's 1.5x line (T8 weak). Separately, until F2 (new or bursting party) and F4 (document software) are built, only rings that also involve an equipment vendor can be held. Every non-equipment ring lands on watch today. We report each of these as an expected miss rather than hiding it.
