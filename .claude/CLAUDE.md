<!-- GSD:project-start source:PROJECT.md -->

## Project

**DealPilot (team Goldman-I)**

DealPilot is our HackUTD 2026 entry for the Goldman Sachs challenge, also entered in the NVIDIA Nemotron prize track. It reads a bank's shared loan folder and pulls out the deal facts. It moves each deal through the six-stage lending pipeline on a simulated clock, asks the right person at every sign-off, and raises alerts and escalations when a deal is stuck. Its core job is catching fake deals by looking **across** deals: an entity graph of deals and the parties, documents and accounts they share. A deterministic Python engine produces every scored output. Nemotron agents investigate, red-team and read hard documents around it. A clean fintech web UI shows the pipeline and the fraud graph.

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

## Verification done (so you know what is measured vs. read)

| Claim | How verified | Result |
|-------|--------------|--------|
| Live Nemotron catalog and exact IDs | `GET https://integrate.api.nvidia.com/v1/models` (works unauthenticated, 84 models) | IDs below are real today |
| All 167 PDFs in `shared_folder` have an extractable text layer | pypdf run over every file | 0 image-only PDFs. OCR is only needed for the 1 JPG |
| PDF Producer/Creator are readable with plain pypdf | Ran on all 167 | Producer counts: FIS Statement Services 9.2 x54, DocuForge 2.1 (Windows) x42 (Creator `DocuForge Templates`), Adobe PDF Library x19, Skia x15, iLovePDF x14, MS Print-to-PDF x8, macOS Quartz x8, QuickBooks Online x7 |
| pypdf speed and layout mode | All 167 PDFs | 2.4 s plain, 2.2 s `extraction_mode="layout"` (keeps statement columns aligned) |
| pdfplumber tables | All 167 PDFs | 14.4 s, 306 tables found. Bank-statement header tables come out as clean key/value rows |
| RapidOCR on Windows, Python 3.13, no system installs | Fresh venv, `pip install rapidocr onnxruntime` | Models ship inside the wheel. Init 13 s, 8 s per image. Read Tyler's `IMG_2291.jpg` correctly: name TYLER JAMES BROOKS, DL34871190, DOB 1996-02-14, address, EXP 2029-04-11 |
| Vite 8 + React 19 + Tailwind 4 + react-force-graph-2d + shadcn compile together | Scaffolded and built in a scratch dir | `vite build` OK (~1 s). One TypeScript 7 gotcha (see Pitfalls) |
| Package versions | `npm view` / `pip index versions` today | Versions below |

## Recommended Stack

### Nemotron (NVIDIA track): hosted API, not Brev

