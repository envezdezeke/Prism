# Prism handoff: Sat 2026-11-07 20:01 CT (H4.1)

HackUTD 2026, Goldman Sachs DealPilot + NVIDIA Nemotron. Repo: `C:\Users\ezeki\hack\prism` → github.com/envezdezeke/Prism (private, work on `main`). Hard deadline **Sun 12:00 CT** (submit 11:40). User = Ezekiel ("Zeke": engine, fraud, Nemotron). Teammate = Jesse (finance, UI, pitch; on a Mac; builds the UI with Claude Code).

## Read first (don't re-derive)
- `.claude/CLAUDE.md`: project rules (no Claude in the product, determinism, never commit `data/` or `.env`, Python path, PYTHONUTF8=1)
- `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`
- **`docs/MODEL_DESIGN.md`**: every settled fraud-model (M1–M21) and Nemotron (N1–N13) decision plus the playbooks. Math: `docs/model/prism_model.pdf` (`.tex` next to it; rebuild with MiKTeX `pdflatex -output-directory=build prism_model.tex` in `docs/model/`)
- `HANDOFF.md` (Jesse's): §5 questions for Vijay (J20 is the top one; #9 = run end time + who runs the hidden set), §9 open items. **Jesse just added §9 items 19–20 for Zeke** (a returning customer causing a false F1 link; `pdf_producer` as an F1 party). Read those.
- `docs/DETAILS_CHECKLIST.md` (rules + J1–J22), `docs/CONTRACT.md` (API), `docs/UI_PLAYBOOK.md` (Jesse's agents), `eval/README.md` + `eval/gold.json` (answer key, all 13 deals done)

## State
- Done and on main: the API contract + mock fixtures (quick 261107-pfc); the engine skeleton with CLI `python -m prism run|validate|score` (261107-qez); the fraud baseline F1/F3/F5 + calibration + Jul–Oct replay (261107-qx4, merged `d5216d7`); run end = last arrival + 30 min (`8a51b18`). 221 tests passed at the last merge. Empty-engine self-score: 12/117 facts.
- **UPDATE 20:06: Move core is MERGED** (`8bbd3db`, 353 tests passing, the real run validates, the worktree and branch removed, local main synced with origin). Skip the merge steps below. Its hand-off notes still apply. Its SUMMARY is at `.planning/quick/261107-qx3-*/261107-qx3-SUMMARY.md` (items 1–15). The default persona is `fast` (`PRISM_MOVE_PERSONA` switches it; that's a J20 decision).
- Its planner's hand-off notes, for Read and Phase 5: it uses a `_move` runtime attr on DealState; `credit_memo` needs adding to the contract's `DealDetail`; Read must fill `legal_name`/`amount_requested` (or Intake never exits), `features["profile"]` and `vendor_verified`; fraud must set `flagged_at`; superseded inbox items carry the answer "superseded", which `InboxItem` would reject unless filtered.
- GSD config: `workflow.use_worktrees=false` (sequential by default). For *parallel* background executors, dispatch with Agent `isolation: "worktree"` after first committing and pushing the PLAN (worktrees branch from origin). `.claude/worktrees/` is gitignored.

## Fraud baseline findings (decide in Phase 5, after F2/F4 exist)
Replay on 72 good Jul–Oct deals: **1 false flag** (a lower bound). F1 fires on ~30% of clean deals (returning guarantors, shared real vendors), F3 on 11% (τ_F3 = 0 bits, since only 3 of 104 clean deals have a lookalike). Proposed generic fixes, not yet decided:
1. A guarantor counts for F1 only across *different* businesses.
2. Drop vendor *name* from F1's strong set and keep the remit account.
3. Give F3 a floor. This matches Jesse's new §9 item 19.
Details are in `.planning/quick/261107-qx4-*/261107-qx4-SUMMARY.md`.

## Next steps (priority order)
1. Pull (Move core is already merged).
2. **Phase 3, Read the folder (critical path, Zeke's):** `/gsd-plan-phase 3`. It includes the Nemotron VL fallback (N2/N10: fill nulls only, format + cross-doc check, cached, ≤ 30 calls, never creates issues or holds). It must fill `features["deposit_months"]` (keys `deposit_count`, `pct_deposits_multiple_of_100`, `deposit_weekdays`) plus `vendor`/`remit_account` EntityRefs for fraud, and the Move inputs above.
3. Phase 5 proper: `decide()` hold rule (F1 + ≥ 2 of F2–F5, sticky), clusters, `history_flags` (≥ 2 links), F2, F4, the M13 thresholds in the output, `prism eval` scorecard. Target **H10 freeze around 01:30–02:00**.
4. Phase 6 Nemotron after the freeze (adaptive red-team headline, prosecutor/defender, cut order N13).

## Pending user decisions / open offers
- **Add a repo-root `AGENTS.md`** pointing to the `.claude/CLAUDE.md` rules so Antigravity (`agy`) follows them? Offered, no answer yet.
- The user was given Antigravity setup commands (gh CLI, `npx -y @opengsd/gsd-core@latest --global --agy`, copying grilling → `~/.gemini/config/skills/{grilling,grill-me}`, the anthropics/skills frontend-design + webapp-testing, the shadcn MCP in `~/.gemini/config/mcp_config.json`). Whether they ran them is unknown. Warn against two tools editing the same files at once.
- Organizer answers still pending (Jesse asks Vijay): J20, the judged run end time, who runs the hidden set.

## Environment gotchas
- Python: `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe`, `PYTHONUTF8=1`. `gh` isn't installed (use curl for public GitHub API, or git). Downloading and running outside binaries gets blocked by the auto-mode classifier; ask the user.
- Run (real data): `python -m prism run --folder data/participant/shared_folder --arrivals data/participant/sim/arrivals.jsonl --out out/submission.json`, then `validate out/submission.json --folder data/participant/shared_folder`, then `score out/submission.json --gold eval/gold.json`.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Always pull --rebase before pushing; Jesse pushes often. The NVIDIA key is in `.env`; never print it.

## Suggested skills
- `gsd-progress`: re-orient at the start of the session
- `gsd-plan-phase` (then `gsd-execute-phase`): Phase 3 Read
- `gsd-quick`: Phase 5 pieces and integration fixes (the pattern used all evening)
- `grilling`: if the Phase 5 F1/F3 fixes or Nemotron scope need deciding
- `gsd-code-review` / `gsd-audit-fix`: before the H10 freeze
