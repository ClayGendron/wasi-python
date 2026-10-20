"""v1.3: numpy and pandas are inside, and their results match native Python at the same pins."""

from __future__ import annotations

import json
import re
import tempfile
import zipfile
from pathlib import Path

import pytest

from harness import jobs, needs, paths

pytestmark = pytest.mark.goal("v1.3")


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_numpy_and_pandas_are_builtin_at_manifest_versions(guest, which) -> None:
    code = (
        "import numpy, pandas, numpy._core._multiarray_umath as m\n"
        "print(numpy.__version__, pandas.__version__, m.__spec__.origin)\n"
    )
    r = guest(which, ["-c", code])
    assert r.exit_code == 0, r.describe()
    m = paths.parse_manifest((paths.artifact_dir() / "MANIFEST").read_text())
    want = f"{m.packages.get('numpy')} {m.packages.get('pandas')} built-in"
    assert r.text.strip() == want, f"guest says {r.text.strip()!r}, MANIFEST says {want!r}"


@pytest.mark.slow
def test_numpy_csv_job_matches_native(guest) -> None:
    why = jobs.compare(
        jobs.expected_path("numpy_csv").read_bytes(), jobs.run_in_guest(guest, "numpy_csv")
    )
    assert why is None, why


@pytest.mark.slow
def test_pandas_csv_job_matches_native(guest) -> None:
    why = jobs.compare(
        jobs.expected_path("pandas_csv").read_bytes(), jobs.run_in_guest(guest, "pandas_csv")
    )
    assert why is None, why


@pytest.mark.slow
def test_random_matches_native(guest) -> None:
    out = jobs.run_in_guest(guest, "numpy_random")
    why = jobs.compare(jobs.expected_path("numpy_random").read_bytes(), out)
    assert why is None, why


@pytest.mark.slow
def test_compress_job_matches_native(guest) -> None:
    """bz2, lzma and tarfile write the same bytes as native (spec 007)."""
    why = jobs.compare(
        jobs.expected_path("compress").read_bytes(), jobs.run_in_guest(guest, "compress")
    )
    assert why is None, why


@pytest.mark.slow
def test_sqlite_job_matches_native(guest) -> None:
    """sqlite3 on a file, with a forced spill to temporary files, and pandas' to_sql and read_sql
    give native's results (spec 007)."""
    why = jobs.compare(
        jobs.expected_path("sqlite").read_bytes(), jobs.run_in_guest(guest, "sqlite")
    )
    assert why is None, why


SQLITE_LOCK = """
import os, sqlite3
db = "/work/t.db"
os.makedirs("/work")
a = sqlite3.connect(db, isolation_level=None)
a.execute("create table t(x)")
a.executemany("insert into t values (?)", [(i,) for i in range(10)])

def probe(label):
    b = sqlite3.connect(db, timeout=0, isolation_level=None)
    try:
        got = b.execute("select count(*) from t").fetchone()[0]
        b.execute("insert into t values (-1)")
    except sqlite3.OperationalError as e:
        got = str(e)
    b.close()
    print(label, os.path.isdir(db + ".lock"), got)

a.execute("begin immediate")
a.execute("insert into t values (99)")
probe("write")
a.execute("commit")
cur = a.execute("select x from t")
cur.fetchone()
probe("select")
cur.close()
probe("closed")
print("first", a.execute("select count(*) from t").fetchone()[0])
a.close()
probe("after")
"""


def test_sqlite_holds_a_lock_while_it_writes(guest) -> None:
    """SQLite's own default locking on WASI is a `<db>.lock` directory beside the database, held
    while a connection writes or has a statement open; another connection then gets "database is
    locked" (at once with timeout=0; after its busy timeout otherwise). The README states it
    (spec 007, Decision 8), and this check holds that default: a future pin that chose another
    locking would fail here."""
    r = guest("snapshot", ["-c", SQLITE_LOCK])
    assert r.exit_code == 0, r.describe()
    want = (
        "write True database is locked\n"
        "select True database is locked\n"
        "closed False 11\n"
        "first 12\n"
        "after False 12\n"
    )
    assert r.text == want, r.text


def test_longdouble_parses(guest) -> None:
    code = (
        "import numpy as np\n"
        "x = np.longdouble('0.1')\n"
        "print(np.finfo(np.longdouble).bits, x > 0, str(np.longdouble(1) / 3)[:8])\n"
    )
    r = guest("plain", ["-c", code])
    assert r.exit_code == 0, r.describe()
    assert r.text.strip() == "128 True 0.333333", r.text.strip()


def test_stdlib_debugging_tools_import(guest) -> None:
    """pdb, pydoc and doctest are pure Python and need _pyrepl, which the zip keeps."""
    r = guest("snapshot", ["-c", "import pdb, pydoc, doctest; print('ok')"])
    assert (r.exit_code, r.text.strip()) == (0, "ok"), r.describe()


