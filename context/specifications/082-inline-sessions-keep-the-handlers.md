# 082 — Inline pytest sessions keep wasmtime's signal handlers

- **Status:** **landed 2026-10-20 in wave 05** (090, 082) on main `c74d0f0`: accepted on `f70c666`, history line 86, 638/708 pass, 0 fail; the integration review `../reviews/wave-05-integration-2026-10-20.md` ("lands as merged at f70c666"); the dry run 39371419248 dispatched as main moved. Before: **built 2026-10-19** on `spec/082-inline-sessions-keep-the-handlers` from main `e00d394`, rebased onto main `f7511b7` after its build review (`../reviews/082-inline-sessions-keep-the-handlers-build-2026-10-20.md`), which says it lands; its L1 and N2 are answered and L2 is the rebase (see "Landing notes"). It enters wave 05. A judge-only specification (no line of `src/` changes), so its pre-build review is optional (AGENTS rule 8).
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, not build-class (§5.7). Files: `tests/conftest.py`, a new unit file `tests/unit/test_inline_sessions.py`, `CHANGELOG.md` and this specification. No line of `src/` changes; the artifact set does not change. It is a **judge change**: the lane accepts it with `--accept-judge`.
- **Depends on:** 071 (landed; the runner's signal guard, `_trap_handlers_ready`, Decision 9) and 080 (landed; its review's F1 names this follow-up). The roadmap reserves it.
- **Research it stands on:** spec 080's review (`../reviews/080-deterministic-recursion-fuel-2026-10-19.md`, F1, EXECUTED on Linux arm64: `units-arm64.log`, `triple-arm64.log`, `culprit2-arm64.log`); 071's research on when wasmtime installs its handlers (once, process-wide, at the first engine); pytest 9.1.1's `_pytest/faulthandler.py` and `_pytest/pytester.py` (READ, in `uv.lock`'s version); this specification's own runs on darwin-arm64 (EXECUTED, the landing notes).

## The problem

### What 080's review saw

On Linux, the serial unit tier had 16 `RuntimeError`s from 071's guard: nine in `tests/unit/test_runner_calls.py`, seven in `tests/unit/test_runner_mounts.py`. Those tests make real engines, and some make the guest trap. The guard refused them: "wasmtime's handler for SIGSEGV was replaced after the first run". It happens only when a file that runs an inline pytest session (`test_landing_lane.py`, `test_plugin.py`) runs after a file that made an engine (`test_guest.py`) and before the runner's files. With the outer session's `-p no:faulthandler`, there were none. It is pre-existing since 071. The release never meets it: no shard puts an inline-session file and a runner file in one Linux process.

### The cause

pytest's faulthandler plugin is not safe to nest in one process.

- **The outer session** enables faulthandler at its start. faulthandler saves the handlers it replaces (`SIG_DFL`) and installs its own for SIGSEGV, SIGFPE, SIGABRT, SIGBUS and SIGILL.
- **The first engine**, on Linux, makes wasmtime install its own handlers for SIGSEGV and SIGILL (and SIGFPE on x86_64), over faulthandler's, once per process. wasmtime chains to the handler it found.
- **An inline session** (`pytester.runpytest`, in process) runs the plugin again. Its `pytest_configure` calls `faulthandler.enable()`, which installs nothing: it is already on. Its `pytest_unconfigure` calls `faulthandler.disable()`, which puts back the handlers faulthandler saved at the outer start, `SIG_DFL`, and so drops wasmtime's. Then it calls `enable()` again, because faulthandler was on before. Now faulthandler's handlers are installed and wasmtime's are gone.
- **The guard is right.** wasmtime installs its handlers only once, so they never come back. A trap in the guest would now reach faulthandler and end the process. The guard sees a handler that is not in wasmtime's library and refuses the call, as 071 meant.

One idea, said twice: the inner session's off-and-on of faulthandler drops every handler installed after the outer session began. Any handler installed after faulthandler is lost.

