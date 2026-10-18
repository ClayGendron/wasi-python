# 036 — Tools in the runner

- **Status:** built 2026-10-18 on `spec/036-tools-in-the-runner` (Landing notes); reviewed
  the same day (`../reviews/036-tools-in-the-runner-2026-10-18.md`: not yet, F1 to F5) and
  revised against it (Landing notes, "Revised against the build review"); awaiting the
  reviewer's confirmation. Drafted 2026-10-17, split from spec 031 by its pre-build review
  (`../reviews/031-a-tool-protocol-over-the-door-spec-2026-10-17.md`, finding 10). The review's
  findings 1, 2, 7, 9, 11 and 12 that concern the runner are answered here. It changes neither
  the guest's imports nor its exports, the artifact set nor the build recipe, so §5.6 asks no
  second review before build. It was reviewed before build anyway, with 031's revision, because
  it changes the door: **confirmed for build with conditions, written in; it builds after 031
  lands** (the review's "Confirmation": C2 in Decisions 5 and 9 and criteria 3 and 11; C6 in
  Decisions 7 and 8 and criterion 4).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`: `run`, `run_async`, `_checked`,
  `Defaults`, `_instance`, `_Call`, `_door`, `Completed`), the bounded invoke in
  `src/wasi_python/tools.py`, judge additions in `tests/`, `README.md`, `CHANGELOG.md`. **Not
  build-class:** it touches no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or release
  workflow, so it can be built in parallel with a build-class specification once 031 has landed.
- **Depends on:** 031 (the protocol, the frame host, the guest package in the zip), which lands
  first; 030 (a cancel during a door call is named); 010 (waits end at the deadline), 011 (a
  call's recorded stop, Ctrl-C deferred), 013 and 014 (arguments checked first), 015 (`cancel=`,
  `run_async`, the epoch callback, the fork hook). Spec 032 also adds a limit to `Defaults` and
  a record to `Completed`; the lane rebases whichever lands second.
- **Research it stands on:** the tool-protocol memo
  (`../research/2026-10-17-a-tool-protocol-over-the-door.md`: finding 5 and "Deadlines, fuel,
  cancel and async"); the review's probes (EXECUTED: `door_copy_probe.txt`, four 256 MiB frames
  copied by today's door before a 1 MiB cap could act; `pool_model.txt`, one guest's stranded
  calls starving another's in a shared pool; `worker_affinity.txt`, a `sqlite3` connection
  refused on another thread); the owner's decisions 12 and 14, 15, 17, 37 and 38 to 40
  (`../decisions.md`), and 42 for comparison.

## The problem

Spec 031 builds the protocol and ships the guest's half. An embedder still cannot use it:
`run` takes no tools, the door copies a frame before any cap can act, a blocked tool holds the
guest past its deadline and its cancel, and the record never reaches the result. The review
found two more things the runner must own: the cap and the budget must act before the copy,
and one call's stalled tools must not starve another's.

## Decisions

1. **`run` and `run_async` take `tools=`, `gate=` and `max_tool_calls=`.**
   - `tools`: an iterable of `Tool`s or plain functions (a plain function goes through
     `tool()`), or `None`, the default: no protocol, and the door is exactly as today. An empty
     iterable is allowed: `host.tools` imports with nothing in it.
   - `gate`: `None` or a callable that is not a coroutine function (031, Decision 5).
   - `max_tool_calls`: its default is `DEFAULTS.tool_calls`, 1,000, a new `Defaults` field with
     a default, checked by `_integer_limit` (`None` means no limit). The names follow spec 032's
     `max_file_calls` and `Defaults.file_calls`.
   - **Checked before anything runs**, in `_checked`, so `run_async` raises in the coroutine
     before queueing: each item is a `Tool` or a function `tool()` accepts; names are unique;
     the gate; the limit.
   - **`host=` and `tools=` exclude each other**, with `TypeError`: "pass host= for the raw
     door or tools= for the tool protocol, not both". The door is one function. Under `tools=`
     the runner is that function and must see every frame to keep the count, the record and the
     rule that the guest supplies nothing the host trusts. Sharing it would mean telling frames
     apart by their bytes, ending the raw door's opacity (§4.4) and letting a guest steer a frame
     to whichever side checks less.
   - **`gate=` or an explicit `max_tool_calls=` without `tools=`** raises `TypeError`: either
     would look like a gate or a limit on the raw door, and neither is one.
   - **An artifact set without the guest package** (one from before 031, through `artifacts=`
     or `WASI_PYTHON_ARTIFACTS`) is refused when `tools=` is given: if its `MANIFEST` has no
     `recipe … recipes/guest/host/tools.py` line, `run` raises `ArtifactsMissing` naming that
     line, before the guest starts. The answer is cached per `MANIFEST` path and its stat stamp.
   - The command line gains nothing: tools are Python callables.

2. **The door refuses by length before any copy (the review's finding 1).**
   - `_door(host, admit=None)`. When `admit` is given, `frame` checks the addresses against the
     memory's size as today, then calls `admit(length)` before `memory.read`. If it returns
     bytes, they are the answer: written through `host_alloc` as any answer, and the frame is
     never read. Otherwise the frame is read and passed to `host` as today.
   - The runner learns the cap from the frame host, not from a number passed around:
     `_instance` builds the call's `_ToolHost` and gives the `_Call` both `host=tool_host` and
     `admit=tool_host.admit`. 031's `admit` counts the frame and answers `budget_exceeded` past
     the limit or `too_large` over 1 MiB.
   - The raw `host=` path passes no `admit` and is unchanged.
   - So a refused frame costs the host constant work, whatever its length. A guest that loops
     on refused frames spends only its own fuel and time, under its own deadline. That makes
     question 52's "run on at the limit" safe.

3. **Tools run on their own threads, not the guest's.**
   - Each tool call runs its work (031, Decision 5: the gate, the tool, the result's encoding)
     on a new daemon thread, inside a copy of the door thread's `contextvars` context. There is
     no shared pool (the review's option (b)): one call's stalled tools cannot hold a thread
     another call needs. Daemon threads, because interpreter exit joins a
     `ThreadPoolExecutor`'s workers, and a hung tool would hang exit.
   - **Why another thread:** the call's deadline, its `cancel` and Ctrl-C must be answered while
     a tool blocks, and host code cannot be interrupted. Only a thread that waits beside the tool
     can answer in time.
   - **Why spec 032's provider differs:** a provider answers the guest's file calls, which are
     many and short and which the guest's libc makes synchronously. A thread per `stat` would
     multiply their cost, and the provider bounds its own time. Tools are fewer and longer, often
     wait on the network, and a timeout the guest can catch is part of their contract.
   - **What that breaks:** objects bound to a thread. A `sqlite3` connection made with
     `check_same_thread` (EXECUTED, `worker_affinity.txt`) and thread-locals do not work inside
     a tool or gate. `contextvars` do. The README says so.

4. **The bound of one tool call.** The door thread waits for the tool's thread in slices of one
   tick (`TICK_S`). The call ends at the first of:
   - the tool's `timeout_s`;
   - the call's deadline less two ticks, read from `stop_at` and the epoch ticker's count as
     spec 010's waits read them, so the guest gets `ToolTimeout` before the run ends inside the
     door. If two ticks or fewer are left, the call is answered `timeout` at once, and neither
     gate nor tool runs (amended 2026-10-18 by the build review's F5: "less than two" before;
     with exactly two left the end is already reached, so a started call would only be
     abandoned at its first slice);
   - the call's `cancel` event;
   - a pending Ctrl-C on the main thread. The wait reads spec 011's flag and never clears it;
     `_shared` clears it, as today.

   Each tool call has its own result slot. A late result of an abandoned call is dropped, never
   delivered to a later call.

5. **Stalled tools are bounded per call (the review's finding 2).**
   - A sync tool's thread cannot be stopped. After a `timeout` or `cancelled` answer it runs to
     its end, unseen, and its result is dropped. Its outcome says `abandoned=True`, since its
     effect may still land.
   - A call may hold at most **4** such threads (`MAX_ABANDONED`). While it holds 4, its next
     tool call is answered `timeout` at once ("4 earlier tool calls are still running"), with no
     gate and no tool run. A slot frees when its thread ends.
   - Why 4: a guest may go on after a few slow calls, and no call can starve another, since
     there is no shared pool.
   - **The bound is per call, not per process (the review's C2).** When a run returns, its
     abandoned threads live on until their tools end, and the next run starts from zero. Each
     run can leave up to five threads behind (four abandoned, and the one running when the run
     ended). Ten runs in sequence against a tool that hangs left 40 threads alive (EXECUTED,
     `thread_model.txt`). A process-wide ceiling would bring back finding 2's starvation, so
     there is none; a tool that can hang must bound itself.
   - **The count is visible.** `runner.stats()` gains `"tool_threads_running"`: the tool threads
     alive in this process, abandoned ones included. An embedder can watch it; the judge reads
     it.
   - **A thread that cannot start is a fault.** If starting a tool's thread raises (the
     operating system's thread limit), the call is answered `tool_error` with "<name> failed
     (internal error)", its outcome's `fault` names the exception, and nothing raises out of the
     frame host.
   - The README says a call retried after `ToolTimeout` may act twice, that a tool that can hang
     must bound itself, and that each run can leave up to five threads behind.

6. **After the answer.**
   - **`timeout`:** the guest gets `ToolTimeout` and runs on.
   - **`cancelled`:** the runner stops the guest, as spec 015 does after any door call, and spec
     030 names the run `"cancelled"`. Under `run_async`, a cancelled task no longer waits on a
     blocked tool; spec 015's caveat remains for a blocked raw `host=`.
   - **Ctrl-C:** the answer is `cancelled`, and `_shared` raises `KeyboardInterrupt` after the
     door returns, as today.
   - **Fuel** counts only guest instructions. A tool's time never changes `fuel_used`, and a call
     whose tools answer the same spends the same fuel, given the same clock and entropy (the
     judge's driver); `run`'s real clock and entropy move any program's fuel by about 10^5
     (031's list order makes discovery the same). (The clause on the clock and entropy amended
     2026-10-18 by the build review, which accepted criterion 17's deviation.)

7. **The record in the result.** `Completed` gains `tools: ToolRecord | None = None`, last, so
   positional use is unchanged; it is `None` for a call without `tools=`, as 032's `files` is
   for a call without mounts. With `tools=` it is returned on every ending: an exit, a trap,
   `"deadline"` and `"cancelled"` (the review's C6). Only when `run` raises (a Ctrl-C) is there
   no `Completed`. `ToolRecord` and `ToolOutcome` are 031's. The command line's JSON
   does not change. `ToolRecord` gains `abandoned: int = 0`, last: every call answered while its
   tool ran on, counted whether or not its outcome is listed, so a guest cannot push those
   records past the 1,000 listed with cheap frames under a higher limit or none (amended
   2026-10-18 by the build review's F2).

8. **Fork.** There is no pool or queue to reset: a forked child has none of its parent's tool
   threads, and spec 015's refusal of a runner used before the fork still applies. If the
   `MANIFEST` check's cache (Decision 1) or the thread count (Decision 5) is guarded by a lock,
   `_after_fork_in_child` makes that lock anew, as it does `_zip_lock`, and sets the count to 0
   (the review's C6). Otherwise the fork hook is unchanged.

9. **Docs.** The README gains "Tools": the decorator and the capability pattern (tools made per
   request, closing over the caller's authority); "a tool runs with your process's authority: a
   `read_file(path)` tool is a filesystem"; the gate; the record; the error rule; the limits and
   their reasons; tools on their own threads (Decision 3); abandoned tools (Decision 5); the
   guest's API; `runner.stats()["tool_threads_running"]`; and two recipes, labelled recipes, not API (decision 40):
   - a LangChain tool through `tool(fn, name=, description=, input_schema=,
     validates_input=True)`, its `ToolException` text re-raised as `ToolError`;
   - an MCP server's tool through the embedder's own client session, `structuredContent` as the
     value and `isError` as `ToolError`.

   Each recipe is run once by the builder in a throwaway environment with pinned versions
   (`uv run --isolated --no-project --with langchain-core==1.6.12 …`, the memo's version; `--with
   mcp==<the then-current release, named exactly>` against the SDK's in-memory server), and the
   commands and outputs go in the landing notes (§4.10, §7). The CHANGELOG gains a line.

## Intent

An embedder hands `run` a few decorated functions. The guest writes `from host import tools` and
calls them. Every call is counted and capped before its bytes are read, validated, optionally
gated, bounded by the call's deadline and cancel, and recorded in the result. Nothing a guest or
a tool does makes `run` raise, and no call's tools can starve another's.

## Design

```
src/wasi_python/runner.py             run/run_async(tools=, gate=, max_tool_calls=); _checked;
                                      Defaults.tool_calls; the MANIFEST check; _door(admit=);
                                      _instance builds _ToolHost after stop_at; _Call carries
                                      admit; Completed.tools
