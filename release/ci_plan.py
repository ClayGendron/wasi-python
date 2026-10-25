"""Which jobs a run of the release workflow needs, from the paths it changes.

    uv run --no-project python -I release/ci_plan.py                      # in the workflow
    uv run --no-project python -I release/ci_plan.py --files - --event pull_request \\
        --ref refs/pull/7/merge --base-ref dev [--label ci:full] [--message TEXT] [--key-moved]

In the workflow it reads the event from the runner's variables (`GITHUB_EVENT_NAME`, `GITHUB_REF`,
`GITHUB_BASE_REF`) and the rest from env (`PLAN_HEAD`, `PLAN_BASE` on a pull request, `PLAN_BEFORE`
on a push, `PLAN_LABELS` as JSON, `PLAN_RELEASE_TIER`), finds the changed paths with git, and
writes one `name=value` line per output to `$GITHUB_OUTPUT` (stdout without it), and a table to
`$GITHUB_STEP_SUMMARY`. Every later job gates on these outputs with `if:`, never with a
workflow-level `paths:` filter, so a skipped job reports success and the required check is always
reported. The changed paths come from git alone: no third-party changed-files action, since one of
those was compromised to leak the secrets of every workflow that ran it. Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHARD_PLAN = REPO / "tests" / "release_shards.toml"
# The outputs a path can set, in the table's order.
FLAGS = ("set", "runner", "harness", "upstream", "workflow", "progress", "news")
# The folders whose paths set no output of their own: not docs_only, so the own shards run.
OWN_ONLY = ("tests/", "fixtures/")
# Each system's runner, as the judge jobs and verify run on it.
RUNNER = {"macos": "macos-15", "linux": "ubuntu-24.04", "windows": "windows-2025"}
VERIFY_RUNNERS = ("ubuntu-24.04", "windows-2025", "macos-15")
OWN_SYSTEMS = ("macos", "linux", "windows")
# The two workflows whose top-level env the set's key holds.
WORKFLOWS = (".github/workflows/release.yml", ".github/workflows/set-cache.yml")
FULL_LABEL = "ci:full"
FULL_LINE = "citest:full"
ACCEPTED = "context/progress/accepted.json"
HISTORY_VOLUME = re.compile(r"context/progress/history(-\d{5,})?\.jsonl")
NEWS = re.compile(r"context/changes/[^/]+\.md")
DOCS_FILES = ("README.md", "CHANGELOG.md", "AGENTS.md", "SECURITY.md", "mkdocs.yml", ".gitignore")
SET_FILES = ("downloads/SHA256SUMS", "release/set_key.py", "release/build-constraints.txt")
HARNESS_FILES = (
    "tests/conftest.py",
    "tests/release_shards.toml",
    "tests/known_gaps.toml",
    "context/embedders.txt",
    "context/release-tier-claims.toml",
    ".gitattributes",
)


def classify(path: str) -> frozenset[str]:
    """The outputs one changed path sets, with `docs` when it may be part of a docs_only change.
    An empty set is a path in no row: it runs the own shards and nothing more."""
    out = set()
    if path in SET_FILES or path.startswith(("scripts/", "recipes/", "tests/harness/constructors")):
        out.add("set")
    if path.startswith("src/") or path in ("pyproject.toml", "uv.lock"):
        out.add("runner")
    if path.startswith(("tests/harness/", "context/upstream/")) or path in HARNESS_FILES:
        out.add("harness")
    if path.startswith("tests/upstream/") or path == "tests/checks/test_v1_3_upstream_suites.py":
        out.add("upstream")
    if path.startswith((".github/", "release/")):
        out.add("workflow")
    if path == ACCEPTED or HISTORY_VOLUME.fullmatch(path):
        out.add("progress")  # the accepted state alone: the folder's README is a document
    if NEWS.fullmatch(path):
        out.add("news")
    if not out and (
        path.startswith(("docs/", ".claude/", "context/", "LICENSE")) or path in DOCS_FILES
    ):
        out.add("docs")
    return frozenset(out)


def is_acceptance(changed: list[str]) -> bool:
    """The acceptance commit's change: accepted.json and the newest history volume, exactly."""
    rest = sorted(set(changed) - {ACCEPTED})
    return ACCEPTED in changed and len(rest) == 1 and bool(HISTORY_VOLUME.fullmatch(rest[0]))


