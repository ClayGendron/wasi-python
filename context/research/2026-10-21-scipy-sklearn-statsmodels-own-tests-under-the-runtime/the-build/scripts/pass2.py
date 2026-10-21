"""Repack the release groups past the bound into groups of whole files under it, and files past
it into [[split]]s by -k, from filefuel.json's estimates. Groups under the bound, already
measured, stay as they are.

    uv run python pass2.py [--target G]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SP = Path(__file__).parent
TARGET = float(sys.argv[sys.argv.index("--target") + 1]) if "--target" in sys.argv else 380.0
BOUND = 480.0
groups = json.loads((SP / "groups.json").read_text())
splits = json.loads((SP / "splits.json").read_text())
ff = json.loads((SP / "filefuel.json").read_text())
measured = json.loads((SP / "measured.json").read_text())
inv = json.loads((SP / "inventory.json").read_text())
START = {"scipy": 20.0, "scikit-learn": 26.0, "statsmodels": 26.0}
IDENT = re.compile(r"[A-Za-z_]\w*")
NOT_IDENT = {"and", "or", "not", "True", "False", "None"}


def parses(expr: str) -> bool:
    from _pytest.mark.expression import Expression

    try:
        Expression.compile(expr)
        return True
    except Exception:  # noqa: BLE001
        return False


def unit_keys(node: str, level: int) -> str | None:
    parts = node.split("::")[1:]
    func = parts[-1]
    name, _, param = func.partition("[")
    if level == 0:
        return parts[0].split("[")[0] if len(parts) > 1 else name
    if level == 1:
        return name
    whole = f"{name}[{param}"
    if re.fullmatch(r"[\w:+\-.\[\]\\/]+", whole) and parses(whole):
        return whole
    m = IDENT.match(param)
    return m[0] if m and m[0] not in NOT_IDENT else None


def chunk(tests: list[tuple[str, float]], target: float, level: int = 0) -> list[tuple[list[str], float]]:
    """Ordered units, each a keyword with its fuel; a unit past the target is split one level
    finer when its tests can be named so."""
    units: dict[str, list[tuple[str, float]]] = {}
    for node, g in tests:
        k = unit_keys(node, level)
        if k is None:
            return [([unit_keys(tests[0][0], level - 1) or "?"], sum(g for _, g in tests))]
        units.setdefault(k, []).append((node, g))
    out = []
    for k, ts in units.items():
        g = sum(x for _, x in ts)
        if g > target and level < 1 and len(ts) > 1:
            out += chunk(ts, target, level + 1)
        elif g > target and level == 1 and len(ts) > 1:
            out += by_prefix(ts, target, 1, k)
        else:
            out.append(([k], g))
    return out


OK_KEY = re.compile(r"[\w:+\-.\[\]\\/]+")


def prefix_key(node: str, depth: int) -> str | None:
    func = node.split("::")[-1]
    name, _, param = func.partition("[")
    parts = param.rstrip("]").split("-")
    key = f"{name}[{param}" if depth >= len(parts) else f"{name}[" + "-".join(parts[:depth])
    if OK_KEY.fullmatch(key) and parses(key):
        return key
    m = IDENT.match(param)  # e.g. an estimator's repr: its name alone, at the first depth
    return m[0] if m and depth == 1 and m[0] not in NOT_IDENT else None


def by_prefix(tests, target: float, depth: int, parent: str) -> list[tuple[list[str], float]]:
    """A parametrized function's cases grouped by the leading characters of their parameters
    (pytest's -k matches a substring: `test_x[500-a` takes every case whose parameters begin
    `500-a`), one character finer only where a group passes the target; the parent's key when
    they cannot be named so."""
    import os.path

    cases = []
    for node, g in tests:
        func = node.split("::")[-1]
        name, _, param = func.partition("[")
        cases.append((node, g, name, param.removesuffix("]")))
    common = os.path.commonprefix([p for *_, p in cases])
    n = len(common) + 1
    units: dict[str, list[tuple[str, float]]] = {}
    for node, g, name, param in cases:
        key = f"{name}[{param[:n]}" + ("]" if n >= len(param) else "")
        if not OK_KEY.fullmatch(key) or not parses(key):
            return [([parent], sum(x for _, x in tests))]
        units.setdefault(key, []).append((node, g))
    out = []
    for k, ts in units.items():
        g = sum(x for _, x in ts)
        if g > target and len(ts) > 1:
            out += by_prefix(ts, target, depth + 1, k)
        else:
            out.append(([k], g))
    return out


def make_split(fam: str, file: str, tests: list[tuple[str, float]], base: str) -> list[dict]:
    units = chunk(tests, TARGET - START[fam])
    bins: list[tuple[list[str], float]] = []
    for keys, g in units:
        if bins and bins[-1][1] + g <= TARGET - START[fam]:
            bins[-1] = (bins[-1][0] + keys, bins[-1][1] + g)
        else:
            bins.append((list(keys), g))
    if len(bins) == 1:  # one unit: a group of its own file, no split
        g = bins[0][1] + START[fam]
        return [{"name": base, "paths": [file], "est": round(g, 1), "cap": int(max(3 * g, 200) * 1e9)}]
    names = [f"{base}-{i + 1}" for i in range(len(bins))]
    splits.setdefault(fam, []).append(
        {"file": file, "groups": names, "keywords": [" or ".join(dict.fromkeys(k)) for k, _ in bins[:-1]]}
    )
    return [
        {"name": n, "paths": [file], "est": round(g + START[fam], 1), "cap": int(max(3 * (g + START[fam]), 200) * 1e9)}
        for n, (_, g) in zip(names, bins)
    ]


import tomllib  # noqa: E402

_smoke = tomllib.loads((SP / "smoke.toml").read_text())
_extra = json.loads((SP / "extra.json").read_text())


def left_out(fam: str, f: str) -> bool:
    """A smoke file (the normal tier's) or a not-selected one: never in a path release group."""
    under = lambda p: f == p or f.startswith(p.rstrip("/") + "/")  # noqa: E731
    smoke = [p for g in _smoke[fam]["smoke"].values() for p in g["paths"]]
    out = [x for n in _extra[fam].get("not_selected", []) for x in n["files"]]
    return any(under(p) for p in smoke) or any(under(p) for p in out)


def short(file: str) -> str:
    return Path(file).stem.removeprefix("test_").strip("_").replace("_", "-")


def smoke_slow() -> list[dict]:
    """scipy's marker release group over the smoke paths, repacked by whole smoke path (the
    marker groups' paths together must be exactly the smoke groups' paths)."""
    import tomllib

    plan = tomllib.loads((SP / "smoke.toml").read_text())
    paths = [p for g in plan["scipy"]["smoke"].values() for p in g["paths"]]
    info = ff["scipy-smoke-slow"]
    cost = {p: sum(g for f, g in info["files"].items() if f == p or f.startswith(p + "/")) for p in paths}
    out, pack, pack_g = [], [], 0.0
    for p in sorted(paths, key=lambda p: -cost[p]):
        if cost[p] + START["scipy"] > TARGET and p.endswith(".py") and p in info.get("tests", {}):
            for g in make_split("scipy", p, info["tests"][p], f"scipy-smoke-slow-{short(p)}"):
                g["release_by"] = "marker"
                out.append(g)
            continue
        if pack and pack_g + cost[p] > TARGET - START["scipy"]:
            out.append({"name": f"scipy-smoke-slow-{len(out) + 1}", "paths": pack, "est": round(pack_g + 20, 1), "cap": int(max(3 * (pack_g + 20), 300) * 1e9), "release_by": "marker"})
            pack, pack_g = [], 0.0
        pack.append(p)
        pack_g += cost[p]
    if pack:
        out.append({"name": f"scipy-smoke-slow-{len(out) + 1}", "paths": pack, "est": round(pack_g + 20, 1), "cap": int(max(3 * (pack_g + 20), 300) * 1e9), "release_by": "marker"})
    return out


new: dict[str, list[dict]] = {}
for fam, gs in groups.items():
    out = smoke_slow() if fam == "scipy" and "scipy-smoke-slow" in ff and not any(
        g.get("release_by") == "marker" for g in gs
    ) else []
    for g in gs:
        name = g["name"]
        m = measured.get(name)
        if name in ff and ff[name]["fuel"] > BOUND and not any(name in s["groups"] for s in splits.get(fam, [])):
            info = ff[name]
            files = []
            for p in g["paths"]:
                files += [
                    f
                    for f in inv[fam]["files"]
                    if (f == p or f.startswith(p.rstrip("/") + "/")) and not left_out(fam, f)
                ]
            est = {f: info["files"].get(f, 0.0) for f in files}
            seen = set(info["files"])
            pack, pack_g, k = [], 0.0, 0
            for f in files:
                capped = info["fuel"] >= 19_900 and f == list(info["files"])[-1]
                if (est[f] + START[fam] > TARGET or capped) and f in info.get("tests", {}):
                    tests = [(n, x) for n, x in info["tests"][f]]
                    out += make_split(fam, f, tests, f"{name}-{short(f)}")
                    if info["fuel"] >= 19_900 and f == list(info["files"])[-1]:
                        out[-1]["cap"] = int(20e12)  # the file where the capped session stopped
                    continue
                if pack and pack_g + est[f] > TARGET - START[fam]:
                    k += 1
                    out.append({"name": f"{name}-{k}", "paths": pack, "est": round(pack_g + START[fam], 1), "cap": int(max(3 * (pack_g + START[fam]), 300) * 1e9)})
                    pack, pack_g = [], 0.0
                pack.append(f)
                pack_g += est[f]
            if pack:
                k += 1
                unseen = [f for f in pack if f not in seen]
                cap = 20e12 if unseen and name in ("scipy-special", "scipy-stats") else max(3 * (pack_g + START[fam]), 300) * 1e9
                out.append({"name": f"{name}-{k}", "paths": pack, "est": round(pack_g + START[fam], 1), "cap": int(cap)})
            print(f"{name}: {info['fuel']:.0f} G -> {len([o for o in out if o['name'].startswith(name + '-')])} groups")
        else:
            out.append(g)
    new[fam] = out
(SP / "groups.json").write_text(json.dumps(new, indent=1))
(SP / "splits.json").write_text(json.dumps(splits, indent=1))
for fam, gs in new.items():
    print(fam, len(gs), "groups")
