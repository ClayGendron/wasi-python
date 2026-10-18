# 034 — Writable mounts

- **Status:** drafted 2026-10-17; not yet reviewed, not built. It is written on spec 032 as
  confirmed for build (`032-a-filesystem-provider.md`, with its review
  `../reviews/032-a-filesystem-provider-spec-2026-10-17.md`). 032 is in build now, on
  `spec/032-a-filesystem-provider`, and may change in its build review. **034 rebases on what
  lands:** where this text names a piece of 032 (`Mount`, `FileRecord`, `FileFault`, `Errno`,
  `MAX_MOUNT_FILES`, the 29 shadows, provider numbers from `2**30`, the staging bound, Decision
  5's path rules), it means that piece as landed, and 034's pre-build review checks the rebase.
  §5.6 does not require a pre-build review here (no import, export, artifact or recipe change);
  032's precedent recommends one, because this widens a security boundary. **The build review
  doubles as a security review** (acceptance 15).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/mounts.py`, `src/wasi_python/runner.py`),
  `src/wasi_python/__init__.py`'s exports, judge additions in `tests/`, `README.md`,
  `CHANGELOG.md`. **Not build-class:** it touches no `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or release workflow. What runs where, as in 032: the Python-level
  checks in `tests/checks/test_v1_4_embedding.py` and the raw parity rows in
  `tests/unit/test_runner_grants.py` run on Windows, Linux and macOS (the `verify` job runs
  those two files); the guard and hostile checks (`tests/checks/test_v1_2_hostile_guest.py`,
  `tests/unit/test_runner_mounts.py`) run on the judge's machine only, since they test the
  runner's own host-independent code.
- **Depends on:** 032 (read-only mounts: the mechanism, the protocol's read half, the limits,
  the record), in build; 034 lands after it. 011 (shared host functions), 015 (`cancel`,
  `run_async`, the deferred Ctrl-C), 017 (typed grants, `HOME`), 025 (nothing writable by
  default), all landed; 030 (a cancel during a door call is named), as 032 amends it.
- **Research it stands on:** `../research/2026-10-17-a-filesystem-provider-for-the-runner.md`
  (findings 2, 6 and 10, and "What it decides": the write half, staging, write-back at close,
  sync and every exit, the refused-write record; its model wrote, appended, renamed, removed and
  recorded a refused write-back on exit 0, EXECUTED on both binaries); 032 and its review (the
  mechanism this stands on, judged there); wasmtime 49's preview1 and filesystem code (READ:
  `context/prior_art/wasmtime-v49/crates/wasi/src/p1.rs:625-692`, a write fills from the first
  non-empty `ciovec`, an append descriptor ignores `fd_pwrite`'s offset as Linux does, and an
  append moves the position to the file's size; `p1.rs:1540-1548`, `fd_fdstat_set_flags`
  refuses the sync flags with `EINVAL` and toggles `APPEND`; `filesystem.rs:987-991`, sync flags
  at open are `ENOTSUP`; `filesystem.rs:994-1000`, `O_DIRECTORY` with `CREAT`, `EXCL` or `TRUNC`
  is `EINVAL`; `filesystem.rs:1003-1008`, a write-shaped open on a read-only preopen is `EPERM`);
  vfs's spec 169 §b4 to §b8 and spec 172 §3 and acceptance 7 (READ, never edited: one verb per
  open, staging, write-back at close, sync and on every exit, "a refused write-back is never
  silent", the verb and staging budgets). Every claim below about wasmtime is READ; every claim
  about what the built runner answers is the builder's to EXECUTE, in the parity table.
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
- **Ending:** how the guest stopped: a normal exit, `proc_exit`, a trap of any kind, its
  deadline, a cancel, `"out of fuel"`, `"out of file calls"`.
- **Unlinked descriptor:** an open provider descriptor whose path the guest itself removed or
  replaced in this call. Its writes are kept in its buffer and never written back, as POSIX
  drops the data of an unlinked file at its last close.

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
     the call and would pin or expose the runner's buffer.
   - **`mkdir`** makes one folder. `EEXIST` when the path exists; `ENOENT` and `ENOTDIR` for a
     parent as above.
   - **`remove`** removes a file. `EISDIR` when the path is a folder (Linux's `unlink` answer;
     the parity table confirms the writable grant's, and the build review corrects this line
     if wasmtime on Linux answers otherwise); `ENOENT` when it is missing.
   - **`rmdir`** removes an empty folder. `ENOTEMPTY` when it holds anything; `ENOTDIR` when it
     is a file; `ENOENT` when it is missing.
   - **`rename`** moves within the mount, with POSIX's replace rule: a file replaces a file at
     `dst`; a folder replaces an empty folder; `ENOTEMPTY` when `dst` is a folder that is not
     empty; `EISDIR` when `src` is a file and `dst` a folder; `ENOTDIR` when `src` is a folder
     and `dst` a file; `ENOENT` when `src` is missing. The cases the runner answers itself are
     in Decision 6.
   - **Quotas, permissions, conflicts** are the provider's: `EACCES`, `EROFS`, `ENOSPC`,
     `EDQUOT`, `ESTALE`, `EBUSY` pass to the guest unchanged. The runner knows nothing about why
     (decision 17).
