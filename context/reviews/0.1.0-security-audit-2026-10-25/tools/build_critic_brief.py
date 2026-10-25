"""Parent-side: build a coverage-critic brief. Usage: build_critic_brief.py <critic_id> <post-wave N | final-clean>"""
import json, os, sys
OUT=os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
SKILL="./.agents/skills/security-audit"
cid, kind = sys.argv[1], sys.argv[2]
h=open(f"{SKILL}/HUNTING.md",encoding="utf-8").read()
i=h.index("## Coverage-critic waves"); j=h.index("The parent rejects proposed units", i)
critic_text=h[i:j]
arch=open(f"{OUT}/architecture.md",encoding="utf-8").read()
L=json.load(open(f"{OUT}/coverage-ledger.json"))
slim=[{k:u[k] for k in ("coverage_id","surface","boundary","subsystem","attack_class","starting_paths","ordinary_attack_class_block","selected_companion_blocks","excluded_blocks","status","agent_id","wave","reviewed_paths","unresolved","result_fingerprints")} | ({"lifecycle":u["lifecycle"]} if "lifecycle" in u else {}) | {"checks":[{"agent_id":c["agent_id"],"invariant":c["invariant"],"method":c["method"],"result":c["result"][:600]} for c in u["local_checks"]], "hardening": u.get("bookkeeping",{}).get("hardening",[]), "bookkeeping_note": u.get("bookkeeping",{}).get("reason") or u.get("bookkeeping",{}).get("note")} for u in L]
dec=json.load(open(f"{OUT}/decisions.json"))
cands=[{"fingerprint":d["fingerprint"],"decision":d["decision"],"title":d["record"]["title"]} for d in dec]
unc=json.load(open(f"{OUT}/uncovered.json"))
prior=[json.load(open(f"{OUT}/agents/{c}/scratch/result.json")) for c in ("c01-critic","c02-critic","c03-critic") if os.path.exists(f"{OUT}/agents/{c}/scratch/result.json")]
root=f"{OUT}/agents/{cid}"; os.makedirs(f"{root}/scratch",exist_ok=True)
brief=f"""# Coverage critic brief: {cid} ({kind})

## 1. Instructions (verbatim from the skill's HUNTING.md)

{critic_text}
You read source under . (read-only; run nothing; write nothing except your own scratch at {root}/scratch/). Return exactly the JSON object the instructions specify, no prose, and write it to {root}/scratch/result.json.

Notes for this run: no prior ledger exists. Two units are `deferred` with a stated reason (no structured result could be produced in this run); do not propose reassigning them and do not restate their subject. The previous critic's accepted proposals have all been hunted (wave 2) and are in the ledger below; its result is attached in section 6 so you do not repeat it. Scope: src/wasi_python, scripts, release, recipes, .github/workflows, build/artifacts; tests/harness only where a release verdict depends on it. For a `missing_unit` give `path#symbol`-style surface and boundary refs and exact `FILE.md#Block name` references. This is the {kind} critic: `stop` is true only if you accept no missing units and no reassignments.

## 2. Architecture summary (verbatim)

{arch}

## 3. The coverage ledger (semantic fields, checks abridged, hardening notes attached)

```json
{json.dumps(slim, indent=1)}
```

## 4. Candidate fingerprints and their Phase 3 decisions

```json
{json.dumps(cands, indent=1)}
```

## 5. `uncovered` leads returned by hunters and their resolution

```json
{json.dumps(unc, indent=1)}
```

## 6. Previous critic result(s)

```json
{json.dumps(prior, indent=1)}
```
"""
open(f"{root}/brief.md","w",encoding="utf-8").write(brief); print(cid, len(brief.split()), "words")
