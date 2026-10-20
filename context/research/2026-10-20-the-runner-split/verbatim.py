"""The residue of spec 104's move (Decision 8, item 2): what is on one side only, by category.

Reads 103's `runner.py` and `__init__.py` from git (the base commit, the one argument) and, after
the move, the eleven modules plus `__init__.py`, strips blank lines, and compares the multisets
of lines, in two steps:

1. The base against the split as the splitter wrote it (`build/104/preformat/`, before ruff
   sorted the imports and formatted the files; `__init__.py` has no pre-format copy and is read
   from the tree). A line only on the new side is tried again with its `_module.` prefixes
   stripped (one prefix per name: `_sessions._sessions.add` is `_sessions.add`); what remains
   must be an import line, a line of a module docstring, a line of the two hooks' bodies, or the
   alias line. A line only on the old side must be an import line, a line of the two hooks' old
   bodies, the "Last:" comment, or the source of a qualified line.
2. The splitter's output against the tree: every line only in the tree is an import line (ruff's
   `I` rule) or a fragment of one line the formatter wrapped (a qualified line past 100 columns,
   or the one comment moved above its line); every line only in the splitter's output is an
   import line or a line that was wrapped.

Prints the residue by category and its counts; the uncategorised residue must be empty on every
side, else the exit code is 1.

    uv run python build/104/verbatim.py <base commit>
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

SRC = Path("src/wasi_python")
PRE = Path("build/104/preformat")
MODULES = [
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
PREFIX = re.compile(r"\b(" + "|".join(MODULES) + r")\.")
SAME = re.compile(r"\b(" + "|".join(MODULES) + r")\.(?=\1\b)")
IMPORT = re.compile(r"^\s*(import\s|from\s.+\simport\s|from\s\S+\simport\s\($)")
IMPORT_CONT = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*( as [A-Za-z_][A-Za-z0-9_]*)?,$|^\)$|^if TYPE_CHECKING:$")
HOOKS = ("_after_fork_in_child", "_release")
ALIAS = "find_artifacts = artifacts"
LAST = "# Last: runner.py imports Artifacts from here."

base = sys.argv[1]


def show(path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{base}:{path}"], capture_output=True, text=True, check=True
    ).stdout


def lines_of(text: str) -> Counter:
    return Counter(line for line in text.splitlines() if line.strip())


def hook_lines(text: str) -> set[str]:
    """Every line of the two hooks' bodies (the def line and the docstring are moves)."""
    tree = ast.parse(text)
    src = text.splitlines()
    out = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in HOOKS:
            first = node.body[1].lineno if ast.get_docstring(node) else node.body[0].lineno
            out |= {line for line in src[first - 1 : node.end_lineno] if line.strip()}
    return out


def docstring_lines(text: str) -> set[str]:
    node = ast.parse(text).body[0]
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
        return {line for line in text.splitlines()[node.lineno - 1 : node.end_lineno] if line.strip()}
    return set()


def is_import(line: str) -> bool:
    return bool(IMPORT.match(line) or IMPORT_CONT.match(line))


old_runner = show("src/wasi_python/runner.py")
old_init = show("src/wasi_python/__init__.py")
old = lines_of(old_runner) + lines_of(old_init)
pre_texts = {m: (PRE / f"{m}.py").read_text() for m in MODULES}
pre_texts["__init__"] = (SRC / "__init__.py").read_text()
final_texts = {m: (SRC / f"{m}.py").read_text() for m in MODULES}
final_texts["__init__"] = pre_texts["__init__"]
pre = sum((lines_of(t) for t in pre_texts.values()), Counter())
final = sum((lines_of(t) for t in final_texts.values()), Counter())

# --- step 1: the base against the splitter's output ----------------------------------------
only_new = pre - old
only_old = old - pre
old_hooks = hook_lines(old_runner)
new_hooks = hook_lines(pre_texts["runner"])
new_docs: set[str] = set()
for m, text in pre_texts.items():
    if m != "runner":  # runner.py keeps today's docstring, which is a move
        new_docs |= docstring_lines(text)

NEW_KINDS = ("import", "docstring", "qualified", "hook", "alias", "uncategorised")
new_by: dict[str, Counter] = {k: Counter() for k in NEW_KINDS}
sources: Counter = Counter()
for line, n in only_new.items():
    candidates = (SAME.sub("", line), PREFIX.sub("", line))
    source = next((c for c in candidates if c != line and old[c] > 0), None)
    if is_import(line):
        new_by["import"][line] += n
    elif line in new_docs:
        new_by["docstring"][line] += n
    elif line in new_hooks:
        new_by["hook"][line] += n
    elif line.strip() == ALIAS:
        new_by["alias"][line] += n
    elif source is not None:
        new_by["qualified"][line] += n
        sources[source] += n
    else:
        new_by["uncategorised"][line] += n

