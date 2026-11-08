"""Document classification (owner: Phase 3, READ-01).

Contract: classify by CONTENT (never the filename), fill ``doc_class``, ``period`` and
``meta``, return the same Doc, and never raise: an unreadable file becomes class "other".
"""
from __future__ import annotations

from prism.engine.state import Doc

DOC_CLASSES: tuple[str, ...] = (
    "application",
    "guarantor_id",
    "certificate_of_formation",
    "ein_letter",
    "bank_statement",
    "financial_statements",
    "tax_return",
    "equipment_quote",
    "other",
)


def classify(doc: Doc) -> Doc:
    """Fill doc_class, period and meta from the file content. Never raises. Stub: unchanged."""
    return doc
