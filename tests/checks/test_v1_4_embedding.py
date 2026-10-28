"""v1.4: an embedder preopens a directory, binds one function, and calls one export.

The guest-side checks use the judge's own driver, which does exactly that and nothing more;
the runner checks call `wasi_python.run`, the wheel's one-call embedding."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from harness import needs, paths, scan

pytestmark = pytest.mark.goal("v1.4")
BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])


@BINARY
def test_door_without_a_host_says_so(guest, which) -> None:
    code = (
        "import _host\n"
        "try:\n"
        "    _host.call(b'x')\n"
        "    print('answered')\n"
        "except ConnectionRefusedError:\n"
        "    print('refused')\n"
        "print(_host.available())\n"
    )
    r = guest(which, ["-c", code])
    assert r.exit_code == 0, r.describe()
    assert r.text.split() == ["refused", "False"], r.text


@BINARY
def test_door_round_trips_bytes_through_a_host(guest, which) -> None:
    seen = []

    def host(frame: bytes) -> bytes:
        seen.append(frame)
        return frame[::-1]

    code = "import _host\nprint(_host.call(b'abc'), _host.available())\n"
    r = guest(which, ["-c", code], host=host)
    assert r.exit_code == 0, r.describe()
    assert r.text.strip() == "b'cba' True", r.text
    assert seen == [b"abc"], seen


@BINARY
def test_run_returns_the_exit_code(guest, which) -> None:
    r = guest(which, ["-c", "import sys; sys.exit(3)"])
    assert r.exit_code == 3, r.describe()


@BINARY
def test_run_reads_argv_and_environment_each_call(guest, which) -> None:
    code = "import os, sys; print(sys.argv[1:], os.environ.get('WASI_PYTHON_PROBE'))"
    for value in ("one", "two"):
        r = guest(which, ["-c", code, value], env={"WASI_PYTHON_PROBE": value})
        assert r.exit_code == 0, r.describe()
        assert r.text.strip() == f"['{value}'] {value}", r.text


NATIVE_MAIN = "['__builtins__', '__doc__', '__loader__', '__name__', '__package__', '__spec__']"
NATIVE_TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "<string>", line 1, in <module>\n'
    "    1/0\n"
    "    ~^~\n"
    "ZeroDivisionError: division by zero\n"
)


@BINARY
def test_main_starts_as_native(guest, which) -> None:
    """A program's __main__ is CPython's, never holding the snapshot's build-time imports."""
    r = guest(which, ["-c", "print(sorted(globals()))"])
    assert r.exit_code == 0, r.describe()
    assert r.text.strip() == NATIVE_MAIN, r.text


@BINARY
def test_uncaught_errors_print_as_native(guest, which) -> None:
    """The user's frames only, through sys.excepthook, as CPython's -c prints them."""
    hook = "import sys\nsys.excepthook = lambda t, e, tb: print('hook', t.__name__)\n1/0\n"
    r = guest(which, ["-c", hook])
    assert (r.exit_code, r.text.strip()) == (1, "hook ZeroDivisionError"), r.describe()
    r = guest(which, ["-c", "1/0"])
    assert r.exit_code == 1, r.describe()
    assert r.stderr.decode(errors="replace") == NATIVE_TRACEBACK, r.stderr


@BINARY
def test_exit_status_is_a_process_status(guest, which) -> None:
    """SystemExit's code comes back as a POSIX process status would: 0 to 255."""
    codes = [guest(which, ["-c", f"raise SystemExit({c})"]).exit_code for c in (256, -1)]
    assert codes == [0, 255], codes


@BINARY
def test_unbuffered_output_survives_a_hard_exit(guest, which) -> None:
    """-u is honoured: what was printed is written before os._exit or a trap can lose it."""
    r = guest(which, ["-u", "-Xutf8", "-c", "print('kept'); import os; os._exit(0)"])
    assert (r.exit_code, r.text) == (0, "kept\n"), r.describe()


UNCLOSED = "f = open('/out.txt', 'w')\nf.write('x' * 100)\ndef g():\n    pass\n"


@BINARY
def test_run_keeps_an_unclosed_files_bytes(guest, which) -> None:
    """A file a program leaves open is flushed when the interpreter finalizes, as in native
    CPython. The snapshot lost the bytes when __main__ defined a function, its frozen __main__
    never freed; run now runs every program
    in a fresh __main__ and unfreezes the heap before finalizing."""
    r = guest(which, ["-c", UNCLOSED])
    assert r.exit_code == 0, r.describe()
    out = r.root / "out.txt"
    kept = out.stat().st_size if out.exists() else 0
    findings = [] if kept == 100 else [f"{which}: a file left open kept {kept} of 100 bytes"]
    assert not findings, scan.report(findings, "unclosed file")


ZIP_LEFT_OPEN = (
    "import zipfile\n"
    "z = zipfile.ZipFile('/out.zip', 'w')\n"
    "z.writestr('a.txt', 'x' * 100)\n"
    "def g():\n"
    "    pass\n"
)
RUN_MODES = ("-c", "stdin", "script", "directory", "-m")


def _in_mode(workdir: Path, mode: str, program: str, which: str, **kw):
    """`program` through `wasi_python.run` in one of run's modes: -c, stdin, a script
    file, a directory holding it as __main__.py, or -m from a read-only grant on the import path.
    Returns the result and the call's root."""
    from wasi_python import Grant

    run = _runner()
    root = _root(workdir)
    if mode == "-c":
        argv = ["-c", program]
    elif mode == "stdin":
        argv, kw = [], {**kw, "stdin": program.encode()}
    elif mode == "script":
        (root / "prog.py").write_text(program)
        argv = ["/prog.py"]
    elif mode == "directory":
        (root / "app").mkdir()
        (root / "app" / "__main__.py").write_text(program)
        argv = ["/app"]
    else:
        code = _folder(workdir, {"prog.py": program}, prefix="mode-")
        argv = ["-m", "prog"]
        kw = {**kw, "grants": [Grant(code, "/code")], "import_path": ["/code"]}
    return run(argv, root=root, snapshot=which == "snapshot", **kw), root


@BINARY
def test_run_keeps_unclosed_files_in_every_mode(guest_workdir, which) -> None:
    """In every mode run has, a file left open beside a function keeps its
    bytes, and a ZipFile left open is finalized (its directory written), as native CPython's
    `python -c`, `python prog.py`, `python dir` and `python -m` keep them. A script and -m ran in
    runpy's temporary module and lost them on both binaries; -c and stdin lost them on the
    snapshot. Records no fuel: run answers entropy and clocks from the host."""
    import zipfile

    findings = []
    for mode in RUN_MODES:
        done, root = _in_mode(guest_workdir, mode, UNCLOSED, which)
        assert done.exit_code == 0, (mode, done)
        out = root / "out.txt"
        kept = out.stat().st_size if out.exists() else 0
        if kept != 100:
            findings.append(f"{mode}: a file left open kept {kept} of 100 bytes")
        done, root = _in_mode(guest_workdir, mode, ZIP_LEFT_OPEN, which)
        assert done.exit_code == 0, (mode, done)
        try:
            with zipfile.ZipFile(root / "out.zip") as z:
                ok = z.read("a.txt") == b"x" * 100
        except (OSError, zipfile.BadZipFile):
            ok = False
        if not ok:
            findings.append(f"{mode}: a zip left open is unreadable")
    assert not findings, scan.report(findings, "unclosed file")


MAIN_PROBE = """\
import sys
W = ('warnings' in sys.modules, '_py_warnings' in sys.modules)
import atexit, gc, pickle
class C:
    pass
g = globals()
print(repr((
    W,
    any(o is g for o in gc.get_objects()),
    g is sys.modules['__main__'].__dict__,
    sorted(k for k in g if k.startswith('__')),
    (__name__, g.get('__file__'), __package__, getattr(__spec__, 'name', None),
     type(__loader__).__name__, type(__builtins__).__name__),
)))
def at():
    m = sys.modules['__main__']
    try:
        ok = type(pickle.loads(pickle.dumps(m.C()))).__name__ == 'C'
    except Exception as e:
        ok = type(e).__name__
    print(repr(('atexit', hasattr(m, 'C'), ok, getattr(m, '__file__', None))))
atexit.register(at)
"""
SIX = ["__builtins__", "__doc__", "__loader__", "__name__", "__package__", "__spec__"]
SEVEN = sorted([*SIX, "__file__"])
MAIN_WANT = {  # native CPython 3.15's __main__ in each mode
    "-c": (SIX, ("__main__", None, None, None, "type", "module"), None),
    "stdin": (SIX, ("__main__", None, None, None, "type", "module"), None),
    "script": (
        SEVEN,
        ("__main__", "/prog.py", None, None, "SourceFileLoader", "module"),
        None,
    ),
    "directory": (
        SEVEN,
        ("__main__", "/app/__main__.py", "", "__main__", "SourceFileLoader", "module"),
        "/app/__main__.py",
    ),
    "-m": (
        SEVEN,
        ("__main__", "/code/prog.py", "", "prog", "SourceFileLoader", "module"),
        "/code/prog.py",
    ),
}


@BINARY
def test_every_program_runs_in_an_unfrozen_main(guest_workdir, which) -> None:
    """In every mode the program's globals are __main__'s, in a collector
    generation (gc.get_objects() never lists the frozen one), with native CPython's names and
    values; and an atexit handler finds the program's __main__ (its class pickles), with
    `__file__` gone after a script, as CPython removes it, and kept for a directory and -m. A
    program starts without `warnings` in sys.modules in every mode, as native CPython's does (a
    script's loader import once brought it in)."""
    import ast

    for mode in RUN_MODES:
        done, _ = _in_mode(guest_workdir, mode, MAIN_PROBE, which)
        assert done.exit_code == 0, (mode, done)
        lines = done.stdout.decode().splitlines()
        assert len(lines) == 2, (mode, done)
        warned, unfrozen, is_main, names, values = ast.literal_eval(lines[0])
        names_want, values_want, file_at_exit = MAIN_WANT[mode]
        got = (warned, unfrozen, is_main, names, values, ast.literal_eval(lines[1]))
        want = (
            (False, False),
            True,
            True,
            names_want,
            values_want,
            ("atexit", True, True, file_at_exit),
        )
        assert got == want, (mode, got, want)


FROZEN_HEAP = {  # what a program hangs on the stdlib the snapshot pre-imports
    "a patched stdlib class": (
        "import json\n"
        "f = open('/out.txt', 'w')\n"
        "f.write('x' * 100)\n"
        "def default(self, o):\n"
        "    return str(o)\n"
        "json.JSONEncoder.default = default\n"
    ),
    "a stdlib module": (
        "import json\njson.log = open('/out.txt', 'w')\njson.log.write('x' * 100)\n"
    ),
    "after gc.unfreeze was replaced": (
        "import gc\n"
        "gc.unfreeze = lambda: None\n"
        "import json\n"
        "f = open('/out.txt', 'w')\n"
        "f.write('x' * 100)\n"
        "def default(self, o):\n"
        "    return str(o)\n"
        "json.JSONEncoder.default = default\n"
    ),
}
FROZEN_HEAP_FINDING = {
    "a patched stdlib class": "a file reached from a patched stdlib class",
    "a stdlib module": "a file stored on a stdlib module",
    "after gc.unfreeze was replaced": "a file reached after gc.unfreeze was replaced",
}


@BINARY
def test_run_keeps_a_file_the_stdlib_reaches(guest, which) -> None:
    """A file a program hangs on a pre-imported stdlib class or module keeps
    its bytes. On the snapshot those are frozen; run undoes the freeze before it finalizes, as a
    session's close does, through a reference taken at build
    time, so a program that replaces gc.unfreeze cannot stop it."""
    findings = []
    for case, program in FROZEN_HEAP.items():
        r = guest(which, ["-c", program])
        assert r.exit_code == 0, (case, r.describe())
        out = r.root / "out.txt"
        kept = out.stat().st_size if out.exists() else 0
        if kept != 100:
            findings.append(f"{which}: {FROZEN_HEAP_FINDING[case]} kept {kept} of 100 bytes")
    assert not findings, scan.report(findings, "frozen heap")


def _frame_names(stderr: bytes) -> list[tuple[str, str]]:
    """The (file, function) of each frame of a traceback, in order."""
    import re

    text = stderr.decode(errors="replace")
    return re.findall(r'^  File "([^"]+)", line \d+, in (\S+)$', text, re.M)


@BINARY
def test_module_and_directory_errors_read_as_native(guest_workdir, which) -> None:
    """-m of a missing module and a directory without __main__.py print
    CPython's own lines, and an -m traceback shows CPython's runpy frames, now that -m runs as
    runpy._run_module_as_main and a directory as CPython runs it."""
    from wasi_python import Grant

    run = _runner()
    snapshot = which == "snapshot"
    code = _folder(guest_workdir, {"boom.py": "def f():\n    return 1 / 0\n\n\nf()\n"})
    grants = [Grant(code, "/code")]
    done = run(["-m", "nope"], grants=grants, import_path=["/code"], snapshot=snapshot)
    assert (done.exit_code, done.stderr) == (
        1,
        b"/usr/local/bin/python.wasm: No module named nope\n",
    ), done
    root = _root(guest_workdir)
    (root / "empty").mkdir()
    done = run(["/empty"], root=root, snapshot=snapshot)
    assert (done.exit_code, done.stderr) == (
        1,
        b"/usr/local/bin/python.wasm: can't find '__main__' module in '/empty'\n",
    ), done
    done = run(["-m", "boom"], grants=grants, import_path=["/code"], snapshot=snapshot)
    assert done.exit_code == 1, done
    frames = _frame_names(done.stderr)
    assert frames == [
        ("<frozen runpy>", "_run_module_as_main"),
        ("<frozen runpy>", "_run_code"),
        ("/code/boom.py", "<module>"),
        ("/code/boom.py", "f"),
    ], (frames, done.stderr)


@BINARY
def test_a_program_sees_real_entropy_and_file_metadata(guest, which) -> None:
    """The constants the build pins while it snapshots never reach a program: entropy, a file's
    inode and times, and a directory's size and link count.

    The directory's two are compared with the host's own answer for the same directory, not with
    fixed numbers. On a host whose real answer is the pinned one (size 0 and one link, as Windows
    may give), this part cannot tell pinned from real; the macOS and Linux runs are the ones that
    tell. The judge's driver answers a file's inode and times itself, but never with the
    pinned 0 and 1767225600 s: its count starts at 1 and its clock a microsecond past that second,
    so a pinned value left in the snapshot's heap would still show here."""
    code = (
        "import os\n"
        "st = os.stat('/w/f')\n"
        "d = os.stat('/w')\n"
        "print(os.urandom(8) != bytes(8), st.st_ino != 0, st.st_mtime != 1767225600)\n"
        "print(d.st_size, d.st_nlink)\n"
    )
    r = guest(which, ["-c", code], files={"/w/f": b"x"})
    assert r.exit_code == 0, r.describe()
    host = os.stat(r.root / "w")
    expected = ["True", "True", "True", str(host.st_size), str(host.st_nlink)]
    assert r.text.split() == expected, (r.text, expected)


FACTS = """
import os, time
now = lambda: time.clock_gettime_ns(time.CLOCK_REALTIME)  # the guest's clock: the driver's
facts = []
for e in sorted(os.scandir('/g'), key=lambda e: e.name):
    s = e.stat()
    facts.append((e.name, str(s.st_ino), repr(s.st_mtime), s.st_mtime_ns,
                  e.inode() == s.st_ino, now() >= s.st_mtime_ns))
os.mkdir('/d')
open('/d/x', 'w').write('x')
os.utime('/d/x', ns=(1, 2))
open('/d/y', 'w').write('y')
x, y = os.stat('/d/x'), os.stat('/d/y')
print(facts)
print(len({f[1] for f in facts}), max(int(f[1]) for f in facts) < 2**30, all(f[4] for f in facts),
      all(f[5] for f in facts), now() >= y.st_mtime_ns, x.st_atime_ns, x.st_mtime_ns)
"""


def _eight_files(folder: Path, year: int) -> None:
    """Eight files made afresh (new host inodes) in `folder`, their times in the given year."""
    import shutil

    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir()
    base = (year - 1970) * 365 * 86400 * 10**9
    for i in range(8):
        (folder / f"f{i}").write_text("x" * i)
        os.utime(folder / f"f{i}", ns=(base + i, base + 2 * i))


@BINARY
def test_file_facts_cost_the_same_on_every_run(guest, tmp_path, which) -> None:
    """A program that reads files' inode numbers and times (by stat and by scandir),
    sets one file's times and writes another, run twice over a granted folder made afresh with
    other host times. On every host: eight distinct inode numbers below 2**30 (the driver's
    count), each `DirEntry.inode()` its stat's, no file after the guest's clock, and the set times
    back as set. On darwin the two runs also print the same and spend the same fuel: the ratchet's
    host, whose file system stamps every change apart. A host with coarse file times can leave a
    write unseen in one run and seen in the other, so there it promises no more (Decision 6)."""
    grant = tmp_path / "g"
    runs = []
    for year, record in ((2019, False), (2024, True)):
        _eight_files(grant, year)
        r = guest(which, ["-c", FACTS], preopens=[("/g", grant, False)], record=record)
        assert r.exit_code == 0, r.describe()
        runs.append(r)
    for r in runs:
        assert r.text.splitlines()[-1] == "8 True True True True 1 2", r.text
    if sys.platform == "darwin":
        assert runs[0].text == runs[1].text, (runs[0].text, runs[1].text)
        assert runs[0].fuel == runs[1].fuel, (runs[0].fuel, runs[1].fuel)


NLINK = """
import json, os, sys
zip_path = next(p for p in sys.path if p.endswith('.zip'))
print(json.dumps(os.stat(zip_path).st_nlink))
"""


@BINARY
def test_fuel_does_not_follow_the_stdlib_zips_link_count(guest, artifacts, tmp_path, which) -> None:
    """The driver gives each run its own copy of the
    stdlib, so a guest sees one link to it whatever links the host holds, and its fuel cannot move
    with them. A private copy of the set's zip runs at one link, then with more links than the
    bisected flip (one set of fuel values up to 1,017 links, another from 1,023): 1,101, or 1,021
    on Windows, where NTFS allows 1,024. The set's own zip is never linked. Fuel is compared on
    darwin (Decision 6); the link count the guest sees everywhere."""
    import shutil

    mine = tmp_path / "stdlib.zip"
    shutil.copyfile(artifacts.path("python-stdlib.zip"), mine)
    links = tmp_path / "links"
    links.mkdir()
    runs = [guest(which, ["-c", NLINK], stdlib=mine, record=False)]
    try:
        for i in range(1021 if sys.platform == "win32" else 1101):
            os.link(mine, links / f"{i}.zip")
        runs.append(guest(which, ["-c", NLINK], stdlib=mine))
    finally:
        shutil.rmtree(links, ignore_errors=True)
    assert [(r.exit_code, r.text) for r in runs] == [(0, "1\n")] * 2, [r.describe() for r in runs]
    if sys.platform == "darwin":
        assert runs[0].fuel == runs[1].fuel, (runs[0].fuel, runs[1].fuel)


def _runner():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python.run


def _root(workdir: Path) -> Path:
    return Path(tempfile.mkdtemp(prefix="runner-", dir=workdir))


def test_runner_runs_a_program_in_one_call(guest_workdir) -> None:
    run = _runner()
    done = run(["-c", "print(1)"], root=_root(guest_workdir))
    assert (done.exit_code, done.stdout) in ((0, b"1\n"), (0, "1\n")), done


def test_runner_binds_a_host(guest_workdir) -> None:
    run = _runner()
    done = run(
        ["-c", "import _host; print(_host.call(b'abc'))"],
        root=_root(guest_workdir),
        host=lambda frame: frame[::-1],
    )
    assert done.exit_code == 0 and "cba" in str(done.stdout), done


def test_runner_stops_a_runaway_guest_by_fuel(guest_workdir) -> None:
    run = _runner()
    done = run(["-c", "while True: pass"], root=_root(guest_workdir), fuel=10**9)
    assert done.trapped and done.exit_code is None, done


def test_runner_runs_the_plain_reactor(guest_workdir) -> None:
    """snapshot=False runs the plain reactor, which starts with only the interpreter's own
    modules; the snapshot has pre-imported csv (no package, so csv tells them apart)."""
    run = _runner()
    code = "import sys; print('csv' in sys.modules, sys.argv)"
    plain = run(["-c", code, "a"], root=_root(guest_workdir), snapshot=False)
    snap = run(["-c", code, "a"], root=_root(guest_workdir))
    assert (plain.exit_code, plain.stdout) == (0, b"False ['-c', 'a']\n"), plain
    assert (snap.exit_code, snap.stdout) == (0, b"True ['-c', 'a']\n"), snap


def test_runner_reports_a_host_fault(guest_workdir) -> None:
    """A host that raises answers -2, which the guest sees as OSError."""
    run = _runner()

    def host(frame: bytes) -> bytes:
        raise RuntimeError("the host broke")

    code = (
        "import _host\n"
        "try:\n"
        "    _host.call(b'x')\n"
        "except OSError as e:\n"
        "    print(type(e).__name__)\n"
    )
    done = run(["-c", code], root=_root(guest_workdir), host=host)
    assert (done.exit_code, done.stdout) == (0, b"OSError\n"), done


def test_runner_caps_memory(guest_workdir) -> None:
    """Past memory_bytes the guest's allocation fails as a MemoryError, not a trap."""
    run = _runner()
    code = "try:\n    b = bytearray(256 * 2**20)\nexcept MemoryError:\n    print('capped')\n"
    done = run(["-c", code], root=_root(guest_workdir), memory_bytes=128 * 2**20)
    assert (done.exit_code, done.stdout, done.trapped) == (0, b"capped\n", None), done


CACHE_PROBE = (
    "import sys, json\n"
    f"sys.path.insert(0, {str(paths.REPO / 'src')!r})\n"
    "from wasi_python import run, runner\n"
    "done = run(['-c', 'pass'], root=sys.argv[1], cache_dir=sys.argv[2])\n"
    "print(json.dumps([done.exit_code, runner.stats()]))\n"
)
# stats() also counts tool threads and open sessions: none here.
NO_TOOL_THREADS = {"tool_threads_running": 0, "sessions_open": 0}


def test_runner_caches_the_compiled_module(guest_workdir) -> None:
    """A first process compiles and writes one .cwasm; a second loads it and compiles nothing."""
    _runner()
    cache = Path(tempfile.mkdtemp(prefix="cache-", dir=guest_workdir))
    seen = [_cache_probe(guest_workdir, cache)[0] for _ in range(2)]
    assert seen[0] == [0, {"compiled": 1, "loaded": 0, "written": 1, **NO_TOOL_THREADS}], seen
    assert seen[1] == [0, {"compiled": 0, "loaded": 1, "written": 0, **NO_TOOL_THREADS}], seen
    assert len(list(cache.glob("*.cwasm"))) == 1


def _cache_probe(guest_workdir: Path, cache: Path) -> tuple[list, str]:
    """One call in a fresh process (an empty in-process cache): its exit code and stats()."""
    out = subprocess.run(
        [sys.executable, "-I", "-c", CACHE_PROBE, str(_root(guest_workdir)), str(cache)],
        capture_output=True,
        text=True,
        env={**os.environ},
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout), out.stderr


FUEL_PROBE = (
    "import sys, json\n"
    f"sys.path.insert(0, {str(paths.REPO / 'src')!r})\n"
    "from wasi_python import run, runner\n"
    "done = run(['-c', 'pass'], root=sys.argv[1], cache_dir=sys.argv[2], fuel=10**12,\n"
    "           deadline_s=None)\n"
    "print(json.dumps([done.exit_code, done.fuel_used, runner.stats()]))\n"
)


def test_fuel_does_not_depend_on_the_module_cache(guest_workdir) -> None:
    """Fuel counts the guest only: a module compiled in the process and one loaded from a .cwasm
    report the same fuel. Without that, wasmtime's memory-image copy at instantiation
    (42.35M on the snapshot) is counted when the image cannot be mapped. The bound is fixed, not
    the judge's 0.01%: the runner's clock is real and moves the count by about 150,000."""
    _runner()
    cache = Path(tempfile.mkdtemp(prefix="fuel-cache-", dir=guest_workdir))
    seen = []
    for _ in range(2):
        out = subprocess.run(
            [sys.executable, "-I", "-c", FUEL_PROBE, str(_root(guest_workdir)), str(cache)],
            capture_output=True,
            text=True,
            env={**os.environ},
        )
        assert out.returncode == 0, out.stderr
        seen.append(json.loads(out.stdout))
    (code_a, fuel_a, stats_a), (code_b, fuel_b, stats_b) = seen
    assert (code_a, stats_a) == (
        0,
        {"compiled": 1, "loaded": 0, "written": 1, **NO_TOOL_THREADS},
    ), seen
    assert (code_b, stats_b) == (
        0,
        {"compiled": 0, "loaded": 1, "written": 0, **NO_TOOL_THREADS},
    ), seen
    assert abs(fuel_a - fuel_b) < 1_000_000, f"compiled {fuel_a:,}, loaded {fuel_b:,}"


def test_runner_refuses_a_cache_others_can_write(guest_workdir) -> None:
    """A .cwasm is native code: on POSIX a cache directory others can write is neither read
    nor written. Windows has no such mode bits, and the runner makes no ownership check there
    (the default cache is under the user's own profile); this check
    records that behaviour."""
    _runner()
    cache = Path(tempfile.mkdtemp(prefix="cache-", dir=guest_workdir))
    cache.chmod(0o777)
    seen, stderr = _cache_probe(guest_workdir, cache)
    if os.name == "posix":
        assert seen == [0, {"compiled": 1, "loaded": 0, "written": 0, **NO_TOOL_THREADS}], seen
        assert "not using the module cache" in stderr, stderr
        assert list(cache.iterdir()) == []
    else:
        assert seen == [0, {"compiled": 1, "loaded": 0, "written": 1, **NO_TOOL_THREADS}], seen


def _zip() -> str:
    """The stdlib zip's guest path, named from MANIFEST's `python` line (python3XY.zip)."""
    directory = paths.artifact_dir()
    assert directory is not None
    version = paths.parse_manifest((directory / "MANIFEST").read_text()).python
    major, minor = version.split(".")[:2]
    return f"/usr/local/lib/python{major}{minor}.zip"


def test_runner_keeps_the_artifact_zip_out_of_the_guests_reach(guest_workdir, artifacts) -> None:
    """A guest that rewrites its zip changes neither the artifact set nor its own next run. Now
    the zip is a read-only grant: the write is refused, and a root holds no zip."""
    run = _runner()
    zip_path = artifacts.path("python-stdlib.zip")
    before = paths.sha256_bytes(zip_path.read_bytes())
    root = _root(guest_workdir)
    ZIP = _zip()
    vandal = (
        f"try:\n    f = open({ZIP!r}, 'r+b'); f.seek(1000); f.write(b'X' * 64); f.close()\n"
        "except PermissionError:\n    print('refused')\n"
    )
    first = run(["-c", vandal], root=root)
    assert (first.exit_code, first.stdout) == (0, b"refused\n"), first
    assert paths.sha256_bytes(zip_path.read_bytes()) == before
    after = run(["-c", "import json, csv; print('ok')"], root=root)
    assert (after.exit_code, after.stdout) == (0, b"ok\n"), after
    assert not (root / ZIP.lstrip("/")).exists()
    assert (root / "usr/local/lib").is_dir()


