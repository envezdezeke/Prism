import sys, os
sys.path.insert(0, "/Users/jes/Goldman-I"); sys.path.insert(0, "/Users/jes/Goldman-I/tests")
os.environ["PYTHONUTF8"]="1"
from pathlib import Path
from datetime import datetime, timedelta
from prism.engine.config import load_rules
from prism.engine.visibility import parse_time as at
from prism.move import stage as ms, routing, sla, inbox
from prism.move.runtime import get_runtime
from prism.move.settings import get_config, use_config
import dataclasses
from test_move_support import make_state, GOOD_PROFILE, fact, persona, add_doc
R = load_rules(Path("/Users/jes/Goldman-I/data/participant"))
def good(folder, arrive, **kw):
    st = make_state(folder, arrive, profile=dict(GOOD_PROFILE), **kw)
    st.facts["annual_revenue_stated"] = fact(700000)
    return st
def summarize(st):
    return [(e.stage, e.entered_at[5:], (e.exited_at or '-')[5:], e.decision) for e in st.stage_log]
print("== E1 amount boundary (never persona to freeze at Committee? use fast and inspect committee req)")
for amt in (249999.99, 250000, 250000.0, "249,999.99", "$250,000.00", 249999.995, 250000.01, 249999.994):
    st = good("Garza Family Pharmacy", "2026-11-02T09:00", amount=amt)
    with persona("fast"):
        ms.step_deal(st, R, at("2026-11-10T12:00"))
    rt = get_runtime(st)
    cr = [r for r in st.human_requests if r.type=="committee_approval"]
    print(repr(amt), cr[0].to if cr else None, "limit", sla.stage_limit_hours(st,R,"Committee"))
print("== E2 OOO boundaries: credit_decision to for Priya (dana) entering Credit at various times")
for t in ("2026-11-02T17:59","2026-11-03T07:59","2026-11-03T08:00","2026-11-06T17:59","2026-11-06T18:00","2026-11-06T18:01","2026-11-09T09:00"):
    print(t, routing.route_gate("credit_decision", make_state("Priya's Bakery"), R, at(t)), "owner stage Credit:", routing.stage_owner("Credit", make_state("Priya's Bakery"), R, at(t)))
print("== E3 deal enters Credit Mon 17:00 (dana in), OOO starts Tue 08:00, never persona")
st = good("Priya's Bakery", "2026-11-02T16:00")
with persona("never"):
    ms.step_deal(st, R, at("2026-11-07T00:00"))
print(summarize(st))
print([(r.type, r.to, r.at[5:]) for r in st.human_requests])
print([(a.level, a.to, a.stage, a.at[5:]) for a in st.alerts])
print("== E4 same but fast persona (answers within business minutes): who answers")
st = good("Priya's Bakery", "2026-11-02T16:00")
with persona("slow"):
    ms.step_deal(st, R, at("2026-11-12T00:00"))
print(summarize(st))
print([(r.type, r.to, r.at[5:], r.answer, (r.answered_at or '')[5:]) for r in st.human_requests])
