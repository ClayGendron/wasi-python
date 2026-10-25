"""Parent-side: build a Phase 5 record-verifier brief. Usage: build_p5_briefs.py <verifier_id> <fingerprint>"""
import json, os, re, sys
SKILL = "./.agents/skills/security-audit"
OUT = os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
TARGET = "."
vid, fp = sys.argv[1], sys.argv[2]
assert re.match(r"^[a-z0-9][a-z0-9_-]{0,63}$", vid)
recs = [r for r in json.load(open(os.path.join(OUT, "findings.json"))) if r["fingerprint"] == fp]
assert len(recs) == 1; rec = recs[0]
dec = [d for d in json.load(open(os.path.join(OUT, "decisions.json"))) if d["fingerprint"] == fp][0]
val = open(os.path.join(SKILL, "VALIDATION-AND-REPORTING.md"), encoding="utf-8").read()
i = val.index("### Phase 5"); j = val.index("### Phase 6")
p5 = val[i:j]
schema = json.load(open(os.path.join(SKILL, "report-schema.json")))["items"]["oneOf"]
root = os.path.join(OUT, "agents", vid); os.makedirs(os.path.join(root, "scratch", "evidence"), exist_ok=True); os.makedirs(os.path.join(root, "artifacts"), exist_ok=True)
brief = f"""# Phase 5 record-verifier brief: {vid}

## 1. Instructions (verbatim from the skill)

{p5}
## 2. The final record to verify (verdict `{rec['verdict']}`, decided by Phase 3 verifier `{dec['verifier']}`; you did not hunt or validate it)

```json
{json.dumps(rec, indent=2)}
```

Evidence the earlier agents promoted (read-only): under `{OUT}/agents/*/artifacts/evidence/` (the hunter's and the Phase 3 verifier's folders; their ids appear in the record's execution instructions or can be found by listing that directory).

## 3. Execution boundary and paths

- Target root: `{TARGET}` (all record paths are repository-relative). Never edit a file under it; never run `uv sync`, plain `uv run`, the download or build scripts, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet.
- Your scratch (the only place you write): `{root}/scratch/`. If you re-run a check, wrap it as: `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME={root}/scratch/home TMPDIR={root}/scratch/tmp WASI_PYTHON_CACHE={root}/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' {TARGET}/.venv/bin/python -I <script under scratch>` with a `subprocess.run(timeout=...)` bound from a trusted driver; confirm `{TARGET}/build/lane.lock` is absent first; never point a writable grant or root at the target or a real cache; this platform cannot read-only mount the target.
- Return exactly one JSON object and no prose: `{{"decision":"verified","fingerprint":"{fp}"}}` or `{{"decision":"replace","reason":"...","record":{{...}}}}` where a replacement record matches its schema branch exactly (`additionalProperties: false`). Also write it to `{root}/scratch/result.json`. Non-material wording or line-number corrections are a `replace` with a reason that says they are non-material; a change of verdict, root cause, trace, execution input, observed result, impact or severity is material and must say so.

## 4. Schema branches (verbatim)

### confirmed
```json
{json.dumps(schema[0], indent=2)}
```
### needs_validation
```json
{json.dumps(schema[1], indent=2)}
```
### rejected
```json
{json.dumps(schema[2], indent=2)}
```
"""
open(os.path.join(root, "brief.md"), "w", encoding="utf-8").write(brief); print(vid, len(brief.split()), "words")
