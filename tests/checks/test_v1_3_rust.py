"""v1.3: Rust, built in: orjson, pydantic-core and the build's own probe module are compiled into
both binaries from one umbrella library, a panic behind PyO3 raises `PanicException` and the run
goes on, a panic where nothing can catch it ends the call with its message, and Rust's standard
library and pydantic-core's hash keys draw their entropy through the same wrap as CPython's while
an image is prepared.

`_rust_probe` is the build's own module: it panics on purpose and builds a standard `HashMap`, so
these rows reach Rust's panic and entropy paths without depending on what orjson happens to do.
"""

from __future__ import annotations

import json

import pytest

from harness import jobs

pytestmark = pytest.mark.goal("v1.3")

BINARY = pytest.mark.parametrize("which", ["plain", "snapshot"])


@pytest.mark.slow
def test_orjson_json_job_matches_native(guest) -> None:
    """orjson's dumps with its sorting, indenting, non-string-key, numpy and passthrough options,
    over datetimes, UUIDs, dataclasses, enums, 64-bit integers and text from several scripts, its
    loads, a Fragment, both depth limits and both error types give native orjson 3.13.0's bytes,
    each result's length and SHA-256."""
    job = "orjson_json"
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.run_in_guest(guest, job))
    assert why is None, f"{job}: {why}"


@pytest.mark.slow
def test_pydantic_models_job_matches_native(guest) -> None:
    """pydantic's nested models with annotated-types' constraints, validators, a discriminated
    union, datetimes, UUIDs and Decimal, a TypeAdapter over a dataclass, JSON dumps of floats, the
    JSON schema and a ValidationError's JSON give native pydantic 2.14.3's bytes over pydantic-core
    2.50.4, each result's length and SHA-256."""
    job = "pydantic_models"
    why = jobs.compare(jobs.expected_path(job).read_bytes(), jobs.run_in_guest(guest, job))
    assert why is None, f"{job}: {why}"


BUILT_IN = """
import json, sys, orjson
print(json.dumps({
    "builtin": sorted(n for n in sys.builtin_module_names if n in ("orjson.orjson", "_rust_probe")),
    "file": orjson.__file__,
    "dumps": orjson.dumps({"b": [1, 2.5, None], "a": "é"}, option=orjson.OPT_SORT_KEYS).decode(),
}))
"""


@BINARY
def test_orjson_is_built_in(guest, which) -> None:
    """orjson's compiled module and the probe are builtin modules, orjson's Python package is read
    from the stdlib zip, and a call through it answers as native orjson does."""
    r = guest(which, ["-c", BUILT_IN])
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    got = json.loads(r.text)
    assert got["builtin"] == ["_rust_probe", "orjson.orjson"], got
    assert ".zip/orjson/__init__.py" in got["file"], got["file"]
    assert got["dumps"] == '{"a":"é","b":[1,2.5,null]}', got["dumps"]


PANICS = """
import json, orjson, _rust_probe
caught = []
try:
    _rust_probe.panic("probe")
except BaseException as e:
    caught.append([type(e).__module__, type(e).__name__, str(e)])
n = 0
for i in range(1000):
    try:
        _rust_probe.panic(f"loop {i}")
    except BaseException:
        n += 1
print(json.dumps({"caught": caught, "loop": n, "after": orjson.dumps([1, "x"]).decode()}))
"""


@BINARY
def test_a_rust_panic_raises_panicexception(guest, guest_turns, which) -> None:
    """A panic inside a PyO3 function unwinds to PyO3's boundary and raises
    `pyo3_runtime.PanicException` with the message; the same run then serialises with orjson,
    a thousand panics in a loop are each caught, and the run exits 0. In one instance kept across
    turns, as a session keeps it, a turn that panics and does not catch it fails as a Python
    error does, and the next turn runs."""
    r = guest(which, ["-c", PANICS])
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    got = json.loads(r.text)
    assert got["caught"] == [["pyo3_runtime", "PanicException", "probe"]], got
    assert (got["loop"], got["after"]) == (1000, '[1,"x"]'), got
    t = guest_turns(which)
    first = t.turn("import _rust_probe\n_rust_probe.panic('in a turn')")
    assert first.trapped is None and first.value != 0, first.describe()
    assert b"PanicException" in first.stderr, first.describe()
    second = t.turn("import orjson\nprint(orjson.dumps({'next': True}).decode())")
    assert (second.value, second.trapped, second.text) == (0, None, '{"next":true}\n'), (
        second.describe()
    )


@BINARY
def test_a_panic_in_c_ends_the_run_with_its_message(guest, which) -> None:
    """A panic inside a plain C entry point, as orjson's own functions are written, cannot unwind
    out of it: the call ends as the trap `unreachable` with the message on stderr, under either
    panic strategy, and a new run starts clean."""
    r = guest(which, ["-c", "import _rust_probe\n_rust_probe.panic_in_c('probe in c')"])
    assert r.trapped is not None and "unreachable" in (r.trap_cause or ""), r.describe()
    assert b"probe in c" in r.stderr, r.describe()
    again = guest(which, ["-c", "import orjson\nprint(orjson.dumps(1).decode())"])
    assert (again.exit_code, again.trapped, again.text) == (0, None, "1\n"), again.describe()


