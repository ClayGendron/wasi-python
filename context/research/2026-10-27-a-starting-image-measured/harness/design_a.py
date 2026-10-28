"""Design (a): a new snapshot module per prelude, made by the pinned wasmtime's own `wasmtime wizer`
(the CLI the build uses, found under the main tree's build/tools; nothing is downloaded).

The build's wizer.initialize runs a compile-time string (PREIMPORT). For this probe only, a copy of
python.wasm has that string's bytes replaced, in place and at the same length, by
`exec(open('/prelude.py').read())` padded with spaces, so wizer runs a prelude file from its root.
It is a measurement device, not a proposal: a real design would read the prelude another way.

Results: results/design-a-<name>.json. Run: uv run --no-sync python harness/design_a.py <prelude>
"""

from __future__ import annotations

import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bare  # noqa: E402
from preludes import PRELUDES  # noqa: E402
from wasm_sections import summary  # noqa: E402

import wasmtime as wt  # noqa: E402

from wasi_python import _artifacts, _zip  # noqa: E402

WASMTIME = Path("/Users/claygendron/Git/Repos/wasi_python/build/tools/wasmtime-v49.0.3-aarch64-macos/wasmtime")
PREIMPORT = b"import encodings, io, os, sys, json, csv, re, _colorize"
REPLACEMENT = b"exec(open('/prelude.py').read())"
FLAGS = "-W exceptions=y,unknown-imports-trap=y -S cli=y,inherit-stdin=n,inherit-stdout=n,inherit-stderr=n -C cache=n --init-func wizer.initialize".split()
RESULTS = Path(__file__).parents[1] / "results"
PUBLISH = "\nimport _reactor\n_reactor._MAIN_NAMES.update({k: v for k, v in dict(globals()).items() if not k.startswith('_')})\n"
PROGRAM = "import sys; print(len(sys.modules)); import random, numpy; print(random.random() != 0.5)"
# For the randomness prelude: what a call sees of the states made under wizer's constant entropy.
RANDOM_PROGRAM = (
    "import random, tempfile, sys, numpy, json, time\n"
    "print(json.dumps({'random': random.random(), 'np_legacy': float(numpy.random.random()),"
    " 'sympy_rng': sys.modules['sympy.core.random'].rng.random(),"
    " 'tempfile_name': next(tempfile._get_candidate_names()), 'monotonic_minus_prelude_s': round(time.monotonic() - t0_mono, 3)}))"
)
EXTRA = {"randomstate": "import random, numpy, numpy.random, tempfile, sympy, time\nnext(tempfile._get_candidate_names())\nt0_mono = time.monotonic()\n"}


def patched_plain(found) -> Path:
    out = bare.WORK / "python-prelude-file.wasm"
    if not out.exists():
        data = found.plain.read_bytes()
        assert data.count(PREIMPORT) == 1
        out.write_bytes(data.replace(PREIMPORT, REPLACEMENT.ljust(len(PREIMPORT), b" ")))
    return out


def main(name: str) -> None:
    found = _artifacts.artifacts()
    folder = _zip._zip_folder(found)
    work = bare.WORK / f"wizer-{name}"
    shutil.rmtree(work, ignore_errors=True)
    root = work / "root"
    (root / "usr/local/lib").mkdir(parents=True)
    (root / "tmp/.home").mkdir(parents=True)
    shutil.copy(found.stdlib_zip, root / "usr/local/lib/python315.zip")
    prelude = "import encodings, io, os, sys, json, csv, re, _colorize\n" + {**PRELUDES, **EXTRA}[name] + PUBLISH
    (root / "prelude.py").write_text(prelude)
    plain = patched_plain(found)
    out = work / "python-snapshot.wasm"
    cmd = [str(WASMTIME), "wizer", *FLAGS, "--dir", f"{root}::/",
           "--dir", f"{folder.data}::/usr/local/lib/python315.zip/{_zip.MPL_DATA_GUEST}",
           "--env", "HOME=/tmp/.home", "--env", "TMPDIR=/tmp", "--env", "PYTHONTZPATH=",
           "-o", str(out), str(plain)]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True)
    wizer_s = time.perf_counter() - t0
    res: dict = {"prelude": name, "wizer_s": round(wizer_s, 1), "wizer_rc": p.returncode, "wizer_stderr": p.stderr[-2000:]}
    if p.returncode != 0:
        print(json.dumps(res, indent=1))
        (RESULTS / f"design-a-{name}.json").write_text(json.dumps(res, indent=1))
        return
    s = summary(out)
    res.update({"module_bytes": s["bytes"], "module_MiB": round(s["bytes"] / 2**20, 1), "memory_min_pages": s["memories"][0]["min"],
                "data_segments": s["data_segments"], "data_MiB": round(s["data_bytes"] / 2**20, 1), "exports": s["exports"]})
    engine, _, _ = bare.engine_and_module()  # the product's metered engine
    t0 = time.perf_counter()
    module = wt.Module(engine, out.read_bytes())
    res["compile_s"] = round(time.perf_counter() - t0, 1)
    cwasm = work / "python-snapshot.cwasm"
    t0 = time.perf_counter()
    cwasm.write_bytes(module.serialize())
    res["serialize_s"] = round(time.perf_counter() - t0, 2)
    res["cwasm_MiB"] = round(cwasm.stat().st_size / 2**20, 1)
    t0 = time.perf_counter()
    from_file = wt.Module.deserialize_file(engine, str(cwasm))
    res["deserialize_file_s"] = round(time.perf_counter() - t0, 3)
    rows = []
    for which, mod in (("compiled_in_process", module), ("deserialized_from_file", from_file)):
        for _ in range(2 if name == "randomstate" else 5):
            f0 = resource.getrusage(resource.RUSAGE_SELF).ru_minflt
            g = bare.Guest(engine, mod, tag="a", argv=("-c", RANDOM_PROGRAM if name == "randomstate" else PROGRAM))
            f1 = resource.getrusage(resource.RUSAGE_SELF).ru_minflt
            try:
                before = g.store.get_fuel()
                t0 = time.perf_counter()
                rc = g.exports["run"](g.store)
                run_s = time.perf_counter() - t0
                o = g.new_output()
                rows.append({"module": which, "instantiate_ms": round(g.instantiate_s * 1000, 2), "instantiate_faults": f1 - f0,
                             "run_ms": round(run_s * 1000, 1), "run_fuel": before - g.store.get_fuel(), "rc": rc,
                             "stdout": o["stdout"].strip(), "stderr": o["stderr"][-400:], "pages": g.pages()})
            finally:
                g.close()
    res["calls"] = rows
    print(json.dumps({k: v for k, v in res.items() if k != "calls"}, indent=1))
    for r in rows:
        print(r)
    (RESULTS / f"design-a-{name}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    os.environ.setdefault("WASI_PYTHON_ARTIFACTS", "/Users/claygendron/Git/Repos/wasi_python/build/release-0.1.1/set/wasi-python-0.1.1")
    bare.on_big_stack(main, sys.argv[1])