src/wasi_python/tools.py              _Bounded: the invoke of Decisions 3 to 5
tests/unit/test_runner_tools.py       refusals, the door's admit, the bound with fakes
tests/checks/test_v1_4_embedding.py   end to end
README.md, CHANGELOG.md
```

## Scope

In: the above. Out: everything 031's Scope leaves out; async tools and `batch` (decision 15's
later specification); `admit` for the raw `host=`; a shared tool pool.

## Acceptance criteria

Each new check is seen failing first: against today's code where the name is missing, and
against the stand-in named where the property is the point. Nothing measures time. A tool that
must block waits on a `threading.Event` the check sets; a short `timeout_s` only chooses the
outcome, and the check asserts the outcome and the record, never a duration.

**Unit** (`tests/unit/test_runner_tools.py`):
1. `test_run_refuses_mistakes_before_anything_runs`: `host=` with `tools=`; `gate=` without
   `tools=`; `max_tool_calls=` without `tools=`; duplicate names; a non-callable gate; a
   coroutine gate; `max_tool_calls` of `True`, `-1`, `2**63` and `"10"`. Each raises from `run`
   and from `run_async` (before the executor is called), with zero artifact lookups. `Defaults`
   built from three arguments works, and `DEFAULTS.tool_calls == 1000`. A `MANIFEST` without the
   guest package's recipe line raises `ArtifactsMissing` naming it.
2. `test_the_door_refuses_by_length_before_reading`: `_door` with a fake caller and a memory that
   counts reads; an `admit` that refuses leaves the read count at 0 and writes its answer; an
   `admit` that passes reads once; no `admit` (the raw door) reads once. Stand-in: `admit`
   called after `memory.read`.
3. `test_the_bound_answers_in_order`: `_Bounded` with fakes for the ticker, `cancel` and the
   Ctrl-C flag: each of the four ends answers its kind; under two ticks left it answers
   `timeout` without starting the work; the Ctrl-C flag is still set afterwards; a fifth call
   with 4 abandoned is answered at once and its work never starts; a thread start that raises
   `RuntimeError` gives a `tool_error` outcome whose `fault` begins `"RuntimeError"`, and
   nothing raises (C2). Stand-in for the last: a bound that lets the start's exception out.
   (Amended 2026-10-18 by the build review: exactly two ticks left also answers at once (F5);
   a result whose thread finished, or only filled its slot, before an end is seen is delivered
   and never counted abandoned, two cases driven by a fake ticker (F3); the fork hook is
   checked in a forked child (F4); 1,000 `list` frames then four abandoned calls give
   `record.abandoned == 4` (F2).)

**End to end** (`tests/checks/test_v1_4_embedding.py`, the built artifact set):
4. `test_a_guest_calls_a_tool`: `run(tools=[…])`, the guest imports and calls two tools, one
   result fed to `pandas.DataFrame`; stdout as expected; `done.tools.outcomes` is `list ok`,
   `call ok`, `call ok`; `done.tools` is `None` for a call without `tools=`. A guest that calls
   a tool and then runs out of fuel returns `trapped == "out of fuel"` with its `tools` record
   (C6; criteria 10 and 13 cover `"deadline"` and `"cancelled"`).
5. `test_a_huge_frame_is_answered_unread`: under `tools=`, a guest sends four frames of 256 MiB
   through `_host.call`; each is answered `too_large`, the guest catches each, and the run exits
   0 with four `too_large` outcomes whose `request_bytes` is 268,435,456. The bytes the runner
   reads from guest memory are counted, and no read reaches 1 MiB, so the check sees that `run`
   gives the door the frame host's `admit` (amended 2026-10-18 by the build review's F1;
   stand-in: `run` passing no `admit`). A further check, `test_abandoned_calls_are_counted_
   past_the_listed_outcomes`, runs the build review's F2 probe end to end.
6. `test_a_gate_refuses_before_the_tool_runs`: the guest catches `PermissionError` and prints the
   gate's message; the tool's counter is 0; the outcome is `denied` with that message.
7. `test_a_tool_fault_stays_on_the_host`: a tool raises `KeyError` naming a host path; the path
   is in neither stdout nor stderr; the outcome's `fault` begins `"KeyError"`; `run` did not
   raise.
8. `test_the_tool_call_limit_holds`: `max_tool_calls=3`; the guest makes six calls, catching
   `ToolBudgetExceeded`; `frames == 7`, three outcomes `ok` (discovery and two calls) and four
   `budget_exceeded`. Stand-in: a frame host that does not count discovery.
9. `test_a_tool_timeout_ends_the_call_not_the_run`: tool A (`timeout_s=0.05`) waits on event E;
   the guest catches `TimeoutError`, then calls tool B, which sets E (so A's late result arrives
   while B's call is in flight) and returns its own value; the guest prints B's answer, which is
   B's. Outcomes: A `timeout` with `abandoned=True`, B `ok`. Stand-in: one result slot per frame
   host instead of per call.
10. `test_a_tool_blocking_past_the_deadline_is_answered`: under `deadline_s=3`, with no
    `timeout_s`, a tool waits on an event the check sets only after `run` returns; `run`
    returns, and the last outcome is `timeout`. `trapped` is not asserted: the guest may finish
    within the last two ticks. Stand-in: a bound by `timeout_s` alone (the child process meets
    its 120 s fail-safe).
11. `test_abandoned_tools_are_bounded_per_call`: a tool with `timeout_s=0.05` that waits on an
    event; the guest calls it six times; four outcomes are `timeout` and abandoned, the fifth and
    sixth are `timeout` at once, and the tool's start counter is 4. After `run` returns,
    `runner.stats()["tool_threads_running"]` is 4 above its value before the call; once the
    check sets the event and the threads end, it is back (C2).
12. `test_one_calls_stalled_tools_do_not_starve_another`: two `run` calls on two threads. A
    abandons its four tools (they wait on an event the check sets at the end); then B's instant
    tool answers `ok`. Stand-in: a shared pool of four threads (the review's `pool_model`).
13. `test_a_cancel_during_a_tool_call_is_named`: in a child process like spec 015's, the tool
    sets "started", the check sets `cancel`; `trapped == "cancelled"`, `exit_code is None`,
    `fuel_used is None`, last outcome `cancelled` with `abandoned=True`. The answer comes within
    a tick, inside `CANCEL_TICKS`, so this is not counted as a check of 030's overdue path.
14. `test_ctrl_c_during_a_tool_call`: in a child on its main thread, the tool sets "started",
    the child sends itself SIGINT; `run` raises `KeyboardInterrupt`, the tool started once, and
    the child exits within the 120 s fail-safe.
15. `test_cancelling_an_async_call_during_a_tool_call`: `run_async` with a one-worker executor;
    the task is cancelled once the tool has started; it raises `CancelledError` while the tool
    still blocks; a new call on the same executor then completes. Stand-in: a bound that does
    not watch `cancel`.
16. `test_tools_run_off_the_guests_thread`: a tool sees a `contextvars` value the caller set,
    and a thread id other than the caller's.
17. `test_fuel_is_exact_across_tool_calls`: one program with two tool calls, run twice, its
    tools sleeping different amounts each time: the fuel is equal through the judge's driver,
    with `runner._tool_host` as its host; through `run`, `fuel_used` is an `int` (amended
    2026-10-18 by the build review, which accepted the deviation: `run`'s real clock and
    entropy move even `-c pass` by about 10^5, so equality through `run` holds for no
    program).
18. `test_no_tools_no_protocol`: without `tools=`, `from host import tools` raises
    `ImportError` with 031's message; every existing `host=` check passes unchanged.

**The whole:**
19. The two README recipes ran once with pinned versions, as Decision 9 says.
20. `uv run pytest` green with `--accept-judge`; lost 0; grew 0 (the artifact set is 031's).

## The owner's choices

None open here. Two choices, in Decisions 4 and 5, are the agent's where the owner's decisions
were silent: question 53 in `../questions-for-the-owner.md` (no per-call default timeout beyond
the run's deadline, and at most 4 abandoned tools per call). Nothing waits on it.

## Landing notes

Built 2026-10-18 by the implementer (a builder agent, Claude Opus 5.5), in the worktree
`wasi_python-036` on `spec/036-tools-in-the-runner`, from main at `64663de` (031 accepted),
against main's frozen artifact set `build/sets/s-0cdc7b2bd78db6f5` (never rebuilt;
`WASI_PYTHON_ARTIFACTS` pointed at it), darwin-arm64, wasmtime-py 49.0.0. Each claim is EXECUTED
unless it says otherwise. The worktree's `build/` and the scratch folder are not kept, so the
lines that matter are quoted here. Not yet reviewed.

**What changed.**
- `src/wasi_python/runner.py`:
  - `run` and `run_async` take `tools=`, `gate=` and `max_tool_calls=`. `_checked` calls the new
    `_check_tools` first: an iterable of `Tool`s or functions (a function goes through `tool()`),
    names unique, the gate callable and not a coroutine function (031's `_is_async`), the limit by
    `_integer_limit`; `host=` with `tools=`, and `gate=` or an explicit `max_tool_calls=` without
    `tools=`, raise `TypeError`. `wasi_python.tools` is imported only when `tools` is given.
  - `Defaults.tool_calls = 1000` (after `file_calls`), checked by `_integer_limit`; `None` means
    no limit, as for every other limit, and the docstring and README say so (the 031 build
    review's F7).
  - `_has_guest_package(manifest)`, cached per path and `_stamp` (no lock); `_run_checked`
    raises `ArtifactsMissing` naming `recipe … recipes/guest/host/tools.py` before the grants
    are walked.
  - `_door(host, admit=None)`: after the address check, `admit(length)`; bytes it returns are
    the answer and `memory.read` is never called. `_Call(..., admit=None)` passes it on.
  - `_tool_host(c, stop_at, cancel)` builds the call's `_ToolHost` with a `_Bounded` invoke
    (`TICK_S`, `stop_at`, the ticker's count, `cancel`, `_ctrl_c_now`, `_count_tool_threads`).
    `_instance` calls it right after `stop_at` is read, makes the frame host the call's `host`
    and its `admit` the door's, and puts `tool_host.record` in `Completed`, after the store is
    closed, on every ending.
  - `Completed.tools: ToolRecord | None = None`, last.
  - `stats()` gains `"tool_threads_running"`, from `_tool_threads` under `_tool_threads_lock`;
    `_after_fork_in_child` makes that lock anew and sets the count to 0 (Decision 8). The
    `MANIFEST` cache has no lock, so the fork hook does nothing else for it.
- `src/wasi_python/tools.py`: `MAX_ABANDONED = 4`, `DEADLINE_MARGIN_TICKS = 2`; `_Slot` (one per
  tool call); `_Bounded`, the invoke of Decisions 3 to 5; `_Interrupted` gains `message` and
  `fault` (defaults `None`, so 031's two-field use still works), and `_ToolHost` records them.
- Judge: `tests/unit/test_runner_tools.py` (new; criteria 1 to 3 and guards); 15 checks appended
  to `tests/checks/test_v1_4_embedding.py` (criteria 4 to 18); and three existing cache checks
  in that file (`test_runner_caches_the_compiled_module`,
  `test_fuel_does_not_depend_on_the_module_cache`, `test_runner_refuses_a_cache_others_can_write`)
  now expect `stats()`'s new key (`**NO_TOOL_THREADS`, `{"tool_threads_running": 0}`). That last
  edit is a judge change the spec requires (Decision 5 adds the key); the lane accepts it with
  `--accept-judge`.
- `README.md`: *Tools* (the API, capabilities, the gate, the record, errors and `bool(...)` for
  numpy's `bool_`, the limits, own threads, time, abandoned tools and the per-run bound, the
  count in `stats()`, the refusals, two recipes); *Running it* names the new arguments and
  `tools`; *The tool protocol* no longer says "a later release". `CHANGELOG.md`: one entry.

**Choices where the spec was silent, or read one way.**
- **"Less than two ticks left."** The bound's deadline end is reached when the ticker's count is
  at or past `stop_at - 2`. It is checked before the work starts too, so a call with two ticks
  or fewer left is answered `timeout` at once ("<name> timed out: the run's deadline is too near
  to start it"), with no gate or tool run. With exactly two left, starting the work would only
  abandon it at the first slice.
- **Ends checked before the start.** A pending Ctrl-C or a set `cancel` also answers
  `cancelled` at once, unstarted (`abandoned=False`), as does the quota.
- **Order of the ends** in each slice: a delivered result first (if the work finished, its
  answer stands, even at an end); then Ctrl-C, `cancel`, the deadline, `timeout_s`.
- **Messages:** "<name> timed out after 0.05 s" (`timeout_s`, by `:g`), "<name> timed out at
  the run's deadline", "<name> timed out: 4 earlier tool calls are still running", "<name> was
  cancelled". They name the configured limit, never a measured time.
- **The 031 build review's F5** (the catch-all). `_Bounded.__call__` never raises an
  `Exception`: before its thread starts, a fault is a `tool_error` `_Done` ("(internal error)",
  `fault` named); after, it is `_Interrupted("tool_error", abandoned=True, …)` with the fault,
  so the record keeps `op`, `tool` and says the tool may still run; if the work had already
  finished, its own answer stands. A `BaseException` (an embedder's own SIGINT handler raising
  `KeyboardInterrupt` in the wait) passes through, as for a raw `host=`: spec 011's stop.
  Checked by `test_a_fault_in_the_bound_keeps_the_call_in_the_record`.
- **The 031 build review's F7.** `max_tool_calls=None` is exposed and documented as "no limit"
  (docstring, README *Tools*); the default is 1,000. numpy's `bool_`: the README says to return
  `bool(df["x"].any())`.
- **Thread names.** Each tool thread is `wasi-python-tool-<name>`, so checks join them.
- **The count's timing.** A thread is counted in before `start()` (out again if `start()`
  raises) and counted out in its last `finally`, so `stats()` can read one high for an instant
  while a thread exits; the checks join the threads before they read it.

**Seen failing first.** Before any code: `tests/unit/test_runner_tools.py` gave `30 failed`
(each `TypeError: run() got an unexpected keyword argument 'tools'`, or `runner` lacking the
new names). The 16 tool-named checks of `test_v1_4_embedding.py` gave `14 failed, 2 passed`:
every new check failed on `unexpected keyword argument 'tools'` (in process or in its child)
except `test_no_tools_no_protocol`, which uses no new name and guards 031's behaviour; the
other pass was an unrelated check the `-k` filter caught. After the code, the three cache
checks failed on the new key, as expected (`{'compiled': 1, 'loaded': 0, 'written': 1,
'tool_threads_running': 0} != {...}`), before their expectation was updated. Then each named
stand-in was applied to the built code, the checks run, and the files restored byte for byte
(`restored True`):

| stand-in | its checks, failing |
|---|---|
| `admit` called after `memory.read` (c2) | `test_the_door_refuses_by_length_before_reading`, `test_a_frame_host_behind_the_door_counts_a_refused_frame_unread` |
| a bound that lets the start's exception out (c3) | `test_a_thread_that_cannot_start_is_a_fault` |
| a frame host that does not count discovery (c8) | `test_the_tool_call_limit_holds` (`[b'ba', b'ba', b'ba', 'budget', …]`) |
| one result slot per frame host (c9) | `test_a_tool_timeout_ends_the_call_not_the_run` (exit 1), `test_a_late_result_is_dropped_and_each_call_gets_its_own` |
| a bound by `timeout_s` alone (c10) | `test_a_tool_blocking_past_the_deadline_is_answered` (`TimeoutExpired`, 120 s) |
| no quota on abandoned threads (c11, not named by the spec) | `test_abandoned_tools_are_bounded_per_call` |
| a shared pool of four threads (c12) | `test_one_calls_stalled_tools_do_not_starve_another` (B's tool timed out at its 5 s: exit 1, empty stdout) |
| a bound that does not watch `cancel` (c15) | `test_cancelling_an_async_call_during_a_tool_call`, `test_a_cancel_during_a_tool_call_is_named` (both `TimeoutExpired`) |

**Acceptance, with evidence.** Unit (`tests/unit/test_runner_tools.py`, 30 tests, all pass):
1. `test_run_refuses_mistakes_before_anything_runs` (17 cases, each through `run` and through
   `run_async` with an executor whose `submit` must not be reached; `find_artifacts` replaced
   by one that fails if called): `host=` with `tools=` (twice, one with `tools=[]`); `gate=`
   and `max_tool_calls=` (`10` and `None`) without `tools=`; duplicate names (two `Tool`s, two
   plain functions); a gate of `5`; a coroutine gate; `max_tool_calls` of `True`, `-1`, `2**63`,
   `"10"`; `tools="lookup"`, `tools=<a Tool>`, `tools=[5]`, a function without hints.
   `test_the_tool_call_limit_has_a_default`: `DEFAULTS.tool_calls == 1000` and
   `Defaults(1 << 30, 60.0, 16 << 20).tool_calls == 1000`. `test_an_artifact_set_without_the_
   guest_package_is_refused`: `ArtifactsMissing` matching `recipe … recipes/guest/host/tools.py`,
   with `_walk_grants` never called; the cache answers again after the file's stamp changes.
2. `test_the_door_refuses_by_length_before_reading`: refusing `admit`: 0 reads, its bytes
   written; passing `admit`: 1 read; no `admit`: 1 read; addresses past memory: `HOST_FAULT`,
   `admit` not called. `test_a_frame_host_behind_the_door_counts_a_refused_frame_unread`: a
   1 MiB + 1 frame and a frame past `max_calls=1`, both answered with 0 reads.
3. `test_the_bound_answers_in_order` (the four ends: `timeout_s`, the deadline less two ticks
   by a fake ticker, `cancel`, the Ctrl-C flag through the runner's own `_tool_host`, the flag
   still `True` afterwards); `test_too_little_time_or_too_many_abandoned_answers_at_once`
   (one tick left: no gate, no tool; three left: starts; six calls: 4 started, 4 abandoned, 2
   at once with the quota's message; a slot frees when its thread ends);
   `test_a_thread_that_cannot_start_is_a_fault` (`fault` begins `"RuntimeError"`, message
   "slow failed (internal error)", nothing raised, the count back to 0). Also
   `test_a_late_result_is_dropped_and_each_call_gets_its_own`,
   `test_a_fault_in_the_bound_keeps_the_call_in_the_record`,
   `test_the_tool_runs_in_a_copy_of_the_callers_context`,
   `test_stats_counts_tool_threads_and_the_fork_hook_resets_it`,
   `test_completed_has_no_tool_record_by_default`.

End to end (`tests/checks/test_v1_4_embedding.py`, the frozen set), all pass:

4. `test_a_guest_calls_a_tool`: stdout `EMEA 60 ['month', 'sales']\nb'\x00cba'\n`; outcomes
   `list ok`, `call lookup_region ok`, `call reverse ok`; `tools is None` without `tools=`; a
   guest that calls `reverse` and spins under `fuel=10**9` returns `trapped == "out of fuel"`
   with outcomes `list ok`, `call reverse ok` (C6).
5. `test_a_huge_frame_is_answered_unread`: `b"too_large\n" * 4`, exit 0, four outcomes
   `(None, "too_large", 268435456)`.
6. `test_a_gate_refuses_before_the_tool_runs`: stdout `ToolDenied count is not allowed today`;
   the tool never ran; last outcome `denied` with that message.
7. `test_a_tool_fault_stays_on_the_host`: stdout `ToolError open_db failed (internal error)`,
   exit 1 (the second, uncaught call); the path is in neither stream; every call's `fault`
   begins `KeyError` and holds the path.
8. `test_the_tool_call_limit_holds`: `[b'ba', b'ba', 'budget', 'budget', 'budget', 'budget']`,
   `frames == 7`, three `ok` and four `budget_exceeded`.
9. `test_a_tool_timeout_ends_the_call_not_the_run`: stdout `ToolTimeout a timed out after
   0.05 s\nB's answer\n`; outcomes A `timeout` abandoned, B `ok`. B sets the event and joins
   A's thread (`wasi-python-tool-a`) before it returns, so A's late result lands while B's
   call is in flight.
