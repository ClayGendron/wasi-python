# 032 — A filesystem provider (read-only mounts)

- **Status:** built 2026-10-17 (Landing notes), awaiting its build review, which is also a
  security review (acceptance 15). Reviewed before build
  (`../reviews/032-a-filesystem-provider-spec-2026-10-17.md`, which is also a security review of
  the design), revised against its ten findings (its Disposition), and confirmed on 2026-10-17
  with conditions N1 and N2 and builder notes N3 (its Confirmation), all written in here.
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`; a new `src/wasi_python/mounts.py`),
  `src/wasi_python/__init__.py`'s exports, judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`. **Not build-class:** it touches no `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or release workflow. What runs where: the Python-level checks in
  `tests/checks/test_v1_4_embedding.py` and the raw parity cases in
  `tests/unit/test_runner_grants.py` run on Windows, Linux and macOS, because the `verify` job
  already runs those two files. The fault, guard and descriptor checks
  (`tests/checks/test_v1_2_hostile_guest.py`, `tests/unit/test_runner_mounts.py`) run on the
  judge's machine only; they test the runner's own code, which does not depend on the host.
- **Depends on:** 011 (shared host functions, found by the thread's call stack), 015 (`cancel`,
  the epoch callback, `call.ended`), 017 (typed grants: `_guest_path`, the preopens, the identity
  check), 025 (nothing writable by default), all landed; 030 (a cancel during a door call is
  named), confirmed for build: 032 lands after it and amends its invariant (Decision 9). Spec
  031 (the tool protocol) also adds a limit to `Defaults` and a record to `Completed`; neither
  depends on the other, and the lane rebases whichever lands second.
- **Research it stands on:** `../research/2026-10-17-a-filesystem-provider-for-the-runner.md`
  and its evidence folder (`shadow.py`, the model; `imports.txt`, `provider.txt`,
  `dot_path.txt`, `cost.txt`, `async_cancel.txt`); the pre-build review's probes
  (`raw_answers`, `grant_paths`, `iovecs`, `reserve_limit`, `forward_trap`; EXECUTED there,
  cited by the review). Where this specification departs from the memo, the decision says so
  and why.
- **Decided by:** the owner's answers (`../decisions.md`): 13 (vfs runs on this runner, which
  needs a filesystem provider; this project never edits vfs); 37's study of vfs (a denial is a
  result, never an exception; vfs counts calls and records refused writes); 41 (a mount at `/`,
  exclusive with `root=`; the zip stays at `/usr/local/lib`); 42 (10,000 provider calls per run
  by default; at the limit the run stops and the result names it); 17 (governance is the
  embedder's; the runner offers the hook); 24 (nothing writable by default).

## The problem

An embedder can hand a guest host folders (spec 017) and nothing else. It cannot serve the
guest's files from its own code: a database, an object store, a permission layer. vfs needs
exactly that to run its guests through `wasi_python.run` (decision 13). Today it would have to
copy everything into a folder before the run and read the changes back after. That gives up
checking each access, which is the reason vfs exists.

The memo shows a way that adds no import (EXECUTED on both binaries). Shadow the guest's file
calls. Serve the ones on a provider's files from embedder code. Forward every other call to
wasmtime's own WASI.

This specification builds that mechanism for **read-only** mounts. Writes are spec 034
(Scope).

## Terms

- **Provider:** an object the embedder passes that answers file operations from its own code.
  Its authority is bound in by the embedder before the call.
- **Mount:** a provider placed at a guest path, as a grant places a host folder.
- **Shadow:** a host function defined over one of wasmtime's own WASI functions, through
  `Linker.allow_shadowing`. The runner already shadows `poll_oneoff`.
- **Forward:** a shadow handing a call it does not own to wasmtime's own WASI.
- **Trampoline:** a tiny wasm module the runner compiles. Its functions call wasmtime's WASI on
  the guest's memory. It is how a forward reaches wasmtime.
- **Placeholder:** an empty, read-only folder the runner owns. Each mount's own preopen is made
  on it, so wasi-libc's preopen scan finds the mount.
- **Provider number:** the descriptor number the runner gives a file or folder opened in a
  mount. It is taken from a high range wasmtime never reaches.
- **Staging:** reading a whole file into host memory at open and serving reads from that buffer.

## Decisions

1. **The mechanism is the memo's (findings 2 and 3), with the review's two changes: provider
   numbers come from a high range, and a forward's trap is the shared function's.**
   - **A second linker, only for calls with mounts.** Per engine, beside today's `_linker`: WASI,
     `allow_shadowing`, the shadowed `poll_oneoff`, the door, and one shadow for each of the
     **29 preview1 calls that act on a descriptor and are not forward-safe**: the 26 file calls
     the guest imports (memo finding 1: 16 on a descriptor, 10 on a path), and `fd_renumber`,
     `fd_allocate` and `fd_fdstat_set_rights`, which today's binaries do not import. Shadowing
     those three costs nothing and keeps a later binary from reaching a provider number
     unseen. A call without mounts uses today's linker object unchanged, so its fuel and
     behaviour are today's exactly.
   - **The forward-safe list is short and reviewed:** `fd_prestat_get`, `fd_prestat_dir_name`,
     the four `sock_*` calls, and `poll_oneoff` (already the runner's, answering by number only).
     On a provider number each answers `EBADF`, or as `poll_oneoff` answers any descriptor; on a
     mount's preopen, wasmtime answers as it does for a grant's (review, `raw_answers.txt`).
     A unit check reads each binary's preview1 imports: every import that takes a descriptor is
     shadowed or on this list, so a new import fails the judge (finding 4).
   - **Each shadow is `_shared`'s form (spec 011),** with `refused` `EBADF` (8) and `stopped`
     `EIO` (29). It finds its call on the thread's stack, serves only that call's store, and
     never raises into wasmtime-py except as Decision 1's trap rule says. A call naming a number
     the call's mount table does not hold is forwarded. `path_rename` and `path_link` name two
     descriptors; `path_symlink` names its descriptor third.
   - **Forwards go through a trampoline.** wasmtime's WASI finds guest memory through the
     calling instance's `memory` export (memo finding 3, READ). The trampoline imports the 29
     originals and the guest's memory, re-exports that memory, and exports one forwarder per
     call. It is compiled once per engine. It is instantiated per call, after the guest and
     before the fuel cap is set and `_initialize` runs, with the guest's own memory and the
     originals taken from today's linker (`Linker.get`), whose file calls are wasmtime's.
     Instantiating it defines no Python callback (decision 11's race is in `define_func` and
     custom output).
   - **A forward runs on the caller's context, with per-call state.** It calls
     `_ffi.wasmtime_func_call` with `caller._context()`, as the epoch code already uses `_ffi`
     under the `<50` pin; it is three times faster than `Func.__call__` (memo finding 5, a
     benchmark fact, never a check). **A forward never goes through `Func.__call__`:** its
     `enter_wasm` reads wasmtime-py's process-wide exception slot (`maybe_raise_last_exn`,
     `wasmtime/_func.py:231-250`, READ) and could raise another thread's exception (spec 011;
     the confirmation's N3). The trampoline's function handles and the argument and
     result arrays live on the call's `_Call`, never on the engine: a function of one store used
     with another store's context aborts the process (INFERRED, wasmtime's store checks), and a
     shared array would race between threads.
   - **A forward's trap is raised, as `_door` raises `host_alloc`'s (finding 1).** A forward is
     guest-side wasm: its entry is an epoch check, and wasmtime answers an out-of-bounds guest
     pointer with an error, not `EFAULT` (review, EXECUTED: `forward_trap.txt`, `iovecs.txt`). A
     trap or error that `wasmtime_func_call` returns is taken into wasmtime-py's own `Trap` or
     `WasmtimeError` (`_from_ptr`, which owns and frees it) and raised to the shared function.
     So, with spec 030, a cancel or a deadline under `cancel=` is named from `call.ended`, and
     anything else is recorded as the call's stop and named by `_drive` as today. A guest that
     passes a bad pointer to a grant's descriptor in a mounted call ends as it ends without
     mounts.
   - **A forward is fuel-neutral.** On a metered call the shadow reads the store's fuel, adds a
     fixed allowance for the trampoline's few instructions, forwards, and sets the fuel back to
     what it read (`wasmtime_context_get_fuel` and `_set_fuel` on the caller's context). The
     confirmation ran it on wasmtime 49 (EXECUTED, `fuel_neutral.txt`): `set_fuel` during a host
     call works, 1,000 neutral forwards cost exactly what wasmtime's own WASI costs (17,005
     against 21,005 without neutrality), and every cap tried ends the same way as today. So no
     `OUT_OF_FUEL` can occur inside a forward, `fuel_used` counts only the guest's own
     instructions (spec 008's rule), and a guest out of fuel traps at its own next check, as it
     does without mounts. Three rules (N3): the fuel is read and set **only on a metered call**
     (`wasmtime_context_get_fuel` errs on an engine without fuel); it is set back in a
     **`finally`, before any trap or error is raised**, so a bad-pointer ending keeps today's
     fuel; and the allowance need only cover the trampoline's few instructions (a larger
     constant is harmless, since the fuel is set back).
   - **One placeholder per call.** An empty folder `mount` inside the call's own private scratch
     folder (the `0700`, locked folder that holds `stdin`, spec 016). `_instance` makes the
     scratch folder and the placeholder before its `preopen_dir` loop (today it makes the scratch
     folder after). Every mount is `preopen_dir(placeholder, guest, False)`, after the stdlib
     folder, the root and the grants. The placeholder is walked with `judge=False` like the
     stdlib folder, checked by identity like every preopen (spec 017, Decision 5), and removed
     with the scratch folder. It lies under the temporary folder, which no grant may be at or
     above, so no grant can reach it.
   - **The identity check runs on today's linker,** so it reads wasmtime's own answers for every
     preopen, placeholders included, never a shadow's.
   - **Provider numbers come from a high range (finding 2).** A file or folder opened in a mount
     gets the lowest free number from `2**30` up, kept in the call's mount table. wasmtime hands
     out the lowest freed number, else one above its highest in use (`p1.rs:434-466`, READ), and
     each of its numbers costs a host handle, so it never reaches `2**30`. A provider number
     costs no host handle, and nothing in wasmtime's table. This replaces the memo's reservation
     (`path_open(".")` on the placeholder), which cost one host descriptor per provider file: the
     review saw hosts refuse after 249 at a soft limit of 256 and after 1,017 at 1,024
     (`reserve_limit.txt`). The trade is POSIX's lowest-number rule: `fileno()` of a mount's file
     is above `2**30`. CPython passes such numbers to the host for `os.fstat`, `os.read` and
     `open(fd)`, and `select.poll` and `selectors.DefaultSelector` (a `PollSelector`, which
     `asyncio` uses) accept them (EXECUTED, the confirmation's `high_numbers.txt`, both
     binaries). `select.select` does not: CPython refuses any number from 1,024 (`FD_SETSIZE`)
     in the guest, with `ValueError`, before the runner sees it (N1). That is a deliberate
     difference (Decision 6), not a reason to lower the base: any number wasmtime can reach
     would bring back the collision the high range avoids. Acceptance 1 opens, reads, scans and
     polls on such numbers.
   - **The table drops a number exactly when the guest closes it.** `fd_close` on a provider
     number frees it. `fd_close` on a mount's own preopen is forwarded, so wasmtime frees that
     number, and the table drops the preopen in the same step; wasmtime may reuse the number for
     any later open, which then is not the mount's. `fd_renumber`, when either number is in the
     table or at or above `2**30`, answers `ENOTSUP` (58) and changes nothing; otherwise it is
     forwarded (finding 4; `raw_answers.txt` shows a forwarded renumber silently replacing the
     target).
   - **If a forward ever carried a provider number by mistake,** wasmtime would answer `EBADF`:
     the number is not in its table. A mount's own preopen is an empty, read-only folder the
     runner owns.
   - **No host path is opened for a mount.** The provider names no host path, and the runner
     opens none for it. The only host folder involved is the runner's own empty placeholder,
     and it costs one host handle per mount, not per file.
2. **`Mount` and `mounts=`.**
   - `Mount(provider, guest)`, a frozen dataclass exported from `wasi_python`. `run` and
     `run_async` take `mounts: Iterable[Mount] = ()`, made a tuple when checked, as `grants`
     is. Spec 034 adds `writable=False`.
   - **Checked before any work** (`TypeError` for a type, `ValueError` for a value; each message
     names the mount's position and guest path, as spec 017's do):
     - `mounts` is an iterable of `Mount`, not a `str` and not one `Mount`;
     - `provider` has callable `stat`, `list` and `read`. A coroutine function among them is
       refused: async providers are a later specification (question 15);
     - `guest` follows `_guest_path`'s rules (absolute; no NUL; no empty, `.` or `..` part; no
       trailing `/`; not at or under `/usr/local/lib`), except that `/` is allowed;
     - no two mounts, and no mount and grant, share a guest path. Nesting is allowed either way:
       a grant inside a mount, a mount inside a grant, a mount inside a mount;
     - a mount at `/` is refused with `root=True` or a root path (decision 41).
   - **`HOME`.** The runner makes no `HOME` in a mount. A mount at `/tmp` counts as a read-only
     grant at `/tmp` does in spec 017's Decision 3: then there is no `HOME`. A mount at `/`
     comes without a root, so `HOME` exists only in a writable grant at `/tmp`. `TMPDIR` stays
     `/tmp`. An embedder may pass `HOME` in `env`.
   - **A mount at `/` makes the embedder the guest's whole filesystem** (decision 41), except
     what more specific preopens own: the stdlib zip at `/usr/local/lib`, every grant, every
     other mount. Relative paths resolve against `/`, so they reach the provider. The runner
     adds nothing to the provider's listings: a provider that wants `/usr` listed lists it.
3. **The provider protocol.** A provider answers; it does not raise. A denial is a value
   (vfs's rule, decision 37). This departs from the memo, which proposed raising `OSError`:
   with values, an embedder whose layer never raises sits behind the runner as it is, an
   exception always means a bug (Decision 4), and no host's `errno` numbering enters the runner
   (an `OSError`'s `errno` differs between Windows and POSIX; §4.3). Question 54 asks the owner
   to confirm; the review agrees.

   ```python
   class FileProvider(Protocol):              # exported for type checkers
       def stat(self, path: str) -> Stat | Errno: ...
       def list(self, path: str) -> Iterable[tuple[str, str]] | Errno: ...  # (name, "file"|"dir")
       def read(self, path: str) -> bytes | bytearray | memoryview | Errno: ...  # the whole file

   @dataclass(frozen=True)
   class Stat:
       kind: str          # "file" or "dir"
       size: int = 0      # bytes, 0 to 2**63 - 1; a bool is refused
       mtime_ns: int = 0  # 0 to 2**64 - 1; a bool is refused

   run(argv, mounts=[Mount(files, "/work")], grants=[Grant(data, "/data")])
   ```

   - **Paths are absolute within the mount;** `/` is the mount itself. Under a mount at `/`,
     the provider's path is the guest's. Every path reaches the provider normalized
     (Decision 5).
   - **`read`'s contract:** it answers `EISDIR` when the path itself is a folder, and `ENOTDIR`
     when a parent is a file. The runner makes a folder descriptor only from `EISDIR`
     (finding 10).
   - **`Errno`** is an `enum.IntEnum` exported from `wasi_python`. Its values are WASI
     preview1's numbers (READ, `wasi-libc/libc-bottom-half/headers/public/wasi/wasip1.h`), so
     the runner passes them to the guest unchanged and never interprets them: EACCES 2, EBUSY
     10, ECANCELED 11, EDQUOT 19, EEXIST 20, EFBIG 22, EINVAL 28, EIO 29, EISDIR 31,
     ENAMETOOLONG 37, ENOENT 44, ENOSPC 51, ENOSYS 52, ENOTDIR 54, ENOTEMPTY 55, ENOTSUP 58,
     EPERM 63, EROFS 69, ESTALE 72, ETIMEDOUT 73, EXDEV 75. The set is closed: no success, no
     `EINTR` or `EAGAIN` that would make the guest's C library retry, no `EBADF` or `EFAULT`,
     which describe the guest's own arguments. It covers every errno in vfs's table
     (`169…/spec.md` §b7), which is already in preview1 numbering. A vfs adapter maps its kinds
     through that table, with one rule of its own: `wrong_kind` on the target itself is
     `EISDIR`, as vfs's shim already decides (§b4), not the table's `ENOTDIR`.
   - **The runner knows nothing about permissions.** Within a mount it calls the provider for
     every access and passes its answer through. Whether `EACCES` means a policy, a missing
     login or a budget is the embedder's business (decision 17).
   - **At most one provider call per open** (169b's table, `169…/spec.md` §b4):

     | the guest's `path_open` | provider call | answer |
     |---|---|---|
     | asks to write: `oflags` holding `CREAT` or `TRUNC`, or `fs_rights_base` holding `FD_WRITE` (wasmtime 49's test, `crates/wasi/src/p1.rs:2156-2210`, READ) | none | a read-only grant's answer (Decision 6) |
     | the call already holds `MAX_MOUNT_FILES` provider numbers | none, and none counted | `EMFILE` (33) |
     | `O_DIRECTORY` | one `list` | the listing is kept for the descriptor; an `Errno` passes through |
     | anything else | one `read` | the bytes are staged; `EISDIR` makes a folder descriptor, listed at its first `fd_readdir`; another `Errno` passes through |

   - **The write half is reserved for spec 034:** `write(path, data)`, `mkdir(path)`,
     `remove(path)`, `rmdir(path)`, `rename(src, dst)`, each answering `None` or an `Errno`.
     This specification never calls them, and a read-only mount never will.
   - **No cache across opens.** Two opens of one path make two `read`s. A provider may cache.
4. **An exception or a bad answer is a fault, never an escape.** As `_door` maps a host's
   exception to `HOST_FAULT`:
   - an `Exception` raised while the runner handles a provider's answer, from the method itself,
     from iterating its listing or from reading its buffer, or an answer of the wrong type, gives
     the guest `EIO` and adds a `FileFault` to the record. The run goes on. Iteration and buffer
     reads run inside the same boundary as the call, since both can run provider code;
   - a bad answer is any value outside the method's annotation; a `Stat` with a `kind` other
     than `"file"` or `"dir"`, or a `size` or `mtime_ns` that is a `bool`, not an `int`, or out
     of range; a listing name that is not a `str`, is empty, `.` or `..`, holds `/` or NUL,
     cannot be encoded as UTF-8 (a lone surrogate), is over 255 bytes in UTF-8, or repeats; a
     listing kind other than `"file"` or `"dir"`; a `Stat` for `/` whose kind is not `"dir"`;
     or an awaitable (closed at once, so it never warns);
   - a `BaseException` that is not an `Exception` (Ctrl-C, `SystemExit`) is recorded as the
     call's stop and raised from `run` on the calling thread, exactly as the door's is
     (spec 011);
   - nothing a provider does reaches wasmtime-py's exception slot.
5. **Paths: the runner normalizes; the provider never does.** For every path argument, in
   order:
   - its pointer and length are checked against the memory's size before a byte is read
     (`EFAULT`), as `_door` and `_poll_oneoff` check theirs, with each `i32` taken unsigned;
   - a path over 4,096 bytes is `ENAMETOOLONG`, without being read;
   - an empty path is `ENOENT`; a path that starts with `/` (given to a descriptor) is `EPERM`;
   - it must be UTF-8 (else `EILSEQ`, 25) without NUL (else `EINVAL`), as wasmtime answers.
     As built (the build review, F4.3): the UTF-8 is judged when the path is read, before the
     empty and leading-`/` rules, as wasmtime decodes it, so a path both absolute and not UTF-8
     is `EILSEQ`, and a write-shaped call's bad UTF-8 is `EILSEQ` as on a grant;
   - a component over 255 bytes is `ENAMETOOLONG`; `.` and empty components are dropped;
   - `..` resolves by text, and if it climbs above the folder of the descriptor the call names,
     even for a moment, the answer is `EPERM` (63), what wasmtime answers on a grant (memo
     finding 7, EXECUTED; cap-std confines each handle to its own folder);
   - a path that ends in `/` or `/.` names a folder: if the provider says it is a file, the
     answer is `ENOTDIR`, as a grant's (`a.txt/.` is 54, `grant_paths.txt`);
   - a normalized path at or under a more specific preopen's guest path (the zip's, a grant's,
     another mount's) is `EPERM`, with no provider call. Only the guest can spell one
     (`/usr/./local/lib` under a mount at `/`), and wasi-libc matched it to this mount by text
     (memo finding 7). Refusing it is the simple rule.

   The provider receives only the normalized `str`.
6. **A read-only mount answers as a read-only grant does, except where this table says.** The
   reference is wasmtime 49 on Linux. For each of the 29 shadowed calls, on a provider file, a
   provider folder and a mount's own preopen, the runner gives what wasmtime gives on a
   read-only grant's file, folder and preopen with the same arguments: the errno and every byte
   it writes to the guest (counts, filetypes, sizes, offsets, `fd_readdir`'s buffer), with
   `dev`, `ino`, times and descriptor numbers left out. What the review already shows: every
   write-shaped call answers `EPERM` (63) on a read-only grant, so on a read-only mount it does
   too, before any provider call; `fd_advise` and `fd_fdstat_set_flags` answer as a grant's file
   or folder answers (on a file 0, but 28 for `SYNC`; on a folder 8; `raw_answers.txt`); a
   vectored read fills only the first non-empty `iovec`, as wasmtime does (`p1.rs:203-219`);
   `readlink` of a file or folder is `EINVAL`.

   The deliberate differences, each safer or simpler, none a way out of the mount:

   | input | a read-only grant (wasmtime) | a read-only mount | why |
   |---|---|---|---|
   | `..` after a missing name or a file (`missing/../b.txt`, `a.txt/../b.txt`) | `ENOENT`, `ENOTDIR`: it walks each part | resolved by text | one provider call per operation, on one normalized path; it also tells the guest less (a grant reveals whether `missing` exists) |
   | the same, on a Windows grant (after landing) | resolved by text too: cap-std's own Windows open drops each `..` with the name before it before any lookup (READ, cap-primitives 4.0.3 `src/fs/manually/open.rs`); `missing/../a.txt` and `a.txt/../b.txt` open their file (0; the first EXECUTED in release dry run 39105048310) | resolved by text | no difference on Windows: the mount and a Windows grant agree; the row above is POSIX's |
   | a path over 4,096 bytes | depends on the host (`ENOENT` on macOS) | `ENAMETOOLONG`, unread | bounded work, the same on every host |
   | a guest pointer past memory | an error that ends the run | `EFAULT` | the runner's own answer, as `poll_oneoff`'s; no trap path in provider code |
   | more than 1,024 `iovec`s | accepted | `EINVAL` | bounded work |
   | letter case | the host's (macOS ignores it) | the provider's | the provider owns its names |
   | `sock_*`, `fd_prestat_dir_name` on a provider number | `ENOTSOCK` (57), `ENOTDIR` (54) on a file | `EBADF` (8) | forward-safe calls; the number is not wasmtime's |
   | `fileno()` of an opened file | the lowest free number | `2**30` or above | no host handle per file (Decision 1) |
   | `select.select` on an opened file | accepted (a low number) | `ValueError` in the guest (`FD_SETSIZE` is 1,024); `select.poll` and `selectors` work | the high range; CPython refuses before the runner sees it |
   | a later `iovec` past memory, after a non-empty one (build review, F4.1) | read: wasmtime checks only up to the first non-empty `iovec` | `EFAULT` | every `iovec` is checked (Decision 7) |
   | `path_filestat_get` without `SYMLINK_FOLLOW` (`os.lstat`) of a file with a trailing `/` or `/.` (`a.txt/`, `a.txt/.`; after landing) | Linux: the file's stat (INFERRED: cap-std's no-follow stat drops the slash; the same stat following links, and an open, are `ENOTDIR`); macOS: `ENOTDIR` | `ENOTDIR` | the path names a folder (POSIX), as Linux's own grant answers when it follows links and as an open answers everywhere; one answer, not two |
   | the three padding bytes after each `fd_readdir` entry's `d_type` (after landing) | whatever wasmtime 49.0.0's buffer held: uninitialized host memory (GHSA-96f6-r43r-8c24, fixed in wasmtime 49.0.2) | zeros | the runner encodes every entry itself; the parity compares the fields, not the padding |
   | an argument the ABI cannot carry: an undefined flag or enum value, an integer out of its type's range, a misaligned pointer (build review, F4.2) | the run ends; `trapped` is `error while executing at wasm backtrace:` | the run ends, with the same `fuel_used`; `trapped` is wiggle's own text, such as `Invalid flag value Oflags` | the runner raises the error itself, as the call's stop |

   The runner adds what a grant cannot say:
   - `path_filestat_get` is one `stat`. `fd_filestat_get` on an open provider file needs no
     call: its kind and size come from the staged bytes, and its times are 0 (one call per
     open; the README says `os.fstat` shows no time). A mount's preopen is a folder.
   - `dev` is `_siphash13` (the zero-keyed hash `_wasi_ino` uses) of the mount's guest path,
     and `ino` of the provider path, both as UTF-8, so `os.path.samefile` and `shutil`'s
     same-file check work and a run repeats exactly; never Python's `hash()`, which changes per
     process. `nlink` is 1.
   - `fd_readdir` serves `.`, `..` and the provider's names with wasmtime's cookie protocol. The
     listing made at open serves the first pass; a `fd_readdir` from cookie 0 after that lists
     again, as `rewinddir` expects.
   - `path_readlink` is one `stat`: a file or folder answers `EINVAL` (not a link), else the
     `stat`'s `Errno`.
   - A call naming a provider number and a descriptor that is not this mount's (a rename or a
     link across) answers what the same call across two read-only grants answers.

   A row whose grant answer differs between Linux, macOS and Windows is asserted per system or
   left out, and the landing notes name it.
7. **Guest memory is checked before it is touched.** Every pointer and length the guest passes
   to a provider-served call (paths, `iovec` arrays and each `iovec`, `fd_readdir`'s buffer,
   every result pointer) is checked against the memory's size first, and the call answers
   `EFAULT` without a provider call if one runs past it. An `iovec` array of more than 1,024
   entries is `EINVAL`. Nothing the guest passes reaches the provider but a normalized path:
   offsets, flags, cookies, rights and pointers stop in the runner.
8. **Limits, each with a default (§4.15).**
   - **Provider calls (decision 42).** `run` and `run_async` take `max_file_calls`, an integer
     or `None`, checked by `_integer_limit`; its default is `DEFAULTS.file_calls`, 10,000, a new
     field of `Defaults`. Every provider method call counts, whatever it answers. The call
     that would pass the limit is not made: the shadow answers `EIO`, records `call.ended =
     "out of file calls"` if nothing ended the call first, and sets the store's epoch deadline
     to 0 in the same step. The guest stops at its next function entry, and `trapped` is `"out
     of file calls"`, `exit_code` and `fuel_used` are `None`, as for a cancel. `_epoch_answer`
     gains one rule after its recorded-stop check: a call whose `ended` is already set stops, so
     the first named end holds under `cancel=` too. Spec 030's entry guard then returns
     `stopped` for every later host call of that run.
   - **Open provider numbers:** at most 1,024 per call (`MAX_MOUNT_FILES`). The next open is
     `EMFILE` (33), checked before the provider is called, so it makes no call and counts none.
     No host handle is spent per file (Decision 1), so this bound holds whatever the host's
     descriptor limit is.
   - **Staged bytes:** the bytes of every open provider file plus every kept listing are at most
     the call's `memory_bytes`, or 4 GiB (wasm32's own ceiling, the most the guest itself can
     hold) when it is `None`. A listing is kept as its encoded preview1 entries (24 bytes and
     the name, each), so the count is what the runner holds. As built (the build review, F2):
     one buffer of the encoded entries and an array of where each starts, counted as the bytes
     allocated for both; while it is gathered the set that finds a repeated name is counted
     too. A `read` whose answer would pass
     the bound is `EFBIG` (22), judged on `memoryview(answer).nbytes` before any copy, and the
     answer is dropped; a listing is judged as it is gathered. The bound is on what the runner
     keeps, not on what the provider made: the README says a provider should refuse a large file
     before it reads it, as vfs judges on `size_bytes` first (`169…/spec.md` §b8). Question 55
     records this.
