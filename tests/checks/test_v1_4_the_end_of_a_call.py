"""v1.4: a call ends as CPython ends, every finalizer in its place, without returning memory to an
instance that is about to be discarded.

`run` and a session's `shutdown` finalize with `Py_FinalizeEx`. Just before it the reactor puts a
hook over Python's three allocator domains; once Python is finalizing (every `atexit` handler has
run), a freed block is kept on a list instead of freed. The link wraps the C library's allocators,
so every allocation teardown makes is counted: before one would take teardown past its 1 MiB
budget, or after one gets NULL, every kept block is freed and frees run as before. A program that
is tracing with tracemalloc at the end keeps the old teardown.

The rows: every export refuses after the instance finalized; teardown's memory against the cap,
with a program that leaves little room; the hook arms only after `atexit`; the outcome of each
native-behaviour probe, equal to native CPython's; teardown's fuel; the cost of the wrappers on a
call that never finalizes; and, read from both binaries, that nothing calls the C library's
allocators but their wrappers. **Teardown's growth** is a program's memory at the end less the
same program's, ended by `os._exit(0)` after a flush; **teardown's fuel** is its fuel less that
program's. Every row counts fuel, bytes or outcomes, never time.
"""

from __future__ import annotations

import gzip
import sqlite3
import zipfile
from pathlib import Path

import pytest

from harness import needs

pytestmark = pytest.mark.goal("v1.4")

WHICH = ["plain", "snapshot"]
KIB = 1024
MIB = 1024 * KIB
BUDGET = MIB  # teardown's budget, the reactor's TEARDOWN_BUDGET
LIMIT = 64 * MIB  # the memory limit of the rows that fill the heap
EXIT = "\nimport os as _o, sys as _s\n_s.stdout.flush()\n_s.stderr.flush()\n_o._exit(0)\n"


def _ended_early(code: str) -> str:
    """The same program, ended by `os._exit(0)` after a flush: no teardown."""
    return code + EXIT


def _growth(guest, which: str, code: str, **kw) -> tuple[int, object]:
    """Teardown's growth of the linear memory, and the full program's result."""
    early = guest(which, ["-c", _ended_early(code)], record=False, **kw)
    assert early.exit_code == 0, early.describe()
    full = guest(which, ["-c", code], **kw)
    assert (full.exit_code, full.trapped) == (0, None), full.describe()
    return full.memory_size - early.memory_size, full


# Criterion (a): no instance runs after its teardown.

REFUSAL_FUEL = 10_000


def _refusals(t) -> dict[str, tuple[int | None, int]]:
    """Each export called once more: (its value, its fuel)."""
    calls = {
        "run": t.run,
        "turn": lambda: t.turn("print('ran')"),
        "turn_input": lambda: t._call(
            lambda: t.exports["turn_input"](t.store, t.write(b"x"), 1), 10**9
        ),
        "prepare": lambda: t.prepare("print('ran')"),
        "checkpoint 1": lambda: t.checkpoint(1),
        "checkpoint 0": lambda: t.checkpoint(0),
        "shutdown": t.shutdown,
    }
    got = {}
    for name, call in calls.items():
        done = call()
        assert done.trapped is None and b"ran" not in done.stdout, (name, done.describe())
        got[name] = (done.value, done.fuel)
    return got


REFUSED = {
    "run": 70,
    "turn": -1,
    "turn_input": -1,
    "prepare": -1,
    "checkpoint 1": -1,
    "checkpoint 0": -1,
    "shutdown": -1,
}


@pytest.mark.parametrize("which", WHICH)
@pytest.mark.parametrize("ended_by", ["run", "shutdown"])
def test_every_export_refuses_after_teardown(guest_turns, which, ended_by) -> None:
    """After `run`, and after a session's `shutdown`, each export refuses, running no Python, in
    under 10,000 fuel: the hook stays installed after teardown, which is safe only because nothing
    runs in the instance afterwards."""
    t = guest_turns(which)
    if ended_by == "run":
        first = t.run()
        assert first.trapped is None and first.value == 0, first.describe()
    else:
        assert t.turn("x = 1").value == 0
        assert t.shutdown().value == 0
    got = _refusals(t)
    assert {name: value for name, (value, _) in got.items()} == REFUSED, got
    costly = {name: fuel for name, (_, fuel) in got.items() if fuel >= REFUSAL_FUEL}
    assert not costly, f"a refusal ran {costly} fuel ({REFUSAL_FUEL:,})"


# Criterion (b): teardown's memory, against the cap.

