"""The gather: a good set of synthetic records passes; each
mutation is red with its own reason."""

from __future__ import annotations

import copy
import importlib.metadata
import json
from pathlib import Path

import pytest

from harness import gather, history, paths, shards

U = shards.UPSTREAM_FILE
W = "a" * 64  # python.wasm
S = "5" * 64  # the set's own SHA256SUMS
WT = "49.0.0"  # the wasmtime uv.lock names
J = "j" * 64  # the judge hash
HEAD = "c" * 40
PROBE = history.PROBE
BUILD_NODE = "tests/checks/test_v1_5_x.py::test_tree"
RULE_NODE = "tests/checks/test_rules.py::test_rule"
# Two checks whose bodies name a CI need, blocked honestly where CI lacks it.
ART = "tests/checks/test_rules.py::test_clones"  # prior-art clones: blocked on every system
DESC = "tests/checks/test_v1_2_portable_and_sealed.py::test_descriptors"  # Windows only
SUITE = f"{U}::test_upstream_suite[g1]"
CLASS = f"{U}::test_upstream_class[g1-k]"
GOAL = sorted([BUILD_NODE, PROBE, RULE_NODE, ART, DESC, SUITE, CLASS])
R_SUITE = f"{U}::test_upstream_suite[r1]"  # a release-tier group's suite
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
PLATFORM = {"build": "linux-aarch64", "macos": "darwin-arm64", "linux": "linux-x86_64"}
PLATFORM["windows"] = "win32-amd64"
PLATFORM["release"] = "linux-x86_64"
MAY_BLOCK = {ART: frozenset({"prior-art clones"}), DESC: frozenset({"descriptor limit"})}


def _record(system: str, shard: str, plan=PLAN, goal_nodes=GOAL, groups=GROUPS, release=()) -> dict:
    goal = set(shards.select(goal_nodes, plan, groups)[shard])
    units = shards.select(UNITS, plan, groups)[shard]
    checks = {}
    for node in goal_nodes:
        area = "rules" if node in (RULE_NODE, ART) else "v1.3"
        if node in goal:
            c = {"area": area, "status": "pass", "reason": "", "need": None, "metrics": {}}
            if node in (SUITE, R_SUITE):
                c["metrics"] = {"passes": 5, "fuel": 100}
                c["facts"] = {"passed_digest": "d1"}
            if node == PROBE:
                c["metrics"] = {"fuel": 7}
            if node == ART or (node == DESC and system == "windows"):
                need = "prior-art clones" if node == ART else "descriptor limit"
                c.update(status="blocked", reason=f"needs: {need}", need=need)
        else:
            c = {"area": area, "status": "deselected", "reason": "", "need": None, "metrics": {}}
        checks[node] = c
    return {
        "meta": {
            "shard": shard,
            "platform": PLATFORM[system],
            "commit": HEAD,
            "artifact": W,
            "set_sums": S,
            "judge": {"hash": J, "files": {}},
            "dirty": False,
            "foreign": [],
            "partial": None,
            "workers": 0,
            "overrides": ["--progress-latest /tmp/r/latest.json"],
            "units": {"count": len(units), "digest": shards.units_digest(units)},
            "wasmtime": WT,
            "tier": shards.tier_of(plan, shard),
        },
        "checks": checks,
        "deselected": sorted(n for n, c in checks.items() if c["status"] == "deselected"),
        "release_checks": sorted(release),
        "collected_files": sorted({n.split("::")[0] for n in goal_nodes + UNITS}),
        "suite": {"passed": len(units), "skipped": 0, "total": len(units)},
    }


def _accepted() -> dict:
    checks = {n: {"status": "pass", "artifact": W, "commit": HEAD, "metrics": {}} for n in GOAL}
    checks[SUITE]["metrics"] = {"darwin-arm64": {"passes": 5, "fuel": 100, "wasmtime": WT}}
    checks[PROBE]["metrics"] = {"darwin-arm64": {"fuel": 7, "wasmtime": WT}}
    return {"schema": 1, "commit": HEAD, "judge": {"hash": J, "files": {}}, "checks": checks}