9. **Spec 030's invariant, amended.** 030's Decision 3 writes at the shared function's branch
   that `call.ended` is set only by the epoch callback, and only on a path that returns an
   error. This specification adds a second setter, the file-call limit, and changes that
   comment, when it lands, to: "`call.ended` is set only where the runner also stops the guest
   by its own act in the same step: by the epoch callback, on a path that returns an error; or
   by the file-call limit's shadow (spec 032), which sets the epoch deadline to 0 before it
   returns. So a `Trap` or `WasmtimeError` caught after `ended` is set is the runner's own stop
   surfacing." The branch stays correct: once `ended` is set, 030's entry guard keeps every
   later host function, forwards included, from running, so no other trap can reach the
   branch with `ended` set; and the limit's shadow raises nothing. Acceptance 5's run under
   `cancel=` shows it.
10. **Time, cancel and threads.**
    - A provider runs synchronously on the thread that runs the guest; under `run_async` that
      is a worker thread, never the event loop's.
    - Before each provider call the runner checks the call's `cancel` and its deadline (the
      ticker's count against `stop_at`). If either has passed, the provider is not called; the
      guest gets `ECANCELED` or `ETIMEDOUT` and stops at its next function entry, named
      `"cancelled"` or `"deadline"` as today. After the call, `_shared` already checks `cancel`.
    - A provider's own time is outside the epoch and cannot be interrupted (memo finding 8;
      vfs's ADR 084 says the same of its verbs). The README says a provider must bound its own
      calls, and that a deferred Ctrl-C on the main thread waits for a blocked provider, as it
      waits for a blocked door host today.
    - One provider may serve concurrent calls. The runner calls it from each call's thread; the
      README says a shared provider must be thread-safe.
    - An embedder whose layer is async may bridge from the worker thread with
      `asyncio.run_coroutine_threadsafe(...).result()` until async providers are specified
      (question 15).