GROWTH = 256 * KIB
GROWS = {
    "a bare call": "pass\n",
    "import numpy": "import numpy\n",
    "a pandas groupby": (
        "import numpy as np, pandas as pd\n"
        "df = pd.DataFrame({'k': np.arange(200_000) % 97, 'v': np.arange(200_000)})\n"
        "print(len(df.groupby('k')['v'].sum()))\n"
    ),
    "200,000 objects with __del__": (
        "class D:\n    def __del__(self):\n        pass\nkeep = [D() for _ in range(200_000)]\n"
    ),
    "200,000 cycles": (
        "class C:\n    pass\n"
        "def cycle():\n    c = C()\n    c.me = c\n"
        "for _ in range(200_000):\n    cycle()\n"
        "import gc\ngc.disable()\n"
        "for _ in range(200_000):\n    cycle()\n"
    ),
}


@pytest.mark.parametrize("which", WHICH)
@pytest.mark.parametrize("program", GROWS)
def test_teardown_grows_the_memory_little(guest, note, which, program) -> None:
    """Teardown allocates little and never reuses a block it did not free: its growth stays
    within 256 KiB on a bare call, after numpy, after a pandas groupby and with 200,000
    finalizers or cycles to run."""
    grew, _ = _growth(guest, which, GROWS[program])
    note(f"teardown grew the memory by {grew:,} bytes")
    assert grew <= GROWTH, f"teardown grew the memory by {grew:,} bytes ({GROWTH:,})"


SESSION_TURNS = (
    "big = {i: i for i in range(500_000)}\n",
    "class D:\n    def __del__(self):\n        pass\nkeep = [D() for _ in range(50_000)]\n",
)


@pytest.mark.parametrize("which", WHICH)
def test_a_sessions_shutdown_grows_the_memory_little(guest_turns, note, which) -> None:
    """A session's turns hold a 500,000-key dict and 50,000 finalizers: its shutdown grows the
    memory within 256 KiB of what the last turn left."""
    t = guest_turns(which)
    for code in SESSION_TURNS:
        done = t.turn(code)
        assert done.value == 0, done.describe()
    before = t.memory_size
    end = t.shutdown()
    assert end.value == 0 and end.trapped is None, end.describe()
    grew = end.memory_size - before
    note(f"shutdown grew the memory by {grew:,} bytes")
    assert grew <= GROWTH, f"shutdown grew the memory by {grew:,} bytes ({GROWTH:,})"


def _filled(room: int, code: str) -> str:
    """`code`, then the heap filled to its last bytes under the memory limit, `room` bytes of it
    given back as one block. The filler is a global, so teardown frees it."""
    return (
        code + "_hold = []\n"
        "def _fill(room):\n"
        "    spare = bytearray(room) if room else None\n"
        "    size = 1 << 20\n"
        "    while size >= 16:\n"
        "        try:\n"
        "            while True:\n"
        "                _hold.append(bytearray(size))\n"
        "        except MemoryError:\n"
        "            size //= 4\n"
        "    return spare\n"
        f"_spare = _fill({room})\n"
        "del _spare\n"
    )


# A finalizer drops a 10 MiB block, which teardown keeps instead of freeing, then asks for 4 MiB
# with 1 MiB of room: Pillow's image memory comes from the C library's allocator, outside Python's
# domains, so only the wrapper's count, past the budget, drains the kept block in time. numpy's
# data is in Python's raw domain, which the hook itself counts.
LATE = (
    "import os\n"
    "class N:\n"
    "    def __init__(self, make):\n"
    "        self.big = [bytes(10 << 20)]\n"
    "        self.make = make\n"
    "    def __del__(self, write=os.write):\n"
    "        self.big.clear()\n"
    "        write(1, b'%d\\n' % self.make())\n"
)
PILLOW_LATE = (
    LATE + "from PIL import Image\n"
    "Image.new('L', (1, 1), 1).getpixel((0, 0))\n"  # what Pillow imports on first use, imported
    "n = N(lambda: Image.new('L', (2048, 2048), 1).getpixel((2047, 2047)))\n"
)
NUMPY_LATE = LATE + "import numpy\nn = N(lambda: int(numpy.ones(4 << 20, dtype=numpy.uint8)[-1]))\n"
CHURN = (
    "import os\n"
    "class F:\n"
    "    def __del__(self, write=os.write):\n"
    "        for _ in range(100):\n"
    "            b = bytearray(64 << 10)\n"
    "            del b\n"
    "        write(1, b'churned\\n')\n"
    "f = F()\n"
)
RENDERER = (
    "import os\n"
    "from matplotlib.backends.backend_agg import RendererAgg\n"
    "class R:\n"
    "    def __del__(self, make=RendererAgg, write=os.write):\n"
    "        r = make(256, 256, 72)\n"
    "        write(1, b'renderer %d\\n' % r.width)\n"
)
SQLITE = (
    "import sqlite3\n"
    "c = sqlite3.connect('t.db')\n"
    "c.execute('create table t(x)')\n"
    "c.execute('insert into t values (0)')\n"
    "c.commit()\n"
    "c.executemany('insert into t values (?)', [(i,) for i in range(1, 1001)])\n"
)
ROOMS = {
    # name: (room, program, its lines)
    "room 0": (0, "print('start')\n", "filled\nstart\n"),  # os.write's line, then print's
    "a NULL before the budget": (512 * KIB, CHURN, "churned\n"),
    "Pillow's allocator, outside the domains": (MIB, PILLOW_LATE, "1\n"),
    "numpy's data, in the raw domain": (MIB, NUMPY_LATE, "1\n"),
    "C++ new": (2 * MIB, RENDERER + "r = R()\n", "renderer 256\n"),
    "a sqlite rollback": (2 * MIB, SQLITE, ""),
}


