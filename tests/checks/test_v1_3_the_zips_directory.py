"""v1.3: the zip's directory is read once (spec 035). The stdlib's own import and resource
machinery works, and is cheap: a start reads the zip's directory through the reactor's own
reader, which gives zipimport's dict; resource reads and metadata answer from that one parse.

Slopes are (fuel on padded.zip − fuel on small.zip) ÷ (their member counts' difference), plain
only: the snapshot runs only beside its own zip (spec 003). Each check runs its measured program
last, on small.zip (plain) or on the artifact zip (snapshot), so that is its fuel metric."""

from __future__ import annotations

import json

import pytest

from harness import needs, paths, zips

pytestmark = pytest.mark.goal("v1.3")

ZIP = "/usr/local/lib/python315.zip"


@pytest.fixture(scope="session")
def judge_zips() -> zips.JudgeZips:
    needs.need("artifact dir", "stdlib zip")
    d = paths.artifact_dir()
    assert d is not None
    return zips.judge_zips(d / "python-stdlib.zip")


def _json(r) -> dict:
    assert r.exit_code == 0, r.describe()
    return json.loads(r.text)


GATE = """
import json, sys, zipimport, _frozen_importlib_external as ext
import _zip_directory as zd
served = dict(zd.served)
print(json.dumps({
    "served": served,
    "reader": zipimport._read_directory is zd.read_directory,
    "encodings": isinstance(sys.modules["encodings"].__spec__.loader, zipimport.zipimporter),
    "origin": zd.__spec__.origin,
    "zipimport": zipimport.__file__,
    "external": ext.__spec__.loader_state.filename,
}))
"""


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_the_zip_reader_is_ours_from_the_first_import(guest, which) -> None:
    """The gate (criterion 1): the start's own read of the zip, which imports `encodings`, went
    through `_zip_directory`, and the modules the core phase imports keep their file names."""
    got = _json(guest(which, ["-c", GATE]))
    assert got == {
        "served": {ZIP: "fast"},
        "reader": True,
        "encodings": True,
        "origin": "frozen",
        "zipimport": f"{ZIP}/zipimport.py",
        "external": f"{ZIP}/importlib/_bootstrap_external.py",
    }, got


def test_a_plain_start_grows_at_most_30k_fuel_per_member(guest, judge_zips, note) -> None:
    padded = guest("plain", ["-c", "pass"], stdlib=judge_zips.padded)
    small = guest("plain", ["-c", "pass"], stdlib=judge_zips.small)
    assert padded.exit_code == 0 and small.exit_code == 0, (padded.describe(), small.describe())
    slope = judge_zips.slope(small.fuel, padded.fuel)
    note(f"{slope:,.0f} fuel per member; small.zip {small.fuel:,}, padded.zip {padded.fuel:,}")
    assert slope <= 30_000, f"a plain start grows {slope:,.0f} fuel per member (bound 30,000)"


READER = """
import json, sys, importlib, zipimport
import _zip_directory as zd

def outcome(read, path):
    try:
        return ["ok", list(read(path).items())]
    except Exception as e:
        return ["error", type(e).__name__, str(e)]

path, module = sys.argv[1], sys.argv[2]
fast = outcome(zd.read_directory, path)
served = zd.served.get(path)
stock = outcome(zd.stock_read_directory, path)
who = None
if module:
    sys.path.insert(0, path)
    who = importlib.import_module(module).WHO
print(json.dumps({
    "equal": fast == stock,
    "served": served,
    "outcome": fast[0] if fast[0] == "ok" else fast,
    "names": len(fast[1]) if fast[0] == "ok" else None,
    "who": who,
    "zip_served": zd.served.get(path),
}))
"""

SNAPSHOT_CACHE = """
import json, sys, zipimport
import _zip_directory as zd
path = sys.path[0]
cached = list(zipimport._zip_directory_cache[path].items())
print(json.dumps({"equal": cached == list(zd.stock_read_directory(path).items()),
                  "names": len(cached)}))
"""

# The odd zips: (the module the check imports from it, what serves its read).
ODD = {
    "zip64": ("zip64_mod", "stock", "zip64"),
    "cp437": (zips.CP437_MODULE, "stock", "cp437"),
    "explicit_dirs": ("xdir.sub.m", "fast", "explicit"),
    "prepended": ("pre_mod", "fast", "prepended"),
    "truncated": ("", "stock", None),
}


@pytest.mark.parametrize("case", ["small", "padded", *ODD, "snapshot"])
def test_the_fast_reader_builds_zipimports_dict(guest, judge_zips, case) -> None:
    """`read_directory` gives zipimport's own dict (keys, values and order) on the judge's zips
    and on odd ones; Zip64, cp437 names and a broken directory go to zipimport's reader, with
    its result or its error (criterion 3)."""
    if case == "snapshot":
        got = _json(guest("snapshot", ["-c", SNAPSHOT_CACHE]))
        assert got["equal"] and got["names"] > 1000, got
        return
    if case in ("small", "padded"):
        stdlib = judge_zips.small if case == "small" else judge_zips.padded
        got = _json(guest("plain", ["-c", READER, ZIP, ""], stdlib=stdlib))
        assert got["equal"] and got["served"] == "fast", got
        return
    module, route, who = ODD[case]
    data = zips.ODD_ZIPS[case]()
    if case == "zip64":
        zips.check_zip64(data)
    if case == "cp437":
        zips.check_cp437(data)
    path = f"/zips/{case}.zip"
    got = _json(guest("plain", ["-c", READER, path, module], files={path: data}))
    assert got["equal"] and got["served"] == route and got["who"] == who, got
    if case == "truncated":  # zipimport's own error, from both: EOFError in 3.15
        assert got["outcome"][0] == "error", got
    else:
        assert got["outcome"] == "ok" and got["zip_served"] == route, got


def test_a_reread_after_invalidate_caches_is_the_fast_read(guest, judge_zips, note) -> None:
    """Agent code that writes a module calls `importlib.invalidate_caches()`; the import after it
    reads the zip's directory again, through the same reader (criterion 8)."""
    reread = (
        "import importlib, json, _zip_directory as zd\n"
        "zd.served.clear()\n"
        "importlib.invalidate_caches()\n"
        "import json.tool\n"
        "print(json.dumps(zd.served))\n"
    )
    plain = "import json.tool\n"
    fuel = {}
    for name, stdlib in (("padded", judge_zips.padded), ("small", judge_zips.small)):
        y = guest("plain", ["-c", plain], stdlib=stdlib)
        x = guest("plain", ["-c", reread], stdlib=stdlib)
        assert y.exit_code == 0, y.describe()
        assert json.loads(x.text if x.exit_code == 0 else "null") == {ZIP: "fast"}, x.describe()
        fuel[name] = x.fuel - y.fuel
    slope = judge_zips.slope(fuel["small"], fuel["padded"])
    note(f"{slope:,.0f} fuel per member; the re-read on small.zip {fuel['small']:,}")
    assert slope <= 30_000, f"the re-read grows {slope:,.0f} fuel per member (bound 30,000)"
