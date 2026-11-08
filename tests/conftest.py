"""Shared fixtures. Nothing here needs data/ and no sample names are used."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

TINY_ARRIVALS = [
    {"path": "Beta & Sons/02_id.pdf", "arrive_at": "2026-01-05T09:30-06:00"},
    {"path": "Alpha Trading/01_app.pdf", "arrive_at": "2026-01-05T09:30-06:00"},
    {"path": "Alpha Trading/02_id.pdf", "arrive_at": "2026-01-05T09:45-06:00"},
    {"path": "notice.txt", "arrive_at": "2026-01-05T10:00-06:00"},
    {"path": "Beta & Sons/01_app.pdf", "arrive_at": "2026-01-05T11:15-06:00"},
]


def write_arrivals(path: Path, rows: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def tiny_set(tmp_path):
    """Synthetic shared folder with two deals, a same-minute tie and a root-level notice."""
    folder = tmp_path / "shared"
    for row in TINY_ARRIVALS:
        p = folder.joinpath(*row["path"].split("/"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")
    arrivals = write_arrivals(tmp_path / "arrivals.jsonl", TINY_ARRIVALS)
    return folder, arrivals
