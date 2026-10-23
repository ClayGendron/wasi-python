# Review of 029 — The landing lane is guarded (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote neither the specification nor the memo behind it. I read `AGENTS.md` (on disk, with rule 6a) and the constitution (§4.13, §4.14, §5.2, §5.6, §5.7, §6.4). Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/029-the-landing-lane-is-guarded.md` as drafted (`20dfcb6`).
- **Read:** the memo `context/research/2026-10-17-parallel-work-without-lowering-the-bar.md` (§1.2, §3.1 to §3.4, "What it decides" parts 1 and 6); `tests/harness/plugin.py` (`run_meta`, `_git`, `pytest_sessionfinish`, how `--accept` reaches `scoreboard.accept`); `tests/harness/scoreboard.py` (`accept`, its refusals); `tests/harness/paths.py` (`JUDGE_PATHS`, `NOT_SOURCE`, `judge_files`, `judge_hash`); `tests/harness/needs.py` (`git`); `tests/checks/conftest.py`; `tests/checks/test_rules.py` (`_committed`, `test_progress_history_is_intact`); `tests/unit/test_plugin.py` (`inner`) and `tests/unit/test_checks_wiring.py` (`_run_repo`, `test_pytest_addopts_is_announced_and_blocks_acceptance`); `tests/unit/conftest.py` (`work`); `context/progress/README.md`; `history.jsonl`; `.github/workflows/release.yml` (checkout depth, the judge steps).
- **Ran (EXECUTED, darwin-arm64, git 2.51.0).** In the main tree I ran only read-only `git` commands and a read-only load of `tests/harness/paths.py` (bytecode writing off). I did not run the judge or `scripts/build.sh` there. Work is under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev028-029/`:
  - `rule1.py`: for each of the 31 commits that changed `history.jsonl`, it compares the commit's first parent with the `commit` of the newest line in that commit's version of the file. It also records the line's `dirty` and the files the commit changed outside `context/progress/`.
  - `git rev-list --merges HEAD`; `git rev-parse --git-dir --git-common-dir`; a search for `.git` entries below the root.
  - `judgehash.py`: today's `paths.judge_files()` hash, and a variant whose stray-conftest walk also prunes any directory holding a `.git` entry (rule 4). It ran on the main tree and on `clone/` (a local clone at `20dfcb6`), before and after `git worktree add clone/.claude/worktrees/x`.
  - `git rev-parse` in six layouts: the main tree, a subdirectory of it, a worktree inside it and a subdirectory of that, a worktree outside it (`wt-out/`), and a submodule (`sup/sub`).
  - A depth-1 clone (`shallow/`): `git log -- context/progress/history.jsonl`.
  - Rule 3 built two ways in the scratch worktree `wt-out/`, with the plugin self-tests run there: (a) naive: `git -C paths.REPO`, `--absolute-git-dir` against `--path-format=absolute --git-common-dir`, refusing all four flags (`rule3-naive.txt`); (b) scoped to `--accept`, when the progress directory lies inside a git work tree (`rule3-scoped.txt`); then a real `--accept x` in `wt-out/` under (b) (`rule3-real.txt`). The baseline is `rule3-baseline.txt`. The patch was reverted afterwards.

## What holds

- **The four rules are the right ones, and none weakens the judge.** Each one adds a refusal or a check. None removes one.
- **Rule 1's history claim is true.** EXECUTED (`rule1.py`): 29 of 31 hold. The two exceptions are `bbeac1f` (line 21 names `a76ab13`) and `29702cb` (line 11 names `ab9bafd`), as the memo says. The newest, `cb0c5a6`, has parent `57b3a23`, the commit its line 34 names. The pattern is always the same: the acceptance is a separate commit on top of the commit it names.
- **Rule 2 passes on the real repository.** EXECUTED: `git rev-list --merges HEAD` is empty (0 of 152 commits).
- **Rule 3's signal works.** EXECUTED: in both worktrees `--git-dir` is `<clone>/.git/worktrees/<name>` and `--git-common-dir` is `<clone>/.git`. In the main tree and in a submodule the two are equal. A scoped refusal printed the spec's line, exited 2 and left `context/progress/history.jsonl` unchanged (`rule3-real.txt`, `cmp` equal).
- **Rule 4 fixes what it says and changes nothing today.** EXECUTED: today's walk descends into `.claude/`, because `NOT_SOURCE` does not name it. In the clone, a worktree at `.claude/worktrees/x` moved the judge hash from `2b7d58ade0c7` (62 files) to `a914aea64e09` (65). The three new files are that worktree's `tests/conftest.py`, `tests/checks/conftest.py` and `tests/unit/conftest.py`. With the rule-4 walk the hash stayed `2b7d58ade0c7`. On the main tree the hash is `821ac988963a` (62 files) both ways. The `context/prior_art/` clones are git repositories, but `prior_art` is already in `NOT_SOURCE` and pruned by name. The only other `.git` entries, `build/uv-cache/sdists-v9/.git` and `build/oracle/cache/sdists-v9/.git`, sit under the already pruned `build/`. So skipping nested repositories does not change today's hash, and that is intended. (The main-tree hash includes another agent's uncommitted test file. It is the same both ways.)

## Acceptance criteria against evidence

1. Rule 1: **would pass a wrong implementation.** One that reads the working-tree history passes both constructed cases, yet is red in the lane between accepting and committing (Finding 3). One that ignores what the acceptance commit carries passes too (Finding 4).
2. Rule 2: reachable and sound.
3. Rule 3: **would pass a wrong implementation.** A naive refusal meets the criterion as written and turns 16 plugin self-tests red in every linked worktree (Finding 1). The criterion's "the plugin's accept function" does not exist (Finding 9).
4. Rule 4: reachable. It should also show that a nested repository under `tests/` stays in the hash (Finding 7).
5. Green with `--accept-judge`: reachable in the main tree. That is exactly where Finding 1 does not show.

## Findings, most severe first

1. **High. Rule 3 as written turns the unit suite red in every builder's worktree.** (Decision 3; criterion 3; `tests/unit/test_plugin.py`, `tests/unit/test_checks_wiring.py`)
   - The defect. The plugin's own self-tests run inner pytest sessions with `--accept`, `--accept-growth`, `--accept-judge` and `--partial`. They point `--progress-dir` at a temporary folder (READ: `inner`, `_run_repo`). The plugin module, and so `paths.REPO`, is the tree the outer judge runs in. A check of "is `paths.REPO` a linked worktree" therefore refuses those inner runs whenever a builder runs the judge in its worktree. The spec says "the judge itself still runs there".
   - Failure. EXECUTED: implementation (a) in `wt-out/` gives `16 failed, 17 passed` for `test_plugin.py` and `test_checks_wiring.py`. Unpatched, the same files give `33 passed`. Scoping the refusal to `--accept` with a progress folder inside any git work tree (b) still fails one test: `test_pytest_addopts_is_announced_and_blocks_acceptance`, whose `work` folder is under `build/harness/`, inside the tree, and which expects exit 1, not 2. Criterion 5 runs only in the main tree, and the spec says builders do not start until 029 lands. So the first builder would find this, not the review.
   - Fix. Decide what the refusal is keyed on: the folder that would be written. Refuse `--accept` when the run is in a linked worktree and the progress folder resolves to a `context/progress` folder of this repository: the worktree's own (the default) or the main tree's, reached by `--progress-dir`. Allow any other `--progress-dir`; it writes no accepted state, and the scoreboard already announces it as an override. Add a criterion: `tests/unit/test_plugin.py` and `tests/unit/test_checks_wiring.py` pass when run from a linked worktree of a temporary clone.

2. **Medium. Rule 3 refuses three flags that write nothing.** (Decision 3)
   - The defect. Without `--accept`, `--accept-judge`, `--accept-growth` and `--partial` only change what the ratchet calls red (READ: `pytest_sessionfinish`, `scoreboard.accept`). `--partial` is AGENTS.md's way for "a machine without artifacts" (rule 6), and a worktree may be one.
   - Failure. INFERRED: a builder who runs `uv run pytest --partial "no set here"` in a worktree gets "only the landing lane accepts", which is false: it was not accepting.
   - Fix. Refuse `--accept` only. `--retire` already needs it. Say that the other three are inert without it.

3. **Medium. Rule 1 does not say which history it reads, and the obvious one fails the lane.** (Decision 1)
   - The defect. "The newest history line" could be the working-tree file (`paths.HISTORY`, what `test_progress_history_is_intact` reads) or the file as committed.
   - Failure. INFERRED from the lane's order (memo, part 1, step 3; `AGENTS.md` 6a). The lane runs `--accept`, which appends line n+1 naming X, and then commits the progress files. Any judge run in between, such as a check before committing, sees line n+1 naming X. The newest commit that changed the file is still the previous acceptance, whose parent is not X, so the run is red. Both of criterion 1's constructed cases still pass.
   - Fix. Read the newest line from `git show <c>:context/progress/history.jsonl`, where `<c>` is the newest commit (from `HEAD`) that changed the file, and compare it with `<c>`'s first parent. Add the uncommitted-acceptance case to criterion 1 as a pass.

4. **Medium. Rule 1 holds for acceptance commits that carry unjudged content.** (Decision 1; the Intent)
   - The defect. The rule checks the parent only. An acceptance commit that also carries code passes, though the commit named in the history never held that code.
   - Failure. EXECUTED (`rule1.py`): 23 of the 31 acceptance commits change files outside `context/progress/`. Examples: `204e4bd` (line 29) adds `tests/checks/test_rules.py` changes and names `98d0210`. `6fcee31` (line 27) changes `src/wasi_python/runner.py` and names `aa2d104`. All of them hold rule 1. Every one of the 34 history lines says `"dirty": true`. `run_meta` runs `git status --porcelain`, which counts untracked files, and the main tree always holds untracked `.idea/`. So the flag that could have caught this is always on.
   - Fix. Rule 1 also requires that the newest acceptance commit change exactly `context/progress/accepted.json` and `context/progress/history.jsonl`. EXECUTED: the newest (`cb0c5a6`) does, and so do 8 of the last 12. The memo's lane produces exactly that shape. `run_meta` reads `dirty` with `--untracked-files=no`, and the rule requires `dirty` false on the newest line from the first acceptance after 029 lands. Older lines are not re-judged.

5. **Medium. Rule 1 fails falsely in a shallow clone.** (Decision 5)
   - Failure. EXECUTED (`shallow/`, `--depth 1`): `git log -- context/progress/history.jsonl` returns `20dfcb6 parents=[]`. That is HEAD, a grafted root that seems to add every file, and it has no parent to compare. The `git` need is met (`git rev-parse HEAD` succeeds), so the check fails instead of being blocked. READ: the release build job checks out with `fetch-depth: 0`, so CI is not affected. A person's `git clone --depth 1` is.
   - Fix. A need such as `git history`: met when `git rev-parse --is-shallow-repository` is `false`. Rule 1 is blocked by it otherwise. Or treat a found commit without a parent as blocked.

6. **Low. Name the absolute forms of the two directories.** (Decision 3)
   - EXECUTED: in a subdirectory of the main tree, `--git-dir` prints the absolute `<clone>/.git`, while `--git-common-dir` prints `../../.git`. As strings they differ in the main tree. The plugin runs `git -C paths.REPO`, so at the root both print `.git` and the bug stays hidden until someone moves the call. Write `git rev-parse --absolute-git-dir` against `git rev-parse --path-format=absolute --git-common-dir` (git 2.31 or later; 2.51 here).
   - The layouts, EXECUTED: a submodule has equal directories and is treated as a main tree. That is correct, since it is not a worktree. A plain clone also has equal directories, so it can accept. INFERRED: such an acceptance still reaches main only through the lane, and rule 1 with Finding 4 would catch a moved one. Say that a clone is out of scope.

7. **Low. Rule 4 must stay out of the `JUDGE_PATHS` walk, and the Kind names the wrong file.** (Decision 4; Kind; Design)
   - The defect. "The walk that hashes the judge's inputs" could mean both walks in `paths.judge_files()`: the `rglob` over `JUDGE_PATHS` (`tests`, …) and the stray-conftest `os.walk`. INFERRED: if the skip were applied to the `rglob`, a nested repository under `tests/` would leave the hash. pytest would still collect it, because `norecursedirs` has `.*`, which drops `.git` itself, not the folder that holds it. That is a judge input changing with nobody seeing. READ: `tests/checks/conftest.py` has no walk. The walk is in `tests/harness/paths.py`.
   - Fix. Apply the skip only to the stray-conftest `os.walk`, below the root. Use `lexists`, so a `.git` file and a broken link count too. Take `tests/checks/conftest.py` out of the Kind and the Design. Criterion 4 adds a nested repository under `tests/` whose files stay in the hash.

8. **Low (§4.14). Rule 4 hides a layout the constitution forbids.**
   - READ: §4.14 puts a specification's worktree "outside the repository". Rule 4 makes one inside harmless to the hash, but nothing reports it. If that is intended, because Claude Code's default place is `.claude/worktrees/`, say so. Otherwise add one line to the scoreboard's announcements, or a rules check, from `git worktree list --porcelain`: a worktree below the root is named.

9. **Low. Leftovers for §5.2.**
   - Decision 5 says rules 1 to 3 "skip with `needs: git`". Rule 3 is plugin behaviour, not a check. Say what happens: where git is absent, `--accept` proceeds.
   - Where the refusal happens. In `pytest_sessionfinish` it comes after a full judge run. In `pytest_configure` it comes before collection and costs nothing. Choose one. Choose the exit code too: today every acceptance refusal exits 1 through the red list, while the spec says 2. Also say which wins when two refusals apply (worktree and `PYTEST_ADDOPTS`).
   - Criterion 3's "the plugin's accept function directly": the plugin has none, and `scoreboard.accept` is pure (READ: no git, no paths). Name the function the build adds, or test through pytester.
   - Rule 1 compares with the first parent. Say "first parent". Rule 2 makes the difference moot on main, but not in a builder's branch.

## Constitution checks

- **§4.13:** uv only. No dependency added. The checks use `git` and `tmp` repositories only.
- **§4.14:** rules 2 and 3 enforce it. Rule 4 tolerates a worktree inside the repository, which §4.14 does not allow (Finding 8).
- **§5.2:** open choices in Findings 1, 3, 5 and 9.
- **§5.6:** a judge change, not a guest, set or recipe change. A pre-build review is not strictly required. It is worth having here, because a defect in the judge reaches every later landing.
- **§5.7:** "only the lane accepts" becomes mechanical, if Findings 1 to 4 are taken.
- **§6.4:** the rules are small. Finding 2 makes rule 3 smaller still.
- **AGENTS.md rule 4 (never weaken the judge):** none of the four removes a check or a refusal. Rule 4 changes what the judge hash covers only for content pytest never loads (Finding 7 keeps it that way).

## Disposition (filled in by the author, then confirmed by the reviewer)

All nine findings are taken.

1. **Fixed.** Decision 4 keys the refusal on the folder that would be written: a linked worktree **and** a progress folder resolving to this repository's `context/progress`; any other `--progress-dir` proceeds. Criterion 4 runs `test_plugin.py` and `test_checks_wiring.py` from a linked worktree.
2. **Fixed.** Only `--accept` is refused; the other three flags stay allowed.
3. **Fixed.** Rule 1 reads committed history (`git show <c>:…`), so an uncommitted acceptance does not move `<c>`; criterion 1 adds that case as a pass.
4. **Fixed.** Rule 1 also requires the acceptance commit to change exactly the two progress files; Decision 2 makes `dirty` ignore untracked files, and from the next acceptance requires it false.
5. **Fixed.** Rules 1 and 3 need `git history` (not shallow) and are blocked otherwise.
6. **Fixed.** `--absolute-git-dir` against `--path-format=absolute --git-common-dir`; clones are out of scope, said.
7. **Fixed.** The skip applies only to the stray-conftest walk in `tests/harness/paths.py`, with `lexists`; `tests/checks/conftest.py` is out of the Kind; criterion 5 keeps a nested repository under `tests/` in the hash.
8. **Fixed.** The scoreboard names a worktree inside the repository (one note line).
9. **Fixed.** The refusal happens in `pytest_configure`, exits 1 like other refusals, and wins over `PYTEST_ADDOPTS`'s; where git is absent `--accept` proceeds; criterion 4 runs through real pytest sessions; "first parent" is written.

## Verdict

Revise first. The four rules are right, and today's repository passes all of them. EXECUTED: 29 of 31 acceptances sit on their named commit, there are no merges, the git-dir signal works, and rule 4 leaves today's hash unchanged. But rule 3 as written breaks the plugin's own self-tests in every worktree (Finding 1, EXECUTED: 16 failures). Rule 1 needs three things it does not yet have: which history file it reads, what the acceptance commit may carry, and a shallow-clone need (Findings 3 to 5). Without them, rule 1 is red in the lane's own sequence and silent about carried code.

One line: key rule 3 on the `context/progress` folder being written and on `--accept` alone, read rule 1's line from the commit, require the acceptance commit to carry only the two progress files, and confine rule 4 to the stray-conftest walk.

## Confirmation

- **Date:** 2026-10-17
- **Reviewer:** the same fresh agent (Claude Opus 5.5); not the author.
- **Reviewed:** the specification as revised in `d6f2792`, and the Disposition above (`b8824bc`). I wrote nothing in the repository but this section. I did not commit or stage it.
- **Ran (EXECUTED, darwin-arm64, APFS).** In `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev028-029/casetest/`, I resolved five ways of writing a progress folder against `<tmp>/context/progress`, comparing both `Path.resolve()` equality and `os.path.samefile`. I also ran `git show --stat` on the five newest "Accept" commits.

### Each disposition against its finding

1. **The refusal's key: closed, with condition A.** READ: Decision 4 keys on a linked worktree **and** a progress folder resolving to this repository's `context/progress`. Criterion 4 runs the plugin self-tests from a worktree.
2. **Only `--accept`: closed.**
3. **Committed history: closed.** READ: `<c>` comes from `git show <c>:…`, the first parent, and the uncommitted case is a pass in criterion 1.
4. **What the acceptance carries: closed in intent, with conditions B, C and D.**
5. **Shallow clones: closed.** READ: the `git history` need, blocked when shallow.
6. **Absolute forms: closed.** Clones are out of scope, and the spec says so.
7. **The walk's scope: closed.** READ: only the stray-conftest walk, with `lexists`. A nested repository under `tests/` stays in the hash. The Kind and the Design are corrected.
8. **A worktree inside: closed.** READ: a scoreboard note from `git worktree list --porcelain`.
9. **Leftovers: closed.** READ: the refusal runs in `pytest_configure` and exits 1, it wins over `PYTEST_ADDOPTS`, `--accept` proceeds where git is absent, and "first parent" is written.

### The coordinator's three questions

- **Relative paths and links.** EXECUTED: `context/progress`, `./context/../context/progress/` and a symbolic link to the folder all resolve equal to the target. But `Context/Progress` does not compare equal (`False`), while `os.path.samefile` says it is the same folder (`True`). macOS APFS ignores case by default. INFERRED: pytest hands the option over as written, so `Path(d)` is relative to the process's working directory, which is the invocation directory. `resolve()` handles that. → Condition A.
- **"Exactly the two files" against the lane's commits.** EXECUTED: `cb0c5a6`, `de91fff`, `c35d222` and `fcf1715` change only `accepted.json` and `history.jsonl`. `380f70d` ("Accept spec 020") also adds 10 lines to `context/questions-for-the-owner.md`. So the lane has already broken (b) once with a harmless doc file, and nothing in its written procedure forbids it. If it happens on main after 029, rule 1 is red, and there is no way back without rewriting history (condition C).
- **`dirty` against uncommitted spec files.** INFERRED from Decision 2. A new spec or review that is untracked does not count, so an acceptance with drafts lying around stays clean. A tracked file edited and not committed does count: a Disposition being filled in, or (EXECUTED, `git status` now) `scripts/build.sh` and `tests/unit/test_build_progress.py` under another agent's hands. That is right under §5.7, since the main tree is the lane's. But it bites at the wrong moment (condition B). And `--untracked-files=no` hides the one case that matters most (condition D).

### Conditions left (each a sentence or two; none changes the design)

- **A. Compare folders with `os.path.samefile`, not resolved-path equality,** whenever the folder exists. A folder that does not exist yet compares by `resolve()`. And "this repository's `context/progress`" means the folder in every worktree `git worktree list --porcelain` lists, the main tree's included, so a builder cannot write into a sibling worktree's folder either.
- **B. Refuse a dirty acceptance when it is made, not on the next run.** As written, rule 1 reads `dirty` from the committed line. So a dirty acceptance is written and committed, and only then does the judge go red. Rule 1 is an accepted pass by then, so its failure is a lost pass. Every later `--accept` is refused as "not green", and main is stuck (INFERRED from `scoreboard.accept`'s refusals). Fix: the plugin also refuses `--accept` when `git status --porcelain --untracked-files=no` is not empty (one line, exit 1, in `pytest_configure` with the worktree refusal). Rule 1's `dirty` test then only catches a hand-edited line. Say which acceptance is the first to be required clean: 029's own.
- **C. Write the lane's commit step and its recovery.** `context/progress/README.md`'s two lines (Design) say that the acceptance commit holds exactly the two files and is made right after the accepting run. Also say how the lane recovers if rule 1(b) is ever red on main. `--accept` is then refused, so the only way back is to redo the lane's own unpushed acceptance commit (`git reset --soft HEAD^` and commit the two files alone). That is not a fast-forward, so either §4.14 needs the owner's word for this one case, or the spec says such a commit is never pushed red: the lane runs the rules tier (`uv run pytest tests/checks/test_rules.py`) on the acceptance commit before moving main.
- **D. `dirty` must still see untracked judge inputs.** READ: `paths.judge_files()` takes `tests/` from disk by `rglob`, untracked files included. The memo (§3.1) caught another agent's untracked test file inside a judge hash. With `--untracked-files=no`, an acceptance judged with an untracked test file reads `dirty: false`, and the committed tree lacks that file. Fix: `dirty` is true when there is a tracked change **or** a judge file that `git ls-files` does not list. `.idea/` and untracked drafts still do not count. Criterion 2 adds the case.

### §5.2

After A to D, nothing is left to the build.

### Verdict

**Passes for build**, once A to D are written in. All nine findings are closed. A and D are precision fixes. B and C close a deadlock the revision introduced: a dirty or over-full acceptance committed on main would make rule 1 red and refuse every later acceptance.

One line: compare folders by `samefile` across every worktree, refuse a dirty `--accept` when it is made, count untracked judge files as dirty, and write the lane's two-file commit and its recovery.

### The confirmation's conditions, written in by the author

Each condition is written into the specification's Decisions or criteria, marked by its letter.
