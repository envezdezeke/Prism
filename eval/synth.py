"""Seeded synthetic-case generator for the Prism fraud model (trick menu v1).

Reads ``eval/trick_menu.yaml`` and emits synthetic history-schema rows (``deals.csv`` and
``monthly_deposits.csv`` columns) for every family x strength and every benign twin.

Rules this file keeps:
* Real history is read ONLY to (a) pick clean "base" business rows (industry, amounts, deposit
  months), (b) compute percentile anchors for the menu's quantile strengths and (c) build a
  reserved set so no invented entity ever equals a real one. No real row is written anywhere:
  every identity column of an emitted row is a fresh fake (made-up names, 555-01xx phones,
  X-/S- ids).
* Deterministic: every random choice comes from ``random.Random(case_seed)`` with
  ``case_seed = strength seed + case index``. No wall clock, no uuid.
* Nothing here learns or tunes a weight or threshold (MODEL_DESIGN M5).

Library use: ``load_menu``, ``load_history``, ``generate_cases``. CLI: writes the generated
(fake only) rows to ``--out-dir`` (default ``out/synth``).
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import random
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from prism.fraud.baseline import CLEAN_REPAYMENTS, HISTORY_COLUMN_KINDS  # noqa: E402
from prism.fraud.canon import canon_value  # noqa: E402
from prism.fraud.rarity import percentile  # noqa: E402

MENU_PATH = ROOT / "eval" / "trick_menu.yaml"
DEFAULT_HISTORY = "/Users/jes/Goldman-I/data/participant/history"

DEAL_COLUMNS = [
    "deal_id", "application_date", "legal_name", "ein", "industry", "naics", "formation_date",
    "business_address", "registered_agent", "registered_agent_address", "guarantor_name",
    "guarantor_dob", "guarantor_ssn_last4", "guarantor_dl_number", "preparer_name",
    "preparer_firm", "preparer_phone", "bank_name", "amount_requested", "product", "purpose",
    "term_months", "annual_revenue_stated", "equipment_vendor", "vendor_remit_acct_last4",
    "pdf_producer", "final_status", "fraud_label", "repayment_status", "relationship_since",
    "prior_note",
]
DEPOSIT_COLUMNS = [
    "deal_id", "month", "total_deposits", "deposit_count", "pct_deposits_multiple_of_100",
    "deposit_weekdays", "largest_deposit", "month_end_balance",
]

# menu "shared" kind -> deal columns that carry it
KIND_COLUMNS: dict[str, tuple[str, ...]] = {
    "preparer": ("preparer_name", "preparer_firm"),
    "phone": ("preparer_phone",),
    "registered_agent": ("registered_agent", "registered_agent_address"),
    "address": ("business_address",),
    "remit_account": ("vendor_remit_acct_last4",),
    "guarantor": ("guarantor_name",),
}
GUARANTOR_ID_COLUMNS = ("guarantor_dob", "guarantor_ssn_last4", "guarantor_dl_number")

SYLLABLES = ["za", "qui", "vor", "mel", "tra", "bex", "lun", "kor", "pri", "dax", "fen", "gol",
             "hux", "jin", "wyn", "yar"]
GREEK = ["Zeta", "Kappa", "Omicron", "Sigma", "Theta", "Upsilon", "Xi", "Rho", "Tau", "Phi",
         "Psi", "Eta", "Iota", "Lambda", "Nu", "Pi"]
NOUNS = ["Works", "Supply", "Holdings", "Partners", "Freight", "Foods", "Outfitters", "Labs",
         "Garage", "Studio", "Salvage", "Fabrication"]
SUFFIXES = ["LLC", "Inc", "Co"]
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
AREA_CODES = ["512", "737", "940"]
COMMON_PRODUCER = "Quillfold Print Engine 2.1"
NEW_PRODUCER = "FakeForge PDF 9.4"
COMMON_PRODUCER_SHARE = 0.10
VENDOR_PLANT_COUNT = 8
BACKGROUND_DEALS = 10
CASE_DATE = date(2026, 11, 2)


# ------------------------------------------------------------------ menu

@dataclass(frozen=True)
class Cell:
    """One family x strength (kind 'ring') or one benign twin (kind 'twin')."""

    id: str
    family: str
    family_name: str
    kind: str
    strength: str
    seed: int
    count: int
    params: Mapping[str, Any]
    expected_full: str
    expected_now: str
    blind_spot: Optional[str]
    must_not: Optional[str]
    role: str


def load_menu(path: Path = MENU_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def cells_of(menu: Mapping[str, Any]) -> list[Cell]:
    out: list[Cell] = []
    for fam in menu["families"]:
        fam_blind = fam.get("blind_spot")
        for strength, s in fam["strengths"].items():
            exp = s["expected"]
            blind = s.get("blind_spot") or fam_blind
            out.append(Cell(
                id=f"{fam['id']}-{strength}", family=fam["id"], family_name=fam["name"],
                kind="ring", strength=strength, seed=int(s["seed"]), count=int(s["count"]),
                params=dict(s["params"]), expected_full=exp["full"],
                expected_now=exp.get("now", exp["full"]),
                blind_spot=str(blind).strip() if blind else None, must_not=None,
                role=fam.get("role", "unseen"),
            ))
        for tw in fam.get("benign_twins", []):
            exp = tw["expected"]
            out.append(Cell(
                id=tw["id"], family=fam["id"], family_name=tw["name"], kind="twin",
                strength="twin", seed=int(tw["seed"]), count=int(tw["count"]),
                params=dict(tw["params"]), expected_full=exp["full"],
                expected_now=exp.get("now", exp["full"]), blind_spot=None,
                must_not=tw.get("must_not"), role=fam.get("role", "unseen"),
            ))
    return out


# ------------------------------------------------------------------ real history (anchors only)

@dataclass
class History:
    deal_rows: list[dict[str, str]]
    deposit_rows: list[dict[str, str]]
    reserved: frozenset[str]
    base_pool: list[tuple[dict[str, str], list[dict[str, str]]]]
    clean_round_shares: list[float]

    def anchor(self, q: float) -> Optional[float]:
        return percentile(self.clean_round_shares, q)


def _read(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def history_dir_from_env() -> Path:
    return Path(os.environ.get("PRISM_HISTORY_DIR", DEFAULT_HISTORY))


def load_history(history_dir: Path) -> Optional[History]:
    """None when the history is absent. Reads rows only to build anchors, base rows, reserved set."""
    hd = Path(history_dir)
    if not (hd / "deals.csv").is_file() or not (hd / "monthly_deposits.csv").is_file():
        return None
    deals = _read(hd / "deals.csv")
    deps = _read(hd / "monthly_deposits.csv")
    reserved: set[str] = set()
    for r in deals:
        for col, kind in HISTORY_COLUMN_KINDS.items():
            v = canon_value(kind, r.get(col))
            if v:
                reserved.add(v)
        for col in ("legal_name", "ein"):
            v = canon_value("preparer", r.get(col))
            if v:
                reserved.add(v)
    by_deal: dict[str, list[dict[str, str]]] = {}
    for r in deps:
        by_deal.setdefault(r["deal_id"], []).append(r)
    pool = []
    shares = []
    for r in sorted(deals, key=lambda x: x["deal_id"]):
        rows = sorted(by_deal.get(r["deal_id"], []), key=lambda x: x["month"])
        clean = (r.get("final_status") == "funded" and r.get("fraud_label") == "none"
                 and r.get("repayment_status") in CLEAN_REPAYMENTS)
        if not clean or len(rows) != 6:
            continue
        try:
            n = sum(float(x["deposit_count"]) for x in rows)
            m = sum(float(x["deposit_count"]) * float(x["pct_deposits_multiple_of_100"]) for x in rows)
        except ValueError:
            continue
        if n <= 0:
            continue
        pool.append((r, rows))
        shares.append(m / n)
    return History(deals, deps, frozenset(reserved), pool, sorted(shares))


# ------------------------------------------------------------------ fake values

class Fakes:
    """Unique, obviously fake identity values; never equal to a reserved (real) canonical value."""

    def __init__(self, rng: random.Random, reserved: frozenset[str]) -> None:
        self.rng = rng
        self.reserved = reserved
        self.issued: set[str] = set()

    def _unique(self, kind: str, make) -> str:
        for _ in range(10_000):
            v = make()
            key = canon_value(kind, v)
            if key and key not in self.reserved and key not in self.issued:
                self.issued.add(key)
                return v
        raise RuntimeError("could not invent a unique fake value")

    def _word(self) -> str:
        return (self.rng.choice(SYLLABLES) + self.rng.choice(SYLLABLES)).capitalize()

    def person(self) -> str:
        return self._unique("guarantor", lambda: f"{self._word()} {self._word()}")

    def preparer(self) -> str:
        return self._unique("preparer", lambda: f"{self._word()} {self._word()}, CPA")

    def business(self) -> str:
        return self._unique("preparer", lambda: (
            f"{self.rng.choice(GREEK)} {self.rng.choice(NOUNS)} {self.rng.choice(SUFFIXES)}"
            if self.rng.random() < 0.5 else
            f"{self._word()} {self.rng.choice(NOUNS)} {self.rng.choice(SUFFIXES)}"))

    def vendor_base(self) -> str:
        return self._unique("preparer", lambda: f"{self.rng.choice(GREEK)} {self._word()}")

    def agent(self) -> str:
        return self._unique("registered_agent", lambda: f"{self._word()} Registered Agents LLC")

    def bank(self) -> str:
        return self._unique("bank", lambda: f"{self._word()} Test National Bank")

    def phone(self) -> str:
        return self._unique("phone", lambda: f"{self.rng.choice(AREA_CODES)}-555-01{self.rng.randrange(100):02d}")

    def account(self) -> str:
        return self._unique("remit_account", lambda: f"9{self.rng.randrange(1000):03d}")

    def address(self) -> str:
        return self._unique("address", lambda: (
            f"{self.rng.randrange(100, 9999)} {self._word()} Test Way Ste {self.rng.randrange(1, 90)}, "
            f"Zetaville, TX 7{self.rng.randrange(1000, 9999)}"))

    def ein(self) -> str:
        return self._unique("preparer", lambda: f"00-7{self.rng.randrange(10 ** 6):06d}")

    def producer(self) -> str:
        return self._unique("pdf_producer", lambda: f"FakeTool {self._word()} {self.rng.randrange(1, 9)}.0")


def fresh_identity(fk: Fakes) -> dict[str, str]:
    """Every identity column replaced by a fresh fake; one deal shares nothing with another."""
    rng = fk.rng
    prep = fk.preparer()
    return {
        "legal_name": fk.business(), "ein": fk.ein(), "business_address": fk.address(),
        "registered_agent": fk.agent(), "registered_agent_address": fk.address(),
        "guarantor_name": fk.person(),
        "guarantor_dob": date(1960 + rng.randrange(35), 1 + rng.randrange(12), 1 + rng.randrange(28)).isoformat(),
        "guarantor_ssn_last4": f"{rng.randrange(10000):04d}",
        "guarantor_dl_number": f"{rng.randrange(10 ** 8):08d}",
        "preparer_name": prep, "preparer_firm": f"{prep.split(',')[0].split()[-1]} Test CPAs",
        "preparer_phone": fk.phone(), "bank_name": fk.bank(),
        "equipment_vendor": "", "vendor_remit_acct_last4": "", "pdf_producer": COMMON_PRODUCER,
        "relationship_since": "", "prior_note": "",
    }


# ------------------------------------------------------------------ case building

@dataclass
class Case:
    cell_id: str
    index: int
    deal_rows: list[dict[str, str]] = field(default_factory=list)  # current deals, trick + background
    deposit_rows: list[dict[str, str]] = field(default_factory=list)
    planted_rows: list[dict[str, str]] = field(default_factory=list)  # synthetic history rows
    trick_ids: list[str] = field(default_factory=list)
    background_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _blank_row() -> dict[str, str]:
    return {c: "" for c in DEAL_COLUMNS}


def _weekday_label(rng: random.Random, n: int) -> str:
    if n >= 5:
        return "Mon-Fri"
    days = sorted(rng.sample(range(7), n))
    return ",".join(DAY_NAMES[d] for d in days)


def _range(v: Any, rng: random.Random) -> int:
    if isinstance(v, (list, tuple)):
        return rng.randrange(int(v[0]), int(v[1]) + 1)
    return int(v)


def _num(v: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def build_case(cell: Cell, index: int, hist: History) -> Case:
    rng = random.Random(cell.seed + index)
    fk = Fakes(rng, hist.reserved)
    p = cell.params
    tag = f"{cell.id}-{index:03d}"
    size = int(p.get("ring_size", p.get("twin_size", 1)))
    case = Case(cell_id=cell.id, index=index)

    shared_kinds = list(p.get("shared", []))
    if ("same_dob_ssn4_dl" in p or "name_variant" in p) and "guarantor" not in shared_kinds:
        shared_kinds.append("guarantor")
    returning = "amount_multiple" in p

    # one fresh value per shared kind for the whole case
    seed_identity = fresh_identity(fk)
    shared_cols: dict[str, str] = {}
    for kind in shared_kinds:
        if kind == "remit_account":
            shared_cols["vendor_remit_acct_last4"] = fk.account()
            continue
        for col in KIND_COLUMNS[kind]:
            shared_cols[col] = seed_identity[col]
    if "guarantor" in shared_kinds and p.get("same_dob_ssn4_dl"):
        for col in GUARANTOR_ID_COLUMNS:
            shared_cols[col] = seed_identity[col]
    if p.get("name_variant") == "exact_common_name":
        shared_cols.pop("guarantor_dob", None)

    # vendor setting (equipment cases)
    vendor_base = usual_account = ""
    uses_vendor = any(k in p for k in ("vendor_change", "vendor_lookalike", "vendor", "remit"))
    if uses_vendor:
        vendor_base, usual_account = fk.vendor_base(), fk.account()

    # base rows
    pool = hist.base_pool
    picks = rng.sample(range(len(pool)), size + BACKGROUND_DEALS)
    producer_new = NEW_PRODUCER if p.get("producer") == "new_shared" else None

    # deposit fingerprint shared by the trick deals
    q = p.get("round_share_q")
    share_value = hist.anchor(float(q)) if q is not None else None
    n_weekdays = p.get("weekdays")
    ring_label = _weekday_label(rng, int(n_weekdays)) if n_weekdays is not None else None
    regular = bool(p.get("regularity"))
    ring_count = None

    spread = int(p.get("app_spread_days", 14))
    for i in range(size + BACKGROUND_DEALS):
        trick = i < size
        base_row, base_dep = pool[picks[i]]
        did = f"S-{tag}-{i + 1}" if trick else f"S-{tag}-b{i - size + 1}"
        row = {c: base_row.get(c, "") for c in DEAL_COLUMNS}
        row.update(fresh_identity(fk))
        offset = round(i * spread / (size - 1)) if (trick and size > 1) else rng.randrange(0, 31)
        applied = CASE_DATE + timedelta(days=offset)
        row.update(deal_id=did, application_date=applied.isoformat(), final_status="pending",
                   fraud_label="", repayment_status="")
        deps = [dict(d, deal_id=did) for d in base_dep]
        if trick:
            row.update(shared_cols)
            if producer_new:
                row["pdf_producer"] = producer_new
            if p.get("name_variant") == "nickname_or_initial" and i > 0:
                first, _, last = row["guarantor_name"].partition(" ")
                row["guarantor_name"] = f"{first} {chr(65 + i)}. {last}"
            if uses_vendor:
                _apply_vendor(row, p, vendor_base, usual_account, fk, shared_cols)
            if "formation_age_months" in p:
                months = _range(p["formation_age_months"], rng)
                row["formation_date"] = (applied - timedelta(days=30 * months)).isoformat()
            if share_value is not None or ring_label is not None or regular:
                if regular and ring_count is None:
                    ring_count = int(round(sum(_num(d["deposit_count"]) for d in deps) / len(deps)))
                for d in deps:
                    if share_value is not None:
                        d["pct_deposits_multiple_of_100"] = f"{share_value:.6f}"
                    if ring_label is not None:
                        d["deposit_weekdays"] = ring_label
                    if regular:
                        d["deposit_count"] = str(max(1, ring_count))
            _shape_deposits_and_revenue(row, deps, p, rng, share_value)
            case.trick_ids.append(did)
        else:
            case.background_ids.append(did)
        case.deal_rows.append(row)
        case.deposit_rows.extend(deps)

    _plant(case, cell, p, fk, rng, hist, shared_cols, shared_kinds, returning, tag, size,
           vendor_base, usual_account, uses_vendor)
    return case


def _apply_vendor(row: dict[str, str], p: Mapping[str, Any], base: str, usual: str,
                  fk: Fakes, shared_cols: Mapping[str, str]) -> None:
    change = p.get("vendor_change") or p.get("vendor_lookalike")
    if change == "suffix_swap":
        row["equipment_vendor"] = f"{base} Inc"
    elif change == "edit_distance_1":
        b = base[:2] + ("x" if base[2] != "x" else "y") + base[3:]
        row["equipment_vendor"] = f"{b} LLC"
    else:  # frequent_modal_form or nothing: the usual form
        row["equipment_vendor"] = f"{base} LLC"
    remit = p.get("remit")
    if "vendor_remit_acct_last4" in shared_cols:
        row["vendor_remit_acct_last4"] = shared_cols["vendor_remit_acct_last4"]
    elif remit == "usual":
        row["vendor_remit_acct_last4"] = usual
    elif remit in ("new_shared", "own_stable"):
        row["vendor_remit_acct_last4"] = shared_cols.setdefault("vendor_remit_acct_last4", fk.account())
    else:
        row["vendor_remit_acct_last4"] = usual
    row["product"], row["purpose"] = "Equipment Loan", "equipment"


def _shape_deposits_and_revenue(row: dict[str, str], deps: list[dict[str, str]],
                                p: Mapping[str, Any], rng: random.Random,
                                share_value: Optional[float]) -> None:
    growth = float(p.get("growth_per_month", 0.0))
    if growth:
        for m, d in enumerate(deps):
            d["total_deposits"] = f"{_num(d['total_deposits']) * (1 + growth) ** m:.2f}"
    if "seasonal_dip" in p:
        for d in deps:
            d["total_deposits"] = f"{_num(d['total_deposits']) * float(p['seasonal_dip']):.2f}"
    if "lump_share_of_month" in p:
        d = deps[rng.randrange(len(deps))]
        d["largest_deposit"] = f"{_num(d['total_deposits']) * float(p['lump_share_of_month']):.2f}"
    pump = float(p.get("pump", 1.0))
    if pump != 1.0:
        for d in deps[-2:]:
            d["total_deposits"] = f"{_num(d['total_deposits']) * pump:.2f}"
            d["largest_deposit"] = f"{_num(d['total_deposits']) * 0.4:.2f}"
    ratio = p.get("revenue_ratio")
    if ratio is not None:
        r = rng.uniform(*ratio) if isinstance(ratio, (list, tuple)) else float(ratio)
        row["annual_revenue_stated"] = f"{r * sum(_num(d['total_deposits']) for d in deps) * 2:.0f}"
    if "amount_multiple" in p:
        row["amount_requested"] = f"{float(row['amount_requested'] or 50000) * float(p['amount_multiple']):.0f}"


def _planted(fk: Fakes, rng: random.Random, did: str, applied: date, outcome: str,
             carry: Mapping[str, str]) -> dict[str, str]:
    row = _blank_row()
    row.update(fresh_identity(fk))
    row.update(carry)
    row.update(deal_id=did, application_date=applied.isoformat(), final_status="funded",
               fraud_label="none", repayment_status=outcome, amount_requested="40000",
               product="Term Loan", purpose="working_capital", term_months="36")
    return row


def _plant(case: Case, cell: Cell, p: Mapping[str, Any], fk: Fakes, rng: random.Random,
           hist: History, shared_cols: Mapping[str, str], shared_kinds: Sequence[str],
           returning: bool, tag: str, size: int, vendor_base: str, usual_account: str,
           uses_vendor: bool) -> None:
    n_hist = len(hist.deal_rows)
    seq = 0

    def next_id() -> str:
        nonlocal seq
        seq += 1
        return f"X-{tag}-{seq:02d}"

    def when(gap: Any = None) -> date:
        days = rng.randrange(30, 300)
        if gap is not None:
            lo, hi = (gap if isinstance(gap, (list, tuple)) else (gap, gap))
            days += int(365 * rng.uniform(lo, hi))
        return CASE_DATE - timedelta(days=days)

    # the common PDF producer is used by a normal share of history, so it is never rare
    k = math.ceil(COMMON_PRODUCER_SHARE * n_hist / (1 - COMMON_PRODUCER_SHARE))
    for _ in range(k):
        case.planted_rows.append(_planted(fk, rng, next_id(), when(), "paid_off", {}))
    if uses_vendor:
        for _ in range(VENDOR_PLANT_COUNT):
            case.planted_rows.append(_planted(fk, rng, next_id(), when(), "paid_off", {
                "equipment_vendor": f"{vendor_base} LLC", "vendor_remit_acct_last4": usual_account,
                "product": "Equipment Loan", "purpose": "equipment"}))
    outcome = str(p.get("planted_outcome", "paid_off" if (returning or cell.kind == "twin") else "current"))
    carry = dict(shared_cols)
    if p.get("remit") == "own_stable":
        first = case.deal_rows[0]
        carry.update(equipment_vendor=first["equipment_vendor"],
                     vendor_remit_acct_last4=first["vendor_remit_acct_last4"])
    share = p.get("shared_entity_history_share")
    if share is not None and carry:
        m = math.ceil(float(share) * n_hist / (1 - float(share)))
        for _ in range(m):
            case.planted_rows.append(_planted(fk, rng, next_id(), when(), "paid_off", carry))
    members = int(p.get("plant_history_members", 0))
    for _ in range(members):
        row_carry = dict(carry)
        if returning:
            first = case.deal_rows[0]
            for col in ("legal_name", "ein", "guarantor_name", "guarantor_dob", "guarantor_ssn_last4",
                        "guarantor_dl_number", "preparer_name", "preparer_firm", "preparer_phone"):
                row_carry[col] = first[col]
            case.deal_rows[0]["relationship_since"] = str(CASE_DATE.year - 3)
            case.deal_rows[0]["prior_note"] = "Prior line repaid in full"
        if cell.family == "T4":  # a different preparer each year: never shared
            row_carry.pop("preparer_name", None)
        case.planted_rows.append(_planted(fk, rng, next_id(), when(p.get("app_gap_years")), outcome, row_carry))
    if returning:
        for r in case.planted_rows[-members:] if members else []:
            r["amount_requested"] = f"{_num(case.deal_rows[0]['amount_requested']) / float(p['amount_multiple']):.0f}"


def generate_cases(cell: Cell, hist: History, limit: Optional[int] = None) -> list[Case]:
    n = cell.count if limit is None else min(cell.count, limit)
    return [build_case(cell, i, hist) for i in range(n)]


# ------------------------------------------------------------------ CLI (fake rows only)

def _write(path: Path, cols: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cols))
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Write the synthetic (fake-only) rows for every menu cell.")
    ap.add_argument("--out-dir", default=str(ROOT / "out" / "synth"))
    ap.add_argument("--max-cases", type=int, default=None)
    args = ap.parse_args(argv)
    hist = load_history(history_dir_from_env())
    if hist is None:
        print(f"synth: real history not found at {history_dir_from_env()} (set PRISM_HISTORY_DIR); skipping")
        return 0
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    deals: list[dict[str, str]] = []
    deps: list[dict[str, str]] = []
    for cell in cells_of(load_menu()):
        for case in generate_cases(cell, hist, args.max_cases):
            deals += case.deal_rows + case.planted_rows
            deps += case.deposit_rows
    _write(out / "deals.csv", DEAL_COLUMNS, deals)
    _write(out / "monthly_deposits.csv", DEPOSIT_COLUMNS, deps)
    print(f"wrote {len(deals)} synthetic deal rows and {len(deps)} deposit rows to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
