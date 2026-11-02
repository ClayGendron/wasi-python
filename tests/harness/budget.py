"""The fast tier's budget: what keeps the judge's own cost from growing by accident.

A normal-tier goal check is over budget when its fuel, on any platform, is past the cap its family
has in `tests/lint/budget.toml`. A product check's family is its file (by stem); an upstream
check's is the package whose TOML holds its group. A check over budget is a finding until it is
listed under `[[over]]` with the specification that will move it to the slow normal tier or the
release tier (`closes_with`, the number of a specification not yet landed) and why
(`reason`); a listed one is reported, naming it, and an entry whose check is no longer over budget
is a finding too, so the list only shrinks.

Fuel counts operations, so it is held where it is measured: the gather holds each shard record's
own fuel, so the pull request that grows a check past its cap is the one that is red, and the
acceptance from CI's record refuses to accept such a check. `lint` holds the accepted fuel too,
the backstop for a cap or an entry edited by hand.

Time is reported, never failed on: a duration depends on the host that ran it, and a test counts
operations. Each goal check the quick job's JUnit report says took longer than the file's
`seconds` becomes a warning annotation and a line of the job's summary:

    uv run python tests/harness/budget.py --times build/ci/quick-rules.xml

A document's length is reported the same way, never failed on: lint names each specification past
2,000 words, or whose landing notes run past 15 lines, as a warning annotation and a line of the
job's summary, so a specification stays one that is read in ten minutes. One written before the
caps is not named.
"""

from __future__ import annotations

import os
import re
import sys
import tomllib
import xml.etree.ElementTree as ElementTree
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

if __package__ in (None, ""):  # run as a script: the harness package lives one folder up
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from harness import paths  # noqa: E402

FILE = paths.REPO / "tests" / "lint" / "budget.toml"
UPSTREAM_FILE = "tests/checks/test_v1_3_upstream_suites.py"
GOAL_DIR = "tests/checks/"
WARNING = "::warning title=fast-tier budget::"  # a GitHub Actions annotation
LENGTH_WARNING = "::warning title=document length::"
SPEC_WORDS = 2000  # a specification says its decisions in about 1,500
LANDING_LINES = 15  # its landing notes are ten lines; the history lives in the pull request
# The caps hold from this date; a specification dated before it is not rewritten to fit, so it is
# not named either, and the warning stays a short list someone can act on.
LENGTH_SINCE = "2026-10-30"
DATE = re.compile(r"^- \*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2})", re.M)
ANY_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
RELEASE_WARNING = "::warning title=release leg minutes::"


@dataclass(frozen=True)
class Over:
    check: str
    closes_with: str
    reason: str


@dataclass(frozen=True)
class Budget:
    seconds: float
    caps: dict[str, int]
    over: tuple[Over, ...]


def load(path: Path = FILE) -> Budget:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    over = tuple(
        Over(o["check"], str(o["closes_with"]), o.get("reason", "")) for o in raw.get("over", [])
    )
    return Budget(float(raw["seconds"]), {k: int(v) for k, v in raw["fuel"].items()}, over)


def upstream_families() -> dict[str, str]:
    """Every upstream check's family: the package whose TOML holds its group."""
    from harness import shards, upstream

    configs = upstream.load_all()
    package = {g: name for name, c in configs.items() for g in c.groups}
    return {node: package[g] for node, g in shards.group_of(configs).items() if g in package}


def family_of(node: str, upstream_family: dict[str, str]) -> str:
    """A check's family: its package for an upstream check, else its file's stem."""
    file = node.split("::", 1)[0]
    if file == UPSTREAM_FILE:
        return upstream_family.get(node, "upstream")
    return PurePosixPath(file).stem


def fuel_over(accepted: dict, caps: dict[str, int], family: Callable[[str], str]) -> list[str]:
    """Each normal-tier accepted check whose fuel on some platform is past its family's cap, or
    whose family has no cap: `node` lines with their reason."""
    out = []
    for node, entry in sorted(accepted.get("checks", {}).items()):
        if entry.get("tier") == "release":
            continue
        fuels = [m["fuel"] for m in entry.get("metrics", {}).values() if "fuel" in m]
        if not fuels:
            continue
        name = family(node)
        cap = caps.get(name)
        if cap is None:
            out.append(f"{node}: records fuel, and its family {name} has no cap in the budget")
        elif max(fuels) > cap:
            out.append(f"{node}: fuel {max(fuels):,} is past its family {name}'s cap {cap:,}")
    return out