11. **The record.** `Completed` gains `files: FileRecord | None = None`, last, so positional
    use is unchanged; it is `None` for a call without mounts.
    - `FileRecord.calls`: a read-only mapping from each method the runner may call (`stat`,
      `list`, `read`) to its count, zeros included. It equals the provider's own count.
    - `FileRecord.faults`: the first 1,000 `FileFault(method, path, error)`s, where `error` is
      the exception's type name and the first line of its text, at most 200 characters, or
      `"bad answer: <type>"`. No exception object is kept, so a result holds no frame of the
      call.
    - No times (§4.9). Spec 034 adds the refused write-backs vfs records even on exit 0.
12. **Docs.** README, a *Mounts* section: the protocol, `read`'s contract, `Errno`, `Mount`, the
    mount at `/`, nesting, `HOME`, the limits and `"out of file calls"`, the staging bound and
    the advice to refuse large files first, read-only until 034, no links, no times from
    `os.fstat`, provider numbers above `2**30` (so `select.select` refuses a mount's file with
    `ValueError`; use `selectors` or `select.poll`), whole-file staging (a 1-byte read stages the
    file), the deliberate differences from a grant, and that a sync provider runs on the
    guest's thread, must bound its own time and be thread-safe, and holds a deferred Ctrl-C; the
    async bridge. The *Safety* section names the provider as the embedder's code, called with
    normalized paths only. CHANGELOG: an *Added* line.

