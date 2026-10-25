# The child: a guest opens a named pipe in a read-only grant; the embedder sets `cancel` after
# 2 s (run), or calls close() after 2 s (Session). Progress lines are flushed as they happen.
import json, sys, time, threading
import wasi_python
from wasi_python import Grant, Session
grant_dir, mode = sys.argv[1], sys.argv[2]
code = "open('/data/pipe','rb').read(1)"
t = time.monotonic()
def say(**kw):
    kw["t"] = round(time.monotonic() - t, 2); print(json.dumps(kw), flush=True)
if mode == "cancel":
    ev = threading.Event()
    threading.Timer(2.0, lambda: (ev.set(), say(event="cancel set"))).start()
    c = wasi_python.run(["-c", code], grants=[Grant(grant_dir, "/data")], deadline_s=1.0, cancel=ev)
    say(event="run returned", trapped=c.trapped)
elif mode == "session":
    s = Session(grants=[Grant(grant_dir, "/data")], deadline_s=1.0, shutdown_s=0)
    say(event="session open")
    def closer():
        time.sleep(2.0); say(event="close() called"); s.close(); say(event="close() returned")
    threading.Thread(target=closer, daemon=True).start()
    c = s.run(code)
    say(event="turn returned", trapped=c.trapped)