| Role | Model ID (exact, verified in live `/v1/models`) | Why | Confidence |
|------|--------------------------------------------------|-----|------------|
| Fraud investigator agent (ReAct + tools) and red-team generator | `nvidia/nemotron-3-super-120b-a12b` | Model card lists function calling, reasoning and structured output. 12B active params, so latency is tolerable for 5-10 step loops. Needs `temperature=1.0, top_p=0.95` per the model card | MEDIUM-HIGH |
| Cheap, fast text jobs (plain-words messages, reply parsing, alert copy) | `nvidia/nemotron-nano-3-30b-a3b` | 3B active, fast. Run with thinking off for short-latency JSON output | MEDIUM (existence verified; tool-call behavior not tested) |
| Vision-language fallback reader (ID photo JPG, unknown layouts) | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | Accepts images as base64 `data:image/jpeg;base64,...` in `image_url` content parts. Model card lists function calling. Fast enough to call per document | MEDIUM-HIGH |
| VL quality escalation (only if nano-omni misreads) | `nvidia/nemotron-3.5-super-vl-120b-a12b` | Bigger VL. Page is inconsistent ("early-access" vs "GA", released 2026-10-15). Treat as optional | MEDIUM-LOW |
| Fallback if Super is rate-limited or erroring | `nvidia/nemotron-3-ultra-550b-a55b` (GA 2026-06-04, tool calling listed) | Strongest but slowest. Use only as a fallback or for a one-shot "write the case" call | MEDIUM |
| Optional layout parse of page images | `nvidia/nemotron-parse-2.0` | Document-to-markdown+bboxes via special control-token prompt (`</s><output_markdown>`), NOT tool calling, 9k-token context. Nice demo, not needed for the scored path. Skip unless time is left | MEDIUM |
- Reasoning is ON by default. `enable_thinking: False` turns it off (use for the fast model and for JSON-only jobs). `low_effort: True` shortens traces (use for the investigator to cut latency). These are documented for self-hosted backends; the hosted examples show `enable_thinking` in `extra_body`, but the page says to confirm the hosted endpoint honors `low_effort`. Test in the smoke test.
- Reasoning goes in `message.reasoning_content`; `content` can be empty on a tool-call turn. Never assume `content` is non-null.
- Image payloads: base64 data URL. The VL page recommends `temperature=0.6, top_p=0.95` for vision.
- PDFs are not a VL input. Rasterize pages first (pypdfium2, below).
- One shared client with a token-bucket limiter at ~30 RPM and `tenacity` retry on 429/5xx (exponential, max 3).
- A ReAct loop of 6 steps costs 6 requests, so one investigation is ~10-15% of a minute's budget. Run investigations sequentially, cache results to disk keyed by cluster hash, and pre-compute the demo investigation before judging.
- Both teammates sharing one key shares the 40 RPM. Use two keys (one per person) if each can generate one.
- Super-120B needs 8x H100-80GB (BF16) per its model card. $60 of Brev credit cannot sustain that. Ultra needs more.
- Only the small models (Nano 30B-A3B, `nemotron-3.5-bolt-e4b`) fit one GPU, and then you own vLLM flags (`--enable-auto-tool-choice --tool-call-parser qwen3_coder`, model-specific reasoning parser, `trust-remote-code`) plus startup and download time out of a 21h budget.
- Use Brev only as a break-glass option if the hosted endpoint is down or throttled during judging: one L40S/H100 running Nano with vLLM using an OpenAI-compatible URL, which means only `base_url` changes. The code needs no changes either way because it is the same client. Do not pre-build it.
- Pitch angle: "Nemotron runs behind one OpenAI-compatible seam; we can point it at hosted NIM or a Brev-deployed NIM with one env var" gets the credit without the risk.

### Agent framework

| Option | Verdict | Why |
|--------|---------|-----|
| Plain `openai` SDK loop (recommended) | USE | You control the loop, the step cap, the trace format, argument validation and the fallbacks. Every tool is a deterministic Python function over the graph, so the agent cannot affect a score. The trace you log (thought / tool / args / result / evidence IDs) is exactly the artifact the NVIDIA judges and the UI timeline want. If hosted tool calling misbehaves, you can swap the loop to a text ReAct format (`Action:` / `Action Input:` JSON parsed by regex) in 30 lines without changing any tool |
| LangGraph 1.2.20 | Only if you want the red-team and investigator as a visible multi-agent graph | Adds `langchain-core` and `langchain-nvidia-ai-endpoints 1.5.0` (ChatNVIDIA), state-schema and checkpointer concepts, plus version churn. The reasoning field and `tool_choice` handling pass through an extra abstraction exactly where you will be debugging. No benefit for one agent with 6-8 tools |
| NVIDIA NeMo Agent Toolkit (`nvidia-nat` 1.9.0) | AVOID for this build | Config-driven (YAML workflows), large dependency surface, its own CLI and plugin model. Real value is profiling/evals/observability, which you cannot afford to learn in 21h. If a judge asks about NeMo, say it is a clean future migration because the tools are plain functions |

