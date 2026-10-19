"""The progress history in volumes (spec 062): synthetic histories in temporary folders, written
through the same `scoreboard.accept` and `history.target` the plugin uses. Every number here is a
count of bytes, lines, digests or ids; nothing measures time."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from harness import history, paths, scoreboard

PROBE = history.PROBE
SYSTEMS = ("darwin-arm64", "linux-x86_64", "win32-amd64")


def node(i: int) -> str:
    """A synthetic node id of 83 bytes, the mean length of today's (the memo, finding 2)."""
    out = f"tests/checks/test_synthetic_area.py::test_a_synthetic_check_that_holds[{i:011d}]"
    assert len(out) == 83
    return out


def old_line(n: int, prev: str | None, passed, *, platform="darwin-arm64", artifact="art", pad=0):
    """A line in the format of lines 1 to 59: the full `passed` list, no `schema`."""
    entry = {
        "n": n,
        "prev": paths.sha256_bytes(prev.encode()) if prev else None,
        "at": "2026-10-16T00:00:00Z",
        "commit": "c",
        "dirty": False,
        "platform": platform,
        "artifact": artifact,
        "reason": "r" + "x" * pad,
        "passed": sorted(passed),
        "accepted": "0" * 64,
    }
    return json.dumps(entry, sort_keys=True)


