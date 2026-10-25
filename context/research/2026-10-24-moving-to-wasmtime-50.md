# Moving to wasmtime 50

- **Status:** research, 2026-10-24. What the move of the `wasmtime` pin from the 49 line to the 50 line needs, measured against wasmtime-py 50.0.1 in a scratch environment. It changes nothing: no code in `src/`, no pin, no test. Its specification is `../specifications/127-the-pin-moves-to-wasmtime-50.md`. Every wall-clock number is a benchmark fact on one machine, never a check.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1). Box: one session, shared with two other research agents on the same machine.
- **Stands on:** `../decisions.md` (decision 86: "the shadow is removed with the pin that moves past wasmtime 49.0.3"; decision 11, the shared callback tables); `../specifications/048-the-sandbox-holds-on-wasmtime-49-0-0.md` (the two shadows and their removal predicate, Decision 5); `../specifications/002-the-progress-harness.md` (Decision 6: fuel is not compared across wasmtime versions); `../specifications/004-alpha-releases.md` (the judge tests one wasmtime major); `../specifications/068-*` through the CHANGELOG (the counted calls); `../specifications/126-native-unwind-information-is-left-out.md`; `2026-10-18-wasmtime-49-advisories.md` and its `advisories/*.json`; `2026-10-18-a-rust-core-with-js-and-python-wrappers.md` §1.5 and §1.6; `2026-10-23-a-rust-runner-against-wasmtime-py-on-speed.md` §3.2 (the inference tested here); `2026-10-24-native-unwind-information-and-the-module-drop.md`; `../upstream/12-wasmtime-py-on-wasmtime-49-0-3/facts.md`; `src/wasi_python/_wasmtime_ffi.py`, `_engines.py`, `_call.py`, `_fs_*.py`; `tests/checks/test_rules.py`, `tests/harness/scoreboard.py`, `tests/harness/gather.py`, `tests/harness/files.py`.
- **Evidence:** `2026-10-24-moving-to-wasmtime-50/` beside this memo. `scripts/` holds the four scripts run; `results/` their outputs, one file per wasmtime-py version where two were run; the folder's top level holds the release, tag, commit and PyPI facts fetched once each (`gh api`, `curl`), the wasmtime-py download script at its 50.0.1 tag, wasmtime 49.0.4's notes and the record of GHSA-mghf-wjfp-p5xm. No `.wasm` or `.cwasm`.
- **Machine:** darwin-arm64, Apple M1 Pro, macOS 26.5.2, Python 3.14; the 0.1.0 artifact set (`build/artifacts`), main `2cd47507`. wasmtime-py 49.0.0 from the project's `.venv`; wasmtime-py 50.0.1 in a scratch venv under `build/scratch-wt50/` (git-ignored), made with `uv venv` and `uv pip install`, the project's `dev` group beside it, the runner imported from `src/`. The main tree's environment was not changed.

Labels: EXECUTED means run here; READ means read from a file or a page, cited; INFERRED means the researcher's reasoning.

## The short version