@dataclass(frozen=True)
class Event:
    name: str  # GITHUB_EVENT_NAME
    ref: str = ""  # GITHUB_REF
    base_ref: str = ""  # GITHUB_BASE_REF: a pull request's base branch
    labels: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()  # the pull request's commit messages
    release_tier: bool = False  # a dispatch's release-tier input

    @property
    def pull_request(self) -> bool:
        return self.name == "pull_request"

    @property
    def tag(self) -> bool:
        return self.name == "push" and self.ref.startswith("refs/tags/")


@dataclass
class Decision:
    set: bool = False
    runner: bool = False
    harness: bool = False
    upstream: bool = False
    workflow: bool = False
    progress: bool = False
    news: bool = False
    docs_only: bool = False
    full: bool = False  # the merge-grade set: every normal-tier shard on its systems, build too
    rebuild: bool = False  # the release shape: the macOS build, both rebuilds and same-bytes
    tier: str = "normal"
    quiet: bool = False  # the acceptance push: every output false
    why: list[str] = field(default_factory=list)

    @property
    def judge(self) -> bool:
        """Any judge job, verify or the gather runs."""
        return not self.quiet and (self.full or not self.docs_only)


def decide(changed: list[str] | None, event: Event, key_moved: bool = False) -> Decision:
    """The outputs for one run. `changed` is None when the run has no change to read (a tag, a
    dispatch, a schedule, a push whose earlier tip is unknown): such a run is whole."""
    d = Decision()
    if event.name == "push" and not event.tag and changed is not None and is_acceptance(changed):
        d.quiet = True
        d.why.append("the acceptance commit: accepted.json and its history volume alone")
        return d
    flags: set[str] = set()
    for path in changed or ():
        flags |= classify(path)
    for name in FLAGS:
        setattr(d, name, name in flags)
    d.set = d.set or key_moved
    if key_moved:
        d.why.append("the set's key moves between the merge base and the head")
    d.docs_only = changed is not None and all("docs" in classify(p) for p in changed)
    lines = {line.strip() for m in event.messages for line in m.splitlines()}
    if event.pull_request and event.base_ref == "main":
        d.full = d.rebuild = True
        d.tier = "release"
        d.why.append("a release pull request into main: the whole workflow")
    elif event.pull_request:
        if changed is None:  # fail closed: a change that cannot be read is judged whole
            d.full = True
            d.why.append("the pull request's base could not be read: the run is whole")
        if FULL_LABEL in event.labels:
            d.full = True
            d.why.append(f"the label {FULL_LABEL}")
        if FULL_LINE in lines:
            d.full = True
            d.why.append(f"a commit line {FULL_LINE}")
        if d.workflow:
            d.full = True
            d.why.append("the workflow or release/ changed")
    elif event.tag:
        d.full = d.rebuild = True
        d.tier = "release"
        d.why.append("a pushed tag: build, judge both tiers, attest, publish")
    elif event.name == "push":
        d.full = True
        d.why.append("a merge into dev: the merge-grade set")
    elif event.name == "schedule":
        d.full = d.rebuild = True
        d.tier = "release"
        d.why.append("the weekly run: the release tier and the rebuilds")
    else:  # workflow_dispatch, or an event the table does not name: whole
        d.full = d.rebuild = True
        if event.release_tier or event.ref == "refs/heads/main":
            d.tier = "release"
        d.why.append(f"a {event.name}: the whole workflow")
    if d.full:
        d.docs_only = False
    return d


@dataclass(frozen=True)
class Shard:
    name: str
    kind: str  # build, release, upstream (by groups) or own
    systems: tuple[str, ...]


def load_shards(path: Path = SHARD_PLAN) -> dict[str, Shard]:
    """The shard plan, in the file's order, each shard with its kind."""
    out: dict[str, Shard] = {}
    for name, s in tomllib.loads(path.read_text(encoding="utf-8")).get("shard", {}).items():
        systems = tuple(s.get("systems", ()))
        if systems == ("build",):
            kind = "build"
        elif systems == ("release",):
            kind = "release"
        elif s.get("groups"):
            kind = "upstream"
        else:
            kind = "own"
        out[name] = Shard(name, kind, systems)
    return out


