import sys, os, json
sys.path.insert(0, "/Users/jes/Goldman-I"); sys.path.insert(0, "/Users/jes/Goldman-I/tests")
exec(open("/private/tmp/claude-501/-Users-jes-Goldman-I/c24be65f-9ce6-4015-9d75-c8a0512b091e/scratchpad/audit-move/exp1.py").read().split('print("== E1')[0])
from prism.contract import Fraud
print("== E15 funded deal then flagged in weekend drop")
st = good("Garza Family Pharmacy","2026-11-02T09:00")
with persona("fast"):
    ms.step_deal(st,R,at("2026-11-02T20:00"))
    print(summarize(st)[-1], get_runtime(st).terminal)
    add_doc(st,"2026-11-07T10:00","collections.pdf")
    st.fraud=Fraud(flagged=True,held=True,flagged_at="2026-11-07T10:00-06:00",stage_at_flag="Closed",reason="collections",linked_deals=[])
    ms.step_deal(st,R,at("2026-11-07T10:00")); ms.step_deal(st,R,at("2026-11-08T12:00"))
    print(summarize(st)[-1]); print([(r.type,r.to) for r in st.human_requests]); print(len(st.alerts))
print("== E16 new doc on an in-flight deal at Credit resolves missing issue -> resume")
st = good("Garza Family Pharmacy","2026-11-02T09:00", issues=["MISSING_DOC:tax_return"])
with persona("fast"):
    ms.step_deal(st,R,at("2026-11-02T11:00")); print(summarize(st)[-1], [(r.type,r.to) for r in st.human_requests])
    st.issues=[]; add_doc(st,"2026-11-02T12:00","tax.pdf"); ms.step_deal(st,R,at("2026-11-02T12:00")); ms.step_deal(st,R,at("2026-11-02T13:00"))
    print(summarize(st)[-1], [(r.type,r.to) for r in st.human_requests])
print("== E17 issue arriving at Committee stage (MISMATCH) while waiting")
st = good("Garza Family Pharmacy","2026-11-02T09:00")
with persona("never"):
    ms.step_deal(st,R,at("2026-11-02T10:00"))
    idx=inbox.pending_requests(st)[0][0]; inbox.record_reply(st,R,idx,"approve",at("2026-11-02T10:10")); ms.step_deal(st,R,at("2026-11-02T10:11"))
    print(summarize(st)[-1])
    st.issues=["MISMATCH:annual_revenue"]; add_doc(st,"2026-11-02T10:20","late.pdf"); ms.step_deal(st,R,at("2026-11-02T10:20"))
    idx=inbox.pending_requests(st)[0][0]; inbox.record_reply(st,R,idx,"approve",at("2026-11-02T11:00")); ms.step_deal(st,R,at("2026-11-02T11:01"))
    print("Committee approved w/ open MISMATCH:annual_revenue ->", summarize(st)[-1], [(r.type,r.to) for r in st.human_requests])
