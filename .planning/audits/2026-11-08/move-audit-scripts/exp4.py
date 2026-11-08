import sys, os
sys.path.insert(0, "/Users/jes/Goldman-I"); sys.path.insert(0, "/Users/jes/Goldman-I/tests")
exec(open("/private/tmp/claude-501/-Users-jes-Goldman-I/c24be65f-9ce6-4015-9d75-c8a0512b091e/scratchpad/audit-move/exp1.py").read().split('print("== E1')[0])
from prism.move import deadline as dl
st = good("Priya's Bakery","2026-11-03T08:46", needed_by="2026-11-06T15:00-06:00")
st.stage_entered_at = at("2026-11-03T08:46"); 
print("projected (code):", dl.project_finish(st,R,at("2026-11-03T08:46")))
tot = sum(dl.typical_hours(R,s) for s in R.stages.pipeline); print("sum typical wall hours", tot, "=> wall-clock finish", at("2026-11-03T08:46")+timedelta(hours=tot))
for s in R.stages.pipeline: print(s, dl.typical_hours(R,s), "latest_exit", dl.latest_exit(st,R,s))
print("answer_by", dl.answer_by(st,R))
# weekend tail
print("badge", dl.needed_by_badge(st,R,at("2026-11-03T08:46")))
