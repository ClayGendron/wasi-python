"""F4 on an engine at wasmtime's defaults (512 KiB, no fuel, no epochs), through the judge's
driver's `own` path: the engine README step 4 describes for other embedders."""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))  # the repository's tests/
sys.path.insert(0, str(Path(__file__).parent))
import wasmtime as wt
from harness import guest as g, paths
_src = (Path(__file__).parent / "f4_edges.py").read_text(); _ns = {}; exec(_src.split("\ndef once(")[0], _ns); KINDS = _ns["KINDS"]

setdir = Path(sys.argv[1]); which = sys.argv[2]; work = Path(tempfile.mkdtemp(dir=sys.argv[3]))
kinds = sys.argv[4].split(",")
m = paths.parse_manifest((setdir / "MANIFEST").read_text())
wasm = setdir / ("python-snapshot.wasm" if which == "snapshot" else "python.wasm")
eng = wt.Engine(wt.Config())
mod = wt.Module.from_file(eng, str(wasm))

def once(kind, n):
    r = g.run(wasm, ["-c", KINDS[kind].format(n=n)], workdir=work, python_version=m.python,
              stdlib=setdir / "python-stdlib.zip", own=(eng, mod), measured=False)
    out = r.stdout.decode(errors="replace").strip()
    if r.trapped:
        return "trap:" + r.trapped
    if r.exit_code == 0 and out.startswith("ok"):
        return "ok"
    err = r.stderr.decode(errors="replace").strip().splitlines()
    return "raise:" + (err[-1][:100] if err else repr(out))

RANGES = {"xpath-parens": (100, 2000), "xpath-predicates": (1000, 4990), "xslt-call-template": (100, 2900),
          "xslt-apply-templates": (100, 2900), "c14n": (200, 5000), "relaxng": (100, 3000),
          "limit-reached": (1000, 8000), "traceback-freed": (1000, 8000), "xslt-apply-bare": (100, 2900)}
for kind in kinds:
    lo, hi = RANGES[kind]
    a, b = once(kind, lo), once(kind, hi)
    if a != "ok" or not b.startswith("trap"):
        print(json.dumps({"kind": kind, "binary": which, "lo": lo, "lo_got": a, "hi": hi, "hi_got": b}), flush=True)
        continue
    while hi - lo > 1:
        mid = (lo + hi) // 2
        got = once(kind, mid)
        if got == "ok": lo = mid
        elif got.startswith("trap"): hi = mid
        else:
            print(json.dumps({"kind": kind, "odd": [mid, got]})); break
    print(json.dumps({"kind": kind, "engine": "defaults", "binary": which, "last_ok": lo, "first_trap": hi}), flush=True)
