# 016 — The security review's leftovers

- **Status:** draft, revised twice on 2026-10-17 against its pre-build review and its confirmation
  (`context/reviews/016-the-security-reviews-leftovers-spec-2026-10-17.md`).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), the release workflow
  (`.github/workflows/release.yml`), judge additions in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 006 (private roots), 009 (release security), 012 (the same-bytes gate).
- **Research it stands on:** the 0.1.0a2 security review
  (`context/reviews/0.1.0a2-security-review-2026-10-17.md`), findings F5, F6, F7 and F10, each
  dispositioned there as "accepted for a later change" or "noted". This specification is that
  change. F8 waits for the wheel's next change, as its disposition says.

## The problem

Four things the security review found, none of which blocked 0.1.0a2:

- **F5.** Nothing outside the build job compares the wheel's copy of the artifact set with the
  set's `SHA256SUMS`. A wheel built from other bytes would pass `same-bytes`, which compares only
  the rebuilds' `SHA256SUMS` with the set's.
- **F6.** A process killed mid-call leaves its private root (`wasi-python-root-*`, about 11 MB:
  the zip, and whatever the guest wrote) and its stdin folder (`wasi-python-*`, holding the
  caller's `stdin`) in the temporary folder for good. The review found 37 roots and 28 stdin
  folders on this machine (EXECUTED there).
- **F7.** A stack overflow ends with `trapped == "error while executing at wasm backtrace:"`, the
  heading wasmtime puts before every trap's backtrace. The embedder sees that the guest trapped,
  but not why. EXECUTED (2026-10-17): the trap is a `wasmtime.Trap` whose `trap_code` is
  `TrapCode.STACK_OVERFLOW`; `_trap_name` reads only the fuel and interrupt codes and otherwise
  takes the message's first line.
- **F10.** On Windows, `_private` cannot check who may write a folder, and answers yes. The
  compiled-module cache (`.cwasm`, native code) is then trusted wherever the embedder points
  `cache_dir` or `WASI_PYTHON_CACHE`. The README does not say so.

## Decisions

1. **The wheel is the attested bytes (F5).**
   - The `rebuild` job also builds the wheel, exactly as the `build` job does (copy
     `build/artifacts` into `src/wasi_python/artifacts`, `uv build --wheel` with the same
     constraints, `SOURCE_DATE_EPOCH` as the build sets it), and uploads it beside its
     `SHA256SUMS`.
   - `same-bytes` then requires the release's wheel to equal the rebuilt wheel, byte for byte
     (`cmp`). That covers the artifacts, `runner.py`, `__init__.py` and `METADATA` together: a
     wheel built from any other source or set fails (the pre-build review's finding 2).
   - Before that `cmp`, three rules name what differs when it fails: every file the set's
     `SHA256SUMS` lists is in the wheel's `wasi_python/artifacts/` with its hash
     (`sha256sum --strict -c`); the wheel's `SHA256SUMS` equals the set's; and the wheel's
     `wasi_python/artifacts/` holds exactly those files plus `SHA256SUMS`.
   - `attest` and `publish` already need `same-bytes`.
   - Each rule, and the whole-wheel `cmp`, is shown failing once, in a local run of the same
     commands on a copy of the wheel: one byte of `MANIFEST` changed; `SHA256SUMS` changed; an
     extra file added; `runner.py` changed. The landing notes record each.
2. **A dead process's folders are swept, by lock and kernel, not by pid (F6).**
   - **Why a lock.** A pid does not say whether a call is alive: pids repeat across pid
     namespaces (two containers sharing a temp folder, EXECUTED by the pre-build review: one
     judged the other's live folder dead), are reused, and a killed child is a zombie until
     reaped. A kernel lock is released when its holder dies, in any pid namespace on that kernel
     (EXECUTED by the confirmation: across two containers on one kernel the sweeper got
     `EWOULDBLOCK` while the holder lived, and the lock once the holder was killed).
   - **Why the kernel's identity too.** A lock taken on one kernel is invisible to another that
     shares the folder: a macOS process and a container in Docker Desktop's VM both took the same
     lock (EXECUTED by the confirmation), and NFS without locking behaves alike. So each lock file
     records the identity of the kernel that made it, and a sweep touches only lock files of its
     own kernel. The identity is: Linux, `/proc/sys/kernel/random/boot_id`; macOS,
     `sysctlbyname("kern.bootsessionuuid")` through `ctypes` (EXECUTED: it answers a UUID);
     Windows, the `MachineGuid` value under `HKLM\SOFTWARE\Microsoft\Cryptography` (`winreg`).
     Where the identity cannot be read, the process neither sweeps nor writes one, and its lock
     files are never swept by anyone: a leak, never a removal.
   - **Making a folder.** For each private root and each stdin folder the runner picks the name:
     the prefix (`wasi-python-root-` or `wasi-python-`) and 16 hex characters from
     `secrets.token_hex(8)`. In order:
     1. create `<name>.lock` in the temporary folder with `O_CREAT | O_EXCL | O_NOFOLLOW |
        O_CLOEXEC` where the platform has them, mode `0600`;
     2. lock it without waiting: POSIX `fcntl.flock(fd, LOCK_EX | LOCK_NB)`; Windows
        `os.lseek(fd, 0, 0)` then `msvcrt.locking(fd, LK_NBLCK, 1)`;
     3. check that the open file is still the file at that path (`os.fstat(fd)` and
        `os.lstat(path)` agree on device and inode);
     4. write the kernel identity into it, one line, and flush;
     5. make the folder `<name>` with `os.mkdir(path, 0o700)`;
     6. add `<name>` to the process's set of held names.

     A failure at steps 1 to 3 or 5 (`FileExistsError`, a lock that is busy, a path that is no
     longer this file) closes what this call opened, removes only a lock file this call created
     and still holds, and draws a new name, up to 100 times, as `mkdtemp` does; then it raises,
     as `mkdtemp` would.
   - **Removing a folder at the end of the call:** remove the folder; drop `<name>` from the held
     set; close the lock file (which releases the lock); then unlink it, ignoring
     `FileNotFoundError`. Closing before unlinking is what Windows requires: it cannot delete a
     file that is open (READ, CPython's `tempfile` does the same).
   - **The sweep.** Once per process, at its first call, the runner claims the sweep under
     `_lock` (a flag), then sweeps without holding `_lock`, before the call's own folders are
     made. For each entry in `tempfile.gettempdir()` whose name matches
     `wasi-python-(root-)?[0-9a-f]{16}\.lock` and is not in this process's held set (NFS clients
     may treat `flock` as owned by the whole process, so the process never sweeps its own):
     1. `lstat` it: a regular file this user owns (POSIX `st_uid == os.getuid()`; Windows, the
        user's own temporary folder) and not a link; otherwise skip;
     2. open it with `O_RDWR | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC`, `fstat` the open file, and
        skip it unless it is a regular file with the device and inode `lstat` gave;
     3. try the lock without waiting (Windows: seek to 0 first); if it is held, skip;
     4. read the first line; skip unless it equals this kernel's identity;
     5. remove the folder `<name>` if it is a directory and not a link
        (`shutil.rmtree(ignore_errors=True)`), counting it in `_swept`; then close and unlink the
        lock file.

     Every step that fails, for any reason (`ENOLCK` on a network filesystem included), leaves
     the entry alone. The whole sweep sits in `try/except Exception`, each entry in its own;
     `KeyboardInterrupt` is not caught. `_swept` counts folders removed, not lone lock files.
   - **What is never swept:** a folder without a lock file (folders from releases before this
     one, and one in the instant before its lock file exists); a lock file of another kernel, or
     with no identity; a link; anything another user owns; anything locked by another process;
     anything this process holds.
   - **`root=` and the temporary folder.** The lock files are outside a private root. If an
     embedder passes the temporary folder itself, or a folder above it, as `root=`, its guest can
     reach the lock files, and other calls' private folders too; it gains nothing it could not do
     already (it could delete those folders). The README warns against such a root.
   - **Cost.** One `listdir` of the temporary folder and one open and lock per matching file,
     once per process. The pre-build review listed 200,000 entries in 0.32 s (EXECUTED there, a
     benchmark fact).
   - `stats()` is unchanged. The runner keeps a module counter, `_swept`, that the checks read.
   - The README's "Not protected" list gains one entry: a process killed mid-call leaves its
     private root, its stdin folder and their lock files until another process using wasi_python
     on the same kernel, with the same temporary folder, starts its first call; folders left by a
     release before 0.1.0a3 have no lock file and are never swept, so a user may delete
     `wasi-python-*` entries by hand when no wasi_python process runs.
3. **Every trap with a code is named by it (F7).** `_trap_name` returns `"out of fuel"` and
   `"deadline"` as before. Any other trap that carries a `trap_code` is named by the rule
   `trap_code.name.lower().replace("_", " ")`: `"stack overflow"`, `"unreachable"`,
   `"memory out of bounds"`, `"integer division by zero"`, `"integer overflow"`,
   `"bad conversion to integer"` (each EXECUTED by the pre-build review, all of which read
   `"error while executing at wasm backtrace:"` today). A trap without a code, and a
   `WasmtimeError` that is not a trap, keep their message's first line. This changes what
   `trapped` says for those traps, so the CHANGELOG says so plainly ("`trapped` now names a
   trap by its kind, such as `"stack overflow"`, instead of wasmtime's heading `"error while
   executing at wasm backtrace:"`").
4. **The README names the Windows cache (F10).** One sentence in the cache paragraph: on Windows
   the runner cannot check who may write the cache folder, so `cache_dir` and
   `WASI_PYTHON_CACHE` must name a folder only you can write; the default, in your own profile,
   is one.
5. **Checks.** Each counts; none measures time. Each new check is seen failing first, against a
   stand-in that has the API but lacks the property where one applies.
   - The sweep's checks live in `tests/checks/test_v1_4_embedding.py` and a new
     `tests/unit/test_runner_sweep.py`, and the `verify` job's file list gains
     `tests/unit/test_runner_sweep.py`, so Linux, macOS and Windows each run them (finding 6).
   - v1.4, `test_a_killed_process_leaves_nothing_after_the_next_call`: child 1, with
     `tempfile.tempdir` set to an empty directory, starts a call whose door host prints a line
     and then blocks; the parent reads that line, kills child 1 (`Popen.kill`) and waits for it
     (`Popen.wait`). The directory then holds child 1's root, stdin folder and two lock files.
     Before child 2 starts, the parent confirms each lock file can be locked (Windows releases a
     dead process's lock after a documented delay): up to 1,200 tries, each a non-blocking lock
     attempt followed by `time.sleep(0.1)`, a fail-safe that counts tries, not a timing.
     Child 2, with the same `tempfile.tempdir`, makes one call and prints `runner._swept`: 2,
     and the directory then holds nothing. A stand-in sweep that takes no lock is not needed:
     the stand-in is "no sweep", which leaves the folders. A 120 s fail-safe guards each child.
   - The stand-in for the kernel rule: a sweep that ignores the first line removes a folder
     whose lock file names another kernel (the unit case above fails).
   - v1.4, `test_a_live_calls_folders_are_never_swept`: child 1 starts a call that blocks in its
     door; while it blocks, child 2 makes a call and prints `runner._swept`: 0, and child 1's
     folders and lock files are all still there; then child 1 is released and ends normally,
     leaving nothing. The stand-in "sweep every lock file without trying the lock" fails it.
   - Unit (`test_runner_sweep.py`), in an empty temporary folder, one sweep each:
     - a folder with an unlocked lock file is removed with its lock file; `_swept == 1`;
     - a folder whose lock file this test holds locked (a second open file description) stays;
     - a folder with no lock file stays; a lock file with no folder is removed alone;
     - a link named like a lock file, and a link named like a root beside an unlocked lock file,
       stay, and the folder each points at, holding a canary file, keeps its canary (on
       Windows, where making a link needs privileges, those two cases are skipped);
     - a dead folder that holds a link to a canary folder outside is removed and the canary
       survives (POSIX);
     - an owner other than this user is refused, through a fake `lstat`;
     - a sweep whose `listdir` raises returns quietly, and the call goes on;
     - a lock file of another kernel (a different first line), and one with no first line,
       beside an unlocked folder, stay with their folders;
     - a name this process holds is skipped, even when its lock could be taken (a fake held set);
     - a lock file replaced by a FIFO between `lstat` and `open` is skipped and the sweep does
       not hang (POSIX; `O_NONBLOCK`);
     - making a folder whose lock file a sweeper holds at that instant draws a new name instead
       of raising (a fake `flock` that fails once), and the call succeeds;
     - at the end of a call, the folder is gone before its lock file is unlinked, and on every
       platform both are gone afterwards.
   - v1.2, `test_a_stack_overflow_is_named`: unbounded recursion under
     `sys.setrecursionlimit(10**8)` ends with `trapped == "stack overflow"`.
   - Unit: `_trap_name` with fake traps: a fuel code, an interrupt code, a stack-overflow code,
     no code (the first line); and every member of `wasmtime.TrapCode` maps by the rule to
     lower-case words with no underscore, so a wasmtime release that renames a code fails here
     first (finding 9).
   - The existing checks that compare `stats()` with an exact dict are unchanged, since
     `stats()` is.
   - `test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise` (v1.2) skips on Windows
     with a reason that names no need, which the judge counts as a failure wherever that file
     runs on Windows (the 015 build review's follow-up). It gains a branch instead: where there is
     no `RLIMIT_NOFILE`, it checks that a call runs and leaves nothing behind.
6. **Docs.** README: the `trapped` sentence, the cache sentence, the new "Not protected" entry.
   CHANGELOG, under 0.1.0a3: the sweep, the trap names (as a change to what `trapped` says), and
   the wheel check.

## Intent

The wheel is proven to be the bytes a second host rebuilt; a killed process no longer leaves a
guest's files and the caller's `stdin` behind for good, and no live call's folder is ever
removed; and a trap says what it was.

## Design

```
.github/workflows/release.yml   rebuild: the wheel too; same-bytes: the wheel, byte for byte;
                                verify: runs tests/unit/test_runner_sweep.py
src/wasi_python/runner.py       lock files beside private folders; the sweep; _trap_name
tests/checks/test_v1_4_embedding.py   the killed process; a live call's folders kept
tests/checks/test_v1_2_hostile_guest.py   stack overflow
tests/unit/test_runner_sweep.py what the sweep keeps and removes (run by verify on every OS)
tests/unit/…                    _trap_name and every TrapCode
README.md, CHANGELOG.md
```

## Scope

In: the above. Out:
- F8 (an installed package preferring a nearby `build/artifacts/`): with the wheel's next change.
- A sweep of a reused `root=`: the embedder owns it.
- Folders left by releases before this one: they have no lock file, so they are left alone;
  the README's entry tells a user they may delete them by hand.
- A temporary folder shared between kernels (a VM and its host, two hosts over a network
  filesystem): each kernel sweeps only its own lock files, and a lock that fails (`ENOLCK`) means
  "leave it", so such folders are only ever leaked, never removed by another kernel. Two kernels
  that report the same identity (a cloned Windows image keeps its `MachineGuid`) and share one
  temporary folder are outside this specification; the README names it.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. A dry run of the release workflow passes every job, including the new wheel check.

## Landing notes

Not built.
