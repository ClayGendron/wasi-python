# The GC proposal off under wasmtime 51

- **Status:** research, 2026-11-22. A probe at the owner's request. It changes nothing that lands: no specification, no pin, no commit. The probe's edits stay uncommitted in its worktree (`../wasi_python-wt/gc-off-probe`, detached at a85cac7, which is `dev`, `main` and `v0.1.5`). Times are wall clock on one shared 4-CPU, 15 GiB virtual machine: benchmark facts, never checks.
- **Researcher:** an agent (Claude Opus 5.5), a probe sub-agent of the orchestrating session. It wrote none of the runner's code.
- **The question:** if the runner's two wasmtime engines set `cfg.wasm_gc = False`, on wasmtime-py 51.0.0, does anything in wasi-python change, and does performance change?
- **Artifacts:** the published 0.1.5 set (`python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip`), given through `WASI_PYTHON_ARTIFACTS`. Nothing was built.

Labels: **EXECUTED** is a fact this probe measured, with its command. **INFERRED** is reasoning.

## The short version

Turning the GC proposal off changes nothing a guest can see (EXECUTED).

- The judge gives the same verdict on every check, GC on or off. The only differences are two unit rows that list the engine's settings one by one, and the probe adds a setting.
- Fuel is the same. Under the judge's seeded driver it is the same to the instruction, on 24 exception-heavy programs and on 430 of 437 metered checks. The other 7 differ by 17 to 34 instructions in one run, and a GC-on run shows the same values.
- The compiled code is the same. A `.cwasm` made with GC off differs from one made with GC on in one byte, a feature bit in the engine header. Every byte of machine code is equal.
- Speed and memory do not change. Every on/off difference sits inside the machine's run-to-run spread.

One thing does change: the module cache. A `.cwasm` made by a GC-on engine is refused by a GC-off engine, so the first GC-off call on an old cache compiles again (about 26 s per binary), silently. The reverse direction loads.

## 1. The probe's diff

The pin moves to 51, and one environment variable turns GC off. The judge's own guest driver mirrors the runner's engine, so it gets the same switch; otherwise most checks would not see the change.

```
$ git diff --stat
 pyproject.toml                   |  2 +-
 src/wasi_python/_engines.py      |  4 +++-
 src/wasi_python/_wasmtime_ffi.py |  2 +-
 tests/harness/files.py           |  5 +++++
 tests/harness/guest.py           |  2 ++
 uv.lock                          | 28 ++++++++++++++--------------
```

- `pyproject.toml`, `PIN` in `_wasmtime_ffi.py` and the import error's text in `_engines.py`: `wasmtime>=50,<51` becomes `wasmtime>=51,<52`. `uv sync` installed wasmtime 51.0.0.
- `src/wasi_python/_engines.py`, in `_engine()`, after `cfg.epoch_interruption = True`:

  ```python
  if os.environ.get("WASI_PYTHON_PROBE_GC") == "off":  # probe only, never lands
      cfg.wasm_gc = False
  ```

- The same two lines in `tests/harness/guest.py` (`engine()`), and in the two engines of `tests/harness/files.py` (`Mounted`, `Counted`), with `import os`.

No check, golden output, gap, upstream allowance or progress file was edited. The unit rows that hold the pin at 50 were left as they are; they fail the same way in both runs.

## 2. The judge

The full fast tier did not fit the machine. `uv run pytest -m "not slow" -n 3` collected 4,998 items, reached 12% in 11 minutes, and then the kernel killed a worker for memory (4.1 GiB resident, three workers on 15 GiB); the run ended with "worker gw0 crashed" (EXECUTED). So the comparison is narrowed to what drives a guest or the runner: all of `tests/checks/` and the unit files of the runner, sessions, snapshots, tools, the CLI, the driver and wasmtime (2,290 items).

