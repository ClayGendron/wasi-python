# 032 — A filesystem provider (read-only mounts)

- **Status:** drafted 2026-10-17. To be reviewed before build. §5.6 asks a second review only
  for a change to the guest's imports or exports, the artifact set or the build recipe; this
  one changes none of them, but it puts embedder code behind the guest's file calls, so it is
  reviewed against the threat model first, as the memo asks ("Cost and risk").
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`; a new `src/wasi_python/mounts.py`),
  `src/wasi_python/__init__.py`'s exports, judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`. **Not build-class:** it touches no `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or release workflow. Its checks run on Windows, Linux and macOS
  through the files the `verify` job already runs.
- **Depends on:** 011 (shared host functions, found by the thread's call stack), 015 (`cancel`,
  the epoch callback, `call.ended`), 017 (typed grants: `_guest_path`, the preopens, the identity
  check), 025 (nothing writable by default), all landed; 030 (a cancel during a door call is
  named), because both change how a stop is named: 032 lands after 030 or rebases on it. Spec
  031 (the tool protocol) also adds a limit to `Defaults` and a record to `Completed`; neither
  depends on the other, and the lane rebases whichever lands second.
- **Research it stands on:** `../research/2026-10-17-a-filesystem-provider-for-the-runner.md`
  and its evidence folder (`shadow.py`, the model; `imports.txt`, `provider.txt`,
  `dot_path.txt`, `cost.txt`, `async_cancel.txt`). Where this specification departs from the
  memo's recommendation, the decision says so and why.
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

This specification builds that mechanism for **read-only** mounts. Writes are the next
specification (Scope).

## Terms

- **Provider:** an object the embedder passes that answers file operations from its own code.
  Its authority is bound in by the embedder before the call.
- **Mount:** a provider placed at a guest path, as a grant places a host folder.
- **Shadow:** a host function defined over one of wasmtime's own WASI functions, through
  `Linker.allow_shadowing`. The runner already shadows `poll_oneoff`.
- **Forward:** a shadow handing a call it does not own to wasmtime's own WASI.
- **Trampoline:** a tiny wasm module the runner compiles. Its functions call wasmtime's WASI on
  the guest's memory. It is how a forward reaches wasmtime.
- **Placeholder:** an empty, read-only folder the runner owns. Each mount is preopened on it, so
  wasmtime's own descriptor table numbers every provider descriptor.
- **Staging:** reading a whole file into host memory at open and serving reads from that buffer.

## Decisions

1. **The mechanism is the memo's (findings 2 to 4).**
   - **A second linker, only for calls with mounts.** Per engine, beside today's `_linker`: WASI,
     `allow_shadowing`, the shadowed `poll_oneoff`, the door, and one shadow for each of the 26
     file calls the guest imports (memo finding 1: 16 on a descriptor, 10 on a path). It also
     shadows `fd_renumber`, which today's binaries do not import, so a later binary cannot free
     a provider number behind the runner's back. A call without mounts uses today's linker
     unchanged, so its fuel and behaviour are today's exactly.
   - **Each shadow is `_shared`'s form (spec 011).** It finds its call on the thread's stack,
     serves only that call's store, and never raises into wasmtime-py. A call on a descriptor
     the call's mount table does not hold is forwarded. `path_rename` and `path_link` name two
     descriptors; `path_symlink` names its descriptor third.
   - **Forwards go through a trampoline.** wasmtime's WASI finds guest memory through the
     calling instance's `memory` export (memo finding 3, READ). The trampoline imports the 27
     originals and the guest's memory, re-exports that memory, and exports one forwarder per
     call. It is compiled once per engine and instantiated per call, after the guest and before
     `_initialize`, with the guest's own memory and the originals taken from today's linker
     (`Linker.get`), whose file calls are wasmtime's. Instantiating it defines no Python
     callback (decision 11's race is in `define_func` and custom output). A forward calls a
     cached `wasmtime_func_call` through `_ffi`, as the epoch code already does under the
     `<50` pin; it is three times faster than `Func.__call__` (memo finding 5, a benchmark
     fact, never a check).
   - **One placeholder per call.** An empty folder `mount` inside the call's own private scratch
     folder (the `0700`, locked folder that holds `stdin`, spec 016), made before the preopens.
     Every mount is `preopen_dir(placeholder, guest, False)`, after the stdlib folder, the root
     and the grants. It is walked with `judge=False` like the stdlib folder, checked by identity
     like every preopen (spec 017, Decision 5), and removed with the scratch folder. It lies
     under the temporary folder, which no grant may be at or above, so no grant can reach it.
   - **The identity check runs on today's linker,** so it reads wasmtime's own answers for every
     preopen, placeholders included, never a shadow's.
   - **wasmtime numbers every provider descriptor (memo finding 4).** When a provider file or
     folder is opened, the runner reserves a number by calling wasmtime's own
     `path_open(fd, ".", O_DIRECTORY)` on the provider descriptor the guest's call names (to
     wasmtime, every provider descriptor is a handle on the placeholder). A small reserve
     module with its own memory makes that call. The guest's `fd_close` releases the number
     through wasmtime's `fd_close`, and the table drops it at the same moment. So a number
     leaves the table exactly when wasmtime frees it, and a reused number is never mistaken
     for a provider's. If a shadow ever forwarded a provider descriptor by mistake, the guest
     would reach an empty, read-only folder the runner owns, nothing more.
   - **No host path is opened for a mount.** The provider names no host path, and the runner
     opens none for it. The only host folder involved is the runner's own empty placeholder.
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
   with values, an embedder whose layer never raises sits behind the runner as it is, and an
   exception always means a bug (Decision 4).

   ```python
   class FileProvider(Protocol):              # exported for type checkers
       def stat(self, path: str) -> Stat | Errno: ...
       def list(self, path: str) -> Iterable[tuple[str, str]] | Errno: ...  # (name, "file"|"dir")
       def read(self, path: str) -> bytes | bytearray | memoryview | Errno: ...  # the whole file

   @dataclass(frozen=True)
   class Stat:
       kind: str          # "file" or "dir", checked in __post_init__
       size: int = 0      # bytes, 0 to 2**63 - 1
       mtime_ns: int = 0  # 0 to 2**64 - 1

   run(argv, mounts=[Mount(files, "/work")], grants=[Grant(data, "/data")])
   ```

   - **Paths are absolute within the mount;** `/` is the mount itself. Under a mount at `/`,
     the provider's path is the guest's. Every path reaches the provider normalized
     (Decision 5).
   - **`Errno`** is an `enum.IntEnum` exported from `wasi_python`. Its values are WASI
     preview1's numbers (READ, `wasi-libc/libc-bottom-half/headers/public/wasi/wasip1.h`), so
     the runner passes them to the guest unchanged and never interprets them: EACCES 2, EBUSY
     10, ECANCELED 11, EDQUOT 19, EEXIST 20, EFBIG 22, EINVAL 28, EIO 29, EISDIR 31,
     ENAMETOOLONG 37, ENOENT 44, ENOSPC 51, ENOSYS 52, ENOTDIR 54, ENOTEMPTY 55, ENOTSUP 58,
     EPERM 63, EROFS 69, ESTALE 72, ETIMEDOUT 73, EXDEV 75. The set is closed: no success, no
     `EINTR` or `EAGAIN` that would make the guest's C library retry, no `EBADF` or `EFAULT`,
     which describe the guest's own arguments. It covers vfs's whole errno table
     (`169…/spec.md` §b7), which is already in preview1 numbering, so vfs's adapter is
     `Errno(WASI_ERRNO[kind])`.
   - **The runner knows nothing about permissions.** Within a mount it calls the provider for
     every access and passes its answer through. Whether `EACCES` means a policy, a missing
     login or a budget is the embedder's business (decision 17).
   - **At most one provider call per open** (169b's table, `169…/spec.md` §b4):

     | the guest's `path_open` | provider call | answer |
     |---|---|---|
     | asks to write: `oflags` holding `CREAT` or `TRUNC`, or `fs_rights_base` holding `FD_WRITE` (wasmtime 49's test, `crates/wasi/src/p1.rs:2156-2210`, READ) | none | a read-only grant's answer (Decision 6) |
     | `O_DIRECTORY` | one `list` | the listing is kept for the descriptor; an `Errno` passes through |
     | anything else | one `read` | the bytes are staged; `EISDIR` makes a folder descriptor, listed at its first `fd_readdir`; another `Errno` passes through |

   - **The write half is reserved for spec 034:** `write(path, data)`, `mkdir(path)`,
     `remove(path)`, `rmdir(path)`, `rename(src, dst)`, each answering `None` or an `Errno`.
     This specification never calls them, and a read-only mount never will.
   - **No cache across opens.** Two opens of one path make two `read`s. A provider may cache.
4. **An exception or a bad answer is a fault, never an escape.** As `_door` maps a host's
   exception to `HOST_FAULT`:
   - an `Exception` from a provider method, or an answer of the wrong type, gives the guest
     `EIO` and adds a `FileFault` to the record. The run goes on;
   - a bad answer is any value outside the method's annotation, a `Stat` that fails its own
     checks, a listing name that is empty, `.`, `..`, holds `/` or NUL, is not a `str`, or is a
     duplicate, a kind other than `"file"` or `"dir"`, a `Stat` for `/` whose kind is not
     `"dir"`, or an awaitable (closed at once, so it never warns);
   - a `BaseException` that is not an `Exception` (Ctrl-C, `SystemExit`) is recorded as the
     call's stop and raised from `run` on the calling thread, exactly as the door's is
     (spec 011);
   - nothing reaches wasmtime-py's exception slot.
5. **Paths: the runner normalizes; the provider never does.** For every path argument, in
   order:
   - its pointer and length are checked against the memory's size before a byte is read
     (`EFAULT`), as `_door` and `_poll_oneoff` check theirs, with each `i32` taken unsigned;
   - a path over 4,096 bytes is refused (`ENAMETOOLONG`) without being read;
   - it must be UTF-8 without NUL; `.` and empty components are dropped; a component over 255
     bytes is `ENAMETOOLONG`;
   - `..` that climbs above the folder of the descriptor the call names, even for a moment,
     is `EPERM` (63), which is what wasmtime answers on a grant (memo finding 7, EXECUTED;
     cap-std confines each handle to its own folder);
   - a trailing `/` on something that is not a folder is `ENOTDIR`;
   - a normalized path at or under a more specific preopen's guest path (the zip's, a grant's,
     another mount's) is `EPERM`, with no provider call. Only the guest can spell one
     (`/usr/./local/lib` under a mount at `/`), and wasi-libc matched it to this mount by text
     (memo finding 7). Refusing it is the simple rule.

   The exact errno for each malformed form, and its order, is wasmtime's on a grant
   (Decision 6). The provider receives only the normalized `str`.
6. **Every answer on a read-only mount is a read-only grant's.** For each of the 27 shadowed
   calls, on a provider file, a provider folder and a mount's own preopen, the runner answers
   what wasmtime 49 answers on a read-only grant's file, folder and preopen with the same
   arguments. The parity checks (acceptance 2 and 3) are the authority; the builder records the
   table in the landing notes. What the memo already shows: every write-shaped call answers
   `EPERM` (63) on a read-only grant (memo finding 2; the 0.1.0a3 security review's first row,
   EXECUTED), so on a read-only mount it does too, before any provider call. What the runner
   adds:
   - `path_filestat_get` is one `stat`. `fd_filestat_get` on an open provider file needs no
     call: its kind and size come from the staged bytes, and its times are 0 (one call per
     open, so the README says `os.fstat` shows no time). A mount's preopen is a folder.
   - `dev` is a 64-bit hash of the mount's guest path and `ino` a 64-bit hash of the provider
     path, so `os.path.samefile` and `shutil`'s same-file check work, and a run repeats exactly.
     `nlink` is 1.
   - `fd_readdir` serves `.`, `..` and the provider's names with wasmtime's cookie protocol
     (`crates/wasi/src/p1.rs`, READ). The listing made at open serves the first pass; a
     `fd_readdir` from cookie 0 after that lists again, as `rewinddir` expects.
   - `path_readlink` is one `stat`: a file or folder answers `EINVAL` (not a link), else the
     `stat`'s `Errno`. `fd_advise` and `fd_fdstat_set_flags` succeed on a provider descriptor.
   - A call naming a provider descriptor and a descriptor that is not this mount's (a rename or
     a link across) answers what the same call across two read-only grants answers.
7. **Guest memory is checked before it is touched.** Every pointer and length the guest passes
   (paths, `iovec` arrays and each `iovec`, `fd_readdir`'s buffer, every result pointer) is
   checked against the memory's size first, and the call answers `EFAULT` without a provider
   call if one runs past it. An `iovec` array of more than 1,024 entries is `EINVAL`. Nothing
   the guest passes reaches the provider but a normalized path: offsets, flags, cookies,
   rights and pointers stop in the runner.
8. **Limits, each with a default (§4.15).**
   - **Provider calls (decision 42).** `run` and `run_async` take `max_file_calls`, an integer
     or `None`, checked by `_integer_limit`; its default is `DEFAULTS.file_calls`, 10,000, a new
     field of `Defaults`. Every provider method call counts, whatever it answers. The call
     that would pass the limit is not made: the shadow answers `EIO`, records `call.ended =
     "out of file calls"` if nothing ended the call first, and sets the store's epoch deadline
     to 0. The guest stops at its next function entry, and `trapped` is `"out of file calls"`,
     `exit_code` and `fuel_used` are `None`, as for a cancel. `_epoch_answer` gains one rule
     after its recorded-stop check: a call whose `ended` is already set stops, so the first
     named end holds under `cancel=` too.
   - **Open provider descriptors:** at most 1,024 per call (`MAX_MOUNT_FILES`); the next open is
     `EMFILE` (33) without a provider call. Each costs the host one directory handle on the
     placeholder, so this bounds those too.
   - **Staged bytes:** the bytes of every open provider file plus every kept listing (each
     name's UTF-8 bytes and 24 for its entry) are at most the call's `memory_bytes`, and
     unbounded when it is `None`. A `read` whose answer would pass it is `EFBIG` (22), judged on
     `memoryview(answer).nbytes` before any copy; the answer is dropped. A listing is judged as
     it is gathered. The guest could hold as much in its own memory; this keeps host memory,
     which the store's limit does not cover, to the same bound.
9. **Time, cancel and threads.**
   - A provider runs synchronously on the thread that runs the guest; under `run_async` that is
     a worker thread, never the event loop's.
   - Before each provider call the runner checks the call's `cancel` and its deadline (the
     ticker's count against `stop_at`). If either has passed, the provider is not called; the
     guest gets `ECANCELED` or `ETIMEDOUT` and stops at its next function entry, named
     `"cancelled"` or `"deadline"` as today. After the call, `_shared` already checks `cancel`.
   - A provider's own time is outside the epoch and cannot be interrupted (memo finding 8;
     vfs's ADR 084 says the same of its verbs). The README says a provider must bound its own
     calls.
   - One provider may serve concurrent calls. The runner calls it from each call's thread; the
     README says a shared provider must be thread-safe.
   - An embedder whose layer is async may bridge from the worker thread with
     `asyncio.run_coroutine_threadsafe(...).result()` until async providers are specified
     (question 15).
10. **The record.** `Completed` gains `files: FileRecord | None = None`, last, so positional
    use is unchanged; it is `None` for a call without mounts.
    - `FileRecord.calls`: a read-only mapping from each method the runner may call (`stat`,
      `list`, `read`) to its count, zeros included. It equals the provider's own count.
    - `FileRecord.faults`: the first 1,000 `FileFault(method, path, error)`s, where `error` is
      the exception's type name and the first line of its text, at most 200 characters, or
      `"bad answer: <type>"`. No exception object is kept, so a result holds no frame of the
      call.
    - No times (§4.9). Spec 034 adds the refused write-backs vfs records even on exit 0.
11. **Docs.** README, a *Mounts* section: the protocol, `Errno`, `Mount`, the mount at `/`,
    nesting, `HOME`, the limits and `"out of file calls"`, read-only until 034, no links, no
    times from `os.fstat`, whole-file staging (a 1-byte read stages the file), a sync provider
    runs on the guest's thread and must bound its own time and be thread-safe, and the async
    bridge. The *Safety* section names the provider as the embedder's code, called with
    normalized paths only. CHANGELOG: an *Added* line.

## Intent

An embedder can serve a guest's ordinary file calls from its own code, read-only, at any guest
path including `/`, with no new import, no host path opened, every guest argument checked
before the embedder sees it, every provider call counted and limited, and nothing a provider
does able to make `run` raise.

## Design

```
src/wasi_python/mounts.py    Mount, FileProvider, Stat, Errno, FileRecord, FileFault; the mount
                             table, path normalization, staging, the 27 shadows' bodies, the
                             trampoline and reserve modules (wasmtime imported inside functions)
