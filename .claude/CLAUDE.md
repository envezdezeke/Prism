<!-- GSD:project-start source:PROJECT.md -->

## Project

**Prism (team Prism)**

Prism (team Prism) is our HackUTD 2026 entry for the Goldman Sachs challenge, also entered in the NVIDIA Nemotron prize track. It reads a bank's shared loan folder and pulls out the deal facts. It moves each deal through the six-stage lending pipeline on a simulated clock, asks the right person at every sign-off, and raises alerts and escalations when a deal is stuck. Its core job is catching fake deals by looking **across** deals: an entity graph of deals and the parties, documents and accounts they share. A deterministic Python engine produces every scored output. Nemotron agents investigate, red-team and read hard documents around it. A clean fintech web UI shows the pipeline and the fraud graph.

**Core Value:** **Catch the cross-deal fraud ring before money goes out, without blocking good deals, using a method that still works on the hidden set's different trick.** If everything else fails, the submission JSON must hold the right deals and leave the good ones alone. That means early holds, linked deals, history flags and zero false flags.

### Constraints

- **Timeline**: ~21 hours, 2 people. Priority order when cutting: Goldman score > Nemotron > UI.
- **Tech stack**: Python (pandas, networkx, pypdf) engine behind FastAPI; React + Vite + Tailwind frontend with a force-graph library. Nemotron via the build.nvidia.com API / Brev. Python at `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe` (plain `python` is the Microsoft Store stub).
- **No Claude in product**: the team chose Nemotron + deterministic code.
- **Determinism**: every scored field in the submission JSON must come from deterministic code. Nemotron output is advisory or validated before it can affect a score (a hold, an extraction, a linked deal).
- **Generalization**: no sample-specific literals in detection logic. The hidden set uses a different trick.
- **Time semantics**: the system only sees files after their `arrive_at`. All times are sim time, America/Chicago (−06:00). SLA timers are wall-clock sim hours.
- **Confidentiality**: the challenge statement is for participants only. Raw data and PDFs stay out of git.
- **Secrets**: the NVIDIA API key lives in `.env` (gitignored). Never commit or print it.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

Full, versioned stack and rationale: `.planning/research/STACK.md`. Gotchas the code won't tell you:
- Python: use `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe` or `py -3.13`; plain `python` is the Microsoft Store stub. Set `PYTHONUTF8=1` (cp1252 chokes on em dashes in the PDFs).
- Nemotron via hosted `https://integrate.api.nvidia.com/v1`; model IDs live in env vars (`.env.example`) because build.nvidia.com page slugs differ from live IDs. Plain OpenAI-SDK tool loop, no agent framework. Brev is break-glass only.
- PDFs: pypdf (+ pdfplumber for tables, RapidOCR for images). Never PyMuPDF (AGPL).
- Frontend: TypeScript 7 removed `baseUrl` (use `paths` only); shadcn CLI 4 uses Base UI, not Radix, so old Radix snippets won't match.

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