```
uv run pytest -m "not slow" -n 2 -p no:cacheprovider tests/checks tests/unit/test_runner_*.py \
  tests/unit/test_snapshot.py tests/unit/test_lifecycles.py tests/unit/test_tools.py \
  tests/unit/test_async_tools.py tests/unit/test_wasmtime_ffi.py tests/unit/test_cli.py \
  tests/unit/test_guest.py tests/unit/test_inline_sessions.py tests/unit/test_home.py \
  tests/unit/test_results.py tests/unit/test_rust_ids.py
```

Run once as it is, and once with `WASI_PYTHON_PROBE_GC=off` (EXECUTED). Each `build/progress/latest.json` was kept and compared with `tests/harness/sameness.py` and by a direct check-by-check diff.

| | GC on | GC off |
|---|---|---|
| pytest | 10 failed, 2,200 passed, 80 skipped | 12 failed, 2,198 passed, 80 skipped |
| v1 checks: pass / blocked / fail | 1,075 / 63 / 7 | 1,075 / 63 / 7 |
| checks whose status differs | | 0 |
| checks with a fuel metric | 437 | 437 |
| fuel exactly equal | | 430 |
| `bytes` metrics equal | | 3 of 3 |
| unit suite (records) | 1,125 of 1,145 | 1,123 of 1,145 |

- **The seven failing checks are the same in both runs**, and none is about wasm: two pin rows that still name 50 (`test_the_builds_wasmtime_is_the_runners_line`, `test_a_plain_install_brings_wasmtime`), two that quote the pin in an error message, two that skip because the container runs as root, and one tool-construction row (`a partial __init__`) that fails on the host side.
- **The two extra failures under GC off** are `tests/unit/test_runner_calls.py::test_the_runner_states_its_wasm_stack` and `::test_the_guest_driver_makes_the_runners_engine`. Each asserts the exact list of settings made on the engine's `Config`, and the probe adds `('wasm_gc', False)` to it. A real change would update those two rows. They do not measure the guest.
- **The seven fuel differences are not the GC.** They are in checkpoint and results checks, and are 17 to 34 instructions in 1.6 million to 263 million (at most 0.0016%). Those checks were run twice more in each mode, interleaved (`build/run-noisy.sh`). In those runs GC off gave the same fuel as GC on, and `test_a_checkpoint_of_a_fork_holds_both_turns` moved between 1,600,498 and 1,600,524 in both modes. It is a residual from where a check runs, not from the engine.
- **The fuel facts** (`facts` with fuel in them; recorded, never ratcheted) differ between the two records. They also differ between two GC-on runs, by as much: `test_a_snapshot_runs_like_a_fresh_run`'s `restored_fuel` was 27,764,237, 27,762,530 and 27,718,419 with GC on, and 27,611,477, 27,771,139 and 27,637,123 with GC off. One fact looked different (`test_a_frames_head_is_a_turns_value_as_text_and_html`). Run five more times in each mode, alone, it took the same three values, 18,701,072, 18,714,647 and 18,725,856, in both.
- **The judge's own times** were 584 s (on) and 810 s (off). These are not a benchmark. The judge keeps one runner cache, `build/cwasm-cache`, and the GC-on run had filled it. In the GC-off run every one of its four entries was refused and compiled again (their times on disk show the rewrite between the run's fourth and seventh minutes). The 16-check control run took 18.7 s and 17.8 s with GC on, and 18.6 s and 17.6 s with GC off.

## 3. The paths that use exceptions

Twelve guest programs, each run on both binaries, use wasm exceptions or end in a trap (`scratchpad/probe/paths.py`, the same programs in `paths_det.py`):