### Core Technologies (Python engine)

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python | 3.13 (`C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe`) | Runtime | Already installed. All wheels below exist for cp313 on Windows | HIGH |
| FastAPI | 0.143.0 installed (0.162.2 latest) | API + SSE | Team won RowdyHacks on this. **Do not upgrade mid-hackathon**; nothing here needs newer | HIGH |
| uvicorn | 0.53.0 installed (0.54.0 latest) | ASGI server | Installed. Run with `--reload` in dev only | HIGH |
| pydantic | 2.13.5 installed | Models for facts, signals, submission JSON, tool args | Use one `Fact(value, source_doc, page, confidence)` model everywhere. Enforces the SUBMISSION_FORMAT shape on write | HIGH |
| pandas | 3.0.1 installed | History baselines (rarity, deposit stats), CSV ingestion | Installed. pandas 3 has copy-on-write and string dtype changes, so write code that does not rely on chained assignment or on `object` string columns | HIGH |
| networkx | 3.7 (needs install) | Deal-entity bipartite graph, connected components, ego graphs, `node_link_data` for the UI | Pure Python, 300 deals is nothing, exports straight to the JSON the force-graph wants | HIGH |
| openai | latest (needs install; `pip index` shows 3.46.0) | Nemotron client | OpenAI-compatible endpoint, official SDK, `extra_body` passthrough | HIGH |
| python-dotenv | 1.2.3 installed | Load `.env` (NVIDIA key) | Installed. `.env` stays gitignored | HIGH |

### PDF and document extraction

| Library | Version | Purpose | When to Use | License | Confidence |
|---------|---------|---------|-------------|---------|------------|
| **pypdf** | 6.21.1 installed (7.0.0 latest; both tested working) | Text per page (`extract_text(extraction_mode="layout")`), `reader.metadata` (Producer, Creator, CreationDate, ModDate, Title, Author), page count, "Page X of N" detection | Primary parser for every PDF. Fast (167 PDFs in 2.4 s). Already installed, already in the PROJECT.md stack | BSD-3 | HIGH |
| **pdfplumber** | 0.11.10 (needs install; pulls pdfminer.six + pypdfium2) | `extract_tables()` for bank-statement transaction tables and financial statements | Use only for statements, P&L, balance sheet where you need rows/columns. 14 s for everything, so call it lazily per document type, not on all pages | MIT | HIGH |
| **pypdfium2** | 5.15.1 (comes with pdfplumber) | Rasterize a PDF page to a PIL image for the Nemotron VL fallback (0.06 s/page at scale 1.5) | VL fallback only. No poppler, no system install on Windows | Apache-2.0/BSD | HIGH |
| **RapidOCR** (`rapidocr` + `onnxruntime`) | rapidocr 3.10.0, onnxruntime 1.31.1 | Local, offline OCR for JPG/scanned pages (ID photo) | Deterministic first pass on images before calling VL: OCR gives text, the VL model interprets layout. Works with no system installs; models are inside the wheel. Adds ~300 MB to a venv (opencv-headless, shapely, numpy) and ~13 s init, so lazy-load it once | Apache-2.0 | HIGH |
| rapidfuzz | 3.14.6 (needs install) | Lookalike detection (e.g. "Metroplex Equipment Supply LLC" vs "Inc."), name normalization | Fuzzy entity resolution for the rarity/lookalike signals. Use token-set ratio on normalized names | MIT | HIGH |

