import sys; sys.path.insert(0,'.')
from harness import *
b=make_baseline()
print('history placeholder dfs:', {k:b.value_counts(k).get(v,0) for k,v in [('preparer','self prepared'),('registered_agent','owner')]})
from collections import Counter
print(Counter(b.value_counts('preparer')).most_common(0), sorted(b.value_counts('preparer').items(), key=lambda x:-x[1])[:8])
print(sorted(b.value_counts('registered_agent').items(), key=lambda x:-x[1])[:8])
print(sorted(b.value_counts('bank').items(), key=lambda x:-x[1])[:12])
print(sorted(b.value_counts('guarantor').items(), key=lambda x:-x[1])[:6])
def links(kind,a,c):
    st={'A':state('A',{kind:[a]}),'B':state('B',{kind:[c]})}
    return any(x.family=='F1' and x.deals[0]=='A' and 'B' in x.deals for x in signals(b,st))
for k,v in [('preparer','N/A'),('preparer','None'),('preparer','Self'),('preparer','Self-Prepared'),('preparer','Owner'),('registered_agent','Same as applicant'),('registered_agent','Self'),('registered_agent','N/A'),('registered_agent','Unknown'),('phone','000-000-0000'),('phone','555-555-5555'),('address','TBD'),('bank','Chase'),('bank','Wells Fargo'),('remit_account','0000'),('remit_account','n/a'),('vendor','TBD'),('pdf_producer','Microsoft Word'),('pdf_producer','Microsoft® Word for Microsoft 365')]:
    print(f'{k:17s} {v!r:36s} two unrelated deals -> F1 link: {links(k,v,v)}')
