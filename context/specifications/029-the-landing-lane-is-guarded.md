# 029 — The landing lane is guarded

- **Status:** drafted 2026-10-17; revised against its pre-build review
  (`../reviews/029-the-landing-lane-is-guarded-spec-2026-10-17.md`), whose confirmation passed it
  for build with four conditions (A to D), written in. Built 2026-10-17; build-reviewed
  (`../reviews/029-the-landing-lane-is-guarded-2026-10-17.md`, verdict: revise first); revised
  against it the same day (Decisions 2 and 6) and confirmed by the reviewer. Landed 2026-10-17
  (accepted on `567d642` as `b798801`; dry run 39088978405).
- **Owner:** Clay Gendron
- **Kind:** judge additions and changes (`tests/checks/test_rules.py`, `tests/harness/plugin.py`,
  `tests/harness/paths.py`'s stray-conftest walk, `run_meta`'s `dirty`, with the rules' logic in
  `tests/harness/scan.py` and the `git history` need in `tests/harness/needs.py`), the
  scoreboard's announcements, `context/progress/README.md`.
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
   `tests/`, `scripts/`, `recipes/`, `pyproject.toml`, `uv.lock`, the judging files, any
   `conftest.py`) or under a folder whose documents can turn a rules check green that the commit
   would fail (`context/specifications/`, `context/reviews/`, `context/upstream/`; the build
   review, finding 3); an untracked `.idea/` or research draft no longer counts (all 34 history
   lines say `true` today; condition D). `--accept` on a dirty tree is refused when it is made,
   in `pytest_configure`, with one line naming the first changed path, exit 1, and refused again
   in `pytest_sessionfinish` just before anything is written, if the tree became dirty or `HEAD`
   moved during the run (the build review, finding 2), so a dirty acceptance is never written
   and main can never be red-locked by one (condition B). Both refusals apply only when the run
   would write a `context/progress` folder of this repository, as Decision 4's does; the
   plugin's self-tests accept into folders of their own. Rule 1 also requires the newest
   committed line's `dirty` to be `false` for every acceptance made by this judge (its committed
   `accepted.json` names `tests/unit/test_landing_lane.py`; a rules check keeps that file in
   place).
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
6. **The lane's steps, and recovery** (rewritten after the build review, finding 1). A red
   rule 1 cannot be repaired by accepting again: a red rule makes the run red, and `--accept`
   refuses a red run. So the lane checks an acceptance before main moves, on a detached HEAD:
   (1) nothing else is uncommitted in the main tree (others' tracked edits are waited for,
   never stashed); (2) `git switch --detach` onto the rebased reviewed commit, which touches no
   working file (a change built in the main tree is committed there with its specification and
   review); (3) `uv run pytest --accept …`; (4) `git commit -m "Accept …" --
   context/progress/accepted.json context/progress/history.jsonl`, the pathspec leaving out
   anything else that is staged; (5) `uv run pytest tests/checks/test_rules.py` on that commit,
   and if it is red, `git reset --soft HEAD^` (still detached, nothing pushed, main unmoved) and
   step 4 again; (6) `git switch main && git merge --ff-only <the acceptance commit>`.
   `context/progress/README.md` writes these steps out. What the lane does if a red acceptance
   commit reaches main anyway is the owner's to decide (the build review recommends allowing
   `git reset --soft HEAD^` of one unpushed acceptance commit as a named exception to §4.14);
   until then the README says step 5 is never skipped.
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

Built 2026-10-17 by the implementer (Claude Opus 5.5), on darwin-arm64, git 2.51.0, in the main
tree; not yet reviewed. Each claim is labelled. Logs are under `build/029/`; the mutants are under
`/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/m029/`.

**What was built** (READ: the diff).
- `tests/checks/test_rules.py`: two rules checks, `test_the_newest_acceptance_sits_on_the_commit_it_judged`
  (Decisions 1 and 2) and `test_main_is_linear` (Decision 3). Both need `git` and `git history`.
- `tests/harness/scan.py`: their findings, `acceptance_errors(repo)` and `merge_commit_errors(repo)`,
  where the other rules' scanners live (the Design named only `test_rules.py`). Rule 1 reads
  `<c>` with `git rev-list -1 HEAD -- context/progress/history.jsonl`, the line with `git show`,
  the first parent with `<c>^1`, and what `<c>` changes with `git diff-tree <c>^1 <c>`. Its
  `dirty` requirement applies to an acceptance whose committed `accepted.json` names
  `tests/unit/test_landing_lane.py` among its judge files: 029's own acceptance and every later
  one, whatever its line number (`scan.FIRST_CLEAN_JUDGE`; since the revision, a rules check keeps that file in place).
- `tests/harness/needs.py`: the need `git history` (Decision 7): met when `git rev-parse
  --is-shallow-repository` prints `false`. Spec 002's needs table does not list it yet.
