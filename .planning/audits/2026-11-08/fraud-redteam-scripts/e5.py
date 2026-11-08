import sys; sys.path.insert(0,'.')
from harness import *
from datetime import date, timedelta
dr=rows('deals.csv')
for x in dr:
    d=date.fromisoformat(x['application_date']); x['application_date']=(d.replace(year=d.year+1)).isoformat()
b=make_baseline(dr)
print('history shifted +1y: n_clean',b.calibration.n_clean,'tau',b.calibration.tau)
ring=lambda: dict(preparer=['K. Delacroix'],phone=['(214) 555-0187'],vendor=['Metroplex Equipment Supply LLC'],remit_account=['4471'],pdf_producer=['DocuForge 2.1 (Windows)'])
st={'R1':state('R1',ring(),dep(8,1.0,'Mon,Thu'))}
print(verdict(signals(b,st)))
# Smaller / different history: drop hist to the first 100 deals
b2=make_baseline(dr[:100], [m for m in rows('monthly_deposits.csv') if m['deal_id'] in {x['deal_id'] for x in dr[:100]}])
print('first 100: ', b2.calibration.n_clean, b2.calibration.tau)
