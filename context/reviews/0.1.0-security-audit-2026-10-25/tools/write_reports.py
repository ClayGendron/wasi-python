"""Parent-side Phase 6: derive REPORT.md, FINDINGS-DETAIL.md and NEEDS-VALIDATION.md from the final records and the ledger."""
import json, os, re
from collections import Counter
OUT=os.path.expanduser("~/security-audit-skill/wasi_python/run-1")
F=json.load(open(f"{OUT}/findings.json")); L=json.load(open(f"{OUT}/coverage-ledger.json"))
meta=json.load(open(f"{OUT}/run-metadata.json")); summ=json.load(open(f"{OUT}/summary.json"))
dec=json.load(open(f"{OUT}/decisions.json")); p5=json.load(open(f"{OUT}/phase5.json"))
critics=[c for c in ("c01-critic","c02-critic","c03-critic","c04-final-clean") if os.path.exists(f"{OUT}/agents/{c}/scratch/result.json")]
agents=sorted(d for d in os.listdir(f"{OUT}/agents") if os.path.isdir(f"{OUT}/agents/{d}"))
recon=4
confirmed=[r for r in F if r["verdict"]=="confirmed"]; needs=[r for r in F if r["verdict"]=="needs_validation"]; rejected=[r for r in F if r["verdict"]=="rejected"]
counts=Counter(u["status"] for u in L)
sev_rank={"critical":0,"high":1,"medium":2,"low":3,"informational":4}
confirmed.sort(key=lambda r:(sev_rank[r["severity"]["overall_severity"]], r["fingerprint"]))
def short(s,n=160): return s if len(s)<=n else s[:n-1]+"…"
def boundary_of(fp):
    us=[u for u in L if fp in u.get("result_fingerprints",[])]
    return "; ".join(u["boundary"].split(";")[0][:110] for u in us) or "—"
def trace_md(r):
    return "\n".join(f"   {i+1}. `{t['file']}:{t['line']}` ({t['kind']}, {t['scope']}): {t['description']}" for i,t in enumerate(r["trace"]))
def evidence_md(r):
    return "\n".join(f"   - `{e['file']}:{e['line']}`: {e['description']}" for e in r["evidence"])
def conds_md(r):
    return "\n".join(f"   - {c['kind']}: {c['description']}" for c in r["conditions"])
def code_block(s, lang=""):
    fence="```" if "```" not in s else "````"
    return f"{fence}{lang}\n{s.rstrip()}\n{fence}"

