# 055 — Bounded sessions

- **Status:** revised against its pre-build review; awaiting the reviewer's confirmation.
  Drafted 2026-10-18; reviewed before build the same day, as §5.6 requires since it changes
  the guest's exports (`../reviews/055-bounded-sessions-spec-2026-10-18.md`, also a security
  review of the design; verdict: ready once F1 to F7 are written in), and revised against all
  fifteen findings (the Disposition, at the end, says where each went). F4 follows the landing
  lane's ruling: the lifetime is tightened, not left to the owner. It is build-class, so once
  confirmed it waits for a free build-class slot (§5.7).
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
  (the roadmap puts 055 last in the build-class queue, after 044 and 045). Specs 053 (async
  host functions) and 054 (read-only code on the import path) are drafted in parallel and will
  most likely land first;
  Decision 5's rule carries what they add to `run` into `Session`, and Decision 5 says how
  each applies in a session. **056** (the 0.1.0a4 security review's fixes to `tool()` and the
  frame host: partial keywords bounded, no tool run after its call is answered) lands first:
  a session keeps its tools and their late threads across turns, so those fixes matter more
  here (the review, F12).
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
- **Idle bound:** the longest a session may stay at rest. **Lifetime:** how long after its
  opening a session's guest may run: no guest instruction runs past it (Decision 9 gives the
  exact promise).

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
     stderr); the code of a `SystemExit` it raised (Decision 4). **−1** means refused, and only
     the C side refuses (below). A refused turn runs no Python.
   - **The C side owns the range** (the review, F1). Guest code can import `_reactor` and
     replace its functions (EXECUTED by the review, `pa_reactor_patch`: `replaced: 300 -1` on
     both binaries), so what Python returns is guest-controlled. The export therefore: calls
     the turn function through a strong reference it took when the bootstrap was loaded
     (`init_interpreter`), never through `sys.modules["_reactor"]`, so replacing
     `_reactor.turn` or deleting the module changes nothing; maps a result that is an `int` to
     its low byte (`& 0xFF`, the rule `SystemExit`'s status follows) and anything else, a
     failed call included (printed with `PyErr_Print`), to 1. So `turn` returns −1 **only** for
     its own refusals, which this runner never triggers, and Decision 7's "lost track" rule
     names only a runner fault. Nothing a guest does makes `session.run` raise.
   - **The C refusals, each returning −1 with no Python run** (the review, F8): `run` was
     already called in this instance; `len` is negative; or a turn is in progress or did not
     return. An `in_turn` flag is set when `turn` starts and cleared only when it returns
     normally; a trap or `proc_exit` unwinds without running C, so after one the flag stays set
     and every later `turn` is refused, as is a re-entrant `turn` from a door callback. The
     guest thereby defends itself against any embedder that breaks the next rule.
   - **Copy, then free.** The export copies the buffer into a `bytes` object and frees the
     buffer before any Python runs, so a large turn never holds twice its size. `turn(0, 0)`
     is an empty turn: it returns 0.
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
     safe to enter. Ending the session is the host's job; the guest also refuses such a call
     (the `in_turn` flag, below).
   - **The plain reactor** needs `_initialize` once before the first `turn`, as before `run`.
     The first `turn` then initializes the interpreter, as `run` does (a random hash secret).
   - The C function sets `pinned = 0` first, as `run` does; it makes the refusals above before
     anything else; it sets a new flag, `turned`, which `run` checks beside `run_called`.

3. **What a turn does in the guest.** The Python half is a new function in the frozen
   bootstrap, `_reactor.turn(source, environ)`, compiled into the reactor at step 60 as today.
   `source` is the buffer's bytes, or `None` for the NULL case; `environ` is the WASI
   environment and argv on the first turn and `None` after.
   - **The first turn sets up the session, once.** `os.environ` from WASI; any WASI arguments
     after `argv[0]` appended to `sys.path`, in order, after the stdlib zip (the session's
     import path, Decision 5); `sys.argv` set to `[""]` (as the interactive interpreter has it)
     and `sys.orig_argv` to `[ARGV0]`; `builtins.exit` and `builtins.quit` rebound (below); and
     `_refresh(False)`: `random` and `numpy.random` reseeded from WASI entropy, logging's start
     time, `zoneinfo`'s path. This setup is not a numbered turn, prints nothing and registers
     nothing in `linecache`, so `<turn 1>` is the embedder's first code as written. Later turns
     reseed nothing, so `random.seed(1)` in one turn governs the next turn's draws, as in any
     interpreter.
   - **`exit()` and `quit()` leave stdin open** (the review, F13). `site`'s `Quitter` closes
     `sys.stdin` before it raises `SystemExit` (EXECUTED by the review,
     `pc_exit_closes_stdin`). In `run` that does not matter, since the program ends; in a
     session, which goes on after `exit()` (Decision 4), every later `sys.stdin.read()` would
     raise `ValueError`. So the session's setup rebinds both names to instances of a subclass
     of `site`'s `Quitter` whose call raises `SystemExit(code)` without closing stdin; their
     `repr` is unchanged.
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
     traps, so this is the agent's choice, recorded for the owner as question 92.
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
     Two specifications drafted beside this one will most likely have landed by then, and how
     each applies is decided here (the review, F5 and F11):
     - **054's `import_path=`** is per session, checked at the opening by 054's rules (its
       Decisions 2 to 5 and 9: guest paths served by read-only grants, nothing writable under
       one). `run` applies it through an argv prelude (054, Decision 7); a session has no argv
       and `turn` takes source, so that prelude does not carry over. Instead the session's WASI
       argv is `[ARGV0, *entries]`, and the first turn's setup (Decision 3) appends
       `argv[1:]` to `sys.path` after the zip. This is the guest-side mechanism 054 foresaw
       ("if a later build-class change rebuilds the bootstrap … the mechanism may move into the
       guest"); `run`'s prelude is unchanged. No turn number is consumed, no line moves, and
       nothing is printed (criterion 30). Without `import_path=`, argv is `[ARGV0]`.
     - **053's async tools and gate** work in a session's turns as in `run`'s call. A session
       driven by `session.run` (synchronous) owns **one** private tool loop for its whole
       life, not one per turn: a session's tools persist across turns, and an async tool that
       caches a loop-bound client (HTTP, MCP) on its first await must find the same loop in
       turn 2. At each turn's end the loop's pending tool tasks are cancelled, as 053 does at a
       call's end; the loop is closed when the session ends. A turn by `run_async` uses the
       caller's loop, as 053's `run_async` does. The README says: an async tool that caches a
       loop-bound object needs all of a session's turns on one loop (all through `run`, or all
       from one event loop).
     The builder adds each such argument to Decision 17's lines, and the review checks them
     against this rule.
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
   - makes the store: the memory cap, the WASI config with the preopens, argv (`[ARGV0]`, plus
     the import path's entries, Decision 5) and env, the two output keys, the linker (the mount
     linker with mounts, the guard linker without), the mount table, and the epoch callback
     (`_watch`), so that every turn can be stopped (Decision 10);
   - takes the session's **clock base**, `origin_ns = time.perf_counter_ns()`, once, as the WASI
     config is made, and keeps it for every turn (the review, F6). wasmtime's monotonic clock
     counts from the store's WASI context, made once; the guest's `time.sleep` reaches
     `poll_oneoff` as an absolute monotonic time (EXECUTED by the review, `pd_sleep_abstime`:
     `ABSTIME=True`), which the runner turns into a wait by subtracting `perf_counter_ns() -
     origin_ns` (READ, `_poll_oneoff`). A base taken per turn, as `_instance` takes one per
     call, would make `time.sleep(1)` an hour into a session wait about an hour, until the
     deadline killed the session. Each turn's `_poll_oneoff` is built with the session's base
     (criterion 31);
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
      epoch deadline, armed as `_instance` arms them today, with the turn's effective deadline,
      the lesser of its `deadline_s` and the session's lifetime left (Decision 9); its
      `stop_at`, waits and checks, on the session's clock base (Decision 6); a
      new frame host for `tools=` (Decision 11); the mount table's per-turn counters (Decision
      11); and a `_Call` for the turn, pushed on the calling thread's stack while the turn runs.
   3. runs, under the deferred Ctrl-C and an active epoch ticker: if the turn's stop is already
      set (its `cancel`, or a `close()`), no guest code runs and the turn returns `trapped ==
      "cancelled"` with the session left as it was, at rest and untouched, the same rule as a
      `run_async` turn cancelled while queued (the review, F10), unless the stop was a
      `close()`, which ends it as `"closed"`. Otherwise: on the first turn only, the plain
      reactor's `_initialize`; then `host_alloc(len)`; then, if it returned a pointer `p` with
      `p != 0` and `p + len` at most the memory's size (the check `_door` makes, the review's
      F8), the code is written there; then `turn(p, len)`, with 0 as the pointer when that check
      fails. **All of it is the turn's**: its fuel, its deadline, its cancel. A trap or exit in
      `_initialize` or `host_alloc` is the turn's, as in `run`.
   4. reads how it ended, by `_drive`'s rules as they stand: an exit trap is an exit; a trap is
      named by `_trap_name`; a recorded stop holds; a named end (`cancelled`, `deadline`, `out
      of file calls`) holds. `fuel_used` is read by `_fuel_used`'s rules.
   5. hands the mounts' dirty buffers to their providers (Decision 11), on every ending that
      returns a result, after the fuel is read, as spec 034's Decision 8 does for `run`.
   6. returns a `Completed` (Decision 14). If the turn ended the session (Decision 8), the
      session is closed before `run` returns or raises.

   A turn's return value of −1, or any value outside −1 to 255, means the runner and the guest
   disagree. Since the C side owns the range (Decision 2), no guest code can produce it: it is a
   runner fault, the session ends with `"error"`, and `run` raises `RuntimeError("wasi_python
   lost track of a session")`, as `_drive` raises for a lost call.