KEYS = [f"key-{i:02d}" for i in range(32)]
PREPARE = f"import _rust_probe\nORDER = _rust_probe.hashed({KEYS!r})\n"


def _order(guest_turns) -> list[str]:
    """The order a Rust `HashMap` held the keys in, made while an image was prepared and read
    back in a turn on that image. The driver answers nothing, so a draw that bypasses the
    preparation's pinned entropy reads the host's own."""
    t = guest_turns("snapshot")
    made = t.prepare(PREPARE)
    assert (made.value, made.trapped) == (0, None), made.describe()
    image = t.image()
    on = guest_turns("snapshot", image=image)
    read = on.turn("import json\nprint(json.dumps(ORDER))")
    assert (read.value, read.trapped) == (0, None), read.describe()
    return json.loads(read.text)


def test_rust_reads_entropy_through_the_wrap(guest_turns) -> None:
    """Two images prepared alike hold a Rust `HashMap` in the same order: the map's random keys
    were drawn through the wrap that pins entropy while an image is prepared. Without the build's
    entropy shim, Rust's standard library reads the host's entropy directly and the two orders
    differ."""
    first, second = _order(guest_turns), _order(guest_turns)
    assert sorted(first) == KEYS, first
    assert first == second, (first, second)


PYDANTIC_BUILT_IN = """
import json, sys, pydantic, pydantic_core
print(json.dumps({
    "builtin": "pydantic_core._pydantic_core" in sys.builtin_module_names,
    "core": pydantic_core.__version__,
    "pydantic": pydantic.VERSION,
    "file": pydantic_core.__file__,
}))
"""


@BINARY
def test_pydantic_core_is_built_in(guest, which) -> None:
    """pydantic-core's compiled module is a builtin module, its Python package and pydantic's are
    read from the stdlib zip, and the two are the pinned pair, pydantic-core 2.50.4 under pydantic
    2.14.3."""
    r = guest(which, ["-c", PYDANTIC_BUILT_IN])
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    got = json.loads(r.text)
    assert (got["builtin"], got["core"], got["pydantic"]) == (True, "2.50.4", "2.14.3"), got
    assert ".zip/pydantic_core/__init__.py" in got["file"], got["file"]


PYDANTIC_PANIC = """
import json, _rust_probe
from pydantic import BaseModel

class Point(BaseModel):
    x: int
    y: float

before = Point.model_validate_json('{"x": 1, "y": 2.5}').model_dump()
caught = []
try:
    _rust_probe.panic("probe")
except BaseException as e:
    caught.append([type(e).__module__, type(e).__name__, str(e)])
after = Point.model_validate({"x": "3", "y": 4}).model_dump()
print(json.dumps({"before": before, "caught": caught, "after": after}))
"""


@BINARY
def test_a_panic_after_pydantic_validates_is_caught(guest, which) -> None:
    """One unwinder and one personality serve every Rust module: a run validates a pydantic model,
    a panic in the probe raises `PanicException`, and the same model validates again in the same
    run."""
    r = guest(which, ["-c", PYDANTIC_PANIC])
    assert (r.exit_code, r.trapped) == (0, None), r.describe()
    got = json.loads(r.text)
    assert got["before"] == {"x": 1, "y": 2.5}, got
    assert got["caught"] == [["pyo3_runtime", "PanicException", "probe"]], got
    assert got["after"] == {"x": 3, "y": 4.0}, got


PYDANTIC_PREPARE = """
from pydantic import BaseModel, ConfigDict

class Loose(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str

KEPT = Loose.model_validate_json('{"name": "a", "b": 1, "c": [2], "d": {"e": 3}}')
"""


def _pydantic_image(guest_turns) -> bytes:
    """The starting image a prelude makes that validates JSON into a model that keeps extra keys,
    whose map of them pydantic-core keys with ahash. The driver answers the clocks and each file's
    inode number and times, as for any image that must repeat (each instance has its own copy of
    the zip, whose metadata the import caches hold), and leaves entropy to the host, so a draw
    that bypasses the wrap reads the host's own."""
    t = guest_turns("snapshot", answered=True, host_entropy=True)
    made = t.prepare(PYDANTIC_PREPARE)
    assert (made.value, made.trapped) == (0, None), made.describe()
    return t.image()


def test_pydantic_core_reads_entropy_through_the_wrap(guest_turns) -> None:
    """Two images prepared alike by a prelude that builds a pydantic validator and validates JSON
    with it are the same bytes: the hash keys pydantic-core draws (ahash through getrandom, and the
    standard library's) come through the wrap that pins entropy while an image is prepared.
    Without the shim's getrandom definition, the keys are the host's and the images differ."""
    first, second = _pydantic_image(guest_turns), _pydantic_image(guest_turns)
    assert len(first) == len(second), (len(first), len(second))
    if first != second:
        pages = [
            i // 65536
            for i in range(0, len(first), 65536)
            if first[i : i + 65536] != second[i : i + 65536]
        ]
        pytest.fail(f"the two prepared images differ: {len(pages)} pages, first {pages[:8]}")
