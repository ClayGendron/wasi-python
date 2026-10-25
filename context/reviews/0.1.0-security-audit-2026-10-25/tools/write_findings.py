"""Parent-side Phase 4: write findings.json from decisions.json, sorted by fingerprint."""
import json, os
OUT = os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
dec = json.load(open(os.path.join(OUT, "decisions.json")))
records = sorted((d["record"] for d in dec), key=lambda r: r["fingerprint"])
with open(os.path.join(OUT, "findings.json"), "w") as f:
    json.dump(records, f, indent=2, ensure_ascii=False); f.write("\n")
print("wrote", len(records), "records:", [(r["verdict"], r["fingerprint"]) for r in records])
