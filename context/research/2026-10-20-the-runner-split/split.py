"""The move of spec 104, done mechanically: runner.py's top-level statements are cut into the
eleven modules by the move table (map.py), each chunk keeping the comment and blank lines above
it; a reference from one module to a function or a mutable of another gains its `_module.`
prefix (Decision 2's second form, resolved by scope so a local that shadows a global is left
alone); classes, aliases, constants and sentinels are imported by `from`; the two hooks' bodies
are Decision 4's. Run from the worktree root on 103's tip; writes src/wasi_python/*.py."""

from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

SRC = Path("src/wasi_python")
HERE = Path("build/104")

ns: dict = {}
exec(Path(HERE / "map.py").read_text().split("ORDER =")[0].split("tree = ast.parse")[0], ns)
exec(
    "\n".join(
        line
        for line in Path(HERE / "map.py").read_text().split("ORDER =")[0].splitlines()
        if line.startswith(("put(", "M = {}", "def put", "    "))
    ),
    ns,
)
M: dict[str, str] = ns["M"]
KINDS = {n: k for n, (m, k, t) in json.load(open(HERE / "kinds.json")).items()}
ORDER = [
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
]
RANK = {m: i for i, m in enumerate(ORDER)}
MAY_IMPORT_MOUNTS = {"_places", "_call", "_sessions", "runner"}

runner_src = (SRC / "runner.py").read_text()
init_src = (HERE / "init-base.py").read_text()  # 103's __init__.py; the tree's is rewritten
runner_lines = runner_src.splitlines(keepends=True)
init_lines = init_src.splitlines(keepends=True)
tree = ast.parse(runner_src)

# __init__.py's artifact block (lines 36–125) and its kinds.
INIT_START, INIT_END = 36, 125
INIT_NAMES = {
    "_ARTIFACT_DIR": "attr",
    "_ARTIFACTS_ENV": "constant",
    "_checkout_artifact_dir": "attr",
    "_CHECKOUT_ARTIFACT_DIR": "attr",
    "ArtifactsMissing": "class",
    "Artifacts": "class",
    "artifact_dir": "attr",
    "artifacts": "attr",
    "find_artifacts": "attr",
}
for n in INIT_NAMES:
    M[n] = "_artifacts"
    KINDS[n] = INIT_NAMES[n]
assert "find_artifacts" in M

# The stdlib import block of runner.py: bound name -> import statement.
STD = {}
TYPING_ONLY = {}
MOUNTS = {"METHODS", "STAGING_CEILING", "FileRecord", "Mount"}
for node in tree.body:
    if isinstance(node, ast.Import):
        for a in node.names:
            STD[a.asname or a.name.split(".")[0]] = f"import {a.name}"
    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module != "__future__":
        for a in node.names:
            STD[a.asname or a.name] = (node.module, a.name)
    elif isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
        for sub in node.body:
            if isinstance(sub, ast.Import):
                for a in sub.names:
                    TYPING_ONLY[a.name.split(".")[0]] = f"import {a.name}"
            elif isinstance(sub, ast.ImportFrom):
                for a in sub.names:
                    TYPING_ONLY[a.name] = (("." * sub.level) + (sub.module or ""), a.name)
assert "TYPE_CHECKING" in STD


# --- scope-aware name resolution ------------------------------------------------------------


