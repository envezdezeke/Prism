"""Hold decision (owner: Phase 5, M8, M17, M18).

Contract: ``decide`` is sticky (a hold is never undone by weaker later evidence).
``evaluate`` = build_graph -> compute_signals -> decide and is the ONLY call run.py makes.
``FraudOutcome.per_deal`` holds a Fraud block for every deal it wants to change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Sequence

from prism.contract import Cluster, Fraud
from prism.engine.config import FraudConfig
from prism.engine.state import DealState
from prism.fraud.baseline import Baseline
from prism.fraud.graph import EntityGraph, build_graph
from prism.fraud.signals import FamilySignal, compute_signals


@dataclass
class FraudOutcome:
    per_deal: dict[str, Fraud] = field(default_factory=dict)
    history_flags: list[str] = field(default_factory=list)
    clusters: list[Cluster] = field(default_factory=list)


def decide(
    signals: Sequence[FamilySignal],
    graph: EntityGraph,
    states: Mapping[str, DealState],
    baseline: Baseline,
    cfg: FraudConfig,
    now: datetime,
) -> FraudOutcome:
    """Apply the hold rule to the signals. Stub: empty outcome."""
    return FraudOutcome()


def evaluate(
    states: Mapping[str, DealState], baseline: Baseline, cfg: FraudConfig, now: datetime
) -> FraudOutcome:
    """build_graph -> compute_signals -> decide."""
    graph = build_graph(states, baseline)
    signals = compute_signals(graph, states, baseline, cfg, now)
    return decide(signals, graph, states, baseline, cfg, now)
