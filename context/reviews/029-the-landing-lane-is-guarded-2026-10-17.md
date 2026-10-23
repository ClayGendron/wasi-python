# Review of 029 — The landing lane is guarded (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification, or its pre-build review and confirmation. I read `AGENTS.md`, the constitution (§4.13, §4.14, §5.2, §5.6, §5.7), specification 029 with its landing notes, its pre-build review with the confirmation and conditions A to D, `context/progress/README.md`, and the diff. I read `scoreboard.accept`, `plugin.pytest_sessionfinish` and `scan.landed_review_errors` around it. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** the uncommitted working-tree change: `tests/checks/test_rules.py`, `tests/harness/{needs,paths,plugin,scan,scoreboard}.py`, the new `tests/unit/test_landing_lane.py` (23 checks), `context/progress/README.md`, and spec 029's landing notes. I compared the eight files byte for byte (`cmp`) with my scratch copy at the end of the review: unchanged.
- **Ran (EXECUTED, darwin-arm64, APFS, git 2.51.0).** Work is under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev029b/`.
  - `uv run pytest` in the main tree, the full judge, no flags (`judge.log`).
  - `uv run ruff check src tests` and `uv run ruff format --check src tests`.
  - `clone/`: a local clone of `7d7a768` with the eight files copied in and committed (`4748466`). There: the new check file (23 passed); 12 mutants through `tools/mut.py`, each applied, run against `tests/unit/test_landing_lane.py`, and restored (`git diff --quiet` asserted after each; `mutants.txt`).
  - `wt/`: a linked worktree of `clone/`. Real `pytest --accept x` sessions there with the default folder and with `--progress-dir` given as a symbolic link to the main tree's folder, as `CONTEXT/Progress`, as `context/../context/progress`, as the worktree's own `Context/PROGRESS`, and as a folder outside.
  - In `clone/` as a main tree: an acceptance of the rules tier (`--partial`, the in-flight spec-035 check deselected; `tools/judge_rules.sh`), then an acceptance commit that also carries a doc file (as `380f70d` did), then the rules tier and a second `--accept`, then the repair by `git reset --soft HEAD^` (`d1.out` to `d4.out`).
  - `tools/race.py`: `scoreboard.accept` called with a run whose `meta.dirty` is true.
  - `tools/dirty.py` and the landed-review rule with an untracked review in `clone/`.
  - `shallow/`: a `--depth 1` clone of `clone/`; rules 1 and 3 there.
  - In the main tree I wrote only this file. The judge run rewrote `build/progress/latest.json`, as every run does; I did not keep the earlier copy. I never passed `--accept`, `--accept-judge` or anything else that writes `context/progress/`. No commit, stage, checkout, restore or stash in the main tree.
  - One slip: one compound command ran a bare `python3 -c` to print the last history line of `clone/` (read-only). Later commands used `uv run --no-project python`.

## The judge

- **Full judge (EXECUTED, `judge.log`).** `189/192 pass · 0 gap · 2 blocked · 1 fail`, unit suite 576/578 with 2 skipped, `765 passed, 4 skipped, 1 failed` in 163 s. Ratchet against `1c8a4bb66c`: `lost 1 · absent 0 · unrun 0 · gained 2 · grew 0`, judge changed. The one failure and the one lost pass are `test_specifications_have_no_open_question` on spec 035's `## Questions for the owner` heading, which is another agent's draft and still in its working tree at `bb7a558`. The two gained passes are rules 1 and 3. The scoreboard printed no worktree note (none is inside). This matches the implementer's `build/029/judge.log`; its `judge-deselect.log` (READ) exits 0 with lost 0, gained 2, grew 0.
- **Ruff (EXECUTED).** Both clean.
- **The new checks (EXECUTED).** 23 passed in 14.6 s in `clone/`. READ: `build/029/first-red.log` shows 20 failed and 3 passed against the old judge, as the landing notes say.

## Findings, most severe first

