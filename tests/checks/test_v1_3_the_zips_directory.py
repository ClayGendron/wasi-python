"""v1.3: the zip's directory is read once. The stdlib's own import and resource
machinery works, and is cheap: a start reads the zip's directory through the reactor's own
reader, which gives zipimport's dict; resource reads and metadata answer from that one parse.
On the plain binary the stdlib zip is read by folder: its archive comment holds a table of its
top-level folders, a start reads every name outside them and each folder's own name and
`__init__` entries, and a folder's other members load on its first use. The snapshot reads the
whole directory when it is built.

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
    through `_zip_directory`, by folder on the plain binary and whole on the snapshot, and the
    modules the core phase imports keep their file names."""
    got = _json(guest(which, ["-c", GATE]))
    assert got == {
        "served": {ZIP: "folders" if which == "plain" else "fast"},
        "reader": True,
        "resources": True,
        "metadata": True,
        "encodings": True,
        "origin": "frozen",
        "zipimport": f"{ZIP}/zipimport.py",
        "external": f"{ZIP}/importlib/_bootstrap_external.py",
    }, got


# A folder no program uses costs a start its own directory entries' bytes and little else: the
# bound per member of a padding folder, for a start, an import and a first resource read.
PER_MEMBER = 2_000
FIRST_GET_DATA = "import pkgutil\npkgutil.get_data('tzdata', 'zoneinfo/UTC')\n"
GROWS = {"a start": "pass", "import pandas": "import pandas", "a first get_data": FIRST_GET_DATA}


@pytest.mark.parametrize("what", GROWS)
def test_a_plain_start_grows_at_most_2k_fuel_per_member(guest, judge_zips, note, what) -> None:
    """The padding is three tabled folders no program touches, so a plain start, `import pandas`
    and a first `pkgutil.get_data` each pay only the walk past their table lines."""
    padded = guest("plain", ["-c", GROWS[what]], stdlib=judge_zips.padded)
    small = guest("plain", ["-c", GROWS[what]], stdlib=judge_zips.small)
    assert padded.exit_code == 0 and small.exit_code == 0, (padded.describe(), small.describe())
    slope = judge_zips.slope(small.fuel, padded.fuel)
    note(f"{what}: {slope:,.0f} fuel per member; small.zip {small.fuel:,}, padded {padded.fuel:,}")
    assert slope <= PER_MEMBER, f"{what} grows {slope:,.0f} fuel per member ({PER_MEMBER:,})"


READER = """
import json, sys, importlib, zipimport
import _zip_directory as zd

def shape(files, by_folder):
    # A dict read by folder: its items sorted and each folder's children in order, once every
    # folder is loaded; any other: its items in order.
    if not by_folder:
        return [list(files.items())]
    kids = {}
    for name in files:
        kids.setdefault(name.rstrip("/").rpartition("/")[0], []).append(name)
    kids.pop("", None)
    return [sorted(files.items()), kids]

def ours(path):
    files = zd.read_directory(path)
    if zd.served.get(path) == "folders":  # in the cache, so every folder loads into it
        zipimport._zip_directory_cache[path] = files
        zd.load_all(path)
    return files

def outcome(read, path, by_folder):
    try:
        return ["ok", *shape(read(path), by_folder)]
    except Exception as e:
        return ["error", type(e).__name__, str(e)]

path, module = sys.argv[1], sys.argv[2]
fast = outcome(ours, path, False)
served = zd.served.get(path)
if served == "folders":
    fast = outcome(lambda p: zipimport._zip_directory_cache[p], path, True)
stock = outcome(zd.stock_read_directory, path, served == "folders")
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
    its result or its error (criterion 3). The stdlib zip, read by folder on the plain binary,
    gives the same dict once every folder is loaded, each folder's children in zipimport's
    order; the snapshot's cached dict is zipimport's, order and all."""
    if case == "snapshot":
        got = _json(guest("snapshot", ["-c", SNAPSHOT_CACHE]))
        assert got["equal"] and got["names"] > 1000, got
        return
    if case in ("small", "padded"):
        stdlib = judge_zips.small if case == "small" else judge_zips.padded
        got = _json(guest("plain", ["-c", READER, ZIP, ""], stdlib=stdlib))
        assert got["equal"] and got["served"] == "folders", got
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


