"""Spec 095's survey: stage one family the way the specification stages it, then run one
selection through tests/upstream/package_drive.py in the snapshot binary, with the judge's own
embedder. A scratch tool, not judge code. From the worktree:

    uv run python build/095/survey/survey.py <family> <label> <fuel> [pytest args...]
    uv run python build/095/survey/survey.py <family> --derived

Paths in the args are relative to the sdist's root. Each run's stream, result and stderr tail
are kept under build/095/survey/out/<label>/; the guest's root is removed after the run.
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

SCRATCH = Path(
    "/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/"
    "6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad/sdists"
)
SETS = W / "build/095/sets"
KIT = Path("/Users/claygendron/Git/Repos/wasi_python/build/upstream/wheels")
SURVEY = W / "build/095/survey"
LOCK = Path("/Users/claygendron/Git/Repos/wasi_python/build/lane.lock")

SCIPY_INI_EXTRA = (
    "    ignore:Module already imported so cannot be rewritten:pytest.PytestAssertRewriteWarning\n"
)
SKLEARN_INI = """[pytest]
doctest_optionflags = NORMALIZE_WHITESPACE ELLIPSIS
addopts = --disable-pytest-warnings
markers =
    no_check_spmatrix: scikit-learn's marker for the tests --check-spmatrix skips
