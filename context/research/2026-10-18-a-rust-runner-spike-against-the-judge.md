# A Rust runner spike against the judge

- **Status:** research, 2026-10-18. A time-boxed spike at the owner's request, recommended by
  `2026-10-18-a-rust-core-with-js-and-python-wrappers.md` (its §1.9, §1.10 and §2.6 step 1).
  It changes nothing: no code in `src/`, no specification, no pin. Written in a scratchpad and
  filed here by the lane; its evidence is the folder of the same name beside it.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: one session.
- **The question:** with the same wasmtime and the same `Config`, does a Rust runner give the
  same answers as the Python runner on the judge's guest jobs (exit code, stdout, stderr,
  written files, and above all exact fuel)? And what does a Rust core cost?
- **Stands on:** `AGENTS.md`; `context/constitution.md`; the assessment named above;
  `src/wasi_python/runner.py` (`_engine`, `_module`, `_instance`, `_drive`, `_fuel_used`);
  `tests/harness/guest.py`; `tests/harness/jobs.py`; `tests/checks/conftest.py`;
  `tests/checks/test_v1_3_data_stack.py`, `test_v1_3_matplotlib.py`;
  `context/research/2026-10-18-wasmtime-49-advisories.md`; the prior-art clone `wasmtime-v49`
  (tag v49.0.3), read only, for the API (`crates/c-api/src/{wasi,linker,config,trap,error}.rs`,
  `crates/wasi/src/{ctx,p1}.rs`, `crates/wasmtime/src/config.rs`). No line was copied.
- **Artifact set:** `build/sets/s-8eb9e35734deeb21` (frozen, read only): python 3.15.0, numpy
  2.5.2, pandas 3.0.6, matplotlib 3.11.2.
- **Evidence, beside this memo:** `comparison-table.txt` (every table below, in full);
  `compare.py`, `runner_compare.py`, `same_root.py`, `cwasm.py`, `make_table.py` (the drivers);
  `results/` (the raw JSON of every run); `spike/` (the spike's `Cargo.toml`, `Cargo.lock`,
  `deny.toml`, `src/main.rs`, and the manifests of its two variants); `logs/` (build logs and
  cargo-deny output). The spike's build tree is at `build/rust-spike/`, git-ignored.
- **Machine:** darwin-arm64, Apple M1 Pro, 10 cores, 32 GiB; rustc 1.97.1; cargo-deny 0.19.0;
  the main tree's uv environment (CPython 3.14.2, wasmtime-py 49.0.0).

Labels: EXECUTED means run here; READ means read from a file, cited; INFERRED means the
researcher's reasoning.

## The short version

1. **Fuel is equal.** A Rust runner on the `wasmtime` and `wasmtime-wasi` crates gives the same
   fuel as the judge's wasmtime-py driver, to the instruction, when both embed the same
   wasmtime. Outputs are equal everywhere: 16 of 16 judge jobs, 8 of 8 product-runner jobs.
2. **The one difference is the wasmtime version, not the language.** wasmtime-py 49.0.0 embeds
   wasmtime **49.0.0**, not the 49.0.3 the project pins for its CLI. On the 49.0.3 crates, the
   matplotlib job spends 231,562 more instructions (3.1e-5, steady). On the 49.0.0 crates the
   gap vanishes. It sits in matplotlib's font-cache build. Which WASI call answers differently
   was not found (two attempts; §5).
3. **What looks like disagreement is the guest's own noise.** Five jobs vary by 17 to 391
   instructions from run to run, on both sides alike. Run on one shared root, the Python run
   and the Rust run agree exactly (22 of 24; the other 2 vary between two Rust runs too).
4. **The compiled module is byte-identical** once the Rust side names wasmtime-py's garbage
   collector. The crate's default features pick a different collector, so by default the Rust
   side refuses wasmtime-py's `.cwasm`.
5. **The cost is small for this fifth of the work:** 376 lines of Rust; a 13.9 MB binary (8.7 MB with lean features and LTO);
   189 crates in the binary; permissive licences that pass cargo-deny; a cold build of 88 s.

**Fuel-equality answer:** yes. Same wasmtime version and same `Config` give the same fuel, to
the instruction. A different wasmtime patch version is the only thing seen to move it.

## 1. What was built

