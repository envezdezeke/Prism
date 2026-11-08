"""Run real Move over the real sample with Read faked from eval/gold.json (Read is a stub in this tree)."""
import json, sys, os
from pathlib import Path
from datetime import datetime
sys.path.insert(0, "/Users/jes/Goldman-I")
os.environ.setdefault("PYTHONUTF8", "1")
from prism.contract import Fact, Fraud
from prism.engine import run as R
from prism.engine.visibility import parse_time
from prism.read import classify as C, extract as X, issues as I
from prism.fraud import decide as D

ROOT = Path("/Users/jes/Goldman-I")
gold = json.load(open(ROOT/"eval/gold.json"))["deals"]
arr = [json.loads(l) for l in open(ROOT/"data/participant/sim/arrivals.jsonl") if l.strip()]
last = {}
for a in arr:
    f = a["path"].split("/")[0]; t = parse_time(a["arrive_at"])
    last[f] = max(last.get(f, t), t)

def mk(overrides=None, fraud_at=None, issues_at_last=True, profile=None):
    overrides = overrides or {}
    def classify(doc): return doc
    def facts(state, rules):
        g = dict(gold[state.folder]["extracted"]); g.update(overrides.get(state.folder, {}))
        return {k: Fact(value=v, source_doc=state.docs[0].path, confidence=0.9) for k, v in g.items() if v is not None}
    def ents(state, rules): return []
    def issues(state, rules, now):
        iss = gold[state.folder]["issues"]
        iss = [i for i in iss if not i.startswith("OLD_TRICK")] if False else iss
        return list(iss) if (not issues_at_last or now >= last[state.folder]) else []
    R.read_classify.classify = classify; R.read_extract.extract_facts = facts
    R.read_extract.extract_entities = ents; R.read_issues.detect_issues = issues
    def evaluate(states, base, cfg, now):
        class O: pass
        o = O(); o.per_deal = {}; o.history_flags = []
        for n, s in states.items():
            g = gold[n]["fraud"]
            if g["flagged"] and s.docs and now >= last[n]:
                o.per_deal[n] = Fraud(flagged=True, held=True, flagged_at=(fraud_at or {}).get(n, last[n]).isoformat(timespec="minutes") if False else last[n].isoformat(timespec="minutes"), stage_at_flag=s.stage, reason="synthetic", linked_deals=[])
            else:
                o.per_deal[n] = s.fraud
        return o
    R.fraud_decide.evaluate = evaluate
    if profile: pass

def go(persona, end=None, **kw):
    os.environ["PRISM_MOVE_PERSONA"] = persona
    from prism.move import settings; settings._cached = None
    mk(**kw)
    res = R.run_sim(ROOT/"data/participant/shared_folder", ROOT/"data/participant/sim/arrivals.jsonl", data_root=ROOT/"data/participant", end=end)
    return res

if __name__ == "__main__":
    persona = sys.argv[1]; end = parse_time(sys.argv[2]) if len(sys.argv) > 2 else None
    res = go(persona, end)
    from prism.engine.writer import build_submission
    p = build_submission(res.states, res.history_flags, res.errors, team="Prism", set_name="sample")
    json.dump(p, open(sys.argv[3] if len(sys.argv) > 3 else f"/private/tmp/claude-501/-Users-jes-Goldman-I/c24be65f-9ce6-4015-9d75-c8a0512b091e/scratchpad/audit-move/sim_{persona}.json", "w"), indent=1)
    print(len(res.states), res.errors[:3])