def test_gzip_round_trips(guest) -> None:
    code = (
        "import gzip, io, zipfile\n"
        "data = b'wasi_python ' * 1000\n"
        "assert gzip.decompress(gzip.compress(data)) == data\n"
        "buf = io.BytesIO()\n"
        "with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:\n"
        "    z.writestr('a.txt', data)\n"
        "with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:\n"
        "    assert z.read('a.txt') == data\n"
        "print('ok')\n"
    )
    r = guest("plain", ["-c", code])
    assert (r.exit_code, r.text) == (0, "ok\n"), r.describe()


def test_default_integer_width_is_documented(guest) -> None:
    r = guest("plain", ["-c", "import numpy as np; print(np.dtype(np.int_).itemsize * 8)"])
    assert r.exit_code == 0, r.describe()
    bits = r.text.strip()
    stated = re.findall(r"default\s+integer\s+is\s+(\d+)-bit", paths.README.read_text("utf-8"))
    assert stated and set(stated) == {bits}, (
        f"the guest's default integer is {bits}-bit; README says {stated}"
    )


# What the snapshot holds at start, read by the program's first statement (spec 069, check a).
START_PROBE = (
    "import sys\n"
    "mods = list(sys.modules)\n"
    "import json\n"
    "print(json.dumps({'modules': mods, 'stdlib': sorted(sys.stdlib_module_names)}))\n"
)
GUARD_NAMES = ("numpy", "pandas", "host")  # the zip's derivation is not vacuous
# The snapshot's start at least 3 times cheaper than the plain start (spec 069, check b). Spec 073
# restated it from 8: by the owner's answer to question 103, run on the snapshot undoes the freeze
# before finalizing, as CPython finalizes, at about 28 M fuel a run (about 3.8 times, measured).
START_FACTOR = 3


def zip_non_stdlib_names(zip_path: Path, stdlib: set[str]) -> set[str]:
    """The top-level names of the zip's members (a folder's first part, a root module's stem) that
    are neither the stdlib's nor the reactor's (spec 069, Decision 5a): the zip's packages."""
    tops = set()
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            first, sep, _ = name.partition("/")
            if sep:
                if not first.endswith((".dist-info", ".egg-info")):
                    tops.add(first)
            elif first.endswith((".pyc", ".py")):
                tops.add(first.rsplit(".", 1)[0])
    return {t for t in tops if not paths.is_stdlib_or_reactor(t, stdlib)}


def test_the_snapshot_pre_imports_no_package(guest, artifacts) -> None:
    """Decision 34 (spec 069): the snapshot starts with the stdlib's bootstrap and no package,
    for every package now and later. The rule needs no list of packages: a module is the stdlib's
    or the reactor's, or it is refused; the zip's own non-stdlib names say which of the refused
    ones is a package from the zip."""
    r = guest("snapshot", ["-c", START_PROBE])
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text.strip().splitlines()[-1])
    stdlib = set(got["stdlib"])
    packages = zip_non_stdlib_names(artifacts.path("python-stdlib.zip"), stdlib)
    missing_guard = [n for n in GUARD_NAMES if n not in packages]
    assert not missing_guard, f"the zip's non-stdlib names lack {missing_guard}: derivation broken"
    tops = {m.split(".", 1)[0] for m in got["modules"]}
    foreign = [
        f"{t} (a package in the zip)" if t in packages else t
        for t in sorted(tops)
        if not paths.is_stdlib_or_reactor(t, stdlib)
    ]
    assert not foreign, _named(foreign, "modules at start that are not the stdlib's")
    absent = [n for n in paths.PREIMPORT if n not in tops]
    assert not absent, f"the pre-import list did not run: {absent} not in sys.modules at start"


def test_the_snapshot_starts_cheaper_than_plain(guest) -> None:
    """The snapshot's reason to exist (spec 069, check b): its start, `-c pass`, is at least
    START_FACTOR times cheaper than the plain reactor's. A change to the plain start, the freeze
    or the teardown restates the factor, with its numbers, as a judge change: spec 073 restated it
    from 8 to 3, when run on the snapshot began to undo the freeze before finalizing (question
    103's answer)."""
    plain = guest("plain", ["-c", "pass"], record=False)
    snap = guest("snapshot", ["-c", "pass"])
    assert plain.exit_code == 0 and snap.exit_code == 0, f"{plain.describe()} / {snap.describe()}"
    ratio = plain.fuel / snap.fuel
    assert snap.fuel * START_FACTOR <= plain.fuel, (
        f"snapshot start {snap.fuel:,} fuel, plain start {plain.fuel:,}: {ratio:.2f} times, "
        f"under {START_FACTOR}; either a package is pre-imported (see "
        "test_the_snapshot_pre_imports_no_package) or the snapshot's reason to exist must be "
        "restated (spec 069, Decision 5b)"
    )


def _named(names: list[str], what: str) -> str:
    return f"{what}: {', '.join(names)} (decision 34, spec 069)"


CPP_THROW = """
import numpy as np
try:
    np.fft.fft(np.zeros(12_000_001))
except MemoryError as e:
    print("caught", repr(e))
print(np.allclose(np.fft.fft(np.ones(4)), [4, 0, 0, 0]))
"""


