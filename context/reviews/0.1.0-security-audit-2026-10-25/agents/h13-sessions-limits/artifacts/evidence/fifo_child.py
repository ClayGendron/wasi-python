# Child: one embedder call whose guest opens a named pipe (FIFO) that the trusted driver made in a
# granted folder. Every call uses deadline_s=1.0. Progress lines are flushed as they happen, so
# the driver sees how far the child got before its wall-clock bound killed it.
import asyncio, json, os, sys, threading, time
import wasi_python
from wasi_python import Grant, Session

folder, mode = sys.argv[1], sys.argv[2]
T0 = time.monotonic()
def say(**kw):
    kw["t"] = round(time.monotonic() - T0, 2)
    print(json.dumps(kw), flush=True)

RO = [Grant(folder, "/data")]
READ = "import os; fd=os.open('/data/pipe', os.O_RDONLY); print('opened', flush=True); print(os.read(fd,1))"
def done(c):
    return dict(exit=c.exit_code, trapped=c.trapped, out=c.stdout.decode()[-80:], err=c.stderr.decode()[-160:])

say(event="start", mode=mode)
if mode == "plain":
    c = wasi_python.run(["-c", "print(open('/data/plain.txt').read())"], grants=RO, deadline_s=1.0)
    say(event="run returned", **done(c))
elif mode == "stat":
    c = wasi_python.run(["-c", "import os; print(os.stat('/data/pipe').st_mode)"], grants=RO, deadline_s=1.0)
    say(event="run returned", **done(c))
elif mode in ("open", "writer_late", "writer_holds"):
    c = wasi_python.run(["-c", READ], grants=RO, deadline_s=1.0)
    say(event="run returned", **done(c))
elif mode == "open_nonblock":
    code = "import os; fd=os.open('/data/pipe', os.O_RDONLY|os.O_NONBLOCK); print('opened')"
    c = wasi_python.run(["-c", code], grants=RO, deadline_s=1.0)
    say(event="run returned", **done(c))
elif mode == "fuel":
    c = wasi_python.run(["-c", READ], grants=RO, deadline_s=1.0, fuel=10**9)
    say(event="run returned", **done(c))
elif mode == "cancel":
    ev = threading.Event()
    threading.Timer(2.0, lambda: (ev.set(), say(event="cancel set"))).start()
    c = wasi_python.run(["-c", READ], grants=RO, deadline_s=1.0, cancel=ev)
    say(event="run returned", **done(c))
elif mode == "sigint":
    try:
        c = wasi_python.run(["-c", READ], grants=RO, deadline_s=1.0)
        say(event="run returned", **done(c))
    except KeyboardInterrupt:
        say(event="KeyboardInterrupt raised")
elif mode == "session_close":
    s = Session(grants=RO, deadline_s=1.0, shutdown_s=0)
    say(event="session open")
    def closer():
        time.sleep(2.0); say(event="close() called"); s.close(); say(event="close() returned")
    threading.Thread(target=closer, daemon=True).start()
    c = s.run(READ)
    say(event="turn returned", **done(c))
elif mode == "wait_for":
    async def main():
        try:
            c = await asyncio.wait_for(wasi_python.run_async(["-c", READ], grants=RO, deadline_s=1.0), 2.0)
            say(event="run_async returned", **done(c))
        except asyncio.TimeoutError:
            say(event="wait_for raised TimeoutError")
    asyncio.run(main())
elif mode == "pool":
    import dataclasses
    wasi_python.set_defaults(dataclasses.replace(wasi_python.defaults(), async_workers=1))
    async def main():
        a = asyncio.ensure_future(wasi_python.run_async(["-c", READ], grants=RO, deadline_s=1.0))
        await asyncio.sleep(0.5)
        b = asyncio.ensure_future(wasi_python.run_async(["-c", "print('B ran')"], deadline_s=1.0))
        finished, _ = await asyncio.wait([b], timeout=6.0)
        say(event="after 6 s", other_call_done=bool(finished), fifo_call_done=a.done())
        os._exit(0)
    asyncio.run(main())
elif mode == "exit_hang":
    t = threading.Thread(target=lambda: wasi_python.run(["-c", READ], grants=RO, deadline_s=1.0), daemon=True)
    t.start(); t.join(2.0)
    say(event="main thread returning; worker alive", alive=t.is_alive())
elif mode == "exit_pool":
    import concurrent.futures
    ex = concurrent.futures.ThreadPoolExecutor(1)
    f = ex.submit(wasi_python.run, ["-c", READ], grants=RO, deadline_s=1.0)
    try:
        f.result(timeout=2.0)
    except concurrent.futures.TimeoutError:
        say(event="future.result timed out; main returning")
elif mode == "session_atexit":
    s = Session(grants=RO, deadline_s=1.0, shutdown_s=0)
    t = threading.Thread(target=lambda: s.run(READ), daemon=True)
    t.start(); t.join(2.0)
    say(event="turn thread alive; main returning", alive=t.is_alive())
elif mode == "root":
    c = wasi_python.run(["-c", READ.replace('/data/pipe', '/pipe')], root=folder, deadline_s=1.0)
    say(event="run returned", **done(c))
elif mode == "wgrant_write":
    code = "import os; fd=os.open('/data/pipe', os.O_WRONLY); print('opened')"
    c = wasi_python.run(["-c", code], grants=[Grant(folder, "/data", writable=True)], deadline_s=1.0)
    say(event="run returned", **done(c))
elif mode == "socket":
    code = "import os\ntry:\n os.open('/data/sock', os.O_RDONLY)\nexcept OSError as e: print('err', e.errno)"
    c = wasi_python.run(["-c", code], grants=RO, deadline_s=1.0)
    say(event="run returned", **done(c))