3. **Opening for writing: at most two provider calls per open.** On a writable mount, an open
   that asks to write (032's test: `oflags` holding `CREAT` or `TRUNC`, or `fs_rights_base`
   holding `FD_WRITE`) is served by this table, after 032's checks (the path rules, the guest
   memory checks, `MAX_MOUNT_FILES`, which answer before any call). The first call is on the
   target; the second, a `stat` of the parent, is made only when the target is missing and the
   open may create it, and never when the parent is the mount itself (`/` is always a folder,
   032 Decision 4).

   | the guest's open | first call | answer |
   |---|---|---|
   | sync flags (`SYNC`, `DSYNC`, `RSYNC`) in `fdflags` | none | `ENOTSUP`, as wasmtime (`filesystem.rs:987-991`) |
   | `O_DIRECTORY` with `CREAT`, `EXCL` or `TRUNC` | none | `EINVAL`, as wasmtime (`filesystem.rs:994-1000`) |
   | `CREAT` and `EXCL` (`"x"`) | `stat` | a file or folder: `EEXIST`; `ENOENT`: the parent check, then a new, empty, dirty buffer; another `Errno` passes through |
   | `CREAT` and `TRUNC` (`"w"`) | `stat` | a file: an empty, dirty buffer (nothing is read); a folder: `EISDIR`; `ENOENT`: the parent check, then a new, empty, dirty buffer; another `Errno` passes through |
   | `TRUNC` without `CREAT` | `stat` | a file: an empty, dirty buffer; a folder: `EISDIR`; an `Errno` passes through |
   | `CREAT` without `TRUNC` or `EXCL` (`"a"`, `os.open(O_CREAT \| O_WRONLY)`) | `read` | the bytes: staged, clean; `EISDIR`: `EISDIR`; `ENOENT`: the parent check, then a new, empty, dirty buffer; another `Errno` passes through |
   | `FD_WRITE` without `CREAT` or `TRUNC` (`"r+"`) | `read` | the bytes: staged, clean; `EISDIR`: `EISDIR`; an `Errno` passes through |

   - **The parent check** is one `stat` of the normalized parent: a folder lets the open go on;
     a file is `ENOTDIR`; an `Errno` passes through. It is how the runner tells a missing
     target from a missing parent, which one `ENOENT` cannot (032's `read` contract makes
     `ENOTDIR` mean "a parent is a file", but a missing ancestor and a missing target are both
     `ENOENT`). So a create under a missing parent fails at open, as on a grant.
   - **A new file is dirty from its open,** so `open(p, "w").close()` writes an empty file. A
     truncating open of an existing file is dirty too, so the truncation lands even if nothing
     is written. A staged file is clean until the guest changes it.
   - **The staging bound** (032 Decision 8) judges every `read` answer here as in 032 (`EFBIG`,
     the answer dropped). A `stat`-served open stages nothing.
   - The descriptor remembers its mount, its normalized path, whether it may write (by wasmtime
     49's rule above) and its `APPEND` flag (from `fdflags`; `fd_fdstat_set_flags` toggles it, as
     wasmtime does, `p1.rs:1540-1548`).
   - vfs's 169b makes one verb per open because its error carries the failing path (§b4); a
     preview1 `Errno` does not, so the runner spends the parent's `stat`, and only on a create of
     a missing file in a subfolder.
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
   - **The staging bound holds for growth.** A write or a size change whose result would take
     the call's staged bytes (every open buffer plus every kept listing, 032 Decision 8) past the
     bound (`memory_bytes`, or 4 GiB when it is `None`) answers `EFBIG` (22) and changes
     nothing. The check is on the new size before any byte is allocated, so a `fd_pwrite` at
     offset `2**40` never allocates.
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
     descriptor that may not write, or on a folder, answers as wasmtime on a writable grant.
   - **An unlinked descriptor** (Decision 7) never writes back; its close and sync make no call.
   - **A cancel or deadline before a write-back** (032 Decision 10's check, and spec 030's entry
     guard once the call has ended): the `write` is not made, and the buffer stays dirty in the
     call's table even when the guest's close freed its number. It is then written back at the
     ending (Decision 8). Nothing the guest wrote is lost to a stop.
   - Every refused, faulted or unmade write-back is recorded (Decision 11).