8. **How a session ends, and what `ended` says.** A session ends at the first of these. Each
   closes the store at once, removes HOME, the scratch folder and a private root, releases the
   mount table and the walked folders, and lowers `sessions_open` by one.

   | cause | `ended` | the turn's result |
   |---|---|---|
   | `close()`, or leaving a `with` block | `"closed"` | a turn it interrupted returns `trapped == "cancelled"` (Decision 10) |
   | the idle bound passed while at rest | `"idle"` | no turn ran; the next call raises `SessionEnded` |
   | the lifetime passed | `"lifetime"` | at rest: no turn ran, and the next call raises `SessionEnded`; during a turn: the turn's effective deadline was the lifetime's remainder, so it returns `trapped == "deadline"` (or its result, if it finished first) and the session ends as it returns (Decision 9) |
   | a turn called `os._exit` (`proc_exit`) | `"exit"` | `exit_code` is the code, `trapped` is `None` |
   | a turn trapped, or the runner stopped it after guest code ran | the turn's `trapped`: `"out of fuel"`, `"deadline"`, `"cancelled"`, `"out of file calls"`, or wasmtime's name for the trap (`"stack overflow"`, …) | `exit_code` is `None`, as in `run` |
   | `run` raised after the guest started (Ctrl-C; a `BaseException` from the embedder's host, provider, tool or gate; a lost call) | `"error"` | none: `run` raises, as it does today |

   - **A `MemoryError` does not end a session**, nor does an exception, a `SystemExit`, a
     truncated output, or a cancel that was set before the turn's guest code began (Decision
     7). The addendum (finding 3) shows the memory cap is met as a Python
     exception, with every later turn running.
   - **After it has ended**, `run` and `run_async` raise `SessionEnded`, whose `reason` is
     `ended`. `close()` does nothing. `ended` is set once, by the first cause, under the
     session's state lock, before anything is closed, and never changes again (the review,
     F10).
   - **A trap ends the session in this version** (decision 21). Keeping the last good state
     after a trap needs a memory image taken at rest (the research's option 4): a later
     specification.
   - **Closing is a stop, not a shutdown.** No guest code runs at close: no `Py_FinalizeEx`, no
     `atexit` handler, no flush of files the program left open, and no write-back to a mount's
     provider. The idle reaper and the collector close sessions on threads where running guest
     or provider code would be wrong, and a stop costs nothing to bound. The README says so:
     write and close files within a turn. What a turn wrote to WASI is already with the host
     (grants) or was offered to the provider at that turn's ending (mounts, Decision 11).
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
     - **at each call**, before the turn starts: a bound that has passed (the lifetime included,
       at or after the moment) ends the session with its reason, and the call raises
       `SessionEnded`;
     - **by one reaper thread per process**, a daemon started with the first session. It sleeps
       until the earliest moment any open session's bound passes, recomputed when a session
       opens, finishes a turn or ends, and ends each session whose bound has passed and that
       has no turn running. Without it, an abandoned session would hold its memory (about
       37 MiB resident after a pandas turn, up to its `memory_bytes`; the research, E5b) until
       someone touched it, which is what the bounds exist to prevent.
   - **The lifetime caps each turn's deadline** (the review, F4; the landing lane's ruling of
     2026-10-18: tighten, so the owner's one hour holds, rather than wait for the owner). No
     turn starts at or after the lifetime: the call raises `SessionEnded("lifetime")`. Each
     turn's effective deadline is the lesser of its own `deadline_s` and the lifetime left when
     it starts, converted to ticks as `deadline_s` is (rounded up to a whole tick); a turn with
     `deadline_s=None` still gets the lifetime left. A turn the cap stops returns `trapped ==
     "deadline"`, and the session ends with `"lifetime"`, because the lifetime set that
     deadline; a turn its own deadline stops ends the session with `"deadline"`. A turn that
     finishes before the cap returns normally, and if the lifetime has passed by its end, the
     session ends as it returns (`"lifetime"`).
   - **The exact promise.** No guest instruction runs later than the opening plus the
     lifetime, to within the deadline's own precision (one tick, `TICK_S`, plus the epoch
     check's slack, as for any deadline: spec 010). What can still happen after that moment is
     exactly what `run` allows after its own deadline, and no more: a raw `host=` function or a
     provider call already in flight is waited for (the runner never kills embedder code; a
     tool call is answered at the deadline and its thread abandoned, spec 036); and the turn's
     mount write-backs, made after the guest has stopped, run as at `run`'s ending, bounded by
     the file calls left and the staging bound, not by the clock (spec 034, Decision 8). The
     session's store, folders and memory are released as soon as that turn returns. The idle
     bound needs no cap: a running turn is never idle.
   - **Injectable, so the judge never sleeps.** The reaper's waiting takes an injected clock and
     wait, as spec 010's `_Waits` and spec 036's `_Bounded` do, and its one step,
     `_reap(now)`, ends what is due at `now` and returns how long to wait. The checks drive
     `_session_clock` and `_reap` with fakes (criteria 13 and 14). The lifetime's cap on a
     turn's deadline is computed from `_session_clock`, so criterion 14 drives it with the fake
     clock too.

10. **Concurrency: one turn at a time; any thread; sessions share nothing.**
    - **One turn at a time.** A session holds a small state lock around two flags, `ended` and
      `busy`. A turn sets `busy` under it, or fails: a second turn while one runs raises
      `RuntimeError("a turn is already running in this session")` at once, from any thread,
      the turn's own thread included (a raw host function or a provider calling back into its
      own session), and from a tool's thread. Blocking instead would queue a model's next turn
      behind a runaway one, invisibly, and the next turn's code usually depends on the last
      one's result anyway. `busy` is cleared in a `finally` on every path, so no host error can
      leave a session the reaper skips forever (the review, F10). The reaper takes the state
      lock, finds `busy` clear and the bound passed, sets `ended`, and only then closes, so a
      racing `run` sees `SessionEnded`, never a closed store.
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
      **`close()` blocks** until the turn returns, which includes a raw `host=` function or a
      provider call in flight; called from a coroutine, it blocks that event loop. Its
      docstring says so.
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
        An open file stays open; a buffer that was written is clean afterwards. A buffer owed
        for a file the guest closed is dropped once written. So the embedder sees what a turn
        wrote, through its provider, when the turn's result arrives, which is the nearest a
        session gets to POSIX's rule that a write is visible at once. Write-backs count against
        that turn's file calls, as at `run`'s ending.
      - **A write-back the file-call limit refuses stays dirty** (the review, F7). Today
        `_Files.walk` records the refusal and marks the buffer clean, which is right for `run`,
        whose ending is final (READ, `mounts.py`, `walk`). In a session that would lose the
        bytes quietly while the guest believes the file written. So in a session a refused
        write-back is recorded in that turn's `files.refused` (cause `"limit"`), and the buffer
        stays dirty (an owed buffer stays owed), to be offered again at the next turn's ending.
        A session that ends at rest never offers it (closing is a stop, Decision 8); the earlier
        turn's record already named the refusal.
      - The staging bound stays `memory_bytes` for the session.
    - **Tools** are fixed for the session: the guest lists them once, when `host.tools` is first
      imported, and keeps the functions (READ, `recipes/guest/host/tools.py`). Per turn:
      - a new frame host, so `Completed.tools` records only that turn's frames, and
        `max_tool_calls` bounds each turn. The discovery frame appears in the record of the turn
        that first imported `host.tools`, and in no later turn's;
      - the turn's deadline, cancel and Ctrl-C bound its tool calls, as in `run` (spec 036).
      - **Abandoned tool threads are counted per session**, not per turn: at most
        `_MAX_ABANDONED` (4; 049 makes the name private) at once across the session's turns. A
        per-turn count would let a session strand four threads per turn for an hour. The count
        falls as the threads end, as it does today within a call. An abandoned tool's effect may
        land during a later turn of the same session, or after `close()`; 056 stops a tool from
        starting after its call is answered, but one already running runs to its end (the
        review, F12). The README's abandoned-tools text says so.
    - **What a session holds on the host, for its whole life** (the review, F2). A session keeps
      its store, so it keeps every host file descriptor its guest opened, up to the process's
      limit, until it ends: up to its idle bound after the last turn, at most its lifetime. One
      call's guest can take every descriptor the process has (EXECUTED by the review,
      `pb_fd_exhaust`: 1,014 files under a soft limit of 1,024, 122,870 under macOS's default,
      after which the host's own `open()` failed with `EMFILE`). For `run` that lasts one call
      (the 0.1.0a2 security review's F11; the README's *Not protected*); a session stretches it.
      It also holds up to `memory_bytes` of linear memory and up to `memory_bytes` of mount
      staging on the host. No descriptor cap exists today, for `run` or a session; a cap per
      store is a later specification (Decision 22), and whether it comes before 0.1.0 is the
      owner's (question 92). The README's *Sessions* and *Not protected* say all this, and
      advise a short `idle_s` for untrusted code and a prompt `close()`.
    - **A session is one trust domain** (the review, F3). Every turn runs inside whatever the
      earlier turns left: an earlier turn can hook `builtins`, `compile`, `exec`,
      `sys.displayhook`, `sys.excepthook`, `sys.settrace`, `print` or `_reactor`'s module
      globals, and so read every later turn's source and data, rewrite what later turns print,
      or make them report exit 0 (Decision 2's C-side entry and range narrow the worst case but
      cannot close this: the guest is the whole interpreter). What any turn or tool put in the
      guest, a secret included, stays readable for the rest of the session. The README's
      *Sessions* and *Not protected* say: a turn's output and exit status are only as
      trustworthy as the least trusted turn before it; never send a more trusted turn (a check
      whose exit code the embedder believes, a turn that holds a token) after less trusted
      code in the same session; open a new session for it.
    - **A raw `host=`** is the same callable for every turn; the runner keeps nothing for it.