### Frontend

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| React | 19.3.1 | UI | PROJECT.md choice, current | HIGH |
| Vite | 8.3.6 (Node >= 20.19, you have 24.20) | Dev server + build | Verified building with the stack below | HIGH |
| `@vitejs/plugin-react` | 6.2.1 | React transform | Peer-requires vite ^8 | HIGH |
| Tailwind CSS + `@tailwindcss/vite` | 4.3.5 | Styling | v4 config is CSS-only (`@import "tailwindcss";`), no `tailwind.config.js`, no PostCSS file | HIGH |
| **react-force-graph-2d** | 1.29.2 (wraps `force-graph` 1.52.0) | **Hero fraud-ring graph** | See graph decision below | HIGH |
| shadcn/ui CLI | 4.23.0 (`npx shadcn@latest`) | Component kit | Copies source into your repo, Tailwind 4 native. Verified `init -d -y` plus `add card badge tabs table sheet scroll-area separator tooltip sonner` all work non-interactively. CLI 4 defaults to the `base-nova` style on **Base UI** (`@base-ui/react`), not Radix. Fine, but do not paste old Radix-based snippets from blog posts | HIGH |
| lucide-react | 1.70.0 | Icons | shadcn default | HIGH |
| `@tanstack/react-query` | 5.107.1 | Fetch/poll the engine (clock state, inbox, alerts) | Polling with `refetchInterval` while the sim clock runs; avoids hand-rolled loading state | HIGH |
| zustand | 5.1.0 | Tiny client state (selected deal, selected node, sim clock) | One store, no boilerplate | MEDIUM-HIGH |
| motion (framer-motion) | 14.10.1 | Panel and list transitions | Optional polish. Skip if behind on time | MEDIUM |

#### Force-graph decision: react-force-graph-2d

| Library | Verdict | Reasoning |
|---------|---------|-----------|
| **react-force-graph-2d** | **USE** | Canvas renderer with per-node/per-link draw callbacks (`nodeCanvasObject`, `linkCanvasObject`). That is what makes the "ring lights up" effect easy and light-theme-safe: you draw the glow, halo, labels and badges yourself on a white background. Built-in `linkDirectionalParticles` animates flow along edges for free. d3-force layout, drag, zoom, `onNodeClick`, `zoomToFit`, `cooldownTicks` all built in. Scoped to this data (tens of deals, hundreds of entities) it is 60 fps. Built in my scratch project in ~1 s. Peer dep is `react: "*"`, so React 19 is fine |
| reagraph 4.32.0 | Runner-up | WebGL (three.js) with nicer out-of-the-box styling, themes, cluster and lasso. But heavier bundle, GPU/WebGL surprises on a judging laptop or projector, 3D-flavored camera controls, and less control of per-edge evidence drawing. Take it only if you want the default look with zero custom drawing |
| sigma 4.0.4 + graphology 0.26.0 + `@react-sigma/core` 6.0.0 | No | Built for 10k+ node graphs. Needs custom node programs for anything beyond circles, and labels/halos are fiddly. Wrong tool at this scale |
| Cytoscape.js 3.34.4 (+ `react-cytoscapejs` 2.0.0, `cytoscape-fcose` 2.2.0) | No | Excellent graph-analysis toolkit and stylesheet model, but the React wrapper is stale, animations/glow are limited, and the look defaults to "academic". Choose it only if you need compound nodes or cola/fcose layouts |
| `@xyflow/react` 12.12.1 | Different job | Use it (optionally) for the six-stage pipeline diagram, not the entity graph. Do not use it for force layouts |

#### UI look

- shadcn `base-nova` theme, Geist Variable (installed by the CLI), light background `#f8fafc`-ish, one accent color (indigo or teal), red/amber reserved for fraud and SLA states only. Cards with 1px borders and soft shadow, tabular numerals for money (`tabular-nums`), badges for stage and status.
- Skip dark mode. Skip chart libraries unless a specific chart is required; the sim-clock timeline and SLA bars are plain divs.

### Development tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `py -m venv` or the system Python | Isolation | The system Python already has FastAPI/pandas/pypdf. A venv is cleaner but you must re-install. Either works; do not mix |
| uvicorn `--reload` | API dev | Dev only; use no reload for the judged run so the sim clock state is not reset by file saves |
| Vite proxy `/api` to `http://localhost:8000` | Avoid CORS | Already verified in `vite.config.ts` in the scratch build; also add CORS middleware as a fallback |
| pytest | Engine regression tests on the 13 folders + submission schema | Add a `tests/test_submission_schema.py` first, because it is the scored artifact |
| oxlint | Comes with the Vite 8 template | Fine; no ESLint config needed |

