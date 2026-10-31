"""The acceptance from CI's record.

    uv run pytest --accept-from=build/ci/record.json --claims=<the news files' folder>

(each option with `=`: pytest reads the plugin's options from the tests' conftest, which it loads
only when no path is given on the command line, and a value after a space reads as a path)

The accept job runs this in a fresh checkout of the commit a merge into dev put there, once the
run's every job is green: it records the gather's merged record as the accepted state, as a local
`--accept` records its own run, and runs no check. Its reasons come from the claim blocks of the
news files changed since the last acceptance, never from a flag. It writes accepted.json, appends
one line to the newest history volume, and writes the acceptance commit's message beside the run
record; the job after it commits those two files alone and pushes them.

On a push to dev a merge is accepted when its run is green: a growth, a fall in a pass count, a
tier move or a verdict-bearing judge file that no claim gives a reason for is accepted, and written
into the history line under `unclaimed` with its values, so the reason is written once, by the
person who knows it, at the merge or at the release. The release pull request's acceptance asks
for it: it is refused while a row written unclaimed since the last release's acceptance has no
claim among the release's, which are the release ledger's, the news files that bump (or date)
removed since that release, read back from git at the commit before the one that removed them,
and the news files still in the folder.

The local acceptance's guards, in their form for a record:

- a linked worktree is no refusal: CI's checkout is a fresh clone, and the record, not the tree,
  carries what was judged;
- a dirty tree is refused, before the record is read and again when the acceptance is written;
- the record's commit and every shard's are the checkout's HEAD (the local run's "HEAD moved");
- the judge's collection at this commit is not empty, and is the record's checks exactly;
- `--shard`, and every flag that gives a reason (`--accept`, `--partial` and the rest), refused;
- the record is green: the gather's verdict has no red line, nothing steered any shard from
  outside the judge, and each shard's only override is `--progress-latest`;
- a lost pass is refused, and no claim clears it;
- an absent check is retired only by a claim's `retired`, and a `retired` entry that names no
  absent check refuses, as `--retire` does;
- an accepted pass blocked, or an accepted upstream check not run, is always refused: a run that
  blocks an accepted pass is a broken run, and no claim clears it;
- a growth is cleared by `grows` with its `growth`, a fall in a pass count by `passes` with its
  `fewer`, a changed judge file by `judge`, a tier move by `moved`; an unclaimed one is recorded
  on dev and refused, named, on the release pull request;
- a history that does not replay, or breaks its chain or its volume rule, is refused.

It also refuses a record of any event but a push to dev or a pull request into main, and one
whose set was neither built in its run nor reused by its key. Every refusal is named at once.

The record is read as the darwin run it contains, as the gather and sameness read it: each check
as the record that ran it saw it, darwin first. A check darwin ran is applied with darwin's
metrics, keyed `darwin-arm64` though the job runs on Linux. A check only another system ran (the
upstream groups run on Linux alone) takes the record's counts (`passes`, `bytes`), which the gather
holds equal on every system, under the same key, where the gather reads them. Its fuel is darwin's
accepted one when darwin measured it under this wasmtime; otherwise it is the record's, labelled
with the system that measured it (`fuel_platform`), so an engine move leaves no check without a
fuel. A labelled fuel is never compared with another system's, nor with its own system's next one,
since Linux's fuel moves between runs; darwin's first measurement replaces it. The history line
names the systems whose probe passed, so the `three systems` need is met by the record.
"""

from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from harness import budget, history, news, paths, scoreboard

DARWIN = "darwin-arm64"  # the platform the ratchet keys darwin's metrics by
COUNTS = ("passes", "bytes", "ignores")  # metrics the gather holds equal on every system
REFUSED = "--accept-from refused"
REUSED = re.compile(r"reused \S+")
MESSAGE_FILE = "acceptance-message.txt"  # beside the run record
# Every option that gives a reason or narrows the run: the reasons are the news files'.
REFUSED_OPTIONS = (
    "--accept",
    "--accept-judge",
    "--accept-growth",
    "--accept-fewer-passes",
    "--accept-tier-move",
    "--partial",
    "--retire",
    "--shard",
    "--tier",
)