- `tests/harness/paths.py`: `git()`, `linked_worktree()` (`--absolute-git-dir` against
  `--path-format=absolute --git-common-dir`, compared with `samefile`), `worktrees()`,
  `worktrees_inside()`, and `dirty_path()`. The stray-conftest walk no longer descends into a
  directory holding a `.git` entry (`os.path.lexists`); the `JUDGE_PATHS` walk is unchanged.
- `tests/harness/plugin.py`: `accept_refusal()`, called first in `pytest_configure`, exits 1
  through `pytest.exit` before collection. The worktree line comes before the dirty line.
  `run_meta()` writes `dirty` from `dirty_path()` and `notes` from `worktrees_inside()`.
- `tests/harness/scoreboard.py`: `render` prints `meta["notes"]` after the overrides line.
- `tests/unit/test_landing_lane.py` (new, 23 checks; 31 after the revision), and `context/progress/README.md`, which
  gets one section on the lane. The CHANGELOG is unchanged, since no earlier judge change is
  logged there.

**Build choices the reviewer should weigh.**
1. *The dirty refusal is keyed like the worktree refusal.* It applies only when the progress folder is a
   `context/progress` of this repository. EXECUTED: the plugin's self-tests accept into
   temporary folders, and the main tree is dirty whenever another agent edits a tracked file
   (`context/specifications/031-…` and `.gitignore` while this was built). A refusal on every
   `--accept` would turn them red there. That is the same reason as the review's Finding 1.
2. *What counts as an untracked judge input.* The six from Decision 2, plus `JUDGE_PATHS` (for
   example a root `conftest.py` or `pytest.ini`), plus any file named `conftest.py`. This is
   condition D's "a judge file that `git ls-files` does not list". `git status` runs with
   `--untracked-files=all`, so a new folder is seen file by file. A nested repository or worktree
   still shows as one entry.
3. *"Exactly the two files" is read as "nothing but the two files."* An acceptance commit that
   changes only `history.jsonl` passes. That happens when a re-acceptance leaves
   `accepted.json` byte-identical.
4. *The notes' path is relative to the root* (`.claude/worktrees/x`).

**A defect in Decision 6, found while building** (READ: `scoreboard.accept`; INFERRED: its
consequence). Decision 6 says an over-full acceptance commit is repaired by accepting again on a
clean tree. That cannot work. Once rule 1 is an accepted pass, a red rule 1 is a lost pass, and
`scoreboard.accept` refuses `--accept` when any pass is lost. So the only repair is the one the
confirmation's condition C named: the lane checks before main moves. `context/progress/README.md`
says so. The lane commits with a pathspec (`git commit -- <the two files>`), which leaves out
anything else that is staged. It then runs `uv run pytest tests/checks/test_rules.py` on that
commit, and main never moves onto a red one. How to recover a red acceptance commit that already
sits on main is the owner's call. This build does not settle it.

**Seen failing first** (EXECUTED, `build/029/first-red.log`). The 23 checks were written
before the code and run against today's judge: 20 failed, 3 passed. The three that passed hold
today and are there to catch wrong implementations. They are: `--accept` elsewhere and
`--partial` proceed in a worktree; the plugin's self-tests pass in a worktree; a nested
repository under `tests/` stays in the hash. Two failures carry the point of the spec:
- the worktree under `.claude/worktrees/x` changed the hash from `76561ebc0607…` to
  `42577ba08484…` by adding `.claude/worktrees/x/tests/conftest.py`;
- `--accept x` in a linked worktree of a clone collected and ran its check, and exited 1 only
  at session end, for another reason. No lane line appeared (`1 passed`, empty stderr).

**Mutants** (EXECUTED, `build/029/mutants.log`).
- Rule 1 ignoring what the commit carries: `…also_carries_code_fails` fails.
- Rule 1 reading the working-tree history: `…appended_but_not_committed_holds` fails, and three
  others with it.
- Rule 1 ignoring `dirty`: `…dirty_acceptance_by_this_judge_fails…` fails.
- Today's `dirty` (any `git status --porcelain` line): the untracked-only case and the untracked
  `conftest.py` case fail.
- The review's naive refusal (any linked worktree, any progress folder), patched onto disk and
  then restored (`cmp` equal): in the worktree, `test_plugin.py` and `test_checks_wiring.py` give
  17 failed and 16 passed, so `…self_tests_pass_in_a_worktree` and `…partial_proceed…` fail.

**The criteria.**
1. EXECUTED: rule 1 holds on its commit with the two files; fails naming both commits after a
   rebase; fails naming `src/code.py` when code rides along; holds while a new acceptance is
   appended and not committed; fails on a dirty line written by 029's judge and holds on an
   older one; and is blocked (`needs: git history`) in a `--depth 1` clone, where `git` is met.
   The cases run the real check function with `paths.REPO` moved to the temporary repository.
2. EXECUTED: `run_meta()["dirty"]` is false with `.idea/`, a draft spec and an uncommitted
   history line present, and true with a tracked change. It is true for an untracked
   `tests/…`, `src/…`, `uv.lock` or `deep/conftest.py`.