1. **What is on PyPI.** wasmtime-py 50.0.1 was uploaded on 2026-10-22 and bundles wasmtime 50.0.0 (released 2026-10-20). There are no files for a wasmtime-py 50.0.0 and there is no wasmtime v50.0.1: 50.0.1 is a wasmtime-py patch on wasmtime 50.0.0 (§1).
2. **The seam holds, but for one read.** Every private name `_wasmtime_ffi.NEEDED` lists exists in 50.0.1; the public API of the eleven classes the runner touches is unchanged; the binding gained three config setters. One read breaks anyway: wasmtime-py's `Slab`, its table of host functions and custom outputs, lost its `list` (now `handles`, a dict) in a commit of 2026-09-24, after 49.0.0. `host_function_count()` raises `AttributeError`, and the import check does not catch it, because it checks that `FUNCTIONS` exists, not what it has (§2).
3. **The runner runs on 50.0.1.** Hello on the snapshot, hello on the plain reactor, a numpy sum and a stat loop exit 0. Fuel is equal to the instruction on the snapshot (53,530,298), the numpy sum (840,980,989) and the stat loop; the plain reactor's hello fell by 502,255 instructions, 1.8e-3. 172 of 175 selected unit and sandbox checks pass with `src/` unchanged; the three that fail are the `Slab` read, ten parity rows whose trap words wasmtime 50 changed, and one that needs the package installed (§3).
4. **Both advisories are fixed in wasmtime 50.0.0 itself.** Against wasmtime's own WASI, with no runner and no guard: the trailing-slash symlink rename answers `ENOTDIR` and moves nothing, where 49.0.0 moves the outside folder in; `fd_readdir`'s padding is zero in 800 of 800 entries, where 49.0.0 leaves host bytes in 200 of 1,000. Decision 86's condition is met: the shadows go (§4).
5. **The judge's removal rule does not know it.** `_guard_may_go(">=50,<51")` is False for both guards today, because it reads each advisory's `patched_versions`, which names only the patch lines (`36.0.18, 48.0.6, 49.0.3`) and never the next major. The same holds for the advisory of 2026-10-19 (`36.0.19, 48.0.7, 49.0.4`). The rule must read the advisories' `vulnerable_version_range` instead, which 50.x lies outside (§4.3).
6. **The speed inference was wrong in its attribution.** On the file program, the product is slower than a bare embedding by 70 to 190 ms. Leaving the two guarded calls native changes nothing. Leaving the three counted calls native too brings the product to bare. The program makes no `fd_readdir` and no `path_rename`; its 2,000 opens and 2,000 closes pass through spec 068's counted shadows, about 24 µs each. The pin move removes no file-call cost (§5).
7. **A side finding that changes spec 126.** Under wasmtime 50.0.0 the module drop with native unwind information kept takes 19.6 ms, where 49.0.0 took 5,732 ms; the 50.0.0 notes say "Bulk libunwind section registration is used when available". `wasi-python run -- -c "print(1)"` takes 0.43 s under 50.0.1 against 5.4 s under 49.0.0. Spec 126's reason goes with the pin; what it would still buy is a 10 MB smaller `.cwasm` (§6).
8. **The wasmtime CLI stays at 49.0.3.** Its one job is the Wizer snapshot. The critical aarch64 advisory of 2026-10-19 needs a `br_table` with more than about 256k targets; `python.wasm`'s largest has 3,203. The two WASI fixes concern a running guest's file calls; the snapshot step preopens one read-only folder. Moving the CLI changes a recipe input and may change the snapshot's bytes: build-class work for the next rebuild, not for this move (§7).
9. **What the judge does at the move.** The run record carries the wasmtime-py version beside every fuel metric. A different version means fuel is not compared and the fresh values are recorded at acceptance; `pyproject.toml` and `uv.lock` are judge files, so the landing needs `--accept-judge` and no `--accept-growth` (§8).

## 1. What wasmtime 50 is (READ)

- **Releases** (`wasmtime-releases.txt`, `gh api`, 2026-10-24): v50.0.0 on 2026-10-20; v49.0.4, v48.0.7 and v36.0.19 on 2026-10-19; v49.0.3 on 2026-10-14; v50.0.0-rc.1 on 2026-10-05. No v50.0.1 (its tag page answers 404).
- **wasmtime-py** (`wasmtime-py-tags.txt`, `wasmtime-py-commits.txt`): tag 50.0.0 at `e44ae48` (2026-10-21, "Bump Wasmtime to 50.0.0 (#345)": `VERSION`, `ci/download-wasmtime.py`, `wasmtime/_bindings.py` +22, one test file; `wasmtime-py-50.0.0-files.txt`) and tag 50.0.1 at `44f51d6` (2026-10-22, "Bump to 50.0.1": `VERSION` only). Between 49.0.0 and 50.0.0 sits one other commit, `280ce73` (2026-09-24, "Make `Slab` safe to use from multiple threads (#344)"), the one that breaks a read (§2).
- **What 50.0.1 bundles:** `ci/download-wasmtime.py` at tag 50.0.1 says `WASMTIME_VERSION = "v50.0.0"` (`wasmtime-py-50.0.1-download-wasmtime.py`, line 15). EXECUTED: the wheel's `_libwasmtime.dylib` carries the string `version: 50.0.0` (49.0.0's carries `version: 49.0.0`; `strings`). So wasmtime-py's version and wasmtime's differ by the patch digit, as spec 048's Decision 5 said they could.
- **PyPI** (`pypi-summary.txt`, one `curl` of the JSON): latest 50.0.1, uploaded 2026-10-22T02:59:50; twelve files, the macOS arm64 wheel 8,096,649 bytes; 50.0.0 has **no files**; 49.0.0 has twelve.
- **The 50.0.0 notes** (`results/wasmtime-50.0.0-release-notes-summary.txt`, one fetch of the release page). What touches the runner: the epoch and call-hook callbacks of the Rust API take a `StoreHookState` (the C API binding's shape is unchanged, §2); "Fuel is now charged for more host allocations made with `Val`" (component-model values; the guest's count did not move, §3); "Bulk libunwind section registration is used when available" (§6); 49.0.1's fuel fix around `call_ref` and exception catches; `Store::set_epoch_deadline` no longer overflows on very large deltas; native stack-walking on macOS arm64 fixed; 49.0.4's aarch64 `br_table` fix (§7); "Several `wasi:filesystem` fixes (`set-times` on directory descriptors, symlink `stat`, `stat` fast path, datetime overflow, directory entry file types)". Not named: `fd_readdir`, `path_rename`, the `.cwasm` format, `native_unwind_info`, the collector, any GHSA of 49.0.2 or 49.0.3. The two fixes are shown present by the probes of §4, not by the notes.
- **The cadence held** (the 2026-10-18 memo §1.6 predicted it): wasmtime-py shipped its major one day after wasmtime's, and shipped no patch release for 49.0.1 to 49.0.4.

