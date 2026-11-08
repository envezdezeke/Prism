import sys; sys.path.insert(0,'.')
from harness import *
from prism.fraud.signals import score_f1, score_f3, score_f5
from collections import Counter
b=make_baseline(); cal=b.calibration; p=b.params
print('tau',cal.tau,'n_clean',cal.n_clean,'fire',cal.fire_rate_clean)
def fired(bits,t): return bits>0 and t is not None and bits>=t
res=[]
for i in b.ordered_ids():
    d=b.deals[i]
    f1=score_f1(d.profile,b,p,exclude=i); f3=score_f3(d.profile,b,p,exclude=i); f5=score_f5(d.profile,b,p,cal.reference,exclude=i)
    fam=[]
    if f1: fam.append('F1')
    if f3 and fired(f3.bits,cal.tau['F3']): fam.append('F3')
    if f5 and fired(f5.bits,cal.tau['F5']): fam.append('F5')
    res.append((i,d.fraud_label,d.final_status,d.repayment_status,fam,[k for k,_,_ in f1.shared] if f1 else []))
holds=[r for r in res if set(r[4])>={'F1','F3','F5'}]
print('LOO full-history holds under F1&F3&F5:',[(r[0],r[1],r[3]) for r in holds])
print('F1&F3 (any):',[(r[0],r[3]) for r in res if set(r[4])>={'F1','F3'}])
print('F1&F5:',[(r[0],r[3]) for r in res if set(r[4])>={'F1','F5'}])
print('F1 alone rate all', sum('F1' in r[4] for r in res)/len(res), Counter(k for r in res for k in r[5]))
print('F3 fired:',sum('F3' in r[4] for r in res),'F5 fired:',sum('F5' in r[4] for r in res), 'of',len(res))
print('F5 fired deals:',[(r[0],r[3]) for r in res if 'F5' in r[4]])
