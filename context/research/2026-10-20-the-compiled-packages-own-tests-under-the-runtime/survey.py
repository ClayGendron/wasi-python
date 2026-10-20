"""Host side of spec 066's survey (Decision 1): stage one family, run one group in the snapshot
binary through the judge's own embedder, keep the stream and the fuel. A scratch tool, not judge
code. Run from the worktree: `uv run python build/survey/survey.py <group>`.
"""

import ast
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

W = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(W / "tests"))
from harness import guest, paths  # noqa: E402

SURVEY = W / "build" / "survey"
TREES = SURVEY / "trees"
OUT = SURVEY / "out"
STAGES = W / "build" / "harness" / "survey-stage"
KIT = W / "build" / "upstream" / "wheels"
CAP = 1_500_000_000_000

MPL = "lib/matplotlib/tests/"
AXES = [MPL + "test_axes.py"]
MATHTEXT = [MPL + f"test_{n}.py" for n in (
    "mathtext", "text", "textpath", "font_manager", "ft2font", "afm", "type1font", "dviread",
    "usetex", "texmanager")]
RENDER = [MPL + f"test_{n}.py" for n in (
    "image", "collections", "constrainedlayout", "figure", "patches", "polar", "legend",
    "colorbar", "contour", "lines", "backend_pdf", "backend_ps", "backend_svg", "backend_pgf",
    "simplification", "quiver", "tightlayout", "streamplot", "bbox_tight", "patheffects",
    "arrow_patches", "triangulation")]
MPL_OUT = [MPL + f for f in ("test_backend_webagg.py", "test_backends_interactive.py",
                             "test_determinism.py")]
TOOLKITS = [f"lib/mpl_toolkits/{t}/tests" for t in ("axes_grid1", "axisartist", "mplot3d")]
MPL_PP = {"matplotlib": "lib/matplotlib",
          "mpl_toolkits.axes_grid1": "lib/mpl_toolkits/axes_grid1",
          "mpl_toolkits.axisartist": "lib/mpl_toolkits/axisartist",
          "mpl_toolkits.mplot3d": "lib/mpl_toolkits/mplot3d"}

LX = "src/lxml/"
LXML_DOC = [f"doc/{n}.txt" for n in (
    "element_classes", "validation", "sax", "tutorial", "api", "FAQ", "parsing", "resolvers",
    "xpathxslt", "objectify", "extensions")]
LXML_HTML_DOC = [LX + f"html/tests/test_{n}.txt" for n in (
    "basic", "formfill", "diff", "rewritelinks", "forms", "xhtml")]

FAMILIES = {
    "matplotlib": dict(tarball="matplotlib-3.11.2", folders=[MPL, "lib/matplotlib/testing/", *[
        t + "/" for t in TOOLKITS]], files=["lib/matplotlib/cm.pyi"],
        ini="[pytest]\nminversion = 7.0\n"),
    "contourpy": dict(tarball="contourpy-1.4.0", folders=["tests/"],
                      ini="[pytest]\nmarkers =\n    flaky: pytest-rerunfailures' marker\n"),
    "pillow": dict(tarball="pillow-13.0.0", folders=["Tests/"],
                   ini="[pytest]\nmarkers =\n    timeout: pytest-timeout's marker, which Pillow's tests carry\n"),
    "kiwisolver": dict(tarball="kiwisolver-1.5.1", folders=["py/tests/"], ini="[pytest]\n"),
    "lxml": dict(tarball="lxml-6.1.3", folders=[LX + "tests/", LX + "html/tests/"],
                 files=LXML_DOC + ["doc/test.xml", "samples/simple.xml", "samples/simple-ns.xml"], ini="[pytest]\ndoctest_optionflags = ELLIPSIS\n"),
    "regex": dict(tarball="regex-2026.9.29", folders=["regex/tests/"], ini="[pytest]\n"),
}


def ignores(files):
    return [f"--ignore={f}" for f in files]


def lxml_keep(tree: Path) -> dict:
    keep = {}
    for p in sorted((tree / LX).glob("**/tests/test_*.py")):
        rel = p.relative_to(tree).as_posix()
        mod = ast.parse(p.read_text(encoding="utf-8"))
        fn = next((n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name == "test_suite"), None)
        if fn is None:
            continue
        names, star = set(), False
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("loadTestsFromTestCase", "makeSuite") and node.args:
                    a = node.args[0]
                    if isinstance(a, ast.Name):
                        names.add(a.id)
                elif node.func.attr == "loadTestsFromModule":
                    star = True
        keep[rel] = "*" if star else sorted(names)
    return keep


