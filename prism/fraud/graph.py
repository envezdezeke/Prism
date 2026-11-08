"""Entity graph over deals and history (owner: Phase 5).

Contract: built from the DealState entities visible now plus the baseline; pure and
deterministic (sorted iteration, no randomness).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from prism.engine.state import DealState, EntityRef
from prism.fraud.baseline import Baseline


@dataclass
class EntityGraph:
    deal_entities: dict[str, list[EntityRef]] = field(default_factory=dict)


def build_graph(states: Mapping[str, DealState], baseline: Baseline) -> EntityGraph:
    """Return the entity graph. Stub: empty."""
    return EntityGraph()
