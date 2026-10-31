"""v1.4: a session's state is a snapshot.

`Session.checkpoint()` reads a live session's memory after its turns as a `Snapshot`. Any number of
sessions and calls then start from it, each from a private copy with its own grants, environment,
import path, tools, clocks and randomness, and the session goes on unchanged. Every row goes
through the public API on the built set and records fuel as a count, never a time. A row that
imports numpy keeps its fuel as a fact: numpy's random module moves a call's count by a little
from run to run.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from harness import needs

pytestmark = pytest.mark.goal("v1.4")
FUEL = 10**12  # a cap that is never reached: it makes each turn report its fuel
FIRST_DRAW = "0.13436424411240122"  # random.seed(1); random.random()

MODEL = (
    "import pandas as pd\n"
    "from sklearn.tree import DecisionTreeClassifier\n"
    "df = pd.DataFrame({'x': [1, 2, 3, 4], 'y': [0, 0, 1, 1]})\n"
    "model = DecisionTreeClassifier(random_state=0).fit(df[['x']], df.y)\n"
    "n = 7\n"
)
SEEN = "print(n, list(df.columns), model.predict(df[['x']]).tolist())"


def _wp():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python


def _folder(guest_workdir: Path, prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix, dir=guest_workdir))


def _ok(done) -> None:
    assert (done.exit_code, done.trapped) == (0, None), done


def _out(done) -> str:
    _ok(done)
    return done.stdout.decode()


def test_names_a_frame_and_a_model_carry_to_every_start(fact) -> None:
    """A checkpoint after a turn that made a frame and fitted a model starts two sessions and a
    call that see them; what one fork changes, the other, the call and the live session never
    see."""
    wp = _wp()
    with wp.Session(fuel=FUEL) as live:
        _ok(live.run(MODEL))
        cp = live.checkpoint()
        o = cp.origin
        assert (o.kind, o.parent_sha256, o.prelude, o.prelude_fuel) == (
            "checkpoint",
            None,
            "",
            None,
        )
        with wp.Session(snapshot=cp, fuel=FUEL) as a, wp.Session(snapshot=cp, fuel=FUEL) as b:
            changed = a.run("n += 1\ndf['z'] = 1\n" + SEEN)
            seen = b.run(SEEN)
        called = wp.run(["-c", SEEN], snapshot=cp, fuel=FUEL)
        after = live.run(SEEN)
    assert _out(changed) == "8 ['x', 'y', 'z'] [0, 0, 1, 1]\n"
    assert _out(seen) == _out(called) == _out(after) == "7 ['x', 'y'] [0, 0, 1, 1]\n"
    assert seen.image_sha256 == called.image_sha256 == o.image_sha256
    fact("fork_fuel", seen.fuel_used)
    fact("call_fuel", called.fuel_used)


def test_randomness_and_the_environment_are_each_starts_own(fact) -> None:
    """A checkpoint changes nothing in the live session: its next draw follows its own seed and
    its environment keeps the turn's change. Each start reseeds the module generators and reads
    its own environment; a generator held in a name draws the same in both."""
    wp = _wp()
    with wp.Session(env={"K": "0"}, fuel=FUEL) as live:
        setup = (
            "import os, random\nimport numpy as np\n"
            "rng = np.random.default_rng()\nrandom.seed(1)\nos.environ['K'] = '1'\n"
        )
        _ok(live.run(setup))
        cp = live.checkpoint()
        draw = "print(random.random(), rng.random(), os.environ.get('K'))"
        mine = _out(live.run(draw)).split()
        with wp.Session(snapshot=cp, fuel=FUEL) as a, wp.Session(snapshot=cp, fuel=FUEL) as b:
            drawn = a.run(draw)
            first, second = _out(drawn).split(), _out(b.run(draw)).split()
    assert (mine[0], mine[2]) == (FIRST_DRAW, "1"), mine
    assert first[0] != second[0], (first, second)
    assert first[1] == second[1] == mine[1], (first, second, mine)
    assert first[2] == second[2] == "None", (first, second)
    fact("fork_fuel", drawn.fuel_used)


def test_an_open_file_is_refused_and_the_session_goes_on(metric) -> None:
    """A file a turn left open refuses the checkpoint before any guest code, with no
    `Completed`, and the session goes on; once the turn closes it, the checkpoint is made."""
    wp = _wp()
    with wp.Session(root=True, fuel=FUEL) as live:
        _ok(live.run("f = open('/tmp/kept.txt', 'w')\nf.write('x')\n"))
        with pytest.raises(wp.SnapshotFailed) as refused:
            live.checkpoint()
        assert refused.value.reason == "open file" and refused.value.completed is None
        assert "1 file open" in str(refused.value)
        assert live.ended is None
        closed = live.run("f.close()\nprint(open('/tmp/kept.txt').read())")
        assert _out(closed) == "x\n"
        cp = live.checkpoint()
        with wp.Session(snapshot=cp, root=True, fuel=FUEL) as fork:
            done = fork.run("print(f.closed)")
    assert _out(done) == "True\n"
    metric("fuel", done.fuel_used)


def test_a_fork_imports_from_its_own_path_only(guest_workdir, metric) -> None:
    """A start's import path is its own: a fork granted writing where the session imported from
    cannot import a module planted there, since the session's path is gone."""
    wp = _wp()
    lib = _folder(guest_workdir, "lib-")
    (lib / "shipped.py").write_text("WHERE = 'shipped'\n")
    plant = _folder(guest_workdir, "plant-")
    (plant / "planted.py").write_text("WHERE = 'planted'\n")
    with wp.Session(grants=[wp.Grant(lib, "/lib")], import_path=["/lib"], fuel=FUEL) as live:
        _ok(live.run("import shipped\nimport sys"))
        cp = live.checkpoint()
    granted = [wp.Grant(plant, "/lib", writable=True)]
    with wp.Session(snapshot=cp, grants=granted, fuel=FUEL) as fork:
        done = fork.run("print(shipped.WHERE, '/lib' in sys.path)\nimport planted")
    assert done.stdout == b"shipped False\n", done
    assert done.exit_code == 1 and b"No module named 'planted'" in done.stderr, done
    metric("fuel", done.fuel_used)


