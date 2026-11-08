"""STMT_TAMPER, REV_INFLATION, MISSING_PAGE through detect_issues (READ-06, READ-08), and the other OLD_TRICKs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from prism.engine.config import Rules
from prism.engine.state import DealState, Doc
from prism.read import docmodel, old_tricks
from prism.read import issues as read_issues
from prism.read import text as read_text
from prism.read.classify import classify
from prism.read.docmodel import Guarantor, ParsedApplication, ParsedTax
from tests.statement_fixtures import DEFAULT_TXNS, closing_of, write_statement, write_statement_csv

TZ = timezone(timedelta(hours=-6))
BASE = datetime(2026, 11, 2, 9, 0, tzinfo=TZ)
MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
RULES = Rules()
MONTHLY_CREDITS = sum(c for _d, _s, c in DEFAULT_TXNS if c > 0)          # 1_233_575
ANNUALIZED = MONTHLY_CREDITS * 12                                          # six months, doubled
LIMIT = ANNUALIZED * 3 // 2                                                # exactly 1.5 times


@pytest.fixture
def fake_app(monkeypatch):
    """Replace the application parser so a test chooses revenue and dates; files are one byte."""
    docmodel._load_modules()
    table: dict[str, object] = {}
    monkeypatch.setitem(docmodel._PARSERS, "application", lambda dt, doc: table.get(doc.path))
    monkeypatch.setitem(docmodel._PARSERS, "tax_return", lambda dt, doc: table.get(doc.path))
    return table


def sub(tmp_path: Path, name: str) -> Path:
    p = tmp_path / name
    p.mkdir()
    return p


def build(tmp_path: Path, *, months=MONTHS, openings=None, table=None, revenue=None,
          app_over=None, kinds=None, tax=None, txns=DEFAULT_TXNS) -> DealState:
    """A deal with generated PDF statements (chained openings unless ``openings`` overrides a month)."""
    read_text.clear_cache()
    docmodel.clear_cache()
    docs: list[Doc] = []
    opening = 1_000_000
    for i, m in enumerate(months):
        if openings and m in openings:
            opening = openings[m]
        name = f"s_{m}.pdf"
        kw = (kinds or {}).get(m, {})
        closing = write_statement(tmp_path, name, m, txns, opening=opening, **kw)
        doc = Doc(path=f"Deal/{name}", name=name, arrive_at=BASE + timedelta(minutes=i), abs_path=tmp_path / name)
        classify(doc)
        docs.append(doc)
        opening = closing
    if table is not None:
        p = tmp_path / "app.dat"
        p.write_bytes(b"x")
        a = Doc(path="Deal/app.dat", name="app.dat", arrive_at=BASE, abs_path=p, doc_class="application")
        fields = dict(signature_date="2026-11-02", signed=True, revenue_cents=revenue,
                      guarantors=(Guarantor(name="A One"),), formation_date="2010-01-01")
        fields.update(app_over or {})
        table[a.path] = ParsedApplication(**fields)
        docs.append(a)
        if tax is not None:
            t = tmp_path / "tax.dat"
            t.write_bytes(b"x")
            td = Doc(path="Deal/tax.dat", name="tax.dat", arrive_at=BASE, abs_path=t, doc_class="tax_return")
            table[td.path] = tax
            docs.append(td)
    st = DealState(folder="Deal", docs=sorted(docs, key=lambda d: (d.arrive_at, d.path)))
    st.last_arrival_at = max(d.arrive_at for d in docs)
    return st


def issues_of(st: DealState, prefix: str = "") -> list[str]:
    got = read_issues.detect_issues(st, RULES, st.last_arrival_at + timedelta(minutes=45))
    # these deals carry only an application and statements, so MISSING_DOC for the rest is noise here
    return [i for i in got if i.startswith(prefix) and not i.startswith("MISSING_DOC")]


# ---------------------------------------------------------------- STMT_TAMPER

def test_clean_chained_statements_raise_nothing(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=LIMIT)
    assert old_tricks.stmt_tamper_reasons(st) == []
    assert issues_of(st) == []


def test_stated_closing_off_by_one_cent_is_tamper(tmp_path, fake_app):
    real = closing_of(1_000_000, DEFAULT_TXNS)
    st = build(tmp_path, table=fake_app, revenue=LIMIT, kinds={"2026-05": {"printed_closing": real + 1}})
    assert "2026-05:summary_closing" in old_tricks.stmt_tamper_reasons(st)
    assert issues_of(st, "OLD_TRICK") == ["OLD_TRICK:STMT_TAMPER"]


def test_an_edited_amount_that_breaks_the_printed_totals_is_tamper(tmp_path, fake_app):
    credits = sum(c for _d, _s, c in DEFAULT_TXNS if c > 0)
    st = build(tmp_path, table=fake_app, revenue=LIMIT, kinds={"2026-07": {"printed_credits": credits + 100}})
    assert "2026-07:credits_sum" in old_tricks.stmt_tamper_reasons(st)


def test_several_failed_checks_give_exactly_one_issue(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=LIMIT,
               kinds={"2026-05": {"printed_closing": 5}, "2026-06": {"printed_debits": 1}},
               openings={"2026-08": 123})
    assert len(old_tricks.stmt_tamper_reasons(st)) >= 3
    assert issues_of(st, "OLD_TRICK:STMT") == ["OLD_TRICK:STMT_TAMPER"]


def test_opening_must_equal_prior_closing_between_consecutive_months(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=LIMIT, openings={"2026-08": 999_999})
    assert old_tricks.stmt_tamper_reasons(st) == ["2026-08:chain"]


def test_a_gap_month_is_not_a_chain_break(tmp_path, fake_app):
    st = build(tmp_path, months=["2026-05", "2026-06", "2026-08", "2026-09", "2026-10"], table=fake_app,
               revenue=LIMIT, openings={"2026-08": 4_242})
    assert old_tricks.stmt_tamper_reasons(st) == []


def test_a_statement_with_a_missing_page_is_excluded_from_footing_and_chain(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=LIMIT,
               kinds={"2026-08": {"markers": [(1, 2)], "printed_closing": 5, "printed_credits": 7}})
    assert old_tricks.stmt_tamper_reasons(st) == []
    got = issues_of(st)
    assert "MISSING_PAGE:bank_statement_2026-08" in got and "OLD_TRICK:STMT_TAMPER" not in got


def test_a_complete_second_copy_clears_the_page_gap(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=LIMIT, kinds={"2026-08": {"markers": [(1, 2)]}})
    assert "MISSING_PAGE:bank_statement_2026-08" in issues_of(st)
    open_08 = 1_000_000
    for _ in range(3):  # May, June and July close where the next month opens
        open_08 = closing_of(open_08, DEFAULT_TXNS)
    name = "s_2026-08_again.pdf"
    write_statement(tmp_path, name, "2026-08", DEFAULT_TXNS, opening=open_08)
    read_text.clear_cache()
    docmodel.clear_cache()
    doc = Doc(path=f"Deal/{name}", name=name, arrive_at=BASE + timedelta(hours=1), abs_path=tmp_path / name)
    classify(doc)
    st.docs.append(doc)
    st.last_arrival_at = doc.arrive_at
    assert [i for i in issues_of(st) if i.startswith("MISSING_PAGE")] == []


def test_csv_months_foot_and_a_missing_csv_month_is_no_tamper(tmp_path, fake_app):
    docs = []
    opening = 500_000
    for m in ["2026-05", "2026-07", "2026-08", "2026-09", "2026-10"]:
        opening = write_statement_csv(tmp_path, f"e_{m}.csv", m, opening=opening)
        d = Doc(path=f"Deal/e_{m}.csv", name=f"e_{m}.csv", arrive_at=BASE, abs_path=tmp_path / f"e_{m}.csv")
        classify(d)
        docs.append(d)
    st = DealState(folder="Deal", docs=docs)
    st.last_arrival_at = BASE
    assert old_tricks.stmt_tamper_reasons(st) == []
    assert not old_tricks.rev_inflation(st)


def test_csv_running_balance_break_is_tamper(tmp_path, fake_app):
    write_statement_csv(tmp_path, "e.csv", "2026-05", bad_balance_at=3)
    d = Doc(path="Deal/e.csv", name="e.csv", arrive_at=BASE, abs_path=tmp_path / "e.csv")
    classify(d)
    st = DealState(folder="Deal", docs=[d])
    st.last_arrival_at = BASE
    assert old_tricks.stmt_tamper_reasons(st) == ["2026-05:running_balance"]


def test_unreadable_or_unparsed_statements_never_raise_tamper(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=LIMIT)
    for d in st.docs:
        if d.doc_class == "bank_statement":
            d.abs_path.write_bytes(b"\x00" * 9)
    docmodel.clear_cache()
    read_text.clear_cache()
    assert old_tricks.stmt_tamper_reasons(st) == []


# ---------------------------------------------------------------- REV_INFLATION

def test_exactly_one_and_a_half_times_does_not_raise_and_one_cent_over_does(tmp_path, fake_app):
    at_limit = build(sub(tmp_path, "a"), table=fake_app, revenue=LIMIT)
    assert old_tricks.rev_inflation_numbers(at_limit) == (LIMIT, ANNUALIZED)
    assert not old_tricks.rev_inflation(at_limit) and issues_of(at_limit) == []
    over = build(sub(tmp_path, "b"), table=fake_app, revenue=LIMIT + 1)
    assert old_tricks.rev_inflation(over)
    assert issues_of(over, "OLD_TRICK") == ["OLD_TRICK:REV_INFLATION"]


def test_a_range_uses_its_midpoint(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=None,
               app_over={"revenue_range_cents": (LIMIT, LIMIT + 4)})
    assert old_tricks.rev_inflation_numbers(st) == (LIMIT + 2, ANNUALIZED)
    assert old_tricks.rev_inflation(st)


def test_a_missing_month_or_missing_revenue_raises_nothing(tmp_path, fake_app):
    five = build(tmp_path, months=MONTHS[:5], table=fake_app, revenue=10 ** 12)
    assert not old_tricks.rev_inflation(five)
    none = build(sub(tmp_path, "n"), table=fake_app, revenue=None)
    assert not old_tricks.rev_inflation(none)


def test_an_incomplete_month_blocks_the_check(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=10 ** 12, kinds={"2026-06": {"markers": [(1, 2)]}})
    assert not old_tricks.rev_inflation(st)


def test_tax_gross_receipts_count_only_for_a_full_tax_year(tmp_path, fake_app):
    big = 10 ** 12
    full = build(tmp_path, table=fake_app, revenue=LIMIT, tax=ParsedTax(gross_receipts_cents=big, tax_year=2025))
    assert old_tricks.rev_inflation(full)
    young = build(sub(tmp_path, "y"), table=fake_app, revenue=LIMIT,
                  app_over={"formation_date": "2025-06-01"}, tax=ParsedTax(gross_receipts_cents=big, tax_year=2025))
    assert not old_tricks.rev_inflation(young)


# ---------------------------------------------------------------- MISSING_PAGE for other classes

def test_missing_page_for_other_document_classes_uses_the_class_name(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=LIMIT)
    app = next(d for d in st.docs if d.doc_class == "application")
    app.meta["page_markers"] = [[1, 3], [3, 3]]
    assert "MISSING_PAGE:application" in issues_of(st)
    app.meta["page_markers"] = [[1, 3], [2, 3], [3, 3]]
    assert "MISSING_PAGE:application" not in issues_of(st)
    app.meta["page_markers"] = []
    assert "MISSING_PAGE:application" not in issues_of(st)


def test_missing_page_is_quiet_gated_like_missing_doc(tmp_path, fake_app):
    st = build(tmp_path, table=fake_app, revenue=LIMIT, kinds={"2026-08": {"markers": [(1, 2)]}})
    label = "MISSING_PAGE:bank_statement_2026-08"
    assert label not in read_issues.detect_issues(st, RULES, st.last_arrival_at + timedelta(minutes=29))
    assert label in read_issues.detect_issues(st, RULES, st.last_arrival_at + timedelta(minutes=30))
