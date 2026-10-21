"""Prove the smoke split on the real stage: every test file of each family's pinned sdist is in
exactly one tier, by the smoke kind's rules as the specification asks 102 to add them.

Reads the three pinned tarballs as data (their SHA-256 checked first) and `plan.toml` beside this
file: each family's smoke groups (the normal tier), its marker release groups over the smoke
paths, and its path release groups (by default one per staged tests folder, as the survey ran
them; the build packs them). Then it runs the rules on the plan, and on six mutants of it that the
rules must refuse. A scratch tool, not judge code. From the worktree:

    uv run python <this file> build/095b/downloads
"""

import hashlib
import itertools
import sys
import tarfile
import tomllib
from pathlib import Path

from _pytest.mark.expression import Expression

HERE = Path(__file__).parent
SUMS = {
    "scipy-1.18.1.tar.gz": "52c4b7422442aba924d03ad4019852b08a92e64ea187b933135687bfe2747307",
    "scikit_learn-1.9.1.tar.gz": "629cada3e33e2b9bf376cdc7614a47a4140b8aedc1d836579e359736fbd82977",
    "statsmodels-0.15.0.tar.gz": "5d257fe58d0772bc46a557880ca78e2a8e07fec7bfd9d11074aef8e33e1aecbc",
}
SMOKE_BUDGET = 500_000_000_000  # each family's smoke groups together


def members(tarball: Path) -> set[str]:
    digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
    assert digest == SUMS[tarball.name], f"{tarball.name}: {digest} is not its pin"
    with tarfile.open(tarball) as tar:
        names = [m.name for m in tar.getmembers() if m.isfile()]
    return {n.split("/", 1)[1] for n in names if "/" in n}


def staged_folders(mem: set[str], pkg: str, skip: list[str]) -> list[str]:
    out = set()
    for m in mem:
        parts = m.split("/")
        if parts[0] != pkg or "tests" not in parts[:-1]:
            continue
        i = parts.index("tests")
        folder = "/".join(parts[: i + 1])
        if folder not in skip:
            out.add(folder)
    return sorted(out)


def is_test_file(path: str) -> bool:
    base = path.rsplit("/", 1)[-1]
    return base.endswith(".py") and (base.startswith("test_") or base.endswith("_test.py"))


def covers(path: str, file: str) -> bool:
    return file == path or file.startswith(path.rstrip("/") + "/")


def truth_errors(marker: str, release: str) -> list[str]:
    """102's table: never both; always one (no excluded marker in these families)."""
    if not release:
        return []
    m, r = Expression.compile(marker), Expression.compile(release)
    used = sorted({w for w in (marker + " " + release).replace("(", " ").replace(")", " ").split()}
                  - {"and", "or", "not"})
    for bits in itertools.product((False, True), repeat=len(used)):
        value = dict(zip(used, bits, strict=True))
        a, b = m.evaluate(lambda n, **_: value[n]), r.evaluate(lambda n, **_: value[n])
        if a == b:
            return [f"marker and release_marker {'overlap' if a else 'miss'} at {value}"]
    return []


def rule_errors(fam: str, cfg: dict, files: list[str]) -> list[str]:
    """The smoke kind's rules, as the specification asks 102 to add them."""
    errors = []
    groups = cfg["groups"]
    smoke = {n: g for n, g in groups.items() if g.get("tier", "normal") == "normal"}
    release = {n: g for n, g in groups.items() if g.get("tier") == "release"}
    has_smoke = any("smoke" in g for g in smoke.values())
    for n, g in release.items():
        if g.get("release_by") == "path" and not has_smoke:
            errors.append(f"{fam}: release group {n}: a path release group needs smoke groups")
    if not has_smoke:
        return errors
    if cfg.get("release_select"):
        errors.append(f"{fam}: a family with smoke groups has no [[release_select]]")
    for n, g in smoke.items():
        if not str(g.get("smoke", "")).strip():
            errors.append(f"{fam}: normal group {n} gives no smoke reason")
    total = sum(g["measured"] for g in smoke.values())
    if total > SMOKE_BUDGET:
        errors.append(f"{fam}: the smoke groups' measured fuel {total:,} is past {SMOKE_BUDGET:,}")
    smoke_paths = [p for g in smoke.values() for p in g["paths"]]
    marker_paths = {p for g in release.values() if g.get("release_by") == "marker"
                    for p in g["paths"]}
    if cfg.get("release_marker") and marker_paths != set(smoke_paths):
        errors.append(f"{fam}: the marker release groups' paths are not the smoke paths")
    if not cfg.get("release_marker") and marker_paths:
        errors.append(f"{fam}: marker release groups without a release_marker")
    errors += [f"{fam}: {e}" for e in truth_errors(cfg.get("marker", ""),
                                                   cfg.get("release_marker", ""))]
    path_groups = {n: g for n, g in release.items() if g.get("release_by") == "path"}
    for n, g in release.items():
        if g.get("release_by") not in ("marker", "path"):
            errors.append(f"{fam}: release group {n} is of no named kind")
    seen: dict[str, str] = {}
    for n, g in path_groups.items():
        for p in g["paths"]:
            if any(covers(s, p) for s in smoke_paths):
                errors.append(f"{fam}: path release group {n}'s {p} lies in a smoke path")
            if p in seen:
                errors.append(f"{fam}: {p} is in two path release groups: {seen[p]}, {n}")
            seen[p] = n
    for s in smoke_paths:
        if not any(covers(s, f) for f in files):
            errors.append(f"{fam}: smoke path {s} holds no test file")
    for f in files:
        in_smoke = [s for s in smoke_paths if covers(s, f)]
        in_path = [n for n, g in path_groups.items() if any(covers(p, f) for p in g["paths"])]
        if len(in_smoke) > 1:
            errors.append(f"{fam}: {f} is in two smoke paths")
        if not in_smoke and len(in_path) != 1:
            errors.append(f"{fam}: {f} is in {len(in_path)} path release groups, not one")
    return errors


