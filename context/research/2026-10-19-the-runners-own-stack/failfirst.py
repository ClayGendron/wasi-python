"""Spec 078's checks seen failing first on main's runner (the 078 worktree's src, unchanged), darwin.
Each case in its own child process: `small-thread` (run from a 256 KiB thread, a guest freeing a
2,000-deep list), `ctrl-c-no-deadline` (main thread, deadline_s=None, Ctrl-C while the guest
computes), `raising-handler` (an embedder's SIGINT handler that raises, cancel= set)."""
import subprocess, sys
CHILD = r'''
import os, signal, sys, threading, _thread
from wasi_python import run
case = sys.argv[1]
kw = dict(cache_dir=os.environ["CACHE"])
if case == "small-thread":
    out = {}
    def go(): out["d"] = run(["-c", "x = []\nfor i in range(2000): x = [x]\ndel x\nprint('freed')"], **kw)
    old = threading.stack_size(256 * 1024); t = threading.Thread(target=go); t.start(); threading.stack_size(old); t.join()
    print("result", out["d"].exit_code, out["d"].trapped, out["d"].stdout, flush=True)
elif case == "ctrl-c-no-deadline":
    def host(req):
        threading.Timer(0.5, _thread.interrupt_main).start(); return b"ok"
    try:
        d = run(["-c", "import _host\n_host.call(b'go')\nwhile True: pass"], host=host, deadline_s=None, **kw)
        print("returned", d.trapped, flush=True)
    except KeyboardInterrupt:
        print("interrupted", flush=True)
    print("next", run(["-c", "print(1)"], **kw).stdout, flush=True)
elif case == "raising-handler":
    def handler(s, f): raise KeyboardInterrupt
    signal.signal(signal.SIGINT, handler)
    main = threading.main_thread().ident
    def host(req):
        threading.Timer(0.5, lambda: signal.pthread_kill(main, signal.SIGINT)).start(); return b"ok"
    try:
        d = run(["-c", "import _host\n_host.call(b'go')\nwhile True: pass"], host=host, cancel=threading.Event(), deadline_s=30, **kw)
        print("returned", d.trapped, flush=True)
    except KeyboardInterrupt:
        print("interrupted", flush=True)
    print("next", run(["-c", "print(1)"], **kw).stdout, flush=True)
'''
for case in sys.argv[1:]:
    try:
        r = subprocess.run([sys.executable, "-c", CHILD, case], capture_output=True, text=True, timeout=120)
        print(case, "exit", r.returncode, r.stdout.strip().replace("\n", " | "), "stderr:", r.stderr.strip().replace("\n", " / ")[-300:])
    except subprocess.TimeoutExpired:
        print(case, "killed at its 120 s limit")
