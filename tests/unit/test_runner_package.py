"""The runner is a package of one module per concern.

Four checks hold the package's shape: the fork hook re-makes every module-level lock the
package holds, the modules import in one written order with no cycle,
a module imports by `from` only what never changes, so a patched seam, a re-made lock or a
cleared cache is seen by every caller, and every runner name is defined in exactly one module.
Check 1 holds until the process state gets one owner, whose own check then retires it.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import re
import subprocess
import sys
import typing
from pathlib import Path

from harness import paths, scan

PACKAGE = paths.REPO / "src" / "wasi_python"

# The order: a module imports only modules before it. A plain tuple, so a new first module
# (the process state's owner) is prepended.
ORDER = (
    "_wasmtime_ffi",
    "_limits",
    "_platform",
    "_artifacts",
    "_engines",
    "_private_dirs",
    "_zip",
    "_places",
    "_home",
    "_call",
    "_sessions",
    "runner",
)
RUNNER_MODULES = ORDER[1:]  # the eleven: the runner's text, one concern each
MAY_IMPORT_MOUNTS = ("_places", "_call", "_sessions", "runner")
ABOVE = ("__init__", "__main__", "cli")  # above `runner`: they import what they like
BESIDE = ("mounts", "tools")  # beside the list: no package module at module level
LATE_ANYWHERE = ("_wasmtime_ffi",)  # the seam's form: `from . import _wasmtime_ffi as ffi` in a def

# The late imports allowed, (file, function, module); any other is a finding.
LATE = (
    ("runner.py", "_check_tools", "tools"),
    ("_call.py", "_instance", "mounts"),
    ("_call.py", "_mount_linker", "mounts"),
    ("_call.py", "_guard_linker", "mounts"),
    ("_call.py", "_stat_trampoline_module", "mounts"),
    ("_call.py", "_trampoline_module", "mounts"),
    ("_call.py", "_tool_host", "tools"),
    ("_sessions.py", "_session_tool_host", "tools"),
    ("_sessions.py", "_open_session", "mounts"),
    ("_sessions.py", "_open_session", "tools"),
    ("mounts.py", "_Files.__init__", "_call"),
    ("mounts.py", "_Files.__init__", "_engines"),
    ("mounts.py", "_Files.__init__", "_home"),
    ("mounts.py", "_Files.__init__", "_places"),
    ("mounts.py", "_Files.__init__", "runner"),
    ("cli.py", "_grants", "runner"),
    ("cli.py", "_main", "runner"),
)

# The module-level locks the fork hook re-makes (eleven) and the ticker's Condition.
LOCKS_RESET_BY_FORK = (
    ("wasi_python.runner", "_pool_lock"),
    ("wasi_python.runner", "_live_lock"),
    ("wasi_python._private_dirs", "_held_lock"),
    ("wasi_python._home", "_stack_size_lock"),
    ("wasi_python._call", "_tool_threads_lock"),
    ("wasi_python._call", "_epoch_callback_lock"),
    ("wasi_python._call", "_outputs_lock"),
    ("wasi_python._zip", "_zip_lock"),
    ("wasi_python._engines", "_lock"),
    ("wasi_python._sessions", "_sessions_lock"),
    ("wasi_python._sessions", "_closers_lock"),
    ("wasi_python._engines", "_epoch_ticker._cond"),
)
# The names the hook rebinds that are not locks (a dict, a dict, a WeakSet, a SimpleQueue).
REBOUND_BY_FORK = (
    ("wasi_python._engines", "_compiling"),
    ("wasi_python._zip", "_zips"),
    ("wasi_python._sessions", "_sessions"),
    ("wasi_python._sessions", "_reaper_queue"),
)
# Module-level locks the hook does not touch, each with its sentence.
NOT_RESET = (
    (
        ("wasi_python._private_dirs", "_pending_warnings_lock"),
        "never reset today; the process state's owner decides",
    ),
    (
        ("wasi_python", "_defaults_lock"),
        "never reset today; the process state's owner takes it",
    ),
)
TICKER_COND = ("wasi_python._engines", "_epoch_ticker._cond")

# Check 3: the names a module may import by `from` that are neither a class, an alias nor an
# immutable constant. A plain tuple, so the process accessor can be added.
SENTINELS = ("_UNSET", "_DONE")

# The child interpreter of check 1: it loads every module of the package, walks them for locks,
# calls the hook, walks again.
FORK_WALK = r"""
import json, sys, threading
import wasi_python
import wasi_python._wasmtime_ffi, wasi_python.cli, wasi_python.tools
from wasi_python import _engines, runner

LOCKS = (type(threading.Lock()), type(threading.RLock()), threading.Condition)


def found():
    out = []
    for name, module in sorted(sys.modules.items()):
        if name != "wasi_python" and not name.startswith("wasi_python."):
            continue
        for attr, value in sorted(vars(module).items()):
            if isinstance(value, LOCKS):
                out.append([name, attr, id(value)])
    out.append(["wasi_python._engines", "_epoch_ticker._cond", id(_engines._epoch_ticker._cond)])
    return out


