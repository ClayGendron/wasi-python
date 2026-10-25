import subprocess, sys
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/v01-cache-swap/scratch"
cmd = ("ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin "
       f"HOME={S}/home TMPDIR={S}/tmp WASI_PYTHON_CACHE={S}/cache "
       "/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' "
       "./.venv/bin/python -I "
       f"{S}/evidence/v01_swap_harness.py {S}/work/swap {sys.argv[1]}")
r = subprocess.run(["/bin/sh", "-c", cmd], capture_output=True, text=True, timeout=120)
open(f"{S}/evidence/v01_swap_run.log", "w").write(
    f"# macOS {sys.platform} arm64; wrapper: {cmd}\n# exit {r.returncode}\n" + r.stdout
    + ("\n# stderr (last 2000 chars)\n" + r.stderr[-2000:] if r.stderr else ""))
print(r.returncode)
