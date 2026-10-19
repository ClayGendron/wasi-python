"""Spec 083 probe: each program runs N times through a judge driver (the tests folder given), same
binary, fresh root each time. It prints, per program, the distinct fuel values (as steps from the
smallest) and the distinct outputs. Usage: uv run python -I probe_times.py <tests dir> <N>"""
import collections
import os
import shutil
import atexit, shutil, sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from harness import guest  # noqa: E402

SET = Path(os.environ.get("P083_SET") or sys.exit("P083_SET: a private copy of the set (cp -c -Rp)"))
N = int(sys.argv[2])
W = "open('/f', 'w').write('x')\n"
PROGRAMS = {
    "pure compute (control)": "print(sum(i * i for i in range(20000)))",
    "mtime_ns into a dict": "import os\n" + W + "s = os.stat('/f')\nd = {}\nfor k in range(200): d[s.st_mtime_ns + k] = k\nprint(len(d))",
    "localtime of mtime": "import os, time\n" + W + "print(time.localtime(os.stat('/f').st_mtime).tm_year)",
    "fstat times": "import os\n" + W + "fd = os.open('/f', os.O_RDONLY)\ns = os.fstat(fd)\nprint(s.st_atime_ns % 7, s.st_mtime_ns % 7, s.st_ctime_ns % 7)",
    "times are the clock's": "import os, time\n" + W + "t0 = time.time_ns()\ns = os.stat('/f')\nprint(s.st_mtime_ns - t0, s.st_atime_ns == s.st_mtime_ns == s.st_ctime_ns)",
    "unchanged file keeps its time": "import os\n" + W + "a = os.stat('/f').st_mtime_ns\nb = os.stat('/f').st_mtime_ns\nprint(a == b)",
    "a write moves mtime": "import os\n" + W + "a = os.stat('/f').st_mtime_ns\nopen('/f', 'a').write('y')\nb = os.stat('/f').st_mtime_ns\nprint(b > a)",
    "utime round trip": "import os\n" + W + "os.utime('/f', ns=(1_000_000_123, 2_000_000_456))\ns = os.stat('/f')\nprint(s.st_atime_ns, s.st_mtime_ns)",
    "utime by fd round trip": "import os\n" + W + "fd = os.open('/f', os.O_RDWR)\nos.utime(fd, ns=(3_000_000_789, 4_000_000_012))\ns = os.fstat(fd)\nprint(s.st_atime_ns, s.st_mtime_ns)",
    "utime now is the clock's": "import os, time\n" + W + "os.utime('/f')\nt = time.time()\nprint(0 <= t - os.stat('/f').st_mtime < 0.05)",
    "a module written after a scan imports": "import sys, os\nsys.path.insert(0, '/m')\nos.mkdir('/m')\nopen('/m/a.py', 'w').write('A = 1')\nimport a\nopen('/m/b.py', 'w').write('B = 2')\nimport b\nprint(a.A, b.B)",
    "embedding check's program": "import os\nos.mkdir('/w')\nopen('/w/f', 'wb').write(b'x')\nst = os.stat('/w/f')\nprint(st.st_ino != 0, st.st_mtime != 1767225600)",
}
work = Path(tempfile.mkdtemp(prefix="p083-", dir=os.environ.get("P083_WORK", "/tmp")))
atexit.register(shutil.rmtree, work, True)  # its run folders hold links to the set's zip
for label, code in PROGRAMS.items():
    fuels, outs = [], collections.Counter()
    for _ in range(N):
        r = guest.run(SET / "python-snapshot.wasm", ["-c", code], workdir=work,
                      python_version="3.15", stdlib=SET / "python-stdlib.zip")
        out = r.text.strip() if r.exit_code == 0 else "FAILED " + r.describe()
        outs[out] += 1
        fuels.append(r.fuel)
    lo = min(fuels)
    steps = dict(sorted(collections.Counter(f - lo for f in fuels).items()))
    print(f"{label:40} distinct fuel {len(steps)} steps {steps}  seq {[f - lo for f in fuels]}  outputs {dict(outs)}")
shutil.rmtree(work, ignore_errors=True)