6. **The namespace calls.** One provider call each, after 032 Decision 5's path rules (which
   already refuse, with no call, a path that climbs out of the mount or reaches a more specific
   preopen):
   - `path_create_directory` is one `mkdir`; `path_unlink_file` one `remove`;
     `path_remove_directory` one `rmdir`; `path_rename` one `rename`, when both descriptors are
     this mount's.
   - **The runner answers, with no provider call:**
     - a `mkdir`, `remove`, `rmdir` or `rename` naming the mount itself (`/`): what a writable
       grant answers for its own preopen (the parity table records the errno);
     - a `rename` whose `dst` is inside `src` (`a` to `a/b`): `EINVAL` (28), POSIX's answer;
     - a `rename` or `rmdir` whose path (`src` or `dst` for a rename) is at or above a more
       specific preopen's guest path (a grant, the zip, another mount, inside this mount):
       `EBUSY` (10), so the guest's view of other preopens stays where it was put;
     - a `rename` between this mount and any other descriptor (a grant, the zip, another
       mount, even one with the same provider): `EXDEV` (75), what POSIX answers across two
       filesystems. `shutil.move` then copies and removes, through the ordinary calls;
     - a `rename` of a path onto itself: one `stat`, and success when it exists, else the
       `stat`'s `Errno`, with no `rename`.
   - A namespace call with a provider path relative to an unlinked folder descriptor answers
     `ENOENT` with no call (Decision 7).