| program | what it does | result (all four runs) |
|---|---|---|
| `cxx_kiwisolver` | C++ throw: kiwisolver `UnsatisfiableConstraint` | caught |
| `cxx_matplotlib_dpi` | C++ throw: `RendererAgg(10, 10, -1)` | `ValueError: dpi must be positive` |
| `pandas_parse_error` | pandas C tokenizer error | `ParserError` |
| `longjmp_qhull` | qhull `longjmp`: `ConvexHull` of collinear points | `QhullError QH6154` |
| `longjmp_tri` | qhull `longjmp` through matplotlib's `Triangulation` | `RuntimeError: Error in qhull Delaunay` |
| `longjmp_brentq_cb` | a `KeyError` raised in a `brentq` callback | `KeyError` caught |
| `rust_panic` | 100 panics through PyO3 | 100 `pyo3_runtime.PanicException`, then orjson works |
| `orjson_error` | four orjson decode and encode errors | the same four errors |
| `pydantic_validation` | a `ValidationError` with two errors, then a valid model | the same |
| `recursion` | Python recursion at the default limit | `RecursionError`, limit 1000 |
| `recursion_deep_limit` | the limit at 10**6 | the trap `stack overflow` |
| `c_panic_trap` | a panic in a C entry point (`_rust_probe.panic_in_c`) | the trap `unreachable`, the panic message on stderr |

**Through the judge's driver** (`harness.guest.run`, which seeds entropy and steps the clocks so fuel repeats), each program ran on both binaries twice with GC on and twice with GC off (EXECUTED). All 24 results are the same in the four runs: exit code, trap, stdout, stderr's tail and fuel, to the instruction. Two examples: `cxx_matplotlib_dpi` on `python.wasm` spent 8,225,471,154 instructions every time, `longjmp_qhull` 3,918,886,607.

**Through the public API** (`wasi_python.run`, `root=True`, a fuel cap and no deadline), the same programs ran twice in each mode, interleaved, each mode with its own cache folder (EXECUTED). Outputs and traps are the same in all four runs. Fuel is not exact here, in either mode: the runner gives the guest the host's entropy, so a fresh call's hash seed differs. `pandas_parse_error` on the plain binary spent 5,075,415,296 and 5,074,041,984 with GC on, and 5,072,010,134 and 5,074,114,793 with GC off. The spread is within 0.1% and the same in both modes.

**A session and the snapshot paths** ran the same way. The session imports pandas and numpy, has a turn that panics uncaught (`PanicException`, the session goes on), a `1/0` turn, a turn that reads the frame again, then `checkpoint()`. A second session starts from that checkpoint and reads the frame. Then `make_package_snapshot(["pandas"])` makes an image, and a `run` starts from it. Every step gave the same output in all four runs, and each process counted `snapshots_made: 2`, `snapshots_restored: 2`.

## 4. The module cache

The cache's file name is `<digest>-wasmtime<version>-<fuel|plain>.cwasm`. It does not carry the GC setting (EXECUTED, `src/wasi_python/_engines.py`, `_module_miss`).

Directly through wasmtime (`scratchpad/probe/cachecompat.py`), for both binaries and both engines (EXECUTED):

- A `.cwasm` serialized with GC on, deserialized by a GC-off engine, is refused: `Module was compiled with support for WebAssembly feature `gc` but it is not enabled for the host`.
- A `.cwasm` serialized with GC off, deserialized by a GC-on engine, loads.
- The two files are the same size, and differ in exactly one byte, at offset 1122, inside the `.wasmtime.engine` section (offset 0x40, 0x425 bytes): 0xAF with GC on, 0x8F with GC off, one feature bit. `.text` and every other section are byte-identical (`cmp -l`, `readelf -S`; on the plain snapshot binary and on both fuel binaries).

Through the runner (`scratchpad/probe/cacheflow.py`, one fresh process per step, one cache folder; EXECUTED):

| step | compiled | loaded | written | warning | file's SHA-256 after |
|---|---|---|---|---|---|
| GC on, empty cache | 1 | 0 | 1 | none | a15d13ca1ce2… |
| GC off | 1 | 0 | 1 | none | d80cde5c9a1c… |
| GC on | 0 | 1 | 0 | none | d80cde5c9a1c… |
| GC off | 0 | 1 | 0 | none | d80cde5c9a1c… |