def run_fuel_over(
    checks: dict, caps: dict[str, int], family: Callable[[str], str], release: set[str]
) -> list[str]:
    """Each passing normal-tier check of one run's record whose own fuel is past its family's
    cap, or whose family has no cap."""
    out = []
    for node, c in sorted(checks.items()):
        metrics = c.get("metrics") or {}
        fuel = metrics.get("fuel") if isinstance(metrics, dict) else None
        if c.get("status") != "pass" or node in release or not isinstance(fuel, int):
            continue
        name = family(node)
        cap = caps.get(name)
        if cap is None:
            out.append(f"{node}: records fuel, and its family {name} has no cap in the budget")
        elif fuel > cap:
            out.append(f"{node}: fuel {fuel:,} is past its family {name}'s cap {cap:,}")
    return out


def stale_caps(
    accepted: dict,
    caps: dict[str, int],
    family: Callable[[str], str],
    pending: Iterable[str] = (),
) -> list[str]:
    """Caps for a family no normal-tier accepted check with fuel belongs to. A `pending` family's
    cap is not stale: its check file is new, and the cap comes with it, since the pull request's
    own run needs it before any of its checks is accepted."""
    used = {
        family(node)
        for node, e in accepted.get("checks", {}).items()
        if e.get("tier") != "release" and any("fuel" in m for m in e.get("metrics", {}).values())
    }
    stale = set(caps) - used - set(pending)
    return [f"the cap for {name} names no family with fuel" for name in sorted(stale)]


def new_families(accepted: dict, files: Iterable[str]) -> set[str]:
    """The families of goal check files (repository-relative paths) that no accepted check comes
    from: files added since the last acceptance."""
    seen = {node.split("::", 1)[0] for node in accepted.get("checks", {})}
    return {PurePosixPath(f).stem for f in files if f not in seen}


def new_upstream_families(accepted: dict, upstream_family: dict[str, str]) -> set[str]:
    """The packages whose upstream checks no accepted check is one of: suites added since the
    last acceptance, whose cap comes with them as a new check file's does."""
    seen = {upstream_family[node] for node in accepted.get("checks", {}) if node in upstream_family}
    return set(upstream_family.values()) - seen


def _node(classname: str, name: str, repo: Path) -> str:
    """A JUnit test case's node id: the longest dotted prefix of its class name that is a file."""
    parts = classname.split(".")
    for i in range(len(parts), 0, -1):
        file = "/".join(parts[:i]) + ".py"
        if (repo / file).is_file():
            return "::".join([file, *parts[i:], name])
    return f"{classname.replace('.', '/')}.py::{name}"


def time_over(
    reports: Iterable[str], seconds: float, release: set[str], repo: Path = paths.REPO
) -> list[str]:
    """Each normal-tier goal check a JUnit report says took longer than `seconds`."""
    out = []
    for text in reports:
        for case in ElementTree.fromstring(text).iter("testcase"):
            node = _node(case.get("classname", ""), case.get("name", ""), repo)
            took = float(case.get("time") or 0)
            if node.startswith(GOAL_DIR) and node not in release and took > seconds:
                out.append(f"{node}: {took:.1f} s in quick, past {seconds:g} s")
    return out


# A specification whose Status says it has landed or was superseded moves nothing any more.
DONE = re.compile(r"(?:landed|superseded)\b", re.I)
STATUS = re.compile(r"^- \*\*Status:\*\*\s*(.*)$", re.M)


def spec_status(folder: Path) -> dict[str, str]:
    """Each written specification's number and its Status line's text, bold marks dropped."""
    out = {}
    for f in sorted(folder.glob("[0-9][0-9][0-9]-*.md")):
        m = STATUS.search(f.read_text(encoding="utf-8"))
        out[f.name[:3]] = m[1].replace("*", "").strip() if m else ""
    return out


