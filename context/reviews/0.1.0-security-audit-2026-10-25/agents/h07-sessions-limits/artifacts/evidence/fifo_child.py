# The child: one run() whose guest opens a named pipe in a read-only grant, deadline 1 s.
import json, sys, time
import wasi_python
from wasi_python import Grant
grant_dir, mode = sys.argv[1], sys.argv[2]
code = {"read": "open('/data/pipe','rb').read(1)",
        "plain": "print(open('/data/plain.txt').read())",
        "stat": "import os; print(os.stat('/data/pipe'))"}[mode]
t = time.monotonic()
print("start", flush=True)
c = wasi_python.run(["-c", code], grants=[Grant(grant_dir, "/data")], deadline_s=1.0)
print(json.dumps({"mode": mode, "wall_s": round(time.monotonic() - t, 3), "exit": c.exit_code,
                  "trapped": c.trapped, "stdout": c.stdout.decode()[-200:],
                  "stderr": c.stderr.decode()[-300:]}), flush=True)
