"""v1.3: the zip's directory is read once. The stdlib's own import and resource
machinery works, and is cheap: a start reads the zip's directory through the reactor's own
reader, which gives zipimport's dict; resource reads and metadata answer from that one parse.

Slopes are (fuel on padded.zip − fuel on small.zip) ÷ (their member counts' difference), plain
only: the snapshot runs only beside its own zip. Each check runs its measured program
last, on small.zip (plain) or on the artifact zip (snapshot), so that is its fuel metric."""

from __future__ import annotations

import json
import zipfile

import pytest

from harness import jobs, needs, paths, zips

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
    "resources": zipimport.zipimporter.get_resource_reader is zd.get_resource_reader,
    "metadata": ext.PathFinder.find_distributions is zd.find_distributions,
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
        "resources": True,
        "metadata": True,
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


ZONES = "import zoneinfo, importlib.resources\n"
PARIS = ZONES + "zoneinfo.ZoneInfo('Europe/Paris')\n"
TOKYO = PARIS + "zoneinfo.ZoneInfo('Asia/Tokyo')\n"


def _fuel(guest, which: str, code: str, **kw) -> int:
    r = guest(which, ["-c", code], **kw)
    assert r.exit_code == 0, r.describe()
    return r.fuel


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_a_zone_load_does_not_grow_with_the_zip(guest, judge_zips, note, which) -> None:
    """A first time zone reads its file through the reactor's resource reader, which answers from
    zipimport's dict, so it costs the same on any zip; a second zone costs its own file and its
    folder's import (criterion 4)."""
    if which == "snapshot":
        a, c, b = (_fuel(guest, which, code) for code in (ZONES, TOKYO, PARIS))
        note(f"Paris {b - a:,}; Tokyo after it {c - b:,}")
        assert b - a <= 15_000_000, f"a first zone costs {b - a:,} fuel on the snapshot (15 M)"
        assert c - b <= 2_000_000, f"a second zone costs {c - b:,} fuel (2 M)"
        return
    pa = _fuel(guest, which, ZONES, stdlib=judge_zips.padded)
    pb = _fuel(guest, which, PARIS, stdlib=judge_zips.padded)
    a = _fuel(guest, which, ZONES, stdlib=judge_zips.small)
    c = _fuel(guest, which, TOKYO, stdlib=judge_zips.small)
    b = _fuel(guest, which, PARIS, stdlib=judge_zips.small)
    slope = judge_zips.slope(b - a, pb - pa)
    note(f"Paris {b - a:,} (padded {pb - pa:,}, {slope:,.0f} per member); Tokyo {c - b:,}")
    assert max(b - a, pb - pa) <= 20_000_000, f"a first zone costs {b - a:,}, {pb - pa:,} (20 M)"
    assert slope <= 1_000, f"a first zone grows {slope:,.0f} fuel per member (1,000)"
    assert c - b <= 2_000_000, f"a second zone costs {c - b:,} fuel (2 M)"