10. `test_a_tool_blocking_past_the_deadline_is_answered` (child): `block timeout True`.
11. `test_abandoned_tools_are_bounded_per_call`: four "stall timed out after 0.05 s", two
    "stall timed out: 4 earlier tool calls are still running"; abandoned `[True]*4 + [False]*2`;
    4 starts; `tool_threads_running` 4 above its value before the call, and back once the event
    is set and the threads are joined.
12. `test_one_calls_stalled_tools_do_not_starve_another`: A (`A done`, 4 abandoned) on one
    thread, then B on another: `now`, outcome `ok`.
13. `test_a_cancel_during_a_tool_call_is_named` (child): `cancelled None None b'' cancelled
    True`.
14. `test_ctrl_c_during_a_tool_call` (child, main thread, SIGINT raised from a helper thread
    once the tool has started): `KeyboardInterrupt 1`; the child exits 0 though the tool's
    thread still blocks.
15. `test_cancelling_an_async_call_during_a_tool_call` (child, a one-worker pool):
    `cancelled while the tool blocks True`, then `b'next\n'`.
16. `test_tools_run_off_the_guests_thread`: the tool returns the context variable the caller
    set (`from the caller`), on a thread id other than the caller's.
17. `test_fuel_is_exact_across_tool_calls`: **read through the judge's driver, not `run`**
    (a deviation from the criterion's wording). Through `run`, fuel is not repeatable at all:
    the guest reads the real clock and real entropy. EXECUTED (`fuel_probe.py`, four runs each):
    `-c pass` without tools gave `82191561, 82095921, 82056035, 82152375`; the two-call program
    with its tool not sleeping gave `92303775, 92304881, 92265765, 92341194`; with
    `PYTHONHASHSEED=0` the spread stayed (`82201278 … 82071294`). The existing cache check says
    the same ("the runner's clock is real and moves the count by about 150,000"). Through the
    judge's driver (fixed clock and entropy) with `runner._tool_host(...)` as its host, the
    program's fuel was `92214720` for pauses of 0, 0.05, 0, 0.05 and 0.2 s (`driver_fuel.py`).
    The check asserts that equality for pauses of 0.05 and 0 s, and, through `run`, that a run
    with tool calls still reports an `int` `fuel_used`.
18. `test_no_tools_no_protocol`: exit 1, `ImportError: this run has no tools: the embedder
    passed none`. Every existing `host=` check passes unchanged.

**The whole.**

19. The recipes, each run once in a throwaway environment against the worktree (scripts in the
    scratch folder; output quoted):
    - `WASI_PYTHON_ARTIFACTS=… uv run --isolated --no-project --with langchain-core==1.6.12
      --with <worktree> python -I recipes/langchain_recipe.py` (a `@langchain_core.tools.tool`
      `search_orders(customer: str, limit: int = 10)` raising `ToolException` for an unknown
      customer):
      ```
      langchain-core 1.6.12 pydantic 2.14.1
      0 None
      (customer: str, limit: int = 10)
      42.5
      ToolError no customer 'bob'
      1 list None ok None None
      2 call search_orders ok None None
      3 call search_orders tool_error no customer 'bob' None
      ```
    - `… --with mcp==2.3.0 …  python -I recipes/mcp_recipe.py` (mcp 2.3.0 was the current
      release; an `mcp.server.mcpserver.MCPServer` with one tool, `forecast(city, days=3) ->
      Forecast` (a `TypedDict`, `structured_output=True`), reached in process through
      `mcp.Client(server)`, with `run_async` on the client's loop):
      ```
      mcp 2.3.0
      0 None
      {'city': 'Oslo', 'highs': [4, 6]}
      ToolError Error executing tool forecast: no forecast for Atlantis
      1 list None ok None None
      2 call forecast ok None None
      3 call forecast tool_error Error executing tool forecast: no forecast for Atlantis None
      ```
      Two things the first try found, now in the README: mcp 2's Python names are snake case
      (`input_schema`, `structured_content`, `is_error`; the wire keeps `structuredContent` and
      `isError`), so the recipe as first written failed with `AttributeError: 'Tool' object has
      no attribute 'inputSchema'`; and a server tool returning a bare `dict` gives no structured
      content (the recipe then returns the text), so the demo server uses a `TypedDict`.
    - The README's first *Tools* example, run as written (`readme_example.py`): `b'Ada\n'`,
      `['ok', 'ok']`.
20. The judge: see below. The artifact set is 031's, unchanged.

**The judge.** In the worktree, no flags, `WASI_PYTHON_ARTIFACTS=…/build/sets/s-0cdc7b2bd78db6f5
uv run pytest` (`ruff check` and `ruff format --check` on `src tests recipes/guest` clean
first). Before any change, the same command gave `216/227 pass · 0 gap · 11 blocked · 0 fail
(unit suite 813/821, 8 skipped)`. After:

```
wasi_python v1: 231/242 pass · 0 gap · 11 blocked · 0 fail   (unit suite 843/851, 8 skipped)
  v1.4  embedding           110/110
ratchet vs c42410a127: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 15 · grew 0 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_tools.py
================= 1074 passed, 19 skipped in 225.26s (0:03:45) =================
```

The 11 blocked are this worktree's (source trees, prior-art clones, the oracle, the wheel, three
systems), as before the change. Gained 15 (the new v1.4 checks), lost 0, grew 0. The lane
accepts with `--accept-judge` (the judge files above).

**What the reviewer should look at.**
- `_Bounded` in `tools.py`: the lock between `_abandon` and the thread's `finally` (a result
  that finishes at an end is delivered, never counted abandoned); the per-call `_abandoned`
  count; that nothing but a `BaseException` leaves `__call__`.