def names_of(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    out = []
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                out.append(t.id)
            elif isinstance(t, ast.Tuple):
                out += [e.id for e in t.elts if isinstance(e, ast.Name)]
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        out.append(node.target.id)
    return out


def targets_of(t: ast.AST) -> list[str]:
    if isinstance(t, ast.Name):
        return [t.id]
    if isinstance(t, (ast.Tuple, ast.List)):
        return [n for e in t.elts for n in targets_of(e)]
    if isinstance(t, ast.Starred):
        return targets_of(t.value)
    return []


SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def bound_in(scope: ast.AST) -> tuple[set[str], set[str]]:
    """(names bound directly in this scope, names declared global in it)."""
    bound: set[str] = set()
    globals_: set[str] = set()
    if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        a = scope.args
        for arg in a.posonlyargs + a.args + a.kwonlyargs:
            bound.add(arg.arg)
        if a.vararg:
            bound.add(a.vararg.arg)
        if a.kwarg:
            bound.add(a.kwarg.arg)
    if isinstance(scope, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
        for gen in scope.generators:
            bound |= set(targets_of(gen.target))
        body = []
    else:
        body = scope.body if not isinstance(scope, ast.Lambda) else [scope.body]

    def walk(child: ast.AST) -> None:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(child.name)
            return  # its own scope
        if isinstance(child, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            # a walrus inside binds here; nothing else does
            for sub in ast.walk(child):
                if isinstance(sub, ast.NamedExpr):
                    bound.add(sub.target.id)
            return
        if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
            bound.add(child.id)
        elif isinstance(child, ast.Global):
            globals_.update(child.names)
        elif isinstance(child, ast.Nonlocal):
            bound.update(child.names)  # not global, whatever it is
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
            for a in child.names:
                bound.add((a.asname or a.name).split(".")[0])
        elif isinstance(child, ast.ExceptHandler) and child.name:
            bound.add(child.name)
        elif isinstance(child, ast.NamedExpr):
            bound.add(child.target.id)
        elif isinstance(child, ast.MatchAs) and child.name:
            bound.add(child.name)
        for sub in ast.iter_child_nodes(child):
            walk(sub)

    for b in body:
        walk(b)
    return bound - globals_, globals_


class Resolver:
    """Walks one top-level chunk and reports every Load Name that resolves to the module scope."""

    def __init__(self) -> None:
        self.found: list[tuple[str, int, int]] = []  # (name, lineno, col)
        self.cache: dict[int, tuple[set[str], set[str]]] = {}

    def scopes(self, node: ast.AST) -> tuple[set[str], set[str]]:
        if id(node) not in self.cache:
            self.cache[id(node)] = bound_in(node)
        return self.cache[id(node)]

    def is_global(self, name: str, chain: list[ast.AST]) -> bool:
        # the current scope first (a class body sees its own names), then enclosing functions
        for i, scope in enumerate(reversed(chain)):
            bound, globals_ = self.scopes(scope)
            if name in globals_:
                return True
            if i > 0 and isinstance(scope, ast.ClassDef):
                continue
            if name in bound:
                return False
        return True

    def visit(self, node: ast.AST, chain: list[ast.AST]) -> None:
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load) and self.is_global(node.id, chain):
                self.found.append((node.id, node.lineno, node.col_offset))
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.decorator_list:
                self.visit(d, chain)
            a = node.args
            for d in a.defaults + [k for k in a.kw_defaults if k is not None]:
                self.visit(d, chain)
            for arg in a.posonlyargs + a.args + a.kwonlyargs + [x for x in (a.vararg, a.kwarg) if x]:
                if arg.annotation:
                    self.visit(arg.annotation, chain)
            if node.returns:
                self.visit(node.returns, chain)
            for b in node.body:
                self.visit(b, chain + [node])
            return
        if isinstance(node, ast.Lambda):
            a = node.args
            for d in a.defaults + [k for k in a.kw_defaults if k is not None]:
                self.visit(d, chain)
            self.visit(node.body, chain + [node])
            return
        if isinstance(node, ast.ClassDef):
            for d in node.decorator_list + node.bases + [k.value for k in node.keywords]:
                self.visit(d, chain)
            for b in node.body:
                self.visit(b, chain + [node])
            return
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            first = node.generators[0]
            self.visit(first.iter, chain)  # evaluated outside
            inner = chain + [node]
            self.visit(first.target, inner)
            for cond in first.ifs:
                self.visit(cond, inner)
            for gen in node.generators[1:]:
                self.visit(gen.iter, inner)
                self.visit(gen.target, inner)
                for cond in gen.ifs:
                    self.visit(cond, inner)
            if isinstance(node, ast.DictComp):
                self.visit(node.key, inner)
                self.visit(node.value, inner)
            else:
                self.visit(node.elt, inner)
            return
        for child in ast.iter_child_nodes(node):
            self.visit(child, chain)


# --- chunks -----------------------------------------------------------------------------------

Chunk = tuple[str | None, int, int, ast.AST]  # module, first line, last line (1-based, inclusive)
chunks: list[Chunk] = []
prev_end = 0
for node in tree.body:
    start, end = prev_end + 1, node.end_lineno
    names = names_of(node)
    if names:
        mod: str | None = M[names[0]]
    elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
        mod = "runner"  # the module docstring
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
        mod = None
    elif isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
        mod = None
    elif isinstance(node, ast.If):
        mod = "runner"  # os.register_at_fork
    else:
        raise SystemExit(f"unplaced top-level statement at line {node.lineno}")
    chunks.append((mod, start, end, node))
    prev_end = end

HOOKS = {"_after_fork_in_child", "_release"}

AFTER_FORK = '''def _after_fork_in_child() -> None:
    """Only assignments, and no lock: a lock may have been held by a thread the fork left out, so
    every lock the runner takes is made anew (spec 015's build review, F8)."""
    global _pool_lock, _live_lock
    _pool_lock, _live_lock = threading.Lock(), threading.Lock()
    _private_dirs._held_lock = threading.Lock()
    # A fork inside the runner's stack-size window leaves the child at the guest thread's size;
    # put back the value the runner found (spec 078, the review's F6).
    if _home._stack_size_found:
        threading.stack_size(_home._stack_size_found[0])
        _home._stack_size_found.clear()
    _home._stack_size_lock = threading.Lock()
    # A child has none of its parent's tool threads (spec 036, Decision 8).
    _call._tool_threads_lock, _call._tool_threads["running"] = threading.Lock(), 0
    _zip._zip_lock, _zip._zips = threading.Lock(), {}  # the parent's zip folders stay the parent's
    _engines._lock, _call._epoch_callback_lock, _call._outputs_lock = (
        threading.Lock(),
        threading.Lock(),
        threading.RLock(),
    )
    _engines._compiling = {}
    _pool.update(pool=None, size=0)
    _pools.clear()
    _live.clear()
    _engines._epoch_ticker._thread, _engines._epoch_ticker._active = None, 0
    _engines._epoch_ticker._cond = threading.Condition()
    # A child has no reaper, no sessions and none open (spec 055, Decision 13).
    _sessions._sessions_lock, _sessions._sessions = threading.Lock(), weakref.WeakSet()
    _sessions._reaper_queue, _sessions._closers_lock = queue.SimpleQueue(), threading.Lock()
    _sessions._closers.clear()
    _sessions._dropped.clear()
    _sessions._reaper.update(thread=None, stop=False, hooked=_sessions._reaper["hooked"])
    _engines._counts["sessions_open"] = 0
    if _platform._fork["used"]:
        _platform._fork["forked"] = True
'''

RELEASE = '''@atexit.register
def _release() -> None:
    """Remove this process's zip folders, and free the cached linkers, modules and engines while
    wasmtime's bindings still exist."""
    _zip._remove_zips()
    _private_dirs._flush_warnings()  # spec 084
    _engines._check_modules.clear()
    _call._linkers.clear()
    _call._mount_linkers.clear()
    _call._guard_linkers.clear()
    _call._trampolines.clear()
    _call._stat_trampolines.clear()
    _engines._modules.clear()
    _engines._engines.clear()
'''

# --- per-module text --------------------------------------------------------------------------

texts: dict[str, list[str]] = defaultdict(list)  # module -> chunk texts
uses: dict[str, set[str]] = defaultdict(set)  # module -> global names it reads
qualified: dict[str, set[int]] = defaultdict(set)  # module -> source lines qualified
insertions = 0
late_deleted = []


def chunk_text(start: int, end: int, edits: list[tuple[int, int, str]]) -> str:
    """The lines start..end with `_module.` prefixes inserted at (line, col)."""
    out = []
    by_line: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for line, col, prefix in edits:
        by_line[line].append((col, prefix))
    for n in range(start, end + 1):
        text = runner_lines[n - 1]
        for col, prefix in sorted(by_line.get(n, []), reverse=True):
            assert text[col:].startswith(prefix.split(".")[0][0]) or True
            text = text[:col] + prefix + text[col:]
        out.append(text)
    return "".join(out)


def strip_late_artifacts_missing(text: str) -> str:
    """Delete the late `from . import ArtifactsMissing` lines (and a blank line they leave at the
    head of a block)."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "from . import ArtifactsMissing":
            late_deleted.append(line.rstrip("\n"))
            if i + 1 < len(lines) and lines[i + 1].strip() == "" and out and out[-1].rstrip().endswith(":"):
                i += 2
                continue
            i += 1
            continue
        out.append(line)
        i += 1
    return "".join(out)


for mod, start, end, node in chunks:
    if mod is None:
        continue
    names = names_of(node)
    if names and names[0] in HOOKS:
        text = AFTER_FORK if names[0] == "_after_fork_in_child" else RELEASE
        gap = "".join(runner_lines[start - 1 : node.lineno - 1 - (1 if names[0] == "_release" else 0)])
        texts[mod].append(gap + text)
        # the hooks read these modules by attribute
        for m in ("_private_dirs", "_home", "_call", "_zip", "_engines", "_sessions", "_platform"):
            uses[mod].add(f"<module {m}>")
        uses[mod].update({"threading", "weakref", "queue", "atexit"})
        continue
    r = Resolver()
    r.visit(node, [])
    edits = []
    for name, line, col in r.found:
        uses[mod].add(name)
        if name in M and M[name] != mod and KINDS[name] == "attr":
            edits.append((line, col, f"{M[name]}."))
            qualified[mod].add(line)
            insertions += 1
    # the `global` names of a chunk must be the chunk's own module's
    for sub in ast.walk(node):
        if isinstance(sub, ast.Global):
            for g in sub.names:
                assert M[g] == mod, (names, g)
    text = chunk_text(start, end, edits)
    before = len(late_deleted)
    text = strip_late_artifacts_missing(text)
    if len(late_deleted) > before:
        uses[mod].add("ArtifactsMissing")  # the late import is now the module-level one
    texts[mod].append(text)

# __init__.py's block goes first in _artifacts.py
init_block = "".join(init_lines[INIT_START - 1 : INIT_END])
init_tree = ast.parse(init_src)
r = Resolver()
for node in init_tree.body:
    if INIT_START <= node.lineno <= INIT_END:
        r.visit(node, [])
init_uses = {name for name, _, _ in r.found}
texts["_artifacts"].insert(0, init_block + "\n\nfind_artifacts = artifacts\n")
uses["_artifacts"] |= init_uses

# --- imports ----------------------------------------------------------------------------------

DOCS = {
    "_limits": '''"""The limits of a call: the tick constants, the checks of every limit argument, the text and
input checks, the worker count, and the sentinel `_UNSET` for an argument not given."""''',
    "_platform": '''"""What the operating system decides: the flags and the kernel's identity, the two lock
implementations, fork, directory descriptors, the stack sizes and the three stack probes, and
the trap-handler guard."""''',
    "_artifacts": '''"""The artifact set: `Artifacts`, `ArtifactsMissing`, `artifact_dir` and `artifacts()`, and the
facts about the set's files the runner reads: its digests, stamps, version tag and guest
packages."""''',
    "_engines": '''"""wasmtime-py's import and the two engines (the adapter import stays inside `_wasmtime`, so
importing this module loads no wasmtime-py), the compiled modules and the `.cwasm` cache, the
module lock and the counts, the epoch ticker, and the preopen check's WAT module."""''',
    "_private_dirs": '''"""Private folders: `_Private` and its lock protocol, the sweep, the budgeted tree remover and
its two walks, the queued warnings, and the removal of a fresh home."""''',
    "_zip": '''"""The private copy of the stdlib zip and matplotlib's data: the zip folders, the member
extraction, the intact check and the removal at exit."""''',
    "_places": '''"""Places a guest may reach: `Grant`, the argument checks for root, grants, mounts and the
import path, the POSIX and Windows walks and their judge, SipHash-1-3 and the preopen check,
the runtime and shared folders, and the real directory at a path."""''',
    "_home": '''"""The threads of a call: the per-thread stack of calls, Ctrl-C on the main thread, and the
home and guest threads a call runs on."""''',
    "_call": '''"""One call: `Completed`, the checked run and the instance, the driver and `_Call`, the
host-function wrapper and the epoch callback, the linkers and trampolines, the output streams,
`poll_oneoff`, the door and the tool host."""''',
    "_sessions": '''"""Sessions: `SessionEnded`, the state of a session, the reaper, the endings and the shutdown,
the turns, and `_open_session`."""''',
}