class Case:
    """The good set, and the hooks a mutation edits before the gather runs."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.records = {k: _record(*k) for k in gather.expected_keys(PLAN)}
        self.accepted = _accepted()
        self.newest = {"artifact": W, "set_sums": S, "dirty": False, "partial_reason": None}
        self.gaps: set[str] = set()
        self.tag = False
        self.set_source = "built"  # a set this run built
        self.plan = PLAN
        self.wasm = W
        self.set_sums = S
        self.wasmtime = WT
        self.may_block = dict(MAY_BLOCK)
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
        return gather.gather(self.inputs(records_dir, handed))

    def inputs(self, records_dir: Path | None = None, handed: dict | None = None) -> gather.Inputs:
        return gather.Inputs(
            plan=self.plan,
            records_dir=records_dir or self.tmp / "records",
            handed=handed or {},
            wasm_sha256=self.wasm,
            set_sums_sha256=self.set_sums,
            wasmtime=self.wasmtime,
            may_block=self.may_block,
            goal_nodes=GOAL,
            unit_nodes=UNITS,
            groups=GROUPS,
            accepted=self.accepted,
            history_lines=[json.dumps(self.newest)],
            gaps=self.gaps,
            judge_hash=self.judge,
            head=HEAD,
            tag=self.tag,
            set_source=self.set_source,
            repo=self.tmp,
        )


@pytest.fixture
def case(tmp_path: Path) -> Case:
    return Case(tmp_path)


def test_the_good_set_passes_and_names_three_systems(case) -> None:
    v = case.run()
    assert v.red == []
    assert f"three systems: darwin linux win32 on {W} · set {S}" in v.lines


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


# Forged records, each red with its own line.
UPS = (("linux", "up-l"), ("windows", "up-w"))
REST = ("macos", "own-rest")


def _blocked(keys, node, need, drop_metrics=False):
    def edit(c: Case) -> None:
        for k in keys:
            c.records[k]["checks"][node].update(status="blocked", need=need)
            if drop_metrics:
                c.records[k]["checks"][node]["metrics"] = {}

    return edit


def _suite(value):
    def edit(c: Case) -> None:
        c.records[REST]["suite"] = value

    return edit


def _metrics(key, node, value):
    def edit(c: Case) -> None:
        c.records[key]["checks"][node]["metrics"] = value

    return edit


def _fuel_unchecked(wasmtime):
    """A darwin record's own meta.wasmtime turns off its fuel ratchet."""

    def edit(c: Case) -> None:
        c.records[MAC_A]["checks"][PROBE]["metrics"] = {"fuel": 70}
        c.records[MAC_A]["meta"]["wasmtime"] = wasmtime

    return edit


