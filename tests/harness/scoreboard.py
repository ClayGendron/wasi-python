"""States, the ratchet, acceptance and the printed scoreboard (spec 002, Decisions 3, 6, 7, 13).

Pure functions over plain dicts, so every transition is unit-tested without running pytest.

A run record:
    {"meta": {...}, "checks": {node id: {"area", "status", "reason", "need", "metrics"}},
     "deselected": [node ids], "collected_files": [paths], "suite": {"passed": n, "total": n}}
`accepted.json`:
    {"schema": 1, "judge": {"hash", "files"},
     "checks": {node id: {"status", "commit", "artifact", "metrics": {platform: {...}}}}}
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from harness import paths

AREAS = {
    "v1.1": "artifact set",
    "v1.2": "portable, sealed",
    "v1.3": "data stack",
    "v1.4": "embedding",
    "v1.5": "rebuild from pins",
    "rules": "constitution rules",
}
STATES = ("pass", "fail", "gap", "blocked", "deselected", "unrun")
FUEL_TOLERANCE = 1e-4  # 0.01%: the clock-and-random memo
NOT_MACHINE_CHECKED = (
    "publication · second-host rebuild · copying from prior art · numpy/pandas test subsets",
    "licence content of wasi-libc, llvm-runtimes and unpinned components (presence only) · "
    "bundled sub-licences · files a build adds inside a source tree",
)
# An accepted pass blocked by one of these is red: a product (artifact, runner, wheel) went missing,
# is how a regression could hide. Other needs (clones, the oracle, source trees, git) are local
# tooling a fresh clone lacks; their unrun passes are reported, not red (spec 002, Decision 6).
PROTECTED_NEEDS = frozenset(
    {"artifact dir", "plain binary", "snapshot binary", "stdlib zip", "manifest", "runner", "wheel"}
)
MAX_FAIL_LINES = 10
MAX_LINES = 25


class AcceptRefused(Exception):
    """`--accept` refused; the message lists every reason."""


@dataclass
class Ratchet:
    lost: list[str] = field(default_factory=list)
    unrun: list[str] = field(default_factory=list)
    unrun_local: list[str] = field(default_factory=list)
    deselected: list[str] = field(default_factory=list)
    outside: list[str] = field(default_factory=list)
    absent: list[str] = field(default_factory=list)
    gained: list[str] = field(default_factory=list)
    growth: list[str] = field(default_factory=list)
    fuel_not_compared: list[str] = field(default_factory=list)
    judge_changed: list[str] = field(default_factory=list)
    baseline: str = ""

    def red(self, partial: bool) -> list[str]:
        """Why this ratchet turns the run red; empty when it does not."""
        why = []
        if self.lost:
            why.append(f"{len(self.lost)} accepted pass(es) lost")
        if self.absent:
            why.append(f"{len(self.absent)} accepted check(s) absent (retire them with --retire)")
        if self.growth:
            why.append(f"{len(self.growth)} metric(s) grew")
        if self.unrun and not partial:
            why.append(f"{len(self.unrun)} accepted pass(es) blocked (say --partial to allow)")
        return why


def _file_of(node: str) -> str:
    return node.split("::", 1)[0]


def compare(run: dict, accepted: dict | None, repo: Path = paths.REPO) -> Ratchet:
    r = Ratchet()
    if not accepted:
        r.gained = sorted(n for n, c in run["checks"].items() if c["status"] == "pass")
        return r
    meta = run["meta"]
    r.baseline = accepted.get("commit", "")
    run_checks = run["checks"]
    deselected = set(run.get("deselected", []))
    collected_files = set(run.get("collected_files", []))
    for node, acc in sorted(accepted["checks"].items()):
        now = run_checks.get(node)
        if acc["status"] == "pass":
            if now is not None:
                if now["status"] in ("fail", "gap"):
                    r.lost.append(node)
                elif now["status"] == "blocked":
                    local = now.get("need") not in PROTECTED_NEEDS
                    (r.unrun_local if local else r.unrun).append(node)
                elif now["status"] == "deselected":
                    r.deselected.append(node)
                elif now["status"] == "unrun":
                    r.outside.append(node)
            elif node in deselected:
                r.deselected.append(node)
            elif not (repo / _file_of(node)).is_file() or _file_of(node) in collected_files:
                r.absent.append(node)
            else:
                r.outside.append(node)
        if now is None:
            continue
        old = acc.get("metrics", {}).get(meta["platform"], {})
        if now["status"] == "pass":
            for name in sorted(set(old) - {"wasmtime"} - set(now.get("metrics", {}))):
                r.growth.append(f"{node}: {name} is no longer recorded")
        for name, value in sorted(now.get("metrics", {}).items()):
            if name not in old:
                continue
            if name == "fuel":
                if old.get("wasmtime") != meta["wasmtime"]:
                    r.fuel_not_compared.append(node)
                elif value > old[name] * (1 + FUEL_TOLERANCE):
                    r.growth.append(f"{node}: fuel {old[name]} -> {value}")
            elif value > old[name]:
                r.growth.append(f"{node}: {name} {old[name]} -> {value}")
    for node, now in sorted(run_checks.items()):
        if now["status"] == "pass" and accepted["checks"].get(node, {}).get("status") != "pass":
            r.gained.append(node)
    old_files = accepted.get("judge", {}).get("files", {})
    new_files = meta["judge"]["files"]
    r.judge_changed = sorted(
        f for f in set(old_files) | set(new_files) if old_files.get(f) != new_files.get(f)
    )
    return r


def dumps(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, indent=1) + "\n"


def last_history_line(history_text: str) -> str | None:
    lines = [line for line in history_text.split("\n") if line.strip()]
    return lines[-1] if lines else None


def accept(
    run: dict,
    accepted: dict | None,
    history_text: str,
    ratchet: Ratchet,
    *,
    green: bool,
    reason: str,
    judge_reason: str | None = None,
    growth_reason: str | None = None,
    partial_reason: str | None = None,
    retire: list[str] = (),
) -> tuple[dict, str]:
    """(new accepted.json content, the history line to append), or AcceptRefused."""
    refusals = []
    if not green:
        refusals.append("the run is not green (or PYTEST_ADDOPTS or a foreign plugin is set)")
    if ratchet.lost:
        refusals.append(f"lost passes: {', '.join(ratchet.lost[:3])}")
    absent = [n for n in ratchet.absent if n not in retire]
    if absent:
        refusals.append(f"absent checks not retired: {', '.join(absent[:3])}")
    if ratchet.unrun and not partial_reason:
        refusals.append("accepted passes are blocked; say --partial with a reason")
    if ratchet.growth and not growth_reason:
        refusals.append("metrics grew; say --accept-growth with a reason")
    if accepted and ratchet.judge_changed and not judge_reason:
        refusals.append(
            f"the judge changed ({', '.join(ratchet.judge_changed[:4])}"
            f"{' and more' if len(ratchet.judge_changed) > 4 else ''}); "
            "say --accept-judge with a reason"
        )
    unknown = [n for n in retire if n not in ratchet.absent]
    if unknown:
        refusals.append(f"--retire names checks that are not absent: {', '.join(unknown)}")
    if refusals:
        raise AcceptRefused("; ".join(refusals))

    meta = run["meta"]
    platform = meta["platform"]
    checks = {k: dict(v) for k, v in (accepted or {}).get("checks", {}).items()}
    for node in retire:
        checks.pop(node, None)
    for node, now in run["checks"].items():
        if now["status"] not in ("pass", "fail", "gap"):
            continue  # not run here: keep what was accepted
        entry = checks.get(node, {})
        metrics = {k: dict(v) for k, v in entry.get("metrics", {}).items()}
        old = metrics.get(platform, {})
        fresh = dict(now.get("metrics", {}))
        if fresh:
            same_engine = old.get("wasmtime") == meta["wasmtime"]
            merged = {"wasmtime": meta["wasmtime"]}
            for name, value in fresh.items():
                keep_old = name in old and not growth_reason and (name != "fuel" or same_engine)
                merged[name] = min(old[name], value) if keep_old else value
            metrics[platform] = merged
        elif growth_reason and now["status"] == "pass":
            metrics.pop(platform, None)  # metrics no longer recorded: accepted growth drops them
        checks[node] = {
            "status": now["status"],
            "commit": meta["commit"],
            "artifact": meta["artifact"],
            "metrics": metrics,
        }
    new = {"schema": 1, "commit": meta["commit"], "judge": meta["judge"], "checks": checks}
    prev = last_history_line(history_text)
    counts = {
        area: f"{n_pass}/{n_all}" for area, (n_pass, n_all) in area_counts(run["checks"]).items()
    }
    line = {
        "n": sum(1 for x in history_text.split("\n") if x.strip()) + 1,
        "prev": paths.sha256_bytes(prev.encode()) if prev else None,
        "at": meta["at"],
        "commit": meta["commit"],
        "dirty": meta["dirty"],
        "platform": platform,
        "host": meta["host"],
        "artifact": meta["artifact"],
        "wasmtime": meta["wasmtime"],
        "reason": reason,
        "judge_reason": judge_reason,
        "growth_reason": growth_reason,
        "partial_reason": partial_reason,
        "retired": sorted(retire),
        "judge_changed": ratchet.judge_changed,
        "counts": counts,
        "passed": sorted(n for n, c in run["checks"].items() if c["status"] == "pass"),
        "accepted": paths.sha256_bytes(dumps(new).encode()),
    }
    return new, json.dumps(line, sort_keys=True)


def history_errors(
    history_text: str, accepted_text: str | None, committed: str | None
) -> list[str]:
    """The history's `prev` chain, its last `accepted` hash, and that it extends its commit."""
    errors = []
    lines = [line for line in history_text.split("\n") if line.strip()]
    prev = None
    for i, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"history line {i} is not JSON")
            break
        want = paths.sha256_bytes(prev.encode()) if prev else None
        if entry.get("prev") != want:
            errors.append(f"history line {i}: prev does not hash line {i - 1}")
        if entry.get("n") != i:
            errors.append(f"history line {i}: n is {entry.get('n')}")
        prev = line
    if lines and not errors:
        last = json.loads(lines[-1])
        if accepted_text is None:
            errors.append("history has lines but accepted.json is missing")
        elif last.get("accepted") != paths.sha256_bytes(accepted_text.encode()):
            errors.append("accepted.json is not the file the last history line wrote")
    if not lines and accepted_text is not None:
        errors.append("accepted.json exists but the history is empty")
    if committed is not None and not history_text.startswith(committed):
        errors.append("history.jsonl does not extend its committed version (a line was rewritten)")
    return errors