### 1.1 The spike (EXECUTED)

`build/rust-spike/src/main.rs`, 376 lines, one binary, our own code. It reads a JSON batch on
stdin and runs each job in a fresh `Store` and instance. Per job it supports:

- folder grants in a given order, read-only or writable (`WasiCtxBuilder::preopened_dir` with
  `FsPerms::ReadOnly` or `ReadWrite`, the same call the C API makes: READ,
  `crates/c-api/src/wasi.rs:312-337`);
- the stdlib zip at `/usr/local/lib` and matplotlib's data beside it, both read-only, granted
  first, as `guest.py` and `runner.py` do;
- fuel metered from the end of instantiation (spec 008: an unmetered budget while it
  instantiates, then the job's budget), the memory cap (`StoreLimitsBuilder::memory_size`),
  and the epoch deadline (10 ms ticks from a ticker thread, `Trap::Interrupt` named
  "deadline");
- argv and env;
- stdout and stderr captured in memory (`MemoryOutputPipe`);
- the plain binary (`_initialize` then `run`) and the snapshot (`run`), chosen by exports as
  `guest.kind` does;
- an optional `.cwasm` cache (`Module::serialize`, `Module::deserialize_file`).

It has two host modes:

- **judge** answers `random_get` and `clock_time_get` from the judge's fixed streams
  (SHA-256 of a counter; a clock from 2026-01-01 stepping 1 µs), as `guest.py` does;
- **runner** leaves both to wasmtime's own WASI, as `runner.py` does.

`host::call` answers -1 ("no host") in both modes, as each Python driver does without a host.

### 1.2 The pins (EXECUTED, READ)

- The project pins the wasmtime **CLI at 49.0.3** (`downloads/SHA256SUMS`, three hosts).
- It pins **wasmtime-py at 49.0.0** (`uv.lock`: `wasmtime-49.0.0`; `pyproject.toml`:
  `wasmtime>=49,<50`). The judge records `"wasmtime": "49.0.0"` beside every fuel metric
  (`context/progress/accepted.json`).
- So the Python side runs **wasmtime 49.0.0**. The spike was built twice from one source:
  - **on 49.0.3**, as asked;
  - **on 49.0.0**, as the control (`spike/v49_0_0/Cargo.toml`).
- Crates come from crates.io only. `Cargo.lock` records each crate's SHA-256, and cargo
  verifies it on download (cargo-deny `sources ok`: no other registry, no git).

### 1.3 The drivers (EXECUTED)

- `compare.py` (judge mode) calls the judge's own driver, `tests/harness/guest.run`, read-only
  from the main tree. It builds the same layout for the Rust side as `guest.run` builds:
  the root with `usr/local/lib`, `lib/python315.zip` hard-linked, the job's files, and the
  grants in the same order (lib, mpl-data, root, extras), with the same argv and env.
  The Config is the judge's, `consume_fuel` only. Each job runs 3 times on each side.
- `runner_compare.py` (runner mode) calls `wasi_python.run` with `WASI_PYTHON_ARTIFACTS` set to
  the frozen set and its `.cwasm` cache under `build/rust-spike/work/`. The Rust side uses
  the runner's Config (`consume_fuel` when a budget is given, `epoch_interruption` always),
  base env, grant order, default memory cap (1 GiB) and default deadline (60 s). Each job
  runs 2 times on each side.
- `same_root.py` runs a job with `guest.run`, then the Rust spike twice on the very same root
  folder.
- `cwasm.py` compiles each module in wasmtime-py and in both Rust builds under one Config,
  hashes the `.cwasm`, and loads wasmtime-py's `.cwasm` in Rust.

## 2. The comparison

### 2.1 The sample (EXECUTED)

16 judge jobs (`compare.py`):

- `print('hello')` on the plain binary and on the snapshot;
- the golden jobs `numpy_csv`, `pandas_csv`, `numpy_random`, `compress`, `sqlite` (plain), and
  `callbacks`, `pandas_tz`, `plot_line` (snapshot). Each is staged as the checks stage it, and
  each output is checked against `tests/jobs/<job>.expected`;
- an exit code with stderr (`sys.exit(3)`), an uncaught `ZeroDivisionError`, argv and env;
- grants: list and read a read-only grant, a refused write there (`PermissionError`, errno
  63), a write to a writable grant;
- two fuel traps: one during start-up (budget 5e7), one in a `while True` (budget 1e9).

8 product-runner jobs (`runner_compare.py`): hello (twice, once with `PYTHONHASHSEED=0`), a
numpy sum, an exit code with stderr, the memory cap (`bytearray(300 << 20)` under 256 MiB),
the grants, and two deadline traps (`while True` with `deadline_s=1.0`, metered and not).

Writes are covered by `sqlite` (a database file), `plot_line` (a PNG) and the grants job.

### 2.2 Judge mode, Rust on 49.0.3 (EXECUTED, Table 1)

| job | outputs | golden | fuel equal on all 6 runs |
|---|---|---|---|
| hello (plain, snapshot) | same | n/a | yes, yes |
| numpy_csv, pandas_csv | same | yes | yes, yes |
| numpy_random, compress, sqlite, callbacks, pandas_tz | same | yes | no: noise on both sides (§2.4) |
| plot_line (snapshot) | same | yes | **no: Rust +231,562 every run** |
| exit 3 with stderr, ZeroDivisionError, argv/env, grants | same | n/a | yes |
| fuel trap at start-up, fuel trap in a loop | same ("out of fuel") | n/a | yes |

Outputs (exit code, trap, stdout, stderr, written files) equal on 16 of 16. Every golden job
matches its golden on both sides. Fuel equal on every run on 10 of 16.

### 2.3 Judge mode, Rust on 49.0.0, the control (EXECUTED, Tables 2a to 2c)

- Outputs equal on 16 of 16, and fuel equal on every run on 11 of 16.
- **plot_line:** Rust gave 7,559,512,583 three times. Python gave 7,559,512,583,
  7,559,512,515 and 7,559,512,583. The 231,562 gap is gone. **It came from the wasmtime
  version.**
- With the collector set to wasmtime-py's (drc, §3.1): outputs equal 16 of 16, and fuel is
  unchanged in kind (Table 2b).
- With `epoch_interruption` on, as the product runner's Config has it: 10 of 10 equal to the
  instruction (Table 2c). Epoch checks cost no fuel.

### 2.4 The noise is the guest's, not the runner's (EXECUTED, Table 4)

- **The pattern.** The five noisy jobs move in steps of 17 or 34 instructions (once 391,
  `compress`). They move as much between two Python runs as between Python and Rust. The
  judge's driver already says fuel "repeats to a few parts in ten million" (READ, `guest.py`
  docstring). The largest step seen, 391 in 3.9e9, is 1e-7.
