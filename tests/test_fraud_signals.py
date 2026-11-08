"""F3 stable-account rule, F5 weekday vocabulary and the shared F5 combination (synthetic history)."""
from __future__ import annotations

import pytest
from test_fraud_synth import deal_row, deposit_rows, iso_day

from prism.engine.config import load_fraud_config
from prism.fraud.baseline import Baseline, DealProfile, deposit_features
from prism.fraud.calibrate import clean_ids, compute_thresholds, floor_bits
from prism.fraud.rarity import FraudParams
from prism.fraud.signals import F3_STABLE_ACCOUNT_SHARE, F5_STATS, f5_bits, f5_statistics, score_f3, score_f5


@pytest.fixture(scope="module")
def params():
    return FraudParams.from_config(load_fraud_config())


def vendor_profile(vendor, account="1111"):
    ents = {"vendor": (vendor,)}
    if account:
        ents["remit_account"] = (account,)
    return DealProfile("q", ents)


def stable_history():
    return [deal_row(f"S-{i:03d}", iso_day(i), equipment_vendor="Kappa Supply LLC",
                     vendor_remit_acct_last4="1111") for i in range(5)]


def unstable_history():
    """Same vendor, a different last four on every deal (the honest equipment-loan pattern)."""
    return [deal_row(f"U-{i:03d}", iso_day(i), equipment_vendor="Kappa Supply LLC",
                     vendor_remit_acct_last4=f"20{i}") for i in range(5)]


# ------------------------------------------------------------------------ F3

def test_stable_group_new_account_fires(params):
    b = Baseline.from_rows(stable_history(), params=params)
    got = score_f3(vendor_profile("kappa supply llc", "9999"), b, params)
    assert got is not None and got.what_differs == "remit account" and got.bits > 0


def test_unstable_group_ignores_the_account(params):
    b = Baseline.from_rows(unstable_history(), params=params)
    assert score_f3(vendor_profile("kappa supply llc", "9999"), b, params) is None
    assert score_f3(vendor_profile("kappa supply llc", "2000"), b, params) is None


def test_suffix_swap_fires_in_both_kinds_of_group(params):
    cases = ((stable_history(), "stable", "suffix, remit account"), (unstable_history(), "unstable", "suffix"))
    for rows, tag, expect in cases:
        b = Baseline.from_rows(rows, params=params)
        got = score_f3(vendor_profile("kappa supply inc", "9999"), b, params)
        assert got is not None, tag
        assert got.what_differs == expect, tag  # the account is listed only where accounts are stable


def test_stability_share_boundary(params):
    # 4 of 5 members share one account: exactly the 0.8 share, so stable
    rows = stable_history()
    rows[4]["vendor_remit_acct_last4"] = "7777"
    assert 4 / 5 >= F3_STABLE_ACCOUNT_SHARE
    b = Baseline.from_rows(rows, params=params)
    assert score_f3(vendor_profile("kappa supply llc", "9999"), b, params) is not None
    # 3 of 5: not stable
    rows[3]["vendor_remit_acct_last4"] = "7778"
    b = Baseline.from_rows(rows, params=params)
    assert score_f3(vendor_profile("kappa supply llc", "9999"), b, params) is None


def test_too_few_accounts_is_not_stable(params):
    rows = stable_history()[:3]
    rows[1]["vendor_remit_acct_last4"] = ""
    rows[2]["vendor_remit_acct_last4"] = ""
    b = Baseline.from_rows(rows, params=params)  # one account observation, below min_vendor_deals
    assert score_f3(vendor_profile("kappa supply llc", "9999"), b, params) is None


def test_clean_unstable_history_does_not_fire_f3_on_itself(params):
    rows = unstable_history() + [
        deal_row(f"O-{i:03d}", iso_day(10 + i), equipment_vendor=f"Other Vendor {i} LLC",
                 vendor_remit_acct_last4=f"30{i}") for i in range(20)
    ]
    cal = compute_thresholds(Baseline.from_rows(rows, params=params), params)
    assert cal.fire_rate_clean["F3"] == 0.0


# ------------------------------------------------------------------------ F5

