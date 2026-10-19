"""Spec 071's delta after 069: where the growth against 069's set comes from (fuel per probe)."""
import re, sys
from pathlib import Path
import wasi_python
sys.path.insert(0, "tests/checks")
src = Path("tests/checks/test_v1_3_lxml.py").read_text()
ENC = re.search(r'ENCODINGS = """(.*?)"""', src, re.S).group(1)
def sets():
    for name, d in (("069", Path("/Users/claygendron/Git/Repos/wasi_python/build/sets/s-1a7242a7a8b518f4")),
                    ("071", Path("build/artifacts")), ("full", Path("build/artifacts-fullwindow"))):
        yield name, wasi_python.Artifacts(d / "python-snapshot.wasm", d / "python.wasm", d / "python-stdlib.zip", d / "MANIFEST")
PROBES = {
    "addresses": "import numpy as np\nprint(*[hex(id(t)) for t in (bool, int, str, dict, list, type, object, np.ndarray)])",
    "pass": "pass",
    "encode-errors": "n = 0\nfor cp in range(0xA0, 0x10000):\n    try:\n        chr(cp).encode('ascii')\n    except UnicodeEncodeError:\n        n += 1\nprint(n)",
    "np-bools": "import numpy as np\nx = [True] * 131072\nfor i in range(4): np.array(x)",
}
for enc in ["euc-jp"]:
    PROBES["enc-" + enc] = ENC.replace('ENCS = ["windows-1252"', 'ENCS = ["%s"]\n_X = ["windows-1252"' % enc)
rows = {}
for name, a in sets():
    for p, code in PROBES.items():
        r = wasi_python.run(["-c", code], fuel=10**11, artifacts=a)
        rows.setdefault(p, {})[name] = (r.fuel_used, r.stdout.decode().strip()[:90])
for p, v in rows.items():
    f0, f1, f2 = v["069"][0], v["071"][0], v["full"][0]
    print(f"{p:16} 069 {f0:>13} | 071 {f1 - f0:>+10} ({(f1 - f0) / f0 * 100:+.3f}%) | whole-stack window {f2 - f0:>+10} ({(f2 - f0) / f0 * 100:+.3f}%)")