1. **High. A red rule 1 on main cannot be repaired by any forward step, from the very first acceptance; the README's "before main moves" step is not yet a procedure.** (Decision 6; `context/progress/README.md`; implementer's flag 1)
   - The defect. The implementer is right that Decision 6's repair ("accept again") cannot work, but the reason is wider than a lost pass. A failing rule 1 makes the run red, and `scoreboard.accept` refuses any red run (`the run is not green`), whether or not rule 1 was ever accepted. So the deadlock exists for 029's own acceptance too. And only `--accept` writes the file whose newest commit rule 1 reads, so no forward commit can move `<c>`.
   - Failure. EXECUTED in `clone/`. Acceptance line 36 names `4748466`, `dirty: false`. Commit it with `context/questions-for-the-owner.md` (`7417d55`): rule 1 fails, "also changes context/questions-for-the-owner.md". Then `--accept "repair"` gives `RED: 1 accepted pass(es) lost; --accept refused: the run is not green …; lost passes: …sits_on_the_commit_it_judged`. The repair that works is `git reset --soft HEAD^`, then `git commit -- <the two files>`, then the doc on its own (`9f4c1dd`, `7bf20fc`): rule 1 holds (lost 0). That is a rewrite, not a fast-forward, if the bad commit was already on main.
   - The README tells the lane to commit and then run `tests/checks/test_rules.py` "before main moves". But `git commit` in a main tree that has `main` checked out *is* main moving. READ: §5.7 already describes the shape that makes the check meaningful: rebase, judge, accept, then fast-forward main. The README does not say where HEAD is while the lane accepts.
   - Fix (author; no constitution change needed). Write the lane's steps in the README, in order: (1) with nothing else uncommitted, `git switch --detach` onto the rebased reviewed commit (for a change built in the main tree, commit it, its spec and its review on the detached HEAD); (2) `uv run pytest --accept …`; (3) `git commit -m "Accept …" -- context/progress/accepted.json context/progress/history.jsonl`; (4) `uv run pytest tests/checks/test_rules.py`; if red, `git reset --soft HEAD^` (main has not moved) and redo step 3; (5) `git switch main` and `git merge --ff-only <the acceptance commit>`. Rewrite Decision 6 in the specification to match, since the landed specification is the record and today it contradicts the README.
   - **Owner question.** What the lane does if a red acceptance commit reaches main anyway. My recommendation: allow `git reset --soft HEAD^` of an unpushed acceptance commit on main as the one named exception to "main moves only by fast-forward" (§4.14), rather than a judge escape such as letting `--accept` proceed when rule 1 is the only failure. The escape would record a failing status as accepted and weaken "only green is accepted" (AGENTS.md rule 4). Either way it changes §4.14 or the judge's acceptance rule, so it is the owner's.

2. **Medium. The dirty refusal is checked only before collection; an edit during the run re-opens condition B's deadlock.** (Decision 2; `plugin.pytest_configure`, `plugin.run_meta`, `scoreboard.accept`)
   - The defect. `accept_refusal` runs in `pytest_configure`. `run_meta` computes `dirty` again at `pytest_sessionfinish`, and `scoreboard.accept` writes whatever it says. A full judge takes about 160 s here. If any tracked file changes in that window, the line is written with `dirty: true`. Once committed, rule 1 is red, and by finding 1 nothing forward repairs it. The same window lets `HEAD` move: the line then names a commit whose tree the judge never fully saw, and rule 1 cannot tell.
   - Failure. EXECUTED (`tools/race.py`): `scoreboard.accept` with `meta.dirty = true` and `green=True` accepts, and the line says `"dirty": true`. EXECUTED (`git log`, `git status`): during this review other agents committed twice on main (`7d7a768` → `ae49b32` → `bb7a558`) and edited `context/questions-for-the-owner.md`. INFERRED: the window is real in this tree.
   - Fix. In `pytest_sessionfinish`, before `scoreboard.accept`, call `accept_refusal` again and also refuse if `HEAD` differs from the one read in `pytest_configure` (stash it). Add a unit case: a tracked edit made between configure and finish refuses the acceptance and writes nothing.

