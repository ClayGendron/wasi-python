# 034 — Writable mounts

- **Status:** drafted 2026-10-17; reviewed before build the same day
  (`../reviews/034-writable-mounts-spec-2026-10-17.md`, which is also a security review of the
  design; verdict: not ready as written, but close) and revised against its ten findings (its
  Disposition). It waits on the reviewer's short confirmation. Not built. It is written on spec
  032 as built for review (`spec/032-a-filesystem-provider`, commit `c69cb31`, read only; its
  seams are named here by function: `_Files`, `_ask`, `_take`, `_drop`, `_across`,
  `FileRecord.calls`). 032 may change in its build review. **034 rebases on what lands:** where
  this text names a piece of 032, it means that piece as landed, and the confirmation or the
  build review checks the rebase. §5.6 does not require a pre-build review here (no import,
  export, artifact or recipe change); 032's precedent asked for one, because this widens a
  security boundary. **The build review doubles as a security review** (acceptance 15).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/mounts.py`, `src/wasi_python/runner.py`),
  `src/wasi_python/__init__.py`'s exports, judge additions and one judge change in `tests/`
  (Decision 11), `README.md`, `CHANGELOG.md`. **Not build-class:** it touches no `scripts/`,
  `recipes/`, `downloads/SHA256SUMS` or release workflow. What runs where, as in 032: the
  Python-level checks in `tests/checks/test_v1_4_embedding.py` and the raw parity rows in
  `tests/unit/test_runner_grants.py` run on Windows, Linux and macOS (the `verify` job runs
  those two files); the guard and hostile checks (`tests/checks/test_v1_2_hostile_guest.py`,
  `tests/unit/test_runner_mounts.py`) run on the judge's machine only, since they test the
  runner's own host-independent code.
- **Depends on:** 032 (read-only mounts: the mechanism, the protocol's read half, the limits,
  the record), built and in its build review; 034 lands after it. 011 (shared host functions),
  015 (`cancel`, `run_async`, the deferred Ctrl-C, the exit hook), 017 (typed grants, `HOME`),
  025 (nothing writable by default), 030 (a cancel during a door call is named), all landed.
- **Research it stands on:** `../research/2026-10-17-a-filesystem-provider-for-the-runner.md`
  (findings 2, 6 and 10, and "What it decides": the write half, staging, write-back at close,
  sync and every exit, the refused-write record; its model wrote, appended, renamed, removed and
  recorded a refused write-back on exit 0, EXECUTED on both binaries); 032 and its review (the
  mechanism this stands on, judged there); this specification's pre-build review and its
  evidence (`grant_writes.txt`, `grant_across.txt`, `preopen_rw.txt`, `unflushed.txt`,
  `tempfile_model.txt`, `tempfile_model_create.txt`: what a writable grant answers, and the
  memo's model with a create at open, EXECUTED there on both binaries); wasmtime 49's preview1
  and filesystem code (READ: `context/prior_art/wasmtime-v49/crates/wasi/src/p1.rs:625-692`, a
  write fills from the first non-empty `ciovec`, an append descriptor ignores `fd_pwrite`'s
  offset as Linux does, and an append moves the position to the file's size;
  `p1.rs:1540-1548`, `fd_fdstat_set_flags` refuses the sync flags with `EINVAL` and toggles
  `APPEND`; `filesystem.rs:951-978`, `CREATE` or `TRUNCATE` opens for writing whatever the
  rights; `filesystem.rs:987-991`, sync flags at open are `ENOTSUP`; `filesystem.rs:994-1000`,
  `O_DIRECTORY` with `CREAT`, `EXCL` or `TRUNC` is `EINVAL`; `filesystem.rs:1003-1008`, a
  write-shaped open on a read-only preopen is `EPERM`); CPython 3.15's `Lib/tempfile.py`
  (READ by the review: `TemporaryFile` on WASI opens a new name with `O_CREAT | O_EXCL` and
  unlinks it while open); vfs's spec 169 §b2 to §b8 and spec 172 §3 and acceptance 7 (READ,
  never edited). Every claim about wasmtime is READ; every claim about what the built runner
  answers is the builder's to EXECUTE, in the parity table.
- **Decided by:** the owner's answers (`../decisions.md`): 13 (vfs runs on this runner; this
  project never edits vfs); 37's study of vfs (a denial is a result; vfs counts calls and
  records refused writes even on exit 0); 41 (a mount at `/`, exclusive with `root=`; the zip
  stays at `/usr/local/lib`); 42 (10,000 provider calls per run, then the run stops and names
  it); 17 (governance is the embedder's); 24 (nothing writable by default, constitution §4.15).

## The problem

Spec 032 lets an embedder serve a guest's file reads from its own code. A guest cannot yet
write there. vfs needs a writable namespace: its guests write CSVs, make folders, rename and
remove files, all checked per access by vfs, with every refused write recorded even when the
guest exits 0 (decision 37; vfs spec 169 §b5). Today an embedder can only give a writable host
folder (spec 017) and read the changes back after the run, which gives up checking each write.

032 reserved this half for 034. It built the mechanism and the security boundary; this
specification adds behaviour on top of a mechanism already judged.

## Terms

032's terms hold (provider, mount, shadow, forward, trampoline, placeholder, provider number,
staging). New here:

- **Buffer:** the bytes the runner holds for one open provider file: staged at open, changed by
  the guest's writes.
- **Dirty:** a buffer whose bytes the provider has not yet been given.
- **Write-back:** one `write(path, data)` call that hands the provider a dirty buffer's whole
  content.
- **Write half:** the provider methods that change the provider's state: `write`, `mkdir`,
  `remove`, `rmdir`, `rename`.
- **May write:** a descriptor opened with `CREAT` or `TRUNC` in `oflags`, or `FD_WRITE` in
  `fs_rights_base` (wasmtime 49's rule, `filesystem.rs:951-978`: `os.open(p, O_CREAT |
  O_RDONLY)` writes, EXECUTED by the review on a writable grant).
- **Ending:** how the guest stopped: a normal exit, `proc_exit`, a trap of any kind, its
  deadline, a cancel, `"out of fuel"`, `"out of file calls"`.
- **Owed buffer:** a dirty buffer whose write-back the runner did not make at the guest's close
  (a cancel, the deadline or the file-call limit came first). Its number stays reserved, and it
  is written back at the ending.
- **The walk:** the ending's write-backs, made after the guest has stopped.
- **Unlinked descriptor:** an open provider descriptor whose path the guest itself removed or
  replaced in this call. A file's writes are kept in its buffer and never written back, as POSIX
  drops the data of an unlinked file at its last close; a folder answers as an open, removed
  directory does (Decision 7).

## Decisions

1. **Nothing is writable unless the embedder says so (spec 025, §4.15).**
   - `Mount(provider, guest, *, writable=False)`. `writable` is keyword-only and must be a real
     `bool`: `"yes"`, `1` or `None` is a `TypeError`, as `Grant`'s is (spec 017). The default
     stays read-only, and a read-only mount never calls a write-half method, whatever the
     provider has.
   - **Checked before any work**, beside 032's checks (`TypeError`, naming the mount's position,
     guest path and the method): a writable mount's provider has callable `write`, `mkdir`,
     `remove`, `rmdir` and `rename`, none a coroutine function (async providers are a later
     specification, question 15).
   - A call with no root, no grants and no mounts still has nothing writable. A writable mount
     is one more explicit embedder choice, as a writable grant is. The command line gains no
     mount (032's Scope).
   - Every 032 placement rule holds for writable mounts: any guest path a grant may use, or
     `/` (decision 41, exclusive with a root); nothing at or under `/usr/local/lib`; no two
     preopens at one guest path; nesting allowed either way. The runner judges guest paths only.
     Whether two providers share state (one mount read-only, another writable, over the same
     store) is the embedder's business: it binds their authority (decision 17).
2. **The protocol's write half.** A provider answers; it does not raise (032 Decision 3). Each
   method answers `None` for success or an `Errno` member; any other value, an awaitable, or an
   `Exception` is a fault (032 Decision 4: the guest gets `EIO`, the record gets a `FileFault`);
   a `BaseException` that is not an `Exception` is the call's stop, raised from `run` (spec 011).

   ```python
   class WritableFileProvider(FileProvider, Protocol):   # exported for type checkers
       def write(self, path: str, data: bytes) -> None | Errno: ...  # the whole file
       def mkdir(self, path: str) -> None | Errno: ...
       def remove(self, path: str) -> None | Errno: ...
       def rmdir(self, path: str) -> None | Errno: ...
       def rename(self, src: str, dst: str) -> None | Errno: ...

   run(argv, mounts=[Mount(store, "/work", writable=True)])
   ```

   Paths reach the provider normalized, by 032 Decision 5, and only those. The contract each
   method keeps (POSIX's, in preview1 numbering):
   - **`write`** replaces the whole content of a file, creating it if it is missing. `EISDIR`
     when the path is a folder; `ENOENT` when a parent is missing; `ENOTDIR` when a parent is a
     file. `data` is a `bytes` object, a copy the provider may keep: a view could be held past
     the call and would pin or expose the runner's buffer. `write(path, b"")` is how the runner
     creates and truncates at open (Decision 3), so a provider sees an empty first version of
     every file a guest creates.
   - **`mkdir`** makes one folder. `EEXIST` when the path exists; `ENOENT` and `ENOTDIR` for a
     parent as above.
   - **`remove`** removes a file. `EISDIR` when the path is a folder (Linux's `unlink` answer,
     the reference; a macOS grant answers `EPERM`, so that row is asserted per system,
     Decision 12); `ENOENT` when it is missing.
   - **`rmdir`** removes an empty folder. `ENOTEMPTY` when it holds anything; `ENOTDIR` when it
     is a file; `ENOENT` when it is missing.
   - **`rename`** moves within the mount, with POSIX's replace rule: a file replaces a file at
     `dst`; a folder replaces an empty folder; `ENOTEMPTY` when `dst` is a folder that is not
     empty; `EISDIR` when `src` is a file and `dst` a folder; `ENOTDIR` when `src` is a folder
     and `dst` a file; `ENOENT` when `src` is missing. The cases the runner answers itself are
     in Decision 6. (A writable grant gives these answers, EXECUTED by the review on macOS,
     `grant_writes.txt`.)
   - **Quotas, permissions, conflicts** are the provider's: `EACCES`, `EROFS`, `ENOSPC`,
     `EDQUOT`, `ESTALE`, `EBUSY`, `ETIMEDOUT` pass to the guest unchanged. The runner knows
     nothing about why (decision 17).
3. **Opening for writing: a create or a truncation lands at open; at most two provider calls
   per open.** On a writable mount, an open by a descriptor that may write is served by this
   table, after 032's checks (the path rules, the guest memory checks, `MAX_MOUNT_FILES`, which
   answer before any call). The table is read top to bottom and the first row that matches
   wins (`CREAT | EXCL | TRUNC` is the `"x"` row). `EXCL` without `CREAT` is ignored, as
   wasmtime ignores it.

   | the guest's open | calls | answer |
   |---|---|---|
   | sync flags (`SYNC`, `DSYNC`, `RSYNC`) in `fdflags` | none | `ENOTSUP`, as wasmtime (`filesystem.rs:987-991`) |
   | `O_DIRECTORY` with `CREAT`, `EXCL` or `TRUNC` | none | `EINVAL`, as wasmtime (`filesystem.rs:994-1000`) |
   | `CREAT` and `EXCL` (`"x"`) | `stat`, then `write(path, b"")` if missing | a file or folder: `EEXIST`; `ENOENT`: the create's answer; another `Errno` passes through |
   | `CREAT` and `TRUNC` (`"w"`) | `write(path, b"")` | success: an empty, clean buffer (the file now exists, or is now empty); an `Errno` (`EISDIR`, `ENOENT`, `ENOTDIR`, the provider's own) passes through |
   | `TRUNC` without `CREAT` | `stat`, then `write(path, b"")` if a file | a file: the truncation's answer; a folder: `EISDIR`; an `Errno` passes through |
   | `CREAT` without `TRUNC` or `EXCL` (`"a"`, `os.open(O_CREAT \| O_WRONLY)`) | `read`, then `write(path, b"")` if missing | the bytes: staged, clean; `EISDIR`: `EISDIR`; `ENOENT`: the create's answer; another `Errno` passes through |
   | may write, without `CREAT` or `TRUNC` (`"r+"`) | `read` | the bytes: staged, clean; `EISDIR`: `EISDIR`; an `Errno` passes through |

   - **The create's answer** is the `write(path, b"")`'s: success gives an empty, clean
     buffer; an `Errno` passes to the guest (`ENOENT` for a missing parent, `ENOTDIR` for a file
     parent, by Decision 2's contract, or the provider's refusal) and is recorded with
     `at == "open"` (Decision 11). So a create under a missing parent, or one the provider
     refuses, fails at open, as on a grant.
   - **Why at open (the review's finding 1).** A file that existed only in the runner's buffer
     until its close broke what real programs do with a file they hold open: CPython's
     `tempfile.TemporaryFile` on WASI opens a new name with `O_CREAT | O_EXCL` and unlinks it at
     once; `mkstemp` and `NamedTemporaryFile` then rename; lock files rely on `O_EXCL`. The
     review ran the memo's model, which staged as the draft did: `TemporaryFile` failed with
     `ENOENT`, a second `O_EXCL` open of a new name succeeded, and a stray file was left
     (EXECUTED, `tempfile_model.txt`). With a create at open the same model gave a grant's
     results (`tempfile_model_create.txt`). vfs's 169b makes one verb per open and so has the
     same gap (INFERRED by the review); a vfs adapter meets this design as it is.
   - **Every buffer starts clean.** A buffer becomes dirty only by a write or a size change
     (Decision 4); `open(p, "w").close()` makes one call, at open.
   - **`O_EXCL` within a call is exact:** the `stat` sees any file this call created, since
     creation reached the provider. Across concurrent writers to one provider it is as atomic as
     that provider's `stat` then `write` (the README says so).
   - **The staging bound** (032 Decision 8) judges every `read` answer here as in 032 (`EFBIG`,
     the answer dropped). A `stat` or a create stages nothing.
   - The descriptor remembers its mount, its normalized path, whether it may write, and its
     `APPEND` flag (from `fdflags`; `fd_fdstat_set_flags` toggles it, as wasmtime does,
     `p1.rs:1540-1548`). `fd_fdstat_get` on a descriptor that may write reports `FD_WRITE` in
     its rights, as wasmtime reports a write-opened file of a writable grant (032's
     `FILE_RIGHTS` omits it for every provider file; the parity table records the exact bytes).
4. **The buffer: writes, appends, truncation.** These calls make no provider call and count
   none. Each answers as wasmtime answers on a writable grant's file (Decision 12), with the
   bytes in the buffer:
   - `fd_write` and `fd_pwrite` take the first non-empty `ciovec`, as wasmtime does
     (`p1.rs:632`). On an append descriptor every write goes at the end and `fd_pwrite`'s offset
     is ignored (Linux semantics, as wasmtime, `p1.rs:655-662`); after an append the position
     is the buffer's size (`p1.rs:682-692`). Otherwise a write at or past the end grows the
     buffer, filling any gap with zeros.
   - `fd_filestat_set_size` truncates or grows (zeros) the buffer.
   - Any of these marks the buffer dirty, even when the bytes do not change, as a grant's file
     has its `mtime` touched.
   - **Order of checks:** a `fd_pwrite` offset, a seek position or a size at or above `2**63`
     answers what wasmtime answers (032 answers `EINVAL` for reads) before the growth bound is
     judged.
   - **The staging bound holds for growth.** A write or a size change whose result would take
     the call's staged bytes (every open or owed buffer plus every kept listing, 032 Decision 8)
     past the bound (`memory_bytes`, or 4 GiB when it is `None`) answers `EFBIG` (22) and
     changes nothing. The check is on the new size before any byte is allocated, so a
     `fd_pwrite` at offset `2**40` never allocates.
   - `fd_filestat_get` on a provider file reports the buffer's size, as 032 says.
   - A write on a descriptor that may not write, or on a folder, answers what wasmtime answers
     on a writable grant's (the parity table records it).
5. **Write-back at close and at sync.**
   - **`fd_close` of a dirty buffer** makes one `write`, then frees the number, whatever the
     answer, as POSIX's `close` frees the descriptor even when it fails. The guest gets the
     `write`'s answer: success, its `Errno`, or `EIO` for a fault. Python's `close()` raises
     `OSError` with that errno. A clean buffer closes with no call.
   - **`fd_sync` and `fd_datasync`** of a dirty buffer make one `write` and answer its result.
     On success the buffer is clean; on a refusal it stays dirty, so the close tries again (and
     a second refusal is recorded again). A clean buffer syncs with no call. A sync on a
     descriptor that may not write, or on a folder, answers as wasmtime on a writable grant;
     a sync of a mount's own preopen stays forwarded (`EBADF` on both kinds of grant, EXECUTED
     by the review, `preopen_rw.txt`).
   - **An unlinked descriptor** (Decision 7) never writes back; its close and sync make no call.
   - **A write-back the runner does not make at close or sync is owed, not refused (the
     review's finding 2).** 032's `_ask` refuses a provider call when the call's `cancel` is
     set (`ECANCELED`), its deadline has passed (`ETIMEDOUT`) or the file-call limit is reached
     (`EIO`); the close or sync answers the guest that errno. Once the call has ended, spec
     030's entry guard answers `EIO` (`stopped`) before any shadow runs. In every one of these
     cases:
     - the write-back is **not recorded** at the close or sync;
     - at a sync, the buffer stays dirty and its descriptor open;
     - at a close, the descriptor is closed for the guest (any later call on its number
       answers `EBADF`), but **its number stays reserved**: it is not returned to `_Files.free`,
       it still counts toward `MAX_MOUNT_FILES`, and its bytes still count toward the staging
       bound, until the walk. So no later open can reuse the number, the number of owed buffers
       is bounded by construction (even if an embedder clears its own `cancel`), and the walk's
       ascending order is well defined;
     - under 030's guard the shadow never runs, so the number is simply still open in the
       table;
     - the walk then writes the buffer back, or records it **once**, at `"exit"`, if it does
       not.
     Nothing the guest wrote is lost to a stop without a record.
   - Every refused or faulted write-back is recorded (Decision 11).
6. **The namespace calls.** One provider call each, after 032 Decision 5's path rules. Those
   rules already answer `EPERM`, with no call, for a path that climbs out of the mount or is at
   or under a more specific preopen's guest path (the zip, a grant, another mount):
   - `path_create_directory` is one `mkdir`; `path_unlink_file` one `remove`;
     `path_remove_directory` one `rmdir`; `path_rename` one `rename`, when both descriptors are
     this mount's.
   - **The runner answers, with no provider call:**
     - a `mkdir`, `remove`, `rmdir` or `rename` naming the mount itself (`/`): what a writable
       grant answers for its own preopen (the parity table records the errno; `os.unlink` of a
       preopen is `EPERM` on a macOS grant, `grant_writes.txt`, so that row is per system);
     - a `rename` whose `dst` is inside `src` (`a` to `a/b`): `EINVAL` (28), as a writable grant
       answers (EXECUTED by the review, `grant_writes.txt`);
     - a `rename` or `rmdir` whose path (`src` or `dst` for a rename) is **strictly above** a
       more specific preopen's guest path: `EBUSY` (10), so the guest's view of other preopens
       stays where it was put. (At or under one is 032's `EPERM`, above.)
     - a `rename` or `path_link` between this mount and any other descriptor (a grant, the zip,
       another mount, even one with the same provider): `EPERM` (63) when the other side is
       read-only (a read-only grant, the zip, a read-only mount), as wasmtime answers between a
       writable and a read-only grant (EXECUTED by the review, `grant_across.txt`); `EXDEV`
       (75), what POSIX answers across two filesystems, only when both sides may be written.
       `shutil.move` then copies and removes, through the ordinary calls. This extends 032's
       `_across`, which answers `EPERM` for every side today;
     - a `rename` of a path onto itself: one `stat`, and success when it exists, else the
       `stat`'s `Errno`, with no `rename` (a grant's answers, `grant_writes.txt`).
7. **Open descriptors follow the guest's own changes, as POSIX descriptors follow the file.**
   After a namespace call **succeeds** (the provider answered `None`), the runner updates its
   own table for this call, before it answers the guest:
   - after `rename(src, dst)`: every descriptor of this mount whose path is `dst` or under it
     becomes unlinked (it named what was replaced); then every descriptor whose path is `src` or
     under it takes the same path under `dst`. So a file renamed while open writes back to its
     new name, and a folder descriptor renamed while open resolves later relative paths under
     its new name;
   - after `remove(path)` or `rmdir(path)`: every descriptor at that path becomes unlinked.
     `tempfile.TemporaryFile`, which opens, unlinks and keeps writing (CPython's choice on WASI,
     whose `os.name` is `"posix"`), then never writes its bytes back;
   - **an unlinked file** keeps its buffer for reads, writes and `fstat` until its close, which
     makes no call; its bytes count toward the staging bound until then;
   - **an unlinked folder** answers as POSIX treats an open, removed directory (the review's
     finding 5): every path call relative to it (`path_open`, `path_filestat_get`,
     `path_readlink`, the set-times call, and the namespace calls) answers `ENOENT`, and
     `fd_readdir` from cookie 0 lists only `.` and `..`, each with no provider call. Its kept
     listing is dropped when it is unlinked. Without this, its old path could name another
     folder (one made after the `rmdir`, or one renamed over it), and the descriptor would read
     that folder's contents.
   The runner knows only this call's own changes. A change made by another run or by the
   embedder while a descriptor is open is not seen: the write-back goes to the path the
   descriptor holds, and the provider may answer `ESTALE` (Decision 12's table).
8. **Write-back at every ending.** The runner plays the part a kernel plays for a process: what
   the guest gave `fd_write` is in the file, and a stopped process does not take it back.
   - **When:** after the guest has stopped by any ending, on the call's thread, outside every
     host function. In 032's `_call_deferred`, the walk runs after `_drive` returns and after
     `_fuel_used` has been read, before `table.record()` builds the result, inside spec 015's
     deferred-Ctrl-C scope. It goes through the call's table in ascending provider number and
     makes one `write` for each dirty buffer of a writable mount that is not unlinked, owed
     buffers included, then frees every buffer.
   - **The walk has its own counted call path, never `_ask`** (the review's finding 2). `_ask`
     needs a caller for `_epoch_now`, and its limit branch sets `call.ended`, which would make
     `_fuel_used` answer `None` for an exit-0 run. The walk's path counts the call (in
     `_Files.total` and `calls`), checks only the file-call limit, the deferred Ctrl-C and
     the interpreter's exit, keeps 032 Decision 4's fault boundary, never sets `call.ended` or
     `call.stopped`, and never touches the epoch or the fuel.
   - **At every ending that returns a `Completed`:** a normal exit and `proc_exit` with any
     code; a trap; `"out of fuel"`; `"deadline"`; `"cancelled"`; `"out of file calls"`. The
     ending stops the guest, not the file system. 032 Decision 10's checks of `cancel` and the
     deadline before each provider call do **not** apply to the walk: the guest is gone.
   - **The walk is bounded in calls and bytes, not in time** (the review's finding 3). After a
     stop the runner makes at most min(1,024, the file calls left) `write`s (owed buffers keep
     their numbers, Decision 5), handing over at most the staging bound in bytes in total
     (`memory_bytes`, 1 GiB by default, or 4 GiB when it is `None`), with one transient copy of
     one buffer at a time. Each call's time is the provider's (032: a provider bounds its own
     calls). So a mounted run may return after its deadline by the time those calls take. The
     README says so in these numbers, and that a provider which must honour the call's deadline
     answers `ETIMEDOUT`, which `refused` records. That is how vfs's own design treats a flush
     after its timeout (169 §b8: each verb waits `future.result(timeout=remaining)`), so the
     split holds: the runner hands the write over, and the provider decides whether there is
     time. Question 71 asks the owner to confirm this rule.
   - **A cancelled `run_async`** ends `"cancelled"` on its worker; `run_async` awaits the worker
     before raising `CancelledError` (READ by the review, `run_async`), so the walk finishes
     first. There is then no result to carry its refusals; the provider, which answered them,
     is the only record.
   - **No walk when the call raises.** When the call will raise instead of returning (a
     `BaseException` recorded as the call's stop, from the door or a provider, spec 011 and 032
     Decision 4, which includes a Ctrl-C noted while the guest ran), `_drive` re-raises and the
     walk never runs: the host is being interrupted, provider code must not run after it, and
     no result could report a refusal. Write-backs made at open, close or sync before it stand.
     A Ctrl-C that arrives during the walk is deferred: the walk stops after the current
     provider call, the rest are dropped, and the deferral raises `KeyboardInterrupt` as the
     call returns. A `BaseException` from a provider during the walk stops it the same way and
     is raised.
   - **No walk when the interpreter is exiting** (the review's finding 3). When spec 015's exit
     hook has run (`_stop_async_calls`, `_hook["exiting"]`), the walk makes no call, and it
     stops before its next call if the hook runs during it. At interpreter exit, loops and
     stores may be closing, and a provider that bridges to a stopped loop with
     `run_coroutine_threadsafe(...).result()` (032's advice) would block exit for ever
     (INFERRED by the review). The README says unclosed files are not written back at
     interpreter exit. No result is returned then, so nothing is recorded.
   - **When the provider fails during the walk:** an `Errno` answer is recorded as refused; an
     `Exception` or a bad answer is a `FileFault` and is recorded as refused with `EIO`; in
     both cases the walk goes on to the next buffer. Nothing raises from `run`.
   - **The file-call limit counts the walk's calls** (decision 42 bounds the embedder's work, so
     no call escapes it). A write-back the limit would pass is not made and is recorded as
     refused with the cause `"limit"`. A run that ended `"out of file calls"` therefore writes
     nothing back, and its record names every dirty file it left, each once.
   - The walk changes neither `exit_code`, `trapped` nor `fuel_used`. Whether a refused write
     makes the run a failure is the embedder's decision (decision 17); vfs, for one, turns it
     into its stage status (169 §b5).
9. **Links, symlinks and times.**
   - **Links and symlinks are refused.** `path_link` and `path_symlink` within a writable mount
     answer `ENOTSUP` (58) with no provider call; `path_link` between a mount and any other
     descriptor answers as `rename` across does (Decision 6: `EPERM` or `EXDEV`). The protocol
     has no link: a link to a provider file would need a second name for one buffer, and a
     symlink's target is text the runner would have to resolve on every later path.
     `path_readlink` stays 032's (one `stat`; `EINVAL` for a file or folder). On a read-only
     mount these calls stay 032's (`EPERM`, as a read-only grant).
   - **Times are the provider's.** `fd_filestat_set_times` and `path_filestat_set_times` on a
     writable mount succeed and change nothing, with no provider call, where a writable grant
     would accept the same call; otherwise they answer the grant's errno. This includes the
     mount's own preopen, by path and by descriptor, which 032 forwards to the read-only
     placeholder (`EPERM`): on a writable mount the preopen's set-times is served, as a
     writable grant accepts it (EXECUTED by the review, `preopen_rw.txt`). `os.utime` and
     `shutil.copy2` then work, and `os.stat` shows the provider's `mtime_ns`. On a read-only
     mount they stay `EPERM`. vfs makes the same choice (169 §b2: accept and ignore).
10. **Limits and costs, inherited from 032 and kept.**
    - **The file-call limit** (`max_file_calls`, `DEFAULTS.file_calls`, 10,000): every
      provider call counts, the write half, the creates at open and the walk included. The
      limit's ending during the guest's run is 032's (`"out of file calls"`, the epoch deadline
      set to 0, Decision 9's invariant). No new limit and no new `Defaults` field.
    - **Open provider numbers** (`MAX_MOUNT_FILES`, 1,024) bound the open and owed buffers, and
      so the walk.
    - **Staged bytes** stay 032's single bound, now also on growth (Decision 4) and on owed
      buffers (Decision 5). The `bytes` copy a write-back hands the provider is transient and is
      not counted: at most one buffer's size beyond the bound, during one call.
    - **Write amplification is the provider's to bound** (the review's finding 4). Each close or
      `fsync` of a changed file hands over the whole file. A guest can grow a buffer to the
      staging bound with one `fd_filestat_set_size`, then loop "write one byte, `fsync`": up to
      `max_file_calls` write-backs of up to the staging bound each (10,000 × 1 GiB with the
      defaults, in practice limited by the deadline and the host's copy speed), where a grant
      would write one byte per sync. A provider that persists or versions every write can be
      made to store far more than the guest ever held. The runner adds no byte budget:
      `EDQUOT` and `ENOSPC` already pass through. The README says this in these numbers and
      advises a provider that persists to quota or rate-limit its writes and answer `EDQUOT`.
      A byte budget on write-backs is a later specification if a consumer asks for one. The
      buffer calls themselves (a grow is a host fill of up to the bound, with no provider call
      and no fuel) are bounded per call by the staging bound and over the run by the deadline:
      the class every host function is in, not a new one.
    - **No new shadow, import or forward.** The 29 shadows exist from 032; this specification
      changes what their bodies do on a writable mount. Forwards stay fuel-neutral, and a call
      served by the runner costs the guest only its call instruction. A mounted run's fuel
      still depends only on what it forwards (032 Decision 1, acceptance 12).
    - **The placeholder stays read-only.** A writable mount is still preopened on 032's empty,
      runner-owned placeholder with `preopen_dir(placeholder, guest, False)`. Every write is
      served by a shadow from the buffer or the provider; wasmtime never writes for a mount. So
      a mistaken forward meets an empty folder that wasmtime refuses to write (`EPERM`,
      `filesystem.rs:1003-1008`), never a host path.
11. **The record.** `FileRecord` (032 Decision 11) gains `refused` and `refused_total`, last, so
    positional use is unchanged.
    - `FileRecord.calls` maps all eight methods (`stat`, `list`, `read`, `write`, `mkdir`,
      `remove`, `rmdir`, `rename`) to their counts, zeros included, for every call with mounts,
      read-only ones too, so its shape never depends on the mounts (032's `METHODS` grows to
      eight). It equals the provider's own count.
    - **This is a judge change to 032's checks** (the review's finding 6). Every 032 assertion
      that compares a `calls` mapping, or the in-memory provider's own count, with a three-key
      literal is rewritten to the eight-key shape with the write half's zeros. In 032's build
      (`c69cb31`) these are in `tests/checks/test_v1_4_embedding.py` (among them
      `dict(done.files.calls) == provider.calls == {"stat": 2, "list": 2, "read": 2}` and
      `provider.calls == {"stat": 5, "list": 0, "read": 0}`) and in
      `tests/unit/test_runner_mounts.py` (among them `m.table.record().calls == {"stat": 2,
      "list": 0, "read": 0}` and `provider.calls == {"stat": 0, "list": 2, "read": 1}`); the
      builder finds every one by searching for `calls ==` and lists them in the landing notes.
      Each rewrite only adds the five zero keys, so each check asserts more than before (that a
      read-only run made no write-half call), never less. The harness provider counts all eight
      methods. The change is named in the `--accept-judge` reason, and the review sees the
      judge-hash line (AGENTS.md, rule 4).
    - `FileRecord.refused`: the first 1,000 `RefusedWrite`s, in the order they happened, each
      `RefusedWrite(mount, method, paths, errno, at, cause)`:
      - `mount`: the mount's guest path; `paths`: the provider path, or `(src, dst)` for a
        rename, as the provider saw them;
      - `method`: the write-half method (`"write"`, `"mkdir"`, `"remove"`, `"rmdir"`,
        `"rename"`);
      - `errno`: the provider's `Errno`, or `Errno.EIO` for a fault or for the limit;
      - `at`: `"open"` (a create or truncation at open, Decision 3), `"call"` (a namespace call
        the guest made), `"close"`, `"sync"` or `"exit"` (the walk);
      - `cause`: `"refused"` (the provider answered an `Errno`), `"fault"` (an exception or a
        bad answer, also in `faults`) or `"limit"` (the file-call limit; no call was made).
    - `FileRecord.refused_total`: every refusal counted, kept or not (the review's finding 7).
      `len(refused) < refused_total` says the list was cut, so a refused write-back is never
      silent, even after a guest has filled the list with cheap refusals.
    - **What it holds:** every write-half call that did not succeed, and every write-back the
      runner owed but did not make, whatever the exit code. An owed write-back appears once,
      at `"exit"` (Decision 5). It holds no refusal of a read-half call (`stat`, `list`,
      `read`), even one made by an open that asked to write: the guest saw that answer at its
      open, before anything was written.
    - It is a convenience. The provider answered every refusal itself and may keep its own
      record; the runner's makes the common case need no bookkeeping in the embedder.
    - No times (§4.9). `RefusedWrite` holds no exception object and no frame.
12. **A writable mount answers as a writable grant does, except where this table says.** The
    reference is wasmtime 49 on Linux, as in 032 Decision 6: for each shadowed call that can
    write, on a provider file, a provider folder and a writable mount's own preopen, the runner
    gives what wasmtime gives on a writable grant's file, folder and preopen with the same
    arguments (the errno and every byte it writes to the guest, with `dev`, `ino`, times and
    descriptor numbers left out). 032's read-only rows and its deliberate differences hold
    unchanged. A row whose grant answer differs between Linux, macOS and Windows is asserted per
    system or left out, and the landing notes name it. Two are known (EXECUTED by the review on
    macOS, `grant_writes.txt`): `os.remove` of a folder (`EPERM` on macOS, Linux's `EISDIR` from
    the provider everywhere) and `os.unlink` of the preopen.

    The deliberate differences, each the price of whole-file staging or a guard, none a way out
    of the mount:

    | input | a writable grant (wasmtime) | a writable mount | why |
    |---|---|---|---|
    | a file's unflushed writes | seen at once by `stat`, a listing and another open | seen only through the descriptor that made them, until its close or `fsync` | whole-file staging; one provider call per write-back |
    | two descriptors writing one path | one shared file | two buffers; the later write-back replaces the earlier | whole-file write-back (question 72) |
    | a write the provider refuses | fails at the write (`ENOSPC`, `EDQUOT`) | fails at the close or `fsync`, with the provider's errno, and is recorded | the provider sees content only at write-back; a create or truncation still fails at open, as on a grant |
    | a write past the staging bound | the host disk's limit | `EFBIG` (22) | host memory is bounded (032 Decision 8) |
    | `rename` or `link` between a mount and another writable preopen | succeeds between two writable grants (`grant_across.txt`) | `EXDEV` (75); `shutil.move` copies and removes | a provider's files are not the host's |
    | `link` or `symlink` within a mount | works on POSIX hosts | `ENOTSUP` (58) | the protocol has no link (Decision 9) |
    | `utime` and the set-times calls | sets the times | succeeds and changes nothing | the protocol has no times (Decision 9) |
    | `rename` or `rmdir` strictly above a nested preopen | allowed: `rmdir("/w1/./inner")` removes a nested writable grant's empty host folder (`grant_across.txt`) | `EBUSY` (10), no call | the guest's view of other preopens stays fixed (Decision 6) |
    | a rename or removal by another run or by the embedder while a descriptor is open | the descriptor follows the file | the write-back goes to the path the descriptor holds | the runner sees only this call's own changes (Decision 7) |
    | a file left open when the interpreter exits during a `run_async` call | its written bytes are in the file | not written back | provider code must not run at interpreter exit (Decision 8) |

13. **Safety: what a writable mount must never reach.**
    - **The runtime's own files.** The zip's preopen at `/usr/local/lib` is more specific than
      any mount, `/` included. A write-half call or a write-shaped open whose normalized path is
      at or under it is `EPERM` with no provider call (032 Decision 5); a rename or `rmdir`
      strictly above it is `EBUSY` (Decision 6). So numpy, pandas and the stdlib stay the zip's
      under a writable mount at `/`.
    - **Other grants and mounts.** The same rules hold for every more specific preopen: a
      read-only grant inside a writable mount stays read-only (wasmtime answers it, `EPERM`), and
      a writable mount cannot rename, remove or write over it.
    - **The host.** No host path is opened for a mount, and the placeholder stays read-only
      (Decision 10). Nothing a guest writes reaches a host file through a mount.
    - **State across runs is the embedder's.** A writable mount whose provider keeps its state
      can hold what a later run meets: modules a later run imports (with a writable mount at
      `/`, a guest run with `-c` has `/`, its working directory, first on `sys.path`), and data
      files that change a later run's answers (`/etc/mime.types`, `/usr/share/zoneinfo/…`,
      named by the threat model). This is the cross-run hazard the threat model names for a
      shared writable root (`../research/2026-10-16-a-principal-engineers-direction.md` §2,
      "Cross-run contamination"), now in a store the embedder owns. The README names both, with
      spec 001's rule: one writable namespace per untrusted program, or one the embedder checks.
    - **`HOME`.** The runner makes no `HOME` in a mount, writable or not (032 Decision 2): making
      one would be a write into the embedder's store that the guest did not ask for. A writable
      mount at `/tmp` holds `tempfile`'s files (`TMPDIR` stays `/tmp`); an embedder may pass
      `HOME` in `env`. Spec 017's rule (`HOME` in a writable grant at `/tmp`) is unchanged.
14. **Docs.** README, the *Mounts* section grows a *Writable mounts* part: `writable=True`; the
    write half and each method's contract; the open table, the create and truncation at open
    (so a provider sees an empty first version of a new file), and `O_EXCL`'s atomicity across
    writers; write-back at close, `fsync` and every ending, and none when the call raises or the
    interpreter is exiting; the walk's bound after a stop, in Decision 8's numbers, and that a
    provider honouring the deadline answers `ETIMEDOUT`; why a refused write shows at close (so
    `with` blocks and `close()` raise it); `refused`, `refused_total` and `RefusedWrite`; the
    deliberate differences (visibility until close, independent buffers, last write-back wins);
    write amplification, with Decision 10's numbers and the `EDQUOT` advice; links and times;
    that bytes still in a Python buffer when the guest stops by `os._exit` or a trap never
    reached the runner (a normal exit's finalization closes Python's files); the staging bound
    on growth; the cross-run hazard, modules and data files; and `HOME`. The *Safety* section
    says a writable mount is the embedder's explicit grant of a write channel into its own code.
    CHANGELOG: an *Added* line, and a note that `FileRecord.calls` now has eight keys.

## Intent

An embedder can let a guest write to a namespace served by its own code: create, write, append,
truncate, make and remove folders, rename within it. Every change reaches the provider as a
whole-file `write` or one namespace call, on a normalized path, counted and limited. A file
exists from its open, as on a grant. What the guest wrote is handed over at close, at `fsync`
and at every ending the runner reports. Every write the provider refuses, or the runner could
not make, is in the result even when the guest exits 0, and the result says when its list was
cut. Nothing is writable unless the embedder says `writable=True`.

## Design

```
src/wasi_python/mounts.py    the writable flag in the mount table; the open table for writing,
                             with the create and truncation at open (Decision 3); the buffer's
                             write calls (fd_write, fd_pwrite, fd_filestat_set_size, fd_sync,
                             fd_datasync) and the growth bound; write-back at close and sync,
                             owed buffers that keep their numbers; the namespace calls (mkdir,
                             unlink, rmdir, rename), their runner-answered cases and _across's
                             EPERM or EXDEV; descriptor paths that follow renames and removals,
                             unlinked files and folders; links and times (the preopen's
                             set-times served); FD_WRITE in a writable descriptor's rights; the
                             walk's own counted call path; RefusedWrite, FileRecord.refused and
                             refused_total; METHODS of eight; WritableFileProvider