def test_a_cpp_exception_reaches_python(guest_workdir) -> None:
    """A C++ `throw` inside numpy (pocketfft's allocation, under a memory cap) becomes a Python
    MemoryError, and the program goes on (spec 005, Decision 9). numpy's own array-allocation
    error carries a shape and a dtype; the bare MemoryError() is C++'s std::bad_alloc."""
    needs.need("runner", "artifact dir")
    import wasi_python

    root = Path(tempfile.mkdtemp(prefix="cpp-throw-", dir=guest_workdir))
    done = wasi_python.run(
        ["-c", CPP_THROW],
        root=root,
        memory_bytes=560 << 20,
        fuel=50_000_000_000,
        cache_dir=False,
    )
    assert (done.exit_code, done.trapped) == (0, None), done
    assert done.stdout == b"caught MemoryError()\nTrue\n", done
    # No fuel metric: the runner's clock is real, which spreads this count by about 96,000,
    # wider than the ratchet's 0.01% (spec 008's review, N2). The judge's driver, whose clock is
    # fixed, records the stack's fuel elsewhere.


@pytest.mark.slow
def test_goldens_reproduce_under_the_pinned_oracle() -> None:
    needs.need("oracle")
    workdir = paths.HARNESS_TMP / "oracle-check"
    for job in jobs.JOBS:
        if not jobs.reproducible_here(job):
            continue  # native pixels may differ off the recording platform (spec 023, Decision 8)
        first = jobs.run_native(job, 0, workdir)
        second = jobs.run_native(job, 1, workdir)
        assert jobs.compare(first, second) is None, f"{job}: two hash seeds disagree"
        why = jobs.compare(jobs.expected_path(job).read_bytes(), first)
        assert why is None, f"{job}: {why}"


NPY = """
import io, os
import numpy as np
os.makedirs("/npy")  # the judge's root has no /tmp

def same(a, b):
    return (a.dtype, a.shape, a.tolist(), a.flags.f_contiguous) == (
        b.dtype, b.shape, b.tolist(), b.flags.f_contiguous)

cases = {
    "plain": np.arange(12, dtype=np.int32).reshape(3, 4),
    "record": np.array([(1, 2.5), (3, 4.5)], dtype=[("a", "<i4"), ("b", "<f8")]),
    "0-d": np.array(7.0),
    "fortran": np.asfortranarray(np.arange(6.0).reshape(2, 3)),
    "large": np.arange(40_000, dtype=np.float64),
    "empty": np.zeros((0, 3), dtype=np.int16),
}
for name, a in cases.items():
    try:
        np.save(f"/npy/{name}.npy", a)
        print(name, same(np.load(f"/npy/{name}.npy"), a))
    except OSError as e:
        print(name, "OSError", e.errno)
try:
    obj = np.array([{"k": 1}, [2, 3], "s"], dtype=object)
    np.save("/npy/object.npy", obj, allow_pickle=True)
    print("object", np.load("/npy/object.npy", allow_pickle=True).tolist() == obj.tolist())
except OSError as e:
    print("object", "OSError", e.errno)
try:
    with open("/npy/two.npy", "wb") as f:
        np.save(f, cases["plain"])
        np.save(f, cases["large"])
    with open("/npy/two.npy", "rb") as f:
        print("two", same(np.load(f), cases["plain"]) and same(np.load(f), cases["large"]))
except OSError as e:
    print("two", "OSError", e.errno)
np.savez("/npy/z.npz", x=cases["plain"], y=cases["record"])
with np.load("/npy/z.npz") as z:
    print("npz", same(z["x"], cases["plain"]) and same(z["y"], cases["record"]))
try:
    np.save("/npy/masked.npy", np.ma.masked_array([1, 2, 3], mask=[False, True, False]))
    back = np.load("/npy/masked.npy")
    print("masked", "saved", back, type(back).__name__)
except Exception as e:
    print("masked", type(e).__name__, e)
np.save("/npy/short.npy", cases["plain"])
with open("/npy/short.npy", "r+b") as f:
    f.truncate(os.path.getsize("/npy/short.npy") - 1)
try:
    np.load("/npy/short.npy")
    print("truncated", "loaded")
except Exception as e:
    print("truncated", type(e).__name__)
"""


@pytest.mark.parametrize("which", ["snapshot", "plain"])
def test_npy_files_round_trip(guest, which) -> None:
    """Guards a change (spec 021, the first carried patch): `np.save` and `np.load` of real files
    raised OSError 58, because numpy's `tofile` and `fromfile` need `os.dup`, which WASI lacks.
    The object array and `.npz` always worked and guard. A masked array saved to a path raises
    native's NotImplementedError, where patch 0001 first wrote its data and dropped its mask; a
    truncated file raises ValueError, native's type, with numpy's in-memory message, a documented
    difference (spec 051, Decision 10)."""
    r = guest(which, ["-c", NPY])
    assert r.exit_code == 0, r.describe()
    names = ["plain", "record", "0-d", "fortran", "large", "empty", "object", "two", "npz"]
    want = "".join(f"{n} True\n" for n in names)
    want += "masked NotImplementedError MaskedArray.tofile() not implemented yet.\n"
    want += "truncated ValueError\n"
    assert r.text == want, r.text