RESOURCES = """
import importlib.resources as ir, json, posixpath, zipfile
Z = "/usr/local/lib/python315.zip"
zf = zipfile.ZipFile(Z)
names = zf.namelist()
zroot = zipfile.Path(zf)
bad = []

top = ir.files("tzdata").parent  # the zip's root, so pandas need not be imported

def ours(at):
    return top.joinpath(at)

def answers(p):
    return [p.is_file(), p.is_dir(), p.exists(), p.name, str(p)]

def error(run):
    try:
        run()
    except Exception as e:
        return type(e).__name__
    return None

root = ir.files("tzdata")
zones = 0
for name in names:
    if name.startswith("tzdata/zoneinfo/") and not name.endswith("/"):
        zones += 1
        if root.joinpath(name[len("tzdata/"):]).read_bytes() != zf.read(name):
            bad.append(["bytes", name])
entries = sorted({n for n in zroot.root.namelist() if n.startswith(("tzdata/", "pandas/"))})
dirs = ["tzdata/", "pandas/"] + [n for n in entries if n.endswith("/")]
for d in dirs:
    mine = sorted(c.name for c in ours(d).iterdir())
    theirs = sorted(c.name for c in zroot.joinpath(d).iterdir())
    if mine != theirs:
        bad.append(["iterdir", d, len(mine), len(theirs)])
odd = ["tzdata/missing", "tzdata/zoneinfo/UTC/", "tzdata/missing/", "tzdata/zoneinfo"]
for at in entries + odd:
    if answers(ours(at)) != answers(zroot.joinpath(at)):
        bad.append(["answers", at, answers(ours(at)), answers(zroot.joinpath(at))])
zi = "tzdata/zoneinfo/tzdata.zi"
for how in ("read_text", "rt", "r+"):
    read = {
        "read_text": lambda p: p.read_text(encoding="utf-8"),
        "rt": lambda p: p.open("rt").read(),
        "r+": lambda p: p.open("r+").read(),
    }[how]
    if read(ours(zi)) != read(zroot.joinpath(zi)):
        bad.append(["text", how])
for pwd in (None, b"k", "k"):  # zipfile.Path.open's keyword; a plain member ignores it
    for mode in ("rb", "r"):
        if ours(zi).open(mode, pwd=pwd).read() != zroot.joinpath(zi).open(mode, pwd=pwd).read():
            bad.append(["pwd", mode, repr(pwd)])
if ir.read_binary("tzdata.zoneinfo", "UTC") != zf.read("tzdata/zoneinfo/UTC"):
    bad.append(["read_binary"])
utc, tzd = "tzdata/zoneinfo/UTC", "tzdata/zoneinfo/"
cases = {
    "iterdir on a file": lambda p: list(p(utc).iterdir()),
    "open a missing name": lambda p: p("tzdata/missing").open("rb"),
    "open a directory": lambda p: p(tzd).open("rb"),
    "read_bytes a missing name": lambda p: p("tzdata/missing").read_bytes(),
    "open('w') a file": lambda p: p(utc).open("w"),
    "open('w') a directory": lambda p: p(tzd).open("w"),
    "open('rb', encoding=)": lambda p: p(utc).open("rb", encoding="utf-8"),
}
for k, run in cases.items():
    mine, theirs = error(lambda: run(ours)), error(lambda: run(zroot.joinpath))
    if mine != theirs or mine is None:
        bad.append(["error", k, mine, theirs])
kinds = [type(root).__name__, type(top).__name__]
print(json.dumps({"type": kinds, "zones": zones, "dirs": len(dirs), "entries": len(entries),
                  "bad": bad[:10]}))
"""

GUEST_ZIP = f"""
import importlib.resources as ir, io, json, sys, zipfile
Z = "/zips/res.zip"
sys.path.insert(0, Z)
zf = zipfile.ZipFile(Z)
pkg = ir.files("{zips.RESOURCE_PACKAGE}")
got = {{"type": type(pkg).__name__}}
got["lzma"] = pkg.joinpath("lzma.txt").read_bytes() == zf.read("{zips.RESOURCE_PACKAGE}/lzma.txt")
try:
    pkg.joinpath("badcrc.txt").read_bytes()
    got["badcrc"] = None
except Exception as e:
    got["badcrc"] = type(e).__name__
with pkg.joinpath("big.bin").open("rb") as f:
    got["stream"] = type(f).__name__
    chunks = iter(lambda: f.read(65536), b"")
    got["big"] = b"".join(chunks) == zf.read("{zips.RESOURCE_PACKAGE}/big.bin")
got["plain"] = pkg.joinpath("plain.txt").read_text(encoding="utf-8")
print(json.dumps(got))
"""


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_resources_read_as_zipfile_reads_them(guest, which) -> None:
    """Resources in a zip on the import path are the reactor's own `Traversable`, with
    `zipfile.Path`'s bytes, listings, answers and errors; a guest's zip whose member is not plain
    and small is read by `zipfile` itself, with its checks and its stream (criterion 5)."""
    if which == "plain":
        data = zips.resource_zip()
        zips.check_resource_zip(data)
        got = _json(guest(which, ["-c", GUEST_ZIP], files={"/zips/res.zip": data}))
        assert got == {
            "type": "ZipDirectoryPath",
            "lzma": True,
            "badcrc": "BadZipFile",
            "stream": "ZipExtFile",
            "big": True,
            "plain": "plain\n",
        }, got
    got = _json(guest(which, ["-c", RESOURCES]))
    assert got["type"] == ["ZipDirectoryPath"] * 2 and not got["bad"], got
    assert got["zones"] > 500 and got["dirs"] > 50 and got["entries"] > 1000, got


def _job(guest, which: str, job: str):
    files = {f"/jobs/{job}.py": jobs.script(job).read_bytes(), "/out/.keep": b""}
    r = guest(which, [f"/jobs/{job}.py", "/data", "/out"], files=files)
    assert r.exit_code == 0, f"{job}: {r.describe()}"
    (r.root / "out" / ".keep").unlink()
    return r, jobs.render(r.stdout, r.root / "out")


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_the_pandas_tz_job_matches_native(guest, note, which) -> None:
    """A Paris timestamp and a Tokyo range, read from `tzdata` as native reads them, print what
    native pandas prints; on the snapshot the job costs at most 60 M fuel beyond its imports
    (criterion 7; it cost 961 M when every zone read parsed the zip)."""
    base = _fuel(guest, which, "import pandas, zoneinfo, importlib.resources")
    r, out = _job(guest, which, "pandas_tz")
    why = jobs.compare(jobs.expected_path("pandas_tz").read_bytes(), out)
    assert why is None, why
    note(f"the job beyond its imports: {r.fuel - base:,} fuel")
    if which == "snapshot":
        assert r.fuel - base <= 60_000_000, f"the job costs {r.fuel - base:,} beyond its imports"


