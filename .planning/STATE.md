---
gsd_state_version: "1.0"
current_phase: 1
current_phase_name: Foundations, Contract and Golden Labels
status: planning
stopped_at: Planning complete; next is `/gsd-plan-phase 1`
last_updated: "2026-11-08T01:49:41.005Z"
last_activity: "2026-11-07 19:22 CT - Completed quick task 261107-qez: engine skeleton (arrival gate, CLI run/validate/score, determinism, stub interfaces for read/move/fraud). Phase 1 engine work done; NEM-02 VL smoke folded into Phase 3 (N10)."
state_head: d5216d763865f22b3134cc52a5b7fb3069f48ab0
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-07)

**Core value:** Catch the cross-deal fraud ring before money goes out, without blocking good deals, using a method that still works on the hidden set's different trick.
**Current focus:** Phase 1 work is done (contract, fixtures, engine skeleton, validator, self-score, golden labels). Ezekiel: Phase 5 history baseline (quick task 261107-qx4), Phases 3-4 in parallel. Jesse: Phase 2 UI (planned, design contract written, not yet executed).

## Current Position

Phase: 1 of 7 (Foundations, Contract and Golden Labels)
Plan: 0 of TBD in current phase
Status: Phase 1 work delivered through quick tasks (pfc, qez); Phase 2 planned (02-01..02-04 + 02-UI-SPEC), execution next
Last activity: 2026-11-07 ~20:10 CT - Merged quick task 261107-qx4 (fraud baseline, F1/F3/F5 + calibration; Jul-Oct replay: 1/72 good-deal false flags as lower bound, F1 fires on ~30% of clean deals). Move core (261107-qx3) still running in a worktree.

Progress: [░░░░░░░░░░] 0%

Clock: H0 = Sat 2026-11-07 15:55 CT. Hard deadline Sun 2026-11-08 12:00 CT; submit target 11:40 (H19.75). Full hour-by-hour table: ROADMAP.md "Who's doing what, when".

## Who Owns What

| Phase | Owner | Window | Status |
|-------|-------|--------|--------|
| 1. Foundations, Contract and Golden Labels | Ezekiel (engine, contract) + Jesse (golden labels) | H0–H2 | Delivered via quick tasks |
| 2. Pipeline Cockpit UI on Mock Data | Jesse | H1–H9 | Planned, executing next (behind schedule) |
| 3. Read the Folder | Ezekiel | H2–H5 | Not started |
| 4. Move the Deal | Ezekiel | H5–H7.5 | Not started |
| 5. Catch the Fakes | Ezekiel | H7.5–H10 | Not started |
| 6. Nemotron Agents | Ezekiel | H10.5–H15.5 | Not started |
| 7. Fraud Graph, Dry Run and Pitch | Jesse lead, Ezekiel from H15.5 | H9–H19.75 | Not started |

## Right Now and Next

**Ezekiel, now:** contract + mock fixtures (261107-pfc) and engine skeleton + validator + determinism + self-score (261107-qez) delivered; 168 tests pass on Jesse's Mac (Sat 19:38). Sample run: 13 deals, 173 files, 0 errors, byte-identical, valid. Next: fraud history baseline F1/F3/F5 + calibration (261107-qx4, planned 19:35), then Phases 3-4. VL read of Tyler's JPG folded into Phase 3.

**Jesse, now:** golden labels delivered Sat 18:29: `eval/gold.json` has all 13 deals `done`, plus `history_flags` and a 20-id `history_must_not_flag`. Labelled blind, then diffed against the research with zero disagreements on issues, holds or links. Judgment calls J1–J20 are locked in `docs/DETAILS_CHECKLIST.md`. Judgment calls J1–J22 all decided. Credit memo template and message templates delivered (~18:40/18:45). Jesse keeps the UI: Phase 2 plans 02-01..02-04 (19:29) and design contract 02-UI-SPEC (19:3x) committed; staff shown as role labels until the engine supplies names (D-22). Next: execute Phase 2. Also owed: `eval/trick_menu.yaml` before Zeke's first synthetic calibration (MODEL_DESIGN M5).

**Next hand-offs and gates:**
- H1 (Sat 16:55): contract + mock fixtures, Ezekiel to Jesse
- H2 (Sat 17:55): golden labels, Jesse to Ezekiel
- H10 (Sun 01:55): engine baseline frozen; UI flips from mock to live by H10.5; live graph endpoint
- H15.5 (Sun 07:25): Nemotron investigator + red-team working; trace and red-team endpoints live
- H18 (Sun 09:55): feature freeze
- H18–H19.75: dry run on a simulated weekend drop, demo recording, pitch; H19.75 (Sun 11:40) submit; hard deadline 12:00
- Weekend drop: arrival time unknown; 90-minute drop-response slot (ROADMAP.md "Drop response slot")

