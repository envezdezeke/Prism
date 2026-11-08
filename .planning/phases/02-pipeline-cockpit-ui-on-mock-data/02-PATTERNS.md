# Phase 2: Pipeline Cockpit UI on Mock Data - Pattern Map

**Mapped:** 2026-11-07
**Files analyzed:** 27 (all under `ui/`, which does not exist yet)
**Analogs found:** 14 / 27 (the rest are new React/CSS code with no in-repo analog; the spec is CONTEXT.md D-01..D-21 and RESEARCH.md)

## Analog Sources

| Source | Tracked in git | Used for |
|--------|----------------|----------|
| `prism/contract.py` | yes | Field source of truth; every UI type mirrors it |
| `prism/api/app.py` | yes | Endpoint behaviour: clock, reply, error `detail` strings |
| `tests/test_contract.py` | yes | Test structure (fixture-validates, parametrized) |
| `fixtures/*.json` | yes | Mock data the UI is built against |
| `docs/CONTRACT.md` | yes | Endpoint list and conventions |
| `/private/tmp/claude-501/-Users-jes-Goldman-I/c14eddd9-8217-4cd4-a56b-9911e9a08267/scratchpad/derive-check/timeview.ts` | no (scratch, outside repo) | Primary analog for `ui/src/time/timeview.ts` and `simtime.ts`; copy, do not retype |
| `.../scratchpad/derive-check/timeview.test.ts` | no (scratch, outside repo) | Primary analog for `ui/src/time/timeview.test.ts` (9 tests, verified 9/9 on Node 26) |

No path above is a gitignored install or runtime mirror. Both scratch files are outside the repo and must be copied into `ui/` by the executor, which then becomes tracked.

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `ui/src/time/timeview.ts` | utility | transform | `timeview.ts` scratch copy | exact (copy) |
| `ui/src/time/simtime.ts` | utility | transform | `timeview.ts` lines 52-83 + `prism/contract.py` 64-84 | exact (split out) |
| `ui/src/time/timeview.test.ts` | test | batch | `timeview.test.ts` scratch copy | exact (fix FX path, see Gaps) |
| `ui/src/api/types.ts` | model | transform | `prism/contract.py` 127-149, 187-268 | role-match |
| `ui/src/api/schema.ts` | generated | n/a | `/openapi.json` from `prism/api/app.py` | generated, do not hand-edit |
| `ui/src/api/client.ts` | service | request-response | `prism/api/app.py` 110-123 (reply) and 45, 91, 114-120 (errors) | role-match |
| `ui/src/state/clockStore.ts` | store | event-driven | `prism/api/app.py` 59-80 (clock endpoints) | role-match |
| `ui/src/state/answersStore.ts` | store | event-driven | `prism/api/app.py` 110-123 (reply overlay semantics) | role-match |
| `ui/src/data/queries.ts` | service | request-response | `prism/api/app.py` 83-96, 102-108 (list and detail endpoints) | role-match |
| `ui/src/labels.ts` | config | transform | `prism/contract.py` 23, 30-38, 43-50 | exact (same enums) |
| `ui/src/components/app/ClockBar.tsx` | component | event-driven | none | no analog |
| `ui/src/components/app/Board.tsx` | component | transform | none | no analog |
| `ui/src/components/app/DealDetail.tsx` | component | request-response | `fixtures/deal_detail.json` (shape) | no analog for UI |
| `ui/src/components/app/Inbox.tsx` | component | request-response | `prism/api/app.py` 110-123 + `fixtures/inbox.json` | role-match |
| `ui/src/components/app/AlertsFeed.tsx` | component | transform | `fixtures/alerts.json` | role-match |
| `ui/src/components/app/Badges.tsx` | component | transform | `prism/contract.py` 213 (needed_by_badge), 216 (watch) | role-match |
| `ui/src/components/app/States.tsx` | component | request-response | `prism/api/app.py` 45 (503 message) | role-match |
| `ui/src/App.tsx` | component | event-driven | none | no analog |
| `ui/src/main.tsx` | config | request-response | none | no analog |
| `ui/src/index.css` | config (tokens) | n/a | CONTEXT D-04..D-08; RESEARCH "Design Tokens" | spec only |
| `ui/vite.config.ts` | config | n/a | `prism/api/app.py` 31 (CORS origin `localhost:5173`) | partial |
| `ui/tsconfig.json`, `ui/tsconfig.app.json` | config | n/a | scaffold output (RESEARCH "Scaffold" steps 1-2) | spec only |
| `ui/components.json` | config | n/a | shadcn init output (`-t vite -b base -p nova`) | generated |
| `ui/src/components/ui/*` | component | n/a | shadcn output | generated, restyle via tokens |

