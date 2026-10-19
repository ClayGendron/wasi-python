"""The gather (spec 063, acceptance 4): a good set of synthetic records passes; each mutation is
red with its own reason."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from harness import gather, history, paths, shards

U = shards.UPSTREAM_FILE
W = "a" * 64  # python.wasm
J = "j" * 64  # the judge hash
HEAD = "c" * 40
PROBE = history.PROBE
BUILD_NODE = "tests/checks/test_v1_5_x.py::test_tree"
RULE_NODE = "tests/checks/test_rules.py::test_rule"
SUITE = f"{U}::test_upstream_suite[g1]"
CLASS = f"{U}::test_upstream_class[g1-k]"
GOAL = sorted([BUILD_NODE, PROBE, RULE_NODE, SUITE, CLASS])
UNITS = ["tests/unit/test_u.py::test_1", "tests/unit/test_u.py::test_2"]
GROUPS = {SUITE: "g1", CLASS: "g1"}
PLAN = {
    "build": shards.Shard("build", ("build",), files=("tests/checks/test_v1_5_x.py",)),
    "own-a": shards.Shard(
        "own-a", shards.OWN_SYSTEMS, files=("tests/checks/test_v1_2_portable_and_sealed.py",)
    ),
    "own-rest": shards.Shard("own-rest", shards.OWN_SYSTEMS, rest=True),
    "up-l": shards.Shard("up-l", ("linux",), groups=("g1",)),
    "up-w": shards.Shard("up-w", ("windows",), groups=("g1",)),
}
PLATFORM = {"build": "darwin-arm64", "macos": "darwin-arm64", "linux": "linux-x86_64"}
PLATFORM["windows"] = "win32-amd64"


def _record(system: str, shard: str) -> dict:
    goal = set(shards.select(GOAL, PLAN, GROUPS)[shard])
    units = shards.select(UNITS, PLAN, GROUPS)[shard]
    checks = {}
    for node in GOAL:
        area = "rules" if node == RULE_NODE else "v1.3"
        if node in goal:
            c = {"area": area, "status": "pass", "reason": "", "need": None, "metrics": {}}
            if node == SUITE:
                c["metrics"] = {"passes": 5, "fuel": 100}
                c["facts"] = {"passed_digest": "d1"}
        else:
            c = {"area": area, "status": "deselected", "reason": "", "need": None, "metrics": {}}
        checks[node] = c
    return {
        "meta": {
            "shard": shard,
            "platform": PLATFORM[system],
            "commit": HEAD,
            "artifact": W,
            "judge": {"hash": J, "files": {}},
            "dirty": False,
            "foreign": [],
            "partial": None,
            "workers": 0,
            "overrides": ["--progress-latest /tmp/r/latest.json"],
            "units": {"count": len(units), "digest": shards.units_digest(units)},
            "wasmtime": "49.0.0",
        },
        "checks": checks,
        "deselected": sorted(n for n, c in checks.items() if c["status"] == "deselected"),
        "collected_files": sorted({n.split("::")[0] for n in GOAL + UNITS}),
        "suite": {"passed": len(units), "skipped": 0, "total": len(units)},
    }


def _accepted() -> dict:
    checks = {n: {"status": "pass", "artifact": W, "commit": HEAD, "metrics": {}} for n in GOAL}
    checks[SUITE]["metrics"] = {"darwin-arm64": {"passes": 5, "fuel": 100, "wasmtime": "49.0.0"}}
    return {"schema": 1, "commit": HEAD, "judge": {"hash": J, "files": {}}, "checks": checks}


class Case:
    """The good set, and the hooks a mutation edits before the gather runs."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.records = {k: _record(*k) for k in gather.expected_keys(PLAN)}
        self.accepted = _accepted()
        self.newest = {"artifact": W, "dirty": False, "partial_reason": None}
        self.gaps: set[str] = set()
        self.tag = False
        self.wasm = W
        self.judge = J
        self.after_write = None  # a function of (records_dir, handed)
        self.handed_edit = None

    def run(self) -> gather.Verdict:
        records_dir = self.tmp / "records"
        handed = {}
        for (system, shard), r in self.records.items():
            folder = records_dir / gather.JOB[system]
            if system != "build":
                folder = folder / f"record-{system}-{shard}"
            folder.mkdir(parents=True, exist_ok=True)
            f = folder / "latest.json"
            f.write_text(json.dumps(r, sort_keys=True, indent=1) + "\n")
            handed[(system, shard)] = paths.sha256_file(f)
        if self.handed_edit:
            self.handed_edit(handed)
        if self.after_write:
            self.after_write(records_dir, handed)
        return gather.gather(
            gather.Inputs(
                plan=PLAN,
                records_dir=records_dir,
                handed=handed,
                wasm_sha256=self.wasm,
                goal_nodes=GOAL,
                unit_nodes=UNITS,
                groups=GROUPS,
                accepted=self.accepted,
                history_lines=[json.dumps(self.newest)],
                gaps=self.gaps,
                judge_hash=self.judge,
                head=HEAD,
                tag=self.tag,
                repo=self.tmp,
            )
        )