class Refused(Exception):
    """The acceptance is refused; the message names every reason."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


@dataclass
class Inputs:
    record: dict  # the gather's merged record
    accepted: dict | None
    history_lines: list[str]
    history_errors: list[str]  # what is wrong with the history folder
    goal_nodes: list[str]  # the judge's collection at this commit
    head: str
    subject: str  # the merged commit's subject: the pull request's title and number
    judge: dict  # {"hash", "files"} of this checkout
    wasmtime: str  # the version uv.lock names
    claims: list[news.Claim]
    dirty: str | None = None  # a path with a change the judge could see
    options: tuple[str, ...] = ()  # the refused options given
    at: str = ""
    host: str = ""
    record_sha256: str = ""
    repo: Path = paths.REPO
    # The fast tier's budget, the upstream checks' families and the specifications' Status lines;
    # None leaves the budget out.
    budget: tuple[budget.Budget, dict[str, str], dict[str, str]] | None = None


@dataclass
class Acceptance:
    accepted: dict
    line: str
    message: str
    reasons: list[str] = field(default_factory=list)


def _merged(record: dict) -> bool:
    meta = record.get("meta")
    return isinstance(meta, dict) and "records" in meta and isinstance(record.get("runs"), dict)


def _release_pr(meta: dict) -> bool:
    """The record is the release pull request's, from dev into main."""
    return meta.get("event") == "pull_request" and meta.get("base_ref") == "main"


def _event_refusal(meta: dict) -> str | None:
    push_to_dev = (
        meta.get("event") == "push" and meta.get("ref") == "refs/heads/dev" and not meta.get("tag")
    )
    if push_to_dev or _release_pr(meta):
        return None
    return (
        f"the record is of a {meta.get('event')!r} on {meta.get('ref')!r}: only a push to dev or "
        "a release pull request into main is accepted"
    )


def record_refusals(i: Inputs) -> list[str]:
    """What the record must be before its rows are read."""
    out = [f"{o} is refused with --accept-from: its reasons are the news files'" for o in i.options]
    if i.dirty is not None:
        out.append(f"a dirty tree: {i.dirty} has a change the judge could see")
    r = i.record
    if not _merged(r):
        return [*out, "not a gather's merged record (no meta.records or runs)"]
    meta = r["meta"]
    if (why := _event_refusal(meta)) is not None:
        out.append(why)
    source = str(meta.get("set_source", ""))
    if source != "built" and not REUSED.fullmatch(source):
        out.append(f"set_source {source!r} is neither built nor reused by its key")
    red = meta.get("red")
    if not isinstance(red, list):
        out.append("the record carries no verdict of its gather (meta.red)")
    elif red:
        out.append(f"the gather's verdict has a red line: {red[0]}")
    if meta.get("commit") != i.head:
        out.append(f"the record's commit {str(meta.get('commit'))[:12]} is not HEAD {i.head[:12]}")
    if meta.get("foreign"):
        out.append(f"steered from outside the judge: {meta['foreign'][:3]}")
    for key, run in sorted(r["runs"].items()):
        if run.get("commit") != i.head:
            out.append(f"{key}: its commit {str(run.get('commit'))[:12]} is not HEAD")
        if run.get("dirty") is not False:
            out.append(f"{key}: judged on a dirty tree")
        if run.get("foreign"):
            out.append(f"{key}: steered from outside the judge: {run['foreign'][:3]}")
        o = run.get("overrides")
        if not (isinstance(o, list) and len(o) == 1 and str(o[0]).startswith("--progress-latest ")):
            out.append(f"{key}: overrides {o}, not --progress-latest alone")
    if (meta.get("judge") or {}).get("hash") != i.judge.get("hash"):
        out.append("the record's judge hash is not this checkout's")
    if meta.get("tier") not in scoreboard.TIERS:
        out.append(f"the record's tier {meta.get('tier')!r} is not normal or release")
    if not i.goal_nodes:
        out.append("the judge at this commit collected no goal check")
    elif set(r.get("checks", {})) != set(i.goal_nodes):
        more = len(set(r.get("checks", {})) - set(i.goal_nodes))
        fewer = len(set(i.goal_nodes) - set(r.get("checks", {})))
        out.append(f"the record's checks are not this commit's collection (+{more} -{fewer})")
    if i.history_errors:
        out.append(f"the history does not replay or breaks its rules: {i.history_errors[0]}")
    return out