def test_a_reread_after_invalidate_caches_is_the_folder_read(guest, judge_zips, note) -> None:
    """Agent code that writes a module calls `importlib.invalidate_caches()`; the import after it
    reads the zip's directory again, through the same reader and by folder (criterion 8)."""
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
        got = json.loads(x.text if x.exit_code == 0 else "null")
        assert got == {ZIP: "folders"}, x.describe()
        fuel[name] = x.fuel - y.fuel
    slope = judge_zips.slope(fuel["small"], fuel["padded"])
    note(f"{slope:,.0f} fuel per member; the re-read on small.zip {fuel['small']:,}")
    assert slope <= PER_MEMBER, f"the re-read grows {slope:,.0f} fuel per member ({PER_MEMBER:,})"


# The baseline imports tzdata's zone package, so a first zone less it is the resource read alone:
# on the plain binary, importing tzdata loads its folder's members.
ZONES = "import zoneinfo, importlib.resources, tzdata.zoneinfo\n"
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


# The stdlib zip read by folder: every reader sees what the whole read gives it.

FULL_READ = """
import sys, zipimport, _zip_directory as zd
ZIP = "/usr/local/lib/python315.zip"

def whole():
    # zipimport's whole read in the cache's place, every importer made again: the reference.
    zipimport._zip_directory_cache[ZIP] = zd.stock_read_directory(ZIP)
    zd._folders.pop(ZIP, None)
    sys.path_importer_cache.clear()
"""


def _both(guest, body: str, **kw) -> dict:
    """`body` defines `answers()`; its value read by folder, then after the whole read."""
    code = FULL_READ + body + "\nimport json\nlazy = answers()\nwhole()\n"
    code += "print(json.dumps({'lazy': lazy, 'whole': answers(), 'served': zd.served[ZIP]}))\n"
    got = _json(guest("plain", ["-c", code], **kw))
    assert got["served"] == "folders", got["served"]
    return got


FIRST_TOUCH = {
    "get_data": "pkgutil.get_data('tzdata', 'zoneinfo/Europe/Paris')",
    "iterdir": "sorted(p.name for p in ir.files('tzdata').joinpath('zoneinfo/Europe').iterdir())",
    "joinpath": "[ir.files('tzdata').joinpath('zoneinfo/Europe/Paris').is_file()]",
    "read_bytes": "ir.files('tzdata').joinpath('zoneinfo/Europe/Paris').read_bytes()",
}


@pytest.mark.parametrize("touch", FIRST_TOUCH)
def test_a_first_resource_read_loads_its_folder(guest, touch) -> None:
    """`pkgutil.get_data` and `importlib.resources`' `iterdir`, `joinpath` and `read_bytes`, each
    as a program's first touch of tzdata, answer as the whole read does."""
    body = f"""
import importlib.resources as ir, pkgutil, zipfile
def answers():
    got = {FIRST_TOUCH[touch]}
    return got.hex() if isinstance(got, bytes) else got
"""
    got = _both(guest, body)
    assert got["lazy"] == got["whole"] and got["lazy"], got


AFTER_INVALIDATION = {
    "get_data": "pkgutil.get_data('tzdata', 'zoneinfo/UTC')",
    "files": "importlib.resources.files('tzdata').joinpath('zoneinfo/UTC').read_bytes()",
}


@pytest.mark.parametrize("how", AFTER_INVALIDATION)
def test_a_read_after_invalidate_caches_reads_again_first(guest, how) -> None:
    """`import tzdata`, `importlib.invalidate_caches()`, then a first read of one of its files:
    the trigger takes the dict through the importer's own `_get_files()`, so the zip is read
    again, every folder loaded before is loaded again, and the file is found."""
    code = (
        "import importlib, importlib.resources, pkgutil, sys, zipfile, tzdata\n"
        "importlib.invalidate_caches()\n"
        f"got = {AFTER_INVALIDATION[how]}\n"
        "print(got == zipfile.ZipFile(sys._stdlib_dir).read('tzdata/zoneinfo/UTC'))\n"
    )
    r = guest("plain", ["-c", code])
    assert (r.exit_code, r.text) == (0, "True\n"), r.describe()


