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
    """A guest that rewrites its zip changes neither the artifact set nor its own next run."""
    run = _runner()
    zip_path = artifacts.path("python-stdlib.zip")
    before = paths.sha256_bytes(zip_path.read_bytes())
    root = _root(guest_workdir)
    ZIP = _zip()
    vandal = f"f = open({ZIP!r}, 'r+b'); f.seek(1000); f.write(b'X' * 64); f.close()"
    assert run(["-c", vandal], root=root).exit_code == 0
    assert paths.sha256_bytes(zip_path.read_bytes()) == before
    after = run(["-c", "import json, csv; print('ok')"], root=root)
    assert (after.exit_code, after.stdout) == (0, b"ok\n"), after
    assert paths.sha256_bytes((root / ZIP.lstrip("/")).read_bytes()) == before


@pytest.mark.parametrize("planted", ["the zip", "its directory"])
def test_runner_never_follows_a_link_a_guest_left(guest_workdir, planted) -> None:
    """A symbolic link the guest planted in its root is replaced, never written through."""
    run = _runner()
    base = Path(tempfile.mkdtemp(prefix="escape-", dir=guest_workdir))
    root, outside = base / "root", base / "outside"
    outside.mkdir()
    ZIP = _zip()
    if planted == "the zip":
        link, target, before = ZIP, "../../../../outside/target", f"os.remove({ZIP!r})"
    else:
        link, target = "/usr/local/lib", "../../../outside"
        before = "os.rename('/usr/local/lib', '/usr/local/old')"
    # Where the host does not let a guest make a link (Windows without the privilege), the
    # guest still removes the zip or its directory, and the next call must repair that.
    code = (
        f"import os\n{before}\n"
        f"try:\n    os.symlink({target!r}, {link!r})\n    print('linked')\n"
        "except OSError:\n    print('no link')\n"
    )
    first = run(["-c", code], root=root)
    assert first.exit_code == 0, first
    if os.name == "posix":  # there the guest can make the link, so the escape is really tried
        assert first.stdout == b"linked\n", first
    second = run(["-c", "print('ok')"], root=root)
    assert (second.exit_code, second.stdout) == (0, b"ok\n"), second
    assert list(outside.iterdir()) == [], list(outside.iterdir())


def test_runner_replaces_a_directory_left_in_the_zips_place(guest_workdir) -> None:
    """A guest that turns its zip path into a directory does not break the next call."""
    run = _runner()
    root = _root(guest_workdir)
    ZIP = _zip()
    code = f"import os; os.remove({ZIP!r}); os.makedirs({ZIP!r} + '/x')"
    assert run(["-c", code], root=root).exit_code == 0
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
wrong, raised = [], []


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
    r = wasi_python.run(["-c", f"print({token!r}, flush=True)\nwhile True: pass"], deadline_s=0.2)
    return r if (r.trapped, r.stdout) != ("deadline", f"{token}\n".encode()) else None


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
"""


def test_concurrent_calls_get_their_own_results() -> None:
    """Guards a change: concurrent calls share nothing (spec 011). 8 threads make 100 calls each,
    a mix of output, the door, a wait, fuel and a deadline trap; each must get its own result.
    It runs in a child process, because a corrupted callback table breaks every later call in
    the process it happens in; the 120 s timeout is a fail-safe, not a timing."""
    _runner()
    out = subprocess.run(
        [sys.executable, "-c", CONCURRENT], capture_output=True, text=True, timeout=120
    )
    assert out.returncode == 0, out.stderr[-2000:]
    summary = [line for line in out.stdout.splitlines() if " calls, " in line]
    assert summary == ["800 calls, 0 wrong, 0 raised"], out.stdout[-2000:]


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
import os, signal, threading, time
signal.signal(signal.SIGINT, signal.default_int_handler)  # as in a plain script
import wasi_python


def host(frame):
    def later():
        time.sleep(0.5)  # a trigger, not a measurement: the guest is computing by then
        os.kill(os.getpid(), signal.SIGINT)

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
