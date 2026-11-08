# 07-09 Progress (Sun 2026-11-08)

Tasks 1 and 2 are done. Task 3 (repository sharing decision) is pending and waits for Jesse. No SUMMARY.md yet.

| Task | State | Commit |
|---|---|---|
| 1. Cut outline to 3 minutes, built-screen demo, sourced placeholders | done | 7fa917d |
| 2. Eight-slide self-contained deck | done (no screenshots, see below) | 8846f72 |
| 3. Decide how the repository is shared with judges | pending, blocking-human, not decided here | none |

## Task 1 measurements

- Spoken-slide notes (slides 1, 2, 3, 5, 6, 7): 292 words (gate 300; was 535). About 1:57 at 150 words a minute.
- Demo Say column: 125 words (gate 150; was 190). About 0:50.
- Banned-phrase gate (no scrubber, bits against, evidence sheet, credit memo panel in the demo or slide visuals): passes.
- Names, history-id and tax-ID guard: passes on the outline, Devpost text and deck.

## Pending on unbuilt screens (tagged `[pending ...]` in the outline, Devpost text and deck)

- Fraud graph page and its evidence panel and cluster panel: 07-01, 07-03 (demo row 3; slides 2, 3, 4, 7).
- Family checklist on the cluster panel: 07-03 (slide 3 visual).
- Investigation panel: 07-04 (end of demo row 3; slide 6 visual).
- Red-team page: 07-05 (slide 6 visual).
- Committee approval request shows the memo's four-line version only on the live engine run (MOVE-10, 07-02). On mock data it is a one-sentence message. No memo panel exists.

## Task 2 state

- `docs/pitch/slides.html`: 8 sections, no network references, no banned effects, tags balanced.
- Screenshots: no browser tool was available to this session (no Playwright MCP, no Chrome), so `docs/pitch/img/` holds only `README.md` listing the five shots. The deck shows a labelled placeholder frame for each missing PNG. Take them from the mock API at 1440x900, never from the live run.
- The Task 2 human check (open at 1280x720, step through, print to PDF, Wi-Fi off) has NOT been done; layout was written blind and needs one visual pass.

## Placeholders still open

None are filled. As of Sun 02:30 CT the committed records do not exist (`eval/scorecard.md`, `eval/blind_drop_score.json`, `eval/blind_drop_record.json`, `eval/redteam_report.json`). The full list with sources is the table at the bottom of `docs/pitch/PITCH_OUTLINE.md`.

## Task 3 options (Jesse to choose)

- private: keep the repository private, submit with a private-access note (default if no answer by H18, Sun 09:55 CT).
- invite: keep it private and invite named judges or the organizer as collaborators (needs handles).
- code-only: publish a code-only copy as a new public repository with fresh history, from an allowlist (cannot be undone).