def _metrics(c: dict, platform: str, i: Inputs, node: str) -> dict:
    """The metrics a check is applied with, keyed darwin (the module docstring)."""
    if platform.startswith("darwin-"):
        return dict(c.get("metrics") or {})
    acc = ((i.accepted or {}).get("checks", {}).get(node, {}).get("metrics") or {}).get(DARWIN, {})
    measured = c.get("metrics") or {}
    kept = {k: v for k, v in acc.items() if k not in scoreboard.LABELS and k not in COUNTS}
    darwins = "fuel" in acc and "fuel_platform" not in acc and acc.get("wasmtime") == i.wasmtime
    if not darwins:  # no fuel darwin measured under this engine: the record's stands in for it
        kept.pop("fuel", None)
        if "fuel" in measured:
            kept.update(fuel=measured["fuel"], fuel_platform=platform)
    kept.update({k: v for k, v in measured.items() if k in COUNTS})
    return kept


def run_from_record(i: Inputs) -> dict:
    """The record as a run the ratchet compares and the acceptance records: each check as the
    record that ran it saw it; a check no shard ran (deselected everywhere, or blocked by a need
    CI lacks) at its merged status."""
    r = i.record
    checks = {}
    for node, c in r["checks"].items():
        source = c.get("source")
        if source is None:
            entry = {k: c.get(k) for k in ("area", "status", "reason", "need")}
            entry["metrics"] = {}
        else:
            entry = {k: v for k, v in source.items() if k != "platform"}
            entry.setdefault("need", None)
            entry["metrics"] = _metrics(c, str(source.get("platform", "")), i, node)
        checks[node] = entry
    meta = r["meta"]
    return {
        "meta": {
            "at": i.at,
            "commit": i.head,
            "dirty": False,
            "platform": DARWIN,
            "host": i.host,
            "wasmtime": i.wasmtime,
            "artifact": meta.get("artifact"),
            "set_sums": meta.get("set_sums"),
            "judge": i.judge,
            "tier": meta.get("tier"),
            "shard": None,
            "foreign": [],
        },
        "checks": checks,
        "deselected": list(r.get("deselected", [])),
        "release_checks": list(r.get("release_checks", [])),
        "collected_files": list(r.get("collected_files", [])),
        "suite": {},
    }


def _node(row: str) -> str:
    """The check a ratchet row names: `<node>: fuel 7 -> 70`."""
    return row.split(": ", 1)[0]


def _joined(reasons: list[str]) -> str | None:
    kept = list(dict.fromkeys(r for r in reasons if r))
    return "; ".join(kept) if kept else None


@dataclass
class Claimed:
    retire: list[str] = field(default_factory=list)
    growth: list[str] = field(default_factory=list)
    fewer: list[str] = field(default_factory=list)
    judge: list[str] = field(default_factory=list)
    moved: list[str] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)
    # Rows no claim gives a reason for: (the claim's kind, the check or file, the ratchet's row).
    # Recorded unclaimed on dev; refused, named, on the release pull request.
    missing: list[tuple[str, str, str]] = field(default_factory=list)


