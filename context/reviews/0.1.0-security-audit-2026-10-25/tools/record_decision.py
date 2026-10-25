"""Parent-side: record a Phase 3 verifier decision. Usage: record_decision.py <verifier_id>
Reads agents/<vid>/scratch/result.json ({"decision","record"}), checks verdict==decision and fingerprint matches a
candidate, appends to decisions.json, and adds a verifier-owned check to the linked ledger unit(s)."""
import json, os, sys, glob
OUT = os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
vid = sys.argv[1]
res = json.load(open(os.path.join(OUT, "agents", vid, "scratch", "result.json")))
dec, rec = res["decision"], res["record"]
assert rec["verdict"] == dec, ("verdict mismatch", rec.get("verdict"), dec)
assert dec in ("confirmed", "needs_validation", "rejected")
fp = rec["fingerprint"]
cands = json.load(open(os.path.join(OUT, "candidates.json")))
assert any(c["fingerprint"] == fp for c in cands), "fingerprint not among candidates"
dpath = os.path.join(OUT, "decisions.json")
decisions = json.load(open(dpath)) if os.path.exists(dpath) else []
decisions = [d for d in decisions if d["fingerprint"] != fp] + [{"fingerprint": fp, "verifier": vid, "decision": dec, "record": rec}]
json.dump(decisions, open(dpath, "w"), indent=2)
ledger = json.load(open(os.path.join(OUT, "coverage-ledger.json")))
paths = sorted({e["file"] for e in rec.get("trace", [])} | {e["file"] for e in rec.get("evidence", [])})
paths = [p for p in paths if not p.startswith("/")]
promoted = sorted(glob.glob(os.path.join(OUT, "agents", vid, "artifacts", "evidence", "*")))
artifact = os.path.relpath(promoted[0], OUT) if promoted else None
check = {"agent_id": vid, "reviewed_paths": paths, "invariant": f"Phase 3 verification of {fp}: {rec['title']}",
         "method": "local" if artifact else "source",
         "result": f"decision={dec}. " + (rec.get("execution", {}).get("observed_result") or rec.get("reason") or "; ".join(rec.get("blockers", []))),
         "artifact": artifact}
n = 0
for u in ledger:
    if fp in u.get("result_fingerprints", []):
        u["local_checks"].append(check)
        u["reviewed_paths"] = sorted(set(u["reviewed_paths"]) | set(paths))
        u.setdefault("bookkeeping", {}).setdefault("decisions", []).append({"fingerprint": fp, "verifier": vid, "decision": dec})
        n += 1
json.dump(ledger, open(os.path.join(OUT, "coverage-ledger.json"), "w"), indent=2, ensure_ascii=False)
print(json.dumps({"verifier": vid, "fingerprint": fp, "decision": dec, "units_updated": n, "artifact": artifact}))
