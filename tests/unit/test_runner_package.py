"""The runner is a package of one module per concern.

Four checks hold the package's shape: the modules import in one written order with no cycle,
and the tool protocol's three in an order of their own beside it; a module imports by `from`
only what never changes, so a patched seam, a re-made lock or a cleared cache is seen by every
caller; and every runner name is defined in exactly one module.
The fork reset is the process state's owner's, and tests/unit/test_process.py holds it.
"""

from __future__ import annotations

import ast
import importlib
import re
import typing
from pathlib import Path

from harness import paths, scan

PACKAGE = paths.REPO / "src" / "wasi_python"

# The order: a module imports only modules before it. The process state's owner stands first,
# since it imports nothing of the package.
ORDER = (
    "_process",
    "_wasmtime_ffi",
    "_limits",
    "_platform_common",
    "_platform_windows",
    "_platform_posix",
    "_platform",
    "_artifacts",
    "_engines",
    "_private_dirs",
    "_zip",
    "_places",
    "_snapshot",
    "_home",
    "_outputs",
    "_results",
    "_call",
    "_sessions",
    "runner",
    "_snapshot_make",
)
RUNNER_MODULES = tuple(m for m in ORDER if m != "_wasmtime_ffi")  # the runner's text, by concern
MAY_IMPORT_MOUNTS = ("_places", "_call", "_sessions", "runner")
ABOVE = ("__init__", "__main__", "cli")  # above `runner`: they import what they like
# The tool protocol stands beside the runner in an order of its own: the schema rules, then the
# public facade, then the host side of a call. Each imports at module level only those before
# it, and no other module imports any of them at module level, so `import wasi_python` loads
# none of them; the runner reaches them late, inside the functions that run only when a call
# is given tools.
TOOLS = ("_tool_schema", "tools", "_tool_host")
BY_NAME_MODULES = (*RUNNER_MODULES, "_tool_schema", "_tool_host")  # the two forms hold over these
# The filesystem stands beside the list too: its modules import one another, in the chain the
# rules checks hold, and no other package module at module level.
FILESYSTEM = ("mounts", "_fs_memory", "_fs_descriptors", "_fs_paths", "_fs_table")
LATE_ANYWHERE = ("_wasmtime_ffi",)  # the seam's form: `from . import _wasmtime_ffi as ffi` in a def

# The late imports allowed, (file, function, module); any other is a finding.
LATE = (
    ("runner.py", "_check_tools", "tools"),
    ("_call.py", "_instance", "_fs_table"),
    ("_call.py", "_mount_linker", "_fs_memory"),
    ("_call.py", "_counted_linker", "_fs_memory"),
    ("_call.py", "_trampoline_module", "_fs_memory"),
    ("_call.py", "_tool_host", "_tool_host"),
    ("_results.py", "_ResultHost.__init__", "_tool_host"),
    ("_results.py", "_ResultHost.__init__", "tools"),
    ("_sessions.py", "_session_tool_host", "_tool_host"),
    ("_sessions.py", "_open_session", "_fs_table"),
    ("_sessions.py", "_open_session", "_tool_host"),
    ("cli.py", "_grants", "runner"),
    ("cli.py", "_main", "runner"),
)

# Check 2: the names a module may import by `from` that are neither a class, an alias nor an
# immutable constant: the two sentinels, and `process`, the accessor of the one process object,
# which is never rebound and never patched (the judge patches the object's attributes).
SENTINELS = ("_UNSET", "_DONE", "process")


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


def _order_errors(package: Path, tools: bool = False) -> list[str]:
    """The written order's findings: the runner's, or with `tools` the tool protocol's, which
    are every import made by one of its modules or naming one."""
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
                if (me in TOOLS or module in TOOLS) != tools:
                    continue
                if tools:
                    errors += _tool_order_error(where, path.name, me, function, module)
                elif function is None:
                    if module in LATE_ANYWHERE:
                        errors.append(f"{where} imports {module} at module level")
                    elif me in ABOVE:
                        continue
                    elif me in FILESYSTEM:
                        if module not in FILESYSTEM:
                            errors.append(
                                f"{where} ({me} imports {module}, outside the filesystem)"
                            )
                    elif module in FILESYSTEM:
                        if me not in MAY_IMPORT_MOUNTS:
                            errors.append(f"{where} ({me} may not import {module})")
                    elif module not in rank or rank[module] >= rank.get(me, -1):
                        errors.append(f"{where} ({me} imports {module}, not before it in ORDER)")
                elif module in LATE_ANYWHERE:
                    continue
                elif (path.name, function, module) not in LATE:
                    errors.append(f"{where} ({function} imports {module} late, not in LATE)")
    return errors


