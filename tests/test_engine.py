"""Engine skeleton: config, money, interface surface, tracer slice."""
from __future__ import annotations

import importlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from prism.contract import Submission
from prism.engine.config import (
    ConfigError,
    Rules,
    load_assignments,
    load_fraud_config,
    load_rules,
    load_stages,
    load_teams,
)
from prism.engine.money import cents_to_number, to_cents
from prism.engine.run import run_sim
from prism.engine.writer import build_submission

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "participant"


# ------------------------------------------------------------ fraud.yaml


def test_fraud_yaml_values():
    c = load_fraud_config()
    assert c.percentiles == {"F2": 0.95, "F3": 0.95, "F4": 0.95, "F5": 0.95}
    assert c.f1_rarity_fraction == 0.02
    assert c.f1_min_linked_deals == 2
    assert c.hold_required == ("F1",)
    assert c.hold_additional_from == ("F2", "F3", "F4", "F5")
    assert c.hold_min_additional == 2
    assert c.non_voting == ("F6",)
    assert c.history_min_links == 2
    assert (c.train_end, c.test_start, c.test_end) == (
        date(2026, 6, 30), date(2026, 7, 1), date(2026, 10, 31),
    )


def _cfg(tmp_path, mutate):
    raw = yaml.safe_load((ROOT / "config" / "fraud.yaml").read_text(encoding="utf-8"))
    mutate(raw)
    p = tmp_path / "fraud.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


def test_bad_percentile(tmp_path):
    with pytest.raises(ConfigError):
        load_fraud_config(_cfg(tmp_path, lambda r: r["families"]["F2"].update(percentile=1.5)))


def test_f6_cannot_vote(tmp_path):
    with pytest.raises(ConfigError):
        load_fraud_config(_cfg(tmp_path, lambda r: r["families"]["F6"].update(votes=True)))


def test_unknown_hold_family(tmp_path):
    with pytest.raises(ConfigError):
        load_fraud_config(_cfg(tmp_path, lambda r: r["hold_rule"]["additional_from"].append("F9")))


def test_non_voting_family_cannot_count_toward_hold(tmp_path):
    with pytest.raises(ConfigError):
        load_fraud_config(_cfg(tmp_path, lambda r: r["hold_rule"]["additional_from"].append("F6")))


def test_min_additional_out_of_range(tmp_path):
    with pytest.raises(ConfigError):
        load_fraud_config(_cfg(tmp_path, lambda r: r["hold_rule"].update(min_additional=9)))


def test_calibration_order(tmp_path):
    with pytest.raises(ConfigError):
        load_fraud_config(
            _cfg(tmp_path, lambda r: r["calibration"].update(test_start="2026-06-01"))
        )


def test_min_linked_deals_floor(tmp_path):
    with pytest.raises(ConfigError):
        load_fraud_config(_cfg(tmp_path, lambda r: r["families"]["F1"].update(min_linked_deals=1)))


