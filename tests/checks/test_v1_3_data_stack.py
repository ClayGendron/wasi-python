"""v1.3: numpy and pandas are inside, and their results match native Python at the same pins."""

from __future__ import annotations

import re

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


def test_longdouble_parses(guest) -> None:
    code = (
        "import numpy as np\n"
        "x = np.longdouble('0.1')\n"
        "print(np.finfo(np.longdouble).bits, x > 0, str(np.longdouble(1) / 3)[:8])\n"
    )
    r = guest("plain", ["-c", code])
    assert r.exit_code == 0, r.describe()
    assert r.text.strip() == "128 True 0.333333", r.text.strip()


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
    stated = re.findall(r"default integer is (\d+)-bit", paths.README.read_text())
    assert stated == [bits], f"the guest's default integer is {bits}-bit; README says {stated}"


def test_snapshot_preimports_the_stack(guest, metric) -> None:
    probe = "import sys; print('numpy' in sys.modules, 'pandas' in sys.modules)"
    r = guest("snapshot", ["-c", probe])
    assert r.text.strip() == "True True", f"pre-imported: {r.text.strip()!r}; {r.describe()}"
    plain = guest("plain", ["-c", "import pandas"], record=False)
    snap = guest("snapshot", ["-c", "import pandas"])
    assert plain.exit_code == 0 and snap.exit_code == 0, f"{plain.describe()} / {snap.describe()}"
    assert snap.fuel * 10 < plain.fuel, f"snapshot fuel {snap.fuel}, plain fuel {plain.fuel}"


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
