# DealPilot — Goldman-I

HackUTD 2026 entry (Goldman Sachs challenge + NVIDIA Nemotron track).

DealPilot reads a bank's shared loan folder, extracts the deal facts, moves each deal through the lending pipeline
(Intake → Credit → Committee → Product → Committed → Closed) on a simulated clock, asks the right human at every
sign-off, alerts and escalates when a deal is stuck, and catches fraud rings by looking **across** deals — an entity
graph of deals and the parties, documents, and accounts they share.

- **Engine:** deterministic Python (pandas, networkx, pypdf) behind FastAPI — owns every scored output.
- **Agents:** NVIDIA Nemotron — fraud investigator (ReAct + tools), red-team scenario generator, VL fallback document reader.
- **UI:** React + Vite + Tailwind, clean light fintech design with an interactive fraud graph.

## Status

Planning — see [`.planning/PROJECT.md`](.planning/PROJECT.md). Roadmap in progress.

## Data

The challenge data pack is **not** committed. Place it at `data/participant/` (gitignored).
