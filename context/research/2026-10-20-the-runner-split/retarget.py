"""Decision 5: every test, check and harness file that names a runner private is re-pointed to
the module the name moved to, in the form it used; the needed `from wasi_python import _x`
is added to the import line in scope (module-level, or the function's own)."""
import ast, json, re, sys
from collections import defaultdict
from pathlib import Path

ns = {}
exec("\n".join(l for l in Path("build/103/map.py").read_text().split("ORDER =")[0].splitlines()
              if l.startswith(("put(", "M = {}", "def put", "    "))), ns)
M = ns["M"]
for n in ("_ARTIFACT_DIR", "_ARTIFACTS_ENV", "_checkout_artifact_dir", "_CHECKOUT_ARTIFACT_DIR",
          "ArtifactsMissing", "Artifacts", "artifact_dir", "artifacts", "find_artifacts"):
    M[n] = "_artifacts"
SKIP = {"tests/harness/api.py", "tests/unit/test_cli.py", "tests/unit/test_runner_package.py"}
ATTR = re.compile(r"(?<![\w.])runner\.([A-Za-z_][A-Za-z0-9_]*)")
SETATTR = re.compile(r'setattr\(runner, "([A-Za-z_][A-Za-z0-9_]*)"')
TOP = re.compile(r"\bwasi_python\.(_ARTIFACT_DIR|_CHECKOUT_ARTIFACT_DIR|_ARTIFACTS_ENV)\b")
TOPSET = re.compile(r'setattr\(wasi_python, "(_ARTIFACT_DIR|_CHECKOUT_ARTIFACT_DIR)"')

report = []
for path in sorted(Path("tests").rglob("*.py")):
    rel = path.as_posix()
    if rel in SKIP:
        continue
    src = path.read_text()
    if "runner" not in src and "wasi_python._" not in src:
        continue
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    # import lines of runner and their scopes
    imports = []  # (lineno, span_start, span_end, names)
    def walk(node, span):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(ch, (ch.lineno, ch.end_lineno))
            elif isinstance(ch, ast.ImportFrom) and ch.module == "wasi_python" and ch.level == 0:
                imports.append([ch.lineno, span, [a.name for a in ch.names], set()])
            else:
                walk(ch, span)
    walk(tree, (1, len(lines)))
    needs = defaultdict(set)  # import index -> modules
    def scope_for(lineno, name_hint):
        best = None
        for i, (il, (a, b), names, _) in enumerate(imports):
            if a <= lineno <= b and ("runner" in names or name_hint == "_artifacts"):
                if best is None or (b - a) < (imports[best][1][1] - imports[best][1][0]):
                    best = i
        return best
    changed = False
    for i, line in enumerate(lines):
        n = i + 1
        new = line
        def rep_attr(m):
            name = m.group(1)
            mod = M.get(name, "runner")
            if mod == "runner":
                return m.group(0)
            needs_mod.append(mod)
            return f"{mod}.{name}"
        def rep_set(m):
            name = m.group(1)
            mod = M.get(name, "runner")
            if mod == "runner":
                return m.group(0)
            needs_mod.append(mod)
            return f'setattr({mod}, "{name}"'
        needs_mod = []
        new = SETATTR.sub(rep_set, new)
        new = ATTR.sub(rep_attr, new)
        new = TOPSET.sub(lambda m: (needs_mod.append("_artifacts"), f'setattr(_artifacts, "{m.group(1)}"')[1], new)
        new = TOP.sub(lambda m: (needs_mod.append("_artifacts"), f"_artifacts.{m.group(1)}")[1], new)
        if new != line:
            lines[i] = new
            changed = True
            report.append(f"{rel}:{n}: {line.strip()}  ->  {new.strip()}")
            for mod in set(needs_mod):
                s = scope_for(n, mod)
                if s is None:
                    needs["<new>"].add(mod)
                else:
                    needs[s].add(mod)
    if not changed:
        continue
    # extend the import lines
    for s, mods in needs.items():
        if s == "<new>":
            continue
        il, _, names, _ = imports[s]
        line = lines[il - 1]
        m = re.match(r"^(\s*)from wasi_python import (.*)$", line)
        assert m, (rel, il, line)
        have = [x.strip() for x in m.group(2).split(",")]
        allnames = sorted(set(have) | mods, key=lambda x: (x.lstrip("_"), x))
        lines[il - 1] = f"{m.group(1)}from wasi_python import {', '.join(allnames)}\n"
    if "<new>" in needs:
        # a module-level import after `import wasi_python` or the first import line
        mods = sorted(needs["<new>"])
        for i, line in enumerate(lines):
            if line.startswith("import wasi_python"):
                lines.insert(i + 1, f"from wasi_python import {', '.join(mods)}\n")
                break
        else:
            raise SystemExit(f"{rel}: nowhere to add {mods}")
        report.append(f"{rel}: added module-level import of {mods}")
    path.write_text("".join(lines))
Path("build/103/retarget-report.txt").write_text("\n".join(report) + "\n")
print(len(report), "lines changed; report in build/103/retarget-report.txt")