def claimed(ratchet: scoreboard.Ratchet, claims: list[news.Claim], judged: bool) -> Claimed:
    """Each row the acceptance needs a reason for, with the claim that gives it; a loss, or a
    claim that names nothing, as a refusal; a row no claim gives a reason for, as missing.
    `judged`: there is an accepted judge to have changed."""
    c = Claimed()
    if ratchet.lost:
        c.refusals.append(f"lost passes, which no claim clears: {', '.join(ratchet.lost[:3])}")
    if ratchet.unrun:
        c.refusals.append(f"accepted passes are blocked: {', '.join(ratchet.unrun[:3])}")
    if ratchet.upstream_unrun:
        c.refusals.append(
            f"accepted upstream checks did not run: {', '.join(ratchet.upstream_unrun[:3])}"
        )
    for node in ratchet.absent:
        if news.reason(claims, "retired", node):
            c.retire.append(node)
        else:
            c.refusals.append(f"absent, and no claim retires it: {node}")
    for claim in claims:
        for entry in claim.retired:
            if not any(news.names(entry, n) for n in ratchet.absent):
                c.refusals.append(f"{claim.spec}: retired names {entry}, which is not absent")
    for kind, rows, into in (
        ("grows", ratchet.growth, c.growth),
        ("passes", ratchet.fewer, c.fewer),
    ):
        for row in rows:
            why = news.reason(claims, kind, _node(row))
            if why:
                into.append(why)
            else:
                c.missing.append((kind, _node(row), row))
    # Only a judge file that moves a verdict needs its reason; the judge's hash in the history
    # records every other change, and a claim for one is not passed on.
    verdict = [f for f in ratchet.judge_changed if paths.is_verdict_bearing(f)]
    for f in verdict if judged else ():
        why = news.reason(claims, "judge", f)
        if why:
            spec, text = why.split(": ", 1)
            c.judge.append(f"{spec}: {f}: {text}")
        else:
            c.missing.append(("judge", f, f))
    for node in ratchet.moved:
        why = news.reason(claims, "moved", node)
        if why:
            c.moved.append(why)
        else:
            c.missing.append(("moved", node, node))
    return c


# How the release pull request names a row no claim gives a reason for.
MISSING = {
    "grows": "a growth, unclaimed: {}",
    "passes": "a pass count that fell, unclaimed: {}",
    "judge": "the judge changed, unclaimed: {}",
    "moved": "a check moved between tiers, unclaimed: {}",
}
# The reason a row accepted unclaimed on dev takes in the history line's own reason fields.
UNCLAIMED = "unclaimed: its reason is due by the release"
# The history line's reason field each kind of row is accepted under.
REASON_OF = {"grows": "growth", "passes": "fewer", "judge": "judge", "moved": "tier move"}
VALUES = re.compile(r"(?P<metric>\S+) (?P<old>\S+) -> (?P<new>\S+)")


def _value(text: str):
    """A metric's value as a ratchet row prints it: a number, or None for `none`."""
    try:
        return json.loads(text)
    except ValueError:
        return None


def unclaimed_row(kind: str, key: str, row: str, accepted: dict | None, judge: dict) -> dict:
    """A row accepted with no claim, as the history line keeps it: its kind, its check (or, for
    a judge file, its file) and the values before and after."""
    acc = accepted or {}
    if kind == "judge":
        old = acc.get("judge", {}).get("files", {}).get(key)
        return {"kind": kind, "file": key, "old": old, "new": judge.get("files", {}).get(key)}
    if kind == "moved":
        was = acc.get("checks", {}).get(key, {}).get("tier") or "normal"
        now = "normal" if was == "release" else "release"
        return {"kind": kind, "check": key, "old": was, "new": now}
    rest = row.split(": ", 1)[1]
    m = VALUES.fullmatch(rest)
    if m is not None:
        metric, old, new = m["metric"], _value(m["old"]), _value(m["new"])
    else:  # "<metric> is no longer recorded"
        metric, new = rest.split(" ", 1)[0], None
        old = acc.get("checks", {}).get(key, {}).get("metrics", {}).get(DARWIN, {}).get(metric)
    return {"kind": kind, "check": key, "metric": metric, "old": old, "new": new}


