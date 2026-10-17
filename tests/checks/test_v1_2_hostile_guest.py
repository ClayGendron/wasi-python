"""v1.2, the hostile guest: a program written to escape, persist, exhaust or crash is held by the
wall and by the runner's defaults (spec 006). Each check names whether it guards a change spec 006
made or behaviour that already held."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from harness import needs, paths

pytestmark = pytest.mark.goal("v1.2")

BOTH = pytest.mark.parametrize("snapshot", [False, True], ids=["plain", "snapshot"])


def _run():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python.run


def _version() -> tuple[str, str]:
    """('3.15', '315') from MANIFEST's python line."""
    directory = paths.artifact_dir()
    assert directory is not None
    major, minor = paths.parse_manifest((directory / "MANIFEST").read_text()).python.split(".")[:2]
    return f"{major}.{minor}", f"{major}{minor}"


def _root(workdir: Path) -> Path:
    return Path(tempfile.mkdtemp(prefix="hostile-", dir=workdir))


@BOTH
def test_a_link_out_of_the_root_is_refused(guest_workdir, snapshot) -> None:
    """Guards existing behaviour: neither kind of link reaches outside the root."""
    run = _run()
    base = Path(tempfile.mkdtemp(prefix="links-", dir=guest_workdir))
    root, outside = base / "root", base / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret").write_text("host data")
    code = (
        "import os\n"
        f"links = (('abs', {str(outside / 'secret')!r}), ('rel', '../outside/secret'))\n"
        "for name, target in links:\n"
        "    try:\n"
        "        os.symlink(target, '/' + name)\n"
        "    except OSError:\n"
        "        print(name, 'refused at creation')\n"
        "        continue\n"
        "    for mode in ('r', 'w'):\n"
        "        try:\n"
        "            with open('/' + name, mode) as f:\n"
        "                print(name, mode, 'OPENED', f.read() if mode == 'r' else f.write('x'))\n"
        "        except OSError:\n"
        "            print(name, mode, 'refused')\n"
    )
    done = run(["-c", code], root=root, snapshot=snapshot)
    assert done.exit_code == 0, done
    assert b"OPENED" not in done.stdout, done.stdout
    assert (outside / "secret").read_text() == "host data"
    assert sorted(p.name for p in outside.iterdir()) == ["secret"]


PLANT = """
import os
mm, tag = {mm!r}, {tag!r}
# Through /usr/./local/lib: the root's own folder, behind the stdlib's read-only grant for every
# path spelled normally (spec 017), but still the guest's to write.
lib = f"/usr/./local/lib/python{{mm}}"
venv = f"/usr/local/bin/lib/python{{mm}}/site-packages"
for d in (lib, lib + "/lib-dynload", lib + "/site-packages", venv):
    os.makedirs(d, exist_ok=True)
for d, name in ((lib, "evil_a"), (lib + "/lib-dynload", "evil_b"),
                (lib + "/site-packages", "evil_c"), (venv, "evil_d")):
    with open(f"{{d}}/{{name}}.py", "w") as f:
        f.write("open('/MARKER-' + __name__, 'w').close()\\n")
for d in (lib + "/site-packages", venv):
    with open(f"{{d}}/zz.pth", "w") as f:
        f.write("import os; open('/MARKER-pth', 'w').close()\\n")
with open("/usr/local/bin/pyvenv.cfg", "w") as f:
    f.write("home = /usr/local/bin\\ninclude-system-site-packages = false\\n")
print("planted")
"""

PROBE = """
import importlib, os, sys
found = []
for name in ("evil_a", "evil_b", "evil_c", "evil_d"):
    try:
        importlib.import_module(name)
        found.append(name)
    except ImportError:
        pass
print(found, sorted(n for n in os.listdir("/") if n.startswith("MARKER")), sys.path)
"""


REFUSED = """
import os
for d in ("/usr/local/lib/python{mm}", "/usr/local/lib/python{mm}/site-packages"):
    try:
        os.makedirs(d, exist_ok=True)
        print("made", d)
    except PermissionError:
        print("refused")
"""


