import os
os.chdir("context/reviews/0.1.0-security-audit-2026-10-25/agents/h13-sessions-limits/scratch/evidence")
p="fifo_child.py"; s=open(p).read()
s=s.replace("    wasi_python.set_defaults(async_workers=1)\n","    import dataclasses\n    wasi_python.set_defaults(dataclasses.replace(wasi_python.defaults(), async_workers=1))\n")
s=s.replace('elif mode == "root":', '''elif mode == "exit_pool":
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
elif mode == "root":''')
open(p,"w").write(s)
d=open("fifo_driver.py").read()
d=d.replace('sock = socket.socket(socket.AF_UNIX); p = f"{folder}/sock"\n        if os.path.exists(p): os.unlink(p)\n        sock.bind(p)',
 'sock = socket.socket(socket.AF_UNIX); p = f"{folder}/sock"\n        if os.path.exists(p): os.unlink(p)\n        here = os.getcwd(); os.chdir(folder); sock.bind("sock"); os.chdir(here)')
open("fifo_driver.py","w").write(d)
