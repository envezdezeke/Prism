"""Validate a filled eval/gold_drop.json against the label schema. No engine calls.

Usage: .venv/bin/python eval/drop_labelling/check_labels.py eval/gold_drop.json [--allow-example]
Exit 0 = clean, 1 = problems (listed), 2 = file unreadable.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

STAGES = ["Intake", "Credit", "Committee", "Product", "Committed", "Closed"]
PURPOSES = {"working_capital", "equipment", "inventory", "payroll", "expansion", "refinance"}
PRODUCTS = {"Term Loan", "Equipment Loan", "Revolving Line of Credit", "Working Capital Loan"}
STATUSES = {"todo", "draft", "done"}
GATES = ["credit_decision", "committee_approval", "commitment_signoff", "funding_release"]
FACTS = ["legal_name", "ein", "amount_requested", "purpose_category", "product", "term_months",
         "guarantor_name", "annual_revenue_stated", "needed_by"]
# Same grammar as prism/contract.py ISSUE_RE (copied so this script stays standalone).
ISSUE_RE = re.compile(
    r"^(MISSING_DOC|MISSING_PAGE):(application|guarantor_id|certificate_of_formation"
    r"|ein_letter|bank_statement_\d{4}-\d{2}|financial_statements|tax_return|equipment_quote)$"
    r"|^MISMATCH:(legal_name|ein|amount_requested|guarantor_name|guarantor_dob"
    r"|guarantor_address|annual_revenue|bank_balance)$"
    r"|^OLD_TRICK:(STMT_TAMPER|REV_INFLATION|ID_MISMATCH|DUP_EIN|SHELL_ADDRESS)$",
    re.ASCII,
)
EIN_RE = re.compile(r"^\d{2}-\d{7}$")
HIST_RE = re.compile(r"^H-[\w-]+$")
STMT_MONTH_RE = re.compile(r"bank_statement_(\d{4})-(\d{2})$")


def _time_ok(s) -> bool:
    if not isinstance(s, str) or "T" not in s or not s.endswith("-06:00"):
        return False
    try:
        return datetime.fromisoformat(s).tzinfo is not None
    except ValueError:
        return False


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_deal(name: str, d: dict, hist_must_not: set, errs: list) -> None:
    def e(msg):
        errs.append(f"{name}: {msg}")

    if not isinstance(d, dict):
        return e("entry must be an object")
    if d.get("status") not in STATUSES:
        e(f"status must be one of {sorted(STATUSES)}, got {d.get('status')!r}")
    x = d.get("extracted")
    if not isinstance(x, dict):
        e("extracted missing")
        x = {}
    else:
        for k in FACTS:
            if k not in x:
                e(f"extracted.{k} missing (use null if unreadable)")
        for k in x:
            if k not in FACTS:
                e(f"extracted.{k} is not one of the 9 facts")
        if x.get("ein") is not None and not (isinstance(x["ein"], str) and EIN_RE.match(x["ein"])):
            e(f"ein must look like 12-3456789, got {x['ein']!r}")
        for k in ("amount_requested", "annual_revenue_stated", "term_months"):
            if x.get(k) is not None and not _num(x[k]):
                e(f"{k} must be a plain number, got {x[k]!r}")
        if x.get("purpose_category") is not None and x["purpose_category"] not in PURPOSES:
            e(f"purpose_category {x['purpose_category']!r} not in {sorted(PURPOSES)}")
        if x.get("product") is not None and x["product"] not in PRODUCTS:
            e(f"product {x['product']!r} not in {sorted(PRODUCTS)}")
        if x.get("needed_by") is not None and not _time_ok(x["needed_by"]):
            e(f"needed_by must be like 2026-11-06T15:00-06:00 or null, got {x['needed_by']!r}")
    acc = d.get("extracted_accept", {})
    if not isinstance(acc, dict) or any(k not in FACTS or not isinstance(v, list) for k, v in acc.items()):
        e("extracted_accept must be {fact: [alternatives]}")
    for key in ("issues", "issues_optional"):
        v = d.get(key)
        if not isinstance(v, list):
            e(f"{key} must be a list")
            continue
        for i in v:
            if not isinstance(i, str) or not ISSUE_RE.fullmatch(i):
                e(f"bad issue code in {key}: {i!r}")
        if len(set(v)) != len(v):
            e(f"duplicate issue in {key}")
    if isinstance(d.get("issues"), list) and isinstance(d.get("issues_optional"), list):
        both = set(d["issues"]) & set(d["issues_optional"])
        if both:
            e(f"issue in both issues and issues_optional: {sorted(both)}")
    r = d.get("routing")
    if not isinstance(r, dict) or set(r) != set(GATES):
        e(f"routing must have exactly the keys {GATES}")
    elif any(v is not None and not (isinstance(v, str) and v) for v in r.values()):
        e("routing values must be a teams.json id string or null")
    fs = d.get("final_stage")
    if fs not in STAGES:
        e(f"final_stage {fs!r} not in {STAGES}")
    f = d.get("fraud")
    if not isinstance(f, dict):
        return e("fraud missing")
    for k in ("flagged", "held"):
        if not isinstance(f.get(k), bool):
            e(f"fraud.{k} must be true or false")
    if f.get("flagged") != f.get("held"):
        e("fraud.flagged and fraud.held must agree (J5/J17: a flag is a hold)")
    lo = f.get("latest_ok_stage")
    if f.get("flagged") is True and lo not in STAGES:
        e(f"flagged deal needs latest_ok_stage from {STAGES}")
    if f.get("flagged") is False and lo is not None:
        e("latest_ok_stage must be null when not flagged")
    if lo == "Closed":
        e("latest_ok_stage 'Closed' is too late: a hold must land before Closed")
    ld = f.get("linked_deals")
    if not isinstance(ld, list) or not all(isinstance(s, str) and s for s in ld):
        e("fraud.linked_deals must be a list of folder names / H- ids")
    else:
        if name in ld:
            e("linked_deals contains the deal itself")
        for s in ld:
            if s.startswith("H-") and s in hist_must_not:
                e(f"links to {s}, which is in history_must_not_flag")
        if ld and f.get("flagged") is False:
            e("links but not flagged: one link is a watch, not a link list; a clear/watch deal keeps linked_deals []")
    if isinstance(d.get("issues"), list) and any(i.startswith("OLD_TRICK:") for i in d["issues"]) \
            and f.get("flagged") is not True:
        e("an OLD_TRICK issue means flagged+held (J17)")
    # a deal that is held/blocked should not have signers it never reaches: soft check
    if isinstance(r, dict) and fs in STAGES and f.get("flagged") is True and fs != "Intake":
        pass  # a hold may come late; do not over-constrain


def check(gold, allow_example: bool = False) -> list:
    errs: list = []
    if not isinstance(gold, dict):
        return ["top level must be an object"]
    deals = gold.get("deals")
    if not isinstance(deals, dict) or not deals:
        errs.append("deals must be a non-empty object")
        deals = {}
    hf, hn = gold.get("history_flags"), gold.get("history_must_not_flag")
    for k, v in (("history_flags", hf), ("history_must_not_flag", hn)):
        if not isinstance(v, list) or not all(isinstance(s, str) and HIST_RE.match(s) for s in v):
            errs.append(f"{k} must be a list of H-... ids")
    hn_set = set(hn) if isinstance(hn, list) else set()
    if isinstance(hf, list) and hn_set & set(hf):
        errs.append(f"in both history_flags and history_must_not_flag: {sorted(hn_set & set(hf))}")
    for name, d in deals.items():
        if not allow_example and name.startswith("X-"):
            errs.append(f"{name}: placeholder example entry still present; delete it")
        check_deal(name, d, hn_set, errs)
        if isinstance(d, dict) and isinstance(d.get("fraud"), dict) and d["fraud"].get("flagged") is True \
                and isinstance(hf, list) and isinstance(d["fraud"].get("linked_deals"), list):
            pass
    names = set(deals)
    for name, d in deals.items():
        ld = (d.get("fraud") or {}).get("linked_deals") if isinstance(d, dict) else None
        if isinstance(ld, list):
            for s in ld:
                if isinstance(s, str) and not s.startswith("H-") and s not in names:
                    errs.append(f"{name}: linked deal {s!r} has no entry of its own (every linked current deal needs a label)")
    return errs


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    allow = "--allow-example" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if len(paths) != 1:
        print(__doc__)
        return 2
    try:
        gold = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        print(f"cannot read {paths[0]}: {ex}")
        return 2
    errs = check(gold, allow_example=allow)
    for m in errs:
        print("PROBLEM:", m)
    n = len(gold.get("deals", {})) if isinstance(gold, dict) and isinstance(gold.get("deals"), dict) else 0
    print(f"{n} deals checked, {len(errs)} problems")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