def _said(row: dict) -> str:
    """One unclaimed row in words: its kind, its subject and how it moved."""
    key = row.get("check") or row.get("file")
    if row.get("kind") == "judge":
        return f"judge {key}: changed"
    old, new = ("none" if v is None else v for v in (row.get("old"), row.get("new")))
    metric = f"{row['metric']} " if "metric" in row else ""
    return f"{row.get('kind')} {key}: {metric}{old} -> {new}"


def _is_release_line(entry: dict) -> bool:
    """A history line the release pull request's acceptance wrote. A line from before the event
    was written names it by CI's source and the release tier, which only that acceptance judges."""
    if "event" in entry:
        return entry["event"] == "pull_request"
    return entry.get("source") == "ci" and entry.get("tier") == "release"


def since_release(history_lines: list[str]) -> tuple[list[tuple[int, dict]], str | None]:
    """Each row accepted unclaimed since the last release's acceptance, with its line's number,
    oldest first, and the commit that acceptance judged; None for the commit when no release was
    accepted, so the whole history is read."""
    rows: list[tuple[int, dict]] = []
    for line in reversed(history_lines):
        entry = json.loads(line)
        if _is_release_line(entry):
            return rows, entry.get("commit")
        rows[:0] = [(entry.get("n"), r) for r in entry.get("unclaimed") or []]
    return rows, None


def reconciled(history_lines: list[str], claims: list[news.Claim]) -> list[str]:
    """The release's refusals: each row accepted unclaimed since the last release that no claim
    of the release's gives a reason for, named with its line and the ledger that would clear it."""
    out = []
    for n, row in since_release(history_lines)[0]:
        if news.reason(claims, str(row.get("kind")), row.get("check") or row.get("file")) is None:
            out.append(
                f"history line {n} accepted {_said(row)} with no claim, and the release has none: "
                f"write its [[claim]] block in {news.LEDGER}"
            )
    return out


def _budget() -> tuple[budget.Budget, dict[str, str], dict[str, str]]:
    """This checkout's budget, its upstream checks' families and its specifications' Status."""
    specs = budget.spec_status(paths.CONTEXT / "specifications")
    return budget.load(), budget.upstream_families(), specs


def message(subject: str, reasons: list[str]) -> str:
    """The acceptance commit's message: the merge's own subject (its pull request's title and
    number) and the reasons. No skip word: the plan is quiet on a push of the accepted state, and
    a skip word would also skip a release pull request whose head this commit is."""
    body = "\n".join(reasons) if reasons else "no row needed a reason"
    return f"Accepted: {subject}\n\n{body}\n"


def accept(i: Inputs) -> Acceptance:
    """The new accepted state, its history line and the commit message, or Refused."""
    refusals = record_refusals(i)
    if refusals:
        raise Refused(refusals)
    run = run_from_record(i)
    ratchet = scoreboard.compare(run, i.accepted, i.repo)
    c = claimed(ratchet, i.claims, judged=bool(i.accepted))
    release = _release_pr(i.record["meta"])
    unclaimed = [] if release else [unclaimed_row(*m, i.accepted, i.judge) for m in c.missing]
    if release:
        c.refusals += [MISSING[kind].format(row) for kind, _, row in c.missing]
        c.refusals += reconciled(i.history_lines, i.claims)
    if i.budget is not None:  # no check is accepted past its family's fuel cap unless listed
        plan_budget, families, specs = i.budget
        over = budget.run_fuel_over(
            run["checks"],
            plan_budget.caps,
            lambda node: budget.family_of(node, families),
            set(run["release_checks"]),
        )
        c.refusals += budget.findings(over, plan_budget, specs, stale=False)[0]
    if c.refusals:
        raise Refused(c.refusals)
    runs = i.record["runs"].values()
    platforms = sorted({str(x.get("platform")) for x in runs if x.get("probe") == "pass"})
    late = {REASON_OF[r["kind"]] for r in unclaimed}
    reasons = {
        k: _joined(v + ([UNCLAIMED] if k in late else []))
        for k, v in (
            ("judge", c.judge),
            ("growth", c.growth),
            ("fewer", c.fewer),
            ("tier move", c.moved),
        )
    }
    why = f"from CI's record of {i.head[:12]}: {i.subject}"
    try:
        new, line = scoreboard.accept(
            run,
            i.accepted,
            i.history_lines,
            ratchet,
            green=True,
            reason=why,
            judge_reason=reasons["judge"],
            growth_reason=reasons["growth"],
            retire=c.retire,
            fewer_reason=reasons["fewer"],
            tier_move_reason=reasons["tier move"],
            extra={
                "source": "ci",
                "record": i.record_sha256,
                "platforms": platforms,
                "event": i.record["meta"].get("event"),
            },
            unclaimed=unclaimed,
        )
    except scoreboard.AcceptRefused as e:
        raise Refused([str(e)]) from None
    listed = [f"{k}: {v}" for k, v in reasons.items() if v]
    listed += [f"retired: {n}" for n in c.retire]
    listed += [f"unclaimed: {_said(r)}" for r in unclaimed]
    return Acceptance(new, line, message(i.subject, listed), listed)