## Pattern Assignments

### `ui/src/time/timeview.ts` and `ui/src/time/simtime.ts` (utility, transform)

**Analog:** scratch `timeview.ts` (copy it; do not retype). Split formatters into `simtime.ts` and keep derivation in `timeview.ts`.

**Sim-time parsing and fixed offset** (scratch `timeview.ts` lines 52-60; mirrors `prism/contract.py` 64-72):
```ts
const SIM_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})-06:00$/
const HOUR_MS = 3600_000

export function simToMs(s: string): number {
  const m = SIM_RE.exec(s)
  if (!m) throw new Error(`not a -06:00 sim time: ${s}`)
  // -06:00 means UTC = wall clock + 6h
  return Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) + 6 * HOUR_MS
}
```
Python side for comparison (`prism/contract.py` 64-72): `parse_sim_time` requires `T` and a trailing `-06:00`. Keep the TS regex identical.

**Formatters** (scratch lines 62-79): `fmtSimTime` gives `Tue 11/03 3:05 PM CT` (D-13); `fmtDuration` gives `26h 10m`. Never use `toLocaleString` or local `Date` methods on sim times.

**Stage in force, SLA freeze, held, inbox and alert filters** (scratch lines 85-125, condensed):
```ts
// Last stage entry started by t. null = not arrived. Held deals keep their last stage.
export function stageAt(log: StageLogEntry[], t: number): StageLogEntry | null {
  let cur: StageLogEntry | null = null
  for (const e of log) {
    if (simToMs(e.entered_at) <= t) cur = e
    else break
  }
  return cur
}

// Held deals freeze SLA at flagged_at.
export function slaPctAt(deal: DetailLike, enteredAt: string, t: number): number {
  const f = deal.fraud
  const frozen = f.held && f.flagged_at !== null && simToMs(f.flagged_at) <= t
  const end = frozen ? simToMs(f.flagged_at as string) : t
  return (end - simToMs(enteredAt)) / HOUR_MS / deal.sla_hours
}

export function alertsAt(items: AlertLike[], t: number): AlertLike[] {
  return items.filter((a) => simToMs(a.at) <= t).sort((a, b) => simToMs(b.at) - simToMs(a.at))
}
```
Also copy `heldAt` (scratch lines 108-110) and `roundPct` (103-106). `roundPct` is the display rounding that reproduces fixture `sla_pct`.

**Rules the fixtures require** (RESEARCH Pattern 2): a deal is hidden before `stage_log[0].entered_at`; current stage is the last entry with `entered_at <= now` (not `exited_at == null`); SLA ends at `flagged_at` when held.

**Interfaces** (scratch lines 3-50): `StageLogEntry`, `FraudBlock`, `DealLike`, `DetailLike`, `InboxLike`, `AlertLike` are structural copies of `prism/contract.py` 127-158 and 205-268. Keep them structural and local to this module. Do not import generated types here, so the module stays testable with plain JSON.

### `ui/src/time/timeview.test.ts` (test, batch)

**Analog:** scratch `timeview.test.ts` (9 tests) and `tests/test_contract.py` (lines 45-57) for the idea of "every fixture validates against the contract, parametrized per file."

**Test shape** (scratch lines 1-14):
```ts
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { simToMs, fmtSimTime, fmtDuration, stageAt, slaPctAt, roundPct, heldAt, inboxAt, alertsAt } from './timeview.ts'

const FX = '/Users/jes/Goldman-I/fixtures/'   // MUST change, see Gaps
const load = (f: string): any => JSON.parse(readFileSync(FX + f, 'utf8'))
const SNAP = simToMs(clock.now)
```

**Test cases to keep verbatim** (scratch file, by line): formatters (16-22); stage at snapshot equals fixture (24-31); SLA reproduces every `sla_pct` with hold freeze (33-40); Bayou held and frozen at 0.44 (42-53); arrival gate, Mama Rosa at 08:30 on 11/02 (55-61); inbox snapshot (63-71); `inbox-005` pending before 11:50 and answered after (73-81); alerts newest first (83-88); board counts `{Intake: 3, Credit: 1, Committee: 1}` (90-97).

**Run:** `node --test src/time/timeview.test.ts` (Node 26 strips types).

### `ui/src/api/types.ts` (model, transform)

