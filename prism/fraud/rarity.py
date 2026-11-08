"""Pure rarity math in bits of surprise (owner: Phase 5; M1, M7).

M1: every signal is ``bits = -log2 P(observation | clean history)`` with +1 smoothing, so
nothing is ever zero: ``p_hat(v) = (df + 1) / (N + 1)``.
M7: an entity is strong iff ``df / N < rho`` (2% in config) and it links at least two deals;
the pair score of two deals sums ``w_type * omega_v * I(v)`` over their shared strong
entities, with ``omega_v = 1 - beta * (repaid + 1) / (df + 2)`` discounting values whose
history deals repaid.

No I/O and no Baseline import: ``FraudParams`` is built once from ``FraudConfig.raw``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping, Optional

from prism.engine.config import ConfigError, FraudConfig

DEFAULT_TYPE_WEIGHT = 1.0


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


@dataclass(frozen=True)
class FraudParams:
    rho: float = 0.02
    min_linked: int = 2
    type_weights: dict[str, float] = field(default_factory=dict)
    default_type_weight: float = DEFAULT_TYPE_WEIGHT
    outcome_beta: float = 0.0
    percentiles: dict[str, float] = field(default_factory=dict)
    train_end: date = date.max
    test_start: date = date.min
    test_end: date = date.max

    def weight(self, kind: str) -> float:
        return self.type_weights.get(kind, self.default_type_weight)

    @classmethod
    def from_config(cls, cfg: Optional[FraudConfig]) -> "FraudParams":
        """Read typed fields plus the additive keys in ``cfg.raw`` (defaults when absent)."""
        if cfg is None:
            return cls()
        fams = (cfg.raw or {}).get("families") or {}
        f1 = fams.get("F1") or {}

        weights_raw = f1.get("type_weights") or {}
        if not isinstance(weights_raw, Mapping):
            raise ConfigError("fraud.yaml: F1.type_weights must be a mapping")
        weights: dict[str, float] = {}
        for kind, w in weights_raw.items():
            if not _num(w) or w < 0:
                raise ConfigError(f"fraud.yaml: F1.type_weights.{kind} must be a number >= 0")
            weights[str(kind)] = float(w)
        beta = f1.get("outcome_beta", 0.0)
        if not _num(beta) or not 0 <= beta <= 1:
            raise ConfigError("fraud.yaml: F1.outcome_beta must be a number in [0, 1]")
        return cls(
            rho=cfg.f1_rarity_fraction,
            min_linked=cfg.f1_min_linked_deals,
            type_weights=weights,
            outcome_beta=float(beta),
            percentiles=dict(cfg.percentiles),
            train_end=cfg.train_end,
            test_start=cfg.test_start,
            test_end=cfg.test_end,
        )


def p_hat(df: int, n: int) -> float:
    """Smoothed history frequency of a value used by ``df`` of ``n`` deals."""
    return (df + 1) / (n + 1)


def surprisal(df: int, n: int) -> float:
    """``I(v) = -log2 p_hat(v)`` in bits (0.0 when there is no history to judge against)."""
    if n <= 0:
        return 0.0
    bits = -math.log2(min(1.0, p_hat(df, n)))
    return bits if bits > 0 else 0.0


def is_strong(df: int, n: int, links: int, rho: float, min_linked: int) -> bool:
    """Strong entity: rare in history (``df / n < rho``) and links at least ``min_linked`` deals."""
    if n <= 0:
        return False
    return df / n < rho and links >= min_linked


def outcome_discount(repaid: int, df: int, beta: float) -> float:
    """``omega_v = 1 - beta * (repaid + 1) / (df + 2)``: shared values that repaid count less."""
    return 1.0 - beta * (repaid + 1) / (df + 2)