# ---------------------------------------------------------------------------------------------
# The news files since the last acceptance, and the command


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def news_since(repo: Path, since: str | None, folder: Path) -> list[news.Claim]:
    """The claims of the news files in `folder` added or changed between the commit the last
    acceptance judged and HEAD; every news file when nothing was accepted yet."""
    if not since:
        return [c for n in news.folder(folder) for c in n.claims]
    if _git(repo, "merge-base", "--is-ancestor", since, "HEAD").returncode != 0:
        raise Refused(
            [f"the last acceptance's commit {since[:12]} is not in this commit's history"]
        )
    try:
        rel = folder.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        raise Refused([f"--claims {folder} is not a folder of this repository"]) from None
    out = _git(repo, "diff", "--name-only", "--no-renames", "--diff-filter=AM", since, "HEAD")
    if out.returncode != 0:
        raise Refused([f"git diff {since[:12]} HEAD failed: {out.stderr.strip()[:120]}"])
    names = sorted(p.rsplit("/", 1)[-1] for p in out.stdout.split() if p.rsplit("/", 1)[0] == rel)
    picked = [news.load(folder / n) for n in names if news.NAME.fullmatch(n)]
    return [c for n in picked for c in n.claims]


def _collect() -> list[str]:
    from harness import gather

    return gather.collect(paths.REPO)[0]


def _head() -> str:
    return (paths.git("rev-parse", "HEAD") or "").strip()


def _subject() -> str:
    return (paths.git("log", "-1", "--format=%s", "HEAD") or "").strip()


def subject_of(record: dict, head_subject: str, version: str) -> str:
    """The acceptance's subject: the merge's own (its pull request's title and number), or, for
    the release pull request's record, whose head is dev's tip and so itself an acceptance, the
    version and both tiers."""
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    if _release_pr(meta):
        return f"the release pull request of {version} into main, both tiers"
    return head_subject


def _version() -> str:
    return news.package_version(paths.REPO) or "an unknown version"


def removed_news(repo: Path, since: str | None) -> list[news.Claim]:
    """The claims of every news file a commit after `since` removed (bump, or date for one merged
    after bump), each read at the parent of the commit that removed it, so a reason written at the
    merge still counts at the release; every removed one when `since` is None."""
    if since and _git(repo, "merge-base", "--is-ancestor", since, "HEAD").returncode != 0:
        raise Refused([f"the last release's commit {since[:12]} is not in this commit's history"])
    span = f"{since}..HEAD" if since else "HEAD"
    out = _git(
        repo, "log", "--diff-filter=D", "--no-renames", "--name-only", "--format=%x01%H", span,
        "--", news.CHANGES,
    )  # fmt: skip
    if out.returncode != 0:
        raise Refused([f"git log of the removed news files failed: {out.stderr.strip()[:120]}"])
    claims = []
    for chunk in out.stdout.split("\x01")[1:]:
        commit, *removed = chunk.split()
        for rel in (r for r in removed if news.is_news_path(r)):
            shown = _git(repo, "show", f"{commit}^:{rel}")
            if shown.returncode != 0:
                raise Refused(
                    [f"git show {commit[:12]}^:{rel} failed: {shown.stderr.strip()[:80]}"]
                )
            claims += news.claims_only(rel.rsplit("/", 1)[-1], shown.stdout)
    return claims