@BOTH
def test_planted_code_never_runs(guest_workdir, snapshot) -> None:
    """Guards a change on the plain reactor (it ran a planted .pth and imported planted modules),
    existing behaviour on the snapshot: code one run leaves in a root never runs in the next.
    Since spec 017 the /usr/local/lib routes are refused outright (the stdlib's read-only grant),
    and the same code is planted through /usr/./local/lib, the root's own folder."""
    run = _run()
    mm, tag = _version()
    root = _root(guest_workdir)
    refused = run(["-c", REFUSED.format(mm=mm)], root=root, snapshot=snapshot)
    assert (refused.exit_code, refused.stdout) == (0, b"refused\nrefused\n"), refused
    first = run(["-c", PLANT.format(mm=mm, tag=tag)], root=root, snapshot=snapshot)
    assert (first.exit_code, first.stdout) == (0, b"planted\n"), first
    second = run(["-c", PROBE], root=root, snapshot=snapshot)
    assert second.exit_code == 0, second
    # Not sys.prefix: a planted pyvenv.cfg still moves the plain reactor's, which is data, not
    # code (spec 006, Decision 4).
    want = f"[] [] ['/usr/local/lib/python{tag}.zip']\n"
    assert second.stdout.decode() == want, second
    assert second.stderr == b"", second.stderr


def test_a_planted_zone_file_leaves_zoneinfo_alone(guest_workdir) -> None:
    """Guards a change: the runner's PYTHONTZPATH="" keeps zoneinfo on the zip's tzdata."""
    run = _run()
    root = _root(guest_workdir)
    plant = (
        "import os, zoneinfo\n"
        "os.makedirs('/usr/share/zoneinfo/America', exist_ok=True)\n"
        "src = zoneinfo.ZoneInfo('Asia/Tokyo')\n"
        "import importlib.resources as r\n"
        "data = r.files('tzdata.zoneinfo').joinpath('Asia/Tokyo').read_bytes()\n"
        "open('/usr/share/zoneinfo/America/New_York', 'wb').write(data)\n"
    )
    assert run(["-c", plant], root=root).exit_code == 0
    probe = (
        "import datetime, zoneinfo\n"
        "t = datetime.datetime(2026, 7, 1, tzinfo=zoneinfo.ZoneInfo('America/New_York'))\n"
        "print(t.utcoffset())\n"
    )
    done = run(["-c", probe], root=root)
    assert (done.exit_code, done.stdout) == (0, b"-1 day, 20:00:00\n"), done


def test_temporary_files_go_to_tmp(guest_workdir) -> None:
    """Guards a change: without /tmp, tempfile used / itself."""
    run = _run()
    root = _root(guest_workdir)
    code = (
        "import os, tempfile\n"
        "fd, p = tempfile.mkstemp()\n"
        "print(tempfile.gettempdir(), os.path.dirname(p))\n"
    )
    done = run(["-c", code], root=root)
    assert (done.exit_code, done.stdout) == (0, b"/tmp /tmp\n"), done


def test_a_call_without_a_root_shares_nothing(guest_workdir, monkeypatch) -> None:
    """Guards a change: no root means a fresh private one, removed after the call."""
    run = _run()
    scratch = Path(tempfile.mkdtemp(prefix="rootless-", dir=guest_workdir))
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    write = "open('/left-behind', 'w').write('x'); print(sorted(__import__('os').listdir('/')))"
    first = run(["-c", write])
    assert (first.exit_code, first.stdout) == (0, b"['left-behind', 'tmp', 'usr']\n"), first
    assert list(scratch.iterdir()) == []
    second = run(["-c", "import os; print(os.path.exists('/left-behind'))"])
    assert (second.exit_code, second.stdout) == (0, b"False\n"), second
    assert list(scratch.iterdir()) == []


def test_memory_has_a_default_cap(guest_workdir, monkeypatch) -> None:
    """Guards a change: a call that names no memory cap still has one."""
    run = _run()
    from wasi_python import runner

    monkeypatch.setattr(runner, "DEFAULTS", runner.Defaults(128 << 20, 60.0, 16 << 20))
    code = (
        "try:\n    b = bytearray(200 << 20)\n    print('allocated')\n"
        "except MemoryError:\n    print('MemoryError')\n"
    )
    done = run(["-c", code], root=_root(guest_workdir))
    assert (done.exit_code, done.stdout) == (0, b"MemoryError\n"), done


def test_a_run_has_a_default_deadline(guest_workdir, monkeypatch) -> None:
    """Guards a change: a call that names no deadline still ends."""
    run = _run()
    from wasi_python import runner

    monkeypatch.setattr(runner, "DEFAULTS", runner.Defaults(1 << 30, 0.2, 16 << 20))
    done = run(["-c", "while True:\n    pass\n"], root=_root(guest_workdir))
    assert (done.exit_code, done.trapped) == (None, "deadline"), done


