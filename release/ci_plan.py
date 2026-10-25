"""Which jobs a run of the release workflow needs, from the paths it changes.

    uv run --no-project python -I release/ci_plan.py                      # in the workflow
    uv run --no-project python -I release/ci_plan.py --files - --event pull_request \\
        --ref refs/pull/7/merge --base-ref dev [--label ci:full] [--message TEXT] [--key-moved]

In the workflow it reads the event from the runner's variables (`GITHUB_EVENT_NAME`, `GITHUB_REF`,
`GITHUB_BASE_REF`, `GITHUB_REPOSITORY`) and the rest from env (`PLAN_HEAD`; on a pull request
`PLAN_BASE`, `PLAN_BODY`, its description, and `PLAN_HEAD_REF`, its branch; `PLAN_BEFORE` on a
push; `PLAN_LABELS` as JSON, `PLAN_RELEASE_TIER`, `PLAN_WEEKLY`; `GH_TOKEN`), finds the changed
paths, a pull request's commits and its review file with git, and on a pull request into dev that
adds documentation alone onto a green head finds that head's run with gh (a read of the Actions
API), which this run then re-uses. It writes one `name=value` line per output to `$GITHUB_OUTPUT`
(stdout without it), and a table to `$GITHUB_STEP_SUMMARY`, which names a run re-used. Every
later job gates on these outputs with `if:`, never with a workflow-level `paths:` filter, so a
skipped job reports success and the required check is always reported. The changed paths come
from git alone: no third-party changed-files action, since one of those was compromised to leak
the secrets of every workflow that ran it. Standard library only.
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
from collections.abc import Callable
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
# A news file, `NNN-<slug>.md` in the changes folder: the folder's README is not one.
NEWS = re.compile(r"context/changes/(\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*)\.md")
# A pull request's review file: a news file's NNN-<slug>, then an optional infix of lowercase words
# (`-step-4`), so one specification may land by several pull requests on one day, then the date.
REVIEW = re.compile(r"context/reviews/(\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*)-pr-(\d{4}-\d{2}-\d{2})\.md")


def review_of(name: str, stem: str) -> bool:
    """Whether a review file's name before `-pr-<date>` is the news file's stem, alone or followed
    by an infix of one or more lowercase words joined by hyphens."""
    return name == stem or bool(
        name.startswith(stem + "-")
        and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name[len(stem) + 1 :])
    )


REVIEWER = re.compile(r"^- \*\*Reviewer:\*\*(.*)$", re.M)
# The self-check's author line, `Author: …` with or without Markdown's emphasis.
AUTHOR = re.compile(r"^[\s>*_-]*author[*_]*\s*:[*_\s]*(.*)$", re.I | re.M)
SESSION = re.compile(r"https://claude\.ai/code/session_[A-Za-z0-9_-]+")
SUB_AGENT = "sub-agent of"
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


def docs_only(changed: list[str]) -> bool:
    """Every changed path is documentation, whatever the label or a commit line asks to run."""
    return all("docs" in classify(p) for p in changed)


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
    weekly: bool = False  # a dispatch's weekly input: the weekly run's shape

    @property
    def pull_request(self) -> bool:
        return self.name == "pull_request"

    @property
    def tag(self) -> bool:
        return self.name == "push" and self.ref.startswith("refs/tags/")


@dataclass(frozen=True)
class Commit:
    sha: str
    paths: tuple[str, ...]  # the paths it changes
    sessions: tuple[str, ...] = ()  # its Claude-Session trailers


@dataclass
class PullRequest:
    """What the review check reads of a pull request: its description (the self-check), its
    commits oldest first, and each review file's text at its head (absent when deleted)."""

    body: str
    commits: list[Commit]
    files: dict[str, str]


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
    accept: bool = False  # a merge into dev: the accept jobs follow a green gather
    weekly: bool = False  # the weekly run: an issue when it is red
    quiet: bool = False  # the acceptance push: every output false
    why: list[str] = field(default_factory=list)

    @property
    def judge(self) -> bool:
        """Any judge job, verify or the gather runs."""
        return not self.quiet and (self.full or not self.docs_only)


