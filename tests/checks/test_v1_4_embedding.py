"""v1.4: an embedder preopens a directory, binds one function, and calls one export.

The guest-side checks use the judge's own driver, which does exactly that and nothing more;
the runner checks call `wasi_python.run`, the wheel's one-call embedding (spec 001)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from harness import needs, paths

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


@BINARY
def test_a_program_sees_real_entropy_and_file_metadata(guest, which) -> None:
    """The constants the build pins while it snapshots never reach a program: entropy, a file's
    inode and times, and a directory's size and link count (spec 012, Decision 4).

    The directory's two are compared with the host's own answer for the same directory, not with
    fixed numbers. On a host whose real answer is the pinned one (size 0 and one link, as Windows
    may give), this part cannot tell pinned from real; the macOS and Linux runs are the ones that
    tell."""
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
    """snapshot=False runs the plain reactor, which starts with nothing pre-imported."""
    run = _runner()
    code = "import sys; print('numpy' in sys.modules, sys.argv)"
    plain = run(["-c", code, "a"], root=_root(guest_workdir), snapshot=False)
    snap = run(["-c", code, "a"], root=_root(guest_workdir))
    assert (plain.exit_code, plain.stdout) == (0, b"False ['-c', 'a']\n"), plain
    assert (snap.exit_code, snap.stdout) == (0, b"True ['-c', 'a']\n"), snap


def test_runner_reports_a_host_fault(guest_workdir) -> None:
    """A host that raises answers -2, which the guest sees as OSError (spec 003, Decision 5)."""
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


def test_runner_caches_the_compiled_module(guest_workdir) -> None:
    """A first process compiles and writes one .cwasm; a second loads it and compiles nothing."""
    _runner()
    cache = Path(tempfile.mkdtemp(prefix="cache-", dir=guest_workdir))
    seen = [_cache_probe(guest_workdir, cache)[0] for _ in range(2)]
    assert seen[0] == [0, {"compiled": 1, "loaded": 0, "written": 1}], seen
    assert seen[1] == [0, {"compiled": 0, "loaded": 1, "written": 0}], seen
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
    report the same fuel (spec 008). Without that, wasmtime's memory-image copy at instantiation
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
    assert (code_a, stats_a) == (0, {"compiled": 1, "loaded": 0, "written": 1}), seen
    assert (code_b, stats_b) == (0, {"compiled": 0, "loaded": 1, "written": 0}), seen
    assert abs(fuel_a - fuel_b) < 1_000_000, f"compiled {fuel_a:,}, loaded {fuel_b:,}"


def test_runner_refuses_a_cache_others_can_write(guest_workdir) -> None:
    """A .cwasm is native code: on POSIX a cache directory others can write is neither read
    nor written. Windows has no such mode bits, and the runner makes no ownership check there
    (spec 001, Decision 3: the default cache is under the user's own profile); this check
    records that behaviour."""
    _runner()
    cache = Path(tempfile.mkdtemp(prefix="cache-", dir=guest_workdir))
    cache.chmod(0o777)
    seen, stderr = _cache_probe(guest_workdir, cache)
    if os.name == "posix":
        assert seen == [0, {"compiled": 1, "loaded": 0, "written": 0}], seen
        assert "not using the module cache" in stderr, stderr
        assert list(cache.iterdir()) == []
    else:
        assert seen == [0, {"compiled": 1, "loaded": 0, "written": 1}], seen


def _zip() -> str:
    """The stdlib zip's guest path, named from MANIFEST's `python` line (python3XY.zip)."""
    directory = paths.artifact_dir()
    assert directory is not None
    version = paths.parse_manifest((directory / "MANIFEST").read_text()).python
    major, minor = version.split(".")[:2]
    return f"/usr/local/lib/python{major}{minor}.zip"


def test_runner_keeps_the_artifact_zip_out_of_the_guests_reach(guest_workdir, artifacts) -> None:
    """A guest that rewrites its zip changes neither the artifact set nor its own next run. Since
    spec 017 the zip is a read-only grant: the write is refused, and a root holds no zip."""
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
    through. Since spec 017 removing or renaming the zip or its folder through /usr/local/lib is
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
    """A guest that would turn its zip path into a directory cannot (spec 017: the zip is a
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


def test_package_imports_without_wasmtime() -> None:
    """The package imports with the `run` extra absent; only run() needs wasmtime."""
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


def test_a_failed_instantiation_reports_no_fuel(guest_workdir) -> None:
    """A memory cap below the module's own minimum fails instantiation: the call traps and
    reports 0 instructions, never the unmetered budget instantiation ran on (spec 008)."""
    run = _runner()
    done = run(["-c", "pass"], root=_root(guest_workdir), memory_bytes=1 << 20, fuel=10**9)
    assert done.exit_code is None and done.trapped, done
    assert done.fuel_used == 0, done


def test_an_ordinary_sleep_still_works(guest_workdir) -> None:
    """A short sleep with no deadline ends as asked and the program goes on (spec 010)."""
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
    """Guards a change: concurrent calls share nothing (spec 011). 8 threads make 100 calls each,
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
    every call's streams (spec 011). The loop that waits for those frees, which wasmtime runs on
    its own threads, is a fail-safe that counts rounds."""
    import gc
    import time

    import wasmtime
    from wasmtime import _func, _wasi

    from wasi_python import runner

    run = _runner()
    root = _root(guest_workdir)
    for fuel in (None, 10**10):
        run(["-c", "print(1)"], root=root, fuel=fuel)
    counts = {"define_func": 0, "custom outputs": 0}
    define_func = wasmtime.Linker.define_func

    def counted(self, *args, **kwargs):
        counts["define_func"] += 1
        return define_func(self, *args, **kwargs)

    allocate = _wasi.CUSTOM_OUTPUTS.allocate

    def counted_output(value):
        counts["custom outputs"] += 1
        return allocate(value)

    monkeypatch.setattr(wasmtime.Linker, "define_func", counted)
    monkeypatch.setattr(_wasi.CUSTOM_OUTPUTS, "allocate", counted_output)
    functions = len(_func.FUNCTIONS.list)
    for fuel in (None, 10**10, None):
        done = run(["-c", "print('x')"], root=root, fuel=fuel)
        assert (done.exit_code, done.stdout) == (0, b"x\n"), done
    assert counts == {"define_func": 0, "custom outputs": 0}, counts
    assert len(_func.FUNCTIONS.list) == functions
    for _ in range(200):
        gc.collect()
        if not runner._outputs:
            break
        time.sleep(0.01)
    assert not runner._outputs, f"{len(runner._outputs)} streams never freed"


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
    process goes on (spec 011). In a child process, with a 120 s fail-safe."""
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
    nothing is written into a given root (spec 013)."""
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
    is honoured and fuel_used is a plain int, from an argument or from DEFAULTS (spec 013)."""
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
    with ValueError before any work (spec 014)."""
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
    arrives as its bytes (spec 014)."""
    run = _runner()
    code = "import os, sys; print(sys.argv[1:], os.environ['K'], sys.stdin.read())"
    done = run(
        (a for a in ["-c", code, _Lying("arg")]),
        root=_root(guest_workdir),
        env={_Lying("K"): _Lying("val")},
        stdin=memoryview(b"h_i_")[::2],
    )
    assert (done.exit_code, done.stdout) == (0, b"['arg'] val hi\n"), done


# Run from async code (spec 015). Each check runs its calls in a child process with a 120 s
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
    turned 1,000 times, so they finish only if the loop runs while they do (spec 015). A
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
        # The process's own zip folder (spec 017) lives until it exits: not the call's.
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
    worker and removes its private root before `CancelledError` reaches the caller (spec 015).
    The guest has no deadline and no other call runs, so only the cancel can end it."""
    assert _child(CANCEL_ASYNC, work) == ["cancelled 1 []", "b'next\\n'"]


CANCEL_RUN = r"""
import asyncio, sys, threading
import wasi_python

case = sys.argv[1]
event = threading.Event()


def sets(frame):
    event.set()
    return b""


def raises(frame):
    raise asyncio.CancelledError


busy, sleeps = "while True: pass", "import time; time.sleep(10**6)"
door = "import _host\n_host.call(b'x')\n"
if case in ("busy", "sleeping"):
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
    set, and names it "cancelled" with no fuel count (spec 015). The guest has no deadline."""
    assert _child(CANCEL_RUN, work) == ["cancelled None"]


def test_a_stop_holds_under_cancel() -> None:
    """Guards a change: a host's exception still stops a call that has a `cancel` (spec 011's
    stop), though the guest catches the door's error and computes on with no deadline (spec
    015's review, finding 1)."""
    assert _child(CANCEL_RUN, "stop") == ["CancelledError"]


def test_a_deadline_under_cancel_is_named() -> None:
    """Guards a change: under `cancel=`, a deadline reaches Python as the epoch callback's error,
    not as wasmtime's interrupt trap; the runner still names it "deadline" (spec 015's review,
    finding 3)."""
    assert _child(CANCEL_RUN, "deadline") == ["deadline None"]


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
    call never starts, so a process with a guest that has no deadline still exits (spec 015)."""
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
from wasi_python import runner

print(hasattr(os, "register_at_fork"), wasi_python.run(["-c", "print('ran')"]).stdout)
print(runner._fork)
"""


def test_a_forked_child_is_refused() -> None:
    """Guards a change: a child forked after its parent ran a guest aborted on macOS, and could
    not keep a deadline elsewhere; now it is refused with a clear error, while a child of a
    parent that only imported the package runs (spec 015). A fresh parent, not pytest's. Where
    there is no fork (Windows), the runner registers no fork hook and a call runs as usual."""
    if not hasattr(os, "fork"):
        assert _child(NO_FORK) == ["False b'ran\\n'", "{'used': True, 'forked': False}"]
        return
    assert _child(FORK, "used") == ["child refused", "status 0"]
    assert _child(FORK, "imported") == ["child ran", "status 0"]


# Dead processes' folders are swept, by lock (spec 016). Each check runs its calls in child
# processes with a 120 s timeout, a fail-safe, and a temporary folder of its own.


HELD = r"""
import sys, tempfile
tempfile.tempdir = sys.argv[1]
import wasi_python

def host(frame):
    print("held", flush=True)
    sys.stdin.readline()  # until the parent says go, or forever
    return b""

done = wasi_python.run(["-c", "import _host; _host.call(b'x')"], host=host, stdin=b"secret")
print("ended", done.exit_code, flush=True)
"""

ONE_CALL = r"""
import sys, tempfile
tempfile.tempdir = sys.argv[1]
import wasi_python
from wasi_python import runner

done = wasi_python.run(["-c", "print(1)"])
print(done.exit_code, runner._sweep_state["swept"])
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

    from wasi_python import runner

    for _ in range(1200):
        free = True
        for lock in temp.glob("*.lock"):
            fd = os.open(lock, os.O_RDWR | getattr(os, "O_BINARY", 0))
            try:
                free = free and runner._try_lock(fd) is True
            finally:
                runner._unlock_close(fd)
        if free:
            return True
        time.sleep(0.1)
    return False


def _entries(temp: Path) -> list[str]:
    return sorted(p.name for p in temp.iterdir() if p.name.startswith("wasi-python-"))


def test_a_killed_process_leaves_nothing_after_the_next_call(tmp_path) -> None:
    """Guards a change: a process killed mid-call left its private root and its stdin folder in
    the temporary folder for good (the 0.1.0a2 security review, F6). Each now has a locked lock
    file beside it; the lock dies with the process, and the next process's first call removes
    both (spec 016). Since spec 017 the killed process's zip folder is left too, with its own
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
    a call still running holds its lock, so its folders stay, and it cleans up after itself
    (spec 016)."""
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


# Typed grants (spec 017).
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
    """Guards a change (spec 017): each grant reaches its guest path with its own mode, nested or
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
    """Guards a change (spec 017): `root=False` with no grants still runs a program, on the zip
    alone; there is no `/`, and no HOME, since there is no /tmp to make it in."""
    run = _runner()
    code = (
        "import os, json\n"
        "try:\n    os.listdir('/')\n    print('root')\nexcept OSError:\n    print('no root')\n"
        "print(os.environ.get('HOME'), json.dumps([1]))\n"
    )
    done = run(["-c", code], root=False)
    assert (done.exit_code, done.stdout) == (0, b"no root\nNone [1]\n"), done


@pytest.mark.parametrize("with_root", [False, True], ids=["no root", "a root"])
def test_home_follows_a_writable_tmp_grant(guest_workdir, with_root) -> None:
    """Guards a change (spec 017, Decision 3): HOME is made in the folder the guest sees at /tmp,
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
    """Guards a change (spec 017): the zip folder is the process's that made it; a child forked
    after a call forgets it, so the child's exit cannot remove it from under its parent. Where
    there is no fork (Windows), a second call reuses the folder."""
    script = FORK_ZIP if hasattr(os, "fork") else NO_FORK_ZIP
    assert _child(script, str(tmp_path)) == ["b'1\\n' True b'2\\n'"]


def test_a_deadline_during_the_grant_check_is_a_deadline(monkeypatch) -> None:
    """Guards a change (spec 017, Decision 5): a deadline that passes while the runner checks the
    preopens traps the check module, and the call reports "deadline", never a refusal; the guest
    never runs. The epoch is advanced by count, not by waiting."""
    run = _runner()
    from wasi_python import runner

    real, calls = runner._check_preopens, []

    def late(wt, linker, store, check, preopens):
        for engine in list(runner._engines.values()):
            for _ in range(1000):
                engine.increment_epoch()
        return real(wt, linker, store, check, preopens)

    monkeypatch.setattr(runner, "_check_preopens", late)
    done = run(["-c", "import _host; _host.call(b'x')"], host=calls.append, deadline_s=0.05)
    assert (done.exit_code, done.trapped, calls) == (None, "deadline", []), done


# The command line (spec 019).
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
    """Guards a change (spec 019): `wasi-python run` prints one JSON line; the command's exit code
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
    """Guards a change (spec 019, Decision 2): the command passes an unset `cancel`, so Ctrl-C stops
    a guest that computes, with no deadline, and the command answers 130 and prints nothing more.
    The sleep only makes the signal likely to land while the guest computes; either way the answer
    must be 130. A fail-safe timeout asserts no duration."""
    lines = _child(COMMAND_CTRL_C)
    assert len(lines) == 2 and json.loads(lines[0])["exit_code"] == 0, lines
    assert lines[1] == "exit 130", lines


def test_the_installed_command_prints_the_same_line() -> None:
    """Guards a change (spec 019): the `wasi-python` script this environment installed."""
    import shutil
    import sysconfig

    _runner()
    script = shutil.which("wasi-python", path=sysconfig.get_path("scripts"))
    assert script is not None, sysconfig.get_path("scripts")
    out = subprocess.run([script, "run", "--", "-c", "print(1)"], capture_output=True, timeout=120)
    assert (out.returncode, out.stdout) == (0, INTENT), out.stderr[-500:]


def test_the_command_grants_folders(capsysbinary, tmp_path) -> None:
    """Guards a change (spec 022): `--grant` and `--grant-writable` reach the guest with their
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
