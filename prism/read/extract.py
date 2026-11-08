"""Fact and entity extraction (owner: Phase 3, READ-02, READ-03).

Contract: both functions are full recomputes over ``state.docs``; the caller replaces
``state.facts`` / ``state.entities`` with the return value. Facts carry source_doc and
confidence; unknown values are simply absent (the writer emits null). ``extract_features`` is a
full recompute too; its dict is merged into ``state.features`` by the caller (never replaced).
"""
from __future__ import annotations

from typing import Any

from prism.contract import Extracted, Fact
from prism.engine.config import Rules
from prism.engine.state import DealState, EntityRef
from prism.engine.money import cents_to_number
from prism.read import docmodel
from prism.read.settings import get_config

FACT_FIELDS: tuple[str, ...] = tuple(Extracted.model_fields)


def extract_facts(state: DealState, rules: Rules) -> dict[str, Fact]:
    """Return the facts known from the visible docs, keyed by Extracted field. Never raises."""
    facts: dict[str, Fact] = {}
    try:
        conf = get_config().confidence
        apps = docmodel.parsed_all(state, "application")
        if apps:
            # latest arrival wins; parsed_all sorts by (arrive_at, path) so the last one is latest
            doc, app = apps[-1]
            if app.legal_name:
                facts["legal_name"] = Fact(value=app.legal_name, source_doc=doc.path,
                                           confidence=conf["label"])
            if app.amount_cents is not None:
                facts["amount_requested"] = Fact(value=cents_to_number(app.amount_cents),
                                                 source_doc=doc.path, confidence=conf["label"])
    except Exception:  # noqa: BLE001
        return facts
    return facts


def extract_entities(state: DealState, rules: Rules) -> list[EntityRef]:
    """Return graph attributes (preparer, phone, agent, ...) from the visible docs. Stub: empty."""
    return []


def extract_features(state: DealState, rules: Rules) -> dict[str, Any]:
    """Return features (deposit_months, profile) to merge into state.features. Stub: empty."""
    return {}