def decide(
    changed: list[str] | None,
    event: Event,
    key_moved: bool = False,
    reused: tuple[int, str] | None = None,
) -> Decision:
    """The outputs for one run. `changed` is None when the run has no change to read (a tag, a
    dispatch, a schedule, a push whose earlier tip is unknown): such a run is whole. `reused`: a
    pull request's green run whose head this one adds documentation alone to (its id and why),
    which this run re-uses: every output false, the refusals still read."""
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
    d.docs_only = changed is not None and docs_only(changed)
    if reused is not None and event.pull_request:
        d.quiet = True
        d.why.append(reused[1])
        return d
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
        d.full = d.accept = True
        d.why.append("a merge into dev: the merge-grade set, then the acceptance")
    elif event.name == "schedule" or (event.name == "workflow_dispatch" and event.weekly):
        d.full = d.rebuild = d.weekly = True
        d.tier = "release"
        d.why.append("the weekly run: the release tier and the rebuilds, an issue when red")
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


def into_dev(event: Event) -> bool:
    """A pull request into dev: the one held to a news file and a review file. The release pull
    request into main carries every released change's, and its review is the release's."""
    return event.pull_request and event.base_ref != "main"


def refusals(
    d: Decision, event: Event, changed: list[str] | None, pr: PullRequest | None = None
) -> list[str]:
    """What ci-status refuses on its own, whatever the judge says: accepted state written by a
    pull request; and a pull request into dev that is not documentation only and carries no news
    file, or (when its commits and description are read, `pr`) no review file that holds."""
    out = []
    if event.pull_request and d.progress:
        written = sorted(p for p in changed or () if "progress" in classify(p))
        out.append(
            "a pull request may not write accepted state; only the job that accepts writes "
            "context/progress/: " + ", ".join(written)
        )
    if into_dev(event) and changed is not None and not docs_only(changed) and not d.news:
        out.append(
            "a pull request that is not documentation only carries its news file, "
            "context/changes/NNN-<slug>.md: its CHANGELOG line, its package rows and its claims"
        )
    if into_dev(event) and changed is not None and not docs_only(changed) and pr is not None:
        out += review_refusals(changed, pr)
    return out


def _identity(text: str) -> str:
    """A name or a session as written, compared without case, emphasis or a closing stop."""
    return " ".join(text.strip().strip("`<>*_").rstrip(".;,").strip("`<>*_").split()).lower()


def _verdict(text: str) -> str:
    """The first line of the review's `## Verdict` section that is not blank."""
    lines = text.splitlines()
    for k, line in enumerate(lines):
        if line.strip() == "## Verdict":
            for after in lines[k + 1 :]:
                if after.startswith("## "):
                    break
                if after.strip():
                    return after.strip().lstrip("*_ ")
    return ""