Started from an empty cache with GC off instead, the GC-off entry is written once and both modes load it from then on.

So the runner does not crash or misbehave. `_load` catches the `WasmtimeError`, compiles in the process and replaces the file, as it does for any stale entry. The cost is one silent compile per binary and engine kind, about 26 s each, the first time a GC-off runner meets a cache a GC-on runner wrote. After that the cache holds the GC-off entry, which both kinds of runner load. A shared cache does not flip back and forth (INFERRED from the table).

The cache entry's size is the same on and off (EXECUTED):

| entry | GC on | GC off |
|---|---|---|
| `python.wasm`, plain | 304,281,104 B | 304,281,104 B |
| `python-snapshot.wasm`, plain | 317,597,048 B | 317,597,048 B |
| `python.wasm`, fuel | 365,743,096 B | 365,743,096 B |
| `python-snapshot.wasm`, fuel | 379,059,032 B | 379,059,032 B |

## 5. A module with GC types

With GC off, a module that declares a GC type does not compile (EXECUTED, `wasmtime.Module(engine, wat2wasm(...))`). The text a user sees:

| module | error |
|---|---|
| `(module (type (struct)))` | `failed to parse WebAssembly module` / `Caused by: struct indexed types not supported without the gc feature (at offset 0xb)` |
| `(module (type (array i32)))` | `... array indexed types not supported without the gc feature (at offset 0xb)` |
| `(module (func (result anyref) ref.null any))` | `... heap types not supported without the gc feature (at offset 0xb)` |

With wasmtime 51's defaults (GC on), `(module (type (struct)))` compiles. The runner only compiles its own two binaries, which have no GC types, so a user would see this only by giving the runner's engine a module of their own (INFERRED).

## 6. Performance

All numbers are wall clock, EXECUTED. Each trial is a fresh process. On and off run in pairs, and the pair's order flips every trial, so drift in the machine falls on both. **Noise** here means a difference smaller than one mode's own min-to-max spread, with off faster in about as many pairs as on. Every row below is noise by that rule.

**Compile time**, no cache, the runner's plain engine (`compile_trial.py`, 10 pairs, both binaries per process):

| binary | GC on, median (min–max) | GC off, median (min–max) | median of off/on per pair | pairs where off was slower |
|---|---|---|---|---|
| `python.wasm` | 26.20 s (25.26–29.43) | 26.96 s (25.78–28.42) | 1.017 | 6/10 |
| `python-snapshot.wasm` | 27.31 s (25.43–28.41) | 26.88 s (25.62–29.04) | 1.009 | 5/10 |

**A call with a warm cache**, in a fresh process (`perf_trial.py`, 20 pairs). `cold` is the process's first `run(["-c", "print(1)"])`: wasmtime-py loads, the `.cwasm` is read and the call runs. The others are later calls in the same process, each a fresh instance of the snapshot binary.

| measure | GC on, median (min–max) | GC off, median (min–max) | median of off/on | off slower |
|---|---|---|---|---|
| cold `print(1)` | 446 ms (374–573) | 448 ms (391–554) | 1.008 | 10/20 |
| `import numpy, pandas` and a groupby | 1,548 ms (1,289–2,344) | 1,448 ms (1,267–2,514) | 0.949 | 4/20 |
| 10,000 caught C++ exceptions (kiwisolver) | 112 ms (84–141) | 90 ms (78–122) | 0.861 | 6/20 |
| 10,000 pydantic `ValidationError`s | 652 ms (491–879) | 608 ms (468–827) | 0.967 | 9/20 |
| 10,000 Rust panics caught | 136 ms (83–186) | 106 ms (86–199) | 0.874 | 6/20 |
| 1,000 qhull `longjmp`s | 1,313 ms (982–1,791) | 1,273 ms (1,112–1,630) | 1.018 | 11/20 |
| peak RSS after the cold call | 87 MiB (87–88) | 87 MiB (86–88) | 1.000 | |
| peak RSS after the pandas call | 177 MiB (176–178) | 177 MiB (176–178) | 1.000 | |

