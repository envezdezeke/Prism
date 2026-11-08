import sys, os, json
sys.path.insert(0, "/Users/jes/Goldman-I"); sys.path.insert(0, "/Users/jes/Goldman-I/tests")
exec(open("/private/tmp/claude-501/-Users-jes-Goldman-I/c24be65f-9ce6-4015-9d75-c8a0512b091e/scratchpad/audit-move/exp1.py").read().split('print("== E1')[0])
print("== E12 unassigned deal")
st = good("Unlisted Co LLC","2026-11-02T09:00")
with persona("fast"):
    ms.step_deal(st,R,at("2026-11-09T09:00"))
print(summarize(st), [(r.type,r.to) for r in st.human_requests], [(a.level,a.to,a.stage,a.at[5:]) for a in st.alerts][:6], st.error)
print("== E13 simultaneous: two files same minute, quiet window exact boundary")
st = good("Garza Family Pharmacy","2026-11-02T09:00")
add_doc(st,"2026-11-02T09:30")  # second doc arrives exactly when 30 min elapsed from first
with persona("never"):
    ms.step_deal(st,R,at("2026-11-02T09:00")); ms.step_deal(st,R,at("2026-11-02T09:30"))
    print(summarize(st))
    ms.step_deal(st,R,at("2026-11-02T09:59")); print(summarize(st))
    ms.step_deal(st,R,at("2026-11-02T10:00")); print(summarize(st))
print("== E14 answer at exact 100% crossing")
st = good("Garza Family Pharmacy","2026-11-02T09:00")
with persona("never"):
    ms.step_deal(st,R,at("2026-11-02T09:31"))
    cred_entered = st.stage_entered_at; print("entered", cred_entered)
    idx=[x for x in pend(st) if x[1]=='credit_decision'][0][0] if False else inbox.pending_requests(st)[0][0]
    t100 = cred_entered + timedelta(hours=48)
    inbox.record_reply(st,R,idx,"approve",t100)
    ms.step_deal(st,R,t100+timedelta(minutes=1))
    print(summarize(st)); print([(a.level,a.to,a.stage,a.at[5:]) for a in st.alerts]); print([(r.type,r.to,r.at[5:],r.answer) for r in st.human_requests])
