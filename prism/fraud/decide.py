"""Hold decision (owner: Phase 5, M8, M17, M18).

Contract: ``decide`` is sticky (a hold is never undone by weaker later evidence).
``evaluate`` = build_graph -> compute_signals -> decide and is the ONLY call run.py makes.
``FraudOutcome.per_deal`` holds a Fraud block for every deal it wants to change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, Sequence

from prism.contract import FAMILY_LABELS, Cluster, Fraud, format_sim_time, parse_sim_time
from prism.engine.config import FraudConfig
from prism.engine.state import PIPELINE, DealState
from prism.fraud.baseline import Baseline
from prism.fraud.graph import EntityGraph, build_graph
from prism.fraud.signals import LINK_MARK, FamilySignal, compute_signals

_REASON_HEAD = "Held by the cross-deal fraud screen."


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
    """Apply the hold rule to the signals, tick by tick, with sticky holds (M17).

    A deal is flagged and held when every family in ``cfg.hold_required`` fired and at
    least ``cfg.hold_min_additional`` fired families come from ``cfg.hold_additional_from``
    (families in ``cfg.non_voting`` never count). A flag, once set, is carried forward from
    ``states[folder].fraud`` unchanged except for ``linked_deals``. ``states`` is not mutated.
    """
    fired: dict[str, dict[str, FamilySignal]] = {}
    for sig in signals:
        if not sig.fired or not sig.deals:
            continue
        by_family = fired.setdefault(sig.deals[0], {})
        if sig.family not in by_family:
            by_family[sig.family] = sig

    out = FraudOutcome()
    for folder in sorted(states):
        state = states[folder]
        fams = fired.get(folder, {})
        partners = _current_partners(folder, fams, states, cfg)
        prev = state.fraud
        if prev.flagged:
            links = sorted(set(prev.linked_deals) | set(partners))
            out.per_deal[folder] = prev.model_copy(update={"linked_deals": links})
            continue
        voting = {f: s for f, s in fams.items() if f not in cfg.non_voting}
        if not _hold_met(set(voting), cfg):
            continue
        out.per_deal[folder] = Fraud(
            flagged=True,
            held=True,
            flagged_at=format_sim_time(now),
            stage_at_flag=stage_in_force(state, now),
            reason=build_reason(voting),
            linked_deals=partners,
        )
    return out


def _hold_met(families: set[str], cfg: FraudConfig) -> bool:
    if not all(f in families for f in cfg.hold_required):
        return False
    extra = sum(1 for f in families if f in cfg.hold_additional_from)
    return extra >= cfg.hold_min_additional


def _current_partners(
    folder: str, fams: Mapping[str, FamilySignal], states: Mapping[str, DealState], cfg: FraudConfig
) -> list[str]:
    """Partners of the deal's required-family signals that are current deals (not history)."""
    out: set[str] = set()
    for fam in cfg.hold_required:
        sig = fams.get(fam)
        if sig is None:
            continue
        out.update(p for p in sig.deals[1:] if p in states and p != folder)
    return sorted(out)


def stage_in_force(state: DealState, t: datetime) -> str:
    """Stage of the last stage_log entry entered at or before ``t``; the first stage if none.

    Reads the log, never ``state.stage``: Move may already have advanced the deal this tick.
    """
    stage = PIPELINE[0]
    best: datetime | None = None
    for entry in state.stage_log:
        entered = parse_sim_time(entry.entered_at)
        if entered <= t and (best is None or entered >= best):
            best = entered
            stage = entry.stage
    return stage


def build_reason(voting: Mapping[str, FamilySignal]) -> str:
    """Plain-words reason: a head sentence, then one sentence per fired voting family.

    F1-style evidence is cut at LINK_MARK so partner ids never appear in the reason.
    Built by concatenation (no format() on document-derived text).
    """
    parts = [_REASON_HEAD]
    for fam in sorted(voting):
        evidence = voting[fam].evidence.partition(LINK_MARK)[0].strip().rstrip(".")
        label = FAMILY_LABELS.get(fam, fam)
        label = label[:1].upper() + label[1:]
        parts.append(label + ": " + evidence + ".")
    return " ".join(parts)


def evaluate(
    states: Mapping[str, DealState], baseline: Baseline, cfg: FraudConfig, now: datetime
) -> FraudOutcome:
    """build_graph -> compute_signals -> decide."""
    graph = build_graph(states, baseline)
    signals = compute_signals(graph, states, baseline, cfg, now)
    return decide(signals, graph, states, baseline, cfg, now)
