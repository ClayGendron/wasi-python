# 029 — The landing lane is guarded

- **Status:** drafted 2026-10-17.
- **Owner:** Clay Gendron
- **Kind:** judge additions (`tests/checks/test_rules.py`, `tests/harness/`, the judge plugin
  and `tests/checks/conftest.py`'s input walk), `context/progress/README.md`.
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

1. **An acceptance sits on the commit it judged.** A rules check: for the newest commit that
   changed `context/progress/history.jsonl`, its parent is the commit that the newest history
   line names. Older history is not re-judged: 29 of 31 past acceptances hold it and the two that
   do not predate the rule (memo, `01_accept_baselines.txt`); the check starts from the newest.
2. **Main is linear.** A rules check: no merge commit is reachable from `HEAD`
   (`git rev-list --merges HEAD` is empty; today it is, EXECUTED by the memo).
3. **`--accept` refuses outside the main tree.** When `git rev-parse --git-dir` differs from
   `git rev-parse --git-common-dir`, the plugin refuses `--accept`, `--accept-judge`,
   `--accept-growth` and `--partial` with one line: `accept: only the landing lane accepts, in
   the main tree (constitution §5.7); this is a linked worktree`, exit 2, and writes nothing
   under `context/progress/`. The judge itself still runs there.
4. **A worktree inside the repository is not judge input.** The walk that hashes the judge's
   inputs skips any directory below the repository's root that holds a `.git` entry of its own
   (a linked worktree or a nested repository), so `.claude/worktrees/` cannot change the main
   tree's judge hash.
5. **Where git is absent** (a source tarball without `.git`), rules 1 to 3 skip with `needs:
   git`, as other git-reading checks do.

## Intent

The parallel-work rules of §4.14 and §5.7 are mechanical, not a matter of care.

## Design

```
tests/checks/test_rules.py      rules 1 and 2
tests/harness/plugin.py         rule 3 (the accept refusal)
tests/checks/conftest.py, tests/harness/paths.py   rule 4 (the input walk)
tests/unit/test_landing_lane.py the checks below, in temporary repositories
context/progress/README.md      the lane, in two lines
```

## Scope

In: the four rules. Out: automating the lane itself (it stays the coordinator's procedure in
`AGENTS.md`); a merge queue; claim files.

## Acceptance criteria

Each check builds a temporary git repository (and worktrees of it) with `git` only; nothing
measures time.

1. Rule 1: a history whose newest acceptance commit's parent is the named commit passes; one
   carried across a rebase (parent differs) fails, naming both commits. Seen failing first on a
   constructed case.
2. Rule 2: a repository with a merge commit fails; a linear one passes; the real repository
   passes.
3. Rule 3: in a linked worktree, `uv run pytest --accept "x"` (driven against a small temporary
   project using the plugin, or the plugin's accept function directly) exits 2 with the line and
   writes nothing; in the main tree it accepts as before.
4. Rule 4: a worktree created under the temporary repository's `.claude/worktrees/` leaves the
   judge hash unchanged; seen failing first.
5. `uv run pytest` green with `--accept-judge`; lost 0; grew 0.

## Landing notes

Not built.
