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
  `fewer`, a changed judge file by `judge`, a tier move by `moved`; an unclaimed row refuses, named;
- a history that does not replay, or breaks its chain or its volume rule, is refused.

It also refuses a record of any event but a push to dev or a pull request into main, and one
whose set was neither built in its run nor reused by its key. Every refusal is named at once.

The record is read as the darwin run it contains, as the gather and sameness read it: each check
as the record that ran it saw it, darwin first. A check darwin ran is applied with darwin's
metrics, keyed `darwin-arm64` though the job runs on Linux. A check only another system ran (the
upstream groups run on Linux alone) keeps darwin's accepted fuel, since fuel on another system is
not ratcheted, and takes the record's counts (`passes`, `bytes`), which the gather holds equal on
every system, under the same key, where the gather reads them. The history line names the systems
whose probe passed, so the `three systems` need is met by the record.
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

from harness import history, news, paths, scoreboard

DARWIN = "darwin-arm64"  # the platform the ratchet keys darwin's metrics by
COUNTS = ("passes", "bytes")  # metrics the gather holds equal on every system
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


@dataclass
class Acceptance:
    accepted: dict
    line: str
    message: str
    reasons: list[str] = field(default_factory=list)


def _merged(record: dict) -> bool:
    meta = record.get("meta")
    return isinstance(meta, dict) and "records" in meta and isinstance(record.get("runs"), dict)


def _event_refusal(meta: dict) -> str | None:
    push_to_dev = (
        meta.get("event") == "push" and meta.get("ref") == "refs/heads/dev" and not meta.get("tag")
    )
    release_pr = meta.get("event") == "pull_request" and meta.get("base_ref") == "main"
    if push_to_dev or release_pr:
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
    kept = {k: v for k, v in acc.items() if k != "wasmtime" and k not in COUNTS}
    if acc.get("wasmtime") != i.wasmtime:
        kept.pop("fuel", None)  # darwin's fuel of another engine is no measurement of this one
    kept.update({k: v for k, v in (c.get("metrics") or {}).items() if k in COUNTS})
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


def claimed(ratchet: scoreboard.Ratchet, claims: list[news.Claim], judged: bool) -> Claimed:
    """Each row the acceptance needs a reason for, with the claim that gives it, or a refusal
    naming the row. `judged`: there is an accepted judge to have changed."""
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
    for kind, rows, into, what in (
        ("grows", ratchet.growth, c.growth, "a growth"),
        ("passes", ratchet.fewer, c.fewer, "a pass count that fell"),
    ):
        for row in rows:
            why = news.reason(claims, kind, _node(row))
            if why:
                into.append(why)
            else:
                c.refusals.append(f"{what}, unclaimed: {row}")
    for f in ratchet.judge_changed if judged else ():
        why = news.reason(claims, "judge", f)
        if why:
            spec, text = why.split(": ", 1)
            c.judge.append(f"{spec}: {f}: {text}")
        else:
            c.refusals.append(f"the judge changed, unclaimed: {f}")
    for node in ratchet.moved:
        why = news.reason(claims, "moved", node)
        if why:
            c.moved.append(why)
        else:
            c.refusals.append(f"a check moved between tiers, unclaimed: {node}")
    return c


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
    if c.refusals:
        raise Refused(c.refusals)
    runs = i.record["runs"].values()
    platforms = sorted({str(x.get("platform")) for x in runs if x.get("probe") == "pass"})
    reasons = {
        "judge": _joined(c.judge),
        "growth": _joined(c.growth),
        "fewer": _joined(c.fewer),
        "tier move": _joined(c.moved),
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
            extra={"source": "ci", "record": i.record_sha256, "platforms": platforms},
        )
    except scoreboard.AcceptRefused as e:
        raise Refused([str(e)]) from None
    listed = [f"{k}: {v}" for k, v in reasons.items() if v]
    listed += [f"retired: {n}" for n in c.retire]
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
    if meta.get("event") == "pull_request" and meta.get("base_ref") == "main":
        return f"the release pull request of {version} into main, both tiers"
    return head_subject


def _version() -> str:
    return news.package_version(paths.REPO) or "an unknown version"


def release_claims(record: dict, repo: Path) -> list[news.Claim]:
    """The release-tier ledger's claims, for the release pull request's record alone: the news
    files that claimed a release-tier row were assembled and removed by bump before it, and the
    run after each merge judged the normal tier alone, so the ledger carries their reasons."""
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    if meta.get("event") == "pull_request" and meta.get("base_ref") == "main":
        return news.ledger_claims(repo)
    return []


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
                + release_claims(record, paths.REPO)
                if not errors
                else []
            ),
            dirty=_dirty(),
            options=given,
            at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            host=paths.sha256_bytes(socket.gethostname().encode())[:12],
            record_sha256=paths.sha256_bytes(data),
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
