"""Sim loop (D-04): step the sim clock over arrival times, ingest -> fraud -> move per tick.

Deterministic: no wall clock, no randomness, no unsorted set iteration. Every entry point
is called through its module (never ``from x import fn``) so a test can monkeypatch one
step. A crash inside one deal's step freezes only that deal (``DealState.error``); the
file is still written.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from prism.engine.config import Rules, load_rules
from prism.engine.state import DealState, Doc
from prism.engine.visibility import Arrival, ArrivalLog
from prism.fraud import baseline as fraud_baseline
from prism.fraud import decide as fraud_decide
from prism.move import sla as move_sla
from prism.move import stage as move_stage
from prism.read import classify as read_classify
from prism.read import extract as read_extract
from prism.read import issues as read_issues

log = logging.getLogger("prism")

_SKIP = object()  # step not built yet (NotImplementedError)
_MAX_ERR = 300


@dataclass
class RunResult:
    states: dict[str, DealState] = field(default_factory=dict)
    history_flags: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    unattached: list[str] = field(default_factory=list)
    n_files: int = 0
    n_ticks: int = 0


def _short(step: str, exc: BaseException) -> str:
    msg = " ".join(f"{step}: {type(exc).__name__}: {exc}".split())
    return msg[:_MAX_ERR]


def _guard(state: DealState, step: str, fn: Callable[..., Any], *args: Any) -> Any:
    """Run one step for one deal. Returns the result, or _SKIP if unbuilt or crashed."""
    try:
        return fn(*args)
    except NotImplementedError:
        return _SKIP
    except Exception as e:  # noqa: BLE001 - isolate the deal, keep the run going
        log.error("deal %r step %s crashed", state.folder, step, exc_info=True)
        if state.error is None:
            state.error = _short(step, e)
        return _SKIP


def deal_dirs(folder: Path) -> list[str]:
    """Immediate subdirectory names of the shared folder (dot-directories ignored)."""
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if p.is_dir() and not p.name.startswith("."))


def _new_doc(folder: Path, a: Arrival) -> Doc:
    return Doc(path=a.path, name=a.name, arrive_at=a.arrive_at, abs_path=folder.joinpath(*a.path.split("/")))


def _ingest(state: DealState, new: list[Arrival], folder: Path, rules: Rules, now: datetime) -> None:
    for a in new:
        doc = _new_doc(folder, a)
        classified = _guard(state, "classify", read_classify.classify, doc)
        state.docs.append(doc if classified is _SKIP else classified)
        if state.error:
            return
    state.last_arrival_at = new[-1].arrive_at
    facts = _guard(state, "extract_facts", read_extract.extract_facts, state, rules)
    if facts is not _SKIP:
        state.facts = facts
    entities = _guard(state, "extract_entities", read_extract.extract_entities, state, rules)
    if entities is not _SKIP:
        state.entities = entities
    issues = _guard(state, "detect_issues", read_issues.detect_issues, state, rules, now)
    if issues is not _SKIP:
        open_now = sorted(set(issues))
        for old in state.issues:
            if old not in open_now and old not in state.resolved_issues:
                state.resolved_issues.append(old)
        state.issues = open_now


def run_sim(
    folder: Path,
    arrivals_path: Path,
    *,
    data_root: Optional[Path] = None,
    fraud_path: Optional[Path] = None,
    end: Optional[datetime] = None,
    end_grace_minutes: int = 30,
) -> RunResult:
    """Step the sim clock over every arrival time.

    If ``end`` is None the run stops at the last arrival plus ``end_grace_minutes``
    (default 30 = the J11 quiet window), so quiet-gated actions on the final
    documents still fire. The judged end time is unconfirmed (question for the
    organizers); pass ``end`` explicitly to override, or ``end_grace_minutes=0``
    to stop exactly at the last arrival.
    """
    folder = Path(folder)
    rules = load_rules(data_root, fraud_path=fraud_path)
    alog = ArrivalLog.from_jsonl(arrivals_path)  # FileNotFoundError is a usage error
    result = RunResult(errors=list(alog.errors), unattached=alog.unattached())
    result.errors.extend(f"config: {w}" for w in rules.warnings)

    names = sorted(set(alog.folders()) | set(deal_dirs(folder)))
    states = {n: DealState(folder=n) for n in names}
    result.states = states

    base = fraud_baseline.build_baseline(rules.history_dir, rules.fraud)

    arrival_times = list(alog.times())
    if end is None and end_grace_minutes > 0 and arrival_times:
        end = max(arrival_times) + timedelta(minutes=end_grace_minutes)
    ticks = [t for t in arrival_times if end is None or t <= end]
    if end is not None and (not ticks or ticks[-1] != end):
        ticks.append(end)

    seen: set[str] = set()
    for now in ticks:
        result.n_ticks += 1
        visible = alog.visible_files(now)
        fresh: dict[str, list[Arrival]] = {}
        for a in visible:
            if a.path in seen or "/" not in a.path:
                continue
            seen.add(a.path)
            fresh.setdefault(a.folder, []).append(a)
            result.n_files += 1

        # (a) ingest
        for name in sorted(fresh):
            state = states[name]
            if state.error is None:
                _ingest(state, fresh[name], folder, rules, now)

        # (b) fraud, one pass over every deal
        try:
            outcome = fraud_decide.evaluate(states, base, rules.fraud, now)
            for name in sorted(outcome.per_deal):
                if name in states:
                    states[name].fraud = outcome.per_deal[name]
            result.history_flags = sorted(set(outcome.history_flags))
        except NotImplementedError:
            pass
        except Exception as e:  # noqa: BLE001
            log.error("fraud pass crashed", exc_info=True)
            result.errors.append(_short("fraud", e))

        # (c) move
        for name in sorted(states):
            state = states[name]
            if state.error is not None:
                continue
            _guard(state, "step_deal", move_stage.step_deal, state, rules, now)
            if state.error is not None:
                continue
            due = _guard(state, "sla_alerts", move_sla.sla_alerts, state, rules, now)
            if due is not _SKIP:
                state.alerts.extend(due)
    return result