def _no_exception_ignored(r) -> None:
    err = r.stderr.decode(errors="replace")
    assert "Exception ignored" not in err and "Error" not in err, err[-400:]


@pytest.mark.parametrize("which", WHICH)
@pytest.mark.parametrize("case", ROOMS)
def test_teardown_ends_as_native_near_the_cap(guest, which, case) -> None:
    """Under a 64 MiB memory limit, a program fills the heap and gives back a little room; its
    teardown ends as native's does, with its lines, exit 0 and no exception ignored, and never
    traps: a NULL drains the kept blocks and retries, and an allocation outside Python's domains
    (numpy's data, C++'s `new`, sqlite's own) that would pass the budget drains them first."""
    room, code, lines = ROOMS[case]
    program = _filled(room, code)
    if case == "room 0":
        program += "os.write(1, b'filled\\n')\n"
        program = "import os\n" + program
    r = guest(which, ["-c", program], memory_limit=LIMIT, mpl_data=case == "C++ new")
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    assert r.text == lines, r.text
    if case == "room 0":  # a heap full to its last bytes: CPython's own teardown may find none
        err = r.stderr.decode(errors="replace")
        assert all("MemoryError" in line or "Exception ignored" in line
                   for line in err.splitlines() if line.strip()), err  # fmt: skip
    else:
        _no_exception_ignored(r)
    if case == "a sqlite rollback":
        db = r.root / "t.db"
        assert sqlite3.connect(db).execute("select count(*) from t").fetchone() == (1,)


@pytest.mark.parametrize("which", WHICH)
def test_a_failed_new_in_teardown_ends_as_native(guest, note, which) -> None:
    """With 128 KiB of room, a finalizer in the first collection, with nothing kept yet, asks C++
    for a 256 KiB pixel buffer: the retry fails as native's would, libc++ throws `bad_alloc`,
    and the call ends without a trap, its outcome recorded."""
    code = RENDERER + "r = R()\nr.me = r\ndel r\n"
    r = guest(which, ["-c", _filled(128 * KIB, code)], memory_limit=LIMIT, mpl_data=True)
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    err = r.stderr.decode(errors="replace").strip().splitlines()
    note(f"stdout {r.text.strip()!r}; stderr's last line {err[-1] if err else ''!r}")


@pytest.mark.parametrize("which", WHICH)
def test_teardown_with_no_limit_stays_within_its_budget(guest, note, which) -> None:
    """With no limit, a finalizer makes and drops 1 MiB 500 times: never draining would grow the
    memory by 500 MiB; the budget drains once and teardown grows by at most the budget, the
    block and 64 KiB."""
    code = (
        "class F:\n"
        "    def __del__(self):\n"
        "        for _ in range(500):\n"
        "            b = bytearray(1 << 20)\n"
        "            del b\n"
        "f = F()\n"
    )
    grew, _ = _growth(guest, which, code)
    bound = BUDGET + MIB + 64 * KIB
    note(f"teardown grew the memory by {grew:,} bytes")
    assert grew <= bound, f"teardown grew the memory by {grew:,} bytes ({bound:,})"


# Criterion (c): the hook arms only after atexit.