@pytest.mark.parametrize("planted", ["the zip", "its directory"])
def test_runner_never_follows_a_link_a_guest_left(guest_workdir, planted) -> None:
    """A symbolic link the guest planted in its root is replaced or left alone, never written
    through. Now removing or renaming the zip or its folder through /usr/local/lib is
    refused, so the guest plants the same links through /usr/./local/lib, the root's own folder
    behind the grant, which the runner still makes real each call."""
    run = _runner()
    base = Path(tempfile.mkdtemp(prefix="escape-", dir=guest_workdir))
    root, outside = base / "root", base / "outside"
    outside.mkdir()
    ZIP = _zip()
    own = ZIP.replace("/usr/local/lib", "/usr/./local/lib")
    if planted == "the zip":
        refused = f"os.remove({ZIP!r})"
        link, target, before = own, "../../../../outside/target", "pass"
    else:
        refused = "os.rename('/usr/local/lib', '/usr/local/old')"
        link, target = "/usr/./local/lib", "../../../outside"
        before = "os.rename('/usr/./local/lib', '/usr/./local/old')"
    # Where the host does not let a guest make a link (Windows without the privilege), the
    # guest still moves the root's folder, and the next call must repair that.
    code = (
        f"import os\ntry:\n    {refused}\n    print('done')\n"
        "except OSError:\n    print('refused')\n"
        f"{before}\n"
        f"try:\n    os.symlink({target!r}, {link!r})\n    print('linked')\n"
        "except OSError:\n    print('no link')\n"
    )
    first = run(["-c", code], root=root)
    assert first.exit_code == 0, first
    assert first.stdout.startswith(b"refused\n"), first
    if os.name == "posix":  # there the guest can make the link, so the escape is really tried
        assert first.stdout == b"refused\nlinked\n", first
    second = run(["-c", "import json; print('ok')"], root=root)
    assert (second.exit_code, second.stdout) == (0, b"ok\n"), second
    assert list(outside.iterdir()) == [], list(outside.iterdir())
    lib = root / "usr/local/lib"
    assert lib.is_dir() and not lib.is_symlink()


def test_runner_replaces_a_directory_left_in_the_zips_place(guest_workdir) -> None:
    """A guest that would turn its zip path into a directory cannot (the zip is a
    read-only grant), and the next call works."""
    run = _runner()
    root = _root(guest_workdir)
    ZIP = _zip()
    code = (
        "import os\n"
        f"for step in (lambda: os.remove({ZIP!r}), lambda: os.makedirs({ZIP!r} + '/x')):\n"
        "    try:\n        step()\n        print('done')\n"
        "    except OSError:\n        print('refused')\n"
    )
    first = run(["-c", code], root=root)
    assert (first.exit_code, first.stdout) == (0, b"refused\nrefused\n"), first
    assert list((root / "usr/local/lib").iterdir()) == []
    after = run(["-c", "print('ok')"], root=root)
    assert (after.exit_code, after.stdout) == (0, b"ok\n"), after


def test_runner_serves_concurrent_calls_on_one_root(guest_workdir) -> None:
    run = _runner()
    root = _root(guest_workdir)
    done = {}

    def call(i: int) -> None:
        done[i] = run(["-c", f"print({i})"], root=root)

    threads = [threading.Thread(target=call, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert {i: (d.exit_code, d.stdout) for i, d in done.items()} == {
        i: (0, f"{i}\n".encode()) for i in range(4)
    }, done


REPORTLAB_IN_MEMORY = """
import io
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table
buf = io.BytesIO()
c = canvas.Canvas(buf, invariant=1)
c.drawString(72, 720, "nothing writable")
c.save()
doc = io.BytesIO()
SimpleDocTemplate(doc, invariant=1).build(
    [Paragraph("A report", getSampleStyleSheet()["Title"]), Table([["a", "b"], ["1", "2"]])]
)
for data in (buf.getvalue(), doc.getvalue()):
    print(data[:5].decode(), len(data))
"""


def test_reportlab_writes_a_pdf_with_nothing_writable() -> None:
    """With no root and no grant, the runner's defaults, nothing is writable, and
    reportlab still builds a canvas PDF and a platypus PDF in memory: unlike openpyxl it needs
    no temporary folder."""
    run = _runner()
    done = run(["-c", REPORTLAB_IN_MEMORY])
    assert done.exit_code == 0, done
    lines = [line.split() for line in done.stdout.decode().splitlines()]
    assert [(head, int(n) > 500) for head, n in lines] == [("%PDF-", True)] * 2, done


def test_package_imports_without_wasmtime() -> None:
    """The package imports where wasmtime-py cannot (an embedder that installed with `--no-deps`
    to keep its own binding, or a platform wasmtime cannot load on); only run() needs wasmtime."""
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(paths.REPO / 'src')!r})\n"
        "sys.modules['wasmtime'] = None  # importing it now raises ImportError\n"
        "import wasi_python\n"
        "print(callable(wasi_python.run))\n"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["True"], out.stdout


def test_a_plain_install_brings_wasmtime() -> None:
    """`pip install wasi-python` runs programs: wasmtime-py is the one required dependency,
    `>=50,<51` with no marker; the `run` extra stays, empty; the dev group does not repeat the
    bound. Exactly one dependency also makes the rule that each dependency has a written reason
    mechanical: another one turns this red until a specification gives its reason."""
    import tomllib

    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet
    from packaging.utils import canonicalize_name

    project = tomllib.loads((paths.REPO / "pyproject.toml").read_text(encoding="utf-8"))
    deps = project["project"].get("dependencies", [])
    assert len(deps) == 1, deps
    req = Requirement(deps[0])
    assert (req.name, req.specifier, req.marker, req.extras) == (
        "wasmtime",
        SpecifierSet(">=50,<51"),
        None,
        set(),
    ), deps
    assert project["project"].get("optional-dependencies") == {"run": []}, project["project"]
    dev = project.get("dependency-groups", {}).get("dev", [])
    names = [canonicalize_name(Requirement(d).name) for d in dev if isinstance(d, str)]
    assert "wasmtime" not in names, dev  # any spelling: `Wasmtime` is the same project


@pytest.mark.parametrize("error", ["RuntimeError", "OSError"])
def test_a_wasmtime_that_cannot_load_is_named(error) -> None:
    """A wasmtime that is installed but cannot load gives `run` one error type, `ImportError`,
    naming the bound, with wasmtime's own error as its cause.
    Its pure wheel on an unsupported platform raises `RuntimeError` at import; a platform
    wheel whose native library will not load raises `OSError`. The
    stand-in is a finder at the head of `sys.meta_path` that raises for `wasmtime`, in a child
    process."""
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(paths.REPO / 'src')!r})\n"
        "class Refuse:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'wasmtime':\n"
        f"            raise {error}('wasmtime cannot load: test')\n"
        "        return None\n"
        "sys.modules.pop('wasmtime', None)\n"
        "sys.meta_path.insert(0, Refuse())\n"
        "import wasi_python\n"
        "try:\n"
        "    wasi_python.run(['-c', 'pass'])\n"
        "except ImportError as e:\n"
        "    c = e.__cause__\n"
        "    print(json.dumps([type(c).__name__, str(c), str(e)]))\n"
        "else:\n"
        "    print(json.dumps(['no error']))\n"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    got = json.loads(out.stdout)
    assert got[:2] == [error, "wasmtime cannot load: test"], got
    assert "wasmtime>=50,<51" in got[2], got


def test_a_failed_instantiation_reports_no_fuel(guest_workdir) -> None:
    """A memory cap below the module's own minimum fails instantiation: the call traps and
    reports 0 instructions, never the unmetered budget instantiation ran on."""
    run = _runner()
    done = run(["-c", "pass"], root=_root(guest_workdir), memory_bytes=1 << 20, fuel=10**9)
    assert done.exit_code is None and done.trapped, done
    assert done.fuel_used == 0, done


def test_an_ordinary_sleep_still_works(guest_workdir) -> None:
    """A short sleep with no deadline ends as asked and the program goes on."""
    run = _runner()
    code = "import time\ntime.sleep(0.05)\nprint('after')\n"
    done = run(["-c", code], root=_root(guest_workdir), deadline_s=None)
    assert (done.exit_code, done.stdout) == (0, b"after\n"), done


CONCURRENT = r"""
import sys, threading
import wasi_python

THREADS, CALLS = 8, 100  # 8 x 40 failed today's runner in 2 of 3 runs; 8 x 100 in 6 of 6
wasi_python.run(["-c", "pass"])
wasi_python.run(["-c", "pass"], fuel=10**10)  # both engines warm: the check is on the tables
wrong, raised, reached = [], [], []


def one(kind, token):
    if kind == "print":
        r = wasi_python.run(["-c", f"print({token!r})"])
        return r if (r.exit_code, r.stdout) != (0, f"{token}\n".encode()) else None
    if kind == "door":
        code = "import _host; print(_host.call(b'x').decode())"
        r = wasi_python.run(["-c", code], host=lambda frame, t=token: t.encode())
        return r if (r.exit_code, r.stdout) != (0, f"{token}\n".encode()) else None
    if kind == "sleep":
        r = wasi_python.run(["-c", f"import time; time.sleep(0.01); print({token!r})"])
        return r if (r.exit_code, r.stdout) != (0, f"{token}\n".encode()) else None
    if kind == "fuel":
        r = wasi_python.run(["-c", f"print({token!r})"], fuel=10**10)
        return r if (r.exit_code, r.stdout) != (0, f"{token}\n".encode()) else None
    # The deadline also covers start-up, which a loaded host can take past 0.2 s (Windows CI,
    # 2026-10-17). The door, called after the print, tells whether the print ran; with no timing,
    # the guest's own token is required once it has, and nothing else is ever allowed.
    printed = []
    code = f"import _host; print({token!r}, flush=True); _host.call(b'x')\nwhile True: pass"
    r = wasi_python.run(["-c", code], host=lambda frame: printed.append(1) or b"", deadline_s=0.2)
    reached.extend(printed)
    allowed = {f"{token}\n".encode()} if printed else {b"", f"{token}\n".encode()}
    return r if r.trapped != "deadline" or r.stdout not in allowed else None


def worker(w):
    for i in range(CALLS):
        kind = ("print", "door", "sleep", "fuel", "trap")[(w + i) % 5]
        try:
            bad = one(kind, f"t-{w}-{i}")
        except BaseException as e:
            raised.append(f"{kind}: {type(e).__name__}: {e}"[:200])
            continue
        if bad is not None:
            wrong.append(f"{kind}: {bad}"[:200])


sys.setswitchinterval(1e-6)  # frequent thread switches make an unlocked table's race likely
threads = [threading.Thread(target=worker, args=(w,)) for w in range(THREADS)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print(f"{THREADS * CALLS} calls, {len(wrong)} wrong, {len(raised)} raised")
for line in (raised + wrong)[:5]:
    print(line)
print(f"trap calls that reached the door: {len(reached)} of {THREADS * CALLS // 5}")  # not asserted
"""


