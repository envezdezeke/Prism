"""Contract tests: fixtures validate, validators accept/reject, every endpoint behaves."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from prism.api.app import create_app
from prism.contract import (
    ISSUE_RE,
    AlertFeedItem,
    Clock,
    ClockAdvance,
    DealDetail,
    DealSummary,
    Submission,
    parse_sim_time,
)
from prism.derive import derive

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"

FIXTURE_MODELS: dict[str, object] = {
    "clock.json": Clock,
    "deals.json": list[DealSummary],
    "deal_detail.json": dict[str, DealDetail],
    "alerts.json": list[AlertFeedItem],
    "submission.json": Submission,
}


def load(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    return TestClient(create_app())


@pytest.mark.parametrize("name", sorted(FIXTURE_MODELS))
def test_fixture_validates(name):
    TypeAdapter(FIXTURE_MODELS[name]).validate_python(load(name))


# ------------------------------------------------------------ sim time

@pytest.mark.parametrize("s", ["2026-11-02T09:30-06:00", "2026-11-02T09:30:00-06:00"])
def test_sim_time_accepts(s):
    parse_sim_time(s)
    Clock(now=s, start=s, end=s)


@pytest.mark.parametrize(
    "s",
    [
        "2026-11-02T09:30Z",
        "2026-11-02T09:30-05:00",
        "2026-11-02T09:30",
        "2026-11-02 09:30-06:00",
        "not-a-time-06:00",
    ],
)
def test_sim_time_rejects(s):
    with pytest.raises(ValueError):
        parse_sim_time(s)
    with pytest.raises(ValidationError):
        Clock(now=s, start=s, end=s)


# ------------------------------------------------------------ issue grammar

DOCS = [
    "application", "guarantor_id", "certificate_of_formation", "ein_letter",
    "bank_statement_2026-09", "financial_statements", "tax_return", "equipment_quote",
]
MISMATCH = [
    "legal_name", "ein", "amount_requested", "guarantor_name", "guarantor_dob",
    "guarantor_address", "annual_revenue", "bank_balance",
]
TRICKS = ["STMT_TAMPER", "REV_INFLATION", "ID_MISMATCH", "DUP_EIN", "SHELL_ADDRESS"]
ACCEPT = (
    [f"MISSING_DOC:{d}" for d in DOCS]
    + ["MISSING_PAGE:bank_statement_2026-08"]
    + [f"MISMATCH:{m}" for m in MISMATCH]
    + [f"OLD_TRICK:{t}" for t in TRICKS]
)
REJECT = [
    "MISSING_DOC:passport",
    "missing_doc:tax_return",
    "MISMATCH:ein ",
    "MISSING_DOC:tax_return\n",
    "MISSING_DOC:bank_statement_2026-5",
    "OLD_TRICK:UNKNOWN",
    "MISMATCH:ein|x",
]


@pytest.mark.parametrize("s", ACCEPT)
def test_issue_accepts(s):
    assert ISSUE_RE.fullmatch(s)


@pytest.mark.parametrize("s", REJECT)
def test_issue_rejects(s):
    assert not ISSUE_RE.fullmatch(s)


def test_clock_advance_exactly_one():
    with pytest.raises(ValidationError):
        ClockAdvance()
    with pytest.raises(ValidationError):
        ClockAdvance(hours=1, to="2026-11-03T08:00-06:00")
    ClockAdvance(hours=1)
    ClockAdvance(to="2026-11-03T08:00-06:00")


# ------------------------------------------------------------ clock endpoints

def test_get_clock(client):
    r = client.get("/api/clock")
    assert r.status_code == 200
    assert r.json() == load("clock.json")


def test_advance_clock(client):
    r = client.post("/api/clock/advance", json={"hours": 2})
    assert r.json()["now"] == "2026-11-04T20:00-06:00"
    r = client.post("/api/clock/advance", json={"hours": 100000})
    assert r.json()["now"] == load("clock.json")["end"]
    assert client.post("/api/clock/advance", json={}).status_code == 422


def test_replay_clock(client):
    r = client.post("/api/clock/replay")
    assert r.status_code == 200
    assert r.json()["now"] == load("clock.json")["start"]
    assert client.post("/api/clock/replay", json={"speed": 4}).status_code == 200


def test_cors(client):
    ok = client.options(
        "/api/clock",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options(
        "/api/clock",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in bad.headers


def test_mock_off_is_503(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    c = TestClient(create_app())
    r = c.get("/api/clock")
    assert r.status_code == 503
    assert r.json()["detail"] == "engine not wired yet"


def test_mock_unset_serves_fixtures(monkeypatch):
    monkeypatch.delenv("MOCK", raising=False)
    assert TestClient(create_app()).get("/api/clock").status_code == 200


# ------------------------------------------------------------ deals slice

def details() -> dict[str, DealDetail]:
    return TypeAdapter(dict[str, DealDetail]).validate_python(load("deal_detail.json"))


def test_derived_fixtures_are_fresh():
    for name, content in derive(details()).items():
        assert load(name) == content, f"{name} is stale; run python -m prism.derive"


def test_detail_keys_and_facts_agree():
    for folder, d in details().items():
        assert d.folder == folder
        facts = d.facts
        assert d.legal_name == (facts.legal_name.value if facts.legal_name else None)
        assert d.amount_requested == (facts.amount_requested.value if facts.amount_requested else None)
        assert d.needed_by == (facts.needed_by.value if facts.needed_by else None)


def test_issue_strings_valid():
    for d in details().values():
        for i in d.issues + d.resolved_issues:
            assert ISSUE_RE.fullmatch(i), i


def test_hold_and_watch_flags():
    for d in details().values():
        if d.held:
            assert d.fraud.held and d.fraud.flagged
        if d.watch:
            assert not d.fraud.flagged and not d.held


def test_required_scenarios():
    ds = list(details().values())
    assert any(d.held for d in ds)
    assert any(d.watch for d in ds)
    assert any(any(i.startswith("MISSING_DOC:") for i in d.issues) for d in ds)
    assert any(d.needed_by for d in ds)
    assert any({a.level for a in d.alerts} >= {"alert", "escalation"} for d in ds)


def test_deals_endpoint(client):
    r = client.get("/api/deals")
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_deal_detail_endpoint_encodings(client):
    for folder in details():
        assert client.get(f"/api/deals/{folder}").status_code == 200
        r = client.get("/api/deals/" + quote(folder, safe=""))
        assert r.status_code == 200
        assert r.json()["folder"] == folder
    assert client.get("/api/deals/nope").status_code == 404


def test_alerts_newest_first(client):
    r = client.get("/api/alerts")
    assert r.status_code == 200
    ats = [parse_sim_time(a["at"]) for a in r.json()]
    assert ats == sorted(ats, reverse=True)


def test_submission_endpoint(client):
    r = client.get("/api/submission")
    assert r.status_code == 200
    Submission.model_validate(r.json())


@pytest.mark.parametrize("path", ["/api/deals", "/api/deals/x", "/api/alerts", "/api/submission"])
def test_deals_routes_503_when_mock_off(monkeypatch, path):
    monkeypatch.setenv("MOCK", "0")
    assert TestClient(create_app()).get(path).status_code == 503


def test_no_sample_folder_names_in_fixtures():
    sample = ROOT / "data" / "participant" / "shared_folder"
    if not sample.is_dir():
        pytest.skip("sample data not present")
    names = [p.name.lower() for p in sample.iterdir() if p.is_dir()]
    for f in FIX.glob("*.json"):
        text = f.read_text(encoding="utf-8").lower()
        for n in names:
            assert n not in text, f"{f.name} contains sample folder name"
