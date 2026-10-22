# Project guidance for Claude Code

## What this is

A statically linked CPython for `wasm32-wasip1` with numpy and pandas
compiled in as builtin modules, built from pinned sources as a few
releases rather than a build of every version of every package.
The product is the artifact set (`python.wasm`, the snapshot, the stdlib
zip, the manifest) and the small `wasi_python` wheel that carries it.
Read `context/constitution.md` first: it is the mission, the goal and
the hard constraints, and it governs this file. Then `README.md` and
`context/README.md`.

## Rules that bind all work

- **Upstream patches are few, recorded and temporary** (constitution
  §4.1, amended 2026-10-17). An adaptation is a recipe file under
  `recipes/` first (a cross file, a compiler wrapper, a rename header,
  a stand-in module). An unavoidable source change is a patch file
  under `recipes/patches/`, reviewed, hashed in `MANIFEST`, named in the
  CHANGELOG, with its upstream pull request drafted under
  `context/upstream/patches/` for the owner to send, and deleted once
  upstream releases the fix. `scripts/steps/apply_patches.sh` applies
  them, and the release fails on any difference from a pinned tarball
  other than exactly the recorded patches (spec 020).
- **Every input is pinned by URL and SHA-256** in `downloads/SHA256SUMS`
  and verified before use. Downloads are untrusted: they unpack under
  `downloads/` and `build/`, never into the system, and run only as
  build tools or under wasmtime.
- **uv only.** `uv run …`, `uv sync`; never a bare `python` or `pip`.
  `ruff check`, `ruff format --check` and `pytest` stay green on `src/`
  and `tests/`.
- **Prior art is studied, never copied.** `context/prior_art/` holds
  shallow clones, git-ignored and read-only. Read, grep, cite, describe;
  every line of code here is ours. Check the licence right after
  cloning and record it in `context/prior_art/README.md`. Building a
  dependency from its released source is not copying.
- **Tests count operations, never wall-clock.** Cold-start and speed
  numbers belong in a research memo as benchmark facts.
- **Artifacts never live in git.** `*.wasm`, `*.cwasm`, `*.zip` and the
  build trees are ignored; hashes and sizes are recorded in the memo or
  the manifest.
- **Nothing lands unreviewed.** A built change is reviewed by a fresh
  agent or a person who did not write it, given the specification and
  the diff, before it lands; the review is recorded under
  `context/reviews/` and cited in the landing notes. Findings are fixed
  or answered in writing first.
- **Structure is reviewed, not only behaviour** (spec 108; the design
  review `context/research/2026-10-20-a-design-review-of-the-runner.md`).
  A specification is **structural** when its change to `src/` adds a
  module-level mutable or lock outside `_process.py`, a use of
  wasmtime-py's private API outside `_wasmtime_ffi.py`, a platform branch
  (`sys.platform`, `os.name`, `platform.system()`) outside
  `_platform.py`, a test seam that is not on the process object, or takes
  a module past the size ceiling or a function past 80 lines. Its Kind
  line carries the bold word **structural**, and it is reviewed before it
  is built, as a change to the build recipe is (constitution §5.6),
  against the eight-row rubric in `context/reviews/README.md`. The rules
  checks of specs 103 to 108 hold the letter of this; the review holds
  its spirit. Before every release, a fresh agent writes a structural
  review of `src/` against the same rubric,
  `context/reviews/<version>-structural-review-YYYY-MM-DD.md`, beside
  the security review; the release waits on its High findings, and the
  judge refuses a released version without one.
- **Code speaks for itself** (the owner, 2026-10-20). A code file
  (`src/`, `tests/`, `scripts/`, `release/`) names no specification,
  memo, review, finding ID or `context/` path (in comments and
  docstrings; the judge reads `context/` as data): its comments and
  docstrings give the reason in words, and the number lives in the
  specification that cites the file. A `context/` document may cite and
  link code files. `src/` is cleared by spec 107 and held by its check;
  `tests/`, `scripts/` and `release/` by spec 109. A page under `docs/`
  and the README name no specification, question, decision, wave or
  review number, no `context/` path and no name from
  `context/embedders.txt`; the judge's scans read them whole (spec 122).
- **Commit or push only when asked.** A specification may be built in
  its own worktree outside the repository, on a local `spec/NNN-<slug>`
  branch (constitution §4.14); no other branch or worktree unless
  asked. Never `git checkout`, `git restore` or `git stash` a file that
  carries uncommitted work.
