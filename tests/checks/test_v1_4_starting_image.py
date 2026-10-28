"""v1.4: a starting image the embedder chooses.

An embedder makes a snapshot from its own code once, with `make_snapshot`, or from every package
the set ships with `make_package_snapshot`, and passes it to `run`, `run_async` or `Session`.
Every check here goes through the public API on the built set, and each records a call's
`fuel_used` as its metric: a count, never a time. A snapshot is made once per module where
several checks share one."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from harness import needs, wat

pytestmark = pytest.mark.goal("v1.4")
FUEL = 10**12  # a cap that is never reached: it makes each call report its fuel

SALES = "region,total\nnorth,10\nsouth,5\nnorth,7\neast,3\n"
PROBE_CODE = (
    "import pandas as pd\n"
    "from sklearn.datasets import load_iris\n"
    "from sklearn.tree import DecisionTreeClassifier\n"
    "df = pd.read_csv('/data/sales.csv')\n"
    "iris = load_iris()\n"
    "model = DecisionTreeClassifier(random_state=0).fit(iris.data, iris.target)\n"
    "def summarize(frame):\n"
    "    return frame.describe().round(3).to_string()\n"
)
PROBE_PROGRAM = (
    "print(summarize(df))\n"
    "print(model.predict(iris.data[[0, 60, 120]]))\n"
    "print(df.groupby('region').total.sum())\n"
)
NAMESPACE_CODE = "x = 1\ndef f():\n    return x\n"


def _wp():
    needs.need("runner", "artifact dir")
    import wasi_python

    return wasi_python


def _folder(guest_workdir: Path, prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix, dir=guest_workdir))


def _data(guest_workdir: Path) -> Path:
    folder = _folder(guest_workdir, "data-")
    (folder / "sales.csv").write_text(SALES)
    return folder


def _ok(done) -> None:
    assert (done.exit_code, done.trapped) == (0, None), done


@pytest.fixture(scope="module")
def namespace_snapshot():
    return _wp().make_snapshot(NAMESPACE_CODE)


def test_a_snapshot_runs_like_a_fresh_run(guest_workdir, metric, fact) -> None:
    """The spike's probe: live objects made by the code, a frame, a fitted model and a function,
    used by a program from the snapshot, print exactly what one program of both prints."""
    wp = _wp()
    grants = [wp.Grant(_data(guest_workdir), "/data")]
    snap = wp.make_snapshot(PROBE_CODE, grants=grants)
    restored = wp.run(["-c", PROBE_PROGRAM], grants=grants, snapshot=snap, fuel=FUEL)
    fresh = wp.run(["-c", PROBE_CODE + PROBE_PROGRAM], grants=grants, fuel=FUEL, deadline_s=None)
    _ok(restored)
    _ok(fresh)
    assert restored.stdout == fresh.stdout and b"north" in restored.stdout, (restored, fresh)
    assert restored.image_sha256 == snap.origin.image_sha256 and fresh.image_sha256 is None
    assert restored.fuel_used < fresh.fuel_used // 10, (restored.fuel_used, fresh.fuel_used)
    fact("fresh_fuel", fresh.fuel_used)
    metric("fuel", restored.fuel_used)


def test_a_call_sees_no_other_calls_mutations(metric) -> None:
    wp = _wp()
    code = (
        "import builtins, sys\nimport numpy\nimport pandas\n"
        "items = [1]\nframe = pandas.DataFrame({'a': [1, 2]})\n"
    )
    snap = wp.make_snapshot(code)
    first = wp.run(
        [
            "-c",
            "items.append(2); frame['b'] = 3; numpy.sum = None\n"
            "del sys.modules['pandas']; builtins.LEAK = 1\nprint(items, list(frame.columns))",
        ],
        snapshot=snap,
    )
    _ok(first)
    assert first.stdout == b"[1, 2] ['a', 'b']\n", first
    second = wp.run(
        [
            "-c",
            "print(items, list(frame.columns), numpy.sum is None, 'pandas' in sys.modules,"
            " hasattr(builtins, 'LEAK'))",
        ],
        snapshot=snap,
        fuel=FUEL,
    )
    _ok(second)
    assert second.stdout == b"[1] ['a'] False True False\n", second
    metric("fuel", second.fuel_used)


def test_a_snapshot_that_leaves_a_file_open_is_refused(guest_workdir) -> None:
    wp = _wp()
    grants = [wp.Grant(_data(guest_workdir), "/data")]
    with pytest.raises(wp.SnapshotFailed) as failed:
        wp.make_snapshot("kept = open('/data/sales.csv')\n", grants=grants)
    assert failed.value.reason == "open file", failed.value
    assert "left 1 file open" in str(failed.value)
    assert failed.value.completed.exit_code == 0


def test_a_failing_snapshot_says_why() -> None:
    wp = _wp()
    with pytest.raises(wp.SnapshotFailed) as failed:
        wp.make_snapshot("import no_such_module\n")
    assert failed.value.reason == "exit", failed.value
    assert b"no_such_module" in failed.value.completed.stderr
    assert "status 1: ModuleNotFoundError: No module named 'no_such_module'" in str(failed.value)
    waits = "import time\nclock = getattr(time, 'monotonic')\nstart = clock()\n"
    waits += "while clock() - start < 1:\n    pass\n"
    with pytest.raises(wp.SnapshotFailed) as looped:
        wp.make_snapshot(waits, fuel=10**8)
    assert looped.value.reason == "trapped", looped.value
    assert looped.value.completed.trapped == "out of fuel"


def test_a_call_does_not_keep_the_makings_import_path(guest_workdir, metric) -> None:
    wp = _wp()
    src = _folder(guest_workdir, "src-")
    (src / "mod_a.py").write_text("NAME = 'a'\n")
    snap = wp.make_snapshot("import mod_a\n", grants=[wp.Grant(src, "/src")], import_path=["/src"])
    planted = _folder(guest_workdir, "planted-")
    (planted / "extra.py").write_text("print('planted code ran')\n")
    done = wp.run(
        ["-c", "import sys\nprint('/src' in sys.path, mod_a.NAME)\nimport extra\n"],
        grants=[wp.Grant(planted, "/src", writable=True)],
        snapshot=snap,
        fuel=FUEL,
    )
    assert done.exit_code == 1 and done.stdout == b"False a\n", done
    assert b"ModuleNotFoundError: No module named 'extra'" in done.stderr, done
    metric("fuel", done.fuel_used)


def test_a_program_shares_the_codes_namespace(namespace_snapshot, metric) -> None:
    wp = _wp()
    program = "x = 2; print(f())"
    restored = wp.run(["-c", program], snapshot=namespace_snapshot, fuel=FUEL)
    one = wp.run(["-c", NAMESPACE_CODE + program])
    _ok(restored)
    assert restored.stdout == one.stdout == b"2\n", (restored, one)
    with wp.Session() as session:
        _ok(session.run(NAMESPACE_CODE))
        turn = session.run(program)
    assert turn.stdout == b"2\n", turn
    metric("fuel", restored.fuel_used)


def test_home_is_the_images_and_each_calls_own(guest_workdir, metric) -> None:
    wp = _wp()
    snap = wp.make_snapshot("import os\nmade_home = os.environ['HOME']\n")
    root = _folder(guest_workdir, "root-")
    first = wp.run(
        ["-c", "print(made_home, os.environ['HOME'])\nopen(os.path.expanduser('~/mark'), 'w')"],
        root=str(root),
        snapshot=snap,
    )
    second = wp.run(
        ["-c", "print(os.environ['HOME'], os.path.exists(os.path.expanduser('~/mark')))"],
        root=str(root),
        snapshot=snap,
        fuel=FUEL,
    )
    _ok(first)
    _ok(second)
    assert first.stdout == b"/tmp/.home-snapshot /tmp/.home-snapshot\n", first
    assert second.stdout == b"/tmp/.home-snapshot False\n", second
    assert not (root / "tmp" / ".home-snapshot").exists()  # never in the shared root
    metric("fuel", second.fuel_used)


def test_grants_in_another_order_work(guest_workdir, metric) -> None:
    wp = _wp()
    folders = {}
    for name in ("a", "b", "c"):
        folders[name] = _folder(guest_workdir, f"grant-{name}-")
        (folders[name] / "which.txt").write_text(name)
    made = [wp.Grant(folders["a"], "/a"), wp.Grant(folders["b"], "/b")]
    snap = wp.make_snapshot("import os\n", grants=made)
    later = [wp.Grant(folders[n], f"/{n}") for n in ("b", "a", "c")]
    program = "print(*(open(f'/{n}/which.txt').read() for n in 'abc'))"
    done = wp.run(["-c", program], grants=later, snapshot=snap, fuel=FUEL)
    _ok(done)
    assert done.stdout == b"a b c\n", done
    metric("fuel", done.fuel_used)


def test_randomness_differs_across_calls(metric) -> None:
    wp = _wp()
    snap = wp.make_snapshot("import random, tempfile\nimport numpy.random\nimport sympy\n")
    program = (
        "import sympy.core.random\n"
        "print(random.random(), numpy.random.random(), sympy.core.random.rng.random(),"
        " next(tempfile._get_candidate_names()))"
    )
    first = wp.run(["-c", program], snapshot=snap)
    second = wp.run(["-c", program], snapshot=snap, fuel=FUEL)
    _ok(first)
    _ok(second)
    a, b = first.stdout.split(), second.stdout.split()
    assert len(a) == len(b) == 4 and all(x != y for x, y in zip(a, b, strict=True)), (a, b)
    metric("fuel", second.fuel_used)


def test_a_call_from_a_snapshot_keeps_an_unclosed_files_bytes(
    guest_workdir, namespace_snapshot, metric
) -> None:
    wp = _wp()
    out = _folder(guest_workdir, "out-")
    program = "f = open('/out/kept.bin', 'wb'); f.write(b'x' * 100)"
    done = wp.run(
        ["-c", program],
        grants=[wp.Grant(out, "/out", writable=True)],
        snapshot=namespace_snapshot,
        fuel=FUEL,
    )
    _ok(done)
    assert (out / "kept.bin").read_bytes() == b"x" * 100
    metric("fuel", done.fuel_used)


def test_a_session_starts_from_a_snapshot(namespace_snapshot, metric) -> None:
    wp = _wp()
    first = wp.Session(snapshot=namespace_snapshot, fuel=FUEL)
    with first:
        a = first.run("y = f() + 41\nprint(y)")
        b = first.run("print(y)")
    with wp.Session(snapshot=namespace_snapshot) as second:
        c = second.run("print(f(), 'y' in globals())")
    _ok(a)
    assert (a.stdout, b.stdout, c.stdout) == (b"42\n", b"42\n", b"1 False\n"), (a, b, c)
    assert a.image_sha256 == namespace_snapshot.origin.image_sha256
    assert first.shutdown_outcome == "finished", first.shutdown_outcome
    metric("fuel", a.fuel_used)


def test_one_prelude_makes_one_image() -> None:
    wp = _wp()
    code = "import json\nTABLE = {'a': [1, 2, 3]}\n"
    one, two = wp.make_snapshot(code), wp.make_snapshot(code)
    assert one.origin.image_sha256 == two.origin.image_sha256
    assert one.origin.image_bytes == two.origin.image_bytes


def test_a_snapshot_saved_and_loaded_runs(guest_workdir, namespace_snapshot, metric) -> None:
    wp = _wp()
    path = _folder(guest_workdir, "saved-") / "app.wpsnap"
    namespace_snapshot.save(path)
    loaded = wp.Snapshot.load(path)
    assert loaded.check() is None
    assert loaded.origin == namespace_snapshot.origin
    here = wp.run(["-c", "print(f())"], snapshot=namespace_snapshot)
    there = wp.run(["-c", "print(f())"], snapshot=loaded, fuel=FUEL)
    _ok(there)
    assert there.stdout == here.stdout == b"1\n", (here, there)
    metric("fuel", there.fuel_used)


def test_another_set_is_refused(guest_workdir, namespace_snapshot) -> None:
    wp = _wp()
    found = wp.artifacts()
    other = _folder(guest_workdir, "other-set-")
    wat.build(other, "python-snapshot.wasm", wat.SNAPSHOT)
    given = wp.Artifacts(
        snapshot=other / "python-snapshot.wasm",
        plain=found.plain,
        stdlib_zip=found.stdlib_zip,
        manifest=found.manifest,
    )
    missing = wp.Grant(other / "no-such-folder", "/data")  # a walk would refuse it first
    with pytest.raises(wp.SnapshotMismatch, match="make it again with this set"):
        wp.run(["-c", "pass"], grants=[missing], artifacts=given, snapshot=namespace_snapshot)
    with pytest.raises(wp.SnapshotMismatch, match="make it again with this set"):
        namespace_snapshot.check(artifacts=given)


def test_concurrent_calls_share_one_image(namespace_snapshot, metric) -> None:
    wp = _wp()

    async def four() -> list:
        calls = [
            wp.run_async(
                ["-c", "import sys; print(sys.argv[1], f())", str(i)],
                snapshot=namespace_snapshot,
                fuel=FUEL,
            )
            for i in range(4)
        ]
        return await asyncio.gather(*calls)

    done = asyncio.run(four())
    for i, d in enumerate(done):
        _ok(d)
        assert d.stdout == f"{i} 1\n".encode(), d
    metric("fuel", max(d.fuel_used for d in done))


def test_a_restored_hello_costs_its_own_work(metric, fact) -> None:
    wp = _wp()
    before = wp.stats()
    snap = wp.make_snapshot("pass\n")
    restored = wp.run(["-c", "print('hello')"], snapshot=snap, fuel=FUEL)
    own = wp.run(["-c", "print('hello')"], fuel=FUEL)
    _ok(restored)
    assert restored.stdout == own.stdout == b"hello\n"
    assert restored.fuel_used < own.fuel_used, (restored.fuel_used, own.fuel_used)
    after = wp.stats()
    assert after["snapshots_made"] >= before["snapshots_made"] + 1
    assert after["snapshots_restored"] >= before["snapshots_restored"] + 1
    fact("own_hello_fuel", own.fuel_used)
    metric("fuel", restored.fuel_used)


PLOT = (
    "import io\nimport matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\n"
    "fig, ax = plt.subplots()\nax.plot([1, 2, 3], [3, 1, 2])\nbuf = io.BytesIO()\n"
    "fig.savefig(buf, format='png')\nprint(buf.getvalue()[:8] == b'\\x89PNG\\r\\n\\x1a\\n')\n"
)


@pytest.mark.slow
def test_the_image_of_every_package_runs_a_hello_and_a_plot(metric, fact) -> None:
    """The helper with no list imports every package the set ships; a restored hello costs
    its own work, and pyplot draws with no root. The helper given a distribution's name
    imports that line's names."""
    wp = _wp()
    every = wp.make_package_snapshot(fuel=10**13)
    hello = wp.run(["-c", "print('hello')"], snapshot=every, fuel=FUEL)
    plot = wp.run(["-c", PLOT], snapshot=every)
    _ok(hello)
    _ok(plot)
    assert (hello.stdout, plot.stdout) == (b"hello\n", b"True\n"), (hello, plot)
    tree = wp.make_package_snapshot(["scikit-learn"])
    imported = wp.run(["-c", "import sys; print('sklearn.tree' in sys.modules)"], snapshot=tree)
    assert imported.stdout == b"True\n", imported
    fact("prelude_fuel", every.origin.prelude_fuel)
    fact("image_bytes", every.origin.image_bytes)
    metric("fuel", hello.fuel_used)
