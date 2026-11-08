"""Deterministic message text (docs/MESSAGE_TEMPLATES.md, MOVE-11).

Plain words, names not ids. Text is built with concatenation and f-strings only, never
``str.format`` on anything derived from a document (a legal name can contain braces).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from prism.engine.config import Rules
from prism.engine.money import to_cents
from prism.engine.state import DealState
from prism.move.routing import Route, person_name, rm_of
from prism.move.timeutil import fmt_date, fmt_money, fmt_when, month_label, parse_iso

NOT_PROVIDED = "not provided"

DOC_LABELS = {
    "application": "signed loan application",
    "guarantor_id": "government photo ID for each guarantor",
    "certificate_of_formation": "certificate of formation",
    "ein_letter": "IRS EIN letter",
    "financial_statements": "financial statements (profit and loss, and balance sheet)",
    "tax_return": "most recent business tax return",
    "equipment_quote": "vendor's quote for the equipment, showing the vendor's remit-to bank account",
}
FIELD_LABELS = {
    "legal_name": "legal name",
    "ein": "EIN",
    "amount_requested": "requested amount",
    "guarantor_name": "guarantor's name",
    "guarantor_dob": "guarantor's date of birth",
    "guarantor_address": "guarantor's address",
    "annual_revenue": "annual revenue",
    "bank_balance": "bank balance",
}
GATE_LABELS = {
    "credit_decision": "credit decision",
    "committee_approval": "committee approval",
    "commitment_signoff": "commitment sign-off",
    "funding_release": "funding release",
    "fraud_hold": "fraud hold",
}


# ------------------------------------------------------------ small helpers


def profile(state: DealState) -> dict[str, Any]:
    p = state.features.get("profile")
    return p if isinstance(p, dict) else {}


def fact_value(state: DealState, name: str) -> Any:
    f = state.facts.get(name)
    return None if f is None else f.value


def borrower_label(state: DealState) -> str:
    name = fact_value(state, "legal_name") or state.folder
    dba = profile(state).get("dba")
    return f"{name} ({dba})" if dba else str(name)


def borrower_name(state: DealState) -> str:
    return str(fact_value(state, "legal_name") or state.folder)


def rm_label(state: DealState, rules: Rules) -> str:
    return person_name(rules.teams, rm_of(state, rules)) if rm_of(state, rules) else NOT_PROVIDED


def money_of(value: Any) -> str:
    try:
        return fmt_money(to_cents(value))
    except (ValueError, TypeError):
        return NOT_PROVIDED


def amount_text(state: DealState) -> str:
    v = fact_value(state, "amount_requested")
    return NOT_PROVIDED if v is None else money_of(v)


def cents_text(profile_cents: Any) -> str:
    return fmt_money(profile_cents) if isinstance(profile_cents, int) and not isinstance(profile_cents, bool) else NOT_PROVIDED


def product_text(state: DealState) -> str:
    return str(fact_value(state, "product") or NOT_PROVIDED)


def purpose_text(state: DealState) -> str:
    v = fact_value(state, "purpose_category")
    return str(v).replace("_", " ") if v else NOT_PROVIDED


def term_text(state: DealState) -> str:
    v = fact_value(state, "term_months")
    return NOT_PROVIDED if v is None else str(v)


def needed_by_dt(state: DealState) -> Optional[datetime]:
    return parse_iso(fact_value(state, "needed_by"))


def needed_clause(state: DealState) -> str:
    nb = needed_by_dt(state)
    return f" Funds are needed by {fmt_when(nb)}." if nb else ""


def covering_sentence(route: Optional[Route], rules: Rules) -> str:
    if route is None or not route.covering:
        return ""
    until = f" until {fmt_date(route.until)}" if route.until else ""
    return f"You are covering for {person_name(rules.teams, route.primary)}, who is out of office{until}."


def option_words(options: tuple[str, ...]) -> str:
    return " / ".join(o.replace("_", " ") for o in options)


# ------------------------------------------------------------ issues as words

_STMT_RE = re.compile(r"^bank_statement_(\d{4}-\d{2})$")


def _split_issue(issue: str) -> tuple[str, str]:
    kind, _, target = issue.partition(":")
    return kind, target


def doc_label(target: str) -> str:
    m = _STMT_RE.match(target)
    if m:
        return f"bank statement for {month_label(m.group(1))}"
    return DOC_LABELS.get(target, target.replace("_", " "))


def evidence(state: DealState, field: str) -> Optional[dict[str, Any]]:
    ev = profile(state).get("mismatch_evidence")
    e = ev.get(field) if isinstance(ev, dict) else None
    return e if isinstance(e, dict) else None


def item_text(issue: str, state: DealState) -> str:
    """One bullet for the borrower, per MESSAGE_TEMPLATES section 4."""
    kind, target = _split_issue(issue)
    if kind == "MISSING_DOC":
        m = _STMT_RE.match(target)
        if m:
            return f"your bank statement for {month_label(m.group(1))}"
        if target == "tax_return":
            return f"{DOC_LABELS['tax_return']} (for example, your latest year's business tax return)"
        return doc_label(target)
    if kind == "MISSING_PAGE":
        m = _STMT_RE.match(target)
        if m:
            return f"the complete {month_label(m.group(1))} statement: one or more pages are missing from the copy we received"
        return f"the complete {doc_label(target)}: one or more pages are missing from the copy we received"
    if kind == "MISMATCH":
        label = FIELD_LABELS.get(target, target.replace("_", " "))
        e = evidence(state, target)
        if e and e.get("application") is not None and e.get("value") is not None:
            doc = e.get("document") or "supporting document"
            return f"confirmation of your {label}: your application shows {e['application']}, but your {doc} shows {e['value']}"
        return f"confirmation of your {label}: your application and a supporting document do not agree"
    return issue


def info_intro(state: DealState) -> str:
    amount, product = fact_value(state, "amount_requested"), fact_value(state, "product")
    if amount is not None and product:
        return f"Thank you for your application for {amount_text(state)} {product}."
    return "Thank you for your application."


def info_request_message(state: DealState, issues: list[str], rules: Optional[Rules] = None) -> str:
    lines = [f"{info_intro(state)} To keep it moving we need:"]
    lines += [f"- {item_text(i, state)}" for i in issues]
    tail = "Once we have these, your loan moves to the next step."
    nb = needed_by_dt(state)
    if nb:
        tail += f" You told us you need the funds by {fmt_when(nb)}, so please send them as soon as you can."
    lines.append(tail)
    return "\n".join(lines)


def info_followup_message(state: DealState, officer: str) -> str:
    return "\n".join([
        f"{info_intro(state)} To keep it moving we need:",
        f"- the additional information {officer} asked for; your relationship manager will confirm exactly what is needed",
        "Once we have it, your loan moves to the next step.",
    ])


# ------------------------------------------------------------ credit decision


def _tax_text(p: dict[str, Any]) -> str:
    t = p.get("tax_doc")
    if t == "tax_return":
        return "tax return"
    if t == "form_7004":
        return "Form 7004 extension (business under 2 years old)"
    return f"tax document ({NOT_PROVIDED})"


def relationship_text(p: dict[str, Any]) -> str:
    rel = p.get("relationship")
    if not isinstance(rel, dict) or not rel.get("status"):
        return f"Relationship: {NOT_PROVIDED}."
    status = rel["status"]
    since = rel.get("since_year")
    since_s = f" since {since}" if since else ""
    if status == "new":
        return "New borrower."
    if status == "returning_clean":
        return f"Returning customer{since_s}, prior loans repaid."
    if status == "returning_past_due":
        return f"Returning customer{since_s}, with a past-due or charged-off prior loan."
    return f"Relationship: {NOT_PROVIDED}."


def credit_decision_message(state: DealState, rules: Rules, route: Optional[Route] = None) -> str:
    p = profile(state)
    months = p.get("statement_months")
    months_s = f"{months} months of statements" if months else f"bank statements (months {NOT_PROVIDED})"
    deposits = cents_text(p.get("deposits_annualized_cents"))
    stated = fact_value(state, "annual_revenue_stated")
    stated_s = NOT_PROVIDED if stated is None else money_of(stated)
    lines = [
        f"Credit decision needed: {borrower_label(state)}, RM {rm_label(state, rules)}, requests "
        f"{amount_text(state)} {product_text(state)} over {term_text(state)} months for {purpose_text(state)}.",
        f"File is complete: {months_s}, financials, {_tax_text(p)}; the bank's 5 known-fraud checks pass.",
        f"Stated revenue {stated_s} vs. about {deposits} a year in deposits. {relationship_text(p)}",
        "Please reply approve, decline or request info." + needed_clause(state),
    ]
    cover = covering_sentence(route, rules)
    if cover:
        lines.append(cover)
    return "\n".join(lines)


def generic_gate_message(state: DealState, rules: Rules, gate_type: str, route: Optional[Route] = None) -> str:
    from prism.move.settings import get_config

    g = get_config().gates.get(gate_type)
    label = GATE_LABELS.get(gate_type, gate_type.replace("_", " "))
    opts = option_words(g.options) if g else "approve or decline"
    lines = [
        f"{label[:1].upper()}{label[1:]} needed: {borrower_label(state)}, RM {rm_label(state, rules)}, "
        f"{amount_text(state)} {product_text(state)} over {term_text(state)} months.",
        f"Please reply {opts}." + needed_clause(state),
    ]
    cover = covering_sentence(route, rules)
    if cover:
        lines.append(cover)
    return "\n".join(lines)


# ------------------------------------------------------------ later gates


def delegated_sentence(rules: Rules, stage_cfg: dict[str, Any]) -> str:
    r = stage_cfg.get("routing")
    if not isinstance(r, dict):
        return ""
    try:
        limit = to_cents(r["delegated_max_amount"]) + 1
    except (KeyError, ValueError, TypeError):
        return ""
    return f"Under the {fmt_money(limit)} delegated limit."


def committee_approval_message(
    state: DealState, rules: Rules, route: Optional[Route], short_memo: str, delegated: Optional[bool], stage_cfg: dict[str, Any]
) -> str:
    lines = [short_memo]
    if delegated:
        s = delegated_sentence(rules, stage_cfg)
        if s:
            lines.append(s)
    cover = covering_sentence(route, rules)
    if cover:
        lines.append(cover)
    return "\n".join(lines)


def commitment_signoff_message(
    state: DealState, rules: Rules, route: Optional[Route], approver: Optional[str], approved_at: Optional[datetime]
) -> str:
    who = person_name(rules.teams, approver) if approver else NOT_PROVIDED
    when = fmt_date(approved_at) if approved_at else NOT_PROVIDED
    lines = [
        f"Commitment ready: {borrower_label(state)}, {amount_text(state)} {product_text(state)} over {term_text(state)} months, "
        f"approved by {who} on {when}.",
        "Please sign the commitment letter and confirm the borrower has countersigned." + needed_clause(state),
    ]
    cover = covering_sentence(route, rules)
    if cover:
        lines.append(cover)
    return "\n".join(lines)


def pay_to_text(state: DealState) -> str:
    d = profile(state).get("disbursement")
    if not isinstance(d, dict):
        return NOT_PROVIDED
    bank = d.get("bank") or NOT_PROVIDED
    last4 = d.get("last4") or NOT_PROVIDED
    if d.get("kind") == "vendor":
        n = d.get("past_loans")
        past = f" ({n} past loans paid to this account)" if isinstance(n, int) and not isinstance(n, bool) else ""
        return f"verified vendor {d.get('vendor') or NOT_PROVIDED}, {bank} ...{last4}{past}"
    if d.get("kind") == "borrower":
        return f"borrower's own account at {bank} ...{last4}"
    return NOT_PROVIDED


def funding_release_message(
    state: DealState, rules: Rules, route: Optional[Route], t: datetime, committed_at: Optional[datetime]
) -> str:
    committed = fmt_date(committed_at) if committed_at else NOT_PROVIDED
    lines = [
        f"Funding release: {amount_text(state)} to {borrower_label(state)}, RM {rm_label(state, rules)}.",
        f"Pay to: {pay_to_text(state)}.",
        f"Final fraud screen: clear as of {fmt_when(t)}. Commitment signed {committed}.",
        "Please release or hold." + needed_clause(state),
    ]
    cover = covering_sentence(route, rules)
    if cover:
        lines.append(cover)
    return "\n".join(lines)
