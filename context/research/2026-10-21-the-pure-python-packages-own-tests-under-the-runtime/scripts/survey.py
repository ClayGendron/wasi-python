"""Spec 067's survey: stage one pure-Python family as the specification stages it, then run one
selection through tests/upstream/package_drive.py in the snapshot binary with the judge's own
embedder. A scratch tool, not judge code (after spec 095's survey tool). From the worktree:

    uv run python <scripts>/survey.py <family> <label> <fuel> [pytest args...]
    uv run python <scripts>/survey.py <family> <label> <fuel> --docstrings mod1 mod2 ...
    uv run python <scripts>/survey.py <family> <label> <fuel> --script <judge file> [args...]

Paths in pytest args are relative to the test source's root. Each run's stream, result and the
tails of stdout and stderr are kept under build/067/survey/out/<label>/; the guest's root is
removed after the run.
"""

import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

W = Path.cwd()
sys.path.insert(0, str(W / "tests"))
sys.path.insert(0, str(Path(__file__).parent))
from families import FAMILIES, TREES  # noqa: E402
from harness import guest, paths  # noqa: E402

SET = W / "build/067/sets/d0d91cef"
KIT = Path("/Users/claygendron/Git/Repos/wasi_python/build/upstream/wheels")
EXTRAS = TREES.parent / "extras"
SURVEY = W / "build/067/survey"
LOCK = Path("/Users/claygendron/Git/Repos/wasi_python/build/lane.lock")


def wait_for_lock() -> None:
    while LOCK.exists():
        time.sleep(20)


def root_of(fam: str) -> Path:
    d = TREES / (FAMILIES[fam].get("tree", fam) if fam in FAMILIES else fam)
    return next(p for p in d.iterdir() if p.is_dir())


def stage(fam: str) -> Path:
    f = FAMILIES[fam]
    src = root_of(fam)
    root = SURVEY / "stage" / fam
    if (root / "staged").exists():
        return root
    if root.exists():
        subprocess.run(["chmod", "-R", "u+w", str(root)], check=True)
        shutil.rmtree(root)
    for rel in f["stage"]:
        s, d = src / rel, root / "tree" / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d, symlinks=False)
        else:
            shutil.copyfile(s, d)
    for rel, srcfam, srcrel in f.get("stage_from", []):  # (dest, other tree, path in it)
        s = root_of(srcfam) / srcrel
        shutil.copytree(s, root / "tree" / rel)
    for rel, old, new in f.get("edits", []):  # survey-only edits, each named in the memo
        p = root / "tree" / rel
        text = p.read_text()
        assert text.count(old) == 1, (rel, old)
        p.write_text(text.replace(old, new))
    (root / "tree" / "_none").mkdir(parents=True, exist_ok=True)
    for w in sorted(KIT.glob("*.whl")):
        with zipfile.ZipFile(w) as z:
            z.extractall(root / "kit")
    for name in f.get("extras", []):
        for w in sorted((EXTRAS / name).glob("*.whl")):
            with zipfile.ZipFile(w) as z:
                z.extractall(root / "kit")
        for t in sorted((EXTRAS / name).glob("*.tar.gz")):  # a pure sdist: its package only
            import tarfile

            with tarfile.open(t) as tf:
                tmp = root / "_sdist"
                tf.extractall(tmp, filter="data")
            top = next(tmp.iterdir())
            for p in top.iterdir():
                if p.is_dir() and (p / "__init__.py").exists():
                    shutil.copytree(p, root / "kit" / p.name)
            shutil.rmtree(tmp)
    (root / "judge").mkdir()
    shutil.copyfile(W / "tests/upstream/package_drive.py", root / "judge/package_drive.py")
    for name, text in f.get("judge_files", {}).items():
        (root / "judge" / name).write_text(text)
    (root / "judge" / f"{fam}.ini").write_text(f["ini"])
    subprocess.run(["chmod", "-R", "a-w", str(root / "tree"), str(root / "kit"),
                    str(root / "judge")], check=True)
    (root / "staged").write_text("")
    return root


def clean(work: Path) -> None:
    for p in work.iterdir():
        if p.is_dir() and p.name.startswith("run-"):
            subprocess.run(["chmod", "-R", "u+w", str(p)], check=True)
            shutil.rmtree(p)


def top_names() -> list[str]:
    with zipfile.ZipFile(SET / "python-stdlib.zip") as z:
        return sorted({n.split("/")[0].removesuffix(".pyc") for n in z.namelist()})


VALUED = {"-m", "-k", "-p", "--deselect", "--ignore", "--constructors"}


def pathed(args: list[str], grant: str) -> list[str]:
    """Paths relative to the source's root become guest paths; an option's value stays."""
    out, prev = [], ""
    for a in args:
        if prev in VALUED and prev != "--ignore":
            out.append(a)
        elif a.startswith("-") or a.startswith("/"):
            out.append(a)
        else:
            out.append(f"{grant}/tree/{a}")
        prev = a
    return out