PANDAS_FOLDERS = ["numpy", "dateutil", "pandas"]


def test_pandas_styler_reads_its_templates(guest) -> None:
    """pandas' Styler, which reads its templates through jinja2's `PackageLoader`, imports, and
    the loader lists and renders them as with the whole read."""
    body = """
import pandas
from pandas.io.formats.style import Styler
import jinja2
def answers():
    loader = jinja2.PackageLoader("pandas", "io/formats/templates")
    html = pandas.DataFrame({"a": [1]}).style.to_html()
    return [loader.list_templates(), "<table" in html]
"""
    got = _both(guest, body)
    assert got["lazy"] == got["whole"] and got["lazy"][0] and got["lazy"][1], got


def test_import_pandas_loads_exactly_its_packages(guest, note) -> None:
    """The folders of packages loaded by `import pandas`: numpy, dateutil and pandas."""
    code = (
        "import sys, json, pandas, _zip_directory as zd\n"
        "print(json.dumps([f for f in zd.loaded(sys._stdlib_dir)"
        " if f not in sys.stdlib_module_names]))\n"
    )
    got = _json(guest("plain", ["-c", code]))
    note(f"loaded: {got}")
    assert sorted(got) == sorted(PANDAS_FOLDERS), got


def test_metadata_and_module_listings_match_the_whole_read(guest) -> None:
    """`importlib.metadata`'s distributions and the zip's top-level names, in order, and
    `pkgutil.iter_modules()` at the top and under `pandas.__path__`, as the whole read gives
    them."""
    body = """
import importlib.metadata as md, pkgutil
def answers():
    import pandas
    md.FastPath.__new__.cache_clear()
    dists = sorted((d.metadata["Name"], d.version) for d in md.distributions())
    root = md.FastPath(ZIP)
    return [dists, list(root.zip_children()), [m.name for m in pkgutil.iter_modules()],
            [m.name for m in pkgutil.iter_modules(pandas.__path__)]]
"""
    got = _both(guest, body)
    assert got["lazy"] == got["whole"] and all(got["lazy"]), got


def test_a_prefixed_zipimporter_answers_as_the_whole_read(guest) -> None:
    """`zipimporter(ZIP + "/pandas/")`, made before pandas is imported, loads the folder and
    answers its API, and its errors on a missing name, as with the whole read."""
    body = """
import zipimport
def answers():
    zi = zipimport.zipimporter(ZIP + "/pandas/")
    out = [zi.prefix, zi.is_package("core"), zi.is_package("io"), zi.get_filename("core"),
           zi.find_spec("core").origin, len(zi.get_data(ZIP + "/pandas/__init__.pyc"))]
    for call in (lambda: zi.is_package("nope"), lambda: zi.get_data(ZIP + "/pandas/nope.txt"),
                 lambda: zi.get_code("nope"), lambda: zi.get_source("nope")):
        try:
            out.append(["ok", str(call())])
        except Exception as e:
            out.append([type(e).__name__, str(e)])
    out.append(zi.find_spec("nope"))
    return out
"""
    got = _both(guest, body)
    assert got["lazy"] == got["whole"], got


def test_namespaces_and_submodules_across_an_invalidation(guest) -> None:
    """The namespace package `mpl_toolkits` (no `__init__`) resolves and loads on its first
    submodule; `invalidate_caches()` between two submodule imports of a folder loses nothing."""
    code = (
        "import importlib, sys\n"
        "import mpl_toolkits.mplot3d\n"
        "import xml.dom\n"
        "importlib.invalidate_caches()\n"
        "import xml.dom.minidom, email.mime\n"
        "importlib.invalidate_caches()\n"
        "import email.mime.text\n"
        "print(type(mpl_toolkits.__spec__.loader).__name__, xml.dom.minidom.__name__,"
        " email.mime.text.__name__)\n"
    )
    r = guest("plain", ["-c", code], mpl_data=True, env={"MPLBACKEND": "Agg"})
    want = "NamespaceLoader xml.dom.minidom email.mime.text\n"
    assert (r.exit_code, r.text) == (0, want), r.describe()


