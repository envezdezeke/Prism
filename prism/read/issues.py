"""Issue detection (owner: Phase 3, READ-04).

Contract: return the FULL set of currently open ``KIND:target`` strings (valid per
``prism.contract.ISSUE_RE``), sorted. Applies the 30-sim-minute quiet rule: a doc that
could still arrive is not yet missing. The caller moves issues that disappear into
``resolved_issues``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Callable

from prism.contract import ISSUE_RE
from prism.engine.config import Rules
from prism.engine.state import DealState
from prism.read import old_tricks, requirements, statements
from prism.read.settings import get_config

log = logging.getLogger("prism")

_QUIET_KINDS = ("MISSING_DOC:", "MISSING_PAGE:")


def _missing_docs(state: DealState, rules: Rules) -> list[str]:
    return [f"MISSING_DOC:{label}" for label in requirements.required_labels(state)]


def _missing_pages(state: DealState, rules: Rules) -> list[str]:
    return [f"MISSING_PAGE:{label}" for label in statements.missing_page_labels(state)]


def _stmt_tamper(state: DealState, rules: Rules) -> list[str]:
    return ["OLD_TRICK:STMT_TAMPER"] if old_tricks.stmt_tamper(state) else []


def _rev_inflation(state: DealState, rules: Rules) -> list[str]:
    return ["OLD_TRICK:REV_INFLATION"] if old_tricks.rev_inflation(state) else []


# Rule groups run in order; each is isolated so one strange document cannot freeze the deal.
_GROUPS: tuple[tuple[str, Callable[[DealState, Rules], list[str]]], ...] = (
    ("missing_doc", _missing_docs),
    ("missing_page", _missing_pages),
    ("stmt_tamper", _stmt_tamper),
    ("rev_inflation", _rev_inflation),
)


def _quiet_over(state: DealState, now: datetime) -> bool:
    last = state.last_arrival_at
    if last is None:
        return True
    return now - last >= timedelta(minutes=get_config().quiet_minutes)


def detect_issues(state: DealState, rules: Rules, now: datetime) -> list[str]:
    """Return the sorted open issue set at ``now`` (never raises; each rule group is isolated).

    MISSING_DOC and MISSING_PAGE are first reported once ``now`` is at least ``quiet_minutes`` after the deal's
    last arrival (inclusive, J11) and stay reported while they hold (``state.issues`` is the previous open set),
    so a later arrival of an unrelated paper cannot make an old issue flicker. MISMATCH and OLD_TRICK are
    never quiet-gated.
    """
    found: set[str] = set()
    try:
        if not state.docs:
            return []
        quiet_over = _quiet_over(state, now)
        previous = set(state.issues)
    except Exception:  # noqa: BLE001
        log.error("issue detection setup failed", exc_info=True)
        return []
    for name, fn in _GROUPS:
        try:
            labels = fn(state, rules)
        except Exception:  # noqa: BLE001 - never include document text in the log
            log.error("issue rule group %s failed", name, exc_info=True)
            continue
        for label in labels:
            if not isinstance(label, str) or not ISSUE_RE.fullmatch(label):
                continue
            if label.startswith(_QUIET_KINDS) and not quiet_over and label not in previous:
                continue
            found.add(label)
    return sorted(found)


def mismatch_evidence(state: DealState, rules: Rules) -> dict[str, dict[str, str]]:
    """Per mismatch field, the application and document wording for the credit memo. Stub: empty (Task 3 fills it)."""
    return {}