# Spec 033: the zip keeps each distribution's METADATA, so a package that asks for its own
# version gets it. A later specification that adds a distribution adds it here.
DISTRIBUTIONS = (
    "attrs",
    "beautifulsoup4",
    "charset-normalizer",
    "cloudpickle",
    "contourpy",
    "cycler",
    "defusedxml",
    "et-xmlfile",
    "fonttools",
    "html5lib",
    "jinja2",
    "joblib",
    "kiwisolver",
    "lxml",
    "markupsafe",
    "matplotlib",
    "more-itertools",
    "mpmath",
    "narwhals",
    "networkx",
    "numpy",
    "openpyxl",
    "packaging",
    "pandas",
    "patsy",
    "pillow",
    "pyparsing",
    "pypdf",
    "python-dateutil",
    "pyyaml",
    "regex",
    "reportlab",
    "scikit-learn",
    "scipy",
    "seaborn",
    "six",
    "soupsieve",
    "sympy",
    "tabulate",
    "threadpoolctl",
    "tomli-w",
    "toolz",
    "tqdm",
    "typing-extensions",
    "tzdata",
    "webencodings",
    "xlrd",
    "xlsxwriter",
    "xmltodict",
)  # specs: matplotlib and its distributions 023; lxml 046; tier A 039; contourpy 043; scipy 037;
# scikit-learn 044; seaborn and reportlab 042

METADATA = """
import json, re
import importlib.metadata as md
import numpy, pandas
dists = sorted(
    (re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(), d.version) for d in md.distributions()
)
print(json.dumps({
    "version": [md.version("numpy"), md.version("pandas")],
    "__version__": [numpy.__version__, pandas.__version__],
    "distributions": dists,
    "files": md.files("numpy"),
}))
"""


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_packages_carry_their_metadata(guest, which) -> None:
    """`importlib.metadata` finds each distribution in the zip at its MANIFEST version. `files()`
    is None: the zip keeps METADATA and entry_points.txt, never RECORD, which would list `.py`
    files the zip does not hold (spec 033, Decision 1)."""
    r = guest(which, ["-c", METADATA])
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    m = paths.parse_manifest((paths.artifact_dir() / "MANIFEST").read_text())
    want = [m.packages.get("numpy"), m.packages.get("pandas")]
    assert got["version"] == want, f"importlib.metadata says {got['version']}, MANIFEST {want}"
    assert got["__version__"] == want, f"__version__ is {got['__version__']}, MANIFEST {want}"
    dists = [[name, m.packages.get(name)] for name in DISTRIBUTIONS]
    assert got["distributions"] == dists, f"distributions {got['distributions']}, want {dists}"
    assert got["files"] is None, f"files('numpy') is {got['files']!r}: RECORD is not kept"