- **The test.** `same_root.py` ran each noisy job with `guest.run`, then the Rust spike twice on
  the same root folder. Same files, same inodes, same times.
- **The result.** numpy_random, numpy_csv, pandas_csv, pandas_tz and callbacks gave the same
  count on all three runs in all four trials (20 of 20). compress matched in two trials. In the
  other two, the first Rust run differed and the second matched Python exactly.
- **INFERRED:** the guest reads host file metadata that changes between fresh roots (times, and
  for compress the times of files it has just written). Each runner sees it alike. It is not a
  runner difference.

### 2.5 Runner mode against `wasi_python.run` (EXECUTED, Table 3)

| job | outputs | how it ended (both) |
|---|---|---|
| hello, hello with `PYTHONHASHSEED=0`, numpy sum | same | exit 0 |
| exit 3 with stderr | same | exit 3 |
| memory cap 256 MiB, `bytearray(300 << 20)` | same (`MemoryError`) | exit 1 |
| read-only and writable grants | same | exit 0 |
| `while True`, `deadline_s=1.0`, unmetered | same | "deadline" |
| `while True`, `deadline_s=1.0`, metered | same | "deadline", fuel None on both |

- **Outputs.** Equal on 8 of 8.
- **Fuel.** With real random and clocks it cannot repeat. Across the four runs of a job it
  spread by 377 to 1,181 parts per million. The spread between two runs of one runner was as
  large as the spread between runners (Table 3).
- **Shadows.** The product runner forwards `fd_readdir` and `path_rename` through spec 048's
  guard linker. The spike calls wasmtime's own, which carry the 49.0.3 fixes. Outputs did not
  differ.

### 2.6 Summary

