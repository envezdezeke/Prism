"""Stage machine (owner: Phase 4, MOVE-01..).

Contract: ``step_deal`` mutates the state in place (stage, stage_entered_at, stage_log,
human_requests, alerts). A fraud hold blocks any advance. Called once per tick for every
deal without an error.

``step_deal`` catches up everything between the previous call and ``now`` in two passes of
one event loop. Pass 1 replays events strictly before ``now`` with the PREVIOUS view of what
Read reported (so a stage is not judged on an issue list that did not exist yet); pass 2
replays events up to and including ``now`` with the CURRENT view. Every action is guarded by
a runtime flag or emitted key, so calling twice at the same ``now`` changes nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from prism.contract import StageLogEntry
from prism.engine.config import Rules
from prism.engine.state import DealState
from prism.move import inbox, messages, routing
from prism.move.runtime import MoveRuntime, View, get_runtime
from prism.move.settings import MoveConfig, get_config
from prism.move.sla import stage_limit_hours
from prism.move.timeutil import fmt_when, iso, to_sim

MAX_EVENTS = 10_000  # T-qx3-02: one call cannot fan out forever

P_START, P_FREEZE, P_LADDER, P_CHASE, P_ANSWER, P_EVAL = 0, 1, 2, 3, 4, 5


@dataclass
class Run:
    state: DealState
    rules: Rules
    rt: MoveRuntime
    cfg: MoveConfig
    now: datetime
    view: View
    count: int = 0


# ------------------------------------------------------------ helpers


def _view(state: DealState) -> View:
    docs = state.docs
    first = min((to_sim(d.arrive_at) for d in docs), default=None)
    last = state.last_arrival_at
    if last is None:
        last = max((d.arrive_at for d in docs), default=None)
    facts = frozenset(k for k, f in state.facts.items() if f is not None and f.value not in (None, ""))
    return View(
        issues=tuple(sorted(set(state.issues))),
        last_arrival=to_sim(last) if last is not None else None,
        first_doc=first,
        facts=facts,
    )


def _matches(patterns, issue: str) -> bool:
    return any(p.fullmatch(issue) for p in patterns)


def _pipeline(run: Run) -> tuple[str, ...]:
    return run.rules.stages.pipeline


def _next_stage(run: Run, stage: str) -> Optional[str]:
    pipe = _pipeline(run)
    i = pipe.index(stage)
    return pipe[i + 1] if i + 1 < len(pipe) else None


def _is_frozen(run: Run) -> bool:
    return run.rt.frozen_at is not None


def _open_entry(run: Run) -> Optional[StageLogEntry]:
    for e in reversed(run.state.stage_log):
        if e.stage == run.state.stage and e.exited_at is None:
            return e
    return None


def _log_enter(run: Run, stage: str, t: datetime, reason: str) -> None:
    run.state.stage_log.append(
        StageLogEntry(stage=stage, entered_at=iso(t), exited_at=None, decision=None, why=f"Entered {stage}: {reason}")
    )


def _enter(run: Run, stage: str, t: datetime, reason: str) -> None:
    st, rt, rules = run.state, run.rt, run.rules
    st.stage, st.stage_entered_at = stage, t
    rt.owner = routing.stage_owner(stage, st, rules, t)
    rt.limit_hours = stage_limit_hours(st, rules, stage)
    cfg = rules.stages.stages.get(stage, {})
    rt.delegated = routing.committee_delegated(st, cfg)
    ready = t
    if not rules.stages.gate(stage):
        ready = t + timedelta(minutes=run.cfg.auto_stage_minutes.get(stage, 0))
    rt.ready_at = ready
    rt.eval_pending = True
    rt.resend_after = None
    _log_enter(run, stage, t, reason)
    _on_enter(run, stage, t)


def _on_enter(run: Run, stage: str, t: datetime) -> None:
    """Stage-specific work on entry (the credit memo is added by the committee stage)."""
    return None


# ------------------------------------------------------------ requests


def _send_info(run: Run, t: datetime, items: list[str]) -> None:
    st, rt = run.state, run.rt
    msg = messages.info_request_message(st, items, run.rules)
    inbox.send_request(st, rt, "info_request", inbox.BORROWER, t, msg, st.stage, f"info:{len(rt.reqs)}", "info")
    for i in items:
        rt.requested_issues.add(i)
        rt.issue_requested_at[i] = t


def _gate_message(run: Run, gate_type: str, route: routing.Route, t: datetime) -> str:
    st, rules = run.state, run.rules
    if gate_type == "credit_decision":
        return messages.credit_decision_message(st, rules, route)
    return messages.generic_gate_message(st, rules, gate_type, route)


def _send_gate(run: Run, gate_type: str, t: datetime) -> bool:
    st, rt, rules = run.state, run.rt, run.rules
    route = routing.route_detail(gate_type, st, rules, t)
    if route is None:
        return False
    msg = _gate_message(run, gate_type, route, t)
    inbox.send_request(st, rt, gate_type, route.to, t, msg, st.stage, f"{st.stage}:{gate_type}", "gate")
    rt.gate_sent[st.stage] = True
    rt.covering[st.stage] = {"primary": route.primary, "until": route.until, "covering": route.covering}
    return True


# ------------------------------------------------------------ evaluation


def _blocking_issue(run: Run, stage: str) -> Optional[str]:
    pats = run.cfg.issues.blocking.get(stage, ())
    for i in run.view.issues:
        if _matches(pats, i):
            return i
    return None


def _is_product(run: Run, stage: str) -> bool:
    return stage == "Product" or stage in _vendor_stages(run)  # "Product" is a contract Stage literal


def _vendor_unverified(run: Run, stage: str) -> bool:
    st = run.state
    if not _is_product(run, stage):
        return False
    if messages.fact_value(st, "product") not in run.cfg.vendor_check_products:
        return False
    return messages.profile(st).get("vendor_verified") is False


def _vendor_stages(run: Run) -> tuple[str, ...]:
    """The stage whose required_to_exit mentions a vendor check (found in data, not by name)."""
    out = []
    for s in _pipeline(run):
        items = run.rules.stages.stages.get(s, {}).get("required_to_exit") or []
        if any(isinstance(x, str) and "vendor" in x.lower() for x in items):
            out.append(s)
    return tuple(out)


def _exit_why(run: Run, stage: str, detail: str, nxt: Optional[str]) -> str:
    items = run.rules.stages.stages.get(stage, {}).get("required_to_exit") or []
    seen = "; ".join(str(x) for x in items) if items else "nothing further required"
    tail = f" Moving to {nxt}." if nxt else " The deal is complete."
    return f"Checked: {seen}. {detail}{tail}"


def _evaluate(run: Run, t: datetime) -> None:
    st, rt, rules, cfg, view = run.state, run.rt, run.rules, run.cfg, run.view
    stage = st.stage
    rt.eval_pending = False
    if rt.frozen_at is not None or rt.terminal:
        return
    # Ask the borrower first, for everything missing at once (J11, MOVE-07).
    ask = [i for i in view.issues if _matches(cfg.issues.requestable, i) and i not in rt.requested_issues]
    if ask:
        _send_info(run, t, ask)
    # (1) facts the stage needs
    if any(f not in view.facts for f in cfg.required_facts.get(stage, ())):
        return
    # (3) anything open that blocks this stage
    if _blocking_issue(run, stage) is not None or _vendor_unverified(run, stage):
        return
    # (4) the human gate
    gate = rules.stages.gate(stage)
    gate_type = gate.get("type") if gate else None
    if gate_type:
        if rt.resend_after is not None:
            if view.last_arrival is not None and view.last_arrival > rt.resend_after:
                rt.resend_after = None
                rt.gate_sent[stage] = False
                rt.gate_satisfied[stage] = False
            else:
                return
        if not rt.gate_sent.get(stage):
            _send_gate(run, gate_type, t)
            return
        if not rt.gate_satisfied.get(stage):
            return
    # (5) exit
    _exit_stage(run, t, gate_type)


def _exit_detail(run: Run, stage: str, gate_type: Optional[str]) -> tuple[str, str]:
    """(decision, plain-words detail) for the log entry on exit."""
    st, rt, rules = run.state, run.rt, run.rules
    if gate_type:
        who, when = rt.decisions.get(gate_type, (None, None))
        option = rt.gate_option.get(stage, "approve")
        name = routing.person_name(rules.teams, who)
        return option, f"{name} answered {option.replace('_', ' ')} on {fmt_when(when)}." if when else f"{option}."
    if _is_product(run, stage):
        decision = f"standard pricing for {messages.product_text(st)}"
        if messages.fact_value(st, "product") in run.cfg.vendor_check_products:
            return decision, "Vendor and remit account were not flagged; standard pricing for the requested product."
        return decision, "No vendor check is needed for this product; standard pricing for the requested product."
    return "advanced", "All required items are present and consistent with the application."


def _exit_stage(run: Run, t: datetime, gate_type: Optional[str]) -> None:
    st, rt, rules = run.state, run.rt, run.rules
    stage = st.stage
    nxt = _next_stage(run, stage)
    if nxt is not None and _next_stage(run, nxt) is None:
        # Entering the last stage means money goes out: refuse while held, flagged or any issue is open.
        if st.fraud.held or st.fraud.flagged or run.view.issues:
            return
    if not _before_exit(run, stage, t):
        return
    decision, detail = _exit_detail(run, stage, gate_type)
    entry = _open_entry(run)
    if entry is not None:
        entry.exited_at, entry.decision, entry.why = iso(t), decision, _exit_why(run, stage, detail, nxt)
    if nxt is None:
        rt.terminal, rt.terminal_at = "closed", t
        rt.eval_pending = False
        return
    _enter(run, nxt, t, f"{stage} complete, {decision}")


def _before_exit(run: Run, stage: str, t: datetime) -> bool:
    return True


# ------------------------------------------------------------ event sources

Event = tuple  # (time, priority, seq, kind, payload)


def _clamp(run: Run, t: datetime) -> datetime:
    wm = run.rt.watermark
    return t if wm is None or t >= wm else wm


def _eval_time(run: Run) -> Optional[datetime]:
    rt, view = run.rt, run.view
    if not rt.eval_pending or rt.ready_at is None:
        return None
    if rt.gate_satisfied.get(run.state.stage):
        return rt.ready_at
    if view.last_arrival is None:
        return rt.ready_at
    return max(rt.ready_at, view.last_arrival + timedelta(minutes=run.cfg.quiet_minutes))


def _candidates(run: Run) -> list[Event]:
    rt, view = run.rt, run.view
    out: list[Event] = []
    if rt.terminal:
        return out
    if not rt.started:
        if view.first_doc is not None:
            out.append((view.first_doc, P_START, 0, "start", None))
        return out
    for src in _SOURCES:
        out.extend(src(run))
    return out


def _src_eval(run: Run) -> list[Event]:
    if run.rt.frozen_at is not None:
        return []
    out: list[Event] = []
    t = _eval_time(run)
    if t is not None:
        out.append((_clamp(run, t), P_EVAL, 0, "eval", None))
    pend = [i for i in run.view.issues if _matches(run.cfg.issues.immediate, i) and i not in run.rt.requested_issues]
    if pend:
        out.append((_clamp(run, run.now), P_EVAL, 1, "immediate", pend))
    return out


_SOURCES: list[Callable[[Run], list[Event]]] = [_src_eval]


def _h_start(run: Run, t: datetime, payload: Any) -> None:
    run.rt.started, run.rt.first_doc_at = True, t
    _enter(run, _pipeline(run)[0], t, f"first document arrived {fmt_when(t)}")


def _h_eval(run: Run, t: datetime, payload: Any) -> None:
    _evaluate(run, t)


def _h_immediate(run: Run, t: datetime, payload: Any) -> None:
    items = [i for i in payload if i not in run.rt.requested_issues]
    if items and run.rt.frozen_at is None:
        _send_info(run, t, items)


_HANDLERS: dict[str, Callable[[Run, datetime, Any], None]] = {
    "start": _h_start,
    "eval": _h_eval,
    "immediate": _h_immediate,
}


def _drain(run: Run, strict: bool) -> None:
    rt = run.rt
    while True:
        best = None
        for ev in _candidates(run):
            t = ev[0]
            if (t < run.now) if strict else (t <= run.now):
                if best is None or ev[:3] < best[:3]:
                    best = ev
        if best is None:
            return
        run.count += 1
        if run.count > MAX_EVENTS:
            raise RuntimeError(f"move: more than {MAX_EVENTS} events in one step")
        t, _, _, kind, payload = best
        rt.watermark = t if rt.watermark is None or t > rt.watermark else rt.watermark
        _HANDLERS[kind](run, t, payload)
        _after_event(run, t)


def _after_event(run: Run, t: datetime) -> None:
    return None


def step_deal(state: DealState, rules: Rules, now: datetime) -> None:
    """Advance the deal as far as the rules allow at ``now``."""
    if not rules.stages.pipeline:
        return None
    now = to_sim(now)
    rt = get_runtime(state)
    cur = _view(state)
    prev = rt.view
    cfg = get_config()
    if prev is not None:
        _drain(Run(state, rules, rt, cfg, now, prev), strict=True)
    if prev is None or cur != prev:
        rt.eval_pending = True
    run = Run(state, rules, rt, cfg, now, cur, count=0)
    _drain(run, strict=False)
    _finish(run)
    rt.view = cur


def _finish(run: Run) -> None:
    return None