- `_door`'s `admit` placement (after the address check, before `memory.read`), and that the raw
  `host=` path is byte for byte the old one when `admit` is `None`.
- Criterion 17's deviation (the driver, not `run`) and its evidence.
- The three cache checks' changed expectations (a judge change).
- The reading of "less than two ticks" and the ends checked before the start.

### Revised against the build review (2026-10-18)

The build review (`../reviews/036-tools-in-the-runner-2026-10-18.md`; written in the scratch
folder, which the lane copies in) found F1 to F6. First the branch was rebased onto main
`3a9588f` (spec 032's Linux-parity fix): `git rebase main`, no conflict. Each new check below
was seen failing first, against the reviewed code `18f5bd1` or against the review's named
mutant, and passes on the revision (EXECUTED; `revision_mutants.py` applied each mutant, ran the
named checks and restored the files, `restored True`).

- **F1 (`run` passes `admit`).** `test_a_huge_frame_is_answered_unread` now counts the bytes
  read through `wasmtime.Memory.read` in process and asserts no read reaches 1 MiB. Against
  M20 (`host, admit = tool_host, None`): `FAILED`. On the revision: passes.
- **F2 (abandoned calls hidden past the listed 1,000).** Chosen: `ToolRecord.abandoned: int = 0`,
  last, counted in `_ToolHost._note` for every outcome with `abandoned=True`, listed or not
  (`src/` only; the artifact set does not change). Always listing abandoned outcomes was the
  other option; a count keeps the list's bound simple and answers the question the embedder
  asks ("is any tool of this run still running?"). Checks:
  `test_abandoned_calls_are_counted_past_the_listed_outcomes`, unit (through `_ToolHost` and
  `_Bounded`) and end to end (the review's probe: 1,000 `list` frames, then four abandoned
  calls, `max_tool_calls=None`: `frames 1005`, `listed 1000`, `unlisted 5`, 0 abandoned listed,
  `abandoned == 4`). Both failed against `18f5bd1` (`AttributeError: 'ToolRecord' object has no
  attribute 'abandoned'`) and against the count removed. README *Tools* and Decision 7 say so.
- **F3 (the finish/abandon window).** `_abandon` now also returns `False` when
  `slot.filled.is_set()`, under the lock: a result in hand is the answer, and the thread's
  `finally` then decrements nothing. Two unit checks drive the order with a fake ticker:
  `test_a_result_that_finished_at_an_end_is_delivered` (case A) and
  `test_a_result_filled_before_an_end_is_delivered` (case B: a slot whose `filled.set()` holds
  the thread before its `finally`). Case B failed against `18f5bd1` (`timeout`, abandoned) and
  against the fix undone (`if slot.finished:`); M8 (`_abandon` ignores both) fails both cases.
- **F4 (the fork hook in process).** The in-process call is gone.
  `test_the_fork_hook_resets_the_tool_thread_count` runs a fresh interpreter that counts 7
  tool threads, forks, and reads the child: `child 0 True` (count 0, a new lock), then
  `parent 7`. Against M13 (the hook keeps the count): `FAILED`. Skipped where there is no
  `fork`.
- **F5 (the text).** Decision 4 now says "two ticks or fewer"; a case with exactly two left was
  added to `test_too_little_time_or_too_many_abandoned_answers_at_once` (a tool with a short
  `timeout_s`, so a wrong boundary fails instead of hanging). Against M4 (`>` for `>=`):
  `FAILED` (the first try used a tool with no `timeout_s`, and M4 hung until the 240 s
  watchdog; changed so it fails at once). Criterion 17 and Decision 6 are amended as the
  review accepted ("given the same clock and entropy"); criteria 3 and 5 name the new checks.
- **F6.** No change asked.

The judge on the revision (worktree, no flags; `ruff check` and `ruff format --check` on
`src tests recipes/guest` clean):

```
wasi_python v1: 232/243 pass · 0 gap · 11 blocked · 0 fail   (unit suite 847/855, 8 skipped)
  v1.4  embedding           111/111
ratchet vs 947036ec8d: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 16 · grew 0 · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_tools.py
================= 1079 passed, 19 skipped in 205.60s (0:03:25) =================
```

**Rebased onto main `77f516d` (spec 048), 2026-10-18:** one conflict in `_instance`, resolved by keeping 048's guard linker and guard `_Files` table for every call and passing 036's `admit` to `_Call` (the guard linker carries the same door), and both CHANGELOG entries (048's replaces the old fd_readdir known issue); judge (no flags) `236/247 pass · 0 gap · 11 blocked · 0 fail (unit suite 855/863)`, `lost 0 · grew 0 · gained 16`, 048's checks in `test_rules.py`, `test_v1_2_hostile_guest.py`, `test_runner_mounts.py` and `test_runner_grants.py` passing.