7. **Open descriptors follow the guest's own changes, as POSIX descriptors follow the file.**
   After a namespace call **succeeds** (the provider answered `None`), the runner updates its
   own table for this call, before it answers the guest:
   - after `rename(src, dst)`: every descriptor of this mount whose path is `dst` or under it
     becomes unlinked (it named what was replaced); then every descriptor whose path is `src` or
     under it takes the same path under `dst`. So a file renamed while open writes back to its
     new name, and a folder descriptor renamed while open resolves later relative paths under
     its new name;
   - after `remove(path)` or `rmdir(path)`: every descriptor at that path becomes unlinked.
     `tempfile.TemporaryFile`, which opens, unlinks and keeps writing on POSIX (CPython's choice
     on WASI, whose `os.name` is `"posix"`), then never writes its bytes back;
   - an unlinked file keeps its buffer for reads, writes and `fstat` until its close, which
     makes no call; its bytes count toward the staging bound until then.
   The runner knows only this call's own changes. A change made by another run or by the
   embedder while a descriptor is open is not seen: the write-back goes to the path the
   descriptor holds, and the provider may answer `ESTALE` (Decision 12's table).
8. **Write-back at every ending.** The runner plays the part a kernel plays for a process: what
   the guest gave `fd_write` is in the file, and a stopped process does not take it back.
   - **When:** after the guest has stopped by any ending, on the call's thread, outside every
     host function, before `Completed` is built. The runner walks the call's table in ascending
     provider number and makes one `write` for each dirty buffer of a writable mount that is not
     unlinked, then frees every buffer. A dirty buffer whose number the guest already closed
     (Decision 5's cancel rule) is in the walk.
   - **At every ending that returns a `Completed`:** a normal exit and `proc_exit` with any
     code; a trap; `"out of fuel"`; `"deadline"`; `"cancelled"`; `"out of file calls"`. The
     ending stops the guest, not the file system. 032 Decision 10's checks of `cancel` and the
     deadline before each provider call do **not** apply to these write-backs: the guest is
     gone, and the work is bounded (at most one `write` per open number, 1,024, each within the
     staging bound, each counted). The README says a provider must bound its own time (032),
     and that the deadline bounds the guest, with the ending's write-backs after it. A
     `run_async` whose task is cancelled ends `"cancelled"` on its worker, so its write-backs
     are made before `CancelledError` is raised; there is then no result to carry their
     refusals, and the provider, which answered them, is the only record.
   - **At an ending that raises, none.** When the call will raise instead of returning (a
     `BaseException` recorded as the call's stop, from the door or a provider, spec 011 and 032
     Decision 4; or a Ctrl-C pending under spec 015's deferral), no ending write-back is made:
     the host is being interrupted, provider code must not run after it, and no result could
     report a refusal. Write-backs made at close or sync before it stand. A Ctrl-C or a
     `BaseException` that arrives during the ending's write-backs stops them after the current
     provider call; the rest are dropped and the call raises it.
   - **When the provider fails during the ending:** an `Errno` answer is recorded as refused;
     an `Exception` or a bad answer is a `FileFault` and is recorded as refused with `EIO`; in
     both cases the walk goes on to the next buffer. Nothing raises from `run`.
   - **The file-call limit counts these calls** (decision 42 bounds the embedder's work, so no
     call escapes it). A write-back the limit would pass is not made and is recorded as refused
     with the cause `"limit"`. A run that ended `"out of file calls"` therefore writes nothing
     back, and its record names every dirty file it left.
   - The ending's write-backs change neither `exit_code`, `trapped` nor `fuel_used`. Whether a
     refused write makes the run a failure is the embedder's decision (decision 17); vfs, for
     one, turns it into its stage status (169 §b5).
9. **Links, symlinks and times.**
   - **Links and symlinks are refused.** `path_link` and `path_symlink` into a writable mount
     answer `ENOTSUP` (58) with no provider call; `path_link` between a mount and any other
     descriptor answers `EXDEV`, as `rename` does. The protocol has no link: a link to a
     provider file would need a second name for one buffer, and a symlink's target is text the
     runner would have to resolve on every later path. `path_readlink` stays 032's (one `stat`;
     `EINVAL` for a file or folder). On a read-only mount these calls stay 032's (`EPERM`, as a
     read-only grant).
   - **Times are the provider's.** `fd_filestat_set_times` and `path_filestat_set_times` on a
     writable mount succeed and change nothing, with no provider call, where a writable grant
     would accept the same call; otherwise they answer the grant's errno. `os.utime` and
     `shutil.copy2` then work, and `os.stat` shows the provider's `mtime_ns`. On a read-only
     mount they stay `EPERM`. vfs makes the same choice (169 §b2: accept and ignore).
10. **Limits and costs, inherited from 032 and kept.**
    - **The file-call limit** (`max_file_calls`, `DEFAULTS.file_calls`, 10,000): every
      provider call counts, the write half and the ending's write-backs included. The limit's
      ending is 032's (`"out of file calls"`, the epoch deadline set to 0, Decision 9's
      invariant). No new limit and no new `Defaults` field.
    - **Open provider numbers** (`MAX_MOUNT_FILES`, 1,024) bound the dirty buffers, and so the
      ending's write-backs.
    - **Staged bytes** stay 032's single bound, now also on growth (Decision 4). The `bytes`
      copy a write-back hands the provider is transient and is not counted: at most one buffer's
      size beyond the bound, during one call.
    - **No new shadow, import or forward.** The 29 shadows exist from 032; this specification
      changes what their bodies do on a writable mount. Forwards stay fuel-neutral, and a call
      served by the runner costs the guest only its call instruction. A mounted run's fuel
      still depends only on what it forwards (032 Decision 1, acceptance 12).
    - **The placeholder stays read-only.** A writable mount is still preopened on 032's empty,
      runner-owned placeholder with `preopen_dir(placeholder, guest, False)`. Every write is
      served by a shadow from the buffer or the provider; wasmtime never writes for a mount. So
      a mistaken forward meets an empty folder that wasmtime refuses to write (`EPERM`,
      `filesystem.rs:1003-1008`), never a host path.
