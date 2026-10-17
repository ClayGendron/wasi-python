"""v1.2, the hostile guest: a program written to escape, persist, exhaust or crash is held by the
wall and by the runner's defaults (spec 006). Each check names whether it guards a change spec 006
made or behaviour that already held."""

from __future__ import annotations

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
lib = f"/usr/local/lib/python{{mm}}"
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


@BOTH
def test_planted_code_never_runs(guest_workdir, snapshot) -> None:
    """Guards a change on the plain reactor (it ran a planted .pth and imported planted modules),
    existing behaviour on the snapshot: code one run leaves in a root never runs in the next."""
    run = _run()
    mm, tag = _version()
    root = _root(guest_workdir)
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