# ---------- REPORT.md ----------
R=[]
R.append("# Security audit report: wasi_python (run-1)\n")
R.append(f"Date: 2026-10-25 (started 2026-10-24). Skill: `security-audit` (cloudflare/security-audit-skill, vendored under `.agents/skills/`). Profile: **{meta['profile']}**. Budget: none set. Agents spent: {len(agents)+recon} invocations ({recon} reconnaissance, {sum(1 for a in agents if a.startswith('h'))} hunters, {sum(1 for a in agents if a.startswith('v'))} candidate verifiers, {sum(1 for a in agents if a.startswith('r'))} record verifiers, {sum(1 for a in agents if a.startswith('c'))} coverage critics), every subagent on Opus at the owner's request.\n")
R.append("## 1. Run parameters\n")
R.append(f"- **Source ref:** `{meta['source_ref']['commit']}` on branch `{meta['source_ref']['branch']}`, worktree dirty. {meta['source_ref']['dirty_note']}")
R.append(f"- **Scope:** {', '.join('`'+p+'`' for p in meta['scope_paths'])}. Out of scope: {', '.join('`'+p+'`' for p in meta['out_of_scope_paths'])}.")
R.append("- **Execution statement:** source review plus bounded local execution only. Every target-controlled run (the runner through the project's own `.venv` Python with `-I`, guests inside wasmtime) was wrapped in an empty allowlisted environment, `sandbox-exec` denying the network, CPU, file-size and descriptor rlimits, with `HOME`, `TMPDIR` and the module cache redirected into the agent's scratch, and a wall-clock bound from a trusted driver. **Two controls the skill asks for could not be enforced on this macOS host: a read-only mount of the target and a memory rlimit.** Every local check says so. No deployed endpoint, no third-party host and no release or shared state was touched; read-only `gh` GET calls against the project's own repository were used, and the project's own v0.1.0 release assets were downloaded once, read-only, for one unit. No target file was edited.")
R.append("- **Prior runs:** none. The project's own reviews under `context/reviews/` (the 0.1.0 security review of 2026-10-21 in particular) were read as background and are not a compatible prior ledger; nothing was carried or excluded on their account.")
R.append(f"- **Coverage loop:** three hunter waves (12 + 1 reassigned hunter; 4; 1), a post-wave critic after each, and a distinct final-clean critic. Critic results: wave 1 proposed 4 units and resolved 3 of 6 `uncovered` leads as already covered; wave 2 proposed 1 unit; wave 3 proposed none; the final-clean critic: see section 7.")
R.append("- **Deferred coverage (partial pass):** two units are `deferred` and make no coverage claim: the sessions-and-call-isolation unit and the limits unit (deadline, fuel, memory, output, open-file and tool budgets as enforced by the runner). Two hunters ran their checks, but neither could deliver a structured result: each final write, and then the parent's own attempt to transcribe one, was stopped by a safety classifier. Their evidence files are retained read-only under `agents/h07-sessions-limits/artifacts/evidence/` and `agents/h13-sessions-limits/artifacts/evidence/` for the owner to read directly. **This report is therefore a partial pass over those two units**, and one lead among that evidence is not represented in `findings.json`. Everything else below is complete coverage as the ledger states it.")
R.append("- **Out of scope by design:** `context/`, `docs/` and `tests/` except where a release verdict depends on `tests/harness` (one unit).\n")
R.append("## 2. Security posture\n")
R.append("The sandbox's core promises held under adversarial review. Across 17 covered units and 135 checks (66 of them executed), no path was found from a guest to a host file outside its grants, to host memory, to the network or to a host process; the two shipped binaries import exactly the 42 WASI preview1 functions plus the one door; the stdlib zip carries no start-up hook, link or installer; code planted in a reused root did not run on either binary under defaults; the release workflow's artifact handoff, tag-on-main check and attestation bind the published assets to the accepted set byte for byte; every build input is verified against the in-repo pin table before use; and the runner's own WASI shadows (file calls, directory listing, rename guard, poll) kept every crafted pointer inside guest memory.\n")
R.append("Three confirmed findings and one unresolved lead survived independent verification. All three confirmed findings are **low** overall severity: each needs an uncommon embedder configuration, and none escapes the sandbox. Two break explicit documented guarantees inside the embedder's process (a tool-registry keyword that a guest can override; an environment key that lets planted code run in a later call). The third is an upstream wasmtime 49.0.0 defect that the shipped binaries reach: the fuel cap under-counts C++ work that ends in a caught exception, so fuel alone does not bound CPU until the pin's floor moves past 49.0.1. The unresolved lead concerns the module cache being checked by name and opened by path, which matters only when a lower-trust user owns an ancestor of the default cache folder. The hunters also returned 66 hardening notes, several of which correct the project's own advisory memo of 2026-10-18.\n")
R.append("## 3. Confirmed findings\n")
R.append("| Severity | Title | Affected boundary | Observed result |")
R.append("|---|---|---|---|")
for r in confirmed:
    R.append(f"| {r['severity']['overall_severity']} (impact {r['severity']['impact']['score']}, likelihood {r['severity']['likelihood']['score']}) | {r['title']} | {boundary_of(r['fingerprint'])} | {short(r['execution']['observed_result'],220)} |")
R.append("")
for i,r in enumerate(confirmed,1):
    R.append(f"### 3.{i} {r['title']}\n")
    R.append(f"- **Fingerprint:** `{r['fingerprint']}`")
    R.append(f"- **Severity:** {r['severity']['overall_severity']} overall. Likelihood {r['severity']['likelihood']['score']}: {r['severity']['likelihood']['reason']} Impact {r['severity']['impact']['score']}: {r['severity']['impact']['reason']}")
    R.append(f"- **Confidence:** {r['confidence']['score']}. {r['confidence']['reason']}")
    R.append(f"- **Lower-trust principal:** {r['execution']['attacker_perspective']}")
    R.append(f"- **Description:** {r['description']}")
    R.append(f"- **Root cause:** {r['root_cause']}")
    R.append(f"- **Intended behaviour:** {r['intended_behavior']}")
    R.append(f"- **Source location (trace):**\n{trace_md(r)}")
    R.append(f"- **Conditions:**\n{conds_md(r)}")
    R.append(f"- **Reproduction (target-native, bounded):** see FINDINGS-DETAIL.md §{i}. Observed: {r['execution']['observed_result']}")
    R.append(f"- **Smallest source fix:** {r['remediation']['strategy']}")
    R.append("")
