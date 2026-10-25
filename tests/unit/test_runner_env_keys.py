"""An `env=` key that begins with `_PYTHON_` is refused before any work.

These are CPython's private build settings. The guest's interpreter is isolated, so it ignores
the documented `PYTHON*` variables, but `sysconfig` still reads these, and one of them,
`_PYTHON_SYSCONFIGDATA_PATH`, names a folder whose `_sysconfigdata_*` module it runs. A guest
that could write a reused root would plant that module in one call, and an embedder that
forwarded the variable would run it in the next, on `import pandas`.

So `run`, `run_async` and `Session` refuse the key with `ValueError` before the guest runs, and
before any artifact is read: with an empty artifact set the env refusal is what is raised. The
controls show the rule refuses only that family: without the key the planted module never runs,
and `PYTHONPATH`, which isolated mode ignores, still reaches nothing. Nothing here measures
time; each verdict is a refusal, an exit status or a marker in stderr."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import wasi_python
from harness import needs
from wasi_python import _artifacts

CALLERS = ("run", "run_async", "Session")
KEY = "_PYTHON_SYSCONFIGDATA_PATH"
MARKER = b"planted-module-ran"
SECRET = "s3cr3t-value"
# What an earlier guest leaves in its root: the module sysconfig would load from the folder the
# key names, and a module of its own that only PYTHONPATH could reach.
MODULE = f"import sys\nsys.stderr.write({MARKER.decode()!r} + '\\n')\nbuild_time_vars = {{}}\n"
PLANT = (
    "import os\n"
    "os.makedirs('/data', exist_ok=True)\n"
    "for name in ('_sysconfigdata__wasi_wasm32-wasi.py', 'planted.py'):\n"
    "    with open('/data/' + name, 'w') as f:\n"
    f"        f.write({MODULE!r})\n"
)


@pytest.fixture(scope="module")
def compiled() -> None:
    """Both binaries compiled once in this process, kept in memory only, so no call below writes
    a compiled module to disk."""
    needs.need("runner", "artifact dir")
    for snapshot in (True, False):
        done = wasi_python.run(["-c", "pass"], snapshot=snapshot, cache_dir=False)
        assert done.exit_code == 0, done


@pytest.fixture
def planted(compiled, tmp_path: Path) -> Path:
    """A root an earlier call wrote: the planted modules under its /data."""
    root = tmp_path / "root"
    done = wasi_python.run(["-c", PLANT], root=str(root), cache_dir=False)
    assert done.exit_code == 0, done.stderr
    assert (root / "data" / "_sysconfigdata__wasi_wasm32-wasi.py").is_file()
    return root


@pytest.fixture
def no_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty folder as the artifact set: any call that reaches the set fails on it."""
    empty = tmp_path / "empty-set"
    empty.mkdir()
    monkeypatch.setenv(_artifacts._ARTIFACTS_ENV, str(empty))


def _call(caller: str, code: str, **kwargs) -> wasi_python.Completed:
    """One call of `code` through the named entry point, with the frozen set and no disk cache."""
    kwargs.setdefault("cache_dir", False)
    if caller == "run":
        return wasi_python.run(["-c", code], **kwargs)
    if caller == "run_async":
        return asyncio.run(wasi_python.run_async(["-c", code], **kwargs))
    with wasi_python.Session(**kwargs) as session:
        return session.run(code)


@pytest.mark.parametrize("caller", CALLERS)
def test_the_key_on_a_planted_root_is_refused_before_the_guest_runs(planted, caller) -> None:
    try:
        done = _call(caller, "import pandas", root=str(planted), env={KEY: "/data"})
    except ValueError as refused:
        assert KEY in str(refused)
    else:
        pytest.fail(
            f"{caller} ran with {KEY}: exit {done.exit_code}, planted module ran: "
            f"{MARKER in done.stderr}"
        )


@pytest.mark.parametrize("caller", CALLERS)
def test_the_key_is_refused_before_any_artifact_is_read(no_set, caller) -> None:
    with pytest.raises(ValueError, match=KEY):
        _call(caller, "pass", env={KEY: "/data"})


@pytest.mark.parametrize("snapshot", [True, False], ids=["snapshot", "plain"])
def test_without_the_key_the_planted_module_never_runs(planted, snapshot) -> None:
    code = "import pandas; print('ok')"
    done = _call("run", code, root=str(planted), snapshot=snapshot)
    assert (done.exit_code, done.stdout) == (0, b"ok\n"), done.stderr
    assert MARKER not in done.stderr


def test_pythonpath_is_still_ignored_not_refused(planted) -> None:
    done = _call("run", "import planted", root=str(planted), env={"PYTHONPATH": "/data"})
    assert done.exit_code == 1
    assert b"ModuleNotFoundError" in done.stderr
    assert MARKER not in done.stderr


@pytest.mark.parametrize("key", [KEY, "_PYTHON_PROJECT_BASE"])
def test_the_message_names_the_key_and_the_control_and_quotes_no_value(no_set, key) -> None:
    with pytest.raises(ValueError) as refused:
        wasi_python.run(["-c", "pass"], env={key: SECRET})
    message = str(refused.value)
    assert key in message
    assert KEY in message
    assert "import_path" in message
    assert SECRET not in message, "the message quotes a value"
