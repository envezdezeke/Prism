import sys; sys.path.insert(0,'.')
from harness import *
from prism.fraud.baseline import HISTORY_COLUMN_KINDS
b=make_baseline()
r={x['deal_id']:x for x in rows('deals.csv')}
for hid in ['H-2511-002','H-2512-005','H-2601-006']:
    x=r[hid]; print(hid,x['legal_name'],x['relationship_since'],x['prior_note'][:50])
    ents={k:[x[c]] for c,k in HISTORY_COLUMN_KINDS.items() if x[c]}
    # new application by same borrower: clone entities; baseline contains the old deals (this one is a different one)
    # use baseline minus hid itself to represent "a later application of a returning customer"
    b2=make_baseline([y for y in rows('deals.csv') if y['deal_id']!=hid],[m for m in rows('monthly_deposits.csv') if m['deal_id']!=hid])
    s=signals(b2,{'N':state('N',ents,dep())})
    print('   ',[(q.family,q.deals,round(q.bits,1)) for q in s])