def argv_ignores(cfg: dict, group: dict) -> list[str]:
    """What a path release group's argv ignores by construction: each smoke path under its
    paths."""
    smoke_paths = [p for g in cfg["groups"].values() if g.get("tier", "normal") == "normal"
                   for p in g["paths"]]
    return sorted(s for s in smoke_paths for p in group["paths"] if covers(p, s) and p != s)


def build(fam: str, plan: dict, mem: set[str]) -> tuple[dict, list[str]]:
    p = plan[fam]
    folders = staged_folders(mem, p["pkg"], p.get("not_staged", []))
    files = [m for m in sorted(mem) if is_test_file(m) and any(covers(f, m) for f in folders)
             and not any(covers(x, m) for x in p.get("not_selected", []))]
    groups = {}
    for name, g in p["smoke"].items():
        groups[name] = {"tier": "normal", "smoke": g["reason"], "paths": g["paths"],
                        "measured": int(g["measured"])}
    if p.get("release_marker"):
        groups[f"{fam}-slow"] = {"tier": "release", "release_by": "marker",
                                 "paths": [x for g in p["smoke"].values() for x in g["paths"]]}
    smoke_paths = [x for g in p["smoke"].values() for x in g["paths"]]
    for folder in folders:
        if any(covers(s, folder) for s in smoke_paths):
            continue  # the whole folder is a smoke path
        label = folder.split("/", 1)[1].removesuffix("/tests").replace("/", ".")
        groups[f"{fam}-{label}"] = {"tier": "release", "release_by": "path", "paths": [folder]}
    cfg = {"marker": p.get("marker", ""), "release_marker": p.get("release_marker", ""),
           "groups": groups}
    return cfg, files


def mutants(cfg: dict) -> dict[str, dict]:
    import copy

    out = {}
    m = copy.deepcopy(cfg)
    drop = next(n for n, g in m["groups"].items() if g.get("release_by") == "path")
    del m["groups"][drop]
    out[f"path release group {drop} dropped"] = m
    m = copy.deepcopy(cfg)
    s = next(g for g in m["groups"].values() if "smoke" in g)
    m["groups"]["x-inside"] = {"tier": "release", "release_by": "path", "paths": [s["paths"][0]]}
    out["a path release group over a smoke path"] = m
    m = copy.deepcopy(cfg)
    next(g for g in m["groups"].values() if "smoke" in g)["smoke"] = " "
    out["an empty smoke reason"] = m
    m = copy.deepcopy(cfg)
    for g in m["groups"].values():
        g.pop("smoke", None)
    out["path release groups and no smoke group"] = m
    m = copy.deepcopy(cfg)
    m["release_select"] = [{"files": ["x"], "keyword": "k", "reason": "r"}]
    out["a [[release_select]] in a smoke family"] = m
    m = copy.deepcopy(cfg)
    next(g for g in m["groups"].values() if "smoke" in g)["measured"] = SMOKE_BUDGET + 1
    out["smoke groups past the budget"] = m
    return out


def main() -> None:
    downloads = Path(sys.argv[1])
    plan = tomllib.loads((HERE / "plan.toml").read_text())
    bad = 0
    for fam, tarball in (("scipy", "scipy-1.18.1.tar.gz"),
                         ("scikit-learn", "scikit_learn-1.9.1.tar.gz"),
                         ("statsmodels", "statsmodels-0.15.0.tar.gz")):
        mem = members(downloads / tarball)
        cfg, files = build(fam, plan, mem)
        errs = rule_errors(fam, cfg, files)
        smoke_paths = [p for g in cfg["groups"].values() if "smoke" in g for p in g["paths"]]
        n_smoke = sum(any(covers(s, f) for s in smoke_paths) for f in files)
        n_path = len([n for n, g in cfg["groups"].items() if g.get("release_by") == "path"])
        ignores = sum(len(argv_ignores(cfg, g)) for g in cfg["groups"].values()
                      if g.get("release_by") == "path")
        print(f"{fam}: {len(files)} test files; {n_smoke} in smoke paths (normal tier"
              f"{', their marked tests release' if cfg['release_marker'] else ''}), "
              f"{len(files) - n_smoke} in {n_path} path release groups ({ignores} smoke paths "
              f"ignored by construction); rules: {'clean' if not errs else errs}")
        bad += bool(errs)
        for what, m in mutants(cfg).items():
            got = rule_errors(fam, m, files)
            print(f"  mutant, {what}: {'REFUSED: ' + got[0] if got else 'NOT REFUSED'}")
            bad += not got
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
