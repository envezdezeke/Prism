---
phase: 06-nemotron-agents
plan: 01
subsystem: agents
tags: [nemotron, client, record-replay]
requires: []
provides: [prism.agents.client, ChatClient]
affects: [prism/read/vl.py]
key-files:
  created: [prism/agents/__init__.py, prism/agents/client.py, tests/test_agents_client.py]
  modified: [prism/read/vl.py, tests/conftest.py]
decisions:
  - "ChatClient speaks OpenAI chat-completions over stdlib urllib (no openai package)"
status: complete
actuals:
  tasks: 2
  commits: 2
---

# Phase 6 Plan 01: Shared Nemotron client Summary

One shared client (`prism/agents/client.py`) owns modes, .env, the urllib transport, digest, record/replay cache and bounded retries. `prism/read/vl.py` delegates to it, and every name the tests use is still there. `ChatClient` adds OpenAI-format tool-calling chat, cached under hash(model, messages, tools, params).

## Commits
- b944f50 feat(06-01): shared client; VL delegates
- f36f473 test(06-01): ChatClient tests; conftest isolates PRISM_AGENT_CACHE_DIR / PRISM_AGENTS_DIR

## Verification
- tests/test_read_vl.py was not edited and all 101 tests pass. The engine literal and wall-clock guards pass.
- test_agents_client + test_read_vl + test_contract: 200 passed.
- The sample run with NEMOTRON_MODE=off and with replay gives byte-identical output (NEM01_BYTE_IDENTICAL).
- No `urlopen(` call is left in vl.py; client.py has 1.

## Deviations
- ChatClient went into the Task 1 commit together with the extraction (same file, written in one pass). Its tests are in the Task 2 commit.
- `post_chat` sets tool_choice to "auto" when tools are passed without a tool_choice.

## Self-Check: PASSED