def vocab_baseline(params, n=60):
    deals, deps = [], []
    for i in range(n):
        deals.append(deal_row(f"X-{i:03d}", iso_day(i)))
        label = "Mon-Fri" if i % 3 else "Mon-Sat"
        deps += deposit_rows(f"X-{i:03d}", [(10, round(0.05 + 0.002 * i, 3), label)] * 6)
    b = Baseline.from_rows(deals, deps, params)
    return b, compute_thresholds(b, params)


def labelled(label, share):
    return DealProfile("q", {}, deposit_features([
        {"deposit_count": "60", "pct_deposits_multiple_of_100": str(share), "deposit_weekdays": label}]))


def fires(b, cal, params, label, share):
    res = score_f5(labelled(label, share), b, params, cal.reference)
    return res.bits > 0 and res.bits >= cal.tau["F5"], res


def test_merely_rare_labels_with_ordinary_round_share_do_not_fire(params):
    b, cal = vocab_baseline(params)
    assert cal.tau["F5"] >= floor_bits(0.95)
    for label in ("Tue-Sun", "Mon-Fri,Sun"):  # more spread than, or only slightly off, the usual days
        fired, res = fires(b, cal, params, label, 0.1)
        assert not fired, (label, res)
        assert res.stat_bits["kl"] > cal.tau["F5"] > res.stat_bits["conc"]  # unlike history, not concentrated


def test_concentrated_and_unlike_weekday_pattern_fires(params):
    b, cal = vocab_baseline(params)
    for label in ("Mon,Thu", "Sat,Sun"):
        fired, res = fires(b, cal, params, label, 0.1)
        assert fired and res.stat == "weekday", (label, res)
        assert "concentrated and unlike history" in res.evidence


def test_high_round_share_fires_through_the_round_component_alone(params):
    b, cal = vocab_baseline(params)
    fired, res = fires(b, cal, params, "Mon-Fri", 1.0)
    assert fired and res.stat == "round"
    assert min(res.stat_bits["conc"], res.stat_bits["kl"]) < cal.tau["F5"]  # weekday part alone would not fire
    fired, res = fires(b, cal, params, "Mon,Thu", 1.0)
    assert fired


def test_ordinary_labels_and_shares_do_not_fire(params):
    b, cal = vocab_baseline(params)
    for label in ("Mon-Fri", "Mon-Sat"):
        assert not fires(b, cal, params, label, 0.1)[0]


def test_f5_bits_is_max_of_round_and_min_of_weekday_parts():
    ref = {"round": [0.1, 0.2, 0.3, 0.4], "conc": [-2.5, -2.4, -2.3, -2.2], "kl": [0.0, 0.1, 0.2, 0.3]}
    high_round = {"round": 0.9, "conc": -2.6, "kl": 0.0}
    bits, name = f5_bits(high_round, ref)
    assert name == "round" and bits == pytest.approx(2.3219, abs=1e-3)
    only_conc = {"round": 0.05, "conc": -1.0, "kl": 0.0}  # concentrated but like history
    bits, name = f5_bits(only_conc, ref)
    assert bits <= 1.0 and name == "round"
    both = {"round": 0.05, "conc": -1.0, "kl": 0.9}
    bits, name = f5_bits(both, ref)
    assert name == "weekday" and bits == pytest.approx(2.3219, abs=1e-3)
    assert f5_bits(both, {}) == (0.0, "round")  # no reference: nothing to compare against


def test_percentile_and_live_score_use_the_same_combination(params):
    b, cal = vocab_baseline(params)
    assert {k: len(v) for k, v in cal.reference.items()} == {s: 60 for s in F5_STATS}
    bits = []
    for i in clean_ids(b, params):
        st = f5_statistics(b.deals[i].profile, b, params, exclude=i)
        bits.append(f5_bits(st, cal.reference)[0])
        live = score_f5(b.deals[i].profile, b, params, cal.reference, exclude=i)
        assert live.bits == bits[-1]
    # the clean-set fire rate in the calibration record is recomputed from those same bits
    expected = sum(1 for x in bits if x > 0 and x >= cal.tau["F5"]) / len(bits)
    assert cal.fire_rate_clean["F5"] == pytest.approx(expected)
