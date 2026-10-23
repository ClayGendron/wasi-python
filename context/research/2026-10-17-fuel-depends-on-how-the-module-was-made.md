# Fuel depends on how the module was made

- **Status:** executed, 2026-10-17. The cause is found; a runner change is recommended, not made.
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5), from the spec 005 build review's finding 3 (`../reviews/005-the-3-15-line-2026-10-17.md`). The experiment and the source reading: a research agent (Claude Opus 5.5), 2026-10-17.
- **Feeds:** the runner's `fuel_used` contract (README, "Running it"); any later use of fuel as a price or a budget (the principal engineer's memo, direction "fuel-priced execution"); the planned deterministic replay (two runs of one program report the same fuel).
- **Blocks:** nothing today. The judge's driver (`tests/harness/guest.py`) always compiles in its own process, so the judge's fuel figures are consistent on one machine; the one runner check that records fuel (`test_a_cpp_exception_reaches_python`) passes `cache_dir=False`. See "The judge" below for what this means across machines.
- **Evidence:** `2026-10-17-fuel-experiment/` (scripts and their outputs). Source read in a shallow clone of wasmtime at tag `v49.0.3` (`../prior_art/wasmtime-v49`, commit f96eaba).

## The finding (EXECUTED: wasmtime-py 49.0.0, the 3.15 artifacts, `wasi_python.run` with
`fuel=10**12`, each line a fresh process; the cache directory private, as the runner requires)

| binary | program | compiled in the process | loaded from the `.cwasm` | difference |
|---|---|---|---|---|
| snapshot | `pass` | 124,130,225 | 81,823,271 | −42.3M |
| snapshot | `sum(range(10**6))` | 1,014,156,397 | 971,797,080 | −42.4M |
| plain | `pass` | 246,595,679 | 241,639,813 | −5.0M |
| plain | `sum(range(10**6))` | 1,143,525,783 | 1,138,165,581 | −5.4M |

- The difference is about constant per binary, not proportional to the work, so it sits in start-up or shutdown, not in the program's own loop (INFERRED, then confirmed below).
- The guest's output is the same either way; the `.cwasm` bytes are identical across runs (the review, EXECUTED).
- The 3.14 artifacts show the same: snapshot `-c pass` 117.6M compiled, 76.8M loaded (the review, EXECUTED).

## The question

Why does a deserialized module consume less fuel than the same module compiled in the process? Which count is right? Can the runner make `fuel_used` the same however the module was obtained, and at what cost?

## The cause

The difference is the fuel wasmtime charges for copying the module's initial memory image into the new instance. It is charged only when the image cannot be mapped copy-on-write. On macOS that is exactly when the module did not come from a file.

### What wasmtime 49 does at instantiation (READ, `wasmtime-v49`)

- A *module startup function* is compiled code that wasmtime generates for each module. It runs at instantiation. It evaluates constant expressions, fills tables and copies data segments into linear memory (`crates/cranelift/src/func_environ.rs`, `translate_module_startup`).
- It is compiled like guest code, so it is fuel-metered. The data copy is modelled as a `memory.init`. It is charged `memory_init_per_byte` fuel per byte copied (`module_initialize_memory_segment`). The default is 1 per byte (`crates/environ/src/tunables.rs`, `VariableOperatorCost::new`). A function's entry costs 1 more.
- With `memory_init_cow` on (the default), all data segments of a memory become one *static image*: a page-aligned block from the lowest to the highest initialised byte, zero gaps included. The host page decides the alignment (16 KiB on Apple silicon).
- Before the startup function runs, the host checks each memory. If the memory was already mapped from the image (copy-on-write), the host clears that segment's pointer, and the startup function skips the copy (`crates/wasmtime/src/runtime/vm/instance.rs`, near "the half of the strategy of implementing memory-init-cow data segments"). If no memory needs initialising, the startup function is not called at all (`ModuleStartup::IfMemoriesNeedInit`).
- Whether a copy-on-write image exists depends on where the module's bytes live (`crates/wasmtime/src/runtime/vm/cow.rs`, `MemoryImage::new`):
  - The module was memory-mapped from a file (`Module::deserialize_file`): the file is the image's source. Unix supports this. No copy, no fuel.
  - Otherwise `MemoryImageSource::from_data` is asked. On Linux it makes a `memfd`, so the image is still mapped. On macOS and every other non-Linux Unix it returns `None` (`sys/unix/vm.rs`). On Windows both `from_file` and `from_data` return `None` (`sys/windows/vm.rs`). With `None`, the startup function copies, and charges.

### The experiment (EXECUTED, macOS arm64, one engine with `consume_fuel` and
`epoch_interruption`, the clock and random answered by the script as the judge does)

Tiny hand-written modules (`image_size.py`, `image_extent.py`): fuel spent by instantiation alone.

| module | compiled | `deserialize` (bytes) | `deserialize_file` |
|---|---|---|---|
| 1 page, no data | 0 | 0 | 0 |
| 1 segment of 11 bytes at 16 | 16,385 | 16,385 | 0 |
| 1 segment of 20,000 bytes at 16 | 32,769 | 32,769 | 0 |
| 1 byte at 0 and 1 byte at 6,000,000 | 6,012,929 | 6,012,929 | 0 |
| 11 bytes, `memory_init_cow` off | 13 | 13 | 13 |