## Installation

# Engine (pandas, pypdf, fastapi, uvicorn, pydantic, python-dotenv already installed)

# pypdfium2 + pdfminer.six arrive with pdfplumber

# Frontend

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Plain OpenAI loop | LangGraph 1.2.20 | You want a visual multi-agent graph with checkpointed state and have 2+ spare hours |
| Plain OpenAI loop | NeMo Agent Toolkit `nvidia-nat` 1.9.0 | You need its built-in eval/profiling and have time to learn its YAML workflow model. Not in a 21h build |
| Hosted build.nvidia.com | Brev GPU | Hosted endpoint is down or throttled, or you want a self-hosted-NIM talking point. Small models only |
| pypdf (+ pdfplumber for tables) | PyMuPDF 2.1 | Only if the repo and demo stay private and closed. It is AGPL-3.0 or a paid Artifex commercial license. A public hackathon repo shipping it is a license problem, and pypdf is already fast enough here |
| RapidOCR | Tesseract + pytesseract 0.3.13 | Never on this machine. Tesseract is not installed and needs an installer plus PATH work |
| RapidOCR | EasyOCR | Pulls PyTorch (GB-scale). No |
| react-force-graph-2d | reagraph 4.32.0 | You want WebGL defaults with zero custom drawing and have tested on the demo machine |
| shadcn/ui | Mantine / MUI | Only if the team already knows them. shadcn gives the cleaner fintech look with the least CSS |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| PyMuPDF / `fitz` | AGPL-3.0 (commercial license otherwise). Unnecessary for this corpus | pypdf + pdfplumber + pypdfium2 |
| `nvidia/nvidia-nemotron-nano-9b-v2` (PROJECT.md example) | Not in the live catalog today | Pick from `/v1/models`: Super / Nano-3 / Nano-Omni |
| Any Claude/Anthropic SDK or model | Out of scope by team decision | OpenAI SDK pointed at NVIDIA |
| LLM output feeding a scored field directly | Violates the determinism constraint; false flags are heavily penalized | Deterministic validator between LLM and submission JSON |
| Training a classifier on `fraud_label` | Does not transfer to the hidden set's different trick | Rarity-vs-baseline + independent-signal agreement |
| Hardcoded literals ("DocuForge", "Delacroix", 4471) | Hidden set uses a different trick | Generic rarity, lookalike, distribution-anomaly signals |
| `PdfReader.extract_text()` in default mode for statements | Columns collapse and amounts detach from descriptions | `extraction_mode="layout"` or pdfplumber tables |
| Calling VL/OCR on every document | Burns the ~40 RPM budget and adds nondeterminism | Text layer first, VL only on gaps |
| Long-lived LangChain/NAT dependency trees | Install time, version churn, debugging through abstractions | Direct SDK |
| Streaming tool-call deltas for the investigator | Extra parsing complexity for no scoring value | Non-streamed calls; stream only the UI trace over SSE from your own loop |

## Stack Patterns by Variant