def test_output_has_a_default_cap(guest_workdir, monkeypatch) -> None:
    """Guards a change: output past the cap is dropped, the program goes on, and it is named."""
    run = _run()
    from wasi_python import runner

    monkeypatch.setattr(runner, "DEFAULTS", runner.Defaults(1 << 30, 60.0, 4096))
    code = (
        "import sys\nsys.stdout.write('x' * (1 << 20))\nsys.stdout.flush()\n"
        "print('done', file=sys.stderr)\n"
    )
    done = run(["-c", code], root=_root(guest_workdir))
    assert done.exit_code == 0, done
    assert done.stdout == b"x" * 4096
    assert done.stderr == b"done\n"
    assert done.truncated == ("stdout",)


def _probe_artifacts(workdir: Path, ptr: int, length: int):
    """The real zip and MANIFEST, with a door-probing WAT module as the snapshot."""
    import wasi_python
    from harness import wat

    real = wasi_python.artifacts()
    d = Path(tempfile.mkdtemp(prefix="door-", dir=workdir))
    probe = wat.build(d, "probe.wasm", wat.door_probe(ptr, length))
    return wasi_python.Artifacts(probe, real.plain, real.stdlib_zip, real.manifest)


@pytest.mark.parametrize(
    "case", ["request past memory", "response too large", "host raises", "a good frame"]
)
def test_the_door_bounds_every_frame(guest_workdir, monkeypatch, case) -> None:
    """Guards a change: every frame is bounded, and nothing a frame or a host does escapes run()."""
    run = _run()
    from wasi_python import runner

    monkeypatch.setattr(runner, "MAX_RESPONSE", 1000)
    seen: list[bytes] = []

    def host(request: bytes) -> bytes:
        seen.append(request)
        if case == "host raises":
            raise RuntimeError("the host failed")
        return b"y" * (2000 if case == "response too large" else 3)

    ptr, length = (65530, 16) if case == "request past memory" else (16, 3)
    found = _probe_artifacts(guest_workdir, ptr, length)
    done = run([], root=_root(guest_workdir), host=host, artifacts=found, cache_dir=False)
    want = 0 if case == "a good frame" else -2
    assert (done.exit_code, done.trapped) == (want, None), done
    if case == "request past memory":
        assert seen == [], "the host was called with a frame that runs past guest memory"
    again = run(["-c", "print('ok')"], root=_root(guest_workdir))
    assert (again.exit_code, again.stdout) == (0, b"ok\n"), again


@BOTH
def test_a_large_response_is_a_host_fault(guest_workdir, snapshot) -> None:
    """Guards existing behaviour: a response larger than the guest's free memory is a host fault."""
    run = _run()
    code = (
        "import _host\n"
        "try:\n    _host.call(b'x')\n    print('answered')\n"
        "except OSError as e:\n    print('OSError')\n"
        "print('after')\n"
    )
    done = run(
        ["-c", code],
        root=_root(guest_workdir),
        snapshot=snapshot,
        memory_bytes=256 << 20,
        host=lambda request: b"z" * (300 << 20),
    )
    assert (done.exit_code, done.stdout) == (0, b"OSError\nafter\n"), done


EXTRA_PREOPEN_PROBE = """
import gc, io, os
print(open('/data/x.txt').read(), open('/mark.txt').read())
try:
    open('/data/new', 'w')
    print('wrote')
except OSError:
    print('refused')
gc.unfreeze()
fds = set()
for o in gc.get_objects():
    if isinstance(o, io.IOBase) and not o.closed:
        try:
            fds.add(o.fileno())
        except (OSError, ValueError):
            pass  # in-memory streams have no descriptor
print(sorted(fds))
"""


@pytest.mark.parametrize("order", ["root first", "data first"])
def test_extra_preopens_work_on_the_snapshot(guest, guest_workdir, order) -> None:
    """Guards a change: the snapshot rebuilds wasi-libc's preopen table from the runtime's
    preopens, by name and in any order, as the plain reactor does."""
    data = Path(tempfile.mkdtemp(prefix="data-", dir=guest_workdir))
    (data / "x.txt").write_text("data")
    preopens = [("/data", data, False)]
    r = guest(
        "snapshot",
        ["-c", EXTRA_PREOPEN_PROBE],
        files={"/mark.txt": "root", "/data/x.txt": "planted in the root"},
        preopens=preopens,
        preopens_first=order == "data first",
    )
    assert r.exit_code == 0, r.describe()
    assert r.text.splitlines()[:3] == ["data root", "refused", "[0, 1, 2]"], r.text


