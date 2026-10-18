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

## What the owner might ask

Whether wasmtime-py plans a release on wasmtime 49.0.3, or on 50.0, and when. Advisories are
public; this is not a new vulnerability report, so wasmtime's private reporting form
(`SECURITY.md`) does not apply (INFERRED).
