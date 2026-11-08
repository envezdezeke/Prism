import sys, os, json
sys.path.insert(0, "/Users/jes/Goldman-I"); sys.path.insert(0, "/Users/jes/Goldman-I/tests")
exec(open("/private/tmp/claude-501/-Users-jes-Goldman-I/c24be65f-9ce6-4015-9d75-c8a0512b091e/scratchpad/audit-move/exp1.py").read().split('print("== E1')[0])
from prism.contract import Fraud
import test_move_pipeline as tp
from test_move_support import persona
def pend(st): return [(i, r.type, r.to) for i, r in inbox.pending_requests(st)]
def run_human(opts, amount=100000, t0="2026-11-02T09:00"):
    st = good("Garza Family Pharmacy", t0, amount=amount)
    with persona("never"):
        t = at(t0) + timedelta(minutes=45)
        ms.step_deal(st, R, t)
        for o in opts:
            t += timedelta(hours=1)
            ms.step_deal(st, R, t)
            p = [x for x in pend(st) if x[1] != 'fraud_hold']
            if not p: print("no pending; stage", st.stage); break
            idx = p[0][0]
            try:
                inbox.record_reply(st, R, idx, o, t)
            except Exception as e:
                print("reply error", o, e); continue
            ms.step_deal(st, R, t)
        ms.step_deal(st, R, t + timedelta(hours=3))
    return st
print("== E7 decline at credit"); st = run_human(["decline"]); print(summarize(st)); print(st.stage_log[-1].why); print(len(st.alerts))
st=None
print("== E8 request_info at credit then new doc")
st = good("Garza Family Pharmacy","2026-11-02T09:00")
with persona("never"):
    ms.step_deal(st,R,at("2026-11-02T10:00")); 
    idx=[x for x in pend(st)][0][0]; inbox.record_reply(st,R,idx,"request_info",at("2026-11-02T11:00")); ms.step_deal(st,R,at("2026-11-02T11:05"))
    print(summarize(st), kinds if False else [(r.type,r.to,r.answer) for r in st.human_requests])
    add_doc(st,"2026-11-02T13:00"); ms.step_deal(st,R,at("2026-11-02T13:00")); ms.step_deal(st,R,at("2026-11-02T13:31"))
    print(summarize(st), [(r.type,r.to,r.at[5:],r.answer) for r in st.human_requests])
print("== E9 commitment not_yet")
st = good("Garza Family Pharmacy","2026-11-02T09:00")
with persona("fast"):
    with __import__('test_move_pipeline').answers(commitment_signoff="not_yet"):
        ms.step_deal(st,R,at("2026-11-09T09:00"))
print(summarize(st), [(r.type,r.to,r.answer) for r in st.human_requests])
print("== E10 funding hold")
st = good("Garza Family Pharmacy","2026-11-02T09:00")
with persona("fast"):
    with __import__('test_move_pipeline').answers(funding_release="hold"):
        ms.step_deal(st,R,at("2026-11-09T09:00"))
print(summarize(st), [(r.type,r.to,r.answer) for r in st.human_requests], [(a.level,a.to,a.stage,a.at[5:]) for a in st.alerts])
print("== E11 fraud_hold release_hold reply")
st = good("Garza Family Pharmacy","2026-11-02T09:00")
with persona("never"):
    ms.step_deal(st,R,at("2026-11-02T10:00"))
    st.fraud=Fraud(flagged=True,held=True,flagged_at="2026-11-02T10:30-06:00",stage_at_flag="Credit",reason="r",linked_deals=[])
    ms.step_deal(st,R,at("2026-11-02T11:00"))
    fi=[x for x in pend(st) if x[1]=='fraud_hold'][0][0]
    inbox.record_reply(st,R,fi,"release_hold",at("2026-11-02T11:30")); ms.step_deal(st,R,at("2026-11-05T11:30"))
    print(summarize(st), st.fraud.held, get_runtime(st).frozen_at)
    print(st.stage_log[-1].why)
