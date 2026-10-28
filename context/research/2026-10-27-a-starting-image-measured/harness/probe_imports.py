"""Question 3: what each package does at import that an image would freeze.

For each prelude: a fresh instance; one turn installs recorders (an audit hook on open and the
filesystem events, and a wrapper on os.environ's item lookup); one turn runs the prelude, with the
shadowed random_get and clock_time_get counted under the prelude's name; one turn reports what was
opened, written, read from the environment, which module-level random generators exist, and which
descriptors are open. Results: results/probe-imports.json.

Run from this folder: uv run --no-sync python harness/probe_imports.py [names...]
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bare  # noqa: E402
from preludes import PER_PACKAGE, PRELUDES  # noqa: E402

RECORDER = r'''
def _install():
    import os, sys
    log = {"open": [], "events": [], "env": []}
    sys._spike_log = log
    def hook(event, args):
        if event == "open":
            path, mode, flags = args
            log["open"].append([str(path), mode, flags])
        elif event in ("os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.symlink", "os.link",
                       "os.truncate", "os.utime", "os.chmod", "shutil.rmtree", "tempfile.mkstemp", "tempfile.mkdtemp"):
            log["events"].append([event, repr(args)[:200]])
    sys.addaudithook(hook)
    cls = type(os.environ)
    real = cls.__getitem__
    def getitem(self, key, _real=real, _log=log["env"]):
        _log.append(key)
        return _real(self, key)
    cls.__getitem__ = getitem
_install()
del _install
'''

REPORT = r'''
def _report():
    import json, os, sys
    log = sys._spike_log
    kinds = []  # only from modules already imported: the report must import neither
    rnd = sys.modules.get("random")
    if rnd is not None:
        kinds.append(rnd.Random)
    npr = sys.modules.get("numpy.random")
    if npr is not None:
        kinds += [npr.RandomState, npr.Generator, npr.BitGenerator]
    kinds = tuple(kinds)
    gens = []
    for name, mod in sorted(sys.modules.items()):
        d = getattr(mod, "__dict__", None)
        if not isinstance(d, dict):
            continue
        for k, v in list(d.items()):
            if isinstance(v, kinds) and not isinstance(v, type):
                gens.append(f"{name}.{k}: {type(v).__module__}.{type(v).__name__}")
    fds = []
    for fd in range(0, 256):
        try:
            os.fstat(fd)
            fds.append(fd)
        except OSError:
            pass
    WRITE = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    def writes(o):
        path, mode, flags = o
        if isinstance(mode, str):
            return any(c in mode for c in "wax+")
        return bool(flags & WRITE)
    opened = log["open"]
    tmp = sys.modules.get("tempfile")
    out = {
        "modules": len(sys.modules),
        "random_imported": "random" in sys.modules,
        "numpy_random_imported": "numpy.random" in sys.modules,
        "opens": len(opened),
        "opens_outside_zip": sorted({o[0] for o in opened if not o[0].startswith("/usr/local/lib/python315.zip")}),
        "writes": sorted({o[0] + " " + str(o[1] or o[2]) for o in opened if writes(o)}),
        "events": log["events"][:40],
        "env_read": sorted(set(log["env"])),
        "generators": gens,
        "tempfile_name_sequence": None if tmp is None else repr(tmp._name_sequence),
        "fds_open": fds,
    }
    print("REPORT" + json.dumps(out))
_report()
del _report
'''


def probe(engine, module, name: str, code: str) -> dict:
    g = bare.Guest(engine, module, tag=f"probe-{name}")
    try:
        bare.set_phase("recorder")
        r0 = g.turn(RECORDER)
        assert r0["status"] == 0, r0
        bare.set_phase(name)
        before = {k: v for k, v in bare.COUNTS.items() if k[0] == name}
        r1 = g.turn(code)
        counts = {k[1]: v - before.get(k, 0) for k, v in bare.COUNTS.items() if k[0] == name}
        bare.set_phase("report")
        r2 = g.turn(REPORT)
        line = [ln for ln in r2["stdout"].splitlines() if ln.startswith("REPORT")]
        rep = json.loads(line[0][6:]) if line else {"error": r2}
        files = sorted(str(p.relative_to(g.root)) for p in g.root.rglob("*") if p.is_file())
        return {
            "prelude": code if len(code) < 200 else code[:200] + "...",
            "status": r1["status"],
            "trapped": r1["trapped"],
            "stderr_tail": r1["stderr"][-800:],
            "fuel": r1["fuel"],
            "seconds": round(r1["s"], 3),
            "wasi_counts": counts,
            "host_files_in_root": files,
            **rep,
        }
    finally:
        g.close()


def main(names):
    engine, module, _ = bare.engine_and_module()
    table = {**PER_PACKAGE, "everything": PRELUDES["everything"]}
    results = {}
    for name in names or table:
        results[name] = probe(engine, module, name, table[name])
        r = results[name]
        print(name, r["status"], r["trapped"], r["fuel"], r["wasi_counts"], len(r.get("generators", [])), flush=True)
    out = Path(__file__).parents[1] / "results" / "probe-imports.json"
    out.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    os.environ.setdefault("WASI_PYTHON_ARTIFACTS", "/Users/claygendron/Git/Repos/wasi_python/build/release-0.1.1/set/wasi-python-0.1.1")
    bare.on_big_stack(main, sys.argv[1:])