12. **From async code: `run_async`.** `await session.run_async(code, …)` runs the turn on
    `executor` or on `run_async`'s default pool, as `wasi_python.run_async` does (spec 015),
    with the same rules: arguments checked in the coroutine before anything is queued; the
    session's `busy` flag claimed in the coroutine before the turn is queued, so a queued turn
    is not idle and a second concurrent `run_async` fails at once (the review, F10); the
    calling context copied to the worker; a task cancelled while its turn is still queued never
    starts it, `busy` is released, and the session is untouched; **a task cancelled while its
    turn runs stops the turn, which ends the session with `"cancelled"`**, and then
    `CancelledError` is raised once the worker has returned. At interpreter exit, a turn
    running on a worker is stopped with `run_async`'s other guests (spec 015's exit hook).

13. **Fork, exit and the collector.**
    - **Fork.** In a process forked after a session was used, `run` and `run_async` raise
      `RuntimeError`, as `wasi_python.run` does (spec 015). `close()` in the child marks the
      session ended and touches neither the store nor any folder: they are the parent's. The
      child has no reaper, an empty registry and `sessions_open` of 0
      (`_after_fork_in_child`). The collector's finalizer (below) does nothing in a forked
      child.
    - **Exit.** An exit hook, registered with the first session (so it runs before `_release`
      frees the engines), stops the reaper and waits for its current step, then closes every
      session at rest. A session whose turn is still running is closed when that turn
      returns. Folders left by a killed process are swept by spec 016's sweep, as `run`'s
      are.
    - **The collector.** A session no one references is ended through a `weakref.finalize` on
      its state, which holds the store and the folders but not the `Session` object. The
      finalizer runs wherever the collector fires: on any thread, inside another session's host
      function, or on the reaper while it holds a lock. So it takes no lock and closes nothing:
      it only marks the state dropped and wakes the reaper, which ends and closes it on its own
      thread (the review, F9; the `_outputs_lock` comment records this project meeting a
      finalizer inside a locked block before). The reaper holds sessions weakly. So a dropped
      session is closed soon after it is collected, or by its idle bound if a reference cycle
      delays the collector.

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
    four sessions), but in the door-loop prototype, without the `ast` split, the echo or
    `linecache` (the review, F15). So before the band is fixed, the builder measures the spread
    of turns 2 to 6 through the real export, over at least five sessions each on macOS and on
    Linux, and records it in the landing notes. Criterion 16 allows 1,000 instructions; if the
    measured spread exceeds 10 (a hundredth of the band), that is a finding for the review, not
    a reason to widen the check.

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
    `RuntimeError` (a turn already running; a forked process; a lost call, which only a runner
    fault produces, Decision 2), `KeyboardInterrupt`
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
    - the bounds and their defaults, the lifetime's cap on a turn's deadline and its exact
      promise (Decision 9), and the reaper;
    - "closing is a stop": write and close files within a turn;
    - what a session holds on the host for its life, and that it is one trust domain
      (Decision 11), in *Sessions* and in *Not protected*; an abandoned tool may land during a
      later turn; async tools that cache loop-bound objects (Decision 5);
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
    - **A cap on open host descriptors per store**, for `run` and sessions alike: a later
      specification (the mount and guard linkers show how `path_open` can be shadowed); its
      place before or after 0.1.0 is the owner's (question 92). Until then, Decision 11's
      README text.

