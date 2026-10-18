# Review of 036 — Tools in the runner (the build; also a security review)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification,
  its pre-build review or the landing notes. I read `AGENTS.md`, the constitution, spec 036 with
  its landing notes, the pre-build review that confirmed it (C2 and C6 in
  `031-a-tool-protocol-over-the-door-spec-2026-10-17.md`) and 031's build review with its
  Confirmation, which is the security frame used here. I also read the diff
  (`git show 18f5bd1`: `runner.py`, `tools.py`, the new unit file, the 15 new checks and the
  three changed cache checks, `README.md` and `CHANGELOG.md`). I read the parts of `runner.py`
  the change touches: `_door`, `_Call`, `_shared`, the Ctrl-C deferral, `_epoch_ticker` and the
  fork hook. I also read the judge's driver `tests/harness/guest.py`. Each claim below is
  labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commit `18f5bd1` on `spec/036-tools-in-the-runner` in the worktree
  `../wasi_python-036`, based on `64663de` (031 accepted). Its artifact set is main's frozen set
  `build/sets/s-0cdc7b2bd78db6f5`, which was not rebuilt.
- **Ran (EXECUTED, darwin-arm64, `uv run`, wasmtime-py 49).** Scripts and outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/036-review/`.
  - `uv sync`, then `WASI_PYTHON_ARTIFACTS=…/s-0cdc7b2bd78db6f5 uv run pytest`, with no flags
    (`judge.txt`). I also ran `ruff check` and `ruff format --check` on
    `src tests recipes/guest`.
  - `mutants.py` gave `mutants_unit.txt` and `mutants_e2e.txt`: 20 mutants. Each was applied,
    judged by the named checks and restored byte for byte (checked by SHA-256). A mutant whose
    check hangs was stopped by a watchdog after 90 s (unit) or 240 s (end to end) and counted
    killed.
  - The probes, each with a `.txt` output: `probe_race.py`, `probe_record_cap.py`,
    `probe_admit_wired.py`, `probe_old_set.py`, `probe_fuel.py`, `probe_fork_hook.py` and
    `probe_empty.py`.
  - `git status` and `git diff --stat` were empty after every mutant and probe.
- Nothing here measures time. The probes block tools on events. A short `timeout_s` only picks
  which ending a call gets.

## The judge

EXECUTED (`judge.txt`). The numbers match the landing notes exactly:

```
wasi_python v1: 231/242 pass · 0 gap · 11 blocked · 0 fail   (unit suite 843/851, 8 skipped)
  v1.4  embedding           110/110
