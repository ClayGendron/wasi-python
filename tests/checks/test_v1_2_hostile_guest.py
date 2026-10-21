"""v1.2, the hostile guest: a program written to escape, persist, exhaust or crash is held by the
wall and by the runner's defaults. Each check names whether it guards a change the
safe-by-default work made or behaviour that already held."""

from __future__ import annotations

import functools
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from harness import files, needs, paths

pytestmark = pytest.mark.goal("v1.2")

BOTH = pytest.mark.parametrize("snapshot", [False, True], ids=["plain", "snapshot"])


def _run():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python.run


def _version() -> tuple[str, str]:
    """('3.15', '315') from MANIFEST's python line. Without an artifact set the need blocks the
    check, as every other check is blocked."""
    needs.need("artifact dir", "manifest")
    directory = paths.artifact_dir()
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
# path spelled normally, but still the guest's to write.
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
    Now the /usr/local/lib routes are refused outright (the stdlib's read-only grant),
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
    # code.
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
    """Guards a change: a private root (`root=True`) is fresh, and removed after the
    call. The runner's stdlib folder is made once per process, in the temporary folder: one call
    first makes it there, as any earlier check would, so the scratch folder judges the root alone
    (the check passes run alone)."""
    run = _run()
    run(["-c", "pass"])  # before the redirect: the runtime's once-per-process folder
    scratch = Path(tempfile.mkdtemp(prefix="rootless-", dir=guest_workdir))
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    write = "open('/left-behind', 'w').write('x'); print(sorted(__import__('os').listdir('/')))"
    first = run(["-c", write], root=True)
    assert (first.exit_code, first.stdout) == (0, b"['left-behind', 'tmp', 'usr']\n"), first
    assert list(scratch.iterdir()) == []
    second = run(["-c", "import os; print(os.path.exists('/left-behind'))"], root=True)
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
    from wasi_python import _call

    monkeypatch.setattr(_call, "MAX_RESPONSE", 1000)
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
    whether the guest was running or waiting. The warm-up call comes before the
    redirect, so the runner's once-per-process stdlib folder is not made in the scratch folder
    (the check passes run alone)."""
    run = _run()
    run(["-c", "pass"])  # the engine, module and stdlib folder, once per process; count after
    scratch = Path(tempfile.mkdtemp(prefix="trapped-", dir=guest_workdir))
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    loop = "    pass\n" if how == "busy" else "    __import__('time').sleep(10**6)\n"
    code = "open('/x', 'w').write('x')\nwhile True:\n" + loop
    fds = Path("/dev/fd")
    before = len(list(fds.iterdir())) if fds.is_dir() else None
    done = _returns(lambda: run(["-c", code], root=True, deadline_s=0.2))
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
    it has not returned after 120 s. A fail-safe against waiting forever (a sleeping guest whose
    deadline was not kept waited 11.6 days), not a timing; a daemon thread cannot keep the
    test process alive."""
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
    """Guards a change: a guest that waits in poll_oneoff still ends at its deadline.
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
done = wasi_python.run(["-c", guest], root=True, stdin=b"secret input")
left = [n for n in os.listdir(scratch) if not n.startswith("wasi-python-zip-")]
print(done.exit_code, done.stdout.decode().strip(), sorted(left))
"""


NO_RLIMIT = r"""
import os, sys, tempfile
scratch = sys.argv[1]
tempfile.tempdir = scratch
import wasi_python
done = wasi_python.run(
    ["-c", "open('/f', 'w').close(); print('refused', 0)"], root=True, stdin=b"x"
)
left = [n for n in os.listdir(scratch) if not n.startswith("wasi-python-zip-")]
print(done.exit_code, done.stdout.decode().strip(), sorted(left))
"""


def test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise(guest_workdir) -> None:
    """Guards a change: a guest that opened files until the host refused made run raise
    OSError (Errno 24) and left its stdin behind. The store is
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
    # The child's zip folder was filtered above while it lived; its exit removes it.
    assert list(scratch.iterdir()) == [], list(scratch.iterdir())


def test_a_stack_overflow_is_named() -> None:
    """Guards a change: a stack overflow was reported as wasmtime's heading, "error while
    executing at wasm backtrace:", which says nothing of why; a trap with a code is now named by
    it."""
    run = _run()
    code = "import sys\nsys.setrecursionlimit(10**8)\ndef f(n): return f(n + 1)\nf(0)"
    done = run(["-c", code])
    assert (done.exit_code, done.trapped) == (None, "stack overflow"), done


# Typed grants. Every write-type call on a read-only grant is refused with EPERM
# (WASI errno 63), whatever route a program takes: each write-type call, by each route measured.
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
    """Guards a change: a read-only grant refuses every write-type call with EPERM, on
    every system (wasmtime refuses a write open before the host sees the path, so the row
    through a link answers EPERM where no link was made too), and a write
    through a read descriptor with the host's errno, EBADF on Linux and macOS and EACCES on
    Windows; the host files, their modes and times, and the folder a link
    inside the grant points at are unchanged."""
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
    want["write a read descriptor"] = str(files.wrong_mode_errno(sys.platform))
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
# The zip in the folder's lib/, matplotlib's data beside it.
(name,) = os.listdir(os.path.join(temp, folder, "lib"))
copy = os.path.join(temp, folder, "lib", name)
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
    """Guards a change (the alphas' exception to safe defaults ends): the zip is no longer copied
    into a root but granted read-only from one folder per process, copied once, replaced if changed
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


MPL_DATA = r"""
import os, sys
data = "/usr/local/lib/python%s.zip/matplotlib/mpl-data" % sys.argv[1]
print("data", sorted(os.listdir(data)))
for what, attempt in [
    ("write", lambda: open(data + "/matplotlibrc", "w")),
    ("append", lambda: open(data + "/matplotlibrc", "a")),
    ("create", lambda: open(data + "/new.txt", "w")),
    ("mkdir", lambda: os.mkdir(data + "/new")),
    ("remove", lambda: os.remove(data + "/matplotlibrc")),
]:
    try:
        attempt()
        print(what, "allowed")
    except OSError as e:
        print(what, type(e).__name__, e.errno)
"""


@BOTH
def test_matplotlib_data_is_granted_read_only(snapshot) -> None:
    """Guards a change: the runner grants matplotlib's data, extracted from
    the zip's inner archive, read-only at the path matplotlib computes; every write, create, mkdir
    and remove there is refused with EPERM (63 in the guest)."""
    _, tag = _version()
    done = _run()(["-c", MPL_DATA, tag], snapshot=snapshot)
    assert done.exit_code == 0, done
    want = "data ['fonts', 'images', 'kpsewhich.lua', 'matplotlibrc', 'plot_directive', "
    want += "'sample_data', 'stylelib']\n"
    want += "".join(f"{w} PermissionError 63\n" for w in ("write", "append", "create", "mkdir"))
    want += "remove PermissionError 63\n"
    assert done.stdout.decode() == want, done.stdout.decode()


@BOTH
def test_usr_local_lib_holds_only_the_zip(snapshot) -> None:
    """Guards a change: the runner's private
    folder now holds the zip in lib/ and matplotlib's data beside it, and only lib/ is granted at
    /usr/local/lib, so the guest sees the zip there and nothing else."""
    _, tag = _version()
    done = _run()(["-c", "import os; print(os.listdir('/usr/local/lib'))"], snapshot=snapshot)
    assert done.exit_code == 0, done
    assert done.stdout.decode() == f"['python{tag}.zip']\n", done.stdout.decode()


def test_a_bad_grant_is_refused_before_any_work(guest_workdir, tmp_path) -> None:
    """Guards a change: each rule refuses before anything is made, a
    guest's link cannot redirect a later grant, and identities, not spellings, are
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
    assert not (base / "x").exists() and not (base / "new").exists()
    # The same rule on every system: `..` is taken on the folders walked,
    # so after a missing folder it is refused for a grant too, and after a file it is not a
    # folder; a root to be made inside the module cache by way of `..` is refused before anything.
    refused(ValueError, "does not exist", grants=[Grant(base / "new" / ".." / "shared", "/s")])
    (base / "a-file").write_text("x")
    refused(ValueError, "is not a folder", root=base / "a-file" / ".." / "y")
    refused(ValueError, "does not exist", root=cache / "new" / ".." / "made")
    assert not (cache / "made").exists() and not (base / "y").exists()
    refused(ValueError, "holds the module cache", grants=[Grant(base, "/b", writable=True)])
    refused(ValueError, "holds the artifact set", root=paths.artifact_dir().parent)
    # The zip folder, or before this process made one, the temporary folder that will hold it.
    either = "holds the (runtime's stdlib folder|temporary folder)"
    refused(ValueError, either, root=tempfile.gettempdir())
    # Read-only too: the temporary folder holds every call's private folders and stdin.
    refused(ValueError, "holds the temporary folder", grants=[Grant(tempfile.gettempdir(), "/t")])
    # A root there too, after the temporary folder moved: the folder the
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
    # The host's own interpreter too: the next host process runs its stdlib.
    import sysconfig

    stdlib = Path(sysconfig.get_paths()["stdlib"])
    refused(ValueError, "the host Python's own code", grants=[Grant(stdlib, "/w", writable=True)])
    scripts = Path(sysconfig.get_paths()["scripts"])  # bin/ or Scripts\
    refused(ValueError, "the host Python's own code", grants=[Grant(scripts, "/w", writable=True)])
    done = run(["-c", "pass"], grants=[Grant(stdlib, "/w")], cache_dir=cache)
    assert done.exit_code == 0, done  # read-only stays allowed
    # A root still to be made above a cache still to be made: the cache is made first, so the
    # root is judged to hold it; the root gets no folders of its own.
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
    refused(TypeError, "writable must be", grants=[Grant(shared, "/s", writable="no")])
    refused(TypeError, "not bytes", grants=[Grant(os.fsencode(shared), "/s")])
    cache.mkdir(exist_ok=True)  # the runner made it already, judging the first call
    inside = cache / "made-by-no-one"
    refused(ValueError, "is inside the module cache", root=inside)
    assert not inside.exists()  # a refused root makes no folder
    if sys.platform in ("darwin", "win32"):  # case-insensitive folders: another spelling
        refused(ValueError, "is inside the module cache", root=str(inside).swapcase())
    if os.name == "posix":
        # Call 1 may make links in its writable grant; call 2 names a path through one.
        plant = "import os\nos.rmdir('/s/data')\nos.symlink('../secret', '/s/data')\n"
        assert (
            run(["-c", plant], root=False, grants=[Grant(shared, "/s", writable=True)]).exit_code
            == 0
        )
        refused(ValueError, "passes through the link 'data'", grants=[Grant(shared / "data", "/d")])
    assert calls == []


def test_a_swapped_grant_is_refused(guest_workdir, monkeypatch) -> None:
    """Guards a change: a middle folder of a grant's path swapped between
    the runner's walk and wasmtime's own open is caught by the identity check before the guest
    runs, and the door is never called. On Windows the walk holds every folder on the way, so the
    swap itself is refused and the call reads the folder that was granted."""
    from wasi_python import Grant
    from wasi_python._process import process

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

    monkeypatch.setattr(process().observers, "after_walk", swap)
    code = "import _host; _host.call(b'x'); print(open('/d/f').read())"
    grants = [Grant(base / "a" / "data", "/d")]
    if os.name == "posix":
        with pytest.raises(RuntimeError, match="grants\\[0\\] at /d changed between"):
            run(["-c", code], grants=grants, host=host)
        assert (swapped, calls) == ([True], [])
    else:
        done = run(["-c", code], grants=grants, host=host)
        assert (swapped, done.stdout) == ([False], b"granted\n"), done


NOTHING_WRITABLE = """
import os
out = []
try:
    os.listdir('/')
    out.append('root listed')
except OSError:
    out.append('no root')
for path in ('/x', '/tmp/x', '/usr/local/lib/x', 'x'):
    try:
        open(path, 'w').close()
        out.append('wrote ' + path)
    except OSError:
        out.append('refused ' + path)
out.append('HOME' if 'HOME' in os.environ else 'no HOME')
import numpy, pandas
out.append(str(int(pandas.Series(numpy.arange(4)).sum())))
print(' '.join(out))
"""


@pytest.mark.parametrize("snapshot", [True, False], ids=["snapshot", "plain"])
def test_nothing_is_writable_by_default(snapshot) -> None:
    """Guards a change: a call given no root
    and no grants has nothing writable, no `/` and no HOME, and still imports and computes."""
    run = _run()
    done = run(["-c", NOTHING_WRITABLE], snapshot=snapshot)
    assert done.exit_code == 0, done.stderr[-1500:]
    assert done.stdout.decode().split() == [
        "no",
        "root",
        "refused",
        "/x",
        "refused",
        "/tmp/x",
        "refused",
        "/usr/local/lib/x",
        "refused",
        "x",
        "no",
        "HOME",
        "6",
    ], done.stdout
    # The private root is asked for by name.
    asked = run(["-c", "open('/x', 'w').write('ok'); print(open('/x').read())"], root=True)
    assert (asked.exit_code, asked.stdout) == (0, b"ok\n"), asked


@pytest.mark.parametrize("how", ["link", "rename"])
def test_a_swapped_root_is_never_prepared_by_path(guest_workdir, monkeypatch, how) -> None:
    """Guards a change: a root swapped after its walk,
    as a guest of another call with a writable folder above it could do, changes nothing outside
    the folder that was checked. The runner prepares the root's usr/local/lib and tmp through
    the walked descriptor, so a link put in its place is never followed and a root moved away is
    never made again by path; the identity check then refuses the call. On Windows the walk
    holds every folder on the way, so the swap itself is refused."""
    from wasi_python._process import process

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

    monkeypatch.setattr(process().observers, "after_walk", swap)
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


# Read-only mounts: a provider is the embedder's code, and nothing it does may make
# run() raise or reach wasmtime-py; a guest cannot spend host descriptors through a mount.


class _Faulty:
    """A provider whose one `method` misbehaves as `how` says; the others answer a small tree."""

    def __init__(self, method: str, how):
        self.method, self.how = method, how
        self.calls = {"stat": 0, "list": 0, "read": 0}

    def _answer(self, method, path, normal):
        self.calls[method] += 1
        return self.how(path) if method == self.method else normal

    def stat(self, path):
        from wasi_python import Stat

        return self._answer("stat", path, Stat("dir" if path == "/" else "file", 1))

    def list(self, path):
        return self._answer("list", path, [("x", "file")])

    def read(self, path):
        return self._answer("read", path, b"x")


def _raises(path):
    raise ValueError("the provider broke\nsecond line")


async def _coroutine():
    return b"x"


class _BadIterator:
    def __iter__(self):
        return self

    def __next__(self):
        raise RuntimeError("the iterator broke")


class _BadBuffer(bytearray):
    def __buffer__(self, flags):
        raise BufferError("no buffer today")


class _Masked:
    """An answer whose `__class__` raises: isinstance() runs it (CPython looks `__class__` up
    when the type itself does not match)."""

    @property
    def __class__(self):  # noqa: F811
        raise RuntimeError("no class")


class _FakeErrno:
    """Passes `isinstance(x, Errno)` through its `__class__` without being one; its own `__int__`
    would make the answer a success with no value (0) or an errno outside the set (2**32 + 8,
    which an i32 truncates to EBADF)."""

    def __init__(self, value: int) -> None:
        self.value = value

    @property
    def __class__(self):  # noqa: F811
        from wasi_python import Errno

        return Errno

    def __int__(self) -> int:
        return self.value

    __index__ = __int__

    def __eq__(self, other: object) -> bool:
        return False

    __hash__ = object.__hash__


class _NamedByMetaclass(type):
    @property
    def __name__(cls):  # noqa: F811
        raise ValueError("metaclass name")


class _Nameless(Exception, metaclass=_NamedByMetaclass):
    pass


class _HostileText(str):
    def strip(self, *args):
        raise ValueError("strip")


class _TextException(Exception):
    def __str__(self):
        return _HostileText("text")


def _raising(error):
    def answer(path):
        raise error

    return answer


def _huge(path):
    import mmap

    return memoryview(mmap.mmap(-1, 512 << 20))  # untouched pages: nothing is committed


FAULTS = {
    "raises": ("read", _raises, "ValueError: the provider broke"),
    "None": ("read", lambda p: None, "bad answer: NoneType"),
    "text": ("read", lambda p: "text", "bad answer: str"),
    "object": ("stat", lambda p: object(), "bad answer: object"),
    "int": ("read", lambda p: 44, "bad answer: int"),
    "coroutine": ("read", lambda p: _coroutine(), "bad answer: coroutine"),
    "iterator raises": ("list", lambda p: _BadIterator(), "RuntimeError: the iterator broke"),
    "buffer raises": ("read", lambda p: _BadBuffer(b"x"), "BufferError: no buffer today"),
    "slash": ("list", lambda p: [("a/b", "file")], "bad answer: list"),
    "NUL": ("list", lambda p: [("a\0", "file")], "bad answer: list"),
    "dotdot": ("list", lambda p: [("..", "dir")], "bad answer: list"),
    "surrogate": ("list", lambda p: [("\udcff", "file")], "bad answer: list"),
    "256 bytes": ("list", lambda p: [("x" * 256, "file")], "bad answer: list"),
    "duplicate": ("list", lambda p: [("x", "file"), ("x", "dir")], "bad answer: list"),
    "link": ("list", lambda p: [("x", "link")], "bad answer: list"),
    "not a pair": ("list", lambda p: [("x",)], "bad answer: list"),
    "size True": ("stat", lambda p: __import__("wasi_python").Stat("file", True), "bad answer"),
    "size negative": ("stat", lambda p: __import__("wasi_python").Stat("file", -1), "bad answer"),
    "kind": ("stat", lambda p: __import__("wasi_python").Stat("fifo"), "bad answer: Stat"),
    "root a file": ("stat", lambda p: __import__("wasi_python").Stat("file"), "bad answer: Stat"),
    "class raises (read)": ("read", lambda p: _Masked(), "bad answer: _Masked"),
    "class raises (stat)": ("stat", lambda p: _Masked(), "bad answer: _Masked"),
    "class raises (list)": ("list", lambda p: _Masked(), "bad answer: _Masked"),
    "item class raises": ("list", lambda p: [_Masked()], "bad answer: list"),
    "a fake Errno of 0": ("list", lambda p: _FakeErrno(0), "bad answer: _FakeErrno"),
    "a fake Errno past i32": ("stat", lambda p: _FakeErrno(2**32 + 8), "bad answer: _FakeErrno"),
    "an exception whose type's name raises": ("read", _raising(_Nameless("x")), "_Nameless: x"),
    "an exception whose text is hostile": ("read", _raising(_TextException()), "_TextException"),
    "past the bound": ("read", _huge, None),
}
FAULT_GUEST = r"""
import json, os, sys
out = {}
for i, (name, method) in enumerate(json.loads(sys.argv[1])):
    base = f"/c{i}"
    try:
        if name == "root a file":
            os.stat(base)
        elif method == "stat":
            os.stat(base + "/x")
        elif method == "list":
            os.listdir(base)
        else:
            open(base + "/x", "rb").read()
        out[name] = "answered"
    except OSError as e:
        out[name] = e.errno
print(json.dumps(out))
"""


@BOTH
def test_a_provider_fault_never_escapes(snapshot) -> None:
    """Guards a change: a provider that raises, answers outside its
    protocol (a wrong type, an awaitable, a listing whose iterator or a buffer whose export
    raises, a name the guest could misread, a bool for a size, a file for /) gives the guest EIO
    and a fault in the record, and no more; one that answers more than the staging bound gives
    EFBIG and no fault. The guest exits 0, run() raises nothing, and no coroutine is left to
    warn that it was never awaited."""
    import gc
    import json
    import warnings

    from wasi_python import Mount

    run = _run()
    names = list(FAULTS)
    providers = [_Faulty(FAULTS[n][0], FAULTS[n][1]) for n in names]
    mounts = [Mount(p, f"/c{i}") for i, p in enumerate(providers)]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        done = run(
            ["-c", FAULT_GUEST, json.dumps([[n, FAULTS[n][0]] for n in names])],
            mounts=mounts,
            memory_bytes=256 << 20,
            snapshot=snapshot,
        )
        gc.collect()
    assert (done.exit_code, done.trapped, done.stderr) == (0, None, b""), done
    answers = json.loads(done.stdout)
    assert answers == {n: (22 if n == "past the bound" else 29) for n in names}, answers
    assert done.files is not None
    faults = [(f.method, f.path, f.error) for f in done.files.faults]
    want = [n for n in names if FAULTS[n][2] is not None]
    assert len(faults) == len(want), faults
    for (method, path, error), name in zip(faults, want, strict=True):
        assert method == FAULTS[name][0] and error.startswith(FAULTS[name][2]), (name, error)
        assert path == ("/x" if method != "list" and name != "root a file" else "/"), path
        assert "\n" not in error and len(error) <= 200
    assert not [w for w in caught if "never awaited" in str(w.message)], caught


def test_a_providers_base_exception_is_raised_from_run() -> None:
    """Guards a change: a provider's BaseException that is not an
    Exception is recorded as the call's stop and raised from run, as a door host's is."""
    from wasi_python import Mount

    def stops(path):
        raise SystemExit(7)

    run = _run()
    with pytest.raises(SystemExit):
        run(["-c", "open('/w/x').read()"], mounts=[Mount(_Faulty("read", stops), "/w")])


_RAN: list[str] = []


class _LyingErrno(OSError):
    """Its slot holds what the constructor got; its `errno` property claims ENOENT."""

    @property
    def errno(self):  # type: ignore[override]
        import errno as codes

        _RAN.append("errno property")
        return codes.ENOENT


class _MaskedOSError(OSError):
    @property
    def __class__(self):  # type: ignore[override]
        _RAN.append("__class__ (OSError)")
        return FileNotFoundError


class _MaskedException(Exception):
    @property
    def __class__(self):  # type: ignore[override]
        _RAN.append("__class__ (not an OSError)")
        return FileNotFoundError


class _EqualInt(int):
    """Claims to be ENOENT to any comparison or hash."""

    def __eq__(self, other):
        return True

    def __hash__(self):
        import errno

        return hash(errno.ENOENT)


def _plain(value):
    e = OSError("x")
    e.errno = value
    return e


def _unmapped_cases():
    """(name, a function making the exception, the guest's errno, whether a fault is kept)."""
    import errno

    return [
        ("InterruptedError(EINTR)", lambda: InterruptedError(errno.EINTR, "x"), 29, True),
        ("BlockingIOError(EAGAIN)", lambda: BlockingIOError(errno.EAGAIN, "x"), 29, True),
        ("OSError(EWOULDBLOCK)", lambda: OSError(errno.EWOULDBLOCK, "x"), 29, True),
        ("OSError(EBADF)", lambda: OSError(errno.EBADF, "x"), 29, True),
        ("OSError(EFAULT)", lambda: OSError(errno.EFAULT, "x"), 29, True),
        ("OSError(ELOOP)", lambda: OSError(errno.ELOOP, "x"), 29, True),
        ("OSError(0)", lambda: OSError(0, "x"), 29, True),
        ("OSError(99999)", lambda: OSError(99999, "x"), 29, True),
        ("errno 2**70", lambda: _plain(2**70), 29, True),
        ("errno True", lambda: _plain(True), 29, True),
        (
            "errno an int subclass equal to ENOENT",
            lambda: _plain(_EqualInt(errno.ENOENT)),
            29,
            True,
        ),
        ("an errno property over a slot of EINTR", lambda: _LyingErrno(errno.EINTR, "x"), 29, True),
        ("an OSError whose __class__ lies", lambda: _MaskedOSError("x"), 29, True),
        ("an Exception whose __class__ lies", lambda: _MaskedException("x"), 29, True),
        ("errno set to ENOENT after construction", lambda: _plain(errno.ENOENT), 44, False),
        ("ValueError", lambda: ValueError("x"), 29, True),
    ]


UNMAPPED_GUEST = r"""
import json, sys
out = {}
for i, name in enumerate(json.loads(sys.argv[1])):
    try:
        with open(f"/c{i}/x", "rb") as f:
            f.read()
        out[name] = "answered"
    except OSError as e:
        out[name] = e.errno
print(json.dumps(out))
"""


def test_an_oserror_that_names_no_member_stays_a_fault() -> None:
    """Guards a change: an `OSError` whose errno names no member of the
    closed set (EINTR, EAGAIN, EBADF, EFAULT, an unknown number, a bool, an int subclass, a slot
    a property lies about) and any other exception stay EIO and a fault, one provider call each;
    an errno set after construction is read from the slot; the boundary never runs the `errno`
    property or a `__class__` property. Bounded by `max_file_calls`, never by a clock."""
    import json

    from wasi_python import Mount

    run = _run()
    cases = _unmapped_cases()

    def raising(make):
        def how(path):
            raise make()

        return how

    providers = [_Faulty("read", raising(make)) for _, make, _, _ in cases]
    _RAN.clear()
    done = run(
        ["-c", UNMAPPED_GUEST, json.dumps([name for name, _, _, _ in cases])],
        mounts=[Mount(p, f"/c{i}") for i, p in enumerate(providers)],
        max_file_calls=20,
    )
    assert (done.exit_code, done.trapped) == (0, None), done
    answers = json.loads(done.stdout)
    assert answers == {name: want for name, _, want, _ in cases}, answers
    assert [p.calls["read"] for p in providers] == [1] * len(cases)
    assert done.files is not None
    faults = done.files.faults
    assert len(faults) == sum(kept for *_, kept in cases), faults
    assert all(f.method == "read" and "\n" not in f.error and len(f.error) <= 200 for f in faults)
    assert _RAN == [], _RAN


MOUNT_DESCRIPTORS = r"""
import os, resource, sys, tempfile
scratch = sys.argv[1]
tempfile.tempdir = scratch
resource.setrlimit(resource.RLIMIT_NOFILE, (256, resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
import wasi_python
from wasi_python import Errno, Mount, Stat

seen = []


class Files:
    reads = 0

    def stat(self, path):
        return Stat("dir" if path == "/" else "file", 1)

    def list(self, path):
        return [("a.txt", "file")]

    def read(self, path):
        Files.reads += 1
        if Files.reads in (1, 1024):  # the call's placeholder, seen from the embedder's side
            folders = [n for n in os.listdir(scratch) if n.startswith("wasi-python-")]
            seen.append([sorted(os.listdir(os.path.join(scratch, n, "mount")))
                         for n in folders if os.path.isdir(os.path.join(scratch, n, "mount"))])
        return b"x"


guest = (
    "import os\nfs = []\n"
    "try:\n    for i in range(1025): fs.append(os.open('/work/a.txt', os.O_RDONLY))\n"
    "    print('opened', len(fs))\n"
    "except OSError as e:\n    print('refused', e.errno, len(fs), min(fs) >= 2**30)\n"
)
done = wasi_python.run(["-c", guest], mounts=[Mount(Files(), "/work")], snapshot=sys.argv[2] == "1")
left = [n for n in os.listdir(scratch) if not n.startswith("wasi-python-zip-")]
print(done.exit_code, done.stdout.decode().strip(), Files.reads, seen, left)
"""


@BOTH
def test_mount_descriptors_are_bounded(guest_workdir, snapshot) -> None:
    """Guards a change: in a child whose soft descriptor limit is 256,
    a guest that opens 1,025 provider files gets EMFILE on the last: provider numbers cost no
    host handle, so the runner's own bound, MAX_MOUNT_FILES, holds at any host limit. The run
    exits 0 after 1,024 reads; the placeholder is empty during the run and gone after it."""
    _run()
    needs.need("descriptor limit")  # Windows has no RLIMIT_NOFILE to lower
    scratch = Path(tempfile.mkdtemp(prefix="mount-fds-", dir=guest_workdir))
    out = subprocess.run(
        [sys.executable, "-c", MOUNT_DESCRIPTORS, str(scratch), "1" if snapshot else "0"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr[-1500:]
    assert out.stdout.strip() == "0 refused 33 1024 True 1024 [[[]], [[]]] []", out.stdout
    assert list(scratch.iterdir()) == []


# The sandbox holds on wasmtime 49.0.0. wasmtime 49.0.0's path_rename puts a source's
# trailing slash back before renameat, and on a kernel that follows a symbolic link named with a
# trailing slash there (macOS, FreeBSD) a guest with a writable place moves a folder from outside
# its sandbox in (GHSA-m9f7-9w4p-gv38, fixed in wasmtime 49.0.3). The runner carries 49.0.3's rule.

ESCAPE_GUEST = r"""
import errno, json, os, sys
top = sys.argv[1]
out = {}
def tried(fn):
    try:
        fn()
        return "ok"
    except OSError as e:
        return [type(e).__name__, errno.errorcode.get(e.errno, str(e.errno))]
out["symlink"] = tried(lambda: os.symlink("../outside", top + "/up"))
out["rename"] = tried(lambda: os.rename(top + "/up/", top + "/stolen"))
out["stolen"] = os.path.lexists(top + "/stolen")
out["up"] = os.path.islink(top + "/up")
out["read"] = tried(lambda: open(top + "/stolen/canary.txt").read())
print(json.dumps(out))
"""

ESCAPE = r"""
import sys, tempfile
temp, where, grant, guest = sys.argv[1:5]
tempfile.tempdir = temp  # the private root is made here, beside the planted folder
import wasi_python
from wasi_python import Grant
if where == "grant":
    done = wasi_python.run(["-c", guest, "/work"], grants=[Grant(grant, "/work", writable=True)])
else:
    done = wasi_python.run(["-c", guest, ""], root=True)
print(done.exit_code, done.trapped)
print(done.stdout.decode().strip())
"""


def _follows_slash_links(base: Path) -> str:
    """Whether this kernel's rename follows a symbolic link named with a trailing slash: only
    reported, never a condition of a check."""
    probe = base / "probe"
    (probe / "target").mkdir(parents=True)
    try:
        os.symlink("target", probe / "link")
    except OSError as e:
        return f"this host cannot make a symbolic link ({e.errno})"
    try:
        os.rename(str(probe / "link") + "/", probe / "moved")
    except OSError as e:
        return f"this kernel refuses a trailing-slash link in rename (errno {e.errno})"
    if (probe / "moved").is_dir() and not (probe / "target").exists():
        return "this kernel follows a trailing-slash link in rename"
    return "this kernel renames the link itself"


@pytest.mark.parametrize("where", ["grant", "root"])
def test_a_trailing_slash_symlink_rename_cannot_escape(tmp_path, where) -> None:
    """Guards a change: a guest with a writable place makes a link that
    climbs out, then renames it with a trailing slash. The rename is refused with ENOTDIR, the
    folder outside every grant and its canary are unchanged, and nothing named `stolen` exists.
    In a child whose temporary folder is this check's own, so the private root's parent is too."""
    _run()
    temp, grant = tmp_path / "temp", tmp_path / "grant"
    temp.mkdir()
    grant.mkdir()
    outside = (tmp_path if where == "grant" else temp) / "outside"
    outside.mkdir()
    (outside / "canary.txt").write_text("CANARY")
    kernel = _follows_slash_links(tmp_path)
    out = subprocess.run(
        [sys.executable, "-c", ESCAPE, str(temp), where, str(grant), ESCAPE_GUEST],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr[-1500:]
    status, line = out.stdout.strip().splitlines()
    assert status == "0 None", (kernel, out.stdout)
    import json

    seen = json.loads(line)
    assert (seen["stolen"], seen["read"][0]) == (False, "FileNotFoundError"), (kernel, seen)
    if seen["symlink"] == "ok":  # a host that cannot make links never had the escape
        assert seen["up"] is True, (kernel, seen)
        assert seen["rename"] == ["NotADirectoryError", "ENOTDIR"], (kernel, seen)
    assert sorted(p.name for p in outside.iterdir()) == ["canary.txt"], kernel
    assert (outside / "canary.txt").read_text() == "CANARY", kernel
    assert not (grant / "stolen").exists() and not (tmp_path / "stolen").exists(), kernel
    assert sorted(p.name for p in temp.iterdir()) == (["outside"] if where == "root" else [])


RULE_GUEST = r"""
import errno, json, os
W = "/work"
def mv(a, b):
    try:
        os.rename(W + "/" + a, W + "/" + b)
        return "ok"
    except OSError as e:
        return errno.errorcode.get(e.errno, str(e.errno))
out = {}
long = "./" * 2100 + "s/"  # 4,202 bytes, past the 4,096 a slash-named source is read to
for a, b in [("f/", "x"), ("s/", "x"), ("missing/", "x"), ("f", "x/"), ("s", "x/"), (long, "x")]:
    out[("./.../s/" if a == long else a) + " -> " + b] = mv(a, b)
out["in place"] = [
    os.path.isdir(W + "/d") and not os.path.islink(W + "/d"),
    os.path.islink(W + "/s") and os.readlink(W + "/s") == "d",
    os.path.isfile(W + "/f"),
    os.path.lexists(W + "/x"),
]
for a, b in [("d/", "d2"), ("d2", "d"), ("d", "d4/"), ("d4/", "d"), ("d", "d3")]:
    out[a + " -> " + b] = mv(a, b)
out["after"] = sorted(os.listdir(W))
print(json.dumps(out))
"""


def test_a_trailing_slash_rename_rule(tmp_path) -> None:
    """Guards a change, on every host: in a writable grant with a folder
    `d`, a file `f` and a link `s` to `d`, a trailing slash on either path of a rename needs a
    source that is a folder, judged without following the source's own link. A slash-named
    file or link, as source or as target, is refused with ENOTDIR; a missing one answers its
    stat's ENOENT; an over-long slash-named source is refused unread (ENAMETOOLONG) and never
    passed on; `d` and `s` stay in place; a folder renames with or without slashes."""
    run = _run()
    from wasi_python import Grant

    grant = tmp_path / "grant"
    (grant / "d").mkdir(parents=True)
    (grant / "d" / "in.txt").write_text("in")
    (grant / "f").write_text("f")
    try:
        os.symlink("d", grant / "s")
    except OSError as e:
        pytest.skip(f"this host cannot make a symbolic link ({e.errno})")
    done = run(["-c", RULE_GUEST], grants=[Grant(grant, "/work", writable=True)])
    assert done.exit_code == 0, done
    import json

    assert json.loads(done.stdout) == {
        "f/ -> x": "ENOTDIR",
        "s/ -> x": "ENOTDIR",
        "missing/ -> x": "ENOENT",
        "f -> x/": "ENOTDIR",
        "s -> x/": "ENOTDIR",
        "./.../s/ -> x": "ENAMETOOLONG",
        "in place": [True, True, True, False],
        "d/ -> d2": "ok",
        "d2 -> d": "ok",
        "d -> d4/": "ok",
        "d4/ -> d": "ok",
        "d -> d3": "ok",
        "after": ["d3", "f", "s"],
    }, _follows_slash_links(tmp_path)
    assert (grant / "d3" / "in.txt").read_text() == "in"
    assert os.readlink(grant / "s") == "d" and (grant / "f").read_text() == "f"


# Writable mounts: a writable mount at / cannot reach the runtime's files, a
# read-only grant inside it, another mount, or the host.

WRITABLE_ROOT = r"""
import json, os, sys, tempfile
scratch = sys.argv[1]
tempfile.tempdir = scratch
sys.path.insert(0, sys.argv[3])
import wasi_python
from harness.files import MemoryProvider
from wasi_python import Grant, Mount

root, out_mount = MemoryProvider(), MemoryProvider({})
data = os.path.join(scratch, "data")
os.mkdir(data)
looked = []

def host(frame):
    if frame == b"look":  # the call's placeholder, seen from the embedder's side
        folders = [n for n in os.listdir(scratch) if n.startswith("wasi-python-")]
        looked.append([sorted(os.listdir(os.path.join(scratch, n, "mount")))
                       for n in folders if os.path.isdir(os.path.join(scratch, n, "mount"))])
        return b""
    return str(root.total() + out_mount.total()).encode()

guest = '''
import _host, json, os, numpy, pandas
out = {}
def row(name, fn):
    before = int(_host.call(b"total"))
    try:
        fn()
        value = "ok"
    except OSError as e:
        value = e.errno
    out[name] = [value, int(_host.call(b"total")) - before]
for base in ("/usr/local/lib/x", "/usr/./local/lib/x", "/data/x"):
    row("write " + base, lambda b=base: open(b, "w"))
    row("mkdir " + base, lambda b=base: os.mkdir(b))
    row("remove " + base, lambda b=base: os.remove(b))
    row("rename into " + base, lambda b=base: os.rename("/a.txt", b))
row("rmdir /usr", lambda: os.rmdir("/usr"))
row("rmdir /usr/local", lambda: os.rmdir("/usr/local"))
row("rename /usr", lambda: os.rename("/usr", "/usr2"))
row("rename /work", lambda: os.rename("/work", "/work2"))
row("rename to the nested writable mount", lambda: os.rename("/a.txt", "/work/out/a.txt"))
row("rename to the read-only grant", lambda: os.rename("/a.txt", "/data/a.txt"))
row("rename into itself", lambda: os.rename("/d", "/d/e"))
with open("/fine.txt", "w") as f:
    f.write("fine")
_host.call(b"look")
out["imports"] = [numpy.__name__, pandas.__name__]
print(json.dumps(out))
'''
mounts = [Mount(root, "/", writable=True), Mount(out_mount, "/work/out", writable=True)]
done = wasi_python.run(["-c", guest], mounts=mounts, grants=[Grant(data, "/data")], host=host,
                       snapshot=sys.argv[2] == "1")
left = [n for n in os.listdir(scratch) if not n.startswith("wasi-python-zip-") and n != "data"]
print(json.dumps([done.exit_code, done.stderr.decode()[-500:], json.loads(done.stdout or "{}"),
                  looked, left, root.tree.get("/fine.txt", b"").decode(), os.listdir(data)]))
"""


@BOTH
def test_a_writable_root_mount_keeps_the_runtime_and_other_grants(guest_workdir, snapshot) -> None:
    """Guards a change (guards: the EBUSY rule, the rule across, the
    dst-inside-src rule): a writable mount at / with a read-only grant at /data and a writable
    mount at /work/out: writing, making, removing or renaming into the zip's folder (spelled
    plainly or past wasi-libc) or the grant is EPERM with no provider call; an rmdir or rename
    above a nested preopen is EBUSY; a rename to the nested writable mount is EXDEV and to the
    grant EPERM; a rename into its own subfolder is EINVAL, all with no call. numpy and pandas
    import; the placeholder is empty while the guest writes and gone after."""
    _run()
    scratch = Path(tempfile.mkdtemp(prefix="writable-root-", dir=guest_workdir))
    tests = str(paths.REPO / "tests")
    out = subprocess.run(
        [sys.executable, "-c", WRITABLE_ROOT, str(scratch), "1" if snapshot else "0", tests],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr[-1500:]
    import json

    exit_code, stderr, rows, looked, left, fine, data = json.loads(out.stdout)
    assert (exit_code, stderr) == (0, ""), stderr
    imports = rows.pop("imports")
    want = {}
    for base in ("/usr/local/lib/x", "/usr/./local/lib/x", "/data/x"):
        for verb in ("write", "mkdir", "remove", "rename into"):
            want[f"{verb} {base}"] = [63, 0]
    want |= {
        "rmdir /usr": [10, 0],
        "rmdir /usr/local": [10, 0],
        "rename /usr": [10, 0],
        "rename /work": [10, 0],
        "rename to the nested writable mount": [75, 0],
        "rename to the read-only grant": [63, 0],
        "rename into itself": [28, 0],
    }
    assert rows == want, {k: (rows.get(k), v) for k, v in want.items() if rows.get(k) != v}
    assert imports == ["numpy", "pandas"]
    assert (looked, left, fine, data) == ([[[]]], [], "fine", [])


DIRTY = (
    "import _host, os\n"
    "fds = [os.open(f'/w/{n}.txt', os.O_WRONLY | os.O_CREAT) for n in (1, 2)]\n"
    "for fd in fds:\n"
    "    os.write(fd, b'dirty')\n"
)


def test_a_call_that_raises_writes_nothing_back() -> None:
    """Guards a change (guard: the skip when the call raises): when the
    call will raise rather than return, the ending's walk makes no write-back: a door host's
    KeyboardInterrupt, and a provider's KeyboardInterrupt in the walk's first write (the second
    file is never written). The Ctrl-C and exit-hook rows are the next check's, in children."""
    from harness.files import MemoryProvider
    from wasi_python import Mount

    run = _run()
    provider = MemoryProvider({})

    def interrupts(frame):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run(
            ["-c", DIRTY + "_host.call(b'stop')\n"],
            mounts=[Mount(provider, "/w", writable=True)],
            host=interrupts,
        )
    assert provider.writes() == [b"", b""]  # the creates at open, and no content
    provider = MemoryProvider({})

    def first(path, data):
        if data:
            raise KeyboardInterrupt

    provider.answers[("write", "/1.txt")] = first
    with pytest.raises(KeyboardInterrupt):
        run(["-c", DIRTY], mounts=[Mount(provider, "/w", writable=True)])
    assert provider.writes("/1.txt") == [b"", b"dirty"] and provider.writes("/2.txt") == [b""]


STOPPED = r"""
import asyncio, signal, sys, tempfile
sys.path.insert(0, sys.argv[2])
import wasi_python
from harness.files import MemoryProvider
from wasi_python import Mount, runner

case = sys.argv[1]
provider = MemoryProvider({})
mounts = [Mount(provider, "/w", writable=True)]
dirty = (
    "import _host, os\n"
    "fds = [os.open(f'/w/{n}.txt', os.O_WRONLY | os.O_CREAT) for n in (1, 2)]\n"
    "for fd in fds:\n"
    "    os.write(fd, b'dirty')\n"
)
if case == "a Ctrl-C in the door":
    signal.signal(signal.SIGINT, signal.default_int_handler)  # a parent may have ignored it

    def host(frame):
        signal.raise_signal(signal.SIGINT)  # os.kill on Windows would end the process
        return b""

    try:
        wasi_python.run(["-c", dirty + "_host.call(b'x')\n"], mounts=mounts, host=host)
        print("returned")
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
elif case == "a Ctrl-C in the walk":
    signal.signal(signal.SIGINT, signal.default_int_handler)

    def first(path, data):
        if data:
            signal.raise_signal(signal.SIGINT)  # deferred: the walk stops after this call

    provider.answers[("write", "/1.txt")] = first
    try:
        wasi_python.run(["-c", dirty], mounts=mounts)
        print("returned")
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
else:  # the exit hook stops a run_async call, called directly as its check does

    def host(frame):
        runner._stop_async_calls()
        return b""

    code = dirty + "_host.call(b'x')\nwhile True:\n    pass\n"
    done = asyncio.run(wasi_python.run_async(["-c", code], mounts=mounts, host=host))
    print(done.trapped)
print(provider.log)
"""


@pytest.mark.parametrize(
    ("case", "want"),
    [
        ("a Ctrl-C in the door", "KeyboardInterrupt"),
        ("a Ctrl-C in the walk", "KeyboardInterrupt"),
        ("the exit hook", "cancelled"),
    ],
)
def test_a_stopped_host_gets_no_write_back(case, want) -> None:
    """Guards a change (guards: the skip when the call raises, the skip
    at the exit hook): in a child, a Ctrl-C the door host sends itself makes run raise
    KeyboardInterrupt with no content write; one sent during the walk's first write stops the
    walk there (the second file is never written) and is raised; a run_async call stopped by
    the hook run_async registers for the interpreter's exit makes no content write."""
    _run()
    out = subprocess.run(
        [sys.executable, "-c", STOPPED, case, str(paths.REPO / "tests")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr[-1500:]
    ended, log = out.stdout.splitlines()
    creates = "[('write', '/1.txt', b''), ('write', '/2.txt', b'')"
    walked = ", ('write', '/1.txt', b'dirty')" if case == "a Ctrl-C in the walk" else ""
    assert (ended, log) == (want, creates + walked + "]"), out.stdout


WRITE_FAULTS = {  # answers outside the write half's protocol
    "a fake Errno of 0": (lambda: _FakeErrno(0), "bad answer: _FakeErrno"),
    "a fake Errno past i32": (lambda: _FakeErrno(2**32 + 8), "bad answer: _FakeErrno"),
    "0": (lambda: 0, "bad answer: int"),
    "a coroutine": (lambda: _coroutine(), "bad answer: coroutine"),
    "an exception whose type's name raises": (
        lambda: _raising(_Nameless("x"))(None),
        "_Nameless: x",
    ),
}
WRITE_FAULT_GUEST = r"""
import json, os, sys
out = {}
for i in range(int(sys.argv[1])):
    try:
        open(f"/w/open{i}", "w")
        out[f"open{i}"] = "answered"
    except OSError as e:
        out[f"open{i}"] = e.errno
    f = open(f"/w/close{i}", "w")
    f.write("x")
    try:
        f.close()
        out[f"close{i}"] = "answered"
    except OSError as e:
        out[f"close{i}"] = e.errno
    try:
        os.mkdir(f"/w/call{i}")
        out[f"call{i}"] = "answered"
    except OSError as e:
        out[f"call{i}"] = e.errno
    fd = os.open(f"/w/exit{i}", os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    os.write(fd, b"x")  # left for the walk
print(json.dumps(out))
"""


@BOTH
def test_a_write_half_fault_never_escapes(snapshot) -> None:
    """Guards a change: an answer of the write half
    outside its protocol (a fake Errno whose int is 0 or past i32, a 0, a coroutine, an
    exception whose type's name raises) at a create at open, a write-back at close, a namespace
    call and the walk gives the guest EIO, one fault and one RefusedWrite(EIO, "fault") each;
    no fake answer is taken for success or for its own number, run raises nothing, and no
    coroutine is left to warn that it was never awaited."""
    import gc
    import json
    import warnings

    from harness.files import MemoryProvider
    from wasi_python import Errno, Mount, RefusedWrite

    run = _run()
    provider, names = MemoryProvider({}), list(WRITE_FAULTS)

    def hostile(make, content_only):
        def answer(path, data=b"x"):
            return make() if data or not content_only else None

        return answer

    for i, name in enumerate(names):
        make = WRITE_FAULTS[name][0]
        provider.answers[("write", f"/open{i}")] = hostile(make, False)
        provider.answers[("write", f"/close{i}")] = hostile(make, True)
        provider.answers[("write", f"/exit{i}")] = hostile(make, True)
        provider.answers[("mkdir", f"/call{i}")] = hostile(make, False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        done = run(
            ["-c", WRITE_FAULT_GUEST, str(len(names))],
            mounts=[Mount(provider, "/w", writable=True)],
            snapshot=snapshot,
        )
        gc.collect()
    assert (done.exit_code, done.trapped, done.stderr) == (0, None, b""), done
    answers = json.loads(done.stdout)
    assert answers == {
        f"{at}{i}": 29 for i in range(len(names)) for at in ("open", "close", "call")
    }
    want_refused, want_faults = [], []
    for i, name in enumerate(names):
        for at, method, path in (
            ("open", "write", f"/open{i}"),
            ("close", "write", f"/close{i}"),
            ("call", "mkdir", f"/call{i}"),
        ):
            want_refused.append(RefusedWrite("/w", method, (path,), Errno.EIO, at, "fault"))
            want_faults.append((method, path, name))
    for i, name in enumerate(names):
        want_refused.append(RefusedWrite("/w", "write", (f"/exit{i}",), Errno.EIO, "exit", "fault"))
        want_faults.append(("write", f"/exit{i}", name))
    assert done.files.refused == tuple(want_refused), done.files.refused
    assert all(type(r.errno) is Errno for r in done.files.refused)
    faults = [(f.method, f.path, f.error) for f in done.files.faults]
    assert len(faults) == len(want_faults), faults
    for (method, path, error), (m, p, name) in zip(faults, want_faults, strict=True):
        assert (method, path) == (m, p) and error.startswith(WRITE_FAULTS[name][1]), (name, error)
    assert not [w for w in caught if "never awaited" in str(w.message)], caught


# Read-only code on the import path: nothing the same call can write lies under an
# entry, and nothing is written to one.


def _digests(folder: Path) -> dict[str, str]:
    """Every file under `folder` and its SHA-256, and every folder (as "dir")."""
    import hashlib

    def digest(p: Path) -> str:
        return "dir" if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest()

    return {str(p.relative_to(folder)): digest(p) for p in sorted(folder.rglob("*"))}


@BOTH
def test_the_import_path_writes_nothing(guest_workdir, snapshot) -> None:
    """An import from a read-only entry writes no `.pyc`, even when the
    program asks for one (the refused write is quiet), and a valid `.pyc` already in an entry is
    the one imported."""
    from wasi_python import Grant

    run = _run()
    base = Path(tempfile.mkdtemp(prefix="import-path-", dir=guest_workdir))
    code = base / "code"
    (code / "pkg").mkdir(parents=True)
    (code / "mylib.py").write_text("VALUE = 'mylib'\n")
    (code / "pkg" / "__init__.py").write_text("NAME = 'pkg'\n")
    before = _digests(code)
    program = "import mylib, pkg; print(mylib.VALUE, pkg.NAME)"
    for prefix in ("", "import sys; sys.dont_write_bytecode = False\n"):
        done = run(["-c", prefix + program], grants=[Grant(code, "/code")],
                   import_path=["/code"], snapshot=snapshot)  # fmt: skip
        assert (done.exit_code, done.stdout, done.stderr) == (0, b"mylib pkg\n", b""), done
        assert _digests(code) == before, (prefix, _digests(code))
    w = base / "w"
    w.mkdir()
    (w / "wmod.py").write_text("X = 1\n")
    done = run(["-c", "import py_compile; py_compile.compile('/w/wmod.py', doraise=True)"],
               grants=[Grant(w, "/w", writable=True)], snapshot=snapshot)  # fmt: skip
    assert done.exit_code == 0, done
    st = (w / "wmod.py").stat()
    (w / "wmod.py").write_text("X = 2\n")  # the same size; its times restored below
    os.utime(w / "wmod.py", ns=(st.st_atime_ns, st.st_mtime_ns))
    done = run(["-c", "import wmod; print(wmod.X, wmod.__spec__.cached)"],
               grants=[Grant(w, "/w")], import_path=["/w"], snapshot=snapshot)  # fmt: skip
    x, cached = done.stdout.decode().split()
    assert (done.exit_code, x) == (0, "1"), done
    assert cached.startswith("/w/__pycache__/wmod.") and cached.endswith(".pyc"), cached


class _Lying(str):
    """A str whose repr and str would write code into a prelude built from them (A5)."""

    PAYLOAD = "'/code'] + [print('injected') or '/code'"

    def __repr__(self) -> str:
        return self.PAYLOAD

    def __str__(self) -> str:
        return self.PAYLOAD


@BOTH
def test_a_writable_place_never_serves_the_import_path(guest_workdir, snapshot) -> None:
    """Each refused layout raises before any work (the door is never
    called), and each allowed one imports from its entry. Every case is tried, and the failure
    names every case that answered wrongly, so a stand-in's count is exact."""
    import re

    from harness.files import MemoryProvider
    from wasi_python import Grant, Mount

    run = _run()
    base = Path(tempfile.mkdtemp(prefix="import-path-", dir=guest_workdir))

    def folder(*parts: str, mylib: bool = False) -> Path:
        d = base.joinpath(*parts)
        d.mkdir(parents=True, exist_ok=True)
        if mylib:
            (d / "mylib.py").write_text("VALUE = 'mylib'\n")
        return d

    code = folder("code", mylib=True)
    folder("code", "out")
    folder("code", "r")
    proj = folder("proj")
    folder("proj", "lib", mylib=True)
    folder("proj", "out")
    ro = Grant(code, "/code")
    mem = MemoryProvider()
    calls: list[bytes] = []

    def host(frame: bytes) -> bytes:
        calls.append(frame)
        return b""

    wrong: list[tuple[str, str]] = []

    def refused(name: str, error: type[Exception], match: str, import_path, **kw) -> None:
        kw.setdefault("grants", [ro])
        before = len(calls)
        try:
            run(["-c", "import _host; _host.call(b'x')"], host=host, import_path=import_path,
                snapshot=snapshot, **kw)  # fmt: skip
        except error as e:
            if not re.search(match, str(e)):
                wrong.append((name, f"message: {e}"))
            elif len(calls) != before:
                wrong.append((name, "the door was called"))
            return
        except Exception as e:  # a refusal of another kind, or for another reason
            wrong.append((name, f"{type(e).__name__}: {e}"))
            return
        wrong.append((name, "ran"))

    def allowed(name: str, import_path, **kw) -> None:
        program = "import sys, mylib; print(sys.path[-1], mylib.VALUE)"
        try:
            done = run(["-c", program], import_path=import_path, snapshot=snapshot, **kw)
        except Exception as e:
            wrong.append((name, f"{type(e).__name__}: {e}"))
            return
        if (done.exit_code, done.stdout) != (0, f"{import_path[0]} mylib\n".encode()):
            wrong.append((name, f"{done.exit_code} {done.stdout[-200:]!r} {done.stderr[-200:]!r}"))

    one = r"import_path\[0\]"
    refused("T1", TypeError, "import_path", "/code")
    refused("T2", TypeError, one, [b"/code"])
    refused("T3", TypeError, one, [Path("/code")])
    refused("T4", TypeError, one, [None])
    refused("T5", TypeError, "import_path", 5)
    refused("V1", ValueError, one, ["code"])
    refused("V2", ValueError, one, ["/code/"])
    refused("V3", ValueError, one, ["/code/../x"])
    refused("V4", ValueError, one + ": / cannot be on the import path", ["/"])
    refused("V5", ValueError, one, ["/usr/local/lib/x"])
    refused("V6", ValueError, r"import_path\[1\]", ["/code", "/code"])
    refused("V7", ValueError, one, ["/co\0de"])
    # The serving place: each entry strictly under its server, so no nesting rule applies.
    writable = "is served by [^,]*, which is writable; only a read-only grant"
    refused("S1", ValueError, writable, ["/x"], root=True)
    work = Grant(folder("work"), "/work", writable=True)
    refused("S2", ValueError, writable, ["/work/lib"], grants=[ro, work])
    mount = "is served by mounts"
    refused("S3", ValueError, mount, ["/m/lib"], mounts=[Mount(mem, "/m")])
    refused("S4", ValueError, mount, ["/w/lib"], mounts=[Mount(mem, "/w", writable=True)])
    refused("S5", ValueError, "no grant serves it", ["/nowhere/lib"])
    refused("S6", ValueError, mount, ["/lib"], mounts=[Mount(mem, "/")])
    alias = [Mount(mem, "/lib"), Mount(mem, "/work", writable=True)]  # one provider, two places
    refused("S7", ValueError, mount, ["/lib/lib"], mounts=alias)
    refused("S8", ValueError, writable, ["/code2"], root=folder("apart"))  # R1: apart from code
    # R3: the match is case-sensitive, as wasi-libc's; a grant at /Code
    # does not serve /code/lib, which the guest resolves through the root.
    refused("S9", ValueError, writable, ["/code/lib"], grants=[Grant(code, "/Code")],
            root=folder("apart"))  # fmt: skip
    # Guest nesting: a writable place, or any mount, under the entry.
    under = "lies under it"
    out = Grant(folder("out-g"), "/code/out", writable=True)
    refused("G1", ValueError, under, ["/code"], grants=[ro, out])
    refused("G2", ValueError, under, ["/code"], mounts=[Mount(mem, "/code/out")])
    deep = Grant(folder("ab"), "/code/a/b", writable=True)
    refused("G3", ValueError, under, ["/code"], grants=[ro, deep])
    # R8, R9: every entry is judged, not only the first.
    a = Grant(folder("a", mylib=True), "/a")
    refused("G4", ValueError, r"import_path\[1\].*" + under, ["/a", "/code"], grants=[a, ro, out])
    # Host nesting: a writable folder inside the serving grant's whole folder.
    holds = "whose folder holds"
    inner = Grant(code / "out", "/out", writable=True)
    refused("H1", ValueError, holds, ["/code"], grants=[ro, inner])
    refused("H2", ValueError, holds, ["/code"], root=code / "r")
    refused("H3", ValueError, holds, ["/code"], root=code / "new")
    if (code / "new").exists():
        wrong.append(("H3", "the refused root was made"))
    p_out = Grant(proj / "out", "/out", writable=True)
    refused("H4", ValueError, holds, ["/p/lib"], grants=[Grant(proj, "/p"), p_out])
    refused("H5", ValueError, r"import_path\[1\].*" + holds, ["/a", "/code"], grants=[a, ro, inner])
    # Allowed.
    lib = folder("lib", mylib=True)
    allowed("A1", ["/work/lib"], grants=[work, Grant(lib, "/work/lib")])
    allowed("A2", ["/code"], grants=[ro], root=True)
    allowed("A3", ["/code"], grants=[ro, Grant(folder("sibling"), "/out", writable=True)])
    allowed("A4", ["/code"], grants=[ro, Grant(folder("code2"), "/code2", writable=True)])
    try:
        done = run(["-c", "import sys, mylib; print(sys.path[-1], mylib.VALUE)"],
                   grants=[ro], import_path=[_Lying("/code")], snapshot=snapshot)  # fmt: skip
        if (done.exit_code, done.stdout) != (0, b"/code mylib\n"):
            wrong.append(("A5", f"{done.exit_code} {done.stdout[-200:]!r}"))
    except Exception as e:
        wrong.append(("A5", f"{type(e).__name__}: {e}"))
    assert wrong == [], f"{len(wrong)} wrong: {[n for n, _ in wrong]}\n{wrong}"


# A cap on files open at once. In a child, as the descriptor checks above, so the
# judge's own process is never starved.

CAP_CHILD = r"""
import json, os, sys
if sys.platform != "win32":
    import resource
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if hard != resource.RLIM_INFINITY and hard < 2048:
        print("skip", hard)
        raise SystemExit(0)
    resource.setrlimit(resource.RLIMIT_NOFILE, (2048, hard))
import wasi_python
from wasi_python import Grant

folder = sys.argv[1]
mine = os.path.join(folder, "f")
open(mine, "wb").close()


def host(frame):
    try:
        open(mine, "rb").close()
        return b"ok"
    except OSError as e:
        return str(e.errno).encode()


fill = (
    "import _host, os\nheld = []\nwhy = None\n"
    "try:\n    while len(held) < 3000:\n        held.append(os.open('/w/f', os.O_RDONLY))\n"
    "except OSError as e:\n    why = e.errno\n"
    "print(len(held), why, _host.call(b'x').decode())\n"
)
capped = wasi_python.run(["-c", fill], grants=[Grant(folder, "/w")], host=host)
print(json.dumps([capped.exit_code, capped.stdout.decode()]), flush=True)
free = (
    "import os\nheld = [os.open('/w/f', os.O_RDONLY) for _ in range(1500)]\n"
    "[os.close(fd) for fd in held]\nprint(len(held))\n"
)
uncapped = wasi_python.run(["-c", free], grants=[Grant(folder, "/w")], max_open_files=None)
print(json.dumps([uncapped.exit_code, uncapped.stdout.decode()]))
"""


def test_a_guest_at_the_open_file_cap_leaves_the_host_descriptors(guest_workdir) -> None:
    """At the default cap, in a child whose soft descriptor limit is 2,048,
    the guest opens exactly 1,024 files and gets EMFILE (33), and the door's host can still open
    a file: the guest no longer takes the descriptors the process needs. With no cap the guest
    opens 1,500. On Windows, which has no RLIMIT_NOFILE, the child sets nothing and the same
    rows run, the guest's loop bounded at 3,000 opens. A host whose hard limit is below 2,048
    skips, saying so."""
    import json

    _run()
    folder = Path(tempfile.mkdtemp(prefix="open-cap-", dir=guest_workdir))
    out = subprocess.run(
        [sys.executable, "-c", CAP_CHILD, str(folder)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if out.stdout.startswith("skip "):
        pytest.skip(f"the hard descriptor limit is {out.stdout.split()[1]}, below 2,048")
    lines = out.stdout.strip().splitlines()
    assert json.loads(lines[0]) == [0, "1024 33 ok\n"], (lines, out.stderr[-1500:])
    assert out.returncode == 0, out.stderr[-1500:]
    assert json.loads(lines[1]) == [0, "1500\n"], lines


# Deep recursion. The guest narrows CPython's C-stack guard to 128 KiB of linear memory,
# so recursion that runs through Python code raises RecursionError while wasmtime's 512 KiB native
# stack still has room. Each program recurses until it is stopped and prints its exception's class,
# the depth it reached and the message.
COUNTED = """
n = 0
def mark():
    global n
    n += 1
{body}
try:
    go()
    print("none", n)
except RecursionError as e:
    print("RecursionError", n, e)
except MemoryError as e:
    print("MemoryError", n, e)
"""
STACK_OVERFLOW = r"Stack overflow \(used 11[23] kB\)"  # the window less CPython's 16 KiB guard
PARSER = r"Parser stack overflowed"

# id: (the recursive body, its class, the message's pattern, the depth floor, runs on plain too)
RECURSIONS = {
    "repr": (
        "class A:\n    def __repr__(self):\n        mark(); return repr(self)\ndef go(): repr(A())",
        "RecursionError",
        STACK_OVERFLOW,
        190,
        True,
    ),
    "getattr": (
        "class A:\n    def __getattr__(self, k):\n        mark(); return getattr(self, k)\n"
        "def go(): A().x",
        "RecursionError",
        STACK_OVERFLOW,
        190,
        False,
    ),
    "eq": (
        "class A:\n    def __eq__(self, o):\n        mark(); return self == o\ndef go(): A() == 1",
        "RecursionError",
        STACK_OVERFLOW,
        215,
        False,
    ),
    "hash": (
        "class A:\n    def __hash__(self):\n        mark(); return hash(self)\ndef go(): hash(A())",
        "RecursionError",
        STACK_OVERFLOW,
        195,
        False,
    ),
    "str": (
        "class A:\n    def __str__(self):\n        mark(); return str(self)\ndef go(): str(A())",
        "RecursionError",
        STACK_OVERFLOW,
        210,
        False,
    ),
    "format": (
        "class A:\n    def __format__(self, s):\n        mark(); return format(self, s)\n"
        "def go(): format(A(), '')",
        "RecursionError",
        STACK_OVERFLOW,
        155,
        False,
    ),
    "iter": (
        "class A:\n    def __iter__(self):\n        mark(); return iter(self)\ndef go(): iter(A())",
        "RecursionError",
        STACK_OVERFLOW,
        190,
        False,
    ),
    "len": (
        "class A:\n    def __len__(self):\n        mark(); return len(self)\ndef go(): len(A())",
        "RecursionError",
        STACK_OVERFLOW,
        205,
        False,
    ),
    "map": (
        "def go():\n    f = lambda x: (mark(), list(map(f, [x])))\n    f(1)",
        "RecursionError",
        STACK_OVERFLOW,
        195,
        False,
    ),
    "sorted-key": (
        "def k(x):\n    mark(); return sorted([1], key=k)\ndef go(): k(1)",
        "RecursionError",
        STACK_OVERFLOW,
        45,
        False,
    ),
    "cmp-to-key": (
        "import functools\ndef c(a, b):\n    mark(); sorted([1, 2], key=functools.cmp_to_key(c))"
        "\n    return 0\ndef go(): c(1, 2)",
        "RecursionError",
        STACK_OVERFLOW,
        45,
        False,
    ),
    "min-key": (
        "def k(x):\n    mark(); return min([1, 2], key=k)\ndef go(): k(1)",
        "RecursionError",
        STACK_OVERFLOW,
        165,
        False,
    ),
    "reduce": (
        "import functools\ndef f(a, b):\n    mark(); return functools.reduce(f, [1, 2])\n"
        "def go(): f(0, 0)",
        "RecursionError",
        STACK_OVERFLOW,
        220,
        False,
    ),
    "lru-cache": (
        "import functools\n@functools.lru_cache(None)\ndef f(k):\n    mark(); return f(k + 1)\n"
        "def go(): f(0)",
        "RecursionError",
        STACK_OVERFLOW,
        185,
        True,
    ),
    "heapq": (  # the thinnest margin measured: 1.12 on x86_64
        "import heapq\nclass A:\n    def __lt__(self, o):\n        mark(); h = [A(), A()]; "
        "heapq.heapify(h); return True\ndef go(): heapq.heapify([A(), A()])",
        "RecursionError",
        STACK_OVERFLOW,
        215,
        True,
    ),
    "repr-list-of-self": (
        "class M:\n    def __repr__(s):\n        mark(); return repr([s])\ndef go(): repr(M())",
        "RecursionError",
        STACK_OVERFLOW,
        180,
        False,
    ),
    "pickle-reduce": (
        "import pickle\nclass A:\n    def __reduce__(self):\n        mark(); return (A, (A(),))\n"
        "def go(): pickle.dumps(A())",
        "RecursionError",
        STACK_OVERFLOW,
        145,
        False,
    ),
    "pickle-partial": (  # CPython's own test_recursive_pickle
        "import functools, pickle\ndef go():\n    f = functools.partial(min)\n"
        "    f.__setstate__((f, (), {}, {}))\n    pickle.dumps(f)",
        "RecursionError",
        STACK_OVERFLOW,
        0,
        True,
    ),
    "re-sub": (
        "import re\ndef r(m):\n    mark(); return re.sub('a', r, 'a')\ndef go(): r(None)",
        "RecursionError",
        STACK_OVERFLOW,
        130,
        False,
    ),
    "np-vectorize": (
        "import numpy as np\ndef f(x):\n    mark(); return np.vectorize(f)(np.array([x]))[0]\n"
        "def go(): f(1)",
        "RecursionError",
        STACK_OVERFLOW,
        85,
        False,
    ),
    "np-frompyfunc": (
        "import numpy as np\ndef f(x):\n    mark(); return u(x)\nu = np.frompyfunc(f, 1, 1)\n"
        "def go(): f(1)",
        "RecursionError",
        STACK_OVERFLOW,
        45,
        False,
    ),
    "np-apply-along-axis": (
        "import numpy as np\ndef f(a):\n    mark(); return np.apply_along_axis(f, 0, a)\n"
        "def go(): f(np.zeros(1))",
        "RecursionError",
        STACK_OVERFLOW,
        90,
        False,
    ),
    "pd-map": (
        "import pandas as pd\ndef f(x):\n    mark(); return pd.Series([x]).map(f).iloc[0]\n"
        "def go(): f(1)",
        "RecursionError",
        STACK_OVERFLOW,
        140,
        False,
    ),
    "eval": (
        "def f():\n    mark(); return eval('f()')\ndef go(): f()",
        "MemoryError",
        PARSER,
        160,
        False,
    ),
    "exec": (
        "def f():\n    mark(); exec('f()')\ndef go(): f()",
        "MemoryError",
        PARSER,
        140,
        False,
    ),
    # lxml's callbacks out of libxml2 and libxslt: measured on the built
    # set, they raise on both hosts (margins 1.45 to 1.78 on x86_64), so they are rows here.
    "lxml-target": (
        "from lxml import etree\nclass Tg:\n    def start(self, tag, attrib):\n        mark(); "
        "etree.fromstring('<a/>', etree.XMLParser(target=Tg()))\n    def close(self): return None\n"
        "def go(): etree.fromstring('<a/>', etree.XMLParser(target=Tg()))",
        "RecursionError",
        STACK_OVERFLOW,
        60,
        False,
    ),
    "lxml-xpath-extension": (
        "from lxml import etree\ndoc = etree.fromstring('<a/>')\ndef f(ctx):\n    mark(); "
        "return doc.xpath('f()', extensions={(None, 'f'): f})\ndef go(): f(None)",
        "RecursionError",
        STACK_OVERFLOW,
        70,
        False,
    ),
    "lxml-resolver": (
        "from lxml import etree\nclass R(etree.Resolver):\n    def resolve(self, url, pid, ctx):\n"
        "        mark(); parse(); return self.resolve_string('', ctx)\ndef parse():\n"
        "    p = etree.XMLParser(load_dtd=True, no_network=False); p.resolvers.add(R())\n"
        "    etree.fromstring('<!DOCTYPE a SYSTEM \"x.dtd\"><a/>', p)\ndef go(): parse()",
        "RecursionError",
        STACK_OVERFLOW,
        75,
        False,
    ),
    "xslt-extension": (
        'from lxml import etree\nSHEET = etree.XML(\'<xsl:stylesheet version="1.0" xmlns:xsl='
        '"http://www.w3.org/1999/XSL/Transform" xmlns:x="urn:x"><xsl:template match="/">'
        '<a><xsl:value-of select="x:f()"/></a></xsl:template></xsl:stylesheet>\')\n'
        "DOC = etree.XML('<a/>')\ndef f(ctx):\n    mark(); etree.XSLT(SHEET)(DOC); return 'x'\n"
        "etree.FunctionNamespace('urn:x')['f'] = f\ndef go(): etree.XSLT(SHEET)(DOC)",
        "RecursionError",
        STACK_OVERFLOW,
        65,
        False,
    ),
    "setrecursionlimit": (
        "import sys\nsys.setrecursionlimit(100000)\nclass A:\n    def __repr__(self):\n"
        "        mark(); return repr(self)\ndef go(): repr(A())",
        "RecursionError",
        STACK_OVERFLOW,
        190,
        True,
    ),
}
RECURSION_CASES = [
    pytest.param(name, snap, id=f"{name}-{'snapshot' if snap else 'plain'}")
    for name, (_, _, _, _, plain) in RECURSIONS.items()
    for snap in ([True, False] if plain else [True])
]
PICKLE_DEEP = """import os, pickle
l = []
for i in range(100000): l = [l]
try:
    pickle.dumps(l)
    print("none", flush=True)
except RecursionError as e:
    print("RecursionError", 0, e, flush=True)
os._exit(0)
"""


def _recursed(done) -> tuple[str, int, str]:
    assert (done.exit_code, done.trapped) == (0, None), (done.trapped, done.stderr[-600:])
    kind, depth, message = (done.stdout.decode().strip().splitlines()[-1].split(" ", 2) + [""])[:3]
    return kind, int(depth), message


@pytest.mark.parametrize(("name", "snapshot"), RECURSION_CASES)
def test_recursion_through_python_raises(name: str, snapshot: bool, guest) -> None:
    """Recursion that runs through Python code raises (RecursionError, or
    the parser's MemoryError for eval and exec) instead of trapping, at no less than the measured
    depth less a tenth; the depths are set by linear bytes, so they hold on every host. Through
    the judge's driver: the runner's engine, with the seeded random and the stepped
    clock, so the plain binary's hash secret, and so the fuel the check records, are the same on
    every run."""
    import re

    body, kind, pattern, floor, _ = RECURSIONS[name]
    done = guest("snapshot" if snapshot else "plain", ["-c", COUNTED.format(body=body)])
    got, depth, message = _recursed(done)
    assert got == kind and re.match(pattern, message), (got, depth, message)
    assert depth >= floor, (depth, floor)


def test_pickling_a_deep_list_raises(guest) -> None:
    """pickle.dumps of a 100,000-deep nested list raises RecursionError
    (ratio 2.7, inside the window's reach); the structure is never freed (os._exit). Through the
    judge's driver, so its fuel is the same on every run."""
    done = guest("snapshot", ["-c", PICKLE_DEEP])
    assert (done.exit_code, done.trapped) == (0, None), (done.trapped, done.stderr[-600:])
    assert done.stdout.decode().startswith("RecursionError 0 Stack overflow"), done.stdout


@BOTH
def test_the_c_stack_window_is_128_kib(snapshot: bool) -> None:
    """The guard fires 112 kB in, the 128 KiB window less CPython's
    16 KiB; on the snapshot this also shows the window survived Wizer. Through `run`, metered:
    the product's thin engine meets a Python-through-C recursion end to end; it
    records no fuel."""
    done = _run()(
        ["-c", COUNTED.format(body=RECURSIONS["repr"][0])], snapshot=snapshot, fuel=10**11
    )
    got, depth, message = _recursed(done)
    assert (got, message) == ("RecursionError", "Stack overflow (used 112 kB)"), (got, message)


def test_recursion_raises_on_wasmtimes_default_engine(guest_workdir) -> None:
    """On an engine left at wasmtime's defaults (no fuel, no epochs, no
    stack set), as another embedder's would be, the window still makes recursion raise. Its own
    engine and module; the driver's cached engine is never swapped."""
    needs.need("artifact dir", "snapshot binary", "stdlib zip", "manifest", "wasmtime-py")
    import wasmtime as wt

    from harness import guest as driver

    d = paths.artifact_dir()
    assert d is not None
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    engine = wt.Engine(wt.Config())
    module = wt.Module.from_file(engine, str(d / "python-snapshot.wasm"))
    for name in ("repr", "lru-cache", "np-frompyfunc"):
        r = driver.run(
            d / "python-snapshot.wasm",
            ["-c", COUNTED.format(body=RECURSIONS[name][0])],
            workdir=guest_workdir,
            python_version=m.python,
            stdlib=d / "python-stdlib.zip",
            own=(engine, module),
        )
        assert (r.exit_code, r.trapped) == (0, None), (name, r.describe())
        assert r.text.split()[0] == "RecursionError", (name, r.text)


def test_recursion_raises_under_the_wasmtime_cli(guest_workdir) -> None:
    """The pinned wasmtime CLI, at its own default stack, runs the plain
    binary's __repr__ recursion to a RecursionError (it used to exit 134 on the trap)."""
    needs.need("artifact dir", "plain binary", "stdlib zip", "manifest", "wasmtime cli")
    d = paths.artifact_dir()
    assert d is not None
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    major, minor = m.python.split(".")[:2]
    lib = Path(tempfile.mkdtemp(prefix="cli-lib-", dir=guest_workdir))
    root = Path(tempfile.mkdtemp(prefix="cli-root-", dir=guest_workdir))
    (lib / f"python{major}{minor}.zip").write_bytes((d / "python-stdlib.zip").read_bytes())
    out = subprocess.run(
        [
            str(paths.wasmtime_cli()),
            "run",
            "-W",
            "exceptions=y,unknown-imports-trap=y",
            "-C",
            "cache=n",
            "--dir",
            f"{lib}::/usr/local/lib",
            "--dir",
            f"{root}::/",
            "--invoke",
            "run",
            str(d / "python.wasm"),
            "-c",
            COUNTED.format(body=RECURSIONS["repr"][0]),
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert out.returncode == 0, (out.returncode, out.stderr[-800:])
    assert "RecursionError" in out.stdout, out.stdout[-400:]


# What still traps at the runner's 8 MiB
# wasm stack, with the lower host's numbers. Each kind has a depth that ends without a trap on both
# hosts with a quarter of room, and one at least 40% past the higher host's edge that ends in the
# named trap; then the next call works. The structure is built, acted on, and either freed (`del`)
# or left (os._exit) so freeing is not what is measured. Edges, arm64 / x86_64 (the research's
# edges-8m-*.jsonl): freeing a list 37,433 / 32,753; a dict 22,785 / 20,962; hash 40,313 / 40,312;
# compiling terms 58,227 / 52,402; C14N 23,818 / 23,817; a raised recursion limit 47,642 / 43,670.
DONE = "print('ok', flush=True)\nos._exit(0)"
LIMIT_FREE = (
    "import os\nN = {n}\nx = []\nfor i in range(N): x = [x]\ndel x\nprint('ok', flush=True)"
)
LIMIT_FREE_DICT = (
    "import os\nN = {n}\nx = {{}}\nfor i in range(N): x = {{'k': x}}\ndel x\n"
    "print('ok', flush=True)"
)
LIMIT_HASH = "import os\nN = {n}\nx = ()\nfor i in range(N): x = (x,)\nhash(x)\n" + DONE
LIMIT_COMPILE = (
    "import os\nN = {n}\ntry:\n    compile('+'.join(['1'] * N), 's', 'eval')\n"
    "except RecursionError:\n    pass\n" + DONE
)
LIMIT_C14N = (
    "import os\nfrom lxml import etree\nN = {n}\nroot = etree.Element('a'); e = root\n"
    "for i in range(N): e = etree.SubElement(e, 'a')\netree.tostring(root, method='c14n')\n" + DONE
)
LIMIT_RELAXNG = (
    "import os\nfrom lxml import etree\nN = {n}\nroot = etree.Element('a'); e = root\n"
    "for i in range(N): e = etree.SubElement(e, 'a')\nrng = etree.RelaxNG(etree.XML("
    '\'<grammar xmlns="http://relaxng.org/ns/structure/1.0"><start><ref name="a"/></start>'
    '<define name="a"><element name="a"><optional><ref name="a"/></optional></element>'
    "</define></grammar>'))\nrng.validate(etree.ElementTree(root))\n" + DONE
)
LIMIT_RAISED = (
    "import os, sys\nN = {n}\nsys.setrecursionlimit(N)\ndef f(): f()\ntry:\n    f()\n"
    "except RecursionError:\n    pass\n" + DONE
)
# kind: (program, ends without a trap at, traps at)
LIMITS = {
    "free-list": (LIMIT_FREE, 24_000, 52_500),
    "free-dict": (LIMIT_FREE_DICT, 15_000, 32_000),
    "hash-tuple": (LIMIT_HASH, 30_000, 57_000),
    "compile-terms": (LIMIT_COMPILE, 39_000, 82_000),
    "c14n-deep-tree": (LIMIT_C14N, 17_000, 34_000),
    "relaxng-deep-tree": (LIMIT_RELAXNG, 4_300, 9_000),  # edges 6,388 / 5,756 (the build)
    "raised-recursion-limit": (LIMIT_RAISED, 32_000, 67_000),
}


@pytest.mark.parametrize("kind", list(LIMITS))
def test_deep_data_limits(kind: str) -> None:
    """The README's limits at the
    runner's 8 MiB wasm stack hold, on a metered call (the engine the limits were measured on).
    The shallower depth ends without a trap; the deep one ends in the trap "stack overflow", the
    host survives, and the next call works."""
    run = functools.partial(_run(), fuel=10**12)  # metered, as the README's limits were measured
    program, good, deep = LIMITS[kind]
    ok = run(["-c", program.format(n=good)])
    assert (ok.exit_code, ok.trapped) == (0, None), (ok.trapped, ok.stderr[-600:])
    assert ok.stdout.decode().startswith("ok"), ok.stdout
    bad = run(["-c", program.format(n=deep)])
    assert (bad.exit_code, bad.trapped) == (None, "stack overflow"), (bad, bad.stdout)
    after = run(["-c", "print('ok')"])
    assert (after.exit_code, after.stdout) == (0, b"ok\n"), after


# What traps at 512 KiB and now ends in its own exception (or completes) at
# 8 MiB, on both hosts (the research's edges-8m-*.jsonl). Each program prints the exception's class.
CAUGHT = """import os
N = {n}
{build}
try:
    {act}
    r = "ok"
except Exception as e:
    r = type(e).__name__ + " " + str(e)[:60]
print(r, flush=True)
os._exit(0)
"""
NEST = "x = []\nfor i in range(N): x = [x]"
EXPAT_AGAIN = (
    "import xml.parsers.expat as E\ndef h(name, attrs):\n"
    "    p = E.ParserCreate(); p.StartElementHandler = h; p.Parse('<a/>', True)"
)
SAX_AGAIN = (
    "import xml.sax\nclass H(xml.sax.ContentHandler):\n    def startElement(self, n, a):\n"
    "        xml.sax.parseString(b'<a/>', H())"
)
ETREE_AGAIN = (
    "import xml.etree.ElementTree as ET\nclass T(ET.TreeBuilder):\n    def start(self, tag, a):\n"
    "        ET.fromstring('<a/>', parser=ET.XMLParser(target=T()))\n"
    "        return super().start(tag, a)"
)
HOOK = (
    "import json\nclass O:\n    def __init__(self, k): self.k = k\n"
    "def dflt(o): return [O(o.k - 1)] if o.k > 0 else []"
)
DEEP_TREE = (
    "from lxml import etree\nroot = etree.Element('a'); e = root\n"
    "for i in range(N): e = etree.SubElement(e, 'a')"
)
XSLT_CALL = (
    'from lxml import etree\nx = etree.XSLT(etree.XML(\'<xsl:stylesheet version="1.0" '
    'xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="/">'
    '<xsl:call-template name="r"><xsl:with-param name="n" select="%d"/></xsl:call-template>'
    '</xsl:template><xsl:template name="r"><xsl:param name="n"/><xsl:if test="$n &gt; 0">'
    '<xsl:call-template name="r"><xsl:with-param name="n" select="$n - 1"/></xsl:call-template>'
    "</xsl:if></xsl:template></xsl:stylesheet>' % N))"
)
XSLT_APPLY = (
    DEEP_TREE + '\nx = etree.XSLT(etree.XML(\'<xsl:stylesheet version="1.0" '
    'xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:template match="a"><b>'
    "<xsl:apply-templates/></b></xsl:template></xsl:stylesheet>'))"
)
# kind: (depth, build, act, the printed line's start)
RAISES = {
    "json-loads": (
        400_000,
        "import json\ns = '[' * N + ']' * N",
        "json.loads(s)",
        "RecursionError",
    ),
    "eq-lists": (
        400_000,
        NEST + "\ny = []\nfor i in range(N): y = [y]",
        "x == y",
        "RecursionError",
    ),
    "repr-list": (400_000, NEST, "repr(x)", "RecursionError"),
    "json-dumps": (400_000, "import json\n" + NEST, "json.dumps(x)", "RecursionError"),
    "json-default": (2_000, HOOK, "json.dumps(O(N), default=dflt)", "RecursionError"),
    "eval-parens": (199, "s = '(' * N + '1' + ')' * N", "eval(s)", "MemoryError Parser stack"),
    "eval-unary": (100_000, "s = '-' * N + '1'", "eval(s)", "MemoryError Parser stack"),
    "expat-handler": (0, EXPAT_AGAIN, "h(None, None)", "RecursionError"),
    "sax-handler": (0, SAX_AGAIN, "xml.sax.parseString(b'<a/>', H())", "RecursionError"),
    "etree-target": (
        0,
        ETREE_AGAIN,
        "ET.fromstring('<a/>', parser=ET.XMLParser(target=T()))",
        "RecursionError",
    ),
    "exception-group": (
        10_000,
        "import traceback\ng = ValueError(0)\nfor i in range(N): g = ExceptionGroup('g', [g])",
        "traceback.format_exception(g)",
        "ok",
    ),
    "xpath-parens": (
        6_000,
        "from lxml import etree",
        "etree.XML('<a/>').xpath('(' * N + '1' + ')' * N)",
        "XPathEvalError",
    ),
    "xpath-predicates": (
        6_000,
        "from lxml import etree",
        "etree.XML('<a/>').xpath('/a' + '[1]' * N)",
        "XPathEvalError",
    ),
    "xslt-call-template": (4_000, XSLT_CALL, "x(etree.XML('<a/>'))", "XSLTApplyError"),
    "xslt-apply-templates": (4_000, XSLT_APPLY, "x(etree.ElementTree(root))", "XSLTApplyError"),
}


@pytest.mark.parametrize("kind", list(RAISES))
def test_deep_data_raises(kind: str) -> None:
    """Recursion in C over nested data, the parser, expat's callbacks, deep
    exception groups, XPath and XSLT, which trap at 512 KiB, end in their own exception (or
    complete) at the runner's 8 MiB stack, on a metered call; the next call works."""
    run = functools.partial(_run(), fuel=10**12)
    depth, build, act, start = RAISES[kind]
    done = run(["-c", CAUGHT.format(n=depth, build=build, act=act)])
    assert (done.exit_code, done.trapped) == (0, None), (done.trapped, done.stderr[-600:])
    assert done.stdout.decode().startswith(start), done.stdout
    after = run(["-c", "print('ok')"])
    assert (after.exit_code, after.stdout) == (0, b"ok\n"), after


# On Linux, a faulthandler change after the first engine used to turn any
# guest trap into the host's death (SIGILL), and a late Python signal handler for SIGILL into a
# hang; the runner now refuses such a call before the guest runs. Each order in a fresh process.
FAULTHANDLER_CHILD = r"""
import faulthandler, signal, sys
import wasi_python
order = sys.argv[1]
if order in ("before", "before-then-disable"):
    faulthandler.enable()
warm = wasi_python.run(["-c", "print(1)"])
assert warm.exit_code == 0, warm
if order == "after":
    faulthandler.enable()
elif order == "before-then-disable":
    faulthandler.disable()
elif order == "after-then-disable":
    faulthandler.enable()
    faulthandler.disable()
elif order == "signal-after":
    signal.signal(signal.SIGILL, lambda *a: None)
# A guest that traps at the runner's 8 MiB stack: freeing a 200,000-deep list (json.loads
# of nested arrays now raises RecursionError there).
deep = "x = []\nfor i in range(200000): x = [x]\ndel x"
try:
    if order == "session-turn-after":  # a session's turn: a turn after a late enable
        with wasi_python.Session() as session:
            assert session.run("print(1)").exit_code == 0
            faulthandler.enable()
            done = session.run(deep)
    else:
        done = wasi_python.run(["-c", deep])
    print("trapped", done.trapped, flush=True)
except RuntimeError as e:
    print("refused", e, flush=True)
"""
REFUSED_ON_LINUX = {"after", "before-then-disable", "signal-after", "session-turn-after"}


@pytest.mark.parametrize(
    "order",
    [
        "none",
        "before",
        "after",
        "before-then-disable",
        "after-then-disable",
        "signal-after",
        "session-turn-after",
    ],
)
def test_a_faulthandler_change_cannot_kill_the_host(order: str) -> None:
    """Whatever the order of the host's
    faulthandler (or a Python signal handler) and the first run, the host survives: on Linux a call
    after a late change is refused with RuntimeError naming the remedy, on macOS and Windows the
    trap is returned. The "after" row is also a second entry into the guest in one process; the
    "session-turn-after" row is a session's second turn after a late enable."""
    _run()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONFAULTHANDLER"}
    try:
        out = subprocess.run(
            [sys.executable, "-c", FAULTHANDLER_CHILD, order],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"{order}: the host hung on the guest's trap")
    assert out.returncode == 0, (order, out.returncode, out.stderr[-800:])
    line = out.stdout.strip().splitlines()[-1]
    if sys.platform.startswith("linux") and order in REFUSED_ON_LINUX:
        assert line.startswith("refused wasmtime's handler for SIG"), line
        assert "faulthandler.disable() undoes it" in line, line
    else:
        assert line == "trapped stack overflow", line


# The runner runs each guest on a stack of its own. Every entry into wasm runs on a
# guest thread the runner makes, with a 10 MiB stack (8 MiB of it for wasm), checked before any
# wasm; the embedder's code runs on the thread that made the call (the home); Ctrl-C and an
# exception raised into the home reach the guest. A child process has a 120 s limit only so a hang
# fails the row instead of the run; an interrupt is started on ticks of the runner's ticker,
# counted, never after a delay.
TICKS_THEN = """
import threading, _thread
from wasi_python import _limits, runner
from wasi_python._process import process
def after_ticks(action):
    def wait():
        start = process().ticker_count
        while process().ticker_count < start + _limits.CANCEL_TICKS + 2:
            threading.Event().wait(0.001)
        action()
    threading.Thread(target=wait, daemon=True).start()
"""


def _child(program: str, *args: str) -> tuple[int, list[str], str]:
    _run()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONFAULTHANDLER"}
    try:
        out = subprocess.run(
            [sys.executable, "-c", program, *args],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"{args}: the child did not end within its limit")
    return out.returncode, out.stdout.strip().splitlines(), out.stderr[-1500:]


def test_every_entry_runs_on_a_guest_thread_with_room(monkeypatch) -> None:
    """Each run, each session's opening, turn and ending (a closer's
    included) enters wasm exactly once, on a thread that is not the caller's, whose stack is at
    least the refusal line; run_async with its own pool and with an executor the same."""
    import asyncio
    import concurrent.futures
    import threading

    run = _run()
    import wasi_python
    from wasi_python import _platform, _sessions
    from wasi_python._process import process

    seen: list[tuple[str, int, int]] = []

    def entry(kind: str) -> None:
        bounds = _platform.PLATFORM.stack_bounds()
        seen.append((kind, threading.get_ident(), 0 if bounds is None else bounds[1]))

    me = threading.get_ident()
    line = _platform._WASM_STACK + _platform._HOST_ROOM // 2
    monkeypatch.setattr(process().observers, "on_entry", entry)
    try:
        assert run(["-c", "print(1)"]).exit_code == 0
        assert [k for k, _, _ in seen] == ["run"]
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            for executor in (None, pool):
                done = asyncio.run(wasi_python.run_async(["-c", "print(1)"], executor=executor))
                assert done.exit_code == 0
        with wasi_python.Session() as s:
            assert s.run("x = 1").exit_code == 0
            assert s.run("print(x)").stdout == b"1\n"
        idle = wasi_python.Session(idle_s=1)
        assert idle.run("y = 2").exit_code == 0
        _sessions._reap(process().observers.clock() + 10)  # its idle bound passed: a closer ends it
        assert idle._state.done.wait(120)
    finally:
        monkeypatch.undo()
    kinds = [k for k, _, _ in seen]
    assert kinds == ["run", "run", "run", "open", "turn", "turn", "shutdown"] + [
        "open",
        "turn",
        "shutdown",
    ], kinds
    assert all(ident != me for _, ident, _ in seen), seen
    assert all(size >= line for _, _, size in seen), seen
    assert idle.ended == "idle" and idle.shutdown_outcome == "finished"


def test_a_small_guest_thread_is_refused_before_any_wasm(monkeypatch) -> None:
    """A guest thread whose stack reads under 9 MiB (or cannot be read)
    refuses the call, a session's opening and a turn with RuntimeError before any wasm runs; the
    door host and the hook are never called; with the real check, the next call works."""
    run = _run()
    import wasi_python
    from wasi_python import _platform
    from wasi_python._process import process

    calls: list[bytes] = []
    entries: list[str] = []
    monkeypatch.setattr(process().observers, "on_entry", entries.append)
    with wasi_python.Session() as session:
        for answer in ((4096, 8 << 20), None):
            monkeypatch.setattr(_platform.PLATFORM, "stack_bounds", lambda a=answer: a)
            with pytest.raises(RuntimeError, match="less than the 9 MiB"):
                run(["-c", "import _host; _host.call(b'x')"], host=calls.append)
            with pytest.raises(RuntimeError, match="less than the 9 MiB"):
                wasi_python.Session()
            monkeypatch.undo()
            monkeypatch.setattr(process().observers, "on_entry", entries.append)
        monkeypatch.setattr(_platform.PLATFORM, "stack_bounds", lambda: (4096, 8 << 20))
        with pytest.raises(RuntimeError, match="less than the 9 MiB"):
            session.run("print(1)")
        monkeypatch.undo()
    assert (calls, entries) == ([], ["open"]), (calls, entries)
    assert run(["-c", "print('ok')"]).stdout == b"ok\n"


SMALL_CALLER = """
import asyncio, concurrent.futures, sys, threading
import wasi_python
row = sys.argv[1]
FREE = "x = []\\nfor i in range(20000): x = [x]\\ndel x\\nprint('ok')"
REPR = ("class A:\\n    def __repr__(self): return repr(self)\\n"
        "try:\\n    repr(A())\\nexcept RecursionError:\\n    print('RecursionError')")
code = FREE if row in ("thread-free", "executor-free") else REPR
out = {}
threading.stack_size(256 * 1024)  # this process's threads are small, as musl's are
if row.startswith("thread"):
    t = threading.Thread(target=lambda: out.update(d=wasi_python.run(["-c", code])))
    t.start(); t.join()
else:
    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        out["d"] = asyncio.run(wasi_python.run_async(["-c", code], executor=pool))
d = out["d"]
print(d.exit_code, d.trapped, d.stdout.decode().strip(), flush=True)
"""


@pytest.mark.parametrize("row", ["thread-free", "thread-repr", "executor-free", "executor-repr"])
def test_a_guest_cannot_overrun_a_small_calling_thread(row: str) -> None:
    """A caller whose thread has 256 KiB of stack (musl gives 128 KiB) runs
    a guest that frees a 20,000-deep list, or recurses through __repr__, to its end; so does
    run_async on an executor of such threads. On main the first killed the host (SIGILL)."""
    code, lines, err = _child(SMALL_CALLER, row)
    assert code == 0, (row, code, err)
    want = "ok" if row.endswith("free") else "RecursionError"
    assert lines[-1] == f"0 None {want}", (row, lines)


CTRL_C_CHILD = (
    TICKS_THEN
    + """
import signal, sys, time
import wasi_python
from wasi_python.tools import tool
row = sys.argv[1]
main = threading.main_thread().ident
if row.startswith("raising"):
    def handler(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, handler)
    if hasattr(signal, "pthread_kill"):
        interrupt = lambda: signal.pthread_kill(main, signal.SIGINT)
    else:
        interrupt = _thread.interrupt_main
else:
    interrupt = _thread.interrupt_main  # Python's default handler: a simulated SIGINT
def host(request):
    after_ticks(interrupt)
    return b"go"
never = threading.Event()
@tool
def block() -> str:
    \"\"\"Wait for an event nobody sets.\"\"\"
    never.wait()
    return "never"
GO = "import _host\\n_host.call(b'go')\\n"
kw = {"deadline_s": None}
if row.endswith("tool"):
    def gate(call):
        after_ticks(interrupt)
        return True
    code = "from host import tools\\ntools.block()"
    kw.update(tools=[block], gate=gate)
else:
    sleep = "import time\\ntime.sleep(10**6)"
    code = GO + (sleep if row.endswith("sleep") else "while True: pass")
    kw.update(host=host)
if row.startswith("raising"):
    kw["cancel"] = threading.Event()
try:
    if row == "default-turn":
        with wasi_python.Session(deadline_s=None, host=host) as s:
            s.run(code)
    else:
        wasi_python.run(["-c", code], **kw)
    print("returned", flush=True)
except KeyboardInterrupt:
    print("interrupted", flush=True)
signal.signal(signal.SIGINT, signal.default_int_handler)
print("next", wasi_python.run(["-c", "print(1)"]).stdout.decode().strip(), flush=True)
"""
)


@pytest.mark.parametrize("row", ["default", "default-turn"])
def test_ctrl_c_stops_a_computing_guest(row: str) -> None:
    """On the main thread, with deadline_s=None and no cancel, a Ctrl-C
    (Python's default handler; a simulated SIGINT) stops a guest that computes and never calls
    back, and run (or the turn) raises KeyboardInterrupt; the next call works. On main the call
    never ended."""
    code, lines, err = _child(CTRL_C_CHILD, row)
    assert code == 0, (row, code, err)
    assert lines[-2:] == ["interrupted", "next 1"], (row, lines, err)


@pytest.mark.parametrize("row", ["raising", "raising-sleep", "raising-tool"])
def test_an_embedders_raising_sigint_handler_stops_the_call(row: str) -> None:
    """An embedder's SIGINT handler that raises
    KeyboardInterrupt, with cancel= set and deadline_s=None, stops a guest that computes, one that
    sleeps, and one waiting for a tool; run raises KeyboardInterrupt and the next call works. On
    main ctypes dropped the interrupt in the epoch callback and the call ran on."""
    code, lines, err = _child(CTRL_C_CHILD, row)
    assert code == 0, (row, code, err)
    assert lines[-2:] == ["interrupted", "next 1"], (row, lines, err)


HOME_CHILD = """
import sys, threading, wasmtime
import wasi_python
from wasi_python import _call, _home, runner
row = sys.argv[1]
state = {"wasm returned": True, "bad": []}
real_drive, real_close, real_join = _call._drive, wasmtime.Store.close, _home._join_guest
def drive(*a, **k):
    state["wasm returned"] = False
    try:
        return real_drive(*a, **k)
    finally:
        state["wasm returned"] = True
def close(self):
    if not state["wasm returned"]:
        state["bad"].append(threading.current_thread().name)
        return None  # recorded, not done: a real close under running wasm ends the process
    return real_close(self)
_call._drive, wasmtime.Store.close = drive, close
real_serve, real_start = _home._Home.serve, threading.Thread.start
once = []
def serve(self):
    if not once:
        once.append(1)
        self.serving = True
        raise KeyboardInterrupt  # raised into the home just after its guest thread started
    return real_serve(self)
def start(self):
    real_start(self)
    if self.name == "wasi-python-guest" and not once:
        once.append(1)
        raise KeyboardInterrupt  # in start()'s own wait, after the OS made the thread
if row == "start-interrupted":
    threading.Thread.start = start
else:
    _home._Home.serve = serve
def join(home):
    if row == "abandoned" and len(once) == 1:
        once.append(2)
        raise KeyboardInterrupt  # and again, inside its join: the home is forced out
    return real_join(home)
_home._join_guest = join
try:
    wasi_python.run(["-c", "while True: pass"], deadline_s=None)
    print("returned", flush=True)
except KeyboardInterrupt:
    print("interrupted", flush=True)
for t in list(threading.enumerate()):
    if t.name == "wasi-python-guest":
        t.join(60)
print("bad closes", state["bad"], flush=True)
print("next", wasi_python.run(["-c", "print(1)"]).stdout.decode().strip(), flush=True)
"""


@pytest.mark.parametrize("row", ["raised-into-home", "abandoned", "start-interrupted"])
def test_the_home_never_tears_down_a_running_guest(row: str) -> None:
    """An exception raised into
    the home while its guest computes stops the guest, and the call raises only after the guest
    thread ended; a home forced out of its join as well leaves the teardown to the guest thread;
    an interrupt inside Thread.start() after the OS made the thread keeps the guest known to its
    home. In none is a store closed while its wasm runs, and the next call works."""
    code, lines, err = _child(HOME_CHILD, row)
    assert code == 0, (row, code, err)
    assert lines[-3:] == ["interrupted", "bad closes []", "next 1"], (row, lines, err)


def test_host_functions_run_on_the_callers_thread() -> None:
    """The door host, every provider step (a
    generator listing using the caller's sqlite3 connection, a __getattr__ provider, a read's
    buffer, a bytes subclass's __bytes__) and a tool's context run on the thread that called run,
    in its live context: thread-locals, context variables and signal.signal work there; through
    run, a session turn and run_async (whose home is its worker)."""
    import asyncio
    import contextvars
    import signal
    import sqlite3
    import threading

    run = _run()
    import wasi_python
    from wasi_python import Mount
    from wasi_python.mounts import Stat
    from wasi_python.tools import tool

    var = contextvars.ContextVar("v078")
    set_inside = contextvars.ContextVar("v078-inside")
    local = threading.local()
    where: list[tuple[str, int]] = []

    class Answer(bytes):
        def __bytes__(self) -> bytes:
            where.append(("door __bytes__", threading.get_ident()))
            return (
                b"door:" + var.get("none").encode() + b":" + local.__dict__.get("v", "-").encode()
            )

    def host(request: bytes) -> bytes:
        where.append(("door", threading.get_ident()))
        if threading.current_thread() is threading.main_thread() and hasattr(signal, "SIGUSR1"):
            signal.signal(signal.SIGUSR1, signal.signal(signal.SIGUSR1, signal.SIG_DFL))
        set_inside.set("set by the door host")
        return Answer(b"")

    class Buffered(bytes):
        """An answer whose buffer export is the provider's code (CPython 3.12 and later)."""

        def __buffer__(self, flags: int) -> memoryview:
            where.append(("read __buffer__", threading.get_ident()))
            return memoryview(bytes.__bytes__(self) if hasattr(bytes, "__bytes__") else b"abc")

    class Provider:
        def __init__(self, conn: sqlite3.Connection) -> None:
            self.conn = conn

        def stat(self, path):
            where.append(("stat", threading.get_ident()))
            return Stat("dir") if path == "/" else Stat("file", size=3)

        def list(self, path):
            where.append(("list", threading.get_ident()))
            self.conn.execute("select 1")  # a thread-bound connection, check_same_thread
            yield ("a", "file")

        def read(self, path):
            where.append(("read", threading.get_ident()))
            set_inside.set("set by the provider")
            return Buffered(b"abc")

    class Lookup:
        """Methods served through __getattr__: the lookup is the provider's code too."""

        def __getattr__(self, name):
            where.append(("getattr " + name, threading.get_ident()))
            return getattr(Provider(conn), name)

    @tool
    def seen() -> str:
        """What a tool sees of the caller's context."""
        return set_inside.get("unset")

    code = (
        "import _host, os\nprint(_host.call(b'x'))\nprint(os.listdir('/m'), os.listdir('/g'))\n"
        "print(open('/m/a').read())"
    )
    tool_code = "from host import tools\nopen('/m/a').read()\nprint(tools.seen())"
    conn = sqlite3.connect(":memory:")

    def check(done, home: int, label: str) -> None:
        assert (done.exit_code, done.trapped) == (0, None), (label, done.stderr[-800:])
        assert done.files.faults == (), (label, done.files.faults)
        assert {ident for _, ident in where} == {home}, (label, where)
        where.clear()

    var.set("from the caller")
    local.v = "caller-local"
    me = threading.get_ident()
    mounts = [Mount(Provider(conn), "/m"), Mount(Lookup(), "/g")]
    done = run(["-c", code], host=host, mounts=mounts)
    check(done, me, "run")
    assert done.stdout.decode().splitlines()[0] == "b'door:from the caller:caller-local'"
    assert set_inside.get() == "set by the door host" or set_inside.get() == "set by the provider"
    done = run(["-c", tool_code], tools=[seen], mounts=[Mount(Provider(conn), "/m")])
    check(done, me, "tool")
    assert done.stdout == b"set by the provider\n", done.stdout
    with wasi_python.Session(host=host, mounts=mounts) as session:
        check(session.run(code), me, "turn")
    workers: list[int] = []

    def worker_conn() -> None:
        workers.append(threading.get_ident())

    async def main():
        loop = asyncio.get_running_loop()
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            await loop.run_in_executor(pool, worker_conn)
            return await wasi_python.run_async(
                ["-c", "import _host\nprint(_host.call(b'x'))"], host=host, executor=pool
            )

    done = asyncio.run(main())
    assert (done.exit_code, done.trapped) == (0, None), done.stderr[-800:]
    assert {ident for _, ident in where} == set(workers), (where, workers)


ABANDONED_TURN_CHILD = """
import threading, wasmtime
import wasi_python
from wasi_python import _home, runner, _sessions
state = {"in wasm": 0, "bad": []}
real_turn, real_close = _sessions._drive_turn, wasmtime.Store.close
hold, held, torn = [], [], []
entered, gate = threading.Event(), threading.Event()
def drive_turn(*a, **k):
    mine = hold == [1]
    if mine:
        hold.append(2)
        held.append(threading.current_thread())
        entered.set()
    state["in wasm"] += 1
    try:
        return real_turn(*a, **k)
    finally:
        if mine:
            gate.wait(60)
        state["in wasm"] -= 1
def close(self):
    if state["in wasm"]:
        state["bad"].append(threading.current_thread().name)
        return None
    return real_close(self)
_sessions._drive_turn, wasmtime.Store.close = drive_turn, close
real_abandon = _sessions._abandon_turn
def abandon(session_state):
    torn.append(threading.current_thread().name)
    return real_abandon(session_state)
_sessions._abandon_turn = abandon
real_serve, real_join = _home._Home.serve, _home._join_guest
armed = []
def serve(self):
    if armed == [1]:
        armed.append(2)
        self.serving = True
        raise KeyboardInterrupt
    return real_serve(self)
def join(home):
    if armed == [1, 2]:
        armed.append(3)
        raise SystemExit("forced out")
    return real_join(home)
_home._Home.serve, _home._join_guest = serve, join
s = wasi_python.Session(deadline_s=None)
print("first", s.run("x = 1").exit_code, flush=True)
armed.append(1)
hold.append(1)
try:
    s.run("while True: pass")
except BaseException as e:
    print("turn raised", type(e).__name__, flush=True)
entered.wait(60)
def busy():  # a turn claimed, marked or not
    return s._state.phase in (_sessions._Phase.TURN, _sessions._Phase.STOPPING)
print("busy while its guest runs", busy(), held[0].is_alive(), flush=True)
try:
    s.run("print(2)")
    print("second turn ran", flush=True)
except RuntimeError as e:
    print("second turn refused", str(e), flush=True)
gate.set()
held[0].join(60)
print("then busy", busy(), "ended", s.ended, "torn down on", torn, flush=True)
s.close()
print("closes while wasm ran", state["bad"], flush=True)
with wasi_python.Session() as t:
    print("next session", t.run("print(3)").stdout.decode().strip(), flush=True)
"""


def test_an_abandoned_turn_keeps_its_session_busy() -> None:
    """A turn whose home is forced
    out keeps the session busy until its guest thread ends; a second turn meanwhile is refused; the
    session then ends "error", no store is closed under wasm, and the next session works.

    The forced-out home stops its guest, which then ends soon (at its next epoch check,
    or before its wasm starts), so the guest thread is held at the end of its turn by a gate in
    the stand-in `_drive_turn`, opened once the second turn has been refused, instead of racing
    the caller's look (the Windows release run saw the guest end first). The teardown is the
    guest thread's, the abandoned path, on every platform."""
    code, lines, err = _child(ABANDONED_TURN_CHILD)
    assert code == 0, (code, err)
    assert lines == [
        "first 0",
        "turn raised SystemExit",
        "busy while its guest runs True True",
        "second turn refused a turn is already running in this session",
        "then busy False ended error torn down on ['wasi-python-guest']",
        "closes while wasm ran []",
        "next session 3",
    ], (lines, err)


HANDOFF_CHILD = """
import queue, sys, threading
import wasi_python
from wasi_python import Mount, _home, runner
from wasi_python.mounts import Stat
row = sys.argv[1]
class P:
    def stat(self, path):
        return Stat("dir") if path == "/" else Stat("file", size=3)
    def list(self, path):
        return [("a", "file")]
    def read(self, path):
        return b"abc"
once = []
if row == "after-get":
    class Inbox:
        def __init__(self):
            self.inner = queue.SimpleQueue()
        def put(self, item):
            self.inner.put(item)
        def get(self, timeout=None):
            item = self.inner.get(timeout=timeout)
            if isinstance(item, _home._Box) and not once:
                once.append(1)
                raise KeyboardInterrupt  # the hand-off is taken, not yet held by serve
            return item
    real_init = _home._Home.__init__
    def init(self):
        real_init(self)
        self.inbox = Inbox()
    _home._Home.__init__ = init
else:
    real_run = _home._Box.run
    def run_box(self):
        self.fn(*self.args)
        if not once:
            once.append(1)
            raise KeyboardInterrupt  # after the provider answered, before the box is released
        real_run(self)
    _home._Box.run = run_box
try:
    wasi_python.run(["-c", "print(open('/m/a').read())"], mounts=[Mount(P(), "/m")])
    print("returned", flush=True)
except KeyboardInterrupt:
    print("interrupted", flush=True)
print("next", wasi_python.run(["-c", "print(1)"]).stdout.decode().strip(), flush=True)
"""


@pytest.mark.parametrize("row", ["after-get", "before-answer"])
def test_an_interrupted_hand_off_is_answered_through_run(row: str) -> None:
    """Through run: an interrupt landing just after
    the home took a provider's hand-off, or after the provider answered and before its box was
    released, still ends the call: run raises KeyboardInterrupt within the child's limit, and the
    next call works."""
    code, lines, err = _child(HANDOFF_CHILD, row)
    assert code == 0, (row, code, err)
    assert lines[-2:] == ["interrupted", "next 1"], (row, lines, err)


# The README's 512 KiB rows of recursion that still traps, held on an engine
# at wasmtime's defaults (no fuel, no epochs, 512 KiB), the engine an embedder who follows the
# README's step 4 gets, so these depths do not move when the runner's stack does. Each completing
# depth is at most three quarters of the lowest edge measured on the runner's engines (metered and
# not) and on this one; each trapping depth at least a quarter past the highest, or between it and
# upstream's own limit where that is closer. Trees are built in Python; each program leaves by
# os._exit, so freeing is not what is measured, but in the row that measures freeing.
TRAP_PRE = "import os, sys\nN = {n}\n"
TRAP_TREE = "root = e = etree.Element('a')\nfor i in range(N - 1): e = etree.SubElement(e, 'a')\n"
TRAP_SHEET = "X = 'http://www.w3.org/1999/XSL/Transform'\n"
TRAP_CALL = """sheet = f'''<xsl:stylesheet version="1.0" xmlns:xsl="{{X}}">
<xsl:template match="/"><o><xsl:call-template name="t"><xsl:with-param name="n" select="{{N}}"/>
</xsl:call-template></o></xsl:template>
<xsl:template name="t"><xsl:param name="n"/><xsl:if test="$n &gt; 0"><xsl:call-template name="t">
<xsl:with-param name="n" select="$n - 1"/></xsl:call-template></xsl:if></xsl:template>
</xsl:stylesheet>'''
"""
TRAP_COPY = """sheet = f'''<xsl:stylesheet version="1.0" xmlns:xsl="{{X}}">
<xsl:template match="*"><xsl:copy><xsl:apply-templates/></xsl:copy></xsl:template>
</xsl:stylesheet>'''
"""
TRAP_BARE = """sheet = f'''<xsl:stylesheet version="1.0" xmlns:xsl="{{X}}">
<xsl:template match="*"><xsl:apply-templates/></xsl:template></xsl:stylesheet>'''
"""
TRAP_END = "print('ok', flush=True)\nos._exit(0)"
TRAPS = {
    "xpath-parens": "from lxml import etree\netree.XML(b'<a/>').xpath('(' * N + '1' + ')' * N)\n",
    "xpath-predicates": "from lxml import etree\n"
    "etree.XML(b'<r><a/></r>').xpath('a' + '[1]' * N)\n",
    "xslt-call-template": "from lxml import etree\n"
    + TRAP_SHEET
    + TRAP_CALL
    + "str(etree.XSLT(etree.XML(sheet.encode()))(etree.XML(b'<x/>')))\n",
    "xslt-apply-templates-copy": "from lxml import etree\n"
    + TRAP_TREE
    + TRAP_SHEET
    + TRAP_COPY
    + "etree.XSLT(etree.XML(sheet.encode()))(root)\n",
    "xslt-apply-templates-bare": "from lxml import etree\n"
    + TRAP_TREE
    + TRAP_SHEET
    + TRAP_BARE
    + "str(etree.XSLT(etree.XML(sheet.encode()))(root))\n",
    "c14n": "from lxml import etree\n" + TRAP_TREE + "etree.tostring(root, method='c14n')\n",
    "relaxng": "from lxml import etree\n"
    + TRAP_TREE
    + """rng = etree.RelaxNG(etree.XML(b'''<grammar xmlns="http://relaxng.org/ns/structure/1.0">
<start><ref name="A"/></start><define name="A"><element name="a"><optional><ref name="A"/>
</optional></element></define></grammar>'''))
rng.validate(root)
""",
    "traceback-freed": """sys.setrecursionlimit(10**6)
def f(k):
    if k == 0: raise ValueError('bottom')
    return f(k - 1) + 1
try:
    f(N)
except ValueError:
    pass
""",
}
# row: (completes at, traps at); the edges were measured on arm64 macOS and linux/amd64.
TRAP_DEPTHS = {
    "xpath-parens": (240, 640),
    "xpath-predicates": (2700, 4950),  # below libxml2's own 5,000, which raises XPathEvalError
    "xslt-call-template": (320, 700),
    "xslt-apply-templates-copy": (320, 680),
    "xslt-apply-templates-bare": (480, 930),
    "c14n": (1000, 2100),
    "relaxng": (260, 660),
    "traceback-freed": (2000, 4200),
}
# Two rows that must not trap: plain recursion that returns (it is freeing a long traceback that
# traps, not recursing), and libxslt's depth lowered by lxml's own call, which turns a deep
# template into XSLTApplyError.
DEEP_RETURNS = """import os, sys
sys.setrecursionlimit(10**6)
def f(k):
    return 0 if k == 0 else f(k - 1) + 1
print('ok', f(20000), flush=True)
os._exit(0)"""
MAX_DEPTH = (
    TRAP_PRE
    + "from lxml import etree\n"
    + TRAP_SHEET
    + "etree.XSLT.set_global_max_depth(250)\n"
    + "def run(sheet, doc):\n"
    + "    try:\n"
    + "        etree.XSLT(etree.XML(sheet.encode()))(doc)\n"
    + "        print('completed', flush=True)\n"
    + "    except etree.XSLTApplyError:\n"
    + "        print('XSLTApplyError', flush=True)\n"
    + TRAP_CALL
    + "run(sheet, etree.XML(b'<x/>'))\n"
    + TRAP_TREE.replace("N - 1", "N")
    + TRAP_COPY
    + "run(sheet, root)\nos._exit(0)"
)
EXHAUSTED = (None, "wasm trap: call stack exhausted")


def test_what_traps_on_wasmtimes_default_engine(guest_workdir) -> None:
    """Each of the README's rows of recursion that still traps at 512 KiB,
    on an engine at wasmtime's defaults: the completing depth prints `ok`; the deep one ends in a
    stack overflow, which the driver's own-engine path reports as wasmtime's "call stack
    exhausted"; the next call on the same engine prints `ok`. Recursing 20,000 deep and returning
    completes, and `etree.XSLT.set_global_max_depth(250)` makes deep templates raise
    `XSLTApplyError`. The snapshot binary only (every edge is the same on both), compiled once;
    every failing row is reported together. It records no fuel."""
    needs.need("artifact dir", "snapshot binary", "stdlib zip", "manifest", "wasmtime-py")
    import wasmtime as wt

    from harness import guest as driver

    d = paths.artifact_dir()
    assert d is not None
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    wasm = d / "python-snapshot.wasm"
    engine = wt.Engine(wt.Config())
    module = wt.Module.from_file(engine, str(wasm))

    def once(program: str):
        return driver.run(
            wasm,
            ["-c", program],
            workdir=guest_workdir,
            python_version=m.python,
            stdlib=d / "python-stdlib.zip",
            own=(engine, module),
            measured=False,
        )

    bad = []
    for row, (good, deep) in TRAP_DEPTHS.items():
        program = TRAP_PRE + TRAPS[row] + TRAP_END
        ok = once(program.format(n=good))
        if (ok.exit_code, ok.trapped, ok.text) != (0, None, "ok\n"):
            bad.append(f"{row} at {good}: {ok.describe()}")
        trap = once(program.format(n=deep))
        if (trap.exit_code, trap.trap_cause) != EXHAUSTED:
            bad.append(f"{row} at {deep}: {trap.describe()}, want {EXHAUSTED}")
        after = once("print('ok')")
        if (after.exit_code, after.text) != (0, "ok\n"):
            bad.append(f"{row}, the next call: {after.describe()}")
    returns = once(DEEP_RETURNS)
    if (returns.exit_code, returns.text) != (0, "ok 20000\n"):
        bad.append(f"recursion 20,000 deep that returns: {returns.describe()}")
    lowered = once(MAX_DEPTH.format(n=2000))
    if (lowered.exit_code, lowered.text) != (0, "XSLTApplyError\nXSLTApplyError\n"):
        bad.append(f"set_global_max_depth(250): {lowered.describe()}")
    assert not bad, "\n".join(bad)


DUP_PROBE = """
import errno, os, threading, time
tid = threading.get_ident()
calls = {
    "os.dup(1)": lambda: os.dup(1),
    "os.dup2(1, 5)": lambda: os.dup2(1, 5),
    "os.dup2(1, 5, inheritable=False)": lambda: os.dup2(1, 5, inheritable=False),
    "os.pipe2(0)": lambda: os.pipe2(0),
    "time.pthread_getcpuclockid(get_ident())": lambda: time.pthread_getcpuclockid(tid),
}
for name, call in calls.items():
    try:
        call()
        print(name, "returned")
    except OSError as e:
        print(name, errno.errorcode.get(e.errno, e.errno))
print("os.pipe", "present" if hasattr(os, "pipe") else "absent")
"""


@pytest.mark.parametrize("which", ["snapshot", "plain"])
def test_dup_is_refused_as_not_supported(guest, which) -> None:
    """A duplicated descriptor and a CPU clock are refused as not
    supported, the answer wasi-libc's own dup gives on preview1. Guards a change: wasi-libc 34's
    fcntl answers F_DUPFD_CLOEXEC, the command os.dup uses, with EINVAL, and
    recipes/fcntl_dup_refusal.c makes it ENOTSUP again (Decision 5); os.dup2, os.pipe2 and
    time.pthread_getcpuclockid exist from wasi-sdk 34 on (Decision 6). os.pipe stays absent."""
    r = guest(which, ["-c", DUP_PROBE])
    assert r.exit_code == 0, r.describe()
    want = [
        "os.dup(1) ENOTSUP",
        "os.dup2(1, 5) ENOTSUP",
        "os.dup2(1, 5, inheritable=False) ENOTSUP",
        "os.pipe2(0) ENOTSUP",
        "time.pthread_getcpuclockid(get_ident()) ENOTSUP",
        "os.pipe absent",
    ]
    assert r.text.splitlines() == want, r.text


HASH_PROBE = """
import sys
h = sys.hash_info
print(h.algorithm, h.width, h.hash_bits, h.seed_bits)
"""


@pytest.mark.parametrize("which", ["snapshot", "plain"])
def test_the_string_hash_is_siphash13(guest, which) -> None:
    """str, bytes and memoryview
    hash with SipHash-1-3, CPython's own default, not 32-bit FNV. CPython's configure falls back to
    FNV when it cannot run its aligned-access probe, as in a cross build, and wasm loads unaligned
    words fine; FNV can be flooded with colliding keys whatever its key (PEP 456). Step 20 passes
    --with-hash-algorithm=siphash13. The hash is computed in 64 bits and kept as Py_hash_t, which
    is 32 bits wide on wasm32, under a 128-bit key."""
    r = guest(which, ["-c", HASH_PROBE])
    assert r.exit_code == 0, r.describe()
    assert r.text.splitlines() == ["siphash13 32 64 128"], r.text


# matplotlib's `_qhull` sends qhull's messages to a stream that writes
# nowhere and opens no path (carried patch 0002). Released, it opens MPL_DEVNULL, /dev/null, for
# writing: in a writable root that holds a `dev` folder, that makes a regular file in the host's
# folder no Python code asked for.
TRI_IMPORT = "import matplotlib.tri as mtri\n"
TRI_RUN = """
try:
    mtri.Triangulation([0.0, 1.0, 2.0, 3.0], [0.0, 1.0, 2.0, 3.0])
except RuntimeError as e:
    print("collinear", str(e).split(":")[0])
print("good", mtri.Triangulation([0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0]).triangles.shape)
"""


def _listing(folder: Path) -> list[tuple[str, str, int]]:
    """Every path under a folder, with its type and, for a file, its size."""
    out = []
    for p in sorted(folder.rglob("*")):
        kind = "link" if p.is_symlink() else "dir" if p.is_dir() else "file"
        out.append(
            (p.relative_to(folder).as_posix(), kind, p.lstat().st_size if kind == "file" else 0)
        )
    return out


@pytest.mark.slow
def test_a_triangulation_leaves_every_writable_grant_as_it_was(guest_turns, guest_workdir) -> None:
    """In a call whose writable root holds a `dev` folder, a Delaunay
    triangulation and a qhull error leave every writable grant as it was: the root, and the font
    cache's own grant (MPLCONFIGDIR), each listed with every path's type and size after
    matplotlib's import and again after the triangulations, in one instance kept across two
    calls."""
    from harness import guest as driver

    directory = paths.artifact_dir()
    assert directory is not None
    _, tag = _version()
    cache = Path(tempfile.mkdtemp(prefix="mplconfig-", dir=guest_workdir))
    data = driver.mpl_data_dir(directory / "python-stdlib.zip", guest_workdir)
    t = guest_turns(
        "snapshot",
        preopens=[
            (f"/usr/local/lib/python{tag}.zip/matplotlib/mpl-data", data, False),
            ("/mplconfig", cache, True),
        ],
        env={"MPLCONFIGDIR": "/mplconfig"},
    )
    (t.root / "dev").mkdir()
    (t.root / "dev" / "keep").write_bytes(b"")
    first = t.turn(TRI_IMPORT)
    assert first.trapped is None and first.value == 0, first.describe()
    grants = {"/": t.root, "/mplconfig": cache}
    before = {g: _listing(p) for g, p in grants.items()}
    assert before["/mplconfig"], "matplotlib's import wrote no font cache: the grant is not used"
    second = t.turn(TRI_RUN)
    assert second.trapped is None and second.value == 0, second.describe()
    assert second.text == (
        "collinear Error in qhull Delaunay triangulation calculation\ngood (2, 3)\n"
    ), second.text
    after = {g: _listing(p) for g, p in grants.items()}
    changed = [
        f"{g}: {sorted(set(after[g]) ^ set(before[g]))}" for g in grants if after[g] != before[g]
    ]
    assert not changed, "a writable grant changed: " + "; ".join(changed)
