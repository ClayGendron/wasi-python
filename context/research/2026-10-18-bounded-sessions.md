# Bounded sessions: what one instance does across several calls

- **Status:** executed, 2026-10-18. An addendum to `2026-10-17-state-across-agent-turns.md`. It
  commits the project to nothing. Section 8 was added the same evening for spec 055's revision
  (the owner's decision on question 92: close as Jupyter does), EXECUTED on main `4a94c14`'s
  artifact set and READ from Jupyter's sources.
- **Owner:** Clay Gendron
- **Researcher:** the drafting agent (Claude Opus 5.5) of spec 055. It wrote none of the runner or
  the recipes. Box: 45 minutes; stopped at about 40. Nothing in the repository was changed by the
  probes; the artifacts were copied to the session's scratch folder and used read-only.
- **Feeds:** spec 055 (bounded sessions).
- **Stands on:** `2026-10-17-state-across-agent-turns.md` (option 1, the door-loop prototype E2,
  E1b's resting shadow stack); `2026-10-17-the-runtime-for-agent-code.md` item 11; the owner's
  decisions 18 to 22 and 49 (`../decisions.md`); `recipes/reactor_main.c`,
  `recipes/reactor_bootstrap.py`, `scripts/steps/80_snapshot.sh`, `src/wasi_python/runner.py`
  at main `62d2c56` (READ).

## The questions

The first memo chose a live instance per session, with a second export that runs a turn
without finalizing. A specification needs six more facts:

1. Can fuel and the epoch deadline be set again before each call into one instance, and does a
   trap leave the store callable?
2. Can one store be called from several threads in turn, and closed from yet another (an idle
   reaper)?
3. What happens when a turn meets the session's memory cap: a Python exception, or a trap?
4. Is every byte a turn wrote in the host's stream when the turn hands control back, so output
   can be capped per turn by swapping streams?
5. When memory is at the cap, how does `host_alloc` fail, for the next turn's code?
6. Does Wizer keep a new export in the snapshot, and what does echoing a final expression cost?

## How the probes were run

- **Machine:** Apple M1 Pro, arm64, macOS; Python 3.14.2 under `uv run`; wasmtime-py 49.0.0 (the
  lock's); the pinned `wasmtime` CLI 49.0.3 from the build's tools, for Wizer only.
- **Artifacts:** main's `build/artifacts/`, copied to the scratch folder and checked against its
  `SHA256SUMS` (all OK): snapshot `f94dec535086b06c…`, plain reactor `5648e4c5143da71d…`, zip
  `daf2cdd86357e617…`.
- **Scripts:** in `2026-10-18-bounded-sessions/`, beside this memo, with each output as run.
  `h.py` is a small harness over wasmtime-py: one store, WASI with the zip preopened at
  `/usr/local/lib`, the door bound to a Python function, and the guest's stdout and stderr
  through the runner's own `_send_outputs` and `_Stream`. `loop.py` is the first memo's door
  loop: one `run`, each door answer the next turn's code. To reproduce, put the artifact set in
  `<dir>/artifacts/`, the zip as `<dir>/probes/zipdir/python315.zip`, the scripts in
  `<dir>/probes/`, and run `uv run python <dir>/probes/pN_….py <dir>/probes` from the
  repository.
- Every number below is a count (fuel, bytes, pages). No wall time is reported.

## What was found

### 1. Fuel and the deadline are per call; a trap does not close the store (EXECUTED, P1, P2)

- `host_alloc(64)` called five times on one snapshot instance, `set_fuel(10,000,000)` before
  each, used 99 fuel each time (`p1_repeat.txt`: `[99, 99, 99, 99, 99]`). The budget is simply
  the store's fuel when the call starts.
- With 5 fuel, `host_alloc` trapped `OUT_OF_FUEL`. After `set_fuel` again, the next call
  returned a pointer. **wasmtime lets a trapped store be called again.** The runner, not
  wasmtime, must refuse the next turn after a trap.
- `set_epoch_deadline(1)`, then two `increment_epoch()`, then a call: it trapped `INTERRUPT`.
  After `set_epoch_deadline(1000)` the next call ran. **The deadline is relative to the engine's
  epoch when it is set**, so the runner can arm a fresh deadline before each turn, as it does
  before `run` today (READ, `_instance`).
- A `run` called afterwards on the same instance, after the two traps, returned 0. The traps
  here hit `malloc`'s entry, not the interpreter. This shows nothing about re-entering an
  interpreter that trapped mid-call; the first memo's reason to end a session on a trap stands
  (INFERRED there: a trap skips CPython's cleanup).

### 2. One store, several threads in turn (EXECUTED, P3)

`host_alloc` on one store from three threads, one after another, then `store.close()` from a
fourth: every call returned a pointer (fuel 99, 99, 101) and the close raised nothing. A
session's turns may therefore run on whichever thread calls, one at a time, and an idle reaper
on its own thread may close the store. The runner's host functions find their call through the
calling thread's stack (READ, `_stack`), so each turn pushes its own call on its own thread.

### 3. The memory cap is a `MemoryError`, and the session goes on (EXECUTED, P4)

A door-loop session with `set_limits(memory_size=256 MiB)` (`p4_memory.txt`):

| turn | result | linear memory after |
|---|---|---:|
| `import numpy as np; x = 1` | ok | 56 MiB |
| `a = np.zeros(300_000_000, np.int8)` | `_ArrayMemoryError: Unable to allocate 286. MiB …` | 56 MiB |
| `print('after a big array', x)` | `after a big array 1` | 56 MiB |
| `b = [0] * (10**8)` | `MemoryError` | 56 MiB |
| `l = []` then `bytearray(1 << 16)` appended until it fails | `MemoryError` | 256 MiB |
| `del l; gc.collect(); print(…)` | `after 64 KiB blocks 1` | 256 MiB |
| `l = []` then `str(len(l))` appended until it fails | `MemoryError` | 256 MiB |
| `print('after small objects', x)` | `after small objects 1` | 256 MiB |

The `run` ended normally (returned 0). Large and small allocations alike failed as Python
exceptions, and every later turn ran with its earlier variables. **Meeting the memory cap does
not end a session.** Memory stayed at its high-water mark (256 MiB) after `del` and a
collection, as the first memo found: linear memory never shrinks.

### 4. A turn's output is all delivered when it hands control back (EXECUTED, P5)

Twenty turns each wrote 1 MiB plus a line to stdout and 512 KiB to stderr, then flushed. At each
door call the host swapped the store's two stream keys to fresh `_Stream`s and counted what the
old ones held: **20 of 20 turns had every byte** (`p5_output.txt`). wasmtime calls the custom
output's write function before `fd_write` returns, so nothing is in flight once the guest has
flushed and control is back with the host. Three small turns after them (`print`, `1/0`,
`print`) each had exactly their own output. Output can be capped and returned per turn by
swapping the stream behind each key between turns, with no change to how the store is made.
The flush matters: Python's own buffer is the guest's, so the turn must flush `sys.stdout` and
`sys.stderr` before it returns (the door loop did; `run` does today in `_reactor.run`'s
`finally`).

### 5. At the cap, `host_alloc` answers NULL (EXECUTED, P6)

A turn filled memory to the 256 MiB cap in 64 KiB blocks, caught the `MemoryError`, and kept
the list. Then, from the host, `host_alloc(1 MiB)` returned 0, while `host_alloc(4096)` and
`host_alloc(64)` returned pointers (`p6_alloc_at_cap.txt`). Nothing trapped, and the next turn
ran. So a turn whose code cannot be placed in guest memory gets a NULL pointer, cleanly, and the
instance is unharmed. The export can turn that into a `MemoryError` inside the guest.

### 6. Wizer keeps a new export; echoing costs about half a million fuel per turn (EXECUTED, P0, P7, P8)

- Today's binaries (`p0_exports.txt`): the snapshot exports `host_alloc`, `memory` and `run`; the
  plain reactor those three plus `_initialize` and `wizer.initialize`. Wizer removes the
  initialisers and keeps the rest.
- A tiny module with exports `memory`, `_initialize`, `wizer.initialize`, `run`, `turn` and
  `host_alloc`, put through the pinned `wasmtime wizer` with step 80's `--init-func`, came out
  with `memory`, `run`, `turn` and `host_alloc` (`p7_wizer.txt`), and `turn` read the global
  and the memory word the initialiser had written (48 = 41 + 7). **A `turn` export survives the
  snapshot step unchanged in kind;** step 80 needs no change.
- The snapshot already re-enters a live interpreter from a new export call: `wizer.initialize`
  runs Python and returns to the host, and every `run` later enters that interpreter afresh
  (READ, `reactor_main.c`; EXECUTED by every snapshot run). A `turn` that returns without
  `Py_FinalizeEx`, and a next `turn` that enters again, is the same pattern repeated.
- `ast` and `linecache` are already imported in the snapshot (P8: `True True`). Through `run`
  on the snapshot, a four-line turn (an import, a list comprehension, a sum, a final
  expression), compiled 100 times, cost 729,100 fuel per plain `compile` and 1,306,044 per
  "parse to `ast`, split off the last expression, compile both" (`p8_echo_cost.txt`, the
  minimum of three runs each). **Echoing the last expression adds about 580,000 instructions to
  a four-line turn.** For scale: a fresh `run(["-c", "pass"])` costs about 82,000,000 (P8's
  "empty"), and the first memo's `x = 41` turn 177,922.

### 7. What the host must hold and do between turns (READ and INFERRED)

- **READ, `runner.py`.** Everything a call needs is made per call in `_call_deferred` and
  `_instance`: the store, HOME, the scratch folder (stdin, the mounts' placeholder), the WASI
  config (argv, env, preopens, the two output keys), the linker choice, the mount table, the tool
  host and its bound, the `_Call`, the epoch ticker's activation. For a session, the store,
  HOME, scratch, WASI config, linker, mount table and the walked grants live as long as the
  session; the `_Call`, the streams' contents, the tool host, the fuel budget, the deadline and
  the ticker's activation are per turn.
- **READ.** The epoch ticker runs only while some call is inside `_epoch_ticker` (`_active >
  0`). An idle session runs no guest code and needs no tick: nothing in the guest waits, and
  nothing in the guest can measure idleness. **Idle and lifetime bounds are host bookkeeping:**
  a monotonic time at open and at the end of each turn, checked when a turn is asked for, and by
  one host thread that closes sessions whose bound has passed. No timer runs in the guest, and
  the guest gains no import.
- **INFERRED.** Because the bounds are host arithmetic on a clock the runner reads, a check can
  inject the clock and drive the reaper's step directly, with no sleep: the same shape as spec
  010's `_Waits` and spec 036's `_Bounded`, both driven by fakes in the judge.
- **READ, `mounts.py`.** A mount table is bound to the store once (`bind`), keeps open entries
  in `table`, and hands dirty buffers to the provider in `walk()` at the call's ending (spec
  034, Decision 8; the owner's decision 71). Its counters (`calls`, `total`, `faults`,
  `refused`) are per call today. A session keeps the table and its open entries across turns;
  the counters and the write-backs can be per turn.
- **READ, `tools.py`.** `_ToolHost` holds one call's frame count, budget and record, and
  `_Bounded` one call's deadline, cancel and abandoned-thread count. The guest's `host.tools`
  lists the tools once, when first imported (`recipes/guest/host/tools.py`), so the tool set must
  stay fixed for a session; the frame host and its record can be per turn.

### 8. Python's shutdown in today's guest, and how Jupyter closes a kernel (EXECUTED, READ; added for the revision)

The owner chose that a session's close and expiry run Python's normal shutdown inside a small
budget, as Jupyter does. Today's guest already runs that shutdown once, at the end of every
`run` (`Py_FinalizeEx` in `reactor_main.c`'s `run`, READ). These probes measure it through
`run`, which has the same C shape a session's ending would have.

- **Set and machine.** Main `4a94c14`'s `build/artifacts/`, checked against its `SHA256SUMS`
  (all OK): snapshot `4eb5418a2b1bb553…`, plain reactor `1655014314805b58…`, zip
  `16ee747c97c5397b…`. Same machine and wasmtime-py as above. Scripts and outputs beside this
  memo (`p9_shutdown`, `p10_flush`, `p10b_flush_main`, `p11_flush_all`, `p12_unfreeze`), run
  with `uv run python <script> <output>` from the repository; copies are in the main tree's
  `build/reviews-evidence/055-revision/`.

**What the shutdown costs (EXECUTED, P9).** The same program ended normally and ended by
`os._exit(0)` (which skips the shutdown), minimum of three runs each:

| binary | program | normal exit | `os._exit` | the shutdown |
|---|---|---:|---:|---:|
| snapshot | `pass` | 83,377,574 | 2,629,274 | 80,748,300 |
| snapshot | `import pandas` | 83,342,747 | 2,644,086 | 80,698,661 |
| plain | `pass` | 166,578,103 | 138,192,010 | 28,386,093 |
| plain | `import pandas` | 4,917,006,376 | 4,614,211,379 | 302,794,997 |

So almost all of a fresh snapshot `run`'s 83 M instructions is its shutdown: the teardown of
the pre-imported stack. A shutdown costs tens to hundreds of millions of instructions, and the
figure moves thirtyfold with the binary and the heap. A fixed small fuel share would stop
ordinary shutdowns.

**atexit and `os._exit` (EXECUTED, P9).** On both binaries: a handler registered in the
program runs at a normal exit; after `os._exit(4)` it does not, and a buffered file is not
flushed (Python's documented `os._exit`). A handler that loops forever is stopped by fuel
(`trapped == "out of fuel"` at `fuel=10**9`) and by the deadline (`"deadline"` at 0.5 s), and
a handler that calls `time.sleep(10**6)` is stopped by the deadline; the program's own output
is all delivered first. `sys.exit(7)` inside a handler is printed as `Exception ignored in
atexit callback … SystemExit: 7` and the exit status stays 0. A handler that registers another
handler during the shutdown: the new one does not run. `os._exit(5)` inside a handler ends the
instance with exit 5 (an exit trap) and the handlers after it do not run.

**Open files are not reliably flushed on the snapshot (EXECUTED, P10, P10b).** A file opened
for writing, written and left open, is flushed by the shutdown on the plain reactor in every
variant tried. On the snapshot it is flushed unless a function is defined in `__main__`: with
any `def` in the program (two variants, two runs each), the file loses its 100 buffered bytes
every time, and it keeps them in every variant without one. A file held only in a reference
cycle (`f.me = f; del f`) loses its bytes on both binaries, which is CPython's own documented
caveat ("Memory tied up in circular references between objects is not freed", the C API's
`Py_FinalizeEx`). INFERRED cause of the snapshot's difference: step 80's initialiser ends with
`gc.collect(); gc.freeze()` (READ, `reactor_main.c`), so `__main__` and its dict sit in the
permanent generation, and a `def` makes the cycle `__main__.__dict__` ↔ the function's
`__globals__`, which the shutdown's collection then never breaks before the file would be
closed. Every model-written turn defines functions, so in a session this would lose buffered
writes on the default binary.

**Two fixes measured (EXECUTED, P11, P12).** The program of P2 plus a cycle-held file:

| binary | shutdown variant | left-open file (110 bytes written) | cycle-held file (100) | fuel of the whole run |
|---|---|---:|---:|---:|
| snapshot | `Py_FinalizeEx` alone | 0 | 0 | 84,542,344 |
| snapshot | `gc.unfreeze()` as the last handler, then the same | 110 | 0 | 309,563,330 |
| snapshot | every live `io.IOBase` flushed as the last handler | 110 | 100 | 87,712,962 |
| plain | `Py_FinalizeEx` alone | 110 | 0 | 167,860,729 |
| plain | `gc.unfreeze()` as the last handler | 110 | 0 | 168,340,290 |
| plain | every live `io.IOBase` flushed as the last handler | 110 | 100 | 210,844,794 |

- `gc.unfreeze()` before the teardown gives the snapshot exactly the plain reactor's (CPython's)
  behaviour, the cycle-held file included, at about 225 M more instructions on today's
  snapshot, whose frozen heap holds the pre-imported stack; on the plain reactor it costs about
  0.5 M.
- Flushing every live file object flushes more than CPython does (the cycle too). Its cost is a
  walk of `gc.get_objects()`: 2,227,374 instructions on the snapshot after pandas, whose stack
  is frozen and so not walked, but 376,439,099 on the plain reactor after importing pandas
  (P11's last lines). The owner's decision 34 (the snapshot pre-imports no package; spec 069)
  will make the snapshot's heap like the plain reactor's, so this walk would cost hundreds of
  millions on the default binary too, while the unfreeze's cost falls with the frozen heap.
  INFERRED; the figures after spec 069 are the builder's to measure.

**How Jupyter closes a kernel (READ, main branches on GitHub, 2026-10-18).**
- **jupyter_client**, `jupyter_client/manager.py`
  (https://github.com/jupyter/jupyter_client/blob/main/jupyter_client/manager.py):
  `KernelManager.shutdown_kernel(now=False)` stops the restarter, sends the kernel an interrupt
  (SIGINT) if it has one, and then either kills it at once (`if now: await
  self._async_kill_kernel()`) or sends a `shutdown_request` on the control channel and waits
  (`_async_finish_shutdown`). The wait is `shutdown_wait_time`, a configurable `Float` whose
  default is `5.0` seconds: "Time to wait for a kernel to terminate before killing it, in
  seconds. When a shutdown request is initiated, the kernel will be immediately sent an
  interrupt (SIGINT), followed by a shutdown_request message, after 1/2 of
  `shutdown_wait_time` it will be sent a terminate (SIGTERM) request, and finally at the end of
  `shutdown_wait_time` will be killed (SIGKILL)." A provisioner may override it.
- **ipykernel**, `ipykernel/kernelbase.py`
  (https://github.com/ipython/ipykernel/blob/main/ipykernel/kernelbase.py):
  `shutdown_request` calls `do_shutdown(restart)` (in `ipkernel.py`, `IPythonKernel.do_shutdown`
  sets `self.shell.exit_now = True` and returns `{"status": "ok", …}`), sends the
  `shutdown_reply`, awaits `_at_shutdown()` (which terminates the kernel's child processes,
  SIGTERM then SIGKILL, and re-broadcasts the reply), then schedules `stop` on the control
  and shell IO loops. `ipykernel/kernelapp.py`'s `IPKernelApp.start()` has nothing after
  `self.io_loop.start()`, so when the loops stop the process returns from `main` and exits
  through Python's normal shutdown: `atexit` handlers run, including the ones the kernel
  itself registered there (`atexit.register(self.cleanup_connection_file)`,
  `atexit.register(self.close)`) and IPython's (`InteractiveShell.__init__` registers
  `atexit.register(self.atexit_operations)`, `IPython/core/interactiveshell.py`).
- **jupyter_server**, `jupyter_server/services/kernels/kernelmanager.py`
  (https://github.com/jupyter-server/jupyter_server/blob/main/jupyter_server/services/kernels/kernelmanager.py):
  culling is off by default (`cull_idle_timeout = Integer(0, …)`, "Values of 0 or lower disable
  culling"); `cull_kernel_if_idle` ends an idle kernel with `shutdown_kernel(kernel_id)`,
  passing no `now`, so a culled kernel takes the same graceful path: interrupt, shutdown
  request, Python's normal exit with its `atexit` handlers if it exits within the wait, killed
  if not.
- **Python's documentation** (READ): the `atexit` module, "Exit handlers are not called when
  the program is killed by a signal not handled by Python, when a Python fatal internal error
  is detected, or when `os._exit()` is called", handlers run last in, first out, and an
  exception in one is printed (unless `SystemExit`) and the rest still run
  (https://docs.python.org/3/library/atexit.html); `os._exit` exits "without calling cleanup
  handlers, flushing stdio buffers, etc." (https://docs.python.org/3/library/os.html#os._exit);
  `Py_FinalizeEx` returns `-1` "if there were errors during finalization (flushing buffered
  data)", and "must not be called recursively from within itself … such as `atexit` handlers"
  (https://docs.python.org/3/c-api/interp-lifecycle.html).

So a Jupyter close and a Jupyter cull are the same thing: a bounded, graceful exit (5 s by
default, the embedder's to set), then a kill. The guest can do the graceful part with
`Py_FinalizeEx`, which runs `atexit` and flushes, provided the snapshot's frozen generation is
undone first; the host does the bound with the fuel and epoch deadline it already arms per call.

## What it decides

- The design the first memo chose holds on today's engine: per-turn fuel, deadline and output;
  turns on any thread, one at a time; close from any thread.
- The memory cap is per session and is not a trap: a turn that meets it gets `MemoryError` and
  the session continues. A session ends on a trap (decision 21), not on a full heap.
- A NULL from `host_alloc` for a turn's code can be reported inside the guest as `MemoryError`,
  with no new string in the result and no end to the session.
- Step 80 is unchanged by a new export. The recipe change is `reactor_main.c` (the export) and
  `reactor_bootstrap.py` (the turn's Python), both recipe files under §4.1.
- Echoing a final expression costs about 0.6 M fuel for a short turn, under 1% of a fresh run.
- (Section 8.) A session's ending can be Python's own shutdown, run through a new export that
  calls `Py_FinalizeEx` after undoing the snapshot's `gc.freeze()`, bounded by the fuel and the
  epoch deadline the host already arms. Its cost is tens to hundreds of millions of
  instructions, so its fuel cannot be a small fixed figure; Jupyter's own bound is a time, 5 s
  by default, set by the embedder.

## One line

One instance answers many calls: fuel and the deadline re-arm per call, output is complete at
each return, a full heap is a `MemoryError` not a trap, a NULL `host_alloc` is clean, Wizer keeps
a `turn` export, and idle and lifetime bounds are host arithmetic on an injectable clock. Python's
shutdown runs in the guest as it does at `run`'s end, bounded by fuel and the deadline, and
flushes open files on the snapshot only once its frozen generation is undone.
