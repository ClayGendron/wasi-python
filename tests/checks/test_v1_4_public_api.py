"""v1.4: the public API is frozen and documented (spec 049).

An embedder relies on the names in `wasi_python.__all__` and `wasi_python.tools.__all__`, the
command and two environment variables; everything else is internal. These checks keep that
surface equal to its snapshot (`tests/public_api.txt`) and to the README's reference, documented,
typed and free of internal names. None needs an artifact set; each counts names, lines or reads.
"""

from __future__ import annotations

import ast
import asyncio
import concurrent.futures
import dataclasses
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from harness import api, paths, scan

pytestmark = pytest.mark.goal("v1.4")

TOP = [
    "Artifacts",
    "ArtifactsMissing",
    "Completed",
    "Defaults",
    "Errno",
    "FileFault",
    "FileProvider",
    "FileRecord",
    "Grant",
    "Mount",
    "RefusedWrite",
    "Session",  # spec 055
    "SessionEnded",
    "Stat",
    "WritableFileProvider",
    "artifact_dir",
    "artifacts",
    "defaults",
    "run",
    "run_async",
    "set_defaults",
    "stats",
]
TOOLS = [
    "PROTOCOL",
    "Tool",
    "ToolCall",
    "ToolDenied",
    "ToolError",
    "ToolOutcome",
    "ToolRecord",
    "stubs",
    "tool",
]


def _copy(tmp_path: Path) -> Path:
    """A scratch copy of the package, for a stand-in to change."""
    dest = tmp_path / "wasi_python"
    shutil.copytree(api.PACKAGE, dest, ignore=shutil.ignore_patterns("__pycache__", "artifacts"))
    return dest


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, f"{path.name}: the stand-in's anchor {old!r} is not unique"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _changed(diff: str) -> list[str]:
    return [
        line
        for line in diff.splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]


# -------------------------------------------------------------------------------------------------
# Criterion 1: the snapshot.


def test_the_public_api_matches_its_snapshot(tmp_path) -> None:
    assert api.SNAPSHOT.is_file(), f"no snapshot: run {api.WRITE}"
    snapshot, _ = api.render()
    old = api.SNAPSHOT.read_text(encoding="utf-8")
    assert old == snapshot, (
        f"the public API differs from its snapshot; a change a specification lists is "
        f"regenerated with {api.WRITE}:\n" + api.diff(old, snapshot, "snapshot", "live")
    )
    # Stand-ins: a scratch copy where Stat.size's default is 1, and where Tool compares by value
    # (`eq=False` dropped), differs by exactly those lines.
    copy = _copy(tmp_path)
    _edit(copy / "mounts.py", "    size: int = 0\n", "    size: int = 1\n")
    _edit(copy / "tools.py", "@dataclass(frozen=True, eq=False)\n", "@dataclass(frozen=True)\n")
    changed, _ = api.render(copy)
    lines = _changed(api.diff(snapshot, changed, "snapshot", "stand-in"))
    assert lines == [
        "-  field size: int = 0",
        "+  field size: int = 1",
        "-dataclass Tool: frozen, eq=False",
        "+dataclass Tool: frozen",
    ], lines


# -------------------------------------------------------------------------------------------------
# Criteria 2 to 4: the two `__all__`s, the underscore rule, nothing private re-exported.


def test_public_modules_export_exactly_their_all() -> None:
    f = api.facts()
    errors = []
    for module, want in (("wasi_python", TOP), ("wasi_python.tools", TOOLS)):
        found = f["inventory"][module]
        names = found["all"]
        if not found["has_all"]:
            errors.append(f"{module} has no __all__")
        if names != sorted(names):
            errors.append(f"{module}.__all__ is not sorted")
        errors += [
            f"{module}.__all__ repeats {n}"
            for n in sorted({n for n in names if names.count(n) > 1})
        ]
        errors += [f"{module}.__all__ names {n}" for n in names if n.startswith("_")]
        star = f["star"][module]
        errors += [f"`from {module} import *` lacks {n}" for n in want if n not in star]
        errors += [f"`from {module} import *` binds {n}" for n in star if n not in want]
    errors += [f"{n} does not resolve" for n in f["unresolved"]]
    assert not errors, scan.report(errors)


