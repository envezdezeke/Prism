"""Synthetic validation runner (trick menu v1; MODEL_DESIGN M5, M15, M16, M21).

Builds every synthetic case from ``eval/synth.py``, scores it with the EXISTING fraud code
(``prism.fraud``, not modified) against the real history plus the case's planted history rows,
and applies the hold rule as the engine has it today: F1 mandatory plus at least
``min_additional`` of the BUILT additional families (F2 and F4 are not built, so today that is
F3 and F5). Writes ``out/synth_report.json`` and ``out/synth_report.md``.

Nothing here tunes anything. Real history supplies the baseline and the calibration (tau, F5
reference), exactly as a real run does; synthetic deals never enter calibration. Two runs on the
same menu, history and commit are byte-identical (no clock, no randomness beyond seeded cases).
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import synth  # noqa: E402
from synth import ROOT, Case, Cell  # noqa: E402

from prism.engine.config import load_fraud_config  # noqa: E402
from prism.fraud.baseline import (  # noqa: E402
    HISTORY_COLUMN_KINDS, Baseline, DealProfile, build_baseline, deposit_features,
)
from prism.fraud.canon import canon_value  # noqa: E402
from prism.fraud.rarity import FraudParams  # noqa: E402
from prism.fraud.signals import _fires, score_f1, score_f3, score_f5  # noqa: E402

BUILT = ("F1", "F3", "F5")
HOLD_BAR = 0.70
TWIN_BAR = 0.05


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def profile_of(row: Mapping[str, str], dep_rows: Sequence[Mapping[str, str]]) -> DealProfile:
    entities: dict[str, tuple[str, ...]] = {}
    for col, kind in HISTORY_COLUMN_KINDS.items():
        v = canon_value(kind, row.get(col))
        if v:
            entities[kind] = (v,)
    return DealProfile(row["deal_id"], entities, deposit_features(list(dep_rows)))


def hold_rule(cfg) -> tuple[str, tuple[str, ...], int]:
    required = cfg.hold_required[0]
    extra = tuple(f for f in cfg.hold_additional_from if f in BUILT)
    return required, extra, cfg.hold_min_additional


def evaluate_case(case: Case, hist: synth.History, params: FraudParams, real: Baseline, cfg) -> dict[str, Any]:
    base = Baseline.from_rows(hist.deal_rows + case.planted_rows, hist.deposit_rows, params=params)
    base.calibration = real.calibration
    cal = real.calibration
    _req, extra, min_extra = hold_rule(cfg)

    deps_by: dict[str, list[dict[str, str]]] = {}
    for r in case.deposit_rows:
        deps_by.setdefault(r["deal_id"], []).append(r)
    profiles = {r["deal_id"]: profile_of(r, deps_by.get(r["deal_id"], [])) for r in case.deal_rows}
    dates = {r["deal_id"]: r["application_date"] for r in case.deal_rows}
    order = sorted(profiles, key=lambda i: (dates[i], i))

    other_fired: dict[str, set[str]] = {}
    for i, prof in profiles.items():
        fired: set[str] = set()
        f3 = score_f3(prof, base, params)
        if f3 is not None and _fires(f3.bits, cal.tau.get("F3")):
            fired.add("F3")
        f5 = score_f5(prof, base, params, cal.reference) if prof.deposits is not None else None
        if f5 is not None and _fires(f5.bits, cal.tau.get("F5")):
            fired.add("F5")
        other_fired[i] = fired

    def state_at(k: int, ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        visible = {i: profiles[i] for i in order[:k]}
        out: dict[str, dict[str, Any]] = {}
        for i in ids:
            if i not in visible:
                continue
            f1 = score_f1(profiles[i], base, params, others=visible)
            fired = set(other_fired[i]) | ({"F1"} if f1 is not None else set())
            held = f1 is not None and len(fired & set(extra)) >= min_extra
            outcome = "hold" if held else ("watch" if fired else "clear")
            out[i] = {"outcome": outcome, "fired": sorted(fired)}
        return out

    final = state_at(len(order), list(profiles))
    first_hold: Optional[int] = None
    for k, i in enumerate(order, start=1):
        if i in case.trick_ids and any(v["outcome"] == "hold" for v in state_at(k, case.trick_ids).values()):
            first_hold = k
            break
    return {
        "trick": {i: final[i] for i in case.trick_ids},
        "background": {i: final[i] for i in case.background_ids},
        "first_hold_position": first_hold,
    }


def summarize_cell(cell: Cell, results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {"hold": 0, "watch": 0, "clear": 0}
    fired = {f: 0 for f in BUILT}
    watch_with_f3 = 0
    case_hold = 0
    positions: list[int] = []
    bg_hold = bg_total = 0
    for res in results:
        outs = [v["outcome"] for v in res["trick"].values()]
        for v in res["trick"].values():
            counts[v["outcome"]] += 1
            for f in v["fired"]:
                fired[f] += 1
            if v["outcome"] == "watch" and "F3" in v["fired"]:
                watch_with_f3 += 1
        if "hold" in outs:
            case_hold += 1
        if res["first_hold_position"] is not None:
            positions.append(res["first_hold_position"])
        for v in res["background"].values():
            bg_total += 1
            bg_hold += v["outcome"] == "hold"
    n = sum(counts.values())
    old_rule = "hold_old_rule" in (cell.expected_full, cell.expected_now)
    share = (lambda x: x / n if n else 0.0)
    if old_rule:
        measured = "not_measurable"
    elif share(counts["hold"]) >= 0.5:
        measured = "hold"
    elif share(counts["hold"] + counts["watch"]) >= 0.5:
        measured = "watch"
    else:
        measured = "clear"
    return {
        "cell": cell.id, "family": cell.family, "name": cell.family_name, "kind": cell.kind,
        "strength": cell.strength, "role": cell.role, "n_cases": len(results), "n_deals": n,
        "deals": counts, "hold_rate": share(counts["hold"]), "watch_rate": share(counts["watch"]),
        "case_hold_rate": case_hold / len(results) if results else 0.0,
        "median_first_hold_position": statistics.median(positions) if positions else None,
        "fired_share": {f: share(fired[f]) for f in BUILT},
        "watch_with_f3_share": share(watch_with_f3),
        "background_hold_deals": bg_hold, "background_deals": bg_total,
        "expected_now": cell.expected_now, "expected_full": cell.expected_full,
        "measured_outcome": measured,
        "matches_expected_now": None if measured == "not_measurable" else measured == cell.expected_now,
        "design_outcome": "not_measurable (F2/F4 not built)",
        "blind_spot": cell.blind_spot, "must_not": cell.must_not,
        "old_rule_cell": old_rule,
    }


def pooled(cells: Sequence[Mapping[str, Any]], key: str = "hold") -> dict[str, Any]:
    n = sum(c["n_deals"] for c in cells)
    h = sum(c["deals"][key] for c in cells)
    return {"cells": [c["cell"] for c in cells], "n_deals": n, "count": h, "rate": h / n if n else 0.0}


def build_report(menu: Mapping[str, Any], hist: synth.History, limit: Optional[int]) -> dict[str, Any]:
    cfg = load_fraud_config()
    params = FraudParams.from_config(cfg)
    real = Baseline.from_rows(hist.deal_rows, hist.deposit_rows, params=params)
    from prism.fraud.calibrate import compute_thresholds
    real.calibration = compute_thresholds(real, params)

    summaries = []
    for cell in synth.cells_of(menu):
        results = [evaluate_case(c, hist, params, real, cfg) for c in synth.generate_cases(cell, hist, limit)]
        summaries.append(summarize_cell(cell, results))

    rings = [s for s in summaries if s["kind"] == "ring"]
    twins = [s for s in summaries if s["kind"] == "twin"]
    bar_cells = [s for s in rings if s["expected_full"] == "hold" and not s["blind_spot"]]
    unseen = [s for s in bar_cells if s["role"] != "positive_control_sample_like"]
    control = [s for s in bar_cells if s["role"] == "positive_control_sample_like"]
    blind = [s for s in rings if s["blind_spot"]]
    old_rule = [s for s in rings if s["old_rule_cell"]]
    twin_all = pooled(twins)
    twin_watch = pooled(twins, "watch")
    ring_bar = pooled(bar_cells)
    return {
        "stamp": {
            "menu_version": menu["version"], "menu_status": menu["status"], "seed": menu["seed"],
            "menu_commit": _git("log", "-1", "--format=%H", "--", "eval/trick_menu.yaml"),
            "engine_commit": _git("rev-parse", "HEAD"),
            "history_rows_count": len(hist.deal_rows),
            "computed_thresholds": {
                "tau": real.calibration.tau,
                "n_clean": real.calibration.n_clean,
                "clean_round_share_anchors": {
                    str(q): hist.anchor(q) for q in (0.5, 0.9, 0.97, 0.995)
                },
            },
            "cases_per_cell_limit": limit,
        },
        "rule": {
            "today": {"required": "F1", "additional_from_built": list(hold_rule(cfg)[1]),
                      "min_additional": hold_rule(cfg)[2]},
            "design_outcomes_measurable": False,
            "design_note": "F2 and F4 are not built; expected_full is reported but not measured.",
        },
        "cells": summaries,
        "bars": {
            "catch_bar": {
                "target": HOLD_BAR, "scope": "ring cells with expected full = hold, blind spots excluded; "
                "measured under today's rule (F1 + 2 of F3/F5)",
                "pooled": ring_bar, "unseen_t2_t8": pooled(unseen), "control_t1": pooled(control),
                "pass_today": ring_bar["rate"] >= HOLD_BAR,
                "design_bar": "not_measurable (F2/F4 not built)",
            },
            "twin_bar": {
                "target": TWIN_BAR, "scope": "all benign twins, holds only",
                "pooled_hold": twin_all, "pooled_watch_friction": twin_watch,
                "pass": twin_all["rate"] <= TWIN_BAR,
                "twins_over_bar": [t["cell"] for t in twins if t["hold_rate"] > TWIN_BAR],
            },
            "blind_spot_cells": [
                {"cell": s["cell"], "hold_rate": s["hold_rate"], "watch_rate": s["watch_rate"],
                 "reason": s["blind_spot"]} for s in blind],
            "not_measurable": {
                "old_rule_cells": [s["cell"] for s in old_rule],
                "old_rule_note": "the bank's known-checks path (hold_old_rule) lives outside prism.fraud signals",
                "history_flags_recall": "decide() and history_flags are not built; planted-row recall not measurable",
                "f6": "terms-shape evidence (amount just under limit) is not built and never votes",
            },
        },
    }


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _round(o: Any) -> Any:
    if isinstance(o, float):
        return round(o, 4)
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_round(v) for v in o]
    return o


def render_markdown(r: Mapping[str, Any]) -> str:
    st, bars = r["stamp"], r["bars"]
    cb, tb = bars["catch_bar"], bars["twin_bar"]
    L = [
        "# Synthetic validation report (trick menu v%s)" % st["menu_version"], "",
        f"- Menu status: {st['menu_status']}; menu commit `{st['menu_commit']}`; engine commit `{st['engine_commit']}`.",
        f"- History rows (baseline only, never edited): {st['history_rows_count']}; clean calibration deals: "
        f"{st['computed_thresholds']['n_clean']}.",
        f"- Rule measured: today's engine, F1 required plus {r['rule']['today']['min_additional']} of "
        f"{', '.join(r['rule']['today']['additional_from_built'])}. F2 and F4 are not built, so design "
        "outcomes are reported but not measurable.", "",
        "## Headline", "",
        "| Bar | Target | Measured today | Result |", "|---|---|---|---|",
        f"| Ring deals held (cells that should hold, blind spots excluded) | >= {_pct(cb['target'])} | "
        f"{_pct(cb['pooled']['rate'])} ({cb['pooled']['count']} of {cb['pooled']['n_deals']}) | "
        f"{'PASS' if cb['pass_today'] else 'FAIL'} (design rule: not measurable) |",
        f"| Unseen tricks T2-T8 only | >= {_pct(cb['target'])} | {_pct(cb['unseen_t2_t8']['rate'])} | n/a |",
        f"| Control T1 | | {_pct(cb['control_t1']['rate'])} | n/a |",
        f"| Benign twins held (false flags) | <= {_pct(tb['target'])} | "
        f"{_pct(tb['pooled_hold']['rate'])} ({tb['pooled_hold']['count']} of {tb['pooled_hold']['n_deals']}) | "
        f"{'PASS' if tb['pass'] else 'FAIL'} |",
        f"| Benign twins on watch (friction, not a flag) | reported | {_pct(tb['pooled_watch_friction']['rate'])} | n/a |",
        "",
    ]
    if tb["twins_over_bar"]:
        L += ["Twins over the 5% bar: " + ", ".join(tb["twins_over_bar"]), ""]
    L += ["## Catch rate by family and strength", "",
          "| Cell | Cases | Deals held | Watch | Case held | Median first hold | Expected (today / design) | Measured | Blind spot |",
          "|---|---|---|---|---|---|---|---|---|"]
    for c in r["cells"]:
        if c["kind"] != "ring":
            continue
        pos = c["median_first_hold_position"]
        L.append(
            f"| {c['cell']} | {c['n_cases']} | {_pct(c['hold_rate'])} | {_pct(c['watch_rate'])} | "
            f"{_pct(c['case_hold_rate'])} | {pos if pos is not None else '-'} | "
            f"{c['expected_now']} / {c['expected_full']} | {c['measured_outcome']} | "
            f"{'yes' if c['blind_spot'] else ''} |")
    L += ["", "## Benign twins", "",
          "| Twin | Cases | Held (false flag) | Watch (friction) | Watch with F3 | Expected | Measured | Must not |",
          "|---|---|---|---|---|---|---|---|"]
    for c in r["cells"]:
        if c["kind"] != "twin":
            continue
        L.append(
            f"| {c['cell']} {c['name']} | {c['n_cases']} | {_pct(c['hold_rate'])} | {_pct(c['watch_rate'])} | "
            f"{_pct(c['watch_with_f3_share'])} | {c['expected_now']} | {c['measured_outcome']} | {c['must_not'] or ''} |")
    L += ["", "## Blind-spot cells (reported, outside the 70% bar)", ""]
    for b in bars["blind_spot_cells"]:
        why = " ".join(str(b["reason"]).split())
        L.append(f"- {b['cell']}: held {_pct(b['hold_rate'])}, watch {_pct(b['watch_rate'])}. {why}")
    nm = bars["not_measurable"]
    L += ["", "## Not measurable with today's fraud code", "",
          f"- Old-rule cells {', '.join(nm['old_rule_cells'])}: {nm['old_rule_note']}.",
          f"- History flags: {nm['history_flags_recall']}.", f"- F6: {nm['f6']}.",
          "- Design (full-rule) outcomes need F2 and F4; expected_full is shown, not measured.", ""]
    return "\n".join(L)


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=str(ROOT / "out"))
    ap.add_argument("--menu", default=str(synth.MENU_PATH))
    ap.add_argument("--max-cases", type=int, default=None, help="cap cases per cell (smoke runs)")
    args = ap.parse_args(argv)
    hist = synth.load_history(synth.history_dir_from_env())
    if hist is None:
        print(f"run_synth: real history not found at {synth.history_dir_from_env()} "
              "(set PRISM_HISTORY_DIR); skipping synthetic validation")
        return 0
    report = _round(build_report(synth.load_menu(Path(args.menu)), hist, args.max_cases))
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "synth_report.json", json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    _write(out / "synth_report.md", render_markdown(report))
    print(f"wrote {out / 'synth_report.json'} and {out / 'synth_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