- **Judge jobs: 16.** Outputs exactly equal on 16 of 16.
- **Fuel exactly equal on every run: 10 of 16 on 49.0.3, 11 of 16 on 49.0.0.**
- **The rest.** On 49.0.0, every remaining job is the guest's own noise (§2.4). On 49.0.3, the
  same holds except plot_line, whose gap is the wasmtime version.
- **Product-runner jobs: 8.** Outputs exactly equal on 8 of 8, including both deadline traps
  and the memory cap.

## 3. The compiled module

### 3.1 The `.cwasm` is byte-identical once the collector matches (EXECUTED, Table 5)

- **Default features.** The spike, on the crate's default features, compiled `.cwasm` files of
  exactly wasmtime-py's size but different bytes. Loading wasmtime-py's file failed:
  "module was compiled for the deferred reference-counting collector but the host is
  configured to use the copying collector".
- **The cause.** The `wasmtime` crate's default features include `gc-copying`, and that
  changes the default collector. wasmtime-py's C library uses deferred reference counting
  (drc). The guest uses no GC types, so fuel did not change (Table 2b against Table 2a).
- **Collector set to drc.** With `Config::collector(Collector::DeferredReferenceCounting)`,
  Rust 49.0.0 wrote byte-identical `.cwasm` files for all four cases (plain and snapshot,
  judge Config and runner Config). wasmtime-py is itself repeatable: two compiles give the
  same SHA-256. Rust then loaded wasmtime-py's `.cwasm` and ran on it: hello, fuel
  166,604,192, load 15 ms.
- **On 49.0.3.** Its `.cwasm` files are 81,920 to 98,304 bytes larger: the compiled code
  differs from 49.0.0's.
- **The lean build** (§4.1, drc set) gave the same fuel for hello (166,604,192). It still
  refused wasmtime-py's `.cwasm`: "Module was compiled with concurrency support but it is not
  enabled for the host". So crate features reach the `.cwasm` header too, not only Config
  calls. Fuel did not move.

### 3.2 A trap in the cache key (READ, EXECUTED)

- **What wasmtime checks.** In wasmtime 49, a `.cwasm` header checks only the **major**
  version: `ModuleVersionStrategy::WasmtimeVersion` yields `CARGO_PKG_VERSION_MAJOR`
  (`crates/wasmtime/src/config.rs:119`).
- **What happened.** The 49.0.3 spike loaded wasmtime-py's 49.0.0 `.cwasm` and ran it, without
  error.
- **Why it matters.** A cache keyed by major version would run 49.0.0's machine code under
  49.0.3 and keep none of 49.0.1 to 49.0.3's code-generation fixes. `runner.py` keys its cache
  by the full version (`wasmtime{_wasmtime_version()}`, READ), so it is safe. A Rust core must
  do the same.

### 3.3 Compile cost (EXECUTED, benchmark facts)

- **Per module.** Compiling one module took 4.7 to 6.1 s in wasmtime-py and 5.0 to 5.8 s in
  Rust (one outlier on each side: 9.4 s and 10.2 s). This is the same Cranelift doing the
  same work.
- **Loading.** A `.cwasm` loads in 14 to 15 ms in Rust.
- **Sizes.** The `.cwasm` is 99 MB (plain) to 143 MB (snapshot, runner Config).

## 4. What a Rust core costs

### 4.1 Size and crates (EXECUTED)

| build | stripped binary | notes |
|---|---|---|
| spike, wasmtime 49.0.3, default features | 13,912,672 B | release, `strip = true` |
| spike, wasmtime 49.0.0, default features | 13,945,424 B | the control |
| spike, 49.0.3, lean features, LTO | 8,714,672 B | `cranelift, runtime, std, parallel-compilation, gc, gc-drc, addr2line, demangle`; `lto = true`, `codegen-units = 1` |
| for scale: wasmtime-py's `_libwasmtime.dylib` | 25,460,800 B | inside a macOS arm64 wheel of 8,438,112 B (`uv.lock`) |

- **The lock.** `Cargo.lock` names **246 crates** besides the spike, for all platforms.
- **In the binary** (`cargo tree -e normal`): **189 crates** on aarch64-apple-darwin, 193 on
  x86_64 Linux, 202 on x86_64 Windows.
