"""Probes for spec 055's revision: what Python's shutdown does in today's guest, through `run`.

Counts only (fuel, bytes, outcomes); no wall time.
"""
import pathlib
import tempfile

from wasi_python import Grant, run

out = []


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line)
    out.append(line)


for snap in (True, False):
    name = "snapshot" if snap else "plain"
    # P1: the fuel of Python's shutdown: the same program ended normally, and by os._exit.
    for prog in ("pass", "import pandas"):
        normal, cut = [], []
        for _ in range(3):
            a = run(["-c", prog], snapshot=snap, fuel=10**11, deadline_s=None)
            b = run(["-c", prog + "\nimport os; os._exit(0)"], snapshot=snap, fuel=10**11, deadline_s=None)
            assert a.exit_code == 0 and b.exit_code == 0, (a, b)
            normal.append(a.fuel_used)
            cut.append(b.fuel_used)
        say(f"p1 {name} {prog!r}: normal exit min {min(normal)}, os._exit min {min(cut)}, "
            f"difference {min(normal) - min(cut)}")

    # P2: atexit runs and an open buffered file is flushed at a normal exit.
    with tempfile.TemporaryDirectory() as d:
        code = (
            "import atexit\n"
            "f = open('/w/buffered.txt', 'w'); f.write('x' * 100)\n"
            "def h():\n"
            "    with open('/w/atexit.txt', 'w') as g: g.write('ran')\n"
            "atexit.register(h)\n"
        )
        r = run(["-c", code], snapshot=snap, grants=[Grant(d, "/w", writable=True)])
        p = pathlib.Path(d)
        say(f"p2 {name} normal exit: exit {r.exit_code}; atexit.txt "
            f"{(p / 'atexit.txt').read_text() if (p / 'atexit.txt').exists() else 'absent'}; "
            f"buffered.txt {(p / 'buffered.txt').stat().st_size} bytes")

    # P3: os._exit after the same: no handler, no flush.
    with tempfile.TemporaryDirectory() as d:
        r = run(["-c", code + "import os; os._exit(4)\n"], snapshot=snap,
                grants=[Grant(d, "/w", writable=True)])
        p = pathlib.Path(d)
        say(f"p3 {name} os._exit: exit {r.exit_code}; atexit.txt "
            f"{'present' if (p / 'atexit.txt').exists() else 'absent'}; "
            f"buffered.txt {(p / 'buffered.txt').stat().st_size} bytes")

    # P4: a hostile atexit handler is bounded by fuel, and by the deadline.
    hostile = "import atexit\natexit.register(lambda: [0 for _ in iter(int, 1)])\nprint('body done')\n"
    r = run(["-c", hostile], snapshot=snap, fuel=10**9)
    say(f"p4 {name} hostile atexit, fuel 1e9: exit {r.exit_code}, trapped {r.trapped!r}, "
        f"stdout {r.stdout!r}")
    r = run(["-c", hostile], snapshot=snap, deadline_s=0.5)
    say(f"p4 {name} hostile atexit, deadline 0.5 s: exit {r.exit_code}, trapped {r.trapped!r}, "
        f"stdout {r.stdout!r}")
    sleeper = "import atexit, time\natexit.register(time.sleep, 10**6)\n"
    r = run(["-c", sleeper], snapshot=snap, deadline_s=0.5)
    say(f"p4 {name} sleeping atexit, deadline 0.5 s: exit {r.exit_code}, trapped {r.trapped!r}")

    # P5: SystemExit raised inside an atexit handler, and a handler that registers another.
    r = run(["-c", "import atexit, sys\natexit.register(sys.exit, 7)\n"], snapshot=snap)
    say(f"p5 {name} sys.exit(7) in atexit: exit {r.exit_code}, stderr tail "
        f"{r.stderr[-120:]!r}")
    r = run(["-c", "import atexit\ndef a():\n    print('a'); atexit.register(print, 'b')\n"
             "atexit.register(a)\n"], snapshot=snap)
    say(f"p5 {name} handler registering a handler: exit {r.exit_code}, stdout {r.stdout!r}")
    # P6: os._exit inside an atexit handler.
    r = run(["-c", "import atexit, os\natexit.register(print, 'later')\n"
             "atexit.register(os._exit, 5)\n"], snapshot=snap)
    say(f"p6 {name} os._exit(5) in atexit: exit {r.exit_code}, trapped {r.trapped!r}, "
        f"stdout {r.stdout!r}")

import sys
pathlib.Path(sys.argv[1]).write_text("\n".join(out) + "\n")
