# Review of 093 — An abandoned turn on Windows (the build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh Claude agent (Opus 5.5), not the author; time box 25 minutes (parallel-safe)
- **Reviewed:** `97be88a..dc49486` on `spec/093-an-abandoned-turn-on-windows`, plus this review's write-in commit `ddbade7` (L2, L3; context only)
- **Run:** the builder's release run 39357013719 on `e58c07c`, every job green; I read its job list (`gh run view`). `judge (windows-2025, own-guest)` reports 413 passed, 0 failed. 078's dry run had 412 passed and 1 failed, so the check ran and passed there (INFERRED: the log is quiet and does not name the node). The commits after `e58c07c` (`dd2d9a1`, `dc49486`) touch only the specification. I dispatched no new run. §5.6 allows a local re-run, and the runs below are it.
- **Re-ran:** (`build/lane.lock` absent before each run; artifact set `WASI_PYTHON_ARTIFACTS=<main>/build/artifacts`, the worktree's env)
  - `uv run pytest "tests/checks/test_v1_2_hostile_guest.py::test_an_abandoned_turn_keeps_its_session_busy"` five times on `dc49486`: 5 passed, exit 0 each (1.4 to 1.8 s).
  - Three mutants of my own on that node, each with `runner.py` restored byte for byte after (`git status` clean):
    - R1: the guest body never runs an abandoned home's steps. **Fails**: the child misses its 120 s limit, because `s.close()` waits on a session that stays busy.
    - R2: `_abandon_turn` ends the session `error` but leaves `busy` set. **Fails** the same way.
    - R4: `_Home.finish` marks the home abandoned but does not stop it. **Passes**. See N1. This gap was 078's and is not new here.
    - (R3, `finish`'s run-now branch made to skip its step, failed too, but through other callers of `finish`, so it says nothing about this check.)
  - `uv run ruff check src tests`: all checks passed. `uv run ruff format --check src tests`: 108 files already formatted.
  - `uv run pytest tests/checks/test_rules.py`: 42 passed, 2 skipped, after the write-in.

## (a) The cause

The cause is right. I read `_Home.finish`, `_Home.body`, `_join_guest`, `_on_guest_thread`, `_session_turn` and `_abandon_turn` on main.

- **What the child forces.** The stand-in `serve` raises `KeyboardInterrupt`. Then `_on_guest_thread`'s `except` calls `home.stop(e)`, so `home.raised` is set. The stand-in join raises `SystemExit` in the `finally`, so `run` leaves without joining.
- **The two paths.** `_session_turn` then reads `home.done`. If the guest is still running, `finish` (under `home.lock`) marks the home abandoned and leaves `_abandon_turn` to the guest body. The body runs it under the same lock once its turn has returned. If the guest has already ended, either `finish` runs the step at once, on the caller, or `_session_turn` takes its normal error path. Each path clears `busy` only after the guest has ended, or on the guest's own teardown.
- **Why Windows differed.** It is a timing difference. The guest's stop arrives at its next epoch check, and on Windows that came before the caller's next look. That is exactly the Windows line pair. Nothing in these functions depends on the platform.
- **Could a real bug hide behind the gate?** The two bugs that print the Windows lines are a home that tears down at once and a turn that frees `busy` while its guest runs. The new check kills both, the builder's mutants M1 and M2. And it passed on Windows in 39357013719, with `busy … True True` and `torn down on ['wasi-python-guest']`. So on Windows too the runner holds `busy` while the guest lives and tears down on the guest thread. The gate sits inside the stand-in's in-wasm count, so a store closed while the guest is held still shows up in line 6. The gate widens the window the check watches. It does not cover anything up.
- **What the gate gives up.** The check now tests one order only: the guest still alive when `finish` takes the lock. The other order, where the guest ends before `finish` runs and `finish` runs the step at once on the caller, has no row. The old check reached that order only by luck, so this is no loss, but it is not covered (N1).

## (b) It still fails on real bugs

- The builder's mutants (EXECUTED by the builder, logs READ):
  - `rows-mutant-turn-frees-busy.log`: `False True`, the second turn told the session ended, and `closes while wasm ran ['MainThread']`, a store closed under wasm.
  - `rows-mutant-home-tears-down-at-once.log`: `False True` and `torn down on ['MainThread']`. Under that mutant the old check printed exactly the Windows lines, so the old check could not tell this bug from a correct runner whose guest ended first. That is the point of Decision 3.
- My R1 and R2 fail (EXECUTED). They fail through the child's 120 s limit, not an assertion line. That still fails the check: the limit is a backstop for hangs, and here it catches a session left busy forever.

## (c) Old assertions

All seven lines are still asserted. Five are unchanged. Line 3 gains the guest thread's liveness and line 5 gains the thread the teardown ran on, so both are stronger. The node id is unchanged. Before, the session row read `busy` by luck. Now it reads it at a fixed point.

## (d) Wall-clock

None decides a verdict. `entered.wait(60)`, `gate.wait(60)` and `held[0].join(60)` each return at once on a correct runner, because each is woken by an event set just before. A timeout only turns a hang into a failure. If `entered` times out, `held[0]` raises `IndexError` and the child exits non-zero. No sleep is added.

## Acceptance criteria against evidence

1. The new check is certain: met. Twelve rows identical in the builder's logs (READ) and five passes of mine (EXECUTED). The "(the Windows order)" wording overstated the second row; L2 fixes it.
2. Seen failing first: met. Two builder mutants (READ) and two of mine (EXECUTED).
3. Windows: met. `judge (windows-2025, own-guest)` green in 39357013719, with no red line (READ, from the job list).
4. Fast tier and linters: ruff green (EXECUTED). The builder's fast tier on `bac6899` (READ): lost 0, 0 fail. The later spoiled runs are explained, and the release run is the record.

## Findings, most severe first

1. **Low (for the lane): the base is old and the Status line is stale.** The Status line says the spec "enters wave 1 first", but wave 01 landed without it (main `e8ba20a`). The branch is 39 commits behind main. `git merge-tree` finds one conflict, in `CHANGELOG.md`: both sides add an entry under the unreleased section. Keep both. The test file auto-merges. Since `97be88a`, main has not touched `_Home`, `finish`, `_session_turn`, `_abandon_turn`, `_drive_turn` or this child. Fix text for the Status line, once rebased: "rebased onto main `<tip>` (CHANGELOG-only conflict, both entries kept); not in wave 01".
2. **Low (written in): criterion 1 called its second row "the Windows order"** (`093-…md:116`). In that row the guest thread is still held, so nothing has been torn down. That is not the Windows order. The text now says what the row shows, and names the old child's row "old, guest ends first" as the true Windows order.
3. **Low (written in): `_run_turn` is not a runner function** (`093-…md:43`, `:126`). The code is `_session_turn`, and both places now say so.

Notes, which need no round:

- **N1 (coverage, 078's).** In this child, `finish`'s own `self.stop(_Stopped())` changes nothing, because the forced-out `serve` has already set `home.raised`. Mutant R4 survives. And no row covers `finish`'s run-now branch from `_session_turn` (the guest ends between the unlocked `home.done` read and `finish`). Neither gap is 093's to close. A follow-up row would need a child whose home is forced out without an exception already recorded. It could become a roadmap line if the owner wants one.
- **N2 (the record).** The claim list expects "gained 0". The CI ratchet line says "gained 1", probably because the release shard compares against its own baseline (INFERRED, not checked). My local single-node run against `9c6ba6db2d` showed `gained 0` and `judge changed: tests/checks/test_v1_2_hostile_guest.py`, as claimed.

## Claim list and flags

- Diff against claims: one check's child and its expected lines and docstring, `CHANGELOG.md`, the specification, and the evidence folder. No `src/` line. Exact.
- Flags: both reasons begin `093:`. Neither has an inner double quote, `$`, backtick or `!`, so both paste safely into bash and zsh. `--accept-judge` is present, as a judge change needs.

## Constitution checks

- §4: no upstream patch, no new input, no artifact in git, uv only. Tests count events, never time. Prior art is untouched.
- §7: nothing tripped. The judge change is its own change, with a reason, and is named for `--accept-judge`. No allowance or golden file was edited to turn a run green. The expected lines changed because the check now asserts more.

## Disposition

1. L1: for the lane at rebase.
2. L2: fixed in `ddbade7` on the branch.
3. L3: fixed in `ddbade7`.

## Verdict

Lands: the cause is a check that raced an order spec 078 never promised. The fix makes the order certain without a sleep, and it kills the bugs the old lines could not tell from a fast guest. The only rebase conflict is in `CHANGELOG.md`.
