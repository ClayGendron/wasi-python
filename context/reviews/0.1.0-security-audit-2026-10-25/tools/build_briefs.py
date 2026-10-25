"""Parent-side: assemble hunter briefs with verbatim blocks, create agent roots, mark units in_progress."""
import json, os, re, sys
SKILL = "./.agents/skills/security-audit"
OUT = os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
TARGET = "."

def load_blocks(fname):
    """Map block name -> verbatim text for a skill markdown file."""
    text = open(os.path.join(SKILL, fname), encoding="utf-8").read()
    lines = text.split("\n")
    blocks = {}
    cur = None; buf = []
    def flush():
        if cur is not None:
            blocks[cur] = "\n".join(buf).rstrip() + "\n"
    for ln in lines:
        m_bold = re.match(r"^\*\*([^*]+)\*\*(\s*\(subagent_type: `[a-z]+`\))?\s*$", ln)
        m_head = re.match(r"^##\s+(.+?)\s*(\([^)]*\))?\s*$", ln)
        if m_bold:
            flush(); cur = m_bold.group(1).strip(); buf = [ln]; continue
        if m_head:
            flush(); cur = m_head.group(1).strip(); buf = [ln]; continue
        if ln.startswith("#") or ln.startswith("> **"):
            flush(); cur = None; buf = []; continue
        if cur is not None:
            buf.append(ln)
    flush()
    return blocks

CACHE = {}
def block(ref):
    fname, name = ref.split("#", 1)
    if fname not in CACHE:
        CACHE[fname] = load_blocks(fname)
    b = CACHE[fname].get(name)
    if b is None:
        raise SystemExit(f"block not found: {ref}; have {sorted(CACHE[fname])[:50]}")
    return f"<!-- {ref} -->\n" + b

def section(path, start_pat, end_pat):
    t = open(os.path.join(SKILL, path), encoding="utf-8").read()
    s = t.index(start_pat); e = t.index(end_pat, s + len(start_pat))
    return t[s:e].rstrip() + "\n"

hunting = open(os.path.join(SKILL, "HUNTING.md"), encoding="utf-8").read()
def fenced_after(heading):
    i = hunting.index(heading)
    j = hunting.index("```text", i); k = hunting.index("\n```", j + 7)
    return hunting[j:k + 4] + "\n"
CORE_METHOD = fenced_after("#### Core hunting method")
PROMOTION = fenced_after("#### Promotion procedure")
CORE_VALIDATION = fenced_after("#### Core validation rules")
i = hunting.index("## Structured hunter result"); j = hunting.index("## Parent consolidation")
STRUCTURED = hunting[i:j].rstrip() + "\n"
schema = json.load(open(os.path.join(SKILL, "report-schema.json")))
branches = schema["items"]["oneOf"]
CONFIRMED = json.dumps(branches[0], indent=2); NEEDS = json.dumps(branches[1], indent=2)

ledger = json.load(open(os.path.join(OUT, "coverage-ledger.json")))
by_id = {u["coverage_id"]: u for u in ledger}
arch = open(os.path.join(OUT, "architecture.md"), encoding="utf-8").read()

assign = json.load(open(sys.argv[1]))  # {agent_id: [surface refs...]}
def find_unit(surface_ref, lifecycle=None):
    hits = [u for u in ledger if u["canonical_refs"]["surface"] == surface_ref]
    if len(hits) != 1:
        raise SystemExit(f"surface {surface_ref} matched {len(hits)} units")
    return hits[0]

owner_of = {}
for aid, surfaces in assign.items():
    for s in surfaces:
        owner_of[find_unit(s)["coverage_id"]] = aid