@pytest.mark.parametrize("how", ["busy", "sleeping"])
def test_a_trapped_call_without_a_root_is_removed(guest_workdir, monkeypatch, how) -> None:
    """Guards a change: a call that ends in a trap still releases its store and removes its root,
    whether the guest was running or waiting (spec 010)."""
    run = _run()
    scratch = Path(tempfile.mkdtemp(prefix="trapped-", dir=guest_workdir))
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    loop = "    pass\n" if how == "busy" else "    __import__('time').sleep(10**6)\n"
    code = "open('/x', 'w').write('x')\nwhile True:\n" + loop
    fds = Path("/dev/fd")
    run(["-c", "pass"])  # the engine and module are loaded once per process; count after that
    before = len(list(fds.iterdir())) if fds.is_dir() else None
    done = _returns(lambda: run(["-c", code], deadline_s=0.2))
    assert done.trapped == "deadline", done
    assert list(scratch.iterdir()) == []
    if before is not None:  # a directory can be removed while open on POSIX; the store must close
        assert len(list(fds.iterdir())) == before, "the trapped call left host files open"


def test_a_planted_pdbrc_in_home_never_runs(guest_workdir) -> None:
    """Guards a change: HOME is fresh for every call, so a .pdbrc one call leaves there is not
    read by pdb in the next. (pdb also reads ./.pdbrc from the current directory, /, as native pdb
    does; the README lists that as not protected on a reused root.)"""
    run = _run()
    root = _root(guest_workdir)
    plant = (
        "import os\n"
        "open(os.path.join(os.environ['HOME'], '.pdbrc'), 'w').write("
        "\"import os; open('/MARKER-pdbrc', 'w').close()\\ncontinue\\n\")\n"
        "print(os.environ['HOME'].startswith('/tmp/.home-'))\n"
    )
    first = run(["-c", plant], root=root)
    assert (first.exit_code, first.stdout) == (0, b"True\n"), first
    probe = "import os, pdb\npdb.Pdb().set_trace()\nprint(os.path.exists('/MARKER-pdbrc'))\n"
    second = run(["-c", probe], root=root, stdin=b"c\n")
    assert second.exit_code == 0, second
    assert second.stdout.endswith(b"False\n"), second


def _returns(call):
    """Run a call that must end at its deadline in a daemon thread and return its result; fail if
    it has not returned after 120 s. A fail-safe against waiting forever (a sleeping guest without
    spec 010 waits 11.6 days), not a timing; a daemon thread cannot keep the test process alive."""
    import threading

    box: list = []
    worker = threading.Thread(target=lambda: box.append(call()), daemon=True)
    worker.start()
    worker.join(120)
    assert box, "the call did not return: its wait outlived the deadline"
    return box[0]


SLEEPERS = {
    "sleep": "import time\ntime.sleep(10**6)\nprint('woke')\n",
    "select": "import select\nselect.select([], [], [], 10**6)\nprint('woke')\n",
    "sleep(0) loop": "import time\nwhile True:\n    time.sleep(0)\n",
}


@pytest.mark.parametrize("how", list(SLEEPERS))
def test_a_sleeping_guest_ends_at_its_deadline(guest_workdir, how) -> None:
    """Guards a change: a guest that waits in poll_oneoff still ends at its deadline (spec 010).
    The call runs under the 120 s fail-safe of `_returns`."""
    run = _run()
    done = _returns(lambda: run(["-c", SLEEPERS[how]], root=_root(guest_workdir), deadline_s=0.2))
    assert (done.exit_code, done.trapped, done.stdout) == (None, "deadline", b""), done


DESCRIPTORS = r"""
import os, resource, sys, tempfile
scratch = sys.argv[1]
tempfile.tempdir = scratch
resource.setrlimit(resource.RLIMIT_NOFILE, (256, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
import wasi_python
guest = (
    "import os\nopen('/f', 'w').close()\nfs = []\n"
    "try:\n    while True: fs.append(os.open('/f', os.O_RDONLY))\n"
    "except OSError as e: print('refused', e.errno)\n"
)
done = wasi_python.run(["-c", guest], stdin=b"secret input")
left = [n for n in os.listdir(scratch) if not n.startswith("wasi-python-zip-")]
print(done.exit_code, done.stdout.decode().strip(), sorted(left))
"""


NO_RLIMIT = r"""
import os, sys, tempfile
scratch = sys.argv[1]
tempfile.tempdir = scratch
import wasi_python
done = wasi_python.run(["-c", "open('/f', 'w').close(); print('refused', 0)"], stdin=b"x")
left = [n for n in os.listdir(scratch) if not n.startswith("wasi-python-zip-")]
print(done.exit_code, done.stdout.decode().strip(), sorted(left))
"""


