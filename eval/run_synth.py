"""Synthetic validation runner (trick menu v1; MODEL_DESIGN M5, M15, M16, M21).

Builds every synthetic case from ``eval/synth.py`` and measures the fraud pipeline on it WITHOUT
Read: each deal is injected at the extracted-features / entity layer (``DealState.entities`` and
``DealState.features["deposit_months"]``), exactly what ``prism.read`` will produce.

Two measurements, both reported side by side:

* ``engine``: the real call. Cases are replayed arrival by arrival through
  ``prism.fraud.decide.evaluate(states, baseline, cfg, now)``; holds are sticky as in
  ``prism/engine/run.py``. While ``decide()`` is a stub this shows ~0% held. This is the number to
  watch as ``decide.py`` gets built; nothing here needs changing when it lands.
* ``proxy``: a reference measurement that applies the documented hold rule (F1 required plus
  ``hold_min_additional`` of the BUILT families F3, F5) directly to the real signal functions.
  It shows what ``decide()`` should reach, and keeps the harness useful today.

Nothing here tunes anything. Real history supplies the baseline and calibration (as in a real
run); synthetic deals never enter calibration. Two runs on the same menu, history and commit are
byte-identical (no clock, no randomness beyond seeded cases).

Usage: ``PYTHONUTF8=1 .venv/bin/python eval/run_synth.py [--menus core,redteam] [--mode both]
[--max-cases N] [--history-dir DIR] [--out-dir out]``
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import synth  # noqa: E402
from synth import ROOT, Case, Cell  # noqa: E402

from prism.engine.config import load_fraud_config  # noqa: E402
from prism.engine.state import PIPELINE, DealState, EntityRef  # noqa: E402
from prism.fraud import decide as fraud_decide  # noqa: E402
from prism.fraud.baseline import (  # noqa: E402
    HISTORY_COLUMN_KINDS, Baseline, DealProfile, deposit_features,
)
from prism.fraud.calibrate import compute_thresholds  # noqa: E402
from prism.fraud.canon import canon_value  # noqa: E402
from prism.fraud.rarity import FraudParams  # noqa: E402
from prism.fraud.signals import _fires, score_f1, score_f3, score_f5  # noqa: E402

BUILT = ("F1", "F3", "F5")
HOLD_BAR = 0.70
TWIN_BAR = 0.05
MODES = ("engine", "proxy")
CT = timezone(timedelta(hours=-6))  # sim time is America/Chicago (-06:00)
SCHEMA_VERSION = 2


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


# ------------------------------------------------------------------ baselines

def shift_dates(rows: Sequence[Mapping[str, str]], days: int) -> list[dict[str, str]]:
    out = []
    for r in rows:
        r = dict(r)
        if days and r.get("application_date"):
            r["application_date"] = (date.fromisoformat(r["application_date"][:10]) + timedelta(days=days)).isoformat()
        out.append(r)
    return out


class BaselineCache:
    """The real baseline (history only, calibrated) per history date shift."""

    def __init__(self, hist: synth.History, params: FraudParams) -> None:
        self.hist, self.params = hist, params
        self._real: dict[int, Baseline] = {}

    def real(self, shift: int = 0) -> Baseline:
        if shift not in self._real:
            b = Baseline.from_rows(shift_dates(self.hist.deal_rows, shift), self.hist.deposit_rows,
                                   params=self.params)
            b.calibration = compute_thresholds(b, self.params)
            self._real[shift] = b
        return self._real[shift]

    def for_case(self, case: Case, shift: int = 0) -> Baseline:
        """History plus the case's planted rows, calibrated on the history alone (as a real run)."""
        base = Baseline.from_rows(
            shift_dates(self.hist.deal_rows, shift) + shift_dates(case.planted_rows, shift),
            self.hist.deposit_rows, params=self.params)
        base.calibration = self.real(shift).calibration
        return base


# ------------------------------------------------------------------ injection at the feature layer

def state_of(row: Mapping[str, str], dep_rows: Sequence[Mapping[str, str]]) -> DealState:
    """A DealState as prism.read will leave it: raw entity values and monthly deposit rows."""
    st = DealState(folder=row["deal_id"])
    st.entities = [
        EntityRef(kind, str(row[col]), f"{row['deal_id']}/synthetic")
        for col, kind in HISTORY_COLUMN_KINDS.items() if (row.get(col) or "").strip()
    ]
    if dep_rows:
        st.features["deposit_months"] = [dict(d) for d in dep_rows]
    return st