src/wasi_python/runner.py    mounts= and max_file_calls= on run and run_async; Defaults.file_calls;
                             the mount linker; the placeholder and its preopens; _drive
                             instantiates the trampoline; _check_preopens on today's linker;
                             _home_folder sees mounts; _epoch_answer's ended rule; Completed.files
src/wasi_python/__init__.py  exports Mount, FileProvider, Stat, Errno, FileRecord, FileFault
tests/harness/files.py       an in-memory provider for the checks, which counts its own calls
tests/checks/test_v1_4_embedding.py   acceptance 1, 2, 4, 5, 6, 11 (run on all three systems)
tests/checks/test_v1_2_hostile_guest.py   acceptance 7, 8's descriptor check
tests/unit/test_runner_mounts.py   acceptance 3, 8's raw calls, 9, 10 (raw WASI through WAT guests)
README.md, CHANGELOG.md
```

The unit file runs WAT guests on the runner's mount linker with a call on the thread's stack,
as `tests/unit/test_runner_grants.py` drives raw WASI calls today. It is not in `verify`'s list;
adding it would make this build-class. The v1.4 checks are, and they cover the Python-level
parity on all three systems.

## Scope

In: read-only mounts at any guest path a grant may use and at `/`; the mechanism; the protocol's
read half; the limits; the record; the docs.

Out, each for its own specification:
- **Writable mounts: spec 034** (to be drafted after this one's pre-build review).
  `Mount(..., writable=False)`, the protocol's write half, staging write-back at close, at
  `fd_sync` and at every exit, creation, truncation, appends, the refused-write record, and the
  write rows of the parity table. The split keeps each change reviewable: this one is the
  mechanism and the security boundary, about half the memo's 700 to 900 lines; 034 adds
  behaviour on top of a mechanism already judged. vfs can mount read-only views after 032 and
  its writable namespace after 034.
- **Async providers** (question 15), with the tool protocol's async tools: awaited on the
  caller's loop, in slices, under the deadline and `cancel` (memo finding 8).
- **Ranged reads** for large files (`read(path, offset, size)`).
- **Mounts on the command line:** a provider is code, and the command adds no power `run` lacks
  (§3).
- **A per-call working directory** (`cwd=`), and the embedder contract's conformance job, which
  the parity table starts.
- **Read-only code on the import path** (decision 16) stays a typed grant. A mount on
  `PYTHONPATH` may import; it is not claimed.

## Acceptance criteria

Every check counts calls, bytes and errno values; none measures time. Each is seen failing first
on today's runner (where `Mount` cannot be imported, by a stand-in), and the landing notes show
it. The in-memory provider counts its own calls.

1. **`test_a_mount_serves_reads`** (v1.4, both binaries). At `/work`: `open().read()` of a file
   makes exactly one `read`; `os.listdir` exactly one `list`; `os.stat` exactly one `stat`; the
   bytes equal the provider's; `done.files.calls` equals the provider's own counts; a guest that
   reads a grant at `/data` in the same run reads it as before.
2. **`test_a_mount_answers_as_a_grant_does`** (v1.4, both binaries, all three systems). The same
   tree as an in-memory `Mount` and as a read-only `Grant` on disk; every row gives the same
   result or errno: a missing file; a folder opened as a file; a file listed as a folder; a
   missing parent; `..` that escapes; `..` that climbs and returns (`/work/a/../../work/b`);
   open for writing, appending, creating, truncating; `mkdir`, `remove`, `rmdir`, `rename`
   within, `rename` to and from a writable grant, `link`, `symlink`, `utime`, `truncate`;
   `readlink` of a file; `seek`, `tell`, `pread` past the end; a trailing `/` on a file; a path
   over 4,096 bytes; a component over 255 bytes; `os.stat` kind and size; a sorted listing.
   Every write row makes no provider call.
3. **`test_raw_calls_answer_as_a_grant_does`** (unit). Through a WAT guest, each of the 27
   shadowed calls on a provider file, folder and preopen, and on a read-only grant's, with the
   same arguments, including unknown flag bits, a seek that overflows, whence 3, a path that is
   not UTF-8, a NUL in a path, and an absolute path given to a descriptor. The two errnos are
   equal in every case; the table is in the landing notes.
4. **`test_a_mount_at_the_root`** (v1.4, both binaries). A mount at `/`: `/a.txt` and the
   relative `a.txt` read the provider's file; numpy and pandas import (the zip is still the
   zip); `/usr/./local/lib/x` is `EPERM` with no provider call; `HOME` is absent; `-c pass`
   makes a fixed number of provider calls on each binary, pinned in the check and recorded in
   the landing notes. `root=True` or a root path with a mount at `/` raises `ValueError`.
5. **`test_the_file_call_limit_stops_the_run`** (v1.4). With `max_file_calls=5`, a guest that
   stats in a loop ends `trapped == "out of file calls"`, `exit_code is None`, `fuel_used is
   None`, after exactly 5 provider calls, and the line after its loop is not printed. The same
   under `cancel=` never set (the epoch callback's path). `DEFAULTS.file_calls == 10_000`, and
   a default run that stats 10,001 times stops after exactly 10,000 provider calls.
6. **`test_a_mount_keeps_its_deadline_and_cancel`** (v1.4). A provider that sets the call's
   `cancel` inside its third call: the run ends `"cancelled"` and the provider is called exactly
   3 times. A provider that advances the epoch ticker past the deadline by count (the seam
   spec 017's deadline check uses): `"deadline"`, with no provider call after it.
7. **`test_a_provider_fault_never_escapes`** (v1.2 hostile). A provider that raises
   `ValueError`; returns `None`, `"text"` or an object; returns a coroutine; lists a name with
   `/`, a NUL, `..`, a duplicate, or the kind `"link"`; answers `stat("/")` with a file; returns
   more than the staged-bytes limit. The guest gets `EIO` (or `EFBIG` for the last) and exits
   0; `run` raises nothing; `done.files.faults` names each fault and no more; no "never
   awaited" warning is emitted.
8. **`test_guest_arguments_never_reach_the_provider`** (unit, raw WASI through a WAT guest). A
   path or `iovec` past memory, an `iovec` array of 1,025 entries, a `fd_readdir` buffer past
   memory, a path of 4,097 bytes: each answers its errno, and the provider's count is 0. And
   **`test_mount_descriptors_are_bounded`** (v1.2 hostile, both binaries): 1,025 open provider
   files give `EMFILE` on the last; the run exits 0; the placeholder is empty during the run
   and gone after it.
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
12. `uv run pytest` green with `--accept-judge`; lost 0; grew 0. `ruff check` and `ruff format
    --check` clean. A release dry run passes every job, Windows included.
13. The build review is also a security review of the new surface against the threat model
    (`../research/2026-10-16-a-principal-engineers-direction.md` §2), recorded under
    `../reviews/`.

## For the owner's confirmation

None open here. Three of these decisions (3, 8, and the names) are the agent's choice where the
owner's decisions were silent; they are recorded as questions 54 to 56 in
`../questions-for-the-owner.md`, and nothing waits on them.

## Landing notes

Not built.
