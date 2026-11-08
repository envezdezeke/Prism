import sys; sys.path.insert(0,'.')
from harness import *
from prism.fraud.baseline import HISTORY_COLUMN_KINDS
b=make_baseline()
r={x['deal_id']:x for x in rows('deals.csv')}
for hid in ['H-2511-002','H-2512-005','H-2601-006']:
    x=r[hid]; ents={k:[x[c]] for c,k in HISTORY_COLUMN_KINDS.items() if x[c]}
    s=signals(b,{'N':state('N',ents,dep())})
    print(hid,x['legal_name'],[(q.family,q.deals,round(q.bits,1),q.evidence[:140]) for q in s if q.family=='F1'])
