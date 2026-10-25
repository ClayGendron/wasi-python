import subprocess, sys
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/v05-eh-fuel-recheck/scratch"
cmd = ("ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=%s/home TMPDIR=%s/tmp "
       "WASI_PYTHON_CACHE=%s/cache /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' "
       "./.venv/bin/python -I %s " % (S, S, S, sys.argv[1])) + " ".join(sys.argv[2:])
p = subprocess.run(["/bin/bash", "-c", cmd], capture_output=True, text=True, timeout=600)
sys.stdout.write(p.stdout); sys.stderr.write(p.stderr[-2000:]); print("rc", p.returncode)