def test_private_names_carry_an_underscore() -> None:
    errors = api.private_name_errors()
    assert not errors, scan.report(errors, "names bound in a public module, not exported, no `_`")


def test_nothing_private_is_re_exported(tmp_path) -> None:
    errors = api.reexport_errors()
    assert not errors, scan.report(errors)
    # Stand-in: `from .runner import _UNSET as UNSET`, exported, is the one finding.
    copy = _copy(tmp_path)
    init = copy / "__init__.py"
    init.write_text(init.read_text(encoding="utf-8") + "from .runner import _UNSET as UNSET\n")
    _edit(init, "__all__ = [\n", '__all__ = [\n    "UNSET",\n')
    assert api.reexport_errors(copy) == ["wasi_python.UNSET is _UNSET"]


# -------------------------------------------------------------------------------------------------
# Criteria 5 and 6: documented, and naming nothing internal.


def test_every_public_name_is_documented() -> None:
    gaps = api.doc_gaps(api.facts()["inventory"])
    counts = {k: len(v) for k, v in gaps.items()}
    missing = [item for v in gaps.values() for item in v]
    assert not missing, f"missing: {counts}; " + scan.report(missing)

    # Stand-in for the reading rule: a generated or an inherited docstring is no docstring.
    @dataclasses.dataclass(frozen=True)
    class NoDoc:
        a: int

    class Bare(RuntimeError):
        pass

    inv = {
        "m": {
            "all": ["Bare", "NoDoc"],
            "doc": "A module.",
            "items": [api._class("Bare", Bare), api._class("NoDoc", NoDoc)],
        }
    }
    assert NoDoc.__doc__ and Bare.__doc__ is None and Bare.__mro__[1].__doc__
    assert api.doc_gaps(inv)["docstrings"] == ["m.Bare", "m.NoDoc"]


# A README in the shape that hid spans from weaker scanners (the pre-build review's
# Confirmation): a fence at the start of a line holding one backtick, three spans, an indented
# fence holding one, a second line-start fence holding one, three more spans.
FENCED = """# A page

```python
a = "`"
```

Uses `DEFAULTS.file_calls`, `DEFAULTS.async_workers` and `DEFAULTS.tool_calls`.

- An item with code:

    ```python
    b = "`"
    ```

```python
c = "`"
```

Then `wasi_python.runner.stats()`, `wasi_python.runner.DEFAULTS` and `wasi_python.cli`.
"""


def _naive(text: str) -> list[str]:
    """Pairs backticks across the whole text, fences and all."""
    return re.findall(r"`([^`]*)`", text)


def _line_start_only(text: str) -> list[str]:
    """Blanks only fences that start a line, then pairs backticks."""
    out, fence = [], None
    for line in text.split("\n"):
        m = re.match(r"(`{3,}|~{3,})", line)
        if fence is None and m:
            fence = m.group(1)
        elif fence is not None and m and m.group(1)[0] == fence[0]:
            fence = None
        elif fence is None:
            out.append(line)
            continue
        out.append("")
    return _naive("\n".join(out))


def test_public_docs_name_nothing_internal() -> None:
    inv = api.facts()["inventory"]
    in_docstrings = api.docstring_hits(inv, api.internal_names())
    constants = api.internal_constants()
    in_readme = api.readme_hits(paths.README.read_text(encoding="utf-8"), constants)
    assert not in_docstrings and not in_readme, (
        f"public docstrings: {len(in_docstrings)}, README: {len(in_readme)}; "
        + scan.report(in_docstrings + in_readme)
    )
    # Stand-ins (condition C1): fences are blanked first, indented ones included.
    hold = [s for s in _naive(FENCED) if api._holds(s, constants)]
    line_start = [s for s in _line_start_only(FENCED) if api._holds(s, constants)]
    assert (len(api.readme_hits(FENCED, constants)), len(hold), len(line_start)) == (6, 0, 3)
    bare = "- Code:\n\n    ```\n    x = '`'\n    ```\n\nSee `DEFAULTS.file_calls`.\n"
    assert api.readme_hits(bare, constants) == ["README.md:7 `DEFAULTS.file_calls` (DEFAULTS)"]
    code = "```python\nwasi_python.runner.DEFAULTS = x\n```\n"
    assert len(api.readme_hits(code, constants)) == 1  # a fence is searched too


