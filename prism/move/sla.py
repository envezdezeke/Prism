"""SLA timers and alerts (owner: Phase 4).

Contract: ``sla_pct`` is elapsed sim hours over the stage SLA (may exceed 1; frozen while
held). ``sla_alerts`` returns only alerts newly due at ``now``, each exactly once, in time
order. Times are wall-clock sim hours.
"""
from __future__ import annotations

from datetime import datetime

from prism.contract import Alert
from prism.engine.config import Rules
from prism.engine.state import DealState


def sla_pct(state: DealState, rules: Rules, now: datetime) -> float:
    """Fraction of the current stage SLA used at ``now``. Stub: 0.0."""
    return 0.0


def sla_alerts(state: DealState, rules: Rules, now: datetime) -> list[Alert]:
    """Alerts newly due at ``now``. Stub: empty."""
    return []