def review_refusals(changed: list[str], pr: PullRequest) -> list[str]:
    """The review check: among the changed paths, a review file named after one of the pull
    request's news files, with or without an infix (the newest by date); no commit after the
    newest one that changed it touches a path that is not documentation only; its Reviewer:
    line is not empty and is not the author, who is the self-check's author line or any
    Claude-Session trailer of a code commit; a reviewer that names the author's session must be
    its fresh sub-agent, so says `sub-agent of <session>`; and its verdict begins "Lands". A
    process guard, not an identity guard: what it holds is that a session other than the
    author's signed a review after the last code."""
    stems = sorted({m[1] for p in changed if (m := NEWS.fullmatch(p))})
    found = sorted(
        (m[2], p)
        for p in changed
        if (m := REVIEW.fullmatch(p)) and any(review_of(m[1], stem) for stem in stems)
    )
    if not found:
        return [
            "a pull request that is not documentation only has no review file "
            "context/reviews/NNN-<slug>-pr-YYYY-MM-DD.md among its changed paths for its news "
            "file " + (", ".join(stems) or "(none)")
        ]
    path = found[-1][1]
    out = []
    last = max((k for k, c in enumerate(pr.commits) if path in c.paths), default=None)
    for c in pr.commits[last + 1 :] if last is not None else ():
        code = [p for p in c.paths if "docs" not in classify(p)]
        if code:
            out.append(
                f"{path}: the review is followed by {c.sha[:12]}, which changes {code[0]}; the "
                "review is committed after the last code, and read again after a fix"
            )
            break
    text = pr.files.get(path)
    if text is None:
        return [*out, f"{path}: the review file is not in the head's tree"]
    m = REVIEWER.search(text)
    reviewer = m[1].strip() if m else ""
    authors = {_identity(a) for a in AUTHOR.findall(pr.body or "") if a.strip()}
    sessions = {s for c in pr.commits if any("docs" not in classify(p) for p in c.paths)
                for s in c.sessions}  # fmt: skip
    sessions |= {u for a in AUTHOR.findall(pr.body or "") for u in SESSION.findall(a)}
    authors |= {_identity(s) for s in sessions}
    if not reviewer or reviewer.startswith("<"):
        out.append(f"{path}: its Reviewer: line is empty")
    elif _identity(reviewer) in authors:
        out.append(f"{path}: its Reviewer: line names the author ({reviewer})")
    else:
        for url in sorted(set(SESSION.findall(reviewer)) & sessions):
            if not re.search(rf"{SUB_AGENT}\s+<?`?{re.escape(url)}", reviewer):
                out.append(
                    f"{path}: its Reviewer: line names the author's session {url}; a fresh "
                    f"sub-agent of it says so ('a fresh {SUB_AGENT} {url}; not the author')"
                )
    if not _verdict(text).startswith("Lands"):
        out.append(f'{path}: the first line of its ## Verdict does not begin "Lands"')
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
        accept=_bool(d.accept),
        weekly=_bool(d.weekly),
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
# A push of documentation alone onto a green head re-uses that head's run

GATHER_JOB = "gather the shards' records"  # the gather's display name in a run's jobs
REQUIRED_JOB = "ci-status"
LOOKED_AT = 5  # runs whose head is behind this one by documentation alone, at most


def find_reusable(
    head: str,
    runs: list[dict],
    *,
    jobs_of: Callable[[int], dict[str, str] | None],
    is_ancestor: Callable[[str], bool],
    changed_since: Callable[[str], list[str]],
) -> tuple[int | None, str]:
    """The newest completed run of this pull request whose head is an ancestor of `head` by
    documentation alone and whose gather passed with every other job but ci-status green or
    skipped (ci-status waited for the review file); its id and why, or (None, "")."""
    looked = 0
    for run in runs:
        sha, run_id = str(run.get("headSha", "")), run.get("databaseId")
        if sha == head or run.get("status") != "completed" or not is_ancestor(sha):
            continue
        if not docs_only(changed_since(sha)):
            continue
        looked += 1
        if looked > LOOKED_AT:
            break
        jobs = jobs_of(int(run_id)) if isinstance(run_id, int) else None
        if not jobs or jobs.get(GATHER_JOB) != "success":
            continue
        if any(c not in ("success", "skipped") for n, c in jobs.items() if n != REQUIRED_JOB):
            continue
        return run_id, (
            f"re-uses run {run_id}, green on {sha[:12]}: every path changed since is documentation"
        )
    return None, ""