@pytest.fixture
def case(tmp_path: Path) -> Case:
    return Case(tmp_path)


def test_the_good_set_passes_and_names_three_systems(case) -> None:
    v = case.run()
    assert v.red == []
    assert f"three systems: darwin linux win32 on {W}" in v.lines


def _meta(key, field, value):
    def edit(c: Case) -> None:
        c.records[key]["meta"][field] = value

    return edit


def _check(key, node, **fields):
    def edit(c: Case) -> None:
        c.records[key]["checks"][node].update(fields)

    return edit


LIN = ("linux", "up-l")
MAC_A = ("macos", "own-a")


def _empty(c: Case) -> None:
    r = c.records[MAC_A]
    for n in r["checks"]:
        r["checks"][n]["status"] = "deselected"
    r["meta"]["units"] = {"count": 0, "digest": shards.units_digest([])}


def _delete(c: Case) -> None:
    c.after_write = lambda d, h: (d / "judge-linux" / "record-linux-up-l" / "latest.json").unlink()


def _empty_value(c: Case) -> None:
    c.handed_edit = lambda h: h.__setitem__(LIN, "")


def _byte(c: Case) -> None:
    def w(d, h):
        f = d / "judge-linux" / "record-linux-up-l" / "latest.json"
        f.write_text(f.read_text().replace('"passes": 5', '"passes": 6'))

    c.after_write = w


def _swapped(c: Case) -> None:
    c.records[LIN] = copy.deepcopy(c.records[("linux", "own-rest")])
    c.records[LIN]["meta"]["overrides"] = ["--progress-latest /tmp/other/latest.json"]


def _one_hash_two(c: Case) -> None:
    c.handed_edit = lambda h: h.__setitem__(("linux", "own-a"), h[("linux", "own-rest")])


def _extra(c: Case) -> None:
    c.after_write = lambda d, h: (d / "judge-linux" / "stray.json").write_text("{}")


def _moved(c: Case) -> None:
    def w(d, h):
        src = d / "judge-linux" / "record-linux-up-l"
        src.rename(d / "judge-macos" / "record-linux-up-l")

    c.after_write = w


def _collection(c: Case) -> None:
    del c.records[MAC_A]["checks"][RULE_NODE]


def _units(c: Case) -> None:
    c.records[("macos", "own-rest")]["meta"]["units"]["digest"] = "0" * 64


def _attr(name, value):
    def edit(c: Case) -> None:
        setattr(c, name, value)

    return edit


def _accepted_gone(c: Case) -> None:
    c.accepted["checks"]["tests/checks/test_rules.py::test_gone"] = {"status": "pass"}


def _passes(system, value):
    def edit(c: Case) -> None:
        key = (system, "up-l" if system == "linux" else "up-w")
        c.records[key]["checks"][SUITE]["metrics"]["passes"] = value

    return edit


def _digest(c: Case) -> None:
    c.records[("windows", "up-w")]["checks"][SUITE]["facts"]["passed_digest"] = "d2"


def _no_probe(c: Case) -> None:
    c.records[("windows", "own-a")]["checks"][PROBE].update(status="blocked", need="oracle")


def _newest(field, value):
    def edit(c: Case) -> None:
        c.newest[field] = value

    return edit


def _tag_judge(c: Case) -> None:
    c.tag = True
    c.accepted["judge"]["hash"] = "k" * 64


def _unit_failed(c: Case) -> None:
    c.records[("macos", "own-rest")]["suite"]["passed"] -= 1