**If a gate slips, cut in this order:** UI polish, then Nemotron prose/VL, then red-team, then investigator. Never cut the engine, validator, determinism harness or trap suite.

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Full log in the PROJECT.md Key Decisions table. Most load-bearing right now:

- Roadmap: NEM-02 (Nemotron smoke test) moved into Phase 1 so hosted tool calling is proven before Phase 6 depends on it.
- Roadmap: the live API ships in Phase 4 on the Phase 1 contract, so the H10 mock-to-live switch is a flag flip.
- The deterministic engine owns every scored output; `NEMOTRON=off` must reproduce it byte for byte.
- Hold = F1 shared rare entity + at least 2 other families; 1–2 families = watch tier; no sample literals in detection code.

### Pending Todos

None yet.

### Blockers/Concerns

- The organizers have not yet said how judges send human answers or how drops arrive during judging. The inbox plus scripted personas cover both cases meanwhile.
- Weekend drop arrival time is unknown; the drop-response slot is reserved.
- Hosted Nemotron tool calling is verified on our key (see loose ends below); the VL read of Tyler's JPG and the rate limit (community-reported 40 RPM) are still unverified.
- ~~Research file counts disagree~~ Resolved 2026-11-07: 173 files on disk = 173 arrivals (167 PDF, 5 CSV, 1 JPG); no file arrives that isn't on disk and vice versa.
- H5–H10 (Phases 4 and 5) is the tightest stretch. FRD-01/FRD-02 can start alongside Phase 4 once Phase 3 lands.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261107-pfc | API contract + mock fixtures (FND-07, I1) | 2026-11-07 | 9712cde | [261107-pfc-api-contract-mock-fixtures-fnd-07-i1](./quick/261107-pfc-api-contract-mock-fixtures-fnd-07-i1/) |
| 261107-qez | Engine skeleton + validator + determinism + self-score (FND-01..06, FND-08) | 2026-11-07 | 7838de3 | [261107-qez-engine-skeleton-validator-determinism-se](./quick/261107-qez-engine-skeleton-validator-determinism-se/) |
| 261107-qx4 | Fraud baseline: history index, F1/F3/F5 bits, calibration, Jul-Oct replay report (FRD-01, FRD-02) | 2026-11-07 | d5216d7 | [261107-qx4-fraud-baseline-history-index-rarity-depo](./quick/261107-qx4-fraud-baseline-history-index-rarity-depo/) |

## Deferred Items

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-11-07 (Ezekiel, planning session)
Stopped at: Planning complete; next is `/gsd-plan-phase 1`
Resume file: None

**Loose ends from the planning session:**
- **Folder rename pending.** Exit Claude Code, then `cd C:\Users\ezeki\hack && ren "Goldman I" Prism && cd Prism && claude`. The git remote already points to `github.com/envezdezeke/Prism`.
- **After the rename,** disable unused account connectors for this project: `/mcp disable` for claude.ai Google Drive, Google Calendar, S&P Global and Claude Docs.
- **Nemotron key verified (Ezekiel's account).**
  - Working models, all with native tool calling: `nemotron-3.5-super-vl-120b-a12b` (agents + VL), `nemotron-3.5-lightning-30b-a3b` (fast), `nemotron-3-nano-omni-30b-a3b-reasoning` (VL fallback), `nemotron-3.5-bolt-e4b` (tiny).
  - `nemotron-3-super-120b-a12b` and `nemotron-nano-3-30b-a3b` return 404 on our tier.
  - The NEM-02 tool-call part is effectively done. Only the VL read of Tyler's JPG is left to check in Phase 1.
- **Jesse:** get a second NVIDIA key (doubles the rate limit). Remote already updated to `github.com/envezdezeke/Prism`.
- **Revoke Jesse's first NVIDIA key.** It was pasted into a chat log on Sat; make a new one and put it only in `.env`.
- **Rotate Ezekiel's NVIDIA key after the hackathon.** It was pasted into a chat log.
- **GSD model profile is now `budget`** (Sonnet writes, Haiku researches), to save usage.
- **Jesse's `docs/DETAILS_CHECKLIST.md` J1–J22 are locked judgment calls.** They agree with PROJECT.md's Key Decisions. Items marked "Vijay?" are still open; J20 (how judges answer staff requests) is top priority.