- Try Ultra, then Nano-3, with native `tools`.
- If all fail, switch the loop to text-based ReAct (the model emits `Action`/`Action Input` JSON, you parse and run). Same tools, same trace, no framework change.
- Feed RapidOCR text plus the image to the VL model ("correct this OCR"), then validate against the loan application (name/DOB/address fuzzy match). Keep the deterministic mismatch check as the thing that raises `ID_MISMATCH`.
- Every Nemotron call has a deterministic fallback: templates for messages, a rule-based case summary from the same evidence list for the investigator, and RapidOCR text for the JPG. Cache all live Nemotron outputs to `artifacts/nemotron_cache/` keyed by prompt hash so a replay needs no network.
- Drop motion, react-query (use `setInterval` fetch), nemotron-parse, and the VL escalation model. Keep: engine, Super investigator, VL on the JPG, react-force-graph-2d.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Vite 8.3.6 | `@vitejs/plugin-react` 6.2.1 (peer `vite ^8`), `@tailwindcss/vite` 4.3.5 (peer `vite ^5..^8`) | Node must be `^20.19.0 or >=22.12`; you have 24.20 |
| TypeScript 7.0.2 (Vite 8 template default) | shadcn `@/` alias | **TS 7 removed `baseUrl`.** shadcn's Vite doc tells you to add `baseUrl`; doing so gives `TS5102: Option 'baseUrl' has been removed`. Use only `"paths": {"@/*": ["./src/*"]}` |
| shadcn-generated `scroll-area.tsx` | TS `noUnusedLocals` | Generated file has an unused `React` import, so `tsc -b` errors with TS6133. Set `"noUnusedLocals": false` in `tsconfig.app.json` or build with `vite build` only |
| react-force-graph-2d 1.29.2 | React 19.3.1 | Peer `react: "*"`, built and typechecked clean in the scratch project. Cast node to `any` for `x`/`y` in canvas callbacks or define your own node type |
| pandas 3.0.1 | NumPy 2.4.3 | Installed pair works. RapidOCR in a separate venv pulled NumPy 2.5.4 and OpenCV 5; if you install it into the main Python, run `pip check` afterwards |
| pypdf 6.21.1 vs 7.0.0 | Same API for `PdfReader`, `.metadata`, `extract_text(extraction_mode="layout")` | Tested on both. No need to upgrade |
| pandas/pypdf/FastAPI already installed | Python 3.13 | All new Python deps listed have cp313 Windows wheels (RapidOCR, onnxruntime, pdfplumber, pypdfium2, networkx, rapidfuzz) |

## Sources

- Live catalog: `GET https://integrate.api.nvidia.com/v1/models` (queried 2026-11-07; authoritative for exact model IDs) — HIGH
- build.nvidia.com model cards fetched 2026-11-07: `nvidia/nemotron-3-super-120b-a12b`, `nemotron-3-nano-omni-30b-a3b-reasoning`, `nemotron-3-ultra-550b-a55b`, `nemotron-3.5-lightning-30b-a3b`, `nemotron-3.5-super-vl-120b-a12b`, `nemotron-parse-2.0` — capabilities (function calling, reasoning, image input), sampling and `chat_template_kwargs` — HIGH for the page text, MEDIUM for hosted-endpoint behavior (pages do not demonstrate hosted tool calling)
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16 — reasoning toggles, `qwen3_coder` tool parser, 8x H100 minimum — HIGH
- NVIDIA developer forum threads on the 40 RPM build.nvidia.com default and no self-serve increase (e.g. forums.developer.nvidia.com "NVIDIA NIM API Rate Limit Increase Request (40 -> 200 RPM)") — MEDIUM (user reports, no official page)
- https://pypi.org/project/pymupdf/ — v2.1 (2026-11-02), AGPL-3.0 or commercial — HIGH
- https://pypi.org/project/rapidocr/ — v3.10.0, Apache-2.0, py3.8-3.13 — HIGH; plus a local run on `IMG_2291.jpg` — HIGH
- https://ui.shadcn.com/docs/installation/vite — manual Vite install steps — HIGH; plus local `shadcn init` and `add` run — HIGH
- npm registry (`npm view`) and PyPI (`pip index versions`) on 2026-11-07 for all version numbers — HIGH
- Local runs against `data/participant/shared_folder` (167 PDFs, 1 JPG) for pypdf/pdfplumber/pypdfium2/RapidOCR behavior and Producer/Creator counts — HIGH
- Not verified: Brev launchable catalog and startup time (no source found), `nvidia-nat` dependency footprint (dry run did not finish), LangGraph behavior against the hosted endpoint — LOW, and not relied on in any recommendation

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