def profile_of(row: Mapping[str, str], dep_rows: Sequence[Mapping[str, str]]) -> DealProfile:
    entities: dict[str, tuple[str, ...]] = {}
    for col, kind in HISTORY_COLUMN_KINDS.items():
        v = canon_value(kind, row.get(col))
        if v:
            entities[kind] = (v,)
    return DealProfile(row["deal_id"], entities, deposit_features(list(dep_rows)))


def arrival_order(case: Case) -> list[str]:
    dates = {r["deal_id"]: r["application_date"] for r in case.deal_rows}
    return sorted(dates, key=lambda i: (dates[i], i))


def sim_time(day: str, k: int) -> datetime:
    """Arrival k (1-based) of a case: noon on its application day plus k minutes, -06:00."""
    return datetime.combine(date.fromisoformat(day[:10]), datetime.min.time(), tzinfo=CT) + timedelta(hours=12, minutes=k)


def _outcome_label(held: bool, watch: bool) -> str:
    return "hold" if held else ("watch" if watch else "clear")


def _deps_by_deal(case: Case) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for r in case.deposit_rows:
        out.setdefault(r["deal_id"], []).append(r)
    return out


def evaluate_case_engine(case: Case, base: Baseline, cfg) -> dict[str, Any]:
    """Replay the case through ``decide.evaluate`` one arrival at a time (sticky holds)."""
    deps_by = _deps_by_deal(case)
    rows = {r["deal_id"]: r for r in case.deal_rows}
    states = {i: state_of(rows[i], deps_by.get(i, [])) for i in rows}
    order = arrival_order(case)
    held: dict[str, str] = {}   # deal -> stage at first hold
    first_hold: Optional[int] = None
    watch: set[str] = set()
    for k, name in enumerate(order, start=1):
        visible = {}
        for j, other in enumerate(order[:k]):
            states[other].stage = PIPELINE[min(k - 1 - j, len(PIPELINE) - 1)]  # synthetic stage clock
            visible[other] = states[other]
        now = sim_time(rows[name]["application_date"], k)
        try:
            outcome = fraud_decide.evaluate(visible, base, cfg, now)
        except NotImplementedError:
            continue
        for d, fr in outcome.per_deal.items():
            if d in visible and (fr.held or fr.flagged) and d not in held:
                held[d] = fr.stage_at_flag or visible[d].stage
        for c in outcome.clusters:
            if c.tier == "watch":
                watch.update(d for d in c.deals if d in visible)
        if first_hold is None and any(t in held for t in case.trick_ids):
            first_hold = k

    def res(i: str) -> dict[str, Any]:
        return {"outcome": _outcome_label(i in held, i in watch), "fired": [], "stage": held.get(i)}

    return {"trick": {i: res(i) for i in case.trick_ids},
            "background": {i: res(i) for i in case.background_ids},
            "first_hold_position": first_hold}


def hold_rule(cfg) -> tuple[str, tuple[str, ...], int]:
    return cfg.hold_required[0], tuple(f for f in cfg.hold_additional_from if f in BUILT), cfg.hold_min_additional


def evaluate_case_proxy(case: Case, base: Baseline, params: FraudParams, cfg) -> dict[str, Any]:
    """Documented hold rule on the real signal functions (reference, not the engine)."""
    cal = base.calibration
    _req, extra, min_extra = hold_rule(cfg)
    deps_by = _deps_by_deal(case)
    profiles = {r["deal_id"]: profile_of(r, deps_by.get(r["deal_id"], [])) for r in case.deal_rows}
    order = arrival_order(case)
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
            is_held = f1 is not None and len(fired & set(extra)) >= min_extra
            out[i] = {"outcome": _outcome_label(is_held, bool(fired)), "fired": sorted(fired), "stage": None}
        return out

    final = state_at(len(order), list(profiles))
    first_hold: Optional[int] = None
    for k, i in enumerate(order, start=1):
        if i in case.trick_ids and any(v["outcome"] == "hold" for v in state_at(k, case.trick_ids).values()):
            first_hold = k
            break
    if first_hold is not None:  # stage of each held deal when the first hold fires (synthetic stage clock)
        for j, other in enumerate(order[:first_hold]):
            if final[other]["outcome"] == "hold":
                final[other]["stage"] = PIPELINE[min(first_hold - 1 - j, len(PIPELINE) - 1)]
        for i, v in final.items():
            if v["outcome"] == "hold" and v["stage"] is None:
                v["stage"] = PIPELINE[min(len(order) - 1 - order.index(i), len(PIPELINE) - 1)]
    return {"trick": {i: final[i] for i in case.trick_ids},
            "background": {i: final[i] for i in case.background_ids},
            "first_hold_position": first_hold}