def _tool_order_error(
    where: str, filename: str, me: str, function: str | None, module: str
) -> list[str]:
    if function is not None:
        if (filename, function, module) in LATE:
            return []
        return [f"{where} ({function} imports {module} late, not in LATE)"]
    if me not in TOOLS:
        return [f"{where} imports {module} at module level"]
    if module not in TOOLS or TOOLS.index(module) >= TOOLS.index(me):
        return [f"{where} ({me} imports {module}, not before it in TOOLS)"]
    return []


def test_the_runner_modules_import_in_the_written_order() -> None:
    """Every module-level relative import names a module earlier in ORDER (or a filesystem
    module from the four that may); `__init__.py` and `cli.py` stand above; a filesystem module
    imports none outside the filesystem at module level; no module imports `_wasmtime_ffi` at
    module level; a late import is one of LATE, or of `_wasmtime_ffi`. The tool protocol's
    modules have their own order, below."""
    errors = _order_errors(PACKAGE)
    assert not errors, scan.report(errors)


def _tool_shape_errors(package: Path) -> list[str]:
    """Each of the three exists and begins with a docstring, and no top-level name is bound in
    two of them. A name bound twice in one module, such as an overloaded function's stubs and
    its body, is one binding: it is counted once per module."""
    where: dict[str, list[str]] = {}
    errors = []
    for module in TOOLS:
        path = package / f"{module}.py"
        if not path.is_file():
            errors.append(f"{path.name} does not exist")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if ast.get_docstring(tree) is None:
            errors.append(f"{path.name} does not begin with a docstring")
        for name in dict.fromkeys(_bound_names(tree)):
            where.setdefault(name, []).append(path.name)
    errors += [
        f"{name} is bound in {' and '.join(files)}"
        for name, files in where.items()
        if len(files) > 1
    ]
    return errors


def test_the_tool_modules_import_in_their_written_order() -> None:
    """The tool protocol's three modules import in the order TOOLS writes: each imports at
    module level only those before it and nothing else of the package; no other module imports
    any of them at module level; a late import of one is one of LATE. Each begins with a
    docstring, and no top-level name is bound in two of them."""
    errors = _order_errors(PACKAGE, tools=True) + _tool_shape_errors(PACKAGE)
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
    """Every `from ._x import name` of a runner module or of the tool protocol's two private
    ones, from any file but `__init__.py` (the public facade re-exports `run` and `artifacts`
    by name): (file, line, module, name)."""
    out = []
    for path in sorted(package.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node, _, _ in _imports(tree):
            if node.module and node.module.split(".")[0] in BY_NAME_MODULES:
                out += [(path.name, node.lineno, node.module, a.name) for a in node.names]
    return out


def _by_name_errors(package: Path) -> list[str]:
    errors = []
    for module in BY_NAME_MODULES:  # a module the rule names and the package lacks is stale
        if not (package / f"{module}.py").is_file():
            errors.append(f"{module}.py does not exist")
    for filename, line, module, name in _from_imports(package):
        obj = getattr(importlib.import_module(f"wasi_python.{module}"), name)
        if not _is_unchanging(name, obj):
            errors.append(
                f"{filename}:{line} imports {name} from {module} by from: {type(obj).__name__}"
            )
    return errors


def _patched(tests: Path) -> set[tuple[str, str]]:
    """Every `monkeypatch.setattr(<module>, "NAME", …)` under tests/ whose first argument names
    a module of BY_NAME_MODULES or the package, under the name the file imports it by:
    (module, NAME)."""
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
                    if a.name in BY_NAME_MODULES:
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
    """Over the fifteen runner modules, no top-level name is bound twice, and each
    module begins with a docstring."""
    errors = _once_errors(PACKAGE)
    assert not errors, scan.report(errors)