# -------------------------------------------------------------------------------------------------
# Criteria 7 and 8: typed.


def test_public_annotations_resolve() -> None:
    f = api.facts()
    report = f["annotations"]
    assert not report["failed"], (
        f"evaluated {report['evaluated']}, failed {len(report['failed'])}; "
        + scan.report(report["failed"])
    )
    tool = next(i for i in f["inventory"]["wasi_python.tools"]["items"] if i["name"] == "tool")
    shapes = [
        (o["params"][0]["name"], o["params"][0]["kind"], o["params"][0]["annotation"], o["returns"])
        for o in tool["overloads"]
    ]
    assert len(shapes) == 2, f"tool has {len(shapes)} overloads: {shapes}"
    assert shapes[0] == ("fn", "positional-only", "Callable[..., Any]", "Tool"), shapes
    assert shapes[1][:3] == ("fn", "positional-only", "None"), shapes
    assert shapes[1][3].startswith("Callable["), shapes
    keywords = [[p["name"] for p in o["params"][1:]] for o in tool["overloads"]]
    assert keywords[0] == keywords[1] == [p["name"] for p in tool["params"][1:]], keywords


def test_the_package_is_typed() -> None:
    marker = "src/wasi_python/py.typed"
    assert (paths.REPO / marker).is_file(), f"{marker} is missing"
    assert marker in paths.tracked_files(marker), f"{marker} is not tracked"


# -------------------------------------------------------------------------------------------------
# Criterion 9: the README's reference.


def test_the_readme_reference_matches_the_api() -> None:
    count, block = api.readme_block(paths.README.read_text(encoding="utf-8"))
    assert count == 1 and block is not None, f"README.md has {count} api reference blocks"
    _, reference = api.render()
    assert block.strip("\n") == reference.strip("\n"), (
        f"the README's reference differs from the API; run {api.WRITE}:\n"
        + api.diff(block, reference, "README", "live")
    )
    # A marker inside a fence is an example, never the block.
    inside = f"```\n{api.BEGIN}\nx\n{api.END}\n```\n"
    assert api.readme_block(inside) == (0, None)


# -------------------------------------------------------------------------------------------------
# Criterion 10: set_defaults, read once per call, under one lock.


class _Stop(Exception):
    pass


class _Counting:
    """A lock stand-in that records the binding `run` reads when it is entered and left. With
    `swap`, entering it also replaces the binding, as another thread's `set_defaults` that took
    the lock just before would: a caller that read the old value outside the lock returns the
    wrong one."""

    def __init__(self, runner: Any, swap: Any = None) -> None:
        self.runner = runner
        self.swap = swap
        self.seen: list[tuple[str, Any]] = []

    def __enter__(self) -> None:
        self.seen.append(("enter", self.runner.DEFAULTS))
        if self.swap is not None:
            self.runner.DEFAULTS = self.swap

    def __exit__(self, *exc: Any) -> None:
        self.seen.append(("exit", self.runner.DEFAULTS))


class _Refusing(concurrent.futures.Executor):
    def submit(self, fn, /, *args, **kwargs):
        raise _Stop


