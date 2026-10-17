# Parallel work without lowering the bar

- **Status:** research, 2026-10-17. A study of precedent, a reading of the harness, and an
  experiment run in a scratch clone only. Nothing in `src/`, `tests/`, `scripts/`, `AGENTS.md`
  or the constitution changed; the proposed wording below waits for the owner.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: one session. It read the governing documents,
  the harness and the runner's cache code; read this repository's own git history and reflog;
  read the git, Claude Code, GitHub and Zuul documentation and three engineering posts; and ran
  six scripts in a scratch clone with two linked worktrees. It never made a worktree, a branch,
  a commit, a stash or a checkout in the main tree, and never ran the main tree's judge.
- **Feeds:** the "Working autonomously" section of `AGENTS.md`; constitution §4.14, §5.4 and §7
  (proposed amendments below, for the owner); a specification for the judge rules in
  *What it decides*, part 6.
- **Stands on:** the owner's request (2026-10-17): "Could you research how to coordinate work of
  several sub agents so we don't have as strict of one change at a time? Maybe work trees could
  be helpful? But we need to make sure that we uphold the strong standards that this repo is
  maintaining." Also `2026-10-16-how-autonomous-ports-were-run.md` (lesson 15, which deferred
  parallel agents), spec 002 (the harness), `context/progress/README.md`, specs 024 to 027 and
  their reviews.

## Terms