def release_claims(
    record: dict, repo: Path, history_lines: list[str], folder: Path | None = None
) -> list[news.Claim]:
    """The release's claims, for the release pull request's record alone: the release ledger's,
    the news files removed since the last release's acceptance (bump assembled and removed them
    before this run, and the runs after their merges judged the normal tier alone) and any news
    file still in `folder`."""
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    if not _release_pr(meta):
        return []
    found = news.ledger_claims(repo) + removed_news(repo, since_release(history_lines)[1])
    if folder is not None:
        found += [c for n in news.folder(folder) for c in n.claims]
    return found


def _dirty() -> str | None:
    return paths.dirty_path()


def _wasmtime() -> str:
    from harness import gather

    return gather.locked_version("wasmtime")


def _say(lines: list[str]) -> None:
    for line in lines:
        print(line)


def main(config) -> int:
    """`--accept-from`: refuse, or accept and write; the exit status pytest returns."""
    from harness import plugin

    given = tuple(o for o in REFUSED_OPTIONS if config.getoption(o))
    claims_dir = config.getoption("--claims")
    record_path = Path(config.getoption("--accept-from"))
    pdir = plugin.progress_dir(config)
    try:
        if not claims_dir:
            raise Refused(
                ["--accept-from takes its reasons from --claims <the news files' folder>"]
            )
        try:
            data = record_path.read_bytes()
            record = json.loads(data)
        except (OSError, ValueError) as e:
            raise Refused([f"{record_path}: not a readable record ({e})"]) from None
        accepted_text = (
            (pdir / "accepted.json").read_text() if (pdir / "accepted.json").is_file() else None
        )
        sealed = history.SEALED if pdir.resolve() == paths.PROGRESS.resolve() else None
        errors = history.errors(history.found_in(pdir), accepted_text, None, sealed)
        lines = history.lines(pdir)
        since = json.loads(lines[-1]).get("commit") if lines and not errors else None
        i = Inputs(
            record=record,
            accepted=json.loads(accepted_text) if accepted_text else None,
            history_lines=lines,
            history_errors=errors,
            goal_nodes=_collect(),
            head=_head(),
            subject=subject_of(record, _subject(), _version()),
            judge={"hash": paths.judge_hash(files := paths.judge_files()), "files": files},
            wasmtime=_wasmtime(),
            claims=(
                news_since(paths.REPO, since, Path(claims_dir).resolve())
                + release_claims(record, paths.REPO, lines, Path(claims_dir).resolve())
                if not errors
                else []
            ),
            dirty=_dirty(),
            options=given,
            at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            host=paths.sha256_bytes(socket.gethostname().encode())[:12],
            record_sha256=paths.sha256_bytes(data),
            budget=_budget(),
        )
        a = accept(i)
        late = _dirty()
        if late is not None:  # the tree as the acceptance is written, not only as it began
            raise Refused([f"a dirty tree as the acceptance is written: {late}"])
    except (Refused, news.NewsError) as e:
        reasons = e.reasons if isinstance(e, Refused) else [str(e)]
        _say([f"RED: {REFUSED}: {r}" for r in reasons])
        return 1
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "accepted.json").write_text(scoreboard.dumps(a.accepted))
    where = history.target(pdir, a.line)
    with where.open("a", encoding="utf-8", newline="\n") as f:
        f.write(a.line + "\n")
    out = plugin.latest_path(config).parent / MESSAGE_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(a.message, encoding="utf-8")
    _say([*(f"reason: {r}" for r in a.reasons), f"message: {out}"])
    _say([f"accepted: {where} line {json.loads(a.line)['n']}"])
    sys.stdout.flush()
    return 0
