# Trusted driver: runs one wrapped command with a wall-clock bound; prints rc, stdout, stderr.
import subprocess, sys
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/v04-eh-fuel/scratch"
T = "."
timeout = float(sys.argv[1]); cmd = sys.argv[2:]
wrapped = ("ulimit -t 300 -f 4000000 -n 4096; exec /usr/bin/env -i PATH=/usr/bin:/bin "
           f"HOME={S}/home TMPDIR={S}/tmp WASI_PYTHON_CACHE={S}/cache "
           "/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' " + " ".join(cmd))
try:
    p = subprocess.run(["/bin/sh", "-c", wrapped], capture_output=True, text=True, timeout=timeout)
    print("rc", p.returncode); print(p.stdout[-20000:]); print("stderr:", p.stderr[-3000:])
except subprocess.TimeoutExpired:
    print("TIMEOUT")
