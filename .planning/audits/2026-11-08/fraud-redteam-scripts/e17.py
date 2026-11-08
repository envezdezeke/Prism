import sys,random,statistics; sys.path.insert(0,'.')
from harness import *
dr=rows('deals.csv'); dp=rows('monthly_deposits.csv')
random.seed(7)
res=[]
for t in range(40):
    keep=set(x['deal_id'] for x in random.sample(dr,int(len(dr)*0.8)))
    b=make_baseline([x for x in dr if x['deal_id'] in keep],[m for m in dp if m['deal_id'] in keep])
    c=b.calibration
    res.append((c.n_clean,c.tau['F3'],c.tau['F5'],c.fire_rate_clean['F1'],c.fire_rate_clean['F3'],c.fire_rate_clean['F5']))
def rng(i): xs=[r[i] for r in res if r[i] is not None]; return f'min {min(xs):.3f} med {statistics.median(xs):.3f} max {max(xs):.3f} (None x{sum(r[i] is None for r in res)})'
print('n_clean',rng(0)); print('tau F3',rng(1)); print('tau F5',rng(2)); print('F1 clean fire rate',rng(3)); print('F3 clean fire',rng(4)); print('F5 clean fire',rng(5))