def test_yaml_is_safe_loaded(tmp_path):
    p = tmp_path / "evil.yaml"
    p.write_text("families: !!python/object/apply:os.getcwd []\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_fraud_config(p)


def test_missing_fraud_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_fraud_config(tmp_path / "nope.yaml")


# ------------------------------------------------------------ data-pack loaders


def test_loaders_on_minimal_json(tmp_path):
    (tmp_path / "s.json").write_text(
        json.dumps({
            "pipeline": ["A", "B"],
            "stages": {"A": {"sla_hours": 8, "human_gate": None},
                       "B": {"sla_hours": 24, "human_gate": {"type": "x"}}},
        }),
        encoding="utf-8",
    )
    (tmp_path / "t.json").write_text(
        json.dumps({"people": [{"id": "p.one", "backup": "p.two", "escalates_to": "p.boss"}],
                    "routing": {"A": "text"}}),
        encoding="utf-8",
    )
    (tmp_path / "a.json").write_text(
        json.dumps({"F": {"relationship_manager": "p.one", "credit_officer": "p.two"}}),
        encoding="utf-8",
    )
    s = load_stages(tmp_path / "s.json")
    assert s.pipeline == ("A", "B") and s.sla_hours("A") == 8.0 and s.sla_hours("Z") is None
    assert s.gate("A") is None and s.gate("B") == {"type": "x"}
    t = load_teams(tmp_path / "t.json")
    assert t.backup_of("p.one") == "p.two" and t.escalates_to("p.one") == "p.boss"
    assert t.person("nobody") is None
    a = load_assignments(tmp_path / "a.json")
    assert a.rm("F") == "p.one" and a.credit_officer("F") == "p.two" and a.rm("Q") is None


def test_bad_json_is_config_error(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("[1]", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_stages(p)
    p.write_text("{oops", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_stages(p)


def test_load_rules_warns_on_missing(tmp_path):
    r = load_rules(tmp_path)
    assert isinstance(r, Rules) and r.fraud is not None
    assert len(r.warnings) == 3 and r.history_dir is None
    assert load_rules(None).warnings == ()


@pytest.mark.skipif(not DATA.is_dir(), reason="sample data not present")
def test_loaders_on_participant_data():
    r = load_rules(DATA)
    assert r.warnings == ()
    assert r.stages.pipeline and r.stages.sla_hours(r.stages.pipeline[0])
    assert r.teams.people and r.assignments.by_folder
    assert r.history_dir is not None


# ------------------------------------------------------------ money


def test_money():
    assert to_cents("$1,234.50") == 123450
    assert to_cents(246000) == 24600000
    assert to_cents(0.125) == 13  # half-up
    assert to_cents(Decimal("2.005")) == 201
    assert to_cents("1,000") == 100000
    for bad in (True, float("nan"), float("inf"), "abc", None, "12-34"):
        with pytest.raises(ValueError):
            to_cents(bad)
    assert cents_to_number(24600000) == 246000 and isinstance(cents_to_number(24600000), int)
    assert cents_to_number(123450) == 1234.5


# ------------------------------------------------------------ interface surface

SURFACE = {
    "prism.engine.state": ["PIPELINE", "Doc", "EntityRef", "DealState"],
    "prism.read.classify": ["DOC_CLASSES", "classify"],
    "prism.read.extract": ["FACT_FIELDS", "extract_facts", "extract_entities"],
    "prism.read.issues": ["detect_issues"],
    "prism.move.stage": ["step_deal"],
    "prism.move.routing": ["route_gate"],
    "prism.move.sla": ["sla_pct", "sla_alerts"],
    "prism.fraud.baseline": ["Baseline", "build_baseline"],
    "prism.fraud.graph": ["EntityGraph", "build_graph"],
    "prism.fraud.signals": ["FamilySignal", "compute_signals"],
    "prism.fraud.decide": ["FraudOutcome", "decide", "evaluate"],
    "prism.engine.config": [
        "ConfigError", "Rules", "Stages", "Teams", "Assignments", "FraudConfig",
        "load_stages", "load_teams", "load_assignments", "load_fraud_config", "load_rules",
    ],
    "prism.engine.run": ["run_sim", "RunResult"],
    "prism.engine.writer": ["build_submission", "dumps", "write_submission"],
    "prism.engine.visibility": ["ArrivalLog", "Arrival", "SIM_TZ", "parse_time"],
}

SIGNATURES = {
    ("prism.read.classify", "classify"): ["doc"],
    ("prism.read.extract", "extract_facts"): ["state", "rules"],
    ("prism.read.extract", "extract_entities"): ["state", "rules"],
    ("prism.read.issues", "detect_issues"): ["state", "rules", "now"],
    ("prism.move.stage", "step_deal"): ["state", "rules", "now"],
    ("prism.move.routing", "route_gate"): ["gate_type", "state", "rules", "now"],
    ("prism.move.sla", "sla_pct"): ["state", "rules", "now"],
    ("prism.move.sla", "sla_alerts"): ["state", "rules", "now"],
    ("prism.fraud.baseline", "build_baseline"): ["history_dir", "cfg"],
    ("prism.fraud.graph", "build_graph"): ["states", "baseline"],
    ("prism.fraud.signals", "compute_signals"): ["graph", "states", "baseline", "cfg", "now"],
    ("prism.fraud.decide", "decide"): ["signals", "graph", "states", "baseline", "cfg", "now"],
    ("prism.fraud.decide", "evaluate"): ["states", "baseline", "cfg", "now"],
}


def test_interface_surface_is_pinned():
    import inspect

    for mod, names in SURFACE.items():
        m = importlib.import_module(mod)
        for n in names:
            assert hasattr(m, n), f"{mod}.{n} missing"
    for (mod, fn), params in SIGNATURES.items():
        got = list(inspect.signature(getattr(importlib.import_module(mod), fn)).parameters)
        assert got == params, f"{mod}.{fn} signature changed: {got}"


def test_deal_state_fields_pinned():
    from dataclasses import fields

    from prism.engine.state import DealState

    assert [f.name for f in fields(DealState)] == [
        "folder", "docs", "facts", "entities", "features", "issues", "resolved_issues",
        "stage", "stage_entered_at", "stage_log", "human_requests", "alerts", "fraud",
        "last_arrival_at", "error",
    ]


def test_doc_classes_and_fact_fields():
    from prism.contract import Extracted
    from prism.read.classify import DOC_CLASSES
    from prism.read.extract import FACT_FIELDS

    assert "other" in DOC_CLASSES and "bank_statement" in DOC_CLASSES
    assert FACT_FIELDS == tuple(Extracted.model_fields)


# ------------------------------------------------------------ tracer


def test_tracer_tiny_set_to_valid_submission(tiny_set):
    folder, arrivals = tiny_set
    result = run_sim(folder, arrivals)
    assert sorted(result.states) == ["Alpha Trading", "Beta & Sons"]
    assert result.n_files == 4 and result.n_ticks == 4
    assert result.unattached == ["notice.txt"]
    payload = build_submission(
        result.states, result.history_flags, result.errors, team="T", set_name="sample"
    )
    assert sorted(payload["deals"]) == ["Alpha Trading", "Beta & Sons"]
    for deal in payload["deals"].values():
        assert set(deal) == {"extracted", "issues", "stage_log", "human_requests", "alerts", "fraud"}
        assert all(v is None for v in deal["extracted"].values())
        assert deal["issues"] == [] and deal["stage_log"] == []
        assert deal["fraud"]["flagged"] is False and deal["fraud"]["held"] is False
    assert payload["history_flags"] == []
    Submission.model_validate(payload)


def test_docs_appear_only_after_arrival(tiny_set):
    from prism.engine.visibility import parse_time

    folder, arrivals = tiny_set
    result = run_sim(folder, arrivals, end=parse_time("2026-01-05T09:45"))
    names = {k: [d.name for d in v.docs] for k, v in result.states.items()}
    assert names == {"Alpha Trading": ["01_app.pdf", "02_id.pdf"], "Beta & Sons": ["02_id.pdf"]}


def test_deal_dir_without_arrivals_still_gets_an_entry(tiny_set):
    folder, arrivals = tiny_set
    (folder / "Gamma Foods").mkdir()
    result = run_sim(folder, arrivals)
    assert "Gamma Foods" in result.states and result.states["Gamma Foods"].docs == []


def test_missing_arrivals_file_is_a_usage_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_sim(tmp_path, tmp_path / "none.jsonl")
