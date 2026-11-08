"""Calibration, restricted baselines, the time-split replay and its report (synthetic history)."""
from __future__ import annotations

import json
import math
import os
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml
from test_fraud_synth import deal_row, deposit_rows, filler_deals, iso_day, write_history

from prism.engine.config import DEFAULT_FRAUD_PATH, load_fraud_config
from prism.fraud import eval_baseline
from prism.fraud.baseline import Baseline, Calibration, build_baseline
from prism.fraud.calibrate import MIN_CLEAN, clean_ids, compute_thresholds, floor_bits
from prism.fraud.rarity import FraudParams, percentile, upper_tail_bits
from prism.fraud.signals import F5_STATS, f5_statistics

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cfg():
    return load_fraud_config()


@pytest.fixture(scope="module")
def params(cfg):
    return FraudParams.from_config(cfg)


# ------------------------------------------------------------------------ clean set

def _mixed_rows(n_clean):
    rows = [deal_row(f"K-{i:03d}", iso_day(100 + i)) for i in range(n_clean)]
    rows += [
        deal_row("X-5", iso_day(30)),
        deal_row("X-2", iso_day(10), repayment_status="paid_off"),
        deal_row("X-3", iso_day(10)),
        deal_row("L-1", iso_day(11), fraud_label="old_trick"),
        deal_row("C-1", iso_day(12), repayment_status="charged_off"),
        deal_row("D-1", iso_day(13), final_status="declined", repayment_status=""),
        deal_row("P-1", iso_day(14), repayment_status="30_days_past_due"),
    ]
    return rows


def test_clean_ids_filters_and_orders(params):
    b = Baseline.from_rows(_mixed_rows(MIN_CLEAN), params=params)
    ids = clean_ids(b, params)
    # funded + label none + current/paid_off, every date, sorted by (applied, id)
    assert ids[:3] == ["X-2", "X-3", "X-5"] and len(ids) == MIN_CLEAN + 3
    assert not {"L-1", "C-1", "D-1", "P-1"} & set(ids)


def test_clean_ids_as_of_keeps_applied_on_or_before(params):
    b = Baseline.from_rows(_mixed_rows(MIN_CLEAN), params=params)
    cut = date.fromisoformat(iso_day(30))
    ids = clean_ids(b, params, as_of=cut)
    # as_of leaves fewer than MIN_CLEAN clean deals, so every label-none deal up to the date stands in
    assert set(ids) == {"X-2", "X-3", "X-5", "C-1", "D-1", "P-1"}


def test_small_history_falls_back_to_all_label_none_deals(params):
    rows = [deal_row(f"X-{i:03d}", iso_day(i)) for i in range(10)]
    rows += [deal_row(f"D-{i:03d}", iso_day(20 + i), final_status="declined", repayment_status="")
             for i in range(30)]
    rows.append(deal_row("L-1", iso_day(60), fraud_label="old_trick"))
    b = Baseline.from_rows(rows, params=params)
    assert len(clean_ids(b, params)) == 40
    assert compute_thresholds(b, params).n_clean == 40


def test_calibration_ignores_every_config_date(params):
    rows = [deal_row(f"X-{i:03d}", iso_day(i), equipment_vendor=f"Vendor {i}") for i in range(30)]
    early = params
    late = replace(params, train_end=date(1990, 1, 1), test_start=date(1991, 1, 1), test_end=date(1992, 1, 1))
    one = compute_thresholds(Baseline.from_rows(rows, params=early), early)
    two = compute_thresholds(Baseline.from_rows(rows, params=late), late)
    assert one == two and one.n_clean == 30


def shifted(rows, deposits, days=365):
    out = []
    for r in rows:
        r = dict(r)
        r["application_date"] = (date.fromisoformat(r["application_date"]) + timedelta(days=days)).isoformat()
        out.append(r)
    return out, deposits