def import_block(mod: str) -> str:
    used = uses[mod]
    std: list[str] = []
    froms: dict[str, set[str]] = defaultdict(set)
    typing_lines: list[str] = []
    typing_froms: dict[str, set[str]] = defaultdict(set)
    for name in sorted(used):
        if name in STD:
            v = STD[name]
            if isinstance(v, str):
                std.append(v)
            else:
                froms[v[0]].add(v[1] if v[1] == name else f"{v[1]} as {name}")
        elif name in TYPING_ONLY:
            v = TYPING_ONLY[name]
            if isinstance(v, str):
                typing_lines.append(v)
            else:
                typing_froms[v[0]].add(v[1])
    pkg: set[str] = set()
    pkg_froms: dict[str, set[str]] = defaultdict(set)
    up_froms: dict[str, set[str]] = defaultdict(set)
    for name in sorted(used):
        if name.startswith("<module "):
            pkg.add(name[8:-1])
        elif name in MOUNTS:
            assert mod in MAY_IMPORT_MOUNTS, (mod, name)
            pkg_froms[".mounts"].add(name)
        elif name in M and M[name] != mod:
            other = M[name]
            if KINDS[name] == "attr":
                assert RANK[other] < RANK[mod], (mod, name, other)
                pkg.add(other)
            elif RANK[other] < RANK[mod]:
                pkg_froms[f".{other}"].add(name)
            else:
                up_froms[f".{other}"].add(name)
    if typing_lines or typing_froms or up_froms:
        froms["typing"].add("TYPE_CHECKING")
    lines = ["from __future__ import annotations", ""]
    lines += std
    for m in sorted(froms):
        lines.append(f"from {m} import {', '.join(sorted(froms[m]))}")
    lines.append("")
    if pkg:
        lines.append(f"from . import {', '.join(sorted(pkg))}")
    for m in sorted(pkg_froms):
        lines.append(f"from {m} import {', '.join(sorted(pkg_froms[m]))}")
    if typing_lines or typing_froms or up_froms:
        lines += ["", "if TYPE_CHECKING:"]
        lines += [f"    {t}" for t in typing_lines]
        for m in sorted({**typing_froms, **up_froms}):
            names = sorted(typing_froms.get(m, set()) | up_froms.get(m, set()))
            lines.append(f"    from {m} import {', '.join(names)}")
    return "\n".join(lines) + "\n"


def join_chunks(parts: list[str]) -> str:
    return "".join(parts)


written = {}
for mod in ORDER:
    parts = texts[mod]
    if mod == "runner":
        doc = parts[0]  # the module docstring, lines 1–17
        body = join_chunks(parts[1:])
        text = doc + "\n" + import_block(mod) + body
    else:
        text = DOCS[mod] + "\n\n" + import_block(mod) + join_chunks(parts)
    if not text.endswith("\n"):
        text += "\n"
    written[mod] = text

for mod, text in written.items():
    (SRC / f"{mod}.py").write_text(text)

print("insertions:", insertions, "lines qualified:", sum(len(v) for v in qualified.values()))
print("lines qualified by module:", {m: len(v) for m, v in qualified.items()})
print("late ArtifactsMissing imports deleted:", len(late_deleted))
over = []
for mod, text in written.items():
    for i, line in enumerate(text.splitlines(), 1):
        if len(line) > 100:
            over.append(f"{mod}.py:{i}: {len(line)}")
print("lines over 100 columns:", over)
print("sizes:", {m: len(t.splitlines()) for m, t in written.items()})