def write_old_volume(folder: Path, lines: list[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / history.FIRST).open("w", encoding="utf-8", newline="\n") as f:
        f.write("".join(x + "\n" for x in lines))


def old_volume(folder: Path, sets: list[set], **kw) -> list[str]:
    lines: list[str] = []
    for s in sets:
        lines.append(old_line(len(lines) + 1, lines[-1] if lines else None, s, **kw))
    write_old_volume(folder, lines)
    return lines


def record(passes, platform="darwin-arm64", artifact="art", set_sums=None) -> dict:
    """A run record whose passing checks are `passes`; checks that did not pass are left out."""
    meta = {
        "at": "2026-10-18T00:00:00Z",
        "commit": "c",
        "dirty": False,
        "platform": platform,
        "host": "h",
        "wasmtime": "49.0.0",
        "artifact": artifact,
        "set_sums": set_sums,
        "judge": {"hash": "j", "files": {}},
        "partial": None,
    }
    checks = {
        n: {"area": "rules", "status": "pass", "reason": "", "need": None, "metrics": {}}
        for n in passes
    }
    return {"meta": meta, "checks": checks, "deselected": [], "collected_files": []}


def accept_into(folder: Path, passes, **meta) -> tuple[str, str, Path]:
    """One acceptance as the plugin makes it: (accepted.json text, the line, where it went)."""
    new, line = scoreboard.accept(
        record(passes, **meta),
        None,
        history.lines(folder),
        scoreboard.Ratchet(),
        green=True,
        reason="r",
    )
    where = history.target(folder, line)
    with where.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    accepted_text = scoreboard.dumps(new)
    (folder / "accepted.json").write_text(accepted_text)
    return accepted_text, line, where


def check_folder(folder: Path, committed=None, sealed=None) -> list[str]:
    accepted = folder / "accepted.json"
    return history.errors(
        history.found_in(folder),
        accepted.read_text() if accepted.is_file() else None,
        committed,
        sealed,
    )


# ---------------------------------------------------------------------------------------------
# Criterion 1: lines stop growing with the checks


def test_a_line_records_what_changed_not_every_pass(tmp_path) -> None:
    many = {node(i) for i in range(5_000)}
    old_volume(tmp_path, [many])
    _, line, _ = accept_into(tmp_path, many)
    entry = json.loads(line)
    assert len(line.encode()) < 4_096, len(line.encode())
    assert "passed" not in entry and entry["schema"] == 2
    assert entry["passed_added"] == entry["passed_removed"] == []
    assert entry["passed_digest"] == history.digest(many)

    now = (many | {node(i) for i in range(5_000, 5_010)}) - {node(7), node(8), node(9)}
    _, line, _ = accept_into(tmp_path, now)
    entry = json.loads(line)
    assert entry["passed_added"] == [node(i) for i in range(5_000, 5_010)]
    assert entry["passed_removed"] == [node(7), node(8), node(9)]
    assert entry["passed_digest"] == history.digest(now)
    sets = list(history.passed_sets(history.lines(tmp_path)))
    assert sets[1] == many and sets[2] == now


# ---------------------------------------------------------------------------------------------
# Criterion 2: many more acceptances, and the limit holds


def simulate(folder: Path, acceptances: int = 500, top: int = 1_500):
    """Volume 1 like main's, then `acceptances` more while the checks grow from 392 to `top`.
    Returns (every run's passes, line by line; {artifact: expected systems}; the committed
    snapshot taken halfway; volume 1's bytes)."""
    sets = [{node(i) for i in range(15 + (360 * k) // 58)} | {PROBE} for k in range(59)]
    old_volume(folder, sets)
    first = (folder / history.FIRST).read_bytes()
    assert len(first) >= 1_000_000, len(first)
    runs, expected, halfway = list(sets), {"art": {"darwin"}}, None
    for k in range(acceptances):
        platform = SYSTEMS[k % 3]
        system = platform.split("-")[0]
        artifact = f"art{k // 30}"
        checks = 392 + ((top - 392) * (k + 1)) // acceptances
        passes = {node(i) for i in range(checks)} | {PROBE}
        passes |= {node(9_000_000 + 10 * (k % 3) + j) for j in range(5)}  # this system's own
        if k % 7 == 3:
            passes.discard(PROBE)
        if k // 30 == 5 and system == "linux":  # the strict subset: linux fails it on art5
            passes.discard(PROBE)
        if k % 50 == 49:
            passes = {node(i) for i in range(20)}  # a partial run
        accept_into(folder, passes, platform=platform, artifact=artifact)
        runs.append(passes)
        if PROBE in passes:
            expected.setdefault(artifact, set()).add(system)
        else:
            expected.setdefault(artifact, set())
        if k == acceptances // 2:
            halfway = {name: data for name, data in history.found_in(folder).items()}
    return runs, expected, halfway, first


@pytest.fixture(scope="module")
def simulated(tmp_path_factory):
    folder = tmp_path_factory.mktemp("simulated")
    history.OPS.clear()
    runs, expected, halfway, first = simulate(folder)
    ops = dict(history.OPS)
    return folder, runs, expected, halfway, first, ops


def test_many_more_acceptances_keep_every_file_under_the_limit(simulated) -> None:
    folder, runs, expected, halfway, first, ops = simulated
    print(f"criterion 2 OPS while writing: {ops}")
    assert (folder / history.FIRST).read_bytes() == first
    for p in folder.iterdir():
        assert len(p.read_bytes()) <= 1 << 20, p.name
    vols = history.volumes(folder)
    assert len(vols) >= 4, [v.name for v in vols]  # volume 1 and at least 3 more
    n = 0
    for v in vols:
        data = v.read_bytes()
        offset = 0
        for i, raw in enumerate(data.split(b"\n")[:-1]):
            offset += len(raw) + 1
            entry = json.loads(raw)
            n += 1
            assert entry["n"] == n
            if i == 0:
                assert v.name == history.volume_name(n)
            if "schema" in entry:
                assert offset <= history.BUDGET, (v.name, n, offset)
    assert n == len(runs)

    history.OPS.clear()
    assert check_folder(folder, halfway, {history.FIRST: paths.sha256_bytes(first)}) == []
    print(f"criterion 2 OPS of one intact check: {dict(history.OPS)}")


def test_many_more_acceptances_replay_every_run_and_answer_three_systems(simulated) -> None:
    folder, runs, expected, *_ = simulated
    assert expected["art5"] == {"darwin", "win32"}  # linux failed the probe on every run of it
    for artifact, systems in expected.items():
        assert history.systems_that_passed(folder, artifact) == systems, artifact
    replayed = list(history.passed_sets(history.lines(folder)))
    assert len(replayed) == len(runs)
    for n, (got, want) in enumerate(zip(replayed, runs, strict=True), 1):
        assert got == want, f"history line {n}"


# ---------------------------------------------------------------------------------------------
# Criterion 3: main's 59 lines replay to their own lists


def test_mains_lines_replay_to_their_passed_lists() -> None:
    lines = history.lines(paths.PROGRESS)
    old = [json.loads(x) for x in lines if '"schema"' not in x]
    assert len(old) >= 59
    replayed = list(history.passed_sets(lines))
    for n, entry in enumerate(old, 1):
        assert replayed[n - 1] == set(entry["passed"]), f"history line {n}"
    assert paths.sha256_bytes(paths.HISTORY.read_bytes()) == history.SEALED[history.FIRST]


# ---------------------------------------------------------------------------------------------
# Criteria 4 and 5: tampering in any volume, and committed volumes only grow

BIG = 2_100  # ids in a big line: about 183 KB, so two fill a volume


def three_volumes(folder: Path) -> dict[str, bytes]:
    """Volume 1 (three big old lines, over BUDGET), then big change-lines into volumes 2 and 3.
    Returns the folder as it stood when it had two volumes (for criterion 5)."""
    full = {node(i) for i in range(BIG)} | {PROBE}
    old_volume(folder, [full, full, full])
    committed = None
    for k in range(4):
        accept_into(folder, full if k % 2 else {node(0)}, platform=SYSTEMS[k % 3])
        if len(history.volumes(folder)) == 2:
            committed = dict(history.found_in(folder))  # the last state with two volumes
    assert [v.name for v in history.volumes(folder)][:1] == [history.FIRST]
    assert len(history.volumes(folder)) == 3, [v.name for v in history.volumes(folder)]
    return committed


@pytest.fixture
def vols(tmp_path):
    folder = tmp_path / "progress"
    committed = three_volumes(folder)
    assert check_folder(folder) == []
    v = history.volumes(folder)
    return folder, v, committed


def _lines_of(p: Path) -> list[bytes]:
    return p.read_bytes().split(b"\n")[:-1]


def _write_lines(p: Path, lines: list[bytes]) -> None:
    p.write_bytes(b"".join(x + b"\n" for x in lines))


def _has(errors: list[str], part: str) -> bool:
    return any(part in e for e in errors)


def test_a_byte_changed_in_a_middle_line_of_volume_2(vols) -> None:
    folder, v, _ = vols
    lines = _lines_of(v[1])
    assert len(lines) >= 2
    lines[0] = lines[0].replace(b'"reason": "r"', b'"reason": "s"')
    _write_lines(v[1], lines)
    assert _has(check_folder(folder), "prev does not hash line")


def test_volume_2_deleted(vols) -> None:
    folder, v, _ = vols
    v[1].unlink()
    errors = check_folder(folder)
    assert _has(errors, "prev does not hash line") and _has(errors, ": n is ")


def test_volume_3_renamed_one_higher(vols) -> None:
    folder, v, _ = vols
    n = history.first_line_of(v[2].name)
    v[2].rename(folder / history.volume_name(n + 1))
    assert _has(check_folder(folder), f"its first line is history line {n}")


@pytest.mark.parametrize(
    "name",
    ["history-00070.jsonl.orig", "history-70.jsonl", "history-000060.jsonl", "history-00001.jsonl"],
)
def test_a_stray_or_non_canonical_name(vols, name) -> None:
    folder, v, _ = vols
    shutil.copy(v[2], folder / name)
    assert _has(check_folder(folder), f"{name}: an unrecognised history file")


def test_a_line_appended_to_volume_1_after_volume_2_exists(vols) -> None:
    folder, v, _ = vols
    with v[0].open("ab") as f:
        f.write(_lines_of(v[1])[0] + b"\n")
    assert _has(check_folder(folder), "prev does not hash line")


def test_volume_3_begun_early(vols) -> None:
    folder, v, _ = vols
    lines = _lines_of(v[1])  # move volume 2's last line into a volume of its own
    moved = lines.pop()
    _write_lines(v[1], lines)
    n = json.loads(moved)["n"]
    _write_lines(folder / history.volume_name(n), [moved])
    assert _has(check_folder(folder), "was begun early")


def test_a_change_line_past_the_budget(vols) -> None:
    folder, v, _ = vols
    _write_lines(v[1], _lines_of(v[1]) + _lines_of(v[2]))  # volume 3 folded into volume 2
    v[2].unlink()
    assert _has(check_folder(folder), "past the volume budget")


def _edit_last(folder: Path, change) -> None:
    newest = history.volumes(folder)[-1]
    lines = _lines_of(newest)
    entry = json.loads(lines[-1])
    change(entry)
    lines[-1] = json.dumps(entry, sort_keys=True).encode()
    _write_lines(newest, lines)


def test_the_last_lines_change_edited_misses_its_digest(vols) -> None:
    folder, _, _ = vols

    def drop_one(e):
        if e["passed_added"]:
            e["passed_added"] = e["passed_added"][1:]
        else:
            e["passed_removed"] = e["passed_removed"][1:]

    _edit_last(folder, drop_one)
    assert _has(check_folder(folder), "does not replay to its passed_digest")


def test_an_old_format_line_after_a_change_line(vols) -> None:
    folder, v, _ = vols
    last = _lines_of(v[2])[-1].decode()
    n = json.loads(last)["n"] + 1
    with v[2].open("a", encoding="utf-8", newline="\n") as f:
        f.write(old_line(n, last, {node(0)}) + "\n")
    assert _has(check_folder(folder), f"history line {n} is in the old format after")


def test_a_change_line_that_carries_passed(vols) -> None:
    folder, _, _ = vols
    _edit_last(folder, lambda e: e.update(passed=[node(0)]))
    assert _has(check_folder(folder), "is in format 2 but carries passed")


def test_accepted_json_edited(vols) -> None:
    folder, _, _ = vols
    p = folder / "accepted.json"
    p.write_text(p.read_text().replace('"pass"', '"fail"', 1))
    assert check_folder(folder) == ["accepted.json is not the file the last history line wrote"]


def test_an_old_format_line_moved_out_of_volume_1(tmp_path) -> None:
    """The review's P6: the last old line moved into a volume of its own, ahead of the change
    lines. Lines are big enough that no volume could have taken the next one, so the chain, `n`,
    the names and the begun-early rule all hold; only the old-format rule (and the seal) see it."""
    folder = tmp_path
    big = {node(i) for i in range(3_500)}
    old_volume(folder, [big, big])
    accept_into(folder, {node(0)})
    assert check_folder(folder) == []
    v = history.volumes(folder)
    assert [x.name for x in v] == [history.FIRST, "history-00003.jsonl"]
    lines = _lines_of(v[0])
    moved = lines.pop()
    first_before = v[0].read_bytes()
    _write_lines(v[0], lines)
    n = json.loads(moved)["n"]
    _write_lines(folder / history.volume_name(n), [moved])
    errors = check_folder(folder)
    assert errors == [f"history line {n} is in the old format outside history.jsonl"], errors
    sealed = {history.FIRST: paths.sha256_bytes(first_before)}
    assert _has(check_folder(folder, sealed=sealed), "history.jsonl is not the sealed volume")


def test_a_blank_line_and_a_missing_final_newline(vols) -> None:
    folder, v, _ = vols
    lines = _lines_of(v[1])
    _write_lines(v[1], [lines[0], b"", *lines[1:]])
    v[2].write_bytes(v[2].read_bytes()[:-1])
    errors = check_folder(folder)
    assert _has(errors, f"{v[1].name} holds a blank line")
    assert _has(errors, f"{v[2].name} does not end with a newline")


@pytest.mark.parametrize("schema", [3, "2"])
def test_an_unknown_schema(vols, schema) -> None:
    folder, _, _ = vols
    _edit_last(folder, lambda e: e.update(schema=schema))
    assert _has(check_folder(folder), f"schema is {schema!r}; only 2 is known")


def test_volume_1_changed_under_its_seal(vols) -> None:
    folder, v, _ = vols
    sealed = {history.FIRST: paths.sha256_bytes(v[0].read_bytes())}
    assert check_folder(folder, sealed=sealed) == []
    lines = _lines_of(v[0])
    lines[0] = lines[0].replace(b'"reason": "r"', b'"reason": "s"')
    _write_lines(v[0], lines)
    assert _has(check_folder(folder, sealed=sealed), "history.jsonl is not the sealed volume")


def test_volumes_are_ordered_by_number_not_by_name(tmp_path) -> None:
    for name in ("history-100000.jsonl", "history.jsonl", "history-99999.jsonl"):
        (tmp_path / name).write_text(json.dumps({"name": name}) + "\n")
    assert [v.name for v in history.volumes(tmp_path)] == [
        "history.jsonl",
        "history-99999.jsonl",
        "history-100000.jsonl",
    ]
    assert history.volume_name(100_000) == "history-100000.jsonl"
    assert history.first_line_of("history-100000.jsonl") == 100_000
    assert [json.loads(x)["name"] for x in history.lines(tmp_path)][-1] == "history-100000.jsonl"


def test_committed_volumes_only_grow(vols) -> None:
    folder, v, committed = vols
    assert set(committed) == {history.FIRST, v[1].name}
    assert check_folder(folder, committed) == []  # volume 3 and lines in volume 2 are new

    kept = committed[v[1].name].split(b"\n")[:-1]
    assert len(kept) >= 2
    saved = v[1].read_bytes()
    _write_lines(v[1], kept[:-1])  # volume 2 lost its last committed line
    assert _has(check_folder(folder, committed), f"{v[1].name} does not extend its committed")
    v[1].write_bytes(saved)

    v[1].rename(folder / "aside")
    assert _has(check_folder(folder, committed), f"committed history volume {v[1].name}")
    (folder / "aside").rename(v[1])

    v[0].write_bytes(v[0].read_bytes().replace(b'"reason": "r"', b'"reason": "s"', 1))
    assert _has(check_folder(folder, committed), "history.jsonl does not extend its committed")


# ---------------------------------------------------------------------------------------------
# Criterion 6 and 12: three systems reads every volume, and a broken history does not meet it


def systems_folder(folder: Path) -> None:
    """Lines 1 to 58 are fillers that put volume 1 over BUDGET; line 59 passes the probe on
    darwin; 60 on linux (already in the set, so not in passed_added); 61 fails it on win32;
    62 passes it on win32; 63 is artifact B on linux without the probe."""
    fillers = [set() for _ in range(58)]
    lines = old_volume(folder, fillers, artifact="none", pad=9_100)
    lines.append(old_line(59, lines[-1], {PROBE, node(1)}, platform="darwin-arm64", artifact="A"))
    write_old_volume(folder, lines)
    assert len((folder / history.FIRST).read_bytes()) > history.BUDGET
    accept_into(folder, {PROBE, node(1), node(2)}, platform="linux-x86_64", artifact="A")
    accept_into(folder, {node(1)}, platform="win32-amd64", artifact="A")
    accept_into(folder, {PROBE, node(1)}, platform="win32-amd64", artifact="A")
    accept_into(folder, {node(1)}, platform="linux-x86_64", artifact="B")


def test_three_systems_reads_every_volume(tmp_path) -> None:
    systems_folder(tmp_path)
    assert [v.name for v in history.volumes(tmp_path)] == [history.FIRST, "history-00060.jsonl"]
    sixty = json.loads(history.lines(tmp_path)[59])
    assert PROBE not in sixty["passed_added"]
    assert PROBE in json.loads(history.lines(tmp_path)[60])["passed_removed"]
    assert history.systems_that_passed(tmp_path, "A") == {"darwin", "linux", "win32"}
    assert history.systems_that_passed(tmp_path, "B") == set()
    assert check_folder(tmp_path) == []


def test_three_systems_on_a_broken_history_is_not_met(tmp_path) -> None:
    systems_folder(tmp_path)
    vol = tmp_path / "history-00060.jsonl"
    lines = _lines_of(vol)
    entry = json.loads(lines[1])
    entry["passed_added"] = [node(1)]  # already in the set: it does not apply
    lines[1] = json.dumps(entry, sort_keys=True).encode()
    _write_lines(vol, lines)
    assert history.systems_that_passed(tmp_path, "A") == set()
    assert _has(check_folder(tmp_path), "history line 61: passed_added names")


# ---------------------------------------------------------------------------------------------
# Criterion 8: an oversize line is refused


def test_an_oversize_line_is_refused_and_nothing_is_written(tmp_path) -> None:
    old_volume(tmp_path, [{node(i) for i in range(7_000)}])
    before = (tmp_path / history.FIRST).read_bytes()
    with pytest.raises(scoreboard.AcceptRefused, match="over the volume budget of 524288"):
        accept_into(tmp_path, {node(0)})
    assert (tmp_path / history.FIRST).read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == [history.FIRST]


# ---------------------------------------------------------------------------------------------
# Criterion 11: each caller verifies only what it must


def test_each_caller_computes_only_the_digests_it_must(simulated) -> None:
    folder, *_ = simulated
    lines = history.lines(folder)
    changes = sum('"schema"' in x for x in lines)
    assert changes >= 200

    history.OPS.clear()
    assert check_folder(folder) == []
    assert history.OPS["digests"] == changes
    intact = dict(history.OPS)

    history.forget()
    history.OPS.clear()
    passes = {node(i) for i in range(100)}
    _, line = scoreboard.accept(
        record(passes), None, lines, scoreboard.Ratchet(), green=True, reason="r"
    )
    cold = dict(history.OPS)
    assert cold["digests"] <= 2, cold

    history.OPS.clear()
    scoreboard.accept(
        record(passes), None, [*lines, line], scoreboard.Ratchet(), green=True, reason="r"
    )
    warm = dict(history.OPS)
    assert warm["digests"] <= 2 and warm.get("parsed", 0) <= len(line.encode()), warm

    history.OPS.clear()
    history.systems_that_passed(folder, "art5")
    three = dict(history.OPS)
    assert three.get("digests", 0) == 0, three
    print(f"criterion 11 OPS: intact {intact}; accept cold {cold}; warm {warm}; three {three}")


def test_a_first_line_whose_n_is_not_a_number_is_reported_not_raised(vols) -> None:
    folder, v, _ = vols
    lines = _lines_of(v[2])
    entry = json.loads(lines[0])
    entry["n"] = "x"
    lines[0] = json.dumps(entry, sort_keys=True).encode()
    _write_lines(v[2], lines)
    errors = check_folder(folder)
    assert _has(errors, f"{v[2].name}: its first line is history line 'x'"), errors


# ---------------------------------------------------------------------------------------------
# Spec 070, Decisions 2 and 3 (spec 062's build review, F1 and F2): the roll at exactly BUDGET
# bytes, and a volume that holds a carriage return.


def _next_line(folder: Path) -> tuple[str, str]:
    """(accepted.json text, the line) the next acceptance makes; nothing is written."""
    new, line = scoreboard.accept(
        record({node(0)}),
        None,
        history.lines(folder),
        scoreboard.Ratchet(),
        green=True,
        reason="r",
    )
    return scoreboard.dumps(new), line


def _volume_1_ending(folder: Path, over: int) -> tuple[str, str]:
    """Volume 1 holds one old-format line, padded so that the next acceptance's line, with its
    newline, ends `over` bytes past BUDGET (0: exactly at it). Returns `_next_line`."""
    old_volume(folder, [{node(0)}])
    size = (folder / history.FIRST).stat().st_size
    _, line = _next_line(folder)
    pad = history.BUDGET + over - size - len(line.encode()) - 1
    assert pad > 0
    old_volume(folder, [{node(0)}], pad=pad)
    accepted_text, line = _next_line(folder)
    assert (folder / history.FIRST).stat().st_size + len(line.encode()) + 1 == history.BUDGET + over
    return accepted_text, line


def _place(folder: Path, where: Path, accepted_text: str, line: str) -> None:
    with where.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line + "\n")
    (folder / "accepted.json").write_text(accepted_text)


def test_a_line_that_ends_exactly_at_the_budget_stays_in_the_newest_volume(tmp_path) -> None:
    accepted_text, line = _volume_1_ending(tmp_path, over=0)
    where = history.target(tmp_path, line)
    assert where == tmp_path / history.FIRST
    _place(tmp_path, where, accepted_text, line)
    assert where.stat().st_size == history.BUDGET
    assert check_folder(tmp_path) == []


def test_a_line_one_byte_past_the_budget_starts_a_volume(tmp_path) -> None:
    accepted_text, line = _volume_1_ending(tmp_path, over=1)
    where = history.target(tmp_path, line)
    assert where == tmp_path / history.volume_name(2)
    _place(tmp_path, where, accepted_text, line)
    assert [v.name for v in history.volumes(tmp_path)] == [history.FIRST, history.volume_name(2)]
    assert check_folder(tmp_path) == []


def test_the_intact_check_holds_the_budget_at_its_exact_byte(tmp_path) -> None:
    """The same two lines, each placed on the wrong side of the boundary by hand."""
    fits, over = tmp_path / "fits", tmp_path / "over"
    accepted_text, line = _volume_1_ending(fits, over=0)
    _place(fits, fits / history.volume_name(2), accepted_text, line)
    assert _has(check_folder(fits), f"{history.volume_name(2)} was begun early")
    accepted_text, line = _volume_1_ending(over, over=1)
    _place(over, over / history.FIRST, accepted_text, line)
    errors = check_folder(over)
    assert _has(errors, f"ends at byte {history.BUDGET + 1} of {history.FIRST}"), errors


def test_a_volume_that_holds_a_carriage_return(vols) -> None:
    """The newest line ending in CR LF: nothing chains to it, so only this rule sees it."""
    folder, v, _ = vols
    data = v[2].read_bytes()
    v[2].write_bytes(data[:-1] + b"\r\n")
    assert check_folder(folder) == [f"{v[2].name} holds a carriage return"]


def test_a_bare_carriage_return_inside_the_newest_line(vols) -> None:
    """Spec 070's build review, F2: a CR away from the line's end, inside the newest line, where
    `json.loads` reads it as whitespace and nothing chains to it."""
    folder, v, _ = vols
    data = v[2].read_bytes()
    i = data.rindex(b'{"') + 1  # just after the newest line's last opening brace
    v[2].write_bytes(data[:i] + b"\r" + data[i:])
    assert check_folder(folder) == [f"{v[2].name} holds a carriage return"]


def test_lines_without_set_sums_then_one_with_it_are_intact(tmp_path) -> None:
    """Spec 085, Decision 5: `set_sums` is one more key of a format-2 line; older lines lack it."""
    old_volume(tmp_path, [{node(1)}])
    accept_into(tmp_path, {node(1), node(2)})
    accept_into(tmp_path, {node(2)}, set_sums="s" * 64)
    lines = history.lines(tmp_path)
    assert [json.loads(x).get("set_sums") for x in lines] == [None, None, "s" * 64]
    assert check_folder(tmp_path) == []
    history.forget()
    assert history.last_passed(lines) == {node(2)}
