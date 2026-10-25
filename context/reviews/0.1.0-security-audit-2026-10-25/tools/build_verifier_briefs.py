"""Parent-side: build a Phase 3 candidate-verifier brief for one candidate fingerprint.
Usage: build_verifier_briefs.py <verifier_id> <fingerprint>
"""
import json, os, re, sys
SKILL = "./.agents/skills/security-audit"
OUT = os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
TARGET = "."
sys.path.insert(0, os.path.join(OUT, "tools"))
from blocks import block  # noqa: E402

vid, fp = sys.argv[1], sys.argv[2]
assert re.match(r"^[a-z0-9][a-z0-9_-]{0,63}$", vid)
cands = json.load(open(os.path.join(OUT, "candidates.json")))
cand = [c for c in cands if c["fingerprint"] == fp]
assert len(cand) == 1, fp
cand = dict(cand[0]); hunter = cand.pop("_hunter")
ledger = json.load(open(os.path.join(OUT, "coverage-ledger.json")))
units = [u for u in ledger if fp in u.get("result_fingerprints", [])]
val = open(os.path.join(SKILL, "VALIDATION-AND-REPORTING.md"), encoding="utf-8").read()
def fenced(after):
    i = val.index(after); j = val.index("```text", i); k = val.index("\n```", j + 7)
    return val[j:k + 4] + "\n"
VERIFIER_PROMPT = fenced("#### Candidate-verifier prompt")
PROMOTION = fenced("Copy this promotion procedure verbatim into every candidate-verifier prompt")
schema = json.load(open(os.path.join(SKILL, "report-schema.json")))
branches = schema["items"]["oneOf"]
arch = open(os.path.join(OUT, "architecture.md"), encoding="utf-8").read()
# companion validation blocks for the linked units
blocks = []
seen = set()
for u in units:
    for b in u["selected_companion_blocks"]:
        f, name = b.split("#", 1)
        if name in ("Core discipline", "Validation rules") and b not in seen:
            seen.add(b); blocks.append(block(b))
root = os.path.join(OUT, "agents", vid)
os.makedirs(os.path.join(root, "scratch", "evidence"), exist_ok=True)
os.makedirs(os.path.join(root, "artifacts"), exist_ok=True)
unit_checks = [{"coverage_id": u["coverage_id"], "surface": u["surface"], "boundary": u["boundary"], "agent_id": u["agent_id"], "local_checks": u["local_checks"]} for u in units]
brief = f"""# Candidate-verifier brief: {vid}

## 1. Role and instructions (verbatim from the skill)

{VERIFIER_PROMPT}
{PROMOTION}
## 2. The candidate (from hunter `{hunter}`; `proposed_verdict` is the hunter's proposal, not a decision)

```json
{json.dumps(cand, indent=2)}
```

## 3. The linked coverage unit(s) and the hunter's checks (artifact paths are relative to `{OUT}`)

```json
{json.dumps(unit_checks, indent=2)}
```

## 4. Architecture facts (the run's architecture summary, verbatim)

{arch}

## 5. Companion validation blocks (verbatim)

{''.join(b + chr(10) for b in blocks)}
## 6. Execution boundary, paths, allowlist

- Target root: `{TARGET}` (all paths in your record are repository-relative to it). Never edit a file under it. Never run `uv sync`, plain `uv run`, `scripts/00_download.sh`, `scripts/build.sh` or `scripts/steps/*.sh`, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet; read-only `gh` GET calls against the project's own repository are allowed.
- Your scratch (the only place you write): `{root}/scratch/`. Parent-owned artifacts (you never write): `{root}/artifacts/`. Allowlist for promotion: regular files directly under `scratch/evidence/` named `*.txt`, `*.json`, `*.log` or `*.py`, at most 24 files, 512 KiB each, 8 MiB total; after you finish the parent promotes them to `artifacts/evidence/<name>`.
- Before any target-controlled execution confirm `{TARGET}/build/lane.lock` does not exist. Wrap every target-controlled run as:
  `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME={root}/scratch/home TMPDIR={root}/scratch/tmp WASI_PYTHON_CACHE={root}/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' {TARGET}/.venv/bin/python -I <script under scratch>` (make the three folders first; give each child a wall-clock bound with `subprocess.run(timeout=...)` from a trusted driver). This platform cannot enforce a read-only target mount or a memory rlimit; never point a writable grant or root at the target or at a real cache; say in the record's `execution.instructions` that the target was not read-only mounted. If a control you need cannot be enforced, do not execute; keep the exact blocker as `needs_validation`.
- You may read the hunter's evidence files under `{OUT}/agents/{hunter}/artifacts/evidence/` (read-only) and re-run its harness in your own scratch. A verifier-owned `local` check must cite a file you wrote under your own `scratch/evidence/`.
- Keep probes small and short (deadlines of a few seconds, small sizes).

## 7. Prior records with the same fingerprint

None (no prior run).

## 8. Result contract

Return exactly one JSON object and no surrounding prose: `{{"decision": "confirmed|needs_validation|rejected", "record": {{ ... }}}}` where `record` exactly matches the decision's branch below (`additionalProperties: false`; do not carry `proposed_verdict`, `_hunter` or any other wrapper field; `verdict` must equal `decision`). Also write the same object to `{root}/scratch/result.json`, writing it incrementally as you settle each part so a partial file exists if your final message is cut off. Use plain factual language.

### `confirmed` branch (verbatim)
```json
{json.dumps(branches[0], indent=2)}
```
### `needs_validation` branch (verbatim)
```json
{json.dumps(branches[1], indent=2)}
```
### `rejected` branch (verbatim)
```json
{json.dumps(branches[2], indent=2)}
```
"""
open(os.path.join(root, "brief.md"), "w", encoding="utf-8").write(brief)
print(vid, "brief", len(brief.split()), "words; units", len(units))