## 2. The seam under 50.0.1 (EXECUTED)

- **`import wasi_python._wasmtime_ffi` succeeds.** `check()` finds every name in `NEEDED`; `ASYNC_STACK_SETTER` is present. So no private name the seam reads moved.
- **The public API diff** (`results/api-diff.txt`: `dir()` of `Store`, `Caller`, `Config`, `Engine`, `Func`, `WasiConfig`, `Linker`, `Module`, `Memory`, `Instance` and the package, on both versions): no class gained or lost a name. `wasmtime._ffi` gained three setters (`wasmtime_config_wasm_compact_imports_set`, `..._component_model_accessors_set`, `..._component_model_canonical_names_set`) and lost none. The debt sheet `../upstream/34-.../facts.md` stays as it is: nothing the runner wants went public.
- **The `Slab` read breaks** (`results/slab-diff.txt`, `results/unit-under-50-full.txt`). `host_function_count()` reads `len(_func.FUNCTIONS.list)`; 50.0.1's `Slab` keeps `handles: Dict[int, T]` and a `counter` from `itertools.count(1)`, never reuses a handle, and says it is "safe to use from many threads" without a lock, every step one dict operation under the GIL. `tests/unit/test_wasmtime_ffi.py::test_the_judges_three_reads_of_wasmtime_pys_own_tables` fails with `AttributeError: 'Slab' object has no attribute 'list'`. The import check passed because `NEEDED` names `("wasmtime._func", "FUNCTIONS")`, not what `FUNCTIONS` must have. The fix is one read (`len(_func.FUNCTIONS.handles)`) and one row in `NEEDED` so the next move names it.
- **A note for decision 11, not for this move:** the race decision 11 recorded (threads that define or free callbacks at once corrupt the tables) is what commit `280ce73` addresses upstream. Spec 011's own table and lock in the runner are untouched by the pin move; whether they can go is a later question with its own measurement.

## 3. The runner under 50.0.1 (EXECUTED)

`scripts/hello_fuel.py`, through `wasi_python.run` with `src/` unchanged, `fuel=10**12`, a scratch cache (`results/hello-fuel-wasmtime-py-*.json`):

| program | 49.0.0 fuel | 50.0.1 fuel | difference |
|---|---|---|---|
| hello, snapshot | 53,530,298 | 53,530,298 | 0 |
| hello, plain reactor | 272,049,097 | 271,546,842 | −502,255 (−1.8e-3) |
| `np.arange(10**6).sum()`, snapshot | 840,980,989 | 840,980,989 | 0 |
| 1,000 `os.stat` on the stdlib folder, snapshot | 64,958,655 | 64,958,655 | 0 |

Every run exited 0 with the expected output. The plain reactor's start-up differs; the snapshot's does not. The plain `_initialize` reads the stdlib folder and zip while it starts, and wasmtime 50's filesystem answers changed in the notes' list ("directory entry file types", "symlink `stat`", "`stat` fast path"); which answer moved the count was not traced (INFERRED that it is one of these; not shown). The fall is beyond the ratchet's 1e-4, and it does not matter to the ratchet: fuel is not compared across wasmtime versions (§8).