R.append("## 4. Needs validation\n")
R.append("These are source-grounded leads whose decisive fact is outside what this run could observe. They carry no severity and are not confirmed vulnerabilities.\n")
R.append("| Title | Repository trace | Exact blocker | Bounded local next step | Owner-observed check |")
R.append("|---|---|---|---|---|")
for r in needs:
    tr=" → ".join(f"`{t['file']}:{t['line']}`" for t in r["trace"])
    R.append(f"| {r['title']} | {tr} | {short(r['blockers'][0],260)} | {short(r['validation_plan'].get('local',''),260)} | {short(r['validation_plan'].get('deployment',''),260)} |")
R.append("\nFull text in NEEDS-VALIDATION.md.\n")
if rejected:
    R.append("Rejected candidates (retained so later runs do not repeat them): " + ", ".join(f"`{r['fingerprint']}`" for r in rejected) + "\n")
R.append("## 5. Hardening notes\n")
R.append("Non-finding observations the hunters returned: a missing defence, a stale document, or a difference from an upstream answer with no demonstrated boundary violation. Grouped by area; each is the hunter's own text.\n")
groups={"Release workflow and CI":["h10-ci","h16-release-assets"],"Build inputs and the wheel":["h11-build"],"Shipped binaries and the stdlib zip":["h12-binary","h17-eh-advisories","h18-gc-exnref"],"Module cache and artifact set":["h04-loader"],"Door and tools":["h05-door","h06-tools"],"Filesystem, private folders and roots":["h01-fs-paths","h03-private-dirs","h09-cli"],"Guest memory and the runner's WASI shadows":["h02-fs-memory","h14-poll-oneoff"],"Environment and third-party loaders":["h15-env-loaders"],"Process integrity":["h08-process"]}
hard=summ["hardening"]
for g,ags in groups.items():
    items=[h for h in hard if h["agent"] in ags]
    if not items: continue
    R.append(f"### {g}\n")
    for h in items: R.append(f"- {h['note']}")
    R.append("")
R.append("### Positive patterns worth keeping\n")
R.append("- Every root and grant is walked component by component with no-follow opens from a held descriptor, links in user-writable folders are refused, and the preopen's inode identity is re-checked after wasmtime opens it (`src/wasi_python/_platform.py`, `_places.py`).")
R.append("- Every WASI call the runner serves masks each guest pointer to 32 bits and checks it against the memory size read at entry before any read or write; the door re-reads the memory size after `host_alloc`; padding bytes are written as zeros (`_fs_memory.py`, `_call.py`).")
R.append("- The guest's interpreter starts isolated: `site` off, only the stdlib zip on `sys.path`, `PYTHON*` variables ignored, `safe_path` on; planted `sitecustomize`, `.pth`, `pyvenv.cfg` and stdlib shadows never ran (`recipes/reactor_main.c`).")
R.append("- Tool frames are admitted by length before being read, parsed by a bounded JSON parser, validated against a closed schema, and gated fail-closed; a plain partial's bound keyword is refused at registration and per frame (`_tool_host.py`, `tools.py`).")
R.append("- Every build input is pinned by SHA-256 in the repository and re-verified in the step that extracts it; the carried patches were read in full and change only what their names say; tools install only from hashed wheels offline.")
R.append("- The release workflow has `permissions: {}` at the top, every action pinned by commit SHA, no `${{ }}` inside any `run:` script, artifact handoff by numeric id with digest mismatch as an error, two rebuilds that must agree byte for byte, a tag-on-main check, and an attestation whose subjects are exactly the published assets; the published v0.1.0 assets equal the accepted set and repack deterministically.\n")
R.append("## 6. Coverage summary\n")
R.append(f"- Units: {len(L)} ({counts.get('covered',0)} covered, {counts.get('candidate',0)} candidate, {counts.get('deferred',0)} deferred, {counts.get('blocked',0)} blocked). Checks: {summ['checks']} ({summ['local_checks']} local with promoted evidence, the rest source).")
R.append("- Waves: wave 1 seeded 18 units from reconnaissance; the post-wave critic added 4; wave 2's critic added 1; wave 3's critic accepted nothing; the final-clean critic's verdict is in section 7.")
R.append("- Deferred: the two units named in section 1 (sessions and call isolation; the limits as enforced by the runner). Their hunters' evidence is retained but no coverage is claimed.")
R.append("- Important exclusions: companion files for HTTP, client-side, RPC and cloud were not selected (no such surface in the repository). `tests/` was read only where a release verdict depends on it. Windows and Linux code paths were read but not executed (macOS host).")
R.append("- Candidate validation: every ledger candidate has an independent Phase 3 decision and every retained record passed Phase 5; one record was promoted from `needs_validation` to `confirmed` in Phase 5 and, as the skill requires, rechecked by a further independent verifier before the promotion was applied.")
R.append("")
R.append("## 7. Final critic and run status\n")
final=json.load(open(f"{OUT}/agents/c04-final-clean/scratch/result.json")) if os.path.exists(f"{OUT}/agents/c04-final-clean/scratch/result.json") else None
if final is None:
    R.append("Final-clean critic: not yet recorded.")