# 64 KiB pieces, each under the budget, so a hook armed too early would keep sixteen of them
# before its count drained them.
ATEXIT_CHURN = (
    "import atexit\n"
    "def churn():\n"
    "    for _ in range(100):\n"
    "        b = bytearray(64 << 10)\n"
    "        del b\n"
)
ATEXIT = {
    "a handler": ATEXIT_CHURN + "atexit.register(churn)\n",
    "a handler registered during atexit": (
        ATEXIT_CHURN + "atexit.register(lambda: atexit.register(churn))\n"
    ),
}


@pytest.mark.parametrize("which", WHICH)
@pytest.mark.parametrize("case", ATEXIT)
def test_atexit_handlers_free_as_before(guest, note, which, case) -> None:
    """An `atexit` handler that makes and drops 64 KiB a hundred times frees as before: frees
    stop only once Python is finalizing, after the last handler, those registered during `atexit`
    included. The program first takes every free block of 64 KiB or more the heap has, then frees
    one, so the handler reuses it as native does, where a hook armed too early would grow the
    memory by the sixteen pieces it kept."""
    code = ATEXIT[case] + (
        "keep = [bytearray(64 << 10) for _ in range(400)]\nspare = bytearray(64 << 10)\ndel spare\n"
    )
    grew, _ = _growth(guest, which, code)
    note(f"teardown grew the memory by {grew:,} bytes")
    assert grew <= 64 * KIB, f"teardown grew the memory by {grew:,} bytes (65,536)"


# Native behaviour: each probe's outcome, equal to native CPython 3.15.2's (run with -I in an
# empty folder): (how it runs, the program, stdout with each newline as "/", the exit code, the
# kinds of thing stderr says, the files it leaves).

