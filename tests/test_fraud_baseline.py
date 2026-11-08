"""History index, entity graph and F1 on synthetic history (nothing from data/)."""
from __future__ import annotations

import math
from datetime import date, datetime, timezone

import pytest
from test_fraud_synth import deal_row, filler_deals, iso_day, write_history

from prism.engine.config import load_fraud_config
from prism.engine.state import DealState, EntityRef
from prism.fraud.baseline import Baseline, build_baseline
from prism.fraud.decide import FraudOutcome, evaluate
from prism.fraud.graph import build_graph
from prism.fraud.signals import compute_signals

NOW = datetime(2026, 11, 1, tzinfo=timezone.utc)
# History size for the tracer: large enough that df = 2 is under the 2% rarity fraction.
HIST_N = 150


@pytest.fixture(scope="module")
def cfg():
    return load_fraud_config()


# ------------------------------------------------------------------------ index

def test_spellings_merge_and_stats(cfg):
    rows = [
        deal_row("X-1", iso_day(0), preparer_name="Zeta Works, L.L.C."),
        deal_row("X-2", iso_day(5), preparer_name="ZETA WORKS LLC", final_status="funded",
                 repayment_status="charged_off"),
        deal_row("X-3", iso_day(9), preparer_name="Other Person", fraud_label="old_trick"),
    ]
    b = Baseline.from_rows(rows)
    assert b.n_history_deals == 3
    df, repaid, first, last = b.entity_stats("preparer", "zeta works llc")
    assert (df, repaid) == (2, 1)
    assert first == date.fromisoformat(iso_day(0)) and last == date.fromisoformat(iso_day(5))
    assert b.deals_with("preparer", "zeta works llc") == ["X-1", "X-2"]
    assert b.df("preparer", "zeta works llc", exclude="X-1") == 1
    assert b.entity_stats("preparer", "zeta works llc", exclude="X-1")[1:] == (
        0, date.fromisoformat(iso_day(5)), date.fromisoformat(iso_day(5)))
    assert b.df("preparer", "nobody") == 0
    assert b.value_counts("preparer")["zeta works llc"] == 2
    assert b.ordered_ids() == ["X-1", "X-2", "X-3"]


def test_n_effective_leave_one_out():
    b = Baseline.from_rows([deal_row("X-1"), deal_row("X-2")])
    assert b.n_effective() == 2
    assert b.n_effective("X-1") == 1
    assert b.n_effective("unknown") == 2


def test_empty_baseline_is_safe():
    b = Baseline()
    assert b.n_history_deals == 0 and b.df("preparer", "x") == 0 and b.n_effective() == 0
    assert b.warnings == [] and b.ordered_ids() == []


def test_build_never_raises(tmp_path, cfg):
    assert build_baseline(None, cfg).n_history_deals == 0
    missing = build_baseline(tmp_path / "nope", cfg)
    assert missing.n_history_deals == 0 and missing.warnings
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert build_baseline(empty_dir, cfg).warnings
    rows = [deal_row("X-1", iso_day(0)), deal_row("X-2", "not-a-date"), deal_row("X-1", iso_day(3)),
            deal_row("", iso_day(4))]
    b = build_baseline(write_history(tmp_path, rows), cfg)
    assert b.n_history_deals == 1
    text = " | ".join(b.warnings)
    assert "X-2" in text and "duplicate" in text.lower()
    assert len(b.warnings) >= 3


def test_missing_columns_degrade_to_empty(tmp_path, cfg):
    hist = tmp_path / "history"
    hist.mkdir()
    (hist / "deals.csv").write_text("deal_id,application_date\nX-1,2026-01-02\n", encoding="utf-8")
    b = build_baseline(hist, cfg)
    assert b.n_history_deals == 1 and b.df("preparer", "x") == 0


# ------------------------------------------------------------- tracer: F1 end to end

def tracer_history(tmp_path):
    rows = filler_deals(HIST_N)
    for r in rows[:30]:
        r["preparer_name"] = "Common Prep LLC"
    rows[3]["vendor_remit_acct_last4"] = "4321"
    rows[7]["vendor_remit_acct_last4"] = "4321"
    return write_history(tmp_path, rows)