def select(d: Decision, plan: dict[str, Shard]) -> dict:
    """The shards each judge job runs, the build shard, verify's runners, and every selected
    (system, shard) pair as `system/shard`, which the gather reads as PLAN."""
    sel: dict = {s: [] for s in (*OWN_SYSTEMS, "release")}
    sel.update(build=False, verify=[])
    if d.judge:
        for system in OWN_SYSTEMS:
            for s in plan.values():
                if system not in s.systems or s.kind not in ("own", "upstream"):
                    continue
                if d.full:
                    take = True
                elif s.kind == "own":
                    take = system != "macos" or d.runner or d.set or d.harness
                else:  # the upstream groups: on Linux, when something they read changed
                    take = system == "linux" and (d.set or d.upstream or d.harness)
                if take:
                    sel[system].append(s.name)
        if d.tier == "release":
            sel["release"] = [s.name for s in plan.values() if s.kind == "release"]
        sel["build"] = d.full and any(s.kind == "build" for s in plan.values())
        sel["verify"] = list(VERIFY_RUNNERS) if d.full else [RUNNER["linux"]]
    sel["selected"] = [f"{s}/{n}" for s in (*OWN_SYSTEMS, "release") for n in sel[s]]
    sel["selected"] += ["build/build"] if sel["build"] else []
    return sel


def refusals(d: Decision, event: Event, changed: list[str] | None) -> list[str]:
    """What ci-status refuses on its own, whatever the judge says."""
    out = []
    if event.pull_request and d.progress:
        written = sorted(p for p in changed or () if "progress" in classify(p))
        out.append(
            "a pull request may not write accepted state; only the job that accepts writes "
            "context/progress/: " + ", ".join(written)
        )
    return out


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _json(value) -> str:
    return json.dumps(value, separators=(",", ":"))


def outputs(d: Decision, sel: dict, refused: list[str]) -> dict[str, str]:
    """Every output as the workflow reads it: one line each."""
    out = {name: _bool(getattr(d, name) and not d.quiet) for name in FLAGS}
    out.update(
        docs_only=_bool(d.docs_only),
        full=_bool(d.full),
        rebuild=_bool(d.rebuild),
        judge=_bool(d.judge),
        tier=d.tier,
        build=_bool(sel["build"]),
        verify=_json(sel["verify"]),
        selected=_json(sel["selected"]),
        refusals=_json(refused),
    )
    for system in (*OWN_SYSTEMS, "release"):
        out[system] = _json(sel[system])
    return out


# ---------------------------------------------------------------------------------------------
# The key at the head and at the merge base


def top_env(text: str) -> dict[str, str]:
    """A workflow's top-level `env:`, each value as written, quotes and comments dropped."""
    out: dict[str, str] = {}
    inside = False
    for line in text.splitlines():
        if line.startswith("env:"):
            inside = True
            continue
        if not inside or line.lstrip().startswith("#"):
            continue
        m = re.fullmatch(r"  ([A-Za-z0-9_]+):\s*(.*?)\s*", re.sub(r"\s+#\s.*$", "", line))
        if m:
            out[m[1]] = m[2].strip("\"'")
        elif line and not line.startswith(" "):
            break
    return out


def _set_key(repo: Path):
    spec = importlib.util.spec_from_file_location(
        "ci_plan_set_key", repo / "release" / "set_key.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _key(sk, tree: Path) -> str:
    """The set's key of one tree, under the env its own workflows set; every workflow's keyed env
    is held, so a value set-cache.yml alone changes moves it too."""
    envs = []
    for rel in WORKFLOWS:
        p = tree / rel
        env = top_env(p.read_text(encoding="utf-8")) if p.is_file() else {}
        envs.append(json.dumps({n: env.get(n) for n in sk.ENV}, sort_keys=True))
    try:
        key = sk.key(tree, top_env((tree / WORKFLOWS[0]).read_text(encoding="utf-8")))
    except (SystemExit, OSError) as e:  # a tree the key cannot be made of: never the same key
        key = f"unkeyable {e} {tree}"
    return hashlib.sha256("\n".join([key, *envs]).encode()).hexdigest()


def key_moved(repo: Path, base: str) -> bool:
    """Whether the set's key at the checkout differs from the key at `base`, each read with this
    checkout's release/set_key.py from its own tree."""
    sk = _set_key(repo)
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "base"
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--quiet", "--detach", str(tree), base],
            check=True,
            capture_output=True,
        )
        try:
            return _key(sk, repo) != _key(sk, tree)
        finally:
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "remove", "--force", str(tree)],
                capture_output=True,
            )


