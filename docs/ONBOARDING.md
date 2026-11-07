# Onboarding: start here, Jesse

This is everything you need to pick up DealPilot without having been in the planning chat. It takes about 10 minutes to read.

## 1. What we're building (30 seconds)

**DealPilot** is a helper for a fictional bank (Trinity Commercial Bank). It does five things:

1. **Reads** each borrower's loan folder (PDFs, CSVs, one phone photo) and pulls out the facts.
2. **Moves** each deal through 6 stages, in order: Intake → Credit → Committee → Product → Committed → Closed. Entering Closed means the money goes out.
3. **Asks a human** at every sign-off, routed to the right person (with a backup when someone is out of office).
4. **Shouts when a deal is stuck**, at 100%, 150% and 200% of each stage's time limit.
5. **Catches fake deals by looking across deals.** One fake deal looks fine on its own. The trick only shows when you compare many deals.

We're entered in **two tracks**:
- **Goldman Sachs challenge.** Judges score the JSON we output on READ, MOVE and FRAUD. They then run our code on a **hidden set with a different trick**, so nothing can be hard-coded to the sample.
- **NVIDIA Nemotron prize.** Nemotron has to do real agent work: plan, call tools, run multi-step workflows. Chat alone doesn't count.

**Priority when time runs short:** Goldman score > Nemotron > UI.

## 2. The fraud we found in the sample (so you can explain it)

- **The ring.** Three current deals share the same hidden fingerprint: **Pecan Grove Catering**, **Ridgeway Freight Logistics** and **Summit Peak Flooring**. They share:
  - the same bookkeeper, "K. Delacroix" (214-555-0187);
  - every PDF made with the same software ("DocuForge"), even the bank statements, which no real bank produces that way;
  - a vendor called "Metroplex Equipment Supply **LLC**" paying into a different bank account (…4471) from the real "Metroplex Equipment Supply, **Inc.**" (…9902);
  - companies less than ~18 months old;
  - loan amounts just under $250k, so only one approver signs instead of the full committee.
- **History has two more** that were already funded: **H-2608-002** (now 30 days past due) and **H-2609-008**. Their deposits are 100% round numbers, landing only on Mondays and Thursdays. Finding these is the "find the rest" score.
- **Strange is not fake.** Flagging a good deal costs a lot of points. These look odd but are real:
  - Tyler: messy CSVs and a phone photo of his ID.
  - James / Okafor: big numbers, international.
  - Westfield: a new vendor.
  - Harbor Tea: a shared registered-agent address.
  - Maria / Garza: a returning customer.
- **Our method** never says "DocuForge = fraud". It builds a **graph** linking deals to the people, phones, vendors, accounts and software they share. It weights each link by how *rare* that entity is across a year of history. A deal is only held when **3 independent kinds of evidence agree**. That way the method still works when the hidden set uses a different trick.

## 3. Who does what

| | Ezekiel | Jesse |
|---|---|---|
| Owns | Python engine (reading, pipeline, alerts, fraud graph), Nemotron agents | Golden answer labels, the web UI, demo + pitch |
| First task | Foundations + API contract | Hand-label `eval/gold.json` (the right answers for all 13 sample deals), then scaffold the UI against mock data |

**The only interface between us is the API contract** (`contracts/` plus JSON fixtures). Jesse builds the UI with `MOCK=1`, so it never waits on the engine. When the engine is ready, we flip one env var.

Jesse's own plan notes (validation protocol, execution checklist, questions for Vijay, pitch framing, Jesse's work list) are in **[`HANDOFF.md`](../HANDOFF.md)**. PROJECT.md wins if the two conflict.

The full timeline, with hour-by-hour windows, is in **[`.planning/ROADMAP.md`](../.planning/ROADMAP.md)**. Where we are right now is in **[`.planning/STATE.md`](../.planning/STATE.md)**.

## 4. Setup (Windows)

```bash
git clone https://github.com/envezdezeke/Goldman-I.git
cd Goldman-I
```

**Get the data (it is NOT in git; the challenge material is participant-only):**
1. Download `participant.zip` from https://github.com/SushmaEati/HackUTD/tree/main/datasets
2. Unzip it so you have `Goldman-I/data/participant/` (containing `shared_folder/`, `history/`, `rules/`, `sim/`, ...).

**Python:** use 3.13. Plain `python` in Git Bash may open the Microsoft Store stub, so use `py -3.13` or the full path.
```bash
py -3.13 -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt        # once the engine scaffold lands
```

**Frontend:** Node 20+. The stack is React 19, Vite, Tailwind 4, shadcn/ui and react-force-graph-2d (`ui/` folder, once scaffolded).

**Nemotron key:** get an API key at https://build.nvidia.com. Put it in `.env` as `NVIDIA_API_KEY=...`. `.env` is gitignored, so **never commit or paste it**. A second key from you doubles our rate limit.

## 5. Working together in git

- `main` must always run. Work on a branch (`jesse/ui-board`, `ezekiel/ingest`), then merge or PR into `main`.
- Run `git pull` before you start and before you push. The planning docs in `.planning/` are shared, so pull often.
- Keep commits small, with messages like `feat(ui): pipeline board`.

## 6. How the planning system works (GSD)

We plan with "GSD" in Claude Code. Everything lives in `.planning/`:

| File | What it is |
|---|---|
| `PROJECT.md` | The why: goals, constraints, the **Key Decisions** table (read this) |
| `REQUIREMENTS.md` | Every checkable requirement, tagged with an owner (E/J) |
| `ROADMAP.md` | Phases, hour windows, who owns what, success criteria |
| `STATE.md` | Where we are right now |
| `research/` | Stack, features, architecture, pitfalls and a SUMMARY |

If you use Claude Code, open the repo and run `/gsd-progress`. It reads STATE.md and tells you what's next. To plan or run a phase: `/gsd-plan-phase N`, then `/gsd-execute-phase N`. Without Claude Code, just read ROADMAP.md and STATE.md.

## 7. Decisions already locked (don't re-argue these; flag them if you disagree)

- Deterministic Python produces every scored answer. Nemotron gives advice or has its output validated, and never decides a hold by itself.
- A deal is held only on **3 agreeing signal families**. 1–2 families puts it on a visible "watch" list.
- A flagged deal is frozen immediately, and Fraud Ops (victor.hale, backup monica.salas) is asked to confirm.
- Nemotron runs through the hosted API (build.nvidia.com). Runs are recorded so the demo can replay them if the API is slow.
- UI style is **clean, light fintech** (think Stripe or Ramp). We're aiming for best design.
- **Gates:** H10 engine baseline frozen · H16 Nemotron agents working · H19 feature freeze → dry run, demo recording, pitch.

## 8. Open questions for the organizers (whoever is near the help desk)

1. During judging, how do the "staff" answers reach us: a UI we run, files, or an API they call?
2. How do the weekend drop and the hidden set arrive: a new zip with its own `arrivals.jsonl`, or files added to the same folder?
3. Is `issues` scored on the end state of the run, or on every issue ever raised?