for aid, surfaces in assign.items():
    if not re.match(r"^[a-z0-9][a-z0-9_-]{0,63}$", aid): raise SystemExit(aid)
    root = os.path.join(OUT, "agents", aid)
    os.makedirs(os.path.join(root, "scratch", "evidence"), exist_ok=True)
    os.makedirs(os.path.join(root, "artifacts"), exist_ok=True)
    units = [find_unit(s) for s in surfaces]
    sel_blocks = []; seen = set()
    for u in units:
        for b in [u["ordinary_attack_class_block"]] + u["selected_companion_blocks"]:
            if b and b not in seen:
                seen.add(b); sel_blocks.append(b)
    excluded = []
    for u in units:
        for e in u["excluded_blocks"]:
            excluded.append(f"- `{e['block']}`: {e['reason']}")
    peers = sorted(cid for cid, o in owner_of.items() if o != aid)
    unit_json = json.dumps([{k: u[k] for k in ["coverage_id", "canonical_refs", "surface", "boundary", "subsystem", "attack_class", "starting_paths", "ordinary_attack_class_block", "selected_companion_blocks", "excluded_blocks"] + (["lifecycle"] if "lifecycle" in u else [])} for u in units], indent=2)
    brief = f"""# Hunter brief: {aid}

## 1. Role
You are a security hunter. Your goal is to find source-grounded security invariant failures in your assigned coverage units of the target repository at `{TARGET}`, and you must return exactly one JSON object matching the structured-result contract at the end of this brief (section 9).

## 2. Architecture summary (verbatim)

{arch}

## 3. Your assigned coverage units

Agent id: `{aid}`. Target root: `{TARGET}` (all paths in your result are repository-relative to it).

```json
{unit_json}
```

## 4. Selected attack-class blocks (verbatim)

{''.join(block(b) + chr(10) for b in sel_blocks)}
## 5. Excluded blocks and reasons

{chr(10).join(excluded)}

## 6. Core hunting method and promotion procedure

{CORE_METHOD}
{PROMOTION}
## 7. Core validation rules

{CORE_VALIDATION}
## 8. Exclusions and peers

No prior-run confirmed records are carried, so nothing is excluded on that account. Documented "not protected" behaviour in `docs/explanation/security-model.md:67-109` is intended behaviour: report it only if you show an effect stronger than documented. The project's own earlier review `context/reviews/0.1.0-security-review-2026-10-21.md` is background you may read; do not re-report its closed findings (its H1 and H2 were fixed by specs 113 and 114).

Peer-owned coverage IDs you must not duplicate (return an unexpected boundary under `uncovered` instead):
{chr(10).join('- `' + p + '`' for p in peers)}

## 9. Paths, sandbox, allowlist, and the result contract

- Your scratch directory (the only place you may write): `{root}/scratch/`
- Your retained artifacts directory (parent-owned; you never write it): `{root}/artifacts/`
- Promotion allowlist: regular files directly under `scratch/evidence/` named `*.txt`, `*.json`, `*.log` or `*.py`, at most 24 files, 512 KiB each, 8 MiB in total. After you finish, the parent promotes them to `artifacts/evidence/<name>`; a `local` check's `artifact` field must name `agents/{aid}/artifacts/evidence/<name>` for a file you wrote to `scratch/evidence/<name>`.
- Never edit any file under the target. Never run `uv sync`, plain `uv run`, `scripts/00_download.sh`, `scripts/build.sh` or any `scripts/steps/*.sh`, `release/set_key.py`, `gh workflow run`, `git push`, `pytest --accept*`, or anything writing under `context/`. Never download from the internet. Read-only `gh` GET calls against the project's own repository are allowed.
- Target-controlled execution (the runner through Python, a guest inside wasmtime, a pytest node id) is allowed only as a bounded local check, wrapped like this, with the three directories under your scratch:
  `ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME={root}/scratch/home TMPDIR={root}/scratch/tmp WASI_PYTHON_CACHE={root}/scratch/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' {TARGET}/.venv/bin/python -I <your script under scratch>`
  (create `scratch/home`, `scratch/tmp`, `scratch/cache` first). Use `subprocess.run(..., timeout=...)` from a trusted driver when a step needs a wall-clock bound. This platform cannot enforce a read-only target mount or a memory rlimit: the project's own memory cap bounds the guest, and you must not point any writable grant or root at the target. Record in each local check that the target was not read-only mounted. If a check needs a control you cannot enforce, do not run it: return `needs_validation` with that blocker.
- Pytest: use `{TARGET}/.venv/bin/python -I -m pytest <nodeid> -p no:cacheprovider --progress-latest {root}/scratch/latest.json` inside the same wrapper; never a whole tier.
- Keep disk use small; delete large files you create under scratch before finishing.

Also write your final JSON object to `{root}/scratch/result.json` (exact same content as you return), so the parent has a copy if the hand-back is truncated.

{STRUCTURED}
### `confirmed` branch of report-schema.json (verbatim)

```json
{CONFIRMED}
```

### `needs_validation` branch of report-schema.json (verbatim)

```json
{NEEDS}
```
"""
    with open(os.path.join(root, "brief.md"), "w", encoding="utf-8") as f:
        f.write(brief)
    for u in units:
        u["status"] = "in_progress"; u["agent_id"] = aid; u["wave"] = 1
        u.setdefault("bookkeeping", {})
    print(aid, len(units), "units; brief", len(brief.split()), "words")

with open(os.path.join(OUT, "coverage-ledger.json"), "w", encoding="utf-8") as f:
    json.dump(ledger, f, indent=2, ensure_ascii=False); f.write("\n")
