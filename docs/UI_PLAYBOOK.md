# UI Playbook (for Jesse and Jesse's agents)

> Purpose: give every Claude Code session building `ui/` the same setup, tools and taste, so the cockpit looks like a bank's own credit tool and not a template.
> **Locked visual decisions are Jesse's D-01 to D-16** in `.planning/phases/02-pipeline-cockpit-ui-on-mock-data/02-CONTEXT.md`. This file adds setup, tokens, recipes and a verification loop. If anything here conflicts with D-01 to D-16, D-01 to D-16 wins.
> Agents: read this file, `02-CONTEXT.md`, `docs/CONTRACT.md` and `prism/contract.py` before writing UI code.

## 1. One-time setup (Mac, inside the repo)

**Run in a normal terminal:**

```bash
git pull
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"      # mock API deps (skip if .venv exists)
MOCK=1 .venv/bin/python -m uvicorn prism.api.app:app --port 8000 # mock API -> http://localhost:8000/docs
```

**Install agent tools (run once; the `/plugin` lines go inside Claude Code, the others in a terminal):**

| Tool | Command | What it gives the agent |
|---|---|---|
| Anthropic skills marketplace | `/plugin marketplace add anthropics/skills` (in Claude Code) | Access to Anthropic's public skills |
| **frontend-design** + **webapp-testing** | `/plugin install example-skills@anthropic-agent-skills` (in Claude Code) | `frontend-design`: deliberate typography/palette/layout choices instead of template defaults. `webapp-testing`: Playwright scripts to open the app, click through it and take screenshots |
| **shadcn MCP** | `npx shadcn@latest mcp init --client claude` (terminal, in `ui/`) | The agent can browse and add shadcn components correctly (shadcn CLI 4 uses **Base UI, not Radix**; old Radix snippets won't match) |
| **Playwright MCP** | `claude mcp add playwright -- npx @playwright/mcp@latest` (terminal) | The agent can *see* the running page: navigate, click, screenshot. This is how it checks its own work |

Restart Claude Code after installing so it picks up the skills and MCP servers, then check with `/mcp` (both servers listed) and by asking "what skills do you have?" (frontend-design and webapp-testing should be listed).

**Give every UI session this context automatically.** Create `ui/CLAUDE.md` (if it doesn't exist yet) containing:

```markdown
# ui/ (Prism cockpit)
@../docs/UI_PLAYBOOK.md
@../.planning/phases/02-pipeline-cockpit-ui-on-mock-data/02-CONTEXT.md
@../docs/CONTRACT.md
Rules: read only fields defined in prism/contract.py. Use the frontend-design skill for any new screen.
Verify every change with the Playwright MCP (screenshot at 1440x900 and 1280x800) against section 6 of UI_PLAYBOOK.md.
```

Stack and versions are in `.planning/research/STACK.md` (React 19, Vite 8, Tailwind 4, shadcn on Base UI, TanStack Query, zustand, lucide icons). TypeScript 7 removed `baseUrl`, so use `paths` only. The Vite dev proxy sends `/api` to `http://localhost:8000`.

## 2. Design tokens (implements D-04 to D-07)

Put these in `ui/src/index.css` as Tailwind 4 theme variables and use **only** these. Never write a raw hex in a component.

```css
@import "tailwindcss";
@theme {
  /* surfaces */
  --color-page: #FAF9F7;        /* warm off-white page */
  --color-surface: #FFFFFF;
  --color-subtle: #F3F1ED;      /* table header, hover row */
  /* warm gray text + lines */
  --color-ink: #1C1B19;         /* primary text */
  --color-ink-2: #57534E;       /* secondary text */
  --color-ink-3: #8A847C;       /* tertiary, captions */
  --color-line: #E4E0D9;        /* hairline borders */
  --color-line-strong: #CFC9BF;
  /* single accent */
  --color-navy: #1B2A41;        /* primary actions, active nav, focus */
  --color-navy-soft: #E8ECF2;
  /* semantic, meaning only (D-05) */
  --color-hold: #B42318;        /* fraud hold ONLY */
  --color-hold-soft: #FDECEA;
  --color-risk: #B54708;        /* SLA past 100%, deadline at risk ONLY */
  --color-risk-soft: #FEF3E2;
  --color-ok: #3F6E4E;          /* cleared / approved ONLY */
  --color-ok-soft: #EAF2EC;
  /* type */
  --font-display: "Source Serif 4", Georgia, serif;   /* page titles only */
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  /* shape */
  --radius-sm: 4px;
  --radius-md: 6px;
}
body { background: var(--color-page); color: var(--color-ink); font-family: var(--font-sans);
       font-feature-settings: "tnum" 1, "cv11" 1; -webkit-font-smoothing: antialiased; }
```

- **Type scale** (keep to these): 12 (captions, table meta) / 13 (table body) / 14 (body) / 16 (section titles, sans semibold) / 22 (page title, serif). Line height 1.4 for body, 1.2 for titles.
- **Spacing**: multiples of 4px. Table rows 36px tall, cell padding 8px × 12px.
- **Borders, not shadows**: `1px solid var(--color-line)` everywhere. The only shadow allowed is `0 1px 2px rgb(0 0 0 / 0.06)` on popovers and menus.
- **Focus**: `outline: 2px solid var(--color-navy); outline-offset: 2px`. Never remove focus rings.
- Load fonts from Google Fonts (Source Serif 4, Inter); self-host if offline demo is a worry.

## 3. Formatting rules (the UI must never change a value's meaning, D-01)

Put these in one file, `ui/src/lib/format.ts`, and use it everywhere:

| Value | Rule | Example |
|---|---|---|
| Money | Integer dollars, thousands separators, right-aligned, tabular | `$246,000` |
| Sim time | Parse the `-06:00` offset from the string and format in that fixed offset. **Never** use the viewer's timezone | `Tue 11/03 3:05 PM CT` |
| Duration | Hours and minutes | `26h 10m` |
| SLA | Time in stage / limit, plus a percentage | `26h 10m / 48h · 55%` |
| Null | An em dash in `--color-ink-3`, with a tooltip "Not found in documents" | `—` |
| People | Display name from `teams.json`; the id goes in a tooltip | `Aisha Grant` |
| Confidence | A word, not a decimal: High ≥ 0.9, Medium ≥ 0.6, else Low | `High` |

## 4. Screen recipes

**App frame.** A left rail (200px) with Pipeline, Inbox (with a count badge), Alerts, and Fraud graph (Phase 7). A top bar holds the **sim clock** (always visible): current sim time, "Advance 1h / 6h / to next arrival" buttons, and "Replay from start". Nothing else goes in the top bar.

**Pipeline board (UI-02).**
- Six columns, Intake → Closed. Each column header shows the stage name, a count, and the stage SLA ("48h").
- Each deal is a compact row-card: legal name (folder name underneath in ink-3), amount on the right, then a thin SLA bar.
- **SLA bar:** a 2px bar under the card. Navy up to 100%, amber past 100%, with tick marks at 100/150/200%. One glance shows who's stuck.
- **Badges:** at most one per card, in this priority: `Held: fraud review` (red) > `Watch` (neutral outline) > `Needed by Fri` (amber when at risk, neutral otherwise) > none.
- Sort within a column: held first, then by needed-by, then by time in stage.

**Deal detail (UI-04).** Two columns.
- **Left (main), in order:** a facts table (field, value, source-document chip, confidence) → issues (each with a plain-words line) → stage log (vertical timeline: stage, entered → exited, decision, *why*) → human requests → alerts.
- **Right (320px):** a deal summary card (RM, credit officer, stage, SLA, needed-by), then fraud status. For a held or watched deal, the fraud panel lists **F1–F6 in order, each with bits vs. threshold**. F6 is labelled "evidence only" (see `docs/MODEL_DESIGN.md`).
- The source chip opens a side sheet with the document name and the extracted snippet. Provenance on click is the strongest trust signal in the app.

**Inbox (UI-05).** A table of pending requests (age, deal, type, to, message preview). Selecting one opens a pane with the full plain-words message and **only the request's allowed options** as buttons (navy for the primary option, outline for the others), plus an optional note. After answering, show a quiet "Answered" state; never a toast storm.

**Alerts feed.** A reverse-chronological table: time, level (`Alert` / `Escalation` / `Second escalation`), deal, stage, to, message. Escalations get an amber left border; nothing else is colored.

**Fraud graph (Phase 7, UI-06), so the board's style carries over.**
- Deals are filled circles (held = red ring, watch = gray ring); entities are small squares labelled with their type.
- **Edge width and opacity scale with surprisal**: rare = thick and dark, common = hairline and faint, with a label like "used by 15 deals".
- Replay with the sim clock: edges fade in at their `first_visible_at` (a 200ms opacity transition, nothing bouncier).
- The cluster header shows "k of 4 voting families agree" and the permutation p-value. Clicking an edge opens the evidence side sheet.
- Use a force-graph library with fixed layout seeding so the graph doesn't jump between renders.

## 5. Touches that make it stand out (and stay institutional)

1. **Keyboard first**: `j/k` to move through rows, `Enter` to open, `g p` / `g i` / `g a` to jump to Pipeline / Inbox / Alerts, `?` for a shortcut sheet. Credit tools are used all day; judges notice.
2. **A clock scrubber with arrival ticks**: a thin timeline under the clock with a tick per file arrival and a red tick where each hold fired. Dragging it replays the week. This is the demo's best moment.
3. **"Why" on every number**: hovering any SLA, badge or fact shows its source (document, stage-log line, rule). Nothing on screen is unexplained.
4. **A side-by-side mismatch view**: for a `MISMATCH:*` issue, show the application value next to the document value, with the differing characters highlighted.
5. **Density toggle** (comfortable / compact), remembered in localStorage.
6. **Printable credit memo**: a clean print stylesheet for the deal page (serif title, no navigation), since committees still print.
7. **Honest empty states**: "No pending requests. Everything is waiting on borrowers or the clock." Written in real banking vocabulary, never "Nothing here yet!".

## 6. Verification loop (agents run this after every screen change)

1. With the mock API and `npm run dev` running, use the **Playwright MCP** to open each changed page at **1440×900** and **1280×800**, take screenshots, and look at them.
2. Check against this list, and fix before reporting done:
   - [ ] Only token colors; red appears only on fraud holds, amber only on SLA/deadline risk (D-05)
   - [ ] No gradients, glow, blur, big shadows, emoji, purple/indigo, or centered hero layouts (D-08 to D-10)
   - [ ] Serif only on page titles; numbers tabular and money right-aligned (D-06)
   - [ ] Hairline borders, radius ≤ 6px, 4px grid (D-07)
   - [ ] Times in sim CT, names not ids, nulls as em dashes (D-13, D-14, §3)
   - [ ] Loading, empty and error states exist for every data view (D-01)
   - [ ] Keyboard focus visible on every interactive element; text contrast ≥ 4.5:1
   - [ ] Every field shown exists in `prism/contract.py`
3. For flows (answering an inbox item, advancing the clock), use the **webapp-testing** skill to script the clicks and assert the result.

## 7. Prompt starters for Jesse

- *"Read ui/CLAUDE.md. Using the frontend-design skill, build the Pipeline board per UI_PLAYBOOK §4 against GET /api/deals. Then verify with the Playwright MCP per §6 and show me the screenshots."*
- *"Restyle the shadcn defaults to the tokens in UI_PLAYBOOK §2. List every component you changed."*
- *"Audit the current screens against UI_PLAYBOOK §6 and 02-CONTEXT D-01 to D-16. Report the violations first, then fix them."*
- *"Add the clock scrubber from UI_PLAYBOOK §5.2 using /api/clock. If the contract doesn't expose arrival times or hold times yet, stop and list the fields you need so Zeke can add them to the contract. Don't invent fields."*

## 8. What not to spend time on

Animations beyond opacity fades, dark mode, a marketing landing page, charts that repeat what a table already shows, custom illustrations. Goldman scores the output file; the UI's job is to make the engine's work **legible and trustworthy** in the demo.
