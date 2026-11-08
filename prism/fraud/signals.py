"""Signal families F1-F6 in bits of surprise (owner: Phase 5, M1, M7, M8).

Contract: one FamilySignal per fired-or-evaluated family per deal group; F6 is evidence
only and never votes. Thresholds come from ``FraudConfig`` percentiles, not literals.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from prism.engine.config import FraudConfig
from prism.engine.state import DealState
from prism.fraud.baseline import Baseline
from prism.fraud.graph import EntityGraph


@dataclass(frozen=True)
class FamilySignal:
    family: str
    deals: tuple[str, ...]
    bits: float
    fired: bool
    evidence: str


def compute_signals(
    graph: EntityGraph,
    states: Mapping[str, DealState],
    baseline: Baseline,
    cfg: FraudConfig,
    now: datetime,
) -> list[FamilySignal]:
    """Return the family signals at ``now``. Stub: empty."""
    return []