- A **worktree** (git's *linked worktree*) is a second working directory of one repository. It
  has its own files, `HEAD` and index, and shares the object store and the branches.
- A **scratch clone** is a whole second repository made with `git clone` into a scratch folder.
  This project already builds specs in them (finding 1.6).
- The **judge** is `uv run pytest`; the **ratchet** is its comparison with
  `context/progress/accepted.json`; an **acceptance** is a `--accept` run, which rewrites
  `accepted.json` and appends one line to `history.jsonl`.
- A **landing lane** is one serial queue through which every change reaches main: rebase, judge,
  accept, fast-forward. Only one change is in the lane at a time.
- **Parallel-safe** work can be built, judged and reviewed beside other work. **Lane-only** work
  must not overlap another change of the same kind.
- A **hot file** is one most changes edit: `README.md`, `CHANGELOG.md`,
  `context/questions-for-the-owner.md`, and the two progress files.

## Labels

EXECUTED: run here, with the script and its captured output in this memo's folder. READ: read
in a cited source or file. INFERRED: this memo's reasoning from those.

## 1. What forces serial work today

### 1.1 Shared mutable state, item by item

Every path the harness uses hangs off `REPO = Path(__file__).resolve().parents[2]`
(`tests/harness/paths.py:21`), so it is the root of whichever tree runs the judge (READ). That
decides most of the table.

| state | size | who writes it | two trees? | evidence |
|---|---|---|---|---|
| `build/artifacts/` (the set the judge reads) | 104 MB | `scripts/build.sh`, in place | **readable by both, safely**: two concurrent judges left every byte unchanged | EXECUTED (02: `main-before.txt` = `main-after.txt` for all 17 files) |
| `WASI_PYTHON_ARTIFACTS` | — | the caller | each judge picks its set; set means "that path and nothing else" | READ (`paths.py:91-98`; spec 002 Decision 5) |
| `build/cwasm-cache/` | 1.9 GB in the main tree, 20 files; 300 MB in a fresh worktree | the runner, per tree: a session fixture forces `WASI_PYTHON_CACHE` to `REPO/build/cwasm-cache` | **per tree**; writes are atomic (`mkstemp` then `os.replace`, `runner.py:2434-2438`); keyed by binary hash, wasmtime version and flavour | READ; EXECUTED (02: 3 files, 300 MB per worktree) |
| a symlinked shared cache | — | — | **refused** by the runner: `_private` uses `lstat`, so a link is not a directory | READ (`runner.py:2449-2465`); EXECUTED (06) |
| `build/progress/latest.json` | 44 KB | every judge, by a plain `write_text` (not atomic) | **per tree**; two judges in one tree overwrite each other | READ (`plugin.py:370-372`); EXECUTED (02: the main tree's file changed during the run, written by another agent's judge in the main tree: its judge hash lists that agent's untracked `tests/unit/test_build_progress.py`) |
| `build/harness/` temp folders | 235 MB in the main tree (leftovers) | `mkdtemp` per session or check | **per tree** and uniquely named | READ (`checks/conftest.py:61-65`, `pins.py:84`) |
| the system temporary folder | — | the runner's private roots and zip folders | shared, but each folder is locked and a sweeper skips locked ones (spec 016) | READ (`runner.py:424-600`) |
| `context/progress/accepted.json`, `history.jsonl` | 34 lines | `--accept` only | **cannot merge**: two acceptances both append line 35 with the same `prev` | EXECUTED (03, 05) |
| `README.md`, `CHANGELOG.md` | — | most landings | textual conflicts on rebase | READ (git log: 30 of 114 commits today touched README, 24 CHANGELOG); EXECUTED (03) |
| spec numbers | — | the drafter | two drafters would both take 028 | READ (`context/specifications/`); INFERRED |
| `downloads/` | 572 MB | `scripts/00_download.sh` | per tree; a build clone copies it | READ (earlier scratch clones hold 413 to 572 MB each) |
| source trees `build/<top>/` | 2.1 to 2.4 GB per build | the build | per tree; a worktree without them leaves 8 v1.5 checks "unrun locally" | EXECUTED (02: `unrun locally 8`) |
| the judge's own files | — | — | the conftest walk covers the whole tree, including any worktree placed inside it | READ (`paths.py:137-140`); EXECUTED (04) |

So git and the harness already isolate almost everything per tree (INFERRED from the table).
What is genuinely shared is small: the accepted state and its history, a few hot prose files,
the spec number sequence, and the artifact bytes when a change alters the build.

### 1.2 The ratchet's baseline is one commit

`accepted.json` names one commit. Of the 31 commits that changed it, 29 name their own parent
(EXECUTED: `01_accept_baselines.txt`). The other two name commits that are no longer in main's
history: `a76ab13` (spec 015, accepted, then the commit was amended into `bbeac1f`) and `ab9bafd`
(spec 010, accepted, then main was reset and the commit remade as `29702cb`; reflog: "reset:
moving to ab9bafd", 03:38:46). INFERRED: the rule the project lives by is "an acceptance is
committed directly on the commit it judged", and both exceptions came from rewriting a commit
after it was accepted. Nothing checks the rule today.

### 1.3 One judge per tree is assumed, not enforced

`latest.json`, `build/harness` and the cwasm cache are per tree, so one judge per tree is safe.
Two judges in **one** tree race on `latest.json` (READ). The 026 review shows the cost: its
reviewer had to restore `build/progress/latest.json` "byte for byte" after judging in the main
tree (READ, `reviews/026-…-2026-10-17.md`). Right now three agents share the main tree: this
one, one editing the build scripts, and one writing a tool-protocol memo (EXECUTED: `git status`
lists all three). The judge in the main tree sees all their half-done work at once.

### 1.4 The review flow is per change, not per tree

A review is given the specification and the diff (constitution §5.6). Nothing in it needs the
main tree. Reviews already re-run the judge in scratch folders (READ: the 026 review ran its
mutants in `rev025/`). INFERRED: review parallelises as soon as each change has its own diff and
its own tree.

### 1.5 What a build costs

A full build from an empty `build/` takes 5 to 6 minutes (READ: 5m46s on 2026-10-17 in
`2026-10-17-delightful-build-progress.md`; 5m06s in the sqlite memo). A build clone holds about
3 GB (READ, EXECUTED: `du` of the scratch clones `build007`, `build018`, `build020`: 3.0, 2.9,
3.1 GB). The fast-tier judge took 123 s in each of two worktrees run at once with cold caches
(EXECUTED, 02); one alone took 116 to 121 s (EXECUTED, 03). The disk has 127 GB free and is 94% full
(EXECUTED: `df -h`); the scratch folder already holds about 14 GB of old scratch clones (EXECUTED: `du -sh build0*`).

### 1.6 Parallel work already happens, informally

The main tree's reflog holds nine `pull --ff-only` from scratch clones
(`scratchpad/build007/repo` … `build022/repo`) between 09:14 and 14:06 on 2026-10-17 (EXECUTED:
`git reflog`). Specs 020 and 022 were in flight together: pulls from `build020` at 13:33, from
`build022` at 13:42, from `build020` again at 14:06. The reflog also records four amends and three
resets of main. Main has no merge commits (EXECUTED: `git rev-list --merges --count
HEAD` → 0). INFERRED: the project already uses scratch clones as worktrees and fast-forward as
its landing. What it lacks is a written rule for the order of landing and for who accepts.

## 2. How others coordinate many agents

- **git worktrees.** A linked worktree shares "everything except per-worktree files such as
  `HEAD`, `index`, etc." Refs under `refs/` are shared. A branch checked out in one worktree is
  refused in another unless forced (READ: git-worktree(1)). INFERRED: a worktree is lighter
  than a scratch clone (no second object store), and the per-branch exclusivity is a free lock:
  one worktree per spec branch.
- **Claude Code worktrees.** `claude --worktree <name>` and the Agent tool's `isolation:
  worktree` create the worktree "under `.claude/worktrees/<name>/` at your repository root, on a
  new branch named `worktree-<name>`". A subagent's worktree is removed if it made no changes,
  and kept otherwise. It is "a fresh checkout, so initialize your development environment
  there". Worktrees branch from `origin/HEAD` by default (`worktree.baseRef: "fresh"`), not from
  local `HEAD`, unless `worktree.baseRef` is `"head"`. While isolated, Claude Code blocks edits
  and git commands aimed at the main checkout, but not a plain `cp` or redirect into it (READ:
  code.claude.com/docs/en/worktrees, /sub-agents). Two consequences here (INFERRED, the first
  EXECUTED in 04): the default location puts a second copy of `tests/` inside the main tree,
  which the main tree's judge counts as judge files; and the default base would start a
  worktree from the last pushed commit, while this project's main is often ahead of `origin`
  between pushes.
- **Agent teams.** A lead, teammates, and a shared task list whose claims use "file locking to
  prevent race conditions"; "Two teammates editing the same file leads to overwrites. Break the
  work so each teammate owns a different set of files"; quality gates through `TaskCompleted`
  hooks. Experimental, off by default (READ: code.claude.com/docs/en/agent-teams).
- **Lock files in git.** Anthropic's C compiler: each agent cloned an upstream bare repository
  into its own container and pushed back; an agent "takes a 'lock' on a task by writing a text
  file to current_tasks/", and "git's synchronization forces the second agent to pick a
  different one"; late regressions were stopped by CI "so that new commits can't break existing
  code" (READ: anthropic.com/engineering/building-c-compiler). Cursor found equal agents sharing
  a lock file slowed twenty agents to the throughput of two or three (READ, through the ports
  memo).
- **The not-rocket-science rule.** "Automatically maintain a repository that never fails its
  tests": a bot "merges (or rebases) it with the latest tip", and the change becomes the tip
  only if "it builds cleanly and that all the tests pass" (READ: Yaron Minsky's account of Graydon Hoare's rule in Jane Street's "Making 'never
  break the build' scale"; bors implemented it for Rust).
- **Merge queues.** GitHub's queue tests each pull request combined "with the latest base branch
  and the pull requests ahead of it" on a temporary branch, and merges only when required
  checks pass; Actions must listen to `merge_group` (READ: GitHub docs, "Managing a merge
  queue").
- **Speculative gating.** Zuul tests queued changes in parallel, each on top of those ahead of
  it, "performing speculative execution of test jobs; it assumes that all jobs will succeed"; when one fails, "changes that were expecting it to succeed are re-tested
  without the failed change" (READ: zuul-ci.org, "Project Gating").
- **Batching.** Jane Street cut integration requests from hundreds a week to thirty or forty by
  keeping features on branches until fully reviewed (READ).

Common thread (INFERRED): everyone parallelises the **building**, and keeps one serial,
mechanical **gate** that judges the exact combined result before the shared branch moves. None
of them lets two writers update the shared record of what passed.

## 3. The experiment (EXECUTED)

All of it ran in `<scratch>/parallel/`: a `git clone` of the main repository's committed `HEAD`
(`c4a8a00`), with two linked worktrees, `wt-a` and `wt-b`, on branches `exp-a` and `exp-b`. The
main tree's uncommitted work (another agent's build-script changes) was therefore not in the
clone. Every judge pointed `WASI_PYTHON_ARTIFACTS` at the main tree's `build/artifacts/`. The
times are benchmark facts from one machine (ten cores) that other agents were also using; no
check reads them.

### 3.1 Two judges at once, in two worktrees (02)

- Both runs: `174/190 pass · 0 gap · 10 blocked · 0 fail · 6 deselected (unit suite 464/472)`,
  `ratchet vs 57b3a23284: lost 0 · absent 0 · unrun 0 · unrun locally 8 · gained 0 · grew 0`,
  exit 0 (`out/wt-a-judge.txt`, `out/wt-b-judge.txt`).
- The "unrun locally 8" are the v1.5 source-tree checks: a worktree has no `build/<top>/` or
  `downloads/`. They are reported, not red (spec 002 Decision 6). So **a worktree's judge is a
  weaker judge than the main tree's**: it cannot see upstream drift. The landing must judge in
  a tree that has the source trees (part 1, step 3).
- No conflict: each worktree wrote its own `build/progress/latest.json`, its own
  `build/harness/`, and its own `build/cwasm-cache/` (3 files, 300 MB). `git status` in both
  worktrees was empty afterwards; `build/` is ignored there as in the main tree.
- The main tree's artifact set was unchanged, file by file (17 SHA-256 lines equal before and
  after, `out/main-before.txt`, `out/main-after.txt`). Its `latest.json` and `build/harness/`
  did change, during the run, by another agent's judge in the main tree, identified by its
  judge hash including that agent's untracked test file (finding 1.1).
- Time: 123 s of pytest each, 141 s wall for both, cold caches. One judge alone, warm: 116 s and
  121 s (`out/final-b.txt`, `out/reaccept-b.txt`). Two at once, warm: 138 s each
  (`out/accept-a.txt`, `out/accept-b.txt`). So two judges cost about 1.15 times one, on this
  machine.

### 3.2 Two acceptances at once (03)

- `--accept` succeeded in **both** worktrees, each writing history line 35 (`out/accept-a.txt`,
  `out/accept-b.txt`). Nothing in the harness stops an acceptance outside the main tree, or two
  at once.
- A landed by fast-forward. Rebasing B onto it stopped with conflicts in `CHANGELOG.md` and
  `context/progress/history.jsonl` (`out/land.txt`, `out/rebase-b-conflicts.txt`).

### 3.3 `accepted.json` merges silently; the history does not (03, 05)

- In the same rebase, git reported "Auto-merging context/progress/accepted.json" with **no
  conflict** (`out/rebase-b.txt`). The two files differed only in fuel values (for example
  82,839,949 against 82,839,932 on one check), in separate hunks, so git combined them into a
  file neither acceptance wrote.
- A lane that kept both history lines (a union merge) is refused by the existing check:
  `history line 36: prev does not hash line 35`, `history line 36: n is 35` (`out/union.txt`,
  `scoreboard.history_errors`, the function behind `test_progress_history_is_intact`).
- The lane's way worked: take main's two progress files, accept again on the rebased commit,
  fast-forward. The history is one chain: line 35 names `c4a8a00` (A's parent), line 36 names
  `7985a2c` (the rebased B, parent of the commit carrying the acceptance). The final judge on
  main's tip: 0 fail, lost 0, grew 0 (`out/land.txt`, `out/final-b.txt`).
- INFERRED: had A landed without an acceptance (a memo, say), B's rebase would have been clean,
  and B's acceptance, taken on `c4a8a00`, would have been carried onto a tree it never judged.
  Judge rule 1 in *What it decides* catches exactly that, because B's acceptance would no
  longer name its commit's parent.

### 3.4 A worktree inside the repository changes the judge (04)

`paths.judge_files()` in the clone: 61 files, judge hash `24da1fb067e6`. With a worktree at
`.claude/worktrees/inside/` (Claude Code's default place): 64 files, hash `f4290620e8fa`, the
three extra being that worktree's `conftest.py` files; `git status` showed `?? .claude/`.
Removed: back to 61 and `24da1fb067e6` (`out/inside.txt`). So a Claude Code worktree in its
default place would make the main tree's judge report "judge changed", and `--accept` there would
refuse without `--accept-judge`.

### 3.5 The set needs no write access; the cache cannot be shared by a link (06)

- A copy of the artifact set with every write bit removed (`chmod -R a-w`) judged the same:
  174/190, 0 fail, lost 0, grew 0, exit 0, in 120 s (`out/ro-judge.txt`).
- The runner given a private cache directory compiled and wrote one module; given a symlink to
  the same directory, it compiled, wrote nothing, and warned "not using the module cache"
  (`out/cache-link.txt`). The ownership check sees the link, not the directory. INFERRED: each
  worktree keeps its own 300 MB cache; that is the price of not trusting a shared native-code
  folder, and it is a fair one.

## What it decides

A memo commits the project to nothing. This is the proposal it supports, and the owner's
decisions it needs. Its idea in one sentence: **build in parallel, land in series.** Many
worktrees may build, judge and be reviewed at once; one lane moves main, one change at a time,
and only that lane ever accepts.

### 1. The shape

- **The coordinator** is the one session the owner talks to. It drafts and numbers
  specifications, starts builders and reviewers, and runs the landing lane. It is the only
  writer of main and of `context/progress/`.
- **The main tree is the lane's tree.** Nobody edits files in
  `/Users/claygendron/Git/Repos/wasi_python` except the lane. Today three agents edit it at once
  (finding 1.3); under this proposal each would have its own worktree.
- **A builder** gets one specification and one worktree: `git worktree add <scratch>/wt/NNN -b
  spec/NNN-<slug> main`, outside the repository (finding 3.4: inside it, the worktree
  changes the main tree's judge). It runs `uv sync`, builds, runs the judge **without**
  `--accept`, writes the landing notes, and commits on its branch. It never touches main.
- **A reviewer** is a fresh agent given the specification and `git diff main...spec/NNN`. It
  re-runs the judge in the builder's worktree (or a second worktree at the same commit), writes
  its review under `context/reviews/` on the same branch, and never edits code (constitution
  §5.6, unchanged).
- **The landing lane** takes one reviewed branch at a time:
  1. **Rebase** the branch onto main's tip in its worktree.
     - `context/progress/` is never merged. Take main's two files and accept again (step 3).
       Git will not always stop you: in the experiment `accepted.json` **auto-merged without a
       conflict** into a file neither run wrote; only `history.jsonl` conflicted (finding 3.3).
     - A hot prose file (`README.md`, `CHANGELOG.md`, `questions-for-the-owner.md`) is resolved
       by the lane by keeping both sides' lines.
     - Any other conflict goes back to the builder, and then back to the reviewer.
  2. **Compare** the rebased change with the reviewed one: `git range-diff <old base>..<reviewed tip>
     main..spec/NNN`. If it differs beyond the hot-file union, the reviewer adds a short addendum
     to the review before the landing goes on.
  3. **Judge and accept in the main tree, on the exact commit.** `git switch --detach
     spec/NNN` (the main tree is clean, because only the lane uses it, so no uncommitted work
     is touched). For a build-class change, `scripts/build.sh` runs here first, so the set the
     judge reads is built from this commit. Then the full `uv run pytest --accept "<reason>"`,
     with the source trees present, and a commit of the two progress files on top. The acceptance's commit is now the parent of the commit that carries it, as
     in 29 of the 31 past acceptances (finding 1.2).
  4. **Fast-forward** main: `git switch main && git merge --ff-only <that commit>`. If the judge
     was red, `git switch main`: main never moved, and the branch goes back to its builder.
  5. **Remove** the worktree and its branch (`git worktree remove`, `git branch -d`).
  6. **Push and dry-run** when the owner asks, as today. A build-class landing waits for its
     dry run before the next build-class landing (part 2).

This is the not-rocket-science rule, run by hand: test the exact combination, then move the tip
(section 2). It is also what the reflog shows the project already doing with scratch clones and
`pull --ff-only` (finding 1.6), made explicit, with acceptance moved to the one place it cannot
race.

### 2. Which work runs in parallel

The rule is mechanical. **A change is build-class when it touches `scripts/` (not
`scripts/bench_*`), `recipes/`, `downloads/SHA256SUMS`, or `.github/workflows/release.yml`.**
Everything else is parallel-safe. The judge already enforces the first half: a worktree whose
scripts or recipes differ from the shared set's `MANIFEST` fails
`test_manifest_recipes_match_the_tree` (READ: spec 002 Decision 12), so build-class work cannot
be judged against the shared set by mistake (INFERRED).

| class | examples from the history | builds against | in flight at once |
|---|---|---|---|
| parallel-safe: runner, command line, judge-only, docs, research | specs 001, 002, 008 to 011, 013 to 017, 019, 022, 025, 026; every research memo | the shared, read-only artifact set | up to three |
| build-class: anything that changes the artifact bytes or the recipe | specs 003 to 007, 012, 018, 020, 021, 024, 027 (READ: `git log -- scripts recipes`) | its own full build in its own worktree (about 3 GB, 5 to 6 minutes) | one |
| lane-only: the coordinator's own work | spec drafts and their pre-build reviews, the constitution, `AGENTS.md`, `decisions.md`, releases | main, directly | — |

- **Spec numbers** are taken when the coordinator lands the draft on main, as today ("Spec 027,
  drafted …, for its pre-build review" was its own commit). Drafting is serial and cheap;
  building is what runs in parallel. No claim files are needed while there is one coordinator.
- **Two build-class changes never overlap.** Each changes the bytes every other check measures
  (fuel, sizes, the snapshot). When one lands, main's artifact set is rebuilt by the lane, and
  every parallel-safe worktree rebases and re-judges against the new set before it may land.
- **A change that edits the judge** (`tests/`, `uv.lock`, `pyproject.toml`) is parallel-safe to
  build, but the lane lands judge changes one at a time and the `--accept-judge` reason names
  the spec (spec 002 Decision 14, unchanged).

### 3. The shared artifact set

- The lane keeps one **frozen set per accepted artifact**, copied from `build/artifacts/` after
  each build-class landing to `build/sets/<first 16 hex of python.wasm's hash>/` and made
  read-only (`chmod -R a-w`). Builders point `WASI_PYTHON_ARTIFACTS` at it. Reason: the judge
  only reads the set (EXECUTED, 02 and 06), but `build.sh` rewrites `build/artifacts/` in place,
  and a rebuild under a running judge would hand it a torn set (INFERRED).
- Each worktree keeps its own cwasm cache (300 MB, compiled on its first run). A shared cache
  through a symlink is refused by the runner's ownership check, which is the right behaviour
  for native code and is not worth weakening (EXECUTED, 06; READ, `runner.py:2449`).

### 4. Budgets

- Disk: 360 MB per parallel-safe worktree (300 MB cache, 58 MB `.venv`, plus the checkout);
  3.5 GB per build-class worktree with its downloads (EXECUTED, 02; READ, the old clones). With
  127 GB free and the disk 94% full, the cap is three parallel-safe and one build-class
  worktree, and every worktree is removed when it lands or is abandoned. The 14 GB of old scratch
  clones in the scratch folder are the first thing to delete (INFERRED).
- Time: a fast-tier judge takes about two minutes, and two at once cost about 1.15 times one
  (EXECUTED, finding 3.1). A build-class change adds a 5 to 6 minute build. The lane's own cost
  per landing is one full judge in the main tree. INFERRED: with three parallel-safe builders,
  the lane, not the builders, becomes the limit only when landings come faster than one every
  few minutes, which this project has never done (EXECUTED: 114 commits and 29 acceptances on 2026-10-17, about one acceptance every 40 minutes).
  Three judges at once on ten cores is the stated ceiling until a measurement says otherwise.
- Tokens: each builder and reviewer is a separate context. Parallelism spends more for the same
  work; it buys wall-clock time only (READ: the agent-teams page says so of teams).

### 5. The standards, one by one

| standard | how it holds under the proposal |
|---|---|
| one specification per landing (§5.4) | unchanged: the lane lands one branch, one spec, at a time |
| implementer never reviews (§5.6) | unchanged: a fresh agent per spec; worktrees make it easier, since the reviewer gets a diff, not a shared tree |
| every landing green on its own, at its exact commit | stronger: the full judge runs on the rebased commit itself before main moves |
| no pass lost quietly; history append-only | unchanged and now race-free: only the lane accepts; a merged acceptance is caught (finding 3.3) |
| commit only what you mean | easier: a worktree holds one change, so `git diff --cached --stat` shows only it |
| never stash, restore or checkout uncommitted work | unchanged; the lane's tree is clean by construction |
| artifacts never in git; downloads untrusted | unchanged: each worktree's `build/` and `downloads/` are ignored as in the main tree |
| the dry run | unchanged: after landing, on main; build-class landings wait for theirs |

### 6. Judge rules that would guard the process

Each is a judge change: it needs its own specification, review and `--accept-judge`.

1. **An acceptance sits on the commit it judged.** For the last commit that changed
   `history.jsonl`, its parent is the commit the last history line names. Today 29 of 31
   acceptance commits hold it; the two that do not predate the rule (EXECUTED,
   `01_accept_baselines.txt`). It catches an acceptance carried across a rebase or an amend,
   which a clean rebase would otherwise let through silently.
2. **Main is linear.** No merge commit is reachable from `HEAD` (today: 0, EXECUTED). It keeps
   every landing a fast-forward.
3. **`--accept` refuses in a linked worktree.** When `git rev-parse --git-dir` differs from
   `--git-common-dir`, the run is not in the main tree, and the plugin refuses to write the
   progress files. This makes "only the lane accepts" mechanical. (The experiment accepted in
   two worktrees at once; nothing stopped it: finding 3.2.)
4. **A worktree inside the repository is not judge input.** The conftest walk skips any
   directory that holds a `.git` entry of its own (a linked worktree or a nested repository).
   Without it, a Claude Code worktree under `.claude/worktrees/` changes the main tree's judge
   hash (finding 3.4).

The existing `test_progress_history_is_intact` already refuses a history in which two
acceptances were both kept (finding 3.3), so no rule is needed for that.

### 7. What the owner would approve

These are decisions only the owner can make (a change to the constitution and to how work is
done). They belong in `questions-for-the-owner.md` if the owner is away; this memo does not
write there.

**Decision A: constitution §4.14.** Today: "Commit or push only when the owner asks. No branches
or worktrees unless asked. Never `git checkout`, `git restore` or `git stash` a file carrying
uncommitted work." Proposed:

> 14. **Git.** Commit or push only when the owner asks. Work on one specification may run in its
>     own git worktree, outside the repository, on a local branch named `spec/NNN-<slug>` made
>     from main's tip; the branch is never pushed and is deleted with its worktree when the
>     specification lands or is abandoned. No other branch or worktree unless asked. Main moves
>     only by fast-forward, through the landing lane (§5.7). Never `git checkout`, `git
>     restore` or `git stash` a file carrying uncommitted work.

**Decision B: constitution §5.4 and a new §5.7.** §5.4 gains one sentence: "Specifications may be
built in parallel; they land one at a time." New:

> 7. **One landing lane.** Builders and reviewers may work in parallel, each in its own
>    worktree. Main changes in one place only: the lane rebases one reviewed branch onto main,
>    compares it with what was reviewed, runs the full judge on that exact commit in the main
>    tree, accepts there, and fast-forwards main. Only the lane accepts. A change to the build
>    recipe overlaps no other change to the build recipe.

**Decision C: constitution §7.** "Commit, push, branch, tag, publish a release, or upload to PyPI
without the owner's explicit instruction for that action" becomes "Commit, push, tag, publish a
release, upload to PyPI, or make a branch or worktree beyond §4.14's, without the owner's
explicit instruction for that action."

**Decision D: `AGENTS.md`.** In *Rules that bind all work*, the Git bullet becomes "Commit or
push only when asked. A specification may be built in its own worktree outside the repository,
on a local `spec/NNN-<slug>` branch (constitution §4.14); no other branch or worktree unless
asked. Never `git checkout`, `git restore` or `git stash` a file that carries uncommitted
work." In *Working autonomously*:

- item 2 ends "One specification per builder; at most three parallel-safe and one build-class
  specification in flight; one landing at a time."
- a new item after 6: "**Only the lane accepts.** A builder runs the judge in its worktree
  without `--accept`, against the frozen artifact set its class allows. The lane rebases,
  compares with the reviewed diff, judges the exact commit in the main tree, accepts, and
  fast-forwards main. Progress files are never merged: take main's and accept again."
- item 9 gains: "A worktree's branch carries exactly one specification."

**Decision E: the judge rules of part 6**, as one specification.

**Decision F: whether the standing instruction to commit covers commits on `spec/` branches.**
They are commits, so §4.14's first sentence applies to them as written.

If the owner declines all of this, two parts still help with no rule change (INFERRED): judge
rule 4 (a worktree inside the tree is not judge input) and the frozen artifact set, because
both protect today's informal scratch-clone practice.

## The folder

`2026-10-17-parallel-work-without-lowering-the-bar/` holds the scripts and what they printed.
Every script takes the main repository and a scratch directory as arguments, and changes nothing
in the main repository: it reads the main tree's artifact set and clones the main repository's
committed `HEAD` (`c4a8a00`), and every worktree, branch and commit it makes is in the clone.

- `01_accept_baselines.sh` → `01_accept_baselines.txt`: for each commit that changed
  `accepted.json`, whether the commit it names is its parent (read-only git).
- `02_two_worktrees.sh`: two worktrees, two fast-tier judges at once against the main tree's set;
  snapshots of the main tree before and after.
- `03_two_acceptances.sh`: both worktrees accept, A lands by fast-forward, B is rebased, its
  progress files are replaced with main's and it is accepted again, then lands.
- `04_worktree_inside_the_tree.sh`: the judge hash with and without a worktree under
  `.claude/worktrees/`.
- `05_union_merge_of_two_acceptances.sh`: the judge's history check on a history that keeps both
  acceptances.
- `06_read_only_set_and_shared_cache.sh`: a judge against a set with no write bits; the runner
  given a symlinked cache.
- `out/`: the captured outputs, trimmed to the scoreboard where a log was long.

To re-run (about fifteen minutes on this machine):

```
D=context/research/2026-10-17-parallel-work-without-lowering-the-bar
S=<an empty scratch directory>
sh $D/01_accept_baselines.sh .
sh $D/02_two_worktrees.sh "$PWD" $S
sh $D/03_two_acceptances.sh "$PWD" $S
sh $D/04_worktree_inside_the_tree.sh $S
sh $D/05_union_merge_of_two_acceptances.sh $S
sh $D/06_read_only_set_and_shared_cache.sh "$PWD" $S
```

## What this memo does not show

- No builder, reviewer or lane was run as an agent here; the experiment ran the git and judge
  steps they would run, by script.
- No build-class change was built in a worktree. The cost figures for one (3 GB, 5 to 6 minutes)
  come from the earlier scratch clones and memos, not from this session.
- The time figures come from one machine under other agents' load. They are benchmark facts,
  not checks.
- The judge rules of part 6 were not written or run; their evidence is the history (rule 1, 2)
  and the experiment (rules 3, 4).

## Sources

- git-worktree(1): <https://git-scm.com/docs/git-worktree> (read 2026-10-17).
- Claude Code, "Run parallel sessions with worktrees":
  <https://code.claude.com/docs/en/worktrees>; "Subagents":
  <https://code.claude.com/docs/en/sub-agents>; "Orchestrate teams of Claude Code sessions":
  <https://code.claude.com/docs/en/agent-teams>; "Common workflows":
  <https://code.claude.com/docs/en/common-workflows> (read 2026-10-17).
- GitHub, "Managing a merge queue":
  <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue>.
- Zuul, "Project Gating": <https://zuul-ci.org/docs/zuul/latest/gating.html>.
- Jane Street, "Making 'never break the build' scale":
  <https://blog.janestreet.com/making-never-break-the-build-scale/> (it quotes Graydon Hoare's
  rule; his original post was not reachable, 404).
- Nicholas Carlini, "Building a C compiler with a team of parallel Claudes":
  <https://www.anthropic.com/engineering/building-c-compiler>.
- This repository: `tests/harness/paths.py`, `plugin.py`, `scoreboard.py`,
  `tests/checks/conftest.py`, `tests/checks/test_v1_4_embedding.py`, `src/wasi_python/runner.py`,
  `git log`, `git reflog`.

## One line

Git and the harness already keep almost everything per tree, so build, judge and review in
parallel worktrees outside the repository, and let one serial lane rebase, judge the exact
commit in the main tree, accept and fast-forward; only the lane accepts, because acceptances
cannot be merged and git will sometimes merge them anyway.
