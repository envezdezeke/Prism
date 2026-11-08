"""Signal families F1-F6 in bits of surprise (owner: Phase 5, M1, M7, M8).

Contract: one FamilySignal per fired-or-evaluated family per deal group; F6 is evidence
only and never votes. Thresholds come from ``FraudConfig`` percentiles, not literals.

Built so far: F1 (shared rare entity), F3 (lookalike vendor or account) and F5 (deposit
pattern). F2, F4 and F6 are not built.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional

from prism.engine.config import FraudConfig
from prism.engine.state import DealState
from prism.fraud.baseline import Baseline, DealProfile
from prism.fraud.graph import EntityGraph
from prism.fraud.rarity import FraudParams, is_strong, outcome_discount, surprisal


@dataclass(frozen=True)
class FamilySignal:
    family: str
    deals: tuple[str, ...]
    bits: float
    fired: bool
    evidence: str


# ------------------------------------------------------------------------------- F1

@dataclass(frozen=True)
class F1Result:
    bits: float  # max pair score over partners
    partners: tuple[str, ...]  # partners with a positive pair score, sorted by id
    shared: tuple[tuple[str, str, int], ...]  # strong shared (kind, value, history df)
    n: int  # history deals the rarity was judged against


def score_f1(
    profile: DealProfile,
    baseline: Baseline,
    params: FraudParams,
    *,
    exclude: Optional[str] = None,
    others: Optional[Mapping[str, DealProfile]] = None,
) -> Optional[F1Result]:
    """F1: max pair score ``sum w * omega * I`` over partners sharing strong entities.

    ``others`` maps other current deal ids to their profile; ``exclude`` is a history id to
    leave out (leave-one-out). None when n is 0 or no strong shared entity exists.
    """
    n = baseline.n_effective(exclude)
    if n <= 0:
        return None
    others = others or {}
    pair: dict[str, float] = {}
    shared: list[tuple[str, str, int]] = []
    for kind in sorted(profile.entities):
        for value in profile.entities[kind]:
            df, repaid, _first, _last = baseline.entity_stats(kind, value, exclude)
            current = sorted(
                oid for oid, op in others.items()
                if oid != profile.deal_id and value in op.entities.get(kind, ())
            )
            links = 1 + df + len(current)
            if not is_strong(df, n, links, params.rho, params.min_linked):
                continue
            partners = baseline.deals_with(kind, value, exclude) + current
            if not partners:
                continue
            contrib = (
                params.weight(kind)
                * outcome_discount(repaid, df, params.outcome_beta)
                * surprisal(df, n)
            )
            for p in partners:
                pair[p] = pair.get(p, 0.0) + contrib
            shared.append((kind, value, df))
    positive = sorted(p for p, s in pair.items() if s > 0)
    if not shared or not positive:
        return None
    return F1Result(
        bits=max(pair[p] for p in positive),
        partners=tuple(positive),
        shared=tuple(shared),
        n=n,
    )


def _plain(kind: str) -> str:
    return kind.replace("_", " ")


def _f1_evidence(res: F1Result) -> str:
    parts = [
        f"{_plain(k)} used by {df} of {res.n} history deals" for k, _v, df in res.shared
    ]
    return "shared rare " + "; ".join(parts) + "; linked to " + ", ".join(res.partners)


# ------------------------------------------------------------------------------ driver

def compute_signals(
    graph: EntityGraph,
    states: Mapping[str, DealState],
    baseline: Baseline,
    cfg: FraudConfig,
    now: datetime,
) -> list[FamilySignal]:
    """Return the family signals at ``now`` (``now`` is unused so far), sorted by (folder, family)."""
    params = baseline.params
    out: list[FamilySignal] = []
    for folder in sorted(graph.profiles):
        profile = graph.profiles[folder]
        f1 = score_f1(profile, baseline, params, others=graph.profiles)
        if f1 is not None:
            out.append(
                FamilySignal("F1", (folder,) + f1.partners, f1.bits, True, _f1_evidence(f1))
            )
    return out