D = "class D:\n    def __init__(s, n): s.n = n\n    def __del__(s): print('del', s.n)\n"
IMPORTS = (
    "class E:\n    def __del__(s):\n        try:\n"
    "            import fractions; print('import ok')\n"
    "        except Exception as x: print('import failed', type(x).__name__)\n"
)
SCANDIR = (
    "import os, json, warnings\nwarnings.simplefilter('always')\n"
    "for n in 'xy': open(n + '.txt', 'w').close()\n"
)
FILE = "f = open('a.txt', 'w'); f.write('x' * 100)\ndef g(): pass\n"
PROBES = {
    "unclosed file": ("c", "f = open('a.txt', 'w'); f.write('x' * 100)", "", 0, "", "a.txt:100"),
    "unclosed file and a def": ("c", FILE, "", 0, "", "a.txt:100"),
    "ZipFile left open and a def": (
        "c",
        "import zipfile\nz = zipfile.ZipFile('a.zip', 'w'); z.writestr('m', 'x' * 10)\n"
        "def g(): pass",
        "",
        0,
        "",
        "a.zip:ok",
    ),
    "a script: unclosed file and a def": ("script", FILE, "", 0, "", "a.txt:100"),
    "-m: unclosed file and a def": ("m", FILE, "", 0, "", "a.txt:100"),
    "gzip left open and a def": (
        "c",
        "import gzip\ng = gzip.open('a.gz', 'wb'); g.write(b'x' * 1000)\ndef h(): pass",
        "",
        0,
        "Exception ignored,Error",
        "a.gz:BAD",
    ),
    "atexit order": (
        "c",
        "import atexit\nfor c in 'abc': atexit.register(print, c)",
        "c/b/a",
        0,
        "",
        "",
    ),  # fmt: skip
    "an atexit handler raises": (
        "c",
        "import atexit\natexit.register(print, 'after')\natexit.register(lambda: 1/0)",
        "after",
        0,
        "Exception ignored,ZeroDivisionError,Error",
        "",
    ),
    "__del__ in __main__, in order": ("c", D + "a = D(1); b = D(2)", "del 1/del 2", 0, "", ""),
    "__del__ of cyclic garbage": (
        "c",
        D + "x = D('cycle'); x.me = x; del x",
        "del cycle",
        0,
        "",
        "",
    ),  # fmt: skip
    "a weakref callback": (
        "c",
        "import weakref\nclass C: pass\nc = C()\nr = weakref.ref(c, lambda r: print('cb'))",
        "",
        0,
        "",
        "",
    ),
    "weakref.finalize": (
        "c",
        "import weakref\nclass C: pass\nc = C()\nweakref.finalize(c, print, 'fin')",
        "fin",
        0,
        "",
        "",
    ),
    "a suspended generator's finally": (
        "c",
        "def gen():\n    try:\n        yield 1\n    finally:\n        print('gen closed')\n"
        "g = gen(); next(g)",
        "gen closed",
        0,
        "",
        "",
    ),
    "__del__ hung on a pre-imported module": (
        "c",
        D + "import json\njson.hung = D('json-hung')",
        "del json-hung",
        0,
        "",
        "",
    ),
    "a file hung on a pre-imported module": (
        "c",
        "import json\njson.log = open('a.txt', 'w'); json.log.write('x' * 100)",
        "",
        0,
        "",
        "a.txt:100",
    ),
    "a ZipFile hung on a pre-imported module": (
        "c",
        "import json, zipfile\njson.z = zipfile.ZipFile('a.zip', 'w')\n"
        "json.z.writestr('m', 'x' * 10)",
        "",
        0,
        "",
        "a.zip:ok",
    ),
    "a pre-imported class patched": (
        "c",
        "import json\nf = open('a.txt', 'w'); f.write('x' * 100)\n"
        "def default(self, o): return str(o)\njson.JSONEncoder.default = default",
        "",
        0,
        "",
        "a.txt:100",
    ),
    "__del__ hung on a module imported later": (
        "c",
        D + "import fractions\nfractions.hung = D('fractions-hung')",
        "del fractions-hung",
        0,
        "",
        "",
    ),  # fmt: skip
    "a weakref callback on a pre-imported class": (
        "c",
        "import weakref, json\nclass K(json.JSONEncoder): pass\n"
        "r = weakref.ref(K, lambda r: print('cb class'))\njson.keep = r",
        "",
        0,
        "",
        "",
    ),
    "streams without a newline": (
        "c",
        "import sys\nsys.stdout.write('out no newline'); sys.stderr.write('err no newline')",
        "out no newline",
        0,
        "err no newline",
        "",
    ),
    "stdout replaced by a file": (
        "c",
        "import sys\nsys.stdout = open('out.txt', 'w')\nprint('hi')",
        "",
        0,
        "",
        "out.txt:3",
    ),
    "sys.exit(3)": ("c", "import sys\nsys.exit(3)", "", 3, "", ""),
    "SystemExit('bye')": ("c", "raise SystemExit('bye')", "", 1, "bye", ""),
    "an uncaught exception": ("c", "1/0", "", 1, "ZeroDivisionError,Error", ""),
    "a stdout whose flush fails": (
        "c",
        "import sys\nclass W:\n    def write(s, x): return len(x)\n"
        "    def flush(s): raise OSError('no')\nsys.stdout = W()",
        "",
        120,
        "Exception ignored,OSError,Error",
        "",
    ),
    "a logging MemoryHandler": (
        "c",
        "import logging, logging.handlers\n"
        "h = logging.handlers.MemoryHandler(100, target=logging.FileHandler('log.txt'))\n"
        "logging.getLogger().addHandler(h)\nlogging.warning('w')",
        "",
        0,
        "",
        "log.txt:2",
    ),
    "a NamedTemporaryFile left open": (
        "c",
        "import tempfile\nt = tempfile.NamedTemporaryFile(dir='.', prefix='tmp')",
        "",
        0,
        "",
        "",
    ),  # fmt: skip
    "a TemporaryDirectory left": (
        "c",
        "import tempfile\nd = tempfile.TemporaryDirectory(dir='.', prefix='tmpd')",
        "",
        0,
        "",
        "",
    ),  # fmt: skip
    "an uncommitted sqlite3 insert": (
        "c",
        "import sqlite3\nc = sqlite3.connect('t.db')\nc.execute('create table t(x)'); c.commit()\n"
        "c.execute('insert into t values (1)')",
        "",
        0,
        "",
        "t.db:rows=0",
    ),
    "an audit hook holds a file": (
        "c",
        "import sys\ndef make():\n    f = open('a.txt', 'w'); f.write('x' * 100)\n"
        "    return lambda *a: f\nsys.addaudithook(make())",
        "",
        0,
        "",
        "a.txt:100",
    ),
    "__del__ sees sys.modules": (
        "c",
        "import sys\nclass E:\n"
        "    def __del__(s): print('json is', type(sys.modules.get('json')).__name__)\ne = E()",
        "json is NoneType",
        0,
        "",
        "",
    ),
    "__del__ imports": ("c", IMPORTS + "e = E()", "import failed ImportError", 0, "", ""),
    "__del__ of a cycle that imports": (
        "c",
        IMPORTS + "e = E(); e.me = e; del e",
        "import ok",
        0,
        "",
        "",
    ),
    "atexit, then __del__": (
        "c",
        D + "import atexit\natexit.register(print, 'atexit')\nd = D('main')",
        "atexit/del main",
        0,
        "",
        "",
    ),  # fmt: skip
    "__del__ sees a global module": (
        "c",
        "import os\nclass E:\n    def __del__(s): print('sep', repr(os.sep))\ne = E()",
        "sep '/'",
        0,
        "",
        "",
    ),  # fmt: skip
    "an audit hook sees teardown": (
        "c",
        "import sys\n"
        "sys.addaudithook(lambda e, a: print(e) if e.startswith('cpython._PySys') else None)",
        "",
        0,
        "",
        "",
    ),
    "gc.callbacks": (
        "c",
        "import gc\n"
        "gc.callbacks.append(lambda phase, info: print('gc', phase) if phase == 'stop' else None)",
        "gc stop",
        0,
        "",
        "",
    ),
    "a profiler set": (
        "c",
        "import sys\nn = []\nsys.setprofile(lambda f, e, a: n.append(e))\n"
        "atexit = __import__('atexit')\natexit.register(lambda: print('calls so far', len(n) > 0))",
        "calls so far True",
        0,
        "",
        "",
    ),
    "__stdout__ written, stdout replaced": (
        "c",
        "import sys\nsys.__stdout__.write('dunder no newline')\nsys.stdout = sys.stderr",
        "dunder no newline",
        0,
        "",
        "",
    ),
    "__del__ on an untracked instance": (
        "c",
        "import gc\nclass E:\n    __slots__ = ()\n    def __del__(s): print('del slots')\ne = E()\n"
        "import sys; print('tracked', gc.is_tracked(e), file=sys.stderr)",
        "del slots",
        0,
        "",
        "",
    ),
    "a profiler watches teardown": (
        "c",
        "import sys\nsys.setprofile(lambda f, e, a: sys.__stderr__.write('P') "
        "if e == 'call' and f.f_code.co_name == '__del__' else None)\n"
        "class E:\n    def __del__(s): pass\ne = E()",
        "",
        0,
        "",
        "",
    ),
    "a StringIO and a closed file left": (
        "c",
        "import io\ns = io.StringIO('x')\nf = open('a.txt', 'w'); f.write('y'); f.close()\n"
        "print('ok')",
        "ok",
        0,
        "",
        "a.txt:1",
    ),
    "a sys.monitoring tool": (
        "c",
        "import sys\nm = sys.monitoring\nm.use_tool_id(3, 'probe')\n"
        "m.register_callback(3, m.events.PY_START, lambda code, off: print('start', code.co_name)"
        " if code.co_name == '_remove' else None)\nm.set_events(3, m.events.PY_START)",
        "",
        0,
        "",
        "",
    ),
    "scandir left open, warnings on": (
        "c",
        SCANDIR + "it = os.scandir('.')\nnext(it, None)\nprint('ok')",
        "ok",
        0,
        "ResourceWarning",
        "x.txt:0 y.txt:0",
    ),  # fmt: skip
    "scandir hung on a pre-imported module": (
        "c",
        SCANDIR + "json.it = os.scandir('.')\nnext(json.it, None)\nprint('ok')",
        "ok",
        0,
        "ResourceWarning",
        "x.txt:0 y.txt:0",
    ),  # fmt: skip
    "tracemalloc tracing at the end": (
        "c",
        "import tracemalloc\ntracemalloc.start()\n" + FILE + "print('tracing', "
        "tracemalloc.is_tracing())",
        "tracing True",
        0,
        "",
        "a.txt:100",
    ),
    "tracemalloc stopped by an atexit handler": (
        "c",
        "import atexit, tracemalloc\ntracemalloc.start()\natexit.register(tracemalloc.stop)\n"
        + FILE
        + "print('tracing', tracemalloc.is_tracing())",
        "tracing True",
        0,
        "",
        "a.txt:100",
    ),
    "tracemalloc started in teardown": (
        "c",
        "import tracemalloc\nclass E:\n    def __del__(s, t=tracemalloc):\n        t.start()\n"
        "        x = [bytes(100) for _ in range(1000)]\n"
        "        print('traced', t.get_traced_memory()[0] > 0)\ne = E()\n" + FILE,
        "traced True",
        0,
        "",
        "a.txt:100",
    ),
}
STDERR_KINDS = (
    "Exception ignored",
    "ZeroDivisionError",
    "bye",
    "OSError",
    "err no newline",
    "ResourceWarning",
    "Error",
)