**Analog:** `prism/contract.py`. Mirror field names exactly; the UI never reads a field the contract does not define.

- `Stage` literal, lines 23: `"Intake" | "Credit" | "Committee" | "Product" | "Committed" | "Closed"` (six columns, in order).
- `RequestType`, lines 30-38: seven values, including `fraud_hold` and `info_request`.
- `StageLogEntry`, lines 127-132: `stage, entered_at, exited_at?, decision?, why`.
- `HumanRequest`, lines 135-141: `type, to, at, message, answer?, answered_at?`.
- `Alert` and `AlertFeedItem`, lines 144-149 and 250-252: `at, stage, level, to, message` plus `id, deal` for the feed.
- `Fraud`, lines 152-158: `flagged, held, flagged_at?, stage_at_flag?, reason?, linked_deals[]`.
- `Fact`, lines 187-190: `value: string | number`, `source_doc: string`, `confidence: number` (0..1, show as whole percent, never color).
- `ExtractedFacts`, lines 193-202: nine nullable facts.
- `DealSummary`, lines 205-217: `legal_name` is nullable (fall back to folder); `needed_by_badge` is `"none" | "ok" | "at_risk" | "overdue"`; `watch` is UI-only; `rm` is a staff id.
- `DealDetail`, lines 223-230: summary plus `facts, issues, resolved_issues, stage_log, human_requests, alerts, fraud`.
- `InboxItem`, lines 258-268: `status: "pending" | "answered"`; `options` has at least one entry.
- `InboxReply`, lines 282-284: `option` required, `note` optional.
- `Clock`, lines 89-92: `now, start, end`.

Use `import type` (TS 7 `verbatimModuleSyntax`). Do not use `enum` (TS `erasableSyntaxOnly`).

### `ui/src/api/schema.ts` (generated)

Generate with the mock running: `npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.ts`. Never hand-edit. Drift check: regenerate and `git diff --exit-code`.

### `ui/src/api/client.ts` (service, request-response)

**Analog:** `prism/api/app.py` for the request shape and error strings.

**Reply body** (`app.py` 110-123). The server accepts `{option}` only (`InboxReply` has `extra="forbid"`):
```ts
// Source: prism/api/app.py 110-123; prism/contract.py 282-284
export async function reply(itemId: string, option: string): Promise<void> {
  const res = await fetch(`/api/inbox/${encodeURIComponent(itemId)}/reply`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ option }),
  })
  if (!res.ok) throw new Error((await res.json()).detail ?? `HTTP ${res.status}`)
}
```

**Error mapping** (`app.py` lines): 404 `unknown deal` (91), 404 `unknown inbox item` (114), 409 `already answered` (116), 422 `option must be one of: ...` (118-120), 503 `engine not wired yet` (45). Display the `detail` string or a fixed message. Never show raw bodies or stack traces (RESEARCH Security V7).

**Folder paths:** always `encodeURIComponent(folder)`; `Mama Rosa's Kitchen` and `Bayou Bistro & Grill` break unencoded (verified 200 when encoded).

**Advance** (`app.py` 63-75): send `{ "to": "YYYY-MM-DDTHH:mm-06:00" }` only. `hours` is computed from `clock.json` on each call in mock mode, so it drifts.

### `ui/src/state/clockStore.ts` (store, event-driven)

**Analog:** `prism/api/app.py` 59-80, plus RESEARCH Pattern 1.

- Hold `now`, `start`, `end` in zustand. Load `GET /api/clock` once at startup. Never refetch it (it always returns 18:00).
- Apply changes locally first, clamp to `[start, end]`, then POST `{to}`.
- Replay sets `now = start` locally. `POST /api/clock/replay` may also be called; the response is ignored.
- `ClockAdvance` (contract 95-105) requires exactly one of `hours` or `to`.

### `ui/src/state/answersStore.ts` (store, event-driven)

**Analog:** `prism/api/app.py` 110-123. The mock returns the fixture `clock.now` as `answered_at` and stores nothing.

Overlay `{ [itemId]: { answer, answered_at: clock.now } }`. It must be applied **before** the status filter in `inboxAt`. The scratch `inboxAt` only trusts fixture `status === 'answered'`, so a UI-only answer would be treated as pending. Extend its signature to take the overlay map.

### `ui/src/data/queries.ts` (service, request-response)

**Analog:** `prism/api/app.py` 83-96 (`/deals`, `/deals/{folder}`), 102-108 (`/inbox`), and `/alerts` (94-96).

