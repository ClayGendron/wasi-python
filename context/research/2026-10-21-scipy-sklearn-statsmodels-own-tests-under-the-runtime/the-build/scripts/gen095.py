"""Spec 095's build tool (scratch, not judge code): the three family TOMLs from a plan.

    uv run python gen095.py init     # groups.json: the pass-1 release groups, packed by survey
    uv run python gen095.py write    # the TOMLs, expected lists and gaps from groups.json,
                                     # measured.json and classes.json

groups.json:   {family: [{name, paths, release_by?, cap?, clock?}]}  (release groups, in order)
splits.json:   {family: [{file, groups, keywords}]}
measured.json: {group: fuel}                (each group's judge-measured fuel)
classes.json:  {group: [{id, outcome, match, reason, closes_with, members: [...]}]}
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

SP = Path(__file__).parent
W = Path("/Users/claygendron/Git/Repos/wasi_python/.claude/worktrees/agent-aab0b516adb4e5c06")
R = W / "context/research/2026-10-21-scipy-sklearn-statsmodels-own-tests-under-the-runtime"
sys.path.insert(0, str(W / "tests"))
from harness import packages, scan  # noqa: E402

INV = json.loads((SP / "inventory.json").read_text())
PLAN = tomllib.loads((SP / "smoke.toml").read_text())
TOP = {"scipy": "scipy", "scikit-learn": "sklearn", "statsmodels": "statsmodels"}
LABEL = {"scipy": "sci", "scikit-learn": "skl", "statsmodels": "sm"}
START = {"scipy": 20.1, "scikit-learn": 26.4, "statsmodels": 26.4}


def survey() -> dict[str, float]:
    out = {}
    for line in (R / "summary.md").read_text().splitlines():
        m = re.match(r"\| ((?:sci|skl|sm)-[nr]-[\w.\-]+) \| ([\d.]+) \|", line)
        if m:
            out[m[1]] = float(m[2])
    return out


def label_of(fam: str, folder: str) -> str:
    top = TOP[fam]
    rest = folder[len(top) + 1 : -len("/tests")] if folder != f"{top}/tests" else "tests"
    return rest.replace("/", ".")


def name_of(fam: str, folder: str) -> str:
    rest = label_of(fam, folder)
    return f"{fam}-" + "-".join(p.strip("_") for p in rest.split(".")) if rest else fam


def smoke_paths(fam: str) -> list[str]:
    return [p for g in PLAN[fam]["smoke"].values() for p in g["paths"]]


def estimate(fam: str, folder: str, s: dict[str, float]) -> float:
    lab, L = label_of(fam, folder), LABEL[fam]
    n = s.get(f"{L}-n-{lab}", s.get(f"{L}-n-{lab}-3", START[fam]))
    r = s.get(f"{L}-r-{lab}")
    return n + (r - START[fam] if r is not None else 0.0)


def init() -> None:
    s = survey()
    groups: dict[str, list[dict]] = {}
    for fam in TOP:
        smoke = smoke_paths(fam)
        out: list[dict] = []
        pack: list[str] = []
        pack_est = 0.0
        start = START[fam]

        def flush() -> None:
            nonlocal pack, pack_est
            if pack:
                name = name_of(fam, pack[0]) + (f"-to-{name_of(fam, pack[-1])[len(fam) + 1:]}" if len(pack) > 1 else "")
                out.append({"name": name, "paths": pack, "est": round(pack_est, 1)})
            pack, pack_est = [], 0.0

        for folder in INV[fam]["folders"]:
            if folder in smoke:
                continue
            est = estimate(fam, folder, s)
            if est > 300:
                flush()
                big = {"name": name_of(fam, folder), "paths": [folder], "est": round(est, 1)}
                out.append(big)
                continue
            if pack and pack_est + est - start > 330:
                flush()
            pack_est = pack_est + est - (start if pack else 0.0)
            pack.append(folder)
        flush()
        for g in out:
            if fam == "scipy" and g["paths"] in (["scipy/special/tests"], ["scipy/stats/tests"]):
                g["cap"] = 20 * 10**12
            else:
                g["cap"] = int(max(500.0, 2.5 * g["est"]) * 1e9)
        groups[fam] = out
    (SP / "groups.json").write_text(json.dumps(groups, indent=1))
    for fam, gs in groups.items():
        print(fam, len(gs), round(sum(g["est"] for g in gs)), "G est")


# ---------------------------------------------------------------------------------------------
# The TOMLs

HEAD = {
    "scipy": """\