def test_calibration_invariant_to_a_one_year_date_shift(params):
    deals, deps = [], []
    labels = ["Mon-Fri", "Mon-Sat", "Mon,Thu"]
    for i in range(30):
        deals.append(deal_row(f"X-{i:03d}", iso_day(i), equipment_vendor="Kappa Supply LLC" if i % 3 else f"V{i}",
                              vendor_remit_acct_last4="1111"))
        deps += deposit_rows(f"X-{i:03d}", [(10, round(0.1 + 0.02 * i, 2), labels[i % 3])] * 6)
    a = compute_thresholds(Baseline.from_rows(deals, deps, params), params)
    sd, sdep = shifted(deals, deps)
    b = compute_thresholds(Baseline.from_rows(sd, sdep, params), params)
    assert a.n_clean == b.n_clean == 30 and a.tau == b.tau and a.tau["F5"] is not None
    assert {k: len(v) for k, v in a.reference.items()} == {k: len(v) for k, v in b.reference.items()}
    assert a == b


# ------------------------------------------------------------------------ thresholds

def vendor_history(inc_lookalike=False):
    rows = [deal_row(f"X-{i:03d}", iso_day(i), equipment_vendor="Kappa Supply LLC",
                     vendor_remit_acct_last4="1111") for i in range(5)]
    for i, v in enumerate(["Omega Trucking LLC", "Sigma Tools LLC", "Delta Pumps LLC", "Theta Cranes LLC"]):
        rows.append(deal_row(f"X-{5 + i:03d}", iso_day(5 + i), equipment_vendor=v, vendor_remit_acct_last4=f"20{i}"))
    if inc_lookalike:
        rows.append(deal_row("X-100", iso_day(20), equipment_vendor="Kappa Supply Inc", vendor_remit_acct_last4="1111"))
    return rows


def test_f3_tau_is_the_theoretical_floor_without_lookalikes(params):
    b = Baseline.from_rows(vendor_history(), params=params)
    cal = compute_thresholds(b, params)
    assert cal.n_clean == 9 and cal.fire_rate_clean["F3"] == 0.0
    assert round(cal.tau["F3"], 4) == 4.3219 == round(floor_bits(0.95), 4)
    assert cal.tau["F5"] is None and cal.reference == {}  # no deposit data at all


def test_f3_tau_is_interpolated_percentile(params):
    b = Baseline.from_rows(vendor_history(inc_lookalike=True), params=params)
    cal = compute_thresholds(b, params)
    lookalike_bits = math.log2(10)  # n_pat 0 of 9 other vendor observations
    # ten clean deals: nine with 0 bits and one with log2(10); rank 0.95 * 9 = 8.55
    empirical = 0.55 * lookalike_bits
    assert empirical < floor_bits(0.95)  # so the floor wins
    assert cal.tau["F3"] == pytest.approx(floor_bits(0.95))
    assert cal.fire_rate_clean["F3"] == 0.0  # log2(10) = 3.32 < 4.32
    hi = compute_thresholds(b, replace(params, percentiles={**params.percentiles, "F3": 0.5}))
    assert hi.tau["F3"] == pytest.approx(floor_bits(0.5))  # floor 1.0 beats the empirical 0
    assert cal.n_clean == 10 and cal.percentiles["F3"] == 0.95


def f5_baseline(params, n=12):
    deals, deps = [], []
    labels = ["Mon-Fri", "Mon-Sat", "Mon,Thu"]
    for i in range(n):
        deals.append(deal_row(f"X-{i:03d}", iso_day(i)))
        deps += deposit_rows(f"X-{i:03d}", [(10, round(0.1 + 0.02 * i, 2), labels[i % 3])] * 6)
    return Baseline.from_rows(deals, deps, params)


def test_f5_tau_matches_percentile_of_clean_bits(params):
    b = f5_baseline(params)
    cal = compute_thresholds(b, params)
    assert {k: len(v) for k, v in cal.reference.items()} == {s: 12 for s in F5_STATS}
    assert all(v == sorted(v) for v in cal.reference.values())
    bits = []
    for i in clean_ids(b, params):
        st = f5_statistics(b.deals[i].profile, b, params, exclude=i)
        bits.append(max(upper_tail_bits(st[s], cal.reference[s]) for s in F5_STATS))
    assert cal.tau["F5"] == pytest.approx(max(percentile(bits, 0.95), floor_bits(0.95)))
    lo = compute_thresholds(b, replace(params, percentiles={**params.percentiles, "F5": 0.5}))
    hi = compute_thresholds(b, replace(params, percentiles={**params.percentiles, "F5": 0.99}))
    assert lo.tau["F5"] <= cal.tau["F5"] <= hi.tau["F5"]
    assert all(t >= floor_bits(q) for t, q in ((lo.tau["F5"], 0.5), (hi.tau["F5"], 0.99)))
    assert 0.0 <= cal.fire_rate_clean["F5"] <= 1.0


