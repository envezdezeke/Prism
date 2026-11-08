import sys; sys.path.insert(0,'.')
from harness import *
from prism.fraud.signals import score_f3
b=make_baseline(); cal=b.calibration; p=b.params
eq=[i for i in b.ordered_ids() if 'vendor' in b.deals[i].profile.entities]
gb={o[0] for g in b.vendor_groups().values() for o in g.members}
fire=[i for i in eq if (lambda f: f and f.bits>=cal.tau['F3'])(score_f3(b.deals[i].profile,b,p,exclude=i))]
print('equipment deals',len(eq),'in frequent-vendor groups',len(gb),'F3 fired',len(fire))
from collections import Counter
print(Counter(1 for i in fire if i in gb), 'fired that are in groups; of group deals fired share', len([i for i in fire if i in gb])/len(gb))
