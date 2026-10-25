"""Guest program (runs inside python.wasm): churns C++ exceptions so wasmtime's GC heap
collects while exnref values are live in many wasm frames. Each round:
  A. kiwisolver: add a required constraint that cannot be satisfied (C++ throw, caught in
     C++, turned into a Python exception);
  B. matplotlib._path (pybind11): pass a path object whose `vertices` property first runs
     round A, then raises; pybind11 throws error_already_set in C++, which unwinds C++
     frames and is converted back to a Python exception (C++ -> Python -> C++ -> Python);
  C. the same nested inside an outer Python try that re-raises and catches.
It checks every caught exception's type and message, and counts them."""
import sys, time
import kiwisolver as kiwi
from matplotlib import _path

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
BUDGET_S = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0

def unsat():
    s = kiwi.Solver()
    x = kiwi.Variable("x")
    s.addConstraint(x >= 10)
    try:
        s.addConstraint(x <= 5)
    except kiwi.UnsatisfiableConstraint as e:
        return type(e).__name__
    return "no-exception"

class Boom(Exception):
    pass

class BadPath:
    codes = None
    should_simplify = False
    @property
    def vertices(self):
        tag = unsat()
        if tag != "UnsatisfiableConstraint":
            raise RuntimeError("wrong inner result " + tag)
        raise Boom("boom-%d" % self.i)
    def __init__(self, i):
        self.i = i

counts = {"A": 0, "B": 0, "C": 0, "wrong": 0}
t0 = time.monotonic()
i = 0
while i < ROUNDS and time.monotonic() - t0 < BUDGET_S:
    if unsat() == "UnsatisfiableConstraint":
        counts["A"] += 1
    else:
        counts["wrong"] += 1
    try:
        _path.point_in_path(0.0, 0.0, 0.0, BadPath(i), None)
        counts["wrong"] += 1
    except Boom as e:
        if str(e) == "boom-%d" % i:
            counts["B"] += 1
        else:
            counts["wrong"] += 1
    except Exception as e:
        counts.setdefault("other:" + type(e).__name__ + ":" + str(e)[:60], 0)
        counts["other:" + type(e).__name__ + ":" + str(e)[:60]] += 1
    try:
        try:
            _path.point_in_path(0.0, 0.0, 0.0, BadPath(i), None)
        except Boom as e:
            raise ValueError("outer-%d" % i) from e
    except ValueError as e:
        if str(e) == "outer-%d" % i and str(e.__cause__) == "boom-%d" % i:
            counts["C"] += 1
        else:
            counts["wrong"] += 1
    except Exception as e:
        k = "otherC:" + type(e).__name__ + ":" + str(e)[:60]
        counts[k] = counts.get(k, 0) + 1
    i += 1
print("rounds", i, "elapsed_guest_s", round(time.monotonic() - t0, 2))
print("counts", sorted(counts.items()))