def main() -> None:
    fam, label, fuel = sys.argv[1], sys.argv[2], int(float(sys.argv[3]))
    rest = sys.argv[4:]
    f = FAMILIES[fam]
    root = stage(fam)
    grant = f"/upstream-{fam}"
    mode, docmods, script, docfiles = "pytest", [], None, []
    if rest and rest[0] == "--docstrings":
        mode, docmods, rest = "doc", rest[1:], []
    elif rest and rest[0] == "--docpkg":  # every module of the package the zip ships
        pkgs, skip = rest[1].split(","), rest[2:]
        with zipfile.ZipFile(SET / "python-stdlib.zip") as z:
            names = z.namelist()
        mods = set()
        for n in names:
            if not n.endswith(".pyc") or n.split("/")[0] not in pkgs:
                continue
            parts = n.removesuffix(".pyc").split("/")
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if any(p in ("tests", "test", "testing") for p in parts) or parts[-1] == "conftest":
                continue
            m = ".".join(parts)
            if not any(m == s or m.startswith(s + ".") for s in skip):
                mods.add(m)
        mode, docmods, rest = "doc", sorted(mods), []
    elif rest and rest[0] == "--docfiles":  # <flags> <path>...: doctest files of the tree
        flags, rels = int(rest[1]), rest[2:]
        if rels and rels[0].startswith("@"):  # a list file beside the scripts folder
            rels = (Path(__file__).parent.parent / rels[0][1:]).read_text().split()
        mode, rest = "doc", []
        docfiles = [[r, flags] for r in rels]
    elif rest and rest[0] == "--script":
        mode, script, rest = "script", rest[1], rest[2:]
    cwd = f.get("cwd", "tree")
    files = {}
    if cwd == "/tmp/work":
        src = root_of(fam)
        for rel in f.get("cwd_folders", []):
            for p in sorted((src / rel).rglob("*")):
                if p.is_file():
                    files[f"/tmp/work/{p.relative_to(src)}"] = p.read_bytes()
    spec = dict(
        package_paths=f.get("pp", {}), extra_sys_path=f.get("esp", []),
        cwd=f"{grant}/tree" if cwd == "tree" else cwd,
        markers=[], split=False, keep_classes={}, doctest_preimport=[], doctest_files=docfiles,
        docstring_modules=docmods, top_names=top_names(),
        args=["--continue-on-collection-errors", *f.get("args", []),
              *pathed(rest if mode == "pytest" else [f"{grant}/tree/_none"], grant)],
    )
    work = SURVEY / "out" / label
    if work.exists():
        subprocess.run(["chmod", "-R", "u+w", str(work)], check=True)
        shutil.rmtree(work)
    work.mkdir(parents=True)
    spec_path = work / "spec.json"
    spec_path.write_text(json.dumps(spec))
    files[f"/tmp/judge/{label}.json"] = json.dumps(spec)
    # the driver reads judge/<name>.json from its grant; the grant is read-only, so the survey
    # gives it a writable copy of the driver beside the spec instead
    files["/tmp/judge/package_drive.py"] = (
        (root / "judge/package_drive.py").read_text()
        .replace('GRANT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))',
                 f'GRANT = "{grant}"')
        .replace('open(f"{GRANT}/judge/{name}.json")', 'open(f"/tmp/judge/{name}.json")')
    )
    if mode == "script":
        argv = ["-u", f"{grant}/judge/{script}", *rest]
    else:
        argv = ["-u", "/tmp/judge/package_drive.py", fam, label]
    m = paths.parse_manifest((SET / "MANIFEST").read_text())
    env = {"TMPDIR": "/tmp", "HOME": "/tmp", **f.get("env", {})}
    wait_for_lock()
    r = guest.run(
        SET / "python-snapshot.wasm", argv, workdir=work, python_version=m.python,
        stdlib=SET / "python-stdlib.zip", env=env, fuel=fuel, files=files,
        preopens=[(grant, root, False)], mpl_data=True, measured=False,
    )
    stream = r.root / "tmp/upstream/outcomes.txt"
    if stream.is_file():
        shutil.copyfile(stream, work / "stream.txt")
    (work / "stdout-tail.txt").write_bytes(r.stdout[-6000:])
    (work / "stderr-tail.txt").write_bytes(r.stderr[-6000:])
    counts: dict[str, int] = {}
    if stream.is_file():
        for line in stream.read_text(errors="replace").splitlines():
            if line.startswith("R "):
                o = line.split()[1]
                counts[o] = counts.get(o, 0) + 1
            elif line.startswith("X "):
                counts["collect-error"] = counts.get("collect-error", 0) + 1
            elif line.startswith("D "):
                counts["deselected-D"] = counts.get("deselected-D", 0) + 1
    clean(work)
    for d in work.glob("mpl-data-*"):
        subprocess.run(["chmod", "-R", "u+w", str(d)], check=True)
        shutil.rmtree(d)
    info = {"label": label, "family": fam, "mode": mode, "args": rest, "docmods": len(docmods),
            "fuel": r.fuel, "exit": r.exit_code, "trapped": r.trapped,
            "trap": r.trap_cause, "counts": counts}
    (work / "result.json").write_text(json.dumps(info, indent=1, default=str))
    with open(SURVEY / "jobs.jsonl", "a") as j:
        j.write(json.dumps(info, default=str) + "\n")
    print(json.dumps(info, default=str))


if __name__ == "__main__":
    main()
