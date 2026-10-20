# Review of 082 — Inline pytest sessions keep wasmtime's signal handlers (build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author; time box 30 minutes (parallel-safe,
  judge-only).
- **Reviewed:** `e00d394..9d37abb` on `spec/082-inline-sessions-keep-the-handlers` (code at
  `6881242`; `6881242..9d37abb` touches only the specification).
- **Run:** none dispatched by this review. Read the builder's release run 39364504472 (on
  `6881242`; the tip's delta is context only).
- **Re-ran** (darwin-arm64, worktree; `build/lane.lock` absent before every run):
  - `uv run pytest -q -n 3` on the new file, `test_plugin.py`, `test_landing_lane.py`,
    `test_upstream.py`, `test_several_cores.py`, `test_checks_wiring.py` → 208 passed, exit 0;
    ratchet lost 0, grew 0, `judge changed: tests/conftest.py, tests/unit/test_inline_sessions.py`.
  - Two mutants and a probe (finding L1), with `PYTHONDONTWRITEBYTECODE=1`.
  - Linux arm64, in the `wp040-arm64` image, from a `git archive` of `9d37abb`, serial: the review's
    cross-file order, with the fix and with `tests/conftest.py` as at `e00d394` (criterion 2a).
  - The fast tier, `-n 3`, against the main tree's artifact set (result in the Disposition).

## Acceptance criteria against evidence

1. **Seen failing first** — met. EXECUTED here too: with the flag dropped from `inline_run`, the
   stand-in check fails, "the inline session replaced the handler: 0x104b367d8" (faulthandler's
   handler, not `SIG_IGN`). The end-to-end check passes on darwin, as it must.
2. **Linux, end to end** — met. READ in 39364504472: `judge (ubuntu-24.04, own-rest)` shows
   `tests/unit/test_inline_sessions.py ..`, 1082 passed, 6 skipped, lost 0, grew 0.
   - **2a. The review's cross-file order, now reproduced** (EXECUTED, Linux arm64; this answers the
     builder's questions 4 and 5).
     - Order: `test_guest.py`, `test_plugin.py`, `test_runner_calls.py`, `test_inline_sessions.py`.
       - With `e00d394`'s conftest: 9 guard refusals in `test_runner_calls.py`, the review's nine
         exactly. Both new checks also fail. The stand-in reads `0xaaaaaf86f824`. The end-to-end
         check fails at its first assertion: "the guard refused before the inline session, on
         SIGSEGV". So that message correctly names an earlier file's inline session.
       - With the fix: 0 refusals, and both new checks pass.
     - Order: `test_guest.py`, `test_landing_lane.py`, `test_runner_calls.py`,
       `test_runner_mounts.py`, `test_inline_sessions.py`.
       - Base: 11 refusals (9 in calls, 2 in mounts).
       - Fix: 0.
       - Here mounts shows 2 refusals, not the review's 7. Twelve tests were skipped without the
         build trees, which likely accounts for the gap.
     - **Failures in both trees, not 082's.** They are the same with the base conftest and with
       the fix.
       - `test_host_paths_are_found_in_every_input_the_guest_sees`: the copy sits at `/src`, so a
         path-prefix collision.
       - `test_unnamed_skip_and_a_skip_naming_a_met_need_are_failures`: a CI need is met in the
         container.
       - Seven `test_landing_lane.py` errors: `git clone /src` fails because an archive is not a
         repository.
       - One flaky `test_a_files_times_and_inode_are_the_drivers`: base only, and it runs before
         any inline session.
3. **Every inline session still passes** — met. EXECUTED: 208 passed, as the notes say.
4. **Fast tier and linters** — READ in the builder's notes (lost 0, 0 fail; ruff green).
   - My fast tier ran against the main tree's set, which has since moved to 086's. It is not
     comparable, and none of its failures touches 082's files (Disposition 3).
5. **The release** — met. READ: one red job, `judge (windows-2025, own-embedding)`, 2 failed. The
   two are `test_the_removal_never_deletes_what_the_guest_may_not[home]` and `[private]`, 084's
   rows, which 094 fixed on main. `upstream-groupby` shows success (attempt 2). No GREW line and
   no G7.