**The unit and sandbox checks** (`results/unit-under-50-full.txt`): `tests/unit/test_wasmtime_ffi.py`, `test_runner_mounts.py`, `test_runner_grants.py`, `test_runner_calls.py`, `test_runner_module_caches.py`, and the two sandbox checks `test_a_trailing_slash_symlink_rename_cannot_escape` and `test_a_trailing_slash_rename_rule` of `tests/checks/test_v1_2_hostile_guest.py`: **172 passed, 3 failed, 2 skipped** in 55 s, with the frozen set and `src/` unchanged (the guard still in place, so the two sandbox checks prove nothing new here; §4 does).

The three failures:

1. `test_the_judges_three_reads_of_wasmtime_pys_own_tables`: the `Slab` read (§2).
2. `test_raw_calls_answer_as_a_grant_does`: ten rows (`results/parity-differing-rows-under-50.txt`). wasmtime 50's argument conversion ends the run with "number too small to fit in target type" for a negative value (`fd_advise -1`, `seek 5 -1`, `open lookup flags out of range`) and "number too large to fit in target type" for one over its type's top (`set_flags out of range`, `seek 5 256`, `open oflags out of range`), each on a file, a folder and the plain folder. 49.0.0 said "out of range integral type conversion attempted" for both, and the runner's `_fs_memory._unsigned` says those words for the mount side. The parity compares the words, so the runner must say wasmtime 50's, by the sign.
3. `test_the_host_errno_table_is_by_name`: its child runs `sys.executable -I`, which drops my `PYTHONPATH`, so `import wasi_python` failed. An artefact of the scratch environment, not of wasmtime 50 (INFERRED from the traceback: `ModuleNotFoundError`).

## 4. The advisories under wasmtime 50.0.0 (EXECUTED)

### 4.1 The probes

`scripts/native_probes.py` drives the judge's raw module (`tests/harness/files.py::grant_raw`) on wasmtime's own WASI: no runner, no guard, one writable preopen `/work` beside a folder `outside/` holding `canary.txt`. Then: `path_symlink("../outside", "up")`; `path_rename("up/", "stolen")`; `path_rename("f.txt/", "e")` on a file; 200 `fd_readdir` listings into a zeroed buffer, each entry's three bytes after `d_type` read (`results/native-probes-wasmtime-py-*.json`).

| probe | wasmtime 49.0.0 (wasmtime-py 49.0.0) | wasmtime 50.0.0 (wasmtime-py 50.0.1) |
|---|---|---|
| `rename("up/", "stolen")` errno | 0 | 54 `ENOTDIR` |
| `outside/` still exists | **no: moved into the grant as `stolen/`, its canary readable** | yes |
| escaped | **true** | false |
| `rename("f.txt/", "e")` of a file | 54 | 54 |
| `fd_readdir` entries with non-zero padding | **200 of 1,000** (bytes `70 2f 1f`) | 0 of 800 |

So GHSA-m9f7-9w4p-gv38 and GHSA-96f6-r43r-8c24 are fixed in the wasmtime that wasmtime-py 50.0.1 bundles, on this host, by the same operations spec 048's research used to confirm them on 49.0.0. The 49.0.0 column reproduces the 2026-10-18 memo's escape in one call (`escaped: true`).

### 4.2 What else 49.0.0 carries that 50.0.0 fixes (READ)

