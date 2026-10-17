"""v1.3: numpy and pandas are inside, and their results match native Python at the same pins."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from harness import jobs, needs, paths

pytestmark = pytest.mark.goal("v1.3")


def _run_job(guest, job: str):
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes()}
    files.update({f"/data/{n}": src.read_bytes() for n, src in jobs.DATA.items()})
    files["/out/.keep"] = b""
    r = guest("plain", [f"/jobs/{job}.py", "/data", "/out"], files=files)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    return jobs.render(r.stdout, r.root / "out")


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
    why = jobs.compare(jobs.expected_path("numpy_csv").read_bytes(), _run_job(guest, "numpy_csv"))
    assert why is None, why


@pytest.mark.slow
def test_pandas_csv_job_matches_native(guest) -> None:
    why = jobs.compare(jobs.expected_path("pandas_csv").read_bytes(), _run_job(guest, "pandas_csv"))
    assert why is None, why


@pytest.mark.slow
def test_random_matches_native(guest) -> None:
    out = _run_job(guest, "numpy_random")
    why = jobs.compare(jobs.expected_path("numpy_random").read_bytes(), out)
    assert why is None, why


@pytest.mark.slow
def test_compress_job_matches_native(guest) -> None:
    """bz2, lzma and tarfile write the same bytes as native (spec 007)."""
    why = jobs.compare(jobs.expected_path("compress").read_bytes(), _run_job(guest, "compress"))
    assert why is None, why


@pytest.mark.slow
def test_sqlite_job_matches_native(guest) -> None:
    """sqlite3 on a file, with a forced spill to temporary files, and pandas' to_sql and read_sql
    give native's results (spec 007)."""
    why = jobs.compare(jobs.expected_path("sqlite").read_bytes(), _run_job(guest, "sqlite"))
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
    stated = re.findall(r"default\s+integer\s+is\s+(\d+)-bit", paths.README.read_text())
    assert stated and set(stated) == {bits}, (
        f"the guest's default integer is {bits}-bit; README says {stated}"
    )


def test_snapshot_preimports_the_stack(guest, metric) -> None:
    probe = "import sys; print('numpy' in sys.modules, 'pandas' in sys.modules)"
    r = guest("snapshot", ["-c", probe])
    assert r.text.strip() == "True True", f"pre-imported: {r.text.strip()!r}; {r.describe()}"
    plain = guest("plain", ["-c", "import pandas"], record=False)
    snap = guest("snapshot", ["-c", "import pandas"])
    assert plain.exit_code == 0 and snap.exit_code == 0, f"{plain.describe()} / {snap.describe()}"
    assert snap.fuel * 10 < plain.fuel, f"snapshot fuel {snap.fuel}, plain fuel {plain.fuel}"


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
        first = jobs.run_native(job, 0, workdir)
        second = jobs.run_native(job, 1, workdir)
        assert jobs.compare(first, second) is None, f"{job}: two hash seeds disagree"
        why = jobs.compare(jobs.expected_path(job).read_bytes(), first)
        assert why is None, f"{job}: {why}"