def group_spec(group: str, tree: Path) -> tuple[str, dict]:
    if group.startswith("matplotlib") or group.startswith("mpl-"):
        base = dict(package_paths=MPL_PP, cwd="/tmp/work")
        if group == "matplotlib-axes":
            args = AXES
        elif group == "matplotlib-mathtext":
            args = MATHTEXT
        elif group in ("matplotlib-render-2a", "matplotlib-render-2b"):
            r = sorted(RENDER)[8:15]
            args = r[:3] if group.endswith("2a") else r[3:]
        elif group in ("matplotlib-render-1", "matplotlib-render-2", "matplotlib-render-3"):
            r = sorted(RENDER)
            args = {"1": r[:8], "2": r[8:15], "3": r[15:]}[group[-1]]
        elif group in ("matplotlib-render-a", "matplotlib-render-b"):
            r = sorted(RENDER)
            args = r[:11] if group.endswith("-a") else r[11:]
        elif group in ("matplotlib-rest-b1", "matplotlib-rest-b2"):
            taken = set(AXES + MATHTEXT + RENDER + MPL_OUT)
            rest = sorted(p.relative_to(tree).as_posix() for p in (tree / MPL).glob("test_*.py")
                          if p.relative_to(tree).as_posix() not in taken)
            rb = rest[len(rest) // 2:]
            args = rb[:len(rb) // 2] if group.endswith("b1") else rb[len(rb) // 2:]
        elif group in ("matplotlib-rest-a", "matplotlib-rest-b"):
            taken = set(AXES + MATHTEXT + RENDER + MPL_OUT)
            rest = sorted(p.relative_to(tree).as_posix() for p in (tree / MPL).glob("test_*.py")
                          if p.relative_to(tree).as_posix() not in taken)
            half = len(rest) // 2
            args = rest[:half] if group.endswith("-a") else rest[half:]
        else:  # mpl-axes_grid1, mpl-axisartist, mpl-mplot3d: one group per toolkit (L4)
            args = [f"lib/mpl_toolkits/{group[4:]}/tests"]
        return "matplotlib", dict(base, args=args)
    if group == "pillow-ro":  # cwd the read-only tree: the measurement fallback when the copy is voided
        return "pillow", dict(args=["Tests", *ignores(["Tests/test_main.py"])],
                              extra_sys_path=[".", "Tests/oss-fuzz"], cwd="/upstream-pillow/tree")
    if group == "pillow":
        return "pillow", dict(args=["Tests", *ignores(["Tests/test_main.py"])],
                              extra_sys_path=[".", "Tests/oss-fuzz"], cwd="/tmp/work")
    if group == "kiwisolver":  # spec 096 fixed the trap: no deselection
        return "kiwisolver", dict(args=["py/tests"])
    if group.startswith("contourpy-"):  # the survey's split: the whole suite passed 1.5 T
        part = group.split("-", 1)[1]
        files = {
            "1": [f"tests/test_{n}.py" for n in ("array", "build_config", "chunk", "config",
                                                 "constructor", "convert", "dechunk", "enum")],
            "filled": ["tests/test_filled.py"],
            "lines": ["tests/test_lines.py"],
            "rest": [f"tests/test_{n}.py" for n in ("internal", "minimal", "misc", "renderer",
                                                    "static", "typecheck", "z_interp")],
        }[part]
        return "contourpy", dict(args=files, extra_sys_path=["."], cwd="/upstream-contourpy/tree")
    if group == "contourpy":
        return "contourpy", dict(args=["tests", *ignores(["tests/test_codebase.py",
                                                          "tests/test_bokeh_renderer.py"])],
                                 extra_sys_path=["."], cwd="/upstream-contourpy/tree")  # baselines by relative path
    if group == "regex":
        return "regex", dict(args=["regex/tests", "--deselect=regex/tests/test_regex.py::test_main"],
                             package_paths={"regex": "regex"})
    if group == "lxml":
        out = [LX + "tests/test_threading.py", LX + "tests/test_isoschematron.py",
               LX + "html/tests/test_feedparser_data.py", LX + "html/tests/test_elementsoup.py"]
        return "lxml", dict(
            args=[LX + "tests", LX + "html/tests", "--doctest-glob=NO-MATCH", *ignores(out)],
            cwd="/tmp/work",
            package_paths={"lxml": "src/lxml", "lxml.html": "src/lxml/html"},
            keep_classes=lxml_keep(tree),
            doctest_preimport=["lxml.doctestcompare"],
            doctest_files=[[f, 8] for f in LXML_DOC] + [[f, 0] for f in LXML_HTML_DOC],
            docstring_modules=["lxml.etree", "lxml.objectify", "lxml.html", "lxml.html.diff",
                               "lxml.tests.selftest", "lxml.tests.selftest2",
                               "lxml.tests.test_xpathevaluator"])
    raise SystemExit(f"no group {group}")


def zip_top_names(z: Path) -> list[str]:
    with zipfile.ZipFile(z) as f:
        return sorted({n.split("/")[0].removesuffix(".pyc") for n in f.namelist()})


def stage(pkg: str, fam: dict, group: str, spec: dict) -> Path:
    tree = TREES / fam["tarball"]
    root = STAGES / group
    if root.exists():
        shutil.rmtree(root)
    for folder in fam["folders"]:
        shutil.copytree(tree / folder, root / "tree" / folder)
    for f in fam.get("files", []):
        (root / "tree" / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tree / f, root / "tree" / f)
    for w in sorted(KIT.glob("*.whl")):
        guest_kit = root / "kit"
        with zipfile.ZipFile(w) as z:
            z.extractall(guest_kit)
    judge = root / "judge"
    judge.mkdir()
    shutil.copyfile(SURVEY / "package_drive.py", judge / "package_drive.py")
    (judge / f"{pkg}.ini").write_text(fam["ini"])
    (judge / f"{group}.json").write_text(json.dumps(spec))
    return root


_TRAP_TEXT: list[str] = []
_orig_cause = guest.trap_cause


def _keep_cause(message):
    _TRAP_TEXT.append(message)
    return _orig_cause(message)


guest.trap_cause = _keep_cause


def main(group: str) -> None:
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    pkg, spec = group_spec(group, TREES / FAMILIES[group_family(group)]["tarball"])
    fam = FAMILIES[pkg]
    spec.setdefault("args", [])
    if len(sys.argv) > 2:  # a bisection run: these args instead of the group's
        spec["args"] = sys.argv[2:]
    spec["top_names"] = zip_top_names(d / "python-stdlib.zip")
    root = stage(pkg, fam, group, spec)
    files = None
    if group == "lxml":  # two tests write test.xml to the working folder: a writable one, with
        # the three data files lxml's tests read by relative paths copied in
        tr = TREES / fam["tarball"]
        files = {f"/tmp/work/{r}": (tr / r).read_bytes()
                 for r in ("doc/test.xml", "samples/simple.xml", "samples/simple-ns.xml")}
    if group == "pillow":
        tests = TREES / fam["tarball"] / "Tests"
        files = {f"/tmp/work/Tests/{p.relative_to(tests).as_posix()}": p.read_bytes()
                 for p in sorted(tests.rglob("*")) if p.is_file()}
    work = OUT / (group + ("-bisect" if len(sys.argv) > 2 else ""))
    if work.exists():
        subprocess.run(["chmod", "-R", "u+w", str(work)], check=True)
        shutil.rmtree(work)
    work.mkdir(parents=True)
    r = guest.run(
        d / "python-snapshot.wasm",
        ["-u", f"/upstream-{pkg}/judge/package_drive.py", pkg, group],
        workdir=work,
        python_version=m.python,
        stdlib=d / "python-stdlib.zip",
        files=files,
        env={"TMPDIR": "/tmp", "HOME": "/tmp"},
        fuel=3 * CAP if pkg == "contourpy" else CAP,
        preopens=[(f"/upstream-{pkg}", root, False)],
        mpl_data=True,
    )
    stream = r.root / "tmp/upstream/outcomes.txt"
    if stream.is_file():
        shutil.copyfile(stream, work / "stream.txt")
    (work / "stdout.txt").write_bytes(r.stdout)
    (work / "stderr.txt").write_bytes(r.stderr)
    if _TRAP_TEXT:
        (work / "trap.txt").write_text("\n".join(_TRAP_TEXT))
    info = {"group": group, "fuel": r.fuel, "exit_code": r.exit_code,
            "trapped": r.trapped, "trap_cause": r.trap_cause}
    (work / "result.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps(info, default=str))


def group_family(group: str) -> str:
    if group == "pillow-ro":
        return "pillow"
    if group.startswith("contourpy"):
        return "contourpy"
    return "matplotlib" if group.startswith("matplotlib") or group.startswith("mpl-") else group


if __name__ == "__main__":
    main(sys.argv[1])