def test_concurrent_calls_get_their_own_results() -> None:
    """Guards a change: concurrent calls share nothing. 8 threads make 100 calls each,
    a mix of output, the door, a wait, fuel and a deadline trap; each must get its own result. A
    trap call's deadline may end it before its print, so it must show its own output only if
    its door call shows the print ran; how many did is printed, not asserted. The other calls run
    under the default 60 s deadline, a fail-safe like the timeout. It runs in a child process,
    because a corrupted callback table breaks every later call in the process it happens in; the
    120 s timeout is a fail-safe, not a timing."""
    _runner()
    out = subprocess.run(
        [sys.executable, "-c", CONCURRENT], capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, out.stderr[-2000:]
    summary = [line for line in out.stdout.splitlines() if " calls, " in line]
    assert summary == ["800 calls, 0 wrong, 0 raised"], out.stdout[-2000:]
    print(out.stdout.splitlines()[-1])


def test_calls_add_nothing_to_wasmtime_pys_tables(guest_workdir, monkeypatch) -> None:
    """Guards a change: after one call per engine, a call defines no host function and sets no
    wasmtime-py custom output, and the runner's own output table empties once wasmtime has freed
    every call's streams. The loop that waits for those frees, which wasmtime runs on
    its own threads, is a fail-safe that counts rounds."""
    import gc
    import time

    import wasmtime

    from wasi_python import _wasmtime_ffi
    from wasi_python._process import process

    run = _runner()
    root = _root(guest_workdir)
    for fuel in (None, 10**10):
        run(["-c", "print(1)"], root=root, fuel=fuel)
    counts = {"define_func": 0, "custom outputs": 0}
    define_func = wasmtime.Linker.define_func

    def counted(self, *args, **kwargs):
        counts["define_func"] += 1
        return define_func(self, *args, **kwargs)

    table = _wasmtime_ffi.custom_output_table()
    allocate = table.allocate

    def counted_output(value):
        counts["custom outputs"] += 1
        return allocate(value)

    monkeypatch.setattr(wasmtime.Linker, "define_func", counted)
    monkeypatch.setattr(table, "allocate", counted_output)
    functions = _wasmtime_ffi.host_function_count()
    for fuel in (None, 10**10, None):
        done = run(["-c", "print('x')"], root=root, fuel=fuel)
        assert (done.exit_code, done.stdout) == (0, b"x\n"), done
    assert counts == {"define_func": 0, "custom outputs": 0}, counts
    assert _wasmtime_ffi.host_function_count() == functions
    for _ in range(200):
        gc.collect()
        if not process().outputs:
            break
        time.sleep(0.01)
    assert not process().outputs, f"{len(process().outputs)} streams never freed"


CTRL_C = r"""
import signal, threading, time
signal.signal(signal.SIGINT, signal.default_int_handler)  # as in a plain script
import wasi_python


def host(frame):
    def later():
        time.sleep(0.5)  # a trigger, not a measurement: the guest is computing by then
        signal.raise_signal(signal.SIGINT)  # os.kill on Windows would end the process

    threading.Thread(target=later, daemon=True).start()
    return b"ok"


work = "x = 0\nfor i in range(30_000_000):\n    x += i\n" if "WORK" == "computes" else ""
code = (
    "import _host\n_host.call(b'go')\n"
    + work
    + "import time\ntime.sleep(10**6)\nprint('woke')\n"  # ignoring Ctrl-C hits the fail-safe
)
try:
    done = wasi_python.run(["-c", code], host=host, deadline_s=None)
    print("returned", done.exit_code, done.trapped, done.stdout)
except KeyboardInterrupt:
    print("KeyboardInterrupt")
print("next", wasi_python.run(["-c", "print(1)"]).stdout)
"""


@pytest.mark.parametrize("when", ["computes", "waits"])
def test_ctrl_c_while_the_guest_runs_ends_the_call(when) -> None:
    """Guards a change: Ctrl-C while a guest computed on the main thread raised inside
    wasmtime-py's trampoline and aborted the whole process (exit 134). Now the call stops at the
    guest's next wait or door call, or within a wait, and raises KeyboardInterrupt, and the
    process goes on. In a child process, with a 120 s fail-safe."""
    _runner()
    script = CTRL_C.replace("WORK", when)
    out = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, (out.returncode, out.stderr[-1500:])
    assert out.stdout.splitlines() == ["KeyboardInterrupt", "next b'1\\n'"], out.stdout


@pytest.mark.parametrize(
    "limit", [{"fuel": -1}, {"memory_bytes": -1}, {"memory_bytes": 2**63}], ids=str
)
def test_a_limit_that_would_remove_itself_is_refused(guest_workdir, monkeypatch, limit) -> None:
    """Guards a change: a negative fuel or memory cap, or a memory cap of 2**63 or more, meant no
    limit at all. run now refuses it with ValueError before any work: no private root is made and
    nothing is written into a given root."""
    run = _runner()
    scratch = Path(tempfile.mkdtemp(prefix="limits-", dir=guest_workdir))
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    root = _root(guest_workdir)

    class Untouched:
        def __getattr__(self, name):
            raise AssertionError(f"the artifacts were used before the check ({name})")

    for given in ({}, {"root": root}, {"artifacts": Untouched()}):
        with pytest.raises(ValueError):
            run(["-c", "print(1)"], **given, **limit)
    assert (list(scratch.iterdir()), list(root.iterdir())) == ([], [])


class _Index:
    """An integer that is not an int, as a numpy integer is."""

    def __init__(self, value: int) -> None:
        self.value = value

    def __index__(self) -> int:
        return self.value


def test_a_limit_given_as_another_integer_type_works(guest_workdir, monkeypatch) -> None:
    """Guards a change: run passes on the plain values it checked, so a numpy-style integer cap
    is honoured and fuel_used is a plain int, from an argument or from DEFAULTS."""
    run = _runner()
    from wasi_python import runner

    done = run(
        ["-c", "print(12345)"],
        root=_root(guest_workdir),
        fuel=_Index(10**10),
        output_bytes=_Index(3),
    )
    assert (done.exit_code, done.stdout, done.truncated) == (0, b"123", ("stdout",)), done
    assert type(done.fuel_used) is int, done
    monkeypatch.setattr(runner, "DEFAULTS", runner.Defaults(_Index(1 << 30), 60.0, _Index(3)))
    done = run(["-c", "print(12345)"], root=_root(guest_workdir))
    assert (done.exit_code, done.stdout, done.truncated) == (0, b"123", ("stdout",)), done


@pytest.mark.parametrize(
    "inputs",
    [
        {"argv": ["-c", "print(1)", "a\0b"]},
        {"env": {"HOME\0x": "/shared"}},
        {"env": {"K=X": "v"}},
        {"argv": ["-c", "print(1)", "\udcff"]},
    ],
    ids=["NUL in argv", "NUL in an env key", "= in an env key", "lone surrogate"],
)
def test_an_input_the_guest_would_see_differently_is_refused(
    guest_workdir, monkeypatch, inputs
) -> None:
    """Guards a change: a NUL cut an argument or an env key short, and an = split a key, so
    {"HOME\\0x": "/shared"} passed a filter for HOME and set HOME. run now refuses such input
    with ValueError before any work."""
    run = _runner()
    scratch = Path(tempfile.mkdtemp(prefix="inputs-", dir=guest_workdir))
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    root = _root(guest_workdir)
    argv = inputs.get("argv", ["-c", "print(1)"])
    env = inputs.get("env")

    class Untouched:
        def __getattr__(self, name):
            raise AssertionError(f"the artifacts were used before the check ({name})")

    for given in ({}, {"root": root}, {"artifacts": Untouched()}):
        with pytest.raises(ValueError):
            run(argv, env=env, **given)
    assert (list(scratch.iterdir()), list(root.iterdir())) == ([], [])


class _Lying(str):
    """A str whose own __str__ and encode lie: the guest must see the real text."""

    def __str__(self) -> str:
        return "evil"

    def encode(self, *args, **kwargs):
        return b"evil"


def test_the_guest_gets_exactly_the_checked_inputs(guest_workdir) -> None:
    """Guards a change: run passes on the values it checked, so a generator argv is not used
    up by the check, a str subclass arrives as its real text, and a non-contiguous memoryview
    arrives as its bytes."""
    run = _runner()
    code = "import os, sys; print(sys.argv[1:], os.environ['K'], sys.stdin.read())"
    done = run(
        (a for a in ["-c", code, _Lying("arg")]),
        root=_root(guest_workdir),
        env={_Lying("K"): _Lying("val")},
        stdin=memoryview(b"h_i_")[::2],
    )
    assert (done.exit_code, done.stdout) == (0, b"['arg'] val hi\n"), done


# Run from async code. Each check runs its calls in a child process with a 120 s
# timeout, a fail-safe and not a timing: the defect each one guards would make a call run forever.


def _child(script: str, *args: str) -> list[str]:
    _runner()
    out = subprocess.run(
        [sys.executable, "-c", script, *args], capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, (out.returncode, out.stderr[-1500:])
    return out.stdout.splitlines()


LOOP_FREE = r"""
import asyncio, contextvars, threading
import wasi_python

gate, late = threading.Event(), threading.Event()
request = contextvars.ContextVar("request")


def host(frame):
    # The guest waits here until the loop has counted 1,000 turns. A blocked loop never counts:
    # the first wait ends at its fail-safe, and every later one at once.
    if request.get(None) != "from main":  # the worker runs in a copy of the caller's context
        return b"NO CONTEXT"
    if gate.wait(0 if late.is_set() else 60):
        return b"ok"
    late.set()
    return b"LATE"


CODE = "import _host, sys\na = _host.call(b'x')\nprint(sys.argv[1] if a == b'ok' else a.decode())"


async def count():
    for _ in range(1000):
        await asyncio.sleep(0)
    gate.set()


async def main():
    request.set("from main")
    counter = asyncio.create_task(count())
    calls = [wasi_python.run_async(["-c", CODE, f"t{i}"], host=host) for i in range(4)]
    done = await asyncio.gather(*calls)
    await counter
    print(sorted(r.stdout.decode().strip() for r in done))


asyncio.run(main())
"""


def test_async_calls_do_not_block_the_loop() -> None:
    """Guards a change: four `run_async` calls each wait in the door until the event loop has
    turned 1,000 times, so they finish only if the loop runs while they do. A
    `run_async` that ran its call in the coroutine reached the host's fail-safe and printed LATE.
    The host also sees the caller's context variables, as `asyncio.to_thread` gives them."""
    assert _child(LOOP_FREE) == ["['t0', 't1', 't2', 't3']"]


CANCEL_ASYNC = r"""
import asyncio, concurrent.futures, os, sys, tempfile, threading
tempfile.tempdir = tempfile.mkdtemp()  # the private root and the stdin scratch are made here
import wasi_python

# The sleeping guest computes once it wakes, so only the epoch callback can end it then.
WORK = {"busy": "while True: pass", "sleeping": "import time; time.sleep(10**6)\nwhile True: pass"}[
    sys.argv[1]
]


class Counting(concurrent.futures.ThreadPoolExecutor):
    finished = 0

    def submit(self, fn, /, *args, **kwargs):
        def counted(*a, **k):
            try:
                return fn(*a, **k)
            finally:
                Counting.finished += 1

        return super().submit(counted, *args, **kwargs)


pool = Counting(1)  # one worker: a new call completes only if the cancelled one freed it
started = threading.Event()


def host(frame):
    started.set()
    return b""


async def main():
    code = "import _host\n_host.call(b'x')\n" + WORK
    call = wasi_python.run_async(["-c", code], host=host, deadline_s=None, executor=pool)
    task = asyncio.create_task(call)
    await asyncio.to_thread(started.wait, 120)
    task.cancel()
    try:
        await task
        print("not cancelled")
    except asyncio.CancelledError:
        # The process's own zip folder lives until it exits: not the call's.
        left = sorted(
            n for n in os.listdir(tempfile.tempdir)
            if n.startswith("wasi-python") and not n.startswith("wasi-python-zip-")
        )
        print("cancelled", Counting.finished, left)
    print((await wasi_python.run_async(["-c", "print('next')"], executor=pool)).stdout)


asyncio.run(main())
"""


@pytest.mark.parametrize("work", ["busy", "sleeping"])
def test_cancelling_an_async_call_stops_its_guest(work) -> None:
    """Guards a change: cancelling the task that awaits `run_async` stops its guest, frees its
    worker and removes its private root before `CancelledError` reaches the caller.
    The guest has no deadline and no other call runs, so only the cancel can end it."""
    assert _child(CANCEL_ASYNC, work) == ["cancelled 1 []", "b'next\\n'"]


CANCEL_RUN = r"""
import asyncio, signal, sys, threading
import wasi_python
from wasi_python import _home, _limits, runner
from wasi_python._process import process

case = sys.argv[1]
event = threading.Event()


def sets(frame):
    event.set()
    return b""


def raises(frame):
    raise asyncio.CancelledError


def ticks(n):
    # Hold the host in the door until the runner's ticker has advanced n epochs: a count, never a
    # time. Past CANCEL_TICKS + 2 (the engine can run one round ahead of the count, and one to
    # spare) the store's epoch deadline is overdue, whatever its phase.
    start = process().ticker_count
    while process().ticker_count < start + n:
        threading.Event().wait(0.001)


def show(r):
    print(r.trapped, r.exit_code, r.fuel_used, r.stdout)


busy, sleeps = "while True: pass", "import time; time.sleep(10**6)"
door = "import _host\n_host.call(b'x')\n"
after = door + "print('after the door')\n"
if case.startswith("door-cancel-"):
    started = threading.Event()

    def blocks(frame):
        started.set()
        event.wait()  # the check sets it once the host has started
        ticks(_limits.CANCEL_TICKS + 2)
        return b"ok"[: int(case.rsplit("-", 1)[1])]

    def check():
        started.wait()
        event.set()

    threading.Thread(target=check, daemon=True).start()
    show(wasi_python.run(["-c", after], host=blocks, cancel=event, deadline_s=None, fuel=10**15))
elif case == "door-deadline":
    deadline_s = 60.0  # long enough that no load ends the run before the door

    def blocks(frame):
        print("in the door", flush=True)  # the guest reached the door before its deadline
        # By count, never by time: this call's deadline is moved to
        # the ticker's count now, then the host holds the door until the cancel check, every
        # CANCEL_TICKS, has run past it.
        _home._stack()[-1].stop_at = process().ticker_count
        ticks(_limits.CANCEL_TICKS + 2)
        return b"ok"

    r = wasi_python.run(
        ["-c", after], host=blocks, cancel=event, deadline_s=deadline_s, fuel=10**15
    )
    show(r)
elif case == "door-ctrl-c":
    signal.signal(signal.SIGINT, signal.default_int_handler)  # a parent may have ignored it

    def blocks(frame):
        signal.raise_signal(signal.SIGINT)  # os.kill on Windows would end the process
        event.set()
        ticks(_limits.CANCEL_TICKS + 2)
        return b"ok"

    try:
        r = wasi_python.run(["-c", after], host=blocks, cancel=event, deadline_s=None)
        print("returned", r.trapped)
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
elif case in ("busy", "sleeping"):
    work = busy if case == "busy" else sleeps
    r = wasi_python.run(["-c", door + work], host=sets, cancel=event, deadline_s=None, fuel=10**15)
    print(r.trapped, r.fuel_used)
elif case == "stop":
    code = "import _host\ntry:\n    _host.call(b'x')\nexcept Exception:\n    pass\n" + busy
    try:
        wasi_python.run(["-c", code], host=raises, cancel=event, deadline_s=None)
        print("returned")
    except asyncio.CancelledError:
        print("CancelledError")
else:
    r = wasi_python.run(["-c", busy], cancel=event, deadline_s=0.2, fuel=10**15)
    print(r.trapped, r.fuel_used)
"""


@pytest.mark.parametrize("work", ["busy", "sleeping"])
def test_run_with_cancel(work) -> None:
    """Guards a change: `run(cancel=event)` stops a computing or waiting guest once the event is
    set, and names it "cancelled" with no fuel count. The guest has no deadline."""
    assert _child(CANCEL_RUN, work) == ["cancelled None"]


def test_a_stop_holds_under_cancel() -> None:
    """Guards a change: a host's exception still stops a call that has a `cancel` (the
    runner's stop from inside a host function), though the guest catches the door's error and
    computes on with no deadline."""
    assert _child(CANCEL_RUN, "stop") == ["CancelledError"]


def test_a_deadline_under_cancel_is_named() -> None:
    """Guards a change: under `cancel=`, a deadline reaches Python as the epoch callback's error,
    not as wasmtime's interrupt trap; the runner still names it "deadline"."""
    assert _child(CANCEL_RUN, "deadline") == ["deadline None"]


@pytest.mark.parametrize("size", [2, 0])
def test_a_cancel_during_a_door_call_is_named(size) -> None:
    """Guards a change: a cancel set while the host blocks in a door call, held there past
    CANCEL_TICKS by count, names the run "cancelled", with no exit code, no fuel count and
    nothing the guest would print after the door; for a 2-byte answer and an empty one.
    Before it, the overdue epoch check fired in host_alloc and the run was named by
    wasmtime's raw error."""
    assert _child(CANCEL_RUN, f"door-cancel-{size}") == ["cancelled None None b''"]


def test_a_deadline_during_a_door_call_under_cancel_is_named() -> None:
    """Guards a change: under `cancel=` (never set), a deadline that passes while the host blocks
    in a door call, counted in ticks, names the run "deadline", with no exit code and no fuel
    count. The host's first line proves the guest reached the door before its
    deadline. The deadline passes by count in the door, so no
    start-up speed decides the outcome."""
    assert _child(CANCEL_RUN, "door-deadline") == ["in the door", "deadline None None b''"]


def test_ctrl_c_before_a_cancel_in_the_door() -> None:
    """Guards a change: on the main thread, Ctrl-C and a cancel both pending while the host blocks
    in a door call past CANCEL_TICKS by count: Ctrl-C comes first, and the call raises
    KeyboardInterrupt."""
    assert _child(CANCEL_RUN, "door-ctrl-c") == ["KeyboardInterrupt"]


AT_EXIT = r"""
import asyncio, dataclasses, threading
import wasi_python
from wasi_python import runner

runner.DEFAULTS = dataclasses.replace(runner.DEFAULTS, async_workers=1)
started = threading.Event()


def host(frame):
    started.set()
    return b""


loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()
code = "import _host\n_host.call(b'x')\nwhile True: pass"
for _ in range(2):  # one runs, one waits in the queue
    call = wasi_python.run_async(["-c", code], host=host, deadline_s=None)
    asyncio.run_coroutine_threadsafe(call, loop)
started.wait(120)
print("exiting")
"""


def test_exit_stops_async_guests() -> None:
    """Guards a change: at interpreter exit, a guest `run_async` started is stopped and a queued
    call never starts, so a process with a guest that has no deadline still exits."""
    assert _child(AT_EXIT) == ["exiting"]


FORK = r"""
import os, sys
import wasi_python

if sys.argv[1] == "used":
    wasi_python.run(["-c", "pass"])
pid = os.fork()
if pid == 0:
    try:
        r = wasi_python.run(["-c", "print('ran')"])
        print("child", r.stdout.decode().strip(), flush=True)
    except RuntimeError as e:
        print("child refused" if "forked" in str(e) else f"child {e}", flush=True)
    os._exit(0)
_, status = os.waitpid(pid, 0)
print("status", os.waitstatus_to_exitcode(status))
"""


NO_FORK = r"""
import os
import wasi_python
from wasi_python._process import process

print(hasattr(os, "register_at_fork"), wasi_python.run(["-c", "print('ran')"]).stdout)
# Labelled, so the line names each field of the fork state it shows.
print({"used": process().fork_used, "forked": process().forked})
"""


def test_a_forked_child_is_refused() -> None:
    """Guards a change: a child forked after its parent ran a guest aborted on macOS, and could
    not keep a deadline elsewhere; now it is refused with a clear error, while a child of a
    parent that only imported the package runs. A fresh parent, not pytest's. Where
    there is no fork (Windows), the runner registers no fork hook and a call runs as usual."""
    if not hasattr(os, "fork"):
        assert _child(NO_FORK) == ["False b'ran\\n'", "{'used': True, 'forked': False}"]
        return
    assert _child(FORK, "used") == ["child refused", "status 0"]
    assert _child(FORK, "imported") == ["child ran", "status 0"]


# Dead processes' folders are swept, by lock. Each check runs its calls in child
# processes with a 120 s timeout, a fail-safe, and a temporary folder of its own.


HELD = r"""
import sys, tempfile
tempfile.tempdir = sys.argv[1]
import wasi_python

def host(frame):
    print("held", flush=True)
    sys.stdin.readline()  # until the parent says go, or forever
    return b""

done = wasi_python.run(
    ["-c", "import _host; _host.call(b'x')"], root=True, host=host, stdin=b"secret"
)
print("ended", done.exit_code, flush=True)
"""

ONE_CALL = r"""
import sys, tempfile
tempfile.tempdir = sys.argv[1]
import wasi_python
from wasi_python._process import process

done = wasi_python.run(["-c", "print(1)"])
print(done.exit_code, process().sweep_swept)
"""


def _held_child(temp: Path) -> subprocess.Popen[str]:
    """A child whose call is held in its door; returns once the call has made its folders."""
    import queue

    child = subprocess.Popen(
        [sys.executable, "-c", HELD, str(temp)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    lines: queue.Queue[str] = queue.Queue()
    threading.Thread(target=lambda: lines.put(child.stdout.readline()), daemon=True).start()
    try:
        assert lines.get(timeout=120) == "held\n"  # a fail-safe, not a timing
    except BaseException:
        child.kill()
        child.wait()
        raise
    return child


def _locks_free(temp: Path) -> bool:
    """Whether every lock file in `temp` can be locked now; Windows frees a dead process's lock
    after a delay, so this tries up to 1,200 times (a fail-safe that counts tries)."""
    import time

    from wasi_python import _platform

    for _ in range(1200):
        free = True
        for lock in temp.glob("*.lock"):
            fd = os.open(lock, os.O_RDWR | getattr(os, "O_BINARY", 0))
            try:
                free = free and _platform.PLATFORM.try_lock(fd) is True
            finally:
                _platform.PLATFORM.unlock_close(fd)
        if free:
            return True
        time.sleep(0.1)
    return False


def _entries(temp: Path) -> list[str]:
    return sorted(p.name for p in temp.iterdir() if p.name.startswith("wasi-python-"))


def test_a_killed_process_leaves_nothing_after_the_next_call(tmp_path) -> None:
    """Guards a change: a process killed mid-call left its private root and its stdin folder in
    the temporary folder for good. Each now has a locked lock
    file beside it; the lock dies with the process, and the next process's first call removes
    both. Now the killed process's zip folder is left too, with its own
    lock file, and is swept with the others: three folders."""
    _runner()
    child = _held_child(tmp_path)
    child.kill()
    child.wait()
    left = _entries(tmp_path)
    assert len(left) == 6 and sum(n.endswith(".lock") for n in left) == 3, left
    assert sum(n.startswith("wasi-python-zip-") for n in left) == 2, left
    assert _locks_free(tmp_path), "a dead process's locks were never released"
    assert _child(ONE_CALL, str(tmp_path)) == ["0 3"]
    assert _entries(tmp_path) == []


def test_a_live_calls_folders_are_never_swept(tmp_path) -> None:
    """Guards a change: another process's first call sweeps only folders whose lock it can take;
    a call still running holds its lock, so its folders stay, and it cleans up after itself."""
    _runner()
    child = _held_child(tmp_path)
    try:
        held = _entries(tmp_path)
        assert len(held) == 6, held  # its private root, its stdin folder, its zip folder (017)
        assert _child(ONE_CALL, str(tmp_path)) == ["0 0"]
        assert _entries(tmp_path) == held
        out, _ = child.communicate("go\n", timeout=120)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
    assert out.split() == ["ended", "0"], out
    assert _entries(tmp_path) == []


# A private root never outlives its call. Each check runs its call in a child process
# with a temporary folder of its own; on POSIX the child lowers its soft RLIMIT_NOFILE to 128, so
# a tree of 256 levels is deeper than its free descriptors. Windows has no such limit, and its
# removal never held a handle per level: there the tree's host path passes 1,300 characters.

DEEP = r"""
import json, os, sys, tempfile, warnings
temp, kind, where, depth, name, soft = sys.argv[1:7]
tempfile.tempdir = temp
if int(soft):
    import resource
    hard = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    resource.setrlimit(resource.RLIMIT_NOFILE, (int(soft), hard))
import wasi_python

start = 'os.environ["HOME"]' if where == "home" else '"/"'
code = f'''
import os
fd = os.open({start}, os.O_RDONLY | os.O_DIRECTORY)
for i in range({depth}):
    os.mkdir({name!r}, dir_fd=fd)
    n = os.open({name!r}, os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd); os.close(fd); fd = n
os.close(fd)
print("built", {depth})
'''
root = True if where == "root" else sys.argv[7]
with warnings.catch_warnings(record=True) as seen:
    warnings.simplefilter("always")
    if kind == "run":
        done = wasi_python.run(["-c", code], root=root)
    else:
        with wasi_python.Session(root=root) as session:
            done = session.run(code)
left = sorted(n for n in os.listdir(temp) if n.startswith("wasi-python-root-"))
homes = [] if where == "root" else sorted(os.listdir(os.path.join(sys.argv[7], "tmp")))
out = done.stdout if isinstance(done.stdout, str) else done.stdout.decode()
print(json.dumps([done.exit_code, out, [str(w.message) for w in seen], left, homes]))
"""


def _deep(tmp_path: Path, kind: str, where: str) -> list:
    """Runs DEEP: [exit, stdout, warnings, roots left after the call, root/tmp's entries, and the
    temporary folder's wasi-python entries after the child exits (its zip folder gone too)]."""
    temp = tmp_path / "temp"
    temp.mkdir()
    args = [str(temp), kind, where]
    args += ["120", "a" * 10, "0"] if os.name == "nt" else ["256", "a", "128"]
    if where == "home":
        (tmp_path / "root").mkdir()
        args.append(str(tmp_path / "root"))
    result = json.loads(_child(DEEP, *args)[-1])
    return [*result, _entries(temp)]


@pytest.mark.parametrize("kind", ["run", "session"])
def test_a_deep_private_root_is_removed(tmp_path, kind) -> None:
    """Guards a change: a guest given root=True built a tree deeper than the process's free
    descriptors through dir_fd, and the runner's rmtree left the root and its lock file, silently.
    The removal now holds two descriptors at any depth."""
    depth = "120" if os.name == "nt" else "256"
    exit_code, out, seen, left, _, after = _deep(tmp_path, kind, "root")
    assert (exit_code, out) == (0, f"built {depth}\n"), (exit_code, out)
    assert seen == [], seen
    assert left == [], left
    assert after == [], after


@pytest.mark.parametrize("kind", ["run", "session"])
def test_a_deep_fresh_home_is_removed(tmp_path, kind) -> None:
    """Guards a change: a guest given a caller's root built a deep tree in its fresh HOME, and
    the HOME's rmtree left it in the caller's root (the session row reaches
    _remove_home)."""
    depth = "120" if os.name == "nt" else "256"
    exit_code, out, seen, _, homes, after = _deep(tmp_path, kind, "home")
    assert (exit_code, out) == (0, f"built {depth}\n"), (exit_code, out)
    assert seen == [], seen
    assert homes == [], homes
    assert after == [], after


MOVED = r"""
import json, os, sys, tempfile, warnings
temp, case, host = sys.argv[1:4]
tempfile.tempdir = temp
import wasi_python
from wasi_python import Grant

data = "/data" if case == "home" else "/w/data"
dest = 'os.environ["HOME"] + "/data"' if case == "home" else '"/data"'
code = f'''
import os
try:
    os.unlink("{data}/ro/secret")
    print("unlinked")
except OSError as e:
    print("refused", type(e).__name__)
os.rename("{data}", {dest})
'''
with warnings.catch_warnings(record=True) as seen:
    warnings.simplefilter("always")
    if case == "home":
        done = wasi_python.run(["-c", code], root=host)
    else:
        done = wasi_python.run(["-c", code], root=True, grants=[Grant(host, "/w", writable=True)])
out = done.stdout if isinstance(done.stdout, str) else done.stdout.decode()
err = done.stderr if isinstance(done.stderr, str) else done.stderr.decode(errors="replace")
mine = [str(w.message) for w in seen if issubclass(w.category, RuntimeWarning)]
print(json.dumps([done.exit_code, out, err[-300:], mine]))
"""


def _read_only(path: Path, on: bool) -> None:
    """The host's protection: a 0500 folder on POSIX; the read-only attribute on Windows."""
    import stat

    if os.name == "nt":
        os.chmod(path / "secret", stat.S_IREAD if on else stat.S_IWRITE | stat.S_IREAD)
    else:
        os.chmod(path, 0o500 if on else 0o700)


@pytest.mark.parametrize("case", ["home", "private"])
def test_the_removal_never_deletes_what_the_guest_may_not(tmp_path, case) -> None:
    """Guards a change: a removal that made folders writable deleted a file the host had made
    read-only, once the guest moved its writable parent into its HOME or its private root.
    The removal changes no mode: the file is kept, and one warning
    names the folder left. A Windows guest deletes a read-only file itself, so there is nothing
    for the removal to keep."""
    import shutil

    needs.need("read-only files")
    if os.name == "posix" and os.geteuid() == 0:
        pytest.skip("modes refuse nothing to root")
    host, temp = tmp_path / "host", tmp_path / "temp"
    (host / "data" / "ro").mkdir(parents=True)
    (host / "data" / "ro" / "secret").write_bytes(b"precious")
    temp.mkdir()
    _read_only(host / "data" / "ro", True)
    try:
        exit_code, out, err, seen = json.loads(_child(MOVED, str(temp), case, str(host))[-1])
        assert exit_code == 0 and out.startswith("refused PermissionError"), (exit_code, out, err)
        if case == "home":
            found = list((host / "tmp").glob(".home-*/data/ro/secret"))
        else:
            found = list(temp.glob("wasi-python-root-*/data/ro/secret"))
        assert [p.read_bytes() for p in found] == [b"precious"], found
        folder = found[0].parents[2]
        assert len(seen) == 1 and str(folder) in seen[0], seen
    finally:
        for ro in [*host.glob("tmp/.home-*/data/ro"), *temp.glob("wasi-python-root-*/data/ro")]:
            _read_only(ro, False)
        for left in [*host.glob("tmp/.home-*"), *temp.glob("wasi-python-root-*")]:
            shutil.rmtree(left) if left.is_dir() else left.unlink()


# Typed grants.
GRANTS_GUEST = r"""
import os
seen = {}
for g in ("/data", "/data/out", "/work", "/ref", "/tmp"):
    seen[g] = sorted(n for n in os.listdir(g) if not n.startswith(".home-"))
for g in ("/data", "/data/out", "/work", "/ref", "/tmp"):
    try:
        open(g + "/written", "w").write("x")
        seen[g].append("writable")
    except PermissionError:
        seen[g].append("read-only")
print(seen)
"""


@pytest.mark.parametrize("snapshot", [False, True], ids=["plain", "snapshot"])
def test_grants_reach_the_guest_in_any_order(guest_workdir, snapshot) -> None:
    """Guards a change: each grant reaches its guest path with its own mode, nested or
    not, whatever order the embedder lists them in (wasi-libc picks the longest guest prefix)."""
    import random

    from wasi_python import Grant

    run = _runner()
    base = Path(tempfile.mkdtemp(prefix="grants-", dir=guest_workdir))
    modes = {"data": False, "out": True, "work": True, "ref": False, "tmp": True}
    for name in modes:
        (base / name).mkdir()
        (base / name / f"{name}.txt").write_text(name)
    guests = {"data": "/data", "out": "/data/out", "work": "/work", "ref": "/ref", "tmp": "/tmp"}
    grants = [Grant(base / n, guests[n], writable=modes[n]) for n in modes]
    want = {
        "/data": ["data.txt", "read-only"],
        "/data/out": ["out.txt", "writable"],
        "/work": ["work.txt", "writable"],
        "/ref": ["ref.txt", "read-only"],
        "/tmp": ["tmp.txt", "writable"],
    }
    order = random.Random(17)  # a fixed seed: the same three orders every run
    for _ in range(3):
        order.shuffle(grants)
        for name in ("out", "work", "tmp"):
            (base / name / "written").unlink(missing_ok=True)
        done = run(["-c", GRANTS_GUEST], root=False, grants=grants, snapshot=snapshot)
        assert done.exit_code == 0, done
        assert done.stdout.decode().strip() == repr(want), (grants, done.stdout)
        assert not (base / "data" / "written").exists() and not (base / "ref" / "written").exists()


def test_no_root_and_no_grants_runs() -> None:
    """Guards a change: `root=False` with no grants still runs a program, on the zip
    alone; there is no `/`, and no fresh HOME, since there is no /tmp to make it in: the HOME is
    the runner's empty, read-only folder."""
    run = _runner()
    code = (
        "import os, json\n"
        "try:\n    os.listdir('/')\n    print('root')\nexcept OSError:\n    print('no root')\n"
        "print(os.environ.get('HOME', '')[:11], json.dumps([1]))\n"
    )
    done = run(["-c", code], root=False)
    assert (done.exit_code, done.stdout) == (0, b"no root\n/tmp/.home- [1]\n"), done


@pytest.mark.parametrize("with_root", [False, True], ids=["no root", "a root"])
def test_home_follows_a_writable_tmp_grant(guest_workdir, with_root) -> None:
    """Guards a change: HOME is made in the folder the guest sees at /tmp,
    so with a writable /tmp grant it is made there (the grant hides a root's own tmp), and it is
    removed after the call."""
    from wasi_python import Grant

    run = _runner()
    base = Path(tempfile.mkdtemp(prefix="home-", dir=guest_workdir))
    tmp = base / "tmp"
    tmp.mkdir()
    code = "import os; h = os.environ['HOME']; print(os.path.isdir(h), os.path.dirname(h))"
    root = base / "root" if with_root else False
    done = run(["-c", code], root=root, grants=[Grant(tmp, "/tmp", writable=True)])
    assert (done.exit_code, done.stdout) == (0, b"True /tmp\n"), done
    assert list(tmp.iterdir()) == []


FORK_ZIP = r"""
import os, sys, tempfile
tempfile.tempdir = sys.argv[1]
import wasi_python

def zips():
    return sorted(n for n in os.listdir(sys.argv[1]) if n.startswith("wasi-python-zip-"))

first = wasi_python.run(["-c", "print(1)"]).stdout
before = zips()
pid = os.fork()
if pid == 0:
    sys.exit(0)  # the child's exit runs the runner's clean-up: it must leave the parent's zip
os.waitpid(pid, 0)
print(first, zips() == before, wasi_python.run(["-c", "import json; print(2)"]).stdout)
"""


NO_FORK_ZIP = r"""
import os, sys, tempfile
tempfile.tempdir = sys.argv[1]
import wasi_python

def zips():
    return sorted(n for n in os.listdir(sys.argv[1]) if n.startswith("wasi-python-zip-"))

first = wasi_python.run(["-c", "print(1)"]).stdout
before = zips()
print(first, zips() == before, wasi_python.run(["-c", "import json; print(2)"]).stdout)
"""


def test_a_forked_child_leaves_the_parents_zip_folder(tmp_path) -> None:
    """Guards a change: the zip folder is the process's that made it; a child forked
    after a call forgets it, so the child's exit cannot remove it from under its parent. Where
    there is no fork (Windows), a second call reuses the folder."""
    script = FORK_ZIP if hasattr(os, "fork") else NO_FORK_ZIP
    assert _child(script, str(tmp_path)) == ["b'1\\n' True b'2\\n'"]


def test_a_deadline_during_the_grant_check_is_a_deadline(monkeypatch) -> None:
    """Guards a change: a deadline that passes while the runner checks the
    preopens traps the check module, and the call reports "deadline", never a refusal; the guest
    never runs. The epoch is advanced by count, not by waiting."""
    run = _runner()
    from wasi_python import _places
    from wasi_python._process import process

    real, calls = _places._check_preopens, []

    def late(wt, linker, store, check, preopens):
        # The deadline passes: the ticker's count, which every call's epoch callback reads now that
        # the runner polls every call, and every engine's epoch, which reaches the callback.
        process().ticker_count += 1000
        for engine in list(process().engines.values()):
            for _ in range(1000):
                engine.increment_epoch()
        return real(wt, linker, store, check, preopens)

    monkeypatch.setattr(_places, "_check_preopens", late)
    done = run(["-c", "import _host; _host.call(b'x')"], host=calls.append, deadline_s=0.05)
    assert (done.exit_code, done.trapped, calls) == (None, "deadline", []), done


# The command line.
INTENT = (
    b'{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\\n", "trapped": null, '
    b'"truncated": []}\n'
)


def _cli(capsysbinary, *args: str) -> tuple[int, dict]:
    _runner()
    from wasi_python import cli

    code = cli.main(list(args))
    out = capsysbinary.readouterr().out
    return code, json.loads(out) if out else {}


def test_the_command_runs_a_program_and_prints_its_result(capsysbinary, tmp_path) -> None:
    """Guards a change: `wasi-python run` prints one JSON line; the command's exit code
    says there is a result, the JSON how the program ended."""
    _runner()
    from wasi_python import cli

    assert cli.main(["run", "--", "-c", "print(1)"]) == 0
    assert capsysbinary.readouterr().out == INTENT
    assert _cli(capsysbinary, "run", "--", "-c", "import sys; sys.exit(3)") == (
        0,
        {"exit_code": 3, "fuel_used": None, "stderr": "", "stdout": "", "trapped": None,
         "truncated": []},
    )  # fmt: skip
    (tmp_path / "in").write_bytes(b"from a file\n")
    code, line = _cli(capsysbinary, "run", "--stdin", str(tmp_path / "in"), "--", "-c",
                      "import sys; print(sys.stdin.read(), end='')")  # fmt: skip
    assert (code, line["stdout"]) == (0, "from a file\n")
    code, line = _cli(capsysbinary, "run", "--deadline-s", "0.5", "--", "-c", "while True: pass")
    assert (code, line["trapped"]) == (0, "deadline")
    code, line = _cli(capsysbinary, "run", "--fuel", "1000", "--", "-c", "while True: pass")
    assert (code, line["trapped"]) == (0, "out of fuel")


COMMAND_CTRL_C = r"""
import signal, sys, threading, time
from wasi_python import cli

signal.signal(signal.SIGINT, signal.default_int_handler)  # a parent may have ignored it

cli.main(["run", "--", "-c", "pass"])  # warm: the module is compiled or loaded
sys.stdout.buffer.flush()
threading.Thread(target=lambda: (time.sleep(1), signal.raise_signal(signal.SIGINT))).start()
code = cli.main(["run", "--deadline-s", "none", "--", "-c", "while True: pass"])
print("exit", code, flush=True)
"""


def test_ctrl_c_stops_the_command_with_130() -> None:
    """Guards a change: the command passes an unset `cancel`, so Ctrl-C stops
    a guest that computes, with no deadline, and the command answers 130 and prints nothing more.
    The sleep only makes the signal likely to land while the guest computes; either way the answer
    must be 130. A fail-safe timeout asserts no duration."""
    lines = _child(COMMAND_CTRL_C)
    assert len(lines) == 2 and json.loads(lines[0])["exit_code"] == 0, lines
    assert lines[1] == "exit 130", lines


def test_the_installed_command_prints_the_same_line() -> None:
    """Guards a change: the `wasi-python` script this environment installed."""
    import shutil
    import sysconfig

    _runner()
    script = shutil.which("wasi-python", path=sysconfig.get_path("scripts"))
    assert script is not None, sysconfig.get_path("scripts")
    out = subprocess.run([script, "run", "--", "-c", "print(1)"], capture_output=True, timeout=120)
    assert (out.returncode, out.stdout) == (0, INTENT), out.stderr[-500:]


def test_the_command_grants_folders(capsysbinary, tmp_path) -> None:
    """Guards a change: `--grant` and `--grant-writable` reach the guest with their
    modes; a write to the read-only one fails in the program, not in the command; a grant `run()`
    refuses (the temporary folder, named as the runner sees it) is exit 1."""
    ro, rw = tmp_path / "in", tmp_path / "out"
    ro.mkdir()
    rw.mkdir()
    (ro / "in.txt").write_text("data")
    grants = ["--grant", f"/in={ro}", "--grant-writable", f"/out={rw}"]
    copy = "open('/out/out.txt', 'w').write(open('/in/in.txt').read().upper())"
    code, line = _cli(capsysbinary, "run", *grants, "--", "-c", copy)
    assert (code, line["exit_code"]) == (0, 0), line
    assert (rw / "out.txt").read_text() == "DATA" and (ro / "in.txt").read_text() == "data"
    code, line = _cli(capsysbinary, "run", *grants, "--", "-c", "open('/in/x', 'w')")
    assert (code, line["exit_code"]) == (0, 1), line
    last = line["stderr"].strip().splitlines()[-1]
    assert last.startswith("PermissionError: [Errno 63] Operation not permitted"), last
    code, line = _cli(capsysbinary, "run", "--grant", f"/t={tempfile.gettempdir()}", "--", "-")
    assert (code, line["kind"]) == (1, "ValueError"), line
    assert "holds the temporary folder" in line["error"], line


# Read-only mounts: a provider's files at a guest path, served from embedder code.
# The provider is the harness's in-memory tree, which counts its own calls; a guest asks the
# door for the counts between its steps, so each step's calls are counted exactly.

MOUNT_READS = r"""
import _host, json, os, select, selectors

def calls():
    return json.loads(_host.call(b"calls"))

def step(name, fn):
    before = calls()
    value = fn()
    after = calls()
    print(json.dumps([name, value, {k: after[k] - before[k] for k in after}]))

step("read", lambda: open("/work/a.txt").read())
step("listdir", lambda: sorted(os.listdir("/work")))
step("scandir", lambda: sorted((e.name, e.is_dir()) for e in os.scandir("/work/d")))
step("stat", lambda: (os.stat("/work/a.txt").st_size, os.path.isdir("/work/d")))
f = open("/work/b.txt", "rb")
fd = f.fileno()
step("fileno", lambda: fd >= 2**30)
step("os.read", lambda: os.read(fd, 10).decode())
p = select.poll()
p.register(fd, select.POLLIN)
step("poll", lambda: p.poll(0) == [(fd, select.POLLIN)])
sel = selectors.DefaultSelector()
sel.register(f, selectors.EVENT_READ)
step("selector", lambda: [k.fd == fd for k, _ in sel.select(0)])
try:
    select.select([f], [], [], 0)
    step("select", lambda: "accepted")
except ValueError as e:
    step("select", lambda: "ValueError")
step("grant", lambda: open("/data/in.csv").read())
"""


def _mount_host(provider):
    import json as _json

    return lambda frame: _json.dumps(provider.calls).encode()


@BINARY
def test_a_mount_serves_reads(guest_workdir, which) -> None:
    """A read makes one `read`, a listing of the mount one `list` and of a folder in it one
    `stat` then one `list`, a stat one `stat`;
    the bytes are the provider's; a mount's file has a number from 2**30 that os.read,
    select.poll and selectors accept and select.select refuses (Decision 6); the record's
    counts are the provider's own; a grant beside the mount reads as before."""
    from harness.files import MemoryProvider
    from wasi_python import Grant, Mount

    run = _runner()
    data = Path(tempfile.mkdtemp(prefix="mount-", dir=guest_workdir))
    (data / "in.csv").write_text("a,b\n1,2\n")
    provider = MemoryProvider()
    done = run(
        ["-c", MOUNT_READS],
        mounts=[Mount(provider, "/work")],
        grants=[Grant(data, "/data")],
        host=_mount_host(provider),
        snapshot=which == "snapshot",
    )
    assert (done.exit_code, done.trapped, done.stderr) == (0, None, b""), done
    no = {
        "stat": 0,
        "list": 0,
        "read": 0,
        "write": 0,
        "mkdir": 0,
        "remove": 0,
        "rmdir": 0,
        "rename": 0,
    }
    steps = [json.loads(line) for line in done.stdout.decode().splitlines()]
    assert steps == [
        ["read", "hello, mount\n", no | {"read": 1}],
        ["listdir", ["a.txt", "b.txt", "d", "e"], no | {"list": 1}],
        ["scandir", [["x.txt", False]], no | {"stat": 1, "list": 1}],  # a folder is asked first
        ["stat", [13, True], no | {"stat": 2}],  # os.stat and os.path.isdir: one each
        ["fileno", True, no],
        ["os.read", "b\n", no],
        ["poll", True, no],
        ["selector", [True], no],
        ["select", "ValueError", no],
        ["grant", "a,b\n1,2\n", no],
    ], done.stdout
    assert done.files is not None
    # The counts writable mounts add, all zero here.
    write_half = {"write": 0, "mkdir": 0, "remove": 0, "rmdir": 0, "rename": 0}
    assert (
        dict(done.files.calls) == provider.calls == {"stat": 3, "list": 2, "read": 2} | write_half
    )
    assert done.files.faults == ()


GRANT_PARITY = r"""
import _host, errno, json, os, sys

base, out = sys.argv[1], "/out"
rows = []

def row(name, fn):
    before = int(_host.call(b"total"))
    try:
        value = fn()
    except OSError as e:
        value = ["errno", e.errno]
    rows.append([name, [value, int(_host.call(b"total")) - before]])

def opened(path, mode):
    with open(path, mode) as f:
        return "opened"

def seeks():
    with open(base + "/a.txt", "rb") as f:
        return [f.seek(100), f.tell(), f.read(4).hex(), os.pread(f.fileno(), 4, 1000).hex(),
                f.seek(-2, 2), f.read().hex()]

row("missing file", lambda: opened(base + "/missing", "rb"))
row("folder opened as a file", lambda: opened(base + "/d", "rb"))
row("file listed as a folder", lambda: os.listdir(base + "/a.txt"))
row("missing parent", lambda: opened(base + "/missing/x.txt", "rb"))
row("dotdot that escapes", lambda: opened(base + "/../etc/passwd", "rb"))
row("dotdot that climbs and returns", lambda: opened(base + "/d/../../work/b.txt", "rb"))
row("dotdot within", lambda: open(base + "/d/../b.txt").read())
for mode in ("wb", "ab", "xb", "r+b", "w+b"):
    row(f"open {mode}", lambda: opened(base + "/a.txt", mode))
row("create", lambda: opened(base + "/new.txt", "wb"))
row("mkdir", lambda: os.mkdir(base + "/newdir"))
row("remove", lambda: os.remove(base + "/a.txt"))
row("rmdir", lambda: os.rmdir(base + "/e"))
row("rename within", lambda: os.rename(base + "/a.txt", base + "/c.txt"))
row("rename to a writable grant", lambda: os.rename(base + "/a.txt", out + "/c.txt"))
row("rename from a writable grant", lambda: os.rename(out + "/w.txt", base + "/c.txt"))
row("link", lambda: os.link(base + "/a.txt", base + "/c.txt"))
row("symlink", lambda: os.symlink("a.txt", base + "/l"))
row("utime", lambda: os.utime(base + "/a.txt", (1, 1)))
row("truncate", lambda: os.truncate(base + "/a.txt", 0))
row("readlink of a file", lambda: os.readlink(base + "/a.txt"))
row("seek, tell and pread past the end", seeks)
row("trailing slash on a file", lambda: opened(base + "/a.txt/", "rb"))
row("trailing slash-dot on a file", lambda: opened(base + "/a.txt/.", "rb"))
row("a component over 255 bytes", lambda: opened(base + "/" + "x" * 256, "rb"))
row("stat of a file", lambda: [os.path.isfile(base + "/a.txt"), os.stat(base + "/a.txt").st_size])
row("stat of a folder", lambda: [os.path.isdir(base + "/d"), os.path.isdir(base + "/a.txt")])
row("sorted listing", lambda: sorted(os.listdir(base)))
row("walk", lambda: sorted((p, sorted(d), sorted(f)) for p, d, f in os.walk(base)))
print(json.dumps(rows))
"""
WRITE_ROWS = (
    "open wb", "open ab", "open xb", "open r+b", "open w+b", "create", "mkdir", "remove", "rmdir",
    "rename within", "rename to a writable grant", "rename from a writable grant", "link",
    "symlink", "utime", "truncate",
)  # fmt: skip
HOST_ROWS_V14 = {  # the grant's answer is the host's own error: asserted on POSIX hosts only
    "trailing slash on a file",
    "trailing slash-dot on a file",
    "a component over 255 bytes",
    "readlink of a file",
}


@BINARY
def test_a_mount_answers_as_a_grant_does(guest_workdir, which) -> None:
    """The same tree as an in-memory mount and as a read-only grant on
    disk gives the same result or errno for every row; every write row makes no provider call.
    Decision 6's deliberate differences are asserted as decided, not as parity."""
    from harness.files import MemoryProvider, write_tree
    from wasi_python import Grant, Mount

    run = _runner()
    base = Path(tempfile.mkdtemp(prefix="parity-", dir=guest_workdir))
    tree = write_tree(base / "tree")
    results = {}
    for side in ("grant", "mount"):
        out = base / f"out-{side}"
        out.mkdir()
        (out / "w.txt").write_text("w")
        provider = MemoryProvider()
        grants = [Grant(out, "/out", writable=True)]
        if side == "grant":
            grants.append(Grant(tree, "/work"))
        mounts = [Mount(provider, "/work")] if side == "mount" else []
        done = run(
            ["-c", GRANT_PARITY, "/work"],
            grants=grants,
            mounts=mounts,
            host=lambda frame, p=provider: str(p.total()).encode(),
            snapshot=which == "snapshot",
        )
        assert (done.exit_code, done.stderr) == (0, b""), done
        rows = dict(json.loads(done.stdout))
        results[side] = {name: value for name, (value, _) in rows.items()}
        if side == "mount":  # every write row makes no provider call
            assert {name: rows[name][1] for name in WRITE_ROWS} == dict.fromkeys(WRITE_ROWS, 0)
        assert sorted(p.name for p in out.iterdir()) == ["w.txt"]
    assert sorted(p.name for p in tree.iterdir()) == ["a.txt", "b.txt", "d", "e"]
    grant, mount = results["grant"], results["mount"]
    for name in WRITE_ROWS:
        assert grant[name] == mount[name] == ["errno", 63], (name, grant[name], mount[name])
    differ = {
        k: (grant[k], mount[k])
        for k in grant
        if grant[k] != mount[k] and (os.name == "posix" or k not in HOST_ROWS_V14)
    }
    assert differ == {}, differ


ROOT_MOUNT = r"""
import os, json, numpy, pandas
rows = {"abs": open("/a.txt").read(), "rel": open("a.txt").read()}
try:
    open("/usr/./local/lib/x")
    rows["nested"] = "opened"
except OSError as e:
    rows["nested"] = e.errno
rows["home"] = os.environ.get("HOME", "")[:11]
rows["numpy"] = numpy.__name__ in __import__("sys").modules
print(json.dumps(rows))
"""
# `-c pass` with a mount at /: measured 0 provider calls on the snapshot and 9 on the plain
# reactor (CPython's start-up path search: 4 stats, 5 reads); the bound is twice the larger.
ROOT_START_BOUND = 18


@BINARY
def test_a_mount_at_the_root(guest_workdir, which) -> None:
    """A mount at / is the guest's whole filesystem but for what more
    specific preopens own: an absolute and a relative path read the provider's file, numpy and
    pandas import from the zip, a path the zip owns spelled past wasi-libc is EPERM with no
    call, and the HOME is the runner's empty, read-only folder, not the provider's. Start-up
    makes at most a bound of provider calls; root= with a mount at / is refused."""
    from harness.files import MemoryProvider
    from wasi_python import Mount

    run = _runner()
    provider = MemoryProvider()
    done = run(["-c", ROOT_MOUNT], mounts=[Mount(provider, "/")], snapshot=which == "snapshot")
    assert (done.exit_code, done.stderr) == (0, b""), done
    assert json.loads(done.stdout) == {
        "abs": "hello, mount\n",
        "rel": "hello, mount\n",
        "nested": 63,
        "home": "/tmp/.home-",
        "numpy": True,
    }
    assert not any(p.startswith("/usr/local/lib") for _, p in provider.paths), provider.paths
    quiet = MemoryProvider()
    done = run(["-c", "pass"], mounts=[Mount(quiet, "/")], snapshot=which == "snapshot")
    assert done.exit_code == 0 and quiet.total() <= ROOT_START_BOUND, quiet.paths
    for root in (True, guest_workdir):
        with pytest.raises(ValueError, match="whole filesystem"):
            run(["-c", "pass"], root=root, mounts=[Mount(quiet, "/")])


STAT_LOOP = (
    "import os\n"
    "for i in range({n}):\n"
    "    try:\n"
    "        os.stat('/work/a.txt')\n"
    "    except OSError:\n"
    "        pass\n"
    "print('after the loop')\n"
)


def test_the_file_call_limit_stops_the_run() -> None:
    """At `max_file_calls` the run stops, named "out of file calls",
    with no exit code and no fuel count, after exactly that many provider calls and before the
    line after the loop; the same under `cancel=` never set (the epoch callback's path and the
    entry guard). The default is 10,000."""
    from harness.files import MemoryProvider
    from wasi_python import Mount
    from wasi_python.runner import DEFAULTS

    run = _runner()
    for cancel in (None, threading.Event()):
        provider = MemoryProvider()
        done = run(
            ["-c", STAT_LOOP.format(n=10**6)],
            mounts=[Mount(provider, "/work")],
            max_file_calls=5,
            fuel=10**12,
            cancel=cancel,
        )
        ending = (done.exit_code, done.trapped, done.fuel_used, done.stdout)
        assert ending == (None, "out of file calls", None, b""), (cancel, done)
        assert provider.calls == {
            "stat": 5,
            "list": 0,
            "read": 0,
            "write": 0,
            "mkdir": 0,
            "remove": 0,
            "rmdir": 0,
            "rename": 0,
        }
        assert done.files is not None and dict(done.files.calls) == provider.calls
    assert DEFAULTS.file_calls == 10_000
    provider = MemoryProvider()
    done = run(["-c", STAT_LOOP.format(n=10_001)], mounts=[Mount(provider, "/work")])
    assert (done.trapped, done.stdout, provider.total()) == ("out of file calls", b"", 10_000)


MOUNT_CANCEL = r"""
import sys, threading
import wasi_python
from wasi_python import Errno, Mount, Stat, _home, _limits, runner
from wasi_python._process import process

case = sys.argv[1]
event = threading.Event()
loop = (
    "import os\nwhile True:\n    try:\n        os.stat('/work/x')\n"
    "    except OSError:\n        pass\n"
)


def ticks(n):
    start = process().ticker_count
    while process().ticker_count < start + n:
        threading.Event().wait(0.001)


DEADLINE_S = 60.0  # long enough that no load ends the run before the provider is reached


def past_deadline():
    # By count, never by time: the ticker's count, which the runner checks before each
    # provider call, and every engine's epoch, which stops the guest, both past this call's
    # deadline (the seams of the deadline check and tests/unit/test_runner_async.py).
    call = _home._stack()[-1]  # on the caller's thread, under its call, kept there
    process().ticker_count = call.stop_at
    for engine in list(process().engines.values()):
        for _ in range(int(DEADLINE_S / _limits.TICK_S) + 2):
            engine.increment_epoch()


class Provider:
    calls = 0

    def stat(self, path):
        Provider.calls += 1
        if case == "cancel" and Provider.calls == 3:
            event.set()
        if case == "deadline" and Provider.calls == 3:
            past_deadline()
        return Stat("file")

    def list(self, path):
        return Errno.ENOTDIR

    def read(self, path):
        return b""


mounts = [Mount(Provider(), "/work")]
if case == "cancel":
    r = wasi_python.run(["-c", loop], mounts=mounts, cancel=event, deadline_s=None)
elif case == "deadline":
    r = wasi_python.run(["-c", loop], mounts=mounts, deadline_s=DEADLINE_S)
else:  # a cancel while the guest makes a run of forwarded calls (prints)

    def later():
        ticks(_limits.CANCEL_TICKS * 3)
        event.set()

    threading.Thread(target=later, daemon=True).start()
    code = "while True:\n    print('x' * 100)\n"
    r = wasi_python.run(["-c", code], mounts=mounts, cancel=event, deadline_s=None)
print(r.trapped, r.exit_code, Provider.calls)
"""


@pytest.mark.parametrize(
    ("case", "want"),
    [
        ("cancel", "cancelled None 3"),
        ("deadline", "deadline None 3"),
        ("forwards", "cancelled None 0"),
    ],
)
def test_a_mount_keeps_its_deadline_and_cancel(case, want) -> None:
    """A provider that sets the call's cancel in its third call ends
    the run "cancelled" after exactly three calls; one that moves the ticker's count and the
    engine's epoch past the call's deadline in its third call (by count, never by time: so it
    is reached under any load) ends it "deadline" with no call after; a cancel during a run of
    forwarded calls is named "cancelled", never a raw error."""
    assert _child(MOUNT_CANCEL, case) == [want]


ERRNO_GUEST = r"""
import errno, json, os, sys
names = json.loads(sys.argv[1])
same = {name: getattr(errno, name) for name in names}
raised = {}
for name in names:
    try:
        os.stat("/work/" + name)
        raised[name] = None
    except OSError as e:
        raised[name] = e.errno
print(json.dumps([same, raised]))
"""


def test_the_errno_values_are_the_guests() -> None:
    """Each `Errno` member is the guest's errno of that name, and a
    provider that answers it makes the guest raise OSError with that errno."""
    from wasi_python import Errno, Mount

    class Answers:
        def stat(self, path):
            return Errno[path.strip("/")]

        def list(self, path):
            return Errno.ENOTDIR

        def read(self, path):
            return Errno.ENOENT

    run = _runner()
    names = [e.name for e in Errno]
    done = run(["-c", ERRNO_GUEST, json.dumps(names)], mounts=[Mount(Answers(), "/work")])
    assert done.exit_code == 0, done
    same, raised = json.loads(done.stdout)
    assert same == {e.name: e.value for e in Errno}
    assert raised == {e.name: e.value for e in Errno}


RAISED_GUEST = r"""
import json, os, sys
out = {}
for base in ("/r", "/o"):
    for name in json.loads(sys.argv[1]):
        try:
            os.stat(f"{base}/{name}")
            out[f"{base}/{name}"] = None
        except OSError as e:
            out[f"{base}/{name}"] = e.errno
print(json.dumps(out))
"""


def test_a_raised_oserror_is_the_answer_of_its_errno() -> None:
    """A provider that raises `OSError` with the host's own errno number
    for each of the 21 names gives the guest exactly what a provider returning `Errno[name]`
    gives (matched by name, never by number, which differs by host), with no fault, and the
    exception's message reaches neither the guest nor the result."""
    import errno

    from wasi_python import Errno, Mount, Stat

    secret = "a-provider-secret-061"

    class Returns:
        def stat(self, path):
            return Stat("dir") if path == "/" else Errno[path.strip("/")]

        def list(self, path):
            return []

        def read(self, path):
            return Errno.ENOENT

    class Raises(Returns):
        def stat(self, path):
            if path == "/":
                return Stat("dir")
            name = path.strip("/")
            raise OSError(getattr(errno, name), f"{name}: {secret}")

    run = _runner()
    names = [e.name for e in Errno]
    done = run(
        ["-c", RAISED_GUEST, json.dumps(names)],
        mounts=[Mount(Returns(), "/r"), Mount(Raises(), "/o")],
    )
    assert done.exit_code == 0, done
    answers = json.loads(done.stdout)
    for base in ("/r", "/o"):
        got = {name: answers[f"{base}/{name}"] for name in names}
        assert got == {e.name: e.value for e in Errno}, (base, got)
    assert done.files is not None
    assert done.files.faults == (), done.files.faults
    assert done.files.calls["stat"] == 2 * len(names), done.files.calls
    assert secret.encode() not in done.stdout + done.stderr
    assert secret not in repr(done)


class _CountStr(FileNotFoundError):
    """A mapped raise whose `__str__` counts: the runner must never format it."""

    calls: list[int] = []

    def __str__(self) -> str:
        _CountStr.calls.append(1)
        return "counted"


class _UserNotFound(FileNotFoundError):
    pass


def _kind_raises(path):
    """A `Stat` whose `kind` raises: an answer object's own code (R1: the property has
    a setter, since `Stat`'s frozen `__init__` sets `kind` with `object.__setattr__`)."""
    import errno

    from wasi_python import Stat

    class KindRaises(Stat):
        @property
        def kind(self):
            raise FileNotFoundError(errno.ENOENT, "from an answer object")

        @kind.setter
        def kind(self, value):
            pass  # stores nothing the runner reads

    return KindRaises("file", 1)


def _class_cases():
    """(name, method, how, action, expected): `how` raises (or returns) for the method; the guest
    does `action` on base/x and reports its errno, or for "open" whether it got a folder."""
    import errno

    from wasi_python import Errno

    def raising(make):
        def how(path):
            raise make()

        return how

    return [
        ("FileNotFoundError('x')", "stat", raising(lambda: FileNotFoundError("x")), "stat", 44),
        ("FileExistsError('x')", "stat", raising(lambda: FileExistsError("x")), "stat", 20),
        ("NotADirectoryError('x')", "stat", raising(lambda: NotADirectoryError("x")), "stat", 54),
        ("PermissionError('x')", "stat", raising(lambda: PermissionError("x")), "stat", 2),
        (
            "TimeoutError('timed out')",
            "stat",
            raising(lambda: TimeoutError("timed out")),
            "stat",
            73,
        ),
        ("a FileNotFoundError subclass", "stat", raising(lambda: _UserNotFound("x")), "stat", 44),
        (
            "PermissionError(EPERM)",
            "stat",
            raising(lambda: PermissionError(errno.EPERM, "x")),
            "stat",
            63,
        ),
        (
            "FileNotFoundError(EACCES)",
            "stat",
            raising(lambda: FileNotFoundError(errno.EACCES, "x")),
            "stat",
            2,
        ),
        (
            "OSError(EOPNOTSUPP)",
            "stat",
            raising(lambda: OSError(errno.EOPNOTSUPP, "x")),
            "stat",
            58,
        ),
        (
            "IsADirectoryError('x') at read",
            "read",
            raising(lambda: IsADirectoryError("x")),
            "open",
            "dir",
        ),
        ("EISDIR returned at read", "read", lambda path: Errno.EISDIR, "open", "dir"),
        ("a counting __str__", "stat", raising(lambda: _CountStr(errno.ENOENT, "x")), "stat", 44),
        (
            "FileNotFoundError(EINTR)",
            "stat",
            raising(lambda: FileNotFoundError(errno.EINTR, "x")),
            "stat",
            29,
        ),
        ("TimeoutError(99999)", "stat", raising(lambda: TimeoutError(99999, "x")), "stat", 29),
        ("a Stat whose kind raises", "stat", _kind_raises, "stat", 29),
        ("InterruptedError('x')", "stat", raising(lambda: InterruptedError("x")), "stat", 29),
        ("BlockingIOError('x')", "stat", raising(lambda: BlockingIOError("x")), "stat", 29),
        (
            "ConnectionRefusedError('x')",
            "stat",
            raising(lambda: ConnectionRefusedError("x")),
            "stat",
            29,
        ),
        ("OSError('x')", "stat", raising(lambda: OSError("x")), "stat", 29),
    ]


class _Answers:
    """A provider whose one `method` answers as `how` says; the others answer a small tree."""

    def __init__(self, method, how):
        self.method, self.how = method, how
        self.calls = {"stat": 0, "list": 0, "read": 0}

    def _answer(self, method, path, normal):
        self.calls[method] += 1
        return self.how(path) if method == self.method and path != "/" else normal

    def stat(self, path):
        from wasi_python import Stat

        return self._answer("stat", path, Stat("dir" if path == "/" else "file", 1))

    def list(self, path):
        return self._answer("list", path, [("x", "file")])

    def read(self, path):
        from wasi_python import Errno

        return self._answer("read", path, Errno.EISDIR if path == "/" else b"x")


CLASS_GUEST = r"""
import json, os, stat, sys
out = {}
for i, (name, action) in enumerate(json.loads(sys.argv[1])):
    path = f"/c{i}/x"
    try:
        if action == "open":
            fd = os.open(path, os.O_RDONLY)
            out[name] = "dir" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file"
            os.close(fd)
        else:
            os.stat(path)
            out[name] = "answered"
    except OSError as e:
        out[name] = e.errno
print(json.dumps(out))
"""


def test_an_oserrors_class_answers_when_its_errno_cannot() -> None:
    """With no errno at all, six classes answer (a `PermissionError` is
    EACCES); a present errno always wins, and one outside the closed set is EIO and a fault
    whatever the class; a raised `IsADirectoryError` at `read` is the EISDIR answer (a folder
    descriptor); an `OSError` from an answer object's own code stays a fault; and a mapped raise
    is never formatted."""
    from wasi_python import Mount

    run = _runner()
    cases = _class_cases()
    providers = [_Answers(method, how) for _, method, how, _, _ in cases]
    _CountStr.calls.clear()
    done = run(
        ["-c", CLASS_GUEST, json.dumps([[name, action] for name, _, _, action, _ in cases])],
        mounts=[Mount(p, f"/c{i}") for i, p in enumerate(providers)],
    )
    assert (done.exit_code, done.trapped, done.stderr) == (0, None, b""), done
    answers = json.loads(done.stdout)
    assert answers == {name: want for name, _, _, _, want in cases}, answers
    assert _CountStr.calls == [], "the runner formatted a mapped raise"
    assert done.files is not None
    faulty = [name for name, _, _, _, want in cases if want == 29]
    assert len(done.files.faults) == len(faulty) == 7, done.files.faults
    folders = [i for i, (_, _, _, action, _) in enumerate(cases) if action == "open"]
    assert len(folders) == 2, folders
    for i in folders:  # the folder rows, found by content: one read each, no list
        assert providers[i].calls == {"stat": 0, "list": 0, "read": 1}, providers[i].calls


WRITE_RAISED_GUEST = r"""
import json, os
out = {}
for base in ("/o", "/r"):
    def attempt(key, fn):
        try:
            fn()
            out[base + key] = None
        except OSError as e:
            out[base + key] = e.errno
    def closed():
        f = open(base + "/closed", "wb")
        f.write(b"data")
        f.close()
    attempt("/create", lambda: open(base + "/created", "wb").close())
    attempt("/close", closed)
    attempt("/mkdir", lambda: os.mkdir(base + "/made"))
    attempt("/rename", lambda: os.rename(base + "/a.txt", base + "/moved.txt"))
    attempt("/remove", lambda: os.remove(base + "/b.txt"))
    fd = os.open(base + "/left", os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    os.write(fd, b"x")  # left open for the ending's walk
print(json.dumps(out))
"""


def test_a_write_halfs_raised_oserror_is_a_refusal() -> None:
    """A writable mount's provider that raises `OSError` (the host's
    numbers) at a create, a close, a `mkdir`, a `rename`, a `remove` and the ending's walk gives
    the guest and the record exactly what a provider returning the same members gives: each a
    `RefusedWrite` with cause "refused", and no fault."""
    import errno

    from harness.files import MemoryProvider
    from wasi_python import Errno, Mount

    def content_only(make):
        def how(path, data):
            if data:
                raise make()

        return how

    def content_only_returns(member):
        return lambda path, data: member if data else None

    raised, returned = MemoryProvider(), MemoryProvider()
    raised.answers.update(
        {
            ("write", "/created"): PermissionError(errno.EACCES, "no create"),
            ("write", "/closed"): content_only(lambda: OSError(errno.ENOSPC, "full")),
            ("mkdir", "/made"): FileExistsError(errno.EEXIST, "there"),
            ("rename", "/a.txt"): OSError(errno.EXDEV, "elsewhere"),
            ("remove", "/b.txt"): IsADirectoryError("a folder"),
            ("write", "/left"): content_only(lambda: OSError(errno.EDQUOT, "quota")),
        }
    )
    returned.answers.update(
        {
            ("write", "/created"): Errno.EACCES,
            ("write", "/closed"): content_only_returns(Errno.ENOSPC),
            ("mkdir", "/made"): Errno.EEXIST,
            ("rename", "/a.txt"): Errno.EXDEV,
            ("remove", "/b.txt"): Errno.EISDIR,
            ("write", "/left"): content_only_returns(Errno.EDQUOT),
        }
    )
    run = _runner()
    done = run(
        ["-c", WRITE_RAISED_GUEST],
        mounts=[Mount(raised, "/o", writable=True), Mount(returned, "/r", writable=True)],
    )
    assert done.exit_code == 0, done
    answers = json.loads(done.stdout)
    want = {"/create": 2, "/close": 51, "/mkdir": 20, "/rename": 75, "/remove": 31}
    for base in ("/o", "/r"):
        assert {k: answers[base + k] for k in want} == want, answers
    assert done.files is not None
    assert done.files.faults == (), done.files.faults
    refused = {
        base: [
            (r.method, r.paths, r.errno, r.at, r.cause)
            for r in done.files.refused
            if r.mount == base
        ]
        for base in ("/o", "/r")
    }
    assert refused["/o"] == refused["/r"], refused
    assert {r[4] for r in refused["/o"]} == {"refused"}, refused
    assert refused["/o"][-1] == ("write", ("/left",), Errno.EDQUOT, "exit", "refused"), refused


@BINARY
def test_a_mounted_run_out_of_fuel_counts_the_cap(guest_workdir, which) -> None:
    """Through run(): with a fuel cap too small to finish, a run with
    a mount ends "out of fuel" with `fuel_used` equal to the cap, as the same run with a grant
    does. The exact equality of fuel is the unit check's."""
    from harness.files import MemoryProvider, write_tree
    from wasi_python import Grant, Mount

    run = _runner()
    tree = write_tree(Path(tempfile.mkdtemp(prefix="fuel-", dir=guest_workdir)))
    code = "while True:\n    print(open('/work/a.txt').read(), end='', flush=True)\n"
    cap = 400_000_000  # past start-up on both binaries (-c pass: 82 M and 241 M)
    for kw in ({"grants": [Grant(tree, "/work")]}, {"mounts": [Mount(MemoryProvider(), "/work")]}):
        done = run(["-c", code], fuel=cap, snapshot=which == "snapshot", **kw)
        assert (done.exit_code, done.trapped, done.fuel_used) == (None, "out of fuel", cap), done
        assert done.stdout.startswith(b"hello, mount\n"), done


def test_a_mount_at_tmp_means_no_home(guest_workdir) -> None:
    """A mount at /tmp counts as a read-only grant there, so a call with a root, private or
    given, makes no HOME in the root's own tmp, which the guest could not see behind the mount,
    and nothing at all there: its HOME is the runner's empty, read-only folder instead."""
    from harness.files import MemoryProvider
    from wasi_python import Mount

    run = _runner()
    root = _root(guest_workdir)
    for given in (True, root):
        done = run(
            ["-c", "import os; print(os.environ.get('HOME', '')[:11])"],
            root=given,
            mounts=[Mount(MemoryProvider(), "/tmp")],
        )
        assert (done.exit_code, done.stdout) == (0, b"/tmp/.home-\n"), (given, done)
    assert not (root / "tmp").exists() or list((root / "tmp").iterdir()) == []


# -------------------------------------------------------------------------------------------------
# The tool protocol through the door: the frame host passed as a raw host=, its record
# read from the object; run(tools=…) is the bound form of the same host.

TOOL_PROGRAM = """
from host import tools
import pandas
r = tools.lookup_region("EMEA")
df = pandas.DataFrame(r["months"])
print(r["code"], int(df["sales"].sum()), list(df.columns))
print(tools.reverse(b"abc\\x00"))
"""


def _region_tools() -> list:
    from wasi_python.tools import tool

    @tool(read_only=True)
    def lookup_region(code: str) -> dict:
        """Look up a sales region by its code.

        Args:
            code: The region code, such as "EMEA".
        """
        return {"code": code, "months": [{"month": m, "sales": 10 * m} for m in (1, 2, 3)]}

    @tool
    def reverse(data: bytes) -> bytes:
        """Reverse some bytes."""
        return data[::-1]

    return [lookup_region, reverse]


@BINARY
def test_the_guest_package_round_trips_through_the_door(guest, which) -> None:
    """Criterion 11: `from host import tools`, two calls, one result fed to pandas, bytes both
    ways; the record lists the discovery and both calls."""
    from wasi_python._tool_host import _ToolHost

    host = _ToolHost(_region_tools())
    r = guest(which, ["-c", TOOL_PROGRAM], host=host)
    assert r.exit_code == 0, r.describe()
    assert r.text == "EMEA 60 ['month', 'sales']\nb'\\x00cba'\n", r.text
    record = host.record
    assert [(o.op, o.tool, o.outcome) for o in record.outcomes] == [
        ("list", None, "ok"),
        ("call", "lookup_region", "ok"),
        ("call", "reverse", "ok"),
    ], record
    assert (record.frames, record.unlisted) == (3, 0)


FORGED = """
import _host, json
for args in ({"n": "seven"}, {"n": 7, "extra": 1}):
    frame = {"v": 1, "id": 1, "op": "call", "tool": "count", "args": args}
    answer = json.loads(_host.call(json.dumps(frame).encode()))
    print(answer["ok"], answer["error"]["kind"])
"""


def test_a_forged_frame_is_validated_first(guest) -> None:
    """Criterion 12: frames the guest writes itself, past the package, are checked against the
    schema before the gate or the tool sees them."""
    from wasi_python._tool_host import _ToolHost
    from wasi_python.tools import tool

    calls = []

    @tool
    def count(n: int) -> int:
        calls.append(n)
        return n

    gated = []
    host = _ToolHost([count], gate=gated.append)
    r = guest("snapshot", ["-c", FORGED], host=host)
    assert r.exit_code == 0, r.describe()
    assert r.text.split("\n")[:2] == ["False invalid_arguments", "False invalid_arguments"], r.text
    assert (calls, gated) == ([], [])
    assert [o.outcome for o in host.record.outcomes] == ["invalid_arguments"] * 2


def test_the_zip_carries_the_host_package(artifacts) -> None:
    """Criterion 13: the guest package is in the stdlib zip, compiled; its recipe files are in
    MANIFEST's recipe lines (the check that they cover every tracked recipe also runs)."""
    import zipfile

    needs.need("stdlib zip", "manifest")
    with zipfile.ZipFile(artifacts.path("python-stdlib.zip")) as z:
        names = set(z.namelist())
    assert {"host/__init__.pyc", "host/tools.pyc"} <= names, sorted(
        n for n in names if n.startswith("host")
    )
    recipes = artifacts.manifest().recipes
    assert {"recipes/guest/host/__init__.py", "recipes/guest/host/tools.py"} <= set(recipes)


# -------------------------------------------------------------------------------------------------
# Tools in the runner: run(tools=…), the door's cap before the copy, the bound of one
# tool call, and the record in the result. A tool that must block waits on an event the check
# sets; a short timeout_s only chooses the outcome. Nothing here measures time.


def _tool_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name.startswith("wasi-python-tool-")]


def _join_tool_threads() -> None:
    for t in _tool_threads():
        t.join(60)  # a fail-safe, not a timing: each check releases its tools first


@pytest.fixture
def release():
    """An event the check's blocking tools wait on, set at the end, and their threads joined, so
    no check leaves a tool thread for the next one to count."""
    event = threading.Event()
    yield event
    event.set()
    _join_tool_threads()


def _outcomes(done) -> list[tuple]:
    return [(o.op, o.tool, o.outcome) for o in done.tools.outcomes]


def test_a_guest_calls_a_tool(guest_workdir) -> None:
    """Criterion 4: `run(tools=…)`; the guest imports and calls two tools, one result fed to
    pandas; the record is in the result, on an exit and on a trap; none without tools=."""
    run = _runner()
    done = run(["-c", TOOL_PROGRAM], tools=_region_tools())
    assert (done.exit_code, done.stdout) == (0, b"EMEA 60 ['month', 'sales']\nb'\\x00cba'\n"), done
    assert _outcomes(done) == [
        ("list", None, "ok"),
        ("call", "lookup_region", "ok"),
        ("call", "reverse", "ok"),
    ]
    assert (done.tools.frames, done.tools.unlisted) == (3, 0)
    assert run(["-c", "pass"]).tools is None
    spin = "from host import tools\ntools.reverse(b'x')\nwhile True: pass\n"
    done = run(["-c", spin], tools=_region_tools(), fuel=10**9)
    assert (done.exit_code, done.trapped) == (None, "out of fuel"), done
    assert _outcomes(done) == [("list", None, "ok"), ("call", "reverse", "ok")]


HUGE_FRAMES = """
import _host, json
frame = bytes(256 * 2**20)
for _ in range(4):
    print(json.loads(_host.call(frame))["error"]["kind"])
"""


def test_a_huge_frame_is_answered_unread(guest_workdir, monkeypatch) -> None:
    """Criterion 5: under tools=, four frames of 256 MiB are each answered `too_large` from
    their length alone, and the run exits 0. The bytes the runner reads out of guest memory are
    counted: `run` must give the door the frame host's `admit`, so no read comes near a frame's
    size (the frame host's own admit on a raw path gives the same
    answers after copying each frame)."""
    import wasmtime

    run = _runner()
    reads: list[int] = []
    read = wasmtime.Memory.read

    def counted(self, store, start=None, stop=None):
        reads.append((stop or 0) - (start or 0))
        return read(self, store, start, stop)

    monkeypatch.setattr(wasmtime.Memory, "read", counted)
    done = run(["-c", HUGE_FRAMES], tools=_region_tools())
    assert (done.exit_code, done.stdout) == (0, b"too_large\n" * 4), done
    assert [(o.op, o.outcome, o.request_bytes) for o in done.tools.outcomes] == [
        (None, "too_large", 268_435_456)
    ] * 4
    assert max(reads, default=0) < 1 << 20, (len(reads), max(reads, default=0))


GATED = """
from host import tools
try:
    tools.count(n=3)
except PermissionError as e:
    print(type(e).__name__, e)
"""


def test_a_gate_refuses_before_the_tool_runs(guest_workdir) -> None:
    """Criterion 6: the gate refuses; the guest catches `PermissionError` with the gate's
    message, the tool never runs, and the record says `denied`."""
    from wasi_python.tools import ToolDenied, tool

    run = _runner()
    calls = []

    @tool
    def count(n: int) -> int:
        """Count."""
        calls.append(n)
        return n

    def gate(call):
        raise ToolDenied(f"{call.tool.name} is not allowed today")

    done = run(["-c", GATED], tools=[count], gate=gate)
    assert (done.exit_code, done.stdout) == (0, b"ToolDenied count is not allowed today\n"), done
    assert calls == []
    last = done.tools.outcomes[-1]
    assert (last.outcome, last.message) == ("denied", "count is not allowed today")


FAULTY = """
from host import tools
try:
    tools.open_db()
except Exception as e:
    print(type(e).__name__, e)
tools.open_db()
"""


def test_a_tool_fault_stays_on_the_host(guest_workdir) -> None:
    """Criterion 7: a tool raises KeyError naming a host path. The guest is told only that the
    tool failed; the path stays in the host's record."""
    from wasi_python.tools import tool

    run = _runner()
    secret = "/srv/private/customers-4417.db"

    @tool
    def open_db() -> int:
        """Open the database."""
        raise KeyError(secret)

    done = run(["-c", FAULTY], tools=[open_db])
    assert done.exit_code == 1, done
    assert done.stdout == b"ToolError open_db failed (internal error)\n", done
    assert secret.encode() not in done.stdout + done.stderr
    assert b"open_db failed (internal error)" in done.stderr
    assert all(o.fault.startswith("KeyError") for o in done.tools.outcomes[1:]), done.tools
    assert secret in done.tools.outcomes[-1].fault


BUDGET = """
from host import tools, ToolBudgetExceeded
seen = []
for i in range(6):
    try:
        seen.append(tools.reverse(b"ab"))
    except ToolBudgetExceeded:
        seen.append("budget")
print(seen)
"""


def test_the_tool_call_limit_holds(guest_workdir) -> None:
    """Criterion 8: `max_tool_calls=3` counts every frame, discovery included: of seven frames,
    three are answered and four refused; the guest runs on."""
    run = _runner()
    done = run(["-c", BUDGET], tools=_region_tools(), max_tool_calls=3)
    assert done.exit_code == 0, done
    assert done.stdout == b"[b'ba', b'ba', 'budget', 'budget', 'budget', 'budget']\n", done
    assert done.tools.frames == 7
    assert [o.outcome for o in done.tools.outcomes] == ["ok"] * 3 + ["budget_exceeded"] * 4


LATE = """
from host import tools
try:
    tools.a()
except TimeoutError as e:
    print(type(e).__name__, e)
print(tools.b())
"""


def test_a_tool_timeout_ends_the_call_not_the_run(guest_workdir, release) -> None:
    """Criterion 9: A times out and the guest runs on; B releases A and waits until A's late
    result has arrived, so it arrives while B's call is in flight; the guest gets B's answer."""
    from wasi_python.tools import tool

    run = _runner()

    @tool(timeout_s=0.05)
    def a() -> str:
        """Wait for the check."""
        release.wait()
        return "A's late result"

    @tool
    def b() -> str:
        """Release A, wait for its late result, then answer."""
        release.set()
        for t in _tool_threads():
            if t.name == "wasi-python-tool-a":
                t.join(60)
        return "B's answer"

    done = run(["-c", LATE], tools=[a, b])
    assert done.stdout == b"ToolTimeout a timed out after 0.05 s\nB's answer\n", done
    outcomes = done.tools.outcomes
    assert [(o.tool, o.outcome, o.abandoned) for o in outcomes[1:]] == [
        ("a", "timeout", True),
        ("b", "ok", False),
    ]


PAST_THE_DEADLINE = r"""
import threading
import wasi_python
from wasi_python import runner
from wasi_python._process import process
from wasi_python.tools import tool

release = threading.Event()


@tool
def block() -> int:
    "Wait for the check, which releases it only after run returns."
    # By count, never by time: the ticker's count, which the tool bound
    # reads, is set past any deadline. Not this call's stop_at: the call stack is per thread,
    # and a tool runs on its own.
    process().ticker_count = 2**62
    release.wait()
    return 1


done = wasi_python.run(["-c", "from host import tools\ntools.block()\n"], tools=[block],
                       deadline_s=60.0)
release.set()
last = done.tools.outcomes[-1]
print(last.tool, last.outcome, last.abandoned)
"""


def test_a_tool_blocking_past_the_deadline_is_answered() -> None:
    """Criterion 10: a tool with no timeout_s blocks past the run's deadline; the call is
    answered `timeout` two ticks before it, so `run` returns. Whether the guest then traps or
    exits is not asserted: it may finish within the last two ticks. The deadline is 60 s and is
    made overdue by count from inside the tool, so the guest's start-up speed decides nothing.
    In a child process, with a 120 s fail-safe."""
    assert _child(PAST_THE_DEADLINE) == ["block timeout True"]


SIX_CALLS = """
from host import tools
for i in range(6):
    try:
        tools.stall()
    except TimeoutError as e:
        print(e)
"""


def test_abandoned_tools_are_bounded_per_call(guest_workdir, release) -> None:
    """Criterion 11: four abandoned calls, then two answered at once without starting; the tool
    threads are counted in `runner.stats()` until they end."""
    from wasi_python import runner
    from wasi_python.tools import tool

    run = _runner()
    starts = []

    @tool(timeout_s=0.05)
    def stall() -> int:
        """Wait for the check."""
        starts.append(1)
        release.wait()
        return 1

    before = runner.stats()["tool_threads_running"]
    done = run(["-c", SIX_CALLS], tools=[stall])
    assert done.exit_code == 0, done
    lines = done.stdout.decode().splitlines()
    assert (
        lines
        == ["stall timed out after 0.05 s"] * 4
        + ["stall timed out: 4 earlier tool calls are still running"] * 2
    ), lines
    outcomes = done.tools.outcomes[1:]
    assert [(o.outcome, o.abandoned) for o in outcomes] == [("timeout", True)] * 4 + [
        ("timeout", False)
    ] * 2
    assert len(starts) == 4
    assert runner.stats()["tool_threads_running"] == before + 4
    release.set()
    _join_tool_threads()
    assert runner.stats()["tool_threads_running"] == before


STALL_FOUR = """
from host import tools
for i in range(4):
    try:
        tools.stall()
    except TimeoutError:
        pass
print("A done")
"""


def test_one_calls_stalled_tools_do_not_starve_another(guest_workdir, release) -> None:
    """Criterion 12: call A leaves four tool threads stalled; call B, on another thread, then
    gets its tool's answer. With a shared pool of four, B's tool would wait behind A's."""
    from wasi_python.tools import tool

    run = _runner()

    @tool(timeout_s=0.05)
    def stall() -> int:
        """Wait for the check."""
        release.wait()
        return 1

    @tool(timeout_s=5)
    def instant() -> str:
        """Answer at once."""
        return "now"

    results: dict[str, object] = {}

    def call(key, code, tools) -> None:
        results[key] = run(["-c", code], tools=tools)

    a = threading.Thread(target=call, args=("A", STALL_FOUR, [stall]))
    a.start()
    a.join()
    b = threading.Thread(
        target=call, args=("B", "from host import tools\nprint(tools.instant())", [instant])
    )
    b.start()
    b.join()
    assert results["A"].stdout == b"A done\n", results["A"]
    assert [o.abandoned for o in results["A"].tools.outcomes[1:]] == [True] * 4
    assert results["B"].stdout == b"now\n", results["B"]
    assert results["B"].tools.outcomes[-1].outcome == "ok"


TOOL_CANCEL = r"""
import sys, threading
import wasi_python
from wasi_python.tools import tool

started, cancel, release = threading.Event(), threading.Event(), threading.Event()


@tool
def block() -> int:
    "Wait for the check."
    started.set()
    release.wait()
    return 1


def check():
    started.wait()
    cancel.set()


code = "from host import tools\ntools.block()\nprint('after the tool')\n"
case = sys.argv[1]
if case == "cancel":
    threading.Thread(target=check, daemon=True).start()
    r = wasi_python.run(["-c", code], tools=[block], cancel=cancel, deadline_s=None, fuel=10**15)
    last = r.tools.outcomes[-1]
    print(r.trapped, r.exit_code, r.fuel_used, r.stdout, last.outcome, last.abandoned)
elif case == "ctrl-c":
    import signal

    signal.signal(signal.SIGINT, signal.default_int_handler)  # a parent may have ignored it
    starts = []

    @tool(name="block")
    def counted() -> int:
        "Wait for the check."
        starts.append(1)
        started.set()
        release.wait()
        return 1

    def interrupt():
        started.wait()
        signal.raise_signal(signal.SIGINT)  # os.kill on Windows would end the process

    threading.Thread(target=interrupt, daemon=True).start()
    try:
        r = wasi_python.run(["-c", code], tools=[counted], deadline_s=None)
        print("returned", r.trapped)
    except KeyboardInterrupt:
        print("KeyboardInterrupt", len(starts))
elif case == "async":
    import asyncio, concurrent.futures

    pool = concurrent.futures.ThreadPoolExecutor(1)  # a new call runs only if the worker is free

    async def main():
        call = wasi_python.run_async(
            ["-c", code], tools=[block], deadline_s=None, executor=pool
        )
        task = asyncio.create_task(call)
        await asyncio.to_thread(started.wait, 120)
        task.cancel()
        try:
            await task
            print("not cancelled")
        except asyncio.CancelledError:
            print("cancelled while the tool blocks", not release.is_set())
        print((await wasi_python.run_async(["-c", "print('next')"], executor=pool)).stdout)

    asyncio.run(main())
"""


def test_a_cancel_during_a_tool_call_is_named() -> None:
    """Criterion 13: `cancel` set while a tool blocks: the call is answered `cancelled` within a
    tick and the run is named "cancelled", with no exit code, no fuel count and nothing the
    guest would print after the call. In a child process, with a 120 s fail-safe. The answer
    comes inside CANCEL_TICKS, so this is not a check of the path a door call takes once
    it is overdue."""
    assert _child(TOOL_CANCEL, "cancel") == ["cancelled None None b'' cancelled True"]


def test_ctrl_c_during_a_tool_call() -> None:
    """Criterion 14: Ctrl-C on the main thread while a tool blocks: `run` raises
    KeyboardInterrupt, the tool started once, and the child exits though its tool still
    blocks (its thread is a daemon)."""
    assert _child(TOOL_CANCEL, "ctrl-c") == ["KeyboardInterrupt 1"]


def test_cancelling_an_async_call_during_a_tool_call() -> None:
    """Criterion 15: the task awaiting `run_async` is cancelled while its tool blocks; it raises
    `CancelledError` with the tool still blocked, and the one worker is free for the next
    call."""
    assert _child(TOOL_CANCEL, "async") == [
        "cancelled while the tool blocks True",
        "b'next\\n'",
    ]


def test_tools_run_off_the_guests_thread(guest_workdir) -> None:
    """Criterion 16: a tool runs on its own thread, in a copy of the caller's context."""
    import contextvars

    from wasi_python.tools import tool

    run = _runner()
    request = contextvars.ContextVar("request")
    seen = []

    @tool
    def where() -> str:
        """Say what it sees."""
        seen.append(threading.get_ident())
        return request.get("no context")

    def call():
        request.set("from the caller")
        return run(["-c", "from host import tools\nprint(tools.where())"], tools=[where])

    done = contextvars.copy_context().run(call)
    assert done.stdout == b"from the caller\n", done
    assert seen and seen[0] != threading.get_ident()


TWO_CALLS = "from host import tools\nprint(tools.nap(1), tools.nap(2))\n"


def test_fuel_is_exact_across_tool_calls(guest, guest_workdir) -> None:
    """Criterion 17: fuel counts only the guest's instructions. One program, two tool calls,
    run twice with its tools sleeping different amounts: the same fuel.

    The equality is read through the judge's driver, whose clock and entropy are fixed, with the
    frame host and bound `run(tools=…)` builds as its host. Through `run` the guest reads the
    real clock and real entropy, which move even `-c pass` by about 150,000 (the cache
    check above says the same), so there it is checked only that a run with
    tool calls still reports its fuel."""
    import time

    from harness.calls import checked_call
    from wasi_python import _call
    from wasi_python.tools import tool

    pause = {"s": 0.0}

    @tool
    def nap(n: int) -> int:
        """Sleep a little: a perturbation, not a measurement."""
        time.sleep(pause["s"])
        return n

    used = []
    for pause["s"] in (0.05, 0.0):
        checked = checked_call(tools=(nap,), tool_calls=1000)
        host = _call._tool_host(checked, None, None, None, None)
        r = guest("snapshot", ["-c", TWO_CALLS], host=host)
        assert (r.exit_code, r.stdout) == (0, b"1 2\n"), r.describe()
        assert [o.outcome for o in host.record.outcomes] == ["ok"] * 3
        used.append(r.fuel)
    assert used[0] == used[1], used
    done = _runner()(["-c", TWO_CALLS], tools=[nap], fuel=10**12)
    assert (done.exit_code, done.stdout) == (0, b"1 2\n"), done
    assert isinstance(done.fuel_used, int) and done.fuel_used > 0, done


def test_no_tools_no_protocol(guest_workdir) -> None:
    """Criterion 18: without tools=, `from host import tools` raises ImportError with the tool
    protocol's message; the raw door is unchanged (every host= check above)."""
    run = _runner()
    done = run(["-c", "from host import tools"])
    assert done.exit_code == 1, done
    assert b"ImportError: this run has no tools: the embedder passed none" in done.stderr, done


LISTS_FIRST = r"""
import _host, json
frame = json.dumps({"v": 1, "id": 1, "op": "list"}).encode()
for _ in range(1000):
    _host.call(frame)
from host import tools
for i in range(4):
    try:
        tools.stall()
    except TimeoutError:
        pass
print("done")
"""


def test_abandoned_calls_are_counted_past_the_listed_outcomes(guest_workdir, release) -> None:
    """With no frame limit, a guest spends the record's 1,000 listed
    outcomes on `list` frames, then abandons four tool calls. The record's `abandoned` still
    counts them, though none is listed."""
    from wasi_python.tools import tool

    run = _runner()

    @tool(timeout_s=0.05)
    def stall() -> int:
        """Wait for the check."""
        release.wait()
        return 1

    done = run(["-c", LISTS_FIRST], tools=[stall], max_tool_calls=None)
    assert (done.exit_code, done.stdout) == (0, b"done\n"), done
    record = done.tools
    assert (record.frames, len(record.outcomes), record.unlisted) == (1005, 1000, 5)
    assert sum(o.abandoned for o in record.outcomes) == 0
    assert record.abandoned == 4


# A keyword bound with functools.partial is
# fixed, neither shown to the guest nor set by it; a call that ended while its gate still
# decided never runs its tool. A gate that must block waits on an event the check sets.

SECRET = "sk-live-SECRET"

PARTIAL_PROBE = r"""
import _host, inspect, json
from host import tools
print(inspect.signature(tools.my_orders))
print(sorted(tools.my_orders.descriptor["inputSchema"]["properties"]))
print(tools.my_orders())
try:
    tools.my_orders(user_id=7)
except TypeError as e:
    print(type(e).__name__)
for args in ({"user_id": 7}, {"api_key": "mine"}):
    frame = {"v": 1, "id": 1, "op": "call", "tool": "my_orders", "args": args}
    answer = json.loads(_host.call(json.dumps(frame).encode()))
    print(answer["ok"], answer["error"]["kind"], answer["error"]["message"])
"""


def _orders_log() -> tuple[list, object]:
    calls: list = []

    def orders(user_id: int, api_key: str) -> list[str]:
        """This user's orders."""
        calls.append((user_id, api_key))
        return [f"orders of user {user_id}"]

    return calls, orders


def test_a_partials_bound_keywords_are_fixed(guest_workdir) -> None:
    """`tool(partial(orders,
    user_id=42, api_key=…))`. The guest's descriptor, signature and stubs name neither keyword
    and hold no bound value; the guest's own call with `user_id=7` is refused before a frame;
    forged frames naming either keyword are answered `invalid_arguments`, as an unknown argument
    is; the tool runs once, as bound."""
    import functools

    from wasi_python.tools import stubs, tool

    run = _runner()
    calls, orders = _orders_log()
    mine = tool(functools.partial(orders, user_id=42, api_key=SECRET), name="my_orders")
    assert mine.input_schema["properties"] == {}, mine.input_schema
    assert SECRET not in json.dumps(mine.descriptor())
    assert SECRET not in stubs([mine]) and "user_id" not in stubs([mine])
    done = run(["-c", PARTIAL_PROBE], tools=[mine])
    assert done.exit_code == 0, done
    assert done.stdout.decode().splitlines() == [
        "() -> list[str]",
        "[]",
        "['orders of user 42']",
        "ToolArgumentError",
        "False invalid_arguments my_orders: the arguments: unknown argument 'user_id'",
        "False invalid_arguments my_orders: the arguments: unknown argument 'api_key'",
    ], done
    assert SECRET.encode() not in done.stdout + done.stderr
    assert calls == [(42, SECRET)]
    assert [o.outcome for o in done.tools.outcomes] == ["ok", "ok"] + ["invalid_arguments"] * 2


def test_bound_keywords_are_fixed_however_the_partial_is_reached() -> None:
    """The same holds where `inspect.signature` finds a partial through
    another object (nested partials, a `__wrapped__` chain, a bound `partialmethod`); a given
    `input_schema` that names a bound keyword is refused; under an open schema a frame naming
    one is answered `invalid_arguments` and the tool does not run; an unbound `partialmethod`
    is refused; a plain function's and a bound method's own defaults are still published."""
    import functools

    from wasi_python._tool_host import _ToolHost
    from wasi_python.tools import tool

    calls, orders = _orders_log()

    def wrapper(**kw):
        return inner(**kw)

    inner = functools.partial(orders, user_id=42, api_key=SECRET)
    functools.update_wrapper(wrapper, inner)
    wrapper.__annotations__ = dict(orders.__annotations__)

    class Shop:
        def orders(self, user_id: int, api_key: str, limit: int = 10) -> list[str]:
            """This user's orders."""
            calls.append((user_id, api_key, limit))
            return []

        mine = functools.partialmethod(orders, api_key=SECRET)

    nested = functools.partial(functools.partial(orders, user_id=42), api_key=SECRET)
    method_left = {"user_id": {"type": "integer"}, "limit": {"type": "integer", "default": 10}}
    for fn, left in [(nested, {}), (wrapper, {}), (Shop().mine, method_left)]:
        made = tool(fn, name="mine")
        assert made.input_schema["properties"] == left, (fn, made.input_schema)
        assert SECRET not in json.dumps(made.descriptor())

    bound = functools.partial(orders, api_key=SECRET)
    given = {"type": "object", "properties": {"user_id": {"type": "integer"}, "api_key": {}}}
    with pytest.raises(ValueError, match="api_key"):
        tool(bound, name="mine", input_schema=given)
    with pytest.raises(TypeError, match="partialmethod"):
        tool(Shop.mine, name="mine")

    calls.clear()
    open_schema = tool(bound, name="mine", input_schema={"type": "object"}, validates_input=True)
    host = _ToolHost([open_schema])
    args = {"user_id": 7, "api_key": "x"}
    frame = {"v": 1, "id": 1, "op": "call", "tool": "mine", "args": args}
    answer = json.loads(host(json.dumps(frame).encode()))
    assert (answer["ok"], answer["error"]["kind"]) == (False, "invalid_arguments"), answer
    assert calls == []

    def plain(user_id: int, limit: int = 10) -> list[str]:
        return []

    assert tool(plain).input_schema["properties"]["limit"] == {"type": "integer", "default": 10}


CLASS_SHAPES = [
    "a partialmethod __init__",
    "a partial __init__",
    "a staticmethod over a partial as __new__",
    "an inherited partialmethod __init__",
    "a functools.wraps __init__ over a partial",
    "a partial over the class",
]


def _class_tool(shape: str, made: list) -> object:
    """A class tool that binds `role="viewer"` on its construction path in one of the shapes,
    its constructor noting the role it ran with. The instance is a dict, so it crosses as
    JSON."""
    import functools
    import typing

    def init(self, q: str, role: str = "user") -> None:
        made.append((q, role))
        dict.__init__(self, q=q, role=role)

    def new(cls, q: str, role: str = "user") -> dict:
        made.append((q, role))
        return {"q": q, "role": role}

    class ByPartialmethod(dict):
        __init__ = functools.partialmethod(init, role="viewer")

    class ByPartial(dict):
        __init__ = functools.partial(init, role="viewer")

    class ByNew:
        __new__ = staticmethod(functools.partial(new, role="viewer"))

    class Inherited(ByPartialmethod):
        pass

    bound_init = functools.partial(init, role="viewer")

    class ByWraps(dict):
        @functools.wraps(bound_init)
        def __init__(self, *args, **kwargs):
            bound_init(self, *args, **kwargs)

    class Meta(type):
        def __call__(cls, *args, **kwargs):
            return super().__call__(*args, **kwargs)

    class ByMetaclass(dict, metaclass=Meta):
        __init__ = functools.partialmethod(init, role="viewer")

    item = typing.TypeVar("item")

    class Generic(dict, typing.Generic[item]):
        __init__ = functools.partialmethod(init, role="viewer")

    return {
        "a partialmethod __init__": ByPartialmethod,
        "a partial __init__": ByPartial,
        "a staticmethod over a partial as __new__": ByNew,
        "an inherited partialmethod __init__": Inherited,
        "a functools.wraps __init__ over a partial": ByWraps,
        "a partial over the class": functools.partial(ByPartialmethod),
        "a delegating metaclass": ByMetaclass,
        "a typing.Generic class's alias": Generic[int],
        "a builtin generic alias": ByPartialmethod[int],
        "an Annotated alias": typing.Annotated[ByPartialmethod, "x"],
        "a partial over a generic alias": functools.partial(Generic[int]),
    }[shape]


def _construction_keyword_is_fixed(shape: str) -> None:
    """A given schema naming the bound keyword is refused at `tool()`; under an open schema a
    frame naming it is answered `invalid_arguments` with neither the gate nor the constructor
    called, and a frame without it reaches the gate with no bound keyword and the constructor
    with the bound value."""
    from wasi_python._tool_host import _ToolHost
    from wasi_python.tools import tool

    made: list = []
    gated: list = []
    cls = _class_tool(shape, made)
    naming = {
        "type": "object",
        "properties": {"q": {"type": "string"}, "role": {"type": "string"}},
        "required": ["q"],
    }
    with pytest.raises(ValueError, match="'role', which the partial binds"):
        tool(cls, name="account", input_schema=naming)

    made_tool = tool(cls, name="account", input_schema={"type": "object"})
    host = _ToolHost([made_tool], gate=lambda call: gated.append(dict(call.arguments)))

    def call(args: dict) -> dict:
        frame = {"v": 1, "id": 1, "op": "call", "tool": "account", "args": args}
        return json.loads(host(json.dumps(frame).encode()))

    answer = call({"q": "x", "role": "admin"})
    assert (answer["ok"], answer["error"]["kind"]) == (False, "invalid_arguments"), answer
    assert "unknown argument 'role'" in answer["error"]["message"], answer
    assert (gated, made) == ([], []), (gated, made)
    answer = call({"q": "x"})
    assert answer["ok"], answer
    assert (gated, made) == ([{"q": "x"}], [("x", "viewer")]), (gated, made)


@pytest.mark.parametrize("shape", CLASS_SHAPES)
def test_a_class_tools_construction_keywords_are_fixed(shape) -> None:
    """A class registered as a tool whose `__init__` or `__new__` binds a keyword with a
    `functools.partial` or `partialmethod`, however the binding is reached (inherited, behind a
    `functools.wraps` wrapper, through a partial over the class), has that keyword fixed as a
    function's is."""
    _construction_keyword_is_fixed(shape)


ALIAS_SHAPES = [
    "a typing.Generic class's alias",
    "a builtin generic alias",
    "an Annotated alias",
    "a partial over a generic alias",
]


@pytest.mark.parametrize("shape", ALIAS_SHAPES)
def test_a_generic_alias_of_a_class_tool_has_its_keywords_fixed(shape) -> None:
    """A generic alias of a class (`Box[int]`, `typing.Annotated[Box, ...]`) is not itself a
    class, but calling it constructs its origin class with the guest's keywords, so a keyword
    bound on that class's construction path is fixed through the alias too."""
    _construction_keyword_is_fixed(shape)


def test_a_delegating_metaclass_does_not_hide_the_constructor() -> None:
    """A Python metaclass whose `__call__` delegates to `type.__call__` still runs the class's
    `__init__` with the guest's keywords, so a keyword a `partialmethod` binds there is fixed
    whatever the metaclass."""
    _construction_keyword_is_fixed("a delegating metaclass")


def test_a_class_tools_published_schema_is_the_one_given() -> None:
    """A class tool's published input schema is the schema given, which leaves the fixed
    keyword out; a class tool with no schema given is still refused for lack of hints."""
    from wasi_python.tools import tool

    given = {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}
    made = tool(_class_tool("a partialmethod __init__", []), name="account", input_schema=given)
    assert made.input_schema == given, made.input_schema
    assert "role" not in json.dumps(made.descriptor())
    with pytest.raises(TypeError, match="type hint"):
        tool(_class_tool("a partialmethod __init__", []), name="account")


def _search_log() -> tuple[list, object]:
    import functools

    calls: list = []

    def search(q: str = "", filter: dict | None = None, user_id: int = 0) -> list[str]:
        calls.append((q, filter, user_id))
        return []

    return calls, functools.partial(search, user_id=42)


_USER_ID = {"type": "object", "properties": {"user_id": {"type": "integer"}}}
_Q = {"type": "object", "properties": {"q": {"type": "string"}}}
TOP_LEVEL_NAMINGS = {
    "a root anyOf branch": {"type": "object", "anyOf": [_USER_ID, _Q]},
    "a root oneOf branch": {"type": "object", "oneOf": [_Q, _USER_ID]},
    "a $defs target a root anyOf branch points to": {
        "type": "object",
        "anyOf": [_Q, {"$ref": "#/$defs/User"}],
        "$defs": {"User": _USER_ID},
    },
}


@pytest.mark.parametrize("where", sorted(TOP_LEVEL_NAMINGS))
def test_a_bound_keyword_named_in_a_root_branch_is_refused(where) -> None:
    """A given schema that names a bound keyword among the names a frame could send at the
    arguments' top level, in a root `anyOf` or `oneOf` branch or a `$defs` target such a branch
    points to, is refused at `tool()`, as one naming it in `properties` is."""
    from wasi_python.tools import tool

    _, bound = _search_log()
    with pytest.raises(ValueError, match="which the partial binds"):
        tool(bound, name="search", input_schema=TOP_LEVEL_NAMINGS[where])


NESTED_NAMINGS = {
    "inline": {
        "type": "object",
        "properties": {"filter": _USER_ID},
    },
    "through $defs": {
        "type": "object",
        "properties": {"filter": {"$ref": "#/$defs/Filter"}},
        "$defs": {"Filter": _USER_ID},
    },
}


@pytest.mark.parametrize("where", sorted(NESTED_NAMINGS))
def test_a_nested_property_named_like_a_bound_keyword_is_accepted(where) -> None:
    """A key of the bound keyword's name inside a property's own object belongs to that object,
    not to the arguments: the schema is accepted, and a frame setting it there is answered `ok`
    with the bound value intact."""
    from wasi_python._tool_host import _ToolHost
    from wasi_python.tools import tool

    calls, bound = _search_log()
    host = _ToolHost([tool(bound, name="search", input_schema=NESTED_NAMINGS[where])])
    args = {"filter": {"user_id": 7}}
    frame = {"v": 1, "id": 1, "op": "call", "tool": "search", "args": args}
    answer = json.loads(host(json.dumps(frame).encode()))
    assert answer["ok"], answer
    assert calls == [("", {"user_id": 7}, 42)], calls


LATE_GATE = """
from host import tools
try:
    tools.transfer(amount=5)
except Exception as e:
    print(type(e).__name__)
print("after the call")
"""


@pytest.mark.parametrize("end", ["timeout", "cancel"])
def test_a_gate_that_allows_late_runs_no_tool(guest_workdir, release, end) -> None:
    """The gate is still deciding when the
    call is answered `timeout` (the tool's `timeout_s`) or `cancelled` (the run's `cancel`, set
    once the gate is entered). `run` returns; the gate then allows; the tool never runs. The
    gate ran once, and the tool thread ends."""
    from wasi_python.tools import tool

    run = _runner()
    ran: list = []
    gated: list = []
    entered = threading.Event()

    @tool(timeout_s=0.05 if end == "timeout" else None)
    def transfer(amount: int) -> str:
        """Move money."""
        ran.append(amount)
        return "sent"

    def gate(call):
        gated.append(call.seq)
        entered.set()
        release.wait()
        return True

    cancel = threading.Event()
    if end == "cancel":
        threading.Thread(target=lambda: entered.wait(60) and cancel.set(), daemon=True).start()
    done = run(["-c", LATE_GATE], tools=[transfer], gate=gate, cancel=cancel, deadline_s=None)
    last = done.tools.outcomes[-1]
    if end == "timeout":
        assert (done.exit_code, done.stdout) == (0, b"ToolTimeout\nafter the call\n"), done
        assert (last.outcome, last.abandoned) == ("timeout", True)
    else:
        assert (done.trapped, done.stdout) == ("cancelled", b""), done
        assert (last.outcome, last.abandoned) == ("cancelled", True)
    release.set()
    _join_tool_threads()
    assert (gated, ran, _tool_threads()) == ([2], [], [])


# Writable mounts: a provider's write half, served at open, at close, at fsync and at
# every ending. The guest asks the door for the provider's counts between its steps, so each
# step's calls are counted exactly; the provider's own log holds every write-half call whole.

WRITES = r"""
import _host, json, os

def calls():
    return json.loads(_host.call(b"calls"))

def step(name, fn):
    before = calls()
    value = fn()
    after = calls()
    moved = {k: after[k] - before[k] for k in after if after[k] != before[k]}
    print(json.dumps([name, value, moved]))

def w():
    f = open("/work/a.txt", "w")
    f.write("new")
    f.close()

held = {}

def x_open():
    held["x"] = open("/work/n.txt", "x")

def append():
    with open("/work/b.txt", "a") as f:
        f.write("more")

def read_plus():
    with open("/work/b.txt", "r+") as f:
        return f.read()

def fsynced():
    f = open("/work/s.txt", "w")
    f.write("s")
    f.flush()
    os.fsync(f.fileno())
    f.close()

def pandas_round_trip():
    import pandas as pd
    pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_csv("/work/p.csv", index=False)
    return pd.read_csv("/work/p.csv").to_dict("list")

step("w, a write and a close", w)
step("w then close", lambda: open("/work/c.txt", "w").close())
step("x", x_open)
step("exists while open", lambda: os.path.exists("/work/n.txt"))
step("close the x", lambda: held.pop("x").close())
step("a on an existing file", append)
step("r+ with no write", read_plus)
step("a write, an fsync and a close", fsynced)
step("mkdir", lambda: os.mkdir("/work/m"))
step("remove", lambda: os.remove("/work/c.txt"))
step("rmdir", lambda: os.rmdir("/work/m"))
step("rename", lambda: os.rename("/work/b.txt", "/work/b2.txt"))
step("pandas", pandas_round_trip)
"""
NONE_WRITTEN = {"write": 0, "mkdir": 0, "remove": 0, "rmdir": 0, "rename": 0}


@BINARY
def test_a_writable_mount_serves_writes(guest_workdir, which) -> None:
    """`"w"`, a write and a close make two `write`s (`b""` at open, the
    bytes at close); `open(p, "w").close()` one; `"x"` one `stat` and one `write(b"")`, and the
    file exists while it is open; `"a"` one `read` and one `write` of the old bytes then the new;
    `"r+"` with no write one `read`; a write, an `fsync` and a close one content `write`;
    `mkdir`, `remove`, `rmdir` and `rename` one call each; pandas round-trips a CSV; the record's
    counts are the provider's own, all eight, and nothing is refused."""
    from harness.files import MemoryProvider
    from wasi_python import Mount

    run = _runner()
    provider = MemoryProvider()
    done = run(
        ["-c", WRITES],
        mounts=[Mount(provider, "/work", writable=True)],
        host=_mount_host(provider),
        snapshot=which == "snapshot",
    )
    assert (done.exit_code, done.trapped, done.stderr) == (0, None, b""), done
    steps = [json.loads(line) for line in done.stdout.decode().splitlines()]
    pandas_calls = steps[-1][2]
    assert steps[:-1] == [
        ["w, a write and a close", None, {"write": 2}],
        ["w then close", None, {"write": 1}],
        ["x", None, {"stat": 1, "write": 1}],
        ["exists while open", True, {"stat": 1}],
        ["close the x", None, {}],
        ["a on an existing file", None, {"read": 1, "write": 1}],
        ["r+ with no write", "b\nmore", {"read": 1}],
        ["a write, an fsync and a close", None, {"write": 2}],
        ["mkdir", None, {"mkdir": 1}],
        ["remove", None, {"remove": 1}],
        ["rmdir", None, {"rmdir": 1}],
        ["rename", None, {"rename": 1}],
    ], done.stdout
    assert steps[-1][:2] == ["pandas", {"a": [1, 2], "b": ["x", "y"]}], steps[-1]
    assert pandas_calls.get("write") == 2, pandas_calls  # b"" at open, the CSV at close
    assert [e for e in provider.log if e[1] != "/p.csv"] == [
        ("write", "/a.txt", b""),
        ("write", "/a.txt", b"new"),
        ("write", "/c.txt", b""),
        ("write", "/n.txt", b""),
        ("write", "/b.txt", b"b\nmore"),
        ("write", "/s.txt", b""),
        ("write", "/s.txt", b"s"),
        ("mkdir", "/m"),
        ("remove", "/c.txt"),
        ("rmdir", "/m"),
        ("rename", "/b.txt", "/b2.txt"),
    ]
    assert provider.tree["/b2.txt"] == b"b\nmore" and "/b.txt" not in provider.tree
    assert provider.tree["/p.csv"] == b"a,b\n1,x\n2,y\n"
    assert dict(done.files.calls) == provider.calls and len(provider.calls) == 8
    assert (done.files.refused, done.files.refused_total) == ((), 0)


REFUSALS = r"""
import json, os
out = {}

def attempt(name, fn):
    try:
        fn()
        out[name] = "ok"
    except OSError as e:
        out[name] = e.errno

def denied():
    with open("/work/denied.txt", "w") as f:
        f.write("x")

attempt("close", denied)
held = open("/work/sync.txt", "w")
held.write("y")
held.flush()
attempt("fsync", lambda: os.fsync(held.fileno()))
attempt("close after the fsync", held.close)
attempt("create", lambda: open("/work/create.txt", "w"))
attempt("a refused stat at a writing open", lambda: open("/work/stat.txt", "x"))
attempt("mkdir", lambda: os.mkdir("/work/nomk"))
attempt("rename", lambda: os.rename("/work/a.txt", "/work/norename"))
print(json.dumps(out))
"""


@BINARY
def test_refused_writes_are_recorded_on_exit_0(which) -> None:
    """A provider that refuses a content `write` with EACCES: the
    guest's `with` block raises PermissionError at its close, the guest exits 0, and the record
    names the refusal (`at == "close"`); a refused fsync is recorded at "sync" and again at the
    close; a refused create fails the open and is recorded at "open"; a refused `stat` at a
    writing open records nothing; a refused `mkdir` and `rename` are recorded at "call".
    `refused_total` counts each."""
    from harness.files import MemoryProvider
    from wasi_python import Errno, Mount, RefusedWrite

    run = _runner()
    provider = MemoryProvider()

    def content_refused(path, data):
        return Errno.EACCES if data else None

    provider.answers.update(
        {
            ("write", "/denied.txt"): content_refused,
            ("write", "/sync.txt"): content_refused,
            ("write", "/create.txt"): Errno.EACCES,
            ("stat", "/stat.txt"): Errno.EACCES,
            ("mkdir", "/nomk"): Errno.EACCES,
            ("rename", "/a.txt"): Errno.EACCES,
        }
    )
    done = run(
        ["-c", REFUSALS],
        mounts=[Mount(provider, "/work", writable=True)],
        snapshot=which == "snapshot",
    )
    assert (done.exit_code, done.trapped, done.stderr) == (0, None, b""), done
    assert json.loads(done.stdout) == {
        "close": 2,
        "fsync": 2,
        "close after the fsync": 2,
        "create": 2,
        "a refused stat at a writing open": 2,
        "mkdir": 2,
        "rename": 2,
    }
    a = Errno.EACCES
    assert done.files.refused == (
        RefusedWrite("/work", "write", ("/denied.txt",), a, "close", "refused"),
        RefusedWrite("/work", "write", ("/sync.txt",), a, "sync", "refused"),
        RefusedWrite("/work", "write", ("/sync.txt",), a, "close", "refused"),
        RefusedWrite("/work", "write", ("/create.txt",), a, "open", "refused"),
        RefusedWrite("/work", "mkdir", ("/nomk",), a, "call", "refused"),
        RefusedWrite("/work", "rename", ("/a.txt", "/norename"), a, "call", "refused"),
    ), done.files.refused
    assert done.files.refused_total == len(done.files.refused)
    assert done.files.faults == ()


FOLLOW = r"""
import _host, json, os, tempfile
out = {}

def mark(name):
    _host.call(b"mark:" + name.encode())

def calls():
    return sum(json.loads(_host.call(b"calls")).values())

mark("temporary")
with tempfile.TemporaryFile(dir="/tmp") as f:
    f.write(b"hello")
    f.seek(0)
    out["temporary"] = f.read().decode()
mark("named")
with tempfile.NamedTemporaryFile("wb", dir="/tmp", delete=False) as f:
    out["named"] = f.name
    f.write(b"x")
    f.flush()
    os.replace(f.name, "/tmp/final.bin")
mark("renamed while open")
f = open("/tmp/old.txt", "w")
os.rename("/tmp/old.txt", "/tmp/new.txt")
f.write("moved")
f.close()
mark("replaced while open")
f = open("/tmp/held.txt", "w")
open("/tmp/other.txt", "w").close()
os.rename("/tmp/other.txt", "/tmp/held.txt")
f.write("lost")
f.close()
mark("a folder renamed while open")
os.mkdir("/tmp/dir1")
with open("/tmp/dir1/x.txt", "w") as f:
    f.write("x")
fd = os.open("/tmp/dir1", os.O_RDONLY | os.O_DIRECTORY)
os.rename("/tmp/dir1", "/tmp/dir2")
relative = os.open("x.txt", os.O_RDONLY, dir_fd=fd)
out["a relative open after the rename"] = os.read(relative, 5).decode()
mark("a folder removed while open")
os.mkdir("/tmp/gone")
g = os.open("/tmp/gone", os.O_RDONLY | os.O_DIRECTORY)
os.rmdir("/tmp/gone")
os.mkdir("/tmp/gone")
with open("/tmp/gone/y", "w"):
    pass
before = calls()
for name, fn in [
    ("a relative open", lambda: os.open("y", os.O_RDONLY, dir_fd=g)),
    ("a relative stat", lambda: os.stat("y", dir_fd=g)),
]:
    try:
        fn()
        out[name] = "found"
    except OSError as e:
        out[name] = e.errno
out["provider calls through the removed folder"] = calls() - before
print(json.dumps(out))
"""


@BINARY
def test_open_files_follow_the_guests_renames_and_removals(which) -> None:
    """Guards the create at open, unlinking and the unlinked-folder rule: in a writable mount
    at /tmp, `TemporaryFile` writes, reads back and closes with one
    `write(b"")` at open, one `remove` and no other write, leaving nothing; `NamedTemporaryFile`
    with `os.replace` inside its `with` lands the bytes at the final name only; a file renamed
    while open is written back to its new name only; a file replaced while open is never written
    back; a folder renamed while open resolves later relative opens under its new name; a folder
    removed and made again answers a relative open and stat through the old descriptor ENOENT,
    with no provider call (the re-list is the unit check's)."""
    from harness.files import MemoryProvider
    from wasi_python import Mount

    run = _runner()
    provider = MemoryProvider({})

    def host(frame: bytes) -> bytes:
        if frame.startswith(b"mark:"):
            provider.log.append(("mark", frame[5:].decode()))
            return b""
        return json.dumps(provider.calls).encode()

    done = run(
        ["-c", FOLLOW],
        mounts=[Mount(provider, "/tmp", writable=True)],
        host=host,
        snapshot=which == "snapshot",
    )
    assert (done.exit_code, done.trapped, done.stderr) == (0, None, b""), done
    out = json.loads(done.stdout)
    named = out.pop("named")[len("/tmp") :]
    assert out == {
        "temporary": "hello",
        "a relative open after the rename": "x",
        "a relative open": 44,
        "a relative stat": 44,
        "provider calls through the removed folder": 0,
    }, out
    parts: dict[str, list] = {}
    for entry in provider.log:
        if entry[0] == "mark":
            parts[entry[1]] = []
        else:
            list(parts.values())[-1].append(entry)
    temporary = parts["temporary"]
    assert [e[0] for e in temporary] == ["write", "remove"], temporary
    name = temporary[0][1]
    assert temporary == [("write", name, b""), ("remove", name)]
    assert parts["named"] == [
        ("write", named, b""),
        ("rename", named, "/final.bin"),
        ("write", "/final.bin", b"x"),
    ], parts["named"]
    assert parts["renamed while open"] == [
        ("write", "/old.txt", b""),
        ("rename", "/old.txt", "/new.txt"),
        ("write", "/new.txt", b"moved"),
    ]
    assert parts["replaced while open"] == [
        ("write", "/held.txt", b""),
        ("write", "/other.txt", b""),
        ("rename", "/other.txt", "/held.txt"),
    ]
    tree = provider.tree
    assert (tree["/final.bin"], tree["/new.txt"], tree["/held.txt"]) == (b"x", b"moved", b"")
    assert {name, named, "/old.txt", "/other.txt", "/dir1"}.isdisjoint(tree), sorted(tree)
    assert tree["/dir2/x.txt"] == b"x" and tree["/gone"] is None


ENDING = r"""
import _host, os, sys
ending = sys.argv[1]
fd = os.open("/work/f.txt", os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
os.write(fd, b"data")  # never closed: no Python object closes it at the end
if ending == "os._exit":
    os._exit(3)
elif ending == "an uncaught exception":
    raise ValueError("uncaught")
elif ending == "out of fuel":
    while True:
        pass
elif ending in ("deadline", "cancel"):
    _host.call(ending.encode())
    while True:
        pass
elif ending == "out of file calls":
    while True:
        os.stat("/work/f.txt")
"""
ENDINGS = {  # each ending's (exit_code, trapped, a fuel count or not)
    "exit 0": (0, None, True),
    "os._exit": (3, None, True),
    "an uncaught exception": (1, None, True),
    "out of fuel": (None, "out of fuel", True),
    "deadline": (None, "deadline", False),
    "cancel": (None, "cancelled", False),
}


@BINARY
def test_writes_land_at_every_ending(guest_workdir, which) -> None:
    """A file written with `os.write` and never closed is written back
    once, by the ending's walk, whatever ends the guest: an exit 0, `os._exit(3)`, an uncaught
    exception, its fuel cap, its deadline, a cancel. Each ends as the same guest does with a
    writable grant, and an exit's `fuel_used` is still counted. At the file-call limit no
    content write is made, and the record names the file once, at "exit", for the limit. The
    deadline is reached by the ticker's count (the door moves the call's deadline to now)."""
    from harness.files import MemoryProvider
    from wasi_python import Errno, Grant, Mount, RefusedWrite, _home
    from wasi_python._process import process

    run = _runner()
    cap = 400_000_000  # past start-up on both binaries

    def host(event: threading.Event):
        def answer(frame: bytes) -> bytes:
            if frame == b"deadline":
                _home._stack()[-1].stop_at = process().ticker_count
            else:
                event.set()
            return b""

        return answer

    for ending, (code, trapped, counted) in ENDINGS.items():
        ends = []
        for side in ("grant", "mount"):
            event = threading.Event()
            provider = MemoryProvider({})
            folder = Path(tempfile.mkdtemp(prefix="ending-", dir=guest_workdir))
            places = (
                {"mounts": [Mount(provider, "/work", writable=True)]}
                if side == "mount"
                else {"grants": [Grant(folder, "/work", writable=True)]}
            )
            done = run(
                ["-c", ENDING, ending],
                host=host(event),
                cancel=event,
                deadline_s=600,
                fuel=cap if ending == "out of fuel" else 10**12,
                snapshot=which == "snapshot",
                **places,
            )
            ends.append((done.exit_code, done.trapped, done.fuel_used is not None))
            if side == "mount":
                assert provider.log == [("write", "/f.txt", b""), ("write", "/f.txt", b"data")]
                assert (done.files.refused, done.files.refused_total) == ((), 0), ending
                if ending == "out of fuel":
                    assert done.fuel_used == cap
            else:
                assert (folder / "f.txt").read_bytes() == b"data", ending
        assert ends == [(code, trapped, counted)] * 2, (ending, ends)
    provider = MemoryProvider({})
    done = run(
        ["-c", ENDING, "out of file calls"],
        mounts=[Mount(provider, "/work", writable=True)],
        max_file_calls=5,
        snapshot=which == "snapshot",
    )
    assert (done.exit_code, done.trapped, done.fuel_used) == (None, "out of file calls", None)
    assert provider.writes() == [b""] and provider.total() == 5
    assert done.files.refused == (
        RefusedWrite("/work", "write", ("/f.txt",), Errno.EIO, "exit", "limit"),
    )
    assert done.files.refused_total == 1


THREE_DIRTY = r"""
import os
fds = [os.open(f"/work/{n}.txt", os.O_WRONLY | os.O_CREAT | os.O_TRUNC) for n in (1, 2, 3)]
for fd in fds:
    os.write(fd, b"bytes of %d" % fd)
print(all(fd >= 2**30 for fd in fds) and fds == sorted(fds))
"""


def test_a_failed_write_back_at_the_ending_is_recorded() -> None:
    """Three dirty files at the ending; the provider refuses the first
    (EIO), raises ValueError for the second and takes the third: run raises nothing; the record
    holds the first ("refused") and the second ("fault", EIO, at "exit") and names the fault;
    the third is written; the walk made exactly three writes, in ascending provider number."""
    from harness.files import MemoryProvider
    from wasi_python import Errno, Mount, RefusedWrite

    run = _runner()
    provider = MemoryProvider({})

    def refused(path, data):
        return Errno.EIO if data else None

    def raises(path, data):
        if data:
            raise ValueError("the store broke")

    provider.answers.update({("write", "/1.txt"): refused, ("write", "/2.txt"): raises})
    done = run(["-c", THREE_DIRTY], mounts=[Mount(provider, "/work", writable=True)])
    assert (done.exit_code, done.stdout) == (0, b"True\n"), done
    walk = [e[1] for e in provider.log if e[0] == "write" and e[2]]
    assert walk == ["/1.txt", "/2.txt", "/3.txt"]
    assert provider.tree["/3.txt"].startswith(b"bytes of ")
    e = Errno.EIO
    assert done.files.refused == (
        RefusedWrite("/work", "write", ("/1.txt",), e, "exit", "refused"),
        RefusedWrite("/work", "write", ("/2.txt",), e, "exit", "fault"),
    )
    assert [(f.method, f.path, f.error) for f in done.files.faults] == [
        ("write", "/2.txt", "ValueError: the store broke")
    ]


WRITE_PARITY = r"""
import json, os, shutil, sys, tempfile
B = sys.argv[1]
rows = []

def tree():
    out = []
    for path, folders, names in os.walk(B):
        rel = os.path.relpath(path, B)
        out += [os.path.normpath(os.path.join(rel, d)) + "/" for d in folders]
        for n in names:
            with open(os.path.join(path, n), "rb") as f:
                out.append(os.path.normpath(os.path.join(rel, n)) + "=" + f.read().hex())
    return sorted(out)

def row(name, fn):
    try:
        value = fn()
    except OSError as e:
        value = ["errno", e.errno]
    rows.append([name, value, tree()])

def put(path, data, mode="w"):
    with open(path, mode) as f:
        return f.write(data)

def with_fd(path, flags, fn):
    fd = os.open(path, flags)
    try:
        return fn(fd)
    finally:
        os.close(fd)

def second_x():
    held = open(B + "/x.txt", "x")
    try:
        return open(B + "/x.txt", "x")
    finally:
        held.close()

def temporary():
    with tempfile.TemporaryFile(dir=B) as f:
        f.write(b"hello")
        f.seek(0)
        return f.read().decode()

def named():
    with tempfile.NamedTemporaryFile("wb", dir=B, delete=False) as f:
        f.write(b"x")
        f.flush()
        os.replace(f.name, B + "/final.bin")
    with open(B + "/final.bin", "rb") as f:
        return f.read().decode()

def save():
    put(B + "/save.tmp", "saved")
    os.replace(B + "/save.tmp", B + "/save.txt")

def rmtree():
    os.makedirs(B + "/t/u")
    put(B + "/t/u/f", "f")
    shutil.rmtree(B + "/t")

W, R, A = os.O_RDWR, os.O_RDONLY, os.O_WRONLY | os.O_APPEND
row("create", lambda: put(B + "/new.txt", "n"))
row("x on an existing file", lambda: open(B + "/a.txt", "x"))
row("a second x of a name just created", second_x)
row("create under a missing parent", lambda: put(B + "/missing/x", "n"))
row("create under a file", lambda: put(B + "/a.txt/x", "n"))
row("open a folder for writing", lambda: open(B + "/d", "w"))
row("O_CREAT | O_RDONLY, then a write", lambda: with_fd(B + "/cr.txt", os.O_CREAT | R,
                                                       lambda fd: os.write(fd, b"q")))
row("append", lambda: put(B + "/a.txt", "++", "a"))
row("truncate by w", lambda: put(B + "/b.txt", ""))
row("os.truncate", lambda: os.truncate(B + "/a.txt", 3))
row("pwrite past the end", lambda: with_fd(B + "/a.txt", W, lambda fd: os.pwrite(fd, b"z", 10)))
row("a seek past the end, then a write", lambda: with_fd(
    B + "/a.txt", W, lambda fd: (os.lseek(fd, 20, 0), os.write(fd, b"s"))))
row("a write on a read-only descriptor", lambda: with_fd(B + "/a.txt", R,
                                                        lambda fd: os.write(fd, b"x")))
row("pwrite on an append descriptor", lambda: with_fd(B + "/b.txt", A,
                                                     lambda fd: os.pwrite(fd, b"P", 0)))
row("fstat size after a write", lambda: with_fd(
    B + "/new.txt", W, lambda fd: (os.write(fd, b"12345"), os.fstat(fd).st_size)))
row("mkdir of an existing path", lambda: os.mkdir(B + "/d"))
row("mkdir under a missing parent", lambda: os.mkdir(B + "/missing/x"))
row("rmdir of a non-empty folder", lambda: os.rmdir(B + "/d"))
row("rmdir of a file", lambda: os.rmdir(B + "/a.txt"))
row("remove of a folder", lambda: os.remove(B + "/e"))
row("remove of a missing file", lambda: os.remove(B + "/missing.txt"))
row("rename a file to a new name", lambda: os.rename(B + "/new.txt", B + "/new2.txt"))
row("rename a file over a file", lambda: os.rename(B + "/new2.txt", B + "/b.txt"))
row("rename a folder over an empty folder", lambda: (os.mkdir(B + "/g"),
                                                    os.rename(B + "/d", B + "/g")))
row("rename a folder over a non-empty folder", lambda: (os.mkdir(B + "/h"), put(B + "/h/k", "k"),
                                                       os.rename(B + "/e", B + "/h")))
row("rename a file over a folder", lambda: os.rename(B + "/a.txt", B + "/e"))
row("rename a folder over a file", lambda: os.rename(B + "/e", B + "/a.txt"))
row("rename a folder into its own subfolder", lambda: os.rename(B + "/g", B + "/g/sub"))
row("rename a path onto itself", lambda: os.rename(B + "/a.txt", B + "/a.txt"))
row("rename to a read-only grant", lambda: os.rename(B + "/a.txt", "/ro/a.txt"))
row("link to a read-only grant", lambda: os.link(B + "/a.txt", "/ro/a.txt"))
row("TemporaryFile", temporary)
row("NamedTemporaryFile and os.replace", named)
row("shutil.copyfile", lambda: shutil.copyfile(B + "/a.txt", B + "/copy.txt"))
row("shutil.copy2", lambda: shutil.copy2(B + "/b.txt", B + "/copy2.txt"))
row("os.replace, an atomic save", save)
row("shutil.rmtree", rmtree)
row("shutil.move to another writable preopen", lambda: (put(B + "/mv.txt", "m"),
                                                       shutil.move(B + "/mv.txt", "/w2/mv.txt")))
row("sorted listing", lambda: sorted(os.listdir(B)))

# Decision 12's deliberate differences, asserted as its table says.
f = open(B + "/u.txt", "w")
f.write("u")
f.flush()
row("unflushed writes", lambda: os.stat(B + "/u.txt").st_size)
f.close()
one, two = open(B + "/two.txt", "w"), open(B + "/two.txt", "r+")
one.write("1111")
one.flush()
two.write("22")
two.flush()
two.close()
one.close()
row("two descriptors, one path", lambda: open(B + "/two.txt").read())
row("rename to another writable preopen", lambda: os.rename(B + "/save.txt", "/w2/save.txt"))
row("link within", lambda: os.link(B + "/a.txt", B + "/l.txt"))
row("symlink within", lambda: os.symlink("a.txt", B + "/s"))
row("utime", lambda: (os.utime(B + "/a.txt", (1, 2)), os.stat(B + "/a.txt").st_mtime_ns))
print(json.dumps(rows))
"""
WRITE_DIFFERENCES = {  # the grant's answer, the mount's (Decision 12)
    "unflushed writes": (1, 0),
    "two descriptors, one path": ("2211", "1111"),
    "rename to another writable preopen": (None, ["errno", 75]),
    "link within": (None, ["errno", 58]),
    "symlink within": (None, ["errno", 58]),
    "utime": ([None, 2000000000], [None, 0]),
}
LINUX_ROWS_V14 = {"remove of a folder": ["errno", 31]}  # the mount's everywhere; macOS says 63


@BINARY
def test_a_writable_mount_answers_as_a_writable_grant_does(guest_workdir, which) -> None:
    """The same tree as an in-memory writable mount and as a writable
    grant on disk: each row gives the same result or errno and leaves the same tree, read by
    the guest after each change. Decision 12's deliberate differences are asserted as its table
    says. A row whose grant answer is the host's own error is asserted on POSIX hosts, and the
    mount's answer to `os.remove` of a folder is Linux's everywhere. The rows whose
    grant answer is the host system's (a Windows grant renames a folder over a file) are asserted
    exactly per system, the mount's answer everywhere, and compared as parity on POSIX hosts."""
    from harness.files import (
        WRITE_BY_SYSTEM,
        WRITE_MOUNT,
        MemoryProvider,
        answer_matches,
        write_by_system,
        write_tree,
    )
    from wasi_python import Grant, Mount

    run = _runner()
    base = Path(tempfile.mkdtemp(prefix="write-parity-", dir=guest_workdir))
    results = {}
    for side in ("grant", "mount"):
        tree = write_tree(base / f"tree-{side}")
        ro, w2 = base / f"ro-{side}", base / f"w2-{side}"
        ro.mkdir()
        w2.mkdir()
        grants = [Grant(ro, "/ro"), Grant(w2, "/w2", writable=True)]
        provider = MemoryProvider()
        if side == "grant":
            grants.append(Grant(tree, "/work", writable=True))
        mounts = [Mount(provider, "/work", writable=True)] if side == "mount" else []
        done = run(
            ["-c", WRITE_PARITY, "/work"],
            grants=grants,
            mounts=mounts,
            snapshot=which == "snapshot",
        )
        assert (done.exit_code, done.stderr) == (0, b""), done
        results[side] = {name: (value, listing) for name, value, listing in json.loads(done.stdout)}
        if side == "mount":
            assert done.files.faults == ()  # each refusal is a row's errno, recorded
            assert {r.at for r in done.files.refused} <= {"open", "call"}
            assert sorted(p.name for p in tree.iterdir()) == ["a.txt", "b.txt", "d", "e"]
        assert sorted(p.name for p in ro.iterdir()) == []
    grant, mount = results["grant"], results["mount"]
    assert len(grant) == len(mount) == 45, len(grant)
    for name, (want_grant, want_mount) in WRITE_DIFFERENCES.items():
        if os.name == "posix":  # a Windows grant's answers are the host's: the dry run's
            assert grant[name][0] == want_grant, (name, grant[name][0])
        assert mount[name][0] == want_mount, (name, mount[name][0])
    for name, value in LINUX_ROWS_V14.items():
        assert mount[name][0] == value, (name, mount[name][0])
    for name in WRITE_BY_SYSTEM:  # the host system's answer, exactly; the mount's everywhere
        want = write_by_system(name, sys.platform)
        assert answer_matches(want, grant[name][0]), (name, sys.platform, grant[name][0])
        assert mount[name][0] == WRITE_MOUNT[name], (name, mount[name][0])
    differ = {}
    for name in grant:
        if name in WRITE_DIFFERENCES or (name in LINUX_ROWS_V14 and sys.platform != "linux"):
            continue
        if name in WRITE_BY_SYSTEM and os.name != "posix":
            continue  # asserted above; on POSIX hosts still compared as parity, value and tree
        host = isinstance(grant[name][0], list) and grant[name][0][:1] == ["errno"]
        if grant[name][0] != mount[name][0] and (os.name == "posix" or not host):
            differ[name] = (grant[name][0], mount[name][0])
        if grant[name][1] != mount[name][1] and os.name == "posix":
            differ[name + " (tree)"] = (grant[name][1], mount[name][1])
    assert differ == {}, differ


LINKS_AND_TIMES = r"""
import _host, json, os, shutil
out = {}

def row(name, fn):
    before = int(_host.call(b"total"))
    try:
        value = fn()
    except OSError as e:
        value = ["errno", e.errno]
    out[name] = [value, int(_host.call(b"total")) - before]

row("link within", lambda: os.link("/work/a.txt", "/work/l.txt"))
row("symlink within", lambda: os.symlink("a.txt", "/work/s"))
row("link to a writable grant", lambda: os.link("/work/a.txt", "/w2/l.txt"))
row("link to a read-only grant", lambda: os.link("/work/a.txt", "/ro/l.txt"))
row("utime of a file", lambda: os.utime("/work/a.txt", (1, 2)))
row("utime of the mount", lambda: os.utime("/work", (1, 2)))
out["stat after"] = os.stat("/work/a.txt").st_mtime_ns
row("shutil.copy2 within", lambda: shutil.copy2("/work/a.txt", "/work/c.txt"))
print(json.dumps(out))
"""


def test_links_and_times_in_a_writable_mount(guest_workdir) -> None:
    """`os.link` and `os.symlink` within a writable mount are ENOTSUP,
    `os.link` to a writable grant EXDEV and to a read-only grant EPERM, each with no provider
    call; `os.utime` of a file succeeds after one `stat`, which finds it as a grant would, and of
    the mount's own path with no call; `os.stat` then shows the provider's `mtime_ns`;
    `shutil.copy2` within the mount succeeds."""
    from harness.files import MemoryProvider
    from wasi_python import Grant, Mount, Stat

    class Timed(MemoryProvider):
        def stat(self, path):
            answer = super().stat(path)
            return Stat(answer.kind, answer.size, 7) if isinstance(answer, Stat) else answer

    run = _runner()
    provider = Timed()
    ro = Path(tempfile.mkdtemp(prefix="ro-", dir=guest_workdir))
    w2 = Path(tempfile.mkdtemp(prefix="w2-", dir=guest_workdir))
    done = run(
        ["-c", LINKS_AND_TIMES],
        mounts=[Mount(provider, "/work", writable=True)],
        grants=[Grant(ro, "/ro"), Grant(w2, "/w2", writable=True)],
        host=lambda frame: str(provider.total()).encode(),
    )
    assert (done.exit_code, done.stderr) == (0, b""), done
    out = json.loads(done.stdout)
    copy2 = out.pop("shutil.copy2 within")
    assert out == {
        "link within": [["errno", 58], 0],
        "symlink within": [["errno", 58], 0],
        "link to a writable grant": [["errno", 75], 0],
        "link to a read-only grant": [["errno", 63], 0],
        "utime of a file": [None, 1],
        "utime of the mount": [None, 0],
        "stat after": 7,
    }, out
    assert copy2[0] == "/work/c.txt" and provider.tree["/c.txt"] == provider.tree["/a.txt"]
    assert (list(ro.iterdir()), list(w2.iterdir())) == ([], [])


UNLINKED_AT_THE_ENDING = r"""
import _host, os, sys
held = os.open("/w/a.txt", os.O_WRONLY)  # "r+": one read, no write at open
os.write(held, b"stale")
os.replace("/w/b.txt", "/w/a.txt")  # the held file is replaced while open
temp = os.open("/w/t", os.O_RDWR | os.O_CREAT | os.O_EXCL)
os.write(temp, b"temp")
os.remove("/w/t")  # removed while open, as TemporaryFile does
if sys.argv[1] == "os._exit":
    os._exit(0)
_host.call(b"cancel")
while True:
    pass
"""


@BINARY
def test_unlinked_files_are_not_written_back_at_the_ending(which) -> None:
    """A file replaced by a rename while
    open and a file removed while open, both left open at an ending that is not their close
    (`os._exit`, a cancel): the walk writes neither back, so the provider holds the
    replacement's bytes and no temporary name, and the only `write` is the create at open."""
    from harness.files import MemoryProvider
    from wasi_python import Mount

    run = _runner()
    for ending, trapped in (("os._exit", None), ("cancel", "cancelled")):
        provider, event = MemoryProvider(), threading.Event()
        done = run(
            ["-c", UNLINKED_AT_THE_ENDING, ending],
            mounts=[Mount(provider, "/w", writable=True)],
            host=lambda frame, e=event: (e.set(), b"")[1],
            cancel=event,
            snapshot=which == "snapshot",
        )
        assert (done.trapped, done.stderr) == (trapped, b""), (ending, done)
        assert provider.log == [
            ("rename", "/b.txt", "/a.txt"),
            ("write", "/t", b""),
            ("remove", "/t"),
        ], (ending, provider.log)
        assert provider.tree["/a.txt"] == b"b\n" and "/t" not in provider.tree, ending
        assert (done.files.refused, done.files.refused_total) == ((), 0)


# Read-only code on the import path: entries a read-only grant serves, after the zip.

IMPORT_PATH_FILES = {
    "mylib.py": "VALUE = 'mylib from the grant'\n",
    "pkg/__init__.py": "",
    "pkg/__main__.py": "import sys\nprint('pkg main', sys.argv)\n",
    "main.py": "import sys, mylib\nprint(sys.argv, mylib.VALUE)\nraise SystemExit(3)\n",
    "boom.py": "def f():\n    return 1 / 0\n\n\nf()\n",
    "s_eval.py": "eval('1/0')\n",
    "s_exec.py": "exec('x = 1/0')\n",
}


def _folder(workdir: Path, files: dict[str, str], prefix: str = "import-path-") -> Path:
    """A fresh host folder holding `files` (relative path -> text)."""
    base = Path(tempfile.mkdtemp(prefix=prefix, dir=workdir))
    for name, text in files.items():
        (base / name).parent.mkdir(parents=True, exist_ok=True)
        (base / name).write_text(text)
    return base


@BINARY
def test_the_import_path_reaches_every_mode(guest_workdir, which) -> None:
    """An entry a read-only grant serves is on `sys.path`, after the zip,
    in every mode the reactor has; and every case below answers byte for byte as the same call
    without an import path does (the prelude's frames and source never show)."""
    from wasi_python import Grant

    run = _runner()
    snapshot = which == "snapshot"
    code = _folder(guest_workdir, IMPORT_PATH_FILES)
    grants = [Grant(code, "/code")]

    def call(argv, stdin=None, **kw):
        return run(argv, grants=grants, snapshot=snapshot, stdin=stdin, **kw)

    def with_path(argv, stdin=None):
        return call(argv, stdin, import_path=["/code"])

    stdlib = call(["-c", "import sys; print(sys.path)"])
    assert stdlib.exit_code == 0, stdlib
    import ast

    zip_entry = ast.literal_eval(stdlib.stdout.decode())[0]
    done = with_path(["-c", "import sys, mylib; print(sys.path, mylib.VALUE)"])
    assert done.stdout.decode() == f"{[zip_entry, '/code']} mylib from the grant\n", done
    done = with_path(["-m", "pkg", "x", "y"])
    assert done.stdout == b"pkg main ['/code/pkg/__main__.py', 'x', 'y']\n", done
    done = with_path(["/code/main.py", "s1"])
    assert (done.exit_code, done.stdout) == (3, b"['/code/main.py', 's1'] mylib from the grant\n")
    done = with_path([], stdin=b"import mylib; print(mylib.VALUE)\n")
    assert (done.exit_code, done.stdout) == (0, b"mylib from the grant\n"), done
    # run_async takes it too (no other check runs that path).
    import asyncio

    from wasi_python import run_async

    program = ["-c", "import sys, mylib; print(sys.path, mylib.VALUE)"]
    done = asyncio.run(run_async(program, grants=grants, snapshot=snapshot, import_path=["/code"]))
    assert done.stdout.decode() == f"{[zip_entry, '/code']} mylib from the grant\n", done
    # The prelude's two frames, and only with an import path: a call without one keeps today's
    # argv (the ratchet's fuel cannot see a prelude added to every call).
    depth = ["-c", "import traceback; print(len(traceback.extract_stack()))"]
    assert (call(depth).stdout, with_path(depth).stdout) == (b"2\n", b"4\n")
    # An entry with a quote, a double quote and a backslash reaches sys.path exactly.
    odd = _folder(guest_workdir, {"odd.py": "WHO = 'odd'\n"})
    name = "/a'b\"c\\d"
    done = run(["-c", "import sys, odd; print(sys.path[-1] == " + repr(name) + ", odd.WHO)"],
               grants=[Grant(odd, name)], import_path=[name], snapshot=snapshot)  # fmt: skip
    assert (done.exit_code, done.stdout) == (0, b"True odd\n"), done
    same = [
        (["-V"], None),
        (["-u", "-c", "print(1)"], None),
        (["-c", "import sys; sys.exit(7)"], None),
        (["-c", "raise SystemExit('bye')"], None),
        (["-c", "1/0"], None),
        (["/code/boom.py"], None),
        (["/code/nope.py"], None),
        (["-c", ORIG_ARGV], None),
        (["/code/s_eval.py"], None),
        (["/code/s_exec.py"], None),
        ([], b"eval('1/0')\n"),
    ]
    differ = []
    for argv, stdin in same:
        a, b = call(argv, stdin), with_path(argv, stdin)
        if (a.exit_code, a.stdout, a.stderr) != (b.exit_code, b.stdout, b.stderr):
            differ.append((argv or "stdin", a.stderr[-300:], b.stderr[-300:]))
    assert differ == [], f"{len(differ)} of {len(same)} differ: {differ}"


@BINARY
def test_the_import_path_comes_after_the_runtime(guest_workdir, which) -> None:
    """A name the runtime has is the runtime's on both binaries; among
    entries the first wins; and today's answers for names the runtime looks for and lacks are
    pinned (Decision 6), so a set that changes them is seen."""
    from wasi_python import Grant

    run = _runner()
    snapshot = which == "snapshot"
    shadows = {f"{n}/__init__.py": f"SHADOW = '{n}'\n" for n in ("json", "numpy", "csv", "host")}
    shadows |= {"uuid.py": "SHADOW = 'uuid'\n", "math.py": "SHADOW = 'math'\n"}
    code = _folder(guest_workdir, shadows)
    program = (
        "import json, math, numpy, csv, uuid, host\n"
        "print([m.__name__ for m in (json, math, numpy, csv, uuid, host) if hasattr(m, 'SHADOW')])"
    )
    done = run(["-c", program], grants=[Grant(code, "/code")], import_path=["/code"],
               snapshot=snapshot)  # fmt: skip
    assert (done.exit_code, done.stdout) == (0, b"[]\n"), done
    a = _folder(guest_workdir, {"same.py": "WHO = 'a'\n"})
    b = _folder(guest_workdir, {"same.py": "WHO = 'b'\n"})
    both = [Grant(a, "/a"), Grant(b, "/b")]
    for order, want in ((["/a", "/b"], b"a\n"), (["/b", "/a"], b"b\n")):
        done = run(["-c", "import same; print(same.WHO)"], grants=both, import_path=order,
                   snapshot=snapshot)  # fmt: skip
        assert (done.exit_code, done.stdout) == (0, want), (order, done)
    pytz = _folder(guest_workdir, {"pytz.py": STUB.format(name="pytz") + "raise ImportError\n"})
    done = run(["-c", "import pandas"], grants=[Grant(pytz, "/e")], import_path=["/e"],
               snapshot=snapshot)  # fmt: skip
    assert done.exit_code == 0, done
    # pandas' import looks for its optional pytz twice, in the call, on both binaries: the
    # snapshot pre-imports no package.
    assert done.stderr.decode().count("HIT pytz") == 2, done.stderr
    hashlib = _folder(guest_workdir, {"_hashlib.py": STUB.format(name="_hashlib")})
    done = run(["-c", "import hashlib"], grants=[Grant(hashlib, "/e")], import_path=["/e"],
               snapshot=snapshot)  # fmt: skip
    err = done.stderr.decode()
    assert done.exit_code == 1 and err.count("HIT _hashlib") == 1, done
    assert err.strip().splitlines()[-1].startswith("AttributeError"), err


ORIG_ARGV = "import sys; print(sys.orig_argv, sorted(k for k in dir() if not k.startswith('__')))"
STUB = "import sys\nsys.stderr.write('HIT {name}\\n')\n"


@BINARY
def test_a_zip_on_the_import_path(guest_workdir, which) -> None:
    """A zip inside a read-only grant, named as an entry, imports, and
    its resources and metadata read; a missing entry is skipped as CPython skips one."""
    import zipfile

    from wasi_python import Grant

    run = _runner()
    snapshot = which == "snapshot"
    code = _folder(guest_workdir, {"mylib.py": "VALUE = 'mylib'\n"})
    with zipfile.ZipFile(code / "lib.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("zmod.py", "VALUE = 'zmod'\n")
        z.writestr("zpkg/__init__.py", "")
        z.writestr("zpkg/data.txt", "resource in a zip\n")
        z.writestr("zdist-1.2.dist-info/METADATA", "Metadata-Version: 2.1\nName: zdist\n"
                   "Version: 1.2\n")  # fmt: skip
    (code / "ddist-3.4.dist-info").mkdir()
    (code / "ddist-3.4.dist-info" / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: ddist\nVersion: 3.4\n"
    )
    grants = [Grant(code, "/code")]
    program = (
        "import zmod, importlib.resources as r, importlib.metadata as m\n"
        "print(zmod.__file__)\n"
        "print(r.files('zpkg').joinpath('data.txt').read_text(), end='')\n"
        "print(m.version('zdist'), m.version('ddist'))\n"
    )
    done = run(["-c", program], grants=grants, import_path=["/code", "/code/lib.zip"],
               snapshot=snapshot)  # fmt: skip
    assert (done.exit_code, done.stdout) == (
        0,
        b"/code/lib.zip/zmod.py\nresource in a zip\n1.2 3.4\n",
    ), done
    program = "import sys, mylib; print(sys.path_importer_cache.get('/code/missing.zip'))"
    done = run(["-c", program], grants=grants, import_path=["/code/missing.zip", "/code"],
               snapshot=snapshot)  # fmt: skip
    assert (done.exit_code, done.stdout) == (0, b"None\n"), done


def test_the_command_takes_import_paths(capsysbinary, tmp_path) -> None:
    """`--import-path` reaches `run()` as `import_path=`; an entry no
    grant serves is `run()`'s refusal, exit 1."""
    _runner()
    (tmp_path / "mylib.py").write_text("VALUE = 'from the command'\n")
    code, line = _cli(capsysbinary, "run", "--grant", f"/code={tmp_path}", "--import-path",
                      "/code", "--", "-c", "import mylib; print(mylib.VALUE)")  # fmt: skip
    assert (code, line["exit_code"], line["stdout"]) == (0, 0, "from the command\n"), line
    code, line = _cli(capsysbinary, "run", "--import-path", "/code", "--", "-c", "pass")
    assert (code, line["kind"]) == (1, "ValueError"), line
    assert "import_path[0]" in line["error"], line


# Async tools: an `async def` tool or gate is awaited on the caller's loop under
# `run_async`, on a loop of the call's own under `run`; every end cancels a started task. A tool
# that must block awaits an event the check sets; a `timeout_s` only chooses the outcome, and is
# long enough for the tool to have started, so the check sees its cancel. Nothing here measures
# time; checks whose defect would hang run in a child with the 120 s fail-safe.

ASYNC_LOOP = "wasi-python-tool--loop"


def _loop_threads() -> set[threading.Thread]:
    return {t for t in threading.enumerate() if t.name == ASYNC_LOOP}


def test_a_guest_calls_an_async_tool_under_run(guest_workdir) -> None:
    """Criterion 9: two `async def` tools and an async gate; the tools ran on the call's own
    loop thread, which is gone once the call has returned and the threads are joined."""
    import asyncio

    from wasi_python import runner
    from wasi_python.tools import tool

    run = _runner()
    seen: list[str] = []

    @tool(read_only=True)
    async def lookup_region(code: str) -> dict:
        """Look up a sales region by its code."""
        await asyncio.sleep(0)
        seen.append(threading.current_thread().name)
        return {"code": code, "months": [{"month": m, "sales": 10 * m} for m in (1, 2, 3)]}

    @tool
    async def reverse(data: bytes) -> bytes:
        """Reverse some bytes."""
        seen.append(threading.current_thread().name)
        return data[::-1]

    async def gate(call) -> bool:
        await asyncio.sleep(0)
        return True

    before_loops = _loop_threads()
    before = runner.stats()["tool_threads_running"]
    done = run(["-c", TOOL_PROGRAM], tools=[lookup_region, reverse], gate=gate)
    assert (done.exit_code, done.stdout) == (0, b"EMEA 60 ['month', 'sales']\nb'\\x00cba'\n"), done
    assert _outcomes(done) == [
        ("list", None, "ok"),
        ("call", "lookup_region", "ok"),
        ("call", "reverse", "ok"),
    ]
    assert seen == [ASYNC_LOOP, ASYNC_LOOP]
    _join_tool_threads()
    assert _loop_threads() - before_loops == set()
    assert runner.stats()["tool_threads_running"] == before


CALLERS_LOOP = r"""
import asyncio, threading
import wasi_python
from wasi_python.tools import tool


async def main():
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    awaiting = asyncio.Event()
    seen = {}

    @tool
    async def wait_for_the_caller() -> int:
        "Await a Future of the caller's loop."
        seen["same loop"] = asyncio.get_running_loop() is loop
        seen["pending"] = not future.done()
        loop.call_soon_threadsafe(awaiting.set)
        return await future

    async def setter():
        await awaiting.wait()
        for _ in range(1000):
            await asyncio.sleep(0)
        future.set_result(42)

    asyncio.ensure_future(setter())
    done = await wasi_python.run_async(
        ["-c", "from host import tools\nprint(tools.wait_for_the_caller())"],
        tools=[wait_for_the_caller],
    )
    o = done.tools.outcomes[-1]
    print(done.stdout, o.outcome, o.fault, seen["same loop"], seen["pending"])


asyncio.run(main())
"""


def test_run_async_awaits_tools_on_the_callers_loop() -> None:
    """Criterion 10: the tool awaits a pending Future of the caller's loop,
    set only after the tool says it is awaiting; on any other loop that await raises."""
    assert _child(CALLERS_LOOP) == ["b'42\\n' ok None True True"]


TIMEOUT_THEN_ANOTHER = """
from host import tools, ToolTimeout
try:
    tools.a()
except ToolTimeout as e:
    print(e)
print(tools.b())
"""


def test_a_timeout_cancels_an_async_tool(guest_workdir) -> None:
    """Criterion 11: A times out and its started task is cancelled once; B then answers."""
    import asyncio

    from wasi_python.tools import tool

    run = _runner()
    started, cancels = threading.Event(), []

    @tool(timeout_s=0.5)
    async def a() -> int:
        """Wait for ever."""
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancels.append(1)
            raise
        return 1

    @tool
    async def b() -> str:
        """Answer, saying how many cancels A has seen. A's cancel was queued on the loop before
        B was posted, so A has met it by the time B runs: the call's end cancelled A, not the
        loop's closing at the run's end."""
        return f"B's answer; A cancelled {len(cancels)}"

    done = run(["-c", TIMEOUT_THEN_ANOTHER], tools=[a, b])
    want = b"a timed out after 0.5 s\nB's answer; A cancelled 1\n"
    assert (done.exit_code, done.stdout) == (0, want), done
    assert [(o.tool, o.outcome, o.abandoned) for o in done.tools.outcomes[1:]] == [
        ("a", "timeout", True),
        ("b", "ok", False),
    ]
    _join_tool_threads()
    assert (started.is_set(), cancels) == (True, [1])


ASYNC_TOOL_CHILD = r"""
import asyncio, signal, sys, threading
import wasi_python
from wasi_python.tools import tool

case = sys.argv[1]
started, cancel = threading.Event(), threading.Event()
cancels = []


@tool
async def block() -> int:
    "Wait for ever."
    started.set()
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        cancels.append(1)
        raise
    return 1


code = "from host import tools\ntools.block()\nprint('after the tool')\n"


def join_loop():
    for t in threading.enumerate():
        if t.name.startswith("wasi-python-tool-"):
            t.join(60)
    return not any(t.name == "wasi-python-tool--loop" for t in threading.enumerate())


if case == "deadline":
    r = wasi_python.run(["-c", code], tools=[block], deadline_s=3)
    joined = join_loop()
    print(r.tools.outcomes[-1].outcome, r.tools.outcomes[-1].message, cancels, joined)
    cancels.clear()

    async def main():
        return await wasi_python.run_async(["-c", code], tools=[block], deadline_s=3)

    r = asyncio.run(main())
    print(r.tools.outcomes[-1].outcome, r.tools.outcomes[-1].message, cancels)
elif case == "async":
    import concurrent.futures

    pool = concurrent.futures.ThreadPoolExecutor(1)

    async def main():
        task = asyncio.create_task(
            wasi_python.run_async(["-c", code], tools=[block], deadline_s=None, executor=pool)
        )
        await asyncio.to_thread(started.wait, 120)
        task.cancel()
        try:
            await task
            print("not cancelled")
        except asyncio.CancelledError:
            print("cancelled", cancels)
        print((await wasi_python.run_async(["-c", "print('next')"], executor=pool)).stdout)

    asyncio.run(main())
elif case == "cancel":
    def check():
        started.wait()
        cancel.set()

    threading.Thread(target=check, daemon=True).start()
    r = wasi_python.run(["-c", code], tools=[block], cancel=cancel, deadline_s=None, fuel=10**15)
    last = r.tools.outcomes[-1]
    joined = join_loop()
    print(r.trapped, r.exit_code, r.fuel_used, r.stdout, last.outcome, last.abandoned, cancels,
          joined)
elif case == "ctrl-c":
    signal.signal(signal.SIGINT, signal.default_int_handler)

    def interrupt():
        started.wait()
        signal.raise_signal(signal.SIGINT)

    threading.Thread(target=interrupt, daemon=True).start()
    try:
        r = wasi_python.run(["-c", code], tools=[block], deadline_s=None)
        print("returned", r.trapped)
    except KeyboardInterrupt:
        print("KeyboardInterrupt", cancels, join_loop())
"""


def test_the_deadline_cancels_an_async_tool() -> None:
    """Criterion 12: an async tool with no `timeout_s` is answered at the run's deadline and
    its task cancelled once, under `run` and under `run_async`."""
    assert _child(ASYNC_TOOL_CHILD, "deadline") == [
        "timeout block timed out at the run's deadline [1] True",
        "timeout block timed out at the run's deadline [1]",
    ]


def test_cancelling_run_async_cancels_an_async_tool() -> None:
    """Criterion 13: the task awaiting `run_async` is cancelled during an async tool; the tool's
    task is cancelled once, and the one worker is free for the next call."""
    assert _child(ASYNC_TOOL_CHILD, "async") == ["cancelled [1]", "b'next\\n'"]


def test_a_cancel_during_an_async_tool_is_named() -> None:
    """Criterion 14: `cancel` set during an async tool: the run is named "cancelled" and the
    task is cancelled once; the call's loop thread ends."""
    assert _child(ASYNC_TOOL_CHILD, "cancel") == ["cancelled None None b'' cancelled True [1] True"]


def test_ctrl_c_during_an_async_tool() -> None:
    """Criterion 15: Ctrl-C during an async tool: `run` raises KeyboardInterrupt, the task is
    cancelled once and the call's loop thread ends."""
    assert _child(ASYNC_TOOL_CHILD, "ctrl-c") == ["KeyboardInterrupt [1] True"]


def test_an_async_tool_that_ignores_its_cancel_is_bounded(guest_workdir) -> None:
    """Criterion 16: four abandoned calls whose tasks ignore their cancel, then two answered at
    once; after `run` returns, the four work threads and the call's loop thread are alive
    (the loop's run-down waits on the tasks), and all end once the tasks are released."""
    import asyncio

    from wasi_python import runner
    from wasi_python.tools import tool

    run = _runner()
    starts: list = []
    held: dict = {}

    @tool(timeout_s=0.5)
    async def stall() -> int:
        """Ignore every cancel until released."""
        starts.append(1)
        if "event" not in held:
            held["event"], held["loop"] = asyncio.Event(), asyncio.get_running_loop()
        while True:
            try:
                await held["event"].wait()
                return 1
            except asyncio.CancelledError:
                continue

    before = runner.stats()["tool_threads_running"]
    result: dict = {}

    def make_the_call() -> None:
        result["done"] = run(["-c", SIX_CALLS], tools=[stall])

    call = threading.Thread(target=make_the_call, daemon=True)
    call.start()
    call.join(120)  # a fail-safe: `run` must return without waiting for the tasks
    if call.is_alive():
        held["loop"].call_soon_threadsafe(held["event"].set)
        pytest.fail("run waited for the tasks that ignore their cancel")
    done = result["done"]
    assert done.exit_code == 0, done
    assert (
        done.stdout.decode().splitlines()
        == ["stall timed out after 0.5 s"] * 4
        + ["stall timed out: 4 earlier tool calls are still running"] * 2
    )
    assert len(starts) == 4
    assert runner.stats()["tool_threads_running"] == before + 5
    held["loop"].call_soon_threadsafe(held["event"].set)
    _join_tool_threads()
    assert runner.stats()["tool_threads_running"] == before


def test_one_calls_blocked_loop_does_not_starve_another(guest_workdir) -> None:
    """Criterion 17: call A's async tool blocks its own loop; call B, on another thread, gets
    its async tool's answer. With one loop for the process B would wait behind A."""
    from wasi_python.tools import tool

    run = _runner()
    blocking, release = threading.Event(), threading.Event()

    @tool(timeout_s=0.5)
    async def hog() -> int:
        """Block the loop it runs on."""
        blocking.set()
        release.wait(60)  # sync code inside a coroutine: the loop is held
        return 1

    @tool(timeout_s=5)
    async def instant() -> str:
        """Answer at once."""
        return "now"

    results: dict = {}

    def call(key, code, tools) -> None:
        results[key] = run(["-c", code], tools=tools)

    code_a = "from host import tools\ntry:\n    tools.hog()\n"
    code_a += "except TimeoutError:\n    print('A done')"
    a = threading.Thread(target=call, args=("A", code_a, [hog]))
    a.start()
    a.join()
    b = threading.Thread(
        target=call, args=("B", "from host import tools\nprint(tools.instant())", [instant])
    )
    b.start()
    b.join()
    release.set()
    _join_tool_threads()
    assert blocking.is_set()
    assert results["A"].stdout == b"A done\n", results["A"]
    assert results["B"].stdout == b"now\n", results["B"]
    assert results["B"].tools.outcomes[-1].outcome == "ok"


def test_fuel_is_exact_across_async_tool_calls(guest, guest_workdir) -> None:
    """Criterion 18: through the judge's driver (fixed clock and entropy), one program of two
    tool calls spends the same fuel with `async def` tools as with their `def` twins, and the
    same whatever its async tools await."""
    import asyncio

    from harness.calls import checked_call
    from wasi_python import _call
    from wasi_python.tools import tool

    turns = {"n": 0}

    @tool(name="nap")
    async def nap_async(n: int) -> int:
        """Nap."""  # the same descriptor as its twin's: the same frames, the same fuel
        for _ in range(turns["n"]):
            await asyncio.sleep(0)
        return n

    @tool(name="nap")
    def nap_sync(n: int) -> int:
        """Nap."""
        return n

    used = []
    for nap, turns["n"] in ((nap_async, 0), (nap_async, 50), (nap_sync, 0)):
        host = _call._tool_host(checked_call(tools=(nap,), tool_calls=1000), None, None, None, None)
        try:
            r = guest("snapshot", ["-c", TWO_CALLS], host=host)
        finally:
            host.close()
        assert (r.exit_code, r.stdout) == (0, b"1 2\n"), r.describe()
        assert [o.outcome for o in host.record.outcomes] == ["ok"] * 3
        used.append(r.fuel)
    assert used[0] == used[1] == used[2], used


# -------------------------------------------------------------------------------------------------
# A per-run budget of request bytes, and a call chain of any depth.

BYTES_BUDGET = """
from host import tools, ToolBudgetExceeded
seen = []
for data in (b"x" * 300_000, b"x" * 300_000, b"x" * 300_000, b"ab"):
    try:
        seen.append(tools.store(data))
    except ToolBudgetExceeded:
        seen.append("budget")
print(seen)
"""


def test_the_request_byte_budget_holds(guest_workdir, monkeypatch) -> None:
    """Under `max_tool_request_bytes=1_000_000`, the third 300,000-byte
    call (a 400,071-byte frame: bytes cross as base64) would pass the budget, so it is refused
    unread and the guest runs on; a small call after it fits. The frames the host reads are
    counted: 4 under the budget, 5 under the default, which a 1.2 MB call does not meet."""
    from wasi_python import _tool_host as H
    from wasi_python.tools import tool

    run = _runner()
    ran: list[int] = []

    @tool
    def store(data: bytes) -> int:
        """Store some bytes."""
        ran.append(len(data))
        return len(data)

    read: list[int] = []
    real = H._ToolHost.__call__

    def reading(self, frame: bytes) -> bytes:
        read.append(len(frame))
        return real(self, frame)

    monkeypatch.setattr(H._ToolHost, "__call__", reading)
    done = run(["-c", BYTES_BUDGET], tools=[store], max_tool_request_bytes=1_000_000)
    assert done.exit_code == 0, done
    assert done.stdout == b"[300000, 300000, 'budget', 2]\n", done
    outcomes = done.tools.outcomes
    assert [(o.op, o.outcome) for o in outcomes] == [
        ("list", "ok"),
        ("call", "ok"),
        ("call", "ok"),
        (None, "budget_exceeded"),
        ("call", "ok"),
    ], outcomes
    assert "bytes" in outcomes[3].message
    assert ran == [300_000, 300_000, 2]
    assert len(read) == 4 and sum(read) <= 1_000_000, read

    read.clear()
    ran.clear()
    done = run(["-c", BYTES_BUDGET], tools=[store])
    assert done.exit_code == 0, done
    assert done.stdout == b"[300000, 300000, 300000, 2]\n", done
    assert len(read) == 5, read


DISCOVERY_REFUSED = """
try:
    from host import tools
except ImportError as e:
    print("ImportError", e)
else:
    print("imported", sorted(tools.__all__))
"""


@pytest.mark.parametrize(
    "limit", [{"max_tool_calls": 0}, {"max_tool_request_bytes": 0}], ids=["calls", "bytes"]
)
def test_a_refused_discovery_frame_is_an_import_error(guest_workdir, limit) -> None:
    """As the README's **Limits** says: when the
    guest's discovery frame is itself refused, `from host import tools` raises `ImportError`
    naming the refusal, not `ToolBudgetExceeded`; the host ran no tool and read no frame past the
    one it refused."""
    from wasi_python.tools import tool

    run = _runner()

    @tool
    def store(data: bytes) -> int:
        """Store some bytes."""
        return len(data)

    done = run(["-c", DISCOVERY_REFUSED], tools=[store], **limit)
    assert done.exit_code == 0, done
    assert done.stdout.startswith(
        b"ImportError the host refused the tool list (budget_exceeded): "
    ), done
    assert [(o.op, o.outcome) for o in done.tools.outcomes] == [(None, "budget_exceeded")], done


def _orders_by_limit() -> tuple[list, object]:
    calls: list = []

    def orders(user_id: int, api_key: str, limit: int = 10) -> list[str]:
        """This user's orders."""
        calls.append((user_id, api_key, limit))
        return []

    return calls, orders


def _call_chain(depth: int, orders) -> object:
    """The deep call chain's construction: each hop an object whose class's `__call__` is the
    next object, the
    last class's `__call__` a partial (as a staticmethod, so 3.11 to 3.14 call it alike), and the
    annotations hand-copied onto every object so the hints read."""
    import functools

    class Last:
        __call__ = staticmethod(functools.partial(orders, user_id=42, api_key=SECRET))

    obj: object = Last()
    obj.__annotations__ = dict(orders.__annotations__)
    for _ in range(depth - 1):
        obj = type("Hop", (), {"__call__": obj})()
        obj.__annotations__ = dict(orders.__annotations__)
    return obj


def test_a_call_chain_of_any_depth_hides_bound_keywords() -> None:
    """A
    partial's bound keywords are fixed through a `__call__` chain of any depth and through a
    metaclass's `__call__`; the walk stops at C slots, so a C callable and an ordinary class
    are unchanged; a `__call__` cycle is refused with `TypeError`."""
    import functools
    import operator

    from wasi_python import _tool_host as H
    from wasi_python import tools as T
    from wasi_python.tools import stubs, tool

    calls, orders = _orders_by_limit()
    bound = functools.partial(orders, user_id=42, api_key=SECRET)
    bound.__annotations__ = dict(orders.__annotations__)

    class Meta(type):
        __call__ = staticmethod(bound)

    class Orders(metaclass=Meta):
        pass

    for label, fn in (
        ("depth 2", _call_chain(2, orders)),
        ("depth 3", _call_chain(3, orders)),
        ("metaclass", Orders),
    ):
        made = tool(fn, name="orders")
        assert list(made.input_schema["properties"]) == ["limit"], (label, made.input_schema)
        assert SECRET not in json.dumps(made.descriptor()), label
        assert SECRET not in stubs([made]) and "user_id" not in stubs([made]), label
        calls.clear()
        host = H._ToolHost([made])
        for args, outcome in (({"user_id": 7}, False), ({"limit": 3}, True)):
            frame = {"v": 1, "id": 1, "op": "call", "tool": "orders", "args": args}
            answer = json.loads(host(json.dumps(frame).encode()))
            assert answer["ok"] is outcome, (label, answer)
            if not outcome:
                assert answer["error"]["kind"] == "invalid_arguments", (label, answer)
                assert "unknown argument 'user_id'" in answer["error"]["message"], label
                assert calls == [], label
        assert calls == [(42, SECRET, 3)], (label, calls)

    assert T._bound_keywords("t", operator.itemgetter(0)) == frozenset()

    class Plain:
        pass

    assert T._bound_keywords("t", Plain) == frozenset()

    class Box:
        def __call__(self, a: int) -> int:
            """Give back a."""
            return a

    assert tool(Box(), name="box").input_schema["properties"] == {"a": {"type": "integer"}}

    class Loop:
        pass

    loop = Loop()
    Loop.__call__ = loop  # type: ignore[assignment]
    with pytest.raises(TypeError, match="nest deeper"):
        tool(loop, name="loop")


# A cap on files open at once.

OPEN_FILES = r"""
import errno, os

def fill(where, limit):
    held = []
    try:
        while len(held) < limit:
            held.append(os.open(where % (len(held) % 20), os.O_RDONLY))
    except OSError as e:
        return held, e.errno == errno.EMFILE
    return held, None

def refused(path):
    try:
        os.close(os.open(path, os.O_RDONLY))
        return "opened"
    except OSError as e:
        return "EMFILE" if e.errno == errno.EMFILE else e.errno

held, why = fill("/w/f%d", 20)
seen = [len(held), why]
os.close(held.pop())
held.append(os.open("/w/f0", os.O_RDONLY))
seen.append(refused("/w/f1"))
for fd in held:
    os.close(fd)
mount = [os.open("/m/f%d" % i, os.O_RDONLY) for i in range(4)]
grant = [os.open("/w/f%d" % i, os.O_RDONLY) for i in range(4)]
seen += [refused("/m/f9"), refused("/w/f9")]
os.close(mount.pop())
grant.append(os.open("/w/f5", os.O_RDONLY))
seen.append(len(mount) + len(grant))
print(*seen)
"""


class _TwentyFiles:
    """A provider of twenty one-byte files, /f0 to /f19, counting its reads."""

    def __init__(self) -> None:
        self.reads = 0

    def stat(self, path):
        from wasi_python import Errno, Stat

        if path == "/":
            return Stat("dir")
        return Stat("file", 1) if path[2:].isdigit() else Errno.ENOENT

    def list(self, path):
        return [(f"f{i}", "file") for i in range(20)]

    def read(self, path):
        from wasi_python import Errno

        if path == "/":
            return Errno.EISDIR
        self.reads += 1
        return b"x"


def test_the_open_file_cap_holds(guest_workdir) -> None:
    """Under `max_open_files=8` the guest opens exactly 8 files, then gets
    EMFILE and runs on; a close frees one slot; mount files count with grant files, and a
    refused mount open makes no provider call. The default does not meet 20 files; `run_async`
    passes its own cap. The guest imports everything first: an import from the zip at the cap
    would meet the cap too."""
    import asyncio

    import wasi_python
    from wasi_python import Grant, Mount

    run = _runner()
    folder = _root(guest_workdir)
    for i in range(20):
        (folder / f"f{i}").write_bytes(b"x")
    grants = [Grant(folder, "/w")]

    provider = _TwentyFiles()
    done = run(["-c", OPEN_FILES], grants=grants, mounts=[Mount(provider, "/m")], max_open_files=8)
    assert (done.exit_code, done.trapped) == (0, None), done
    assert done.stdout == b"8 True EMFILE EMFILE EMFILE 8\n", done
    assert done.files.calls["read"] == 4 == provider.reads

    first = "import os\nprint(len([os.open('/w/f%d' % i, os.O_RDONLY) for i in range(20)]))\n"
    done = run(["-c", first], grants=grants)
    assert (done.exit_code, done.stdout) == (0, b"20\n"), done

    code = (
        OPEN_FILES.split("def refused")[0]
        + "held, why = fill('/w/f%d', 20)\nprint(len(held), why)\n"
    )
    done = asyncio.run(wasi_python.run_async(["-c", code], grants=grants, max_open_files=2))
    assert (done.exit_code, done.stdout) == (0, b"2 True\n"), done


STAGE_FOLDERS = ("/stage", "/stage/lib", "/stage/lib/test", "/stage/judge")
STAGE_LISTER = f"import os\nfor d in {STAGE_FOLDERS!r}:\n    print(d, sorted(os.listdir(d)))\n"


def _a_stage(guest_workdir: Path) -> Path:
    """A small read-only stage, made and sealed as the judge's stages are."""
    from harness import litter

    root = Path(tempfile.mkdtemp(prefix="stage-", dir=guest_workdir))
    for rel in ("lib/test/a.py", "lib/test/b.txt", "lib/c.py", "judge/d.json"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(rel)
    litter.seal(root)
    return root


@pytest.mark.parametrize("which", ["plain", "snapshot"])
def test_a_file_dropped_into_a_stage_changes_nothing(guest, guest_workdir, which) -> None:
    """Guards a change: a desktop process (macOS's folder-size cache) writes `.DS_Store`
    into folders under the home folder, the judge's stages among them, and a file that lands in a
    grant changes what the guest lists and its fuel. A drop is refused or named, never measured:
    - where a folder's mode binds (POSIX, not root), every folder of a stage the judge grants
      read-only is sealed, so each drop is refused, and the guest's output and fuel are a twin's
      no writer touched (`os.listdir` reads no inode number or time, so they compare exactly);
    - where it does not (Windows; root), the drops land and the run fails with `HostLitter`,
      naming them.
    The twin is the run measured last, so the fuel row is the same program on every host."""
    from harness import litter

    binds = sys.platform != "win32" and os.geteuid() != 0
    clean, dropped = _a_stage(guest_workdir), _a_stage(guest_workdir)
    try:
        landed, refused = [], []
        for d, _dirs, _files in os.walk(dropped):
            try:
                (Path(d) / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1" + bytes(6140))
                landed.append(d)
            except PermissionError:
                refused.append(d)  # the seal: what a desktop writer meets too
        grant = [("/stage", dropped, False)]
        if binds:
            run = guest(which, ["-c", STAGE_LISTER], preopens=grant)
        else:
            assert landed, "the drops were refused where a folder's mode should not bind"
            with pytest.raises(litter.HostLitter, match=r"/stage/\.DS_Store \(before the run\)"):
                guest(which, ["-c", STAGE_LISTER], preopens=grant, record=False)
        twin = guest(which, ["-c", STAGE_LISTER], preopens=[("/stage", clean, False)])
        assert twin.exit_code == 0 and b"a.py" in twin.stdout, twin
        if binds:
            assert (run.exit_code, run.stdout) == (twin.exit_code, twin.stdout), run.stdout
            assert run.fuel == twin.fuel, (run.fuel, twin.fuel)
            assert landed == [] and len(refused) == len(STAGE_FOLDERS), (landed, refused)
            assert litter.litter_in(dropped) == []
    finally:
        litter.remove(clean)
        litter.remove(dropped)


EXCEL = """
import io, json
import openpyxl, pandas as pd
out = {}

def attempt(label, call):
    try:
        call()
        out[label] = "ok"
    except Exception as e:
        out[label] = [f"{type(e).__module__}.{type(e).__name__}", str(e)]

attempt("openpyxl", lambda: openpyxl.Workbook().save(io.BytesIO()))
df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
attempt("to_excel", lambda: df.to_excel(io.BytesIO()))
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="xlsxwriter", engine_kwargs={"options": {"in_memory": True}}) as w:
    df.to_excel(w, index=False)
out["in_memory"] = pd.read_excel(io.BytesIO(buf.getvalue())).equals(df)
print(json.dumps(out))
"""


@pytest.mark.parametrize("tmp", [False, True], ids=["nothing writable", "a writable /tmp"])
def test_excel_output_needs_a_writable_folder_or_xlsxwriter_in_memory(guest_workdir, tmp) -> None:
    """Through the runner's own defaults, which give nothing writable (the
    owner's decision 46): openpyxl's save and pandas' default .xlsx writer (xlsxwriter) need a
    temporary folder, so with none they raise, while xlsxwriter in memory writes a workbook that
    pandas reads back equal. A writable grant at /tmp makes both writers work. No deadline: the
    check counts outcomes, not time."""
    from wasi_python import Grant

    run = _runner()
    grants = []
    if tmp:
        folder = _root(guest_workdir)
        grants = [Grant(folder, "/tmp", writable=True)]
    done = run(["-c", EXCEL], grants=grants, deadline_s=None)
    assert (done.exit_code, done.trapped) == (0, None), done
    got = json.loads(done.stdout)
    assert got.pop("in_memory") is True, got
    if tmp:
        assert got == {"openpyxl": "ok", "to_excel": "ok"}, got
        return
    kind, message = got["openpyxl"]
    assert kind == "builtins.FileNotFoundError", got
    assert "No usable temporary directory" in message, got
    assert got["to_excel"][0] == "xlsxwriter.exceptions.FileCreateError", got


def test_the_judges_writable_roots_are_outside_the_home_folder(guest_workdir) -> None:
    """Guards a change: macOS's folder-size cache writes `.DS_Store` into folders under the home
    folder, and a writable root cannot be sealed against it (it is watched, not sealed), so a
    long run there was voided by `HostLitter`. On darwin every folder the judge's driver grants a
    guest unsealed lives under `paths.GUEST_TMP`, in the per-user temporary folder: a real path
    with no link in it (the runner refuses a link in a folder the user can write), outside the
    home folder, on the checkout's device (the fuel proof covers one device). Elsewhere it stays
    under `paths.HARNESS_TMP`. No artifact: a WAT command run through the driver, unmeasured."""
    needs.need("wasmtime-py")
    from harness import guest as driver
    from harness import wat

    wasm = wat.build(guest_workdir, "exit7.wasm", wat.COMMAND_EXIT_7)
    done = driver.run(wasm, [], workdir=guest_workdir, measured=False)
    assert done.exit_code == 7, done
    root = Path(done.root)
    if sys.platform != "darwin":
        assert root.is_relative_to(paths.HARNESS_TMP), root
        return
    assert os.path.realpath(root) == str(root), f"{root} passes through a link"
    home = Path(os.path.realpath(Path.home()))
    assert not root.is_relative_to(home), (
        f"a writable guest root under the home folder: {root}; macOS writes .DS_Store there"
        " (set TMPDIR to a folder outside the home folder)"
    )
    assert root.is_relative_to(paths.GUEST_TMP), (root, paths.GUEST_TMP)
    paths.HARNESS_TMP.mkdir(parents=True, exist_ok=True)
    devices = os.stat(paths.GUEST_TMP).st_dev, os.stat(paths.HARNESS_TMP).st_dev
    assert devices[0] == devices[1], (
        f"{paths.GUEST_TMP} (device {devices[0]}) and {paths.HARNESS_TMP} (device {devices[1]})"
        " are on two devices; the fuel proof covers one: set TMPDIR to a folder on the"
        " checkout's volume outside the home folder"
    )


# kiwisolver's solver keeps an equality chain of n + 1 variables; each of k calls either adds a
# required equality the chain contradicts, which the C++ solver throws and the binding catches
# as UnsatisfiableConstraint ("throw"), or adds and removes one it satisfies ("hold"). Both build
# a row whose size grows with the chain, so their work grows with it.
KIWI_CHAIN = """
import sys
import kiwisolver as kw
n, k, mode = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
solver = kw.Solver()
v = [kw.Variable(f"v{i}") for i in range(n + 1)]
solver.addConstraint(v[0] == 0)
for i in range(n):
    solver.addConstraint(v[i + 1] == v[i] + 1)
caught = 0
for j in range(k):
    if mode == "throw":
        try:
            solver.addConstraint(v[n] == -1 - j)
        except kw.UnsatisfiableConstraint:
            caught += 1
    else:
        c = v[n] == n
        solver.addConstraint(c)
        solver.removeConstraint(c)
print(mode, k, caught)
"""
CHAIN_SIZES = (200, 2000)
CHAIN_CALLS = 50
CALL_KINDS = {"throw": "failing", "hold": "no-throw"}


@pytest.mark.slow
def test_fuel_counts_the_work_a_caught_exception_ends(fact) -> None:
    """Fuel counts the work of a C++ call that ends in a caught exception. Each call's fuel is
    (the chain's run with 50 calls - the same chain's run with none) / 50, on the snapshot,
    whose fixed hash key repeats a run's fuel exactly (the plain reactor's fresh key moves this
    chain's by up to about 600,000 a run, more than 50 failing calls cost). A failing call at
    2,000 variables costs at least 3 times its cost at 200, as the no-throw call does (about 10
    times): an engine that resets fuel on a caught exception's edge to what remained before the
    call counts the failing call flat across the sizes. The deadline is a backstop, so a slow
    runner cannot hang the check; it fails differently from a short count."""
    needs.need("runner", "artifact dir", "snapshot binary")
    import wasi_python

    def fuel(n: int, k: int, mode: str) -> int:
        done = wasi_python.run(
            ["-c", KIWI_CHAIN, str(n), str(k), mode],
            fuel=10**12,
            deadline_s=600,
        )
        caught = k if mode == "throw" else 0
        assert (done.exit_code, done.trapped) == (0, None), done
        assert done.stdout == f"{mode} {k} {caught}\n".encode(), done
        assert done.fuel_used is not None, done
        return done.fuel_used

    per_call: dict[str, dict[int, int]] = {kind: {} for kind in CALL_KINDS}
    for n in CHAIN_SIZES:
        none = fuel(n, 0, "hold")
        for kind in CALL_KINDS:
            per_call[kind][n] = (fuel(n, CHAIN_CALLS, kind) - none) // CHAIN_CALLS
    fact(
        "fuel_per_call", {kind: {str(n): f for n, f in by.items()} for kind, by in per_call.items()}
    )
    print(f"fuel per call: {per_call}")
    small, large = CHAIN_SIZES
    findings = [
        f"a {label} call's fuel at {large:,} variables is under 3 times its fuel at {small:,}"
        for kind, label in CALL_KINDS.items()
        if per_call[kind][large] < 3 * per_call[kind][small]
    ]
    assert not findings, scan.report(findings, "fuel per call")
