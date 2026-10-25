import subprocess, sys
S = sys.argv[1]
cmd = ["/bin/sh", "-c", "ulimit -t 300 -f 4000000 -n 4096; exec /usr/bin/env -i PATH=/usr/bin:/bin "
       f"HOME={S}/home TMPDIR={S}/tmp WASI_PYTHON_CACHE={S}/cache /usr/bin/sandbox-exec -p "
       "'(version 1)(allow default)(deny network*)' ./.venv/bin/python -I "
       f"{S}/evidence/v03_check.py {S}"]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
open(f"{S}/evidence/v03_run.log", "w").write(r.stdout + "\n--stderr--\n" + r.stderr + f"\nrc={r.returncode}\n")
print(r.returncode)