src/wasi_python/runner.py    Mount's writable check among the mount checks; the walk in
                             _call_deferred after _fuel_used and before table.record(), skipped
                             when the call raises or the exit hook has run
src/wasi_python/__init__.py  exports RefusedWrite and WritableFileProvider
tests/harness/files.py       032's in-memory provider gains the write half; it counts all eight
                             methods and can refuse, fault or raise per path and per method
tests/checks/test_v1_4_embedding.py   acceptance 1, 2, 4, 5, 6, 9, 11 (all three systems); 032's
                             three-key `calls` assertions rewritten to eight keys (Decision 11)
tests/unit/test_runner_grants.py      acceptance 3, the raw write rows (all three systems)
tests/checks/test_v1_2_hostile_guest.py   acceptance 7, 10
tests/unit/test_runner_mounts.py      acceptance 8, 12, 16, and the guards' exact parts; 032's
                             three-key `calls` assertions rewritten to eight keys
README.md, CHANGELOG.md
```

The raw write rows extend 032's table-driven WAT module: the same rows run on a writable grant
and on a writable mount, so a row is data, not a new guest.

### Build order

One builder, in four steps, each green before the next, starting from 032 as landed (not from
its worktree). The write half is about 500 to 800 lines on 032's `mounts.py` (the review's
estimate, INFERRED). It is not split: a namespace that can create files but not remove or
rename them would be its own half-feature, and vfs needs all of it at once (decision 13).

1. **The writable flag, the open table with the create at open, and the buffer** (Decisions 1,
   3, 4), with write-back at close and sync and owed buffers (Decision 5), `RefusedWrite`,
   `refused_total`, and the eight-key `calls` with its judge change (Decision 11). The harness
   provider's write half first.
2. **The namespace calls** (Decision 6) and the table's following of renames and removals,
   files and folders (Decision 7).
3. **The walk** (Decision 8): every ending, owed buffers, the limit, faults, a raise, the exit
   hook.
4. **The parity table's write rows, links and times** (Decisions 9 and 12), and the docs. Then
   **one release dry run**, so the Linux and Windows answers fill the per-system rows before
   the build review, not at the end.

## Scope

In: writable mounts at any guest path a grant may use and at `/`; the protocol's write half;
writing opens with creation and truncation at open, writes, appends, truncation, `fsync`;
folders, removal and rename within a mount; write-back at close, sync and every ending; the
refused-write record; the write rows of the parity table; links and times as decided; the docs.

Out, each for its own specification if ever wanted:
- **Async providers** (question 15), with the read half's.
- **Ranged reads and writes** (`read(path, offset, size)`, `write(path, offset, data)`), for
  files too large to stage; with them, a log appended over a long run need not be rewritten
  whole at each close.
- **A byte budget on write-backs** (Decision 10).
- **One buffer per path shared by every descriptor in a call,** which would remove the
  visibility and last-write-back-wins differences at the cost of reference-counted buffers
  (question 72).
- **Links and symlinks in a provider,** and **times** set through the protocol.
- **`HOME` in a mount.**
- **Mounts on the command line** (032's Scope: a provider is code).
- **sqlite3 over a mount** is not claimed: it needs ranged writes and locking.
- **Permissions and mode bits:** preview1 has no `chmod`; access is the provider's answer.

## Acceptance criteria

Every check counts calls, bytes, fuel and errno values; none measures time. Each is seen failing
first, and the landing notes show it. The new checks fail on 032's runner, where `writable` is
not a `Mount` field. For acceptance 7, 8, 9, 10, 12 and 16, which exist to catch a missing
guard, "seen failing" means against the built runner with **one guard removed** at a time, as
032 does. The guards: no writable check (a read-only mount calls the write half); no create at
open (a new file exists only from its first write-back); no growth bound; no `dst`-inside-`src`
rule; no `EBUSY` rule; no `EPERM`-or-`EXDEV` rule across; no unlinking of file descriptors; no
unlinked-folder rule; no reserved number for an owed buffer; no fault catch in the walk; no
limit in the walk; no skip when the call raises; no skip at the exit hook; no `refused_total`.
Each named check fails on its own guard's removal and passes with it. The in-memory provider
counts its own calls. A deadline or a cancel is reached by the epoch ticker's count, or by a
provider that sets `cancel`, as specs 017 and 030's checks do, never by a sleep.

1. **`test_a_writable_mount_serves_writes`** (v1.4, both binaries). At `/work`, writable:
   `open("/work/a.txt", "w")`, a write and a close make exactly two `write`s (`b""` at open, the
   bytes at close) and no other call; `open(p, "w").close()` makes exactly one `write(p, b"")`;
   `open("/work/n.txt", "x")` makes one `stat` and one `write(b"")`, and `os.path.exists` of it
   is `True` while it is open; `"a"` on an existing file makes one `read` and one `write`
   holding the old bytes then the new; `"r+"` with no write makes one `read` and no `write`; a
   write, an `os.fsync` and a close make exactly one content `write`; `os.mkdir`, `os.remove`,
   `os.rmdir` and `os.rename` within the mount make exactly one call each; pandas' `to_csv` then
   `read_csv` of the same path round-trips; `done.files.calls` equals the provider's own counts,
   all eight keys; `done.files.refused` is empty and `refused_total == 0`.
2. **`test_a_writable_mount_answers_as_a_writable_grant_does`** (v1.4, both binaries, all three
   systems). The same tree as an in-memory writable `Mount` and as a writable `Grant` on disk;
   each row gives the same result or errno and leaves the same tree: create; `"x"` on an
   existing file; a second `"x"` open of a name just created (`EEXIST`); create under a missing
   parent and under a file; open a folder for writing; `os.open(p, O_CREAT | O_RDONLY)` then
   `os.write`; append; truncate by `"w"` and by `os.truncate`; `pwrite` past the end (zeros in
   the gap); a seek past the end then a write; a write on a read-only descriptor; `pwrite` on an
   append descriptor; `mkdir` of an existing path and under a missing parent; `rmdir` of a
   non-empty folder and of a file; `remove` of a folder (per system) and of a missing file;
   `rename` file to new, file over file, folder over an empty folder, folder over a non-empty
   folder, file over folder, folder over file, folder into its own subfolder, a path onto
   itself; `rename` and `link` to a read-only grant (`EPERM`); `tempfile.TemporaryFile` (write,
   seek, read back, close); `NamedTemporaryFile` with `os.replace` inside its `with`;
   `shutil.copyfile`, `shutil.copy2`, `shutil.rmtree`, `os.replace` for an atomic save;
   `os.fstat` size after a write; a sorted listing after each change, once the writer has
   closed. Decision 12's deliberate differences are asserted as its table says, not as parity.
3. **`test_raw_write_calls_answer_as_a_writable_grant_does`** (unit, in `test_runner_grants.py`,
   all three systems). Through 032's table-driven WAT module, each shadowed call that can write
   (`path_open` with each `oflags`, `fdflags` and rights shape, sync flags, `EXCL` without
   `CREAT`, and `O_DIRECTORY` with `CREAT` included; `fd_fdstat_get` on a write-opened file;
   `fd_write` and `fd_pwrite` with one and two `ciovec`s and with an offset at `2**63`;
   `fd_filestat_set_size`; `fd_sync` and `fd_datasync`, on a file and on the preopen;
   `fd_fdstat_set_flags` with `APPEND`; `fd_allocate`; `path_create_directory`,
   `path_unlink_file`, `path_remove_directory`, `path_rename`; the set-times calls, on a file
   and on the preopen by path and by descriptor) on a provider file, folder and preopen, and on
   a writable grant's, with the same arguments. The whole results are equal (errno and every
   byte written, with `dev`, `ino`, times and numbers masked), except Decision 12's
   differences; a row that differs by system is asserted per system. The table is in the
   landing notes.
4. **`test_refused_writes_are_recorded_on_exit_0`** (v1.4, both binaries). A provider that
   answers `Errno.EACCES` to a content `write("/denied.txt", …)` and accepts its `b""`: the
   guest's `with open(...)` block raises `PermissionError` (errno 2) at its close; the guest
   catches it and exits 0; `exit_code == 0`, and `done.files.refused` is exactly one
   `RefusedWrite("/work", "write", ("/denied.txt",), Errno.EACCES, "close", "refused")`. The
   same for a refused `fsync` (`at == "sync"`, then a second entry at the close), for a refused
   create (`open(p, "w")` raises at open; `at == "open"`), and for a refused `mkdir` and
   `rename` (`at == "call"`). A refused `stat` at a writing open records nothing.
   `refused_total` equals the number of entries in each case.
5. **`test_writes_land_at_every_ending`** (v1.4, both binaries). A guest opens a file in a
   writable mount with `os.open`, writes with `os.write` and does not close it (so no Python
   object closes it), then: exits 0; calls `os._exit(3)`; raises an uncaught exception; spins
   until its fuel cap; spins until its deadline; spins until `cancel=` is set; stats in a loop
   until `max_file_calls`. In the first six, the provider holds the bytes after `run` returns,
   from exactly one content `write` made by the walk; `refused` is empty; `trapped`,
   `exit_code` and `fuel_used` are the ending's as without mounts (an exit-0 run's `fuel_used`
   is not `None`). In the last, no content `write` is made, and `refused` names the file once,
   with `at == "exit"` and `cause == "limit"`.
6. **`test_a_failed_write_back_at_the_ending_is_recorded`** (v1.4). Three dirty files at the
   ending; the provider answers `Errno.EIO` for the first, raises `ValueError` for the second
   and accepts the third: `run` raises nothing; `refused` holds the first (`"refused"`) and the
   second (`"fault"`, `Errno.EIO`, `at == "exit"`); `faults` names the `ValueError`; the third is
   written; the walk made exactly three `write`s, in ascending provider number.
7. **`test_a_call_that_raises_writes_nothing_back`** (v1.2 hostile). A dirty file left open,
   then a door host that raises `KeyboardInterrupt`: `run` raises it and the provider's content
   `write` count is 0. Two dirty files, and a provider whose first walk `write` raises
   `KeyboardInterrupt`: `run` raises it and the second file's `write` count is 0. A pending
   Ctrl-C on the main thread (the host sends itself SIGINT, as 030's check does): `run` raises
   `KeyboardInterrupt` and the content `write` count is 0. In a child process, a `run_async`
   call with a dirty file stopped by spec 015's exit hook (`_stop_async_calls` called directly,
   as 015's exit check does): the content `write` count is 0 (guard: the skip at the exit hook).
   Guard: the skip when the call raises.
8. **`test_a_writable_mount_is_asked_for`** (unit). A `Mount` with no `writable`, on a provider
   that has the write half: every write-shaped call (each row of Decision 3's table, `mkdir`,
   `remove`, `rmdir`, `rename`, `link`, `symlink`, set-times) answers `EPERM` and the write-half
   counts stay 0 (guard: the writable check). `writable` of `"yes"`, `1` and `None` is a
   `TypeError`; `writable=True` with a provider missing any one of the five methods, or with a
   coroutine-function `write`, is a `TypeError` naming it; each before any work (the provider's
   and a door host's counts stay 0). 025's `test_nothing_is_writable_by_default` passes
   unchanged.
9. **`test_open_files_follow_the_guests_renames_and_removals`** (v1.4, both binaries).
   `tempfile.TemporaryFile` in a writable mount at `/tmp`: write, seek, read back, close; the
   provider sees one `write(b"")` at open, one `remove`, and no other `write`, and is left with
   no file (guards: the create at open, and unlinking). `NamedTemporaryFile` with `os.replace`
   inside its `with` lands the bytes at the final name and nothing at the temp name. A file
   opened, renamed, written and closed is written back to its new name and never to its old
   one. A file held open while another path is renamed over it is never written back. A folder
   descriptor renamed while open resolves a later relative open under its new name. An open
   folder removed with `rmdir`, then remade with `mkdir`: a relative open, a relative `stat` and
   a re-list from cookie 0 through the old descriptor answer `ENOENT`, `ENOENT` and only `.`
   and `..`, each with no provider call (guard: the unlinked-folder rule).
10. **`test_a_writable_root_mount_keeps_the_runtime_and_other_grants`** (v1.2 hostile, both
    binaries). A writable mount at `/` with a read-only grant at `/data` and a writable mount at
    `/work/out` inside it: writing, making a folder in, removing or renaming into
    `/usr/local/lib/x`, `/usr/./local/lib/x` and `/data/x` is `EPERM` with no provider call;
    `rmdir` of `/usr` or `/usr/local`, and renaming `/usr` or `/work`, are `EBUSY` with no call
    (guard: the `EBUSY` rule); renaming `/a.txt` to `/work/out/a.txt` is `EXDEV` and to
    `/data/a.txt` is `EPERM`, with no call (guard: the rule across); renaming `/d` to `/d/e` is
    `EINVAL` with no call (guard: the `dst`-inside-`src` rule); numpy and pandas import; the
    placeholder is empty during the run and gone after it.
11. **`test_links_and_times_in_a_writable_mount`** (v1.4). `os.link` and `os.symlink` within the
    mount are `ENOTSUP`, `os.link` to a writable grant is `EXDEV` and to a read-only grant
    `EPERM`, all with no provider call; `os.utime` of a file and of the mount's own path
    succeeds with no call, and `os.stat` then shows the provider's `mtime_ns`; `shutil.copy2`
    within the mount succeeds.
12. **`test_writes_are_bounded`** (unit). With a staging bound the test sets through
    `memory_bytes`: a `fd_pwrite` of one byte at offset `2**40`, a seek to the bound then a
    write, a `fd_filestat_set_size` past the bound, and two files whose sum passes it each
    answer `EFBIG` and leave the buffer's size unchanged, with the runner's held-bytes count
    (a counting seam on the mount table) never above the bound (guard: the growth bound). With
    `max_file_calls` set so that the walk's write-backs pass it, the provider's total call
    count equals the limit exactly, every unmade write-back is one `RefusedWrite` with
    `cause == "limit"`, and the run's `fuel_used` is the same as with no limit (guard: the limit
    in the walk). A walk `write` that raises `ValueError` does not stop the walk (guard: the
    fault catch in the walk). 1,001 refused `mkdir`s and one refused walk write-back:
    `len(refused) == 1000` and `refused_total == 1002` (guard: `refused_total`).
13. **032's checks pass, with only their record shape changed** (Decision 11: the three-key
    `calls` literals become eight-key ones, a named judge change). Among them 032's acceptance
    10 and 12: a call without mounts uses today's linker and invokes no shadow; forwards cost
    no fuel. The ratchet shows no fuel growth on any accepted check.
14. `uv run pytest` green with `--accept-judge` (naming Decision 11's change); lost 0; grew 0.
    `ruff check` and `ruff format --check` clean. A release dry run passes every job, Windows
    included.
15. **The build review is also a security review** of the write channel against the threat
    model (`../research/2026-10-16-a-principal-engineers-direction.md` §2: the host, the
    embedder's other runs, the runtime's own files, the integrity of the result, the embedder's
    resources), recorded under `../reviews/`. It re-runs the guard checks with each guard
    removed.
16. **`test_a_close_stopped_by_a_cancel_is_owed`** (unit, `test_runner_mounts.py`, raw WAT; the
    review's finding 2). A guest opens a provider file for writing and writes to it; then a
    provider whose `stat` sets the call's `cancel` is called by `path_filestat_get`, and
    `fd_close` of the dirty file follows at once, with no function entry between. The close
    answers `ECANCELED` (11); a `path_open` after it makes no provider call; the number stays
    reserved (a seam on the table: not in `free`, counted in `opened`); the walk makes exactly
    one `write` of that buffer; `refused` is empty (guard: the reserved number). The same with
    the file-call limit reached instead: the close answers `EIO`, no `write` is made, and
    `refused` holds the file once, at `"exit"`, `cause == "limit"`.

## The owner's choices

None open here. Two of these decisions are the agent's choice where the owner's decisions were
silent; they are recorded as questions 71 and 72 in `../questions-for-the-owner.md`, and
nothing waits on them for build: Decision 8's write-back after a cancel or a deadline, with no
walk at interpreter exit, and Decision 12's one buffer per descriptor. The pre-build review
recommends the owner answers 71 before the landing lane lands 034, since it defines what a
deadline means for a mounted run.

## Landing notes

Not built.
