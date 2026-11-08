import sys; sys.path.insert(0,'.')
from harness import *
from dataclasses import replace
from prism.fraud.baseline import deposit_features, DealProfile
from prism.fraud.signals import score_f5
b=make_baseline(); cal=b.calibration; p=b.params
print('tau F5',cal.tau['F5'])
import statistics
rs=sorted(b.round_shares()); print('hist round share quantiles', [round(rs[int(q*(len(rs)-1))],3) for q in (.5,.9,.95,.99,1)])
for days in ('Mon-Fri','Mon-Sat','Mon,Wed,Fri','Tue,Thu','Mon,Thu','Mon','all days'):
    row=[]
    for rnd in (0.1,0.3,0.5,0.7,0.9,1.0):
        dp=deposit_features(dep(8,rnd,days)); f=score_f5(DealProfile('x',{},dp),b,p,cal.reference)
        row.append(f'{rnd}:{f.bits:.1f}{"*" if f.bits>=cal.tau["F5"] else ""}({f.stat})')
    print(f'{days:12s}',' '.join(row))
# deposit_weekdays labels present in history
from collections import Counter
print(Counter(m['deposit_weekdays'] for m in rows('monthly_deposits.csv')))
# count effect: few deposits per month
for c in (2,4,8,20):
    dp=deposit_features(dep(c,1.0,'Mon-Fri')); f=score_f5(DealProfile('x',{},dp),b,p,cal.reference); print('count',c,'100% round Mon-Fri',round(f.bits,2),f.stat)
