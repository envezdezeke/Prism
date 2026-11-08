"""Fraud end to end on the sample: tuning deals only (D-02), compared with eval/gold.json.

Skipped when the sample data pack is absent. No deal is named here; every expectation is
read from the answer key for the tuning folders.
"""
from __future__ import annotations

import json

import pytest

from prism.contract import parse_sim_time
from prism.engine.run import run_sim
from tests.real_data import ROOT, requires_sample, sample_root, tuning_folders


@pytest.fixture(scope="module")
def sample_run():
    root = sample_root()
    if root is None:
        pytest.skip("sample data not present")
    return run_sim(root / "shared_folder", root / "sim" / "arrivals.jsonl", data_root=root)


@pytest.fixture(scope="module")
def gold():
    return json.loads((ROOT / "eval" / "gold.json").read_text(encoding="utf-8"))["deals"]


@pytest.fixture(scope="module")
def tuning():
    root = sample_root()
    if root is None:
        pytest.skip("sample data not present")
    folders = tuning_folders(root)
    assert folders
    return folders


def _flagged_gold(gold, tuning):
    return [f for f in tuning if gold[f]["fraud"]["flagged"]]


def _ring_gold(gold, tuning):
    """Gold-flagged tuning deals that have ring partners (the hold-rule path)."""
    return [f for f in _flagged_gold(gold, tuning) if gold[f]["fraud"]["linked_deals"]]


@requires_sample
def test_ring_tuning_deals_are_flagged_and_held(sample_run, gold, tuning):
    ring = _ring_gold(gold, tuning)
    assert ring
    for folder in ring:
        got = sample_run.states[folder].fraud
        assert got.flagged and got.held, "a ring tuning deal is not held"


@requires_sample
def test_good_tuning_deals_are_not_flagged(sample_run, gold, tuning):
    for folder in tuning:
        if not gold[folder]["fraud"]["flagged"]:
            got = sample_run.states[folder].fraud
            assert not got.flagged and not got.held, "a good tuning deal was flagged"


@requires_sample
def test_ring_tuning_deals_are_held_at_intake_in_the_sim_week(sample_run, gold, tuning):
    flagged = _ring_gold(gold, tuning)
    assert flagged
    for folder in flagged:
        st = sample_run.states[folder]
        assert st.fraud.stage_at_flag == "Intake"
        t = parse_sim_time(st.fraud.flagged_at)
        assert st.docs and t >= min(d.arrive_at for d in st.docs)
        assert all(e.stage == "Intake" for e in st.stage_log)