QUERY = "import importlib.metadata\n"
MISS = QUERY + (
    "try:\n"
    "    importlib.metadata.version('nope')\n"
    "except importlib.metadata.PackageNotFoundError:\n"
    "    pass\n"
)

METADATA = f"""
import importlib.metadata as md, json, zipfile
zf = zipfile.ZipFile("/usr/local/lib/python315.zip")
folders = sorted({{n.split("/", 1)[0] for n in zf.namelist()
                  if n.split("/", 1)[0].endswith(".dist-info")}})

def facts(d):
    files = d.files
    return {{
        "version": d.version,
        "metadata": sorted(d.metadata.items()),
        "entry_points": sorted([e.name, e.group, e.value] for e in d.entry_points),
        "files": None if files is None else [[str(p), p.hash and p.hash.value, p.size]
                                             for p in files],
        "requires": d.requires,
        "origin": repr(d.origin),
        "METADATA": d.read_text("METADATA"),
    }}

bad, kinds = [], set()
refs = [md.PathDistribution(zipfile.Path(zf, folder + "/")) for folder in folders]
for folder, ref in zip(folders, refs):
    ours = md.distribution(ref.metadata["Name"])
    kinds.add(type(ours._path).__name__)
    if facts(ours) != facts(ref):
        bad.append(folder)
found = sorted({{(d.metadata["Name"], d.version) for d in md.distributions()}})
want = sorted({{(d.metadata["Name"], d.version) for d in refs}})
group = "{zips.GROUP}"
points = sorted([e.name, e.value] for e in md.entry_points(group=group))
ref_points = sorted([e.name, e.value] for d in refs for e in d.entry_points.select(group=group))
print(json.dumps({{"folders": folders, "bad": bad, "kinds": sorted(kinds),
                  "distributions": found == want, "entry_points": [points, ref_points]}}))
"""


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_metadata_answers_from_the_zips_directory(guest, judge_zips, note, which) -> None:
    """`importlib.metadata` finds the distributions in a zip on the import path from zipimport's
    dict, with upstream's answers for each, and a miss does not parse the zip (criterion 6)."""
    stdlib = judge_zips.small if which == "plain" else None
    got = _json(guest(which, ["-c", METADATA], stdlib=stdlib))
    judge = ["judge_meta_a-1.0.dist-info", "judge_meta_b-2.0.dist-info"]
    assert len(got["folders"]) >= 5 and not got["bad"], got
    assert (set(judge) <= set(got["folders"])) == (which == "plain"), got["folders"]
    assert got["kinds"] == ["ZipDirectoryPath"] and got["distributions"], got
    points, ref_points = got["entry_points"]
    assert points == ref_points and len(points) == (2 if which == "plain" else 0), got
    if which == "snapshot":
        a, b = _fuel(guest, which, QUERY), _fuel(guest, which, MISS)
        # The miss splits every member's name (Decision 7), so its bound grows with the artifact
        # zip: 20 M at 1,758 members, plus 6,000 a member beyond them; the plain slope bound below
        # holds each member's cost.
        with zipfile.ZipFile(paths.artifact_dir() / "python-stdlib.zip") as z:
            members = len(z.infolist())
        bound = 20_000_000 + 6_000 * max(0, members - 1_758)
        note(f"a miss after the import: {b - a:,} fuel ({members:,} members, bound {bound:,})")
        assert b - a <= bound, f"a metadata miss costs {b - a:,} fuel on the snapshot ({bound:,})"
        return
    pa = _fuel(guest, which, QUERY, stdlib=judge_zips.padded)
    pb = _fuel(guest, which, MISS, stdlib=judge_zips.padded)
    a = _fuel(guest, which, QUERY, stdlib=judge_zips.small)
    b = _fuel(guest, which, MISS, stdlib=judge_zips.small)
    slope = judge_zips.slope(b - a, pb - pa)
    note(f"a miss after the import: {b - a:,} (padded {pb - pa:,}, {slope:,.0f} per member)")
    assert slope <= 6_000, f"a metadata miss grows {slope:,.0f} fuel per member (6,000)"