Three rows leaned towards GC off, so they were measured again with less noise (`perf_min.py`, 10 pairs). Each process makes one warm-up call, then runs each workload five times and keeps the fastest:

| workload, fastest of 5 | GC on, median (min–max) | GC off, median (min–max) | median of off/on | off slower |
|---|---|---|---|---|
| `print(1)` | 17 ms (14–25) | 19 ms (15–29) | 0.973 | 5/10 |
| numpy, pandas and a groupby | 1,389 ms (1,277–1,481) | 1,327 ms (1,240–1,552) | 0.988 | 3/10 |
| 10,000 C++ exceptions | 81 ms (77–91) | 83 ms (78–109) | 1.045 | 7/10 |
| 10,000 `ValidationError`s | 530 ms (488–600) | 545 ms (501–697) | 1.002 | 5/10 |
| 10,000 Rust panics | 91 ms (70–145) | 89 ms (70–112) | 0.963 | 5/10 |

With the noise taken down, the lean is gone. Every median is within 5% of 1, and the signs split. That matches the compiled code being byte-identical (section 4): the switch has no code to make faster or slower (INFERRED).

## 7. Other things this probe saw

These are the same with GC on and off. They are recorded because the probe found them, not because the switch causes them.

- **A C++ exception that escapes ends the call with an unclear trap.** A kiwisolver `Solver` that is reused keeps growing with each failed `addConstraint`. Past about 5,500 failures at the default 1 GiB (about 2,500 at 256 MiB, 11,500 at 3 GiB) the call ends with `trapped='error while executing at wasm backtrace:'`, no stderr, and no named cause. The judge's driver names it: `trap_cause='thrown Wasm exception'`. Most likely a `std::bad_alloc` escapes to the host when the memory limit is reached (INFERRED). A fresh solver for each try ran 20,000 failures cleanly. 20,000 Rust panics and 20,000 qhull `longjmp`s ran cleanly too. The runner names `stack overflow`, `unreachable` and running out of fuel, but not an uncaught wasm exception.
- **The runner's cache does not record the engine's features** (section 4). Any future engine setting that changes the feature bits will have the same one-time silent recompile.

## 8. The commands

All in the worktree, with `WASI_PYTHON_ARTIFACTS` set to the 0.1.5 set. Logs and records are under `build/`. The probe scripts are in the session's scratchpad (`probe/`).

```
uv sync                                              # wasmtime 51.0.0
uv run python probe/cachecompat.py <artifacts>       # build/cachecompat.log
uv run pytest -m "not slow" -n 2 -p no:cacheprovider <selection>   # build/judge-gc-on.log
WASI_PYTHON_PROBE_GC=off uv run pytest ... (the same)              # build/judge-gc-off.log
uv run python tests/harness/sameness.py build/latest-gc-on.json build/latest-gc-off.json
build/run-noisy.sh                                   # the 16 checks, on/off/on/off
build/run-paths.sh                                   # public API, build/paths-compare.txt
uv run python probe/paths_det.py tests <artifacts> build/detwork build/det-<m>-<i>.json   # build/det-compare.txt
build/run-perf.sh, build/run-perf2.sh, build/run-perf3.sh, build/run-perf4.sh            # build/perf-*.jsonl
build/run-after-perf.sh                              # build/cacheflow.jsonl
cmp -l <on>.cwasm <off>.cwasm; readelf -S -W <on>.cwasm
```

## In one line

On wasmtime 51, with the GC proposal off, the guest gives the same results and the same fuel, the machine code is byte-identical and the speed is the same; the only effect is a one-time silent recompile of `.cwasm` entries that a GC-on runner wrote.