def _stderr_kinds(err: str) -> str:
    kinds: list[str] = []
    for line in err.splitlines():
        kinds += [k for k in STDERR_KINDS if k in line and k not in kinds]
    return ",".join(kinds)


def _left(root: Path) -> str:
    """The files a probe left, each with what matters of it."""
    out = []
    for p in sorted(root.iterdir()):
        n = p.name
        if n in ("prog.py", "__pycache__", "usr", "code"):
            continue
        if n.startswith("tmp"):
            out.append("tmp*")
        elif n.endswith(".zip"):
            try:
                out.append(n + (":ok" if zipfile.ZipFile(p).read("m") else ":BAD"))
            except Exception:
                out.append(n + ":BAD")
        elif n.endswith(".gz"):
            try:
                out.append(n + (":ok" if len(gzip.open(p).read()) == 1000 else ":short"))
            except Exception:
                out.append(n + ":BAD")
        elif n == "t.db":
            rows = sqlite3.connect(p).execute("select count(*) from t").fetchone()[0]
            out.append(f"{n}:rows={rows}")
        else:
            out.append(f"{n}:{p.stat().st_size}")
    return " ".join(out)


@pytest.mark.parametrize("which", WHICH)
@pytest.mark.parametrize("probe", PROBES)
def test_a_probe_ends_as_native(guest, which, probe) -> None:
    """Every finalizer, `atexit` handler, flush and warning of teardown still runs, in CPython's
    order: the probe's stdout, exit code, stderr's kinds and files equal native CPython's."""
    how, code, stdout, rc, kinds, files = PROBES[probe]
    argv = {"c": ["-c", code], "script": ["/prog.py"], "m": ["-c", IMPORT_PATH, "-m", "prog"]}
    extra = {"script": {"files": {"/prog.py": code}}, "m": {"files": {"/code/prog.py": code}}}
    r = guest(which, argv[how], **extra.get(how, {}))
    assert r.trapped is None, r.describe()
    got = (
        r.text.strip().replace("\n", "/"),
        r.exit_code,
        _stderr_kinds(r.stderr.decode(errors="replace")),
        _left(r.root),
    )
    assert got == (stdout, rc, kinds, files), got