# Spec 033, Decision 5: the stand-in names and sizes wasm32's C types, gives numpy the dtype it
# gives a real one, and refuses every foreign call. The names are what sympy and threadpoolctl
# import, written here by name; the sizes are the guest's own sysconfig. Spec 038, Decision 3: the
# numeric simple types and c_void_p hold values, so numpy's `ndarray.ctypes` works; nothing has
# an address and nothing is called.
CTYPES = """
import json, sysconfig
bad = []

def step(label, run, want=True):
    try:
        got = run()
    except Exception as e:
        bad.append(f"{label}: {type(e).__name__}: {e}")
    else:
        if got != want:
            bad.append(f"{label}: {got!r}, want {want!r}")

def refused(label, run):
    try:
        run()
    except OSError as e:
        if str(e) != "ctypes is unavailable on wasm32-wasi":
            bad.append(f"{label}: OSError {e}")
    except Exception as e:
        bad.append(f"{label}: {type(e).__name__}: {e}")
    else:
        bad.append(f"{label}: no error")

def clipboard():
    import pandas.io.clipboard
    return True

def sympys():
    from ctypes import c_long, sizeof
    return sizeof(c_long) > 0

import numpy as np, pandas as pd
import ctypes
step("import pandas.io.clipboard", clipboard)
step("sympy's names", sympys)
for bits in (8, 16, 32, 64):
    for name in (f"c_int{bits}", f"c_uint{bits}"):
        step(name, lambda name=name: ctypes.sizeof(getattr(ctypes, name)) * 8, bits)

def declare():
    class Info(ctypes.Structure):
        _fields_ = [("name", ctypes.c_char * 16), ("p", ctypes.c_void_p), ("s", ctypes.c_char_p)]
    return Info

step("threadpoolctl's names", lambda: isinstance(ctypes.DEFAULT_MODE, int) and bool(declare()))
def find_library():
    from ctypes.util import find_library
    return find_library("c")

step("find_library", find_library, None)
sizes = (
    ("SIZEOF__BOOL", "c_bool"), ("SIZEOF_SHORT", "c_short"), ("SIZEOF_INT", "c_int"),
    ("SIZEOF_LONG", "c_long"), ("SIZEOF_LONG_LONG", "c_longlong"), ("SIZEOF_SIZE_T", "c_size_t"),
    ("SIZEOF_VOID_P", "c_char_p"), ("SIZEOF_VOID_P", "c_wchar_p"), ("SIZEOF_VOID_P", "c_void_p"),
    ("SIZEOF_WCHAR_T", "c_wchar"), ("SIZEOF_FLOAT", "c_float"), ("SIZEOF_DOUBLE", "c_double"),
    ("SIZEOF_LONG_DOUBLE", "c_longdouble"), ("SIZEOF_TIME_T", "c_time_t"),
)
for key, name in sizes:
    want = sysconfig.get_config_var(key)
    step(f"sizeof({name})", lambda name=name: ctypes.sizeof(getattr(ctypes, name)), want)
step(
    "sizeof(POINTER(c_int))",
    lambda: ctypes.sizeof(ctypes.POINTER(ctypes.c_int)),
    sysconfig.get_config_var("SIZEOF_VOID_P"),
)
step("sizeof(c_char * 16)", lambda: ctypes.sizeof(ctypes.c_char * 16), 16)
step("c_int is c_long", lambda: ctypes.c_int is ctypes.c_long)
step("c_int32 is c_long", lambda: ctypes.c_int32 is ctypes.c_long)
step("dtype(c_double)", lambda: np.dtype(ctypes.c_double) == np.float64)
step("dtype(c_long)", lambda: np.dtype(ctypes.c_long) == np.int32)
step("dtype(c_int32 be)", lambda: np.dtype(ctypes.c_int32.__ctype_be__) == np.dtype(">i4"))
step("as_ctypes_type", lambda: np.ctypeslib.as_ctypes_type(np.int32) is ctypes.c_long)
step("hasattr(np, 'ctypeslib')", lambda: hasattr(np, "ctypeslib"))

# Introspection with numpy loaded (review 033, finding 1): help() and np.info read every base.
import io, pydoc

def helped(thing):
    out = io.StringIO()
    pydoc.Helper(output=out).help(thing)
    return "ctypes" in out.getvalue()

def info(thing):
    out = io.StringIO()
    np.info(thing, output=out)
    return bool(out.getvalue())

step("help(ctypes)", lambda: helped(ctypes))
step("pydoc.render_doc(ctypes.c_int)", lambda: "c_long" in pydoc.render_doc(ctypes.c_int))
step("pydoc.render_doc(numpy.ctypeslib)", lambda: "ctypeslib" in pydoc.render_doc(np.ctypeslib))
step("np.info(ctypes.c_int)", lambda: info(ctypes.c_int))
frame = pd.DataFrame({"a": [1, 2, 3]})
arr = np.arange(3)
step("ndarray.ctypes.data", lambda: arr.ctypes.data == arr.__array_interface__["data"][0])
step("c_int(1)", lambda: ctypes.c_int(1).value, 1)
step("c_ulong(-1)", lambda: ctypes.c_ulong(-1).value, 2**32 - 1)
refused("data_as(POINTER(c_double))", lambda: arr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)))
refused("ndarray.ctypes.shape", lambda: arr.ctypes.shape)
refused("from_dataframe", lambda: pd.api.interchange.from_dataframe(frame.__dataframe__()))
refused("CDLL(None)", lambda: ctypes.CDLL(None))
refused("c_char_p(b'x')", lambda: ctypes.c_char_p(b"x"))
refused("Structure()", lambda: declare()())
refused("byref", lambda: ctypes.byref(None))
refused("byref(c_int(1))", lambda: ctypes.byref(ctypes.c_int(1)))
refused("addressof(c_void_p(8))", lambda: ctypes.addressof(ctypes.c_void_p(8)))
refused("from_buffer", lambda: ctypes.c_int.from_buffer(b""))
refused("dtype(Structure)", lambda: np.dtype(declare()))
refused("WinError", lambda: ctypes.WinError())
try:
    import ctypes.wintypes
    bad.append("ctypes.wintypes imported")
except ImportError:
    pass
print(json.dumps(bad))
"""


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_ctypes_stand_in_names_what_packages_import(guest, which) -> None:
    """The names sympy, threadpoolctl and pandas' clipboard import resolve; each C type's size is
    the guest's sysconfig; numpy's dtypes are numpy's own for a real type, never dtype('O'); and
    every call that would reach C raises OSError (spec 033, Decision 5). A numeric value and a
    `c_void_p` are held, so `ndarray.ctypes.data` is the array's address; what needs an address
    or a typed pointer still raises (spec 038, Decision 3)."""
    r = guest(which, ["-c", CTYPES])
    assert r.exit_code == 0, r.describe()
    bad = json.loads(r.text)
    assert bad == [], "; ".join(bad)


