# 126: Native unwind information is left out

- **Status:** **Superseded in substance by 127 (the pin moves to wasmtime 50), the same day:** under wasmtime-py 50.0.1, with native unwind information left on, the snapshot's module drop measures 22 ms (EXECUTED, the lane, in 127's scratch environment; 127's research memo measured 19.6 ms and `wasi-python run` at 0.43 s). wasmtime 50 fixed the registration upstream. What 126 would still buy after 127 is about 10 MB off every cached `.cwasm` and a drop of 2 to 12 ms instead of 22; the owner decided on 2026-10-25 to drop it (`../decisions.md`, "Spec 126 is dropped"): 127 gives the win that mattered, and the leftover is a benchmark fact in the memo. 126 is **retired, not for build**, and this file stays as the record. Before: **drafted 2026-10-24**, from the owner's question on the speed spike's teardown finding ("why does this happen?"). Its checks are named in Decision 4 and not yet written: the builder writes them first and records them failing on main's code (AGENTS.md rule 3), then builds. It is runner code, so a **pre-build review is required** (AGENTS.md rule 8); a different agent reviews the build.
- **Date:** 2026-10-24
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/` (`_engines.py` only), the judge's driver (`tests/harness/guest.py`), two unit-check files already in the `own-runner` shard (`tests/unit/test_runner_calls.py`, `tests/unit/test_runner_module_caches.py`), two lines of `docs/`, and `CHANGELOG.md`. It touches nothing under `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow, and no artifact byte. Decision 6 says why it is not structural by AGENTS.md's definition. It changes no default an embedder can see (constitution §4.15): no limit, no channel, no path.
- **Depends on:** landed and unchanged: 113 (every module cache is guarded: the cache name, the private-folder rule and `_load`'s stamp check, which this specification keeps), 104 (the runner as a package: `_engines`). On nothing in flight. It shares `CHANGELOG.md` with whatever lands beside it, nothing else.
- **Research it stands on:** `../research/2026-10-24-native-unwind-information-and-the-module-drop.md` (the cause, the stack sample, the measurements) and `../research/2026-10-23-a-rust-runner-against-wasmtime-py-on-speed.md` §4 (where it was found). Every number below is one of theirs (EXECUTED there) unless marked.

## The problem

Dropping the compiled module costs **4.4 to 5.0 s** on macOS, in wasmtime-py and in a Rust embedding alike. `wasi-python run -c "print(1)"` takes **4.9 s**, of which about 0.35 s is the run. Each pytest process pays it at exit for every module it compiled or loaded. An embedder's long-lived process pays it once, at exit.

The cause is in wasmtime, below the binding. It emits native unwind information (an `.eh_frame` section) for the compiled code so a system unwinder or a profiler can walk through wasm frames, and on macOS it registers that information with the system's libunwind **one entry per function**, then takes each back at drop. `python.wasm` and the snapshot define **89,060 functions**. libunwind's registrations are a list searched per call, so the drop is quadratic: a stack sample during it puts every one of 2,409 samples in `__deregister_frame`. wasmtime's own documentation of the option says as much: "Some platforms exhibit quadratic behavior when registering/unregistering unwinding information."

wasmtime does not need the information for anything the product uses: its own wasm backtraces, trap words and fuel come from its own tables. The option that leaves it out, `Config.native_unwind_info`, is public in wasmtime-py.

Measured with it off: the drop falls to **2 to 12 ms**; hello's `fuel_used` is **53,519,933 on both** settings; the `.cwasm` loses its **10.5 MB** `.eh_frame` section and every other section keeps its size.

One catch decides the shape of the change: a `.cwasm` compiled **with** the information, loaded under an engine with the option **off**, loads without complaint (wasmtime's header does not record the setting) and still costs **4,516 ms** to drop. The information lives in the file. So the cache's file name must change with the setting, or every existing cache keeps the cost.

## Decisions

### 1. Both runner engines leave native unwind information out

`_engines._engine` sets `cfg.native_unwind_info = False` on both engines (metered and unmetered), after `epoch_interruption` and before the stack settings, so the recorded order of settings reads: fuel, epochs, unwind, stack.

- **Why both.** The two engines differ only in fuel metering; the information is a property of the code memory, the same in both.
- **Through the public property, not the seam.** `Config.native_unwind_info` is a public setter on wasmtime-py's `Config` (`_config.py:483`), so `_wasmtime_ffi.py` gains nothing and spec 108's seam rule is untouched.
- **Windows.** wasmtime keeps the information there whatever the setting (its ABI requires it); the line is harmless and uniform. The README and docs name no platform difference.
- **What an embedder loses.** A native profiler (Instruments, `sample`, `perf`) attributes time inside wasm frames to unknown addresses. Nothing in the product, the judge or the research method uses that: fuel is wasmtime's own count. `docs/explanation/how-it-works.md` says so in one sentence (Design).
- **Rejected: `os._exit` in the command line** (suggested 2026-10-23 before the cause was known). It hides the cost at one call site, leaves every pytest process's and embedder's exit as it is, and leaves the 89,060 registrations at every load.
- **Rejected: dropping the module on a background thread at exit.** The cost would still be paid, by the user's CPU, and a process that exits before the thread finishes would be killed mid-deregistration.

### 2. The module cache's name carries the setting

The cache file name becomes `{digest[:32]}-wasmtime{version}-{flavor}-no-unwind.cwasm`, where `flavor` stays `fuel` or `plain`. One new token; the rest as spec 113 left it.

- **Why a name, not a header check.** wasmtime's `.cwasm` header records the engine's compiler settings and refuses a mismatch (the 2026-10-18 spike met this with the collector), but it does **not** record this setting: the old file loads and keeps its cost. The runner must tell the two apart itself, and the name is where it already tells wasmtime versions and flavors apart.
- **Why a token naming the setting** ("strings speak for themselves", spec 112): a reader of the cache folder sees what the file lacks. Rejected: a generation number (`-v2`), which says nothing.
- **Old files stay.** Nothing in the runner removes a `.cwasm` under another name today (a wasmtime version move leaves the old files too), and this specification adds no sweep: a sweep is its own change with its own risks in a folder the runner shares with other versions of itself. The cost: up to about 600 MB per user cache until the user deletes them. `docs/get-started/install.md` gains one sentence saying the files under the old names may be deleted.
- **One recompile per host.** The first call after the upgrade compiles again (about 15 s on darwin-arm64 for one module) and writes the new name. On Windows the recompile buys nothing (Decision 1), and is accepted for one rule on every system.
- `_load`'s rules (spec 113) are unchanged: a private folder, a private file, the stamp check after the load.

### 3. The judge's driver has the same engine

`tests/harness/guest.py`'s `engine()` sets `cfg.native_unwind_info = False` in the same position. The judge's engine states the product's settings (`test_runner_calls.py` pins both lists, Decision 5), and the judge's processes drop the two real modules at every exit, which is where the judge itself pays the cost today. `tests/harness/files.py`'s two engines compile small modules for the filesystem checks and are left alone: they state no promise about the product's engine, and their modules are tiny.

### 4. The checks first

Written before the code, seen failing on main's code, each in a file the `own-runner` shard already runs on all three systems. No check measures time (AGENTS.md: tests count operations, never wall-clock).

- `tests/unit/test_runner_module_caches.py::test_the_cached_module_carries_no_native_unwind_section`: the runner compiles the plain binary into a fresh cache folder (as the file's existing checks do), and the check reads the `.cwasm` as an ELF64 file: its section header names include `.text` and `.wasmtime.info` and do **not** include `.eh_frame`. On main: `.eh_frame` is present (10,521,060 bytes in the snapshot's). A second row loads the module back from the cache and runs hello, so the check holds that the file the runner wrote is one it reads. The ELF walk is about 20 lines in the check (the section header table's offset, count and string-table index from the file header; each header's name offset and size); nothing from `src/` reads ELF.
- `tests/unit/test_runner_module_caches.py::test_a_module_cached_with_unwind_information_is_not_loaded`: a `.cwasm` at the **old** name (`...-{flavor}.cwasm`), written by the check at the runner's modes, is left untouched and unread: the runner compiles, writes the new name, and `stats()["loaded"]` does not move. This is the row that holds Decision 2's catch: without the name change the old file would load and keep its cost.
- The two existing name helpers in that file (`test_runner_module_caches.py:81` and `:344`) take the new token; every row that uses them then holds the new name.

### 5. The existing checks this changes (a judge change, with its reason)

- `tests/unit/test_runner_calls.py:241-254` (the runner's two engines' recorded settings) and `:309-314` (the judge driver's): each list gains `("native_unwind_info", False)` after `("epoch_interruption", True)`. The reason, in the claim list: the engines leave native unwind information out; the lists state every setting the engines make.
- `tests/unit/test_runner_module_caches.py`'s two name helpers (Decision 4).
- Nothing in `tests/checks/` changes. No golden output, no `known_gaps.toml`, no upstream allowance.

### 6. The shape of the change (not structural)

One assignment in `_engine`, one token in `_module_miss`'s f-string, one assignment in `guest.engine()`. No module-level mutable or lock, no private wasmtime-py name, no platform branch (Windows's behaviour is wasmtime's, not a branch of ours), no test seam. `_engines.py` stays at about 330 lines; `_engine` stays at 16 lines and `_module_miss` at about 45. The build shows the rules checks green.

### 7. Fuel does not move

The information is metadata beside the code, not in it: hello's fuel is equal to the instruction on both settings, and `.text` has the same size. The builder's release run on the branch is the confirmation across every check and system; **any growth line is red for this specification**, since it claims none. If one appears, the specification is wrong about the cause of the growth and stops until it is explained.

## Intent

A process that compiled or loaded the guest no longer pays seconds at exit on macOS, and the command line answers in the time its run takes. Nothing the guest or an embedder can observe changes: not fuel, not trap words, not the public API, not a default.

## Design

- `src/wasi_python/_engines.py`: `_engine` sets `native_unwind_info = False` on both engines, with a comment giving the reason in words (one unwind entry per function registered with the system's unwinder on macOS, taken back one by one at drop; wasmtime's own backtraces do not use it). `_module_miss` names the cache file with the `-no-unwind` token; the comment beside the name says why the setting is in the name (a cached file keeps the information it was compiled with, and wasmtime's header does not record the setting).
- `tests/harness/guest.py`: `engine()` sets the same, with a one-line reason.
- `tests/unit/test_runner_calls.py`, `tests/unit/test_runner_module_caches.py`: Decisions 4 and 5.
- `docs/explanation/how-it-works.md`, the `.cwasm` paragraph: one sentence: the compiled module carries no native unwind information, so a system profiler cannot see inside wasm frames; wasmtime's own backtraces and fuel do not depend on it.
- `docs/get-started/install.md`, the cache paragraph: one sentence: a release that changes how the module is compiled writes a new file name and leaves the old files, which may be deleted.
- `CHANGELOG.md`, under the next unreleased section (`release/version.py bump` makes it): one line (below).
- `README.md`: unchanged (it names neither the cache's file names nor a profiler).

### The CHANGELOG line

- **The compiled module carries no native unwind information** (spec 126). On macOS, wasmtime registered one unwind entry per function of the guest with the system's unwinder, 89,060 of them, and took them back one by one when the module was dropped: about 4.4 s at every process exit, which made `wasi-python run` take 4.9 s for a 0.35 s run. The runner's engines now leave the information out, as the judge's driver does; the drop takes milliseconds, `fuel_used` is unchanged to the instruction, and the cached `.cwasm` is 10 MB smaller. The cache file's name carries the setting, so the first call after upgrading compiles once more; files under the old names stay and may be deleted. What is lost: a native profiler can no longer attribute time inside wasm frames.

## Scope

In: the two runner engines, the judge driver's engine, the cache name, the two unit-check files, two sentences of docs, the CHANGELOG line. Out: any sweep of old cache files; `tests/harness/files.py`'s engines; the command line (unchanged); Linux and Windows measurements (the change is uniform and harmless there); the Rust spike (research only).

## Acceptance criteria

1. Both runner engines and the judge driver's engine record `native_unwind_info = False`, and the pinned settings lists say so (Decision 5).
2. The `.cwasm` the runner writes has no `.eh_frame` section and is loaded back and run (Decision 4, first check).
3. A `.cwasm` under the old name is neither loaded nor overwritten (Decision 4, second check).
4. The fast tier is green on the branch; the release run on the branch is green on three systems with **no growth line** (Decision 7).
5. `ruff check`, `ruff format --check` and the rules checks are green; no function or module crosses a ceiling.
6. The builder records, as benchmark facts in the landing notes and not as checks: `wasi-python run -c "print(1)"` wall before and after on the build machine, and one module drop timed in a fresh process (the memo's method), so the landing notes show the saving the specification claims.

## For the lane

- **Wave kind:** parallel-safe, runner code; the pre-build review is required.
- **The claim list:** the two settings lists in `test_runner_calls.py` (gain one row each: the engines leave native unwind information out); the two cache-name helpers in `test_runner_module_caches.py` (the name carries the setting). No gap entry, no golden output, no growth.
- **Flags:** `--accept "126: native unwind information is left out"`, `--accept-judge "126: the engine settings lists and the cache names carry the new setting"`. No `--accept-growth`: a growth line ejects the entry.

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first, the fast tier, the branch's release run (its id, every line green, no growth line), the benchmark facts of acceptance criterion 6, the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

The runner's engines and the judge's driver set `native_unwind_info = False`, and the module cache's file name says so, so the 89,060-entry registration with macOS's libunwind that cost 4.4 s at every module drop is gone, with fuel unchanged and the `.cwasm` 10 MB smaller.