# What the runner's import path does: /code on sys.path, then the rest of argv run as a call.
IMPORT_PATH = (
    "__import__('sys').path.extend(['/code']) or __import__('sys').exit(__import__('_reactor')"
    ".run(['/usr/local/bin/python.wasm', *__import__('sys').argv[1:]], dict(__import__('os')"
    ".environ)))"
)
SESSION = (
    "f = open('a.txt', 'w'); f.write('x' * 100)\ndef g(): pass\nimport atexit\n"
    "atexit.register(lambda: open('b.txt', 'w').write('atexit'))\n",
    "class D:\n    def __del__(s): open('c.txt', 'w').write('del')\nd = D()\nimport json\n"
    "json.keep = open('e.txt', 'w'); json.keep.write('y' * 50)\n",
)


@pytest.mark.parametrize("which", WHICH)
def test_a_sessions_shutdown_ends_as_native(guest_turns, which) -> None:
    """A session's turns leave an unclosed file beside a function, an `atexit` handler that
    writes a file, a finalizer that writes one and a file hung on a pre-imported module: its
    shutdown ends as native's end of the same code does, three files kept and the finalizer's
    `open` gone with the builtins it ran after."""
    t = guest_turns(which)
    for code in SESSION:
        assert t.turn(code).value == 0
    end = t.shutdown()
    assert end.value == 0, end.describe()
    left = {p.name: p.stat().st_size for p in t.root.iterdir() if p.suffix == ".txt"}
    assert left == {"a.txt": 100, "b.txt": 6, "e.txt": 50}, left
    assert _stderr_kinds(end.stderr.decode(errors="replace")) == "Exception ignored,Error"


# The cost, as counts.

# Teardown's fuel on a bare call, each binary: 19.8 M and 33.8 M measured at the first build, with
# the zip's directory kept past teardown; 23.3 M and 40.1 M with the directory kept and every free
# made, 39.1 M and 53.3 M before either.
TEARDOWN_FUEL = {"plain": 22_000_000, "snapshot": 36_000_000}


