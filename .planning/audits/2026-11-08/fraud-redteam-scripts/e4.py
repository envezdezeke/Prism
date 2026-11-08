import sys; sys.path.insert(0,'.')
from harness import *
from prism.fraud.signals import score_f1, score_f3, score_f5
b=make_baseline(); cal=b.calibration; p=b.params
r={x['deal_id']:x for x in rows('deals.csv')}
for i in ['H-2604-013','H-2605-019','H-2511-012']:
    d=b.deals[i]; f1=score_f1(d.profile,b,p,exclude=i); f3=score_f3(d.profile,b,p,exclude=i); f5=score_f5(d.profile,b,p,cal.reference,exclude=i)
    x=r[i]; print(i,x['legal_name'],x['final_status'],x['equipment_vendor'],x['vendor_remit_acct_last4'],x['guarantor_name'],x['preparer_name'],x['amount_requested'],x['relationship_since'],x['prior_note'][:60])
    print('  F1',f1 and (round(f1.bits,2),f1.shared,f1.partners)); print('  F3',f3 and (round(f3.bits,2),f3.evidence)); print('  F5',f5 and (round(f5.bits,2),f5.stat))
# list F3 firing by what_differs
from collections import Counter
c=Counter()
for i in b.ordered_ids():
    f3=score_f3(b.deals[i].profile,b,p,exclude=i)
    if f3 and f3.bits>=cal.tau['F3']: c[f3.what_differs]+=1
print(c)
