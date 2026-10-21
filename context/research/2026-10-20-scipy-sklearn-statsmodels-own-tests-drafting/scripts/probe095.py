"""Spec 095's drafting probe: stage one package's tests from its unpacked, hash-checked sdist and
run a selection through tests/upstream/package_drive.py in the snapshot binary, with the judge's
own embedder. A scratch tool, not judge code. Run from the worktree:

    WASI_PYTHON_ARTIFACTS=<set> uv run python <this> <package> <label> <fuel> [pytest args...]

<package> is scipy or sklearn. Paths in the args are relative to the sdist's root.
"""

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

W = Path.cwd()
sys.path.insert(0, str(W / "tests"))
from harness import guest, paths  # noqa: E402

SCRATCH = Path(__file__).resolve().parents[1]
TREES = {
    "scipy": SCRATCH / "sdists/scipy/scipy-1.18.1",
    "sklearn": SCRATCH / "sdists/sklearn/scikit_learn-1.9.1",
}
INI = {
    # scipy: its own pytest.ini, as the sdist has it
    "scipy": None,
    # scikit-learn: its pyproject's [tool.pytest.ini_options], transcribed (no --color, no
    # import-mode: the driver passes it); the faulthandler keys need the plugin the driver turns off
    "sklearn": "[pytest]\ndoctest_optionflags = NORMALIZE_WHITESPACE ELLIPSIS\n"
    "addopts = --disable-pytest-warnings\n"
    # used by its tests, registered nowhere in the sdist (upstream runs without --strict-markers)
    "markers =\n    no_check_spmatrix: scikit-learn's marker for tests --check-spmatrix skips\n",
}
KIT = Path("/Users/claygendron/Git/Repos/wasi_python/build/upstream/wheels")
PROBE = W / "build" / "probe095"


def test_folders(tree: Path, pkg: str) -> list[str]:
    out = []
    for p in sorted((tree / pkg).rglob("tests")):
        rel = p.relative_to(tree).parts
        if p.is_dir() and "odr" not in rel and "tests" not in rel[:-1]:
            out.append(p.relative_to(tree).as_posix())
    return out


def main() -> None:
    pkg, label, fuel, args = sys.argv[1], sys.argv[2], int(float(sys.argv[3])), sys.argv[4:]
    tree = TREES[pkg]
    d = paths.artifact_dir()
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    root = PROBE / "stage" / pkg
    if not root.exists():
        folders = test_folders(tree, pkg)
        for f in folders:
            shutil.copytree(tree / f, root / "tree" / f)
            # each ancestor package's own __init__.py (tarball members, never imported: the
            # product's package is found first), so pytest names the modules
            # scipy.linalg.tests.test_basic, not tests.test_basic
            parts = f.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                init = "/".join(parts[:i]) + "/__init__.py"
                if (tree / init).is_file() and not (root / "tree" / init).exists():
                    shutil.copyfile(tree / init, root / "tree" / init)
        for extra in (f"{pkg}/conftest.py",):
            shutil.copyfile(tree / extra, root / "tree" / extra)
        if pkg == "sklearn":
            for extra in ("sklearn/externals/conftest.py",):
                (root / "tree" / extra).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(tree / extra, root / "tree" / extra)
        for w in sorted(KIT.glob("*.whl")):
            with zipfile.ZipFile(w) as z:
                z.extractall(root / "kit")
        (root / "judge").mkdir()
        shutil.copyfile(W / "tests/upstream/package_drive.py", root / "judge/package_drive.py")
        ini = INI[pkg] if INI[pkg] is not None else (tree / "pytest.ini").read_text()
        # the driver imports hypothesis before pytest starts, so pytest warns it cannot rewrite
        # it; scipy's filterwarnings = error would make that warning fatal at configure
        ini = ini.replace(
            "    error\n",
            "    error\n    ignore:Module already imported so cannot be rewritten:"
            "pytest.PytestAssertRewriteWarning\n", 1)
        (root / "judge" / f"{pkg}.ini").write_text(ini)
        (root / "folders.json").write_text(json.dumps(folders))
    folders = json.loads((root / "folders.json").read_text())
    pp = {pkg: pkg}
    for f in folders:
        parent = f.rsplit("/", 1)[0]
        pp[parent.replace("/", ".")] = parent
    with zipfile.ZipFile(d / "python-stdlib.zip") as z:
        top = sorted({n.split("/")[0].removesuffix(".pyc") for n in z.namelist()})
    grant = f"/upstream-{pkg}"
    spec = dict(
        package_paths=pp, extra_sys_path=[], cwd="/tmp/work", markers=[], split=False,
        keep_classes={}, doctest_preimport=[], doctest_files=[], docstring_modules=[],
        top_names=top,
        args=[a if a.startswith("-") else f"{grant}/tree/{a}" for a in args],
    )
    (root / "judge" / f"{label}.json").write_text(json.dumps(spec))
    work = PROBE / "out" / label
    if work.exists():
        subprocess.run(["chmod", "-R", "u+w", str(work)], check=True)
        shutil.rmtree(work)
    work.mkdir(parents=True)
    env = {"TMPDIR": "/tmp", "HOME": "/tmp"}
    env.update(json.loads(os.environ.get("PROBE_ENV", "{}")))
    r = guest.run(
        d / "python-snapshot.wasm",
        ["-u", f"{grant}/judge/package_drive.py", pkg, label],
        workdir=work, python_version=m.python, stdlib=d / "python-stdlib.zip",
        env=env, fuel=fuel, preopens=[(grant, root, False)], mpl_data=True, measured=False,
    )
    stream = r.root / "tmp/upstream/outcomes.txt"
    if stream.is_file():
        shutil.copyfile(stream, work / "stream.txt")
    (work / "stdout.txt").write_bytes(r.stdout)
    (work / "stderr.txt").write_bytes(r.stderr)
    counts: dict[str, int] = {}
    if stream.is_file():
        for line in stream.read_text().splitlines():
            if line.startswith("R "):
                o = line.split()[1]
                counts[o] = counts.get(o, 0) + 1
            elif line.startswith("X "):
                counts["collect-error"] = counts.get("collect-error", 0) + 1
    info = {"label": label, "fuel": r.fuel, "exit": r.exit_code, "trapped": r.trapped,
            "trap": r.trap_cause, "counts": counts}
    (work / "result.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps(info, default=str))


if __name__ == "__main__":
    main()