## Intent

An embedder opens a session, sends an agent's code one turn at a time, and gets one result per
turn, each costing a fraction of a fresh run, with variables, functions and data kept between
them. Every turn has its own fuel, deadline, output cap, cancel, file-call and tool-call
allowance; the session has one memory cap, an idle bound and a lifetime, all with defaults, and
no guest code runs past its lifetime. A trap, an `os._exit`, a bound or `close()` ends the
session and frees everything it held at once; an exception, a `SystemExit` or a full heap does
not, and nothing a guest does makes `session.run` raise. `run()` is exactly as it was.

## Design

```
recipes/reactor_main.c            export "turn"(ptr, len) -> i32; the `turned` and `in_turn`
                                  flags; run() refuses after a turn; turn() refuses after run(),
                                  during or after an unfinished turn, and a negative length; a
                                  strong reference to the bootstrap's turn; the 0..255 clamp;
                                  copy, then free
recipes/reactor_bootstrap.py      _reactor.turn(source, environ): first-turn setup (env, the
                                  import path from argv, exit/quit rebound, reseed), <turn N>,
                                  linecache, the echo, the interactive interpreter's reporting,
                                  SystemExit's status, the flush
src/wasi_python/runner.py         Session (open, run, run_async, close, ended, context manager);
                                  SessionEnded; Defaults.session_idle_s and session_lifetime_s;
                                  _session_clock; the reaper (_reap, its thread, its injected
                                  wait); the state lock; per-turn streams behind the output keys;
                                  the per-turn _Call on the existing _drive rules; stats()'s
                                  sessions_open; the fork and exit hooks extended
src/wasi_python/mounts.py         _Files: per-turn counters reset; owed buffers dropped once
                                  written; in a session, a refused write-back stays dirty
src/wasi_python/tools.py          _Bounded: an abandoned-thread count that a session shares
                                  across its turns; with 053, one tool loop per session
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
   the message of Decision 2 on stderr. A negative length gets −1. A `turn` called from the
   door during a turn (re-entrant) gets −1; a `turn` after a turn that ran out of fuel gets −1
   with no Python run; `turn(0, 0)` returns 0. Stand-in: an export without the `in_turn` flag
   (the after-trap call runs Python).
3. `test_a_null_code_buffer_is_a_memory_error`: `turn(0, 10)` returns 1, stderr's last line is
   `MemoryError: no memory for this turn's code`, and a next `turn` with `print(1)` returns 0.
   The same on the plain reactor after `_initialize`. Stand-in: an export that reads the NULL
   buffer (it traps).

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
    1 with `bye\n` on stderr; `exit(5)` returns 5, and a later `print(repr(sys.stdin.read()))`
    prints `''` (the review, F13); after each, a turn reading earlier variables returns 0, and
    `ended is None` throughout. Stand-ins: a runner that ends the session on `SystemExit`; a
    setup that leaves `site`'s `exit` (stdin then raises `ValueError`).