@pytest.mark.parametrize("which", WHICH)
def test_a_bare_calls_teardown_costs_less(guest, note, which) -> None:
    """A bare call's teardown, its fuel less the same call ended by `os._exit(0)`, is under its
    bound: it no longer returns memory to an instance about to be discarded."""
    early = guest(which, ["-c", _ended_early("pass\n")], record=False)
    full = guest(which, ["-c", "pass\n"])
    assert early.exit_code == 0 and full.exit_code == 0, (early.describe(), full.describe())
    teardown = full.fuel - early.fuel
    note(f"teardown {teardown:,} fuel of a bare call's {full.fuel:,}")
    bound = TEARDOWN_FUEL[which]
    assert teardown <= bound, f"a bare call's teardown costs {teardown:,} fuel ({bound:,})"


GROUPBY = GROWS["a pandas groupby"]


@pytest.mark.parametrize("which", WHICH)
@pytest.mark.parametrize("program", ["a bare call", "a pandas groupby"])
def test_the_wrappers_cost_on_a_call_that_never_finalizes(guest, which, program) -> None:
    """A call ended by `os._exit(0)` runs no teardown, so its fuel is the program's and the
    unarmed wrappers': one flag checked per allocation. Recorded, so a change that grows it is
    listed with its reason."""
    code = "pass\n" if program == "a bare call" else GROUPBY
    r = guest(which, ["-c", _ended_early(code)])
    assert r.exit_code == 0, r.describe()


# Coverage, read from both binaries.

ALLOCATORS = ("malloc", "calloc", "realloc", "aligned_alloc", "posix_memalign")
# musl's own names for malloc and calloc are aliases: one function, so their wrappers call it too.
WRAPPERS = {
    "malloc": {"__wrap_malloc", "__wrap___libc_malloc"},
    "calloc": {"__wrap_calloc", "__wrap___libc_calloc"},
    "realloc": {"__wrap_realloc"},
    "aligned_alloc": {"__wrap_aligned_alloc"},
    "posix_memalign": {"__wrap_posix_memalign"},
}
# Who calls sbrk, the one function that grows the memory: dlmalloc, the C library's allocator, and
# mimalloc's page allocator, which CPython compiles in and never selects in this build (no
# pymalloc, no free threading: every domain is malloc's).
SBRK_CALLERS = {"dlmalloc", "_mi_prim_alloc"}


@pytest.mark.parametrize("which", WHICH)
def test_only_the_wrappers_call_the_c_allocators(artifacts, which) -> None:
    """Every allocation teardown makes is counted: the only direct callers of the C library's
    allocators are their wrappers, none of them is in the function table, exported or named by
    `ref.func`, and only sbrk grows the memory, called by the allocators alone."""
    needs.need("artifact dir")
    from harness import instructions, wasm

    mod = wasm.parse_file(artifacts.binary(which))
    by_name = {name: index for index, name in mod.names.items()}
    read = instructions.read_all(mod)
    callers: dict[int, set[str]] = {}
    refs: set[int] = set()
    for index, body in read.items():
        for target in body.calls:
            callers.setdefault(target, set()).add(mod.names.get(index, f"#{index}"))
        refs |= body.refs
    present = [name for name in ALLOCATORS if name in by_name]
    assert {"malloc", "calloc", "realloc"} <= set(present), present
    for name in present:
        index = by_name[name]
        assert callers.get(index, set()) <= WRAPPERS[name], (name, callers.get(index))
        assert index not in mod.elements.values(), f"{name} is in the function table"
        assert index not in refs and mod.export_index.get(name) != index, name
    growers = sorted(mod.names.get(i, f"#{i}") for i, body in read.items() if body.grows)
    assert growers == ["sbrk"], growers
    assert callers.get(by_name["sbrk"], set()) == SBRK_CALLERS, callers.get(by_name["sbrk"])


HOOKS = {"skipping_malloc", "skipping_calloc", "skipping_realloc", "skipping_free"}


@pytest.mark.parametrize("which", WHICH)
def test_no_hook_sits_where_the_callback_scan_reads_a_method(artifacts, which) -> None:
    """The callback scan reads FreeType's BDF property table, `{"ADD_STYLE_NAME", 1, 1, 0}`, as a
    method at function table index 1, called with a method's type. The hooks, found by name,
    have other types, so none may sit there; what does must take a method's arguments."""
    needs.need("artifact dir")
    from harness import wasm

    mod = wasm.parse_file(artifacts.binary(which))
    placed = {mod.names.get(f): t for t, f in mod.elements.items() if mod.names.get(f) in HOOKS}
    assert set(placed) == HOOKS, placed
    assert 1 not in placed.values(), f"a hook sits at table index 1: {placed}"
    method = wasm.FuncType(("i32", "i32"), ("i32",))
    first = mod.elements[1]
    assert mod.func_type(first) == method, (mod.names.get(first), mod.func_type(first))
