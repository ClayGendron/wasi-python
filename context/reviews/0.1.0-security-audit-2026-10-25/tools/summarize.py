"""Parent-side Phase 6 helper: ledger coverage counts and the hunters' hardening notes, as JSON for the report."""
import json, os
from collections import Counter
OUT=os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
L=json.load(open(f"{OUT}/coverage-ledger.json"))
counts=Counter(u["status"] for u in L)
hard=[]
seen=set()
for u in L:
    for h in u.get("bookkeeping",{}).get("hardening",[]):
        if h not in seen:
            seen.add(h); hard.append({"unit": u["surface"][:90], "agent": u["agent_id"], "note": h})
checks=sum(len(u["local_checks"]) for u in L)
local=sum(1 for u in L for c in u["local_checks"] if c["method"]=="local")
agents=sorted({u["agent_id"] for u in L if u["agent_id"]} | {c["agent_id"] for u in L for c in u["local_checks"]})
out={"counts":dict(counts),"units":len(L),"checks":checks,"local_checks":local,"agents_with_checks":agents,"hardening":hard,
     "deferred":[{"surface":u["surface"][:120],"reason":u["unresolved"][0][:300]} for u in L if u["status"]=="deferred"],
     "covered_by_wave":Counter((u["wave"],u["status"]) for u in L).most_common()}
json.dump(out,open(f"{OUT}/summary.json","w"),indent=1,default=str)
print(json.dumps({k:out[k] for k in ("counts","units","checks","local_checks")}), "hardening notes:", len(hard))
