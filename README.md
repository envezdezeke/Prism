# DealPilot — Goldman-I

HackUTD 2026 entry (Goldman Sachs challenge + NVIDIA Nemotron track).

DealPilot reads a bank's shared loan folder, extracts the deal facts, moves each deal through the lending pipeline
(Intake → Credit → Committee → Product → Committed → Closed) on a simulated clock, asks the right human at every
sign-off, alerts and escalates when a deal is stuck, and catches fraud rings by looking **across** deals — an entity
graph of deals and the parties, documents, and accounts they share.

- **Engine:** deterministic Python (pandas, networkx, pypdf) behind FastAPI — owns every scored output.
- **Agents:** NVIDIA Nemotron — fraud investigator (ReAct + tools), red-team scenario generator, VL fallback document reader.
- **UI:** React + Vite + Tailwind, clean light fintech design with an interactive fraud graph.

## New to the repo? Start here

**[`docs/ONBOARDING.md`](docs/ONBOARDING.md)**: what we're building, the fraud we found, who does what, setup, and how we work.

## Status

- Plan: [`.planning/ROADMAP.md`](.planning/ROADMAP.md) (phases, hour windows, owners)
- Right now: [`.planning/STATE.md`](.planning/STATE.md)
- Why and decisions: [`.planning/PROJECT.md`](.planning/PROJECT.md)

## Data

The challenge data pack is **not** committed. Place it at `data/participant/` (gitignored).
