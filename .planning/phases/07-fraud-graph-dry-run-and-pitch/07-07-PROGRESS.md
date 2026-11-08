# 07-07 Progress (not a SUMMARY; the plan is unfinished)

**Task 1 done** (script and tests), commit `1f031ac`: `scripts/seal_blind_run.py`, `tests/test_seal_blind_run.py`. Full suite: 361 passed.

Rehearsal on the sample (out/seal_rehearsal, gitignored): seal wrote the record (13 deals, 0 errors, validator ok, deterministic), a second seal was refused with exit 2, `eval/` untouched. Score mode was rehearsed too, against `eval/gold.json` into out/ only.

**Task 2 is waiting on the weekend drop.** It needs:
1. The drop unzipped under `data/drop/` with `__MACOSX/` removed. Nobody opens its files. Nothing shipped in the zip is run.
2. The drop's folder and arrivals file paths from the organizers' message (own zip plus arrivals, or files added to the sample folder with an updated arrivals file).
3. The H10 baseline tag, which must resolve to HEAD. If there is no tag yet, do not seal.
4. Clean `prism/` and `config/` (`git status --porcelain -- prism config` empty) and no `eval/gold_drop.json`.

Command:

    PYTHONUTF8=1 .venv/bin/python scripts/seal_blind_run.py seal --folder <drop folder> --arrivals <drop arrivals> --tag <H10 baseline tag> --record eval/blind_drop_record.json

Then commit only `eval/blind_drop_record.json` as `docs(07-07): sealed first run on engine <short commit>`, push, and tell Jesse he may open the drop and label (Task 3). Do not read `out/blind_drop/` until his labels are committed. After "labels committed": `scripts/seal_blind_run.py score`, commit `eval/blind_drop_score.json`, write `eval/drop_run_log.md`.

Note: the record's `command` field redacts any path under a folder named `data`.