- Deals: `useQuery` on `/api/deals`. Detail: `useQueries` per folder on `/api/deals/{folder}` (no bulk detail endpoint; the derivation needs each `stage_log`).
- Defaults: `staleTime: Infinity`, `refetchOnWindowFocus: false`. Never make the clock a query.
- Do not write inbox replies into the Query cache (Pitfall 3).

### `ui/src/labels.ts` (config, transform)

**Analog:** `prism/contract.py` 23, 30-38, 43-50.

- Stage and RequestType enums as listed above.
- `ISSUE_RE` (43-50): issue strings are `MISSING_DOC:<doc>`, `MISSING_PAGE:<doc>`, `MISMATCH:<field>`, `OLD_TRICK:<code>`. Unknown strings fall back to the raw code.
- Plain-words maps are UI-only; the wire value never changes. Request labels: `credit_decision` = "Credit decision", `committee_approval` = "Committee approval", `commitment_signoff` = "Commitment sign-off", `funding_release` = "Funding release", `fraud_hold` = "Fraud hold", `fraud_release` = "Fraud release", `info_request` = "Borrower information request".
- Option labels: `approve`, `decline`, `request_info`, `confirm_hold`, `release_hold` (options come from `item.options` only).
- Recipient role labels (D-17): `credit_decision` = "Credit officer", `committee_approval` = "Committee approver", `commitment_signoff` = "Relationship manager", `funding_release` = "Closing and funding", `fraud_hold` and `fraud_release` = "Fraud Operations", `info_request` = "Borrower". Raw `to` id in a tooltip only.

### `ui/src/components/app/Inbox.tsx` (component)

**Analog:** `fixtures/inbox.json` for shape; `prism/api/app.py` 110-123 for allowed actions.

Render buttons from `item.options` only. Answered items show the answer in the row with no toast (D-20). Buttons are navy outline or navy primary, including fraud actions; no red.

### `ui/src/components/app/Badges.tsx` (component)

**Analog:** `prism/contract.py` 213 and 216.

| Value | Display | Color |
|-------|---------|-------|
| `needed_by_badge: none` | no badge | none |
| `ok` | neutral "Needed by {date}" | none |
| `at_risk` | "At risk" | amber |
| `overdue` | "Overdue" | amber (never red) |
| `held` (`fraud.held` at time t) | "Held: fraud review" plus reason | red (the only red) |
| `watch` | neutral "Watch" | none |

### `ui/src/components/app/States.tsx` (component)

**Analog:** `prism/api/app.py` 45 (503 "engine not wired yet") and the empty-board case from RESEARCH Pitfall 10.

Three shared states: loading, empty ("No deals have arrived as of Mon 11/02 8:00 AM CT."), and error (neutral ink, hairline border, lucide icon; never red). Error text: "The engine is not connected." for 503.

### `ui/src/components/app/DealDetail.tsx`, `Board.tsx`, `AlertsFeed.tsx`, `ClockBar.tsx`, `App.tsx`, `main.tsx`

No in-repo analog. Build from the spec:
- Board: six stage columns in `Stage` order; rows show legal name (or folder), amount, time in stage vs SLA, needed-by badge, hold/watch status.
- DealDetail: facts table with source-doc chip and confidence; issues and resolved issues in separate lists; stage log with each `why`; human requests; alerts. Caption facts and issues "Engine values for the run" (no timestamps; RESEARCH Pitfall 11).
- AlertsFeed: newest first (`alertsAt` already sorts).
- ClockBar: current sim time via `fmtSimTime`; +1 h, +6 h, +1 day, next event, replay.
- Layout is a left nav plus content switch with zustand `selectedFolder` (no router, D-02).

### `ui/src/index.css` (tokens)

**Spec:** CONTEXT D-03..D-08 and RESEARCH "Design Tokens" block (lines 337-379). Override tokens in `:root`; delete the template `.dark` block and the template purple accent (`#aa3bff`). Do not edit shadcn component files for colors.

Key tokens: `--background #FAF9F7`, `--primary #1B2A41` (only accent), `--destructive #B42318` (fraud hold only), `--sla #B54708` (amber), `--cleared #067647` (green), `--radius 0.375rem`, `--shadow-sm: none`.

### `ui/vite.config.ts` (config)

**Analog:** `prism/api/app.py` 31: `ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]`. Keep the dev server on 5173 so the mock's CORS allow-list matches.

Plugins `react()` and `tailwindcss()`; alias `@` to `./src`; `server.proxy` and `preview.proxy` `'/api'` to `http://localhost:8000`. Do not widen CORS.