def test_empty_clean_set_gives_no_tau(params):
    b = Baseline.from_rows([deal_row("X-1", iso_day(1), fraud_label="old_trick")], params=params)
    cal = compute_thresholds(b, params)
    # F3 keeps its floor (a vendor lookalike can still be judged); F5 has no reference sample
    assert cal.n_clean == 0 and cal.tau["F5"] is None and cal.tau["F3"] == pytest.approx(floor_bits(0.95))
    assert cal.fire_rate_clean == {"F1": 0.0, "F3": 0.0, "F5": 0.0}
    assert compute_thresholds(Baseline(), params).n_clean == 0


def test_leave_one_out_f1_on_the_clean_set(params):
    rows = filler_deals(60)
    rows.append(deal_row("U-1", iso_day(61), vendor_remit_acct_last4="5555"))
    cal = compute_thresholds(Baseline.from_rows(rows, params=params), params)
    assert cal.fire_rate_clean["F1"] == 0.0  # a lone user of an entity does not share with itself
    rows.append(deal_row("U-2", iso_day(62), vendor_remit_acct_last4="5555"))
    cal = compute_thresholds(Baseline.from_rows(rows, params=params), params)
    assert cal.fire_rate_clean["F1"] == pytest.approx(2 / 62)


def test_build_baseline_attaches_deterministic_calibration(tmp_path, cfg, params):
    labels = ["Mon-Fri", "Mon-Sat", "Mon,Thu"]
    hist = write_history(
        tmp_path,
        [deal_row(f"X-{i:03d}", iso_day(i)) for i in range(12)],
        [r for i in range(12) for r in deposit_rows(
            f"X-{i:03d}", [(10, round(0.1 + 0.02 * i, 2), labels[i % 3])] * 6)],
    )
    one, two = build_baseline(hist, cfg), build_baseline(hist, cfg)
    assert one.calibration.n_clean == 12 and set(one.calibration.tau) == {"F3", "F5"}
    assert one.calibration.tau["F5"] is not None and one.calibration == two.calibration
    assert isinstance(one.calibration, Calibration)
    assert one.calibration == compute_thresholds(one, params)


