import sys, os, copy, json
sys.path.insert(0, "/Users/jes/Goldman-I"); sys.path.insert(0, "/Users/jes/Goldman-I/tests")
exec(open("/private/tmp/claude-501/-Users-jes-Goldman-I/c24be65f-9ce6-4015-9d75-c8a0512b091e/scratchpad/audit-move/exp1.py").read().split('print("== E1')[0])
from prism.contract import Fraud
def dump(st): return json.dumps([[e.model_dump() for e in st.stage_log],[r.model_dump() for r in st.human_requests],[a.model_dump() for a in st.alerts]], sort_keys=True)
print("== E5 jump vs incremental equivalence (never persona, ladder)")
for pers in ("never","slow","fast"):
    a = good("Oakline Auto","2026-11-02T09:00"); b = good("Oakline Auto","2026-11-02T09:00")
    with persona(pers):
        ms.step_deal(a,R,at("2026-11-12T00:00"))
        t = at("2026-11-02T09:00")
        while t < at("2026-11-12T00:00"):
            ms.step_deal(b,R,t); t += timedelta(minutes=17)
        ms.step_deal(b,R,at("2026-11-12T00:00"))
    print(pers, dump(a)==dump(b))
print("== E6 hold at Credit then clear; SLA freeze")
st = good("Oakline Auto","2026-11-02T09:00")
with persona("never"):
    ms.step_deal(st,R,at("2026-11-02T12:00"))
    print(summarize(st), st.stage_entered_at)
    st.fraud = Fraud(flagged=True, held=True, flagged_at="2026-11-02T13:00-06:00", stage_at_flag="Credit", reason="x", linked_deals=[])
    ms.step_deal(st,R,at("2026-11-02T14:00"))
    ms.step_deal(st,R,at("2026-11-08T14:00"))
    print([(e.stage,e.entered_at,e.exited_at,e.decision) for e in st.stage_log])
    print(st.stage_log[-1].why)
    print([(r.type,r.to,r.at[5:]) for r in st.human_requests])
    print([(a.level,a.to,a.at[5:]) for a in st.alerts])
    print("sla_pct", sla.sla_pct(st,R,at("2026-11-08T14:00")))
    st.fraud = Fraud()
    ms.step_deal(st,R,at("2026-11-09T09:00"))
    print([(e.stage,e.entered_at[5:],e.decision) for e in st.stage_log]); print(st.stage_log[-1].why)
    ms.step_deal(st,R,at("2026-11-14T09:00"))
    print([(a.level,a.to,a.at[5:]) for a in st.alerts])