## The builder's questions

1. **One fixture override, or a flag at each call site.** The override is right.
   - Today there are five in-process `runpytest` call sites: `test_plugin.py` ×3,
     `test_landing_lane.py`, `test_upstream.py`. A flag at each site would miss the next one
     someone adds.
   - Overriding a fixture of the same name in a conftest, and requesting the original, is pytest's
     documented pattern.
   - Setting the attribute on the instance works. `runpytest_inprocess` calls `self.inline_run`,
     and an instance attribute shadows the class function. Mutant B proves it.
   - `monkeypatch` undoing the attributes is harmless. Plain assignment would also do, since the
     fixture is function-scoped.
2. **Does it cover every in-process path in pytest 9.1.1?** Yes, through pytester (READ in
   `.venv/.../_pytest/pytester.py`).
   - Through `inline_run`: `runpytest` (inprocess), `runpytest_inprocess`, `inline_runsource`
     (1076) and `inline_genitems` (1085).
   - Through `parseconfig`: `parseconfigure` (1264), and from it `getmodulecol` (1330),
     `getitems`, `getitem`, `runitem` and `getpathnode` (1024).
   - What it does not cover:
     - `genitems` and `getnode` take a config the caller already made.
     - The `_config_for_test` fixture is a separate fixture, and nothing uses it.
     - `tests/harness/gather.py:540` calls `pytest.main` directly. It runs only in the `gather.py`
       CLI process. No test calls `collect()` in process (READ, grep). If one ever does, it needs
       the same flag (note N2).
   - The `parseconfig` half has no check (L1).
3. **Is the ctypes `sigaction` code safe?** Yes, on the hosts the project runs on.
   - **Layout.** The handler union is the first member of userspace `struct sigaction` on glibc
     (x86_64, aarch64), on musl and on macOS. glibc on MIPS puts `sa_flags` first, but MIPS is
     not a host here.
   - **Buffer size.** 1024 bytes is larger than any of them: glibc 152, musl 152, macOS 16. libc
     reads and writes only its own `sizeof`.
   - **What is kept.** The check copies the saved bytes and changes only the first word. Mask,
     flags and restorer are kept. On glibc, `SA_RESTORER` in the saved flags is harmless:
     glibc's wrapper sets its own restorer anyway.
   - **Restoring.** Putting back the saved bytes reinstates faulthandler's handler and flags
     exactly. faulthandler's own saved previous handlers are untouched, with or without the fix.
     So the process ends in a consistent state.
   - **Lookup.** `CDLL(None)` is a fresh handle each call. Setting `argtypes` on it cannot clobber
     another user's `sigaction` prototype, such as the runner's.
   - **`SIG_IGN` on SIGABRT.** It is harmless for the check's window: `abort()` resets to the
     default action and still ends the process.
   - **The `enabled_here` branch** (outer run without faulthandler). It switches faulthandler on,
     then off. That order is safe: `disable()` puts back what `enable()` found, wasmtime's
     included. So "never switches faulthandler off and on" holds in the order that matters.
   - The check still catches the bug in this branch, because the inner plugin's `disable()`
     drops `SIG_IGN` there too.
4. **The Linux gap in the cross-file order** — closed by this review (criterion 2a, EXECUTED).
   Nothing is asked of the builder.
5. **The 16 refusals never reproduced** — reproduced in the same container family as 080's
   review: 9 of 9 in `test_runner_calls.py`, and 2 in mounts with 12 tests skipped (criterion 2a).

## AGENTS rule 4: does the override change other tests or hide a failure?

No.
- **What it changes.** It only blocks one plugin in the inner sessions, and their roots are
  pytester's temporary folders.
  - No inner test sets `faulthandler_timeout` or uses faulthandler (grep).
  - `foreign_steering` gains nothing, because blocking a plugin adds none.
  - The harness reads `PYTEST_ADDOPTS`, not `-p`.
  - The 208 inline-session tests pass unchanged.
- **Python exceptions.** An inner test that raises is reported by the inner session's own report.
  faulthandler plays no part, so no traceback is lost.
