# 016 — The security review's leftovers

- **Status:** built and reviewed 2026-10-17 (`../reviews/016-the-security-reviews-leftovers-2026-10-17.md`, with its confirmation); revised twice before the build against its pre-build review, which its second confirmation passed for build (`context/reviews/016-the-security-reviews-leftovers-spec-2026-10-17.md`).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), the release workflow (`.github/workflows/release.yml`), judge additions in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 006 (private roots), 009 (release security), 012 (the same-bytes gate).
- **Research it stands on:** the 0.1.0a2 security review (`context/reviews/0.1.0a2-security-review-2026-10-17.md`), findings F5, F6, F7 and F10, each dispositioned there as "accepted for a later change" or "noted". This specification is that change. F8 waits for the wheel's next change, as its disposition says.

## The problem

Four things the security review found, none of which blocked 0.1.0a2:

- **F5.** Nothing outside the build job compares the wheel's copy of the artifact set with the set's `SHA256SUMS`. A wheel built from other bytes would pass `same-bytes`, which compares only the rebuilds' `SHA256SUMS` with the set's.
- **F6.** A process killed mid-call leaves its private root (`wasi-python-root-*`, about 11 MB: the zip, and whatever the guest wrote) and its stdin folder (`wasi-python-*`, holding the caller's `stdin`) in the temporary folder for good. The review found 37 roots and 28 stdin folders on this machine (EXECUTED there).
- **F7.** A stack overflow ends with `trapped == "error while executing at wasm backtrace:"`, the heading wasmtime puts before every trap's backtrace. The embedder sees that the guest trapped, but not why. EXECUTED (2026-10-17): the trap is a `wasmtime.Trap` whose `trap_code` is `TrapCode.STACK_OVERFLOW`; `_trap_name` reads only the fuel and interrupt codes and otherwise takes the message's first line.
- **F10.** On Windows, `_private` cannot check who may write a folder, and answers yes. The compiled-module cache (`.cwasm`, native code) is then trusted wherever the embedder points `cache_dir` or `WASI_PYTHON_CACHE`. The README does not say so.

## Decisions

1. **The wheel is the attested bytes (F5).**
   - The `rebuild` job also builds the wheel, exactly as the `build` job does (copy `build/artifacts` into `src/wasi_python/artifacts`, `uv build --wheel` with the same constraints, `SOURCE_DATE_EPOCH` as the build sets it), and uploads it beside its `SHA256SUMS`.
   - `same-bytes` then requires the release's wheel to equal the rebuilt wheel, byte for byte (`cmp`). That covers the artifacts, `runner.py`, `__init__.py` and `METADATA` together: a wheel built from any other source or set fails (the pre-build review's finding 2).
   - Before that `cmp`, three rules name what differs when it fails: every file the set's `SHA256SUMS` lists is in the wheel's `wasi_python/artifacts/` with its hash (`sha256sum --strict -c`); the wheel's `SHA256SUMS` equals the set's; and the wheel's `wasi_python/artifacts/` holds exactly those files plus `SHA256SUMS`.
   - `attest` and `publish` already need `same-bytes`.
   - Each rule, and the whole-wheel `cmp`, is shown failing once, in a local run of the same commands on a copy of the wheel: one byte of `MANIFEST` changed; `SHA256SUMS` changed; an extra file added; `runner.py` changed. The landing notes record each.
