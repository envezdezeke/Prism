"""Fact and entity extraction (owner: Phase 3, READ-02, READ-03).

Contract: both functions are full recomputes over ``state.docs``; the caller replaces
``state.facts`` / ``state.entities`` with the return value. Facts carry source_doc and
confidence; unknown values are simply absent (the writer emits null).
"""
from __future__ import annotations

from prism.contract import Extracted, Fact
from prism.engine.config import Rules
from prism.engine.state import DealState, EntityRef

FACT_FIELDS: tuple[str, ...] = tuple(Extracted.model_fields)


def extract_facts(state: DealState, rules: Rules) -> dict[str, Fact]:
    """Return the facts known from the visible docs, keyed by Extracted field. Stub: empty."""
    return {}


def extract_entities(state: DealState, rules: Rules) -> list[EntityRef]:
    """Return graph attributes (preparer, phone, agent, ...) from the visible docs. Stub: empty."""
    return []
