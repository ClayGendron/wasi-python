"""Runs inside the WASI guest. Shows the failure, then applies the patched
`isfileobj` at run time and round-trips .npy files through real paths.

The host driver prepends `PATCHED_ISFILEOBJ`, the exact function source from
the patched numpy tree.
"""
import io
import os
import platform
import sys

import numpy as np
from numpy.lib import _format_impl

print("sys.platform", sys.platform, "| platform.machine()", repr(platform.machine()),
      "| numpy", np.__version__)
try:
    os.dup(1)
    print("os.dup(1) works")
except OSError as e:
    print("os.dup(1) ->", repr(e))


def attempt(label, f):
    try:
        r = f()
        print(f"{label}: ok" + ("" if r is None else f" -> {r}"))
    except Exception as e:
        print(f"{label}: {type(e).__name__}: {e}")


a = np.arange(6).reshape(2, 3)
print("--- stock numpy", np.__version__)
attempt("np.save('/tmp/a.npy')", lambda: np.save("/tmp/a.npy", a))
print("    /tmp/a.npy is", os.path.getsize("/tmp/a.npy"), "bytes (header only)")
buf = io.BytesIO()
np.save(buf, a)
with open("/tmp/b.npy", "wb") as f:
    f.write(buf.getvalue())
attempt("np.load('/tmp/b.npy') of a good file", lambda: np.load("/tmp/b.npy").tolist())
attempt("a.tofile('/tmp/c.bin')", lambda: a.tofile("/tmp/c.bin"))
attempt("np.fromfile('/tmp/b.npy')", lambda: np.fromfile("/tmp/b.npy", dtype=np.uint8).size)



class _NoMonkeypatch:
    """This is the real platform: `sys.platform` is already "wasi" and
    `os.dup` already raises, so the test's monkeypatches are not applied."""

    def setattr(self, target, name, value):
        assert name in ("platform", "dup")


def run_proposed_test(label):
    import pathlib
    tmp = pathlib.Path("/tmp/t")
    tmp.mkdir(exist_ok=True)
    failed = []
    arrays = basic_arrays + record_arrays  # noqa: F821
    for i, arr in enumerate(arrays):
        try:
            test_save_load_without_dup(tmp, _NoMonkeypatch(), arr)  # noqa: F821
        except Exception as e:
            failed.append(f"{type(e).__name__}: {e}")
    print(f"{label}: test_save_load_without_dup passed {len(arrays) - len(failed)}"
          f" of {len(arrays)} arrays")
    for msg in sorted(set(failed)):
        print("    ", msg)


run_proposed_test("stock numpy")

# Apply the patch at run time: the module gains `import sys`, and
# `isfileobj` is replaced by the patched function, run in the module's namespace.
_format_impl.sys = sys
exec(PATCHED_ISFILEOBJ, _format_impl.__dict__)  # noqa: F821
print("--- with the patched isfileobj")
run_proposed_test("patched")
cases = {
    "C int64 2x3": a,
    "Fortran float64": np.asfortranarray(np.linspace(0, 1, 12).reshape(3, 4)),
    "structured": np.array([(1, 2.5, b"ab")], dtype=[("x", "<i4"), ("y", ">f8"), ("z", "S2")]),
    "zero-size": np.zeros((0, 3)),
    "0-d": np.array(3.5),
    "big-endian": np.arange(5, dtype=">u4"),
    "unicode": np.array(["héllo", "wörld"]),
    "object (pickled)": np.array([{"k": 1}, None], dtype=object),
    "3 MiB, more than BUFFER_SIZE": np.arange(3 * 2**20 // 8, dtype=np.float64),
}
bad = 0
for name, arr in cases.items():
    try:
        np.save("/tmp/r.npy", arr)
        back = np.load("/tmp/r.npy", allow_pickle=True)
        same = back.dtype == arr.dtype and back.shape == arr.shape and (
            np.array_equal(back, arr) if arr.dtype != object else back.tolist() == arr.tolist())
        same = same and back.flags.f_contiguous == arr.flags.f_contiguous
        print(f"  {name}: {'round-trips' if same else 'DIFFERS'}")
        bad += not same
    except Exception as e:
        print(f"  {name}: {type(e).__name__}: {e}")
        bad += 1
# Through open file objects, too.
with open("/tmp/f.npy", "wb") as f:
    np.save(f, a)
    np.save(f, a * 2)
with open("/tmp/f.npy", "rb") as f:
    one, two = np.load(f), np.load(f)
ok = one.tolist() == a.tolist() and two.tolist() == (a * 2).tolist()
print("  two arrays through one open file:", "round-trip" if ok else "DIFFER")
bad += not ok
# The written file is byte-identical to what an in-memory save produces.
buf = io.BytesIO()
np.save(buf, a)
with open("/tmp/a.npy", "rb") as f:
    np.save("/tmp/a.npy", a)
with open("/tmp/a.npy", "rb") as f:
    same_bytes = f.read() == buf.getvalue()
print("  file bytes equal BytesIO bytes:", same_bytes)
bad += not same_bytes
print("failures:", bad)

