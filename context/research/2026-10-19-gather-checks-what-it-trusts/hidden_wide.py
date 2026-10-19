# Spec 085, the pre-build review's F5: what the widened hidden_ci_needs would flag. A prototype.
# uv run python -I <this> <repo root>. Exempt: needs.py and gather.py (they define the vocabulary);
# under tests/harness/ a CI need counts only as a call argument or a container element.
import ast, sys
from pathlib import Path
CI = {"oracle", "prior-art clones", "three systems", "descriptor limit"}
root = Path(sys.argv[1])
files = sorted([*root.glob("tests/checks/**/*.py"), *root.glob("tests/harness/*.py"), root / "tests/conftest.py"])
for f in files:
    rel = f.relative_to(root).as_posix()
    tree = ast.parse(f.read_text())
    inside = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_") and rel.startswith("tests/checks/"):
            for m in ast.walk(n):
                inside.add(id(m))
    parent = {id(c): n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    for n in ast.walk(tree):
        if rel in ("tests/harness/needs.py", "tests/harness/gather.py"):
            break
        if rel.startswith("tests/harness/") and isinstance(n, ast.Constant) and n.value in CI:
            up = parent.get(id(n))
            if not isinstance(up, (ast.Call, ast.Dict, ast.List, ast.Tuple, ast.Set, ast.keyword)):
                continue
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            if n.value in CI and id(n) not in inside:
                print(f"{rel}:{n.lineno}: {n.value!r}")
            if n.value.startswith("needs: "):  # anywhere, test bodies too
                print(f"{rel}:{n.lineno}: {n.value!r} (a 'needs: ' literal)")
