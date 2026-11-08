"""Issue detection (owner: Phase 3, READ-04).

Contract: return the FULL set of currently open ``KIND:target`` strings (valid per
``prism.contract.ISSUE_RE``), sorted. Applies the 30-sim-minute quiet rule: a doc that
could still arrive is not yet missing. The caller moves issues that disappear into
``resolved_issues``.
"""
from __future__ import annotations

from datetime import datetime

from prism.engine.config import Rules
from prism.engine.state import DealState


def detect_issues(state: DealState, rules: Rules, now: datetime) -> list[str]:
    """Return the sorted open issue set at ``now``. Stub: empty."""
    return []