- **The lean build:** 162 crates on aarch64-apple-darwin (205 in its lock).
- **For scale.** wasmtime's own workspace lock names 581 (the assessment, §1.3).

### 4.2 Licences (EXECUTED, `cargo deny list`, `cargo deny check`)

- **The licences.** Every crate is permissive or offers a permissive choice: Apache-2.0,
  Apache-2.0 WITH LLVM-exception, MIT, BSD-2/3-Clause, Unicode-3.0, Zlib, Unlicense.
- **Where to look:**
  - `ittapi` is GPL-2.0-only OR BSD-3-Clause. It comes from wasmtime's default `profiling`
    feature, on x86 Linux and Windows only, and is not in the macOS tree.
  - `r-efi` is MIT OR Apache-2.0 OR LGPL-2.1-or-later. It is for UEFI only, and is not in the
    tree here.
  - `zstd-sys` (BSD-3-Clause) comes from the `cache` feature.
  - `encoding_rs` is (Apache-2.0 OR MIT) AND BSD-3-Clause.
- **cargo-deny on the 49.0.3 spike**, allowing those nine licence expressions:
  `advisories ok, bans ok, licenses ok, sources ok`. There were 19 duplicate-version warnings
  (windows-sys and its targets, syn, thiserror, hashbrown, wasm-encoder and others). The
  advisory database was fetched fresh, 2026-10-18.
- **cargo-deny on the 49.0.0 control:** `advisories FAILED`, with **23 RustSec vulnerability
  records** against the wasmtime 49.0.0 crates (RUSTSEC-2026-0315 onward). Among them:
  - the `fd_readdir` padding leak;
  - the rename sandbox escape;
  - the `call_ref` fuel accounting.

  All 23 are cleared at 49.0.3. **INFERRED:** they name the code wasmtime-py 49.0.0 carries
  today. That is the lag the advisories memo and spec 048 already describe (28 GHSA records
  there; cargo-deny counts the 23 that reach this crate graph).
- **What would ship.** A release binary would ship about 190 licence notices (§4.12 of the
  constitution). Today wasmtime-py ships them.

### 4.3 Build time (EXECUTED, benchmark facts)

- **Cold**, 49.0.3, empty `target/`, 87 crates downloaded: **87.9 s** wall (508.8 s user),
  201 compile units.
- **Warm**, `src/main.rs` touched: **4.5 s**.
- **The 49.0.0 control, cold:** 109.1 s, run beside a guest job, so not clean.
- **The lean LTO build, cold:** 246.9 s wall (383.2 s user). One codegen unit with LTO is slow to link, and part of it ran beside the probe jobs.

## 5. The plot_line gap, as far as it went

- **Probe 1 (EXECUTED):** 20 `os.listdir` calls over matplotlib's font folder, and 2,000
  `os.stat` calls. Both were equal on 49.0.3 and wasmtime-py, to the instruction (Table 6). So
  `fd_readdir` and `path_filestat_get` alone do not explain it, although 49.0.2 and 49.0.3
  changed `fd_readdir` (spec 048).
- **Probe 2 (EXECUTED):** `import matplotlib.pyplot` with a fresh `MPLCONFIGDIR` costs
  **+203,016** on 49.0.3. Drawing one figure adds about 28,600 more. The total, +231,600,
  matches plot_line's gap. So the gap is in matplotlib's font-cache build and font loading.
- **Where it stopped:** two attempts, and per the two-strike rule no more. **INFERRED:** one of
  49.0.1 to 49.0.3's WASI changes makes some call answer differently (a timestamp, a file type,
  an errno). The guest then takes a slightly longer path. The output is unchanged. The
  candidates are in the advisories memo's §2.
- **What it means for the judge.** When the project's wasmtime-py pin moves past 49.0.0, the
  matplotlib checks' fuel should move by about 3e-5. That is inside the ratchet's 1e-4
  tolerance (`scoreboard.py:31`, per the assessment).

## 6. What the skipped pieces would take in Rust (INFERRED, brief)

- **The door (`host::call`) and the tool protocol's wire.** A `func_wrap` that reads the
  request from guest memory, calls the embedder, and writes the reply through the guest's
  `host_alloc` export. Rust can call that export from inside the host function through
  `Caller`. The embedder call is a PyO3 call under the GIL, or a napi-rs
  `ThreadsafeFunction` awaited on the worker. About 100 lines in the core. The tool layer
  (schema, gate, budgets, async tools) stays in each host language, as the assessment says.
