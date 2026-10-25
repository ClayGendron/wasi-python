"""Trusted driver (h14-poll-oneoff): runs check_poll.py once per mode inside the brief's wrapper
(ulimit CPU/file/descriptors, env -i with allowlisted variables, sandbox-exec denying network),
with a wall-clock bound from subprocess.run(timeout=). The target is not read-only mounted
(macOS offers no such mount here); no grant or root points at the target."""
import subprocess, sys, time
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/h14-poll-oneoff/scratch"
PY = "./.venv/bin/python"
for mode, limit in (("A", 120), ("A-mounts", 120), ("B", 60), ("B-abs", 60), ("C", 30)):
    cmd = (f"ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME={S}/home "
           f"TMPDIR={S}/tmp WASI_PYTHON_CACHE={S}/cache /usr/bin/sandbox-exec -p "
           f"'(version 1)(allow default)(deny network*)' {PY} -I {S}/evidence/check_poll.py "
           f"{mode} {S}/evidence/check_poll_{mode}.json")
    t = time.monotonic()
    try:
        r = subprocess.run(["/bin/sh", "-c", cmd], capture_output=True, text=True, timeout=limit)
        print(f"[{mode}] rc={r.returncode} wall={time.monotonic()-t:.1f}s")
        print(r.stdout.strip()[-1500:]); print(r.stderr.strip()[-2500:])
    except subprocess.TimeoutExpired:
        print(f"[{mode}] TIMEOUT after {limit}s")
