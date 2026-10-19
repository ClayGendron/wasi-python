- **Project:** wasmtime-py (https://github.com/bytecodealliance/wasmtime-py)
- **Against:** 49.0.0 (the release `uv.lock` pins; PyPI's only 49 release, uploaded 2026-09-21)
- **Status:** drafted
- **Title:** A wasmtime-py 49.0.x release on wasmtime 49.0.3 (security fixes since 49.0.0)
- **Files:** ci/download-wasmtime.py, VERSION
- **Why we need it:** the runner's guests run on wasmtime 49.0.0, whose `fd_readdir` copies uninitialized host memory into the guest (GHSA-96f6-r43r-8c24, fixed in wasmtime 49.0.2); no wasmtime-py release carries a fixed wasmtime.

**This is a facts sheet, not an issue or a pull request** (question 80 in
`context/questions-for-the-owner.md`). wasmtime-py is a Bytecode Alliance project. Wasmtime's
own `AGENTS.md` (READ, tag `v49.0.3`) applies the Bytecode Alliance AI Tool Use Policy: agents
never open pull requests, never comment on issues or pull requests, and are never listed as
co-authors; those are done manually by humans. wasmtime-py's `CONTRIBUTING.md` (READ, `280ce73`)
names no policy of its own and says it is a Bytecode Alliance project, so the same policy is
taken to apply (INFERRED). Whether to ask, and the words, are the owner's. Nothing has been
posted, and no agent will post anything.

## The facts

1. **wasmtime-py 49.0.0 bundles wasmtime 49.0.0.** `ci/download-wasmtime.py` sets
   `WASMTIME_VERSION = "v49.0.0"` and `VERSION` is `49.0.0` (READ, `280ce73`). PyPI lists 48.0.0
   and 49.0.0 and nothing later (EXECUTED 2026-10-18, PyPI's JSON API).
2. **Wasmtime has fixed security advisories since 49.0.0** (READ, `RELEASES.md` at `v49.0.3`):
   49.0.2 (2026-10-02) lists `fd_readdir copies uninitialized struct padding into guest memory`
   (GHSA-96f6-r43r-8c24) among others; 49.0.3 (2026-10-14) lists fifteen, among them `Filesystem
   sandbox escape when renaming symlinks with trailing slashes` (GHSA-m9f7-9w4p-gv38).
3. **The padding is visible from a guest.** On wasmtime-py 49.0.0, a read-only preopen's
   `fd_readdir` into a buffer zeroed before each call wrote a non-zero byte after `d_type` in
   995 of 1,000 calls on darwin-arm64 (`evidence/padding.txt`, `evidence/padding.py`: always in
   the `..` entry, the byte 0x04); a GitHub Actions macOS arm64 runner wrote 0x60 after the `.`
   entry's `d_type` (`evidence/ci-39097514484.txt`, run 39097514484). Three bytes per entry of
   whatever the host's buffer held reach the guest. In wasmtime 49.0.3's source the dirent is a
   zeroed `vec![0; 24]` reused for every entry (READ, `crates/wasi/src/p1.rs:2010-2019`), so the
   fix is in the library, and only a wasmtime-py release can carry it to Python embedders.
4. **What would close it:** a wasmtime-py release whose `ci/download-wasmtime.py` fetches
   `v49.0.3` (or a 50 release); the C API used by wasmtime-py did not change in a patch release
   (INFERRED from wasmtime's versioning).
   When `uv.lock` moves to such a release, `tests/harness/files.py`'s `DIRENT_MASKED` drops
   the padding bytes, so the parity compares them again.
5. **On Windows, wasmtime 49.0.0 renames a file named with a trailing slash; 49.0.3 refuses it**
   (spec 076, cause 4). 49.0.0's `crates/wasi/src/filesystem/primitives/via_parent/rename.rs`
   strips a trailing slash from both paths and puts the source's back only under
   `#[cfg(unix)]` (lines 22-26 and 33-42, READ, the crate from the cargo registry); on Windows
   it renames by `std::fs::rename` of the two full paths with no kind check
   (`primitives/windows/fs/rename_unchecked.rs`, READ). So `path_rename("f/", "e")` of a file
   `f` renames it. 49.0.3 checks, on every system but Linux, that the source is a folder when
   either path ends in `/`, without following, and answers `ENOTDIR` (the same file, lines
   25-27 and 55-60, READ). The runner's guard carries 49.0.3's rule (spec 048), so a guest of
   the runner already gets `ENOTDIR`. Seen on GitHub's `windows-2025-vs2026` image, version
   20261007.264.1, in spec 063's branch dry runs 39182550825, 39184807592 and 39186533835: a
   loop of such renames on wasmtime-py 49.0.0 alone ended `ENOENT` (the file renamed, then a
   folder renamed over it, then the source missing), where the guard's ended `ENOTDIR`
   (EXECUTED there). A wasmtime-py on 49.0.3 would end the difference; the check that states
   it per system (`NATIVE_RENAME_END` in `tests/unit/test_runner_mounts.py`) then fails and
   loses its Windows value, with a reason.

## What the owner might ask

Whether wasmtime-py plans a release on wasmtime 49.0.3, or on 50.0, and when. Advisories are
public; this is not a new vulnerability report, so wasmtime's private reporting form
(`SECURITY.md`) does not apply (INFERRED).