- **All project knowledge lives in this repo** under `context/` (the
  agents' memory) and `docs/` (what we tell users); no out-of-repo
  memory.
- **Every package runs its own tests in the release** (spec 063). A
  specification that adds a package adds its suite's groups under
  `tests/upstream/` and to a shard in `tests/release_shards.toml`, or
  says in `tests/upstream/packages.toml` why not yet; the judge checks it.

## Working autonomously

How an agent works here alone, drawn from the ports that converged
(`context/research/2026-10-16-how-autonomous-ports-were-run.md`).
The judge is `uv run pytest`; its scoreboard is the progress signal
(`context/specifications/002-the-progress-harness.md`).

1. **Orient from the scoreboard, not from memory.** Start every session
   with `uv run pytest -m "not slow"`. Read its last twenty lines: the
   count per goal, the failures, the ratchet, and the `next:` line.
   Then read the specification you are on.
2. **Pick work by what it unblocks.** The `next:` line names the
   prerequisite that blocks the most checks. Work on the
   specification that provides it. One specification per builder; at
   most three parallel-safe and three build-class specifications in
   flight (six build-class from 2026-10-19, the owner; four earlier that
   day); landings go by waves of up to five reviewed specifications
   (constitution §5.7, the owner, 2026-10-19: one package or stacked
   chain, two other build-class, the rest parallel-safe; the toolchain
   alone with judge-only changes). A builder enters a wave by rebasing
   onto its tip in the lane's order and naming every conflict it
   resolved; the lane rebuilds once, accepts once, and a fresh agent
   reviews the integration. Build-class means it touches `scripts/`,
   `recipes/`, `downloads/SHA256SUMS` or the release workflow. A
   specification whose dependency is built and reviewed may be built on
   that dependency's reviewed tip (§4.14, a stacked build), rebasing
   onto main, or the wave's tip, when the base lands. Every
   specification is "built" only once its builder has dispatched the
   release workflow on its branch and read the run: every red line a
   growth line or G7, the run id in the landing notes; the build review
   names its run. A builder that only rebased onto a wave's tip (every
   conflict named, the fast tier green) dispatches no new run: the
   wave's dry run on three systems is the check (the owner, 2026-10-20).
   Its CHANGELOG lines go under the one unreleased
   section, which becomes "0.1.0" (no more alphas, the owner, 2026-10-19).
3. **Write the check before the code.** A new behaviour gets a check
   (or a gap entry naming its closer) first. A new failure mode, once
   seen, becomes a check, so it cannot come back.
3a. **Loop on the fast tier; run the full judge once.** `uv run pytest
   -m "not slow"` skips the guest jobs, the oracle and the upstream
   suites (3 min 48 s on darwin-arm64, against about 9 min for the full
   run, 2026-10-18). Iterate on it while building or reviewing, and run
   a slow check you are changing alone by its node id. Both tiers may
   run on several cores with `-n 6` (spec 052): the same verdicts, about
   a third of the time; use `-n 3` when another agent's judge is running
   on the machine. The full judge runs once per stage, at its end, and
   on GitHub Actions (the owner, 2026-10-19): the builder's dispatch of
   the release workflow before it writes "built", the reviewer's own
   dispatch on the reviewed commit before its verdict, or the builder's
   run when it is on that exact commit (constitution §5.6; the owner,
   2026-10-20), each reading the run back (`gh run view <id> --json jobs`,
   `gh run download <id> -n release-record-1`). A branch run may reuse
   a set the cache holds under its commit's key (spec 101); its verdict
   is the same verdict, and a release record's `meta.set_source` says
   which. Locally, builders and
   reviewers run the fast tier and single node ids only. The one local
   full judge is the lane's `uv run pytest -n 3` on the wave's tip.
   That is the judge's normal tier. The release tier (spec 102) runs on
   a tag, on the dry run on main, and in the lane's release acceptance
   before a tag, never at a landing; a builder whose specification
   changes a release-tier row writes its block in
   `context/release-tier-claims.toml` from its local `--tier release`
   runs by node id, and the first CI run of its release groups is the
   dry run on main. Only a specification that changes the release-tier
   CI job itself dispatches a branch run with `release-tier: true`, and
   says so in its Kind line (the owner, 2026-10-21).
   Until spec 092 (the judge reads a release record) lands, one
   reviewer per wave also keeps a local `-n 3` record for the lane's
   sameness line, at a time the lane grants. At most three release
   workflow runs are live at once (the plan is Pro); a fourth waits.
   The local budget, which the lane grants slots from: while
   `build/lane.lock` exists in the main tree (the lane's acceptance or
   the integration fast tier is running), no other tier of the judge
   runs, the fast tier included, only single node ids; no container
   build starts; at most one native build runs. Otherwise, at most one
   native build, one container build and one fast tier at once (the one
   reviewer's `-n 3` record takes the fast tier's place), and never two
   full judges. Ask the lane for a build or judge slot before starting
   one.
