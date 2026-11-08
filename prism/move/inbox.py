"""Requests and replies: the one reply path scripted personas and the future API share.

``send_request`` writes a HumanRequest. ``record_reply`` is the only way an answer is
written: scripted personas call it from the stage machine and the API calls it for a human
reply, so both move a deal identically. Replies are validated against the gate's options
(T-qx3-01); the request payload is never editable from a reply.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from prism.contract import HumanRequest
from prism.engine.config import Rules
from prism.engine.state import DealState
from prism.move.runtime import MoveRuntime, ReqMeta, get_runtime
from prism.move.settings import MoveConfig, Persona, get_config
from prism.move.timeutil import business_add, iso, to_sim

BORROWER = "borrower"


class ReplyError(ValueError):
    """A reply that cannot be recorded: unknown request, unknown option, or not pending."""


def gate_options(gate_type: str) -> tuple[str, ...]:
    g = get_config().gates.get(gate_type)
    return g.options if g else ()


def answer_option(gate_type: str) -> Optional[str]:
    return get_config().responder.answers.get(gate_type)


def persona_for(to: str, gate_type: str, cfg: Optional[MoveConfig] = None) -> Optional[Persona]:
    cfg = cfg or get_config()
    r = cfg.responder
    name = r.by_person.get(to) or r.by_type.get(gate_type) or r.default
    return r.personas.get(name)


def due_time(to: str, gate_type: str, at: datetime) -> Optional[datetime]:
    """When a scripted persona would answer; None for the borrower or a persona that never does."""
    cfg = get_config()
    if to == BORROWER or gate_type not in cfg.gates:
        return None
    p = persona_for(to, gate_type, cfg)
    if p is None:
        return None
    return business_add(at + timedelta(hours=p.wall_hours), p.business_minutes, cfg)


def send_request(
    state: DealState,
    rt: MoveRuntime,
    gate: str,
    to: str,
    at: datetime,
    message: str,
    stage: str,
    group: str,
    kind: str,
) -> int:
    at = to_sim(at)
    state.human_requests.append(HumanRequest(type=gate, to=to, at=iso(at), message=message))
    idx = len(state.human_requests) - 1
    rt.reqs.append(
        ReqMeta(idx=idx, gate=gate, stage=stage, group=group, to=to, kind=kind, at=at, due=due_time(to, gate, at))
    )
    return idx


def meta_for(rt: MoveRuntime, idx: int) -> Optional[ReqMeta]:
    for m in rt.reqs:
        if m.idx == idx:
            return m
    return None


def pending_requests(state: DealState) -> list[tuple[int, HumanRequest]]:
    """Requests a human can still answer (addressed to a person, no answer, not superseded)."""
    rt = get_runtime(state)
    out = []
    for m in rt.reqs:
        req = state.human_requests[m.idx]
        if req.answer is None and not m.superseded and m.to != BORROWER and m.gate in get_config().gates:
            out.append((m.idx, req))
    return out


def record_reply(state: DealState, rules: Rules, idx: int, option: str, at: datetime) -> None:
    """Write an answer. Rejects unknown options and requests that are not pending."""
    rt = get_runtime(state)
    m = meta_for(rt, idx)
    if m is None or not (0 <= idx < len(state.human_requests)):
        raise ReplyError(f"no such request: {idx}")
    req = state.human_requests[idx]
    if m.to == BORROWER or m.gate not in get_config().gates:
        raise ReplyError(f"request {idx} is not answerable by reply")
    if req.answer is not None or m.superseded:
        raise ReplyError(f"request {idx} is not pending")
    if option not in gate_options(m.gate):
        raise ReplyError(f"{option!r} is not an option for {m.gate}")
    at = max(to_sim(at), m.at)
    req.answer = option
    req.answered_at = iso(at)
    m.recorded, m.option, m.answered_at = True, option, at
    label = get_config().responder.superseded_label
    for other in rt.reqs:
        if other is m or other.group != m.group:
            continue
        o_req = state.human_requests[other.idx]
        if o_req.answer is None:
            o_req.answer = label
            o_req.answered_at = iso(at)
            other.superseded = True
