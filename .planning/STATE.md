---
gsd_state_version: '1.0'
status: planning
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
**Current focus:** Phase 1: Foundations, Contract and Golden Labels (both). Phase 2 (Jesse's UI on mock data) opens at H1.

## Current Position

Phase: 1 of 7 (Foundations, Contract and Golden Labels)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-11-07 15:55 CT (H0): roadmap created, 7 phases, 48/48 v1 requirements mapped

Progress: [░░░░░░░░░░] 0%

Clock: H0 = Sat 2026-11-07 15:55 CT. Hard deadline Sun 2026-11-08 12:00 CT; submit target 11:40 (H19.75). Full hour-by-hour table: ROADMAP.md "Who's doing what, when".

## Who Owns What

| Phase | Owner | Window | Status |
|-------|-------|--------|--------|
| 1. Foundations, Contract and Golden Labels | Ezekiel (engine, contract) + Jesse (golden labels) | H0–H2 | Ready to plan |
| 2. Pipeline Cockpit UI on Mock Data | Jesse | H1–H9 | Opens when the contract lands (H1) |
| 3. Read the Folder | Ezekiel | H2–H5 | Not started |
| 4. Move the Deal | Ezekiel | H5–H7.5 | Not started |
| 5. Catch the Fakes | Ezekiel | H7.5–H10 | Not started |
| 6. Nemotron Agents | Ezekiel | H10.5–H15.5 | Not started |
| 7. Fraud Graph, Dry Run and Pitch | Jesse lead, Ezekiel from H15.5 | H9–H19.75 | Not started |

## Right Now and Next

**Ezekiel, now:** plan and start Phase 1. The first deliverable is the API contract plus mock fixtures, due to Jesse at H1 (Sat 16:55).

**Jesse, now:** write the golden labels for the 13 sample deals into `eval/gold.json`, due at H2 (Sat 17:55). Per deal: expected facts, issues, who each sign-off goes to, hold or no hold, linked deals, `history_flags`. The exact file shape comes with the Phase 1 plan; start with per-deal notes. You need the data pack at `data/participant/` on your machine; it is not in git, so get it from Ezekiel. From H1, start Phase 2 against the mock fixtures; it does not wait on the engine.

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
- Hosted Nemotron tool calling and rate limits (community-reported 40 requests per minute) are unverified until the Phase 1 smoke test.
- Research file counts disagree (167 vs 146 files; 173 arrivals vs 186 files); Phase 1 inventories them.
- PROJECT.md notes the remote repo already has a commit; pull before the first push.
- H5–H10 (Phases 4 and 5) is the tightest stretch. FRD-01/FRD-02 can start alongside Phase 4 once Phase 3 lands.

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
- **Jesse:** get a second NVIDIA key (doubles the rate limit). Update your remote with `git remote set-url origin https://github.com/envezdezeke/Prism.git`.
- **Rotate Ezekiel's NVIDIA key after the hackathon.** It was pasted into a chat log.
- **GSD model profile is now `budget`** (Sonnet writes, Haiku researches), to save usage.
- **Jesse's `docs/DETAILS_CHECKLIST.md` J1–J20 are locked judgment calls.** They agree with PROJECT.md's Key Decisions. Items marked "Vijay?" are still open; J20 (how judges answer staff requests) is top priority.