def systems_that_passed(history: Path, artifact: str) -> set[str]:
    """The operating systems whose accepted runs passed the guest on this artifact's bytes."""
    if not history.is_file():
        return set()
    probe = "tests/checks/test_v1_2_portable_and_sealed.py::test_guest_runs_here[plain]"
    systems = set()
    for line in history.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("artifact") == artifact and probe in entry.get("passed", []):
            systems.add(entry["platform"].split("-")[0])
    return systems


def area_counts(checks: dict) -> dict[str, tuple[int, int]]:
    out = {}
    for area in AREAS:
        mine = [c for c in checks.values() if c["area"] == area]
        out[area] = (sum(c["status"] == "pass" for c in mine), len(mine))
    return out


def render(
    run: dict, ratchet: Ratchet | None, providers: dict[str, str], red: list[str]
) -> list[str]:
    """The scoreboard, at most 25 lines (Decision 13)."""
    checks = run["checks"]
    states = Counter(c["status"] for c in checks.values())
    total = len(checks)
    suite = run.get("suite", {})
    lines = [
        f"wasi_python v1: {states['pass']}/{total} pass · {states['gap']} gap · "
        f"{states['blocked']} blocked · {states['fail']} fail"
        + (f" · {states['deselected']} deselected" if states["deselected"] else "")
        + (
            f"   (unit suite {suite.get('passed', 0)}/{suite.get('total', 0)}"
            + (f", {suite['skipped']} skipped" if suite.get("skipped") else "")
            + ")"
            if suite
            else ""
        )
    ]
    if run["meta"].get("overrides"):
        names = ", ".join(o.split(" ", 1)[0] for o in run["meta"]["overrides"])
        lines.append(f"JUDGE INPUTS OVERRIDDEN: {names} (see latest.json)")
    for area, (n_pass, n_all) in area_counts(checks).items():
        mine = Counter(c["status"] for c in checks.values() if c["area"] == area)
        rest = " ".join(f"{k} {mine[k]}" for k in ("gap", "blocked", "fail") if mine[k])
        lines.append(f"  {area:<5} {AREAS[area]:<19} {n_pass:>2}/{n_all:<3} {rest}")
    needs = Counter(c["need"] for c in checks.values() if c["status"] == "blocked")
    if needs:
        lines.append(
            "blocked by: " + " · ".join(f"{n} {k}" for n, k in sorted(needs.items(), key=_desc))
        )
    closers = Counter(c.get("closer") or "?" for c in checks.values() if c["status"] == "gap")
    if closers:
        lines.append(
            "gaps close with: "
            + " · ".join(f"{Path(d).stem} {k}" for d, k in sorted(closers.items(), key=_desc))
        )
    work: Counter[str] = Counter()
    unblocks: Counter[str] = Counter()
    for need, k in needs.items():
        unblocks[providers.get(need, need)] += k
        work[providers.get(need, need)] += k
    for closer, k in closers.items():
        work[closer] += k
    if work:
        doc, _ = sorted(work.items(), key=_desc)[0]
        lines.append(f"next: {doc} (unblocks {unblocks[doc]}, closes {closers.get(doc, 0)})")
    tail = []  # the ratchet and the verdict are never cut; the FAIL lines give way
    if ratchet is not None:
        tail.append(_ratchet_line(ratchet, run["meta"].get("partial")))
        tail += [f"LOST {node}" for node in ratchet.lost[:3]]
        tail += [f"ABSENT {node}" for node in ratchet.absent[:3]]
        tail += [f"GREW {g}" for g in ratchet.growth[:3]]
    if red:
        tail.append("RED: " + "; ".join(red))
    tail += [f"not machine-checked: {NOT_MACHINE_CHECKED[0]}", f"  {NOT_MACHINE_CHECKED[1]}"]
    fails = [(n, c) for n, c in sorted(checks.items()) if c["status"] == "fail"]
    room = max(0, MAX_LINES - len(lines) - len(tail) - 1)
    shown = min(len(fails), MAX_FAIL_LINES, room)
    lines += [f"FAIL {node} — {c['reason'][:160]}" for node, c in fails[:shown]]
    if len(fails) > shown:
        lines.append(f"+{len(fails) - shown} more failures in build/progress/latest.json")
    return (lines + tail)[:MAX_LINES]


def _desc(item: tuple[str, int]) -> tuple[int, str]:
    return (-item[1], item[0])


def _ratchet_line(r: Ratchet, partial: str | None) -> str:
    base = f"ratchet vs {r.baseline[:10] or 'no baseline'}: "
    parts = [
        f"lost {len(r.lost)}",
        f"absent {len(r.absent)}",
        f"unrun {len(r.unrun)}" + (" (partial)" if partial and r.unrun else ""),
        *([f"unrun locally {len(r.unrun_local)}"] if r.unrun_local else []),
        f"gained {len(r.gained)}",
        f"grew {len(r.growth)}",
    ]
    if r.deselected or r.outside:
        parts.append(f"not selected {len(r.deselected) + len(r.outside)}")
    if r.fuel_not_compared:
        parts.append(f"fuel not compared (wasmtime changed) {len(r.fuel_not_compared)}")
    if r.judge_changed:
        more = len(r.judge_changed) - 3
        extra = f" and {more} more" if more > 0 else ""
        parts.append(f"judge changed: {', '.join(r.judge_changed[:3])}{extra}")
    return base + " · ".join(parts)