OLD_KINDS = ("import", "hook", "last", "qualified source", "uncategorised")
old_by: dict[str, Counter] = {k: Counter() for k in OLD_KINDS}
for line, n in only_old.items():
    if is_import(line):
        old_by["import"][line] += n
    elif line in old_hooks:
        old_by["hook"][line] += n
    elif line.strip() == LAST:
        old_by["last"][line] += n
    elif sources[line] > 0:
        old_by["qualified source"][line] += n
    else:
        old_by["uncategorised"][line] += n

# --- step 2: the splitter's output against the tree ----------------------------------------
# Per module, the lines only on one side, in file order, as one token stream (parentheses and
# commas dropped: the formatter adds and moves them); a line is a wrapped fragment when its
# tokens are a contiguous run of the other side's stream.
TOKEN = re.compile(r"\w+|[^\w\s]")


def toks(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text) if t not in "(),"]


def contiguous(part: list[str], whole: list[str]) -> bool:
    n = len(part)
    return n > 0 and any(whole[i : i + n] == part for i in range(len(whole) - n + 1))


only_final = final - pre
only_pre = pre - final
FINAL_KINDS = ("import", "wrapped fragment", "uncategorised")
PRE_KINDS = ("import", "wrapped", "uncategorised")
final_by: dict[str, Counter] = {k: Counter() for k in FINAL_KINDS}
pre_by: dict[str, Counter] = {k: Counter() for k in PRE_KINDS}
COMMENT_MOVED = (  # the one trailing comment moved above its line (build/104/wrap_comment.py)
    "    _private_dirs._flush_warnings()  # what the release's removals queued, outside every lock (spec 084)",
)


def side(text: str, only: Counter) -> list[str]:
    """The lines of `text`, in order, that are only on this side, each as many times as it is."""
    left = Counter(only)
    out = []
    for line in text.splitlines():
        if left[line] > 0 and not is_import(line):
            out.append(line)
            left[line] -= 1
    return out


for m in pre_texts:
    pre_side = side(pre_texts[m], lines_of(pre_texts[m]) - lines_of(final_texts[m]))
    final_side = side(final_texts[m], lines_of(final_texts[m]) - lines_of(pre_texts[m]))
    pre_stream = toks(" ".join(pre_side))
    final_stream = toks(" ".join(final_side))
    for line in final_side:
        part = toks(line)
        ok = not part or contiguous(part, pre_stream)  # a bare bracket line, or a run of tokens
        final_by["wrapped fragment" if ok else "uncategorised"][f"{m}: {line}"] += 1
    for line in pre_side:
        if line in COMMENT_MOVED:
            pre_by["wrapped"][line] += 1
        else:
            ok = contiguous(toks(line), final_stream)
            pre_by["wrapped" if ok else "uncategorised"][f"{m}: {line}" if not ok else line] += 1
for line, n in only_final.items():
    if is_import(line):
        final_by["import"][line] += n
for line, n in only_pre.items():
    if is_import(line):
        pre_by["import"][line] += n

print(f"lines (blank lines stripped): base {sum(old.values())}, split {sum(pre.values())}, tree {sum(final.values())}")
print("step 1, only in the split, by category:")
for k, c in new_by.items():
    print(f"  {k}: {sum(c.values())}")
print("step 1, only in the base, by category:")
for k, c in old_by.items():
    print(f"  {k}: {sum(c.values())}")
print("step 2, only in the tree, by category:")
for k, c in final_by.items():
    print(f"  {k}: {sum(c.values())}")
print("step 2, only in the split, by category:")
for k, c in pre_by.items():
    print(f"  {k}: {sum(c.values())}")
if pre_by["wrapped"]:
    print("the lines the formatter wrapped (each a qualified line past 100 columns, or the moved comment):")
    for line in pre_by["wrapped"]:
        print(f"  {line.strip()}")
bad = False
for name, c in (
    ("split (step 1)", new_by["uncategorised"]),
    ("base (step 1)", old_by["uncategorised"]),
    ("tree (step 2)", final_by["uncategorised"]),
    ("split (step 2)", pre_by["uncategorised"]),
):
    if c:
        bad = True
        print(f"uncategorised residue on the {name} side ({sum(c.values())} lines):")
        for line, n in sorted(c.items()):
            print(f"  {n}x {line}")
print("uncategorised residue:", "none" if not bad else "see above")
sys.exit(1 if bad else 0)
