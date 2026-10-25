import subprocess, sys
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/v02-class-partial/scratch"
cmd = ("ulimit -t 300 -f 4000000 -n 4096; /usr/bin/env -i PATH=/usr/bin:/bin HOME=%s/home TMPDIR=%s/tmp WASI_PYTHON_CACHE=%s/cache "
       "/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' ./.venv/bin/python -I %s/evidence/v02_class_ctor_partial.py") % (S, S, S, S)
r = subprocess.run(["/bin/sh", "-c", cmd], capture_output=True, timeout=240)
open(S + "/evidence/v02_class_ctor_partial.out.json", "wb").write(r.stdout)
open(S + "/evidence/v02_class_ctor_partial.err.txt", "wb").write(r.stderr + b"\nexit=%d\n" % r.returncode)
print(r.returncode)
