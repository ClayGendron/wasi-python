import subprocess, sys
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/h02-fs-memory/scratch"
script = sys.argv[1]; log = sys.argv[2]
cmd = ("ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin "
       f"HOME={S}/home TMPDIR={S}/tmp WASI_PYTHON_CACHE={S}/cache "
       "/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' "
       f"./.venv/bin/python -I {script} {S}")
with open(log, "w") as f:
    p = subprocess.run(["/bin/sh", "-c", cmd], stdout=f, stderr=subprocess.STDOUT, timeout=240, cwd=S)
print("exit", p.returncode)
