"""v1.4: an embedder makes a starting image with the snapshot's `prepare` export.

`prepare` runs code the host passes in a snapshot instance that has run nothing, with the clocks
and entropy pinned, then leaves the instance as the build leaves the snapshot: its heap frozen and
its table of preopens forgotten. The host reads the memory whole, and each later call copies it
into a fresh instance before `run` or `turn`. Every row drives the export through the judge's own
driver, which answers entropy and the clocks alike in every run, so a row shows that a generator
was reseeded, not that two calls differ.
"""

from __future__ import annotations

import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest

from harness import needs, scan

pytestmark = pytest.mark.goal("v1.4")

PIN_REALTIME = "1767225600.0"  # 2026-01-01T00:00:00Z, the build's constant
MPL_ENV = {"MPLCONFIGDIR": "/mplconfig"}  # a writable cache folder in the judge's root
TRAP_FUEL = 50_000_000
UNCLOSED = "def g():\n    pass\nf = open('/out.txt', 'w')\nf.write('x' * 100)\n"
ZIP_LEFT_OPEN = (
    "import zipfile\n"
    "z = zipfile.ZipFile('/out.zip', 'w')\n"
    "z.writestr('a.txt', 'x' * 100)\n"
    "def g():\n"
    "    pass\n"
)
DRAWS = (
    "import random, tempfile, numpy.random, sympy.core.random, more_itertools.recipes\n"
    "print(random.random(), numpy.random.random(), sympy.core.random.rng.random(),"
    " next(tempfile._get_candidate_names()), more_itertools.recipes._private_randrange(0, 10**9))\n"
)


def _folder(workdir: Path, files: dict[str, str]) -> Path:
    """A fresh host folder holding `files` (name -> text)."""
    base = Path(tempfile.mkdtemp(prefix="prepare-", dir=workdir))
    for name, text in files.items():
        (base / name).write_text(text)
    return base


def _image(guest_turns: Callable, code: str, **kw) -> tuple[bytes, object]:
    """The starting image `code` makes in a fresh snapshot instance, and the `prepare` call."""
    t = guest_turns("snapshot", answered=True, **kw)
    made = t.prepare(code)
    assert (made.value, made.trapped) == (0, None), made.describe()
    return t.image(), made