3. **Medium. "A change the judge could see" misses untracked files the rules read.** (Decision 2, condition D; `paths.DIRTY_UNTRACKED`; implementer's flag 3)
   - The defect. The rules checks read `context/specifications/` and `context/reviews/` (`test_landed_specifications_cite_an_existing_review`, the header and open-question rules). An untracked file there can turn a rule green on disk while the committed tree is red, and `dirty` still says false.
   - Failure. EXECUTED in `clone/`: spec 029 committed as landed citing `reviews/029-demo-review.md`, the review left untracked. `dirty_path()` is `None`; the rule passes. With the file gone (as in the commit), it fails: "cites reviews/029…, which does not exist". This is exactly 029's own landing: this review is an untracked file in the main tree.
   - Fix. Add `context/specifications` and `context/reviews` to `DIRTY_UNTRACKED` (and any other folder a rules check reads; `paths.CONTEXT` users are the list). The cost is small: an untracked draft specification with an open question already turns the run red. Today `037-scipy.md` and `038-scipy-second-milestone.md` sit untracked in the main tree; they would then have to be committed or moved to a worktree before the lane accepts, which §5.7 already implies. This widens Decision 2, so the author amends the specification.

4. **Low. Four mutants survive; each is a missing case.** (`tests/unit/test_landing_lane.py`)
   - EXECUTED (`mutants.txt`). Caught: folder compare by `resolve()` instead of `samefile`; only the run's own progress folder; prune on `isdir(.git)` instead of `lexists`; no `--untracked-files=all`; dirty checked before the worktree; no notes line in `render`; rule 1 needing only `git`. Survived:
     - `context-tracked-exempt` (tracked changes under all of `context/` ignored): no case edits a tracked file under `context/`. Add one (a tracked spec edited is dirty).
     - `dirty-is-true` (rule 1 requires `dirty is True` to fail, not `is not False`): a line with no `dirty` key or `null` passes. Add one.
     - `any-parent` (the named commit may be any parent of `<c>`): no case has a merge as `<c>`. Rule 3 makes this moot on main; a one-line case keeps "first parent" honest.
     - `git-dir-strings` (string compare of the two directories): equivalent while `paths.REPO` is the root. No action needed; noted.
   - Not a gap: `rename-source-ignored` is equivalent in effect (the new name is reported first).

5. **Low. Rule 1's clean-from-here key lapses if its guard file is deleted.** (`scan.FIRST_CLEAN_JUDGE`; implementer's flag 5)
   - READ: the key is `tests/unit/test_landing_lane.py` in the committed judge files, and its guard `test_the_first_clean_judge_file_exists` lives in that same file. Renaming it is caught; deleting it removes the key and the guard together, and the `dirty` requirement silently stops. A unit check is not a protected pass.
   - Fix. Move that guard into `tests/checks/test_rules.py`, whose checks are protected by the ratchet: dropping it is then an absent check that needs `--retire`. The key itself is a reasonable choice (it marks 029's judge exactly, whatever the line number).

6. **Low. Spec 002's needs table lacks `git history`, and git older than 2.31 fails closed.** (implementer's flag 6; `paths.linked_worktree`)
   - READ: spec 002's table lists `git` (line 73), not `git history`. Add the row.
   - INFERRED: on git before 2.31, `--path-format=absolute` is not understood, so the two directories cannot match and `linked_worktree` says true in the main tree. The lane's `--accept` is then refused with the worktree line. It fails closed, and the owner's machine has 2.51. One sentence in Decision 4 ("git 2.31 or later") already says it; the README could too.

7. **Low. The README's two lines omit two steps the lane needs.**
   - The order: commit the reviewed change, its specification and its review first; only then is the tree clean enough to accept.
   - Other agents' tracked edits in the main tree block every acceptance, and §4.14 forbids stashing them. READ (`git status` now): `.gitignore` and `context/questions-for-the-owner.md` are modified by others. The lane waits for them, or they move to worktrees.

## The implementer's flags

1. Agreed, and wider: finding 1.
2. Agreed. EXECUTED: the plugin self-tests accept into temporary folders, and the refusal keyed on this repository's progress folders lets them pass from a worktree (criterion 4).
3. Right as far as Decision 2 reaches; the list is too narrow: finding 3.
4. Agreed. "Nothing but the two files" is the right reading. INFERRED from `scoreboard.accept`: `accepted.json` always changes (its `commit` field) unless the same commit is accepted twice, and `<c>` is defined by `history.jsonl` changing, so the only difference is that harmless case.
5. Sound key, weak guard: finding 5.
6. Finding 6.
7. Sound. READ: the fixture clones this repository, copies the judge as it is on disk (tracked and untracked, `--exclude-standard`) into the clone, commits it, and adds a worktree outside. That tests the tree as built, not as last committed, which is what the criterion needs. It runs `sys.executable -m pytest` with `PYTEST_ADDOPTS` removed; that is the test's own subprocess, not a bare `python` in the workflow.

