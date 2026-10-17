# State across agent turns

- **Status:** research, 2026-10-17. It commits the project to nothing. The owner approved this
  research before any specification.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). It wrote none of the runner or the recipes. Box:
  60 minutes; stopped at about 60. The artifacts were used read-only; nothing in the repository
  was edited but this file.
- **Feeds:** a later specification for sessions, if the owner wants one;
  `2026-10-17-market-research-use-cases.md`, question 3 ("state across calls");
  `2026-10-17-the-runtime-for-agent-code.md`, item 11.
- **Stands on:** constitution §3, §4.4, §4.15, §5.2 and §5.6; `src/wasi_python/runner.py`;
  `recipes/reactor_main.c`; `recipes/reactor_bootstrap.py`;
  `2026-10-17-what-a-replayable-run-needs.md`.

## The question

Agents expect a variable defined in turn one to exist in turn two. Today every `run()` is a
fresh instance, so it does not. How should state cross turns, and at what cost to speed, memory,
safety and determinism?

## Terms

- **Turn:** one piece of model-written code, run after the last one has finished.
- **Session:** the turns of one conversation, with whatever state they share.
- **Instance:** one wasmtime store with the module instantiated in it. Today, one per `run()`.
- **At rest:** no export of the instance is running. Only then is the guest's whole state in
  its linear memory.
- **Fuel:** wasmtime's count of executed instructions. Tests count it; wall time is a benchmark
  fact (constitution §4.9).

## How the experiments were run

- **Machine:** Apple M1 Pro, arm64, macOS; wasmtime-py 49.0.0. Every wall time below is a
  benchmark fact from this machine, not a test.
- **Artifacts:** `build/artifacts/`, read-only. Snapshot sha256 `4130d3baa218ce9b…`, plain
  reactor `2df569f2f59397d5…`. Compiled modules came from the runner's own cache
  (`WASI_PYTHON_CACHE=build/cwasm-cache`), so no wall time includes a compile.
- **Scripts:** in the session's scratch folder, outside the repository (`state/h.py`, a small
  harness over wasmtime-py; `e1_run_twice.py` to `e5b_delta_and_idle.py`). Each was run with
  `WASI_PYTHON_CACHE=… uv run --project <repo> python <script>`. The essential programs are
  quoted below, so each result can be reproduced from this memo alone.
- **The turns used** (one list, so the options compare): `x = 41`; `print('x+1 =', x + 1)`;
  `import pandas as pd, numpy as np` and a 100,000-row DataFrame `df`; a `groupby` sum; a `def`
  and a `lambda`; a print of all of them; `y = 1`; `y += 1`; a 50 MB `np.zeros`; `del` of it;
  `print('y =', y)`.

## What the reactor does today (READ, then EXECUTED)

- **READ, `recipes/reactor_main.c`.** The snapshot exports `memory`, `run` and `host_alloc`; the
  plain reactor also exports `_initialize` and `wizer.initialize`. `run` sets `run_called`. A
  second call prints `run() may be called once per instance` and returns 70. After the program,
  `run` calls `Py_FinalizeEx()`. So `__main__`, and the interpreter with it, are gone when `run`
  returns.
- **READ, `recipes/reactor_bootstrap.py`.** `_reactor.run` reads argv and the environment, reseeds
  `random` and `numpy.random`, then executes the program in `sys.modules["__main__"].__dict__`.
- **READ, `runner.py`.** `_call_deferred` makes one `wt.Store` per call and closes it in a
  `finally`. `_drive` instantiates, calls `_initialize` if present, then `run`. Limits are set on
  the store before instantiation: memory by `set_limits`, the deadline by `set_epoch_deadline`,
  fuel by `set_fuel` after instantiation.