else:
    R.append(f"Final-clean critic returned `stop: {str(final['stop']).lower()}` with {len(final['missing_units'])} missing units and {len(final['reassign_ids'])} reassignments.")
R.append(f"\nRun status: **{meta['run_status']}**" + (f" ({meta.get('incomplete_reason','')})" if meta.get('incomplete_reason') else "") + ". Artifacts: `findings.json` (validated), `coverage-ledger.json` (validated), `architecture.md`, `run-metadata.json`, per-agent briefs and promoted evidence under `agents/`.\n")
open(f"{OUT}/REPORT.md","w",encoding="utf-8").write("\n".join(R))

# ---------- FINDINGS-DETAIL.md ----------
D=["# Findings detail: confirmed records (medium, high, critical impact)\n","Each section copies the final record's source path and target-neutral local reproduction. Dummy principals only; nothing here is live-probe guidance.\n"]
k=0
for r in confirmed:
    if sev_rank[r["severity"]["impact"]["score"]]>sev_rank["medium"] and sev_rank[r["severity"]["overall_severity"]]>sev_rank["medium"]:
        continue
    k+=1
    D.append(f"## {k}. {r['title']}\n")
    D.append(f"Fingerprint `{r['fingerprint']}`. Overall severity {r['severity']['overall_severity']}; impact {r['severity']['impact']['score']}; likelihood {r['severity']['likelihood']['score']}.\n")
    D.append("### Ordered trace\n"+trace_md(r)+"\n")
    D.append("### Evidence\n"+evidence_md(r)+"\n")
    D.append(f"### Principal and affected resource\n- Attacker: {r['execution']['attacker_perspective']}\n- Invariant violated: {r['intended_behavior']}\n")
    D.append("### Native input and bounded instructions\n")
    for j,p in enumerate(r["execution"]["payloads"],1):
        D.append(f"Payload {j}:\n\n"+code_block(p)+"\n")
    D.append("\n".join(f"{j}. {s}" for j,s in enumerate(r["execution"]["instructions"],1))+"\n")
    D.append(f"### Observed output\n{r['execution']['observed_result']}\n")
    D.append("### Conditions and containment\n"+conds_md(r)+"\n")
    D.append(f"### Remediation and regression case\n{r['remediation']['strategy']}\n")
    for c in r["remediation"].get("code_changes",[]):
        D.append(f"Proposed change to `{c['file_name']}`:\n\n"+code_block(c["fixed_code"],"python")+"\n")
open(f"{OUT}/FINDINGS-DETAIL.md","w",encoding="utf-8").write("\n".join(D))

# ---------- NEEDS-VALIDATION.md ----------
N=["# Needs validation: unresolved leads\n","Prioritized leads with a complete source trace whose decisive fact lies outside this run's observation. No severity is assigned; none is a confirmed vulnerability. Plans are bounded local fixtures or owner-observed facts, never live probing.\n"]
for i,r in enumerate(needs,1):
    N.append(f"## {i}. {r['title']}\n")
    N.append(f"Fingerprint `{r['fingerprint']}`.\n")
    N.append(f"### Description\n{r['description']}\n")
    N.append(f"### Claimed root cause\n{r['claimed_root_cause']}\n")
    N.append("### Source trace\n"+trace_md(r)+"\n")
    N.append("### Verified evidence\n"+evidence_md(r)+"\n")
    N.append("### Exact blockers\n"+"\n".join(f"- {b}" for b in r["blockers"])+"\n")
    N.append(f"### Affected boundary\n{boundary_of(r['fingerprint'])}\n")
    vp=r["validation_plan"]
    if vp.get("local"): N.append(f"### Bounded local plan\n{vp['local']}\n")
    if vp.get("deployment"): N.append(f"### Owner-observed deployment check\n{vp['deployment']}\n")
open(f"{OUT}/NEEDS-VALIDATION.md","w",encoding="utf-8").write("\n".join(N))
print("reports written:", {f: len(open(f"{OUT}/{f}").read().split()) for f in ("REPORT.md","FINDINGS-DETAIL.md","NEEDS-VALIDATION.md")})