## Intent

Running an inline pytest session inside the judge leaves the process's signal handlers as it found them. A serial `uv run pytest` on Linux, in any file order, never turns the runner's guard against a real-engine test because an inline session ran before it. The runner keeps its behaviour; the judge's own sessions stop disturbing it.

## Decisions

1. **The judge's `pytester`, once, not each call site.** `tests/conftest.py` overrides pytest's `pytester` fixture with one that requests pytest's own and wraps two of its methods: `inline_run`, through which `runpytest` (in process), `inline_runsource`, `inline_genitems` and `getitems` all go; and `parseconfig`, through which `parseconfigure` goes (it runs the plugins' `pytest_configure`). Each puts `-p no:faulthandler` first. Every inline session there is today (`test_plugin.py`, `test_landing_lane.py`, `test_upstream.py`) and every one added later gets it without a line of its own.
2. **`-p no:faulthandler`, not a subprocess.** The review named both. A subprocess per session would cost a process start per case and change what the inner sessions share with the outer one (`sys.path`, imported modules). Blocking the plugin changes only the plugin.
3. **Nothing is lost by it.** The inner session runs in the outer process, and the outer session's faulthandler stays on throughout, so a crash or hang inside an inner session still dumps every thread's traceback. The inner plugin only re-did what was already done.
4. **The outer judge keeps faulthandler.** Passing `-p no:faulthandler` to the judge itself would also fix it (the review's run), but it would drop the tracebacks of a real crash in a guest call or a hang in the judge. The fix stays where the harm starts.
5. **Not the runner.** The guard's refusal is correct and 071's message already says what to do. No line of `src/` changes.
6. **A check on every POSIX host, and one end to end on Linux.** The first check needs no wasmtime: a stand-in handler (`SIG_IGN` on SIGABRT, set and put back with `sigaction` through `ctypes`) plays wasmtime's part, installed after faulthandler, so it fails on macOS as on Linux without the fix. SIGABRT is one of faulthandler's signals, and ignoring it is harmless: `abort()` still ends the process. The whole `struct sigaction` is put back after, and faulthandler is never switched off and on by the check (which would itself drop wasmtime's handlers). The second check is the review's case: an engine, an inline session, and the runner's `_trap_handlers_ready()` still `None`. It means something only on Linux (elsewhere the guard always answers `None`); the release's `own-rest` shard runs it on Linux.

## Design

`tests/conftest.py` keeps `pytest_plugins = ["harness.plugin", "pytester"]` and adds a fixture named `pytester`:

- It requests `pytester` (pytest's own, from the plugin) and `monkeypatch`.
- It sets `pytester.inline_run` to a function that calls the original with `("-p", "no:faulthandler", *args)`, and `pytester.parseconfig` likewise. `monkeypatch` undoes both at the test's end.
- `runpytest_subprocess` is untouched: a session in another process cannot touch this one's handlers.

`-p no:faulthandler` works wherever it sits in the arguments: pytest reads `-p no:` before it imports its default plugins (`consider_preparse`, then `import_plugin`), so the inner session never loads the plugin. The inner sessions' roots are pytester's temporary folders, never the repository, so the judge's "steered from outside the judge" rule does not apply to them; and blocking a plugin adds none.

`tests/unit/test_inline_sessions.py`, three checks, each running one trivial inner session:

- `test_an_inline_session_keeps_a_handler_installed_after_faulthandler` (skipped on Windows, which has no `sigaction`): enables faulthandler if the outer session has not (and disables it after only then), saves SIGABRT's `struct sigaction`, installs `SIG_IGN` through `sigaction`, runs the inner session (`runpytest`, so `inline_run`), reads the installed handler, puts the saved struct back, and asserts the handler read was `SIG_IGN`.
- `test_a_parseconfigure_keeps_a_handler_installed_after_faulthandler` (skipped on Windows): the same stand-in around `pytester.parseconfigure()` and the config's `_ensure_unconfigure()`, so the `parseconfig` half of the fixture is held too (the build review, L1). The stand-in's install, read and restore are one helper both checks share.
- `test_an_inline_session_after_an_engine_leaves_the_guard_ready`: makes a `wasmtime.Engine()`, asserts `runner._trap_handlers_ready()` is `None`, runs the inner session, and asserts it is still `None`. The first assertion names the case where something before this check broke the guard, so a failure says which.

The new file has no entry in `tests/release_shards.toml`: it falls in `own-rest` (macOS and Linux), where the judge's own tooling runs.

## Scope

- **In:** the `pytester` fixture in `tests/conftest.py`; `tests/unit/test_inline_sessions.py`; `CHANGELOG.md`; this specification.
- **Out:** `src/` (no runner change, Decision 5); the outer judge's own faulthandler (Decision 4); sessions run in a subprocess (`runpytest_subprocess`), which need nothing; any other code that switches faulthandler in the judge's process (none today: the one check that does, 071's criterion 11, does it in a child process); a shard assignment that would run an inline-session file and a runner file together in the release (none today; with this fix any order is safe).
- **Out, and noted:** `tests/harness/gather.py`'s `collect()` calls `pytest.main` in process (line 540), outside pytester, so the fixture does not reach it. Today it runs only in the `gather.py` command's own process, and no test calls `collect()` in process; a test that ever does needs `-p no:faulthandler` there as well (the build review, N2).

## Acceptance criteria

1. **Seen failing first.** With `tests/conftest.py` as at `e00d394` and the new file present, `uv run pytest -q tests/unit/test_inline_sessions.py` on darwin-arm64 fails `test_an_inline_session_keeps_a_handler_installed_after_faulthandler`: "the inline session replaced the handler: 0x1024827d8", faulthandler's handler where `SIG_IGN` was. The end-to-end check passes there, as it must off Linux. With the fix, both pass (the landing notes).
   - **1a. The `parseconfig` half.** With the flag dropped from the fixture's `parseconfig` wrapper alone (`PYTHONDONTWRITEBYTECODE=1` and no `__pycache__`, so no stale bytecode masks the mutant), `test_a_parseconfigure_keeps_a_handler_installed_after_faulthandler` fails and the other two pass; with the fix, all three pass.
2. **Linux, end to end.** The release run on this branch: the job `judge (ubuntu-24.04, own-rest)` (x86_64, so SIGFPE is guarded too) passes both checks, so after an engine and an inline session the guard still finds wasmtime's handlers in a real Linux process. That shard runs serially, in one process. `test_guest.py` (an engine) runs before the new file, and `test_landing_lane.py` and `test_plugin.py` (inline sessions) after it, so the check's own inline session is the one it tests: the order inside the check is the review's (engine, then inline session), not the file order. Nothing in that shard checks the guard after the other files' sessions.
3. **Every inline session still passes.** `test_plugin.py`, `test_landing_lane.py`, `test_upstream.py`, `test_several_cores.py` and `test_checks_wiring.py` pass with the fixture in place (208 passed with the new file, `-n 3`).
4. **The fast tier and the linters.** `uv run pytest -m "not slow" -n 3` on the branch: lost 0, 0 fail, grew 0; `ruff check` and `ruff format --check` green on `src/` and `tests/`.
5. **The release.** Every red line of the release workflow on this branch is a GREW line, G7, or one of main's known Windows reds that spec 094 fixes (084's two removal rows), each named in the landing notes.

## For the lane

**What this claims**, each for the build review to check:

- 082: no line of src changes; the diff is tests/conftest.py, the new tests/unit/test_inline_sessions.py, CHANGELOG.md and this specification.
- 082: every in-process pytester session (inline_run, and parseconfig for parseconfigure) runs with -p no:faulthandler; subprocess sessions are untouched.
- 082: the outer judge keeps faulthandler on, so a crash inside an inner session still dumps its tracebacks.
- 082: the stand-in check fails on darwin-arm64 without the fixture and passes with it; it puts back the whole struct sigaction and never switches faulthandler off and on.
- 082: the parseconfigure check fails with the flag dropped from the parseconfig wrapper alone and passes with it, so both halves of the fixture are held (the build review, L1).
- 082: the end-to-end check passes on Linux x86_64 in the release run's own-rest shard (an engine, then the check's own inline session, and the guard still ready); no shard runs the review's cross-file order.
- 082: the record is lost 0, grew 0, gained 0 (the three new checks are unit tests, outside the goal counts), judge changed; no fuel or bytes move.

**The flags**, each pasted as is:

```
--accept "082: the judge's inline pytest sessions run with -p no:faulthandler, so they keep wasmtime's signal handlers and the runner's guard; no runner change"
--accept-judge "082: tests/conftest.py wraps pytester's inline_run and parseconfig with -p no:faulthandler; new tests/unit/test_inline_sessions.py holds both wrapped paths with a stand-in handler on every POSIX host and end to end on Linux; spec 080's review F1; no src change"
```

If the lane's run has a growth line, it is the base's, not this change's: name it with `--accept-growth` in the base's words, or answer it in the landing notes.

## Landing notes

- **Built** on `spec/082-inline-sessions-keep-the-handlers` from main `e00d394`.
- **Seen failing first (EXECUTED, darwin-arm64).** The new file with `tests/conftest.py` as at `e00d394`: 1 failed, 1 passed; the stand-in check read `0x1024827d8` (faulthandler's handler) where it had installed `SIG_IGN`. With the fixture: 2 passed.
- **The inline-session files (EXECUTED).** `uv run pytest -q -n 3` on `test_plugin.py`, `test_landing_lane.py`, `test_upstream.py`, `test_several_cores.py`, `test_checks_wiring.py` and the new file: 208 passed.
- **The fast tier (EXECUTED).** `uv run pytest -m "not slow" -n 3` against the main tree's artifact set (`WASI_PYTHON_ARTIFACTS`): 552/701 pass, 0 fail, 28 blocked (the worktree has no build trees); unit suite 1732/1740, 8 skipped; ratchet lost 0, grew 0, gained 0, `judge changed: tests/conftest.py, tests/unit/test_inline_sessions.py`. `ruff check` and `ruff format --check` green.
- **Not reproduced here:** the review's Linux serial order across files (`test_guest.py`, then `test_plugin.py`, then `test_runner_calls.py`). darwin has no guard to refuse. The Linux evidence is the end-to-end check in the release run (below), whose own inline session follows an engine in one process; no release shard runs the review's file order.
- **The release run on `6881242` (EXECUTED):** 39364504472. Every job green but two:
  - `judge (windows-2025, own-embedding)`: 2 failed, 176 passed; lost 2, grew 0. The two are `test_the_removal_never_deletes_what_the_guest_may_not[home]` and `[private]`, "skipped without a known need: a Windows guest deletes a read-only file itself (spec 084, C2)": main's known Windows reds, 084's two removal rows, which spec 094 fixes. Not this change's.
  - `judge (ubuntu-24.04, upstream-groupby)`: its pytest passed (2 passed; lost 0, grew 0); the job failed only uploading its record (`Failed to CreateArtifact: Unable to make request: ETIMEDOUT`, twice), a network failure. Re-run alone as attempt 2 of the same run: success.
  - So the run's one red job is the known Windows one; `gather` and the publishing jobs are skipped because of it, as on main until 094 lands.
  - No GREW line and no G7 anywhere.
  - `judge (ubuntu-24.04, own-rest)` and `judge (macos-15, own-rest)`: 1082 passed, 6 skipped; `tests/unit/test_inline_sessions.py ..` on both, so on Linux x86_64 the guard found wasmtime's handlers before and after the check's inline session. Lost 0, grew 0, gained 0, `judge changed: tests/conftest.py, tests/unit/test_inline_sessions.py`.
- **The build review** (`../reviews/082-inline-sessions-keep-the-handlers-build-2026-10-20.md`): lands. It reproduced the review's cross-file order on Linux arm64 in a container: 9 and 11 guard refusals with `e00d394`'s conftest, 0 with the fix. Its findings, answered:
  - **L1, the `parseconfig` half had no check:** fixed. A third check, `test_a_parseconfigure_keeps_a_handler_installed_after_faulthandler`, runs the stand-in around `pytester.parseconfigure()` and `_ensure_unconfigure()`. EXECUTED on darwin-arm64 with the flag dropped from the `parseconfig` wrapper alone, every `__pycache__` under `tests/` removed and `PYTHONDONTWRITEBYTECODE=1`: 1 failed (that check, "the configured session replaced the handler: 0x105fee7d8"), 2 passed. With the fix: 3 passed (criterion 1a).
  - **N2, gather's in-process `pytest.main`:** recorded in the Scope.
  - **L2, not on main's tip:** rebased onto `f7511b7`. The one conflict was `CHANGELOG.md`; the entry stays under "0.1.0a8 — unreleased", after spec 092's. No other file the spec touches moved on main.
  - **N1:** the release run 39364504472 was on `6881242`, before the rebase and the third check. The rebase brings main's wave 03 (judge changes only) and the third check is a unit test, so no new release run was dispatched; the lane's run judges the rebased tip.
- **On the rebased tip (EXECUTED, darwin-arm64, `build/lane.lock` absent):** the new file, `test_plugin.py`, `test_landing_lane.py`, `test_upstream.py`, `test_several_cores.py`, `test_checks_wiring.py` and `tests/checks/test_rules.py`, `-n 3`, against a private copy of the main tree's artifact set: 252 passed, 1 skipped; ratchet vs `c0d2e7e` lost 0, grew 0, gained 0, `judge changed: tests/conftest.py, tests/unit/test_inline_sessions.py`. `ruff check` and `ruff format --check` green.

### Rebased onto wave/05

- **Base:** local `wave/05` at `70a8e07` (main `ebd0449`, spec 086 landed, plus spec 090). The five commits rebased as `a7e4fbb` to `a29d480`.
- **Hunks:** one conflict, `CHANGELOG.md`, under "0.1.0a8 — unreleased": 086's three bullets (wasi-sdk 34, SipHash-1-3, the missing-module message) and 082's bullet, kept both, 082's after 086's and before spec 065's. `tests/conftest.py` and `tests/unit/test_inline_sessions.py` do not change between `f7511b7` and `wave/05` (090 touches neither), so they rebased as they were; the spec and the review are new files.
- **On the rebased tip (EXECUTED, darwin-arm64, `build/lane.lock` absent):** the new file, `test_plugin.py`, `test_landing_lane.py`, `test_upstream.py`, `test_several_cores.py`, `test_checks_wiring.py` and `tests/checks/test_rules.py`, `-n 3`, against a private copy of a set (not the main tree's, which the lane is rebuilding): 252 passed, 1 skipped; ratchet vs `a75e5d4` lost 0, grew 0, gained 0. `ruff check` and `ruff format --check` green.

### Landed in wave 05

- The third check (L1, the parseconfig half) was read by the wave's integration review, which mutated each wrapper in turn: each half fails its own check alone. It has run on darwin only so far; the dry run on main runs it on Linux (the integration review's N1). The unit suite +3.
- Reviews: `../reviews/082-*` and the wave's integration review.
- **The dry run 39371419248 on `c74d0f0` passed every job on all three systems**: the third check (the parseconfig half) now ran on Linux too (the integration review's N1).