- **EXECUTED (E1).** One snapshot instance, `run` called twice: the first returns 0 and prints
  `turn 41`; the second returns 70 with the message above. Linear memory afterwards: 59,113,472
  bytes (902 pages, the snapshot's starting size).
- **EXECUTED (E1b, by parsing the binaries).** Both modules have one memory, one table and two
  globals. One global is mutable: the shadow stack pointer, initial value 16,777,216, not
  exported. At rest it is back at that value, so a memory image taken at rest is the whole
  guest state on the wasm side.

So no option that keeps a live interpreter works on today's exports as they are meant to be
used. Option 1 below either changes the recipe or bends the door.

## Option 1: a long-lived instance per session

Keep the store and instance. Run each turn in the same `__main__`.

### The prototype, with no recipe change (EXECUTED, E2)

`run` is called once, with `-c` and a program that loops on the door:

```python
import _host, sys, traceback
g = {"__name__": "__main__", "__builtins__": __builtins__}
while True:
    code = _host.call(b"next")
    if not code:
        break
    try:
        exec(compile(code, "<turn>", "exec"), g)
    except BaseException:
        traceback.print_exc()
    sys.stdout.flush(); sys.stderr.flush()
```

The host answers each door call with the next turn. Inside that host call it reads the fuel the
last turn used and sets the next turn's budget, through the caller's context
(`wasmtime_context_get_fuel` and `wasmtime_context_set_fuel`). It works. All eleven turns ran;
`y = 2` and `82 9 100000` came out, so variables, the DataFrame, a `def` and a `lambda` all
crossed turns.

| Turn | Fuel | Wall, warm (benchmark) | Linear memory after |
| --- | ---: | ---: | ---: |
| `x = 41` | 177,922 | 0.20 ms | 56.4 MiB |
| `print('x+1 =', x + 1)` | 290,526 | 0.24 ms | 56.4 MiB |
| `import pandas …; df = …` (100k rows) | 9,611,555 | 2.2 ms | 57.9 MiB |
| `groupby` sum and print | 33,065,326 | 5.1 ms | 58.2 MiB |
| `def double …; square = lambda …` | 559,233 | 0.28 ms | 58.2 MiB |
| `y = 1` | 171,201 | 0.09 ms | 58.2 MiB |
| `big = np.zeros(50_000_000, int8)` | 50,332,885 | 3.8 ms | 105.6 MiB |
| `del big` | 155,308 | 0.13 ms | **105.6 MiB** |

- **Against a fresh run (EXECUTED).** `wasi_python.run(["-c", "pass"], fuel=…)` used 81,913,302
  fuel and took about 25 ms warm. A trivial turn in a session uses about 175,000: some 460 times
  less fuel, and a fraction of a millisecond. Instantiating the session's store took 0.8 ms warm.
- **Repeatable (EXECUTED, four sessions).** Every turn's fuel was the same in each session, to
  within 9 instructions (the `print` turn: 290,526 or 290,535; the `groupby` turn: 33,065,319 or
  33,065,326). That is the same kind of noise the replay memo traced to inodes and the host's
  clock. A turn's fuel depends on the turns before it, so it is not the fuel of the same code in
  a fresh run.
- **Memory never shrinks (EXECUTED).** After `del big`, linear memory stayed at 105.6 MiB.
  WebAssembly memory can only grow. A session holds its high-water mark until it is closed.
- **An idle session's host memory (EXECUTED, E5b; benchmark).** Ten stores, each after the
  pandas turns, held open: host RSS grew by 37 MiB for one, 186 MiB for five, 374 MiB for ten.
  It fell back to +3 MiB when they were closed. So one idle session costs about 37 MiB of
  resident memory for this small workload, and more after a large one.
- **A turn that hits a limit ends the session (EXECUTED).** With a per-turn budget of 10⁹ fuel,
  `while True: pass` trapped with `all fuel consumed by WebAssembly`; the next turn never ran
  and the state was gone. `os._exit(4)` ended the session with `ExitTrap` code 4. `raise
  SystemExit(3)` was caught by the loop above; a real design must decide what it means.
- **Why a trap ends the session (INFERRED).** A trap unwinds the wasm stack without running
  CPython's cleanup. The interpreter is left mid-call, with its thread state, the GIL and any
  half-built object as they were. Nothing safe can be called in it again. micropython-wasm
  states the same rule: after a trap the session is thrown away (below).

### What the door prototype gets wrong

- **It spends the door (INFERRED).** §4.4 makes the door's frames "opaque to this project; what
  they mean is the embedder's". A runner that uses the door to send turns gives it a meaning, and
  shares it with the embedder's own tools. Every frame would need a tag to say which it is. That
  is a tool-call convention, which the owner deferred (question 12).
- **The guest is never at rest (INFERRED).** It waits inside a host call. So option 4's image
  cannot be taken, and a deadline that fires while the host waits for the model's next turn
  would have to be suspended by hand.

### What a new export would need (READ and INFERRED)

- **§4.4 limits imports, not exports (READ).** "The guest reaches the host through exactly two
  things: the WASI preview1 calls and one custom import". An export adds no way out. §5.6 still
  applies: a specification that changes the guest's exports is reviewed once more before it is
  built.
- **The shape (INFERRED).** A second export beside `run`, for example `turn(ptr, len) -> i32`.
  The host writes the code into memory through `host_alloc`, as the door already does. The export
  unpins, initializes on first use like `run`, compiles the code as `<turn>`, executes it in
  `__main__.__dict__`, prints any traceback through `sys.excepthook`, flushes, and returns
  without `Py_FinalizeEx`. `run` keeps its once-per-instance rule; a store uses either `run` or
  `turn`, never both. This is a recipe file change (`reactor_main.c` and the frozen bootstrap),
  not an upstream patch.
- **Per-turn limits (INFERRED from E2 and `runner.py`).** Between turns the instance is at rest,
  so the runner can call `store.set_fuel` and `store.set_epoch_deadline` before each turn, just
  as it does today before `run`. The output cap can be per turn on the host side. Memory is the
  exception: `set_limits` is per store, so the memory cap is per session.
- **Runner work (INFERRED).** A `Session` object that owns one store, its root and its HOME; one
  turn at a time (a store is not safe to use from two threads at once); `close()` and a context
  manager; an idle timeout and a lifetime limit, each with a default (§4.15); the session marked
  dead after any trap or exit; and per-turn `Completed` results.

## Option 2: replay earlier turns in a fresh instance (EXECUTED, E3)

Each turn is a fresh `wasi_python.run`. Its program executes every earlier turn with output
silenced and exceptions swallowed, then the new turn.

| Turn | Fuel of that turn's run | Wall (benchmark) |
| ---: | ---: | ---: |
| 1 (`x = 41`) | 84,043,976 | 40 ms |
| 4 (after pandas and `groupby`) | 127,143,249 | 43 ms |
| 9 (after `np.zeros`) | 179,074,591 | 40 ms |
| 11 | 179,585,569 | 40 ms |

- **Cost grows with the session.** Turn *n* pays for turns 1 to *n*. The eleven turns cost about
  1.44 billion fuel in all; the same turns in one session cost about 95 million plus one start.
- **Side effects repeat (EXECUTED).** One turn called the door once (`_host.call(b'send-email')`);
  over four turns the door was called four times. A tool call, a file write or an append repeats
  on every later turn.
- **It is not even the same state (EXECUTED).** Turn 1 printed `random.random()` as
  0.7793614797437172. Turn 2, which replays turn 1, printed `r` as 0.0034206604403239638. Every
  run reseeds from WASI entropy, so state that drew entropy changes silently. Only a fixed seed
  per session (the replay memo's work) would make it repeat; the inode and clock noise would
  remain.
- **What it keeps.** Every turn is a fresh instance, so every limit and every safety property of
  `run()` holds unchanged. An idle session costs only its code. No recipe change.

## Option 3: pickle the globals into the guest's root (EXECUTED, E4)

Each turn is a fresh `wasi_python.run` with `root=` one directory per session. A prelude loads
`/.state/globals.pkl`, runs the turn in `__main__`, and pickles what it can back. Modules are
kept by name and imported again.

- **The naive form wedges the session (EXECUTED).** Pickling the whole dict at once succeeded on
  the `def` turn, because pickle stores a function as the name `__main__.double`. The next turn's
  load failed with `AttributeError: module '__main__' has no attribute 'double'`, and so did every
  turn after it. One `def` broke the session for good.
- **Per name, it degrades instead (EXECUTED, E4b).** Each value pickled on its own and loaded on
  its own; a failure loses that name only.

| Value | Survives a turn? |
| --- | --- |
| `int`, `str`, `DataFrame`, `Series`, `ndarray` | yes |
| modules (`pd`, `np`) | yes, re-imported by name |
| a `lambda` | no: `PicklingError` when saving |
| a `def` function, a class, an instance of that class | no: saved by name, `AttributeError` when loading |
| a generator, an open file | no: `TypeError` when saving |

  The print turn after these showed `[False, False, False, False, False, False]` for `double`,
  `square`, `Point`, `p`, `gen` and `fh`. Agents define functions often, so this loss is common,
  not a corner case. Keeping the source of `def` and `class` turns and replaying them, or
  pickling code objects with `marshal` as dill does, would close part of it. Either is new code
  of this project's own, and dill is not in the artifact.
- **Cost (EXECUTED; wall is benchmark).** With the 100k-row DataFrame, a turn cost 89 to 126
  million fuel and about 30 ms, with an 801 KB state file. After a 1,000,000-row DataFrame with a
  string column, even `y = 1` cost 2,064,472,579 fuel and 188 ms: 78 ms to load and 83 ms to save
  a 10.7 MB file, every turn. A session turn of `y = 1` costs 171,201 fuel.
- **Safe by construction.** Every turn is a fresh instance with every limit. The state file is in
  the session's own root and is unpickled only inside the guest. The host must never unpickle it.
  A guest can write anything into that file, and only the same session's later turns read it.
- **No recipe change.** The prelude is Python passed by `-c`, or a small module the runner
  ships. pandas' `to_pickle` and `np.savez` work in the guest; `np.save` to a file does not
  (`2026-10-17-numpy-npy-files-need-dup.md`); pyarrow is not built, so Parquet is not available.

## Option 4: a memory image per session

Take the instance's linear memory after a turn. Start the next turn from it in a fresh store.

- **The image can only be taken at rest (READ and INFERRED).** The wasm call stack lives on the
  host's native stack, not in linear memory. An image taken inside a host call (the door
  prototype) cannot be resumed. So this option needs option 1's new export first; it is a way to
  keep a session between turns, not a way around the recipe change.
- **An image taken at rest restores and runs (EXECUTED, E5).** Instance A of the plain reactor
  ran `_initialize` and `wizer.initialize` (what Wizer runs at build time): 4,964,078,845 fuel.
  Its 56.4 MiB of memory were copied. Instance B, fresh, was grown to the same size, A's image
  written over it, and `run` called with `import sys; x = 7; print('pandas preloaded:', 'pandas'
  in sys.modules, x * 6)`. It printed `pandas preloaded: True 42` and returned 0, using
  82,186,824 fuel. The published snapshot running the same program used 82,289,031. So the
  image alone carried the live interpreter.
- **Cost (EXECUTED; benchmark).** Copying 56.4 MiB out took 10.2 ms; writing it into B took
  5.4 ms. zlib level 1 shrank it to 15.6 MiB but took 412 ms, too slow per turn.
- **A delta is small (EXECUTED, E5b).** After four session turns (pandas, a `groupby`, a `def`),
  1,391 of the 4 KiB pages differed from the snapshot's starting image: 5.4 MiB, or 1.7 MiB
  compressed. An image could be stored as a delta against the published snapshot.
- **What the image does not hold (READ and INFERRED).** The host's WASI state: open file
  descriptors, the preopens' host side, the output streams, and the monotonic clock's origin
  (the runner counts it per store, `runner.py`, `origin_ns`). A file left open across turns
  would point at nothing; `time.monotonic()` would jump. The preopen table inside memory matches
  only if the new store preopens the same directories in the same order.
- **Wizer at run time (READ, INFERRED).** Wizer writes a new module, which must be compiled. The
  first compile of the snapshot takes about 3 s (README). Per turn, that rules it out.
  wasmtime-py exposes no dirty-page tracking and no instance snapshot; this research found no
  such API in wasmtime either (UNVERIFIED that none exists).
- **What it gives (INFERRED).** Every turn runs in a fresh store, so every per-store limit is per
  turn again, memory included. A trap loses only the turn: the next turn restores the last good
  image. An idle session costs disk, not resident memory. This is the pattern behind Anthropic's
  checkpoint after five idle minutes and E2B's pause (below).
- **What it costs (INFERRED).** The images hold the tenant's data. They need per-tenant storage,
  and an integrity check if they ever leave the host's control. Restoring a tampered image gives
  the guest arbitrary state, still inside the wall. The image's format is tied to one module
  digest; a new release cannot load an old session.

## Option 5: what others do (READ, by a research sub-agent on 2026-10-17; each link was fetched)

- **Pydantic Monty:** serializes. `session.dump()` writes globals, functions and classes to
  bytes (CBOR with a version header, capped at 256 MiB); `load_session` restores into a fresh
  session. A bytecode change rejects old dumps. Dumps are not authenticated. No idle timeout: the
  session is bytes the host keeps.
  ([snapshots](https://pydantic.dev/docs/monty/concepts/snapshots/),
  [limits](https://pydantic.dev/docs/monty/concepts/resource-limits/),
  [article](https://pydantic.dev/articles/pydantic-monty))
- **micropython-wasm:** both option 1 and option 2. `MicroPythonSession` keeps one wasmtime
  instance on a thread; the guest blocks on a host function, `__session_next__()`, for the next
  snippet: the door prototype above. `MicroPythonReplaySession` replays earlier successful
  snippets. Fuel is refilled per run; after a trap the session must be discarded; separate
  worker processes are advised for many tenants.
  ([post](https://simonwillison.net/2026/Jun/6/micropython-in-a-sandbox/),
  [repo](https://github.com/simonw/micropython-wasm))
- **Pyodide tools:** LangChain Sandbox (archived 2026-01-14) returned pickled `session_bytes`
  with dill, passed back next call ([repo](https://github.com/langchain-ai/langchain-sandbox)).
  Cohere Terrarium kept no state ([repo](https://github.com/cohere-ai/cohere-terrarium)).
  mcp-run-python (archived) warned that code can taint the runtime for later calls
  ([repo](https://github.com/pydantic/mcp-run-python)). smolagents' local executor keeps one
  `state` dict ([source](https://raw.githubusercontent.com/huggingface/smolagents/main/src/smolagents/local_python_executor.py)).
- **E2B:** a live interpreter in a Firecracker microVM; at most 1 h (Hobby) or 24 h (Pro).
  Pause saves memory and filesystem, about 4 s per GiB to pause and 1 s to resume.
  ([sandbox](https://docs.e2b.dev/sandbox), [persistence](https://docs.e2b.dev/sandbox/persistence))
- **Jupyter:** a live kernel. `cull_idle_timeout` is off by default
  ([config](https://jupyter-server.readthedocs.io/en/latest/other/full-config.html)); Enterprise
  Gateway suggests 12 h ([culling](https://jupyter-enterprise-gateway.readthedocs.io/en/latest/operators/config-culling.html)).
- **OpenAI code interpreter:** a container that expires after 20 minutes idle; memory tiers 1 to
  64 GB; objects in memory are lost at expiry
  ([guide](https://developers.openai.com/api/docs/guides/tools-code-interpreter)).
- **Anthropic code execution tool:** a container reused by id; checkpointed after about 5
  minutes idle and restored on the next request; expires 30 days after creation; 5 GiB of memory
  ([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool)).
- **Others:** AWS AgentCore, 15 min default session, up to 8 h
  ([docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-session-characteristics.html));
  Azure dynamic sessions, a 300 to 3,600 s cooldown
  ([docs](https://learn.microsoft.com/en-us/azure/container-apps/session-pool)); Daytona,
  auto-stop at 15 min ([docs](https://www.daytona.io/docs/en/sandboxes.md)); Together, 60-minute
  sessions by `session_id` ([blog](https://www.together.ai/blog/code-interpreter)).
- **Wasm memory images:** Cloudflare's Python Workers snapshot Pyodide's memory once, at deploy
  time, not per session ([blog](https://blog.cloudflare.com/python-workers-advancements/)).
  Wasmer's journal records memory and stacks, using asyncify for the stacks
  ([journal](https://github.com/wasmerio/wasmer/blob/main/docs/journal.md)). Wizer snapshots
  ahead of time only ([repo](https://github.com/bytecodealliance/wizer)).

The pattern: a live interpreter with an idle timeout is the norm (20 min at OpenAI, 15 min at
AWS and Daytona). Memory or VM snapshots let a session outlive its process. Serialization is
what the in-process tools without a live instance use.

## Comparison

Fuel and memory are EXECUTED; wall times are benchmark facts on one M1 Pro.

| | 1. Live instance | 2. Replay | 3. Pickle in root | 4. Memory image |
| --- | --- | --- | --- | --- |
| **Latency per turn** | ~0.1–5 ms for these turns; ~175k fuel for `y = 1` | a fresh run (~25–40 ms, ≥82M fuel) plus every earlier turn; grows with the session | a fresh run plus load and save of all state: 30 ms small, 188 ms and 2.06B fuel at a 10.7 MB state | a fresh store, plus ~5 ms to write 56 MiB in and ~10 ms to copy out (raw); compression or deltas cost more |
| **Memory per session** | resident: ~37 MiB idle after pandas; linear memory never shrinks | the code only | the state file on disk (size of the data) | an image on disk: ~56 MiB raw, ~1.7 MiB as a compressed delta after 4 turns |
| **Limits each turn** | fuel, deadline, output per turn; memory per session only | all, per turn (but each turn pays for replay) | all, per turn | all, per turn, memory included |
| **After a trap** | the session is lost | the next turn replays | the last saved state remains | the last good image remains |
| **Leak between tenants** | only if a session is reused; must be bound to one caller | none | none; the file is in the session's root | none in memory; images on disk hold tenant data |
| **What survives** | everything | everything, recomputed; entropy differs | data; not functions, classes, lambdas, files, generators | everything except open files and host-side state |
| **Determinism** | same turns, same fuel (±9) | outputs drift with entropy; side effects repeat | same as a fresh run plus the state | same as option 1 |
| **Complexity** | runner `Session`; idle and lifetime bounds | runner only | a prelude; per-name failures to report | option 1's export plus image storage, restore, and WASI caveats |
| **Recipe change** | a new export (`turn`), or the door bent | none | none | the same new export |

## Recommendation

1. **Specify option 1, with a new export, as an opt-in session.** It is the only option where a
   turn costs a fraction of a millisecond and everything survives, functions included. It is
   what Jupyter, E2B, the hosted tools and micropython-wasm do. `run()` stays exactly as it is:
   one program, one instance, nothing kept. A session is a separate, explicit object.
2. **Use the export, not the door.** The door loop works today and proved the numbers. But it
   gives the door a meaning the constitution reserves for the embedder, and it never comes to
   rest, which closes off option 4. An export adds no way out of the wall (§4.4); it needs the
   pre-build review of §5.6.
3. **Make it safe by default (§4.15).** A memory cap per session (today's 1 GiB). Fuel, deadline
   and output caps per turn, with today's defaults. An idle timeout and a maximum lifetime, both
   on by default, after which the runner closes the store. A trap or an exit ends the session and
   says so in the turn's result. A session belongs to the caller that opened it; the runner never
   pools or hands one to another caller.
4. **Leave option 4 for later.** Once the export exists, an image at rest gives pause and resume,
   per-turn memory caps, and rollback after a trap. It is real work (storage, the WASI caveats, a
   format tied to one release), and agents get most of the value from option 1 alone.
5. **Do not build option 2 or 3 into the product.** Replay repeats side effects and drifts with
   entropy. Pickling loses functions, the thing agents define most. An embedder who wants state to
   outlive a process can already write files to a granted root and read them back; the README
   can show that pattern without new code.

## What a specification would need to decide

- **The export:** its name and signature (code by pointer and length through `host_alloc`); what
  it returns; whether a turn echoes the value of a final expression, as a notebook does.
- **`SystemExit` in a turn:** end the session, or report the code and keep going.
- **`run` and `turn` in one store:** refused, and how.
- **Per-turn setup:** whether random reseeds each turn or once per session; whether `argv`,
  `env` and `stdin` are per session (WASI fixes them per store) or per turn.
- **The runner API:** `Session` methods, results per turn (`Completed` or a new type), thread
  rules, and how `run_async` (spec 015) extends to turns.
- **Defaults:** idle timeout, maximum lifetime, maximum turns if any, per-session memory cap, and
  what happens at each bound.
- **The root:** a fresh private root per session, removed on close, and HOME per session.
- **The judge:** checks that count, never time. A variable crosses turns. A `def` crosses turns.
  A runaway turn traps on its own fuel and ends the session. A closed session refuses turns. Two
  sessions share nothing. Fuel per turn repeats within a stated band. `run()`'s results are
  unchanged.
- **Determinism:** whether a session's per-turn fuel is promised, and with what noise, given the
  inode and clock findings of the replay memo.

## Questions for the owner

1. **May the guest gain a second export for turns?** It changes the recipe and the guest's
   exports, not its imports (§4.4), so it needs the §5.6 pre-build review.
2. **Is a session in scope?** §3 says the project is "not a development environment" and "an
   embedder runs a program and gets its result". A session is a long-lived interpreter the
   runner holds. Is that still "a run", or a step toward a shell the constitution rules out?
3. **The default bounds.** Which idle timeout and lifetime should a session have when the caller
   names none? The market uses 15 to 20 minutes idle.
4. **Is "a trap ends the session" acceptable for v1,** with pause, resume and rollback (option 4)
   left to a later specification?
5. **Should the README show the files-in-a-root pattern** (option 3, written by the embedder) for
   state that must outlive a process, instead of the project shipping it?

## One line

A live instance per session, through a new export that runs a turn without finalizing, makes a
turn about 460 times cheaper than a fresh run and keeps everything, including functions; it
holds memory while idle and loses the session on a trap, so it needs default bounds, and memory
images can later add pause and rollback.
