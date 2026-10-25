# Bounded checks of the limits and of call-to-call isolation, every call with a small deadline.
# Each case prints one JSON line. Argument: the folder of ten small files to grant read-only.
import asyncio, json, math, sys, threading, time
import wasi_python
from wasi_python import Grant, Mount, Session
from wasi_python.mounts import Stat, Errno

folder = sys.argv[1]
def say(case, **kw): print(json.dumps({"case": case, **kw}), flush=True)
def brief(c): return dict(exit=c.exit_code, trapped=c.trapped, out=c.stdout.decode()[-200:],
                          err=c.stderr.decode()[-200:], truncated=list(c.truncated))

class Mem:
    files = {f"/m{i}.txt": f"m{i}".encode() for i in range(10)}
    def stat(self, p):
        if p == "/": return Stat("dir")
        return Stat("file", len(self.files[p])) if p in self.files else Errno.ENOENT
    def list(self, p): return [(k[1:], "file") for k in self.files] if p == "/" else Errno.ENOTDIR
    def read(self, p): return self.files.get(p, Errno.ENOENT)

# 1. The guest has no way to make a FIFO or a device node.
c = wasi_python.run(["-c", "import os; print(hasattr(os,'mkfifo'), hasattr(os,'mknod'))"], deadline_s=2)
say("guest_mkfifo_available", **brief(c))

# 2. The open-file cap counted across a grant and a mount together.
code = ("import os\nfds=[]\nerr=None\n"
        "names=[f'/g/f{i}.txt' for i in range(10)]+[f'/m/m{i}.txt' for i in range(10)]\n"
        "order=[n for pair in zip(names[:10],names[10:]) for n in pair]\n"
        "for n in order:\n"
        "    try: fds.append((n, os.open(n, os.O_RDONLY)))\n"
        "    except OSError as e: err=(n, e.errno); break\n"
        "print(len(fds), err)\n")
c = wasi_python.run(["-c", code], grants=[Grant(folder, "/g")], mounts=[Mount(Mem(), "/m")],
                    max_open_files=8, deadline_s=2)
say("open_files_cap_8_grant_plus_mount", **brief(c))

# 3. The cap held across a session's turns: files opened in turn 1 still count in turn 2.
s = Session(grants=[Grant(folder, "/g")], max_open_files=6, deadline_s=2, shutdown_s=0)
t1 = s.run("import os\nkeep=[]\nfor i in range(10):\n  try: keep.append(os.open(f'/g/f{i}.txt', os.O_RDONLY))\n  except OSError as e: print('t1 stop', len(keep), e.errno); break")
t2 = s.run("try:\n  os.open('/g/f9.txt', os.O_RDONLY); print('t2 opened')\nexcept OSError as e: print('t2 errno', e.errno)\nfor f in keep: os.close(f)\nos.open('/g/f9.txt', os.O_RDONLY); print('t2 after close: opened')")
s.close()
say("open_files_cap_across_turns", t1=brief(t1), t2=brief(t2))

# 4. The memory cap with numpy: a 512 MiB array under a 128 MiB cap.
code = "import numpy as np\ntry:\n  a=np.ones(64<<20)\n  print('allocated', a.nbytes)\nexcept MemoryError: print('MemoryError')"
c = wasi_python.run(["-c", code], memory_bytes=128 << 20, deadline_s=5)
say("memory_cap_numpy", **brief(c))

# 5. deadline_s=None with fuel: a busy loop ends out of fuel.
t = time.monotonic()
c = wasi_python.run(["-c", "while True: pass"], deadline_s=None, fuel=200_000_000)
say("fuel_without_deadline", wall_s=round(time.monotonic() - t, 2), **brief(c))

# 6. Two threads on one session at once: the second is refused, not interleaved.
s = Session(deadline_s=2, shutdown_s=0)
res = {}
def turn(name, code):
    try: res[name] = brief(s.run(code))
    except Exception as e: res[name] = f"{type(e).__name__}: {e}"
a = threading.Thread(target=turn, args=("A", "import time; time.sleep(0.8); print('A')"))
b = threading.Thread(target=lambda: (time.sleep(0.3), turn("B", "print('B')")))
a.start(); b.start(); a.join(); b.join(); s.close()
say("session_two_threads", **res)

# 7. Outputs of concurrent calls: three run() threads and a session turn at once, each with its
# own token; each result must hold only its own token.
CODE = "import os,sys\nt=os.environ.get('TOKEN','S')\nfor i in range(800):\n  sys.stdout.write(t+'\\n'); sys.stderr.write(t+'\\n')\n  if i%50==0: sys.stdout.flush()"
out = {}
def one(tok): out[tok] = wasi_python.run(["-c", CODE], env={"TOKEN": tok}, deadline_s=20)
s = Session(env={"TOKEN": "sess"}, deadline_s=20, shutdown_s=0)
ths = [threading.Thread(target=one, args=(f"tok{i}",)) for i in range(3)]
ths.append(threading.Thread(target=lambda: out.__setitem__("sess", s.run(CODE))))
for th in ths: th.start()
for th in ths: th.join()
s.close()
say("concurrent_outputs", **{k: {"stdout_tokens": sorted(set(v.stdout.decode().split())),
                                 "stderr_tokens": sorted(set(v.stderr.decode().split())),
                                 "lines": v.stdout.count(b"\n")} for k, v in sorted(out.items())})

# 8. Limit arguments that would remove a limit.
def tried(fn):
    try: fn(); return "accepted"
    except (TypeError, ValueError) as e: return f"{type(e).__name__}"
cases = {}
for name, val in [("deadline_s", float("nan")), ("deadline_s", float("inf")), ("deadline_s", -1),
                  ("deadline_s", 0), ("deadline_s", True), ("deadline_s", 1e300),
                  ("fuel", -1), ("fuel", True), ("fuel", 2**63), ("memory_bytes", -1),
                  ("memory_bytes", 2**63), ("output_bytes", -1), ("max_open_files", -1),
                  ("max_tool_calls", -1), ("max_file_calls", True)]:
    cases[f"run {name}={val!r}"] = tried(lambda: wasi_python.run(["-c", "pass"], **{name: val}))
for name, val in [("idle_s", 0), ("idle_s", float("nan")), ("lifetime_s", -5), ("shutdown_s", None),
                  ("shutdown_s", float("inf"))]:
    cases[f"Session {name}={val!r}"] = tried(lambda: Session(**{name: val}).close())
s = Session(deadline_s=2, shutdown_s=0)
for name, val in [("deadline_s", float("nan")), ("fuel", 5), ("output_bytes", -1)]:
    cases[f"turn {name}={val!r}"] = tried(lambda: s.run("pass", **{name: val}))
s.close()
say("limit_arguments", **cases)