2. **A dead process's folders are swept, by lock and kernel, not by pid (F6).**
   - **Why a lock.** A pid does not say whether a call is alive: pids repeat across pid namespaces (two containers sharing a temp folder, EXECUTED by the pre-build review: one judged the other's live folder dead), are reused, and a killed child is a zombie until reaped. A kernel lock is released when its holder dies, in any pid namespace on that kernel (EXECUTED by the confirmation: across two containers on one kernel the sweeper got `EWOULDBLOCK` while the holder lived, and the lock once the holder was killed).
   - **Why the kernel's identity too.** A lock taken on one kernel is invisible to another that shares the folder: a macOS process and a container in Docker Desktop's VM both took the same lock (EXECUTED by the confirmation), and NFS without locking behaves alike. So each lock file records the identity of the kernel that made it, and a sweep touches only lock files of its own kernel. The identity is: Linux, `/proc/sys/kernel/random/boot_id`; macOS, `sysctlbyname("kern.bootsessionuuid")` through `ctypes` (EXECUTED: it answers a UUID); Windows, the `MachineGuid` value under `HKLM\SOFTWARE\Microsoft\Cryptography` (`winreg`, opened with `KEY_READ | KEY_WOW64_64KEY`, so a 32-bit Python reads the 64-bit view). Where the identity cannot be read, the process neither sweeps nor writes one, and its lock files are never swept by anyone: a leak, never a removal.
   - **Making a folder.** For each private root and each stdin folder the runner picks the name: the prefix (`wasi-python-root-` or `wasi-python-`) and 16 hex characters from `secrets.token_hex(8)`. In order:
     0. add `<name>` to the process's set of held names, before anything exists on disk;
     1. create `<name>.lock` in the temporary folder with `O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC` where the platform has them, mode `0600`;
     2. lock it without waiting: POSIX `fcntl.flock(fd, LOCK_EX | LOCK_NB)`; Windows `os.lseek(fd, 0, 0)` then `msvcrt.locking(fd, LK_NBLCK, 1)`. Only contention means busy: `BlockingIOError` on POSIX, `EACCES` or `EDEADLOCK` on Windows. Any other error means this filesystem gives no lock (below);
     3. check that the open file is still the file at that path (`os.fstat(fd)` and `os.lstat(path)` agree on device and inode); a path that no longer exists fails the check, since a sweeper may have removed the new, still-empty file (the build review, finding 1);
     4. if the lock was taken, write the kernel identity into it at offset 0 (`os.lseek(fd, 0, 0)`, then `os.write`), one line;
     5. make the folder `<name>` with `os.mkdir(path, 0o700)`.

     A failure at steps 1 to 3 or 5 (`FileExistsError`, a lock that is busy, a path that is no longer this file) closes what this call opened, removes the lock file only if step 3 found it still this call's file, drops `<name>` from the held set, and draws a new name, up to 100 times, as `mkdtemp` does; then it raises, as `mkdtemp` would.
   - **A filesystem without locks** (the build review, finding 2). Where the lock fails for any reason but contention (`ENOLCK` on NFS without a lock daemon, `ENOTSUP` on some network filesystems), the call goes on without a lock and writes no identity. A lock file with an empty first line beside a folder is never swept, even by a sweep whose lock works (a lock daemon that comes back), so such a call's folders are only ever leaked by a kill, never removed: the behaviour before this specification. A sweep whose own lock attempt errors leaves the entry, whatever its first line. Raising instead would make every call fail on such a temporary folder, where `mkdtemp` worked; drawing again, as the first build did, made every call fail and left 100 lock files.
   - **Removing a folder at the end of the call:** remove the folder; unlock the lock file (Windows only, where a closed handle's lock is freed after a delay) and close it; unlink it only if the folder no longer exists, ignoring `FileNotFoundError`; and drop `<name>` from the held set last. A folder that `rmtree` could not fully remove keeps its lock file, so a later sweep can try again. Closing before unlinking is what Windows requires: it cannot delete a file that is open (READ, CPython's `tempfile` does the same).
   - **The sweep.** Once per process, at its first call, the runner claims the sweep under `_lock` (a flag), then sweeps without holding `_lock`, before the call's own folders are made. For each entry in `tempfile.gettempdir()` whose name matches `wasi-python-(root-)?[0-9a-f]{16}\.lock` and is not in this process's held set (NFS clients may treat `flock` as owned by the whole process, so the process never sweeps its own):
     1. `lstat` it: a regular file this user owns (POSIX `st_uid == os.getuid()`; Windows, the user's own temporary folder) and not a link; otherwise skip;
     2. open it with `O_RDWR | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC`, `fstat` the open file, and skip it unless it is a regular file with the device and inode `lstat` gave;
     3. try the lock without waiting (Windows: seek to 0 first); if it is held, skip;
     4. read the first line from offset 0 (`os.lseek(fd, 0, 0)`, then `os.read`); skip unless it equals this kernel's identity;
     5. remove the folder `<name>` if it is a directory and not a link (`shutil.rmtree(ignore_errors=True)`), counting it in `_swept` if it is then gone; and unlink the lock file only if no folder `<name>` remains. On POSIX the unlink comes before the close, while the lock is still held, so a creator that locks the file afterwards fails step 3 and draws again; Windows cannot delete an open file, so there it closes first and leaves that narrow window (a leak if the creator is then killed, never a removal; the build review, finding 6).

     A lock file with no folder beside it whose lock is free is removed if its first line is this kernel's identity or it is empty (a creator killed before step 4): there is nothing of a call's to lose.

     Every step that fails, for any reason (`ENOLCK` on a network filesystem included), leaves the entry alone. The whole sweep sits in `try/except Exception`, each entry in its own; `KeyboardInterrupt` is not caught. `_swept` counts folders removed, not lone lock files.
   - **What is never swept:** a folder without a lock file (folders from releases before this one, and one in the instant before its lock file exists); a lock file of another kernel, or with no identity; a link; anything another user owns; anything locked by another process; anything this process holds.
   - **`root=` and the temporary folder.** The lock files are outside a private root. If an embedder passes the temporary folder itself, or a folder above it, as `root=`, its guest can reach the lock files, and other calls' private folders too; it gains nothing it could not do already (it could delete those folders). The README warns against such a root.
   - **Cost.** One `listdir` of the temporary folder and one open and lock per matching file, once per process. The pre-build review listed 200,000 entries in 0.32 s (EXECUTED there, a benchmark fact).
   - `stats()` is unchanged. The runner keeps a module counter, `_swept`, that the checks read.
   - The README's "Not protected" list gains one entry: a process killed mid-call leaves its private root, its stdin folder and their lock files until another process using wasi_python on the same kernel, with the same temporary folder, starts its first call; folders left by a release before 0.1.0a3 have no lock file and are never swept, so a user may delete `wasi-python-*` entries by hand when no wasi_python process runs.
3. **Every trap with a code is named by it (F7).** `_trap_name` returns `"out of fuel"` and `"deadline"` as before. Any other trap that carries a `trap_code` is named by the rule `trap_code.name.lower().replace("_", " ")`: `"stack overflow"`, `"unreachable"`, `"memory out of bounds"`, `"integer division by zero"`, `"integer overflow"`, `"bad conversion to integer"` (each EXECUTED by the pre-build review, all of which read `"error while executing at wasm backtrace:"` today). A trap without a code, and a `WasmtimeError` that is not a trap, keep their message's first line. This changes what `trapped` says for those traps, so the CHANGELOG says so plainly ("`trapped` now names a trap by its kind, such as `"stack overflow"`, instead of wasmtime's heading `"error while executing at wasm backtrace:"`").
4. **The README names the Windows cache (F10).** One sentence in the cache paragraph: on Windows the runner cannot check who may write the cache folder, so `cache_dir` and `WASI_PYTHON_CACHE` must name a folder only you can write; the default, in your own profile, is one.
5. **Checks.** Each counts; none measures time. Each new check is seen failing first, against a stand-in that has the API but lacks the property where one applies.
   - The sweep's checks live in `tests/checks/test_v1_4_embedding.py` and a new `tests/unit/test_runner_sweep.py`, and the `verify` job's file list gains `tests/unit/test_runner_sweep.py`, so Linux, macOS and Windows each run them (finding 6).
   - v1.4, `test_a_killed_process_leaves_nothing_after_the_next_call`: child 1, with `tempfile.tempdir` set to an empty directory, starts a call whose door host prints a line and then blocks; the parent reads that line, kills child 1 (`Popen.kill`) and waits for it (`Popen.wait`). The directory then holds child 1's root, stdin folder and two lock files. Before child 2 starts, the parent confirms each lock file can be locked (Windows releases a dead process's lock after a documented delay): up to 1,200 tries, each a non-blocking lock attempt followed by `time.sleep(0.1)`, a fail-safe that counts tries, not a timing. Child 2, with the same `tempfile.tempdir`, makes one call and prints `runner._swept`: 2, and the directory then holds nothing. A stand-in sweep that takes no lock is not needed: the stand-in is "no sweep", which leaves the folders. A 120 s fail-safe guards each child.
   - The stand-in for the kernel rule: a sweep that ignores the first line removes a folder whose lock file names another kernel (the unit case above fails).
   - v1.4, `test_a_live_calls_folders_are_never_swept`: child 1 starts a call that blocks in its door; while it blocks, child 2 makes a call and prints `runner._swept`: 0, and child 1's folders and lock files are all still there; then child 1 is released and ends normally, leaving nothing. The stand-in "sweep every lock file without trying the lock" fails it.
   - Unit (`test_runner_sweep.py`), in an empty temporary folder, one sweep each:
     - a folder with an unlocked lock file is removed with its lock file; `_swept == 1`;
     - a folder whose lock file this test holds locked (a second open file description) stays;
     - a folder with no lock file stays; a lock file with no folder is removed alone;
     - a link named like a lock file, and a link named like a root beside an unlocked lock file, stay, and the folder each points at, holding a canary file, keeps its canary (on Windows, where making a link needs privileges, those two cases are skipped);
     - a dead folder that holds a link to a canary folder outside is removed and the canary survives (POSIX);
     - an owner other than this user is refused, through a fake `lstat` (POSIX), and `_owned` answers for two `stat_result`s;
     - a sweep whose `listdir` raises returns quietly, and the call goes on to make its folder;
     - a lock file of another kernel (a different first line), and one with no first line, beside an unlocked folder, stay with their folders;
     - a name this process holds is skipped, even when its lock could be taken (a fake held set);
     - a lock file replaced by a FIFO between `lstat` and `open` is skipped (POSIX). `O_RDWR` on a FIFO does not block, so the check cannot see `O_NONBLOCK`, which guards a file under a lease; the regular-file and inode checks are what skip the FIFO;
     - a drawn name whose lock file exists is left untouched and another is drawn (`O_EXCL`);
     - a lock file a sweeper removes before its creator locks it: the creator draws again;
     - a filesystem without locks (a fake `flock` raising `ENOLCK`): the folder is made, its lock file stays empty, a sweep leaves it, and the end of the call leaves nothing; `_try_lock` answers busy only for contention;
     - a folder `rmtree` could not fully remove keeps its lock file, and a later sweep removes both;
     - the sweep unlinks a lock file before it lets the lock go (POSIX);
     - a lock file naming this kernel whose lock attempt errors (`ENOLCK`) stays with its folder;
     - making a folder whose lock file a sweeper holds at that instant draws a new name instead of raising (a fake `flock` that fails once), and the call succeeds;
     - at the end of a call, the folder is gone before its lock file is unlinked, and on every platform both are gone afterwards.
   - v1.2, `test_a_stack_overflow_is_named`: unbounded recursion under `sys.setrecursionlimit(10**8)` ends with `trapped == "stack overflow"`.
   - Unit: `_trap_name` with fake traps: a fuel code, an interrupt code, a stack-overflow code, no code (the first line); and every member of `wasmtime.TrapCode` maps by the rule to lower-case words with no underscore, so a wasmtime release that renames a code fails here first (finding 9).
   - The existing checks that compare `stats()` with an exact dict are unchanged, since `stats()` is.
   - `test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise` (v1.2) skips on Windows with a reason that names no need, which the judge counts as a failure wherever that file runs on Windows (the 015 build review's follow-up). It gains a branch instead: where there is no `RLIMIT_NOFILE`, it checks that a call runs and leaves nothing behind.
6. **Docs.** README: the `trapped` sentence, the cache sentence, the new "Not protected" entry. CHANGELOG, under 0.1.0a3: the sweep, the trap names (as a change to what `trapped` says), and the wheel check.

## Intent

The wheel is proven to be the bytes a second host rebuilt; a killed process no longer leaves a guest's files and the caller's `stdin` behind for good, and no live call's folder is ever removed by a process of the same kernel identity; and a trap says what it was.

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
- Folders left by releases before this one: they have no lock file, so they are left alone; the README's entry tells a user they may delete them by hand.
- A temporary folder shared between kernels (a VM and its host, two hosts over a network filesystem): each kernel sweeps only its own lock files, and a lock that fails (`ENOLCK`) means "leave it", so such folders are only ever leaked, never removed by another kernel. Two kernels that report the same identity (a cloned Windows image keeps its `MachineGuid`) and share one temporary folder are outside this specification; the README names it.

## Acceptance criteria

1. The checks exist and were seen failing before the change.
2. `uv run pytest` is green with `--accept-judge`.
3. A dry run of the release workflow passes every job, including the new wheel check.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5) in a scratch clone of `9ed86d6`, after the pre-build review and its two confirmations passed it for build, then revised against its build review (below), whose confirmation passed it. Every claim below was run (EXECUTED) on macOS arm64, CPython 3.14.2, wasmtime-py 49.0.0, with the main tree's artifact set, unless it says otherwise.

### What was built

- `_Private` (a folder and its locked lock file), `_kernel_identity`, `_try_lock`, `_sweep_once` and `_sweep_entry` in `src/wasi_python/runner.py`; the private root and the stdin folder use `_Private`; the first call sweeps. On this Mac the identity is the boot session's UUID.
- `_trap_name` names any trap with a code by `_trap_code_name`.
- The release workflow: `rebuild` uploads the wheel as `rebuild-wheel-<os>` beside its `SHA256SUMS`; `same-bytes` checks the release's wheel against the set's `SHA256SUMS` (three rules) and against the rebuilt wheel (`cmp`); `verify` runs `tests/unit/test_runner_sweep.py`. The first attempt broke two rules of spec 012's workflow scan (`test_release_workflow_rebuilds_on_a_second_host`): the `SHA256SUMS` upload moved into a folder, and a `||` in `same-bytes`. The judge was not changed; the workflow was: the wheel has its own upload, and the rule is an `if … then exit 1`.
- README: the `trapped` sentence, the Windows cache sentence, and a new "Not protected" entry (killed processes, and a `root=` at or above the temporary folder). CHANGELOG: three lines under 0.1.0a3.

### The wheel rules, each seen failing (Decision 1)

Two local builds of the wheel from the same tree and set, with `SOURCE_DATE_EPOCH` set, were byte-identical. The workflow's rules, run locally on four changed copies of that wheel (scratch `build016/wheelcheck/`): one byte of `MANIFEST` changed fails rule 1 (a hash); a changed `SHA256SUMS` fails rule 2; an extra file fails rule 3; a changed `runner.py` passes rules 1 to 3 and fails rule 4, the comparison with the rebuilt wheel.

### Seen failing first (Decision 5)

Against `main` the new checks fail for missing names and missing lock files. Against stand-ins (scratch `build016/standins.py`, output `standins.txt`), each runner change made by text replacement and reverted afterwards:

| stand-in | checks that fail |
|---|---|
| the sweep does not try the lock | `test_a_live_calls_folders_are_never_swept`, `test_a_held_lock_keeps_its_folder` |
| the sweep ignores the kernel identity | `test_another_kernels_folder_and_an_unnamed_one_stay` (both) |
| no sweep | `test_a_killed_process_leaves_nothing_after_the_next_call` |
| the old trap name | `test_a_trap_is_named_by_its_code`, `test_a_stack_overflow_is_named` |
| a busy lock raises instead of drawing again | `test_a_busy_name_is_drawn_again` |
| the sweep follows a link named like a root | none: `shutil.rmtree` refuses a symbolic link itself, so the canary survives; the check guards the outcome, which two layers give |

The descriptor check's Windows branch and the sweep's Windows path (`msvcrt.locking`, `MachineGuid`) run first in the release workflow's Windows verify job.

### The judge

`uv run pytest` in the clone (no source trees, oracle, prior-art clones or wheel there): 155/166 pass, 0 gap, 0 fail, 11 blocked; v1.4 59/59; unit suite 331/337, 6 skipped; ratchet lost 0, gained 3, grew 0; judge changed: `tests/checks/test_v1_2_hostile_guest.py`, `tests/checks/test_v1_4_embedding.py`, `tests/unit/test_runner_sweep.py`. ruff: clean. The `--accept-judge` run is made on `main` after the build review.

### Left over

- Linux and Windows run the sweep first in the release workflow; the Linux NFS case (C2) and Windows's lock-release delay are covered by design, not by a run here.
- The cross-kernel and container cases were run by the reviewer during the pre-build rounds, not against this code.

### Revised against the build review

The build review (`context/reviews/016-the-security-reviews-leftovers-2026-10-17.md`) found three medium defects and six smaller ones. All are fixed; its disposition section says how. In short:

- **Finding 1.** `_same_file` answers False when the path is gone, and the lock file is removed on a redraw only when step 3 found it still this call's. The reviewer's stepped probe (p1) now draws again, and its stress probe made 6,000 of 6,000 folders with 0 errors and 0 lost (EXECUTED, scratch `build016/mut2/probes/stepped2.txt`).
- **Finding 2, a new decision (above, "A filesystem without locks").** The reviewer's `ENOLCK` probe now runs its call and leaves nothing (EXECUTED, `mut2/probes/stepped.txt`).
- **Finding 3.** The unit test reads the identity through the holder's descriptor.
- **Findings 4 to 8.** New unit cases, each seen failing against a mutation of the fixed runner (EXECUTED, `mut2/run.py`):

| mutation | checks that fail |
|---|---|
| `_same_file` raises when the path is gone | `test_a_lock_file_swept_before_its_lock_makes_the_creator_draw_again` |
| any lock error is "busy" | `test_a_filesystem_without_locks_still_makes_a_folder_that_is_never_swept`, `test_only_contention_is_busy` |
| `_owned` always true | `test_another_owner_is_refused`, `test_owned_means_this_users` |
| `remove()` unlinks the lock file even when the folder is left | `test_a_folder_rmtree_could_not_remove_keeps_its_lock_file` |
| no `O_EXCL` | `test_an_existing_lock_file_is_never_opened_again` |
| the sweep closes before it unlinks | `test_the_sweep_unlinks_before_it_lets_the_lock_go` |

  The stepped probe p2 now shows the live call keeping its lock file: the sweeper holds the lock until its unlink, so the creator draws another name.
- **Finding 7.** When the release's wheel and the rebuilt one differ, `same-bytes` prints each entry found in only one (name, mode, size, CRC, date) and fails. Seen on two hand-made wheels that differ in one entry (EXECUTED).
- **Finding 9.** The `trapped` comment; the failing-listing case makes a folder afterwards; Windows unlocks before it closes (`_unlock_close`); `sysctlbyname` has its `argtypes`.
- **Not checked, and why.** No check can see `O_NONBLOCK` (above), or that a name joins the held set before the open (m14) or leaves it last (m09): only an NFS client that treats `flock` as per-process could tell. The layered defences m07, m08, m10 and m11 each survive alone because another layer holds; the checks guard the outcome.
- **Also.** `_call` makes the stdin folder inside its `try`, so a failure there still closes the store (the review's section 1).
- **The judge (EXECUTED, in the clone, with the main tree's artifact set):** 155/166 pass, 0 fail, 11 blocked; v1.4 59/59; unit suite 338/344, 6 skipped; 493 passed, 17 skipped; ratchet lost 0, gained 3, grew 0; judge changed in the same three files. ruff: clean.
