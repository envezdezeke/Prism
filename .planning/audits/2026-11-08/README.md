# Audits, Sun 2026-11-08 (~01:00-02:30 CT)

Read-only audits run by Jesse's Claude Code session. No repo code was changed by them.

| Report | Scope |
|---|---|
| SUBMIT-AUDIT.md | Self-score on the sample, determinism, time gate, hard constraints, secrets/confidentiality, clean checkout, API |
| MOVE-AUDIT.md | Pipeline engine vs data/participant/rules/stages.json (routing, SLA ladder, needed-by, memo, HANDOFF §9) |
| FRAUD-REDTEAM.md | Evasion and false-hold attacks on F1/F3/F5 and the MODEL_DESIGN hold rule |

The scripts folders hold the repro scripts the reports cite. They read data/ locally and wrote their
outputs to a scratch folder; generated JSON outputs (which contain sample data) are deliberately not committed.
Run from the repo root with `PYTHONUTF8=1 .venv/bin/python <script>`; some scripts expect a scratch output
directory, so check the path at the top of each script before running.