FORGERIES = [
    (
        "a class check blocked by the oracle, which its body does not name",
        _blocked(UPS, CLASS, "oracle"),
        f"G4 linux/up-l {CLASS}: blocked by 'oracle', which its check does not call",
    ),
    (
        "an upstream suite blocked by three systems everywhere, its metrics gone",
        _blocked(UPS, SUITE, "three systems", drop_metrics=True),
        f"G4 linux/up-l {SUITE}: blocked by 'three systems', which its check does not call",
    ),
    (
        "the descriptor limit claimed on Linux, where it is met",
        _blocked([("linux", "own-a")], DESC, "descriptor limit"),
        f"G4 linux/own-a {DESC}: blocked by 'descriptor limit', which does not block on linux",
    ),
    (
        "an accepted pass blocked by the oracle in every record that runs it",
        _blocked(UPS, CLASS, "oracle"),
        f"G5 {CLASS}: accepted pass, ran in no record",
    ),
    ("a suite of {}", _suite({}), "G4 macos/own-rest: suite {} is not its 2 unit tests"),
    (
        "a suite of zeros",
        _suite({"passed": 0, "skipped": 0, "total": 0}),
        "G4 macos/own-rest: suite",
    ),
    (
        "a suite one short",
        _suite({"passed": 1, "skipped": 0, "total": 1}),
        "G4 macos/own-rest: suite",
    ),
    (
        "a suite of strings",
        _suite({"passed": "2", "skipped": 0, "total": "2"}),
        "G4 macos/own-rest: suite",
    ),
    (
        "a suite with a bool",
        _suite({"passed": True, "skipped": 1, "total": 2}),
        "G4 macos/own-rest: suite",
    ),
    (
        "a negative skip",
        _suite({"passed": 4, "skipped": -2, "total": 2}),
        "G4 macos/own-rest: suite",
    ),
    (
        "a float count",
        _suite({"passed": 2.0, "skipped": 0, "total": 2}),
        "G4 macos/own-rest: suite",
    ),
    (
        "a Linux record drops an upstream suite's fuel",
        _metrics(LIN, SUITE, {"passes": 5}),
        f"G5 linux/up-l: {SUITE} records no fuel (accepted.json has it)",
    ),
    (
        "a Windows record drops a product check's fuel",
        _metrics(("windows", "own-a"), PROBE, {}),
        f"G5 windows/own-a: {PROBE} records no fuel (accepted.json has it)",
    ),
    (
        "a Linux record's fuel is a string",
        _metrics(("linux", "own-a"), PROBE, {"fuel": "7"}),
        f"G5 linux/own-a: {PROBE} metric fuel is not a number",
    ),
    # json reads NaN and Infinity, and the ratchet's `>` is false for NaN.
    (
        "a macOS record's fuel is NaN",
        _metrics(MAC_A, PROBE, {"fuel": float("nan")}),
        f"G5 macos/own-a: {PROBE} metric fuel is not a number",
    ),
    (
        "a macOS record's fuel is Infinity",
        _metrics(MAC_A, PROBE, {"fuel": float("inf")}),
        f"G5 macos/own-a: {PROBE} metric fuel is not a number",
    ),
    # Malformed shapes give a reason line, never a raise.
    (
        "a need given as a list",
        _blocked([("linux", "own-a")], DESC, ["descriptor limit"]),
        f"G4 linux/own-a {DESC}: blocked by ['descriptor limit']",
    ),
    (
        "metrics given as a list",
        _metrics(("linux", "own-a"), PROBE, [7]),
        f"G5 linux/own-a: {PROBE} metrics is not a mapping",
    ),
    (
        "ten times the fuel on macOS, under another wasmtime",
        _fuel_unchecked("48.0.0"),
        "G2 macos/own-a: wasmtime '48.0.0' is not uv.lock's 49.0.0",
    ),
    (
        "ten times the fuel on macOS, under no wasmtime",
        _fuel_unchecked(None),
        "G2 macos/own-a: wasmtime None is not uv.lock's 49.0.0",
    ),
    (
        "the newest line on another set",
        _newest("set_sums", "f" * 64),
        "G7 the newest acceptance is not on the release's set (SHA256SUMS)",
    ),
    (
        "the newest line with no set (from before 085)",
        lambda c: c.newest.pop("set_sums"),
        "G7 the newest acceptance is not on the release's set (SHA256SUMS)",
    ),
    (
        "a record that judged another set",
        _meta(("linux", "own-a"), "set_sums", "f" * 64),
        "G2 linux/own-a: set_sums is not the build's SHA256SUMS",
    ),
    (
        "no set-sums-sha256 handed on",
        _attr("set_sums", ""),
        "G1 the build job handed on no set-sums-sha256",
    ),
]


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


@pytest.mark.parametrize(("what", "edit", "error"), FORGERIES, ids=[m[0] for m in FORGERIES])
def test_each_forgery_is_red(case, what, edit, error) -> None:
    """Each of these left the gather green (or made it raise) before."""
    edit(case)
    v = case.run()
    assert any(r.startswith(error) for r in v.red), (what, v.red)


