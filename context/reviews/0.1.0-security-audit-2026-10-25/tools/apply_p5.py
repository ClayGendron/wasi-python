"""Parent-side Phase 5: apply a record verifier's decision. Usage: apply_p5.py <verifier_id> <material:yes|no>
verified -> mark; replace (non-material) -> update decisions.json's record; material replacements are NOT applied here."""
import json, os, sys
OUT = os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
rid, material = sys.argv[1], sys.argv[2]
res = json.load(open(os.path.join(OUT, "agents", rid, "scratch", "result.json")))
p5p = os.path.join(OUT, "phase5.json"); p5 = json.load(open(p5p)) if os.path.exists(p5p) else []
dec = json.load(open(os.path.join(OUT, "decisions.json")))
if res["decision"] == "verified":
    fp = res["fingerprint"]; p5.append({"verifier": rid, "fingerprint": fp, "decision": "verified"})
elif res["decision"] == "replace":
    rec = res["record"]; fp = rec["fingerprint"]
    old = [d for d in dec if d["fingerprint"] == fp][0]
    assert material == "no", "material replacement must go to a fresh verifier first"
    assert old["record"]["verdict"] == rec["verdict"], "verdict changed: material"
    old["record"] = rec; old["phase5_replacement_by"] = rid; old["phase5_reason"] = res["reason"]
    p5.append({"verifier": rid, "fingerprint": fp, "decision": "replace", "material": False, "reason": res["reason"]})
else:
    raise SystemExit("unknown decision")
json.dump(dec, open(os.path.join(OUT, "decisions.json"), "w"), indent=2)
json.dump(p5, open(p5p, "w"), indent=2)
print(json.dumps(p5[-1], indent=1)[:600])
