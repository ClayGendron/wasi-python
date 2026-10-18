# 055 — Bounded sessions

- **Status:** drafted 2026-10-18; awaiting its pre-build review (required: it changes the
  guest's exports). §5.6 asks for a review of this specification by an agent or person who did
  not write it, recorded as `../reviews/055-bounded-sessions-spec-YYYY-MM-DD.md`, before any
  build. It is build-class, so after that review it waits for a free build-class slot (§5.7).
- **Owner:** Clay Gendron
- **Kind:** **build-class.** The guest's recipe (`recipes/reactor_main.c`: a new export, `turn`;
  `recipes/reactor_bootstrap.py`: the turn's Python), so both binaries, `MANIFEST`'s recipe
  hashes and the artifact set's exports change. The runner (`src/wasi_python/runner.py`:
  `Session`, `SessionEnded`, the reaper, two `Defaults` fields, a `stats()` key),
  `src/wasi_python/__init__.py` (two names), `src/wasi_python/mounts.py` (the mount table's
  per-turn counters), `src/wasi_python/tools.py` (one abandoned-thread count per session). Judge
  additions and judge changes in `tests/` (Decision 19), `README.md`, `CHANGELOG.md`. **It
  changes the public API** (spec 049, Decision 13): Decision 17 lists the snapshot's lines.
  Step 80 (`scripts/steps/80_snapshot.sh`) is not changed (Decision 19).
- **Depends on:** 049 (the public API frozen: its snapshot, its docstring rules, `defaults()`),
  which must have landed before this is built; 034 (writable mounts: write-back at an ending)
  and 048 (the guard linker), landed; 001, 008, 010, 011, 013, 014, 015, 017, 025, 030, 031,
  032 and 036, landed. Build-class work ahead of it (035, in build; then the queue the roadmap
  orders) may also edit `recipes/reactor_main.c` or `recipes/reactor_bootstrap.py`;
  build-class work is serial, so this is built from main after the work ahead of it has landed
  (the roadmap puts 055 last in the build-class queue, after 044 and 045). Specs 053 (async host functions) and 054
  (read-only code on the import path) are drafted in parallel and will most likely land first;
  Decision 5's rule carries what they add to `run` into `Session`.
- **Research it stands on:** `../research/2026-10-17-state-across-agent-turns.md` (option 1:
  a live instance per session through a second export; its prototype E2, the per-turn fuel and
  memory figures, and E1b's resting shadow stack); this specification's addendum,
  `../research/2026-10-18-bounded-sessions.md` (EXECUTED: fuel and the deadline re-arm per call;
  a trapped store stays callable; one store called from three threads and closed from a fourth;
  the memory cap is a `MemoryError`, not a trap; a turn's output is all delivered when it hands
  control back; `host_alloc` answers NULL at the cap; Wizer keeps a `turn` export; echoing a
  final expression costs about 0.58 M fuel); `../research/2026-10-17-the-runtime-for-agent-code.md`,
  item 11; the owner's decisions 18 to 22 and 49 (`../decisions.md`); constitution §3 (amended
  for bounded sessions), §4.4, §4.6, §4.15, §5.2, §5.6 and §6.

## The problem

An agent writes code one turn at a time. It expects a variable from turn one to exist in turn
two, and a function it defined to stay defined. Today every `run()` is a fresh instance. Each
call starts from the snapshot and forgets everything when it returns.

The owner decided a session is in scope (decision 19): one guest kept across several calls,
with an idle bound and a lifetime, not a shell. The guest gains a second export that runs a turn
without finalizing (decision 18). The bounds are 15 minutes idle and 1 hour of lifetime by
default, both overridable (decision 20). A trap ends the session; pause, resume and rollback
come later (decision 21). 0.1.0 carries it (decision 49).

The research measured the gain. A trivial turn in a live instance costs about 175,000
instructions; a fresh run costs about 82,000,000, some 460 times more. Everything survives:
variables, DataFrames, functions, classes, lambdas.

## Terms

- **Turn:** one piece of code run in a session, after the previous one has returned.
- **Session:** one instance of the guest, kept by the runner across turns, with its own store,
  folders and limits.
- **At rest:** no export of the session's instance is running. Between turns a session is at
  rest.
- **Ended:** a session that will run no more turns. Its store is closed and its folders are
  removed.
- **Idle bound:** the longest a session may stay at rest. **Lifetime:** the longest a session
  may exist from its opening.

## Decisions

1. **A session is a separate, explicit object; `run()` is unchanged.** An embedder opens a
   `Session`, runs turns with `session.run(code)`, and closes it. `wasi_python.run` keeps
   exactly its behaviour, results and fuel: one program, one instance, nothing kept. Nothing in
   `run`'s path calls the new export. A session belongs to the caller that opened it: the
   runner never pools sessions and never hands one to another caller.

2. **The new export: `turn(ptr: i32, len: i32) -> i32`.** It is added in
   `recipes/reactor_main.c`, a recipe file (§4.1; no upstream patch). It adds no import (§4.4
   limits imports, not exports). Its contract, for this runner and for any embedder:
   - **The code.** The host asks `host_alloc(len)` for a buffer, writes the turn's source there
     as UTF-8, and passes the pointer and length. `turn` takes ownership of the buffer and frees
     it on every path, a refusal included.
   - **A NULL pointer with a length above 0** means the host could not get the buffer (the
     addendum, finding 5: `host_alloc` answers 0 at the memory cap, cleanly). The turn then
     raises `MemoryError("no memory for this turn's code")` inside the guest, reports it as any
     exception (Decision 3), and returns 1. The session goes on.
   - **The return value** is the turn's exit status, 0 to 255, as `run` returns one for the
     same code given with `-c`: 0 when the code finished; 1 when it raised (the traceback is on
     stderr); the code of a `SystemExit` it raised (Decision 4). **−1** means refused: `run` was
     already called in this instance, or `len` is negative. A refused turn runs no Python.
   - **`run` and `turn` exclude each other in one instance.** A `run` after a `turn` returns 70
     with the message `python.wasm: run() may be called once per instance, and not after
     turn()`, as a second `run` does today. A `turn` after a `run` returns −1.
   - **It never finalizes.** `Py_FinalizeEx` is never called by `turn`. The interpreter stays
     live in linear memory until the host drops the instance.
   - **Before each turn the host re-arms its limits** (fuel, the epoch deadline) as it does
     before `run`; they are store settings, and the addendum (findings 1 and 2) shows they apply
     per call.
   - **After a trap or an exit** (`proc_exit`, which wasmtime raises as an exit trap), the host
     must not call `turn` again. wasmtime allows it (the addendum, finding 1), but a trap
     unwinds the guest without running CPython's cleanup, so the interpreter's state is not
     safe to enter. Ending the session is the host's job.
   - **The plain reactor** needs `_initialize` once before the first `turn`, as before `run`.
     The first `turn` then initializes the interpreter, as `run` does (a random hash secret).
   - The C function sets `pinned = 0` first, as `run` does; it refuses before anything else if
     `run_called` is set; it sets a new flag, `turned`, which `run` checks beside `run_called`.