## Intent

An embedder can serve a guest's ordinary file calls from its own code, read-only, at any guest
path including `/`, with no new import, no host path opened, every guest argument checked
before the embedder sees it, every provider call counted and limited, and nothing a provider
does able to make `run` raise.

## Design

```
src/wasi_python/mounts.py    Mount, FileProvider, Stat, Errno, FileRecord, FileFault; the mount
                             table and provider numbers, path normalization, staging, the 29
                             shadows' bodies, the trampoline (wasmtime imported inside functions)
src/wasi_python/runner.py    mounts= and max_file_calls= on run and run_async; Defaults.file_calls;
                             the mount linker; the placeholder made before the preopens; _drive
                             instantiates the trampoline; _check_preopens on today's linker;
                             _home_folder sees mounts; _epoch_answer's ended rule; 030's comment;
                             Completed.files
src/wasi_python/__init__.py  exports Mount, FileProvider, Stat, Errno, FileRecord, FileFault
tests/harness/files.py       an in-memory provider for the checks, which counts its own calls
tests/checks/test_v1_4_embedding.py   acceptance 1, 2, 4, 5, 6, 11, 12 (all three systems)
tests/unit/test_runner_grants.py      acceptance 3, the raw parity table (all three systems)
tests/checks/test_v1_2_hostile_guest.py   acceptance 7, and 8's descriptor check
tests/unit/test_runner_mounts.py      acceptance 8's raw guards, 9, 10, 12's exact part, 13
README.md, CHANGELOG.md
```

The raw parity table is table-driven: one WAT module re-exports each preview1 call with its raw
signature, as the review's `raw_answers.py` does, so a row is data, not a new guest. It runs
the same rows on a read-only grant and on a mount, with the runner's mount linker and a call on
the thread's stack, as `test_runner_grants.py` drives raw WASI calls today.

### Build order

One builder, in four steps, each green before the next (the review's order, adapted to the high
range):

1. **The mount linker with every shadow forwarding** (no provider yet), the forward-safe import
   check, the per-call forward state, Decision 1's trap rule and fuel neutrality. The judge,
   run with an unused mount, gives today's answers; acceptance 12 passes here.
2. **The table, the placeholder and provider numbers,** with `fd_close` and `fd_renumber`'s
   rules and `MAX_MOUNT_FILES`.
3. **`path_open`, `fd_read`, `fd_pread`, `fd_seek`, `fd_tell`, `fd_close`, `fd_readdir` and the
   filestat calls on a provider,** with Decisions 5 and 7.
4. **The rest of the parity table, the limits, the record, and the docs.**

Build the raw parity harness first, in step 1.

## Scope

In: read-only mounts at any guest path a grant may use and at `/`; the mechanism; the protocol's
read half; the limits; the record; the docs.

Out, each for its own specification:
- **Writable mounts: spec 034** (to be drafted after this one is built). `Mount(...,
  writable=False)`, the protocol's write half, staging write-back at close, at `fd_sync` and at
  every exit, creation, truncation, appends, the refused-write record, and the write rows of the
  parity table. The split keeps each change reviewable: this one is the mechanism and the
  security boundary, about half the memo's 700 to 900 lines; 034 adds behaviour on top of a
  mechanism already judged. vfs can mount read-only views after 032 and its writable namespace
  after 034.
- **Async providers** (question 15), with the tool protocol's async tools: awaited on the
  caller's loop, in slices, under the deadline and `cancel` (memo finding 8).
- **Ranged reads** for large files (`read(path, offset, size)`).
- **Mounts on the command line:** a provider is code, and the command adds no power `run` lacks
  (§3).
- **A per-call working directory** (`cwd=`), and the embedder contract's conformance job, which
  the parity table starts.
- **Read-only code on the import path** (decision 16) stays a typed grant. A mount on
  `PYTHONPATH` may import; it is not claimed.
- **sqlite3 over a mount** is not claimed.

## Acceptance criteria

Every check counts calls, bytes, fuel and errno values; none measures time. Each is seen failing
first, and the landing notes show it. For acceptance 3, 7, 8 and 13, which exist to catch a
missing guard, "seen failing" means against the built runner with **one guard removed** at a
time (no pointer check, no climb check, no nested-preopen check, no name check, no fault catch,
no `MAX_MOUNT_FILES`, no `fd_renumber` rule, no import list), each named check failing on its
own guard's removal and passing with it. The others are seen failing on today's runner, where
`Mount` cannot be imported. The in-memory provider counts its own calls.

1. **`test_a_mount_serves_reads`** (v1.4, both binaries). At `/work`: `open().read()` of a file
   makes exactly one `read`; `os.listdir` and `os.scandir` exactly one `list` each; `os.stat`
   exactly one `stat`; the bytes equal the provider's; `f.fileno()` is at least `2**30`;
   `os.read`, `select.poll` and `selectors.DefaultSelector` on it work, and `select.select` on it
   raises `ValueError` (Decision 6's row); `done.files.calls` equals the provider's own counts;
   a guest that reads a grant at `/data` in the same run reads it as before.
2. **`test_a_mount_answers_as_a_grant_does`** (v1.4, both binaries, all three systems). The same
   tree as an in-memory `Mount` and as a read-only `Grant` on disk; every row gives the same
   result or errno: a missing file; a folder opened as a file; a file listed as a folder; a
   missing parent; `..` that escapes; `..` that climbs and returns (`/work/a/../../work/b`); open
   for writing, appending, creating, truncating; `mkdir`, `remove`, `rmdir`, `rename` within,
   `rename` to and from a writable grant, `link`, `symlink`, `utime`, `truncate`; `readlink` of a
   file; `seek`, `tell`, `pread` past the end; a trailing `/` and a trailing `/.` on a file; a
   component over 255 bytes; `os.stat` kind and, for files, size; a sorted listing. Every write
   row makes no provider call. Decision 6's deliberate differences are asserted as that table
   says, not as parity.
3. **`test_raw_calls_answer_as_a_grant_does`** (unit, in `test_runner_grants.py`, all three
   systems). Through the table-driven WAT module, each of the 29 shadowed calls on a provider
   file, folder and preopen, and on a read-only grant's, with the same arguments, including
   unknown flag bits, a seek that overflows, whence 3, an empty path, a leading `/`, a path that
   is not UTF-8, a NUL in a path, a two-`iovec` read and `SYNC` in `fd_fdstat_set_flags`. The
   whole results are equal (errno and every byte written, with `dev`, `ino`, times and numbers
   masked), except Decision 6's listed differences; a row that differs by system is asserted per
   system. The table is in the landing notes.
4. **`test_a_mount_at_the_root`** (v1.4, both binaries). A mount at `/`: `/a.txt` and the
   relative `a.txt` read the provider's file; numpy and pandas import (the zip is still the
   zip); `/usr/./local/lib/x` is `EPERM` with no provider call; `HOME` is absent. `-c pass` makes
   at most a bound of provider calls on each binary, set at twice the count the builder
   measures, with the measured counts in the landing notes, so a change to the zip or to
   CPython does not edit this check. `root=True` or a root path with a mount at `/` raises
   `ValueError`.
5. **`test_the_file_call_limit_stops_the_run`** (v1.4). With `max_file_calls=5`, a guest that
   stats in a loop ends `trapped == "out of file calls"`, `exit_code is None`, `fuel_used is
   None`, after exactly 5 provider calls, and the line after its loop is not printed. The same
   under `cancel=` never set (the epoch callback's path and 030's guard). `DEFAULTS.file_calls ==
   10_000`, and a default run that stats 10,001 times stops after exactly 10,000 provider calls.