ratchet vs c42410a127: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 15 · grew 0 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_tools.py
1074 passed, 19 skipped in 234.81s
```

- Ruff is clean on the judged paths: "All checks passed!" and "65 files already formatted".
- The 11 blocked checks belong to this worktree: no source trees, no oracle, no wheel, one
  system. They were blocked before the change too.
- The judge-changed line names exactly the two files the change edits.

## Findings, most severe first

### F1 — Medium. Nothing in the judge checks that `run(tools=…)` passes `admit` to the door

- **Background.** Decision 2 answers the pre-build review's finding 1: under `tools=`, the
  door refuses a frame by its length before it copies the frame. Two pieces make that happen.
  - `_door` asks `admit(length)` before `memory.read`.
  - `_instance` passes `tool_host.admit` to `_Call` (`runner.py:1842`).
- **What is checked.** The unit checks cover the first piece only. They build their own door:
  `runner._door(host, refuses)` and `runner._door(host, host.admit)`.
- **What is not checked.** Criterion 5's end-to-end check asserts the answers: four
  `too_large` outcomes with `request_bytes` 268,435,456. Those answers are the same when the
  frame is copied first, because `_ToolHost.__call__` then admits the frame itself (031's raw
  path, by design).
- **Mutant M20 survives.** It changes `host, admit = tool_host, tool_host.admit` to
  `host, admit = tool_host, None`. It survived the 22 tool and cache checks and three unit
  files: `test_runner_tools.py`, `test_tools.py` and `test_runner_calls.py` (EXECUTED,
  `mutants_e2e.txt`).
- **The probe shows what the mutant breaks.** `probe_admit_wired.py` counts the bytes read
  through `wasmtime.Memory.read` while a guest sends four 256 MiB frames under `tools=`
  (EXECUTED):
  - built code: largest read 14 bytes, 0 reads of 1 MiB or more;
  - under M20: largest read 268,435,456 bytes, 4 such reads, and the same four `too_large`
    outcomes.
- **Why it matters.** This is the security property the specification was split out to
  build. A later change to `_instance` could drop it, and nothing would turn red.
- **Fix.** Add a check that counts the reads, seen failing against M20. Either of these works:
  - give criterion 5's check a counter on `wasmtime.Memory.read` in process, as the probe
    does (it counts bytes, not time);
  - or add a unit check that `_instance` passes the frame host's `admit` to `_Call`.

### F2 — Medium. A guest can push its abandoned tool calls out of the record

- **How.** The record lists the first `RECORD_OUTCOMES` = 1,000 outcomes (`tools.py:56`). With
  `max_tool_calls=None` (documented as "no limit"), or any limit above 1,000, a guest can spend
  its first 1,000 frames on cheap `list` frames. Its abandoned calls then land in `unlisted`.
- **Probe.** EXECUTED, `probe_record_cap.py`:
  `max_tool_calls None exit 0 b'done\n' frames 1005 listed 1000 unlisted 5 abandoned listed 0 threads alive 4`
  (the same with 2000).
- **Why it matters.** It goes to the integrity of the result (threat model asset 4).
  - Decision 5 records `abandoned=True` so the embedder learns that a tool's effect may still
    land after `run` returned. That tool still runs with the embedder's authority.
  - Here four tools are still running, and the record shows none of them.
  - `stats()["tool_threads_running"]` counts the whole process, so it cannot say which run
    left the threads, or which tools they are.
- **With the default limit** of 1,000 this cannot happen: every frame a tool can run in is
  listed (INFERRED from `admit` and `_note`).
- **Fix: either of these.**
  - Give `ToolRecord` an `abandoned: int` field: the calls answered while their tool ran on,
    counted whether or not they are listed. Append it last with a default, so positional use
    is unchanged. This is `src/` only and the artifact set does not change. Add a check like
    the probe, seen failing first.
  - Or always list an abandoned outcome, whatever the cap. The list stays bounded by
    `frames`.
- A written answer could only say "watch `stats()`". I do not recommend that, for the reason
  above.

### F3 — Low. The finish/abandon lock leaves a window, and its main property has no check

- **The window.** The thread sets `slot.filled` (`tools.py:1461`) before its `finally` sets
  `slot.finished` under the lock. `_abandon` (`tools.py:1482`) reads only `finished`. So
  suppose an ending is seen after the work's last slice has passed but before its thread
  reaches the `finally`. Then the call is answered `timeout` or `cancelled`, the finished result
  is dropped, and the outcome says `abandoned=True`.
  - EXECUTED, `probe_race.py` case B, holding the thread between the two steps:
    `B timeout timeout True filled True per-call abandoned count 1`.
  - The count goes back to 0 once the thread ends, so nothing leaks.
  - The cost: a guest that retries after `ToolTimeout` acts twice, and the record says the
    tool may still run when it has finished.
  - The landing notes say "a result that finishes at an end is delivered, never counted
    abandoned". That holds only once the thread has reached its `finally`.
- **The missing check.** Mutant M8 drops the `finished` test from `_abandon`. It survives the
  unit file (EXECUTED, `mutants_unit.txt`).
  - Under M8, a call whose work finished just before the ending is answered `timeout`. Its
    per-call count then stays at 1 forever, because the `finally` has already run.
  - Four such races, and every later call in the run is refused.
  - The deterministic probe `probe_race.py` case A kills M8 (EXECUTED,
    `probe_race_m8.txt`: `A None timeout True per-call abandoned count 1`). On the built code it
    gives `A done ok False per-call abandoned count 0`.
- **Fix.**
  - In `_abandon`, under the lock, also return `False` when `slot.filled.is_set()`. `filled`
    is set before the `finally`, so the window closes. The thread's `finally` then sees
    `abandoned` false and decrements nothing.
  - Add cases A and B as unit checks. Their fake `ticks` drives the order, with no timing.
    Case B should be seen failing against `18f5bd1`.

### F4 — Low. A unit check calls the fork hook in the judge's own process

- `test_stats_counts_tool_threads_and_the_fork_hook_resets_it` calls `_after_fork_in_child()`
  in process (`test_runner_tools.py:451`).
- The hook rebinds every runner lock and resets the default async pool, the zip folders, the
  compile table and the epoch ticker's thread and condition. The test restores only `_fork`
  and the count.
- EXECUTED, `probe_fork_hook.py`: after one run, the hook, and a second run, **2** epoch-ticker
  threads are alive. The old one waits forever on the old condition.
- **Why it is harmless today.** It is harmless only by the order of the judge. The unit suite
  runs after the checks, and runs are sequential.
- **The risk** (INFERRED from `_epoch_ticker._tick`). If the hook were called while a run held
  the ticker, the old thread would rejoin on the new condition, and epochs would advance twice
  per tick. Every deadline would then come early.
- **Fix.** Check the hook in a forked child, as the existing fork checks do
  (`test_v1_4_embedding.py:1073` and `:1315`), or save and restore every global it rebinds.

### F5 — Low. The specification's text should match what was built

- **Criterion 17 and Decision 6.** These need a recorded amendment; see "The deviation" below.
- **Decision 4.** It says "If less than two ticks are left, the call is answered `timeout` at
  once". The build answers at once with two ticks **or fewer** left (`ticks >= stop_at - 2`).
  - This reading is right. It is the same test as the in-flight end, "the call's deadline less
    two ticks", and a call started with exactly two left would be abandoned at its first slice.
  - Amend the text to "two ticks or fewer".
  - The exact boundary is not checked. The unit check tries one and three ticks left. Mutant M4
    (`>` for `>=`) is killed only because another case then hangs. Add a case with exactly two
    left.

### F6 — Info. Needs no change

- **What leaves `__call__`.** Only a `BaseException` that is not an `Exception` can leave
  `_Bounded.__call__`: in practice, a `KeyboardInterrupt` from an embedder's own SIGINT handler
  (READ). `_shared` turns it into a recorded stop, and `run` raises. Two consequences follow.
  - If it arrives between `self._count(1)` and a start that did not happen, the process count
    stays one high.
  - The threads left that way are why "up to five" per run is the honest bound. Without one,
    the bound is four, because the deadline end always answers before the run ends.

  Both are acceptable.
- **The quota's answer.** The quota's `timeout` answer ("4 earlier tool calls are still
  running") is given with nothing run, and `abandoned=False` says so. That is right.
- **The `MANIFEST` cache.** It has no lock, and none is needed (READ).
  - A dictionary `get` or set is atomic.
  - A race only reads the file twice.
  - A forked child inherits correct entries, since an entry is keyed by path and stat stamp
    (device, inode, size, mtime, ctime).
  - Decision 8's condition then asks nothing of the fork hook for it.

## Mutants

EXECUTED. **18 killed and 2 survived** (F1, F3).

| mutant | killed by |
|---|---|
| M1 abandoning does not count | `test_too_little_time_or_too_many_abandoned_answers_at_once` |
| M2 a slot never frees | the same |
| M3 no deadline margin | `test_the_bound_answers_in_order` hangs (stopped) |
| M4 margin `>` for `>=` | the same hang (see F5) |
| M5 the bound clears the Ctrl-C flag | `test_the_bound_answers_in_order` |
| M6 no `contextvars` copy | `test_the_tool_runs_in_a_copy_of_the_callers_context` |
| M7 `timeout_s` end not abandoned | `test_the_bound_answers_in_order` |
| **M8 `_abandon` ignores `finished`** | **survives** (F3) |
| M9 per-call count not set up | `test_the_bound_answers_in_order` (a crash; not a real shared-quota model) |
| M10 quota `>` for `>=` | `test_too_little_time_…` |
| M12 the thread not counted in | `test_too_little_time_…` |
| M13 the fork hook keeps the count | `test_stats_counts_tool_threads_…` |
| M14 every `MANIFEST` has the guest package | `test_an_artifact_set_without_the_guest_package_is_refused` |
| M15 the cache ignores the stamp | the same |
| M16 no record on a trap | `test_a_guest_calls_a_tool` (the out-of-fuel case) |
| M17 tool threads not daemons | `test_a_cancel_during_a_tool_call_is_named` |
| M18 the deadline not watched in the wait | `test_the_bound_answers_in_order` |
| M19 the gate runs on the door's thread, unbounded | the unit check hangs (stopped) |
| **M20 `run` passes no `admit`** | **survives** (F1) |
| M21 no check before the start | `test_the_bound_answers_in_order` |

The implementer's own stand-ins (`standins.txt`) cover the rest of the named stand-ins (READ).

## The questions the implementer asked

**The deviation on criterion 17 (fuel through the driver, not `run`): accepted, with an
amendment recorded in the specification.**
- **The premise holds.**
  - EXECUTED, `probe_fuel.py`: through `run`, `-c pass` gave 82,185,254, 82,141,086 and
    82,184,519. The two-call program with instant tools gave 92,325,359, 92,244,924 and
    92,291,126.
  - So `run()`'s fuel moves by tens of thousands with no tool sleeping at all. Equality through
    `run` is not achievable for any program.
  - The cause is that `run` supplies the real clock and real entropy, by design. The project
    already decided how to measure fuel exactly: the driver answers `clock_time_get` and
    `random_get` itself (`tests/harness/guest.py`;
    `research/2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md`).
- **The check measures the right thing** (READ).
  - Its host is `runner._tool_host(...)`, the frame host and `_Bounded` that `run` builds.
  - The tools run on real threads, and a 0.05 s pause spans five one-tick slices of the wait.
  - So the property, that time in a tool adds no guest instructions, is what is asserted.
  - Through `run`, it asserts that `fuel_used` is still reported.
- **I do not require something else.** A tolerance on `run()`'s fuel would be a statistical
  check, which is weaker, and §4.9 does not want one.
- **The amendment** (dated, with this reason):
  - Criterion 17 should read: "through the judge's driver, with `runner._tool_host` as its
    host; through `run`, `fuel_used` is an `int`".
  - Decision 6's "a call whose tools answer the same spends the same fuel" should gain "given
    the same clock and entropy (the judge's driver); `run`'s real clock moves any program's
    fuel by about 10^5".

**`_Bounded`.**
- The per-call count holds (EXECUTED: M1, M2 and M10 killed; READ: one `_Bounded` per
  `_instance`, made in `_tool_host`).
- The lock between abandoning and the `finally` is right except for the window in F3, and its
  key property needs a check (F3).
- Only a `KeyboardInterrupt`-type exception leaves `__call__` (READ; EXECUTED,
  `test_a_fault_in_the_bound_keeps_the_call_in_the_record` and
  `test_a_thread_that_cannot_start_is_a_fault`). See F6.

**`_door`.**
- `admit` comes after the address check and before `memory.read` (READ, `runner.py:2561`;
  EXECUTED, the unit check, the implementer's c2 stand-in, and `probe_admit_wired.py`: largest
  read 14 bytes).
- With `admit=None`, the raw path is the old one: `response = host(bytes(memory.read(…)))`
  runs exactly as before, and a host returning `None` is still `HOST_FAULT` (READ;
  EXECUTED, every `host=` check passes).
- The wiring is unguarded (F1).

**The three cache-check expectation changes.**
- **Accepted as a judge change.** Decision 5 adds the key to `stats()`, so the exact
  dictionaries those checks compare must gain it.
- A probe child that ran no tool must read 0, so the new expectation is no weaker.
- The lane accepts with `--accept-judge`. The judge-changed line lists exactly the two files.

**Where the specification was silent.**
- **Two ticks or fewer gives a `timeout` at once.** Right (F5: amend the text, and check the
  boundary).
- **The ends are checked before the start.** Right. A pending Ctrl-C or `cancel` answers
  `cancelled`, unstarted and not abandoned. The guest is being stopped anyway, and nothing runs
  that the run cannot wait for.
- **The order within a slice is a delivered result first, then Ctrl-C, `cancel`, the deadline,
  `timeout_s`.** Right. A result that is in hand is the truth, and telling the guest about it
  cannot run anything further. The stops come before the timeouts, so a stop is never reported
  as a timeout.
- **Thread names** (`wasi-python-tool-<name>`). Fine. The name is a validated identifier of at
  most 64 characters, and it names no embedder.

**The `MANIFEST` cache without a lock, and the fork hook.** Right (F6). The fork hook remakes
`_tool_threads_lock` and zeroes the count (READ; EXECUTED, M13 killed). Its check needs F4.

**`ArtifactsMissing` for a set without the guest package.**
- Holds. EXECUTED, `probe_old_set.py` against the real pre-031 set `s-8d84b3b190fe9bce`:
  `tools=` raises `ArtifactsMissing` naming the `recipe … recipes/guest/host/tools.py` line, and
  the same set without `tools=` prints `1`.
- It is raised in `_run_checked` before the grants are walked (READ; EXECUTED, the unit check
  and M14 and M15 killed).

## Security, against the threat model

The adversary is the guest: arbitrary Python, the door and every preview1 call. The tools and
the gate are the embedder's code, judged here for robustness.

- **No third import (§4.4).** The artifact set is 031's, unchanged, so the guest's imports and
  exports are unchanged (READ: no file under `recipes/` or `scripts/` changes).
- **Can a guest make `run` raise?** No (READ; EXECUTED).
  - Everything on the frame host's path catches `Exception`: `_ToolHost.__call__`,
    `_Bounded.__call__` and `_door`'s `call`.
  - The tool's thread catches `BaseException` (`_Work`, and `target`), so a tool raising
    `SystemExit` or `KeyboardInterrupt` stays on its thread.
  - A thread that cannot start is a `tool_error` (EXECUTED, criterion 3).
  - Only Ctrl-C makes `run` raise, as before.
  - The `MANIFEST` check reads the embedder's file, not the guest's input.
- **Can a guest starve the host's threads?** Only within the stated per-run bound (READ;
  EXECUTED).
  - A run starts at most one thread per tool frame, and each ends with its tool.
  - At most 4 per run outlive their call (EXECUTED, criterion 11), or 5 with an embedder's
    `KeyboardInterrupt` (F6).
  - There is no shared pool, so one run's stalled tools cannot hold a thread another run needs
    (EXECUTED, criterion 12; the implementer's shared-pool stand-in fails it).
  - Many runs against a tool that can hang still grow the process's threads. That is C2's
    accepted residual risk, stated in Decision 5 and the README, and visible in `stats()`.
  - A guest cannot make an embedder's tool hang. It can only choose the arguments, inside the
    schema, of a tool the embedder offered.
- **Can a guest hold the door's thread?** Only within the run's own deadline, `cancel` or
  Ctrl-C (READ).
  - The wait is sliced by ticks, and the deadline end comes two ticks before the epoch trap
    (EXECUTED, criterion 10).
  - Validation stays on the door's thread under 031's counted budget, so it is bounded by work,
    not time.
  - A refused frame costs constant host work whatever its length (EXECUTED, probe: 14-byte
    largest read). This rests on F1's unguarded wiring.
  - With `deadline_s=None`, no `cancel` and a tool without `timeout_s`, a blocked tool blocks
    `run`. That is the embedder's choice, as with a raw `host=`, and the README says a tool that
    can hang must bound itself.
- **Can a tool keep running past the end of its run, with its authority?** Yes, by design. Its
  call is recorded `abandoned=True` (EXECUTED, criteria 9, 11 and 13). There are two gaps.
  - **F2:** with a limit above 1,000 or none, a guest can keep those records out of the list.
  - **F3:** the opposite error, a finished call recorded as abandoned, which is harmless to the
    embedder but can make a retry act twice.
- **Only chosen text crosses.** A fault stays in the record (EXECUTED, criterion 7: the host
  path in neither stream). The bound's own messages name configured limits, never measured
  times.
- **Thread-bound objects.** The gate and the tool run on a fresh thread in a copy of the
  caller's context. Thread-locals and `check_same_thread` objects do not cross; context
  variables do (EXECUTED, criterion 16). The README says so.

## Each Decision against the code

1. **`tools=`, `gate=`, `max_tool_calls=`.** Holds (EXECUTED, 17 refusal cases through `run`
   and `run_async` with no artifact lookup and no `submit`; `probe_empty.py`: `tools=[]` imports
   `host.tools` with nothing in it, and `run_async` with a tool answers `ok`;
   `ArtifactsMissing` against a real pre-031 set).
2. **Refusal by length before the copy.** Holds in `_door` and in the wiring (EXECUTED, the
   probe). The wiring is unchecked (F1).
3. **Tools on their own threads.** Holds (EXECUTED, criterion 16; M6 and M17 killed).
4. **The bound of one call.** Holds (EXECUTED, criterion 3, M3, M5, M7 and M18). See F5 for
   "fewer than two".
5. **Stalled tools bounded per call.** Holds (EXECUTED, criteria 11 and 12, and the failed
   start), except F2 and F3.
6. **After the answer.** Holds (EXECUTED, criteria 9, 13, 14 and 15). For fuel, see the
   amendment.
7. **The record in the result.** Holds on an exit, a trap and `"cancelled"` (EXECUTED; M16
   killed). On `"deadline"` it holds by reading only (READ: the record is taken without a
   condition).
8. **Fork.** Holds (READ; M13 killed). See F4 for its check.
9. **Docs.** The README *Tools* section is accurate (READ), and the CHANGELOG entry is
   accurate. The recipes' runs are the implementer's (see criterion 19).

## Acceptance criteria against evidence

| # | criterion | evidence | holds |
|---|---|---|---|
| 1 | refusals before anything runs; the default; a `MANIFEST` without the guest package | EXECUTED (judge; M14, M15; `probe_old_set.py`) | yes |
| 2 | the door refuses by length before reading | EXECUTED (judge; the implementer's c2 stand-in) | yes, for `_door`; the wiring in F1 |
| 3 | the bound answers in order | EXECUTED (judge; M3 to M7, M10, M12, M18, M21) | yes; boundary in F5, lock in F3 |
| 4 | a guest calls a tool; the record on exit and trap | EXECUTED (judge; M16) | yes |
| 5 | a huge frame is answered unread | EXECUTED (judge passes; probe: 14-byte largest read) | the outcome yes; "unread" is not observed by the check (F1) |
| 6 | a gate refuses before the tool runs | EXECUTED (judge) | yes |
| 7 | a tool fault stays on the host | EXECUTED (judge) | yes |
| 8 | the tool call limit holds | EXECUTED (judge; the implementer's c8 stand-in) | yes |
| 9 | a timeout ends the call, not the run; one slot per call | EXECUTED (judge; the implementer's c9 stand-in) | yes |
| 10 | a tool blocking past the deadline is answered | EXECUTED (judge; the implementer's c10 stand-in) | yes |
| 11 | abandoned tools bounded per call; `stats()` | EXECUTED (judge; M1, M2, M10) | yes; F2 for the record |
| 12 | one call's stalled tools do not starve another | EXECUTED (judge; the implementer's c12 stand-in) | yes |
| 13 | a cancel during a tool call is named | EXECUTED (judge; M17) | yes |
| 14 | Ctrl-C during a tool call | EXECUTED (judge) | yes |
| 15 | cancelling `run_async` during a tool call | EXECUTED (judge; the implementer's c15 stand-in) | yes |
| 16 | tools run off the guest's thread | EXECUTED (judge; M6) | yes |
| 17 | fuel is exact across tool calls | EXECUTED (judge; `probe_fuel.py`) | yes, through the driver; amend the text |
| 18 | no tools, no protocol | EXECUTED (judge) | yes |
| 19 | the two README recipes ran once, pinned | READ (landing notes; `036/mcp_recipe.txt` and the recipe scripts); not re-run, since it would fetch packages | yes, as the implementer's record |
| 20 | judge green with `--accept-judge`; lost 0; grew 0 | EXECUTED (no flags: lost 0 · grew 0 · gained 15; judge changed: the two files) | yes; the lane accepts |

## Constitution checks

- **§4.1, §4.2, §4.8.** No patch, no new input, no download (READ: no change under `recipes/`,
  `scripts/` or `downloads/`).
- **§4.4.** No new import. The protocol rides the one door, and only under `tools=` (READ).
- **§4.5.** No embedder is named (EXECUTED: `grep` of the added lines). LangChain and MCP
  appear only as recipes, as decision 40 allows.
- **§4.9.**
  - No check reads a clock. `test_no_test_reads_a_clock` passes (EXECUTED).
  - `timeout_s=0.05` and the criterion 17 pauses only pick outcomes; the tools block on events.
  - Criterion 12 gives B's tool `timeout_s=5`, which needs a trivial call to answer within
    5 s. That is a fail-safe, not a measurement.
- **§4.10.** The landing notes' scoreboard is reproduced exactly (EXECUTED). Their fuel numbers
  are reproduced in kind (EXECUTED, `probe_fuel.py`: the same spread).
- **§4.13.** No dependency is added (READ: `pyproject.toml` is unchanged), and ruff is green
  (EXECUTED).
- **§4.15.**
  - No channel opens without `tools=`.
  - `max_tool_calls` has a default (1,000). `None` is an explicit opt-out, like the other
    limits.
  - There is no per-call default timeout beyond the run's deadline: owner question 53, recorded.
- **§5.6.** C2 and C6 from the pre-build review are met.
  - The per-call statement, the count in `stats()` and the failed start as a fault are built.
  - The record comes back on every ending.
  - The fork hook remakes the lock it added.
- **§5.7.** Not build-class.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the implementer, 2026-10-18, on `e093e82` (the branch rebased onto main `3a9588f` first:
`git rebase main`, no conflict; the reviewed commit is now `0da463f`). Each new check was seen
failing first against `18f5bd1` (the reviewed code, rebased) or the named mutant; the mutants
were applied by `../036/revision_mutants.py`, which restores the files (`restored True`;
output in `../036/revision_mutants.txt`). EXECUTED unless labelled.

| # | disposition | where |
|---|---|---|
| F1 | **Fixed.** `test_a_huge_frame_is_answered_unread` counts the bytes read through `wasmtime.Memory.read` in process (as `probe_admit_wired.py`) and asserts `max(reads) < 1 MiB`. M20 (`host, admit = tool_host, None`): FAILED. Revision: passes. | the check; criterion 5 amended |
| F2 | **Fixed, first option.** `ToolRecord.abandoned: int = 0`, last (positional use unchanged), counted in `_ToolHost._note` for every `abandoned=True` outcome, listed or not. Your probe as checks: unit (`_ToolHost` + `_Bounded`, 1,000 `list` frames, five calls: `frames 1005`, `listed 1000`, `unlisted 5`, `abandoned 4`) and end to end (`max_tool_calls=None`, 1,000 raw `list` frames, four abandoned calls: 0 abandoned listed, `abandoned == 4`). Both failed against `18f5bd1` (`AttributeError … 'abandoned'`) and with the count removed. README *Tools* and Decision 7 amended. | `tools.py`; `test_abandoned_calls_are_counted_past_the_listed_outcomes` (both files) |
| F3 | **Fixed as proposed.** `_abandon` returns `False` when `slot.finished or slot.filled.is_set()`, under the lock. Cases A and B are unit checks driven by a fake ticker (B: a slot whose `filled.set()` holds the thread before its `finally`). Case B failed against `18f5bd1` (`timeout`, abandoned) and against `if slot.finished:`; M8 (`if False:`) fails A and B. After B's thread ends, the per-call count is 0. | `test_a_result_that_finished_at_an_end_is_delivered`, `test_a_result_filled_before_an_end_is_delivered` |
| F4 | **Fixed.** The in-process call of the hook is removed. `test_the_fork_hook_resets_the_tool_thread_count` runs a fresh interpreter that counts 7 tool threads and forks; the child reports `child 0 True` (count 0, new lock), the parent `parent 7`. M13: FAILED. Skipped without `os.fork`. `test_stats_counts_tool_threads` keeps the count's plain check. | `tests/unit/test_runner_tools.py` |
| F5 | **Fixed.** Decision 4: "two ticks or fewer", dated, with the reason. A case with exactly two left (`stop_at=12`, ticks 10): answered at once, no gate, no tool, the "too near" message. M4 (`>` for `>=`): FAILED at once (the first version's tool had no `timeout_s`, so M4 hung until the watchdog; the case now uses `timeout_s=0.01`). Criterion 17 and Decision 6 amended as you wrote ("given the same clock and entropy (the judge's driver)"; "through `run`, `fuel_used` is an `int`"), dated, citing this review. | spec Decisions 4, 6, 7; criteria 3, 5, 17 |
| F6 | **No change**, as the review says. | — |

The judge on `e093e82` (worktree, no flags; ruff clean on `src tests recipes/guest`):
`wasi_python v1: 232/243 pass · 0 gap · 11 blocked · 0 fail (unit suite 847/855, 8 skipped)`;
`v1.4 111/111`; `ratchet vs 947036ec8d: lost 0 · absent 0 · unrun 0 · unrun locally 9 ·
gained 16 · grew 0 · judge changed: tests/checks/test_v1_4_embedding.py,
tests/unit/test_runner_tools.py`; `1079 passed, 19 skipped`. The spec's landing notes carry the
same under "Revised against the build review".

## Verdict

**Not ready to land yet. Fix F1 and F3, and fix or answer F2. The fixes are small and in
`src/` and `tests/` only.**
- **F1** is a missing guard on the very property the review asked for: the copy refused by
  length. Today it is built and works, but no check would notice if it went.
- **F2** lets a guest hide the record of tools still running with the embedder's authority
  once the limit is above 1,000.
- **F3** is a narrow race, and an untested lock property whose mutant leaks the quota.
- **F4 and F5** can be fixed or answered in the Disposition.

The deviation on criterion 17 is accepted, with the criterion and Decision 6 amended as
written above. The cache-check changes are an accepted judge change.

After that comes a short confirmation: the new checks, each seen failing first against
`18f5bd1` (F1 against M20, F3 against case B and M8), and the judge re-run on the revised
commit. Then the lane rebases, judges in the main tree and accepts with `--accept-judge`.
There is no growth to accept.

## One line

The tools are bounded as designed: refused by length before the copy, on their own threads,
four abandoned per run, and nothing a guest does makes `run` raise. But no check sees that
`run` actually passes `admit` to the door, a guest can hide abandoned tools from the record
when the limit is above 1,000, and a narrow race records a finished call as abandoned. Fix
those; the fuel deviation is accepted with an amendment.

## Confirmation (2026-10-18)

- **Reviewed.** I checked the revision `e093e82` on `spec/036-tools-in-the-runner` against the
  Disposition above.
  - The branch was rebased onto main `3a9588f`. `git range-diff` shows that the reviewed commit
    `18f5bd1` and its rebased form `0da463f` carry the same patch.
  - I read the diff `0da463f..e093e82`: `tools.py`, the two check files, the README and the
    specification's amendments to Decisions 4, 6 and 7 and criteria 3, 5 and 17.
- **Ran (EXECUTED).** Outputs are in this folder:
  - `judge2.txt`, `probes_revision.txt`;
  - `mutants_rev.py` and `mutants_rev.txt`, where each mutant was applied, judged and restored
    byte for byte by SHA-256.
  - `git status` and `git diff --stat` were empty after every step.
- **The judge** (EXECUTED: `WASI_PYTHON_ARTIFACTS=…/s-0cdc7b2bd78db6f5 uv run pytest` in the
  worktree, no flags) reads exactly as the Disposition says:
  - `232/243 pass · 0 gap · 11 blocked · 0 fail (unit suite 847/855, 8 skipped)`;
  - `v1.4 111/111`;
  - `ratchet vs 947036ec8d: lost 0 · … · gained 16 · grew 0 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_tools.py`;
  - `1079 passed, 19 skipped`.

  Ruff is clean on `src tests recipes/guest`.

### Each disposition against its finding

- **F1: confirmed fixed.**
  - `probe_admit_wired.py` on the revision: largest read 14 bytes, 0 reads of 1 MiB or more.
  - Criterion 5's check now counts the bytes read through `wasmtime.Memory.read` and requires
    every read to be under 1 MiB.
  - **M20 is now killed** (`R1`: `test_a_huge_frame_is_answered_unread` FAILED).
- **F2: confirmed fixed.**
  - `ToolRecord.abandoned: int = 0` is the last field, counted in `_note` whether or not the
    outcome is listed (READ).
  - `probe_record_cap.py`, for both `max_tool_calls=None` and 2000: `frames 1005 listed 1000
    unlisted 5 abandoned listed 0 record.abandoned 4`.
  - Two mutants are killed by the unit and end-to-end checks: the count removed (`R4`), and the
    count kept only for listed outcomes (`R5`). The second is the subtle one.
- **F3: confirmed fixed.**
  - `_abandon` returns `False` when the slot is `finished` or `filled`, under the lock (READ).
  - `probe_race.py` on the revision:
    - case A: `done ok False`, count 0;
    - case B: `ok False filled True`, count 0, and 0 after the thread ends. It was `timeout True`
      before.
  - **M8 is now killed** (`R2`), and so is the fix undone to `finished` only (`R3`), each by its
    own new check.
- **F4: confirmed fixed.**
  - The hook is now checked in a forked child of a fresh interpreter.
  - The hook keeping the count (`R7`, M13) is killed, and so is the hook keeping the old lock
    (`R8`, my new mutant).
  - No in-process call of the hook remains (READ).
- **F5: confirmed fixed.**
  - Decision 4 now says "two ticks or fewer", dated, with the reason.
  - The exactly-two case is pinned. Under M4 (`>` for `>=`), the boundary check alone fails at
    once (EXECUTED: `1 failed in 0.17s`).
  - In a run of the whole file with `-x`, M4 still hangs first in
    `test_the_bound_answers_in_order` (`R6`, stopped by the watchdog). Either way it is killed.
  - Criterion 17 and Decision 6 carry the amendment as written in this review.
- **F6:** no change, as agreed.

### Mutants

**8 of 8 killed** (`mutants_rev.txt`). The two that survived the first round, M20 and M8, are
now killed by their own checks.

### Nit (no action needed before landing)

The README's *The record* bullet has one line longer than its neighbours: "…listed or not, so
1,000 cheap frames cannot hide one. It comes back…". This is cosmetic only.

### Verdict

**036 lands.**
- Every finding is fixed and confirmed by probe and by mutant.
- The judge is green with lost 0 and grew 0.
- It needs no further review round.

The lane then:
- compares the branch with `e093e82`;
- judges that exact commit in the main tree;
- accepts with `--accept-judge`, naming the two judge files: the new and changed tool checks,
  and the cache checks' new `stats()` key. There is no growth to accept.

### One line

F1 to F5 are fixed and confirmed: no read of 1 MiB or more, four abandoned calls counted past
the 1,000 listed, a filled slot is never abandoned, the fork hook is checked in a child, and the
two-tick boundary is pinned. 8 of 8 mutants are killed and the judge is 232/243 with lost 0 and
grew 0, so 036 lands.