def findings(
    over: list[str], budget: Budget, specs: dict[str, str], stale: bool = True
) -> tuple[list[str], list[str]]:
    """(the findings, the reported lines): an over-budget line is a finding unless `[[over]]`
    lists its check with a reason and the number of a specification still to land (`specs` maps
    each written one to its Status), when it is reported, naming it; with `stale`, an entry
    whose check is not over budget is a finding (not on a run of some shards, where the entry's
    check may not have run)."""
    listed = {o.check: o for o in budget.over}
    bad, reported = [], []
    seen = set()
    for line in over:
        node = line.split(": ", 1)[0]
        entry = listed.get(node)
        if entry is not None:
            seen.add(node)
        if entry is None:
            bad.append(
                f"{line}: move it to the slow normal tier or the release tier, or list it under "
                "[[over]] with the specification that will"
            )
        elif not entry.reason.strip():
            bad.append(f"{line}: its [[over]] entry gives no reason")
        elif entry.closes_with not in specs:
            bad.append(f"{line}: its [[over]] entry names {entry.closes_with!r}, no specification")
        elif DONE.match(specs[entry.closes_with].replace("*", "").strip()):
            bad.append(
                f"{line}: its [[over]] entry names {entry.closes_with!r}, which has landed and "
                "moves nothing now"
            )
        else:
            reported.append(f"{line}: specification {entry.closes_with} moves it")
    if stale:
        bad += [
            f"[[over]] {o.check} is not over budget" for o in budget.over if o.check not in seen
        ]
    return bad, reported


def time_warnings(
    reports: Iterable[Path],
    seconds: float,
    release: set[str],
    repo: Path = paths.REPO,
    summary: Path | None = None,
) -> list[str]:
    """The annotation lines for each goal check past `seconds`, or for a report that is not
    there, each written to the job's summary too when it is given. Never a failure."""
    lines, texts = [], []
    for report in reports:
        if report.is_file():
            texts.append(report.read_text(encoding="utf-8"))
        else:
            lines.append(f"no timing report at {report}")
    lines += time_over(texts, seconds, release, repo)
    if summary is not None and lines:
        with summary.open("a", encoding="utf-8") as f:
            f.write("### The fast tier's time budget (warnings)\n\n")
            f.write("".join(f"- {line}\n" for line in lines) + "\n")
    return [WARNING + line for line in lines]


def length_over(
    specs: Iterable[Path], words: int = SPEC_WORDS, lines: int = LANDING_LINES
) -> list[str]:
    """Each specification past `words` words, and each whose landing notes section runs past
    `lines` lines that are not blank. One dated before `LENGTH_SINCE` is left out: its Date line,
    or else the first date its header names (the oldest specifications have only a Status)."""
    out = []
    for spec in specs:
        text = spec.read_text(encoding="utf-8")
        dated = DATE.search(text) or ANY_DATE.search(text.split("\n## ", 1)[0])
        if dated and dated[1] < LENGTH_SINCE:
            continue
        count = len(text.split())
        if count > words:
            out.append(f"{spec.name}: {count:,} words, past {words:,}")
        notes = re.search(r"^## Landing notes[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if notes:
            n = sum(1 for line in notes[1].splitlines() if line.strip())
            if n > lines:
                out.append(f"{spec.name}: its landing notes run {n} lines, past {lines}")
    return out


def length_warnings(specs: Iterable[Path], summary: Path | None = None) -> list[str]:
    """The annotation lines for each specification `length_over` names, each written to the
    job's summary too when it is given. Never a failure."""
    lines = length_over(specs)
    if summary is not None and lines:
        with summary.open("a", encoding="utf-8") as f:
            f.write("### Long specifications (warnings)\n\n")
            f.write("".join(f"- {line}\n" for line in lines) + "\n")
    return [LENGTH_WARNING + line for line in lines]


def release_minutes_warnings(plan: dict) -> list[str]:
    """The annotation lines for each release shard whose measured minutes pass the packing's
    cap: a group too long to share a leg, named until its suite's groups are split. Never a
    failure, since the minutes were read from one run's host."""
    from harness import shards

    cap = shards.RELEASE_LEG_MINUTES
    return [
        f"{RELEASE_WARNING}{name}: {s.minutes} measured minutes, past the release legs' {cap}"
        for name, s in plan.items()
        if "release" in s.systems and isinstance(s.minutes, int | float) and s.minutes > cap
    ]


def main(argv: list[str]) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(prog="budget.py")
    ap.add_argument("--times", action="append", default=[], type=Path, help="a JUnit report")
    a = ap.parse_args(argv)
    accepted = json.loads((paths.PROGRESS / "accepted.json").read_text(encoding="utf-8"))
    release = {n for n, e in accepted.get("checks", {}).items() if e.get("tier") == "release"}
    named = os.environ.get("GITHUB_STEP_SUMMARY")
    for line in time_warnings(
        a.times, load().seconds, release, summary=Path(named) if named else None
    ):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
