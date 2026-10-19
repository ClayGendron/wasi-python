- **Project:** Wasmtime (https://github.com/bytecodealliance/wasmtime), crate `wasmtime-wasi`
- **Against:** 49.0.0 (the wasmtime wasmtime-py 49.0.0 bundles), 49.0.3 (tag `v49.0.3`,
  `f96eaba`) and main `2d9c19b`; the same in all three
- **Status:** drafted
- **Title:** preview1 `fd_write` and `fd_read` pass the host's error for a descriptor used in a mode it was not opened for: `EBADF` on Unix, `EACCES` on Windows
- **Files:** crates/wasi/src/p1.rs, crates/wasi/src/filesystem.rs
- **Why we ask:** nothing waits on it. The runner states the difference per system (spec 076,
  Decision 4) and refuses to relabel it, because that would put a host round trip on the guest's
  hottest calls. A guest's code would behave the same on every host if Wasmtime answered
  `EBADF` everywhere, as POSIX does.

**This is a facts sheet, not an issue or a pull request** (question 80 in
`context/questions-for-the-owner.md`). Wasmtime's own `AGENTS.md` (READ, tag `v49.0.3`) applies
the Bytecode Alliance AI Tool Use Policy: agents never open pull requests or comment on issues;
those are done by humans. Whether to ask, and the words, are the owner's. Nothing has been
posted, and no agent will post anything.

## The facts

1. **preview1 checks neither the grant's permissions nor the descriptor's open mode** (READ).
   `fd_write_impl` (49.0.0 `crates/wasi/src/p1.rs:626-695`; 49.0.3 `p1.rs:625-694`; main
   `2d9c19b` `p1.rs:625`) takes the file from the table and writes through the host's file,
   with no check of `perms` or `open_mode`. `fd_read` is built the same way (49.0.3
   `p1.rs:1665-1720`). The host's `io::Error` becomes the guest's errno through
   `ErrorCode::from(&io::Error)` (49.0.0 `p1.rs:904-918`).
2. **So the guest sees the host's number** (EXECUTED on macOS; seen on Windows). On Linux and
   macOS, `write(2)` on a descriptor opened only to read, and `read(2)` on one opened only to
   write, give `EBADF`, preview1's 8 (spec 076's pre-build review, `probe_read_twin.py`, and
   the unit case `test_a_read_only_grant_refuses_raw_writes`). On Windows, `WriteFile` on a
   handle without write access gives `ERROR_ACCESS_DENIED`, which Wasmtime maps to
   `ErrorCode::Access`, preview1's `EACCES`, 2 (49.0.0 and 49.0.3 `crates/wasi/src/
   filesystem.rs:434`, READ). Seen as 2 on GitHub's `windows-2025-vs2026` image in spec 063's
   branch dry runs 39182550825, 39184807592 and 39186533835 (EXECUTED there); the read twin is
   observed by spec 076's Windows dry run.
3. **preview2 checks the grant's permissions only** (READ). Its `write` answers `NotPermitted`
   on a read-only grant (49.0.0 `crates/wasi/src/p2/host/filesystem.rs:141`); `open_mode`
   feeds only `get_flags` (49.0.0 `filesystem.rs:543-556`), so on a writable grant preview2
   also passes the host's error for a descriptor opened only to read.
4. **Wasmtime already smooths one such Windows difference** (READ). `sync_data` ignores
   Windows' `ERROR_ACCESS_DENIED` from `FlushFileBuffers` on a file not open for writing, for
   POSIX compatibility (49.0.0 `crates/wasi/src/filesystem.rs:509-520`).
5. **Every write is still refused.** This is an error number, not a hole: the descriptor's
   host handle has no write access, so the host refuses the write on every system.

## What the owner might ask

Whether Wasmtime would answer `EBADF` (preview1) or `BadDescriptor` for a write through a
descriptor opened without write, and a read through one opened without read, on every host,
from the `open_mode` it already records, as `sync_data` already smooths Windows' answer.