# ------------------------------------------------------------------ summaries

def summarize_cell(cell: Cell, results: Sequence[Mapping[str, Any]], expect_key: str) -> dict[str, Any]:
    counts = {"hold": 0, "watch": 0, "clear": 0}
    fired = {f: 0 for f in BUILT}
    watch_with_f3 = case_hold = bg_hold = bg_total = 0
    positions: list[int] = []
    stages: list[int] = []
    for res in results:
        outs = [v["outcome"] for v in res["trick"].values()]
        for v in res["trick"].values():
            counts[v["outcome"]] += 1
            for f in v["fired"]:
                fired[f] += 1
            if v["outcome"] == "watch" and "F3" in v["fired"]:
                watch_with_f3 += 1
            if v["outcome"] == "hold" and v.get("stage") in PIPELINE:
                stages.append(PIPELINE.index(v["stage"]))
        case_hold += "hold" in outs
        if res["first_hold_position"] is not None:
            positions.append(res["first_hold_position"])
        for v in res["background"].values():
            bg_total += 1
            bg_hold += v["outcome"] == "hold"
    n = sum(counts.values())
    share = (lambda x: x / n if n else 0.0)
    expected = cell.expected_full if expect_key == "full" else cell.expected_now
    if "hold_old_rule" in (cell.expected_full, cell.expected_now):
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
        "earliest_hold_stage": PIPELINE[min(stages)] if stages else None,
        "fired_share": {f: share(fired[f]) for f in BUILT},
        "watch_with_f3_share": share(watch_with_f3),
        "background_hold_deals": bg_hold, "background_deals": bg_total,
        "expected_now": cell.expected_now, "expected_full": cell.expected_full,
        "expected_for_this_mode": expected, "measured_outcome": measured,
        "matches_expected": None if measured == "not_measurable" else measured == expected,
        "blind_spot": cell.blind_spot, "must_not": cell.must_not,
        "old_rule_cell": "hold_old_rule" in (cell.expected_full, cell.expected_now),
    }


def pooled(cells: Sequence[Mapping[str, Any]], key: str = "hold") -> dict[str, Any]:
    n = sum(c["n_deals"] for c in cells)
    h = sum(c["deals"][key] for c in cells)
    return {"cells": [c["cell"] for c in cells], "n_deals": n, "count": h, "rate": h / n if n else 0.0}