4. **Never weaken the judge to get a pass.** Do not edit a check, a
   golden output, `tests/known_gaps.toml`, the upstream suites'
   allowances (`tests/upstream/*.toml`, `tests/upstream/expected/`, CPython's plan
   `tests/upstream/python/`)
   or `context/progress/` to turn a run green. Changing the judge is its own change, with a
   reason, and the review sees the judge-hash line.
5. **No pass is lost quietly.** A run that loses an accepted pass or
   grows fuel or bytes is red. Fix it, or accept growth with a stated
   reason (`--accept "<reason>" --accept-growth "<why it grew>"`). New
   passes never pay for a lost one.
6. **Accept only green, reviewed work.** `uv run pytest --accept
   "<reason>"` records the state in `context/progress/`; the history
   is append-only. A changed judge needs `--accept-judge "<reason>"`;
   a machine without artifacts runs with `--partial "<reason>"`. See
   `context/progress/README.md`.
6a. **Only the lane accepts.** A builder judges without `--accept`: on
   GitHub Actions, and in its worktree the fast tier against the frozen
   artifact set its class allows. The lane compares each entry's
   rebase with its reviewed diff, judges the wave's tip in the main
   tree on three cores, accepts once with every specification's
   reasons, and fast-forwards main. It records `uv run python
   tests/harness/sameness.py` between each reviewer's record (or the
   wave's dry-run record, once spec 092 lands) and its own; a
   difference is clean only when it is a check blocked in that worktree
   or a row in another entry's claim list; any other difference ejects
   the entry until the check is fixed, never a re-run (spec 052,
   Decision 11). The wave's dry run, serial on three systems at 1e-4
   (gather G5), is the serial confirmation Decision 11 asks for; it
   replaces the local serial acceptance every fifth landing (the owner,
   2026-10-19). Progress files are never merged: take main's and accept
   again.
6b. **Tag only what a dry run passed.** Before a release tag, the lane
   makes the release acceptance on main's tip (`uv run pytest -n 6
   --tier release --accept "Release <version>: the release tier"`,
   at `-n 6` only while `build/lane.lock` is held and nothing else runs
   on the machine, else `-n 3`; it may be the last wave's own acceptance
   when the wave's tip carries the version bump, after a normal-tier run
   without `--accept` is green; decisions.md, 2026-10-22),
   checks every release-tier difference against
   `context/release-tier-claims.toml` (spec 102, Decision 6), then
   dispatches the release workflow on main's exact commit, which runs
   the release tier itself, and waits for every job to pass on all
   three systems. Only Windows runs there; a landing
   never runs it, so a check can pass the lane and still fail the
   release (0.1.0a4's tag run failed on Windows, 2026-10-18). Commits
   that touch only `context/`, `CHANGELOG.md` or `README.md` may follow
   the dry run if the fast tier passes on the commit tagged (the owner,
   question 95, 2026-10-18); any other file means a new dry run.
7. **Two strikes, then write it down.** After two failed attempts on
   one hypothesis, stop. Record where you stood and why in the memo
   or specification, and move to work that does not depend on it.
8. **The implementer never reviews.** A fresh agent gets the
   specification and the diff, re-runs the scoreboard, and writes the
   review under `context/reviews/`. Review follows risk (the owner,
   2026-10-19): the pre-build review is required where constitution §5.6
   requires it (the guest's imports or exports, the artifact set, the
   build recipe), for the runner's code and for a structural change
   ("Structure is reviewed", above), optional for a judge-only or
   context-only specification; a Low finding or a note needs no further
   review round when its answer is in writing or touches only `context/`.
   A Low finding that touches only `context/` may be written in by the
   reviewer itself, as a commit of the exact text once the builder hands
   the branch over; a code fix stays the builder's, and the lane reads
   it against the finding (the owner, 2026-10-19). Before asking for a
   review, the builder writes the self-check list
   (`context/reviews/README.md`); the reviewer reads the builder's CI run
   when it is on the exact commit reviewed, else dispatches its own
   first (the owner, 2026-10-20), then works its checklist in its time box. A wave's
   integration gets its own fresh reviewer, one who reviewed none of
   its entries.
9. **Commit only what you mean.** Before every commit, read `git diff --cached --stat`: a
   `git mv` or an earlier `git add` stays staged and rides along. A commit on `main` is green on
   its own; when two pieces of work share the tree, check the commit in a clean clone. A
   worktree's branch carries exactly one specification.
10. **Keep output short.** Logs go to files under `build/`; a failure is
   one line with its reason.

## Explaining things

Short sentences. One idea each. Define a term of art the first time it
appears. Say the key idea more than once in different words. End with a
one-line version.
