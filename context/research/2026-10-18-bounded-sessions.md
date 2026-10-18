# Bounded sessions: what one instance does across several calls

- **Status:** executed, 2026-10-18. An addendum to `2026-10-17-state-across-agent-turns.md`. It
  commits the project to nothing.
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

## One line

One instance answers many calls: fuel and the deadline re-arm per call, output is complete at
each return, a full heap is a `MemoryError` not a trap, a NULL `host_alloc` is clean, Wizer keeps
a `turn` export, and idle and lifetime bounds are host arithmetic on an injectable clock.
