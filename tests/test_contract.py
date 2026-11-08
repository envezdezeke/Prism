"""Contract tests: fixtures validate, validators accept/reject, every endpoint behaves."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from prism.api.app import create_app
from prism.contract import (
    ISSUE_RE,
    Clock,
    ClockAdvance,
    parse_sim_time,
)

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"

FIXTURE_MODELS: dict[str, object] = {
    "clock.json": Clock,
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