# Spec 051, Decision 4: the minimum coverage, set from the frozen set's 3,072 / 1,125 / 1,990
# with room, so a toolchain change cannot make the scan pass by finding nothing.
CALLBACK_MINIMUMS = {"arrays": 2_500, "getsets": 1_000, "singles": 1_500}


def test_callbacks_have_the_types_cpython_calls(artifacts, note) -> None:
    """Every C callback in a table something points at (method arrays, code-referenced single
    method definitions, getset arrays) has the wasm type CPython calls it with; a mismatch traps
    the guest at its first call (spec 051, Decision 4). Read from the plain binary: the snapshot is
    the same code and the same table. Its coverage is the pass's reason in latest.json."""
    needs.need("plain binary")
    from harness import callbacks, wasm

    report = callbacks.scan(wasm.parse_file(artifacts.binary("plain")))
    found = callbacks.findings(report)
    short = [
        f"{k} {report.coverage[k]} < {floor}"
        for k, floor in CALLBACK_MINIMUMS.items()
        if report.coverage[k] < floor
    ]
    assert not found and not short, (
        f"{len(found)} callback mismatches: {'; '.join(found)}"
        + (f"; coverage below its minimum: {', '.join(short)}" if short else "")
        + f" (scanned {report.summary()})"
    )
    note(f"scanned {report.summary()}")


# Spec 096, check 3: the slot scan's minimums, set from main's set (481 types, 454 specs, 149
# module definitions, 5,360 functions) with room; its bounds (0 unreferenced type candidates, at
# most 1 type named at run time); and the records it must read, one or more per compiled package,
# so one package's tables cannot vanish under the minimums (the pre-build review's F2).
SLOT_MINIMUMS = {"types": 400, "specs": 380, "modules": 120, "functions": 4_500}
SLOT_MAXIMUMS = {"unreferenced type candidates": 0, "types named at run time": 1}
KIWI_SPECS = {f"kiwisolver.{t}" for t in ("Constraint", "Expression", "Term", "Variable")}
SLOT_NAMED = {
    "spec": KIWI_SPECS | {"pandas._libs.tslibs.timestamps._Timestamp"},
    "spec slot": {f"{k}.tp_clear" for k in KIWI_SPECS},
    "type": {"type", "numpy.ndarray", "ImagingCore", "lxml.etree._Element"},
    "module": {"_regex", "ft2font"},
}


def test_type_slots_have_the_types_cpython_calls(artifacts, note) -> None:
    """Every function CPython calls through a static type object's slots and method suites, a
    `PyType_Slot` array or a static module definition has the wasm type CPython calls it with
    (spec 096): a mismatch traps the guest at its first call, as kiwisolver's `void` tp_clear did
    at every garbage collection that met one. Every dropped record is counted by its reason, the
    coverage meets its minimums and bounds, and the named records were read. Read from the plain
    binary; its coverage is the pass's reason in latest.json."""
    needs.need("plain binary")
    from harness import callbacks, wasm

    report = callbacks.scan_slots(wasm.parse_file(artifacts.binary("plain")))
    problems = callbacks.slot_verdict(report, SLOT_MINIMUMS, SLOT_MAXIMUMS, SLOT_NAMED)
    assert not problems, (
        f"{len(problems)} slot problems: {'; '.join(problems)} (scanned {report.summary()})"
    )
    note(f"scanned {report.summary()}")


def _job_on(guest, which: str, job: str):
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes()}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    files["/out/.keep"] = b""
    r = guest(which, [f"/jobs/{job}.py", "/data", "/out"], files=files)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    return jobs.render(r.stdout, r.root / "out")


@pytest.mark.slow
@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_callbacks_job_matches_native(guest, which) -> None:
    """`copy.copy` of numpy scalars, `a.dtype = …`, and the scan's private findings called in the
    guest give native's output; each trapped the guest before patch 0002 (spec 051, Decision 5)."""
    why = jobs.compare(
        jobs.expected_path("callbacks").read_bytes(), _job_on(guest, which, "callbacks")
    )
    assert why is None, why


# Spec 051, Decision 9: the warning's fourth line is the caller's; pandas' find_stack_level skips
# the frames whose code names a file under pandas' own folder.
WARN = """import io, json, os, warnings; warnings.simplefilter("always")
import pandas as pd
with warnings.catch_warnings(record=True) as w:
    pd.read_csv(io.StringIO("a;b\\n1;2\\n"), sep=None)
code = pd.core.frame.DataFrame.__init__.__code__.co_filename
print(json.dumps({
    "warnings": [[x.category.__name__, x.filename, x.lineno] for x in w],
    "co_filename": code,
    "rule": os.path.dirname(pd.__file__) + "/core/frame.py",
}))
"""


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_a_pandas_warning_names_the_callers_line(guest, which) -> None:
    """A pandas warning points at the user's line, as natively: the zip's code objects carry the
    path zipimport gives the module (`/usr/local/lib/python3XY.zip/<member>.py`), so pandas'
    `find_stack_level` recognises its own frames (spec 051, Decisions 6 to 9)."""
    r = guest(which, ["/job/warn.py"], files={"/job/warn.py": WARN.encode()})
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    assert got["warnings"] == [["ParserWarning", "/job/warn.py", 4]], got["warnings"]
    assert got["co_filename"] == got["rule"], got


