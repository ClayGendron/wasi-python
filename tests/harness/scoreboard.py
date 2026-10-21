"""States, the ratchet, acceptance and the printed scoreboard.

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

from harness import history, paths

AREAS = {
    "v1.1": "artifact set",
    "v1.2": "portable, sealed",
    "v1.3": "data stack",
    "v1.4": "embedding",
    "v1.5": "rebuild from pins",
    "rules": "constitution rules",
}
STATES = ("pass", "fail", "gap", "blocked", "deselected", "unrun")
FUEL_TOLERANCE = 1e-4  # 0.01%: a run's fuel repeats exactly under the judge's own clock
NOT_MACHINE_CHECKED = (
    "publication · copying from prior art · numpy's 25 files that need its C test modules "
    "(number 89) · pandas beyond eight groups · CPython's tests that need its C test modules "
    "(number 101) · CPython under -bb · a fuel fact's fuel below its cap (spec 091)",
    "licence content of wasi-libc, llvm-runtimes and unpinned components "
    "(presence only) · "
    "bundled sub-licences · files a build adds inside a source tree · "
    # The gate sees the driver; the record scan sees meson, autoconf, CPython and step
    # 60; a compile that leaves no record, or a pragma the grep misses, is caught by same-bytes.
    "source pragmas and compiler options outside the scanned records (same-bytes is the backstop)",
)
# An accepted pass blocked by one of these is red: a product (artifact, runner, wheel) went missing,
# is how a regression could hide. Other needs (clones, the oracle, source trees, git) are local
# tooling a fresh clone lacks; their unrun passes are reported, not red.
PROTECTED_NEEDS = frozenset(
    {"artifact dir", "plain binary", "snapshot binary", "stdlib zip", "manifest", "runner", "wheel"}
)
MAX_FAIL_LINES = 10
MAX_LINES = 25
# A metric that must not fall: a fall is `fewer`, never `growth`.
COUNTS_UP = frozenset({"passes"})
# The checks that run numpy's and pandas' own tests: `--accept` refuses while one that has an
# accepted pass or gap did not run here, unless --partial.
UPSTREAM_FILE = "tests/checks/test_v1_3_upstream_suites.py"


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
    fewer: list[str] = field(default_factory=list)  # a count that must not fall fell
    more: list[str] = field(default_factory=list)  # such a count rose: reported, not `gained`
    upstream_unrun: list[str] = field(default_factory=list)  # upstream checks this run left out
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
        if self.fewer:
            why.append(f"{len(self.fewer)} pass count(s) fell (say --accept-fewer-passes)")
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
        elif acc["status"] == "gap" and now is None and node not in deselected:
            # A gap's check that is gone (its class or trap removed once fixed) is absent too,
            # so --retire can take it; a gap is never "lost".
            if not (repo / _file_of(node)).is_file() or _file_of(node) in collected_files:
                r.absent.append(node)
        if (
            _file_of(node) == UPSTREAM_FILE
            and acc["status"] in ("pass", "gap")
            and node not in r.absent
            and (now is None or now["status"] not in ("pass", "fail", "gap"))
        ):
            r.upstream_unrun.append(node)
        if now is None:
            continue
        old = acc.get("metrics", {}).get(meta["platform"], {})
        if now["status"] == "pass":
            for name in sorted(set(old) - {"wasmtime"} - set(now.get("metrics", {}))):
                if name in COUNTS_UP:  # only --accept-fewer-passes may drop it
                    r.fewer.append(f"{node}: {name} {old[name]} -> none")
                else:
                    r.growth.append(f"{node}: {name} is no longer recorded")
        for name, value in sorted(now.get("metrics", {}).items()):
            if name not in old:
                continue
            if name in COUNTS_UP:
                if value < old[name]:
                    r.fewer.append(f"{node}: {name} {old[name]} -> {value}")
                elif value > old[name]:
                    r.more.append(f"{node}: {name} {old[name]} -> {value}")
            elif name == "fuel":
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


def accept(
    run: dict,
    accepted: dict | None,
    history_lines: list[str],
    ratchet: Ratchet,
    *,
    green: bool,
    reason: str,
    judge_reason: str | None = None,
    growth_reason: str | None = None,
    partial_reason: str | None = None,
    retire: list[str] = (),
    fewer_reason: str | None = None,
) -> tuple[dict, str]:
    """(new accepted.json content, the history line to append), or AcceptRefused. The line is
    in format 2: the change in the passed set since the newest of
    `history_lines`, and a digest of the whole set."""
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
    if ratchet.fewer and not fewer_reason:  # --accept-growth never carries a lost pass
        refusals.append(
            f"pass counts fell ({', '.join(ratchet.fewer[:3])}); "
            "say --accept-fewer-passes with a reason"
        )
    if ratchet.upstream_unrun and not partial_reason:
        refusals.append(
            f"{len(ratchet.upstream_unrun)} accepted upstream suite check(s) did not run here "
            f"({UPSTREAM_FILE}); say --partial with a reason"
        )
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
    try:
        before = history.last_passed(history_lines)
    except ValueError as e:
        raise AcceptRefused(f"the history does not replay: {e} (spec 062)") from None

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
                if name in COUNTS_UP:  # only --accept-fewer-passes lowers it
                    keep = name in old and not fewer_reason
                    merged[name] = max(old[name], value) if keep else value
                    continue
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
    prev = history_lines[-1] if history_lines else None
    passes = {n for n, c in run["checks"].items() if c["status"] == "pass"}
    counts = {
        area: f"{n_pass}/{n_all}" for area, (n_pass, n_all) in area_counts(run["checks"]).items()
    }
    line = {
        "n": len(history_lines) + 1,
        "prev": paths.sha256_bytes(prev.encode()) if prev else None,
        "at": meta["at"],
        "commit": meta["commit"],
        "dirty": meta["dirty"],
        "platform": platform,
        "host": meta["host"],
        "artifact": meta["artifact"],
        "set_sums": meta.get("set_sums"),  # the set, beside python.wasm
        "wasmtime": meta["wasmtime"],
        "reason": reason,
        "judge_reason": judge_reason,
        "growth_reason": growth_reason,
        "partial_reason": partial_reason,
        "fewer_reason": fewer_reason,
        "retired": sorted(retire),
        "judge_changed": ratchet.judge_changed,
        "counts": counts,
        "schema": 2,
        "passed_added": sorted(passes - before),
        "passed_removed": sorted(before - passes),
        "passed_digest": history.digest(passes),
        "accepted": paths.sha256_bytes(dumps(new).encode()),
    }
    text = json.dumps(line, sort_keys=True)
    size = len(text.encode()) + 1
    if size > history.BUDGET:  # never written, even once
        raise AcceptRefused(
            f"the history line would be {size} bytes, over the volume budget of "
            f"{history.BUDGET} (spec 062)"
        )
    history.remember(text, passes)
    return new, text


def area_counts(checks: dict) -> dict[str, tuple[int, int]]:
    out = {}
    for area in AREAS:
        mine = [c for c in checks.values() if c["area"] == area]
        out[area] = (sum(c["status"] == "pass" for c in mine), len(mine))
    return out


def no_trap_here(checks: dict) -> list[str]:
    """The open trap entries whose check ran here and recorded no trap: a
    fixed trap asks to be seen, never red."""
    out = []
    for node, c in sorted(checks.items()):
        if "::test_upstream_trap[" in node and (c.get("facts") or {}).get("trap") == (
            "no trap on this host"
        ):
            out.append(node.rsplit("[", 1)[1].rstrip("]"))
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
    lines += run["meta"].get("notes", [])  # e.g. a worktree inside the repository
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
    quiet = no_trap_here(checks)
    if quiet:
        lines.append("trap entries with no trap here: " + " · ".join(quiet))
    # The ratchet line, every FEWER line, the verdict and the "not
    # machine-checked" lines are never cut. LOST, ABSENT and GREW lines give way first, then the
    # FAIL lines, then the lines above the tail.
    head, examples, end = [], [], []
    if ratchet is not None:
        head.append(_ratchet_line(ratchet, run["meta"].get("partial")))
        head += [f"FEWER {f}" for f in ratchet.fewer]
        examples += [f"LOST {node}" for node in ratchet.lost[:3]]
        examples += [f"ABSENT {node}" for node in ratchet.absent[:3]]
        examples += [f"GREW {g}" for g in ratchet.growth[:3]]
    if red:
        end.append("RED: " + "; ".join(red))
    end += [f"not machine-checked: {NOT_MACHINE_CHECKED[0]}"]
    end += [f"  {line}" for line in NOT_MACHINE_CHECKED[1:]]
    fixed = len(head) + len(end)
    examples = examples[: max(0, MAX_LINES - len(lines) - fixed)]
    tail = head + examples + end
    fails = [(n, c) for n, c in sorted(checks.items()) if c["status"] == "fail"]
    room = max(0, MAX_LINES - len(lines) - len(tail) - 1)
    shown = min(len(fails), MAX_FAIL_LINES, room)
    lines += [f"FAIL {node} — {c['reason'][:160]}" for node, c in fails[:shown]]
    if len(fails) > shown:
        lines.append(f"+{len(fails) - shown} more failures in build/progress/latest.json")
    return lines[: max(1, MAX_LINES - len(tail))] + tail


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
        *([f"fewer {len(r.fewer)}"] if r.fewer else []),
        *([f"more {len(r.more)}"] if r.more else []),
        *([f"upstream unrun {len(r.upstream_unrun)}"] if r.upstream_unrun else []),
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