def _defaults_loads(path: Path) -> list[str]:
    """Where a module loads the name `DEFAULTS`, outside `_current_defaults`, by `ast`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    allowed = {
        id(n)
        for f in ast.walk(tree)
        if isinstance(f, ast.FunctionDef) and f.name == "_current_defaults"
        for n in ast.walk(f)
    }
    return [
        f"{path.name}:{n.lineno}"
        for n in ast.walk(tree)
        if isinstance(n, ast.Name)
        and n.id == "DEFAULTS"
        and isinstance(n.ctx, ast.Load)
        and id(n) not in allowed
    ]


def test_set_defaults_changes_what_run_reads(monkeypatch) -> None:
    import wasi_python
    from wasi_python import _artifacts, _limits, runner
    from wasi_python._process import process

    # The runner reads its defaults only through `_current_defaults`, so the count of its calls
    # below is every read (the build review's F2); every module of the package is read, so a
    # `DEFAULTS` load outside `_current_defaults` is refused wherever it is written.
    direct = [
        hit
        for path in sorted(Path(runner.__file__).parent.glob("*.py"))
        for hit in _defaults_loads(path)
    ]
    assert not direct, f"DEFAULTS read outside _current_defaults: {direct}"

    lookups: list[int] = []

    def found() -> Any:
        lookups.append(1)
        raise _Stop

    monkeypatch.setattr(_artifacts, "find_artifacts", found)
    before = wasi_python.defaults()
    new = dataclasses.replace(before, memory_bytes=before.memory_bytes + 4096)
    raced = dataclasses.replace(before, memory_bytes=before.memory_bytes + 8192)
    lock = _Counting(runner, swap=raced)
    monkeypatch.setattr(process(), "defaults_lock", lock)
    try:
        assert wasi_python.set_defaults(new) is raced, "the old value is read inside the lock"
        assert lock.seen == [("enter", before), ("exit", new)]
        lock.swap = None
        assert wasi_python.defaults() is new
        unset = _limits._UNSET
        checked = runner._checked(["-c", "pass"], None, None, None, unset, unset, unset, None)
        assert checked.memory_bytes == new.memory_bytes
        for wrong in (None, {}):
            with pytest.raises(TypeError):
                wasi_python.set_defaults(wrong)  # type: ignore[arg-type]
        assert wasi_python.defaults() is new
    finally:
        assert wasi_python.set_defaults(before) is new
    assert wasi_python.defaults() is before
    assert [s for s, _ in lock.seen] == ["enter", "exit", "enter", "exit"]  # once per call
    assert lookups == []

    # One read per call, with tools= so every check that takes a default is reached: run stops
    # at its first step after the checks (the artifact lookup), run_async at its submit.
    from wasi_python.tools import tool

    @tool
    def noop() -> None:
        """Do nothing."""

    reads: list[int] = []
    real = runner._current_defaults

    def counting() -> Any:
        reads.append(1)
        return real()

    monkeypatch.setattr(runner, "_current_defaults", counting)
    with pytest.raises(_Stop):
        runner.run(["-c", "pass"], tools=[noop])
    assert (len(reads), len(lookups)) == (1, 1), "run reads the defaults once"
    with pytest.raises(_Stop):
        asyncio.run(runner.run_async(["-c", "pass"], executor=_Refusing(), tools=[noop]))
    assert len(reads) == 2, "run_async reads the defaults once"


class _Racing:
    """The pool's lock, with a `set_defaults` on another thread landing each time it is taken:
    every entry sets a new `async_workers`, so only a read made inside the lock sees the last
    one (`run_async` also takes this lock earlier, to register its exit hook)."""

    def __init__(self, real: Any, before: Any) -> None:
        self.real = real
        self.before = before
        self.sizes: list[int] = []

    def __enter__(self) -> None:
        import wasi_python

        size = (self.sizes[-1] if self.sizes else 1) + 1
        size += size == self.before.async_workers  # never the value read before any entry
        self.sizes.append(size)
        wasi_python.set_defaults(dataclasses.replace(self.before, async_workers=size))
        self.real.acquire()

    def __exit__(self, *exc: Any) -> None:
        self.real.release()


def test_the_pool_takes_the_newest_size(monkeypatch) -> None:
    """The size of `run_async`'s own pool is process state, not a call's limit: it is read
    under the pool's lock, so a call that read its limits before a `set_defaults` never sizes
    the pool back (the build review's F3, and its confirmation's N1)."""
    import wasi_python
    from wasi_python import _artifacts, runner
    from wasi_python._process import process

    def found() -> Any:
        raise _Stop

    monkeypatch.setattr(_artifacts, "find_artifacts", found)
    before = wasi_python.defaults()
    racing = _Racing(process().pool_lock, before)
    monkeypatch.setattr(process(), "pool_lock", racing)
    try:
        with pytest.raises(_Stop):
            asyncio.run(runner.run_async(["-c", "pass"]))
        assert racing.sizes, "the pool's lock was never taken"
        assert process().pool_size == racing.sizes[-1], (process().pool_size, racing.sizes)
    finally:
        wasi_python.set_defaults(before)
