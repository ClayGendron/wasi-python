# 029 — The landing lane is guarded

- **Status:** drafted 2026-10-17; revised against its pre-build review
  (`../reviews/029-the-landing-lane-is-guarded-spec-2026-10-17.md`), whose confirmation passed it
  for build with four conditions (A to D), written in.
- **Owner:** Clay Gendron
- **Kind:** judge additions and changes (`tests/checks/test_rules.py`, `tests/harness/plugin.py`,
  `tests/harness/paths.py`'s stray-conftest walk, `run_meta`'s `dirty`), the scoreboard's
  announcements, `context/progress/README.md`.
- **Depends on:** 002 (the progress harness: the ratchet, `--accept`, the judge hash).
- **Research it stands on:** `../research/2026-10-17-parallel-work-without-lowering-the-bar.md`
  (part 6, its four rules, and the experiment behind them), adopted by the owner on 2026-10-17
  (constitution §4.14, §5.7; `../decisions.md`, decision E). Parallel builders do not run until
  this lands.

## The problem

The constitution now lets specifications be built in parallel worktrees and requires that only
the landing lane accepts and that main moves only by fast-forward. Today nothing enforces either.
The memo's experiment accepted in two worktrees at once with nothing stopping it; a rebase can
carry an acceptance onto a commit it never judged; and a worktree under the repository (Claude
Code's default `.claude/worktrees/`) changes the main tree's judge hash.

## Decisions

1. **An acceptance sits on the commit it judged, and carries nothing else.** A rules check reads
   committed history only: `<c>` is the newest commit reachable from `HEAD` that changed
   `context/progress/history.jsonl`; its newest line is read with `git show
   <c>:context/progress/history.jsonl`; and the check requires (a) that line's commit equal `<c>`'s
   **first** parent, and (b) that `<c>` change exactly `context/progress/accepted.json` and
   `context/progress/history.jsonl` and nothing else. An acceptance appended but not yet committed
   does not move `<c>`, so the lane is never red between accepting and committing. Older history
   is not re-judged (23 of 31 past acceptance commits also carried code; the newest, `cb0c5a6`,
   carries only the two files; the review's `rule1.py`).
2. **`dirty` means a change the judge could see, and an acceptance refuses it.** `run_meta`
   records `dirty` as true when `git status --porcelain` shows any tracked change anywhere
   (`context/progress/` excepted) or any untracked file under the judge's inputs (`src/`,
   `tests/`, `scripts/`, `recipes/`, `pyproject.toml`, `uv.lock`); an untracked `.idea/` no longer
   counts (all 34 history lines say `true` today; condition D). `--accept` on a dirty tree is
   refused when it is made, in `pytest_configure`, with one line naming the first changed path,
   exit 1, so a dirty acceptance is never written and main can never be red-locked by one
   (condition B). Rule 1 also requires the newest committed line's `dirty` to be `false` from the
   first acceptance after this lands.
3. **Main is linear.** A rules check: `git rev-list --merges HEAD` is empty.
4. **Only the lane accepts.** The plugin refuses `--accept` alone (`--accept-judge`,
   `--accept-growth` and `--partial` write nothing without it, so they stay allowed) when the run
   is in a linked worktree (`git rev-parse --absolute-git-dir` differs from `git rev-parse
   --path-format=absolute --git-common-dir`, git 2.31 or later) **and** the progress folder it
   would write resolves to a `context/progress` folder of this repository (the worktree's own,
   the default, or the main tree's, reached by `--progress-dir`), compared with
   `os.path.samefile` against `context/progress` of every worktree `git worktree list
   --porcelain` names, so case and links cannot slip past (condition A). Any other `--progress-dir`, as
   the plugin's own self-tests use, is allowed: it writes no accepted state, and the scoreboard
   already announces it. The refusal happens in `pytest_configure`, before collection, with one
   line `accept: only the landing lane accepts, in the main tree (constitution §5.7); this is a
   linked worktree`, exit 1 like every acceptance refusal today. When both this and
   `PYTEST_ADDOPTS`'s refusal apply, this one is reported. A plain clone and a submodule are not
   linked worktrees; a clone is out of scope (rule 1 still catches an acceptance moved from one).
5. **A worktree inside the repository is not judge input, and is named.** The skip applies only
   to `paths.judge_files()`'s stray-conftest `os.walk` below the root (never the walk over
   `JUDGE_PATHS`, so a nested repository under `tests/` stays in the hash): a directory holding a
   `.git` entry (`os.path.lexists`, so a `.git` file or broken link counts) is not descended. And
   the scoreboard announces each worktree below the root found by `git worktree list
   --porcelain` (one line, `note: a worktree inside the repository: <path> (constitution §4.14
   puts them outside)`), since §4.14 places them outside; the hash stays stable either way.
6. **The lane's acceptance commit, and recovery.** After `--accept` the lane commits with
   `git commit -- context/progress/accepted.json context/progress/history.jsonl` and nothing
   else. If an acceptance commit carries anything more (as `380f70d` did, a doc file), rule 1 is
   red until the lane accepts again on a clean tree and commits only the two files: the newest
   acceptance is what rule 1 reads, so one correct acceptance restores it; history is never
   rewritten (condition C). `context/progress/README.md` says this in two lines.
7. **Where git or its history is absent.** Rules 1 and 3 need `git history`: met when `git
   rev-parse --is-shallow-repository` prints `false`; otherwise they are blocked, not failed (a
   shallow clone's root commit has no parent to compare; the release builds with
   `fetch-depth: 0`). Where git is absent, `--accept` proceeds as today.

## Intent

The parallel-work rules of §4.14 and §5.7 are mechanical, not a matter of care.

## Design

```
tests/checks/test_rules.py      rules 1 and 3 (Decisions 1, 3)
tests/harness/plugin.py         the accept refusal (Decision 4); run_meta's dirty (Decision 2)
tests/harness/paths.py          the stray-conftest walk (Decision 5); the scoreboard's note
tests/unit/test_landing_lane.py the checks below, in temporary repositories
context/progress/README.md      the lane, in two lines
```

## Scope

In: the four rules. Out: automating the lane itself (it stays the coordinator's procedure in
`AGENTS.md`); a merge queue; claim files.

## Acceptance criteria

Each check builds a temporary git repository (and worktrees of it) with `git` only; nothing
measures time.

1. Rule 1 passes for an acceptance commit whose first parent is the named commit and which
   changes only the two files; fails, naming both commits, for one carried across a rebase; fails
   for one that also changes a code file; passes while a new acceptance is appended but
   uncommitted; is blocked in a shallow clone. The first failing cases are seen failing first.
2. `dirty` is `false` with only untracked files present, `true` with a tracked change.
3. Rule 3 fails on a repository with a merge commit and passes on a linear one and on this
   repository.
4. In a linked worktree of a temporary clone: `--accept` with the default progress folder exits 1
   with the line before collecting and writes nothing; `--accept` with a `--progress-dir` outside
   the repository proceeds; `--partial` alone proceeds. `tests/unit/test_plugin.py` and
   `tests/unit/test_checks_wiring.py` pass when run from that worktree (the review's
   implementation (a) failed 16 of 33 there).
5. A worktree under the temporary repository's `.claude/worktrees/` leaves the judge hash
   unchanged and is named by the scoreboard's note; a nested repository under `tests/` stays in
   the hash. The first is seen failing first.
6. `uv run pytest` green with `--accept-judge`; lost 0; grew 0.

## Landing notes

Not built.
