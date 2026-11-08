"""History baseline (owner: Phase 5, M13).

Contract: built once per run from whatever history ships with the dataset; thresholds are
recomputed from percentiles in config/fraud.yaml, never stored as bit values.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from prism.engine.config import FraudConfig


@dataclass
class Baseline:
    n_history_deals: int = 0


def build_baseline(history_dir: Optional[Path], cfg: FraudConfig) -> Baseline:
    """Return the history baseline (``history_dir`` may be None). Stub: empty baseline."""
    return Baseline()
