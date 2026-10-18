# 036 — Tools in the runner

- **Status:** drafted 2026-10-17, split from spec 031 by its pre-build review
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
     door. If less than two ticks are left, the call is answered `timeout` at once, and neither
     gate nor tool runs;
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
     whose tools answer the same spends the same fuel (031's list order makes discovery the same).

7. **The record in the result.** `Completed` gains `tools: ToolRecord | None = None`, last, so
   positional use is unchanged; it is `None` for a call without `tools=`, as 032's `files` is
   for a call without mounts. With `tools=` it is returned on every ending: an exit, a trap,
   `"deadline"` and `"cancelled"` (the review's C6). Only when `run` raises (a Ctrl-C) is there
   no `Completed`. `ToolRecord` and `ToolOutcome` are 031's. The command line's JSON
   does not change.

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

**End to end** (`tests/checks/test_v1_4_embedding.py`, the built artifact set):
4. `test_a_guest_calls_a_tool`: `run(tools=[…])`, the guest imports and calls two tools, one
   result fed to `pandas.DataFrame`; stdout as expected; `done.tools.outcomes` is `list ok`,
   `call ok`, `call ok`; `done.tools` is `None` for a call without `tools=`. A guest that calls
   a tool and then runs out of fuel returns `trapped == "out of fuel"` with its `tools` record
   (C6; criteria 10 and 13 cover `"deadline"` and `"cancelled"`).
5. `test_a_huge_frame_is_answered_unread`: under `tools=`, a guest sends four frames of 256 MiB
   through `_host.call`; each is answered `too_large`, the guest catches each, and the run exits
   0 with four `too_large` outcomes whose `request_bytes` is 268,435,456.
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
17. `test_fuel_is_exact_across_tool_calls`: one program with two tool calls, run twice under a
    fuel cap, its tools sleeping different amounts each time; `fuel_used` is equal.
18. `test_no_tools_no_protocol`: without `tools=`, `from host import tools` raises
    `ImportError` with 031's message; every existing `host=` check passes unchanged.

**The whole:**
19. The two README recipes ran once with pinned versions, as Decision 9 says.
20. `uv run pytest` green with `--accept-judge`; lost 0; grew 0 (the artifact set is 031's).

## Questions for the owner

None open here. Two choices, in Decisions 4 and 5, are the agent's where the owner's decisions
were silent: question 53 in `../questions-for-the-owner.md` (no per-call default timeout beyond
the run's deadline, and at most 4 abandoned tools per call). Nothing waits on it.

## Landing notes

Not built.