- **Mounts and providers.** The hard part. wasmtime-wasi's p1 functions cannot be called one by
  one from outside (READ, `p1.rs:846-870`). A shadow must either forward through a trampoline
  as `mounts.py` does, or reimplement the call over the host's own descriptor table. Staging,
  write-back at every ending, and the parity table come over unchanged in kind. This is
  `mounts.py`'s 2,054 lines again, not a wrapper.
- **Output caps.** `MemoryOutputPipe` errors when full. The runner instead drops bytes and
  names the stream. That needs a small custom `StdoutStream`, about 40 lines.
- **Async.** No wasmtime async is needed. Run each guest on a worker thread, and hand back a
  Python `Future` or a JS `Promise` (napi `AsyncTask`).
- **Cancel and Ctrl-C.** `Store::epoch_deadline_callback` with the store's own data replaces
  spec 011's process-wide ctypes table. One ticker thread per engine, and a cancel flag the
  callback reads. Ctrl-C stays the host language's job; the core only exposes cancel.
  Spec 015's measured promises are re-proven.
- **Sessions (spec 055).** A `Store` kept in a struct behind a mutex (`Store<T>` is `Send`), the
  instance kept, and `run` called once per turn, with a reaper thread. It is straightforward
  in Rust, but the specification is written against the Python runner and must be re-specified.
- **The `.cwasm` cache.** `serialize` and `deserialize_file` are there. The cache must be keyed
  by the full wasmtime version (§3.2), must keep `runner.py`'s private-directory rule, and
  must name the collector explicitly so the Config is wasmtime-py's (§3.1).

## 7. What this changes in the assessment

- **§1.9 moves from "likely but unproven" to measured.** Equal outputs, and fuel equal to the
  instruction, whenever both runners embed the same wasmtime. **INFERRED:** the assessment's
  step 2 conformance checks (a Node package compared with the Python runner on `fuel_used`)
  are sound, on two conditions:
  - both sides pin the same wasmtime patch version, or the checks allow the ratchet's 1e-4;
  - the checks either use the judge's host-supplied random and clock, or a shared root,
    because on fresh roots the guest's own noise is about 1e-7.
- **§1.10's "easy fifth" is confirmed easy.** It took 376 lines and one session. Fuel, grants,
  limits and deadlines carry over without surprise.
- **One new caution for any Rust core:** the crate's default features do not make wasmtime-py's
  Config. The collector differs, and the CLI, the C API and the crate each choose their own
  defaults. Trimming features changes the `.cwasm` header again (concurrency support). Name
  every Config setting that reaches the `.cwasm`, and never share a cache across differently
  built runtimes. None of this moved fuel.
- **Nothing here changes the verdict** ("adopt in part, after 0.1.0"). The spike removes the
  technical doubt about a Node package on a Rust core. It does not touch the cost the verdict
  rests on: mounts, the door's threading, cancel, sessions, and a native release matrix.

## 8. Where it stopped

- **Not identified:** the WASI call behind the plot_line gap on 49.0.3 (two attempts, §5).
- **Only on darwin-arm64.** Linux and Windows, where instantiation charges per byte when it
  cannot map the image (READ, `runner.py`'s comment on `UNMETERED`), were not run. Fuel is
  metered after instantiation, so equality is expected there too (INFERRED).
- **Untested:** the Rust side's trap words for traps other than fuel and deadline. No guest job
  in the sample raised one.
- **The upstream suites** (numpy and pandas tests, 10^11 instructions each) were not run
  through the spike.
- **Not built:** a PyO3 or napi-rs binding. The spike is a plain binary driven over JSON.

## One line

With the same wasmtime and the same Config, a Rust runner matches the judge's wasmtime-py
driver on every output and on fuel to the instruction (16 of 16 jobs; the only fuel gap,
3e-5 on matplotlib, follows the 49.0.0-versus-49.0.3 version and not the language). The
`.cwasm` is byte-identical once the collector is named, and the easy fifth of a Rust core costs
376 lines, a 14 MB binary and 189 permissively licensed crates.