# scipy's own tests in the guest. A judge file: every edit is a judge change.
#
# The suite runs whole in the release tier, before a publication; two smoke groups run in the
# normal tier at every check, chosen to touch every compiled subpackage and every carried patch
# (smoke_cover says which file or golden job line covers each). Every test runs in exactly one
# tier: the smoke groups run upstream's normal marker, a marker release group runs their slow and
# very slow cases, and the path release groups run every other staged file whole.
#
# stage_folders   every top-level tests folder of the sdist but scipy.odr's (out of this line:
#                 the product's scipy.odr is a stand-in module)
# package_inits   the ancestors' __init__.py are staged too, so pytest names every module by its
#                 package; the generated package_paths entries are the product's own packages
# derived         the three tables scipy's build makes from its text data for special's tests,
#                 made in the guest from staged members; their facts are on derived_row's row
# env             set for every run of the family, each with its reason
# [groups.*]      one guest session and one check each; cap 1.5 times the measured fuel
""",
    "scikit-learn": """\
# scikit-learn's own tests in the guest. A judge file: every edit is a judge change.
#
# The suite runs whole in the release tier, before a publication; one smoke group runs in the
# normal tier at every check, chosen to touch every compiled subpackage and the carried patch
# (smoke_cover says which file or golden job line covers each). scikit-learn marks no test slow,
# so the smoke files run whole in the normal tier and the path release groups run every other
# staged file whole: every test runs in exactly one tier.
#
# component       the source tree's name, as its tarball names it
# package_inits   the ancestors' __init__.py are staged too (see scipy.toml)
# env             set for every run of the family, each with its reason
""",
    "statsmodels": """\
