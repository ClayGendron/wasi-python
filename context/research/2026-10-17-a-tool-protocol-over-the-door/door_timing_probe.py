"""How a run ends when its deadline passes, or its cancel is set, while a raw `host` blocks.

Run from the repository root: uv run python -I context/research/2026-10-17-a-tool-protocol-over-the-door/door_timing_probe.py
No tool layer: `host` is a plain function. The sleeps only choose the order of events; what is
reported is the run's outcome (`trapped`) and whether the guest ran on after the door returned.
"""

import threading
import time

from wasi_python import run

GUEST = "import _host\nr = _host.call(b'x')\nprint('after door', len(r), flush=True)\nwhile True: pass\n"


def show(label, done):
    print(f"--- {label}\ntrapped={done.trapped!r} exit_code={done.exit_code} stdout={done.stdout!r}")


def blocking(seconds, answer=b"ok"):
    def host(frame):
        time.sleep(seconds)
        return answer

    return host


# a. the deadline passes while the host blocks; no cancel
show("deadline 0.3 s, host blocks 1 s, answers 2 bytes",
     run(["-c", GUEST], host=blocking(1.0), deadline_s=0.3))
show("deadline 0.3 s, host blocks 1 s, answers 0 bytes",
     run(["-c", GUEST], host=blocking(1.0, b""), deadline_s=0.3))

# b. cancel is set while the host blocks
for size in (2, 0):
    ev = threading.Event()
    threading.Timer(0.2, ev.set).start()
    show(f"cancel set at 0.2 s, host blocks 1 s, answers {size} bytes",
         run(["-c", GUEST], host=blocking(1.0, b"ok"[:size]), cancel=ev, deadline_s=None))

# c. the control: cancel set while the guest computes
ev = threading.Event()
threading.Timer(0.3, ev.set).start()
show("control: cancel set while the guest computes",
     run(["-c", "while True: pass"], cancel=ev, deadline_s=None))