"""

FAMILIES = {
    "scipy": dict(
        tree=SCRATCH / "scipy/scipy-1.18.1", pkg="scipy", set="main-142bdd38",
        grant="/upstream-scipy",
        support=["scipy/conftest.py", "scipy/special/utils/makenpz.py"],
        env={"SCIPY_XSLOW": "1"},
        derived=["boost", "gsl", "local"],
        skip_folders=["scipy/odr/tests"],
    ),
    "scikit-learn": dict(
        tree=SCRATCH / "sklearn/scikit_learn-1.9.1", pkg="sklearn", set="main-142bdd38",
        grant="/upstream-scikit-learn",
        support=["sklearn/conftest.py", "sklearn/externals/conftest.py"],
        env={"SKLEARN_RUN_FLOAT32_TESTS": "1", "SKLEARN_SEED": "0"},
        derived=[], skip_folders=[],
    ),
    "statsmodels": dict(
        tree=SCRATCH / "sm/statsmodels-0.15.0", pkg="statsmodels", set="sm-14adfa5f",
        grant="/upstream-statsmodels",
        support=["statsmodels/conftest.py"],
        env={}, derived=[], skip_folders=[],
    ),
}


def statsmodels_ini(tree: Path) -> str:
    import tomllib

    opts = tomllib.loads((tree / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    lines = ["[pytest]", f"minversion = {opts['minversion']}", "xfail_strict = true",
             f"empty_parameter_set_mark = {opts['empty_parameter_set_mark']}", "filterwarnings ="]
    lines += [f"    {w}" for w in opts["filterwarnings"]]
    lines += ["markers ="] + [f"    {m}" for m in opts["markers"]]
    # used by its tests, registered nowhere in the sdist (pytest-run-parallel's marker, and one
    # its own conftest reads)
    lines += ["    thread_unsafe: pytest-run-parallel's marker",
              "    skip_randomstate_check: statsmodels' marker its conftest reads"]
    return "\n".join(lines) + "\n"


def ini_text(fam: str, tree: Path) -> str:
    if fam == "scipy":
        return (tree / "pytest.ini").read_text().replace("    error\n", "    error\n" + SCIPY_INI_EXTRA, 1)
    if fam == "scikit-learn":
        return SKLEARN_INI
    return statsmodels_ini(tree)


def test_folders(tree: Path, pkg: str, skip: list[str]) -> list[str]:
    out = []
    for p in sorted((tree / pkg).rglob("tests")):
        rel = p.relative_to(tree)
        if p.is_dir() and "tests" not in rel.parts[:-1] and rel.as_posix() not in skip:
            out.append(rel.as_posix())
    return out


def artifact(fam: str) -> Path:
    return SETS / FAMILIES[fam]["set"]


def wait_for_lock() -> None:
    import time

    while LOCK.exists():
        time.sleep(30)


def run_guest(fam: str, argv: list[str], fuel: int, work: Path):
    d = artifact(fam)
    m = paths.parse_manifest((d / "MANIFEST").read_text())
    f = FAMILIES[fam]
    root = SURVEY / "stage" / fam
    env = {"TMPDIR": "/tmp", "HOME": "/tmp", **f["env"]}
    wait_for_lock()
    return guest.run(
        d / "python-snapshot.wasm", argv, workdir=work, python_version=m.python,
        stdlib=d / "python-stdlib.zip", env=env, fuel=fuel,
        preopens=[(f["grant"], root, False)], mpl_data=True, measured=False,
    )


def clean(work: Path) -> None:
    # the run's own root only: matplotlib's data is extracted once per process and shared
    for p in work.iterdir():
        if p.is_dir() and p.name.startswith("run-"):
            subprocess.run(["chmod", "-R", "u+w", str(p)], check=True)
            shutil.rmtree(p)


def stage(fam: str) -> Path:
    f = FAMILIES[fam]
    tree, pkg = f["tree"], f["pkg"]
    root = SURVEY / "stage" / fam
    if (root / "folders.json").exists():
        return root
    folders = test_folders(tree, pkg, f["skip_folders"])
    for fo in folders:
        shutil.copytree(tree / fo, root / "tree" / fo)
        parts = fo.split("/")[:-1]
        for i in range(1, len(parts) + 1):
            init = "/".join(parts[:i]) + "/__init__.py"
            if (tree / init).is_file() and not (root / "tree" / init).exists():
                (root / "tree" / init).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(tree / init, root / "tree" / init)
    for s in f["support"]:
        (root / "tree" / s).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tree / s, root / "tree" / s)
    for w in sorted(KIT.glob("*.whl")):
        with zipfile.ZipFile(w) as z:
            z.extractall(root / "kit")
    (root / "judge").mkdir()
    shutil.copyfile(W / "tests/upstream/package_drive.py", root / "judge/package_drive.py")
    (root / "judge" / f"{fam}.ini").write_text(ini_text(fam, tree))
    (root / "folders.json").write_text(json.dumps(folders))
    return root


def derived(fam: str) -> None:
    f = FAMILIES[fam]
    root = stage(fam)
    out = []
    for name in f["derived"]:
        work = SURVEY / "out" / f"derived-{name}"
        if work.exists():
            subprocess.run(["chmod", "-R", "u+w", str(work)], check=True)
            shutil.rmtree(work)
        work.mkdir(parents=True)
        script = f"{f['grant']}/tree/scipy/special/utils/makenpz.py"
        r = run_guest(fam, ["-u", script, name, "-o", "/"], 200_000_000_000, work)
        made = r.root / f"{name}.npz"
        st = os.lstat(made) if os.path.lexists(made) else None
        info = {"name": name, "fuel": r.fuel, "exit": r.exit_code, "trapped": r.trapped,
                "regular": bool(st) and os.path.isfile(made) and not os.path.islink(made),
                "size": st.st_size if st else None,
                "stderr": r.stderr.decode(errors="replace")[-400:]}
        if info["regular"]:
            with zipfile.ZipFile(made) as z:
                info["npy_members"] = sum(n.endswith(".npy") for n in z.namelist())
            dest = root / "tree" / "scipy/special/tests/data" / f"{name}.npz"
            shutil.copyfile(made, dest)
            import hashlib

            info["sha256"] = hashlib.sha256(dest.read_bytes()).hexdigest()
        clean(work)
        (work / "result.json").write_text(json.dumps(info, indent=1))
        out.append(info)
        print(json.dumps({k: v for k, v in info.items() if k != "stderr"}))


def drop_old_mpl_data() -> None:
    for d in (SURVEY / "out").glob("*/mpl-data-*"):
        subprocess.run(["chmod", "-R", "u+w", str(d)], check=True)
        shutil.rmtree(d)


def main() -> None:
    drop_old_mpl_data()
    fam = sys.argv[1]
    if sys.argv[2] == "--derived":
        derived(fam)
        return
    label, fuel, args = sys.argv[2], int(float(sys.argv[3])), sys.argv[4:]
    f = FAMILIES[fam]
    root = stage(fam)
    folders = json.loads((root / "folders.json").read_text())
    pp = {f["pkg"]: f["pkg"]}
    if os.environ.get("PP_OWN_ONLY"):  # only the ancestors of the folders this run names
        folders = [fo for fo in folders if any(a.startswith(fo) for a in args)]
    for fo in folders:
        parts = fo.split("/")[:-1]
        for i in range(2, len(parts) + 1):
            pp[".".join(parts[:i])] = "/".join(parts[:i])
    d = artifact(fam)
    with zipfile.ZipFile(d / "python-stdlib.zip") as z:
        top = sorted({n.split("/")[0].removesuffix(".pyc") for n in z.namelist()})
    grant = f["grant"]
    spec = dict(
        package_paths=pp, extra_sys_path=[], cwd="/tmp/work", markers=[], split=False,
        keep_classes={}, doctest_preimport=[], doctest_files=[], docstring_modules=[],
        top_names=top,
        args=[a if a.startswith("-") else f"{grant}/tree/{a}" for a in args],
    )
    (root / "judge" / f"{label}.json").write_text(json.dumps(spec))
    work = SURVEY / "out" / label
    if work.exists():
        subprocess.run(["chmod", "-R", "u+w", str(work)], check=True)
        shutil.rmtree(work)
    work.mkdir(parents=True)
    r = run_guest(fam, ["-u", f"{grant}/judge/package_drive.py", fam, label], fuel, work)
    stream = r.root / "tmp/upstream/outcomes.txt"
    if stream.is_file():
        shutil.copyfile(stream, work / "stream.txt")
    (work / "stdout-tail.txt").write_bytes(r.stdout if "--co" in args else r.stdout[-4000:])
    (work / "stderr-tail.txt").write_bytes(r.stderr[-4000:])
    counts: dict[str, int] = {}
    if stream.is_file():
        for line in stream.read_text().splitlines():
            if line.startswith("R "):
                o = line.split()[1]
                counts[o] = counts.get(o, 0) + 1
            elif line.startswith("X "):
                counts["collect-error"] = counts.get("collect-error", 0) + 1
    clean(work)
    info = {"label": label, "family": fam, "args": args, "fuel": r.fuel, "exit": r.exit_code,
            "trapped": r.trapped, "trap": r.trap_cause, "counts": counts}
    (work / "result.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps(info, default=str))


if __name__ == "__main__":
    main()