MUTATIONS = [
    ("a failed unit test", _unit_failed, "G4 macos/own-rest: 1 unit test(s) failed"),
    ("an empty shard", _empty, "G3 macos/own-a: selected nothing"),
    ("a missing shard", _delete, "G1 linux/up-l: 0 files"),
    ("an empty handed-on value", _empty_value, "G1 linux/up-l: no SHA-256"),
    ("a byte changed after hashing", _byte, "G1 linux/up-l: 0 files"),
    ("a record handed on under another name", _swapped, "G2 linux/up-l: meta.shard"),
    ("one hash for two shards", _one_hash_two, "G1 one SHA-256 is handed on for two shards"),
    ("an extra file", _extra, "G1 judge-linux/stray.json: a file no job handed on"),
    ("a record under another job", _moved, "G1 linux/up-l: its record is not under"),
    ("the wrong artifact", _meta(LIN, "artifact", "b" * 64), "G2 linux/up-l: artifact"),
    ("no wasm-sha256", _attr("wasm", ""), "G1 the build job handed on no wasm-sha256"),
    ("another commit", _meta(LIN, "commit", "d" * 40), "G2 linux/up-l: commit"),
    ("another judge", _meta(LIN, "judge", {"hash": "x", "files": {}}), "G2 linux/up-l: judge"),
    ("dirty", _meta(LIN, "dirty", True), "G2 linux/up-l: dirty"),
    ("foreign", _meta(LIN, "foreign", ["plugin x"]), "G2 linux/up-l: steered"),
    ("partial", _meta(LIN, "partial", "why"), "G2 linux/up-l: partial"),
    ("workers", _meta(LIN, "workers", 2), "G2 linux/up-l: workers 2"),
    (
        "a --progress-dir override",
        _meta(LIN, "overrides", ["--progress-dir /x", "--progress-latest /y"]),
        "G2 linux/up-l: overrides",
    ),
    ("another platform", _meta(LIN, "platform", "darwin-arm64"), "G2 linux/up-l: platform"),
    ("a check of its share not run", _check(LIN, CLASS, status="deselected"), "G3 linux/up-l: ran"),
    ("an extra check run", _check(LIN, RULE_NODE, status="pass"), "G3 linux/up-l: ran other goal"),
    ("another collection", _collection, "G3 macos/own-a: its collection is not the gather's"),
    ("other unit tests", _units, "G3 macos/own-rest: ran other unit tests"),
    ("a fail", _check(LIN, SUITE, status="fail", reason="boom"), "G4 linux/up-l"),
    ("an unrun", _check(LIN, SUITE, status="unrun"), "G4 linux/up-l"),
    ("a gap not in the gaps file", _check(LIN, CLASS, status="gap"), "G4 linux/up-l"),
    (
        "blocked by the kit",
        _check(LIN, CLASS, status="blocked", need="upstream kit"),
        "G4 linux/up-l",
    ),
    ("an accepted pass that ran nowhere", _accepted_gone, "G5 "),
    ("passes differ between systems", _passes("windows", 4), "G5 g1: passes or passed_digest"),
    ("passed_digest differs", _digest, "G5 g1: passes or passed_digest"),
    ("passes below accepted", _passes("linux", 4), "G5 "),
    ("the probe missing on win32", _no_probe, "G6 the probe passed on ['darwin', 'linux']"),
    ("the newest line on another artifact", _newest("artifact", "e" * 64), "G7 the newest"),
    ("the newest line partial", _newest("partial_reason", "x"), "G7 the newest acceptance is p"),
    ("the newest line dirty", _newest("dirty", True), "G7 the newest acceptance was not"),
    ("a tag with another judge", _tag_judge, "G7 a tag, and this commit's judge"),
]


@pytest.mark.parametrize(("what", "edit", "error"), MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_each_mutation_is_red(case, what, edit, error) -> None:
    edit(case)
    v = case.run()
    assert any(r.startswith(error) for r in v.red), (what, v.red)


def test_a_dry_run_with_a_changed_judge_passes(case) -> None:
    case.accepted["judge"]["hash"] = "k" * 64  # a branch's judge change; not a tag
    assert case.run().red == []


def test_a_select_that_drops_items_from_every_share_is_red(tmp_path, monkeypatch) -> None:
    real = shards.select

    def dropping(nodes, plan, groups):
        got = real(nodes, plan, groups)
        return {k: [n for n in v if n not in (RULE_NODE, UNITS[0])] for k, v in got.items()}

    monkeypatch.setattr(gather.shards, "select", dropping)  # the plugin's and the gather's alike
    red = Case(tmp_path).run().red
    assert f"G3 {RULE_NODE}: collected, run in no record" in red
    assert f"G3 {UNITS[0]}: a unit test in no shard's share" in red


def test_the_merged_record(case) -> None:
    case.records[("linux", "own-a")]["checks"][PROBE]["status"] = "fail"
    case.records[("macos", "own-a")]["checks"][PROBE]["metrics"] = {"fuel": 7}
    case.records[("linux", "own-rest")]["checks"][PROBE]["metrics"] = {"fuel": 9}
    merged = case.run().merged
    assert merged["checks"][RULE_NODE]["status"] == "pass"  # pass on one system beats deselected
    assert merged["checks"][PROBE]["status"] == "fail"  # fail anywhere is fail
    assert merged["checks"][PROBE]["metrics"] == {"fuel": 7}  # the darwin record's
    assert merged["checks"][SUITE]["metrics"]["passes"] == 5  # no darwin record: the linux one's
    assert set(merged["suite"]) == {"build", "darwin", "linux", "win32"}
    assert merged["suite"]["linux"]["total"] == 2


@pytest.mark.parametrize(
    ("environ", "tag"),
    [
        ({"GITHUB_EVENT_NAME": "push", "GITHUB_REF_TYPE": "tag"}, True),
        ({"GITHUB_EVENT_NAME": "push", "GITHUB_REF_TYPE": "branch"}, False),
        ({"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF_TYPE": "tag"}, False),
        ({}, False),
    ],
)
def test_only_a_pushed_tag_is_a_tag(environ, tag) -> None:
    """The G7 judge clause applies to a pushed tag only (the build review, F7)."""
    assert gather.is_tag(environ) is tag
