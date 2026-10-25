import subprocess, sys
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/h18-gc-exnref/scratch"
args = sys.argv[1:]
cmd = ("ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=%s/home TMPDIR=%s/tmp WASI_PYTHON_CACHE=%s/cache "
       "/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I %s/evidence/driver_exn_churn.py %s"
       % (S, S, S, S, " ".join(args)))
try:
    p = subprocess.run(["/bin/bash", "-c", cmd], capture_output=True, text=True, timeout=290)
    print("returncode", p.returncode)
    print(p.stdout[-5000:])
    print("host-stderr", p.stderr[-3000:])
except subprocess.TimeoutExpired as e:
    print("TIMEOUT", (e.stdout or b"")[-2000:] if e.stdout else "")
