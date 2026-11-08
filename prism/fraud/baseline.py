"""History baseline (owner: Phase 5, M13).

Contract: built once per run from whatever history ships with the dataset; thresholds are
recomputed from percentiles in config/fraud.yaml, never stored as bit values.

``build_baseline`` reads ``deals.csv`` with the stdlib csv module and NEVER raises for history
content: a missing dir or file, a bad date, a duplicate id or an absent column becomes a
warning string on ``Baseline.warnings`` and a skipped row. Every value is canonicalized
(prism.fraud.canon) so spellings of one entity share one key. Queries take an optional
``exclude`` deal id (leave-one-out) that subtracts exactly that deal in O(1) via id sets.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from prism.engine.config import FraudConfig
from prism.fraud.canon import canon_value
from prism.fraud.rarity import FraudParams

# History CSV column -> entity kind. preparer_firm, registered_agent_address, ein, ssn and
# licence columns are intentionally not indexed (see the plan SUMMARY).
HISTORY_COLUMN_KINDS: dict[str, str] = {
    "preparer_name": "preparer",
    "preparer_phone": "phone",
    "registered_agent": "registered_agent",
    "business_address": "address",
    "equipment_vendor": "vendor",
    "vendor_remit_acct_last4": "remit_account",
    "pdf_producer": "pdf_producer",
    "bank_name": "bank",
    "guarantor_name": "guarantor",
}

# The history only carries the application-packet producer.
HISTORY_PRODUCER_CLASS = "application"

CLEAN_REPAYMENTS = ("current", "paid_off")


@dataclass(frozen=True)
class DealProfile:
    """Canonical entities (and, later, deposit features) of one deal, history or current."""

    deal_id: str
    entities: dict[str, tuple[str, ...]] = field(default_factory=dict)
    deposits: Optional[Any] = None


@dataclass(frozen=True)
class HistoryDeal:
    deal_id: str
    applied: date
    final_status: str
    fraud_label: str
    repayment_status: str
    profile: DealProfile

    @property
    def repaid(self) -> bool:
        """Funded, unlabelled and still performing or paid off."""
        return (
            self.final_status == "funded"
            and self.fraud_label == "none"
            and self.repayment_status in CLEAN_REPAYMENTS
        )


@dataclass
class Baseline:
    n_history_deals: int = 0
    deals: dict[str, HistoryDeal] = field(default_factory=dict)
    params: FraudParams = field(default_factory=FraudParams)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._build_indexes()

    # ------------------------------------------------------------------ indexes
    def _build_indexes(self) -> None:
        self.n_history_deals = len(self.deals)
        ids: dict[tuple[str, str], set[str]] = {}
        for d in self.deals.values():
            for kind, values in d.profile.entities.items():
                for v in values:
                    ids.setdefault((kind, v), set()).add(d.deal_id)
        self._ids = ids
        self._repaid_ids = {i for i, d in self.deals.items() if d.repaid}
        self._ordered = sorted(self.deals, key=lambda i: (self.deals[i].applied, i))

    # ------------------------------------------------------------------ queries
    def n_effective(self, exclude: Optional[str] = None) -> int:
        return len(self.deals) - (1 if exclude is not None and exclude in self.deals else 0)

    def _members(self, kind: str, value: str, exclude: Optional[str]) -> list[str]:
        members = self._ids.get((kind, value), ())
        return sorted(i for i in members if i != exclude)

    def df(self, kind: str, value: str, exclude: Optional[str] = None) -> int:
        members = self._ids.get((kind, value), ())
        return len(members) - (1 if exclude is not None and exclude in members else 0)

    def deals_with(self, kind: str, value: str, exclude: Optional[str] = None) -> list[str]:
        return self._members(kind, value, exclude)

    def entity_stats(
        self, kind: str, value: str, exclude: Optional[str] = None
    ) -> tuple[int, int, Optional[date], Optional[date]]:
        """(df, repaid count, first seen, last seen) over history deals, minus ``exclude``."""
        members = self._members(kind, value, exclude)
        if not members:
            return 0, 0, None, None
        dates = [self.deals[i].applied for i in members]
        repaid = sum(1 for i in members if i in self._repaid_ids)
        return len(members), repaid, min(dates), max(dates)

    def value_counts(self, kind: str) -> dict[str, int]:
        """Document frequency of every canonical value of ``kind`` in history."""
        return {v: len(s) for (k, v), s in sorted(self._ids.items()) if k == kind}

    def producer_counts(self, doc_class: str) -> dict[str, int]:
        """Producer distribution for a document class (history has only the packet class)."""
        return self.value_counts("pdf_producer") if doc_class == HISTORY_PRODUCER_CLASS else {}

    def ordered_ids(self) -> list[str]:
        """History ids sorted by (application date, id)."""
        return list(self._ordered)

    # ------------------------------------------------------------------ builders
    @classmethod
    def from_rows(
        cls,
        deal_rows: Iterable[Mapping[str, Any]],
        deposit_rows: Iterable[Mapping[str, Any]] = (),
        params: Optional[FraudParams] = None,
    ) -> "Baseline":
        """Build from parsed CSV rows. Never raises; skips bad rows with a warning each."""
        warnings: list[str] = []
        deals: dict[str, HistoryDeal] = {}
        for n, row in enumerate(deal_rows, start=2):  # row 1 is the header
            deal_id = str(row.get("deal_id") or "").strip()
            if not deal_id:
                warnings.append(f"deals.csv row {n}: missing deal_id, skipped")
                continue
            if deal_id in deals:
                warnings.append(f"deals.csv row {n}: duplicate deal id {deal_id}, first row kept")
                continue
            try:
                applied = date.fromisoformat(str(row.get("application_date") or "").strip())
            except ValueError:
                warnings.append(f"deals.csv row {n}: {deal_id} has an invalid application_date, skipped")
                continue
            entities: dict[str, tuple[str, ...]] = {}
            for col, kind in HISTORY_COLUMN_KINDS.items():
                v = canon_value(kind, row.get(col))
                if v:
                    entities[kind] = (v,)
            deals[deal_id] = HistoryDeal(
                deal_id=deal_id,
                applied=applied,
                final_status=str(row.get("final_status") or "").strip(),
                fraud_label=str(row.get("fraud_label") or "").strip(),
                repayment_status=str(row.get("repayment_status") or "").strip(),
                profile=DealProfile(deal_id=deal_id, entities=entities),
            )
        return cls(deals=deals, params=params or FraudParams(), warnings=warnings)

    def restricted_to(self, ids: Iterable[str]) -> "Baseline":
        """A fresh Baseline over only ``ids`` (unknown ids ignored) with its own indexes."""
        keep = {i: self.deals[i] for i in sorted(set(ids)) if i in self.deals}
        return Baseline(deals=keep, params=self.params)


def _read_csv(path: Path, warnings: list[str]) -> Optional[list[dict[str, str]]]:
    if not path.is_file():
        warnings.append(f"{path.name}: not found")
        return None
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        warnings.append(f"{path.name}: unreadable ({type(e).__name__})")
        return None


def build_baseline(history_dir: Optional[Path], cfg: FraudConfig) -> Baseline:
    """Return the history baseline (``history_dir`` may be None). Never raises on history content."""
    params = FraudParams.from_config(cfg)
    if history_dir is None:
        return Baseline(params=params, warnings=["no history directory: empty baseline"])
    hist = Path(history_dir)
    warnings: list[str] = []
    deal_rows = _read_csv(hist / "deals.csv", warnings)
    base = Baseline.from_rows(deal_rows or (), params=params)
    base.warnings[:0] = warnings
    return base