def _gh(environ, *args: str) -> object | None:
    """One read of GitHub's API through gh, as JSON; None without a token or on any failure."""
    if not environ.get("GH_TOKEN"):
        return None
    try:
        r = subprocess.run(
            ["gh", *args, "--repo", environ.get("GITHUB_REPOSITORY", "")],
            capture_output=True,
            text=True,
            env={**os.environ, **environ},
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def green_runs(environ, head_ref: str) -> list[dict] | None:
    """This pull request's newest runs of the release workflow, newest first (one API call)."""
    if not head_ref:
        return None
    fields = "databaseId,headSha,status,conclusion"
    got = _gh(environ, "run", "list", "--workflow", "release.yml", "--branch", head_ref,
              "--event", "pull_request", "--limit", "20", "--json", fields)  # fmt: skip
    return got if isinstance(got, list) else None


def run_jobs(environ, run_id: int) -> dict[str, str] | None:
    """A run's jobs by name, each with its conclusion (one API call)."""
    got = _gh(environ, "run", "view", str(run_id), "--json", "jobs")
    if not isinstance(got, dict) or not isinstance(got.get("jobs"), list):
        return None
    return {str(j.get("name")): str(j.get("conclusion")) for j in got["jobs"]}


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


def _is_ancestor(sha: str, head: str) -> bool:
    r = subprocess.run(
        ["git", "-C", str(REPO), "merge-base", "--is-ancestor", sha, head], capture_output=True
    )
    return r.returncode == 0


def _diff(a: str, b: str) -> list[str]:
    # --no-renames: a moved file counts at both of its paths.
    return [p for p in _git("diff", "--name-only", "--no-renames", a, b).splitlines() if p]


def read_pull_request(
    repo: Path, base: str, head: str, body: str, changed: list[str]
) -> PullRequest:
    """A pull request's commits from `base` (its merge base) to `head`, oldest first, each with
    the paths it changes and its Claude-Session trailers, and the text at the head of each review
    file among the changed paths."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
        ).stdout

    commits = []
    for sha in git("rev-list", "--reverse", f"{base}..{head}").split():
        names = git("diff-tree", "--no-commit-id", "--name-only", "-r", "--no-renames", sha)
        trailers = git("log", "-1", "--format=%(trailers:key=Claude-Session,valueonly)", sha)
        commits.append(
            Commit(sha, tuple(n for n in names.splitlines() if n), tuple(trailers.split()))
        )
    files = {}
    for path in changed:
        if REVIEW.fullmatch(path):
            r = subprocess.run(
                ["git", "-C", str(repo), "show", f"{head}:{path}"], capture_output=True, text=True
            )
            if r.returncode == 0:
                files[path] = r.stdout
    return PullRequest(body, commits, files)


def from_runner(
    environ,
) -> tuple[Event, list[str] | None, bool, PullRequest | None, tuple[int, str] | None]:
    """The event, the changed paths, whether the key moved and, on a pull request, its commits
    and description and the green run it re-uses, if any, as the workflow's run gives them."""
    labels = tuple(json.loads(environ.get("PLAN_LABELS") or "[]") or ())
    event = Event(
        environ.get("GITHUB_EVENT_NAME", ""),
        environ.get("GITHUB_REF", ""),
        environ.get("GITHUB_BASE_REF", ""),
        labels,
        (),
        environ.get("PLAN_RELEASE_TIER") == "true",
        environ.get("PLAN_WEEKLY") == "true",
    )
    head = environ.get("PLAN_HEAD") or "HEAD"
    changed: list[str] | None = None
    moved = False
    pr = None
    reused = None
    if event.pull_request and _is_commit(environ.get("PLAN_BASE", "")):
        base = _git("merge-base", environ["PLAN_BASE"], head).strip()
        changed = _diff(base, head)
        messages = _git("log", "--format=%B%x00", f"{base}..{head}").split("\0")
        event = Event(event.name, event.ref, event.base_ref, labels, tuple(messages))
        moved = key_moved(REPO, base)
        pr = read_pull_request(REPO, base, head, environ.get("PLAN_BODY", ""), changed)
        runs = (
            green_runs(environ, environ.get("PLAN_HEAD_REF", ""))
            if into_dev(event) and not docs_only(changed)
            else None
        )
        if runs:
            run_id, why = find_reusable(
                _git("rev-parse", head).strip(),
                runs,
                jobs_of=lambda run_id: run_jobs(environ, run_id),
                is_ancestor=lambda sha: _is_ancestor(sha, head),
                changed_since=lambda sha: _diff(sha, head),
            )
            reused = (run_id, why) if run_id is not None else None
    elif event.name == "push" and not event.tag and _is_commit(environ.get("PLAN_BEFORE", "")):
        changed = _diff(environ["PLAN_BEFORE"], head)
    return event, changed, moved, pr, reused


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
        pr = None  # the review check reads the pull request's commits, which a list does not give
        reused = None
    else:
        event, changed, moved, pr, reused = from_runner(os.environ)
    d = decide(changed, event, moved, reused)
    sel = select(d, load_shards())
    refused = refusals(d, event, changed, pr)
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
