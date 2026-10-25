import json, re, sys
brief = open('context/reviews/0.1.0-security-audit-2026-10-25/agents/r02-cache-swap/brief.md').read()
m = re.search(r"## 2\..*?```json\n(.*?)\n```", brief, re.S)
rec = json.loads(m.group(1))
rec["description"] = rec["description"].replace(
    " The verifier reproduced",
    " A guest is not the lower-trust principal here: the grant judge refuses a writable grant at, inside or above any module cache folder, ancestors included, so the remaining principal is another OS user (or process identity) that owns or can write an ancestor. The verifier reproduced")
for e in rec["evidence"]:
    if e["file"] == "docs/get-started/install.md":
        e["description"] = ("In the Windows paragraph, says cache_dir and $WASI_PYTHON_CACHE must name a folder only you can write and that 'the default, in your own profile, is one'; the page's one-line summary (line 64) says the first call caches 'where only you can write'. An assumption about the default that a process with another user's HOME breaks; not a declaration that HOME is trusted input.")
rec["evidence"].insert(3, {"file": "src/wasi_python/_places.py", "line": 297,
    "description": "_cache_chain gives every existing folder on each module cache's path to the grant judge, which refuses a writable grant at, inside or above it: ancestors are guarded against the guest, but their owner and writability by other OS users are never checked."})
rec["blockers"][0] = ("The cross-user case was not observed. This macOS machine lists a second local account (uid 502), but the audit holds no credentials for it and no non-interactive root, and running as another account on the owner's real machine is outside the execution boundary; uid 501 is in the admin group, so its own sudo with HOME kept would cross no boundary. The verifier's evidence uses one user in both roles, where the swapper already owns the cache folder and needs no race, so it shows the identity gap but not a crossed boundary.")
rec["blockers"][1] = rec["blockers"][1].replace(
    "so whether this host's sudo keeps HOME could not be read.",
    "and sudo -V run by a non-root user prints only versions (sudo 1.9.17p2), so whether this host's sudo keeps HOME could not be read; it would not settle the deployment question in any case.")
out = {"decision": "replace",
 "reason": "Non-material corrections; verdict, fingerprint, root cause, trace, observed results and validation plan unchanged. Source lines re-checked and accurate (_engines.py 85/178/217/222/228/233/237, _platform.py 534/545/556-577/564/1091, runner.py 115/130, _call.py 146). Blocker 1 said the machine offers one OS user; dscl lists a second account (uid 502), so the blocker is restated as no credentials, no non-interactive root, and the boundary forbids acting as another real account; it stays decisive. Blocker 2: sudo -V as non-root prints only versions and /etc/sudoers is 0440 root, so HOME-keeping is not answerable locally, and would not settle the deployment fact anyway. The install.md evidence is in the Windows paragraph, now said so. Added _places.py:297 evidence and one description sentence: guest grants above the cache are refused, so the lower-trust principal must be another OS user. Kept needs_validation rather than confirmed: with one user the swapper already owns the cache, so no boundary is crossed; the identity gap is demonstrated but a security result needs a distinct lower-trust owner of an ancestor, which was not demonstrated.",
 "record": rec}
s = json.dumps(out, ensure_ascii=False)
open('context/reviews/0.1.0-security-audit-2026-10-25/agents/r02-cache-swap/scratch/result.json','w').write(s)
print(s)