3. EXECUTED: rule 3 fails naming the merge commit, and holds on a linear repository and on
   this one. This repository today: no merges, rule 1 holds (`dc188a6` on `1c8a4bb`, the two
   files only), not shallow, no worktree inside.
4. EXECUTED: in a linked worktree of a temporary clone that carries this tree's judge, these
   hold. `--accept x` exits 1 with the line on stderr, before collection; it writes no
   `latest.json` and leaves `history.jsonl` byte-equal. `--accept x --progress-dir <elsewhere>`
   exits 0 and writes there. `--partial` alone exits 0. `test_plugin.py` and
   `test_checks_wiring.py` pass from the worktree. The lane line wins over a dirty tree (unit
   case). The refusal also covers the main tree's folder reached from a worktree, a symbolic link to it,
   `context/../context/progress`, and `Context/Progress` on this case-insensitive APFS.
5. EXECUTED: a worktree at `.claude/worktrees/x` leaves the hash unchanged, `run_meta()` names
   it in `notes`, and `render` prints the note. A nested repository under `tests/` stays in the
   hash.
6. EXECUTED (`build/029/judge.log`, the set in `build/artifacts/` as another agent's build left
   it): `uv run pytest` gives 189/192 pass, 2 blocked (`three systems`, `wheel`), 1 fail. The
   ratchet says lost 1, gained 2 (the two new rules), grew 0, and judge changed (the seven files
   above). The unit suite is 576/578 with 2 skipped. The one failure is not this change. It is
   `test_specifications_have_no_open_question`, on the `## Questions for the owner` headings of
   drafts 031, 033, 035 and 036, which other agents are writing now. With only that check
   deselected (`build/029/judge-deselect.log`), the run exits 0: lost 0, gained 2, grew 0.
   `uv run ruff check` and `uv run ruff format --check` on `src` and `tests` are clean. Nothing
   was accepted. Under Decision 2, 029's own acceptance needs a tree with no tracked change, so
   the lane commits or waits out the other agents' edits first (`.gitignore` and spec 031 were
   modified while this was built).

**Revised 2026-10-17 against the build review**
(`../reviews/029-the-landing-lane-is-guarded-2026-10-17.md`, verdict: revise first) by the
implementer. Every finding is fixed or answered in its Disposition. Logs are under `build/029/`.
- **Finding 1.** Decision 6 is rewritten as the lane's six steps on a detached HEAD, and
  `context/progress/README.md` writes them out. What to do with a red acceptance that reaches
  main is left to the owner.
- **Finding 2.** `pytest_sessionfinish` calls `accept_refusal` again before writing, and also
  refuses when `HEAD` moved since `pytest_configure` (stashed there only when the run would write
  this repository's progress folder). Decision 2 says so.
- **Finding 3.** Untracked files under `context/specifications/`, `context/reviews/` and
  `context/upstream/` now count as dirty. Decision 2 is widened.
  `context/research/` is left out: a memo's presence cannot turn a rules check green, and no
  known gap names a closer today (`tests/known_gaps.toml` is empty).
- **Finding 4.** New cases: a tracked file under `context/` that is edited; a line with no
  `dirty` key, and one with `null`; a merge whose second parent is the named commit.
- **Finding 5.** The guard is now the rules check `test_the_clean_acceptance_key_is_in_the_judge`.
- **Finding 6.** Spec 002 gets one amendment line for `git history`; no check reads its table.
  The README says that git older than 2.31 fails closed.
- **Finding 7.** The README's step 1 covers the order and other agents' edits.

**Seen failing first** (EXECUTED, `build/029/revision-first-red.log`). With the new cases in and
no fix yet, 5 failed and 26 passed. The failures were the three untracked-document cases and the
two during-the-run cases: an edit, and a commit that moves `HEAD`. The new cases for finding 4 pass
on the real code. Each of them kills its mutant (EXECUTED, `build/029/revision-mutants.log`;
every file restored and `cmp` equal):
- `dirty is True`: both no-key cases fail.
- Any parent allowed: the merge case fails.
- All of `context/` exempt: the tracked-under-context case fails.

**The judge** (EXECUTED, `build/029/judge-revised.log`). `uv run pytest` exits 0. The scoreboard
says 191/193 pass, 2 blocked (`three systems`, `wheel`), 0 fail. The unit suite is 584/586 with
2 skipped. The ratchet says lost 0, absent 0, unrun 0, gained 3 (the three new rules), grew 0,
and judge changed. Ruff is clean. Nothing was accepted.

**Landed 2026-10-17** by its own procedure: the change, its specification and its review were
committed on a detached HEAD (`567d642`); the full judge accepted it with `--accept-judge` (775
passed, 4 skipped; v1 191/193, the two blocked as before; lost 0, grew 0); the two progress files
were committed alone (`b798801`); the rules tier passed on that commit (22 passed); and main moved
by `git merge --ff-only`. Release dry run 39088978405 on `b798801`: every job passed, the arm64
Linux rebuild from the pins and "the same bytes from every host" included.
