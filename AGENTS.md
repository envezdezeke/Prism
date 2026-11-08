# Prism – Agent Rules

All AI coding agents (Antigravity, Claude Code, Codex, etc.) **must** follow the
rules in [`.claude/CLAUDE.md`](.claude/CLAUDE.md) before making any changes.

Key non-negotiables:
- **No Claude in the product** – use Nemotron + deterministic code.
- **Determinism** – every scored field comes from deterministic code; Nemotron is advisory only.
- **Never commit** `data/`, `.env`, or secrets.
- **Python path**: `C:/Users/ezeki/AppData/Local/Programs/Python/Python313/python.exe` (set `PYTHONUTF8=1`).
- **Generalization** – no sample-specific literals in detection logic.
- **Time semantics** – sim time, America/Chicago (−06:00); only see files after `arrive_at`.
- Read `.planning/STATE.md` and `.planning/ROADMAP.md` for current project state.
- Read `docs/MODEL_DESIGN.md` for all fraud-model (M1–M21) and Nemotron (N1–N13) decisions.
- Commits use `Co-Authored-By:` trailer. Always `git pull --rebase --autostash` before pushing.

## Start here
1. `git pull --rebase --autostash`
2. Read `docs/SESSION_HANDOFF.md` (where we are, next steps, gotchas), then `.planning/STATE.md`.
3. The next job is **Phase 3 (Read)**. The fields it must hand to Move and Fraud are listed in the handoff.

## How to work (keep the robustness)
- **One small task at a time.** Write a short plan in `.planning/quick/<YYMMDD>-<slug>/PLAN.md` (goal, files, tests, done-when) before coding, and a `SUMMARY.md` after. Follow the pattern of the existing quick tasks there.
- **Tests first for engine code.** Function signatures are pinned in `tests/`. Don't change a pinned signature or delete a test to make it pass.
- **Every change has to pass this gate before you commit:**
  ```bash
  PYTHONUTF8=1 python -m pytest -q
  python -m prism run --folder data/participant/shared_folder --arrivals data/participant/sim/arrivals.jsonl --out out/submission.json
  python -m prism validate out/submission.json --folder data/participant/shared_folder
  python -m prism score out/submission.json --gold eval/gold.json
  ```
  The score must not go down. Report the before and after numbers in the SUMMARY.
- **Don't re-decide settled questions.** Model decisions M1–M21 and N1–N13 in `docs/MODEL_DESIGN.md` are final unless Zeke says otherwise.
- **Never** hard-code deal names, people or amounts from the sample data in detection logic. Never print `.env`.
- Commit small and often, with a clear message. Pull before you push; Jesse pushes often. Don't edit `ui/` (that's Jesse's).
