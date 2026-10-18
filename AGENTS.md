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
- **Commit or push only when asked.** A specification may be built in
  its own worktree outside the repository, on a local `spec/NNN-<slug>`
  branch (constitution §4.14); no other branch or worktree unless
  asked. Never `git checkout`, `git restore` or `git stash` a file that
  carries uncommitted work.
- **All project knowledge lives in this repo** under `context/`; no
  out-of-repo memory.

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
   most three parallel-safe and one build-class specification in
   flight; one landing at a time (constitution §5.7; build-class means
   it touches `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the
   release workflow).
3. **Write the check before the code.** A new behaviour gets a check
   (or a gap entry naming its closer) first. A new failure mode, once
   seen, becomes a check, so it cannot come back.
4. **Never weaken the judge to get a pass.** Do not edit a check, a
   golden output, `tests/known_gaps.toml`, the upstream suites'
   allowances (`tests/upstream/*.toml`, `tests/upstream/expected/`)
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
6a. **Only the lane accepts.** A builder runs the judge in its worktree
   without `--accept`, against the frozen artifact set its class
   allows. The lane rebases, compares with the reviewed diff, judges
   the exact commit in the main tree, accepts, and fast-forwards main.
   Progress files are never merged: take main's and accept again.
7. **Two strikes, then write it down.** After two failed attempts on
   one hypothesis, stop. Record where you stood and why in the memo
   or specification, and move to work that does not depend on it.
8. **The implementer never reviews.** A fresh agent gets the
   specification and the diff, re-runs the scoreboard, and writes the
   review under `context/reviews/`.
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