# ---------------------------------------------------------------------------------------------
# The command line


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True
    ).stdout


def _is_commit(sha: str) -> bool:
    if not sha or set(sha) == {"0"}:
        return False
    r = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "-e", f"{sha}^{{commit}}"], capture_output=True
    )
    return r.returncode == 0


def _diff(a: str, b: str) -> list[str]:
    # --no-renames: a moved file counts at both of its paths.
    return [p for p in _git("diff", "--name-only", "--no-renames", a, b).splitlines() if p]


def from_runner(environ) -> tuple[Event, list[str] | None, bool]:
    """The event, the changed paths and whether the key moved, as the workflow's run gives them."""
    labels = tuple(json.loads(environ.get("PLAN_LABELS") or "[]") or ())
    event = Event(
        environ.get("GITHUB_EVENT_NAME", ""),
        environ.get("GITHUB_REF", ""),
        environ.get("GITHUB_BASE_REF", ""),
        labels,
        (),
        environ.get("PLAN_RELEASE_TIER") == "true",
    )
    head = environ.get("PLAN_HEAD") or "HEAD"
    changed: list[str] | None = None
    moved = False
    if event.pull_request and _is_commit(environ.get("PLAN_BASE", "")):
        base = _git("merge-base", environ["PLAN_BASE"], head).strip()
        changed = _diff(base, head)
        messages = _git("log", "--format=%B%x00", f"{base}..{head}").split("\0")
        event = Event(event.name, event.ref, event.base_ref, labels, tuple(messages))
        moved = key_moved(REPO, base)
    elif event.name == "push" and not event.tag and _is_commit(environ.get("PLAN_BEFORE", "")):
        changed = _diff(environ["PLAN_BEFORE"], head)
    return event, changed, moved


def summary(d: Decision, sel: dict, refused: list[str], changed: list[str] | None) -> str:
    rows = [f"| {name} | {getattr(d, name)} |" for name in (*FLAGS, "docs_only", "full", "rebuild")]
    lines = ["### The plan", "", "| output | value |", "|---|---|", *rows, f"| tier | {d.tier} |"]
    lines += ["", f"Why: {'; '.join(d.why) or 'the changed paths'}."]
    count = "not read: the run is whole" if changed is None else len(changed)
    lines += [f"Changed paths: {count}."]
    lines += [f"Selected: {len(sel['selected'])} (system, shard) pairs; verify on {sel['verify']}."]
    lines += [f"Refused: {r}" for r in refused]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="ci_plan.py")
    ap.add_argument("--files", help="the changed paths, one per line; - reads stdin")
    ap.add_argument("--event", default="pull_request")
    ap.add_argument("--ref", default="")
    ap.add_argument("--base-ref", default="")
    ap.add_argument("--label", action="append", default=[])
    ap.add_argument("--message", action="append", default=[])
    ap.add_argument("--release-tier", action="store_true")
    ap.add_argument("--key-moved", action="store_true")
    a = ap.parse_args(argv)
    if a.files is not None:
        text = sys.stdin.read() if a.files == "-" else Path(a.files).read_text(encoding="utf-8")
        changed: list[str] | None = [p.strip() for p in text.splitlines() if p.strip()]
        event = Event(a.event, a.ref, a.base_ref, tuple(a.label), tuple(a.message), a.release_tier)
        moved = a.key_moved
    else:
        event, changed, moved = from_runner(os.environ)
    d = decide(changed, event, moved)
    sel = select(d, load_shards())
    refused = refusals(d, event, changed)
    text = "".join(f"{k}={v}\n" for k, v in outputs(d, sel, refused).items())
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    report = summary(d, sel, refused, changed)
    sys.stderr.write(report)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