- **Hard crashes.** A crash (SIGSEGV) inside an inner session kills the whole process. The outer
  faulthandler is still enabled and still installed, under wasmtime's chaining handler on Linux,
  so it dumps every thread.
- **A side effect that helps.** Before the fix, each inner session's `pytest_unconfigure`
  re-enabled faulthandler on the inner session's stderr fd. Under `runpytest_inprocess`'s sys
  capture that is fd 2. Now an inner session never moves the outer handler's target.
- **The outer judge.** It keeps faulthandler (Decision 4).

## Findings, most severe first

1. **L1 (Low): the `parseconfig` half of the fixture has no check** (`tests/conftest.py:25–26`).
   - Removing its flag fails no check on the branch. EXECUTED as mutant A: both new checks pass.
   - It does fail this probe, which passes with the fix (EXECUTED):
     `config = pytester.parseconfigure(); config._ensure_unconfigure()` between the stand-in's
     install and read.
   - No call site uses `parseconfig` today, so nothing is wrong now. But the claim "every
     in-process pytester session (inline_run, and parseconfig …)" is only half held.
   - **Fix (the builder's, code):** add a third check,
     `test_a_parseconfigure_keeps_a_handler_installed_after_faulthandler`. It is the stand-in
     check with that pair of calls in place of `makepyfile` and `runpytest`. Or narrow the claim:
     "parseconfig is wrapped; READ, and probed in the build review".
   - Mutant B (the flag dropped from `inline_run`) fails the stand-in check, as intended.
2. **L2 (Low, self-check): not on main's tip.**
   - The branch is on `e00d394`. Main is `f7511b7` (wave 03).
   - A rebase conflicts only in `CHANGELOG.md` (`git merge-tree`), and the fix is trivial. No
     code file the spec touches moved on main.
   - The request carried no builder's self-check list.
   - **Fix:** the lane rebases and resolves the CHANGELOG hunk under `0.1.0a8 — unreleased`.
3. **N1 (note): the run is the builder's.** No run was dispatched on `9d37abb` itself. The
   delta from `6881242` is the specification only, so 39364504472 stands for it.
4. **N2 (note): one direct `pytest.main` outside pytester.** `tests/harness/gather.py:540`
   (`collect()`) runs `pytest.main` in process. Today that is only the gather CLI.
   - The spec's Scope says no other code in the judge's process switches faulthandler. That holds
     today.
   - A future unit test that calls `collect()` in process would need `-p no:faulthandler` there as
     well. One line in the spec's Scope would record it.

## Constitution checks

- §4: no `src/` line, no artifact, no recipe, no pin changes. The diff is `tests/conftest.py`, one
  new unit file, `CHANGELOG.md` and the specification, as claimed.
- The judge changes, and the lane accepts with `--accept-judge`; the flags are given.
- §7: nothing tripped. No check, golden file, known gap or allowance was edited.
- Tests count operations, not time.
- The claim list matches the diff, apart from L1's half-held claim.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. L1 — open.
2. L2 — for the lane.
3. Fast tier on `9d37abb` (reviewer, EXECUTED, `-n 3`, `WASI_PYTHON_ARTIFACTS` = the main
   tree's `build/artifacts`): 82/701 pass, 276 fail, 222 blocked; unit suite 1725/1740.
   - **This run cannot be compared with the builder's.** Main's tree is now at `a75e5d4`, with
     086's rebuilt set (wasi-sdk 34). The failures are the set's findings, such as "python.wasm
     is missing" and the licence notices, and seven artifact-bound `test_runner_mounts.py` units.
   - **None touches 082.** No failure is in the six inline-session files or the new file. There is
     no guard refusal anywhere in the log.
   - **What stands for the counted run instead:** the builder's fast tier on `e00d394`'s set (READ:
     lost 0, 0 fail) and CI's own-rest on both systems (READ: green).

## Verdict

**Lands.** The fix is correct, minimal and held where it matters: the cross-file order is now
reproduced on Linux, with 9 + 2 refusals before and 0 after. L1 and L2 are Lows with fix text, and
need no further round.

## One line

082 stops inline pytest sessions from dropping wasmtime's handlers; Linux shows 11 refusals before
and 0 after. It lands, with one Low: put a check on the `parseconfig` half.