def _bytes(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def test_prepare_refuses(guest_turns, metric) -> None:
    """`prepare` returns -1 and runs no Python on the plain reactor, after `run`, after `turn`
    and a second time: an image is made once, from a snapshot instance that has run nothing. After
    a `prepare` that failed, `prepare`, `run` and `turn` refuse too: that instance is discarded."""
    calls = {}
    plain = guest_turns("plain")
    calls["the plain reactor"] = plain.prepare("print('ran')")
    ran = guest_turns("snapshot", argv=["-c", "pass"])
    assert ran.run().value == 0
    calls["after run"] = ran.prepare("print('ran')")
    turned = guest_turns("snapshot")
    assert turned.turn("pass").value == 0
    calls["after turn"] = turned.prepare("print('ran')")
    twice = guest_turns("snapshot", answered=True)
    first = twice.prepare("x = 1")
    assert first.value == 0, first.describe()
    calls["a second time"] = twice.prepare("print('ran')")
    failed = guest_turns("snapshot", answered=True, argv=["-c", "print('ran')"])
    first_failed = failed.prepare("x = 1\nraise SystemExit(3)")
    assert first_failed.value == 3, first_failed.describe()
    calls["after a failed prepare"] = failed.prepare("print('ran')")
    ran_after = failed.run()
    if (ran_after.value, ran_after.stdout) != (70, b""):
        calls["a run after a failed prepare"] = ran_after
    failed_too = guest_turns("snapshot", answered=True)
    assert failed_too.prepare("raise ValueError('setup failed')").value == 1
    calls["a turn after a failed prepare"] = failed_too.turn("print('ran')")
    found = [
        f"{when}: {c.describe()}, stdout {c.stdout!r}"
        for when, c in calls.items()
        if (c.value, c.trapped, c.stdout, c.stderr) != (-1, None, b"", b"")
    ]
    assert not found, scan.report(found, "prepare refusals")
    metric("fuel", first.fuel)


def test_a_trapped_prepare_leaves_nothing_callable(guest_turns, metric) -> None:
    """A prelude that never returns (here it runs out of fuel) leaves the instance refusing every
    export: `run` returns 70 and `prepare`, `turn` and `shutdown` return -1, with no output."""
    t = guest_turns("snapshot", answered=True)
    trapped = t.prepare("while True:\n    pass\n", fuel=TRAP_FUEL)
    assert trapped.trapped == "out of fuel", trapped.describe()
    calls = {
        "run": (t.run(), 70),
        "prepare": (t.prepare("print('ran')"), -1),
        "turn": (t.turn("print('ran')"), -1),
        "shutdown": (t.shutdown(), -1),
    }
    found = [
        f"{name}: {c.describe()}, stdout {c.stdout!r}"
        for name, (c, want) in calls.items()
        if (c.value, c.trapped, c.stdout, c.stderr) != (want, None, b"", b"")
    ]
    assert not found, scan.report(found, "after a trapped prepare")
    metric("fuel", sum(c.fuel for c, _ in calls.values()))


def test_the_makings_import_path_is_gone(guest, guest_turns, guest_workdir) -> None:
    """A module the prelude imported from the making call's import path stays imported, but the
    path is gone: no entry on `sys.path` and none in the importer cache."""
    code = _folder(guest_workdir, {"amod.py": "VALUE = 1\n"})
    image, _ = _image(guest_turns, "import amod\n", argv=["/a"], preopens=[("/a", code, False)])
    program = (
        "import sys, amod\n"
        "print('/a' in sys.path, '/a' in sys.path_importer_cache, amod.__name__)\n"
    )
    r = guest("snapshot", ["-c", program], image=image)
    assert (r.exit_code, r.text) == (0, "False False amod\n"), r.describe()


def test_a_prepared_image_runs_a_program(guest, guest_turns) -> None:
    """A restored instance's `run` sees what the prelude defined."""
    image, _ = _image(guest_turns, "def f():\n    return 42\nx = [1, 2]\n")
    r = guest("snapshot", ["-c", "print(f(), x)"], image=image)
    assert (r.exit_code, r.text) == (0, "42 [1, 2]\n"), r.describe()


def test_the_preopens_are_the_calls(guest, guest_turns, guest_workdir) -> None:
    """The image forgets the making call's table of preopens: a restored call granted the same
    folders in another order, and one more, reads each folder at its own guest path."""
    a, b, c = (_folder(guest_workdir, {"name.txt": name}) for name in "abc")
    prelude = "import os\nseen = os.listdir('/a') + os.listdir('/b')\n"
    image, _ = _image(guest_turns, prelude, preopens=[("/a", a, False), ("/b", b, False)])
    program = "print(*(open(f'/{n}/name.txt').read() for n in 'abc'), seen)"
    grants = [("/b", b, False), ("/a", a, False), ("/c", c, False)]
    r = guest("snapshot", ["-c", program], image=image, preopens=grants)
    assert (r.exit_code, r.text) == (0, "a b c ['name.txt', 'name.txt']\n"), r.describe()


def test_the_prelude_sees_pinned_clocks(guest, guest_turns) -> None:
    """While the prelude runs, the wall clock reads the build's constant, the monotonic clock 0
    and entropy zeros; so no time the image holds lies in a restored call's future."""
    # The guest reads its own clocks, by name; the judge reads none.
    read = "getattr(time, c)() for c in ('time', 'monotonic')"
    prelude = f"import os, time\nT = (*({read}), os.urandom(4))\n"
    image, _ = _image(guest_turns, prelude)
    program = "import time; print(T[0], T[1], T[2].hex(), getattr(time, 'monotonic')() >= T[1])"
    r = guest("snapshot", ["-c", program], image=image)
    assert (r.exit_code, r.text) == (0, f"{PIN_REALTIME} 0.0 00000000 True\n"), r.describe()


def test_a_prelude_does_not_pin_files(guest_turns, metric) -> None:
    """File metadata stays the host's while the prelude runs: two files are two files, and
    `shutil.copyfile` from one onto the other works."""
    t = guest_turns("snapshot", answered=True)
    (t.root / "p.txt").write_text("from p")
    (t.root / "q.txt").write_text("from q")
    prelude = (
        "import os, shutil\n"
        "p, q = os.stat('/p.txt'), os.stat('/q.txt')\n"
        "print((p.st_dev, p.st_ino) != (q.st_dev, q.st_ino))\n"
        "shutil.copyfile('/p.txt', '/q.txt')\n"
        "print(open('/q.txt').read())\n"
    )
    made = t.prepare(prelude)
    assert (made.value, made.text) == (0, "True\nfrom p\n"), made.describe()
    metric("fuel", made.fuel)


def test_the_refresh_reseeds_what_the_image_froze(guest, guest_turns) -> None:
    """`random`, numpy's legacy generator, sympy's generators, more-itertools' private one and
    `tempfile`'s name sequence are seeded afresh in each call from an image: none of their next
    draws repeats the prelude's."""
    image, made = _image(guest_turns, DRAWS)
    r = guest("snapshot", ["-c", DRAWS], image=image)
    assert r.exit_code == 0, r.describe()
    before, after = made.text.split(), r.text.split()
    assert len(before) == len(after) == 5, (made.text, r.text)
    names = ("random", "numpy.random", "sympy", "tempfile", "more_itertools")
    same = [f"{n}: {b}" for n, b, a in zip(names, before, after, strict=True) if a == b]
    assert not same, scan.report(same, "a draw the image repeats")


def test_a_program_shares_the_codes_namespace(guest, guest_turns) -> None:
    """A program runs in the module the code ran in: what it rebinds, the code's functions see,
    as in one `-c` program of both."""
    code = "x = 1\ndef f():\n    return x\n"
    one = guest("snapshot", ["-c", code + "x = 2; print(f())"], record=False)
    assert (one.exit_code, one.text) == (0, "2\n"), one.describe()
    image, _ = _image(guest_turns, code)
    r = guest("snapshot", ["-c", "x = 2; print(f())"], image=image)
    assert (r.exit_code, r.text) == (0, "2\n"), r.describe()


def test_a_prepared_call_keeps_an_unclosed_files_bytes(guest, guest_turns) -> None:
    """A call from an image keeps the bytes of a file its program left open beside a function
    it defined: the program's own names are dropped and collected at the end."""
    image, _ = _image(guest_turns, "import os\n")
    r = guest("snapshot", ["-c", UNCLOSED], image=image)
    assert r.exit_code == 0, r.describe()
    kept = _bytes(r.root / "out.txt")
    assert kept == 100, f"a file left open kept {kept} of 100 bytes"


def test_a_prepared_call_finalizes_a_zipfile_left_open(guest, guest_turns) -> None:
    """A `ZipFile` a call from an image leaves open is finalized: its directory is written."""
    image, _ = _image(guest_turns, "import zipfile\n")
    r = guest("snapshot", ["-c", ZIP_LEFT_OPEN], image=image)
    assert r.exit_code == 0, r.describe()
    try:
        with zipfile.ZipFile(r.root / "out.zip") as z:
            members = {n: z.read(n) for n in z.namelist()}
    except (OSError, zipfile.BadZipFile) as e:
        members = {"unreadable": str(e).encode()}
    assert members == {"a.txt": b"x" * 100}, members


def test_a_hung_writer_is_flushed(guest, guest_turns) -> None:
    """A file a call hangs on a module the image holds is flushed at the end, not finalized."""
    image, _ = _image(guest_turns, "import json\n")
    program = "import json\nf = open('/out.txt', 'w')\nf.write('x' * 100)\njson.kept = f\ndel f\n"
    r = guest("snapshot", ["-c", program], image=image)
    assert r.exit_code == 0, r.describe()
    kept = _bytes(r.root / "out.txt")
    assert kept == 100, f"a file hung on json kept {kept} of 100 bytes"


def test_a_prepared_call_runs_atexit(guest, guest_turns) -> None:
    """The image's `atexit` handlers and the call's run at the end of the call, the last
    registered first."""
    image, _ = _image(guest_turns, "import atexit\natexit.register(print, 'image')\n")
    r = guest("snapshot", ["-c", "import atexit; atexit.register(print, 'call')"], image=image)
    assert (r.exit_code, r.text) == (0, "call\nimage\n"), r.describe()


def test_a_prepared_session_ends_light(guest_turns, metric) -> None:
    """A session from an image ends as a call from one does: `shutdown` returns 0 and an
    unclosed file keeps its bytes."""
    image, _ = _image(guest_turns, "import os\n")
    t = guest_turns("snapshot", answered=True, image=image)
    turned = t.turn(UNCLOSED)
    assert (turned.value, turned.trapped) == (0, None), turned.describe()
    ended = t.shutdown()
    assert (ended.value, ended.trapped, ended.stderr) == (0, None, b""), ended.describe()
    kept = _bytes(t.root / "out.txt")
    assert kept == 100, f"a file left open in a session kept {kept} of 100 bytes"
    metric("fuel", turned.fuel + ended.fuel)


def test_a_prepared_image_is_reproducible(guest_turns, metric) -> None:
    """One prelude prepared twice in one process gives the same bytes: the export adds nothing
    of its own that differs between two makings."""
    prelude = "import json\nx = [i * i for i in range(100)]\ndef f():\n    return x\n"
    first, made = _image(guest_turns, prelude)
    second, _ = _image(guest_turns, prelude)
    if first != second:
        pages = [
            i // 65536
            for i in range(0, min(len(first), len(second)), 65536)
            if first[i : i + 65536] != second[i : i + 65536]
        ]
        pytest.fail(f"two images differ: {len(first)} and {len(second)} bytes, pages {pages[:8]}")
    metric("fuel", made.fuel)


@pytest.mark.slow
def test_the_everything_prelude_prepares(guest, guest_turns, artifacts, fact) -> None:
    """A prelude that imports every name of MANIFEST's `x-snapshot-package` lines prepares, and a
    call from its image runs `-c pass`: each package the set ships imports under the pinned clocks.
    The prelude's fuel, the image's pages and the restored call's fuel are facts: a call from an
    image that holds numpy's random module spends a number of instructions that moves a little
    from run to run, even under this driver's seeded entropy and clocks, and the judge holds a
    metric's fuel exact."""
    needs.need("manifest")
    lines = artifacts.path("MANIFEST").read_text().splitlines()
    names = [n for ln in lines if ln.startswith("x-snapshot-package ") for n in ln.split()[2:]]
    assert names, "MANIFEST has no x-snapshot-package line"
    prelude = "".join(f"import {n}\n" for n in names)
    image, made = _image(guest_turns, prelude, env=MPL_ENV, mpl_data=True)
    r = guest("snapshot", ["-c", "pass"], image=image, env=MPL_ENV, mpl_data=True, record=False)
    assert (r.exit_code, r.stderr) == (0, b""), r.describe()
    fact("prelude_fuel", made.fuel)
    fact("image_pages", len(image) // 65536)
    fact("names", len(names))
    fact("restored_fuel", r.fuel)