def per_trick(cells: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One row per trick family: ring held/watch (pooled and by strength), twin false-hold."""
    out = []
    for fam in sorted({c["family"] for c in cells}):
        rings = [c for c in cells if c["family"] == fam and c["kind"] == "ring"]
        twins = [c for c in cells if c["family"] == fam and c["kind"] == "twin"]
        stages = [c["earliest_hold_stage"] for c in rings if c["earliest_hold_stage"]]
        r, w, tw = pooled(rings), pooled(rings, "watch"), pooled(twins)
        out.append({
            "trick": fam, "name": rings[0]["name"] if rings else twins[0]["name"],
            "ring_deals": r["n_deals"], "ring_held_rate": r["rate"], "ring_watch_rate": w["rate"],
            "ring_held_by_strength": {c["strength"]: c["hold_rate"] for c in rings},
            "twin_deals": tw["n_deals"], "twin_false_hold_rate": tw["rate"],
            "twin_watch_rate": pooled(twins, "watch")["rate"],
            "earliest_hold_stage": min(stages, key=PIPELINE.index) if stages else None,
        })
    return out


# ------------------------------------------------------------------ report

def measure(mode: str, cells: Sequence[Cell], hist: synth.History, limit: Optional[int],
            cache: BaselineCache, cfg, params: FraudParams) -> dict[str, Any]:
    summaries = []
    for cell in cells:
        shift = int(cell.params.get("history_shift_days", 0))
        results = []
        for case in synth.generate_cases(cell, hist, limit):
            base = cache.for_case(case, shift)
            if mode == "engine":
                results.append(evaluate_case_engine(case, base, cfg))
            else:
                results.append(evaluate_case_proxy(case, base, params, cfg))
        summaries.append(summarize_cell(cell, results, "full" if mode == "engine" else "now"))

    rings = [s for s in summaries if s["kind"] == "ring"]
    twins = [s for s in summaries if s["kind"] == "twin"]
    bar_cells = [s for s in rings if s["expected_full"] == "hold" and not s["blind_spot"]]
    unseen = [s for s in bar_cells if s["role"] != "positive_control_sample_like"]
    control = [s for s in bar_cells if s["role"] == "positive_control_sample_like"]
    blind = [s for s in rings if s["blind_spot"]]
    old_rule = [s for s in rings if s["old_rule_cell"]]
    ring_bar = pooled(bar_cells)
    twin_all = pooled(twins)
    return {
        "mode": mode,
        "rule": ({"measured": "prism.fraud.decide.evaluate (whatever decide() does today)"} if mode == "engine" else
                 {"measured": "proxy: F1 required plus hold_min_additional of the built families",
                  "required": hold_rule(cfg)[0], "additional_from_built": list(hold_rule(cfg)[1]),
                  "min_additional": hold_rule(cfg)[2]}),
        "per_trick": per_trick(summaries),
        "cells": summaries,
        "bars": {
            "catch_bar": {
                "target": HOLD_BAR, "scope": "ring cells with expected full = hold, blind spots excluded",
                "pooled": ring_bar, "unseen": pooled(unseen), "control_t1": pooled(control),
                "pass": ring_bar["rate"] >= HOLD_BAR,
            },
            "twin_bar": {
                "target": TWIN_BAR, "scope": "all benign twins, holds only",
                "pooled_hold": twin_all, "pooled_watch_friction": pooled(twins, "watch"),
                "pass": twin_all["rate"] <= TWIN_BAR,
                "twins_over_bar": [t["cell"] for t in twins if t["hold_rate"] > TWIN_BAR],
            },
            "background_false_holds": {
                "deals": sum(s["background_deals"] for s in summaries),
                "held": sum(s["background_hold_deals"] for s in summaries),
            },
            "blind_spot_cells": [{"cell": s["cell"], "hold_rate": s["hold_rate"],
                                  "watch_rate": s["watch_rate"], "reason": s["blind_spot"]} for s in blind],
            "not_measurable": {
                "old_rule_cells": [s["cell"] for s in old_rule],
                "history_flags_recall": "needs decide() history_flags; planted X- rows are in the baseline",
            },
        },
    }


def build_report(menus: Sequence[str], hist: synth.History, limit: Optional[int],
                 modes: Sequence[str] = MODES, fraud_path: Optional[Path] = None) -> dict[str, Any]:
    cfg = load_fraud_config(fraud_path)
    params = FraudParams.from_config(cfg)
    cache = BaselineCache(hist, params)
    cells = synth.cells_for(menus)
    core = synth.load_menu()
    real = cache.real(0)
    return {
        "schema_version": SCHEMA_VERSION,
        "stamp": {
            "menus": list(menus), "menu_version": core["version"], "menu_status": core["status"],
            "seed": core["seed"],
            "menu_commit": _git("log", "-1", "--format=%H", "--", "eval/trick_menu.yaml"),
            "engine_commit": _git("rev-parse", "HEAD"),
            "history_rows_count": len(hist.deal_rows),
            "computed_thresholds": {
                "tau": real.calibration.tau, "n_clean": real.calibration.n_clean,
                "clean_round_share_anchors": {str(q): hist.anchor(q) for q in (0.5, 0.9, 0.97, 0.995)},
            },
            "cases_per_cell_limit": limit,
            "injection": "feature layer: DealState.entities + features['deposit_months'] (Read bypassed)",
        },
        "modes": {m: measure(m, cells, hist, limit, cache, cfg, params) for m in modes},
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
    st = r["stamp"]
    L = [
        "# Synthetic validation report", "",
        f"- Menus: {', '.join(st['menus'])} (core v{st['menu_version']}, {st['menu_status']}); menu commit "
        f"`{st['menu_commit']}`; engine commit `{st['engine_commit']}`.",
        f"- History rows (baseline only): {st['history_rows_count']}; clean calibration deals: "
        f"{st['computed_thresholds']['n_clean']}. Injection: {st['injection']}.", "",
    ]
    for mode, m in r["modes"].items():
        cb, tb = m["bars"]["catch_bar"], m["bars"]["twin_bar"]
        L += [f"## Measurement: {mode}", "", f"Rule: {m['rule']['measured']}", "",
              "| Bar | Target | Measured | Result |", "|---|---|---|---|",
              f"| Ring deals held (cells that should hold, blind spots excluded) | >= {_pct(cb['target'])} | "
              f"{_pct(cb['pooled']['rate'])} ({cb['pooled']['count']} of {cb['pooled']['n_deals']}) | "
              f"{'PASS' if cb['pass'] else 'FAIL'} |",
              f"| Benign twins held (false flags) | <= {_pct(tb['target'])} | "
              f"{_pct(tb['pooled_hold']['rate'])} ({tb['pooled_hold']['count']} of {tb['pooled_hold']['n_deals']}) | "
              f"{'PASS' if tb['pass'] else 'FAIL'} |",
              f"| Benign twins on watch (friction) | reported | {_pct(tb['pooled_watch_friction']['rate'])} | n/a |",
              f"| Background deals held | 0 | {m['bars']['background_false_holds']['held']} of "
              f"{m['bars']['background_false_holds']['deals']} | n/a |", "",
              "### Per trick", "",
              "| Trick | Ring held | Ring watch | Held low / med / high | Twin false-hold | Twin watch | Earliest hold stage |",
              "|---|---|---|---|---|---|---|"]
        for t in m["per_trick"]:
            by = t["ring_held_by_strength"]
            strengths = " / ".join(_pct(by[s]) if s in by else "-" for s in ("low", "med", "high"))
            L.append(f"| {t['trick']} {t['name']} | {_pct(t['ring_held_rate'])} | {_pct(t['ring_watch_rate'])} | "
                     f"{strengths} | {_pct(t['twin_false_hold_rate']) if t['twin_deals'] else '-'} | "
                     f"{_pct(t['twin_watch_rate']) if t['twin_deals'] else '-'} | {t['earliest_hold_stage'] or '-'} |")
        L += ["", "### Cells", "",
              "| Cell | Cases | Held | Watch | Case held | Median first hold | Earliest stage | Expected | Measured | Blind spot |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for c in m["cells"]:
            pos = c["median_first_hold_position"]
            L.append(
                f"| {c['cell']} {c['name'] if c['kind'] == 'twin' else ''} | {c['n_cases']} | {_pct(c['hold_rate'])} | "
                f"{_pct(c['watch_rate'])} | {_pct(c['case_hold_rate'])} | {pos if pos is not None else '-'} | "
                f"{c['earliest_hold_stage'] or '-'} | {c['expected_for_this_mode']} | {c['measured_outcome']} | "
                f"{'yes' if c['blind_spot'] else ''} |")
        if tb["twins_over_bar"]:
            L += ["", "Twins over the 5% bar: " + ", ".join(tb["twins_over_bar"])]
        L += ["", "Blind-spot cells (reported, outside the 70% bar):", ""]
        for b in m["bars"]["blind_spot_cells"]:
            L.append(f"- {b['cell']}: held {_pct(b['hold_rate'])}, watch {_pct(b['watch_rate'])}")
        nm = m["bars"]["not_measurable"]
        L += ["", f"Not measurable here: old-rule cells {', '.join(nm['old_rule_cells']) or 'none'} "
              f"(known-checks path lives outside prism.fraud); {nm['history_flags_recall']}.", ""]
    return "\n".join(L)


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", default=str(ROOT / "out"))
    ap.add_argument("--menus", default="core", help="comma list of: core, redteam")
    ap.add_argument("--mode", default="both", choices=["both", *MODES])
    ap.add_argument("--max-cases", type=int, default=None, help="cap cases per cell (smoke runs)")
    ap.add_argument("--history-dir", default=None, help="history folder (default: PRISM_HISTORY_DIR or the data pack)")
    args = ap.parse_args(argv)
    hdir = Path(args.history_dir) if args.history_dir else synth.history_dir_from_env()
    hist = synth.load_history(hdir)
    if hist is None:
        print(f"run_synth: history not found at {hdir} (use --history-dir or PRISM_HISTORY_DIR); skipping")
        return 0
    modes = MODES if args.mode == "both" else (args.mode,)
    report = _round(build_report([m for m in args.menus.split(",") if m], hist, args.max_cases, modes))
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "synth_report.json", json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    _write(out / "synth_report.md", render_markdown(report))
    print(f"wrote {out / 'synth_report.json'} and {out / 'synth_report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