3. **What a turn does in the guest.** The Python half is a new function in the frozen
   bootstrap, `_reactor.turn(source, environ)`, compiled into the reactor at step 60 as today.
   `source` is the buffer's bytes, or `None` for the NULL case; `environ` is the WASI
   environment on the first turn and `None` after.
   - **The first turn sets up the session, once.** `os.environ` from WASI, `sys.argv` set to
     `[""]` (as the interactive interpreter has it), and `_refresh(False)`: `random` and
     `numpy.random` reseeded from WASI entropy, logging's start time, `zoneinfo`'s path. Later
     turns reseed nothing, so `random.seed(1)` in one turn governs the next turn's draws, as in
     any interpreter.
   - **Each turn's code is named `<turn N>`**, N counting from 1 in this instance, and is
     registered in `linecache` (as `_reactor.run` does for `-c`), so a traceback shows the
     source lines of the turn that raised and of any earlier turn whose function it called.
   - **The source is decoded as strict UTF-8.** A decode error is reported as an exception
     (exit status 1).
   - **The final expression is echoed.** The source is parsed to an AST. If its last statement
     is an expression, that statement is split off, the rest is executed in
     `__main__.__dict__`, and then the expression is evaluated there and passed to
     `sys.displayhook`, which prints its `repr` to stdout unless it is `None` and binds
     `builtins._`. This is what the interactive interpreter and every notebook do, and
     model-written code relies on it (`df.head()` as a last line). The cost: about 580,000
     instructions more than a plain `compile` for a four-line turn (the addendum, finding 6),
     under 1% of a fresh run. `ast` and `linecache` are already imported in the snapshot.
   - **An exception is reported as the interactive interpreter reports it:** `sys.last_exc`,
     `sys.last_type`, `sys.last_value` and `sys.last_traceback` are set, and the traceback is
     printed through `sys.excepthook` with the bootstrap's own `<reactor>` frames removed
     (`_report`, as today). The turn returns 1. The session goes on.
   - **At the end of every turn**, whatever happened, `sys.stdout` and `sys.stderr` are flushed,
     so all of a turn's output reaches the host before the export returns (the addendum,
     finding 4: wasmtime delivers every byte by then; Python's own buffer is the guest's to
     flush). Other files' buffers are the program's: a file a turn leaves open and unflushed
     keeps its buffered bytes in the guest.
   - Nothing else is reset between turns. `__main__`'s namespace, imported modules, open files,
     the working directory and the random state all persist.

4. **`SystemExit` in a turn is reported, and the session goes on.** `raise SystemExit(3)`,
   `sys.exit(3)`, `exit()` and `quit()` make the turn return their exit status, computed as
   `_reactor.run` computes it today (`None` is 0; an int is its low byte; anything else is
   printed to stderr and is 1). The interpreter is not finalized.
   - **Why it does not end the session.** Model-written code ends scripts with `sys.exit(main())`
     by habit. Ending the session there would destroy every earlier turn's state on a line that
     usually means "this script is done", not "discard my workspace". Jupyter's kernel follows
     the same rule: a `SystemExit` in a cell is reported and the kernel lives. The session's
     life is the embedder's to set (its bounds, `close()`), and the turn's exit status still
     tells the embedder what the code asked for. The research's first recommendation leaned
     the other way ("a trap or an exit ends the session"); the owner's decision 21 settles only
     traps, so this is the agent's choice, recorded for the owner as question 91.
   - **`os._exit(n)` does end the session.** It calls WASI's `proc_exit`, which wasmtime raises
     as an exit trap: the guest's stack unwinds without CPython's cleanup, as at any trap.
     The turn's `exit_code` is `n`, and the session ends with `ended == "exit"` (Decision 8).
   - So the export needs no finalize path at all, which keeps its C small.