ZIP_NAMES = """
import json, marshal, sys, zipfile
archive = next(p for p in sys.path if p.endswith(".zip"))
codes, bad = 0, []

def walk(code, want):
    global codes
    codes += 1
    if code.co_filename != want and len(bad) < 5:
        bad.append(f"{want}: {code.co_name} names {code.co_filename}")
    for c in code.co_consts:
        if hasattr(c, "co_filename"):
            walk(c, want)

with zipfile.ZipFile(archive) as z:
    names = [n for n in z.namelist() if n.endswith(".pyc")]
    for n in names:
        walk(marshal.loads(z.read(n)[16:]), archive + "/" + n[:-1])
print(json.dumps({"archive": archive, "pyc": len(names), "codes": codes, "bad": bad}))
"""


def test_zip_code_objects_carry_the_zip_path(guest) -> None:
    """Every code object in every `.pyc` of the zip, nested ones included, names its file as
    zipimport would name a source in the same zip: the archive's path, a slash, the member less
    its `c` (spec 051, Decision 7; criterion 2)."""
    r = guest("plain", ["-c", ZIP_NAMES], record=False)
    assert r.exit_code == 0, r.describe()
    got = json.loads(r.text)
    assert got["pyc"] > 1000 and not got["bad"], got


# numpy's own floating-point signals, kept in software (spec 099). wasm has no floating-point
# status flags; recipes/npy_fenv_flags.h gives numpy's flags bits and one flag word, so what numpy
# raises itself reaches np.errstate. Each program prints one line per case; the expected text is
# native numpy's (checks 1 and 2) or the README's documented silence (check 3).
SINGULAR = """
import numpy as np

S = np.array([[1.0, 2.0], [2.0, 4.0]])  # singular: LU's second pivot is exactly 0
N = np.array([[1.0, 2.0], [2.0, 1.0]])  # symmetric, not positive definite


def case(name, fn):
    try:
        fn()
        print(name, "returned")
    except np.linalg.LinAlgError as e:
        print(name, "LinAlgError", e)


case("inv", lambda: np.linalg.inv(S))
case("inv float32", lambda: np.linalg.inv(S.astype(np.float32)))
case("inv complex128", lambda: np.linalg.inv(S.astype(np.complex128)))
case("inv stacked", lambda: np.linalg.inv(np.stack([np.eye(2), S])))
case("solve", lambda: np.linalg.solve(S, np.array([1.0, 1.0])))
case("solve matrix", lambda: np.linalg.solve(S, np.eye(2)))
case("tensorinv", lambda: np.linalg.tensorinv(S, ind=1))
case("tensorsolve", lambda: np.linalg.tensorsolve(S, np.array([1.0, 1.0])))
case("matrix_power -1", lambda: np.linalg.matrix_power(S, -1))
case("cholesky", lambda: np.linalg.cholesky(N))
case("cholesky upper", lambda: np.linalg.cholesky(N, upper=True))
with np.errstate(all="ignore"):
    case("inv under errstate ignore", lambda: np.linalg.inv(S))
print("det", np.linalg.det(S))
print("slogdet", *np.linalg.slogdet(S))
print("inv regular", np.linalg.inv(np.array([[2.0, 1.0], [1.0, 1.0]])).tolist())
print("errstate after", np.geterr())
"""

SINGULAR_NATIVE = """\
inv LinAlgError Singular matrix
inv float32 LinAlgError Singular matrix
inv complex128 LinAlgError Singular matrix
inv stacked LinAlgError Singular matrix
solve LinAlgError Singular matrix
solve matrix LinAlgError Singular matrix
tensorinv LinAlgError Singular matrix
tensorsolve LinAlgError Singular matrix
matrix_power -1 LinAlgError Singular matrix
cholesky LinAlgError Matrix is not positive definite
cholesky upper LinAlgError Matrix is not positive definite
inv under errstate ignore LinAlgError Singular matrix
det 0.0
slogdet 0.0 -inf
inv regular [[1.0, -1.0], [-1.0, 2.0]]
errstate after {'divide': 'warn', 'over': 'warn', 'under': 'ignore', 'invalid': 'warn'}
"""

SIGNAL_CASE = """
import warnings

import numpy as np


def case(name, fn):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            fn()
            got = "returned"
        except FloatingPointError as e:
            got = f"FloatingPointError {e}"
    said = [f"{x.category.__name__} {x.message}" for x in w]
    print(name, got, *(["warns", *said] if said else ["silent"]))

"""