- With copy-on-write on, the charge is the image's size in bytes plus 1: one, two or 367 host pages of 16,384 bytes. It counts the zero gap between segments.
- With copy-on-write off, every path copies segment by segment and is charged alike: the segment's bytes, plus 1 for its `i32.const` offset, plus 1 for the function entry.

The real artifacts (`artifacts.py`): fuel after `instantiate`, and fuel spent after it.

| binary | program | how | instantiate | after instantiate |
|---|---|---|---|---|
| snapshot | `pass` | compiled, or `deserialize` from bytes | 42,352,641 | 81,947,194 |
| snapshot | `pass` | `deserialize_file` | 0 | 81,947,194 |
| snapshot | `print(sum(range(10**6)))` | compiled, or from bytes | 42,352,641 | 972,080,303 |
| snapshot | `print(sum(range(10**6)))` | `deserialize_file` | 0 | 972,080,303 |
| plain | `pass` | compiled, or from bytes | 5,046,273 | 241,447,265 |
| plain | `pass` | `deserialize_file` | 0 | 241,447,265 |
| snapshot | `pass`, `memory_init_cow` off | every way | 38,648,305 | 81,947,194 |

- The snapshot has 10,000 active data segments, 38,638,304 bytes, spanning 42,352,640 bytes once page-aligned. The instantiation charge is that span plus 1, exactly.
- The plain reactor's image spans 5,046,272 bytes. Its charge is that plus 1, exactly.
- With copy-on-write off: 38,638,304 segment bytes + 10,000 offsets + 1 entry = 38,648,305.
- Everything after instantiation is identical to the instruction in every case. The guest's own count never differed.
- Neither artifact has a start section, so the startup function runs no guest code.

What does not matter (EXECUTED, `matrix.py`, the one-segment module): `epoch_interruption` on or off; `cranelift_opt_level` none, speed or speed-and-size; `parallel_compilation` off; `wasm_exceptions` on; `Module.from_file`; deserialising into a second engine; wasmtime's own `Config.cache` on a cache hit (it still loads bytes, so it still copies and is charged).

### Which number is right

- Both follow wasmtime's rules. Neither is a miscount.
- The guest's own instructions are the same either way: 81,947,194 for snapshot `pass`.
- The extra 42.35M is not an instruction the guest executed. It is wasmtime's way of filling memory when it cannot map it. It depends on the operating system and on how the module was obtained, not on the program.
- So the loaded figure (81.8M through the runner) is the one that counts only what the guest ran. The compiled figure adds a host-dependent cost of instantiation (INFERRED from the above).
- Expected by platform, from the source (INFERRED, not run here):

  | host | compiled in process | `deserialize_file` |
  |---|---|---|
  | macOS | charged | not charged |
  | Linux | not charged (`memfd`) | not charged |
  | Windows | charged | charged |

- No report of this was found in wasmtime's tracker by web search (not exhaustive). wasmtime 49.0.0's release notes say only that operator costs now apply to constant expressions and the synthesised `start` call (#14215).

## The judge

- The judge's driver compiles in its own process. On macOS each of its fuel figures includes the image copy: about 42.35M for the snapshot, 5.05M for the plain reactor (INFERRED from the above; same code path).
- On Linux the same check would count those millions fewer; on Windows it would match macOS (INFERRED). The progress record's fuel is therefore comparable only between runs on the same operating system.

## What it decides now

- Recommended for the runner (EXECUTED in miniature, `remedy.py`): meter from after instantiation. Give instantiation its own large budget; then set the caller's fuel; then call `_initialize` and `run`. In `_call` that is: `store.set_fuel(2**63 - 1)` before `linker.instantiate`, and `store.set_fuel(fuel)` straight after it. `fuel_used` stays `fuel - store.get_fuel()`.
  - The result: `fuel_used` and the cap are the same however the module was obtained, and on every operating system. In `remedy.py` a cap of 1,000 traps at instantiation for the compiled module today and runs for the loaded one; with the change both run and both report 702.
  - The cost: nothing measurable. Two calls. The unmetered work is wasmtime's own memory fill, bounded by the size of our artifact, not by the guest. It runs no guest code because the artifacts have no start section. If a later artifact gains one, its start function would run unmetered; a check should hold "no start section".
  - What it changes: today's runner figures for compiled modules fall by 42.35M (snapshot) and 5.05M (plain); loaded ones do not change. `fuel_used` then means "instructions the guest executed, from `_initialize` (or `run`) on". The README line "compare only like with like" can go, and `test_a_cpp_exception_reaches_python` need not pass `cache_dir=False`.
- Alternatives, and why not:
  - Always load through `deserialize_file`, even without a cache: this fixes macOS and Linux and makes instantiation faster, but Windows still charges. It does not make fuel platform-free.
  - `memory_init_cow = False`: the same count everywhere (38,648,305 charged), but every instantiation copies the whole image on every platform, and the count still includes host work.
  - `Config::operator_cost` with `memory_init_per_byte = 0`: wasmtime-py 49 does not expose `operator_cost` (EXECUTED: absent from `wasmtime.Config`), and it would also stop charging the guest's own `memory.init`.
- The same change in the judge's driver would make the judge's fuel the same across operating systems. It is a change to the judge: its own change, with `--accept-judge`, and the fuel figures in `context/progress/` fall by the image size on the machines that copy.

## One line

A module compiled in the process, on macOS or Windows, pays one fuel per byte of its initial memory image at instantiation, because wasmtime must copy that image instead of mapping it; a module mapped from a `.cwasm` file pays nothing; the guest's own count is identical, so the runner should start metering after instantiation.
