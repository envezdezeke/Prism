"""Prism API. MOCK=1 (or unset) serves fixtures; MOCK=0 returns 503 until the engine is wired."""
from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from prism.contract import (
    AlertFeedItem,
    Clock,
    ClockAdvance,
    ClockReplay,
    DealDetail,
    DealSummary,
    FraudGraph,
    InboxItem,
    InboxReply,
    InvestigatorTrace,
    RedTeamReport,
    Submission,
    format_sim_time,
    parse_sim_time,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def load_fixture(name: str) -> Any:
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


def mock_enabled() -> bool:
    return os.environ.get("MOCK", "1").strip().lower() not in ("0", "false")


def require_mock() -> None:
    if not mock_enabled():
        raise HTTPException(status_code=503, detail="engine not wired yet")


def create_app() -> FastAPI:
    app = FastAPI(title="Prism API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api = APIRouter(prefix="/api", dependencies=[Depends(require_mock)])

    # ---- clock
    @api.get("/clock", response_model=Clock)
    def get_clock() -> Any:
        return load_fixture("clock.json")

    @api.post("/clock/advance", response_model=Clock)
    def advance_clock(body: ClockAdvance) -> Any:
        clock = load_fixture("clock.json")
        end = parse_sim_time(clock["end"])
        if body.hours is not None:
            now = parse_sim_time(clock["now"]) + timedelta(hours=body.hours)
        else:
            now = parse_sim_time(body.to)  # type: ignore[arg-type]
        now = min(now, end)
        return {**clock, "now": format_sim_time(now)}

    @api.post("/clock/replay", response_model=Clock)
    def replay_clock(body: Optional[ClockReplay] = None) -> Any:
        clock = load_fixture("clock.json")
        return {**clock, "now": clock["start"]}

    # ---- deals
    @api.get("/deals", response_model=list[DealSummary])
    def list_deals() -> Any:
        return load_fixture("deals.json")

    @api.get("/deals/{folder}", response_model=DealDetail)
    def get_deal(folder: str) -> Any:
        details = load_fixture("deal_detail.json")
        if folder not in details:
            raise HTTPException(status_code=404, detail="unknown deal")
        return details[folder]

    @api.get("/alerts", response_model=list[AlertFeedItem])
    def list_alerts() -> Any:
        return load_fixture("alerts.json")

    @api.get("/submission", response_model=Submission)
    def get_submission() -> Any:
        return load_fixture("submission.json")

    # ---- inbox
    @api.get("/inbox", response_model=list[InboxItem])
    def list_inbox(status: Optional[Literal["pending", "answered"]] = None) -> Any:
        items = load_fixture("inbox.json")
        if status is not None:
            items = [i for i in items if i["status"] == status]
        return items

    @api.post("/inbox/{item_id}/reply", response_model=InboxItem)
    def reply_inbox(item_id: str, body: InboxReply) -> Any:
        item = next((i for i in load_fixture("inbox.json") if i["id"] == item_id), None)
        if item is None:
            raise HTTPException(status_code=404, detail="unknown inbox item")
        if item["status"] == "answered":
            raise HTTPException(status_code=409, detail="already answered")
        if body.option not in item["options"]:
            raise HTTPException(
                status_code=422,
                detail=f"option must be one of: {', '.join(item['options'])}",
            )
        now = load_fixture("clock.json")["now"]
        return {**item, "status": "answered", "answer": body.option, "answered_at": now}

    # ---- graph and agents
    @api.get("/graph", response_model=FraudGraph)
    def get_graph(at: Optional[str] = Query(default=None)) -> Any:
        graph = load_fixture("graph.json")
        if at is None:
            return graph
        try:
            cutoff = parse_sim_time(at)
        except ValueError:
            raise HTTPException(status_code=422, detail="at must be a sim time ending -06:00")
        edges = [e for e in graph["edges"] if parse_sim_time(e["first_visible_at"]) <= cutoff]
        used = {e["source"] for e in edges} | {e["target"] for e in edges}
        nodes = [n for n in graph["nodes"] if n["type"] != "entity" or n["id"] in used]
        return {**graph, "nodes": nodes, "edges": edges}

    @api.get("/investigator/{cluster_id}", response_model=InvestigatorTrace)
    def get_investigator(cluster_id: str) -> Any:
        trace = load_fixture("investigator.json")
        if trace["cluster_id"] != cluster_id:
            raise HTTPException(status_code=404, detail="unknown cluster")
        return trace

    @api.get("/redteam", response_model=RedTeamReport)
    def get_redteam() -> Any:
        return load_fixture("redteam.json")

    app.include_router(api)
    return app


app = create_app()