def test_the_monotonic_clock_never_runs_backwards(fact) -> None:
    """After a turn that slept 2 s, a fork's monotonic clock reads no time below the session's
    last, and a short sleep there ends well inside a 1 s deadline: its absolute deadline is
    read in the fork's own time."""
    wp = _wp()
    with wp.Session(fuel=FUEL) as live:
        slept = "import time\nclock = getattr(time, 'monotonic')\ntime.sleep(2)\nlast = clock()"
        _ok(live.run(slept))
        cp = live.checkpoint()
    with wp.Session(snapshot=cp, fuel=FUEL, deadline_s=1) as fork:
        done = fork.run("now = clock()\ntime.sleep(0.01)\nprint(now >= last, clock() > now)")
    assert _out(done) == "True True\n"
    fact("fuel", done.fuel_used)  # a sleep's waits: not exact


def test_a_checkpoint_of_a_fork_holds_both_turns(guest_workdir, metric) -> None:
    """A fork's checkpoint holds the session's turn and its own, names the first checkpoint as its
    parent, and starts again once saved and loaded."""
    wp = _wp()
    with wp.Session(fuel=FUEL) as live:
        _ok(live.run("a = 1"))
        first = live.checkpoint()
    with wp.Session(snapshot=first, fuel=FUEL) as fork:
        _ok(fork.run("b = 2"))
        second = fork.checkpoint()
    assert second.origin.parent_sha256 == first.origin.image_sha256
    assert second.origin.home == first.origin.home
    path = _folder(guest_workdir, "saved-") / "fork.wpsnap"
    second.save(path)
    loaded = wp.Snapshot.load(path)
    assert loaded.origin == second.origin and loaded.check() is None
    with wp.Session(snapshot=loaded, fuel=FUEL) as again:
        done = again.run("print(a, b)")
    called = wp.run(["-c", "print(a, b)"], snapshot=loaded, fuel=FUEL)
    assert _out(done) == _out(called) == "1 2\n"
    metric("fuel", done.fuel_used + called.fuel_used)


def test_a_hook_carries_and_tools_are_each_starts_own(metric) -> None:
    """A turn's hook on `builtins.print` runs in every fork, with the fork's own grants and tools;
    a tool the fork lacks answers `unknown_tool`, judged by the fork's host."""
    wp = _wp()

    def ping() -> str:
        """Answer pong."""
        return "pong"

    def other() -> str:
        """Answer other."""
        return "other"

    hook = (
        "import builtins\nfrom host import tools\n_print = builtins.print\n"
        "def hooked(*a, **k):\n    _print('hooked', *a, **k)\n"
        "builtins.print = hooked\nprint(tools.ping())"
    )
    with wp.Session(tools=[ping], fuel=FUEL) as live:
        assert _out(live.run(hook)) == "hooked pong\n"
        cp = live.checkpoint()
    with wp.Session(snapshot=cp, tools=[other], fuel=FUEL) as fork:
        code = "try:\n    tools.ping()\nexcept Exception as e:\n    print(e.kind)"
        done = fork.run(code)
    assert _out(done) == "hooked unknown_tool\n"
    metric("fuel", done.fuel_used)


def test_the_refusals_leave_the_session_as_it_was(guest_workdir, metric) -> None:
    """Before a turn returned, from inside a running turn, on the plain binary and once the
    session has ended, `checkpoint()` raises by its type and runs no guest code."""
    wp = _wp()
    with wp.Session(snapshot=False) as plain:
        _ok(plain.run("pass"))
        with pytest.raises(ValueError, match="snapshot binary"):
            plain.checkpoint()
    raised: list[BaseException] = []
    session: list = []

    def inside() -> str:
        """Checkpoint the session from inside its own turn."""
        try:
            session[0].checkpoint()
        except BaseException as e:  # recorded for the row
            raised.append(e)
        return "done"

    with wp.Session(tools=[inside], fuel=FUEL) as live:
        session.append(live)
        with pytest.raises(RuntimeError, match="a turn that returned"):
            live.checkpoint()
        done = live.run("from host import tools\nprint(tools.inside())")
        assert _out(done) == "done\n"
        assert len(raised) == 1 and isinstance(raised[0], RuntimeError), raised
        assert "already running" in str(raised[0])
        assert live.ended is None
    with pytest.raises(wp.SessionEnded):
        live.checkpoint()
    metric("fuel", done.fuel_used)