def test_yaml_holds_percentiles_not_bit_thresholds():
    raw = yaml.safe_load(DEFAULT_FRAUD_PATH.read_text(encoding="utf-8"))

    def keys(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield str(k)
                yield from keys(v)

    assert not [k for k in keys(raw) if "bit" in k.lower() or k.lower().startswith("tau")]
    for fam, spec in raw["families"].items():
        if "percentile" in spec:
            assert 0 < spec["percentile"] < 1


# ------------------------------------------------------------------------ restricted_to

def test_restricted_to_has_its_own_indexes(params):
    rows = [deal_row(f"X-{i}", iso_day(i), preparer_name="Shared Prep" if i in (1, 3) else f"Own {i}")
            for i in range(5)]
    b = Baseline.from_rows(rows, params=params)
    b.calibration = Calibration(n_clean=9)
    r = b.restricted_to(["X-3", "X-1", "nope"])
    assert r.n_history_deals == 2 and r.ordered_ids() == ["X-1", "X-3"]
    assert r.df("preparer", "shared prep") == 2 and b.restricted_to(["X-1"]).df("preparer", "shared prep") == 1
    assert r.calibration == Calibration() and r.params is b.params
    assert b.n_history_deals == 5 and b.calibration.n_clean == 9


# ------------------------------------------------------------------------ time-split replay

def mk(day, **over):
    row = filler_deals(1, prefix="T", start=day)[0]
    row.update(over)
    return row


def eval_history():
    rows = filler_deals(100)
    rows += [
        mk(190, vendor_remit_acct_last4="7777"),
        mk(195, vendor_remit_acct_last4="7777"),
        mk(200, deal_id="T-200a", preparer_name="Ring Prep"),
        mk(200, deal_id="T-200b", preparer_name="Ring Prep"),
        mk(210),
        mk(215, fraud_label="old_trick", final_status="fraud_confirmed", repayment_status=""),
    ]
    return rows


SIX_OF_106 = 6 / 106  # holds out exactly the last six deals of eval_history()


def run_main(tmp_path, *extra, name="out"):
    hist = tmp_path / "history" if (tmp_path / "history").is_dir() else write_history(tmp_path, eval_history())
    out = tmp_path / name
    code = eval_baseline.main(["--history", str(hist), "--out-dir", str(out), *extra])
    return code, out


def test_replay_never_sees_the_future(cfg, params):
    full = Baseline.from_rows(eval_history(), params=params)
    rep = eval_baseline.build_report(full, params, None, 0, SIX_OF_106)
    rows = {r["deal_id"]: r for r in rep["deals"]}
    assert [r["deal_id"] for r in rep["deals"]] == ["T-190", "T-195", "T-200a", "T-200b", "T-210", "T-215"]
    assert rows["T-190"]["f1_partners"] == []  # A, scored before B exists
    assert rows["T-195"]["f1_partners"] == ["T-190"]  # B sees A
    assert rows["T-200a"]["f1_partners"] == [] and rows["T-200b"]["f1_partners"] == ["T-200a"]  # tie: id order
    assert rep["meta"]["n_train_deals"] == 100 and rep["meta"]["n_history_deals"] == 106
    assert rep["meta"]["n_test_deals"] == 6 and rep["meta"]["train_cutoff"] == iso_day(99)
    assert all(r["f1_partners"] == [] for r in rep["deals"] if r["deal_id"] in ("T-210", "T-215"))


def test_summary_counts_match_hand_computation(params):
    full = Baseline.from_rows(eval_history(), params=params)
    s = eval_baseline.build_report(full, params, None, 0, SIX_OF_106)["summary"]
    assert (s["n_test_deals"], s["n_good_test_deals"]) == (6, 5)
    assert s["fired_among_good"] == {"F1": 2, "F3": 0, "F5": 0}
    assert s["fire_rate_among_good"]["F1"] == pytest.approx(0.4)
    assert s["false_flags_f1_f3_f5"] == 0 and s["false_flag_ids"] == []
    assert s["watch_any_family_among_good"] == 2


def test_false_flag_rule_needs_all_three():
    rows = [
        {"deal_id": "a", "good": True, "fired": ["F1", "F3", "F5"]},
        {"deal_id": "b", "good": True, "fired": ["F1", "F3"]},
        {"deal_id": "c", "good": False, "fired": ["F1", "F3", "F5"]},
        {"deal_id": "d", "good": True, "fired": []},
    ]
    s = eval_baseline.summarize(rows)
    assert s["false_flags_f1_f3_f5"] == 1 and s["false_flag_ids"] == ["a"]
    assert s["watch_any_family_among_good"] == 2 and s["n_good_test_deals"] == 3


def test_report_files_and_determinism(tmp_path):
    code, out = run_main(tmp_path, "--holdout-fraction", str(SIX_OF_106))
    assert code == 0
    data = json.loads((out / "baseline_eval.json").read_text(encoding="utf-8"))
    assert set(data) == {"meta", "thresholds", "summary", "deals", "scheme"} and data["scheme"] is None
    keys = [(r["applied"], r["deal_id"]) for r in data["deals"]]
    assert keys == sorted(keys)
    first = data["deals"][1]
    assert set(first["bits"]) == {"F1", "F3", "F5"} and first["fired"] == ["F1"]
    md = (out / "baseline_eval.md").read_text(encoding="utf-8")
    assert "F2 and F4 are not built" in md and "lower bound" in md and "train period" in md and "by rank" in md
    assert "holdout_fraction" in data["meta"] and "train_cutoff" in data["meta"]
    code2, out2 = run_main(tmp_path, "--holdout-fraction", str(SIX_OF_106), name="out2")
    assert code2 == 0
    for name in ("baseline_eval.json", "baseline_eval.md"):
        assert (out / name).read_bytes() == (out2 / name).read_bytes()
        assert b"\r" not in (out / name).read_bytes()


def test_scheme_links_with_gold(tmp_path):
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps({"history_flags": ["T-195", "T-190", "T-200b", "NOT-THERE", 5]}), encoding="utf-8")
    code, out = run_main(tmp_path, "--gold", str(gold), "--holdout-fraction", str(SIX_OF_106))
    assert code == 0
    sch = json.loads((out / "baseline_eval.json").read_text(encoding="utf-8"))["scheme"]
    assert sch["members_in_test_period"] == ["T-190", "T-195", "T-200b"]
    assert [(r["deal_id"], r["has_link"]) for r in sch["later_members"]] == [("T-195", True), ("T-200b", False)]
    assert sch["later_members"][0]["linked_to_earlier_members"] == ["T-190"]
    assert (sch["n_later"], sch["n_linked"]) == (2, 1)


