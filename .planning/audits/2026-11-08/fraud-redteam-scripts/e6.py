import sys; sys.path.insert(0,'.')
from harness import *
from collections import defaultdict
from dataclasses import replace
from prism.fraud.baseline import deposit_features
from prism.fraud.signals import score_f5
b=make_baseline(); cal=b.calibration; p=b.params
mon=defaultdict(list)
for m in rows('monthly_deposits.csv'): mon[m['deal_id']].append(m)
clean=[i for i in b.ordered_ids() if b.deals[i].clean and b.deals[i].applied<=p.train_end]
allc=[i for i in b.ordered_ids() if b.deals[i].clean]
for k in (1,2,3,6):
    fired=0;n=0
    for i in allc:
        ms=sorted(mon[i],key=lambda m:m['month'])
        if not ms: continue
        for sel in ([ms[:k]] if k<6 else [ms]):
            dp=deposit_features(sel)
            if dp is None: continue
            prof=replace(b.deals[i].profile,deposits=dp)
            f5=score_f5(prof,b,p,cal.reference,exclude=i); n+=1
            fired+= bool(f5 and f5.bits>0 and f5.bits>=cal.tau['F5'])
    print(f'first {k} months: F5 fires on {fired}/{n} = {fired/n:.1%} of clean (nominal 5%)')
# months-per-deal and counts
import collections
print(collections.Counter(len(v) for v in mon.values()))