# statsmodels' own tests in the guest. A judge file: every edit is a judge change.
#
# The suite runs whole in the release tier, before a publication; one smoke group runs in the
# normal tier at every check, chosen to touch every compiled subpackage, ordinary least squares
# and the carried datasets patch (smoke_cover says which file or golden job line covers each).
# No smoke file carries a slow marker, so the smoke files run whole in the normal tier and the
# path release groups run every other staged file whole, slow tests included: every test runs in
# exactly one tier.
#
# package_inits   the ancestors' __init__.py are staged too (see scipy.toml)
""",
}
SUPPORT = {
    "scipy": ["scipy/conftest.py", "scipy/special/utils/makenpz.py"],
    "scikit-learn": ["sklearn/conftest.py", "sklearn/externals/conftest.py"],
    "statsmodels": ["statsmodels/conftest.py"],
}
ENV = {
    "scipy": {
        "SCIPY_XSLOW": (
            "1",
            "scipy's very slow cases run, in whichever tier their file is in; its tests read the "
            "variable outside their marker too, so it is set for every group",
        )
    },
    "scikit-learn": {
        "SKLEARN_RUN_FLOAT32_TESTS": ("1", "the float32 cases of each test run too"),
        "SKLEARN_SEED": (
            "0",
            "the package's setup seeds the global generators from this, not from the product's "
            "own draws, so no change elsewhere moves every test on the global generator",
        ),
    },
    "statsmodels": {},
}


def q(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def arr(items: list[str], indent: str = "") -> str:
    if len(items) <= 1 and sum(len(i) for i in items) < 70:
        return "[" + ", ".join(q(i) for i in items) + "]"
    return "[\n" + "".join(f"{indent}    {q(i)},\n" for i in items) + f"{indent}]"


def load_json(name: str, default):
    p = SP / name
    return json.loads(p.read_text()) if p.exists() else default


def write() -> None:
    groups = load_json("groups.json", {})
    splits = load_json("splits.json", {})
    measured = load_json("measured.json", {})
    classes = load_json("classes.json", {})
    extra = load_json("extra.json", {})  # per family: not_selected, smoke_cover, derived, ...
    gaps = []
    trap_gaps: list[dict] = []
    expected_dir = W / "tests/upstream/expected"
    for fam in TOP:
        plan = PLAN[fam]
        e = extra.get(fam, {})
        lines = [HEAD[fam], f'package = "{fam}"', 'driver = "package"', f'grant = "/upstream-{fam}"']
        if fam == "scikit-learn":
            lines.append('component = "scikit_learn"')
        body: list[str] = []
        caps = 0
        group_lines: list[str] = []
        all_groups: list[tuple[str, dict]] = []
        for name, g in plan["smoke"].items():
            all_groups.append((name, {"paths": g["paths"], "smoke": g["reason"], "tier": "normal"}))
        if fam == "scipy" and not any(g.get("release_by") == "marker" for g in groups.get(fam, [])):
            sm = [p for g in plan["smoke"].values() for p in g["paths"]]
            all_groups.append(("scipy-smoke-slow", {"paths": sm, "tier": "release", "release_by": "marker"}))
        for g in groups.get(fam, []):
            d = {"paths": g["paths"], "tier": "release"}
            if fam == "scipy":
                d["release_by"] = g.get("release_by", "path")
            if "clock" in g:
                d["clock"] = g["clock"]
            d["cap"] = g.get("cap")
            if "comment" in g:
                d["comment"] = g["comment"]
            all_groups.append((g["name"], d))
        for name, d in all_groups:
            m = measured.get(name)
            cap = packages.rule_cap(m) if m else int(d.get("cap") or 3 * 10**12)
            caps += cap
            gl = [f"[groups.{name}]"]
            if "comment" in d:
                gl.append(f"# {d['comment']}")
            gl.append(f"paths = {arr(d['paths'])}")
            if d.get("smoke"):
                gl.append(f"smoke = {q(d['smoke'])}")
            if d["tier"] == "release":
                gl.append('tier = "release"')
            if d.get("release_by"):
                gl.append(f'release_by = "{d["release_by"]}"')
            gl.append(f"fuel = {cap:_}")
            gl.append(f"measured = {(m or cap * 2 // 3):_}")
            if "clock" in d:
                gl.append(f"clock_step_ns = {d['clock']:_}")
                gl.append(
                    'clock_reason = "the test repeats a call until the clock has advanced 0.5 ms; '
                    "the judge's clock advances only when read\""
                )
            group_lines.append("\n".join(gl))
        derived = e.get("derived", [])
        caps += sum(packages.rule_cap(dv["measured"]) for dv in derived)
        budget = caps + 5 * 10**10 * len(e.get("traps", []))  # each trap's session cap
        lines.append(f"budget = {budget:_}")
        lines.append(f"stage_folders = {arr(INV[fam]['folders'])}")
        lines.append("package_inits = true")
        lines.append(f"support_files = {arr(SUPPORT[fam])}")
        if fam == "scipy":
            lines.append('marker = "not slow and not xslow"')
            lines.append('release_marker = "slow or xslow"')
            row = next(
                n for n, d in all_groups
                if any(p == "scipy/special/tests/test_data.py" or "scipy/special/tests/test_data.py".startswith(p.rstrip("/") + "/") for p in d["paths"])
                and d["tier"] == "release" and d.get("release_by") != "marker"
            )
            lines.append(f'derived_row = "{row}"')
        lines.append('cwd = "/tmp/work"')
        lines.append("markers = []")
        lines.append("")
        for k, (v, why) in ENV[fam].items():
            lines += [f"[env.{k}]", f"value = {q(v)}", f"reason = {q(why)}", ""]
        for dv in derived:
            lines += [
                "[[derived]]",
                f"script = {q(dv['script'])}",
                f"args = {arr(dv['args'])}",
                f"inputs = {q(dv['inputs'])}",
                f"output = {q(dv['output'])}",
                f"measured = {dv['measured']:_}",
                f"fuel = {packages.rule_cap(dv['measured']):_}",
                "",
            ]
        if e.get("smoke_cover"):
            lines.append("[smoke_cover]")
            lines += [f"{q(k)} = {q(v)}" for k, v in e["smoke_cover"].items()]
            lines.append("")
        for n in e.get("not_selected", []):
            lines += [
                "[[not_selected]]",
                f"files = {arr(n['files'])}",
                f"reason = {q(n['reason'])}",
                f"closes_with = {q(n['closes_with'])}",
                "",
            ]
        for t in e.get("traps", []):
            lines += [
                "[[trap]]",
                f"id = {q(t['id'])}",
                f"node = {q(t['node'])}",
                f"group = {q(t['group'])}",
                f"reason = {q(t['reason'])}",
                f"closes_with = {q(t['closes_with'])}",
                "",
            ]
            trap_gaps.append(t)
        lines += [g + "\n" for g in group_lines]
        for s in splits.get(fam, []):
            lines += [
                "[[split]]",
                f"file = {q(s['file'])}",
                f"groups = {arr(s['groups'])}",
                f"keywords = {arr(s['keywords'])}",
                "",
            ]
        names = {n for n, _ in all_groups}
        for gname in sorted(classes):
            if gname not in names:
                continue
            for k in classes[gname]:
                lines += [
                    "[[expected]]",
                    f"id = {q(k['id'])}",
                    f"group = {q(gname)}",
                    f"outcome = {q(k['outcome'])}",
                    f"match = {q(k['match'])}",
                    f"reason = {q(k['reason'])}",
                    f"closes_with = {q(k['closes_with'])}",
                    "",
                ]
                members = sorted(set(k["members"]))
                f = expected_dir / gname / f"{k['id']}.txt"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("".join(m + "\n" for m in members))
                if members:
                    gaps.append((gname, k, members))
        (W / f"tests/upstream/{fam}.toml").write_text("\n".join(lines).rstrip() + "\n")
    write_gaps(gaps, trap_gaps)


GAP_START = "# scipy's, scikit-learn's and statsmodels' own tests: each class of known failures"


def write_gaps(gaps, trap_gaps=()) -> None:
    f = W / "tests/known_gaps.toml"
    text = f.read_text()
    if GAP_START in text:
        text = text[: text.index(GAP_START)].rstrip() + "\n"
    out = [
        "",
        GAP_START,
        "# with members, by group (each listed in tests/upstream/expected/<group>/<class>.txt).",
    ]
    for gname, k, members in gaps:
        node = f"tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[{gname}-{k['id']}]"
        out += [
            "",
            "[[gap]]",
            f"check = {q(node)}",
            f'match = "{len(members)} finding(s), digest {scan.digest(members)}"',
            f"reason = {q(k['reason'])}",
            f"closes_with = {q(k['closes_with'])}",
        ]
    for t in trap_gaps:
        node = f"tests/checks/test_v1_3_upstream_suites.py::test_upstream_trap[{t['id']}]"
        out += [
            "",
            "[[gap]]",
            f"check = {q(node)}",
            f'match = "1 finding(s), digest {scan.digest([f"out of fuel at {t["node"]}"])}"',
            f"reason = {q(t['reason'])}",
            f"closes_with = {q(t['closes_with'])}",
        ]
    f.write_text(text + "\n".join(out) + "\n")


if __name__ == "__main__":
    {"init": init, "write": write}[sys.argv[1]]()
