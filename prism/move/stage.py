"""Stage machine (owner: Phase 4, MOVE-01..).

Contract: ``step_deal`` mutates the state in place (stage, stage_entered_at, stage_log,
human_requests, alerts). A fraud hold blocks any advance. Called once per tick for every
deal without an error.
"""
from __future__ import annotations

from datetime import datetime

from prism.engine.config import Rules
from prism.engine.state import DealState


def step_deal(state: DealState, rules: Rules, now: datetime) -> None:
    """Advance the deal as far as the rules allow at ``now``. Stub: no-op."""
    return None
