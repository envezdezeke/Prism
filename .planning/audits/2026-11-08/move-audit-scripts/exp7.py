import sys, os, json
sys.path.insert(0, "/Users/jes/Goldman-I"); sys.path.insert(0, "/Users/jes/Goldman-I/tests")
exec(open("/private/tmp/claude-501/-Users-jes-Goldman-I/c24be65f-9ce6-4015-9d75-c8a0512b091e/scratchpad/audit-move/exp1.py").read().split('print("== E1')[0])
print("== E18 OLD_TRICK issue, fraud module silent")
st = good("Granite Bay Building Supply","2026-11-03T15:00", issues=["OLD_TRICK:STMT_TAMPER","OLD_TRICK:REV_INFLATION"], amount=300000)
with persona("fast"):
    ms.step_deal(st,R,at("2026-11-12T00:00"))
print(summarize(st), [(r.type,r.to) for r in st.human_requests], [(a.level,a.to,a.at[5:]) for a in st.alerts])
print("== E19 vendor_verified None vs False on equipment loan")
for vv in (None, False, True):
    prof = dict(GOOD_PROFILE); 
    if vv is not None: prof["vendor_verified"]=vv
    st = make_state("Garza Family Pharmacy","2026-11-02T09:00", product="Equipment Loan", profile=prof); st.facts["annual_revenue_stated"]=fact(700000)
    with persona("fast"):
        ms.step_deal(st,R,at("2026-11-12T00:00"))
    print(vv, st.stage)
print("== E20 info_request message: dup suppression when same issue reappears")
