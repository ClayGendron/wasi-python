# 055 — Bounded sessions

- **Status:** confirmed for build 2026-10-18; revised for the owner's decision (close and
  exit() as Jupyter does); its re-review confirmed (F3's error row and C1 written in, checked
  by the lane). The re-review (`../reviews/055-bounded-sessions-close-revision-2026-10-18.md`,
  copied there by the lane; verdict: ready once F1 to F3 are written in) and where each of its
  findings went: "Disposition of the re-review", near the end. The owner answered question 92
  on the evening of 2026-10-18 (`../decisions.md`, "The owner's answers of 2026-10-18,
  evening"): `sys.exit()` keeping the session and the echo stand; `exit()` and `quit()` now
  end it, as in Jupyter (the lane's ruling on the re-review's F1, Decision 4); a session's
  close and expiry now run Python's shutdown inside a small budget (Decisions 2, 8 and 9, and the section
  "Revised for the owner's decision of 2026-10-18", near the end); the cap on open files comes
  before 0.1.0 as spec 068 and applies to sessions (Decisions 5, 11 and 22). Since the revision
  adds a guest export, §5.6 asks for its delta to be reviewed before build. Earlier history:
  confirmed for build 2026-10-18 (the review's Confirmation, N1–N3 written in);
  build-class: builds in its turn in the queue (after 023 and the scipy line, per the roadmap),
  and after 049, 053, 054, 056 and 068 land. Drafted 2026-10-18; reviewed before build the same day,
  as §5.6 requires since it changes the guest's exports
  (`../reviews/055-bounded-sessions-spec-2026-10-18.md`, also a security review of the design;
  verdict: ready once F1 to F7 are written in); revised against all fifteen findings (the
  Disposition, near the end, says where each went; F4 follows the landing lane's ruling: the
  lifetime is tightened, not left to the owner); confirmed with three notes, N1 to N3, written
  in (the Confirmation's notes, near the end).
- **Owner:** Clay Gendron
- **Kind:** **build-class.** The guest's recipe (`recipes/reactor_main.c`: two new exports,
  `turn` and `shutdown`; `recipes/reactor_bootstrap.py`: the turn's Python), so both binaries, `MANIFEST`'s recipe
  hashes and the artifact set's exports change. The runner (`src/wasi_python/runner.py`:
  `Session`, `SessionEnded`, the reaper and the session's ending, three `Defaults` fields, a
  `stats()` key),
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
  here (the review, F12). **068** (a cap on open files, before 0.1.0 by the owner's decision on
  question 92; drafting on `spec/068-a-cap-on-open-files`) is expected to land first; Decision
  5 says how its cap applies in a session, and if 055 lands first, whichever lands second
  carries the other's interplay (criterion 40). **069** (the snapshot pre-imports no package,
  the owner's decision 34) changes the snapshot's frozen heap, so the ending's fuel figures of
  Decision 8 are re-measured on the set this is built against.
- **Research it stands on:** `../research/2026-10-17-state-across-agent-turns.md` (option 1:
  a live instance per session through a second export; its prototype E2, the per-turn fuel and
  memory figures, and E1b's resting shadow stack); this specification's addendum,
  `../research/2026-10-18-bounded-sessions.md` (EXECUTED: fuel and the deadline re-arm per call;
  a trapped store stays callable; one store called from three threads and closed from a fourth;
  the memory cap is a `MemoryError`, not a trap; a turn's output is all delivered when it hands
  control back; `host_alloc` answers NULL at the cap; Wizer keeps a `turn` export; echoing a
  final expression costs about 0.58 M fuel; and, added for the revision, section 8: Python's
  shutdown in today's guest costs 28 M to 303 M instructions, runs `atexit`, is bounded by fuel
  and the deadline, keeps a left-open file's bytes on the snapshot, when a function is defined
  in `__main__`, only once `gc.freeze()` is undone, and
  how Jupyter closes and culls a kernel, READ from jupyter_client, ipykernel and
  jupyter_server); `../research/2026-10-17-the-runtime-for-agent-code.md`,
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
- **The ending:** what the runner does between a session's end and its store's close. When the
  session is at rest and its interpreter is sound, the ending runs **Python's shutdown**
  (`atexit` handlers, then the interpreter's finalization, which flushes open files) through the
  `shutdown` export, inside the **shutdown budget**: the session's per-turn fuel and
  `shutdown_s` seconds (Decision 8). Otherwise it runs no guest code.
- **Idle bound:** the longest a session may stay at rest. **Lifetime:** how long after its
  opening a session's turns may run: no turn's instruction runs past it, and the ending that
  follows runs for at most `shutdown_s` more (Decision 9 gives the exact promise).

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
     stderr); the code of a `SystemExit` it raised (Decision 4). **256 plus the status** (256
     to 511) means the same status, and that the turn called the interactive `exit()` or
     `quit()`, which asks for the session to end after the turn (Decision 4; the re-review's
     F1). **−1** means refused, and only the C side refuses (below). A refused turn runs no
     Python.
   - **The C side owns the range** (the review, F1). Guest code can import `_reactor` and
     replace its functions (EXECUTED by the review, `pa_reactor_patch`: `replaced: 300 -1` on
     both binaries), so what Python returns is guest-controlled. The export therefore: calls
     the turn function through a strong reference it took when the bootstrap was loaded
     (`init_interpreter`), never through `sys.modules["_reactor"]`, so replacing
     `_reactor.turn` or deleting the module changes nothing; maps a result that is an `int` to
     its low byte (`& 0xFF`, the rule `SystemExit`'s status follows), a result that is a
     `tuple` of exactly two items whose first is an `int` to that int's low byte, plus 256 when
     the second item is `True` itself (an identity test, `== Py_True`, so no guest code runs),
     and anything else, a failed call included, to 1. **No guest code runs in that reading**
     (the re-review's confirmation, C1): the tuple is accepted only if `PyTuple_CheckExact`
     holds and is read only through `PyTuple_GET_SIZE` and `PyTuple_GET_ITEM`, never the
     sequence protocol, so a tuple subclass is "anything else"; an int is accepted only if
     `PyLong_Check` holds and is masked with `PyLong_AsUnsignedLongMask(...) & 0xFF`, which has
     no overflow path, so a huge or negative guest-made int (2**100 + 4, −1) leaves no
     exception pending and does not depend on `-1`'s error convention. The bootstrap's turn returns
     `(status, quit)`, `quit` being whether `exit()` or `quit()` was called (Decision 3); a
     guest that fakes `quit` only ends its own session, which it can do anyway with
     `os._exit`. **A failed call is printed without `PyErr_Print`** (the
     Confirmation, N1): `PyErr_Print` answers a pending `SystemExit` with `Py_Exit`, which
     finalizes, runs `atexit` handlers and exits (EXECUTED by the reviewer through today's
     `run`, `pe_pyerr_print_exits`: a replaced `_reactor._exit_code` raising `SystemExit` gave
     exit 9 and the handler's output, on both binaries). So the C side takes the exception with
     `PyErr_GetRaisedException`, shows it with `PyErr_DisplayException` (a `SystemExit`
     included, never acted on), drops it, and returns 1; the interpreter is never finalized by
     a turn. So `turn` returns −1 **only** for
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
     live in linear memory until the host calls `shutdown` (below) or drops the instance.
   - **Before each turn the host re-arms its limits** (fuel, the epoch deadline) as it does
     before `run`; they are store settings, and the addendum (findings 1 and 2) shows they apply
     per call.
   - **After a trap or an exit** (`proc_exit`, which wasmtime raises as an exit trap), the host
     must not call `turn` again. wasmtime allows it (the addendum, finding 1), but a trap
     unwinds the guest without running CPython's cleanup, so the interpreter's state is not
     safe to enter. Ending the session is the host's job; the guest also refuses such a call
     (the `in_turn` flag, below).
   - **The instance's WASI argv** is `[ARGV0, *entries]`, where each entry is an absolute guest
     path of a read-only folder to put on the import path (the Confirmation, N3); the runner
     enforces that with 054's rules, and another embedder must too, since a relative or
     writable entry would let one turn plant code another imports. The guest's setup skips any
     entry that is not absolute. Ordinary program arguments have no place here: a turn's input
     is its code.
   - **The plain reactor** needs `_initialize` once before the first `turn`, as before `run`.
     The first `turn` then initializes the interpreter, as `run` does (a random hash secret).
   - The C function sets `pinned = 0` first, as `run` does; it makes the refusals above before
     anything else; it sets a new flag, `turned`, which `run` checks beside `run_called`.
   - **The ending's export, `shutdown() -> i32`** (added by the revision, Decision 8). Also in
     `recipes/reactor_main.c`; it adds no import. It runs Python's normal shutdown once, in an
     instance that ran turns:
     - **Its refusals, each returning −1 with no Python run:** no `turn` was ever called in
       this instance (`turned` unset; this covers an instance that ran `run`, which finalizes
       itself, and one where nothing ran); `in_turn` is set (a turn is in progress, a
       re-entrant call from a door callback, or a turn that a trap or `proc_exit` unwound,
       whose interpreter is not safe to enter); or `shutdown` was already called (a new flag,
       `shut`, set before any Python runs, so a call from the door during the shutdown, which
       CPython forbids, "must not be called recursively from within itself … such as `atexit`
       handlers", and a call after a shutdown that trapped are both refused).
     - **What it does:** sets `pinned = 0` and `shut = 1`; calls `gc.unfreeze()` through a
       strong reference, so replacing `gc.unfreeze` changes nothing; then `Py_FinalizeEx()`,
       which runs the `atexit` handlers (last registered, first run) and tears the interpreter
       down, flushing `sys.stdout`, `sys.stderr` and the files the teardown closes; then C's
       `fflush(stdout)` and `fflush(stderr)`, as `run` does. It returns 0, or 120 when
       `Py_FinalizeEx` returned −1 ("errors during finalization (flushing buffered data)"),
       the code `run` already returns for that (the re-review's N2).
     - **The reference is taken by the first `turn`**, after its refusals and before any
       Python runs (the re-review's N1), not in `init_interpreter`: importing `gc` there would
       put it in `sys.modules` for every plain-reactor `run` (EXECUTED by the re-review: today
       `'gc' in sys.modules` is `False` at a program's start on the plain reactor), against
       Decision 1. No guest code has run at that point, so the reference is as safe as one
       taken at initialization.
     - **Why the unfreeze.** The snapshot's initialiser ends with `gc.collect(); gc.freeze()`.
       With `__main__` frozen, a file a program left open beside any function defined in
       `__main__` loses its buffered bytes at `Py_FinalizeEx` on the snapshot, though the
       plain reactor flushes it (the addendum, section 8, P10b: 0 bytes against 100, both
       runs). Undoing the freeze first gives the snapshot exactly the plain reactor's, that is
       CPython's, behaviour (P12). On the plain reactor nothing is frozen and it costs about
       0.5 M instructions. On today's snapshot it raises the whole shutdown from about 85 M to
       about 310 M instructions, because the teardown then reaches the frozen, pre-imported
       stack; spec 069 (no pre-imported package) shrinks that frozen heap, and the builder
       re-measures on the set it builds against. The alternative measured, flushing every live
       file object from a last `atexit` handler, was not taken: it does more than CPython does
       (it also flushes a file held only in a cycle), and its walk of `gc.get_objects()` cost
       about 376 M instructions on the plain reactor after importing pandas, a cost the
       snapshot would share once 069 has landed (P11). An error from the call (a guest cannot reach it through the
       reference, but the C side does not assume so) is taken with
       `PyErr_GetRaisedException`, shown with `PyErr_DisplayException` and dropped, never
       through `PyErr_Print` (the Confirmation, N1), and the shutdown goes on.
     - **After it, every export refuses:** `turn` returns −1 (it checks `shut`), `run` returns
       70 (it already refuses after a turn), `shutdown` returns −1.
     - **Why a new export, not `turn` or `run`.** `turn` promises never to finalize, and N1
       closed the one path by which guest code could make it do so; a finalizing mode of
       `turn` would reopen that. `run` runs once per instance and reads argv; giving it a
       second meaning would blur its contract for every other embedder. A separate, argument-
       free export the guest cannot reach (a guest has no way to call its own exports) keeps
       both contracts as they are. It changes the artifact set's exports (Decision 19), which
       is why §5.6's re-review covers this revision.

3. **What a turn does in the guest.** The Python half is a new function in the frozen
   bootstrap, `_reactor.turn(source, environ)`, compiled into the reactor at step 60 as today.
   `source` is the buffer's bytes, or `None` for the NULL case; `environ` is the WASI
   environment and argv on the first turn and `None` after.
   - **The first turn sets up the session, once.** `os.environ` from WASI; any WASI arguments
     after `argv[0]` that are absolute paths appended to `sys.path`, in order, after the stdlib
     zip (the session's import path, Decision 5; any other entry is skipped, Decision 2);
     `sys.argv` set to `[""]` (as the interactive interpreter has it) and `sys.orig_argv` to
     `[ARGV0]`; `builtins.exit` and `builtins.quit` rebound (below); and
     `_refresh(False)`: `random` and `numpy.random` reseeded from WASI entropy, logging's start
     time, `zoneinfo`'s path. This setup is not a numbered turn, prints nothing and registers
     nothing in `linecache`, so `<turn 1>` is the embedder's first code as written. Later turns
     reseed nothing, so `random.seed(1)` in one turn governs the next turn's draws, as in any
     interpreter.
   - **`exit()` and `quit()` ask for the session to end, and leave stdin open** (the
     re-review's F1; the review, F13). The session's setup rebinds both names to instances of a
     subclass of `site`'s `Quitter`, `repr` unchanged, whose call does two things: it sets the
     bootstrap's quit flag, as ipykernel's `exit` sets the shell's `exit_now` (Decision 4), and
     then raises `SystemExit(code)` as `site`'s does, so the turn stops at that line and
     returns that status. Catching the `SystemExit` does not clear the flag, as nothing clears
     `exit_now` in Jupyter. It does not close `sys.stdin`, unlike `site`'s `Quitter` (EXECUTED
     by the review, `pc_exit_closes_stdin`), so code that catches the `SystemExit` can still
     read stdin in the same turn. At the turn's end the bootstrap's turn returns
     `(status, quit_flag)` (Decision 2).
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
     keeps its buffered bytes in the guest until a later turn flushes it or the session's
     ending runs Python's shutdown (Decision 8).
   - Nothing else is reset between turns. `__main__`'s namespace, imported modules, open files,
     the working directory and the random state all persist.

4. **`sys.exit()` in a turn is reported and the session goes on; `exit()` and `quit()` end
   the session, through Python's shutdown, after the turn.** Both follow Jupyter, as the owner
   asked (question 92, `../decisions.md`: keep the choices where they follow precedent,
   "especially that of Jupyter"; the landing lane's ruling on the re-review's F1,
   2026-10-18).
   - **`raise SystemExit(3)` and `sys.exit(3)`** make the turn return their exit status,
     computed as `_reactor.run` computes it today (`None` is 0; an int is its low byte;
     anything else is printed to stderr and is 1). The interpreter is not finalized, and the
     session goes on. In Jupyter, IPython's `run_code` catches `SystemExit`, shows it and
     warns "To exit: use 'exit', 'quit', or Ctrl-D.", and the kernel lives on (READ,
     `IPython/core/interactiveshell.py`, IPython 9.10.0, `except SystemExit as e:` in
     `run_code`).
   - **`exit(code)` and `quit(code)`** make the turn return the same status, computed the same
     way, and then end the session with `ended == "quit"`. The turn returned normally, so the
     interpreter is sound and the session's ending runs Python's shutdown on the turn's thread
     before `session.run` returns (Decision 8). In Jupyter the two names are one object, the
     shell's exiter (`ns['exit'] = self.exiter`, `ns['quit'] = self.exiter`), a
     `ZMQExitAutocall` whose call sets `keepkernel_on_exit` and calls `ask_exit()`; that sets
     `exit_now`, whose observer stops the kernel's IO loop, and the process leaves through
     Python's normal shutdown, `atexit` handlers included (READ, ipykernel 7.2.0
     `ipykernel/zmqshell.py`, `ZMQInteractiveShell._update_exit_now` and `ask_exit`; IPython
     9.10.0 `IPython/core/autocall.py`, `ZMQExitAutocall.__call__`; the plain REPL agrees:
     `exit()` ends it).
   - **Where the session still differs from Jupyter, and why.** Jupyter's `exit` takes no
     status (its one argument is `keep_kernel`, so `exit(1)` there keeps the kernel) and only
     sets a flag, so the rest of the cell runs before the kernel stops. The session keeps
     Python's own `exit(code)`: it raises `SystemExit(code)`, so the turn stops at that line
     and the status reaches the embedder, which is what model-written scripts mean by
     `exit(1)`. `exit(keep_kernel=True)` is not supported: it raises `TypeError`, as Python's
     `exit` does. Both are the session following Python's `exit` within the turn and Jupyter's
     for the session.
   - **The quit flag wins over the lifetime.** A turn that called `exit()` and returned after
     the lifetime passed ends with `"quit"`: it was asked for first.
   - **Why `sys.exit()` does not end the session.** Model-written code ends scripts with `sys.exit(main())`
     by habit. Ending the session there would destroy every earlier turn's state on a line that
     usually means "this script is done", not "discard my workspace". Jupyter's kernel follows
     the same rule: a `SystemExit` in a cell is reported and the kernel lives. The session's
     life is the embedder's to set (its bounds, `close()`), and the turn's exit status still
     tells the embedder what the code asked for. The research's first recommendation leaned
     the other way ("a trap or an exit ends the session"); the owner's decision 21 settles only
     traps, so this was the agent's choice, put to the owner as question 92. **The owner kept
     it** (2026-10-18, evening: "`sys.exit()` keeps the session … as in Jupyter").
   - **`os._exit(n)` still ends the session at once.** It calls WASI's `proc_exit`, which
     wasmtime raises as an exit trap: the guest's stack unwinds without CPython's cleanup, as at
     any trap. The turn's `exit_code` is `n`, and the session ends with `ended == "exit"`
     (Decision 8). Its ending runs no guest code: no `atexit` handler and no flush, which is
     what `os._exit` means in Python ("without calling cleanup handlers, flushing stdio
     buffers, etc.") and what it does in a Jupyter kernel, whose process it ends; the addendum,
     section 8, P9, shows the same through `run`.
   - So `turn` needs no finalize path; Python's shutdown has its own export, `shutdown`, which
     only the session's ending calls (Decisions 2 and 8).

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
     max_tool_calls=<default>, max_tool_request_bytes=<default>, idle_s=<default>,
     lifetime_s=<default>, shutdown_s=<default>)`**, plus the cap on open files that 068
     adds to `run`, under the name 068 gives it (below). Every argument is
     keyword-only. Each of `run`'s arguments means here what it means for `run`, with the scope
     the table below gives it. `idle_s` and `lifetime_s` default to two new `Defaults`
     fields (Decision 9), and `shutdown_s` to a third (Decision 8). There is no `argv` and no `stdin`: a turn's input is its code, and
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
     - **060's `max_tool_request_bytes=`** is per turn, set once on the session, like
       `max_tool_calls`: each turn's frame host gets the session's value (060, Decision 7;
       written in by 060's branch).
     - **068's cap on open files** (the owner's decision on question 92: a per-sandbox limit on
       files open at once, set by the embedder like the other limits, default 1,024, `EMFILE`
       past it, for `run` and sessions alike) is **per session**, set once at the opening and
       read from `defaults()` then, like `memory_bytes`. It counts the descriptors open in
       the session's store at once, whichever turn opened them, because a session's store
       keeps them across turns (Decision 11): a per-turn count would let each turn open the
       full allowance again and keep it. It holds through the session's ending too, so an
       `atexit` handler that opens files meets it (Decision 8). A turn that meets it gets
       `OSError` with `EMFILE` in the guest, as in `run`; the session goes on, and a file a
       later turn closes frees its slot. 068 owns the mechanism, the name and the messages;
       this specification only scopes it (written in here for 068, as 060's was; if 055 lands
       before 068, 068 carries this bullet and criterion 40).
     The builder adds each such argument to Decision 17's lines, and the review checks them
     against this rule.
   - **`session.run(code: str, *, fuel=<session's>, deadline_s=<session's>,
     output_bytes=<session's>, cancel=None) -> Completed`** runs one turn and returns how it
     ended.
   - **`await session.run_async(code, *, fuel=…, deadline_s=…, output_bytes=…, executor=None)
     -> Completed`**: the same from async code (Decision 12).
   - **`session.close() -> None`** ends the session, running its ending (Decision 8), and
     returns once the store is closed; it may be called any number of times.
     **`session.ended -> str | None`** is `None` while the session can run turns, and the reason
     it ended once it cannot (Decision 8). **`session.shutdown_outcome -> str | None`** is
     `None` until the ending has finished, then `"finished"`, `"stopped"` or `"skipped"`
     (Decision 8). `with Session(...) as s:` closes it on leaving the
     block, however the block ends.
   - **What is per session and what is per turn:**

     | argument | scope | why |
     |---|---|---|
     | `root`, `grants`, `mounts`, `env`, `host`, `tools`, `gate`, `snapshot`, `artifacts`, `cache_dir` | per session | WASI fixes preopens, env and imports per store; the guest lists tools once (`host.tools` at import) |
     | `memory_bytes` | per session | `set_limits` is a store setting, and linear memory never shrinks (the research, E2) |
     | 068's cap on open files | per session | the store keeps its descriptors across turns (Decision 11) |
     | `idle_s`, `lifetime_s`, `shutdown_s` | per session | they bound the session and its ending |
     | `fuel`, `deadline_s`, `output_bytes` | per turn; the session's value is each turn's default, and a turn may pass its own | each is re-armed before every turn (the addendum, findings 1, 2 and 4) |
     | `max_file_calls`, `max_tool_calls`, `max_tool_request_bytes` | per turn, set once on the session | each turn gets the full allowance; a per-turn override would only widen the surface |
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
   - checks every argument, exactly as `run` does and with the same messages, plus `idle_s`,
     `lifetime_s` (Decision 9) and `shutdown_s` (Decision 8), before any work: `TypeError` or
     `ValueError`, with no artifact lookup;
   - finds the artifact set, and refuses with `ArtifactsMissing` a set whose chosen binary does
     not export `turn` or `shutdown` (read from the compiled module's exports), naming each
     missing export and saying the set predates sessions; `tools=` keeps its `MANIFEST` check
     (spec 036);
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
   6. returns a `Completed` (Decision 14). If the session has ended by the time the turn
      returns, whether the turn ended it or something marked it while the turn ran (Decision
      8), the session's ending runs and the store is closed before `run` returns or raises.
      **The interpreter's state decides what the ending runs** (the re-review's F3): a turn
      whose export returned (its result is an exit status) **and whose `run` returns a
      `Completed`** left a sound interpreter, so its ending runs Python's shutdown on this
      thread, and `run` returns up to `shutdown_s` later, whatever marked the session: the
      turn's own `exit()` or `quit()`, the lifetime passing while it ran, a `close()` from
      another thread or from the turn's own thread, or the exit hook. A turn that trapped,
      called `os._exit` or was stopped left the interpreter unwound, and its ending runs no
      guest code. **A turn whose `run` raises runs no shutdown either, whatever the export
      returned** (the re-review's confirmation, F3's `"error"` row): a Ctrl-C that
      `_deferred_ctrl_c` noted and raises once the export has returned, a `BaseException` from
      a provider in step 5's write-back walk, or a lost call ends the session with `"error"`,
      and running more guest code, and more embedder calls, after the user's Ctrl-C or the
      embedder's own `BaseException` is what F4 rejects for the write-back.

   A turn's return value of −1, or any value outside −1 to 511, means the runner and the guest
   disagree. Since the C side owns the range (Decision 2), no guest code can produce it: it is a
   runner fault, the session ends with `"error"`, and `run` raises `RuntimeError("wasi_python
   lost track of a session")`, as `_drive` raises for a lost call.

8. **How a session ends, what its ending runs, and what `ended` says.** Revised for the
   owner's decision on question 92 (2026-10-18, evening), which `../decisions.md` records as:
   "at close and at expiry the session runs Python's shutdown (`atexit`, flushes) inside a
   small fuel and time budget, and is stopped if the budget runs out", following Jupyter. A session ends at the first of the causes
   below. `ended` is set to the cause once, under the session's state lock, before anything
   else (the review, F10), so a racing `run` sees `SessionEnded`, never a closed store. Then the
   session's **ending** runs, and when it has finished, everything the session held is released
   and `shutdown_outcome` says how the ending went.

   | cause | `ended` | the turn's result | the ending |
   |---|---|---|---|
   | `close()`, or leaving a `with` block, at rest | `"closed"` | no turn ran | Python's shutdown, on the caller's thread |
   | `close()` during a turn, which the close stops | `"closed"` | the turn returns `trapped == "cancelled"` (Decision 10) | no guest code: the stop unwound the interpreter |
   | `close()` during a turn, which returns normally before the stop takes effect | `"closed"` | the turn's own result | Python's shutdown, on the turn's thread, before `run` returns; `close()` waits for it |
   | the turn called `exit()` or `quit()` and returned | `"quit"` | the turn's status as `exit_code`, `trapped` is `None` | Python's shutdown, on the turn's thread, before `run` returns (Decision 4) |
   | the idle bound passed while at rest | `"idle"` | no turn ran; the next call raises `SessionEnded` | Python's shutdown, on a closer thread |
   | the lifetime passed while at rest | `"lifetime"` | no turn ran; the next call raises `SessionEnded` | Python's shutdown, on a closer thread |
   | the lifetime passed during a turn | `"lifetime"` | the turn's effective deadline was the lifetime's remainder (Decision 9): it returns `trapped == "deadline"`, or its result if it finished first | after `"deadline"`, no guest code; after a normal finish, Python's shutdown, on the turn's thread, before `run` returns |
   | the session was dropped unclosed (the collector), or the process exits with it at rest | `"closed"` | none | Python's shutdown, on a closer thread (Decision 13) |
   | the process exits during a turn | `"closed"` | as for `close()` during a turn | as for `close()` during a turn: none if the turn is stopped; Python's shutdown on the turn's thread if it returns normally first, and the exit hook waits for it (Decision 13) |
   | a turn called `os._exit` (`proc_exit`) | `"exit"` | `exit_code` is the code, `trapped` is `None` | no guest code (Decision 4) |
   | a turn trapped, or the runner stopped it after guest code ran | the turn's `trapped`: `"out of fuel"`, `"deadline"`, `"cancelled"`, `"out of file calls"`, or wasmtime's name for the trap (`"stack overflow"`, …) | `exit_code` is `None`, as in `run` | no guest code |
   | `run` raised after the guest started (Ctrl-C; a `BaseException` from the embedder's host, provider, tool or gate; a lost call) | `"error"` | none: `run` raises, as it does today | no guest code |

   - **When the ending runs Python's shutdown: one rule** (the re-review's F3). The ending runs
     Python's shutdown when all of these hold: at least one turn was called in the session; no
     turn is running, and the last turn's export returned (an exit status, not a trap, an exit
     or a stop), so the interpreter is sound; that turn's `run` returned a `Completed` (a turn
     whose `run` raised, the `"error"` row, runs none, even after a normal return from the
     export: Decision 7, step 6); `shutdown_s` is above 0; the ending's capped
     deadline (below) is still in the future; and this is not a process forked after the
     session was used (Decision 13). **The interpreter's state decides, never the cause or the
     moment it was marked**: a close, an idle bound, a lifetime, an `exit()`, a dropped session
     and the exit hook all run it, whether they marked the session at rest or during a turn
     that then returned normally. **Which thread runs it:** a turn's thread if a turn was
     running when the session was marked (after that turn returns, before `run` returns);
     otherwise `close()`'s caller for a `close()`, and a closer thread for an ending the
     runner starts itself (below). That is the owner's rule ("at close and
     at expiry"), and Jupyter's: a culled kernel is shut down by the same `shutdown_kernel`
     call, without `now`, as a closed one (the addendum, section 8, READ). Otherwise the
     ending runs no guest code, and `shutdown_outcome` is `"skipped"`. With no turn ever
     called there is nothing to shut down: no guest code has run since the opening, and the
     plain reactor's interpreter has not even started.
   - **The shutdown budget.** The ending runs inside two limits, both armed by the host before
     the export is called, so nothing the guest does extends them:
     - **Time: `shutdown_s`**, a new per-session argument whose default is a new field,
       `Defaults.session_shutdown_s = 5.0` seconds. It is a number of seconds, finite and at
       least 0: a bool, `None` or a non-number raises `TypeError`; a negative, NaN or infinite
       value raises `ValueError`, from `Session(...)` and from `Defaults(...)` alike. **It is
       capped by the lifetime** (the re-review's F2), as a turn's deadline is: the ending's
       deadline is the lesser of its start plus `shutdown_s` and the opening plus the lifetime
       plus `shutdown_s` (with `lifetime_s=None`, its start plus `shutdown_s`), both read from
       `_session_clock`. If that moment is not in the future when the ending starts (a reaper
       or a `close()` that came that late), the shutdown is skipped (`"skipped"`). So the
       lifetime's promise (Decision 9) holds to a tick whatever the reaper's or the embedder's
       latency. It is armed as `deadline_s` is, as an epoch deadline rounded up to a whole
       tick, and the ending's waits and tool calls stop at it as a turn's do at its deadline
       (specs 010 and 036). **0**
       is the embedder's way to skip the shutdown: the ending then runs no guest code, as
       Jupyter's `shutdown_kernel(now=True)` kills without a request. **`None` is refused**
       because the runner itself starts endings, on a closer thread at expiry and in its exit
       hook at process exit (Decision 13); an unbounded ending there would hold a thread, the
       session's memory and the host's exit for as long as the guest liked, which is what the
       bounds exist to prevent. Why 5 s: it is Jupyter's own figure, jupyter_client's
       `shutdown_wait_time` default ("Time to wait for a kernel to terminate before killing
       it"), configurable there as here; the shutdown measured at most about 0.31 G
       instructions on today's binaries (below). The time that takes is a benchmark fact the
       builder records in the landing notes, never a check.
     - **Fuel: the session's per-turn fuel.** In a metered session the ending gets the `fuel`
       the session was opened with, as a turn that passes none does; an unmetered session has
       no fuel, and the deadline alone bounds its ending. Why no fixed small share: the
       shutdown's cost moves thirtyfold with the binary and the heap (the addendum, section 8,
       P9 and P12: 28 M instructions on the plain reactor with nothing imported, about 303 M
       after importing pandas there, about 310 M on today's snapshot with the unfreeze of
       Decision 2), so any fixed figure small enough to call small would stop ordinary
       shutdowns, and any figure large enough would not be small. Why no new argument: the
       per-turn fuel is already the embedder's own statement of how much one call into this
       session may compute, and the ending is one more call. The README states the measured
       cost, so an embedder can size `fuel` to cover its ending. §4.15 holds: both limits have
       defaults (5 s; the session's fuel, or none in an unmetered session as for every turn),
       and the embedder sets both. **How "small" is read** (the re-review's N4): the owner asked
       for "a small fuel and time budget". The time is the small one, 5 s against a turn's 60;
       the fuel is the session's per-turn fuel, which may be large or, unmetered, none, for the
       reason above. "The owner's choices" says so, for the owner to see.
     - **Everything else is one turn's.** The session's `memory_bytes` holds. The ending gets
       a fresh frame host and fresh mount counters with one turn's `max_tool_calls`,
       `max_tool_request_bytes` and `max_file_calls`. 068's cap on open files holds, since the
       store is the session's (Decision 5). The ending's stdout and stderr go to two streams
       whose cap is 0, so nothing is kept: `close()` returns nothing and the reaper has no
       caller to give it to. Jupyter is alike here: a kernel's `atexit` handlers run after its
       IO loops have stopped, so nothing they print reaches the notebook (INFERRED from
       `kernelbase.py` and `kernelapp.py`, the addendum, section 8).
   - **How the ending runs, in order.**
     1. `ended` is set, as above. From here `run` and `run_async` raise `SessionEnded`.
     2. If the shutdown applies, the runner builds a call for it as for a turn (Decision 7,
        step 2) with the budget above, the deadline capped as above, and calls `shutdown()`. The session's stop condition
        "the session is closing" (Decision 10) does not apply to this call, which the session's
        own close would otherwise stop at once: the ending's stops are its deadline, its fuel
        and a Ctrl-C on the thread that runs it.
     3. The outcome is read by `_drive`'s rules. **`"finished"`**: the export returned 0 or
        120, or an `atexit` handler called `os._exit` (an exit trap; the guest ended its own
        shutdown, and the handlers after it do not run, P9). **`"stopped"`**: the fuel or the
        deadline ran out, any other trap, a Ctrl-C, a `BaseException` from the embedder's own
        code, or any other return value (a runner fault: only the export's refusals give −1,
        and this runner calls it only when they cannot apply). **A runner fault here is
        quiet** (the re-review's N3), where a turn's raises `RuntimeError`: an expiry's ending
        has no caller to raise to, and a `close()` that raised after the session was fully
        released would tell the embedder nothing it can act on; `"stopped"` records it, and the
        export's refusals are checked raw (criterion 34).
     4. The mounts' dirty buffers are handed to their providers through spec 034's walk, its
        deferred-Ctrl-C check included, on exactly the endings for which a turn would return a
        `Completed` (the re-review's F4): after `"finished"`, and after a `"stopped"` caused by
        the fuel, the deadline or a trap. After a Ctrl-C or a `BaseException` from the
        embedder's own code there is no walk, as a `run` that raises makes none (spec 034,
        Decision 8), and a Ctrl-C that arrives during the walk ends it as in `run`. The walk is
        bounded by the ending's file calls left and the staging bound. A write-back refused here
        is lost: no later turn offers it again, and no result records it.
     5. The store is closed, so no export of the instance is ever called again: **no guest code
        runs after a stopped ending**. HOME, the scratch folder and a private root are removed;
        the mount table and the walked folders are released; `sessions_open` falls by one;
        `shutdown_outcome` is set under the state lock; any `close()` waiting for the ending
        returns.
     When the shutdown does not apply, steps 2 to 4 are skipped and `shutdown_outcome` is
     `"skipped"`.
   - **Where it runs.** On a turn's thread if a turn was running when the session was marked
     (the rule above); otherwise on the thread that ends the session, `close()`'s caller. An
     ending the runner starts itself at rest (the idle bound, the lifetime at rest, a dropped
     session, and the exit hook's endings, Decision 13) runs on a **closer thread**: a daemon
     thread started for that one ending, so no session's ending, and no embedder code it
     calls, delays the reaper or another session. A session has at most one closer, and a
     closer lives for the ending's budget, plus any embedder call in flight when it runs out,
     plus the ending's mount write-backs (step 4).
   - **What the embedder's code sees during the ending** (the re-review's F7). The ending's
     host functions, providers, tools and gate run:
     - **in a `contextvars` context** that is the running thread's own when the ending runs on
       `close()`'s caller or on a turn's thread (as a turn's would be), and on a closer thread
       a copy of the context taken when the session was opened (`contextvars.copy_context()`
       in `Session(...)`), so a door host that reads a context variable sees the opener's
       value;
     - **with async tools on the session's private tool loop** (Decision 5, 053): the loop its
       synchronous turns used, or, for a session whose turns all came through `run_async`, one
       made for the ending. The private loop is closed after the ending, not when `ended` is
       set. A caller's loop is never used by an ending, since it may be stopped or closed by
       then; an async tool that cached an object bound to another loop fails there and is
       answered to the guest as a tool error, as 053 answers it;
     - **possibly after the embedder's own cleanup.** A dropped session's ending calls the
       embedder's functions after the embedder let go of the session. At process exit the
       runner's exit hook, registered with the first session, runs after every `atexit`
       handler the embedder registered later (last in, first out), so a provider or host
       function those handlers already closed may see calls; they fail as the embedder's code
       fails, the guest sees a fault, and the ending stays bounded by its deadline. An embedder
       that needs otherwise closes its sessions before its own cleanup. The README says so.
   - **`close()` while an ending runs** waits for it and returns once the store is closed, as
     it waits for a running turn (Decision 10); it does not shorten the ending, which is
     already bounded. Called on the ending's own thread (a raw `host=` function or a provider
     that the shutdown called), it returns at once.
   - **What bounds a hostile `atexit` handler.** Its compute is bounded by the fuel (metered)
     and the deadline; its waits (`time.sleep`, `poll_oneoff`) and tool calls by the deadline;
     its memory by `memory_bytes`; its output is dropped; its provider and tool calls by one
     turn's allowances; its open files by 068's cap. A handler that loops, sleeps or both is
     stopped (the addendum, section 8, P9, through `run`). A handler that registers another
     handler during the shutdown does not get it run; `sys.exit` in a handler is printed and
     ignored (P9). A handler blocked inside the embedder's own code (a raw `host=` function or
     a provider) is waited for, as in any turn, since the runner never kills embedder code; on
     a closer thread that holds only that thread. Once the ending is stopped the store is
     closed, so nothing of the guest runs again; a tool thread it started is abandoned under
     spec 036's rule and counted in the session's abandoned-thread quota (Decision 11).
   - **Why a turn that traps, exits or is stopped gets no shutdown.** A trap or `proc_exit`
     unwinds the guest without CPython's cleanup (Decision 2); the interpreter is not safe to
     enter, `shutdown` refuses it (`in_turn`), and the runner does not ask. This is where a
     session differs from Jupyter, and why. Jupyter's close first sends SIGINT, which Python
     turns into `KeyboardInterrupt` at a safe point, so a busy cell unwinds through Python and
     the kernel still exits normally. The guest has no signals, and a stop by the epoch
     callback is a trap, not an exception, so `close()` during a turn stops that turn hard and
     its ending runs nothing, unless the turn returned before the stop took effect (the rule
     above). Delivering a stop to the guest as a Python exception is left out
     (Decision 22). The README therefore keeps its advice: write and close files within a turn;
     the ending's flush covers a session closed or expired at rest, not one stopped mid-turn.
   - **A `MemoryError` does not end a session**, nor does an exception, a `SystemExit`, a
     truncated output, or a cancel that was set before the turn's guest code began (Decision
     7). The addendum (finding 3) shows the memory cap is met as a Python
     exception, with every later turn running.
   - **After it has ended**, `run` and `run_async` raise `SessionEnded`, whose `reason` is
     `ended`. `close()` returns at once if the ending has finished, and otherwise waits for it.
     `ended` is set once, by the first cause, under the session's state lock, before anything
     is closed, and never changes again (the review, F10). `shutdown_outcome` is set once, when
     the ending has finished, and never changes again; it is `None` until then, so an
     embedder that wants it after a `SessionEnded` from an expiry calls `close()` first.
   - **A trap ends the session in this version** (decision 21). Keeping the last good state
     after a trap needs a memory image taken at rest (the research's option 4): a later
     specification.
   - **The promised strings.** `ended`: `"closed"`, `"idle"`, `"lifetime"`, `"quit"`,
     `"exit"` and `"error"`, with `Completed.trapped`'s four; wasmtime's trap names are not promised (049,
     Decision 5). `shutdown_outcome`: `"finished"`, `"stopped"` and `"skipped"`.
   - **Why the outcome is a second attribute, not more values of `ended`.** `ended` must be
     set before the ending starts, so that a racing `run` is refused (F10), and the outcome is
     known only after the ending; one string set once cannot carry both. `ended` therefore
     says why the session ended, whichever way its ending went, and `shutdown_outcome` says
     whether Python's shutdown finished, was stopped by its budget, or did not run.

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
       has no turn running, handing each one's ending to a closer thread (Decision 8), so a
       slow ending never delays the next session's. Without it, an abandoned session would hold its memory (about
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
   - **The exact promise** (revised for the owner's decision on question 92). No **turn's**
     instruction runs later than the opening plus the lifetime, to within the deadline's own
     precision (one tick, `TICK_S`, plus the epoch check's slack, as for any deadline: spec
     010). The session's ending may then run Python's shutdown (Decision 8), whose deadline is
     the lesser of its start plus `shutdown_s` and the opening plus the lifetime plus
     `shutdown_s`, and which is skipped if that moment has passed when it starts (the
     re-review's F2). So no guest instruction of the session runs later than the opening plus
     the lifetime plus `shutdown_s` (5 s by default), to the same precision, however late the
     reaper wakes or the embedder calls `close()`; with `shutdown_s=0` the promise is the
     lifetime itself, exactly as before. That loosening by
     the budget is the owner's decision (`../decisions.md`: "at close and at expiry … inside a
     small fuel and time budget"), not this specification's, as §4.15 requires of a loosened limit. What can still
     happen after the last guest instruction is exactly what `run` allows after its own
     deadline, and no more: a raw `host=` function or a provider call already in flight is
     waited for (the runner never kills embedder code; a tool call is answered at the deadline
     and its thread abandoned, spec 036); and the mount write-backs of the last turn or of the
     ending, made after the guest has stopped, run as at `run`'s ending, bounded by the file
     calls left and the staging bound, not by the clock (spec 034, Decision 8). The session's
     store, folders and memory are released as soon as the ending finishes. The idle bound
     needs no cap: a running turn is never idle, and an ending after the idle bound is bounded
     by `shutdown_s`.
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
      lock, finds `busy` clear and the bound passed, sets `ended`, and only then starts the
      session's ending on a closer thread (Decision 8), so a racing `run` sees `SessionEnded`,
      never a closed store or a turn that overlaps the shutdown.
    - **Any thread.** Turns may run on whichever thread calls, one after another; the store may
      be closed from another thread (the addendum, finding 2). Each turn pushes its own call on
      its own thread's stack, so the shared host functions (spec 011) serve it.
    - **Sessions share nothing.** Each has its own store, folders and output keys, as
      concurrent `run` calls do (spec 011). Two sessions may run turns at the same time.
    - **`close()` during a turn stops it.** If a turn is running on another thread, `close()`
      sets `ended = "closed"`, stops the turn as `cancel` would (within `CANCEL_TICKS` ticks of
      compute, or at the end of a wait or a tool call, specs 015, 030 and 036), waits for the
      turn to return, and returns once the session is closed. The turn returns `trapped ==
      "cancelled"`, and the session's ending runs no guest code, since the stop unwound the
      interpreter (Decision 8: `shutdown_outcome == "skipped"`). If the turn returns normally
      before the stop takes effect, it returns its own result, and by Decision 8's one rule its
      ending runs Python's shutdown on the turn's thread before that `run` returns; `close()`
      waits for that ending too (the re-review's F3). An embedder's shutdown path can therefore
      end a session without knowing whether a turn is in flight. Called on the turn's own thread (a raw host function or a
      provider, which run there), `close()` marks the session and returns at once, since
      waiting there would wait on itself; the turn stops, or returns normally, and the session's
      ending runs as the turn returns, by the same rule. Called from a tool's thread, it waits as from any other thread: the turn stops
      waiting for that tool at once (spec 036's cancel), so the wait ends. Each turn's stop
      condition is therefore "its `cancel` is set, or the session is closing", and the
      session's store always has the epoch callback (Decision 6). That costs one Python call
      per `CANCEL_TICKS` ticks of compute and no fuel; the ticker runs during every turn.
      **`close()` blocks** until the turn returns, which includes a raw `host=` function or a
      provider call in flight, and then until the ending has finished: at rest, that is
      Python's shutdown, at most `shutdown_s` of guest code plus any embedder call it made;
      called from a coroutine, it blocks that event loop. Its docstring says so.
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
        The session's ending offers it once more when it runs Python's shutdown (Decision 8,
        step 4); an ending that runs no guest code does not. Either way the earlier turn's
        record already named the refusal.
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
        land during a later turn of the same session, during the ending, or after `close()`;
        056 stops a tool from
        starting after its call is answered, but one already running runs to its end (the
        review, F12). The README's abandoned-tools text says so.
    - **What a session holds on the host, for its whole life** (the review, F2). A session keeps
      its store, so it keeps every host file descriptor its guest opened, up to 068's cap,
      until it ends: up to its idle bound after the last turn, at most its lifetime, plus its
      ending's `shutdown_s`. One
      call's guest can take every descriptor the process has (EXECUTED by the review,
      `pb_fd_exhaust`: 1,014 files under a soft limit of 1,024, 122,870 under macOS's default,
      after which the host's own `open()` failed with `EMFILE`). For `run` that lasts one call
      (the 0.1.0a2 security review's F11; the README's *Not protected*); a session stretches it.
      It also holds up to `memory_bytes` of linear memory and up to `memory_bytes` of mount
      staging on the host. **The cap on open files is spec 068's**, which the owner placed
      before 0.1.0 (question 92, answered 2026-10-18: a per-sandbox limit on files open at
      once, set by the embedder like the other limits, default 1,024, `EMFILE` past it, for
      `run` and sessions alike; `../decisions.md`). In a session it is per session (Decision 5): a session holds
      at most the cap's descriptors at once, whichever turn opened them, for its whole life,
      the ending included. The cap guards the host process, not what the guest may use: the
      owner's principle is that a guest given a file system may use it "until time, fuel,
      memory, etc of that individual session run out". The README's *Sessions* and *Not
      protected* say all this (the cap, its default and its scope, from 068's text), and
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
      session ended and touches neither the store nor any folder: they are the parent's. It
      runs no guest code (`shutdown_outcome == "skipped"`): the guest is the parent's too. The
      child has no reaper, an empty registry and `sessions_open` of 0
      (`_after_fork_in_child`). The collector's finalizer (below) does nothing in a forked
      child.
    - **Exit.** An exit hook, registered with the first session (so it runs before `_release`
      frees the engines), stops the reaper and waits for its current step, then drains the
      collector's queue (the re-review's F8: a session collected just before exit sits there,
      in no list the hook walks, since the reaper holds sessions weakly) and ends each session
      on it as the reaper would, then ends every
      session at rest (`ended == "closed"`), each on its own closer thread, so their endings
      run Python's shutdown at once and side by side, as a Jupyter server shuts its kernels
      down when it stops, and waits for every ending in progress, closers the reaper started
      included. The host's exit therefore waits at most the largest `shutdown_s` among them,
      plus any embedder call in flight, plus the endings' mount write-backs, which spec 034
      bounds by calls and bytes, not time (F8). A session whose turn is still running is marked
      `"closed"`, which stops the turn (with `run_async`'s other guests, spec 015, for one on a
      worker); by Decision 8's one rule its ending runs no guest code if the turn is stopped,
      and Python's shutdown on the turn's thread if the turn returns normally first, and the
      hook waits for that ending as for the closers' (F3). The embedder's own `atexit`
      handlers registered after the first session have run by then (Decision 8, F7). Folders left by a killed process are swept by spec 016's sweep, as
      `run`'s are.
    - **The collector.** A session no one references is ended through a `weakref.finalize` on
      its state, which holds the store and the folders but not the `Session` object. The
      finalizer runs wherever the collector fires: on any thread, inside another session's host
      function, or on the reaper while it holds a lock. So it takes no lock and closes nothing:
      it only puts the state on a `queue.SimpleQueue`, whose `put` Python documents as safe
      from weakref callbacks and which takes no lock a collector could interrupt, unlike
      `threading.Event.set` or `Condition.notify` (the Confirmation, N2). The reaper waits on
      that queue (`SimpleQueue.get(timeout=…)`, the timeout being the wait `_reap` returns), so
      the same put wakes it; it then ends the session (`ended == "closed"`) and starts its
      ending on a closer thread, which runs Python's shutdown as for any session closed at
      rest (Decision 8; the review, F9; the `_outputs_lock` comment records this project meeting a finalizer inside
      a locked block before). The reaper holds sessions weakly. So a dropped
      session is closed soon after it is collected, or by its idle bound if a reference cycle
      delays the collector.

14. **Each turn returns a `Completed`.** No new result type. The fields mean what they mean for
    `run`, for the turn alone:
    - `exit_code`: the turn's exit status (Decision 2; for a turn that called `exit()` or
      `quit()`, the export's value less 256), or an `os._exit` code, or `None` when it
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
      from `defaults()` at the opening), `shutdown_s` among them; the methods `run`,
      `run_async` and `close`; the properties `ended` and `shutdown_outcome`; `__enter__` and
      `__exit__`. 049's render records a class's public methods; it must
      also record `Session.__init__`'s parameters and the two context-manager methods, rendered
      explicitly as it renders `Tool.__call__`. That is a change to `tests/harness/api.py`, a
      judge change made here.
    - **`SessionEnded`**, an exception whose base is `RuntimeError` (049, Decision 6: a new
      failure is a subclass of a promised type), with the attribute `reason: str`.
    - **`Defaults`** gains `session_idle_s: float | None = 900.0`, `session_lifetime_s: float
      | None = 3600.0` and `session_shutdown_s: float = 5.0`, last, with defaults (dataclass
      fields placed last with a default: an addition). The `defaults()` line records the three
      values. 068's field and `Session`'s argument for the cap on open files are 068's lines,
      or this specification's if it lands second (Decision 5's rule).
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
    `Session` shares with `run` is described by the same text in both. `close()`'s `Raises:`
    names `KeyboardInterrupt` and a `BaseException` raised by the embedder's own host,
    provider, tool or gate during the ending, each raised only after the session is fully
    closed (Decision 8: the ending is then `"stopped"`); its docstring says it blocks, and for
    how long (Decision 10). `shutdown_outcome`'s docstring names its three values. The README's generated
    reference shows them. `tests/public_api.txt` and the README block are regenerated with
    `tests/harness/api.py --write` on this branch, and the review checks the diff is exactly
    these lines.

18. **No command line.** `wasi-python run` stays one program, one result. A session needs a host
    process that holds the instance between turns; that process is the embedder's program. A
    command that kept an interpreter alive between invocations would be a shell, which §3 rules
    out, and would add a power `run()`'s command does not have.

19. **The artifact set.**
    - **Both binaries gain the exports `turn`, of type `(i32, i32) -> i32`, and `shutdown`,
      of type `() -> i32`.** Their imports do not change: WASI preview1 and `host::call`, as the judge checks today
      (`test_imports_are_wasi_and_the_door_only`).
    - **Step 80 is unchanged.** Wizer removes only the initialisers and keeps every other export
      (the addendum, finding 6: `run`, `host_alloc` today, and a `turn` export on a test module
      through the pinned `wasmtime wizer`); `shutdown` is one more ordinary export. Its strong
      reference to `gc.unfreeze` is taken by the first `turn` (Decision 2), so neither the
      snapshot's heap nor the plain reactor's `run` changes for it.
    - **The bytes grow**: two C functions and a larger frozen bootstrap, in both binaries. The
      judge's byte ratchet sees it, and the lane accepts it with `--accept-growth` and the
      reason. `run`'s fuel on the judge's jobs is not expected to move; any change the scoreboard
      shows is stated in the landing notes with its cause (the snapshot's heap layout after a
      larger bootstrap is the likely one), never accepted silently.
    - **`MANIFEST`'s recipe lines** for the two recipe files change hash, as any recipe change
      does. Rebuilds stay byte-identical across hosts (specs 012 and 040): the export adds no
      host-dependent input.
    - **The judge's export lists** (`tests/harness/artifacts.py`: `PLAIN_EXPORTS`,
      `SNAPSHOT_EXPORTS`) gain `turn` and `shutdown`, and the check reads their function
      types: a judge change.

20. **The README.** A new section, `### Sessions`, after `### The tool protocol` and before
    the API reference (049) and `## Safety`:
    - what a session is and is not (one guest across turns; not a shell; nothing is kept after
      it ends);
    - the per-session and per-turn table (Decision 5), the echo, `sys.exit()` keeping the
      session and `exit()` or `quit()` ending it through the shutdown (all as in Jupyter, with
      Decision 4's one difference: `exit(code)` stops the turn and reports its status), and how
      a session ends (Decision 8's table);
    - the bounds and their defaults, the lifetime's cap on a turn's deadline and its exact
      promise, the shutdown's `shutdown_s` included (Decision 9), and the reaper;
    - **closing runs Python's shutdown, as Jupyter does** (Decision 8), in about these words:
      "When a session is closed, or its idle bound or lifetime passes while it is at rest, it
      runs Python's normal shutdown, as a Jupyter kernel does when it is shut down or culled:
      `atexit` handlers run, then the interpreter is finalized, which flushes the files it
      closes. The shutdown has `shutdown_s` seconds (5 by default; 0 skips it) and, in a
      metered session, the session's `fuel`; if either runs out the session is simply stopped.
      `shutdown_outcome` says which: `"finished"`, `"stopped"`, or `"skipped"` when no
      shutdown ran. `exit()` and `quit()` in a turn end the session the same way once the turn
      returns. Nothing the shutdown prints is kept. A session that ends by a trap, `os._exit`,
      or a stop (a `close()` that stops a running turn included) runs no shutdown, because its
      interpreter was stopped mid-turn. So write and close files within a turn: the shutdown
      is a courtesy for a session closed at rest, not a guarantee. A session's shutdown may
      call your host functions, providers and tools after your own cleanup: when you drop a
      session without closing it, and at process exit, where it runs after the `atexit`
      handlers you registered later; close sessions first if that matters." With the measured
      fuel of a shutdown on each binary (Decision 8, re-measured on the built set), so a
      metered session's `fuel` can cover it, and the note that a file held only in a reference
      cycle may not be flushed, as in CPython (the re-review's N5);
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
    contract (Decision 2), for an embedder that keeps an instance across turns, including that
    argv after `argv[0]` holds only absolute, read-only import-path folders. The constitution's
    §2.4 ("calling one export") still describes the minimum to run a program; a session is
    optional and §3 admits it. No constitution change is needed. The CHANGELOG's unreleased
    section gains, under Added: `Session` (with `shutdown_s` and `shutdown_outcome`),
    `SessionEnded`, the three `Defaults` fields (`session_idle_s`, `session_lifetime_s`,
    `session_shutdown_s`), `stats()["sessions_open"]`, and the `turn` and `shutdown` exports,
    with one line: "a session's close and expiry, and `exit()` or `quit()` in a turn, run
    Python's shutdown (`atexit`, flushes) within `shutdown_s` seconds and the session's fuel,
    as a Jupyter kernel's do; past that budget the session is stopped; `sys.exit()` keeps the
    session." The fourth paragraph of "Any other embedder does the same
    three things" also gives `shutdown`'s contract (Decision 2): call it once, at rest, after a
    turn that returned normally, under a deadline, and never call the instance again; and
    `turn`'s values 256 to 511: the status plus 256, when the turn called `exit()` or
    `quit()`, after which an embedder that follows Jupyter calls `shutdown`.

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
    - **A cap on open host descriptors per store**, for `run` and sessions alike: spec 068,
      before 0.1.0, by the owner's answer to question 92; Decision 5 scopes it per session.
      Not left out any more, but not built here.
    - **Delivering a stop to the guest as a Python exception** (as Jupyter's SIGINT becomes
      `KeyboardInterrupt`), so that a turn stopped by `close()` could unwind through Python
      and still run the shutdown: a later specification, if ever. The guest has no signals,
      and the epoch stop is a trap (Decision 8).
    - **Returning the shutdown's output** to the embedder: not in this version; `close()`
      returns nothing and an expiry has no caller (Decision 8).
    - **Jupyter's `exit(keep_kernel=True)`**, and Jupyter's rule that the rest of a cell runs
      after `exit()`: not followed; the session keeps Python's `exit(code)` within the turn
      (Decision 4).

## Intent

An embedder opens a session, sends an agent's code one turn at a time, and gets one result per
turn, each costing a fraction of a fresh run, with variables, functions and data kept between
them. Every turn has its own fuel, deadline, output cap, cancel, file-call and tool-call
allowance; the session has one memory cap, one cap on open files (068), an idle bound and a
lifetime, all with defaults, and no turn runs past its lifetime. A trap, an `os._exit`, an
`exit()` or `quit()`, a bound or `close()` ends the session; an exception, a `sys.exit()` or a
full heap does not, and
nothing a guest does makes `session.run` raise. A session closed or expired at rest runs
Python's shutdown, `atexit` and flushes, as a Jupyter kernel does, inside a small budget of
time and fuel capped by its lifetime, and is simply stopped if that runs out; so does one whose
turn called `exit()` or returned normally after being closed; a session stopped mid-turn runs
none.
Either way everything it held is freed when its ending finishes. `run()` is exactly as it was.

## Design

```
recipes/reactor_main.c            export "turn"(ptr, len) -> i32; the `turned` and `in_turn`
                                  flags; run() refuses after a turn; turn() refuses after run(),
                                  during or after an unfinished turn, after shutdown(), and a
                                  negative length; a strong reference to the bootstrap's turn;
                                  the 0..255 clamp; copy, then free. export "shutdown"() -> i32;
                                  the `shut` flag; its refusals; a strong reference to
                                  gc.unfreeze; gc.unfreeze() then Py_FinalizeEx()
recipes/reactor_bootstrap.py      _reactor.turn(source, environ): first-turn setup (env, the
                                  import path from argv, exit/quit rebound, reseed), <turn N>,
                                  linecache, the echo, the interactive interpreter's reporting,
                                  SystemExit's status, the flush
src/wasi_python/runner.py         Session (open, run, run_async, close, ended,
                                  shutdown_outcome, context manager); SessionEnded;
                                  Defaults.session_idle_s, session_lifetime_s and
                                  session_shutdown_s; _session_clock; the reaper (_reap, its
                                  thread, its injected wait); the ending (the shutdown's call
                                  and budget, closer threads, write-backs, release); the state
                                  lock; per-turn streams behind the output keys; the per-turn
                                  _Call on the existing _drive rules; stats()'s sessions_open;
                                  the fork and exit hooks extended
src/wasi_python/mounts.py         _Files: per-turn counters reset; owed buffers dropped once
                                  written; in a session, a refused write-back stays dirty
src/wasi_python/tools.py          _Bounded: an abandoned-thread count that a session shares
                                  across its turns; with 053, one tool loop per session
src/wasi_python/__init__.py       Session, SessionEnded in __all__
tests/harness/guest.py            turns(): the judge's own driver for `turn` and `shutdown` on
                                  one instance
tests/unit/test_guest.py          turns() checked against a stand-in module that exports `turn`
tests/unit/test_runner_sessions.py    refusals, the bounds and the reaper with fakes, the state lock
tests/checks/test_v1_4_embedding.py   the export driven raw, and sessions end to end (built set)
tests/harness/artifacts.py        PLAIN_EXPORTS, SNAPSHOT_EXPORTS gain turn and shutdown; their
                                  types checked
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

In: the above, with the revision's part: the `shutdown` export, the session's ending (Python's
shutdown at close and at expiry inside `shutdown_s` and the session's fuel, stopped past
them), `Session.shutdown_outcome`, `Defaults.session_shutdown_s`, and the scoping of 068's cap
on open files to a session. Out: Decision 22's list; a command line (Decision 18); any change
to `run`, `run_async` or `Completed`; any new import or a second custom import (§4.4); any
change to step 80, the zip or the pins; 068's cap itself (its mechanism, names and messages
are 068's); running a shutdown after a turn that trapped, exited or was stopped (Decision 8).

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
   and prints `41`. A fifth with `exit(4)` returns 260 (256 plus 4) and a sixth with
   `quit()` on another instance 256; on a third instance, a turn that sets
   `_reactor._exit_code = lambda e: 300` and raises `SystemExit` returns 44, not 300 (no quit
   bit from a guest-made status), and one whose `_exit_code` returns `2**100 + 4` returns 4,
   with nothing on stderr from the C side (C1: no overflow path, no exception left pending).
   Stand-ins: a `turn` that finalizes (the fourth returns non-zero or traps); a C side that
   reads bit 8 of the raw status (the 300 case returns 300); a C side that masks with
   `PyLong_AsLong` (the `2**100 + 4` case returns 1 or leaves an `OverflowError` pending).
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
   and `Defaults(session_idle_s=0)` raises `ValueError`. `shutdown_s` of `None`, `True` and
   `"5"` raises `TypeError`, and of `-1`, `float("nan")` and `float("inf")` `ValueError`, from
   `Session(...)` with zero artifact lookups and from `Defaults(session_shutdown_s=…)`;
   `shutdown_s=0` is accepted; `Defaults().session_shutdown_s == 5.0`.
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
   `run` as today. A second stand-in that exports `turn` but not `shutdown` is refused the same
   way, its message naming `shutdown` and not `turn`.
7. `test_the_reaper_ends_what_is_due` (fakes): sessions registered with fake due times;
   `_reap(now)` ends exactly those due at `now` with the right reason (`"idle"` or
   `"lifetime"`), skips one whose `busy` flag is set, and returns the wait until the next due
   one; with none open it returns "no wait". A reaper loop driven by an injected clock and wait,
   for a fixed number of rounds, ends sessions in due order. Each due session's ending is handed
   to the injected closer starter, one call per session, after its `ended` is set; `_reap`
   itself runs no ending. Stand-ins: a reaper that ends a busy session; a reaper that runs the
   ending itself (the starter is never called).
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
    `ended is None` throughout. (`exit()` and `quit()` end the session: criterion 41.)
    Stand-in: a runner that ends the session on `SystemExit`.
12. `test_os_exit_and_a_trap_end_the_session`: (a) `os._exit(4)` returns `exit_code == 4`,
    `trapped is None`; `ended == "exit"`; the next `run` raises `SessionEnded` with `reason ==
    "exit"`; `sessions_open` is back to its value before the opening. (b) A metered session
    (`fuel=10**9`): `while True: pass` returns `trapped == "out of fuel"`, `exit_code is None`;
    `ended == "out of fuel"`. (c) `deadline_s=0.5` on one turn of an unmetered session with
    `while True: pass`: `trapped == "deadline"`, `ended == "deadline"`. (d) `cancel` set by a tool
    that runs inside the turn: `trapped == "cancelled"`, `ended == "cancelled"`. In each,
    `sessions_open` returns to its value before, and `shutdown_outcome == "skipped"`. (e) A `cancel` already set when `session.run`
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
21. `test_close_ends_and_cleans_up`: a `root=True` session with `shutdown_s=60` that ran one
    turn; `close()` sets
    `ended == "closed"` and `shutdown_outcome == "finished"`; a session closed before any turn
    has `shutdown_outcome == "skipped"`;
    the runner's held private-folder names (`runner._held`) shrink by the session's two (root
    and scratch); `close()` again does nothing; `run` raises `SessionEnded("closed")`; a `with`
    block that raises inside closes the session too. A `close()` from another thread while a tool
    blocks inside a turn returns only after the turn has returned with `trapped == "cancelled"`
    (the check orders this by events), `ended == "closed"`, and `shutdown_outcome ==
    "skipped"`. Stand-in: a `close()` that returns before the turn has returned (the check sees
    the order reversed).
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
    folder; with `shutdown_s=60`, a turn in that session registered an `atexit` handler that
    writes a file to a
    writable grant of the parent's temporary folder, and after the child exits the file holds
    the handler's bytes (the exit hook ran the ending). (c) A session dropped without
    `close()` (`shutdown_s=60`), whose turn registered the same handler: after `gc.collect()`
    and one reaper step
    (`_reap`, driven by the check) and a join of its closer (through a test hook),
    `sessions_open` is back to its value before, the handler's file holds its bytes, and the
    finalizer itself took no lock (it is called while the check holds the registry lock, and
    returns). (d) The re-review's F8: in a child, a session (`shutdown_s=60`) whose turn
    registered the same handler is dropped and collected after the reaper was stopped (a test
    hook stops it first), so its state is on the collector's queue at exit; after the child
    exits the handler's file holds its bytes. Stand-ins: no finalizer (the count stays up); an
    exit hook that closes without an ending (the file is absent); an exit hook that does not
    drain the queue (in (d) the file is absent).
25. `test_a_session_on_the_plain_reactor`: `Session(snapshot=False)` runs `print(1)` then
    `print(2)`: `1\n` then `2\n`, both `exit_code == 0`.

**The artifact set and the whole:**
26. `test_plain_reactor_exports` and `test_snapshot_exports` require `turn`, of type `(i32, i32)
    -> i32`, and `shutdown`, of type `() -> i32`, in both binaries;
    `test_imports_are_wasi_and_the_door_only` passes unchanged.
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
    turn 6 `print(2)` returns 0. Turn 7 registers an `atexit` handler that prints, and turn 8
    makes `_reactor._exit_code` itself raise `SystemExit(9)` and then raises `SystemExit`:
    `exit_code == 1`, `ended is None`, and no output from the handler (the Confirmation, N1);
    the handler runs only at the session's ending, whose output is not kept (Decision 8).
    No call raises, and `ended is None` throughout. Stand-ins: today's text (a turn returning −1
    or 300, and `session.run` raises `RuntimeError`); a failed call printed with `PyErr_Print`
    (turn 8 exits 9 and the handler prints).
33. `test_close_on_the_turns_own_thread`: a session with a raw `host=` whose function calls
    `session.close()` and returns `b""`: `close()` returns at once (no deadlock; the check's
    120 s fail-safe), the turn returns `trapped == "cancelled"`, and `ended == "closed"`.
    Stand-in: a `close()` that always waits (the child hits the fail-safe).

**Added by the revision for the owner's decision of 2026-10-18** (close as Jupyter does; end
to end on the built set, both binaries, unless named). A file's bytes are read after `close()`
returns, which waits for the ending (Decision 10). A short `shutdown_s` only chooses the
outcome; the check asserts the outcome, never a duration, under the existing 120 s fail-safe.
**Every check that expects `"finished"` passes `shutdown_s=60`** (the re-review's F6), so the
outcome is decided by the guest's work, never by the machine's speed; criterion 4 checks the
default's value.
34. `test_the_shutdown_export_raw` (the judge's driver, `turns()`, in
    `tests/checks/test_v1_4_embedding.py`): turn 1 registers an `atexit` handler that prints
    `bye`, opens a file on a writable preopen, writes 100 bytes without flushing, and defines a
    function in `__main__` (the case of the addendum's P10b); `shutdown()` returns 0, stdout
    ends `bye\n`, and the file holds 100 bytes. Then `turn` returns −1, `run` returns 70 and
    `shutdown` returns −1, none running Python. Each refusal returns −1 with stdout and stderr
    empty: `shutdown` on a fresh instance; on an instance that ran `run`; after a turn that ran
    out of fuel; from the door during a turn. From the door during the shutdown (a handler
    calls the door, whose host function calls `shutdown`), the inner call returns −1 and the
    outer one goes on to return 0. Stand-ins: an export without `shut` (the inner call
    finalizes again or traps); an export without the unfreeze (on the snapshot the file holds
    0 bytes).
35. `test_close_runs_python_shutdown`: a session (`shutdown_s=60`) with a writable grant at
    `/w`; turn 1 registers
    a handler that writes `ran` to `/w/atexit.txt`; turn 2 runs `f = open('/w/buffered.txt',
    'w'); f.write('x' * 100)` and `def g(): pass`. `close()` returns with `ended == "closed"`
    and `shutdown_outcome == "finished"`; `atexit.txt` holds `ran` and `buffered.txt` 100
    bytes. With a writable mount in place of the grant, the provider has received the 100
    bytes when `close()` returns (Decision 8, step 4). With `shutdown_s=0`, neither file is
    written and `shutdown_outcome == "skipped"`. Stand-ins: closing as a stop (no
    `atexit.txt`); a shutdown without the unfreeze (on the snapshot, `buffered.txt` holds 0
    bytes); an ending without the write-back (the provider receives nothing).
36. `test_expiry_runs_python_shutdown` (the injected clock of criteria 13 and 14;
    `shutdown_s=60`): the same handler in turn 1. Past the idle bound, `_reap(now)` ends the session; `close()` then waits
    for its closer; `ended == "idle"`, `shutdown_outcome == "finished"`, and the file holds
    `ran`. The same at rest past the lifetime gives `"lifetime"`. A turn whose tool moves the
    fake clock past the lifetime and then returns normally: `run` returns its result, and by
    then the file holds `ran`, `ended == "lifetime"`, `shutdown_outcome == "finished"`. A turn
    the lifetime's cap stops (`trapped == "deadline"`): no file, `shutdown_outcome ==
    "skipped"`. **The cap on the ending's deadline** (the re-review's F2; `shutdown_s=5`,
    lifetime 3,600 s): a reaper step at fake t = 3,602 arms the ending's epoch deadline at
    `ceil(3 / TICK_S)` ticks (read through criterion 14's test hook on the arming), and the
    file is written; a reaper step at t = 3,605, and a `close()` at t = 3,610 on a session the
    reaper never reached, each skip the shutdown: no file, `shutdown_outcome == "skipped"`, and
    the export-call hook records no `shutdown`. Stand-ins: a reaper whose endings run no
    shutdown (no file); an ending armed from its start (at t = 3,602 the armed ticks are
    `ceil(5 / TICK_S)`, and at t = 3,610 the file is written).
37. `test_a_hostile_atexit_is_stopped`: each session's turn registers one handler, and each
    `close()` returns, with `ended == "closed"`, `sessions_open` back to its value before and
    the session's folders gone from `runner._held`. (a) A metered session (`fuel=10**9`,
    `shutdown_s=600`, so the 120 s fail-safe would come first if fuel did not bound the
    ending; the re-review's F5) whose handler loops forever (`[0 for _ in iter(int, 1)]`):
    `shutdown_outcome == "stopped"`. (a2) **The figure is the session's fuel**: a handler whose
    cost the builder calibrates to about 10^9 instructions (recorded in the landing notes),
    with `shutdown_s=600`, finishes in a session opened with `fuel=4 * 10**9`
    (`"finished"`), and is `"stopped"` in one opened with `fuel=10**9`. (b)
    An unmetered session with `shutdown_s=0.5` whose handler runs `while True: pass`:
    `"stopped"`. (c) The same with a handler that calls `time.sleep(10**6)`: `"stopped"`. (d)
    A handler that registers another handler and then calls `sys.exit(7)`: `"finished"`. (e) A
    handler that calls `os._exit(5)`, registered after one that writes a file (so it runs
    first): `"finished"`, and no file. Stand-ins: an ending armed with no deadline (in (b) the
    child hits the fail-safe); an ending armed with no fuel (in (a) the child hits the
    fail-safe); an ending given a fixed fuel other than the session's, such as 10^8 (in (a2)
    the first session is `"stopped"`).
38. `test_no_guest_code_after_a_stopped_ending`: a session with a raw `host=` that counts its
    calls, `shutdown_s=0.5`, and a handler that calls the door in an endless loop. `close()`
    returns with `shutdown_outcome == "stopped"`; the count read then equals the count read
    after a second session has run a whole turn; a test hook on the runner's calls into the
    instance's exports records exactly one `shutdown` and nothing after it. The same with a
    tool in place of the raw host function. **No write-back after a Ctrl-C or an embedder
    `BaseException`** (the re-review's F4): a session with a writable mount and a raw `host=`;
    turn 1 leaves a mount file open with unflushed bytes and registers a handler that flushes
    it and then calls the door, whose host function raises `KeyboardInterrupt`; `close()`
    raises `KeyboardInterrupt` after `sessions_open` has fallen, `shutdown_outcome ==
    "stopped"`, and the provider has received no write. Stand-ins: a runner that calls an
    export of the instance again after a stopped ending (the hook records a second call); an
    ending that writes back on every outcome (the provider receives the bytes).
39. `test_no_shutdown_after_a_trap_or_exit`: turn 1 registers a handler that writes a file;
    then (a) `os._exit(4)`; (b) in a metered session, `while True: pass` (`"out of fuel"`); (c)
    `close()` from another thread while a tool blocks inside a turn. In each, no file is
    written, `shutdown_outcome == "skipped"`, and the export-call hook records no `shutdown`.
    Stand-in: a runner that calls `shutdown` after a trap (the hook records the call, and the
    export's −1 makes the outcome `"stopped"`).
40. `test_the_cap_on_open_files_in_a_session` (068 is expected to land first; if it has not,
    this criterion and Decision 5's 068 bullet move to 068): with 068's cap set to 8 on the
    session, turn 1 opens files on a writable grant and keeps them until `OSError` with
    `EMFILE`, and records how many it opened; turn 2 opens one more and gets `EMFILE`; turn 3
    closes one and opens one, which succeeds; `ended is None` throughout. A handler that opens
    files until `EMFILE` lets the ending finish (`"finished"`). Stand-in: a cap counted per
    turn (turn 2's open succeeds). (Its ending passes `shutdown_s=60`.)
41. `test_exit_and_quit_end_the_session_through_the_shutdown` (the re-review's F1, the lane's
    ruling): a session with `shutdown_s=60` and a writable grant; turn 1 registers a handler
    that writes a file; turn 2 runs `print("a"); exit(5); print("b")`: it returns
    `exit_code == 5`, `trapped is None`, stdout `a\n` only; when `run` returns the file holds
    the handler's bytes, `ended == "quit"` and `shutdown_outcome == "finished"`; the next
    `run` raises `SessionEnded` with `reason == "quit"`. The same with `quit()` gives
    `exit_code == 0`. A turn that calls `exit(3)` inside `try`, catches the `SystemExit`,
    and then prints `repr(sys.stdin.read())` prints `''` (stdin left open, the review's F13),
    returns 0, and still ends the session with `"quit"` (the flag stays set, as `exit_now`
    does). In
    the same session, earlier turns' `sys.exit(3)` and `raise SystemExit(3)` kept it open
    (criterion 11). Stand-ins: a runner that keeps the session after `exit()` (`ended is
    None`); a flag cleared by catching `SystemExit` (the last case keeps the session); a
    rebound `exit` that closes stdin (`ValueError`).
42. `test_a_turn_that_returns_after_close_runs_the_shutdown` (the re-review's F3;
    `shutdown_s=60`): turn 1 registers a handler that writes a file. Turn 2 runs `print(1)`; a
    test hook in the runner, called after the export has returned and before the turn's
    ending is decided, lets the check call `close()` from another thread and waits until the
    session is marked. Turn 2 returns `exit_code == 0` with `1\n`; by then the file holds the
    handler's bytes, `ended == "closed"`, `shutdown_outcome == "finished"`, the export-call
    hook records `shutdown` on the turn's thread, and the other thread's `close()` returned
    only after it. **A turn whose `run` raises** (the re-review's confirmation, F3's
    `"error"` row): in a child on its main thread, a pure-compute turn (`sum(range(10**6))`,
    no host call) during which a test hook notes a Ctrl-C through `_deferred_ctrl_c`; the
    export returns normally, `run` raises `KeyboardInterrupt`, `ended == "error"`,
    `shutdown_outcome == "skipped"`, no file, and the export-call hook records no
    `shutdown`. Stand-ins: an ending decided by the moment the session was marked (no
    file, `"skipped"`); an ending run by the waiting `close()`'s thread (the hook records the
    other thread); an ending decided by the export's return alone (the Ctrl-C case records a
    `shutdown` and writes the file).

## The owner's choices

None open here. The owner's decisions 18 to 22 and 49 are carried as written. Question 92
put to the owner three choices that were the agent's where those decisions were silent, and
one placement. **The owner answered it on 2026-10-18, evening** (`../decisions.md`, "The
owner's answers of 2026-10-18, evening", the bullet for 92): keep the choices that follow
precedent, "especially that of Jupyter".

- `SystemExit` keeps the session (Decision 4): **kept for `sys.exit()` and `raise
  SystemExit`**, as in Jupyter. The re-review (F1) found that Jupyter's `exit()` and `quit()`
  end the kernel through Python's normal exit; the landing lane ruled to follow Jupyter there
  too, so `exit()` and `quit()` now end the session, through the shutdown, after the turn
  (`ended == "quit"`).
- The final expression is echoed (Decision 3): **kept**, as in Jupyter.
- Closing was a stop with no shutdown: **changed**. Jupyter lets Python exit normally, so at
  close and at expiry the session now runs Python's shutdown inside a small fuel and time
  budget and is stopped if the budget runs out (Decisions 2, 8 and 9; the section "Revised for
  the owner's decision of 2026-10-18", below).
- The cap on open host descriptors: **before 0.1.0**, as spec 068, default 1,024, for `run`
  and sessions alike (Decisions 5, 11 and 22).
- **How "a small fuel and time budget" was read** (the re-review's N4), for the owner to see:
  the time is the small part, `shutdown_s` = 5 s by default (Jupyter's figure), capped by the
  lifetime; the fuel is the session's own per-turn fuel, which may be large, or none in an
  unmetered session, because the shutdown's cost runs from 28 M to about 310 M instructions
  with the binary and the heap, so a small fixed figure would stop ordinary shutdowns
  (Decision 8).

The lifetime was already no longer among the choices: following the landing lane's ruling on
the review's F4, a turn's deadline is capped at the lifetime left, so the owner's one hour
holds as a bound on every turn (Decision 9); the shutdown the owner chose may follow it by at
most `shutdown_s`.

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
  per-store descriptor cap was recorded as a later specification and its place relative to
  0.1.0 put to the owner (question 92). **Answered** (2026-10-18, evening): before 0.1.0, as
  spec 068, default 1,024; Decision 5 scopes it per session and criterion 40 checks it.
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
  `Quitter` subclass that does not close stdin (Decision 3). Check: criterion 11, and since
  the re-review's F1 (where `exit()` ends the session), criterion 41.
- **F14 (low), stand-ins.** Named for criteria 3, 11, 12, 13, 14, 17, 18, 21 and 24(c); the
  added criteria 30 to 33 each name one, and 33 covers `close()` on the turn's own thread.
- **F15 (low), the fuel band.** The builder measures the spread through the real export, over
  at least five sessions each on macOS and Linux, before the band is fixed; a spread above 10
  is a finding (Decision 16). The review's note on 049's `_MAX_ABANDONED` is taken (Decision
  11).
- **Question 92, the owner's.** Answered on the evening of 2026-10-18 (`../decisions.md`):
  `SystemExit` and the echo stand; closing follows Jupyter and runs Python's shutdown inside a
  small budget; the cap on open files comes before 0.1.0 as spec 068. Written in by the
  revision (the section "Revised for the owner's decision of 2026-10-18", below, and "The
  owner's choices", above); the revision awaits a short re-review.

## The Confirmation's notes

The reviewer confirmed this specification at `c25713c` for build once N1 was written in, with
two further low notes (the Confirmation, appended to the review). All three are written in.

- **N1 (needed), a failed call must not go through `PyErr_Print`.** Its `SystemExit` handling
  finalizes and exits, which a guest can reach by making a bootstrap helper raise `SystemExit`
  (EXECUTED by the reviewer, `pe_pyerr_print_exits`). Decision 2 now fetches and displays the
  exception itself and returns 1; criterion 32 gains turns 7 and 8 and the stand-in.
- **N2 (low), a lock-free wake.** The finalizer puts the state on a `queue.SimpleQueue`, safe
  from weakref callbacks, and the reaper waits on that queue (Decision 13).
- **N3 (low), what argv after `argv[0]` means.** Absolute, read-only import-path folders only;
  the guest skips anything else (Decisions 2 and 3, and Decision 20's README paragraph).

## Revised for the owner's decision of 2026-10-18 (92)

The owner answered question 92 on the evening of 2026-10-18 (`../decisions.md`, "The owner's
answers of 2026-10-18, evening", the bullet for 92). Two of the agent's three choices stand,
because they follow Jupyter: `sys.exit()` keeps the session, and a turn's last expression is
echoed. The re-review then found that Jupyter's `exit()` and `quit()` do end a kernel, and the
landing lane ruled to follow Jupyter there as well (its F1). The third did not follow Jupyter, and changes: closing was a stop that ran no guest
code; now, at close and at expiry, the session runs Python's shutdown inside a small fuel and
time budget, and is stopped if the budget runs out. The placement asked about is answered too:
the cap on open files comes before 0.1.0, as spec 068, and applies to sessions. This revision
writes those answers in. It was made before the build, against the text the review confirmed.

**What changed, and why.**

- **`exit()` and `quit()` end the session** (Decision 4; the re-review's F1, the lane's
  ruling). They set a quit flag, as ipykernel's exiter sets `exit_now`, and raise
  `SystemExit(code)` as Python's do; the turn returns its status, and the session ends with
  `ended == "quit"`, its ending running Python's shutdown on the turn's thread. `turn`
  carries the flag back as 256 plus the status (Decision 2). `sys.exit()` still keeps the
  session.

- **A third export, `shutdown() -> i32`** (Decision 2). Closing now runs guest code, so the
  guest needs an entry for it. It runs `gc.unfreeze()` and then `Py_FinalizeEx()`, once, in an
  instance whose last turn returned normally, and refuses (−1, no Python) otherwise. It is a
  new export rather than a mode of `turn` (which promises never to finalize, N1) or of `run`
  (once per instance, argv-driven). The unfreeze is there because the addendum's new section 8
  found that on the snapshot, whose initialiser freezes the heap, a file left open beside any
  function defined in `__main__` loses its buffered bytes at `Py_FinalizeEx`; undoing the
  freeze gives the snapshot CPython's own exit behaviour, the plain reactor's.
- **The ending** (Decision 8, rewritten). `ended` still says why the session ended, set once
  before anything else (F10 unchanged). A new property, `shutdown_outcome`, says how the
  ending went: `"finished"`, `"stopped"` (its budget ran out, or it trapped) or `"skipped"`
  (no guest code ran). Python's shutdown runs when the session is at rest with a sound
  interpreter: at `close()`, past the idle bound, at the lifetime reached at rest or at the end
  of a turn that finished after it, for a dropped session, and at process exit. It does not run
  after a turn that trapped, exited or was stopped, `close()` during a turn included, because
  that interpreter was unwound mid-call; Jupyter interrupts a busy kernel with SIGINT, which
  Python can unwind, and the guest has no such signal. `os._exit` still ends the session at
  once, with no shutdown, as in Python and in a Jupyter kernel (Decision 4).
- **The budget** (Decision 8). Time is a new named limit, `shutdown_s`, default
  `Defaults.session_shutdown_s = 5.0`, set per session by the embedder, `0` to skip the
  shutdown, `None` refused because the runner itself starts endings and must bound them. 5 s
  is jupyter_client's `shutdown_wait_time` default. Fuel is the session's own per-turn fuel in
  a metered session, with no new argument: the shutdown costs 28 M to about 310 M instructions
  on today's binaries (section 8), so a small fixed share would stop ordinary shutdowns. The
  memory cap, one turn's file and tool allowances and 068's cap also hold; the ending's output
  is dropped.
- **Where endings run** (Decisions 8, 9, 10 and 13). On the closing thread for `close()`; on a
  closer thread of its own for every ending the runner starts (the reaper's, the collector's,
  the exit hook's), so one slow ending never holds another session or the reaper. The exit
  hook runs at-rest sessions' endings side by side and waits for them.
- **The lifetime's promise** (Decision 9). No turn runs past the lifetime, as before; the
  shutdown may follow for at most `shutdown_s`, its deadline capped at the opening plus the
  lifetime plus `shutdown_s` (the re-review's F2). That loosening is the owner's decision, as
  §4.15 requires; `shutdown_s=0` restores the old promise exactly.
- **Mounts at the ending** (Decisions 8 and 11). A shutdown's flushes reach a mount's
  provider: the ending hands dirty buffers over, as at a turn's end, bounded the same way.
- **The cap on open files** (Decisions 5, 11 and 22). Scoped per session, set at the opening,
  holding through the ending, written in here for 068 as 060's argument was; 068 owns the
  mechanism. Decision 22 no longer lists it as left out.
- **The judge** (criteria 4, 6, 7, 12, 21, 24, 26 and 32 amended; 34 to 40 added): the raw
  export and its refusals; `atexit` and flushes on close and on expiry; a hostile handler
  stopped by fuel and by the deadline; no guest code after a stopped ending; no shutdown after
  a trap or an exit; the cap in a session.
- **The rest follows**: the Terms (the ending, the budget), *Kind* and *Depends on* (068 and
  069), the Intent, the Design, the Scope, the public API (Decision 17: `shutdown_s`,
  `shutdown_outcome`, the `Defaults` field, `close()`'s `Raises:`), the artifact set (Decision
  19: both binaries gain `shutdown`), the README and CHANGELOG text (Decision 20), and the
  owner's choices.

**What did not change.** `turn`'s contract, N1's rule that no turn finalizes, F10's ordering,
the reaper's step and the collector's lock-free wake, every per-turn limit, and `run()`.

**Review.** §5.6 asks for a pre-build review of a specification that changes the guest's
exports, and this revision adds one, so its delta was re-reviewed before the build (verdict:
ready once F1 to F3 are written in; "Disposition of the re-review", below). The re-review was
asked to look in particular at: the `shutdown` export's refusals and the
unfreeze (Decision 2); the ending's order and the outcome's rules (Decision 8); `None`
refused for `shutdown_s` and fuel taken from the session; closer threads and the exit hook
(Decisions 8 and 13); the loosened lifetime promise (Decision 9); the mount write-back at the
ending; and whether criteria 34 to 40 and their stand-ins prove the new behaviour.

## Disposition of the re-review

The re-review: `../reviews/055-bounded-sessions-close-revision-2026-10-18.md` (copied there by
the lane from `build/reviews-evidence/055-revision/rereview/`, with its probes `r1_probe` and
`r2_threads_at_exit`), of `ddc3fff`. Verdict: ready once F1 to F3 are written in; F4 to F8
written in or answered; the notes as the author sees fit. It confirmed the export's refusals,
the unfreeze at the export's own placement (100 bytes kept, 308.7 M fuel against 83.9 M
without), and the two-attribute design, which the lane accepts. Every finding is written in;
none is declined.

- **F1 (medium), `exit()` and `quit()` end a Jupyter kernel.** The lane's ruling: follow
  Jupyter. Decision 4 now says `sys.exit()` keeps the session and `exit()` / `quit()` end it
  through the shutdown after the turn, citing IPython's `run_code` and ipykernel's
  `ZMQExitAutocall` / `ask_exit` / `exit_now`; it names the one difference kept (Python's
  `exit(code)` stops the turn and reports the status). Decision 3 gives the mechanism (a quit
  flag the rebound `exit` sets), Decision 2 the export's 256-plus values and how the C side
  reads them without a guest-made status setting the bit, Decision 8 the `"quit"` row and
  string. Checks: criteria 1 and 41; criterion 11 drops `exit(5)`.
- **F2 (medium), the lifetime's promise needs a capped deadline.** Decision 8 arms the
  ending's deadline at the lesser of its start plus `shutdown_s` and the opening plus the
  lifetime plus `shutdown_s`, and skips the shutdown when that is past; Decision 9's promise
  says so. Check: criterion 36's new part (fake clock; armed ticks read; late reaper and late
  `close()` skip).
- **F3 (medium), one rule for when the shutdown runs.** The interpreter's state decides: a
  turn whose export returned leaves a sound interpreter, so its ending runs the shutdown on
  the turn's thread before `run` returns, whatever marked the session; a trapped, exited or
  stopped turn's ending runs none. Written in Decision 7 step 6, Decision 8's rule ("one
  rule", with which thread) and table (rows for a turn that `close()` stops and one that
  returns first, for `exit()`, and for the exit hook during a turn), Decision 10 and Decision
  13. Check: criterion 42 (a test hook between the export's return and the ending).
- **F4 (low), no write-back after a Ctrl-C or an embedder `BaseException`.** Decision 8 step 4
  walks through spec 034's walk, deferred-Ctrl-C check included, only on the endings for which
  a turn would return a `Completed`. Check: criterion 38's new part.
- **F5 (low), 37(a) did not prove the fuel.** 37(a) passes `shutdown_s=600` with a no-fuel
  stand-in; 37(a2) pins the figure to the session's fuel, with a fixed-fuel stand-in.
- **F6 (low), wall time under the default.** Every check that expects `"finished"` passes
  `shutdown_s=60` (the preamble of criteria 34 to 42; criteria 21, 24, 35, 36, 40, 41, 42).
- **F7 (low), context, loop and timing.** Decision 8's "What the embedder's code sees during
  the ending": the `contextvars` context (the thread's own, or the opening's copy on a closer
  thread); async tools on the session's private loop, closed after the ending, never a
  caller's loop; dropped sessions and the exit order (the runner's hook runs after the
  embedder's later `atexit` handlers). Decision 20's README text says so.
- **F8 (low), the exit hook.** Decision 13: it drains the collector's queue after stopping the
  reaper and ends those sessions too; the exit bound adds the endings' mount write-backs.
  Check: criterion 24(d).
- **N1, taken.** The `gc.unfreeze` reference is taken by the first `turn`, before any Python,
  not in `init_interpreter`, so the plain reactor's `run` is unchanged (Decisions 2 and 19).
- **N2, taken.** `shutdown` returns 120 for a failed finalization, as `run` does; the runner
  reads 0 and 120 as `"finished"` (Decisions 2 and 8).
- **N3, answered.** Decision 8 step 3 now says why a runner fault in the ending is quiet: an
  expiry has no caller, a `close()` raising after full release tells the embedder nothing it
  can act on, `"stopped"` records it, and the refusals are checked raw.
- **N4, taken.** Decision 8 and "The owner's choices" say how "small" was read: the time is
  the small part; the fuel is the session's per-turn fuel.
- **N5, taken.** The memo's wording is corrected (the snapshot loses a left-open file's bytes
  only when a function is defined in `__main__`; the cycle caveat rests on the probes and on
  native CPython, not on the C API's memory sentence), and the README text says a cycle-held
  file "may not be" flushed.
- **N6, answered.** 069 keeps `gc.freeze()`, so the unfreeze stays and its cost falls with the
  frozen heap; 055 already re-measures the ending's fuel on the set it builds against
  (*Depends on*, Decision 2). 069's own bullet for 055 is 069's text to update; the lane is
  told.

**The confirmation** (of `59509ac`, appended to the re-review) confirmed F1, F2 and F4 to F8 and
the notes, reopened F3 narrowly, and added one note, C1; once both are written in, the
revision is ready for build with no further round, and the lane checks them.
- **F3's `"error"` row, written in.** The shutdown runs only when the turn's `run` returns a
  `Completed`: a Ctrl-C noted by `_deferred_ctrl_c` after the export returned, a provider's
  `BaseException` in the turn's write-back walk, or a lost call ends with `"error"` and no
  shutdown (Decision 7, step 6; Decision 8's rule). Check: criterion 42's new part.
- **C1, taken (both).** The C side reads the tuple only if `PyTuple_CheckExact` holds, through
  `PyTuple_GET_SIZE` and `PyTuple_GET_ITEM`, and masks an int with `PyLong_Check` and
  `PyLong_AsUnsignedLongMask(...) & 0xFF` (Decision 2). Check: criterion 1's `2**100 + 4`
  case.

## Landing notes