before = found()
runner._after_fork_in_child()
print(json.dumps([before, found()]))
"""


def _fork_walk() -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], int]]:
    out = subprocess.run(
        [sys.executable, "-c", FORK_WALK],
        capture_output=True,
        text=True,
        timeout=120,  # a fail-safe, never a verdict
    )
    assert out.returncode == 0, out.stderr[-1500:]
    before, after = json.loads(out.stdout)
    return (
        {(module, name): ident for module, name, ident in before},
        {(module, name): ident for module, name, ident in after},
    )


def _hook_targets(hook: typing.Any) -> set[tuple[str, str]]:
    """What `_after_fork_in_child` rebinds, by `ast`: its `global` names (the hook's own
    module's) and its depth-one `_module.name` assignment targets; a `Subscript` target
    (`_call._tool_threads["running"]`) and an attribute of an attribute
    (`_engines._epoch_ticker._thread`) are mutations of an object, not rebindings."""
    tree = ast.parse(inspect.getsource(hook))
    own = hook.__module__
    out: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            out |= {(own, name) for name in node.names}
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                elts = target.elts if isinstance(target, ast.Tuple) else [target]
                for elt in elts:
                    if isinstance(elt, ast.Attribute) and isinstance(elt.value, ast.Name):
                        out.add((f"wasi_python.{elt.value.id}", elt.attr))
    return out


def test_every_module_level_lock_is_remade_after_fork() -> None:
    """A child interpreter loads every module of the package (the three `import wasi_python`
    leaves out too), finds every lock they hold at module level, and the hook re-makes each one
    it names; the hook, the lists and the modules agree three ways."""
    from wasi_python import runner

    before, after = _fork_walk()
    reset = set(LOCKS_RESET_BY_FORK)
    not_reset = {key for key, _ in NOT_RESET}
    unlisted = sorted(key for key in before if key not in reset and key not in not_reset)
    assert not unlisted, f"locks in neither list: {unlisted}"
    assert len(before) >= 14, f"the walk found {len(before)} locks; at least 14 expected"
    missing = sorted(key for key in reset if key not in before)
    assert not missing, f"LOCKS_RESET_BY_FORK entries the walk did not find: {missing}"
    kept = sorted(key for key in reset if after[key] == before[key])
    assert not kept, f"locks the hook did not re-make: {kept}"
    for key, sentence in NOT_RESET:
        assert key in before, f"NOT_RESET entry not found: {key} ({sentence})"
        assert after[key] == before[key], f"{key} was reset; its sentence says: {sentence}"
    expected = (reset | set(REBOUND_BY_FORK)) - {TICKER_COND}
    assert len(expected) == 15
    assert _hook_targets(runner._after_fork_in_child) == expected


def _module_name(path: Path) -> str:
    return path.stem


def _imports(tree: ast.Module) -> list[tuple[ast.ImportFrom, str | None, bool]]:
    """Every relative import in a module: (node, the enclosing function's qualified name or None
    at module level, under TYPE_CHECKING)."""
    out: list[tuple[ast.ImportFrom, str | None, bool]] = []

    def walk(node: ast.AST, stack: list[str], typing_only: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If) and not stack:
                guarded = isinstance(child.test, ast.Name) and child.test.id == "TYPE_CHECKING"
                walk(child, stack, typing_only or guarded)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                walk(child, stack + [child.name], typing_only)
            elif isinstance(child, ast.ImportFrom) and child.level:
                out.append((child, ".".join(stack) or None, typing_only))
            else:
                walk(child, stack, typing_only)

    walk(tree, [], False)
    return out


def _named_modules(node: ast.ImportFrom, package: Path) -> list[str]:
    """The package modules an import names: `from .x import …` names `x`; `from . import a, b`
    names each `a` that is a module file, and `__init__` for a name that is not."""
    if node.module:
        return [node.module.split(".")[0]]
    return [a.name if (package / f"{a.name}.py").is_file() else "__init__" for a in node.names]


def _order_errors(package: Path) -> list[str]:
    rank = {m: i for i, m in enumerate(ORDER)}
    errors = []
    for path in sorted(package.glob("*.py")):
        me = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node, function, typing_only in _imports(tree):
            if typing_only:
                continue
            for module in _named_modules(node, package):
                where = f"{path.name}:{node.lineno}"
                if function is None:
                    if module == "tools" or module in LATE_ANYWHERE:
                        errors.append(f"{where} imports {module} at module level")
                    elif me in ABOVE:
                        continue
                    elif me in BESIDE:
                        errors.append(f"{where} ({me} imports a package module at module level)")
                    elif module == "mounts":
                        if me not in MAY_IMPORT_MOUNTS:
                            errors.append(f"{where} ({me} may not import mounts)")
                    elif module not in rank or rank[module] >= rank.get(me, -1):
                        errors.append(f"{where} ({me} imports {module}, not before it in ORDER)")
                elif module in LATE_ANYWHERE:
                    continue
                elif (path.name, function, module) not in LATE:
                    errors.append(f"{where} ({function} imports {module} late, not in LATE)")
    return errors


def test_the_runner_modules_import_in_the_written_order() -> None:
    """Every module-level relative import names a module earlier in ORDER (or
    `mounts` from the four that may); `__init__.py` and `cli.py` stand above; `mounts.py` and
    `tools.py` import no package module at module level; no module imports `tools` or
    `_wasmtime_ffi` at module level; a late import is one of LATE, or of `_wasmtime_ffi`."""
    errors = _order_errors(PACKAGE)
    assert not errors, scan.report(errors)


def _is_unchanging(name: str, obj: typing.Any) -> bool:
    """The by-name form: a class, a generic alias, an immutable constant or a sentinel."""
    if isinstance(obj, type) or typing.get_origin(obj) is not None:
        return True
    if isinstance(obj, (tuple, frozenset)):
        return all(_is_unchanging(name, element) for element in obj)
    if isinstance(obj, (int, float, str, bytes, re.Pattern)):
        return True
    return name in SENTINELS


def _from_imports(package: Path) -> list[tuple[str, int, str, str]]:
    """Every `from ._x import name` of a runner module, from any file but `__init__.py` (the
    public facade re-exports `run` and `artifacts` by name): (file, line, module, name)."""
    out = []
    for path in sorted(package.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node, _, _ in _imports(tree):
            if node.module and node.module.split(".")[0] in RUNNER_MODULES:
                out += [(path.name, node.lineno, node.module, a.name) for a in node.names]
    return out


def _by_name_errors(package: Path) -> list[str]:
    errors = []
    rebound = {name for _, name in LOCKS_RESET_BY_FORK + REBOUND_BY_FORK}
    for filename, line, module, name in _from_imports(package):
        obj = getattr(importlib.import_module(f"wasi_python.{module}"), name)
        if name in rebound:
            errors.append(f"{filename}:{line} imports {name} by from: the fork hook rebinds it")
        elif not _is_unchanging(name, obj):
            errors.append(
                f"{filename}:{line} imports {name} from {module} by from: {type(obj).__name__}"
            )
    return errors


def _patched(tests: Path) -> set[tuple[str, str]]:
    """Every `monkeypatch.setattr(<module>, "NAME", …)` under tests/ whose first argument names
    a runner module or the package, under the name the file imports it by: (module, NAME)."""
    out = set()
    for path in scan.files_under(tests, "."):
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        known = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == "wasi_python":
                        known[a.asname or a.name] = "wasi_python"
            elif isinstance(node, ast.ImportFrom) and node.module == "wasi_python":
                for a in node.names:
                    if a.name in RUNNER_MODULES:
                        known[a.asname or a.name] = f"wasi_python.{a.name}"
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setattr"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in known
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                out.add((known[node.args[0].id], node.args[1].value))
    return out


def _seam_errors(package: Path, tests: Path) -> list[str]:
    """The condition the by-name form rests on: a class or a constant the judge patches by
    `setattr` is read only in its defining module, so no package module from-imports it (held
    here until the test seams move off module globals)."""
    imported = {name: f"{f}:{line}" for f, line, _, name in _from_imports(package)}
    errors = []
    for module, name in sorted(_patched(tests)):
        obj = getattr(importlib.import_module(module), name, None)
        if obj is not None and _is_unchanging(name, obj) and name in imported:
            errors.append(f"{imported[name]} from-imports {name}, which tests patch on {module}")
    return errors


def test_a_module_imports_by_name_only_what_never_changes() -> None:
    """The two forms: a `from ._x import name` binds a class, an alias, an immutable
    constant or a sentinel; a function, a hook and every mutable object is reached as
    `_x.name`, so a re-made lock, a replaced seam or a cleared cache is seen by every caller."""
    errors = _by_name_errors(PACKAGE) + _seam_errors(PACKAGE, paths.REPO / "tests")
    assert not errors, scan.report(errors)


def _bound_names(tree: ast.Module) -> list[str]:
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                elts = target.elts if isinstance(target, ast.Tuple) else [target]
                out += [e.id for e in elts if isinstance(e, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out.append(node.target.id)
    return [n for n in out if not (n.startswith("__") and n.endswith("__"))]


def _once_errors(package: Path) -> list[str]:
    where: dict[str, list[str]] = {}
    errors = []
    for module in RUNNER_MODULES:
        path = package / f"{module}.py"
        if not path.is_file():
            errors.append(f"{path.name} does not exist")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if ast.get_docstring(tree) is None:
            errors.append(f"{path.name} does not begin with a docstring")
        for name in _bound_names(tree):
            where.setdefault(name, []).append(path.name)
    errors += [
        f"{name} is bound in {' and '.join(files)}"
        for name, files in where.items()
        if len(files) > 1
    ]
    return errors


def test_every_runner_name_is_defined_in_one_module() -> None:
    """Over the eleven runner modules, no top-level name is bound twice, and each
    module begins with a docstring."""
    errors = _once_errors(PACKAGE)
    assert not errors, scan.report(errors)
