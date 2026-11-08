import sys; sys.path.insert(0,'.')
from harness import *
import copy
dr=rows('deals.csv'); dep_=rows('monthly_deposits.csv')
tmpl=copy.deepcopy(dr[10])
for k in (0,2,4,5,6,8,12):
    extra=[]
    for j in range(k):
        x=copy.deepcopy(tmpl); x.update(deal_id=f'X-{j}',legal_name=f'Fake {j} LLC',ein=f'00-000000{j}',guarantor_name=f'G{j}',business_address=f'{j} Z St',preparer_name='Zed Quill',preparer_phone='469-555-0111',
            registered_agent=f'Agent {j}',equipment_vendor='',vendor_remit_acct_last4='',pdf_producer='Skia/PDF m124',final_status='funded',fraud_label='none',repayment_status='current')
        extra.append(x)
    b=make_baseline(dr+extra,dep_)
    s=[q for q in signals(b,{'N':state('N',dict(preparer=['Zed Quill'],phone=['469-555-0111'],bank=['Trinity Commercial Bank']),dep()),'M':state('M',dict(preparer=['Zed Quill'],phone=['469-555-0111']),dep())}) if q.family=='F1']
    print(f'{k} prior ring members in history (n={len(dr)+k}): F1 fires for 2 new ring deals:', bool([q for q in s if q.deals[0]=='N' and 'M' in q.deals]), '| strong kinds:', [q.evidence[:90] for q in s][:1])
