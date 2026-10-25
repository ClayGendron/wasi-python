# Trusted driver: runs the child under the sandbox wrapper with a 20 s wall-clock bound.
import subprocess, sys, json, time
S = "context/reviews/0.1.0-security-audit-2026-10-25/agents/h07-sessions-limits/scratch"
wrap = ["/usr/bin/env", "-i", "PATH=/usr/bin:/bin", f"HOME={S}/home", f"TMPDIR={S}/tmp",
        f"WASI_PYTHON_CACHE={S}/cache", "/usr/bin/sandbox-exec", "-p",
        "(version 1)(allow default)(deny network*)",
        "./.venv/bin/python", "-I", f"{S}/evidence/fifo_child2.py",
        f"{S}/fifo_grant"]
for mode in sys.argv[1:]:
    t = time.monotonic()
    try:
        p = subprocess.run(wrap + [mode], capture_output=True, timeout=20)
        print(json.dumps({"mode": mode, "driver_wall_s": round(time.monotonic()-t, 2), "killed": False,
                          "rc": p.returncode, "stdout": p.stdout.decode()[-600:], "stderr": p.stderr.decode()[-400:]}))
    except subprocess.TimeoutExpired as e:
        print(json.dumps({"mode": mode, "driver_wall_s": round(time.monotonic()-t, 2), "killed": True,
                          "stdout": (e.stdout or b"").decode()[-600:]}))
