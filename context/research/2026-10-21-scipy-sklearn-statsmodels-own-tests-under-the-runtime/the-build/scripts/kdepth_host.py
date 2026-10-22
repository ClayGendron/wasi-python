"""The AST depth of the -k expression each split group runs (pytest's parser nests one level per
`or` or `and`, so a long chain is deep; the guest's compile fails past about 300)."""

import ast
import sys

from _pytest.mark.expression import Scanner, expression

sys.path.insert(0, "/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06/tests")
from harness.packages import Split  # noqa: E402


def depth(node: ast.AST) -> int:
    kids = list(ast.iter_child_nodes(node))
    return 1 + (max(depth(k) for k in kids) if kids else 0)


def expr_depth(text: str) -> int:
    return depth(expression(Scanner(text)))


def split_depth(s: dict) -> int:
    sp = Split(s["file"], tuple(s["groups"]), tuple(s["keywords"]))
    return max(expr_depth(sp.keyword(g)) for g in s["groups"])


if __name__ == "__main__":
    import json
    from pathlib import Path

    for fam, ss in json.loads((Path(__file__).parent / sys.argv[1]).read_text()).items():
        for s in ss:
            print(fam, s["file"], len(s["groups"]), "depth", split_depth(s))