OWN_SIGNALS = (
    SIGNAL_CASE
    + """
i64 = np.array([1, 2], dtype=np.int64)
case("int floor_divide by 0", lambda: i64 // 0)
case("int remainder by 0", lambda: i64 % 0)
case("int divmod by 0", lambda: np.divmod(i64, 0))
case("int32 min floor_divide -1", lambda: np.array([-(2**31)], dtype=np.int32) // -1)
case("timedelta floor_divide 0", lambda: np.array([10], dtype="m8[s]") // np.timedelta64(0, "s"))
case("float64 to float16 overflow", lambda: np.array([1e6]).astype(np.float16))
case("int scalar floor_divide 0", lambda: np.int64(1) // np.int64(0))
case("int8 scalar add overflow", lambda: np.int8(127) + np.int8(1))
with np.errstate(divide="raise"):
    case("int floor_divide by 0 under raise", lambda: i64 // 0)
with np.errstate(over="raise"):
    case("float16 overflow under raise", lambda: np.array([1e6]).astype(np.float16))
with np.errstate(divide="ignore"):
    case("int floor_divide by 0 under ignore", lambda: i64 // 0)
"""
)

OWN_SIGNALS_NATIVE = "".join(
    line + "\n"
    for line in (
        "int floor_divide by 0 returned warns RuntimeWarning divide by zero encountered in"
        " floor_divide",
        "int remainder by 0 returned warns RuntimeWarning divide by zero encountered in remainder",
        "int divmod by 0 returned warns RuntimeWarning divide by zero encountered in divmod",
        "int32 min floor_divide -1 returned warns RuntimeWarning overflow encountered in"
        " floor_divide",
        "timedelta floor_divide 0 returned warns RuntimeWarning divide by zero encountered in"
        " floor_divide",
        "float64 to float16 overflow returned warns RuntimeWarning overflow encountered in cast",
        "int scalar floor_divide 0 returned warns RuntimeWarning divide by zero encountered in"
        " scalar floor_divide",
        "int8 scalar add overflow returned warns RuntimeWarning overflow encountered in scalar add",
        "int floor_divide by 0 under raise FloatingPointError divide by zero encountered in"
        " floor_divide silent",
        "float16 overflow under raise FloatingPointError overflow encountered in cast silent",
        "int floor_divide by 0 under ignore returned silent",
    )
)

HARDWARE_SIGNALS = (
    SIGNAL_CASE
    + """
one = np.array([1.0])
case("float divide by 0", lambda: one / 0.0)
case("float floor_divide by 0", lambda: one // 0.0)
case("log 0", lambda: np.log(np.array([0.0])))
case("sqrt -1", lambda: np.sqrt(np.array([-1.0])))
case("exp 1000", lambda: np.exp(np.array([1000.0])))
case("nan to int64", lambda: np.array([np.nan]).astype(np.int64))
case("float scalar divide by 0", lambda: np.float64(1.0) / np.float64(0.0))
with np.errstate(all="raise"):
    case("float divide by 0 under raise", lambda: one / 0.0)
"""
)

HARDWARE_SIGNALS_GUEST = """\
float divide by 0 returned silent
float floor_divide by 0 returned silent
log 0 returned silent
sqrt -1 returned silent
exp 1000 returned silent
nan to int64 returned silent
float scalar divide by 0 returned silent
float divide by 0 under raise returned silent
"""


def _signals(guest, which: str, code: str) -> str:
    r = guest(which, ["-c", code], root_writable=False)
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    return r.text


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_a_singular_matrix_raises_linalgerror(guest, which) -> None:
    """numpy.linalg raises LinAlgError for an exactly singular matrix and for one that is not
    positive definite, as natively (spec 099, check 1): umath_linalg reports LAPACK's failure by
    the invalid flag, which the recipe header keeps in software. Both matrices meet an exact zero or
    negative pivot in any LAPACK, so the check is clear of the lapack_lite and OpenBLAS divergence
    (Decision 6) and holds on spec 100's OpenBLAS too. The last four lines are controls."""
    got = _signals(guest, which, SINGULAR)
    assert got == SINGULAR_NATIVE, got


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_numpys_own_floating_point_signals_reach_errstate(guest, which) -> None:
    """The signals numpy raises itself, in software, warn or raise under np.errstate as natively
    (spec 099, check 2): integer division by zero and overflow in division, timedelta division by
    zero, and float16 overflow (the C++ half of the recipe, through cpp_args). The scalar lines
    are controls: scalar math returns its codes and warned before spec 099 too."""
    got = _signals(guest, which, OWN_SIGNALS)
    assert got == OWN_SIGNALS_NATIVE, got


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_hardware_floating_point_signals_stay_silent_as_documented(guest, which) -> None:
    """What only the hardware would signal stays silent, as the README's bullet "No floating-point
    status flags in wasm" says (spec 099, check 3, Decision 6): float division by zero, log(0),
    sqrt(-1), exp(1000), a nan cast to an integer and a scalar division give native's values with
    no warning, and errstate(all="raise") does not raise. Natively every line warns. It shows the
    recipe changed only numpy's own signals; a toolchain with real wasm flags turns it red together
    with the header's #error."""
    got = _signals(guest, which, HARDWARE_SIGNALS)
    assert got == HARDWARE_SIGNALS_GUEST, got