12. `test_os_exit_and_a_trap_end_the_session`: (a) `os._exit(4)` returns `exit_code == 4`,
    `trapped is None`; `ended == "exit"`; the next `run` raises `SessionEnded` with `reason ==
    "exit"`; `sessions_open` is back to its value before the opening. (b) A metered session
    (`fuel=10**9`): `while True: pass` returns `trapped == "out of fuel"`, `exit_code is None`;
    `ended == "out of fuel"`. (c) `deadline_s=0.5` on one turn of an unmetered session with
    `while True: pass`: `trapped == "deadline"`, `ended == "deadline"`. (d) `cancel` set by a tool
    that runs inside the turn: `trapped == "cancelled"`, `ended == "cancelled"`. In each,
    `sessions_open` returns to its value before. (e) A `cancel` already set when `session.run`
    is called: `trapped == "cancelled"`, `fuel_used is None`,
    `ended is None`, and a next turn reads an earlier variable (Decision 7). Stand-in for (a):
    a runner that keeps the session after an exit trap.
13. `test_the_idle_bound_by_an_injected_clock`: `_session_clock` replaced by a counter the check
    advances. Opened at t = 0 with the default bounds: a turn at t = 0 returns 0; at t = 899.9
    (from the last turn's end) a turn returns 0; at 900.0 past that turn's end, `run` raises
    `SessionEnded` with `reason == "idle"`, `ended == "idle"`, and `sessions_open` is back. A
    session opened with `idle_s=None, lifetime_s=None` runs a turn at t = 10^6.
    `_reap(now)` with `now` past an untouched session's idle bound ends it (`"idle"`) with no call
    from the embedder. No sleep anywhere. Stand-ins: bounds enforced only by the reaper (the
    call at 900.0 runs); bounds enforced only at call time (the untouched session stays open).
14. `test_the_lifetime_by_an_injected_clock`: turns every 600 s of fake time (under the idle
    bound) return 0 until the call at t = 3600, which raises `SessionEnded` with `reason ==
    "lifetime"`. A turn whose tool advances the fake clock past 3600 while it runs, then
    returns, finishes with `exit_code == 0` and its output, and afterwards `ended ==
    "lifetime"`. **The cap** (Decision 9): at fake t = 3599.5, a turn with the default 60 s
    deadline running `while True: pass` returns `trapped == "deadline"` and `ended ==
    "lifetime"`; the same turn at t = 0 with `deadline_s=0.5` gives `ended == "deadline"`; a
    turn with `deadline_s=None` at t = 3599.5 is stopped the same way. The epoch deadline the
    turn armed is read (through a test hook on the arming, as a count of ticks) and equals
    `ceil(0.5 / TICK_S)` for the capped turn. `lifetime_s=None` keeps a session past t = 10^6.
    Stand-in: a turn whose deadline is not capped (the capped turn's armed ticks are 6,000).
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
    this turn's code`; a short turn then returns 0; `ended is None` throughout. Stand-in: a
    runner that ends the session on a turn's `MemoryError`.
18. `test_mounts_and_grants_across_turns`: a writable mount whose provider records writes: turn 1
    opens `/m/out.txt`, `os.write`s `a` and leaves it open: when `run` returns, the provider has
    received one write of `b"a"`; turn 2 writes `b` to the same descriptor and closes it: the
    provider's last write is `b"ab"`; each turn's `files.calls` counts only its own calls. A
    writable grant: a file turn 1 writes is on the host when turn 1 returns. `max_file_calls=3`
    with a turn that makes more ends it `"out of file calls"` and the session with it.
    **A refused write-back** (the review, F7): with a `max_file_calls` the turn exhausts
    exactly before its ending, a dirty open file's write-back is in that turn's
    `files.refused` with cause `"limit"`; the next turn makes no write to that file, and at its
    ending the provider receives the bytes. Stand-ins: write-backs only at close (turn 1's
    `b"a"` is missing when it returns); today's `walk`, which marks a refused buffer clean (the
    next turn's ending sends nothing).
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
    (the check orders this by events), and `ended == "closed"`. Stand-in: a `close()` that
    returns before the turn has returned (the check sees the order reversed).
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
    folder. (c) A session dropped without `close()`: after `gc.collect()` and one reaper step
    (`_reap`, driven by the check), `sessions_open` is back to its value before, and the
    finalizer itself took no lock (it is called while the check holds the registry lock, and
    returns). Stand-in: no finalizer (the count stays up).
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

**Added by the pre-build review** (end to end unless named):
30. `test_the_import_path_in_a_session` (054 is expected to land first; if it has not, this
    criterion and Decision 5's import-path text move to 054, as whichever lands second carries
    the other's interplay): a session with `import_path=["/lib"]` and a read-only grant of a
    folder holding `mylib.py` imports `mylib` in turn 1, whose traceback for a raising call
    shows `<turn 1>` line 2 as written; `sys.path` ends with `"/lib"` after the zip; turn 1's
    stdout holds only its own output; a writable grant under `/lib` is refused at the opening
    with 054's error and zero folders made. Stand-in: an import path prepended to turn 1's code
    (the line number moves).
31. `test_a_turn_waits_on_the_sessions_clock_base` (unit, fakes): a `_poll_oneoff` built for a
    turn whose `_Call` is made when the injected clock reads the session's base plus 3,600 s;
    the guest asks for an absolute wait ending at base plus 3,601 s (`ABSTIME`, as
    `time.sleep(1)` sends it); the wait is exactly 1 s of fake time. End to end: a test hook
    reads each turn's `_Call` clock base, equal in turns 1 and 3 of one session. Stand-in: a
    base taken per turn (the wait is 3,601 s, cut by the deadline).
32. `test_a_guest_cannot_make_session_run_raise` (the review, F1): turn 1 sets
    `_reactor.turn = lambda s, e: -1`; turn 2 `print(1)` returns `exit_code == 0` with `1\n` (the
    C side's strong reference); turn 3 sets `_reactor._exit_code = lambda e: 300` and raises
    `SystemExit`: `exit_code == 44` (300's low byte); turn 4 sets it to return `"x"` and raises
    `SystemExit`: `exit_code == 1`; turn 5 runs `del __import__("sys").modules["_reactor"]`, and
    turn 6 `print(2)` returns 0. No call raises, and `ended is None` throughout. Stand-in:
    today's text (a turn returning −1 or 300, and `session.run` raises `RuntimeError`).
33. `test_close_on_the_turns_own_thread`: a session with a raw `host=` whose function calls
    `session.close()` and returns `b""`: `close()` returns at once (no deadlock; the check's
    120 s fail-safe), the turn returns `trapped == "cancelled"`, and `ended == "closed"`.
    Stand-in: a `close()` that always waits (the child hits the fail-safe).

## The owner's choices

None open here. The owner's decisions 18 to 22 and 49 are carried as written. Question 92 in
`../questions-for-the-owner.md` records, for the owner, three choices that are the agent's
where those decisions are silent, and one placement; nothing waits on it: `SystemExit` keeps
the session (Decision 4); closing is a stop with no shutdown (Decision 8); the final expression
is echoed (Decision 3); and whether a cap on open host descriptors per store comes before or
after 0.1.0 (Decision 11, Decision 22). The lifetime is no longer among them: following the
landing lane's ruling on the review's F4, a turn's deadline is capped at the lifetime left, so
the owner's one hour holds as a bound on guest execution (Decision 9).

## Disposition of the pre-build review

The review: `../reviews/055-bounded-sessions-spec-2026-10-18.md` (verdict: ready once F1 to F7
are written in). Every finding is fixed in this revision; none is declined.

- **F1 (high), a guest can make `session.run` raise.** Fixed in the export (Decision 2): the C
  side calls the bootstrap's turn through a strong reference taken at initialization, maps an
  `int` result to its low byte and anything else to 1, so −1 comes only from C refusals and
  Decision 7's "lost track" names only a runner fault. Check: criterion 32 (replaced
  `_reactor.turn`, `_exit_code` returning 300 and a non-int, a deleted module).
- **F2 (medium), descriptors and host memory held for the session's life.** Documented in
  Decision 11 ("What a session holds on the host") and in Decision 20's README text (*Sessions*
  and *Not protected*), with the advice of a short `idle_s` and a prompt `close()`. A
  per-store descriptor cap is recorded as a later specification (Decision 22); its place
  relative to 0.1.0 is put to the owner (question 92).
- **F3 (medium), one trust domain.** Documented in Decision 11 ("A session is one trust
  domain") and in the README text of Decision 20: a turn is only as trustworthy as the least
  trusted turn before it; never send a more trusted turn after less trusted code.
- **F4 (medium), the lifetime loosened the owner's number.** Tightened, by the landing lane's
  ruling: no turn starts at or after the lifetime, and each turn's effective deadline is the
  lesser of its own and the lifetime left (Decision 9), with the exact promise written there
  (no guest instruction past the lifetime, within a tick; afterwards only what `run` allows
  past its own deadline: an embedder call in flight and the turn's write-backs). Terms,
  Decisions 7, 8 and 9, the Intent and criterion 14 follow; item 3 is removed from the owner's
  question.
- **F5 (medium), 054's import path.** Decided (Decision 5): the session's WASI argv carries the
  entries, and the first turn's unnumbered setup (Decision 3) appends them to `sys.path`; no
  line moves, nothing is printed; `run`'s prelude is unchanged. Check: criterion 30.
- **F6 (medium), the clock base.** `origin_ns` is per session (Decision 6), each turn's waits
  are built on it (Decision 7). Check: criterion 31.
- **F7 (medium-low), refused write-backs.** In a session a write-back the limit refuses is
  recorded and stays dirty (owed stays owed) for the next turn's ending (Decision 11). Check:
  criterion 18's new part.
- **F8 (low), the export defends itself.** The `in_turn` flag refuses re-entry and any call
  after a trap or exit; the buffer is copied then freed before Python runs; `turn(0, 0)` is an
  empty turn; the host checks `p + len` against memory as `_door` does (Decisions 2 and 7).
  Check: criterion 2.
- **F9 (low), finalizer and reaper locks.** The finalizer takes no lock and only marks the state
  and wakes the reaper; the exit hook stops the reaper and waits for its step first (Decision
  13). Check: criterion 24(c).
- **F10 (low), concurrency details.** Written in: `ended` set once under the lock before any
  close (Decision 8); `busy` cleared in a `finally`, and the reaper's order (Decision 10);
  `run_async` claims `busy` in the coroutine and releases it if cancelled while queued
  (Decision 12); a cancel set before guest code runs leaves the session untouched, unless it
  was a `close()` (Decision 7, criterion 12(e)); `close()` blocks, documented (Decision 10).
- **F11 (low), 053's loop.** One private tool loop per session for synchronous turns, its
  tasks cancelled at each turn's end and closed at the session's end; `run_async` turns use the
  caller's loop; a README line on loop-bound caches (Decision 5).
- **F12 (low), 056 first.** Added to *Depends on*; the README's abandoned-tools text says an
  abandoned tool may land during a later turn or after `close()` (Decision 11).
- **F13 (low), `exit()` closes stdin.** The session's setup rebinds `exit` and `quit` to a
  `Quitter` subclass that does not close stdin (Decision 3). Check: criterion 11.
- **F14 (low), stand-ins.** Named for criteria 3, 11, 12, 13, 14, 17, 18, 21 and 24(c); the
  added criteria 30 to 33 each name one, and 33 covers `close()` on the turn's own thread.
- **F15 (low), the fuel band.** The builder measures the spread through the real export, over
  at least five sessions each on macOS and Linux, before the band is fixed; a spread above 10
  is a finding (Decision 16). The review's note on 049's `_MAX_ABANDONED` is taken (Decision
  11).

## Landing notes
