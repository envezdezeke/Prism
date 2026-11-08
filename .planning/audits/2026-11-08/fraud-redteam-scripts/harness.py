import csv, sys, copy
from datetime import datetime
from pathlib import Path
sys.path.insert(0, '/Users/jes/Goldman-I')
from prism.engine.config import load_fraud_config
from prism.engine.state import DealState, EntityRef
from prism.fraud.baseline import build_baseline, Baseline
from prism.fraud.rarity import FraudParams
from prism.fraud.calibrate import compute_thresholds
from prism.fraud.graph import build_graph
from prism.fraud.signals import compute_signals

HIST = Path('/Users/jes/Goldman-I/data/participant/history')
CFG = load_fraud_config(None)

def rows(name):
    return list(csv.DictReader(open(HIST/name, encoding='utf-8-sig', newline='')))

def make_baseline(deal_rows=None, dep_rows=None, cfg=CFG):
    params = FraudParams.from_config(cfg)
    b = Baseline.from_rows(deal_rows if deal_rows is not None else rows('deals.csv'),
                           dep_rows if dep_rows is not None else rows('monthly_deposits.csv'), params=params)
    b.calibration = compute_thresholds(b, params)
    return b

def state(folder, ents, dep=None):
    s = DealState(folder=folder)
    s.entities = [EntityRef(k, v, f'{folder}/x.pdf') for k, vs in ents.items() for v in (vs if isinstance(vs, list) else [vs])]
    if dep is not None:
        s.features['deposit_months'] = dep
    return s

def dep(count=8, round_=0.15, days='Mon-Fri', months=6):
    return [dict(deposit_count=count, pct_deposits_multiple_of_100=round_, deposit_weekdays=days) for _ in range(months)]

def signals(b, states):
    g = build_graph(states, b)
    return compute_signals(g, states, b, CFG, datetime(2026,11,3))

def verdict(sigs):
    """Hold rule as designed with what exists: F1 + >=2 of F2..F5 (only F3/F5 built)."""
    out = {}
    folders = sorted({d for s in sigs for d in s.deals if s.family != 'F1'} | {s.deals[0] for s in sigs})
    for f in folders:
        fam = {s.family for s in sigs if s.deals[0] == f and s.fired}
        extra = len(fam & {'F2','F3','F4','F5'})
        out[f] = ('HOLD' if 'F1' in fam and extra >= 2 else 'watch' if fam else 'clear', sorted(fam))
    return out