The 2026-10-18 memo assessed the 49.0.1 to 49.0.3 advisories: only the two above reach a guest of this project. Since then: wasmtime 49.0.4 (2026-10-19; `wasmtime-49.0.4-notes.md`) fixes four `wasi-http` and component-model advisories, which do not reach us (no component, no `wasi-http`), and **GHSA-mghf-wjfp-p5xm** (critical; `GHSA-mghf-wjfp-p5xm.json`): "Cranelift backend on aarch64 can jump to incorrect target on large Wasm `br_table` instruction", for "more than ~256k targets on one `br_table`", a sandbox escape by "a user-controlled Wasm module". The vulnerable range is `<36.0.19, >=37.0.0, <48.0.7, >=49.0.0, <49.0.4`; the 50.0.0 notes list the fix. The module here is not user-controlled, and EXECUTED (`results/br-table-scan.txt`, the pinned wasi-sdk's `llvm-objdump -d`): `python.wasm` has 20,151 `br_table` instructions and the largest has **3,203** targets; the snapshot the same. So it does not reach this project's guest, on wasmtime-py 49.0.0 or on the CLI at 49.0.3. It is still a reason to move: 49.0.0 sits inside the vulnerable range of every advisory fixed since September, which is what a dependency scanner reads.

### 4.3 The judge's removal rule (EXECUTED, `results/guard-rule-on-50.txt`)

`tests/checks/test_rules.py::_guard_may_go` says a guard may go only when, for every major line the requirement admits, the advisory's `patched_versions` lists a version in that line at or below the lowest admitted. Evaluated on the two guards' lists:

| requirement | padding guard may go | rename guard may go |
|---|---|---|
| `>=49,<50` (today) | no | no |
| `>=50,<51` | **no** | **no** |
| `>=49.0.3,<51` | no | no |
| `>=50.0.1,<51` | no | no |

Under the pin the project moves to, the rule keeps both guards, and once the guard is deleted the check turns red ("admits a vulnerable wasmtime, and the filesystem names no guard"). The cause is the field it reads: `patched_versions` names the patch releases of the lines that existed when the advisory was written (`36.0.18, 48.0.6, 49.0.3`), never a later major. Every one of the 28 records of 2026-10-18 has this shape, and so does the record of 2026-10-19. Spec 048 chose the field to avoid "at or past" reasoning, because wasmtime's releases are not one ordered line (v50.0.0-rc.1 predates v49.0.3).

The field that does say which versions are vulnerable is `vulnerable_version_range`: for the rename, `<= 36.0.17, >= 37.0.0, <= 48.0.5, >= 49.0.0, <= 49.0.2`; for the padding, `< 36.0.17, >= 37.0.0, < 48.0.4, >= 49.0.0, < 49.0.2` (READ, the two JSON records). Each is a list of spans, one per release line the advisory knows, and a version outside every span is one the advisory does not call vulnerable. 50.0.0 is outside both. That reading is still not "at or past": it is the advisory's own statement, span by span, and the probes of §4.1 confirm it for 50.0.0 by running the attack. The specification changes the rule to read this field (its Decision 3).

## 5. The file-call inference (EXECUTED)

The speed spike (§3.2 of its memo) measured the product 118 ms slower than a bare wasmtime-py embedding on the file program (505 against 387 ms), "5.4 µs a call: its guard linker, which shadows `fd_readdir` and `path_rename` and forwards the rest (spec 048)". Two things to check: whether the guard is on the program's path, and whether removing it closes the gap.

**What is on the path (READ).** A call without mounts runs on `_call._guard_linker`, which shadows five preview1 calls: the two in `_fs_memory.GUARDED` (`fd_readdir`, `path_rename`; spec 048) and the three in `COUNTED` (`path_open`, `fd_close`, `fd_renumber`; spec 068's cap on open files). Every other call, `path_filestat_get`, `fd_read`, `fd_seek` and the rest, is wasmtime's own. The program (`bench.py`'s `FILES`) does 20,000 `os.stat` and 2,000 `open`/`read`/`close`. `os.stat` is `path_filestat_get`: native. Each `open` is one `path_open` and each `close` one `fd_close`: 4,000 shadowed calls, each a C-to-Python callback, a trampoline forward through `wasmtime_func_call` and the count against the cap. No `fd_readdir` and no `path_rename` is made, except the stdlib folder's listing at start-up, which the hello program makes too.

**The measurement** (`scripts/files_bench.py`, `results/files-bench-wt49.json`, `results/files-bench-wt50.json`). Four arms, each in a fresh process (the linker is built once per engine and cached on the process object, so an arm cannot change it after the first call): the product as shipped; the product with `GUARDED` emptied before the first call, so the two guarded calls stay native; the product with `GUARDED` and `COUNTED` emptied, so all five stay native; a bare wasmtime-py embedding (the spike's `bare` arm, with the grant preopened). Each process warms once, then times three runs; three rounds interleave the arms; the median of nine. Medians in ms; the machine was shared, so the ranges are given too:

| arm | 49.0.0 median (min–max) | 50.0.1 median (min–max) |
|---|---|---|
| product | 657 (566–838) | 548 (535–763) |
| product, guarded calls native | 731 (536–999) | 552 (537–617) |
| product, guarded and counted calls native | 572 (485–903) | **455** (435–521) |
| bare wasmtime-py | 466 (432–543) | **478** (446–622) |
| product, hello | 18.7 | 18.6 |
| bare, hello | 11.9 | 12.5 |

**What it says.** Leaving the two guarded calls native changes nothing the noise does not cover (548 against 552 on the quieter 50 run; 657 against 731 on the 49 run, inside its spread). Leaving the three counted calls native too puts the product at or under bare (455 against 478). So the product's extra on this program is spec 068's counted shadows, not spec 048's guard: about 95 ms over 4,000 shadowed calls, **about 24 µs a shadowed call** (the spike's "5.4 µs a call" divided its 118 ms over all 22,000 calls, 18,000 of which were never shadowed). The hello rows show the product's fixed cost per call, about 6 to 7 ms over bare, the same on both versions.

**What follows.** The pin move removes no file-call cost; the specification promises none. The cost that is there belongs to the cap on open files, which needs a Python round trip per open and close on wasmtime-py; whether that cap can be kept more cheaply (a Rust core counts natively; wasmtime-py has no cheaper hook) is a question for the Rust-core research, not for this move. The spike's §3.2 sentence should be read with this correction.

## 6. The module drop and the command line's wall (EXECUTED)

Spec 126 (drafted this morning) leaves native unwind information out because dropping the compiled module costs about 4.4 s on macOS: wasmtime registers one unwind entry per function (89,060) with libunwind and takes them back one by one. The 50.0.0 notes say "Bulk libunwind section registration is used when available". Measured (`scripts/drop_timing.py`, `results/drop-timing-wasmtime-py-*.json`): the snapshot compiled in-process on an engine with fuel and epochs, unwind information on and off, then `del module; gc.collect()` timed.

| | 49.0.0 | 50.0.1 |
|---|---|---|
| drop, unwind information on (the runner today) | **5,732 ms** | **19.6 ms** |
| drop, unwind information off (spec 126) | 19.3 ms | 19.0 ms |
| compile | 18.2 s | 15.1 to 19.7 s |

And the command line, a fresh process each time, the module from the cache (`results/cli-wall.txt`): `wasi-python run -- -c "print(1)"` takes **5.37 to 5.92 s** under 49.0.0 and **0.43 to 0.56 s** under 50.0.1 (a first run of 0.95 s). So the pin move gives what spec 126 set out to give, with no code and no cache-name change. What 126 would still do: leave the 10.5 MB `.eh_frame` out of the `.cwasm` (the research of this morning) and keep a line in the engine settings. Whether to withdraw 126 or keep it for the size is the owner's call; spec 127 does not depend on it and names the facts in its header. Spec 126's claim that a `.cwasm` compiled with the information still costs 4.5 s to drop under an engine with it off was true of 49.0.0; under 50.0.0 the cost is gone either way.

## 7. The wasmtime CLI pin (READ, EXECUTED, INFERRED)

The CLI at 49.0.3 is three pinned archives in `downloads/SHA256SUMS` (macOS arm64, Linux aarch64, Linux x86_64), named in `scripts/line.conf` and `scripts/00_download.sh`, unpacked by step 10, and used by **one step**: `scripts/steps/80_snapshot.sh` runs `wasmtime wizer` with `-W exceptions=y,unknown-imports-trap=y -S cli=y,inherit-stdin=n,... -C cache=n --init-func wizer.initialize` and one read-only preopen (the folder holding the stdlib zip) to make `python-snapshot.wasm` (READ). Step 20's `make pythoninfo` also runs `python.wasm` under the CLI on the build host (READ, its comment). `scripts/compare_snapshots.py` uses wasmtime-py, not the CLI. The runner never sees the CLI, and the CLI never sees wasmtime-py: the two versions are independent (READ).

Does anything require the CLI to move with the binding?

- **Security.** The two WASI fixes concern a running guest with a writable place (the escape) or any listing (the padding); the snapshot step runs `wizer.initialize` with one read-only preopen and no guest-controlled program, and G7 holds the snapshot to the same bytes on three hosts, so no host byte reached it (INFERRED from the same-bytes check). The aarch64 `br_table` advisory needs about 256k targets on one instruction; `python.wasm` has 3,203 at most (§4.2, EXECUTED). Nothing reaches the snapshot step.
- **Bytes.** Wizer's output is wasm the CLI's own Wizer code writes; a newer wasmtime may encode or lay the snapshot out differently (INFERRED, not tried: a scratch build of the snapshot with wasmtime 50 was outside the box, and the three archives are not pinned). A changed snapshot is a new artifact set: a rebuild on three systems, the dry run, every snapshot check's fuel re-recorded, `MANIFEST`'s `x-wizer` line. That is build-class work (AGENTS.md: it touches `downloads/SHA256SUMS` and `scripts/`).
- **Fuel.** The snapshot's bytes decide the guest's instruction counts, not the CLI's version as such; a same-bytes snapshot from wasmtime 50 would change no fuel (INFERRED).

So the move of the binding is parallel-safe and does not cover the CLI; the CLI's move is its own build-class specification for the next rebuild of the line, where a changed snapshot is expected anyway (the toolchain or a package). The specification says so in one decision, and the roadmap holds the follow-up.

## 8. What the judge does at a pin move (READ)

- **The record** carries `meta.wasmtime`, read from `importlib.metadata.version("wasmtime")` (`tests/harness/plugin.py::run_meta`), and the acceptance writes it beside every metric per platform (`scoreboard.py:287`, `{"wasmtime": meta["wasmtime"], ...}`).
- **Fuel across versions is not compared.** `scoreboard.compare`: when the accepted row's `wasmtime` is not the run's, the node goes to `fuel_not_compared`, never to `growth` (`scoreboard.py:183`); at acceptance, `same_engine` is False and the fresh fuel replaces the old without `--accept-growth` (`scoreboard.py:286-294`). Spec 002's Decision 6 states it: "On a different wasmtime version fuel is not compared, and the change shows as a judge change (`uv.lock`)." The 2026-10-18 spike's +231,562 on the matplotlib job between 49.0.0 and 49.0.3 and this memo's −502,255 on the plain hello are the kind of move this rule exists for.
- **The judge hash.** `pyproject.toml` and `uv.lock` are in `JUDGE_PATHS` (`tests/harness/paths.py:277`), so the move is a judge change and the acceptance carries `--accept-judge`. Gather's G2 compares each record's `meta.wasmtime` with `uv.lock`'s (`gather.py:196`), so a branch run on a lock that names 50.0.1 is read against 50.0.1.
- **The release tier** is not touched: no release-tier row changes by this move other than its fuel, which the same rule covers. The claims ledger stays empty.
- **The checks that change** are listed in the specification (Decision 3): the removal rule and its table; the guard's own checks in `tests/unit/test_runner_mounts.py` and `test_runner_grants.py` (deleted or re-derived against a plain grant); the per-system `NATIVE_RENAME_END` (wasmtime 50 answers `ENOTDIR` on every system, so the Windows row and the check that holds it go); the mask `(21, 22, 23)` at `test_runner_mounts.py:1185`; the ten trap-word rows; the `Slab` read; the pin's text in `test_v1_4_embedding.py` and `test_wasmtime_ffi.py`; the harness's `Guarded` class, which keeps only the counted calls.

## 9. Where it stopped

- The scratch environment had the runner on `PYTHONPATH`, not installed, so one unit check's `-I` child could not import it; the builder's worktree will not have this.
- The two sandbox checks were run with the guard still in place (they pass trivially). The native probes of §4.1 stand in; the builder's run of the same checks after the guard's removal is the check that counts.
- The over-long slash-named source (`test_a_trailing_slash_rename_rule`'s `ENAMETOOLONG` row, 048's own staging limit) was not probed against wasmtime 50; the specification lets the row follow wasmtime 50's own answer and asks the builder to record it.
- Which filesystem answer moved the plain reactor's start-up fuel by 502,255 was not traced.
- A snapshot built with wasmtime 50's `wizer` was not tried (unpinned archive; build-class).
- Windows and Linux were not run; the branch's release run is where they show.

## One line

wasmtime-py 50.0.1 (wasmtime 50.0.0) runs the frozen set with equal snapshot fuel, fixes both advisories natively (the escape answers `ENOTDIR`, the padding is zero), drops the module in 20 ms instead of 5.7 s, needs one `Slab` read and ten trap-word rows changed, and its pin needs the judge's removal rule to read the advisories' vulnerable ranges; the guard was never the file-call cost, spec 068's counted calls are, and the wasmtime CLI stays at 49.0.3 for the next rebuild.