## Acceptance criteria against evidence

1. **Met.** EXECUTED: the five rule-1 cases pass (on its commit; across a rebase, naming both; carrying `src/code.py`; appended but uncommitted; blocked in a shallow clone). EXECUTED (`shallow/`): the real rules file in a `--depth 1` clone reports `blocked by: git history 2`. READ: `first-red.log` shows them failing first. Gap: finding 4's missing cases.
2. **Met.** EXECUTED: untracked `.idea/`, a draft spec and an uncommitted history line are clean; a tracked change is dirty; untracked `tests/…`, `src/…`, `uv.lock`, `deep/conftest.py` are dirty. Too narrow by finding 3.
3. **Met.** EXECUTED: a merge commit fails naming it; a linear history and this repository hold.
4. **Met.** EXECUTED in `wt/`: `--accept x` exits 1 with the lane's line and nothing written (`cmp` of the main tree's `history.jsonl` equal) for the default folder, a symbolic link to the main tree's folder, `CONTEXT/Progress`, `context/../context/progress` and `Context/PROGRESS`; `--progress-dir` outside exits 0 and writes there. The plugin self-tests pass from the worktree (in the 23).
5. **Met.** EXECUTED: a worktree under `.claude/worktrees/x` leaves the hash, is named in `notes` and printed by `render`; a nested repository under `tests/` stays in the hash. The `prune-isdir` and `no-notes` mutants are caught.
6. **Met with the known exception.** EXECUTED: lost 1 (spec 035's draft heading, not this change), gained 2, grew 0; READ: with that check deselected, exit 0.

## Each Decision against the code

1. **Holds** (READ `scan.acceptance_errors`; EXECUTED cases). `<c>` from `git rev-list -1 HEAD -- history.jsonl`, the line from `git show <c>:…`, first parent `<c>^1`, changes by `diff-tree`.
2. **Holds as written, with two holes** (findings 2 and 3). The refusal names the first path and exits 1 in `pytest_configure`.
3. **Holds.** `git rev-list --merges HEAD`.
4. **Holds** (EXECUTED end to end, every spelling tried). The worktree line wins over a dirty tree. Other flags proceed.
5. **Holds.** Only the stray-conftest walk prunes on `lexists(.git)`; the note comes from `git worktree list --porcelain`.
6. **Does not hold; cannot as written** (finding 1).
7. **Holds.** EXECUTED: blocked in a shallow clone; `--accept` proceeds without git (unit case).

## Can the lane accept 029 itself?

Yes, once three things are true. INFERRED from the code and EXECUTED in `clone/` (line 36, `dirty: false`, rule 1 green after a two-file commit):

- The full judge is green: today spec 035's heading keeps it red.
- The main tree has no tracked change and no untracked judge input: today `.gitignore` and `context/questions-for-the-owner.md` (others' edits) block it, and by finding 3 this review file must be committed with the change.
- 029's change, specification and this review are committed first (on a detached HEAD, per finding 1). Rule 1 then still reads `dc188a6` (on `1c8a4bb`, the two files), which predates 029's judge, so it holds. After the lane commits the two files, rule 1 reads 029's own acceptance and requires `dirty: false`; the refusal guarantees that, except in finding 2's window.

## Constitution checks

- **§4.13:** uv only; no dependency added. Ruff clean.
- **§4.14:** rules 1 and 3 enforce it. The repair of a red acceptance on main is not settled (finding 1, owner question).
- **§5.2:** Decision 6 is now contradicted by the README; the specification needs it rewritten.
- **§5.6:** a judge change, reviewed here before landing.
- **§5.7:** "only the lane accepts" is mechanical for linked worktrees (EXECUTED). The lane's ordered procedure is not yet written (finding 1).
- **AGENTS.md rule 4:** nothing weakens the judge. The change adds two protected rules and a refusal; the judge hash moves over seven files, which the lane accepts with `--accept-judge`.
- **AGENTS.md rule 9:** the pathspec commit (`git commit -- <two files>`) leaves other staged paths out. Good.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the implementer, 2026-10-17. Every finding is taken. The evidence is in spec 029's landing notes ("Revised 2026-10-17 …") and under `build/029/`.

1. **Fixed; the owner's part is left to the owner.**
   - Decision 6 is rewritten as the lane's six steps. In order: a quiet tree; `git switch --detach` onto the reviewed commit, with a main-tree change committed there; `--accept`; a pathspec commit of the two files; the rules tier; on red, `git reset --soft HEAD^` while still detached, else `git switch main && git merge --ff-only`.
   - `context/progress/README.md` writes these steps out.
   - The spec gives the deadlock's full reason: any red run is refused, not only a lost pass.
   - What to do with a red acceptance that reaches main is the owner's to decide; the spec records your recommendation. Until then the README says step 5 is never skipped.
2. **Fixed.**
   - `pytest_sessionfinish` re-runs `accept_refusal` just before writing.
   - It also refuses when `HEAD` differs from the commit stashed in `pytest_configure`. The stash is taken only when the run would write this repository's progress folder, so self-tests are not refused when other agents commit.
   - New unit case `test_a_change_during_the_run_refuses_the_acceptance[edit|commit]`: an inner session edits a tracked file, or commits. It exits 1 with `--accept refused …`, and both progress files stay byte-equal. Both cases failed before the fix.
3. **Fixed.**
   - `DIRTY_UNTRACKED` adds `context/specifications`, `context/reviews` and `context/upstream`. The last holds the patches' pull request drafts, whose presence `patch_errors` requires.
   - Decision 2 is widened to match. Three unit cases failed before the fix.
   - `context/research` is not added. A memo's presence cannot turn a rules check green, since the label rule only adds findings. A gap closer could, but `tests/known_gaps.toml` has no entries. Adding it would block the lane on every research draft that other agents keep in the main tree.
4. **Fixed.**
   - New cases: a tracked spec under `context/` edited is dirty; a history line with no `dirty` key, and one with `null`, fail rule 1; a merge commit whose second parent is the named commit fails, naming its first parent.
   - Each kills its mutant (`build/029/revision-mutants.log`).
   - `git-dir-strings` and `rename-source-ignored` are left as noted.
5. **Fixed.** The guard moves to `tests/checks/test_rules.py` as `test_the_clean_acceptance_key_is_in_the_judge`, a protected check. The unit copy is removed.
6. **Fixed.**
   - Spec 002's table is not read by the judge, so spec 002 gets one amendment line naming the need and pointing to 029.
   - The README says git older than 2.31 fails closed.
7. **Fixed.** The README's step 1 says nothing else may be uncommitted. Other agents' tracked edits are waited for, never stashed, and a main-tree change is committed with its spec and review in step 2.

The judge after the revision (EXECUTED): exit 0; 191/193 pass, 0 fail; lost 0, gained 3, grew 0, judge changed.

## Verdict

**Revise first.** The four rules are built as specified and hold up: every refusal spelling I tried from a worktree is caught, the hash ignores an inside worktree, a shallow clone is blocked, and the judge is green but for another agent's draft. Three things stand in the way of landing. Decision 6's repair does not exist, and the README's check before main moves needs the lane to work on a detached HEAD (finding 1). The dirty refusal must be repeated when the acceptance is written, or an edit during the run red-locks main (finding 2). And untracked reviews and specifications must count as dirty, which bites at 029's own landing (finding 3). Findings 4 to 7 are small. What to do when a red acceptance reaches main anyway is an owner question.

One line: the guards work; write the lane's detached-HEAD procedure and rewrite Decision 6, re-check dirty and HEAD at the moment of writing, count untracked specs and reviews as dirty, and ask the owner how a red acceptance on main is undone.

## Confirmation (2026-10-17)

- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the revised working tree (the eight files, plus `context/specifications/002-…`), the Disposition above, question 70 in `context/questions-for-the-owner.md`, and `build/029/judge-revised.log` (READ: exit 0, 775 passed). I wrote nothing in the repository but this section. No commit, stage, checkout, restore or stash in the main tree. I never passed `--accept` or anything else that writes `context/progress/`.
- **Ran (EXECUTED).** Under the same scratch folder: `clone2/`, a clone of `39a340f` with the revised files copied in and committed (`57a0c63`).
  - `uv run pytest` in the main tree (`judge2.log`).
  - `uv run ruff check src tests` and `uv run ruff format --check src tests`.
  - The new check file in `clone2/` (31 passed).
  - Nine mutants through `tools/mut2.py` (`mutants2.txt`): the three that had survived, and six against the revision itself. Each was restored, with `git diff --quiet` asserted.
  - The README's lane end to end in `clone2/`, with `main` set back to `39a340f` so the reviewed commit sits off main.

### Each disposition against its finding

1. **Closed.** READ: Decision 6 and the README now give the six steps in order. They state the full reason for the deadlock: any red run is refused, not only a lost pass. Question 70 asks the owner about the residual case, and records the recommendation (an unpushed reset, not a judge escape). EXECUTED, the lane end to end in `clone2/`:
   - Step 1: the tree was empty.
   - Step 2: `git switch --detach 57a0c63`; main stayed at `39a340f`.
   - Step 3: the rules-tier `--accept` wrote line 36, naming `57a0c633c17e`, `dirty: false`.
   - Step 4: the pathspec commit took only the two files. A doc staged beforehand stayed staged and was left out.
   - Step 5: rule 1 held (lost 0).
   - Then the slip step 5 exists for. An acceptance commit carrying the doc (`267b1b5`) turned rule 1 red. `git reset --soft HEAD^` left HEAD detached at `57a0c63` with main untouched. Re-committing only the two files turned rule 1 green.
   - Step 6: `git switch main && git merge --ff-only` moved main to the acceptance commit (`2f824ee`). No merges; rule 1 still green.
2. **Closed.** READ: `pytest_sessionfinish` re-runs `accept_refusal` and `head_moved` before writing. The HEAD stash is taken only for a run that writes this repository's progress folder. EXECUTED: removing the late check, or keeping only its dirty half or only its HEAD half, each fails `test_a_change_during_the_run_refuses_the_acceptance` (`[edit]`, `[commit]`, or both).
3. **Closed.** READ: `DIRTY_UNTRACKED` now holds `context/specifications`, `context/reviews` and `context/upstream`, and Decision 2 says so. EXECUTED: dropping any one of the three is caught by its own parametrised case. The answer on `context/research` (a memo cannot turn a rule green; `known_gaps.toml` has no closers today) is sound. INFERRED: if a gap entry ever names a research memo as its closer, revisit this.
4. **Closed.** EXECUTED: `context-tracked-exempt`, `dirty-is-true` (both the `no key` and the `null` case) and `any-parent` are all caught now.
5. **Closed.** READ: the guard is `test_the_clean_acceptance_key_is_in_the_judge` in `tests/checks/test_rules.py`, a protected check. It is the third gained pass.
6. **Closed.** READ: spec 002 has one amendment line naming `git history`. The README states that git before 2.31 fails closed.
7. **Closed.** READ: README step 1 (a quiet tree, nothing stashed); step 2 (a main-tree change is committed with its spec and review on the detached HEAD).

### The judge

EXECUTED (`judge2.log`): exit 0. `191/193 pass · 0 gap · 2 blocked · 0 fail`, unit suite 584/586 with 2 skipped, `775 passed, 4 skipped`. Ratchet against `1c8a4bb66c`: `lost 0 · absent 0 · unrun 0 · gained 3 · grew 0`, judge changed (seven files). Spec 035's heading is fixed upstream, so nothing is deselected. Ruff is clean on both counts.

### Notes (none blocks landing)

- In a narrowed run without `--partial`, step 5's command can exit 1 for an unrun check, not for rule 1. EXECUTED: `clone2/` lacks artifacts, so it says `unrun 1`. In the main tree, with the set present, it should be green. Say "if that check fails" in step 5, or name the check's node id in the command.
- Question 70's "Meanwhile" says the README tells the lane to stop and write it down. The README says only that step 5 must not be skipped. One line in either place makes them agree.
- `paths.dirty_path`'s docstring still calls "a draft under context/" clean. Only research drafts are clean now.

### Lands?

**Yes: 029 passes for landing.** The judge is green. All seven findings are closed with EXECUTED evidence. The lane's procedure works end to end, including its reset on red.

The lane must follow the procedure for 029 itself:
- commit the change, its spec, spec 002's line and this review together on a detached HEAD; the dirty refusal now insists, since this review sits under `context/reviews/`;
- accept with `--accept-judge`;
- commit the two files alone, run the rules, then fast-forward.

The residual red-on-main case waits on the owner (question 70).

One line: 029 lands; the lane follows its own six steps for the first time on itself, and question 70 stays with the owner.