11. **The record.** `FileRecord` (032 Decision 11) gains `refused`, last, so positional use is
    unchanged.
    - `FileRecord.calls` maps all eight methods (`stat`, `list`, `read`, `write`, `mkdir`,
      `remove`, `rmdir`, `rename`) to their counts, zeros included, for every call with mounts,
      read-only ones too, so its shape never depends on the mounts. It equals the provider's own
      count.
    - `FileRecord.refused`: the first 1,000 `RefusedWrite`s, in the order they happened, each
      `RefusedWrite(mount, method, paths, errno, at, cause)`:
      - `mount`: the mount's guest path; `paths`: the provider path, or `(src, dst)` for a
        rename, as the provider saw them;
      - `method`: the write-half method (`"write"`, `"mkdir"`, `"remove"`, `"rmdir"`,
        `"rename"`);
      - `errno`: the provider's `Errno`, or `Errno.EIO` for a fault or for the limit;
      - `at`: `"call"` (a namespace call the guest made), `"close"`, `"sync"` or `"exit"` (the
        ending's write-back);
      - `cause`: `"refused"` (the provider answered an `Errno`), `"fault"` (an exception or a
        bad answer, also in `faults`) or `"limit"` (the file-call limit; no call was made).
    - **What it holds:** every write-half call that did not succeed, and every write-back the
      runner owed but did not make, whatever the exit code. It holds no refusal of a read-half
      call (`stat`, `list`, `read`), even one made by an open that asked to write: the guest saw
      that answer at its open, before anything was written.
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
    system or left out, and the landing notes name it.

    The deliberate differences, each the price of whole-file staging or a guard, none a way out
    of the mount:

    | input | a writable grant (wasmtime) | a writable mount | why |
    |---|---|---|---|
    | a file's unflushed writes | seen at once by `stat`, a listing and another open | seen only through the descriptor that made them, until its close or `fsync` | whole-file staging; one provider call per write-back |
    | a file made by an open with `CREAT` | exists from the open | appears at its first write-back (close or `fsync`); two `"x"` opens of one new name in one run both succeed, and the later write-back wins | at most two calls per open, none of them a write |
    | two descriptors writing one path | one shared file | two buffers; the later write-back replaces the earlier | whole-file write-back |
    | a write the provider refuses | fails at the open or the write (`EACCES`, `ENOSPC`) | fails at the close or `fsync`, with the provider's errno, and is recorded | the provider sees a write only at write-back |
    | a write past the staging bound | the host disk's limit | `EFBIG` (22) | host memory is bounded (032 Decision 8) |
    | `rename` or `link` between a mount and anything else | succeeds between two grants on one host disk | `EXDEV` (75); `shutil.move` copies and removes | a provider's files are not the host's |
    | `link` or `symlink` within a mount | works on POSIX hosts | `ENOTSUP` (58) | the protocol has no link (Decision 9) |
    | `utime` and the set-times calls | sets the times | succeeds and changes nothing | the protocol has no times (Decision 9) |
    | `rename` or `rmdir` at or above a nested preopen | allowed on the host | `EBUSY` (10), no call | the guest's view of other preopens stays fixed (Decision 6) |
    | a rename or removal by another run or by the embedder while a descriptor is open | the descriptor follows the file | the write-back goes to the path the descriptor holds | the runner sees only this call's own changes (Decision 7) |

13. **Safety: what a writable mount must never reach.**
    - **The runtime's own files.** The zip's preopen at `/usr/local/lib` is more specific than
      any mount, `/` included. A write-half call or a write-shaped open whose normalized path is
      at or under it is `EPERM` with no provider call (032 Decision 5); a rename or rmdir above
      it is `EBUSY` (Decision 6). So numpy, pandas and the stdlib stay the zip's under a writable
      mount at `/`.
    - **Other grants and mounts.** The same rules hold for every more specific preopen: a
      read-only grant inside a writable mount stays read-only (wasmtime answers it, `EPERM`), and
      a writable mount cannot rename, remove or write over it.
    - **The host.** No host path is opened for a mount, and the placeholder stays read-only
      (Decision 10). Nothing a guest writes reaches a host file through a mount.
    - **State across runs is the embedder's.** A writable mount whose provider keeps its state
      can hold files a later run reads, and modules a later run imports: with a writable mount at
      `/`, a guest run with `-c` has `/` (its working directory) first on `sys.path`. This is
      the cross-run hazard the threat model names for a shared writable root
      (`../research/2026-10-16-a-principal-engineers-direction.md` §2, "Cross-run
      contamination"), now in a store the embedder owns. The README says so, with spec 001's
      rule: one writable namespace per untrusted program, or one the embedder checks.
    - **`HOME`.** The runner makes no `HOME` in a mount, writable or not (032 Decision 2): making
      one would be a write into the embedder's store that the guest did not ask for. A writable
      mount at `/tmp` holds `tempfile`'s files (`TMPDIR` stays `/tmp`); an embedder may pass
      `HOME` in `env`. Spec 017's rule (`HOME` in a writable grant at `/tmp`) is unchanged.
14. **Docs.** README, the *Mounts* section grows a *Writable mounts* part: `writable=True`; the
    write half and each method's contract; the open table and its two calls; write-back at
    close, `fsync` and every ending, and none when the call raises; why a refused write shows at
    close (so `with` blocks and `close()` raise it); `refused` and `RefusedWrite`; the
    deliberate differences (visibility until close, independent buffers, last write-back wins);
    links and times; that bytes still in a Python buffer when the guest stops never reached the
    runner (close files, or use `with`); the staging bound on growth; the cross-run hazard and
    `HOME`. The *Safety* section says a writable mount is the embedder's explicit grant of a
    write channel into its own code. CHANGELOG: an *Added* line.

## Intent

An embedder can let a guest write to a namespace served by its own code: create, write, append,
truncate, make and remove folders, rename within it. Every change reaches the provider as a
whole-file `write` or one namespace call, on a normalized path, counted and limited. What the
guest wrote is handed over at close, at `fsync` and at every ending the runner reports. Every
write the provider refuses, or the runner could not make, is in the result even when the guest
exits 0. Nothing is writable unless the embedder says `writable=True`.

## Design

```
src/wasi_python/mounts.py    the writable flag in the mount table; the open table for writing
                             (Decision 3); the buffer's write calls (fd_write, fd_pwrite,
                             fd_filestat_set_size, fd_sync, fd_datasync) and the growth bound;
                             write-back at close and sync; the namespace calls (mkdir, unlink,
                             rmdir, rename) and their runner-answered cases; descriptor paths
                             that follow renames and removals; links and times; the ending's
                             write-back walk; RefusedWrite and FileRecord.refused;
                             WritableFileProvider
src/wasi_python/runner.py    Mount's writable check among the mount checks; the ending's
                             write-back after _drive stops the guest and before Completed is
                             built, skipped when the call raises; no other change to 032's paths
src/wasi_python/__init__.py  exports RefusedWrite and WritableFileProvider
tests/harness/files.py       032's in-memory provider gains the write half; it counts all eight
                             methods and can refuse, fault or raise per path and per method
tests/checks/test_v1_4_embedding.py   acceptance 1, 2, 4, 5, 6, 9, 11 (all three systems)
tests/unit/test_runner_grants.py      acceptance 3, the raw write rows (all three systems)
tests/checks/test_v1_2_hostile_guest.py   acceptance 7, 10
tests/unit/test_runner_mounts.py      acceptance 8, 12, and the guards' exact parts
README.md, CHANGELOG.md
```

The raw write rows extend 032's table-driven WAT module: the same rows run on a writable grant
and on a writable mount, so a row is data, not a new guest.

### Build order

One builder, in four steps, each green before the next. The write half is about half the size
of 032's mechanism (INFERRED: the memo's model served writes, appends, renames and removals in
part of its 250-line shim; the runner's version adds the checks, the record and parity). It is
not split: a namespace that can create files but not remove or rename them would be its own
half-feature, and vfs needs all of it at once (decision 13).

1. **The writable flag, the open table and the buffer** (Decisions 1, 3, 4), with write-back at
   close and sync (Decision 5) and `RefusedWrite` for those two. The harness provider's write
   half first.
2. **The namespace calls** (Decision 6) and the table's following of renames and removals
   (Decision 7).
3. **The ending's write-back** (Decision 8): every ending, the limit, faults, a raise.
4. **The parity table's write rows, links and times** (Decisions 9 and 12), and the docs.

## Scope

In: writable mounts at any guest path a grant may use and at `/`; the protocol's write half;
writing opens, writes, appends, truncation, `fsync`; folders, removal and rename within a mount;
write-back at close, sync and every ending; the refused-write record; the write rows of the
parity table; links and times as decided; the docs.

Out, each for its own specification if ever wanted:
- **Async providers** (question 15), with the read half's.
- **Ranged reads and writes** (`read(path, offset, size)`, `write(path, offset, data)`), for
  files too large to stage; with them, a log appended over a long run need not be rewritten
  whole at each close.
- **One buffer per path shared by every descriptor in a call,** which would remove the
  visibility and last-write-back-wins differences at the cost of reference-counted buffers.
- **Links and symlinks in a provider,** and **times** set through the protocol.
- **`HOME` in a mount.**
- **Mounts on the command line** (032's Scope: a provider is code).
- **sqlite3 over a mount** is not claimed: it needs ranged writes and locking.
- **Permissions and mode bits:** preview1 has no `chmod`; access is the provider's answer.

## Acceptance criteria

Every check counts calls, bytes, fuel and errno values; none measures time. Each is seen failing
first, and the landing notes show it. The new checks fail on 032's runner, where `writable` is
not a `Mount` field. For acceptance 7, 8, 10 and 12, which exist to catch a missing guard,
"seen failing" means against the built runner with **one guard removed** at a time, as 032
does: no writable check (a read-only mount calls the write half), no growth bound, no
`dst`-inside-`src` rule, no `EXDEV` rule, no `EBUSY` rule, no unlinking of descriptors, no fault
catch at the ending, no limit at the ending, no skip when the call raises. Each named check
fails on its own guard's removal and passes with it. The in-memory provider counts its own
calls. A deadline or a cancel is reached by the epoch ticker's count, as specs 017 and 030's
checks do, never by a sleep.

1. **`test_a_writable_mount_serves_writes`** (v1.4, both binaries). At `/work`, writable:
   `open("/work/a.txt", "w")`, a write and a close make exactly one `stat` and one `write`, whose
   `data` is the bytes written; `open("/work/d/b.txt", "w")` with `d` present makes two `stat`s
   (target and parent) and one `write`; `"a"` on an existing file makes one `read` and one
   `write` holding the old bytes then the new; `"r+"` with no write makes one `read` and no
   `write`; a write, an `os.fsync` and a close make exactly one `write`; `open(p, "w").close()`
   writes `b""`; `os.mkdir`, `os.remove`, `os.rmdir` and `os.rename` within the mount make
   exactly one call each; pandas' `to_csv` then `read_csv` of the same path round-trips;
   `done.files.calls` equals the provider's own counts, all eight keys; `done.files.refused` is
   empty.
2. **`test_a_writable_mount_answers_as_a_writable_grant_does`** (v1.4, both binaries, all three
   systems). The same tree as an in-memory writable `Mount` and as a writable `Grant` on disk;
   each row gives the same result or errno and leaves the same tree: create; `"x"` on an
   existing file; create under a missing parent and under a file; open a folder for writing;
   append; truncate by `"w"` and by `os.truncate`; `pwrite` past the end (zeros in the gap); a
   seek past the end then a write; a write on a read-only descriptor; `pwrite` on an append
   descriptor; `mkdir` of an existing path and under a missing parent; `rmdir` of a non-empty
   folder and of a file; `remove` of a folder and of a missing file; `rename` file to new, file
   over file, folder over an empty folder, folder over a non-empty folder, file over folder,
   folder over file, folder into its own subfolder, a path onto itself; `shutil.copyfile`,
   `shutil.copy2`, `shutil.rmtree`, `os.replace` for an atomic save; `os.fstat` size after a
   write; a sorted listing after each change, once the writer has closed. Decision 12's
   deliberate differences are asserted as its table says, not as parity.
3. **`test_raw_write_calls_answer_as_a_writable_grant_does`** (unit, in `test_runner_grants.py`,
   all three systems). Through 032's table-driven WAT module, each shadowed call that can write
   (`path_open` with each `oflags`, `fdflags` and rights shape, sync flags and `O_DIRECTORY`
   with `CREAT` included; `fd_write` and `fd_pwrite` with one and two `ciovec`s;
   `fd_filestat_set_size`; `fd_sync`; `fd_datasync`; `fd_fdstat_set_flags` with `APPEND`;
   `fd_allocate`; `path_create_directory`, `path_unlink_file`, `path_remove_directory`,
   `path_rename`; the set-times calls) on a provider file, folder and preopen, and on a
   writable grant's, with the same arguments. The whole results are equal (errno and every byte
   written, with `dev`, `ino`, times and numbers masked), except Decision 12's differences; a
   row that differs by system is asserted per system. The table is in the landing notes.
4. **`test_refused_writes_are_recorded_on_exit_0`** (v1.4, both binaries). A provider that
   answers `Errno.EACCES` to `write("/denied.txt")`: the guest's `with open(...)` block raises
   `PermissionError` (errno 2) at its close; the guest catches it and exits 0; `exit_code == 0`,
   and `done.files.refused` is exactly one
   `RefusedWrite("/work", "write", ("/denied.txt",), Errno.EACCES, "close", "refused")`. The
   same for a refused `fsync` (`at == "sync"`, then a second entry at the close), and for a
   refused `mkdir` and `rename` (`at == "call"`). A refused `stat` at a writing open records
   nothing.
5. **`test_writes_land_at_every_ending`** (v1.4, both binaries). A guest opens a file in a
   writable mount, writes with `os.write` and does not close it, then: exits 0; calls
   `os._exit(3)`; raises an uncaught exception; spins until its fuel cap; spins until its
   deadline; spins until `cancel=` is set; stats in a loop until `max_file_calls`. In the first
   six, the provider holds the bytes after `run` returns, from exactly one `write` made after
   the guest stopped (the file was opened with `os.open`, so no Python object closes it);
   `refused` is empty; and `trapped` and `exit_code` are the ending's as without mounts. In the last, no `write` is made, and `refused` names the file with
   `cause == "limit"`. A file closed by the guest after `cancel` was set (its close answered by
   030's guard) is written back once, at the ending.
6. **`test_a_failed_write_back_at_the_ending_is_recorded`** (v1.4). Three dirty files at the
   ending; the provider answers `Errno.EIO` for the first, raises `ValueError` for the second
   and accepts the third: `run` raises nothing; `refused` holds the first (`"refused"`) and the
   second (`"fault"`, `Errno.EIO`, `at == "exit"`); `faults` names the `ValueError`; the third is
   written; the walk made exactly three `write`s, in ascending provider number.
7. **`test_a_call_that_raises_writes_nothing_back`** (v1.2 hostile). A dirty file left open,
   then a door host that raises `KeyboardInterrupt`: `run` raises it and the provider's `write`
   count is 0. Two dirty files, and a provider whose first ending `write` raises
   `KeyboardInterrupt`: `run` raises it and the second file's `write` count is 0. A pending
   Ctrl-C on the main thread (the host sends itself SIGINT, as 030's check does): `run` raises
   `KeyboardInterrupt` and the provider's `write` count is 0. Guard: the skip when the call
   raises.
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
   provider sees one `remove` and no `write` for its name (guard: unlinking). A file opened,
   renamed, written and closed is written back to its new name and never to its old one. A file
   held open while another path is renamed over it is never written back. A folder descriptor
   renamed while open resolves a later relative open under its new name. An open folder removed
   with `rmdir` answers `ENOENT` to a later relative open, with no provider call.
10. **`test_a_writable_root_mount_keeps_the_runtime_and_other_grants`** (v1.2 hostile, both
    binaries). A writable mount at `/` with a read-only grant at `/data` and a writable mount at
    `/work/out` inside it: writing, making a folder in, removing or renaming into
    `/usr/local/lib/x`, `/usr/./local/lib/x` and `/data/x` is `EPERM` with no provider call;
    renaming or removing `/usr`, `/usr/local` or `/work` is `EBUSY` with no call (guard: the
    `EBUSY` rule); renaming `/a.txt` to `/work/out/a.txt` is `EXDEV` with no call (guard: the
    `EXDEV` rule); renaming `/d` to `/d/e` is `EINVAL` with no call (guard: the `dst`-inside-`src`
    rule); numpy and pandas import; the placeholder is empty during the run and gone after it.
11. **`test_links_and_times_in_a_writable_mount`** (v1.4). `os.link` and `os.symlink` within the
    mount are `ENOTSUP`, and `os.link` to a grant is `EXDEV`, all with no provider call;
    `os.utime` succeeds with no call, and `os.stat` then shows the provider's `mtime_ns`;
    `shutil.copy2` within the mount succeeds.
12. **`test_writes_are_bounded`** (unit). With a staging bound the test sets through
    `memory_bytes`: a `fd_pwrite` of one byte at offset `2**40`, a seek to the bound then a
    write, a `fd_filestat_set_size` past the bound, and two files whose sum passes it each
    answer `EFBIG` and leave the buffer's size unchanged, with the runner's held-bytes count
    (a counting seam on the mount table) never above the bound (guard: the growth bound). With
    `max_file_calls` set so that the ending's write-backs pass it, the provider's total call
    count equals the limit exactly and every unmade write-back is a `RefusedWrite` with
    `cause == "limit"` (guard: the limit at the ending). An ending `write` that raises
    `ValueError` does not stop the walk (guard: the fault catch at the ending).
13. **032's checks pass unchanged,** acceptance 10 and 12 among them: a call without mounts uses
    today's linker and invokes no shadow; forwards cost no fuel. The ratchet shows no fuel growth
    on any accepted check.
14. `uv run pytest` green with `--accept-judge`; lost 0; grew 0. `ruff check` and `ruff format
    --check` clean. A release dry run passes every job, Windows included.
15. **The build review is also a security review** of the write channel against the threat
    model (`../research/2026-10-16-a-principal-engineers-direction.md` §2: the host, the
    embedder's other runs, the runtime's own files, the integrity of the result, the embedder's
    resources), recorded under `../reviews/`. It re-runs acceptance 7, 8, 10 and 12 with each
    guard removed.

## The owner's choices

None open here. Two of these decisions are the agent's choice where the owner's decisions were
silent; they are recorded as questions 71 and 72 in `../questions-for-the-owner.md`, and
nothing waits on them: Decision 8's write-back after a cancel or a deadline, and Decision 12's
one buffer per descriptor.

## Landing notes

Not built.