def test_split_is_by_rank(params):
    order = [f"d{i}" for i in range(10)]
    assert eval_baseline.split_ids(order, 0.36) == (order[:7], order[7:])  # ceil(6.4) = 7
    assert eval_baseline.split_ids(order, 0.5) == (order[:5], order[5:])
    assert eval_baseline.split_ids([], 0.36) == ([], [])


@pytest.mark.parametrize("bad", ["0", "1", "-0.2", "1.5", "nan"])
def test_holdout_fraction_must_be_in_the_open_unit_interval(tmp_path, capsys, bad):
    code, _ = run_main(tmp_path, "--holdout-fraction", bad)
    assert code == 2 and "holdout-fraction" in capsys.readouterr().err


def test_report_is_identical_when_every_date_is_shifted_by_a_year(params):
    rows = eval_history()
    one = eval_baseline.build_report(Baseline.from_rows(rows, params=params), params, None, 0, SIX_OF_106)
    moved = []
    for r in rows:
        r = dict(r)
        r["application_date"] = (date.fromisoformat(r["application_date"]) + timedelta(days=365)).isoformat()
        moved.append(r)
    two = eval_baseline.build_report(Baseline.from_rows(moved, params=params), params, None, 0, SIX_OF_106)
    for rep in (one, two):
        rep["meta"].pop("train_cutoff")
        for d in rep["deals"]:
            d.pop("applied")
    assert one == two
    assert one["meta"]["n_train_deals"] == 100


def test_main_missing_history_returns_2(tmp_path, capsys):
    assert eval_baseline.main(["--history", str(tmp_path / "nope"), "--out-dir", str(tmp_path / "o")]) == 2
    assert "deals.csv" in capsys.readouterr().err
    empty = tmp_path / "empty"
    empty.mkdir()
    assert eval_baseline.main(["--history", str(empty), "--out-dir", str(tmp_path / "o")]) == 2


# ------------------------------------------------------------------------ optional real-data smoke

def _real_history():
    env = os.environ.get("PRISM_HISTORY_DIR")
    for p in (Path(env) if env else None, ROOT / "data" / "participant" / "history"):
        if p is not None and (p / "deals.csv").is_file():
            return p
    return None


@pytest.mark.skipif(_real_history() is None, reason="history data not present")
def test_smoke_on_real_history(tmp_path, cfg):
    hist = _real_history()
    b = build_baseline(hist, cfg)
    assert b.n_history_deals > 0 and {"F3", "F5"} <= set(b.calibration.tau)
    outs = []
    for name in ("a", "b"):
        assert eval_baseline.main(["--history", str(hist), "--out-dir", str(tmp_path / name)]) == 0
        outs.append(tmp_path / name)
    for name in ("baseline_eval.json", "baseline_eval.md"):
        assert (outs[0] / name).read_bytes() == (outs[1] / name).read_bytes()


@pytest.mark.skipif(_real_history() is None or not (ROOT / "eval" / "gold.json").is_file(),
                    reason="history data or gold file not present")
def test_signal_level_trap_is_recorded_not_asserted(tmp_path, cfg, params, capsys):
    """Records which history_must_not_flag deals reach F1+F3+F5 in the test period.

    The ids are read from the gold file at test time only. The full assertion lives in the
    decide-level trap (05-04); here the intersection is printed so the number is on record.
    """
    gold = json.loads((ROOT / "eval" / "gold.json").read_text(encoding="utf-8"))
    full = build_baseline(_real_history(), cfg)
    rep = eval_baseline.build_report(full, params, gold.get("history_flags"), 0)
    must_not = set(gold.get("history_must_not_flag") or [])
    false_flags = rep["summary"]["false_flag_ids"]
    hit = sorted(must_not & set(false_flags))
    in_test = sorted(must_not & {r["deal_id"] for r in rep["deals"]})
    with capsys.disabled():
        print(f"\n[05-02 trap, signal level] false_flag_ids={false_flags} "
              f"must_not_flag in test period={len(in_test)} reaching F1+F3+F5={hit}")
    assert isinstance(false_flags, list)
