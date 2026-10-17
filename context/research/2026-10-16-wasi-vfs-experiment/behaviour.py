"""The behaviour runs (memo findings 3 and 5). Usage: behaviour.py <scratch dir> <repo>"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import drive  # noqa: E402

X, REPO = Path(sys.argv[1]), Path(sys.argv[2])
OUT = X / "out"
PROBE = (Path(__file__).parent / "probe_guest.py").read_text()
ZIP = REPO / "build/out/python-stdlib.zip"
ZG = "/usr/local/lib/python314.zip/matplotlib/mpl-data"
PG = "/usr/local/share/wasi-python/mpl-data"
runs = 0


def root(with_zip=True):
    global runs
    runs += 1
    r = X / "roots" / f"r{runs}"
    shutil.rmtree(r, ignore_errors=True)
    (r / "usr/local/lib").mkdir(parents=True)
    if with_zip:
        shutil.copyfile(ZIP, r / "usr/local/lib/python314.zip")
    return r


def show(title, wasm, argv, preopens):
    res = drive.run(wasm, argv, preopens=preopens, io=X / "io" / f"i{runs}")
    print(f"=== {title}: exit {res['exit']} trapped {res['trapped']} fuel {res['fuel']}")
    print(res["stdout"].rstrip())
    tail = res["stderr"].strip().splitlines()[-2:]
    if tail:
        print("stderr:", " | ".join(tail))
    return res


which = sys.argv[3:] or ["A", "P", "Z", "B"]
if "A" in which:
    for f in ("python.wasm", "python-snapshot.wasm"):
        r = root()
        show(f"packA {f}, root /", OUT / "packA" / f,
             ["-c", PROBE, ZG, "/usr/local/lib/python314.zip/./matplotlib/mpl-data"],
             [(r, "/", True)])
        print("host root after:", sorted(p.name for p in r.iterdir()))
if "P" in which:
    for f in ("python.wasm", "python-snapshot.wasm"):
        r = root()
        show(f"packP {f}, root /", OUT / "packP" / f,
             ["-c", PROBE, PG, "/usr/local/share/./wasi-python/mpl-data"], [(r, "/", True)])
        print("host files planted:", sorted(str(p.relative_to(r)) for p in (r / "usr/local").rglob("*")))
if "Z" in which:
    sealed = ("import decimal, numpy; print(1)\n"
              "import os, sys, tempfile, json\n"
              "print('cwd', os.getcwd())\n"
              "for name, f in [('listdir /', lambda: os.listdir('/')),\n"
              "                ('open /tmp/x w', lambda: open('/tmp/x', 'w')),\n"
              "                ('open /x w', lambda: open('/x', 'w')),\n"
              "                ('mkstemp', lambda: tempfile.mkstemp()),\n"
              "                ('listdir /usr/local/lib', lambda: os.listdir('/usr/local/lib')),\n"
              "                ('remove zip', lambda: os.remove('/usr/local/lib/python314.zip')),\n"
              "                ('import csv (lazy)', lambda: __import__('csv').__file__),\n"
              "                ('import fractions (lazy)', lambda: __import__('fractions').__file__)]:\n"
              "    try: print('ok ', name, repr(f())[:100])\n"
              "    except Exception as e: print('err', name, type(e).__name__, getattr(e, 'errno', ''), e)\n")
    for f in ("python.wasm", "python-snapshot.wasm"):
        show(f"packZ {f}, NO preopen", OUT / "packZ" / f, ["-c", sealed], [])
    # Root added on top of the packed files.
    plant = ("import os\n"
             "for name, f in [('zip isfile', lambda: os.path.isfile('/usr/local/lib/python314.zip')),\n"
             "  ('listdir /usr/local/lib', lambda: os.listdir('/usr/local/lib')),\n"
             "  ('listdir /', lambda: sorted(os.listdir('/'))),\n"
             "  ('write /w', lambda: open('/w', 'w').write('x')),\n"
             "  ('remove zip', lambda: os.remove('/usr/local/lib/python314.zip')),\n"
             "  ('remove zip via ./', lambda: os.remove('/usr/local/./lib/python314.zip')),\n"
             "  ('plant module via ./', lambda: open('/usr/local/./lib/plantme.py', 'w').write('X=1')),\n"
             "  ('import json', lambda: __import__('json').__file__),\n"
             "  ('import plantme', lambda: __import__('plantme').__file__)]:\n"
             "    try: print('ok ', name, repr(f())[:100])\n"
             "    except Exception as e: print('err', name, type(e).__name__, getattr(e, 'errno', ''), e)\n")
    for d, f in (("packZ", "python.wasm"), ("packZ", "python-snapshot.wasm"),
                 ("packZr", "python-snapshot.wasm")):
        r = root(with_zip=True)
        (r / "usr/local/lib/python314.zip").write_bytes(b"not a zip")
        show(f"{d} {f}, root / holding a bad zip", OUT / d / f, ["-c", plant], [(r, "/", True)])
        print("host root after:", sorted(str(p.relative_to(r)) for p in r.rglob("*")))
if "B" in which:
    r = root()
    show("orderB (step 80, then pack), root /", OUT / "orderB" / "python.wasm",
         ["-c", PROBE, ZG, "/usr/local/lib/python314.zip/./matplotlib/mpl-data"], [(r, "/", True)])