IMPORT_PATH_ZIP = """
import json, sys, _zip_directory as zd
sys.path[:0] = ["/zips/tabled.zip", "/zips/plain.zip"]
import tabled_pkg.mod, plain_pkg.mod
print(json.dumps([zd.served["/zips/tabled.zip"], zd.served["/zips/plain.zip"],
                  tabled_pkg.mod.WHO, plain_pkg.mod.WHO]))
"""


def test_a_zip_on_the_import_path_is_read_whole(guest, work_zip_pair) -> None:
    """Only the stdlib zip is read by folder: a guest's zip on the import path, with a folder
    table or without, is read whole, as before."""
    got = _json(guest("plain", ["-c", IMPORT_PATH_ZIP], files=work_zip_pair))
    assert got == ["fast", "fast", "tabled", "plain"], got


@pytest.fixture
def work_zip_pair(tmp_path) -> dict[str, bytes]:
    tabled = tmp_path / "tabled.zip"
    tabled.write_bytes(
        zips.build({"tabled_pkg/__init__.py": "", "tabled_pkg/mod.py": "WHO = 'tabled'\n"})
    )
    zips.write_folder_table(tabled)
    with zipfile.ZipFile(tabled) as z:
        assert z.comment.startswith(b"wasi-python folders 1\n")
    plain = zips.build({"plain_pkg/__init__.py": "", "plain_pkg/mod.py": "WHO = 'plain'\n"})
    return {"/zips/tabled.zip": tabled.read_bytes(), "/zips/plain.zip": plain}


POP = (
    "import os, zipimport, _zip_directory as zd\n"
    "ZIP = '/usr/local/lib/python315.zip'\n"
    "zd.load_all(ZIP)\n"
    "zd._folders.clear()\n"  # the reader's own hold on a dict read by folder
)


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_teardown_does_not_free_the_stdlib_directory(guest, note, which) -> None:
    """The reactor holds the stdlib zip's dict to the instance's end, so dropping the cache's
    reference frees nothing: popping it costs within 1 M of not popping it, with every folder
    loaded on the plain binary."""
    stay = guest(which, ["-c", POP + "os._exit(0)\n"], record=False)
    drop = guest(which, ["-c", POP + "zipimport._zip_directory_cache.pop(ZIP)\nos._exit(0)\n"])
    assert stay.exit_code == 0 and drop.exit_code == 0, (stay.describe(), drop.describe())
    note(f"the pop costs {drop.fuel - stay.fuel:,} fuel")
    assert drop.fuel - stay.fuel <= 1_000_000, f"the pop costs {drop.fuel - stay.fuel:,} (1 M)"


LOAD_RAISES = """
import sys
ZIP = sys._stdlib_dir
armed = [True]

def hook(event, args):
    # Only the open a folder's load makes, the first time.
    if not (armed[0] and event == "open" and args and args[0] == ZIP):
        return
    frame = sys._getframe(1)
    while frame is not None and frame.f_code.co_name != "_load":
        frame = frame.f_back
    if frame is not None:
        armed[0] = False
        raise RuntimeError("refused once")

sys.addaudithook(hook)
try:
    import tomllib
    print("first: imported")
except RuntimeError as e:
    print("first:", e)
import tomllib
print("second:", tomllib.loads("a = 1"))
"""


def test_a_load_that_raises_is_tried_again(guest) -> None:
    """An audit hook refuses the open of the zip that a folder's first load makes: that import
    raises, and the folder stays pending, so the next import loads it and succeeds, as natively."""
    r = guest("plain", ["-c", LOAD_RAISES])
    assert (r.exit_code, r.text) == (0, "first: refused once\nsecond: {'a': 1}\n"), r.describe()