6. **`test_a_mount_keeps_its_deadline_and_cancel`** (v1.4). A provider that sets the call's
   `cancel` inside its third call: the run ends `"cancelled"` and the provider is called exactly
   3 times. A provider that advances the epoch ticker past the deadline by count (the seam
   `tests/unit/test_runner_async.py` and spec 017's deadline check use): `"deadline"`, with no
   provider call after it. A cancel set (by the ticker pattern of spec 030's checks) while the
   guest makes a run of forwarded calls (prints to stdout) ends `"cancelled"`, never a raw
   error.
7. **`test_a_provider_fault_never_escapes`** (v1.2 hostile). A provider that raises `ValueError`;
   returns `None`, `"text"` or an object; returns a coroutine; returns a listing whose iterator
   raises, or a buffer-like object whose buffer export raises; lists a name with `/`, a NUL,
   `..`, a lone surrogate, 256 bytes, a duplicate, or the kind `"link"`; answers `stat` with
   `size=True`; answers `stat("/")` with a file; returns more than the staged-bytes bound. The
   guest gets `EIO` (or `EFBIG` for the last) and exits 0; `run` raises nothing;
   `done.files.faults` names each fault and no more; no "never awaited" warning is emitted.
8. **`test_guest_arguments_never_reach_the_provider`** (unit, raw WASI). A path or `iovec` past
   memory, an `iovec` array of 1,025 entries, a `fd_readdir` buffer past memory, a path of 4,097
   bytes: each answers its errno from Decision 6's table, and the provider's count is 0. And
   **`test_mount_descriptors_are_bounded`** (v1.2 hostile, both binaries), in a child process
   whose soft descriptor limit is 256 (POSIX; skipped where it cannot be set): 1,025 opens of
   provider files give `EMFILE` on the last; the provider's `read` count is 1,024; the run exits
   0; the placeholder is empty during the run and gone after it.
9. **`test_a_bad_mount_is_refused_before_any_work`** (unit). One case per rule in Decision 2,
   and `max_file_calls` of `True`, `-1`, `2**63` and `"10"`: each raises the named error, and
   the provider's count and a door host's count stay 0.
10. **`test_a_call_without_mounts_is_unchanged`** (unit and the judge). A call without mounts
    uses today's linker object and invokes no shadow (a counting seam); the ratchet shows no
    fuel growth on any accepted check. Concurrent calls with and without mounts on two threads
    (spec 011's pattern) each get their own results, and each provider sees only its own call's
    paths.
11. **`test_the_errno_values_are_the_guests`** (v1.4). In the guest, `getattr(errno, name)`
    equals each `Errno` member's value, and a provider answering each member raises `OSError`
    with that `errno` in the guest.
12. **`test_forwards_cost_no_fuel_and_keep_traps`**, in two parts (N2: fuel through `run()`
    moves with the real clock and entropy by thousands, more than the 4 per forward this guards;
    the confirmation's `fuel_repeat.txt`).
    - **Exact, in `test_runner_mounts.py`, through the WAT module:** a guest that calls a WASI
      function N times spends exactly the same fuel on the mount linker as on today's linker,
      and ends the same way, with the same fuel used, at each of a range of small caps (the
      confirmation's `fuel_neutral.py` is the pattern). A forwarded `fd_read` on a grant's
      descriptor with a pointer past memory ends the call with the same `trapped` and the same
      fuel used on both linkers, and the trap object is freed (wasmtime-py's own wrapper holds
      it).
    - **Through `run()`** (v1.4, both binaries): with a fuel cap too small to finish, a run with
      a mount ends `"out of fuel"` with `fuel_used` equal to the cap, as the same run with a
      grant does. No exact fuel comparison is made through `run()`.
13. **`test_every_descriptor_import_is_shadowed`** (unit). For each binary in the artifact set,
    every `wasi_snapshot_preview1` import that takes a descriptor is among the 29 shadows or on
    the forward-safe list. A forwarded `fd_renumber` onto or from a provider number answers
    `ENOTSUP` and the table is unchanged; closing a mount's preopen drops it, and a later open
    that reuses the number is served by wasmtime.
14. `uv run pytest` green with `--accept-judge`; lost 0; grew 0. `ruff check` and `ruff format
    --check` clean. A release dry run passes every job, Windows included.
15. The build review is also a security review of the new surface against the threat model
    (`../research/2026-10-16-a-principal-engineers-direction.md` §2), recorded under
    `../reviews/`.

## For the owner's confirmation

None open here. Three of these decisions (3, 8, and the names) are the agent's choice where the
owner's decisions were silent; they are recorded as questions 54 to 56 in
`../questions-for-the-owner.md`, and nothing waits on them.

## Landing notes

Built 2026-10-17 by the implementer (a fresh agent, Claude Opus 5.5), in the worktree
`wasi_python-032` on `spec/032-a-filesystem-provider`, against the frozen artifact set
`build/sets/4befe9de64edc783` (never rebuilt). Each claim is EXECUTED unless it says otherwise.

**The branch carries spec 030 first.** Decision 9 amends a comment spec 030 writes, and acceptance
5 (under `cancel=`) and 6 (a cancel during forwards) need 030's entry guard and except branch. So
the first commit is 030's (`52674ed` cherry-picked unchanged); the lane drops it when it rebases
onto a main that has landed 030. 032's own `_shared` change is one line beside 030's
(`getattr(call, kind)(caller, *bound, *args)`, so a file shadow is bound to its call's name) plus
the amended invariant comment, worded as Decision 9 says; `_epoch_answer` gains the named-end
rule after its recorded-stop check.

**What changed.**
- `src/wasi_python/mounts.py` (new): `Mount`, `FileProvider`, `Stat`, `Errno`, `FileRecord`,
  `FileFault`; `SIGNATURES` (the 29 shadowed calls), `SHADOWED`, `FORWARD_SAFE`; the trampoline's
  WAT; `_Files`, the per-call mount table: provider numbers from 2**30, path normalization,
  staging, the provider calls with their fault boundary and limits, the 29 handlers, and the
  fuel-neutral forward by `_ffi.wasmtime_func_call` on the caller's context.
- `src/wasi_python/runner.py`: `mounts=` and `max_file_calls=` on `run` and `run_async`, checked
  by `_check_places`/`_check_mounts` before any work; `Defaults.file_calls = 10_000`;
  `Completed.files` (last field); `_mount_linker` (today's linker plus the 29 shadows, once per
  engine) and `_trampoline_module` (once per engine); `_instance` makes the scratch folder and its
  `mount` placeholder before the preopens, preopens each mount on it after every other preopen,
  and uses the mount linker only when there are mounts; `_drive` takes `plain=` (today's linker:
  the identity check and the trampoline's imports) and binds the trampoline after the guest and
  before the fuel cap; `_home_folder` sees a mount at `/tmp`; `_Call.table` and `_Call.files`;
  `_fuel_used` keeps the fuel recorded at a forward's own error (below); `_release` frees the new
  caches.
- `src/wasi_python/__init__.py`: the six exports.
- Judge: `tests/harness/files.py` (new: the counting in-memory provider, the disk twin, the
  table-driven raw module and its driver, a grant side and a mount side); `tests/unit/
  test_runner_grants.py` (acceptance 3: the raw parity table and the deliberate differences);
  `tests/unit/test_runner_mounts.py` (new: acceptance 8's raw guards, 9, 10, 12's exact part, 13,
  and unit guards for Decisions 5, 8 and 10); `tests/checks/test_v1_4_embedding.py` (1, 2, 4, 5,
  6, 11, 12's `run()` part); `tests/checks/test_v1_2_hostile_guest.py` (7, and 8's descriptor
  check). `README.md` (*Mounts*, a *Safety* bullet), `CHANGELOG.md` (an *Added* line).

**The build order.** The four steps were built in order in one pass and committed together. Step
1's claim was run as an experiment: the whole judge with one unused mount added to every `run()`
call (a `sitecustomize` on `PYTHONPATH` wrapping `_check_places`, so child processes got it too),
which sends every file call of every guest through the 29 shadows and the trampoline:
`204/215 pass · 0 fail`, `ratchet … lost 0 · grew 0`; the one unit failure was
`test_a_call_without_mounts_is_unchanged`, which asserts that a call without mounts has
`files is None`, as the injection made false. (The logs named here were under the worktree's
`build/`, which is not kept; their lines are quoted.)
`grew 0` there is the judge's own fuel metrics unchanged with forwards on every call.

**Seen failing first.** On today's runner (the main tree's `src/` on `PYTHONPATH`): every new
v1.2 and v1.4 check and both new parity tests fail (20 failed, `ImportError: cannot import name
'Mount'`), and `test_runner_mounts.py` fails to import (`build/seen-failing-today.log`). The
guard checks were seen failing with one guard removed at a time from the built `mounts.py`, and
passing with it (`build/guards.log`; the file was restored byte for byte):

| guard removed | its checks, failing |
|---|---|
| the pointer check (`_Memory.fits` true for any pointer) | `test_guest_arguments_never_reach_the_provider`, `test_the_deliberate_differences_are_as_decided` |
| the climb check | `test_raw_calls_answer_as_a_grant_does`, `test_a_path_is_normalized_before_the_provider_sees_it` |
| the nested-preopen check | `test_a_path_is_normalized_before_the_provider_sees_it`, `test_a_mount_at_the_root[plain, snapshot]` |
| the name check | `test_a_provider_fault_never_escapes[plain, snapshot]` |
| the fault catch around the provider call | `test_a_provider_fault_never_escapes[plain, snapshot]` (`ValueError` out of `run`) |
| the fault boundary around a `read` answer | `test_a_provider_fault_never_escapes[plain, snapshot]` (`BufferError` out of `run`) |
| `MAX_MOUNT_FILES` | `test_mount_descriptors_are_bounded[plain, snapshot]` (`opened 1025`), `test_the_staging_bound_and_the_open_limit` |
| the `fd_renumber` rule | `test_renumber_and_close_keep_the_table_true`, `test_the_deliberate_differences_are_as_decided` |
| the import list (`fd_advise` left out of `SHADOWED`) | `test_every_descriptor_import_is_shadowed[python.wasm, python-snapshot.wasm]` |
| fuel neutrality (the fuel not set back) | `test_forwards_cost_no_fuel_and_keep_traps` |

**Acceptance, with evidence.**
1. `test_a_mount_serves_reads` (both binaries): a read, `os.listdir`, `os.scandir` and `os.stat`
   make exactly 1 `read`, 1 `list`, 1 `list`, 1 `stat` (counted between steps through the door);
   `fileno() >= 2**30`; `os.read`, `select.poll` and `selectors.DefaultSelector` work on it;
   `select.select` raises `ValueError`; `done.files.calls == provider.calls == {stat: 2, list: 2,
   read: 2}`; the grant at `/data` reads its CSV.
2. `test_a_mount_answers_as_a_grant_does` (both binaries): 32 rows, grant and mount equal; the 16
   write rows are `EPERM` on both and make 0 provider calls each. Rows asserted on POSIX only
   (`HOST_ROWS_V14`): a trailing `/` and `/.` on a file, a component over 255 bytes, `readlink` of
   a file.
3. `test_raw_calls_answer_as_a_grant_does`: 330 rows (each of the 29 shadowed calls on a provider
   file, a folder opened with `O_DIRECTORY`, a folder opened without it and the mount's preopen,
   plus seeks, reads, `fd_readdir` cookies and short buffers, 50 `path_open` forms, path stats,
   readlinks, every write-shaped path call, renames and links within and to and from a writable
   grant, the forward-safe calls on the preopen, and closing), all equal, whole results compared
   (errno and every byte written; `dev`, `ino`, times, numbers, and a folder's size and link
   count masked). Asserted on POSIX hosts only, since the grant's answer is the host's own error
   (`HOST_ROWS`): `fd_advise`, `fd_write`, `fd_pwrite`, `fd_datasync` and `fd_sync` on a file;
   `path_open` of `a.txt\0`, `a.txt/`, `a.txt/.` and a 256-byte name; `path_filestat_get` of
   `a.txt/`, `a.txt/.`, `a.txt/x`, `a\0` and a 256-byte name; `path_readlink` of `a.txt`, `d`,
   `a.txt/`. `test_the_deliberate_differences_are_as_decided` asserts Decision 6's table (`..` by
   text: grant 44 and 54, mount 0; over 4,096 bytes: 37; a pointer past memory: grant ends the run,
   mount 21; 1,025 iovecs: grant reads 1 byte, mount 28; `fd_renumber`: grant 0, mount 58;
   `sock_shutdown` and `fd_prestat_dir_name` on a provider number: grant 57 and 54, mount 8; a
   provider number `>= 2**30`; case is the provider's). **Not run on Linux or Windows** (only
   the release dry run's `verify` job runs there).
4. `test_a_mount_at_the_root` (both binaries): `/a.txt` and `a.txt` read the provider's file;
   numpy and pandas import; `/usr/./local/lib/x` is 63 with no provider path under
   `/usr/local/lib`; no `HOME`; `root=True` and a root path raise `ValueError`. `-c pass` with a
   mount at `/` made 0 provider calls on the snapshot and 9 on the plain reactor (4 `stat`, 5
   `read`: CPython's start-up search for `pyvenv.cfg`, `._pth`, `pybuilddir.txt`, the zip and
   `lib-dynload`); the bound is 18 on both, twice the larger.
5. `test_the_file_call_limit_stops_the_run`: with `max_file_calls=5` and `fuel=10**12`, with and
   without `cancel=` (never set): `(None, "out of file calls", None, b"")` after exactly 5 `stat`s;
   `DEFAULTS.file_calls == 10_000`, and 10,001 stats stop at exactly 10,000 provider calls.
6. `test_a_mount_keeps_its_deadline_and_cancel` (child processes, 120 s fail-safe): a cancel set
   in the third call: `cancelled None 3`; a provider that holds the guest 20 ticks past a 0.05 s
   deadline in its third call: `deadline None 3`; a cancel (by ticks) during a loop of prints, all
   forwarded: `cancelled None 0`.
7. `test_a_provider_fault_never_escapes` (both binaries): 25 misbehaving providers, one per
   mount: 24 give the guest 29 and one fault each (method, path and error checked, single-line,
   at most 200 characters); the one past the staging bound (a 512 MiB untouched `mmap` under
   `memory_bytes=256 MiB`) gives 22 and no fault; exit 0; no "never awaited" warning. Beyond the
   spec's list: a plain `int`, a pair of one, a negative size, a `Stat` kind of `"fifo"`, and an
   answer or listed item whose `__class__` raises (below). `test_a_providers_base_exception_is_
   raised_from_run`: `SystemExit` from a provider is raised from `run`.
8. `test_guest_arguments_never_reach_the_provider`: 17 rows (a path, a path's length, results,
   iovec arrays, each iovec, 1,025 iovecs, readdir's buffer and count, readlink's buffer, fdstat,
   filestat, seek) answer 21, 28 or 37 with no provider call and nothing moved.
   `test_mount_descriptors_are_bounded` (both binaries, a child at a soft limit of 256): `0
   refused 33 1024 True 1024 [[[]], [[]]] []`: EMFILE on the 1,025th open, 1,024 reads, numbers
   from 2**30, the placeholder empty when looked at during the 1st and 1,024th read, nothing left
   after.
9. `test_a_bad_mount_is_refused_before_any_work`: 19 cases, each through `run` and `run_async`,
   each the named error; the provider's and a door host's counts stay 0.
10. `test_a_call_without_mounts_is_unchanged`: a call without mounts reached `_drive` with
    `runner._linker(...)` itself and no shadow ran; three threads (two with their own mounts, one
    without) ran three calls each with their own results, each provider seeing only `/x`, the
    mounted calls on the mount linker. The judge's ratchet: `grew 0`.
11. `test_the_errno_values_are_the_guests`: all 21 members equal the guest's `errno` constants,
    and each, answered by `stat`, is the guest's `OSError.errno`.
12. Exact part: a 200-call loop of `fd_fdstat_get` spends 3,405 fuel on both linkers; at 102 caps
    (1 to 59, and 3,365 to 3,407) the two end the same way with the same fuel; a forwarded
    `fd_read` with a pointer past memory ends `(None, 'error while executing at wasm backtrace:',
    11)` on both, the error a `wasmtime.WasmtimeError` holding its pointer. Through `run()` (both
    binaries): a printing loop capped at 400,000,000 fuel ends `"out of fuel"` with `fuel_used`
    equal to the cap, with a grant and with a mount.
13. `test_every_descriptor_import_is_shadowed` (both binaries): 33 descriptor imports (28 `fd_`
    and `path_`, four `sock_`, `poll_oneoff`), all shadowed or forward-safe;
    `test_the_mount_linker_shadows_every_call` (all 29 reach the table);
    `test_renumber_and_close_keep_the_table_true`.
14. `uv run pytest` (`build/judge-2.log`): `wasi_python v1: 204/215 pass · 0 gap · 11 blocked ·
    0 fail (unit suite 623/631, 8 skipped)`, `ratchet vs 567d64204b: lost 0 · … · gained 22 ·
    grew 0`, `827 passed, 19 skipped`. `ruff check` and `ruff format --check` clean on `src` and
    `tests`. **Not run here:** `--accept-judge` (the lane's) and the release dry run (it needs the
    workflow; it is the first run of acceptance 2's and 3's rows on Linux and Windows).
15. The build review's: not written by the implementer.

**Where the specification was silent, the builder decided** (each for the reviewer to judge):
- *ABI errors end the run, as on a grant.* wasmtime ends the run (an error, not an errno) for a
  flag or enum value it does not define, an integer out of its type's range and a misaligned
  pointer (a probe of a read-only grant on plain wasmtime-py; the same answers are the grant
  side of acceptance 3, run live on every judge). Decision 6
  makes parity the rule except for its table, so a served call does the same: it raises a
  `WasmtimeError` to the shared function, which records it as the call's stop. Its message is
  wiggle's text (`Invalid flag value Fdflags`), so through `run()` `trapped` reads that, where a
  grant's reads `error while executing at wasm backtrace:`. A pointer past memory stays `EFAULT`
  (Decision 6's row).
- *A forward's error keeps today's `fuel_used`.* With the shared function recording the
  forward's error as the stop, `_fuel_used` would answer `None`; it now answers the fuel read
  when that exact error was raised (set back first, N3), so acceptance 12's "same fuel used"
  holds through `_drive`. It applies only when the recorded stop is that error and no end is
  named.
- *UTF-8 is decoded when a path is read,* as wasmtime does, so a write-shaped call's bad UTF-8 is
  `EILSEQ` on both sides; a path both absolute and not UTF-8 is `EILSEQ`, not Decision 5's
  `EPERM`.
- *Every iovec is checked against memory* (Decision 7's "each iovec"); wasmtime reads only up to
  the first non-empty one.
- *A rename or link across a mount and a wasmtime descriptor* asks wasmtime whether its
  descriptor is a folder by two forwards that change nothing (`fd_fdstat_set_rights` answers
  `ENOTSUP` on any open file or folder, `fd_allocate` `EBADF` on all but a file), so a bad other
  descriptor is `EBADF`, as across two grants; otherwise `EPERM`.
- *A mount's own preopen*: the calls wasmtime answers alike for every read-only preopen are
  forwarded to the placeholder (its fdstat with the preopen rights, advise, sync, flags, reads,
  writes, seek, set_size, set_times); its listing, its stat and every path under it are the
  provider's; `fd_close` is forwarded and drops it.
- *Times*: `path_filestat_get` reports `mtime_ns` as the access, modification and change time; a
  folder's size is 0 and every link count 1.
- *Found in self-review and fixed before landing:* `isinstance()` on a provider's answer can run
  the answer's own `__class__` property (CPython looks it up when the type does not match), and
  so can the listing iterator's `close` lookup; both first sat outside the fault boundary, so a
  hostile answer could have made `run` raise. All answer handling is now inside it; acceptance 7
  has rows for an answer and an item whose `__class__` raises, and removing the boundary fails it.

**For the build review (also a security review, acceptance 15).** Look first at
`mounts.py`'s boundary: `_Memory`, `_iovecs`, `_result`, `_path` and `_resolve` (every guest
pointer, length, count and path before any provider call); `_ask`, `_stat`, `_read`, `_list` and
`_listed` (everything a provider returns is judged inside the fault boundary; a `BaseException`
is let through on purpose, as Decision 4 says); `forward` (`_ffi.wasmtime_func_call` on the
caller's context, the per-call handles and arrays, the fuel set back in a `finally`, the trap or
error taken by wasmtime-py's own `_from_ptr`); `_fd_renumber` and `_fd_close` (the table can
never hold a number wasmtime reuses); `_path_open`'s order of checks (write-shaped opens refused
before the provider; `EMFILE` before it); the high range and `MAX_MOUNT_FILES`; and in
`runner.py` the scratch-and-placeholder order in `_instance`, the identity check on today's
linker, the HOME rule, `_fuel_used`'s new branch, and Decision 9's comment beside 030's branch.
The Windows answers of acceptance 2's and 3's rows are unknown until the release dry run.

**Revised 2026-10-17 against the build review** (`../reviews/032-a-filesystem-provider-2026-10-17.md`,
not yet: F1 to F5), by the implementer, on the lane's rebase `c69cb31` (spec 030 landed in main;
the cherry-picked copy dropped out). Each new check was seen failing first, on the reviewed code
(its `mounts.py` and `runner.py` swapped in, then restored and compared) or with its one rule
removed. EXECUTED unless it says otherwise.

- **F1, answers judged by their real type; a total `_described`.** `type(answer) is Errno`
  (exact: an enum with members has no subclass), `answer is Errno.EISDIR`, `issubclass(type(…),
  Stat)` and `(bytes, bytearray, memoryview)` and `Iterable`; `_listed` takes only a plain tuple
  of plain str; a size or time is judged by `issubclass(type(…), int)`; a coroutine by its type.
  `_described` reads the type's own name (`type.__dict__["__name__"]`), keeps the text only when
  `str(e)` is a plain str, and never raises. `_fd_readdir` answers `EIO` for a listing it could
  not keep, never an assertion. Acceptance 7 gains four rows: a fake `Errno` of 0 and one past
  i32, an exception whose type's name raises, one whose text is a hostile str subclass. On the
  reviewed code the first made `run` raise `AssertionError`, the second gave the guest EBADF with
  no fault, the third and fourth made `run` raise `ValueError` (the reviewer's `hostile.py`, rerun);
  now each is EIO with one fault (`bad answer: _FakeErrno`, `_Nameless: x`, `_TextException`).
  The four earlier `__class__` rows now read `bad answer: _Masked` (and `bad answer: list` for
  the item): no provider code runs to judge them.
- **F2, a listing is kept as what it is counted at.** One `bytearray` of encoded entries (each
  header with its `d_next`, then the name) and an `array("I")` of offsets; `fd_readdir` serves
  one slice of it from the cookie's offset, which is byte for byte what wasmtime writes (the 330
  parity rows are unchanged and equal). `held` is `sys.getsizeof` of the two; while gathering,
  the set of encoded names that finds a repeat, and its names, are counted too. One million
  8-byte names: counted 38,816,299, held 38,818,230 after (1.00; the reviewed code: 4.9),
  peak 113,374,317 while gathering, all of it judged against the bound as it grows.
  `test_a_listing_is_counted_as_what_it_holds` (tracemalloc, 20,000 names): kept within 4 KiB of
  the count, and a listing past a bound of half its size stops with `EFBIG` at a peak within
  1.25 times the bound; on the reviewed code it failed (counted 640,051, held 3,153,076).
- **F3, nothing of a finished call waits for the collector.** `_instance` takes the record, then
  `table.release()` drops the staged files and listings, the trampoline's handles, the fuel
  record and the link back to the call. That alone left a trapped call alive: wasmtime-py's
  `Trap` keeps a traceback whose frames hold the call, which was true without mounts too (a
  call that ran out of fuel left one `_Call` until a collection). `_drive` now drops the
  traceback of a trap or error it has named, and of a wasmtime error it reports as a stop.
  `test_a_finished_call_holds_nothing`, with the collector off: after a guest that exits with a
  mount file open, one that runs out of fuel holding one, and one stopped "out of file calls",
  no `_Call`, `_Files` or `_Open` is alive; on the reviewed code 4 were.
- **F4, the three differences documented, and one closed.** Decision 5 says when UTF-8 is
  judged; Decision 6's table and the README gain a later `iovec` past memory and an ABI error's
  `trapped` text. An ABI error's `fuel_used` is now the grant's, not `None`: `_Files` records the
  fuel when it raises one, as a forward's error does (`stop_fuel`, renamed from
  `forward_stop`). `test_an_abi_error_keeps_the_grants_fuel`: an undefined `oflags` bit ends
  both with `fuel_used` 11; on the reviewed code the mount's was `None`. Decision 8 says how a
  listing is counted.
- **F5.** `test_a_mount_at_tmp_means_no_home` (v1.4): with `root=True` and with a root path, a
  mount at `/tmp` gives the guest no `HOME`. With `_home_folder`'s two lines removed it fails
  (`HOME` is `/tmp/.home-…`, made in the root's own tmp behind the mount).
- **F6.** The README's climb rule now reads "above the folder the call starts from". The other
  notes need no change. Acceptance 4's bound of 18 was measured on the set `4befe9de64edc783`;
  spec 033's new zip may move the plain reactor's start-up count, which the lane sees at
  acceptance.

The judge after the revision (`WASI_PYTHON_ARTIFACTS=…/4befe9de64edc783 uv run pytest`):
`wasi_python v1: 208/219 pass · 0 gap · 11 blocked · 0 fail (unit suite 627/635, 8 skipped)`,
`ratchet vs aac0a98618: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 19 · grew 0`,
`835 passed, 19 skipped`. `ruff check` and `ruff format --check` clean.

**Revised after landing, 2026-10-18 (a judge change).** The release dry run 39097514484 failed
in "build and judge (arm64 macOS)": `test_raw_calls_answer_as_a_grant_does` differed on `dir
fd_readdir` and `plain dir fd_readdir`, only in the byte after one entry's `d_type`: the grant
wrote `0x60`, the mount `0x00` (`context/upstream/12-wasmtime-py-on-wasmtime-49-0-3/evidence/
ci-39097514484.txt`). EXECUTED unless it says otherwise.

- **The cause is wasmtime's, and known.** wasmtime 49.0.2's release notes list "`fd_readdir`
  copies uninitialized struct padding into guest memory" (GHSA-96f6-r43r-8c24; READ,
  `context/prior_art/wasmtime-v49/RELEASES.md`). wasmtime-py 49.0.0, the release `uv.lock` pins
  and PyPI's only 49 release, bundles wasmtime 49.0.0 (READ, `ci/download-wasmtime.py`). In
  49.0.3's source the dirent is a zeroed `vec![0; 24]` (READ, `crates/wasi/src/p1.rs:2010`).
  Reproduced locally: on a read-only preopen, with the guest buffer zeroed before each call, the
  `..` entry's first padding byte was `0x04` in 995 of 1,000 calls
  (`…/12-wasmtime-py-on-wasmtime-49-0-3/evidence/padding.txt`). The local judge had passed by
  chance of what the host's buffer held.
- **The judge change and its reason.** The bytes are undefined on the reference side, so the
  parity compares each entry's fields, not its padding: `masked_dirents` (`tests/harness/
  files.py`) now zeroes bytes 21 to 24 of each header beside `d_ino`, so entries compare by
  `d_next`, `d_namlen`, `d_type` and name, cut-short buffers included. That is not a weaker
  claim about the mount: `test_a_mount_writes_zero_dirent_padding` (new) fills the buffer with
  0xFF and asserts every entry's padding is zero on full and cut-short buffers, from a folder
  and from the mount's preopen. Seen failing first with the mount's `DIRENT` made to write
  `0x04` there (and the masked parity still passing). Decision 6's table and the README have a
  row for it.
- **Our grants are affected, by default.** Every `fd_readdir` wasmtime serves leaks up to three
  bytes of uninitialized host memory per entry: the stdlib zip's folder at `/usr/local/lib` on
  every call (nothing granted is needed), a root, every grant. A guest can repeat it at will.
  What the bytes hold is the host's (INFERRED: stack or heap leftovers of the thread running the
  guest, possibly pointer fragments). It is a host-memory disclosure to the guest, the adversary
  of the threat model (`../research/2026-10-16-a-principal-engineers-direction.md` §2), reachable with no argument, so §4.15's spirit and §5.5's rule apply:
  a security fix in a pinned component is a reason to release. None can be taken yet, because
  no wasmtime-py release carries wasmtime 49.0.2 or later. `context/upstream/12-…/facts.md` is
  a facts sheet for the owner to ask wasmtime-py for one (the Bytecode Alliance AI Tool Use
  Policy keeps agents from posting). Not done here, for the owner's decision: a runner
  workaround, shadowing `fd_readdir` on today's linker and zeroing each forwarded entry's
  padding, which changes calls without mounts and so needs a specification.
- **Also in the same release notes, unexamined here:** wasmtime 49.0.3 fixes "Filesystem
  sandbox escape when renaming symlinks with trailing slashes" (GHSA-m9f7-9w4p-gv38), which may
  bear on writable grants and roots; it deserves its own research.
- **The judge after the change** (`WASI_PYTHON_ARTIFACTS=…/s-8d84b3b190fe9bce uv run pytest`):
  `wasi_python v1: 212/223 pass · 0 gap · 11 blocked · 0 fail (unit suite 633/641, 8 skipped)`,
  `ratchet vs 789c841673: lost 0 · … · gained 0 · grew 0 · judge changed: tests/harness/files.py,
  tests/unit/test_runner_mounts.py`, `845 passed, 19 skipped`. `ruff check` and `ruff format
  --check` clean.
- **Revised against its review** (`../reviews/032-dirent-padding-2026-10-18.md`): the leak is
  listed under the README's *Safety* → *Not protected* and as a known issue in the CHANGELOG's
  0.1.0a4 section, naming GHSA-96f6-r43r-8c24 and that a mitigation is being researched (F1);
  the zero-padding check also cuts buffers inside a header (sizes 22, 23, 47 and 48, F2);
  `DIRENT_MASKED` and the facts sheet say the padding mask goes once `uv.lock` moves to a
  wasmtime-py on wasmtime 49.0.2 or later (F3); the evidence script's unused import is gone (F5).
  Judge: `212/223 pass · 0 fail`, `lost 0 · gained 0 · grew 0`, `845 passed, 19 skipped`; ruff
  clean.

**Revised after landing, second part, 2026-10-18 (a judge change): Linux's answers.** The spec
034 builder ran `test_raw_calls_answer_as_a_grant_does` on Linux (a `python:3.13-slim`
linux/arm64 container, wasmtime-py 49.0.0's manylinux aarch64 wheel from `uv.lock`'s pinned URL,
hash-checked, the worktree mounted read-only) and found four rows that macOS never showed. The
`verify` job runs this file on Linux, so the next dry run would have failed. Reproduced the same
way (EXECUTED), then decided per row, Linux being Decision 6's reference:

- **`fd_read` and `fd_pread` at 2**63 − 1: the mount now answers as Linux.** On Linux a
  grant's read is `EINVAL` when its end would pass 2**63 − 1 (the kernel's `rw_verify_area`):
  `fd_read` of 4 bytes at 2**63 − 4 is 28 and at 2**63 − 5 is 0; of 100,000 bytes, 28 at
  2**63 − 100,000 and 0 one lower. `fd_pread` reads through wasmtime's stream, which asks for at
  most `MAX_READ_SIZE_ALLOC`, 64 KiB, at a time (READ, `crates/wasi/src/lib.rs:31`,
  `p2/filesystem.rs:88`): 100,000 bytes are 28 at 2**63 − 65,536 and 0 at 2**63 − 65,537; a read
  with no non-empty buffer is 0. macOS answers 0 to all of these. `_reads` now refuses exactly
  what Linux refuses (`PREAD_CHUNK`); refusing more weakens no guard. The two parity rows are
  compared on Linux only (`SYSTEM_ROWS`), and `test_the_deliberate_differences_are_as_decided`
  asserts the mount's answers at seven pread and five read points on every system; on main's
  `mounts.py` it fails (`[0, 0, 0, …] != [28, 28, 0, …]`).
- **`path_filestat_get` of `a.txt/` and `a.txt/.`: kept `ENOTDIR`, a deliberate difference.**
  Linux's grant answers the file's stat (0, a regular file of 13 bytes), but an `open` of the
  same paths is 54 on Linux, macOS and the mount, and so is `readlink`; macOS's stat is 54; a
  trailing slash names a folder (POSIX). Matching Linux would make the mount call one path a
  file to `stat` and not a folder to `open`. The cause is cap-std's own resolution stripping the
  trailing slash before the last component's syscall in `stat_at` (INFERRED from the answers;
  `open` keeps it) — the same mechanism family as GHSA-m9f7-9w4p-gv38, which spec 048 handles
  for `path_rename` (`../research/2026-10-18-wasmtime-49-advisories.md` §1), but a read-only
  stat with no side effect, so not that escape. The rows are compared on macOS only, Decision
  6's table and the README have a row, and the deliberate test asserts the mount's 54.
- **The judge change and its reason:** `SYSTEM_ROWS` in `tests/unit/test_runner_grants.py`
  names the systems where each of the four rows is compared, because the grant's answer differs
  between POSIX systems; the mount's own answer for each is asserted on every system.
- **Run:** the whole `tests/unit/test_runner_grants.py` on Linux as uid 1000 (the host venv's
  pure-Python pytest mounted read-only, the repository's conftest off, since its plugin writes
  progress files): `18 passed, 2 skipped` (the two Windows-only checks); as root,
  `test_the_walk_judges_links` fails because every folder is writable to the superuser, as the
  README says, which predates 032. On macOS: `18 passed, 2 skipped`. The full judge on macOS
  (`…/s-8d84b3b190fe9bce`): `212/223 pass · 0 gap · 11 blocked · 0 fail (unit suite 633/641, 8
  skipped)`, `ratchet vs 8e42777c9f: lost 0 · … · gained 0 · grew 0 · judge changed:
  tests/unit/test_runner_grants.py`, `845 passed, 19 skipped`; ruff clean. The v1.4 rows of
  acceptance 2 were not rerun on Linux here.
- **Revised against its review** (`../reviews/032-linux-parity-2026-10-18.md`, rebased onto main
  `64663de`). F1: the Linux stat difference is only the stat *without* `SYMLINK_FOLLOW`
  (`os.lstat`): with lookup flags 1, `a.txt/` and `a.txt/.` are 54 on Linux's grant too, so the
  README now names `os.lstat` and Decision 6's row the no-follow `path_filestat_get` (the cause
  INFERRED: cap-std's no-follow stat; its source was not read). F2: the parity gains `pstat
  'a.txt/' following links` and `pstat 'a.txt/.' following links`, compared on every POSIX
  system (54 on Linux, macOS and the mount). F3: the parity gains zero-length `fd_pread` (`[]`,
  `[0]`) at 2**63 and 2**64 − 1 and zero-length `fd_read` after a seek to 2**63, compared
  everywhere (28 on both grants and the mount); removing `at >= 2**63` now fails the parity on
  Linux and on macOS (EXECUTED); the redundant `count and` is dropped (it changed no answer). F4:
  the four 64 KiB boundary rows (`fd_pread` of 100,000 at 2**63 − 65,536 and − 65,537, `fd_read`
  of 100,000 at 2**63 − 100,000 and − 100,001) are in the parity, compared on Linux, beside the
  deliberate asserts that hold the mount on every system. F5: Windows's grant answers near
  2**63, and to the trailing-slash stats, are not observed and not compared there; the mount
  answers as Linux and its answers are asserted on Windows too. F6: so on macOS a mount refuses
  with `EINVAL` where a grant reads nothing near 2**63, a host difference under Decision 6, not a
  table row. The file on Linux (container, uid 1000) and on macOS: `18 passed, 2 skipped` each.
  The full judge (`…/s-0cdc7b2bd78db6f5`): `216/227 pass · 0 gap · 11 blocked · 0 fail (unit
  suite 813/821, 8 skipped)`, `lost 0 · gained 0 · grew 0 · judge changed:
  tests/unit/test_runner_grants.py`, `1029 passed, 19 skipped`; ruff clean.

**Revised after landing, third part, 2026-10-18 (a judge change): Windows's `..`.** Release dry
run 39105048310 failed only in "verify (windows-2025)", at
`tests/unit/test_runner_grants.py:648`: `assert both(lambda r: r.open(3, "missing/../a.txt")[0])
== (44, 0)` got `(0, 0)` (EXECUTED, `gh run view 39105048310 --log-failed`). The mount's 0 is
as decided (Decision 6 resolves `..` by text); the Windows grant resolves it by text too and
opens `a.txt`, where Linux's and macOS's grants walk each part and answer 44. In the same run
`test_raw_calls_answer_as_a_grant_does` passed on Windows: its first run there, with
`HOST_ROWS` and the per-system rows left out.

- **The change:** the row's grant side is system-specific (Windows 0, POSIX 44); the mount's 0
  stays asserted everywhere. Decision 6's table gains a Windows row and the README's `..` line
  says a Windows grant resolves by text too.
- **The rest of the test, reasoned, not run on Windows** (the failure stopped it at its first
  assertion): the next row, `a.txt/../b.txt`, meets the same code. cap-std opens one component
  at a time on Windows, so Win32 never sees the `..`; its own `Context::new`, in a
  `#[cfg(windows)]` block ("Windows resolves `..` before doing filesystem lookups"), pops the
  normal name before each `..` before any lookup (READ, cap-primitives 4.0.3,
  `src/fs/manually/open.rs`, on docs.rs; wasmtime 49 pins 4.0.3 in its `Cargo.lock`). So the
  Windows grant's 0 is asserted for both rows (revised against the review of the third part,
  F1 and F2). Every later grant-side assertion depends
  on wasmtime's own logic, not the host's path handling: wiggle's pointer check, the first
  non-empty `iovec`, `fd_renumber`, the `sock_*` and prestat answers (READ, `p1.rs`), and the
  same calls already compared equal on Windows in the parity table. The v1.4 checks, which ran
  on Windows in the same job, passed.
- **Run:** `tests/unit/test_runner_grants.py` on macOS and on Linux (the container method, uid
  1000): `18 passed, 2 skipped` each. The full judge on macOS (`…/s-0cdc7b2bd78db6f5`):
  `220/231 pass · 0 gap · 11 blocked · 0 fail (unit suite 821/829, 8 skipped)`, `lost 0 · gained
  0 · grew 0 · judge changed: tests/unit/test_runner_grants.py`, `1041 passed, 19 skipped`; ruff
  clean.

**Revised after landing, fourth part, 2026-10-18 (a judge change): acceptance 6's deadline by
count.** The review of the third part (its O1) saw `test_a_mount_keeps_its_deadline_and_cancel[
deadline]` fail 3 of 5 times alone at load average 174: its 0.05 s deadline is wall-clock, and
under load the guest's start-up outlived it, so the run ended "deadline" with 0 provider calls,
not 3. Reproduced here (EXECUTED) at load average about 230: 2 of 5 runs gave `deadline None 0`.
Acceptance 6 asks for a provider that "advances the epoch ticker past the deadline by count";
the case now does exactly that and nothing by time: the run's deadline is 60 s, and the provider,
in its third call, sets the ticker's count to the call's `stop_at` and advances every engine's
epoch past the deadline (6,002 increments), the seams of spec 017's deadline check and
`tests/unit/test_runner_async.py`. So the provider is always reached, the guest stops at its
next entry, and no fourth call is made: `deadline None 3`. Passed 10 of 10 runs at load
averages 206 to 237 (EXECUTED). The cancel case and the forwards case already wait only on
counts (a provider call, ticker ticks) and keep their form.
- **Run, with the third part's revision (F1 to F4 of its review: the Windows grant's 0 asserted
  for `a.txt/../b.txt` too, READ in cap-std; the mechanism named as cap-std's, not Win32's; the
  docstring; the file's `POSIX`):** `tests/unit/test_runner_grants.py` on macOS and on Linux
  (container, uid 1000): `18 passed, 2 skipped` each. The full judge on macOS
  (`…/s-0cdc7b2bd78db6f5`), at load average about 335: `220/231 pass · 0 gap · 11 blocked · 0
  fail (unit suite 821/829, 8 skipped)`, `lost 0 · gained 0 · grew 0 · judge changed:
  tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_grants.py`, `1041 passed, 19
  skipped`; ruff clean.

**The post-landing parts landed 2026-10-18:** the dirent padding (`ebc9f53`), Linux's parity rows
(`3a9588f`), and the Windows grant's `..` with the count-based deadline check (`77bd08e`), each
reviewed and confirmed. Release dry run 39109451358 on `77bd08e`: every job passed, including the
first complete run of this spec's raw parity and deliberate-differences tests on Windows.
