import subprocess, sys
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/r03-class-partial/scratch"
cmd = ("ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin "
       f"HOME={S}/home TMPDIR={S}/tmp WASI_PYTHON_CACHE={S}/cache "
       "WASI_PYTHON_ARTIFACTS=./build/artifacts "
       "/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' "
       f"./.venv/bin/python -I {S}/evidence/r03_probe.py")
r = subprocess.run(["/bin/zsh", "-c", cmd], capture_output=True, timeout=240, cwd=f"{S}/tmp")
open(f"{S}/evidence/r03_probe.out.json", "wb").write(r.stdout)
open(f"{S}/evidence/r03_probe.err.txt", "wb").write(r.stderr + f"\nexit={r.returncode}".encode())
print(r.returncode)