### `ui/tsconfig.json`, `ui/tsconfig.app.json` (config)

Scaffold steps 1-2 in RESEARCH "Scaffold": root `tsconfig.json` needs `compilerOptions.paths` (`@/*`), or shadcn writes into `./@/`. Do not add `baseUrl` (TS 7 error TS5102). Keep `noUnusedLocals`.

## Shared Patterns

### Sim time (all screens)
**Source:** `ui/src/time/simtime.ts` (scratch lines 52-79)
**Apply to:** every component that shows a time or duration; every derivation.
Use `fmtSimTime` and `fmtDuration` only. No `toLocale*`, no local-zone `Date` methods.

### Engine strings are text (all screens)
**Source:** RESEARCH Pitfall 13 and Security V5/V7
**Apply to:** names, facts, messages, evidence, `why`, `reason`, `source_doc`, `linked_deals`.
Render as React text only. No `dangerouslySetInnerHTML`. Build no `href` from engine strings.

### Money, percent and count formatting
**Source:** RESEARCH "Don't Hand-Roll": `Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2, minimumFractionDigits: 0 })`
**Apply to:** `amount_requested`, facts with money fields, board rows. Apply `tabular-nums` class to every money, percent, count and time cell (D-06).

### Red reserved for holds (all screens)
**Source:** CONTEXT D-05 and D-20
**Apply to:** every badge, button and banner. Only `fraud.held` uses red. Amber for SLA above 100% and `at_risk` / `overdue`. Green only for cleared or approved outcomes.

### Loading, empty and error on every query (D-01)
**Source:** `ui/src/components/app/States.tsx` (above)
**Apply to:** board, detail, inbox, alerts, clock bar.

### Folder encoding
**Source:** `prism/api/app.py` 87-92 and RESEARCH Pitfall 9
**Apply to:** every URL that includes a folder or item id.

## Gaps and Conflicts for the Planner

1. **Hard-coded fixture path in the test.** Scratch `timeview.test.ts` line 6 uses `/Users/jes/Goldman-I/fixtures/`. Zeke is on Windows (CONTEXT environment notes), so this breaks. Replace with a path relative to the test file, for example `new URL('../../../fixtures/', import.meta.url)`, or pass the path through an env variable. Confirm the relative depth from `ui/src/time/`.
2. **`inboxAt` has no overlay parameter.** The scratch function filters on fixture `status`. Add the `answers` overlay argument and apply it before the status check (RESEARCH Pattern 3 says so; the reference code does not).
3. **Reference copy is not in the repo.** The scratch files are outside git. The executor must copy them into `ui/src/time/` and then run `node --test`.
4. **Staff ids vs names (D-14, D-17).** Five fixture ids are not in `contacts/teams.json`. Use role labels with ids in tooltips. Do not copy `data/participant/contacts/` content into `ui/`.
5. **No DBA field (D-15).** Show folder plus `legal_name`; `legal_name` can be null, so fall back to folder.
6. **Routing conflict in fixtures** (`inbox-002` to `committee.osei` for $410,000; `inbox-003/004` to `fraudops.keller`). The UI displays the value it receives; flag to Zeke, do not correct it in the UI.
7. **`fmtSimTime` throws on a non-matching string.** Wrap render-time calls at the data boundary so one bad fixture value does not blank the screen (D-01).
8. **Token and palette values** are Claude's discretion (CONTEXT). Contrast is computed in RESEARCH; keep those hex values.
9. **Serif** (D-06, D-19): Source Serif 4 needs the package checkpoint first. If not approved, use the system serif stack.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `ui/src/components/app/*.tsx` (layout and views) | component | request-response | No frontend in repo; build from CONTEXT specifics and D-tokens |
| `ui/src/App.tsx`, `ui/src/main.tsx` | component | event-driven | No frontend in repo |
| `ui/src/index.css` | tokens | n/a | No frontend in repo; use RESEARCH token block |
| `ui/vite.config.ts` and tsconfig | config | n/a | No frontend in repo; use RESEARCH scaffold steps |

## Metadata

**Analog search scope:** `prism/`, `fixtures/`, `tests/`, `docs/CONTRACT.md` (git-tracked), plus the scratch derive-check directory.
**Files scanned:** 14 repo files read or grepped (`prism/contract.py`, `prism/api/app.py`, `tests/test_contract.py`, `fixtures/clock.json`, `deals.json`, `inbox.json`, `alerts.json`, `deal_detail.json` (keys), and the two scratch files).
**Pattern extraction date:** 2026-11-07