def test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise(guest_workdir) -> None:
    """Guards a change: a guest that opened files until the host refused made run raise
    OSError (Errno 24) and left its stdin behind (the 0.1.0a2 security review, F1). The store is
    now closed, releasing the guest's descriptors, before anything else is cleaned up. In a child
    process with a 256-descriptor limit, so the judge's own process is not starved. Windows has
    no RLIMIT_NOFILE to lower: there the child shows only that a call leaves nothing behind."""
    _run()
    scratch = Path(tempfile.mkdtemp(prefix="descriptors-", dir=guest_workdir))
    script = NO_RLIMIT if sys.platform == "win32" else DESCRIPTORS
    out = subprocess.run(
        [sys.executable, "-c", script, str(scratch)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr[-1500:]
    exit_code, refused, _errno, left = out.stdout.split("\n")[0].split(" ", 3)
    assert (exit_code, refused, left) == ("0", "refused", "[]"), out.stdout
    # The child's zip folder (spec 017) was filtered above while it lived; its exit removes it.
    assert list(scratch.iterdir()) == [], list(scratch.iterdir())


def test_a_stack_overflow_is_named() -> None:
    """Guards a change: a stack overflow was reported as wasmtime's heading, "error while
    executing at wasm backtrace:", which says nothing of why; a trap with a code is now named by
    it (the 0.1.0a2 security review, F7; spec 016)."""
    run = _run()
    code = "import sys\nsys.setrecursionlimit(10**8)\ndef f(n): return f(n + 1)\nf(0)"
    done = run(["-c", code])
    assert (done.exit_code, done.trapped) == (None, "stack overflow"), done


# Typed grants (spec 017). Every write-type call on a read-only grant is refused with EPERM
# (WASI errno 63), whatever route a program takes; memo §1's rows and the pre-build review's.
READ_ONLY = r"""
import os, shutil, tempfile
R, W = "/ro", "/rw"
def fd(path, flags=os.O_RDONLY):
    return os.open(path, flags)
ops = {
    "open w": lambda: open(R + "/f.txt", "w"),
    "open a": lambda: open(R + "/f.txt", "a"),
    "open r+": lambda: open(R + "/f.txt", "r+"),
    "O_WRONLY": lambda: fd(R + "/f.txt", os.O_WRONLY),
    "O_RDWR": lambda: fd(R + "/f.txt", os.O_RDWR),
    "O_WRONLY|O_APPEND": lambda: fd(R + "/f.txt", os.O_WRONLY | os.O_APPEND),
    "O_RDONLY|O_TRUNC": lambda: fd(R + "/f.txt", os.O_RDONLY | os.O_TRUNC),
    "create": lambda: open(R + "/new.txt", "x"),
    "O_CREAT|O_EXCL read-only": lambda: fd(R + "/new2", os.O_CREAT | os.O_EXCL | os.O_RDONLY),
    "truncate": lambda: os.truncate(R + "/f.txt", 0),
    "rename in place": lambda: os.rename(R + "/f.txt", R + "/g.txt"),
    "rename out": lambda: os.rename(R + "/f.txt", W + "/g.txt"),
    "rename in": lambda: os.rename(W + "/w.txt", R + "/w.txt"),
    "replace over": lambda: os.replace(W + "/w.txt", R + "/f.txt"),
    "move's copy in": lambda: shutil.move(W + "/w.txt", R + "/moved.txt"),
    "unlink": lambda: os.unlink(R + "/f.txt"),
    "rmdir": lambda: os.rmdir(R + "/sub"),
    "mkdir": lambda: os.mkdir(R + "/d"),
    "symlink": lambda: os.symlink("f.txt", R + "/l"),
    "link in place": lambda: os.link(R + "/f.txt", R + "/h"),
    "link out": lambda: os.link(R + "/f.txt", W + "/h"),
    "link in": lambda: os.link(W + "/w.txt", R + "/h"),
    "utime": lambda: os.utime(R + "/f.txt", (1, 1)),
    "utime no-follow": lambda: os.utime(R + "/f.txt", (1, 1), follow_symlinks=False),
    "utime of the grant": lambda: os.utime(R, (1, 1)),
    "mkdir by dir_fd": lambda: os.mkdir("d", dir_fd=fd(R)),
    "create by dir_fd": lambda: os.open("n", os.O_CREAT | os.O_WRONLY, dir_fd=fd(R)),
    "TemporaryFile": lambda: tempfile.TemporaryFile(dir=R),
    "ftruncate": lambda: os.ftruncate(fd(R + "/f.txt"), 0),
    "utime of a descriptor": lambda: os.utime(fd(R + "/f.txt"), (1, 1)),
    "write a read descriptor": lambda: os.write(fd(R + "/f.txt"), b"x"),
    "through a link in the grant": lambda: open(R + "/escape/x", "w"),
}
for name, op in ops.items():
    try:
        op()
        print(name, "DONE")
    except OSError as e:
        print(name, e.errno)
open(W + "/control.txt", "w").write("written")  # the writable grant is the control
print("control", open(W + "/control.txt").read())
"""


def _tree(folder: Path) -> list[tuple[str, int, bytes]]:
    return sorted(
        (str(p.relative_to(folder)), p.lstat().st_mode, b"" if p.is_dir() else p.read_bytes())
        for p in folder.rglob("*")
        if not p.is_symlink()
    )


@BOTH
def test_a_read_only_grant_refuses_every_write(guest_workdir, snapshot) -> None:
    """Guards a change (spec 017): a read-only grant refuses every write-type call with EPERM,
    and a write through a read descriptor with EBADF; the host files, their modes and times, and
    the folder a link inside the grant points at are unchanged."""
    from wasi_python import Grant

    run = _run()
    base = Path(tempfile.mkdtemp(prefix="grants-", dir=guest_workdir))
    ro, rw, outside = base / "ro", base / "rw", base / "outside"
    for d in (ro, ro / "sub", rw, outside):
        d.mkdir()
    (ro / "f.txt").write_text("original")
    (rw / "w.txt").write_text("w")
    if os.name == "posix":
        (ro / "escape").symlink_to(outside)
    before = _tree(ro)
    times = os.stat(ro / "f.txt").st_mtime_ns
    grants = [Grant(ro, "/ro"), Grant(rw, "/rw", writable=True)]
    done = run(["-c", READ_ONLY], root=False, grants=grants, snapshot=snapshot)
    assert done.exit_code == 0, done
    lines = dict(line.rsplit(" ", 1) for line in done.stdout.decode().splitlines())
    assert lines.pop("control") == "written"
    want = {name: "63" for name in lines}
    want["write a read descriptor"] = "8"  # EBADF: the descriptor has no write right
    if os.name != "posix":
        want["through a link in the grant"] = "44"  # ENOENT: no link was made on Windows
    assert lines == want, done.stdout.decode()
    assert _tree(ro) == before and os.stat(ro / "f.txt").st_mtime_ns == times
    assert list(outside.iterdir()) == []


ZIP_SHARED = r"""
import os, sys, tempfile
temp, root = sys.argv[1], sys.argv[2]
tempfile.tempdir = temp
import wasi_python

def folders():
    return sorted(n for n in os.listdir(temp) if n.startswith("wasi-python-zip-") and "." not in n)

guest = "\n".join([
    "import os",
    "name = os.listdir('/usr/local/lib')[0]",
    "try:",
    "    open('/usr/local/lib/' + name, 'r+b')",
    "except PermissionError:",
    "    print('refused')",
])
first = wasi_python.run(["-c", guest], root=root)
(folder,) = folders()
(name,) = os.listdir(os.path.join(temp, folder))
copy = os.path.join(temp, folder, name)
stamp = os.stat(copy)
second = wasi_python.run(["-c", "import json; print('ok')"])
copied_once = folders() == [folder] and os.stat(copy).st_ino == stamp.st_ino
with open(copy, "r+b") as f:  # the host changes the copy: the next call replaces it first
    f.seek(1000)
    f.write(b"X" * 64)
third = wasi_python.run(["-c", "import json, csv; print('ok')"])
with open(copy, "rb") as f, open(wasi_python.artifacts().stdlib_zip, "rb") as g:
    restored = f.read() == g.read()
import shutil
shutil.rmtree(os.path.join(temp, folder))  # a temporary-folder cleaner: the next call recovers
fourth = wasi_python.run(["-c", "import json; print('ok')"])
print(first.stdout.decode().strip(), second.stdout.decode().strip(), copied_once,
      third.stdout.decode().strip(), restored, fourth.stdout.decode().strip(),
      os.listdir(os.path.join(root, "usr", "local", "lib")))
"""


def test_the_zip_is_read_only_and_shared(guest_workdir) -> None:
    """Guards a change (spec 017; §4.15's alpha exception ends): the zip is no longer copied into
    a root but granted read-only from one folder per process, copied once, replaced if changed
    on disk, and removed when the process exits. In a child with its own temporary folder."""
    _run()
    base = Path(tempfile.mkdtemp(prefix="zip-", dir=guest_workdir))
    temp, root = base / "temp", base / "root"
    temp.mkdir()
    out = subprocess.run(
        [sys.executable, "-c", ZIP_SHARED, str(temp), str(root)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr[-1500:]
    assert out.stdout.split() == ["refused", "ok", "True", "ok", "True", "ok", "[]"], out.stdout
    assert list(temp.iterdir()) == [], list(temp.iterdir())


def test_a_bad_grant_is_refused_before_any_work(guest_workdir, tmp_path) -> None:
    """Guards a change (spec 017, Decision 4): each rule refuses before anything is made, a
    guest's link cannot redirect a later grant (memo §7a), and identities, not spellings, are
    compared."""
    from wasi_python import Grant

    run = _run()
    base = Path(tempfile.mkdtemp(prefix="bad-", dir=guest_workdir))
    cache = base / "cache"
    calls = []

    def host(frame: bytes) -> bytes:
        calls.append(frame)
        return b""

    def refused(error: type[Exception], match: str, **kw) -> None:
        with pytest.raises(error, match=match):
            run(["-c", "import _host; _host.call(b'x')"], host=host, cache_dir=cache, **kw)

    shared, secret = base / "shared", base / "secret"
    (shared / "data").mkdir(parents=True)
    secret.mkdir()
    (secret / "key.txt").write_text("HOST SECRET")
    # The runner makes the cache before it judges, so a root above it is refused.
    refused(ValueError, "holds the module cache", root=base.parent)
    refused(ValueError, "does not exist", root=base / "new" / ".." / "x")
    refused(ValueError, "holds the module cache", grants=[Grant(base, "/b", writable=True)])
    refused(ValueError, "holds the artifact set", root=paths.artifact_dir().parent)
    # The zip folder, or before this process made one, the temporary folder that will hold it.
    either = "holds the (runtime's stdlib folder|temporary folder)"
    refused(ValueError, either, root=tempfile.gettempdir())
    # Read-only too: the temporary folder holds every call's private folders and stdin.
    refused(ValueError, "holds the temporary folder", grants=[Grant(tempfile.gettempdir(), "/t")])
    # A root there too, after the temporary folder moved (the confirmation, C1): the folder the
    # runner's private folders go to now is never a guest's root.
    moved = base / "moved-temp"
    moved.mkdir()
    old, tempfile.tempdir = tempfile.tempdir, str(moved)
    try:
        refused(ValueError, "which holds every call's private folders", root=moved)
    finally:
        tempfile.tempdir = old
    import wasmtime

    own = Path(wasmtime.__file__).parent
    refused(ValueError, "wasmtime-py's own code", grants=[Grant(own, "/w", writable=True)])
    # The host's own interpreter too (spec 024, S2): the next host process runs its stdlib.
    import sysconfig

    stdlib = Path(sysconfig.get_paths()["stdlib"])
    refused(ValueError, "the host Python's own code", grants=[Grant(stdlib, "/w", writable=True)])
    scripts = Path(sysconfig.get_paths()["scripts"])  # bin/ or Scripts\ (the build review, 2)
    refused(ValueError, "the host Python's own code", grants=[Grant(scripts, "/w", writable=True)])
    done = run(["-c", "pass"], grants=[Grant(stdlib, "/w")], cache_dir=cache)
    assert done.exit_code == 0, done  # read-only stays allowed
    # A root still to be made above a cache still to be made: the cache is made first, so the
    # root is judged to hold it (the build review, finding 1); the root gets no folders of its own.
    fresh = base / "fresh"
    with pytest.raises(ValueError, match="holds the module cache"):
        run(["-c", "pass"], root=fresh / "a", cache_dir=fresh / "a" / "cache")
    assert sorted(p.name for p in (fresh / "a").iterdir()) == ["cache"]
    refused(
        ValueError,
        "read-only but inside",
        grants=[Grant(shared / "data", "/d"), Grant(shared, "/s", writable=True)],
    )
    refused(ValueError, "same guest path", grants=[Grant(shared, "/s"), Grant(secret, "/s")])
    refused(ValueError, "does not exist", grants=[Grant(base / "nothing", "/n")])
    refused(TypeError, "got True", root=True)
    refused(TypeError, "writable must be", grants=[Grant(shared, "/s", writable="no")])
    refused(TypeError, "not bytes", grants=[Grant(os.fsencode(shared), "/s")])
    cache.mkdir(exist_ok=True)  # the runner made it already, judging the first call
    inside = cache / "made-by-no-one"
    refused(ValueError, "is inside the module cache", root=inside)
    assert not inside.exists()  # a refused root makes no folder
    if sys.platform in ("darwin", "win32"):  # case-insensitive folders: another spelling
        refused(ValueError, "is inside the module cache", root=str(inside).swapcase())
    if os.name == "posix":
        # Memo §7a: call 1 may make links in its writable grant; call 2 names a path through one.
        plant = "import os\nos.rmdir('/s/data')\nos.symlink('../secret', '/s/data')\n"
        assert (
            run(["-c", plant], root=False, grants=[Grant(shared, "/s", writable=True)]).exit_code
            == 0
        )
        refused(ValueError, "passes through the link 'data'", grants=[Grant(shared / "data", "/d")])
    assert calls == []


def test_a_swapped_grant_is_refused(guest_workdir, monkeypatch) -> None:
    """Guards a change (spec 017, Decision 5): a middle folder of a grant's path swapped between
    the runner's walk and wasmtime's own open is caught by the identity check before the guest
    runs, and the door is never called. On Windows the walk holds every folder on the way, so the
    swap itself is refused and the call reads the folder that was granted."""
    from wasi_python import Grant, runner

    run = _run()
    base = Path(tempfile.mkdtemp(prefix="swap-", dir=guest_workdir))
    (base / "a" / "data").mkdir(parents=True)
    (base / "a" / "data" / "f").write_text("granted")
    (base / "evil" / "data").mkdir(parents=True)
    (base / "evil" / "data" / "f").write_text("SECRET")
    calls, swapped = [], []

    def host(frame: bytes) -> bytes:
        calls.append(frame)
        return b""

    def swap() -> None:
        try:
            os.rename(base / "a", base / "a-old")
        except PermissionError:
            swapped.append(False)  # Windows: the walk holds it
            return
        os.rename(base / "evil", base / "a")
        swapped.append(True)

    monkeypatch.setattr(runner, "_after_walk", swap)
    code = "import _host; _host.call(b'x'); print(open('/d/f').read())"
    grants = [Grant(base / "a" / "data", "/d")]
    if os.name == "posix":
        with pytest.raises(RuntimeError, match="grants\\[0\\] at /d changed between"):
            run(["-c", code], grants=grants, host=host)
        assert (swapped, calls) == ([True], [])
    else:
        done = run(["-c", code], grants=grants, host=host)
        assert (swapped, done.stdout) == ([False], b"granted\n"), done


@pytest.mark.parametrize("how", ["link", "rename"])
def test_a_swapped_root_is_never_prepared_by_path(guest_workdir, monkeypatch, how) -> None:
    """Guards a change (spec 024, the 0.1.0a3 security review's S1): a root swapped after its walk,
    as a guest of another call with a writable folder above it could do, changes nothing outside
    the folder that was checked. The runner prepares the root's usr/local/lib and tmp through
    the walked descriptor, so a link put in its place is never followed and a root moved away is
    never made again by path; the identity check then refuses the call. On Windows the walk
    holds every folder on the way, so the swap itself is refused."""
    from wasi_python import runner

    run = _run()
    base = Path(tempfile.mkdtemp(prefix="rootswap-", dir=guest_workdir))
    arena, outside = base / "arena", base / "outside"
    (arena / "sub").mkdir(parents=True)
    outside.mkdir()
    for name in ("usr", "tmp"):
        (outside / name).write_text("HOST FILE")
    swapped = []

    def swap() -> None:
        try:
            os.rename(arena / "sub", arena / "sub-old")
        except PermissionError:
            swapped.append(False)  # Windows: the walk holds it
            return
        if how == "link":
            os.symlink(outside, arena / "sub")
        swapped.append(True)

    monkeypatch.setattr(runner, "_after_walk", swap)
    if os.name == "posix":
        import wasmtime

        # A link: wasmtime opens where it points, and the identity check refuses. Moved away:
        # wasmtime finds nothing at the path, as for any grant removed after its walk.
        error = RuntimeError if how == "link" else wasmtime.WasmtimeError
        with pytest.raises(error, match="root changed" if how == "link" else "preopen"):
            run(["-c", "pass"], root=arena / "sub")
        assert swapped == [True]
        assert sorted(p.name for p in outside.iterdir()) == ["tmp", "usr"]
        assert all((outside / n).read_text() == "HOST FILE" for n in ("usr", "tmp"))
        if how == "rename":
            assert not (arena / "sub").exists()  # never made again by path
        # The preparation landed in the folder that was checked, now moved.
        assert (arena / "sub-old" / "usr" / "local" / "lib").is_dir()
    else:
        done = run(["-c", "pass"], root=arena / "sub")
        assert (swapped, done.exit_code) == ([False], 0), done
        assert all((outside / n).read_text() == "HOST FILE" for n in ("usr", "tmp"))
