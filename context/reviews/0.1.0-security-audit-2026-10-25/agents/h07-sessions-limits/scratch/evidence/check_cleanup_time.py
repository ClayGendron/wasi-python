# How long run() takes after the deadline when the guest filled its private root with empty
# files and folders: the cleanup's cost against the deadline. Small: 2 s of creation.
import json, time, os, tempfile
import wasi_python
code = ("import os\nn=0\nos.makedirs('/w', exist_ok=True)\n"
        "while True:\n d=f'/w/{n//500}'\n"
        " if n%500==0: os.mkdir(d)\n open(f'{d}/{n}','w').close(); n+=1\n"
        " if n%5000==0: print(n, flush=True)\n")
t = time.monotonic()
c = wasi_python.run(["-c", code], root=True, deadline_s=2.0)
wall = time.monotonic() - t
lines = c.stdout.decode().split()
left = [e for e in os.listdir(tempfile.gettempdir()) if e.startswith("wasi-python-root-")]
print(json.dumps({"deadline_s": 2.0, "wall_s": round(wall, 3), "trapped": c.trapped,
                  "files_made_at_least": int(lines[-1]) if lines else 0, "roots_left": left}))
