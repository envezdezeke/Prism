import sys; sys.path.insert(0,'.')
from harness import *
from prism.fraud.baseline import deposit_features, DealProfile
from prism.fraud.signals import score_f5
b=make_baseline(); cal=b.calibration; p=b.params
for days in ('Tue-Sun','Mon-Thu','Sat,Sun','Sat-Sun','Mon-Fri,Sun','Tue-Sat','Mon-Wed','Thu-Sat','Mon-Fri (Sat)','daily'):
    dp=deposit_features(dep(8,0.15,days))
    if dp is None: print(days,'-> unparsed: no day mass'); continue
    f=score_f5(DealProfile('x',{},dp),b,p,cal.reference); print(f'{days:14s} honest 15% round -> {f.bits:.2f} {f.stat} fires={f.bits>=cal.tau["F5"]}')