def test_ten_times_the_fuel_under_the_locked_wasmtime_is_red_through_the_ratchet(case) -> None:
    """The control for the two wasmtime forgeries: the ratchet itself catches it."""
    _fuel_unchecked(WT)(case)
    assert any(r.startswith(f"G5 macos/own-a: grew {PROBE}: fuel 7 -> 70") for r in case.run().red)


def _src(tmp_path: Path, text: str):
    """A function `f` defined in a module file, so inspect can read its source."""
    import importlib.util

    f = tmp_path / f"mod_{abs(hash(text))}.py"
    f.write_text(text)
    spec = importlib.util.spec_from_file_location(f.stem, f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.f


@pytest.mark.parametrize(
    ("body", "found"),
    [
        ('def f():\n    needs.need("oracle")\n', {"oracle"}),
        ('def f():\n    needs.need("oracle", "three systems")\n', {"oracle", "three systems"}),
        ('def f():\n    if x:\n        for y in z:\n            need("git")\n', {"git"}),
        ('def f():\n    helper("oracle")\n', set()),
        ("def f():\n    needs.need(NAME)\n", set()),
        ('def f():\n    needs.need(f"source tree {c}")\n', set()),
    ],
)
def test_needs_called_reads_only_literal_needs_in_the_body(tmp_path, body, found) -> None:
    assert gather.needs_called(_src(tmp_path, body)) == found


def test_needs_called_on_a_source_it_cannot_read() -> None:
    assert gather.needs_called(len) == set()
    assert gather.needs_called(None) == set()


def test_the_removal_rows_may_be_blocked_on_windows_alone() -> None:
    """The two rows of the private root's read-only check name "read-only files" in their own
    body, a need met everywhere but Windows, where a guest deletes a read-only file itself;
    the gather allows that block on Windows and refuses it on every other system."""
    import importlib.util
    import os

    from harness import needs

    path = paths.REPO / "tests" / "checks" / "test_v1_4_embedding.py"
    spec = importlib.util.spec_from_file_location("embedding_094", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    called = gather.needs_called(module.test_the_removal_never_deletes_what_the_guest_may_not)
    assert called == {"read-only files"}
    node = (
        "tests/checks/test_v1_4_embedding.py::test_the_removal_never_deletes_what_the_guest_may_not"
    )
    may_block = {f"{node}[{case}]": frozenset(called) for case in ("home", "private")}
    for case in ("home", "private"):
        ok = {
            s
            for s in gather.EVERYWHERE
            if gather.allowed(f"{node}[{case}]", "read-only files", s, may_block)
        }
        assert ok == {"windows"}
    assert needs.VOCABULARY["read-only files"].met() == (os.name != "nt")


def test_no_ci_need_is_hidden_in_the_repository() -> None:
    """Every CI need the gather allows is found in a check's own body."""
    assert gather.hidden_ci_needs(paths.REPO) == []


HIDDEN = {
    "tests/checks/conftest.py": '@pytest.fixture\ndef f():\n    needs.need("oracle")\n',
    "tests/checks/sub/conftest.py": 'NEED_OF = {"a": "oracle"}\n',
    "tests/checks/test_x.py": 'def test_x():\n    pytest.skip("needs: three systems")\n',
    "tests/harness/h.py": 'X = {"k": "descriptor limit"}\n',
    "tests/harness/k.py": 'X = "prior-art clones"\n',
    "tests/conftest.py": 'ALL = ["three systems"]\n',
    # A check's decorator and defaults are not its body.
    "tests/checks/test_p.py": '@pytest.mark.parametrize("n", ["oracle"])\ndef test_p(n):\n'
    "    needs.need(n)\n",
    "tests/checks/test_d.py": 'def test_d(n="three systems"):\n    needs.need(n)\n',
    "tests/harness/c.py": 'class K:\n    NEED = "prior-art clones"\n',
    "tests/harness/e.py": 'X = "three systems" if y else ""\n',
}
NOT_HIDDEN = {
    "tests/checks/test_y.py": 'def test_y():\n    needs.need("oracle")\n',
    "tests/harness/jobs.py": 'ORACLE = JOB_DIR / "oracle"\n',
    "tests/harness/needs.py": 'Need("oracle", met, "x")\nPREFIX = "needs: "\n',
    "tests/harness/gather.py": 'CI_NEEDS = {"oracle": frozenset()}\n',
}


def test_hidden_ci_needs_flags_each_spelling(tmp_path) -> None:
    for rel, text in {**HIDDEN, **NOT_HIDDEN}.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    found = gather.hidden_ci_needs(tmp_path)
    assert sorted({x.split(":", 1)[0] for x in found}) == sorted(HIDDEN), found


def test_locked_version(tmp_path) -> None:
    lock = tmp_path / "uv.lock"
    lock.write_text('version = 1\n\n[[package]]\nname = "wasmtime"\nversion = "1.2.3"\n')
    assert gather.locked_version("wasmtime", lock) == "1.2.3"
    assert gather.locked_version("absent", lock) == ""
    assert gather.locked_version("wasmtime") == importlib.metadata.version("wasmtime")


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


def test_the_merged_record_carries_what_sameness_needs(case) -> None:
    """The run fields, a suite per run, a foreign union, each check's
    source."""
    case.records[("windows", "own-a")]["checks"][PROBE].update(status="blocked", need="oracle")
    case.records[("linux", "own-rest")]["meta"]["foreign"] = ["a conftest outside"]
    case.records[("macos", "own-a")]["collected_files"].append("tests/unit/test_mac_only.py")
    merged = case.run().merged
    assert merged["deselected"] == []
    assert "tests/unit/test_mac_only.py" in merged["collected_files"]
    assert set(merged["collected_files"]) >= {n.split("::")[0] for n in GOAL + UNITS}
    assert set(merged["runs"]) == {f"{s}/{n}" for s, n in gather.expected_keys(PLAN)}
    assert merged["runs"]["linux/up-l"] == {
        "platform": "linux-x86_64",
        "suite": case.records[LIN]["suite"],
    }
    assert merged["meta"]["foreign"] == ["a conftest outside"]
    assert merged["checks"][PROBE]["status"] == "blocked"  # the worst, as before
    assert merged["checks"][PROBE]["worst_platform"] == "win32-amd64"  # where it was worst
    assert merged["checks"][RULE_NODE]["worst_platform"].startswith("darwin-")
    assert merged["checks"][PROBE]["source"]["platform"] == "darwin-arm64"
    assert merged["checks"][PROBE]["source"]["status"] == "pass"
    assert "metrics" not in merged["checks"][PROBE]["source"]
    assert merged["checks"][SUITE]["source"]["platform"] == "linux-x86_64"  # no darwin run
    # The build's, from build-shard's arm64 Linux build.
    assert merged["checks"][BUILD_NODE]["source"]["platform"] == "linux-aarch64"


def test_a_ci_need_block_is_no_source(case) -> None:
    """A check blocked by a need CI lacks ran nowhere: no source; another system that ran it is
    the source, metrics and all."""
    for key in (("macos", "own-a"), ("linux", "own-a")):
        case.records[key]["checks"][PROBE].update(status="blocked", need="oracle", metrics={})
    case.records[("windows", "own-a")]["checks"][PROBE]["metrics"] = {"fuel": 3}
    merged = gather.merge(case.records, case.inputs())
    assert merged["checks"][PROBE]["source"]["platform"] == "win32-amd64"
    assert merged["checks"][PROBE]["metrics"] == {"fuel": 3}
    case.records[("windows", "own-a")]["checks"][PROBE].update(status="blocked", need="oracle")
    merged = gather.merge(case.records, case.inputs())
    assert "source" not in merged["checks"][PROBE]
    assert merged["checks"][PROBE]["status"] == "blocked"


def test_a_check_no_record_ran_is_deselected_in_the_merged_record(case) -> None:
    for key in case.records:
        case.records[key]["checks"][RULE_NODE]["status"] = "deselected"
    merged = gather.merge(case.records, case.inputs())
    assert merged["deselected"] == [RULE_NODE]
    assert "source" not in merged["checks"][RULE_NODE]


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
    """The G7 judge clause applies to a pushed tag only."""
    assert gather.is_tag(environ) is tag


# ---------------------------------------------------------------------------------------------
# The build record comes from build-shard on arm64 Linux; where the set came from


def test_the_build_record_is_build_shards_on_linux(case) -> None:
    assert gather.JOB["build"] == "build-shard"
    assert case.records[("build", "build")]["meta"]["platform"].startswith("linux-")
    assert case.run().red == []


def test_a_build_record_from_darwin_is_red_at_g2(case) -> None:
    case.records[("build", "build")]["meta"]["platform"] = "darwin-arm64"
    assert any(e.startswith("G2 build/build: platform") for e in case.run().red)


def test_a_build_record_under_the_build_jobs_folder_is_red_at_g1(case) -> None:
    def move(d: Path, h: dict) -> None:
        old = d / "build-shard" / "latest.json"
        (d / "build").mkdir()
        old.rename(d / "build" / "latest.json")

    case.after_write = move
    red = case.run().red
    assert any(e.startswith("G1 build/build") for e in red), red


def test_a_tag_whose_set_was_reused_is_red_at_g7(case) -> None:
    case.tag = True
    case.set_source = "reused wasi-python-set-v1-" + "0" * 64
    assert "G7 a tag, and the set was not built in this run" in case.run().red


def test_a_branch_may_judge_a_reused_set(case) -> None:
    case.set_source = "reused wasi-python-set-v1-" + "0" * 64
    v = case.run()
    assert v.red == []
    assert v.merged["meta"]["set_source"] == case.set_source
    assert any(line.startswith("set: reused wasi-python-set-v1-") for line in v.lines)


def test_a_tag_with_no_set_source_is_red_at_g7(case) -> None:
    case.tag = True
    case.set_source = ""
    assert "G7 a tag, and the set was not built in this run" in case.run().red


def test_a_named_entry_no_check_matches_is_red_at_g3(case) -> None:
    case.plan = {
        **PLAN,
        "build": shards.Shard(
            "build", ("build",), files=PLAN["build"].files, nodes=(f"{RULE_NODE}_gone",)
        ),
    }
    red = case.run().red
    assert f"G3 build: names {RULE_NODE}_gone, which no collected check is" in red, red


# ---------------------------------------------------------------------------------------------
# The two tiers: a normal run leaves the release shards out; a release run must run them

R_PLAN = {**PLAN, "up-r": shards.Shard("up-r", ("release",), groups=("r1",))}
R_GOAL = sorted([*GOAL, R_SUITE])
R_GROUPS = {**GROUPS, R_SUITE: "r1"}


class TierCase(Case):
    def __init__(self, tmp: Path, tier: str) -> None:
        super().__init__(tmp)
        self.tier = tier
        self.release_run = False
        self.records = {
            k: _record(*k, plan=R_PLAN, goal_nodes=R_GOAL, groups=R_GROUPS, release=[R_SUITE])
            for k in gather.expected_keys(R_PLAN, tier)
        }
        self.accepted["checks"][R_SUITE] = {
            "status": "pass",
            "artifact": W,
            "commit": HEAD,
            "tier": "release",
            "metrics": {"darwin-arm64": {"passes": 5, "fuel": 100, "wasmtime": WT}},
        }
        self.newest["tier"] = "release"

    def inputs(self, records_dir: Path | None = None, handed: dict | None = None) -> gather.Inputs:
        i = super().inputs(records_dir, handed)
        i.plan, i.goal_nodes, i.groups = R_PLAN, R_GOAL, R_GROUPS
        i.tier, i.release_run, i.release_checks = self.tier, self.release_run, {R_SUITE}
        return i


def test_a_normal_run_expects_no_release_record_and_leaves_its_checks_unrun(tmp_path) -> None:
    case = TierCase(tmp_path, "normal")
    assert ("release", "up-r") not in case.records
    v = case.run()
    assert v.red == [], v.red
    assert v.merged["meta"]["tier"] == "normal"
    assert v.merged["checks"][R_SUITE]["status"] == "deselected"
    assert "source" not in v.merged["checks"][R_SUITE]


def test_a_release_tier_check_run_in_a_normal_run_is_red(tmp_path) -> None:
    case = TierCase(tmp_path, "normal")
    c = case.records[LIN]["checks"][R_SUITE]
    c.update(status="pass", metrics={"passes": 5, "fuel": 100})
    assert f"G3 {R_SUITE}: a release-tier check ran in a normal run" in case.run().red


def test_a_release_run_expects_the_release_record(tmp_path) -> None:
    case = TierCase(tmp_path, "release")
    assert ("release", "up-r") in case.records
    v = case.run()
    assert v.red == [], v.red
    assert v.merged["meta"]["tier"] == "release"
    assert v.merged["checks"][R_SUITE]["source"]["platform"] == "linux-x86_64"
    del case.records[("release", "up-r")]
    assert any(r.startswith("G1 release/up-r: no SHA-256") for r in case.run().red)


def test_a_release_record_must_say_its_tier(tmp_path) -> None:
    case = TierCase(tmp_path, "release")
    case.records[("release", "up-r")]["meta"]["tier"] = "normal"
    assert "G2 release/up-r: meta.tier is 'normal', not release" in case.run().red


def test_a_tag_or_main_with_the_normal_tier_is_red_at_g1(tmp_path) -> None:
    case = TierCase(tmp_path, "normal")
    case.release_run = True
    red = case.run().red
    assert "G1 a tag (or a dispatch on main), and the release tier did not run" in red


def test_a_tag_or_main_needs_a_release_acceptance(tmp_path) -> None:
    case = TierCase(tmp_path, "release")
    case.release_run = True
    assert case.run().red == []
    case.newest["tier"] = "normal"
    red = case.run().red
    assert (
        "G7 a tag (or a dispatch on main), and the newest acceptance did not run the release tier"
        in red
    )


def test_a_branch_run_with_the_release_tier_needs_no_release_acceptance(tmp_path) -> None:
    case = TierCase(tmp_path, "release")
    case.newest["tier"] = "normal"
    assert case.run().red == []


@pytest.mark.parametrize("tier", ["normal", "release"])
def test_an_accepted_check_whose_tier_moved_is_red_at_g5(tmp_path, tier) -> None:
    case = TierCase(tmp_path, tier)
    del case.accepted["checks"][R_SUITE]["tier"]
    red = case.run().red
    assert f"G5 {R_SUITE}: accepted in the normal tier, release-tier now" in red
    case = TierCase(tmp_path, tier)
    case.accepted["checks"][SUITE]["tier"] = "release"
    assert f"G5 {SUITE}: accepted in the release tier, normal-tier now" in case.run().red


def test_an_unknown_tier_is_red(tmp_path) -> None:
    case = TierCase(tmp_path, "normal")
    case.tier = "fast"
    assert "G1 TIER is 'fast', not normal or release" in case.run().red


@pytest.mark.parametrize(
    ("environ", "release"),
    [
        (
            {"GITHUB_EVENT_NAME": "push", "GITHUB_REF_TYPE": "tag", "GITHUB_REF": "refs/tags/v1"},
            True,
        ),
        ({"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main"}, True),
        ({"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/spec/102"}, False),
        ({"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/mainline"}, False),
        ({}, False),
    ],
)
def test_a_release_run_is_a_tag_or_main(environ, release) -> None:
    assert gather.is_release_run(environ) is release
