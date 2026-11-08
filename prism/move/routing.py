"""Gate routing (owner: Phase 4).

Contract: return the teams.json person id that should receive the human gate
(``credit_decision``, ``committee_approval``, ...) for this deal at ``now``, or None when
the deal should never reach that gate. Backups and thresholds come from the rules data.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from prism.engine.config import Rules
from prism.engine.state import DealState


def route_gate(gate_type: str, state: DealState, rules: Rules, now: datetime) -> Optional[str]:
    """Return a teams.json id or None. Stub: None."""
    return None
