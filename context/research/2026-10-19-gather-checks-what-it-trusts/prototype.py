# Records: gh run download 39255794160 -p 'record-*' -D <records dir> (the a7 tag run; 39265738300 for
# spec 065's dry run). Data only: parsed as JSON, never run. Spec 085's research, 2026-10-19.
"""Spec 085: a throwaway prototype of the three new rules, applied to real records, to show they
are red on the forgeries and never on an honest run. Not the build: the builder writes gather.py.
    uv run python <this> <records dir> <accepted commit>"""

import ast
import inspect
import json
import subprocess
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, "tests")
import pytest  # noqa: E402

from harness import plugin  # noqa: E402

# Decision 2: the needs CI lacks, and the systems on which each may block a check.
CI_NEEDS = {
    "oracle": {"macos", "linux", "windows", "build"},
    "prior-art clones": {"macos", "linux", "windows", "build"},
    "three systems": {"macos", "linux", "windows", "build"},
    "descriptor limit": {"windows"},
}


def needs_called(func) -> set[str]:
    """The needs a check's own body names in a call `needs.need("…")` or `need("…")`."""
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    except (OSError, TypeError, SyntaxError):
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            if name == "need":
                out |= {a.value for a in n.args if isinstance(a, ast.Constant) and isinstance(a.value, str)}
    return out


class C:
    def __init__(self):
        self.may = {}

    def pytest_collection_finish(self, session):
        for item in session.items:
            if plugin.area_of(item) is None:
                continue
            got = needs_called(getattr(item, "function", None)) & set(CI_NEEDS)
            if got:
                self.may[item.nodeid] = got


c = C()
import contextlib, io  # noqa: E401,E402
with contextlib.redirect_stdout(io.StringIO()):
    pytest.main(["--collect-only", "-qq", "-p", "no:cacheprovider"], plugins=[c])
print("derived (check, need) pairs:")
for n, ns in sorted(c.may.items()):
    print("  ", n, sorted(ns), "on", sorted(set().union(*(CI_NEEDS[x] for x in ns)) - {"build"}))

src = Path(sys.argv[1])
acc = json.loads(subprocess.run(["git", "show", f"{sys.argv[2]}:context/progress/accepted.json"],
                                capture_output=True, text=True, check=True).stdout)
red = []
for f in sorted(src.glob("record-*/latest.json")):
    name = f.parent.name.removeprefix("record-")
    system = "build" if name == "build-build" else name.split("-", 1)[0]
    r = json.loads(f.read_text())
    s, u = r.get("suite", {}), r["meta"].get("units", {})
    ints = all(type(s.get(k)) is int and s[k] >= 0 for k in ("passed", "skipped", "total"))
    if not ints or s["total"] != u.get("count") or s["passed"] + s["skipped"] != s["total"]:
        red.append(f"G4 {name}: suite {s} is not its {u.get('count')} unit tests")
    for node, ch in r["checks"].items():
        if ch["status"] == "blocked":
            need = ch.get("need")
            if need not in c.may.get(node, set()) or system not in CI_NEEDS[need]:
                red.append(f"G4 {name} {node}: blocked by {need!r}, not allowed here")
        if ch["status"] == "pass":
            want = set(acc["checks"].get(node, {}).get("metrics", {}).get("darwin-arm64", {})) - {"wasmtime"}
            for m in sorted(want - set(ch.get("metrics", {}))):
                red.append(f"G5 {name}: {node} records no {m} (accepted.json has it)")
print(f"{len(red)} red line(s) on {src.name}:", *red[:8], sep="\n  ")