def test_tracer_f1_hand_computed(tmp_path, cfg):
    base = build_baseline(tracer_history(tmp_path), cfg)
    assert base.n_history_deals == HIST_N
    cur = DealState(folder="cur-a", entities=[
        EntityRef("remit_account", "4321", "cur-a/x.pdf"),
        EntityRef("preparer", "common prep, l.l.c.", "cur-a/x.pdf"),
    ])
    states = {"cur-a": cur}
    graph = build_graph(states, base)
    assert graph.entity_weights[("remit_account", "4321")].strong
    assert not graph.entity_weights[("preparer", "common prep llc")].strong
    assert graph.entity_deals[("remit_account", "4321")] == ["X-003", "X-007", "cur-a"]

    sigs = [s for s in compute_signals(graph, states, base, cfg, NOW) if s.family == "F1"]
    assert len(sigs) == 1
    s = sigs[0]
    w = cfg.raw["families"]["F1"]["type_weights"]["remit_account"]
    beta = cfg.raw["families"]["F1"]["outcome_beta"]
    omega = 1 - beta * (2 + 1) / (2 + 2)  # both history deals repaid
    assert s.bits == pytest.approx(w * omega * -math.log2(3 / (HIST_N + 1)))
    assert s.fired and s.deals == ("cur-a", "X-003", "X-007")
    assert "remit account" in s.evidence.lower()


def test_current_vs_current_link_without_history(tmp_path, cfg):
    base = build_baseline(tracer_history(tmp_path), cfg)
    ent = [EntityRef("registered_agent", "Brand New Agent Co", "d/p.pdf")]
    states = {"a": DealState(folder="a", entities=list(ent)), "b": DealState(folder="b", entities=list(ent)),
              "c": DealState(folder="c", entities=[EntityRef("registered_agent", "Lonely Agent", "d")])}
    sigs = compute_signals(build_graph(states, base), states, base, cfg, NOW)
    by_deal = {s.deals[0]: s for s in sigs if s.family == "F1"}
    assert set(by_deal) == {"a", "b"}
    assert by_deal["a"].deals == ("a", "b") and by_deal["b"].deals == ("b", "a")
    w = cfg.raw["families"]["F1"]["type_weights"]["registered_agent"]
    beta = cfg.raw["families"]["F1"]["outcome_beta"]
    assert by_deal["a"].bits == pytest.approx(w * (1 - beta * 1 / 2) * math.log2(HIST_N + 1))


def test_errored_state_is_skipped_and_empty_baseline_gives_nothing(tmp_path, cfg):
    base = build_baseline(tracer_history(tmp_path), cfg)
    ent = [EntityRef("remit_account", "4321", "d")]
    states = {"a": DealState(folder="a", entities=ent, error="boom")}
    assert compute_signals(build_graph(states, base), states, base, cfg, NOW) == []
    states = {"a": DealState(folder="a", entities=ent)}
    assert compute_signals(build_graph(states, Baseline()), states, Baseline(), cfg, NOW) == []


def test_signals_are_deterministic(tmp_path, cfg):
    base = build_baseline(tracer_history(tmp_path), cfg)
    states = {k: DealState(folder=k, entities=[EntityRef("remit_account", "4321", "d")]) for k in "ba"}
    one = compute_signals(build_graph(states, base), states, base, cfg, NOW)
    two = compute_signals(build_graph(dict(reversed(states.items())), base),
                          dict(reversed(states.items())), base, cfg, NOW)
    assert one == two


def test_engine_output_unchanged_decide_is_stub(tmp_path, cfg):
    base = build_baseline(tracer_history(tmp_path), cfg)
    states = {"a": DealState(folder="a", entities=[EntityRef("remit_account", "4321", "d")])}
    out = evaluate(states, base, cfg, NOW)
    assert out == FraudOutcome() and out.per_deal == {} and out.clusters == []
