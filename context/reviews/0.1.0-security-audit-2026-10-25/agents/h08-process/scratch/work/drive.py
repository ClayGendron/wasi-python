import subprocess, sys
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/h08-process/scratch"
mode, limit = sys.argv[1], int(sys.argv[2])
cmd = ("ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin "
       f"HOME={S}/home TMPDIR={S}/tmp WASI_PYTHON_CACHE={S}/cache "
       "/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' "
       "./.venv/bin/python -I "
       f"{S}/evidence/{sys.argv[3] if len(sys.argv) > 3 else 'h08_checks.py'} {mode}")
try:
    r = subprocess.run(["/bin/sh", "-c", cmd], capture_output=True, text=True, timeout=limit)
    print(r.stdout); print("STDERR:", r.stderr[-3000:]); print("RC:", r.returncode)
except subprocess.TimeoutExpired as e:
    print("TIMEOUT", (e.stdout or b"")[-3000:] if e.stdout else "")
