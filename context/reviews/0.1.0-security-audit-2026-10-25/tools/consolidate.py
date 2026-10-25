"""Parent-side: fold one hunter's structured result into the ledger.

Usage: consolidate.py <agent_id>  (reads agents/<id>/scratch/result.json, requires promote.py already run)
Rules (HUNTING.md): every assigned ID exactly once; covered needs paths+checks, no fingerprints, no unresolved;
candidate needs fingerprints; blocked needs unresolved; source checks have artifact null; local checks name a promoted file
under agents/<check.agent_id>/artifacts/. Candidates are appended to candidates.json for Phase 3.
"""
import json, os, re, sys
OUT = os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
aid = sys.argv[1]
res = json.load(open(os.path.join(OUT, "agents", aid, "scratch", "result.json")))
ledger = json.load(open(os.path.join(OUT, "coverage-ledger.json")))
by_id = {u["coverage_id"]: u for u in ledger}
assigned = [u for u in ledger if u["agent_id"] == aid and u["status"] == "in_progress"]
assigned_ids = {u["coverage_id"] for u in assigned}
seen = set(); errors = []
AID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
FP_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$")

def rel_ok(p):
    return isinstance(p, str) and p and not p.startswith("/") and ".." not in p.split("/")

for unit in res.get("units", []):
    cid = unit.get("coverage_id")
    if cid not in assigned_ids or cid in seen:
        errors.append(f"unit id not assigned or duplicate: {cid}"); continue
    seen.add(cid)
    u = by_id[cid]
    disp = unit.get("disposition")
    paths = unit.get("reviewed_paths", []); checks = unit.get("checks", [])
    fps = unit.get("candidate_fingerprints", []); unresolved = unit.get("unresolved", [])
    ok = True
    if not paths or not checks: ok = False; errors.append(f"{cid}: empty paths or checks")
    union = set()
    for c in checks:
        if not AID_RE.match(c.get("agent_id", "")): ok = False; errors.append(f"{cid}: bad check agent_id")
        if not c.get("reviewed_paths"): ok = False; errors.append(f"{cid}: check without paths")
        if not all(rel_ok(p) for p in c.get("reviewed_paths", [])): ok = False; errors.append(f"{cid}: non-relative path")
        union.update(c.get("reviewed_paths", []))
        if c.get("method") == "source" and c.get("artifact") is not None: ok = False; errors.append(f"{cid}: source check with artifact")
        if c.get("method") == "local":
            a = c.get("artifact") or ""
            prefix = f"agents/{c.get('agent_id')}/artifacts/"
            if not a.startswith(prefix) or not os.path.isfile(os.path.join(OUT, a)):
                ok = False; errors.append(f"{cid}: local check artifact not promoted: {a}")
    if set(paths) != union:
        # tolerate: set unit paths to the union, record note
        paths = sorted(union)
    if disp == "covered" and (fps or unresolved): ok = False; errors.append(f"{cid}: covered with fingerprints/unresolved")
    if disp == "candidate" and not fps: ok = False; errors.append(f"{cid}: candidate without fingerprints")
    if disp == "blocked" and (not unresolved or fps): ok = False; errors.append(f"{cid}: blocked needs unresolved and no fingerprints")
    if any(not FP_RE.match(f) for f in fps): ok = False; errors.append(f"{cid}: bad fingerprint")
    if not ok:
        continue  # stays in_progress -> parent will reset to planned
    u["status"] = disp; u["reviewed_paths"] = sorted(paths); u["local_checks"] = checks
    u["result_fingerprints"] = fps; u["unresolved"] = unresolved
    u.setdefault("bookkeeping", {})["hardening"] = res.get("hardening", [])

for u in assigned:
    if u["coverage_id"] not in seen or u["status"] == "in_progress":
        u["status"] = "planned"; u["agent_id"] = None; u["reviewed_paths"] = []; u["local_checks"] = []
        u["result_fingerprints"] = []; u["unresolved"] = []
        errors.append(f"{u['coverage_id']}: left planned for reassignment")

cands_path = os.path.join(OUT, "candidates.json")
cands = json.load(open(cands_path)) if os.path.exists(cands_path) else []
for c in res.get("candidates", []):
    c["_hunter"] = aid
    cands.append(c)
json.dump(cands, open(cands_path, "w"), indent=2)
unc_path = os.path.join(OUT, "uncovered.json")
unc = json.load(open(unc_path)) if os.path.exists(unc_path) else []
for x in res.get("uncovered", []):
    x["_hunter"] = aid; unc.append(x)
json.dump(unc, open(unc_path, "w"), indent=2)
with open(os.path.join(OUT, "coverage-ledger.json"), "w") as f:
    json.dump(ledger, f, indent=2, ensure_ascii=False); f.write("\n")
print(json.dumps({"agent": aid, "units": len(seen), "candidates": len(res.get("candidates", [])), "uncovered": len(res.get("uncovered", [])), "errors": errors}, indent=1))
