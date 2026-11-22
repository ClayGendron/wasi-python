# Moving to wasmtime 51

- **Date:** 2026-11-22
- **Author:** the orchestrating session (an agent, Claude), https://claude.ai/code/session_01ThzDEVEoH7V2U4kpFD24Yy
- **For:** specification 202, the pin moves to wasmtime 51, and release 0.1.6.

Labels: EXECUTED, run and seen; READ, read from a file or a page, cited; INFERRED, reasoned.

## 1. What is out

- wasmtime 51.0.0 was released on 2026-11-20 (READ: `RELEASES.md` at tag `release-51.0.0`; the tag `v51.0.0` is commit `32656dc`, "Release Wasmtime 51.0.0 (#15391)", 2026-11-20 15:57 UTC, EXECUTED by a blob-less fetch of the tag).
- wasmtime-py 51.0.0 was uploaded to PyPI on 2026-11-20 at 16:41 UTC (EXECUTED: PyPI's JSON). Its C header says `WASMTIME_VERSION "51.0.0"` (EXECUTED: `crates/c-api/include/wasmtime.h` at `v51.0.0`; INFERRED that the wheel bundles it, since it was built after the tag, and to be confirmed from the wheel's library by the builder, as 127 did).
- There is no wasmtime 51.0.1 (READ: the releases page, 2026-11-22).
- wasmtime 50.0.2 (2026-11-16) and 50.0.3 (2026-11-19) exist, but **no wasmtime-py 50.0.2 or 50.0.3 does** (EXECUTED: PyPI's release list ends 50.0.1, 51.0.0). The runner's pin `wasmtime>=50,<51` therefore admits only wasmtime-py 50.0.1, which bundles wasmtime 50.0.0. No user of 0.1.5 can get either patch release's fixes by pinning.

## 2. The advisories, and which reach the runner

Nine advisories were fixed after wasmtime 50.0.0. Each page's affected and patched versions were READ from its GitHub advisory page on 2026-11-22. The last column says whether each one reaches the runner as 0.1.5 ships it.

| Advisory | Severity | Fixed in | Reaches 0.1.5's runner? |
|---|---|---|---|
| GHSA-f2pq-268w-886c, WASI file sandbox escape on Windows through a drive-prefixed path component | High (CVSS 4: 7.5) | 50.0.3, 49.0.7, 48.0.10, 36.0.22; carried by 51.0.0 (below) | **Yes, on Windows, INFERRED.** A call on a plain host grant is forwarded to wasmtime's own call. See §3. |
| GHSA-5m8g-xhq4-4h93, unbounded host memory from empty writes to `AsyncWriteStream` | Moderate (6.9) | 50.0.2 | **Likely, on Windows, INFERRED.** The page names the C API's `wasi_config_set_stdout_custom`, which the runner uses where the platform gives no pipe it can open by path, and Windows gives none. |
| GHSA-43j2-gcp4-m22g, stale GC heap base pointer aborts the host | Moderate (4.7) | 50.0.2 | No. It needs a host function that returns GC objects. The runner's host functions take and return numbers only. |
| GHSA-wvgq-g5hf-6gm6, abort when a GC heap reservation is not a page multiple | Low | 50.0.2 | No. It needs `gc_heap_may_move(false)` or `memory_may_move(false)`, which the runner does not set. |
| GHSA-rc4p-x33f-vpr2, abort in builds without the `gc` feature | Low | 50.0.2 | No. wasmtime-py's library is built with it. |
| GHSA-2674-w29h-wqvj, abort in builds without the `threads` feature | Low | 50.0.2 | No, for the same reason. |
| GHSA-hj27-mpw9-ff4c, panic in `Caller::get_module_export` outside wasm | Low | 50.0.2 | No. The runner never calls one of its host functions from the host. |
| GHSA-xrvr-8678-5wp8, component stream cancel panic | Low | 50.0.2 | No. No component model. |
| GHSA-f8mm-ggr3-89wh, wasi-http empty body writes | Moderate | 50.0.2 | No. No wasi-http. |

**51.0.0 carries the Windows fix, though its notes do not list it.** The fix is commit `486e6db`, "[backport 50] Disallow colons in all paths on Windows (#15373)", between `v50.0.2` and `v50.0.3` (EXECUTED: `git log v50.0.2..v50.0.3`). It changes `crates/wasi/src/filesystem/primitives/windows/` and adds `tests/windows_colons.rs`. At `v51.0.0` that test file is present and `git diff v50.0.3 v51.0.0 -- crates/wasi/src/filesystem/primitives/windows/` is empty (EXECUTED). The advisory's affected ranges stop at `<50.0.3` and do not name 51 (READ).

## 3. Why the Windows escape reaches the runner

- A path call on a descriptor of wasmtime's own (a plain host grant, not a runner mount) goes to wasmtime unchanged: `_path_open` calls `_forwarded_open` when the table has no entry for the descriptor, and `_path_create_directory`, `_path_remove_directory`, `_path_unlink_file`, `_path_filestat_get`, `_path_readlink`, `_path_symlink`, `_path_rename` and `_path_link` each call `files.forward` in the same case (READ: `src/wasi_python/_fs_paths.py`). The look before an open is itself wasmtime's `path_filestat_get` on the same path.
- The runner's own rule against a `:` in a name, `_resolve`, serves only its mounts (READ: `_fs_paths.py`, `_resolve`, "A backslash or a colon is a separator or a drive to some host's path logic: refused on every host").
- So on Windows a guest given any host folder can name `./C:…` and reach what the advisory describes: reads through a read-only grant, and writes through a writable one (INFERRED). The specification's first check is to see it fail on wasmtime 50.0.0 on the Windows leg before the pin moves.

## 4. What else in 51 touches the runner

- **The engine seam holds.** Every private name in `_wasmtime_ffi.NEEDED` and `OPTIONAL` resolves on wasmtime-py 51.0.0. `wasmtime.Func._func` is an instance attribute, set in `__init__`, as before (EXECUTED in a scratch environment). wasmtime-py's Python layer changed only in `_bindings.py` and `_ffi.py`. The changes are regenerated bindings (`wasmtime_error_*` moved in the file, `wasmtime_struct_type_new` gained an out-pointer, a new memory-creator callback shape, GuestProfiler module sets, `wasmtime_tabletype_*`), and none is a name the runner reads (EXECUTED: a diff of the two installed packages).
- **0.1.5's binaries load unchanged.** `wasmtime.Module.validate` accepts `python.wasm` and `python-snapshot.wasm` from the 0.1.5 wheel under wasmtime-py 51.0.0 (EXECUTED).
- **File output is still written on the guest's thread.** The seam's bump steps ask for this to be checked again at every major. `OutputFile::write` still calls `write_all` on the file directly (READ: `crates/wasi/src/cli/file.rs` at `v51.0.0`).
- **A write larger than the stream's budget now traps.** wasmtime 51 adds a check to `OutputFile::write` (above `MAX_READ_SIZE_ALLOC`) and to the C API's `CustomOutputStream::write` (above 64 KiB), both `StreamError::Trap("write exceeded budget")` (READ: `git diff v50.0.1 v51.0.0 -- crates/wasi/src/cli/file.rs crates/c-api/src/wasi.rs`). WASIp1's `fd_write` asks `check_write` first, so a guest's large write should be split, not trapped (INFERRED). The output checks with large writes, on both captures, are the evidence.
- **Removing a folder named with a trailing slash changed** (READ: the release notes, #14662 and #14663). The runner forwards `path_remove_directory` on a plain grant and answers it itself on a mount by Linux's reference (READ: `_fs_paths.py`, `_namespace`). The slash rows of the sandbox and parity checks may record a new answer per system.
- **`poll_oneoff` drops its temporary streams explicitly** (READ: `crates/wasi/src/p1.rs`). The runner shadows `poll_oneoff` (spec 140) and compares some rows with wasmtime's own. No change is expected (INFERRED).
- **Fuel.** Fuel is never compared across wasmtime versions (spec 002, Decision 6), so every metered check is recorded fresh under 51.0.0.
- **Not used by the runner:** the component model and its async fixes, wasi-http and `wasmtime serve`, GuestProfiler, filling unknown imports with defaults, Cranelift's 128-bit atomics and `interrupt_poll`, the fiber limit (no async), and the new WASI buffer-size settings, which wasmtime-py 51.0.0 does not expose (EXECUTED: no such binding in `_bindings.py`).

## 5. The GC proposal is on, and off loses nothing found yet

- The runner's engines leave wasmtime's default, under which the GC proposal is enabled. A module declaring `(type (struct))` loads on 50 and 51 (EXECUTED).
- With `Config.wasm_gc = False` on wasmtime-py 51.0.0, toy modules with a tag, `throw`, `try_table` and an `exnref` parameter still load, and a GC struct type is refused. Both 0.1.5 binaries validate, with GC on and with it off (EXECUTED).
- The owner asked for a fuller probe before deciding (`decisions.md`, 2026-11-22): `2026-11-22-the-gc-proposal-off-under-wasmtime-51.md`.

## 6. The build's command line must move too

`tests/checks/test_rules.py::test_the_builds_wasmtime_is_the_runners_line` holds the three `*_WASMTIME_DIR` folders of `scripts/line.conf` on the runner's major (READ). Moving the pin to 51 moves the CLI to 51.0.0. That gives new archives in `downloads/SHA256SUMS`, a snapshot made by `wasmtime wizer` 51.0.0, and so new artifact bytes. That is build-class work under constitution §5.6 (INFERRED from 0.1.3's move, `decisions.md`, "the pins").

## One line

wasmtime-py 51.0.0 is the only wasmtime-py that closes a High Windows sandbox escape which 0.1.5's runner very likely forwards to, and the move costs a seam that already fits, a CLI that must follow, and fresh fuel.