5. **The host API: `Session`.** In `runner.py`, exported from `wasi_python`.

   ```python
   from wasi_python import Session

   with Session(grants=[...], tools=[...]) as session:
       session.run("import pandas as pd; df = pd.read_csv('/data/sales.csv')")
       done = session.run("df.groupby('region').total.sum()")
       done.stdout   # the echoed Series
   ```

   - **`Session(*, root=False, grants=(), mounts=(), env=None, host=None, snapshot=True,
     fuel=None, deadline_s=<default>, memory_bytes=<default>, output_bytes=<default>,
     cache_dir=None, artifacts=None, max_file_calls=<default>, tools=None, gate=None,
     max_tool_calls=<default>, idle_s=<default>, lifetime_s=<default>)`.** Every argument is
     keyword-only. Each of `run`'s arguments means here what it means for `run`, with the scope
     the table below gives it. `idle_s` and `lifetime_s` default to the two new `Defaults`
     fields (Decision 9). There is no `argv` and no `stdin`: a turn's input is its code, and
     WASI fixes argv and stdin per store. The guest's stdin is empty: `sys.stdin.read()`
     returns `""`.
   - **The rule for arguments `run` gains.** A session takes every argument of `run` except
     `argv`, `stdin` and `cancel`, with `run`'s meaning, as `run` stands when this is built.
     Two specifications drafted beside this one will most likely have landed by then: 054's
     `import_path=` is per session, applied at the first turn as `run` applies it before its
     program; 053's async tools and gate work in a session's turns as in `run`'s call, and a
     turn by `run_async` passes its loop as `run_async` does. The builder adds each such
     argument to Decision 17's lines, and the review checks them against this rule.
   - **`session.run(code: str, *, fuel=<session's>, deadline_s=<session's>,
     output_bytes=<session's>, cancel=None) -> Completed`** runs one turn and returns how it
     ended.
   - **`await session.run_async(code, *, fuel=…, deadline_s=…, output_bytes=…, executor=None)
     -> Completed`**: the same from async code (Decision 12).
   - **`session.close() -> None`** ends the session; it may be called any number of times.
     **`session.ended -> str | None`** is `None` while the session can run turns, and the reason
     it ended once it cannot (Decision 8). `with Session(...) as s:` closes it on leaving the
     block, however the block ends.
   - **What is per session and what is per turn:**

     | argument | scope | why |
     |---|---|---|
     | `root`, `grants`, `mounts`, `env`, `host`, `tools`, `gate`, `snapshot`, `artifacts`, `cache_dir` | per session | WASI fixes preopens, env and imports per store; the guest lists tools once (`host.tools` at import) |
     | `memory_bytes` | per session | `set_limits` is a store setting, and linear memory never shrinks (the research, E2) |
     | `idle_s`, `lifetime_s` | per session | they bound the session |
     | `fuel`, `deadline_s`, `output_bytes` | per turn; the session's value is each turn's default, and a turn may pass its own | each is re-armed before every turn (the addendum, findings 1, 2 and 4) |
     | `max_file_calls`, `max_tool_calls` | per turn, set once on the session | each turn gets the full allowance; a per-turn override would only widen the surface |
     | `cancel` | per turn only | it stops one turn |

   - **`code`** must be a `str` that `run`'s text rule accepts (`_text`: no NUL, no lone
     surrogate), and at most 2,147,483,647 bytes as UTF-8 (the export's length is an `i32`);
     otherwise `TypeError` or `ValueError` before anything runs, and the session stays open.
   - **Fuel needs a metered session.** Fuel metering changes the compiled code, so the engine
     and module are chosen when the session opens: `Session(fuel=N)` opens a metered session
     whose turns each get `N` unless they pass their own `fuel`; `fuel=None` on one of its turns
     means no cap for that turn (the count is still kept and reported). `Session(fuel=None)`,
     the default, is unmetered: its turns report `fuel_used=None`, and a turn that passes an
     integer `fuel` raises `ValueError` before anything runs.
   - **A session reads the defaults once, when it opens** (049, Decision 2's rule for a call).
     Its turns use the session's values, never the defaults of the moment.

6. **Opening a session runs no guest code.** `Session(...)` does, in order:
   - checks every argument, exactly as `run` does and with the same messages, plus `idle_s` and
     `lifetime_s` (Decision 9), before any work: `TypeError` or `ValueError`, with no artifact
     lookup;
   - finds the artifact set, and refuses with `ArtifactsMissing` a set whose chosen binary does
     not export `turn` (read from the compiled module's exports), naming the export and saying
     the set predates sessions; `tools=` keeps its `MANIFEST` check (spec 036);
   - walks the root and grants, makes a private root for `root=True`, makes HOME where `/tmp`
     is writable, makes the scratch folder (empty stdin, the mounts' placeholder), all as `run`
     makes them for one call, and keeps them, held open, for the session's life;
   - makes the store: the memory cap, the WASI config with the preopens, argv `[ARGV0]` and
     env, the two output keys, the linker (the mount linker with mounts, the guard linker
     without), the mount table, and the epoch callback (`_watch`), so that every turn can be
     stopped (Decision 10);
   - instantiates the module. Instantiation runs no guest code: neither binary has a start
     section (spec 008, Decision 2, checked by the judge). The preopen identity check (spec 017,
     Decision 5) runs here, once.

   A failure after the first folder is made removes what was made and raises as `run` would.
   The session counts as open from here: `stats()["sessions_open"]` goes up by one.

7. **A turn on the host.** `session.run(code)` does, in order:
   1. checks its arguments (Decision 5); then the session's state: `SessionEnded` if it has
      ended, or if its idle bound or lifetime has passed (which ends it first, Decision 9);
      `RuntimeError` if a turn is already running (Decision 10); `RuntimeError` in a process
      forked after the session was used (as `run`).
   2. builds the turn's call: a fresh pair of `_Stream`s put behind the store's two output keys
      (the output cap is per turn; the addendum, finding 4); the turn's fuel (`set_fuel`) and
      epoch deadline, armed as `_instance` arms them today; its `stop_at`, waits and checks; a
      new frame host for `tools=` (Decision 11); the mount table's per-turn counters (Decision
      11); and a `_Call` for the turn, pushed on the calling thread's stack while the turn runs.
   3. runs, under the deferred Ctrl-C and an active epoch ticker: on the first turn only, the
      plain reactor's `_initialize`; then `host_alloc(len)`; then, if it returned a pointer
      within memory, the code is written there; then `turn(pointer, len)`, with 0 as the pointer
      when `host_alloc` returned 0 or a pointer past memory. **All of it is the turn's**: its
      fuel, its deadline, its cancel. A trap or exit in `_initialize` or `host_alloc` is the
      turn's, as in `run`.
   4. reads how it ended, by `_drive`'s rules as they stand: an exit trap is an exit; a trap is
      named by `_trap_name`; a recorded stop holds; a named end (`cancelled`, `deadline`, `out
      of file calls`) holds. `fuel_used` is read by `_fuel_used`'s rules.
   5. hands the mounts' dirty buffers to their providers (Decision 11), on every ending that
      returns a result, after the fuel is read, as spec 034's Decision 8 does for `run`.
   6. returns a `Completed` (Decision 14). If the turn ended the session (Decision 8), the
      session is closed before `run` returns or raises.

   A turn's return value of −1, or any value outside −1 to 255, means the runner and the guest
   disagree. It is a runner fault: the session ends with `"error"` and `run` raises
   `RuntimeError("wasi_python lost track of a session")`, as `_drive` raises for a lost call.

8. **How a session ends, and what `ended` says.** A session ends at the first of these. Each
   closes the store at once, removes HOME, the scratch folder and a private root, releases the
   mount table and the walked folders, and lowers `sessions_open` by one.

   | cause | `ended` | the turn's result |
   |---|---|---|
   | `close()`, or leaving a `with` block | `"closed"` | a turn it interrupted returns `trapped == "cancelled"` (Decision 10) |
   | the idle bound passed while at rest | `"idle"` | no turn ran; the next call raises `SessionEnded` |
   | the lifetime passed | `"lifetime"` | a turn running when it passed returns normally; the session ends as it returns (Decision 9) |
   | a turn called `os._exit` (`proc_exit`) | `"exit"` | `exit_code` is the code, `trapped` is `None` |
   | a turn trapped, or the runner stopped it | the turn's `trapped`: `"out of fuel"`, `"deadline"`, `"cancelled"`, `"out of file calls"`, or wasmtime's name for the trap (`"stack overflow"`, …) | `exit_code` is `None`, as in `run` |
   | `run` raised after the guest started (Ctrl-C; a `BaseException` from the embedder's host, provider, tool or gate; a lost call) | `"error"` | none: `run` raises, as it does today |

   - **A `MemoryError` does not end a session**, nor does an exception, a `SystemExit`, or a
     truncated output. The addendum (finding 3) shows the memory cap is met as a Python
     exception, with every later turn running.
   - **After it has ended**, `run` and `run_async` raise `SessionEnded`, whose `reason` is
     `ended`. `close()` does nothing. `ended` never changes again.
   - **A trap ends the session in this version** (decision 21). Keeping the last good state
     after a trap needs a memory image taken at rest (the research's option 4): a later
     specification.
   - **Closing is a stop, not a shutdown.** No guest code runs at close: no `Py_FinalizeEx`, no
     `atexit` handler, no flush of files the program left open. The idle reaper and the
     collector close sessions on threads where running guest code would be wrong, and a stop
     costs nothing to bound. The README says so: write and close files within a turn. What a
     turn wrote to WASI is already with the host (grants) or the provider (mounts, Decision 11).
   - The fixed strings `"closed"`, `"idle"`, `"lifetime"`, `"exit"` and `"error"` are promised,
     with `Completed.trapped`'s four. wasmtime's trap names are not (049, Decision 5).

9. **The idle bound and the lifetime.**
   - **Defaults:** `Defaults.session_idle_s = 900.0` (15 minutes) and
     `Defaults.session_lifetime_s = 3600.0` (1 hour), the owner's numbers (decision 20). Each
     is a number of seconds, finite and above 0, or `None` for no bound, checked by the rule
     `deadline_s` follows today, generalised to name its argument. `Session(idle_s=…,
     lifetime_s=…)` overrides them for one session (§4.15: every limit has a default; `None` is
     the embedder's explicit choice).
   - **What they measure.** The runner reads one monotonic clock (an internal
     `_session_clock`, `time.monotonic` by default). The idle time is measured from the end of
     the last turn, or from the opening before any turn. The lifetime is measured from the
     opening. A bound has passed when the time measured is at least the bound: an idle bound of
     900 s has passed 900.0 s after the last turn ended. A running turn is never idle.
   - **Where they are enforced: host bookkeeping, no guest timer.** The guest runs nothing at
     rest and cannot see time pass, so nothing in the guest enforces them (the addendum,
     section 7). The runner checks them in two places:
     - **at each call**, before the turn starts: a bound that has passed ends the session with
       its reason, and the call raises `SessionEnded`;
     - **by one reaper thread per process**, a daemon started with the first session. It sleeps
       until the earliest moment any open session's bound passes, recomputed when a session
       opens, finishes a turn or ends, and ends each session whose bound has passed and that
       has no turn running. Without it, an abandoned session would hold its memory (about
       37 MiB resident after a pandas turn, up to its `memory_bytes`; the research, E5b) until
       someone touched it, which is what the bounds exist to prevent.
   - **A running turn is never cut by a bound.** A turn's limits are fixed when it starts: its
     own deadline bounds it. If the lifetime passes during a turn, the turn returns its result
     normally and the session ends as it returns (`ended == "lifetime"`). So a session exists at
     most its lifetime plus one turn's deadline (60 s by default). A turn's deadline does not
     shrink as the session ages, so the same turn ends the same way whenever it is sent.
   - **Injectable, so the judge never sleeps.** The reaper's waiting takes an injected clock and
     wait, as spec 010's `_Waits` and spec 036's `_Bounded` do, and its one step,
     `_reap(now)`, ends what is due at `now` and returns how long to wait. The checks drive
     `_session_clock` and `_reap` with fakes (criteria 13 and 14).

10. **Concurrency: one turn at a time; any thread; sessions share nothing.**
    - **One turn at a time.** A session holds a small state lock around two flags, `ended` and
      `busy`. A turn sets `busy` under it, or fails: a second turn while one runs raises
      `RuntimeError("a turn is already running in this session")` at once, from any thread,
      the turn's own thread included (a raw host function or a provider calling back into its
      own session), and from a tool's thread. Blocking instead would queue a model's next turn
      behind a runaway one, invisibly, and the next turn's code usually depends on the last
      one's result anyway.
    - **Any thread.** Turns may run on whichever thread calls, one after another; the store may
      be closed from another thread (the addendum, finding 2). Each turn pushes its own call on
      its own thread's stack, so the shared host functions (spec 011) serve it.
    - **Sessions share nothing.** Each has its own store, folders and output keys, as
      concurrent `run` calls do (spec 011). Two sessions may run turns at the same time.
    - **`close()` during a turn stops it.** If a turn is running on another thread, `close()`
      sets `ended = "closed"`, stops the turn as `cancel` would (within `CANCEL_TICKS` ticks of
      compute, or at the end of a wait or a tool call, specs 015, 030 and 036), waits for the
      turn to return, and returns once the session is closed. The turn returns `trapped ==
      "cancelled"`. An embedder's shutdown path can therefore end a session without knowing
      whether a turn is in flight. Called on the turn's own thread (a raw host function or a
      provider, which run there), `close()` marks the session and returns at once, since
      waiting there would wait on itself; the turn stops and the session closes as the turn
      returns. Called from a tool's thread, it waits as from any other thread: the turn stops
      waiting for that tool at once (spec 036's cancel), so the wait ends. Each turn's stop
      condition is therefore "its `cancel` is set, or the session is closing", and the
      session's store always has the epoch callback (Decision 6). That costs one Python call
      per `CANCEL_TICKS` ticks of compute and no fuel; the ticker runs during every turn.
    - **No cap on sessions per process.** Each session is opened by an explicit call, holds at
      most its `memory_bytes`, and is reclaimed by its bounds; a count cap would be policy over
      the embedder's own process, which the embedder already controls by opening fewer.
      `stats()["sessions_open"]` lets it watch.

11. **Grants, mounts and tools between turns.**
    - **Grants and the root** are walked once, at the opening, and held for the session's life.
      What a turn writes to a writable grant is on the host when the turn returns. The guest sees
      the folders the session opened with; a host folder swapped after the opening does not
      change what the session's preopens point at.
    - **Mounts.** The mount table lives as long as the session, bound to its store once, so a
      file a turn leaves open stays open for the next turn. Per turn:
      - the counters start at zero (`calls`, `faults`, `refused`, `refused_total`), so each
        turn's `Completed.files` records only that turn's provider calls;
      - `max_file_calls` bounds each turn's provider calls, and "out of file calls" stops the
        turn, which ends the session (Decision 8);
      - **at the end of every turn that returns a result**, dirty buffers are handed to their
        providers, as `run` does at its ending (spec 034, Decision 8; the owner's decision 71).
        An open file stays open; its buffer is clean afterwards. A buffer owed for a file the
        guest closed is dropped once written. So the embedder sees what a turn wrote, through
        its provider, when the turn's result arrives, which is the nearest a session gets to
        POSIX's rule that a write is visible at once. Write-backs count against that turn's
        file calls, as at `run`'s ending.
      - The staging bound stays `memory_bytes` for the session.
    - **Tools** are fixed for the session: the guest lists them once, when `host.tools` is first
      imported, and keeps the functions (READ, `recipes/guest/host/tools.py`). Per turn:
      - a new frame host, so `Completed.tools` records only that turn's frames, and
        `max_tool_calls` bounds each turn. The discovery frame appears in the record of the turn
        that first imported `host.tools`, and in no later turn's;
      - the turn's deadline, cancel and Ctrl-C bound its tool calls, as in `run` (spec 036).
      - **Abandoned tool threads are counted per session**, not per turn: at most
        `MAX_ABANDONED` (4) at once across the session's turns. A per-turn count would let a
        session strand four threads per turn for an hour. The count falls as the threads end,
        as it does today within a call.
    - **A raw `host=`** is the same callable for every turn; the runner keeps nothing for it.

12. **From async code: `run_async`.** `await session.run_async(code, …)` runs the turn on
    `executor` or on `run_async`'s default pool, as `wasi_python.run_async` does (spec 015),
    with the same rules: arguments checked in the coroutine before anything is queued; the
    calling context copied to the worker; a task cancelled while its turn is still queued never
    starts it, and the session is untouched; **a task cancelled while its turn runs stops the
    turn, which ends the session with `"cancelled"`**, and then `CancelledError` is raised once
    the worker has returned. At interpreter exit, a turn running on a worker is stopped with
    `run_async`'s other guests (spec 015's exit hook).

13. **Fork, exit and the collector.**
    - **Fork.** In a process forked after a session was used, `run` and `run_async` raise
      `RuntimeError`, as `wasi_python.run` does (spec 015). `close()` in the child marks the
      session ended and touches neither the store nor any folder: they are the parent's. The
      child has no reaper, an empty registry and `sessions_open` of 0
      (`_after_fork_in_child`). The collector's
      finalizer (below) does nothing in a forked child.
    - **Exit.** An exit hook, registered with the first session (so it runs before `_release`
      frees the engines), closes every session at rest. A session whose turn is still running is
      closed when that turn returns. Folders left by a killed process are swept by spec 016's
      sweep, as `run`'s are.
    - **The collector.** A session no one references is closed by a `weakref.finalize` on its
      state, which holds the store and the folders but not the `Session` object. The reaper
      holds sessions weakly. So a dropped session is closed when it is collected, or by its idle
      bound if a reference cycle delays the collector.

14. **Each turn returns a `Completed`.** No new result type. The fields mean what they mean for
    `run`, for the turn alone:
    - `exit_code`: the turn's exit status (Decision 2), or an `os._exit` code, or `None` when it
      trapped;
    - `stdout`, `stderr`, `truncated`: what this turn wrote, capped at this turn's
      `output_bytes`; nothing from an earlier turn;
    - `trapped`: as `run`'s;
    - `fuel_used`: this turn's instructions, in a metered session, by `_fuel_used`'s rules
      (`None` after a deadline or a stop); `None` in an unmetered session. The first turn's count
      includes the session's setup (Decision 3) and, on the plain reactor, `_initialize` and the
      interpreter's start;
    - `files`, `tools`: this turn's records (Decision 11), or `None` without mounts or tools.

    Whether the session lives on is `session.ended`, read after the turn.

15. **Memory is per session, and a full heap is not a trap.** `memory_bytes` caps the session's
    linear memory for its whole life, because `set_limits` is a store setting. It cannot be per
    turn: memory only grows, so a session holds its high-water mark until it ends (the research,
    E2: `del` of a 50 MB array left 105.6 MiB). A turn that meets the cap gets `MemoryError` and
    the session continues (the addendum, finding 3). A per-turn memory cap needs a memory image
    per turn: the later specification of Decision 8.

16. **Determinism: nothing new is promised.** Fuel counts follow the guest's code and are not
    promised (049, Decision 8). A turn's fuel depends on the turns before it, so it is not the
    fuel of the same code in a fresh run. The first turn reseeds from WASI entropy and reads the
    real clock, which moves its count. The judge checks only that later turns repeat closely:
    the research saw two sessions' identical turns agree to within 9 instructions (EXECUTED, E2,
    four sessions); criterion 16 allows 1,000, a hundred times that, and a wider band seen in
    build is a finding, not a reason to widen the check.

17. **The public API under spec 049.** This specification changes the surface 049 freezes.
    Every line of `tests/public_api.txt` it adds or changes, and the rule of 049's Decision 8
    that allows each (additions a minor release may make; until 0.1.0 alphas may change
    anything, but the list is required either way):
    - `wasi_python.__all__` gains **`Session`** and **`SessionEnded`** (names: an addition).
    - **`Session`**, a class with no public base: its constructor's parameters (Decision 5),
      all keyword-only, with their annotations and defaults (`<default>` where the value comes
      from `defaults()` at the opening); the methods `run`, `run_async` and `close`; the property
      `ended`; `__enter__` and `__exit__`. 049's render records a class's public methods; it must
      also record `Session.__init__`'s parameters and the two context-manager methods, rendered
      explicitly as it renders `Tool.__call__`. That is a change to `tests/harness/api.py`, a
      judge change made here.
    - **`SessionEnded`**, an exception whose base is `RuntimeError` (049, Decision 6: a new
      failure is a subclass of a promised type), with the attribute `reason: str`.
    - **`Defaults`** gains `session_idle_s: float | None = 900.0` and `session_lifetime_s: float
      | None = 3600.0`, last, with defaults (dataclass fields placed last with a default: an
      addition). The `defaults()` line records the two values.
    - **`stats()`** gains the key `sessions_open` (stats keys: an addition).
    - `Completed`, `run` and `run_async` do not change.

    Every new public name, method, property and parameter is documented under 049's Decision
    10: `Args:`, `Attributes:` and `Raises:` sections, no specification numbers in a public
    docstring, no internal name. `Session.run`'s and `run_async`'s `Raises:` name exactly:
    `TypeError`, `ValueError` (a bad argument; the session stays open), `SessionEnded`,
    `RuntimeError` (a turn already running; a forked process; a lost call), `KeyboardInterrupt`
    (`run`) or `asyncio.CancelledError` (`run_async`), and a `BaseException` raised by the
    embedder's own host, provider, tool or gate. The constructor's `Raises:` names the types
    049's Decision 6 lists for `run` before any work and while a call is prepared. An argument
    `Session` shares with `run` is described by the same text in both. The README's generated
    reference shows them. `tests/public_api.txt` and the README block are regenerated with
    `tests/harness/api.py --write` on this branch, and the review checks the diff is exactly
    these lines.

18. **No command line.** `wasi-python run` stays one program, one result. A session needs a host
    process that holds the instance between turns; that process is the embedder's program. A
    command that kept an interpreter alive between invocations would be a shell, which §3 rules
    out, and would add a power `run()`'s command does not have.

19. **The artifact set.**
    - **Both binaries gain the export `turn`, of type `(i32, i32) -> i32`.** Their imports do not
      change: WASI preview1 and `host::call`, as the judge checks today
      (`test_imports_are_wasi_and_the_door_only`).
    - **Step 80 is unchanged.** Wizer removes only the initialisers and keeps every other export
      (the addendum, finding 6: `run`, `host_alloc` today, and a `turn` export on a test module
      through the pinned `wasmtime wizer`).
    - **The bytes grow**: one C function and a larger frozen bootstrap, in both binaries. The
      judge's byte ratchet sees it, and the lane accepts it with `--accept-growth` and the
      reason. `run`'s fuel on the judge's jobs is not expected to move; any change the scoreboard
      shows is stated in the landing notes with its cause (the snapshot's heap layout after a
      larger bootstrap is the likely one), never accepted silently.
    - **`MANIFEST`'s recipe lines** for the two recipe files change hash, as any recipe change
      does. Rebuilds stay byte-identical across hosts (specs 012 and 040): the export adds no
      host-dependent input.
    - **The judge's export lists** (`tests/harness/artifacts.py`: `PLAIN_EXPORTS`,
      `SNAPSHOT_EXPORTS`) gain `turn`, and the check reads its function type: a judge change.

20. **The README.** A new section, `### Sessions`, after `### The tool protocol` and before
    the API reference (049) and `## Safety`:
    - what a session is and is not (one guest across turns; not a shell; nothing is kept after
      it ends);
    - the per-session and per-turn table (Decision 5), the echo, `SystemExit`, and how a session
      ends (Decision 8's table);
    - the bounds and their defaults, that a running turn is never cut, and the reaper;
    - "closing is a stop": write and close files within a turn;
    - **the owner's decision 22: state that outlives a process.** A recipe in which a turn writes
      its state as files to a writable grant (`df.to_csv`, `json.dump`, or `df.to_pickle`;
      Parquet is not available, since pyarrow is not built) and a later session or `run` reads
      them back. It carries the research's caution: only a guest may unpickle what a guest wrote;
      the host never unpickles a guest's file. The recipe runs once, as the README's other
      recipes are run (criterion 28).

    "Any other embedder does the same three things" gains a fourth paragraph: the `turn` export's
    contract (Decision 2), for an embedder that keeps an instance across turns. The constitution's
    §2.4 ("calling one export") still describes the minimum to run a program; a session is
    optional and §3 admits it. No constitution change is needed. The CHANGELOG's unreleased
    section gains, under Added: `Session`, `SessionEnded`, the two `Defaults` fields,
    `stats()["sessions_open"]`, and the `turn` export.

21. **Order of build.** After this review confirms it, the specification waits for a free
    build-class slot. Its builder starts from main after 049 has landed (Decision 17 regenerates
    049's snapshot) and after the build-class work ahead of it has landed, since any of it (035
    first) may edit the same two recipe files. If 049 has not landed when this specification's
    slot comes, the slot passes to the next build-class specification and this one waits.

22. **Left out, each for a later specification or for good.**
    - **Pause, resume, rollback after a trap, and per-turn memory caps** (the research's option
      4, memory images at rest): later, as decision 21 says.
    - **Replay of earlier turns and pickling of globals** (options 2 and 3): not in the product
      (the research's recommendation 5). The README's files-in-a-folder recipe covers state that
      must outlive a process (decision 22).
    - **Changing grants, mounts, tools or env during a session**: they are fixed by the store and
      by the guest's import of `host.tools`; an embedder that needs different ones opens a new
      session.
    - **stdin and argv per session or per turn**: a turn's input is its code.
    - **A session pool, or a session shared between callers**: never; a session belongs to its
      opener (Decision 1).
    - **A cap on sessions per process**: none (Decision 10).

## Intent

An embedder opens a session, sends an agent's code one turn at a time, and gets one result per
turn, each costing a fraction of a fresh run, with variables, functions and data kept between
them. Every turn has its own fuel, deadline, output cap, cancel, file-call and tool-call
allowance; the session has one memory cap, an idle bound and a lifetime, all with defaults. A
trap, an `os._exit`, a bound or `close()` ends the session and frees everything it held at once;
an exception, a `SystemExit` or a full heap does not. `run()` is exactly as it was.

## Design

```
recipes/reactor_main.c            export "turn"(ptr, len) -> i32; the `turned` flag; run() refuses
                                  after a turn; turn() refuses after run()
recipes/reactor_bootstrap.py      _reactor.turn(source, environ): first-turn setup, <turn N>,
                                  linecache, the echo, the interactive interpreter's reporting,
                                  SystemExit's status, the flush
src/wasi_python/runner.py         Session (open, run, run_async, close, ended, context manager);
                                  SessionEnded; Defaults.session_idle_s and session_lifetime_s;
                                  _session_clock; the reaper (_reap, its thread, its injected
                                  wait); the state lock; per-turn streams behind the output keys;
                                  the per-turn _Call on the existing _drive rules; stats()'s
                                  sessions_open; the fork and exit hooks extended
src/wasi_python/mounts.py         _Files: per-turn counters reset; owed buffers dropped once written
src/wasi_python/tools.py          _Bounded: an abandoned-thread count that a session shares
                                  across its turns
src/wasi_python/__init__.py       Session, SessionEnded in __all__
tests/harness/guest.py            turns(): the judge's own driver for `turn` on one instance
tests/unit/test_guest.py          turns() checked against a stand-in module that exports `turn`
tests/unit/test_runner_sessions.py    refusals, the bounds and the reaper with fakes, the state lock
tests/checks/test_v1_4_embedding.py   the export driven raw, and sessions end to end (built set)
tests/harness/artifacts.py        PLAIN_EXPORTS, SNAPSHOT_EXPORTS gain turn; its type checked
tests/harness/api.py, tests/public_api.txt   Session.__init__ and the context methods rendered;
                                  the snapshot regenerated
README.md, CHANGELOG.md
```

The runner's session reuses the per-call pieces as they are: `_check_*`, `_walk_grants`,
`_Private`, `_home_folder`, `_linker`/`_mount_linker`/`_guard_linker`, `_send_outputs`,
`_Call`, `_shared`, `_epoch_answer`, `_watch`, `_trap_name`, `_fuel_used`, `_tool_host`. What
`_call_deferred` and `_instance` do in one call is split into what a session does once (Decision
6) and what each turn does (Decision 7). `run`'s own path is not refactored beyond what that split
needs, and its results and fuel stay as they are (criterion 20).

## Scope

In: the above. Out: Decision 22's list; a command line (Decision 18); any change to `run`,
`run_async` or `Completed`; any new import or a second custom import (§4.4); any change to step
80, the zip or the pins.

## Acceptance criteria

Each new check is seen failing first: against today's code where the name or export is missing,
and against the stand-in named where the property is the point. **Nothing measures time.** The
bounds are checked by an injected clock and by calling the reaper's step; a turn that must block
waits on a `threading.Event` the check sets; a short `deadline_s` only chooses the outcome, and
the check asserts the outcome, never a duration. `sessions_open` is read from `stats()` before and
after, as a count.

**The export, driven raw** (the judge's own driver, `tests/harness/guest.py`, gains `turns()`,
which drives `turn` on one instance without the runner and is itself checked in
`tests/unit/test_guest.py` against a stand-in module; these three checks are in
`tests/checks/test_v1_4_embedding.py`, on the built set):
1. `test_turn_keeps_the_interpreter`: one snapshot instance; `turn` with `x = 41`, then with
   `print(x + 1)`: returns 0 and 0, and stdout is `42\n`. Code is written through `host_alloc`.
   A third `turn` with `raise SystemExit(3)` returns 3, and a fourth with `print(x)` returns 0
   and prints `41`. Stand-in: a `turn` that finalizes (the fourth returns non-zero or traps).
2. `test_run_and_turn_exclude_each_other`: an instance that ran `run` gets −1 from `turn`, and
   no Python runs (stdout and stderr empty); an instance that ran `turn` gets 70 from `run`, with
   the message of Decision 2 on stderr. A negative length gets −1.
3. `test_a_null_code_buffer_is_a_memory_error`: `turn(0, 10)` returns 1, stderr's last line is
   `MemoryError: no memory for this turn's code`, and a next `turn` with `print(1)` returns 0.
   The same on the plain reactor after `_initialize`.

**Unit** (`tests/unit/test_runner_sessions.py`, no artifacts unless named):
4. `test_session_refuses_mistakes_before_anything_runs`: each of `run`'s argument mistakes (one
   per kind from specs 013, 014, 017, 032 and 036's lists), plus `idle_s` and `lifetime_s` of
   `True`, `0`, `-1`, `float("nan")`, `float("inf")` and `"10"`, raises from `Session(...)` with
   zero artifact lookups. `Defaults().session_idle_s == 900.0`, `session_lifetime_s == 3600.0`,
   and `Defaults(session_idle_s=0)` raises `ValueError`.
5. `test_a_turn_refuses_mistakes_and_the_session_stays_open` (built set): `run(b"x")`,
   `run("a\0b")`, `run("\ud800")`, `fuel=5` on an unmetered session, `deadline_s=0`,
   `output_bytes=-1`, `cancel="yes"`: each raises `TypeError` or `ValueError`, `ended` stays
   `None`, and a next turn runs.
6. `test_an_old_artifact_set_is_named` (built set): an artifact set whose snapshot is a
   stand-in module from `tests/harness/wat.py` that exports `memory`, `run` and `host_alloc` but
   not `turn`, beside the real zip and `MANIFEST` (as `_probe_artifacts` in
   `tests/checks/test_v1_2_hostile_guest.py` builds one), makes `Session(artifacts=…)` raise
   `ArtifactsMissing` whose message names `turn`, before any folder is made (`runner._held`
   unchanged) and with `sessions_open` unchanged; `run` with the same set runs the stand-in's
   `run` as today.
7. `test_the_reaper_ends_what_is_due` (fakes): sessions registered with fake due times;
   `_reap(now)` ends exactly those due at `now` with the right reason (`"idle"` or
   `"lifetime"`), skips one whose `busy` flag is set, and returns the wait until the next due
   one; with none open it returns "no wait". A reaper loop driven by an injected clock and wait,
   for a fixed number of rounds, ends sessions in due order. Stand-in: a reaper that ends a busy
   session.
8. `test_one_turn_at_a_time` (built set): a tool blocks on an event inside a turn on thread 1;
   `session.run("1")` on thread 2 raises `RuntimeError` at once; the same call made from inside
   the tool raises `RuntimeError` there too, which the turn sees as a `tool_error` whose `fault`
   begins `"RuntimeError"`; in a session with a raw `host=`, the host function calling
   `session.run` on the turn's own thread gets `RuntimeError`, which the door answers as a host
   fault (the guest's `_host.call` raises `OSError`). After the event is set, turn 1 returns 0
   and a next turn runs. Stand-in: a lock that blocks.

**End to end** (`tests/checks/test_v1_4_embedding.py`, the built set, the snapshot unless named):
9. `test_state_crosses_turns`: turns `x = 41`; `def double(v): return v * 2`; `class P: k = 1`;
   `square = lambda v: v * v`; `import pandas as pd; df = pd.DataFrame({"a": [1, 2, 3]})`; then
   `print(double(x) + P.k, square(3), int(df.a.sum()))`: every turn returns `exit_code == 0`,
   and the last prints `83 9 6\n`. `ended is None`.
10. `test_the_last_expression_is_echoed`: `x = 41`, then `x + 1` prints `42\n`; `None` prints
    nothing; `print(1); 2` prints `1\n2\n`; `_ * 2` prints `4\n`; `def f(): pass` prints
    nothing. Stand-in: a turn without the echo.
11. `test_an_exception_or_an_exit_keeps_the_session`: `1/0` returns `exit_code == 1`, its stderr
    ends `ZeroDivisionError: division by zero\n`, and its traceback names `<turn 2>` and shows
    the line `1/0`; a function defined in turn 1 that raises, called in turn 3, shows turn 1's
    source line in turn 3's traceback; `raise SystemExit(3)` returns 3; `sys.exit("bye")` returns
    1 with `bye\n` on stderr; after each, a turn reading earlier variables returns 0, and
    `ended is None` throughout.
12. `test_os_exit_and_a_trap_end_the_session`: (a) `os._exit(4)` returns `exit_code == 4`,
    `trapped is None`; `ended == "exit"`; the next `run` raises `SessionEnded` with `reason ==
    "exit"`; `sessions_open` is back to its value before the opening. (b) A metered session
    (`fuel=10**9`): `while True: pass` returns `trapped == "out of fuel"`, `exit_code is None`;
    `ended == "out of fuel"`. (c) `deadline_s=0.5` on one turn of an unmetered session with
    `while True: pass`: `trapped == "deadline"`, `ended == "deadline"`. (d) `cancel` set by a tool
    that runs inside the turn: `trapped == "cancelled"`, `ended == "cancelled"`. In each,
    `sessions_open` returns to its value before.
13. `test_the_idle_bound_by_an_injected_clock`: `_session_clock` replaced by a counter the check
    advances. Opened at t = 0 with the default bounds: a turn at t = 0 returns 0; at t = 899.9
    (from the last turn's end) a turn returns 0; at 900.0 past that turn's end, `run` raises
    `SessionEnded` with `reason == "idle"`, `ended == "idle"`, and `sessions_open` is back. A
    session opened with `idle_s=None, lifetime_s=None` runs a turn at t = 10^6.
    `_reap(now)` with `now` past an untouched session's idle bound ends it (`"idle"`) with no call
    from the embedder. No sleep anywhere.
14. `test_the_lifetime_by_an_injected_clock`: turns every 600 s of fake time (under the idle
    bound) return 0 until the call at t = 3600, which raises `SessionEnded` with `reason ==
    "lifetime"`. A turn whose tool advances the fake clock past 3600 while it runs returns
    `exit_code == 0` with its output, and afterwards `ended == "lifetime"`. `lifetime_s=None`
    keeps a session past t = 10^6.
15. `test_per_turn_limits_are_per_turn`: (a) fuel: a metered session with budget B; a turn whose
    cost lies between B/2 and B (the builder calibrates its loop count from a measured count and
    records it in the landing notes) runs three times, each `exit_code == 0` and `fuel_used <= B`,
    and the three counts sum to more than B. Stand-in: a budget set once per session (the third
    turn runs out of fuel). (b) output: with `output_bytes=1000`, a turn printing 2,000 bytes
    returns 1,000 bytes and `truncated == ("stdout",)`; the next turn printing `ok` returns
    exactly `b"ok\n"` and `truncated == ()`. Stand-in: one stream for the session. (c) tools:
    `max_tool_calls=2`; turn A imports `host.tools` and makes one call (record: `list ok`,
    `call ok`); turn B makes three calls (two `ok`, one `budget_exceeded`); turn C makes two
    (both `ok`, and no `list` frame).
16. `test_turn_fuel_repeats`: two metered sessions given the same six turns (the first a
    `pass`, then five of criterion 9's): turns 2 to 6 have `fuel_used` equal within 1,000
    between the two (Decision 16).
17. `test_memory_is_per_session_and_not_a_trap`: `memory_bytes=256 * 2**20`:
    `np.zeros(300_000_000, np.int8)` returns 1 with `_ArrayMemoryError` on stderr; a turn that
    appends 64 KiB `bytearray`s until `MemoryError`, catches it and keeps the list returns 0; a
    next turn whose code is 1 MiB (a comment pads it) returns 1 with `MemoryError: no memory for
    this turn's code`; a short turn then returns 0; `ended is None` throughout.
18. `test_mounts_and_grants_across_turns`: a writable mount whose provider records writes: turn 1
    opens `/m/out.txt`, `os.write`s `a` and leaves it open: when `run` returns, the provider has
    received one write of `b"a"`; turn 2 writes `b` to the same descriptor and closes it: the
    provider's last write is `b"ab"`; each turn's `files.calls` counts only its own calls. A
    writable grant: a file turn 1 writes is on the host when turn 1 returns. `max_file_calls=3`
    with a turn that makes more ends it `"out of file calls"` and the session with it.
19. `test_sessions_share_nothing`: two sessions on two threads, turns interleaved by events:
    `x = 1` in A, `x = 2` in B, then each prints its own `x`; a file A writes in its private root
    (`root=True`) does not exist in B's; `sessions_open` rises by 2 and returns.
20. `test_run_is_unchanged`: the judge's existing `run` checks and jobs pass with their accepted
    fuel and outputs (the scoreboard's ratchet: lost 0, fuel grown 0 unless the landing notes
    state it, Decision 19).
21. `test_close_ends_and_cleans_up`: a `root=True` session; `close()` sets `ended == "closed"`;
    the runner's held private-folder names (`runner._held`) shrink by the session's two (root
    and scratch); `close()` again does nothing; `run` raises `SessionEnded("closed")`; a `with`
    block that raises inside closes the session too. A `close()` from another thread while a tool
    blocks inside a turn returns only after the turn has returned with `trapped == "cancelled"`
    (the check orders this by events), and `ended == "closed"`.
22. `test_run_async_on_a_session`: a turn by `run_async` returns its `Completed`; a task
    cancelled while a tool blocks inside its turn raises `CancelledError`, the session's `ended`
    is `"cancelled"`, and a new session on the same executor then runs a turn. A task cancelled
    while its turn is still queued (a one-worker executor kept busy) never starts it, and
    `ended is None`.
23. `test_ctrl_c_during_a_turn`: in a child on its main thread, a tool sets "started" and the
    child sends itself SIGINT: `session.run` raises `KeyboardInterrupt`, `ended == "error"`, and
    the child exits within the 120 s fail-safe.
24. `test_fork_exit_and_the_collector`: (a) in a child forked after a session ran a turn,
    `session.run` raises `RuntimeError`, and after the child exits the parent's session runs a
    turn that reads a file in its private root. (b) A child process opens a `root=True` session,
    runs a turn and exits without `close()`: the child prints the folder names the runner holds
    (`runner._held`) before it exits, and after it exits none of them exists in the temporary
    folder. (c) A session dropped without `close()`: after `gc.collect()`,
    `sessions_open` is back to its value before.
25. `test_a_session_on_the_plain_reactor`: `Session(snapshot=False)` runs `print(1)` then
    `print(2)`: `1\n` then `2\n`, both `exit_code == 0`.

**The artifact set and the whole:**
26. `test_plain_reactor_exports` and `test_snapshot_exports` require `turn`, of type `(i32, i32)
    -> i32`, in both binaries; `test_imports_are_wasi_and_the_door_only` passes unchanged.
27. `tests/public_api.txt` and the README's reference block are regenerated; the diff is exactly
    Decision 17's lines; the docstring checks of 049's Decision 10 pass.
28. The README's sessions recipe and its files-in-a-granted-folder recipe ran once, as written
    (Decision 20).
29. `uv run ruff check`, `ruff format --check` and `uv run pytest` green with `--accept-judge`
    (the judge changed: Decision 19's export lists, 049's render, the new checks) and
    `--accept-growth` with the bytes' reason; lost 0.

## The owner's choices

None open here. The owner's decisions 18 to 22 and 49 are carried as written. Four choices are
the agent's where those decisions are silent, and are recorded for the owner as question 91 in
`../questions-for-the-owner.md`; nothing waits on it: `SystemExit` keeps the session (Decision
4); closing is a stop with no shutdown (Decision 8); a running turn is never cut by the lifetime
(Decision 9); the final expression is echoed (Decision 3).

## Landing notes
