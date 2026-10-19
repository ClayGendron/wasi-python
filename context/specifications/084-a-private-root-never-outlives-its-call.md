# 084 — A private root never outlives its call

- **Status:** **built 2026-10-19** on `spec/084-a-private-root-never-outlives-its-call`, rebased
  onto main `9d89535` (the Landing notes): the full judge has 0 fail, lost 0, grew 0, gained 6;
  awaiting its build review and the lane's Windows dry run (criterion 17). Before that: drafted 2026-10-19 on `spec/084-a-private-root-never-outlives-its-call` from main
  `a6dfc17` (`d203d78`); **revised 2026-10-19 against its pre-build review** (written in the
  lane's scratchpad, `084-review/084-a-private-root-never-outlives-its-call-spec-2026-10-19.md`,
  with its probes and logs, to be copied to `../reviews/` by the lane; verdict: "ready once F1
  to F3 are written in"; every finding answered in "Disposition of the pre-build review");
  **confirmed for build once C1 is written in** (the confirmation, appended to the same review,
  on `eaf584d`), and C1, C2 and N1 are written in (the same section). It builds after spec 083
  lands, since both touch the runner (the lane). It
  changes neither the guest's imports nor its exports, the artifact set nor the build recipe,
  so §5.6 asks no review before build; the lane asked for one. The review says none of its
  findings needs another pre-build review if written in as it asks. A different agent reviews
  the build, and re-runs the review's `r1_escalation.py` and `r2_walk_attacks.py` against the
  built `_remove_tree`. Due before
  0.1.0 final (the 0.1.0a7 security review, F1).
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** the runner, the judge and docs; **parallel-safe**, not build-class (§5.7). The code:
  `src/wasi_python/runner.py` only (`_Private.remove`, `_sweep_once`, `_sweep_entry`, the fresh
  `HOME`'s removal in `_call_deferred` and `_remove_home`, the warning queue and its flush,
  two comments that say Windows guests cannot make links, and one new private function,
  `_remove_tree`). The checks: `tests/unit/test_runner_sweep.py` (new cases, and one case's
  body restated, Decision 9) and `tests/checks/test_v1_4_embedding.py` (three new checks). The
  docs: `README.md` (*Safety*, *Not protected*), `CHANGELOG.md` (0.1.0a8). It touches no
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` or workflow, and not the guest, so no rebuild:
  the wheel's runner changes, the artifact set does not. **It changes no line of
  `tests/public_api.txt`**: no public name, default, field or `stats()` key (Decision 7).
- **Depends on:** 016 (the lock files beside each private folder, and the sweep), 017 (the zip
  folder, a third private folder), 024 (the fresh `HOME` made and removed through a handle on
  `/tmp`), 055 (a session's release removes its folders), 068 (the store is closed before the
  clean-up, so the clean-up has descriptors). All landed.
- **Research it stands on:**
  - The 0.1.0a7 security review, F1 (`../reviews/0.1.0a7-security-review-2026-10-19.md`,
    EXECUTED there, its probe `p31d_private_root_dirfd.py`): under `root=True`, a guest that
    builds 400 levels at a soft limit of 256, or 1,500 at 1,024, leaves its private root and
    lock file behind; `run` returns exit 0.
  - This spec's probes, EXECUTED on darwin arm64 (Darwin 25.5.0) with CPython 3.14.2, 3.12.12
    and 3.11.14 and wasmtime-py 49, against a fresh `cp -Rp` copy of main's set
    `s-c50ca51fae5eb55b-c9dcb5b8`; on Linux in `python:3.13-slim` (its linux/amd64 image, emulated on arm64) as uid 1000 for the removal's
    prototypes. Scripts and outputs: `../research/2026-10-19-a-private-roots-removal/`. Each
    probe runs in a child with `tempfile.tempdir` set to a folder of its own, and every root it
    left was deleted by name afterwards (`matrix.sh` prints each deletion).
  - CPython's `Lib/shutil.py` (`context/prior_art/cpython`, branch 3.14, `7c04882`, READ):
    `_rmtree_safe_fd` pushes each level's descriptor on its stack with an `os.close` action, so
    it holds one descriptor per level until that level's subtree is done; `os.scandir(fd)` dups
    the descriptor. The installed 3.11.14's `_rmtree_safe_fd` recurses, one Python frame per
    level; 3.12.12's is the stack version (READ, each `shutil.py`). `Lib/os.py` `_fwalk` keeps
    each level's descriptor on its stack the same way (READ).
  - CPython's `Modules/posixmodule.c`, `Py_DeleteFileW` (READ): on Windows `os.unlink` removes
    a directory symbolic link or junction with `RemoveDirectoryW`, and never follows it.
  - cap-primitives 4.0.3, the version wasmtime 49 locks (`context/prior_art/wasmtime-v49`,
    `Cargo.lock`; source in the cargo registry, READ): on Windows `create_dir_unchecked` makes a
    folder by the full path of its parent's handle joined with the name
    (`get_path.rs`, `concatenate`), through Rust's `std::fs`.
  - The WASI preview1 interface (`crates/wasi/witx/p1/wasi_snapshot_preview1.witx` in
    wasmtime-v49, READ): no call sets a file's permissions or attributes. `fd_filestat_set_size`
    and the two `*_set_times` are the only setters.
  - Constitution §2.2 (no host process) and `src/wasi_python/` (READ: no `subprocess`,
    `os.system` or `Popen` anywhere in the runner).
  - The pre-build review's probes (with the review, EXECUTED there on darwin): `r1_escalation.py`
    (F1: the permission repair deletes a file the guest cannot), `r2_walk_attacks.py` (the
    climb's identity check under five attacks by hook, and without it; a writer that adds a file
    after each unlink), `r3_chmod_toctou.py`, `r4_311_1024.log` (3.11 at a soft limit of 1,024),
    `r6_walk_three_free.py`.
  - This spec's probes after the review (EXECUTED, darwin, CPython 3.14.2, the same set):
    - `p_guest_modes.py` → `.out`: whether a guest can make anything unwritable or unreadable
      (Decision 4);
    - `proto_walk2.py`: the walk as revised (no permission repair; a budget of calls), with
      `t_walk2.out` (the static cases), `t_writer.out` (the budget against a writer),
      `r1_escalation_walk2.out` (the review's F1 probe against it: the protected file is kept)
      and `r2_walk2.out` (the review's attacks against it: the canary kept in every case;
      emptied in three without the identity check).

## The problem

`root=True` gives a call a fresh private folder as its `/`. The README promises it is "removed
afterwards", and that only a killed process leaves one behind. A hostile guest breaks that
promise.

**What it does.** The guest builds a tree one level at a time through `dir_fd`. It holds one
descriptor at a time, so 068's cap never refuses it. The runner removes the root with
`shutil.rmtree(path, ignore_errors=True)`. Python's descriptor-safe `rmtree` holds one
descriptor per level while it descends. A tree deeper than the process's free descriptors makes
it fail. The failure is silent: errors are ignored.

**Reproduced** (EXECUTED, `m-run-256.log`, `m-more.log`, `m-check-params.log`). Each row is a
child process at the soft limit shown; the call's own removal ran with 9 descriptors open, the
next process's sweep with 5.

| soft limit | depth | `run` | the call's removal | the root after `run` | the next process's sweep |
|---|---|---|---|---|---|
| 256 | 244 | exit 0 | clean | gone | nothing to do |
| 256 | 246 | exit 0 | one `EMFILE` at the leaf, then removed | gone | nothing to do |
| 256 | 247 | exit 0 | one `EMFILE`, 247 `ENOTEMPTY` | **left, all 247 levels** | removed it (5 open) |
| 256 | 250 | exit 0 | the same | **left, 250 levels** | removed it |
| 256 | 400 | exit 0 | the same | **left, 400 levels** | **failed too; still left** |
| 128 | 256 | exit 0 | one `EMFILE`, 119 `ENOTEMPTY` | **left** | **failed; left** |
| 1,024 | 1,000 | exit 0 | clean | gone | nothing to do |
| 1,024 | 1,020 | exit 0 | one `EMFILE`, 1,015 `ENOTEMPTY` | **left** | **failed; left** |
| 1,024 | 1,500 | exit 0 | the same | **left** | **failed; left** |

- **The threshold.** The call's removal fails once the depth reaches the free descriptors at
  that moment: 256 − 9 = 247 here. Nothing is removed at all: `rmtree` fails at the bottom, and
  every folder above it is then not empty.
- **Sessions.** A `Session(root=True)` whose turn builds the tree leaves it the same way at its
  close: 300 levels at 256, 1,500 at 1,024, 256 at 128 (`m-more.log`, `m-check-params.log`).
- **What follows.** The lock file stays (the folder still exists), the name is dropped, and this
  process never retries. The next process's first call retries once, with the same `rmtree`,
  and fails the same way under the same limit. So disk use adds up call by call, and the
  README's bound, "until its deadline", does not hold.
- **How deep a call gets.** On darwin a guest reached 3,000 levels within the default 60 s
  deadline at a soft limit of 8,192; its cost per level grows with depth, so a deadline of 60 s
  did not reach 4,100 (EXECUTED, `p_deadline_depth.out`; a benchmark fact). A session keeps its
  root across turns, each with its own deadline, and `deadline_s=None` has none, so neither is
  bounded.
- **CPython 3.11, which the wheel supports** (`requires-python = ">=3.11"`). Its `rmtree`
  recurses, one Python frame per level, so past about 995 levels **`run` raises
  `RecursionError`** out of `_Private.remove`, whichever comes first, the frames or the
  descriptors. At Linux's common soft limit of 1,024 the frames come first: 990 levels are
  removed, and 1,010 make `run` raise (EXECUTED, the review's `r4_311_1024.log`). At 8,192, 1,500
  levels raise (EXECUTED, `p311.log`: the traceback runs `run`, `_run_checked`, `remove`,
  `rmtree`, `_rmtree_safe_fd` ×995). At 256, 400 levels fail silently as above. `remove` then
  never reaches `_unlock_close` or `_drop`, so the lock stays held and the name stays in `_held`
  for the process's life, and no sweep of this process ever tries it (READ, `runner.py`). This
  breaks a second promise: nothing a guest does makes `run` raise. 3.12.12 and 3.14.2 do not
  raise (`p312.log`, `m-more.log`). The release's jobs run 3.14.2 only (`UV_PYTHON`, READ by the
  review), so no release job sees this.
- **The fresh `HOME`.** A call given a root of the caller's, or a writable grant at `/tmp`,
  gets a fresh `HOME` in that folder, removed with the same `rmtree` through a handle on
  `/tmp`. A guest that builds 256 levels in its `HOME` at a soft limit of 128 leaves
  `/tmp/.home-…` in the caller's root (EXECUTED, `p_home.out`). The README promises that `HOME`
  is "removed after it".
- **What it does not break.** The folder is `0700`, never reused, and nothing outside the
  temporary folder changes; no other call sees it.

## Decisions

1. **One removal for every folder the runner makes for a call, `_remove_tree`.** It replaces
   `shutil.rmtree` in `_Private.remove` (the private root, the stdin folder, a session's scratch
   folder, the zip folder), in `_sweep_entry`, and in the fresh `HOME`'s two removals
   (`_call_deferred` and `_remove_home`). It returns True when nothing is left at the name, and
   never raises `OSError`.
   - Its form: `_remove_tree(path, *, dir_fd=None, budget=None) -> bool` (`budget`: Decision
     12, the `HOME` removals only). With `dir_fd`, `path` is a name in
     that folder, as `shutil.rmtree` takes it. The checks patch it by this name.
   - **Not changed:** the zip folder's own helpers (`_copy_zip`, `_extract_data`, `_real_folder`)
     keep `shutil.rmtree` for what they replace inside the zip folder. Only the runner writes
     there, and no guest can (the zip and matplotlib's data are read-only grants).

2. **On POSIX the removal is a walk that holds at most two descriptors.**
   - **Down by name, up by `..`.** It holds the folder it is in. It opens the next folder down
     by name, relative to that one, with `O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC`
     (`O_NONBLOCK` where defined), then closes the one it held. When a folder has nothing left
     it can remove, it opens `..` relative to it, checks that this is the parent it recorded on
     the way down, closes the child and removes the child by name with `rmdir`.
   - **What it records.** One frame per level below the top: the folder's name in its parent,
     the parent's `(st_dev, st_ino)`, and the names in the parent it could not remove. Memory
     grows with depth, never descriptors.
   - **The identity check.** If `..` is not the recorded parent (a folder moved during the walk),
     the walk stops and reports failure. So it never leaves the tree by climbing.
   - **How it lists.** A listing reads at most 1,024 entries of the folder with
     `os.scandir(fd)`, skipping names already recorded as failed, and closes the listing before
     it acts, so no entry is removed while a listing is open (some filesystems skip entries
     removed under an open listing). It then unlinks each entry that is not a folder, in order,
     until it meets the first folder, and descends into it. The folder is listed again after a
     descent returns, and after a listing that removed something. A listing that removes nothing
     and finds no folder to enter ends that folder. Without a writer, every entry is read about
     once; with one (only a `HOME` can have one), Decision 12's budget ends the walk.
   - **Links are never followed.** An entry is a folder only if `DirEntry.is_dir(follow_symlinks=
     False)` says so. A link, to anything, is unlinked like a file. A folder swapped for a link
     between the listing and the open fails the `O_NOFOLLOW` open; the name is then recorded as
     failed and left, and the removal returns False (the review's attack B, EXECUTED: the link
     and the moved folder are left, the canary kept). Only a concurrent writer can make that
     swap; a private root is then retried by the sweep, which sees a plain link and unlinks it.
   - **A folder it cannot open** (`EACCES` or `EPERM` on the open: a folder of mode `0000`, say)
     is tried once with `rmdir` by name before it is recorded as failed (the confirmation's N1).
     Removing an empty folder needs only the parent's write permission, which the guest has as
     well, so this oversteps nothing; a folder that is not empty refuses, and is left.
   - **Another device.** A folder whose `st_dev` differs from the top's is never entered; it is
     left and the removal fails. A guest cannot mount anything; only the host could put one
     there. `st_dev` does not tell a bind mount of the same filesystem from a plain folder, so
     the walk enters one; only root can make one, and `shutil.rmtree` enters every mount today.
   - **The top.** `lstat` first. A name that is no longer a folder (a link or a file in its
     place) is unlinked, never followed: the runner made that name, and it is the runner's to
     remove. A folder is opened with `O_NOFOLLOW` and checked against the `lstat` by
     `(st_dev, st_ino)`, as `_sweep_entry` already checks the lock file.
   - **It creates and renames nothing.** It only unlinks and removes folders, which on the common
     filesystems need no free space (the third alternative below says why that matters). A
     copy-on-write filesystem filled to its last block (btrfs) can still refuse them; then the
     removal fails and is retried.
   - **An empty top.** A folder with nothing in it is removed with one `rmdir`, and no `unlink`
     is called (`test_a_private_folder_goes_before_its_lock_file` counts exactly one
     `os.unlink` during `remove()`: the lock file's).
   - **Descriptors.** The folder it is in, plus one: the next folder down, `..`, or the
     listing's dup. At most two at once, three with the parent handle a `dir_fd` call already
     holds. The check gives it three free and no more (criterion 4).
   - **Why not the alternatives.**
     - `shutil.rmtree`: one descriptor per level (READ; EXECUTED above), and on 3.11 one Python
       frame per level, which raises.
     - `os.fwalk`, bounded or not: it keeps each level's descriptor on its stack until that
       level is done (READ), so the same failure.
     - **Renaming each deep folder up into a holding folder**, so the tree becomes wide and each
       piece is removed at depth two (the security review's first suggestion): it works, at four
       descriptors (EXECUTED, `proto_remove.py`, `t_proto.out`), but it must make a folder and
       add entries. A guest can fill the disk before it ends ("tens of GiB in the default 60
       s"). On a full 8 MiB volume the rename design failed at its first `mkdir` with `ENOSPC`,
       and the walk removed the same 300-level tree (EXECUTED, `t_full.out`).
     - **`rmtree` first, the walk only on `EMFILE`** (the security review's second suggestion): two code
       paths, and the one that matters runs only under attack, so it is the least exercised.
       The walk costs a default call a few more system calls than `rmtree` on a tree of five
       folders. One path, run by every call.
     - **A native `rm -rf`**: the runner starts no host process (constitution §2.2; READ, no
       `subprocess` in `src/wasi_python/`); a child process from a process that runs wasmtime is
       what spec 015 had to refuse for `fork`; and Windows has no `rm`.

3. **On Windows the same walk runs on paths.**
   - **Extended-length paths.** The top's absolute path with the `\\?\` prefix. The walk goes
     down by joining a name and up by dropping the last one. Windows has no `dir_fd`
     (`_dir_fd_ok()` is false there today), and an extended-length path is not limited to 260
     characters.
   - **Why a path walk reaches everything a guest made.** On Windows cap-primitives makes a
     guest's folder by its full host path (READ), so no guest path can be longer than that
     path's limit, 32,767 characters, which is the walk's limit too.
   - **Links and junctions are never entered.** An entry is a folder only if it is a folder
     without a reparse point that `shutil` treats as a link: `DirEntry.is_dir(follow_symlinks=
     False)` and not `DirEntry.is_junction()` (3.12 and later), or on 3.11 not
     `st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT` from `lstat` (as `shutil`'s
     `_rmtree_islink`). Each link or junction is removed with `os.unlink`, which removes a
     directory link without following it (READ, `Py_DeleteFileW`).
   - **The read-only attribute is never cleared** (Decision 4). A delete refused with
     `PermissionError` records the entry as failed; the folder is left, warned about and retried.
   - **Links on Windows.** A Windows guest can make links where the user holds the
     symbolic-link privilege: wasmtime 49 calls `symlink_dir` or `symlink_file` there (READ by
     the review, `filesystem/windows.rs`), and GitHub's Windows runners run as an administrator.
     The runner's two comments that say Windows guests "cannot make links" (`_call_deferred`,
     `_real_dir`) are corrected to say so; their code does not change. A path walk descends by
     name, so a reparse point swapped in by a concurrent writer between the listing and the
     descent is followed, as `shutil.rmtree` on Windows does today (`avoids_symlink_attacks` is
     False there). Only a concurrent call on a shared root can make that swap, under the
     *Not protected* entry for concurrent calls on one root; no private root has a writer.
   - **Open handles.** The call's own handles are closed before the removal: the store, and every
     walked folder (Windows holds them until then, `_run_checked`'s `finally`). A file another
     program holds open without delete sharing (an antivirus scanner, the search indexer) makes
     the removal fail. That folder is retried (Decision 5).

4. **No permission repair: what the removal may not delete, it leaves.** The removal never
   changes a mode or an attribute, on POSIX or on Windows. An entry whose removal is refused
   (`EACCES`, `EPERM`, a read-only attribute) is recorded as failed; the folder is then left,
   warned about (Decision 7) and, if it is a private folder, retried (Decision 5).
   - **Why (the review's F1, EXECUTED).** A repair makes the runner the guest's deputy. The host
     makes `data/ro/` `0500` in a writable root or grant, with a file in it. The guest cannot
     unlink that file (`PermissionError`), but it can rename the writable `data/` into its
     `HOME` or its private root. A removal that made `ro` `0700` then deleted the file; main's
     `rmtree` leaves it. The revised walk leaves it too, in both cases (EXECUTED,
     `r1_escalation_walk2.out`: the file found intact in the `HOME` and in the left private
     root). No rule tells the call's own folders from moved-in ones, so the repair goes.
   - **What it costs: nothing for what a guest makes (EXECUTED, `p_guest_modes.out`).** A guest
     cannot make anything unwritable or unreadable. In the guest, `os.mkdir(p, 0o500)`,
     `os.mkdir(p, 0o000)`, `os.open(p, O_CREAT, 0o400)` and `os.chmod` on a folder and a file all
     return without error, but on the host every folder is `0755` and every file `0644` (the
     host's umask, 022, applied to wasmtime's defaults), and the host's `rmtree` removes them
     all; `os.fchmod`, `os.umask` and `os.mkfifo` do not exist in the guest. Preview1 has no call
     that sets a mode or an attribute (READ), so the same holds on Windows (INFERRED from the
     same interface). Read-only content in a
     folder the runner removes is therefore always the host's: made by the host or one of its
     tools, or moved in by the guest. It is left, and named.
   - **What it leaves behind.** A private root that holds such content is kept with its lock
     file, retried by up to three sweeps in this process and by the next process's first call,
     and named by one warning in each process that tries; the protected file is never deleted.
     That is main's behaviour for this content, plus the warning.

5. **What a removal leaves is retried by the next call's sweep.**
   - **The call's own removal.** When `_remove_tree` leaves the folder, `_Private.remove` keeps
     the lock file (as today), unlocks and closes it, **drops the name from `_held` first, and
     only then re-arms this process's sweep**: `_sweep_state["claimed"]` goes back to False,
     under `_lock`. In the other order a sweep on another thread could claim the re-arm, see the
     name still held, skip it, and so spend the retry (the review's F6). The next call's
     `_sweep_once` then lists the temporary folder again and finds that folder like a dead
     process's: unlocked, this kernel's, not held. It removes it with the same walk.
   - **The bound.** `_sweep_state` keeps a count of failed attempts per name. A sweep collects
     its failures and, **after its loop over the temporary folder ends**, re-arms once if any
     failed name has failed fewer than three sweeps in this process. A re-arm from inside the
     loop would let a second sweep start while the first still lists; on NFS, where `flock` may
     be per process, two walks could then meet on one folder and report a false failure (F6). A
     name at its bound is skipped by later sweeps of this process. So a folder that cannot be
     removed (a file held open for good) costs this process its own removal and at most three
     more sweeps, then waits for the next process's first call. A dead process's folder is
     retried the same way: at most three re-armed sweeps.
   - **Why the sweep, not a list of this process's leftovers.** The sweep already has every rule
     a retry needs: the lock (so a retry never races a live call), the kernel's identity, the
     owner check, links refused at the top. A second mechanism would need them all again. The
     cost is one listing of the temporary folder per retry, only after a failure.
   - **The fresh `HOME`.** A `HOME` the removal leaves lies in the caller's own folder (its root's
     `tmp`, or a writable grant at `/tmp`), with no lock file, so no sweep can know it is dead.
     It is not retried; it is warned about (Decision 7). A `HOME` in a private root goes with the
     root.

6. **`remove` never raises, and always lets go.** `_Private.remove` calls `_remove_tree` inside
   `try … except Exception` (a failure is a folder left), and unlocks, closes and drops the name
   in a `finally`. So a removal that fails in a way no one foresaw (3.11's `RecursionError` was
   one) leaves a folder with its lock file free for the sweep, never a held lock and a held name.
   `_sweep_entry` and the `HOME` removals keep their errors from the call the same way.

7. **A folder left is reported as a `RuntimeWarning`, once per folder per process.**
   - The message names the folder's host path, says it was kept with its lock file and will be
     retried by the next call's sweep (or, for a `HOME`, that it was left in the caller's
     folder), and gives the first error: `wasi_python: could not remove the private folder
     /…/wasi-python-root-…: [Errno 16] …; kept with its lock file, retried at the next call`.
   - A sweep's failure warns too, once per name per process, so a folder no process can remove
     is named once by each process that tries.
   - **It never makes `run` raise.** The call to `warnings.warn` is inside `try … except
     Exception`, so a filter that turns warnings into errors loses the warning, never the call.
     Nothing a guest does makes `run` raise, and that holds here.
   - **It is given outside every runner lock (the review's F6).** `warnings.warn` calls the
     embedder's `showwarning` (a `logging.captureWarnings` handler, say), which may call
     `wasi_python.stats()` (it takes `_lock`, which is not re-entrant) or `run`. A removal can
     run under `_zip_lock` (`_zip_folder`'s re-make, `_zip_folder_locked`'s failure) and, once
     078 lands, under its home's lock. So a removal never warns itself: it appends its message
     to a queue (a list under a lock of its own, held only to append or to take the list), and
     `_flush_warnings()` gives the queued warnings. The flush runs where no runner lock is held:
     as `run`, `run_async`'s worker, `Session`'s constructor, `Session.run` and `Session.close`
     return (normally or by raising), at the end of a session's idle or lifetime ending, and at
     the end of the exit hook `_release`. A message queued after its call returned (078's
     abandoned teardown) is given by the next flush.
   - **Why a warning.** The review found the call "reports nothing". A warning is Python's way to
     tell a host about trouble that did not stop the call, and the runner already uses one for a
     module cache it refuses (`_private`).
   - **Why not a field or a `stats()` key.** A field in `Completed` reports the guest's call, and
     the folder's removal comes after the guest; a key would change the frozen public API
     (spec 049) for a diagnostic the warning already gives. Neither is needed to close F1.

8. **A live call is never raced.** The rules that keep a sweep off a live call's folder stand:
   the owning call removes its folder after its store and its walked handles are closed, holding
   its lock; a sweep removes only a folder whose lock it took, of this kernel, not a name this
   process holds; a session removes its folders at its release, after its store. **On POSIX**
   the walk adds its identity checks, so even a folder moved during the walk (for a private root
   only a host process of the same user could; for a `HOME` in a shared root, a concurrent call)
   cannot lead it outside the tree: the review's attacks by hook found the canary kept in every
   case, and emptied without the check (EXECUTED, `r2_walk2.out`). **On Windows** the path walk
   has no such check (Decision 3); there the claim is only that no private root has a writer.

9. **One existing check is restated, not weakened.** `test_a_folder_rmtree_could_not_remove_keeps
   _its_lock_file` makes the removal fail by replacing `shutil.rmtree`, which the runner no
   longer calls for its folders. It replaces `runner._remove_tree` with one that returns False
   instead, and asserts what it asserted: both entries kept, then one sweep removes both. It
   adds one assertion: `remove()` gives one `RuntimeWarning` (`pytest.warns`, with
   `_flush_warnings()` called inside the block). Its name is kept, so the ratchet sees the same
   pass. Its explicit `claimed = False` stays, so the check does not depend on the re-arm,
   which criterion 10 tests. If `shutil` becomes unused in the file, its import goes (ruff
   F401). The judge-hash line shows the file.

10. **Where the checks run.** `tests/unit/test_runner_sweep.py` is in the release's `own-runner`
    shard and `tests/checks/test_v1_4_embedding.py` in `own-embedding`, each on macOS, Linux and
    Windows (`tests/release_shards.toml`). On POSIX the deep cases set `RLIMIT_NOFILE` in a child
    process, so they count descriptors and entries and time nothing. Windows has no
    `RLIMIT_NOFILE`, and its removal never held a handle per level; there the deep cases build
    trees whose host paths pass 260 characters, the limit the old removal met there. Criterion 17
    names which leg each check runs on Windows.

11. **Coordination.**
    - **072 (a bound on path depth, not drafted).** It bounds the components of one path a path
      call resolves. F1's tree is built one component at a time, `"a"` relative to a held
      descriptor, so 072 does not close F1, and 084 does not bound depth. The two touch different
      functions. Both edit the README's *Not protected* paragraph (072 its sentence "a bound on
      path depth is planned"); the second to land rebases that sentence.
    - **078 (the runner runs each guest on a thread of its own, being built).** 078 moves the
      guest's call onto a runner-owned thread with an 8 MiB stack. The removals stay in the same
      `finally` blocks, after the store closes, and 084 changes only what those blocks call. The
      walk holds no recursion, so the stack does not matter to it. If 078 lets `run` return
      while a stopped guest's thread still runs, the folder must be removed on that thread after
      its store closes, not on the caller's; that is 078's ordering to keep. 078's Decision 14
      registers the teardown steps with its home and runs them under the home's lock: 084's
      removal never raises (as those steps need), and it neither warns nor re-arms the sweep
      under that lock in a way that can deadlock (the warning is queued, Decision 7; the re-arm
      takes only `_lock`, which no teardown step holds). Whichever lands second rebases the
      `finally` blocks textually and keeps both rules.
    - **073 (`run` keeps an unclosed file's bytes, built, waiting to land).** It adds about 220
      lines to `tests/checks/test_v1_4_embedding.py`, where criteria 1 to 3 go. The merge is
      textual; whichever lands second rebases that file.
    - **083 (the judge's driver, confirmed for build).** The driver removes its run folders with
      `shutil.rmtree(ignore_errors=True)`. 084's checks call `wasi_python.run` and `Session` in
      child processes with temporary folders of their own, never the driver, so they neither
      depend on 083 nor leave anything in its folders. The driver may call `runner._remove_tree`
      once 084 lands; that is not in this scope.
    - **068 (the open-file cap).** The store closes before the clean-up, so the walk's two
      descriptors are there unless other calls hold the whole table. Then the removal fails, the
      folder keeps its lock file, and the next sweep retries it.

12. **A budget bounds the removals that can have a concurrent writer: the `HOME`'s (the review's
    F3; its confirmation, C1).**
    - **The case.** A `HOME` in a caller's root, or in a writable grant at `/tmp`, can be written
      while it is removed, by another call on the same root (a session, or a call with
      `deadline_s=None`). Decision 2 lists a folder again after a listing that removed something,
      so a writer that keeps adding entries keeps the walk going, and the first call's `run`
      does not return: a hook that added a file after each unlink gave 20,002 unlinks for 20,000
      files added (EXECUTED by the review, `r2.log`, `E_writer_*`; `r2_walk2.out` the same for
      the revised walk under the default budget, since 20,000 is below it). Today's `rmtree`
      lists each folder once and gives up.
    - **The bound.** `_remove_tree` takes `budget=None`. The two `HOME` removals
      (`_call_deferred`, `_remove_home`) pass `budget=_REMOVE_BUDGET`, `2**20` (1,048,576)
      counted calls: each `os.open`, listing, `os.unlink` and `os.rmdir`. Past it, the walk
      closes what it holds and returns False: the `HOME` is left in the caller's folder and
      named in a warning. A writer can hold one `HOME` removal for at most that many calls:
      about 50 s on an arm64 Mac (the review's benchmark, `r7_entry_rate.log`: 83,103 counted
      calls in 4.3 s of host time on a flat tree; a benchmark fact, never a check). With a
      budget of 10,000 and a writer adding a file after each unlink, the revised walk returned
      False after 4,998 unlinks and 5,000 listings; with the default budget and the writer
      stopped at 50,000 files, it removed everything (EXECUTED, `t_writer.out`).
    - **No budget for private folders.** `_Private.remove` and `_sweep_entry` pass none: the
      private root, the stdin and scratch folders and the zip folder. None has a writer when it
      is removed:
      - the call's guest has ended: its store is closed first (`_run_checked`'s and
        `_instance`'s `finally`; a session's release; under 078, the guest's thread after its
        store);
      - the folder is `0700`, under a name drawn at random and never handed to the embedder or
        the guest (no field of `Completed` carries it), and only the runner writes the stdin,
        scratch and zip folders; no grant may reach the temporary folder (spec 032), so no
        other call's guest can either; a mount's placeholder in the scratch folder is served by the
        embedder's provider, never written on disk by the guest;
      - a sweep removes a dead process's folder only under its lock, so no live call of any
        process writes it;
      - a host process of the same user could still write it, but such a process can do anything
        to the user's files, and the identity check keeps the walk inside the tree regardless.
      I found no case where a private folder has a writer. A budget there would buy nothing, and
      would cost F1's harm again by size: a guest made 83,000 files in 10 s (the review,
      `r7_entry_rate.log`), so a session or a call with `deadline_s=None` can pass the four
      million entries that four budgets remove, and such a root would outlive its call.
    - **Why a budget of calls, not a cap on listings per visit.** A cap on listings still lets
      one listing grow with a writer on some filesystems (a directory stream may return entries
      made after it opened), and needs a second rule for very wide folders; a count of calls
      bounds every case with one number, counts operations, and times nothing.
    - **What it costs a legitimate `HOME`.** One budget removes about 300,000 entries (the
      prototype spent about 3.5 counted calls per entry, `t_walk.out`). A `HOME` larger than that
      is left in the caller's folder and named; a guest that needs such a cache in its `HOME`
      can be given `HOME` in `env=`.
    - **The value.** 2**20 is large enough that no check or common call meets it, and small
      enough that a writer cannot hold a `run` for more than about a million system calls. The
      checks patch `runner._REMOVE_BUDGET` to test the bound.

## Intent

A folder the runner makes for a call is gone when the call returns, whatever the guest built in
it: deep, wide, full of links. The removal never deletes what the host forbids: it changes no
mode and no attribute, so content the host made read-only is left, even when the guest moved it
in. If anything stops the removal (such content, a file another program holds open, a full
descriptor table), a private folder keeps its lock file, the embedder gets one warning, and
the next call retries it. A `HOME` in the caller's folder, which another call on that root may
be writing, has a budget of calls; past it, it is left and named. The removal holds two
descriptors whatever the depth, and creates nothing.

## Design

- **`_remove_tree(path, *, dir_fd=None, budget=None) -> bool`** (`runner.py`, beside
  `_Private`). POSIX
  (`_dir_fd_ok()` true): Decision 2's walk, through descriptors. Elsewhere: Decision 3's walk,
  through extended-length paths (the `\\?\` prefix only on Windows; the same code with plain
  absolute paths when a test forces this branch on POSIX). Both: no permission repair
  (Decision 4), the identity check at the top, Decision 12's budget when one is passed (the
  `HOME` removals only), `False` on any failure,
  `True` when the name is gone. It keeps the first error it met, for the warning.
- **`_REMOVE_BUDGET = 2**20`**, a module constant (Decision 12), passed as `budget=` by the two
  `HOME` removals only; `_remove_tree(path, *, dir_fd=None, budget=None)`.
- **`_Private.remove`**: `gone = _remove_tree(self.path)` guarded (Decision 6); unlock and close;
  the lock file unlinked only if the folder is gone (as today); `_drop(self.name)`; then, if the
  folder is left, `_left(self.path, error)`: queue the warning once (Decision 7) and re-arm the
  sweep (Decision 5). The `_drop` sits in a `finally`, and the re-arm comes after it.
- **`_sweep_once`**: claims as today; collects the names that failed; after the loop, re-arms
  once if any of them is below the bound. **`_sweep_entry`**: `_remove_tree(path)` in place of
  `rmtree`; on failure, the per-name count and the queued warning; it never re-arms itself. A
  name at its bound is skipped.
- **The `HOME`**: `_remove_tree(name, dir_fd=tmp_fd)` where there is a handle, else
  `_remove_tree(tmp / name)`; on failure, the queued warning only.
- **The warnings**: `_warn_later(message)` appends to `_pending_warnings` under
  `_pending_warnings_lock` (held only to append or to swap the list); `_flush_warnings()` swaps
  the list out and gives each message with `warnings.warn(message, RuntimeWarning,
  stacklevel=…)` inside `try … except Exception`, at the points Decision 7 lists.
- **State**: `_sweep_state` gains `"failed": dict[str, int]` (names to failed sweeps) beside
  `"claimed"` and `"swept"`, and the warned names live in a set beside it, under the locks the
  existing fields use. They grow only with failures.
- **Comments**: the two that say Windows guests cannot make links (`_call_deferred`, `_real_dir`)
  say instead that they can where the user holds the symbolic-link privilege (Decision 3).

## Scope

In: Decisions 1 to 12; the README's *Safety* and *Not protected* sentences on the private root,
the `HOME`, read-only content, the budget and what a removal leaves; two CHANGELOG entries under
0.1.0a8 (criterion 19).

Out, each with its reason:
- **A bound on depth or on entries a guest makes.** 072's work for paths; disk use inside a call
  stays as *Not protected* says, bounded by the call's deadline, but no longer adds up across
  calls.
- **Removing content the host made read-only** (Decision 4).
- **Race-freedom of the Windows path walk against a concurrent writer** (Decision 3): only a
  shared root has one, and concurrent calls on one root stay *Not protected*.
- **The judge driver's folders** (083's; Decision 11).
- **Folders from releases before 0.1.0a3**, which have no lock file: unchanged, removed by hand.
- **A count in `Completed` or `stats()`** (Decision 7).
- **Removing with a host process** (Decision 2).
- **The zip folder's own helpers** (Decision 1).

## Acceptance criteria

Each check is written before the code and seen failing on main (`a6dfc17`) where the defect
shows there; each named stand-in (a mutant of the built code) is applied, its check run and seen
failing, and the file restored. The landing notes list each with its failing line. "Child"
means a fresh `sys.executable` process with `tempfile.tempdir` set to the case's own empty
folder, run with a 120 s fail-safe (a timeout that never decides a verdict), as spec 016's
checks run. "Three free descriptors" means the child, after its imports, sets its soft
`RLIMIT_NOFILE` so that exactly three descriptor numbers below the limit are unused, counting
the holes below the highest open descriptor (the review counted four free with the parent held,
`r6.log`, so the arithmetic must count them). A tree deeper than about 500 levels is built
through `dir_fd`, one level at a time, since macOS's `PATH_MAX` is 1,024 bytes. Each check that
expects a warning calls `runner._flush_warnings()` before it looks.

1. **`test_a_deep_private_root_is_removed[run]` and `[session]`** (`tests/checks/
   test_v1_4_embedding.py`, artifacts). In a child at a soft limit of 128, a guest given
   `root=True` (or the turn of a `Session(root=True)`, then closed) builds 256 levels through
   `dir_fd` as F1's probe does, and prints `built 256`.
   - The call (the turn) returns exit 0 and `built 256`; no warning was raised in the child
     (`warnings.catch_warnings(record=True)`, `simplefilter("always")`).
   - After `run` returns (the session closes), the child's temporary folder holds no
     `wasi-python-root-*` entry and no lock file of one; after the child exits, it holds no
     `wasi-python-*` entry at all.
   - **Windows:** the guest builds 120 levels of a ten-character name (a host path of more than
     1,300 characters), no limit set; the same assertions.
   - Seen failing on main (POSIX): the root and its lock file are left, 256 levels (EXECUTED
     with these parameters, `m-check-params.log`, and by the review, `r5_criterion1_on_main.log`).
     On Windows it guards the long-path case and may pass on main.
   - Stand-ins: (a) `_remove_tree` replaced by `shutil.rmtree(…, ignore_errors=True)` and
     `True`: the root is left; (b) the walk keeps each level's descriptor open until it climbs:
     the root is left.
2. **`test_a_deep_fresh_home_is_removed[run]` and `[session]`** (`tests/checks/
   test_v1_4_embedding.py`, artifacts). In a child at a soft limit of 128, a guest given a
   caller's root builds 256 levels under its `HOME`: in one `run`, or in the turn of a
   `Session` with that root, then closed (the review's F7: this reaches `_remove_home`).
   Afterwards the root's `tmp` holds no `.home-*` entry, and no warning was raised. Windows: 120
   levels of a ten-character name, no limit. Seen failing on main (POSIX, `[run]`): `.home-…` is
   left (EXECUTED, `p_home.out`). Stand-ins: the `HOME` removal in `_call_deferred` left on
   `shutil.rmtree` fails `[run]`; `_remove_home` left on it fails `[session]`.
3. **`test_the_removal_never_deletes_what_the_guest_may_not[home]` and `[private]`**
   (`tests/checks/test_v1_4_embedding.py`, artifacts; the review's F1, its `r1_escalation.py`).
   - **Setup.** A caller's folder holds `data/ro/secret` (bytes `precious`), with `ro` made
     read-only by the host: mode `0500` on POSIX; on Windows the read-only attribute on `secret`
     (`os.chmod(p, stat.S_IREAD)`).
   - **`[home]`:** the folder is the call's root. The guest tries `os.unlink` on the file and
     gets `PermissionError`, then renames `data` into its `HOME`.
   - **`[private]`:** the folder is a writable grant at `/w` beside `root=True`. The guest tries
     the unlink, then renames `/w/data` to `/data`, into its private root.
   - **After the call:** `secret` still exists with its bytes (`[home]`: under the root's
     `tmp/.home-…/data/ro/`; `[private]`: under the left `wasi-python-root-…/data/ro/` in the
     child's temporary folder), and exactly one `RuntimeWarning` names the folder. The case
     restores the modes and deletes what is left, by name.
   - On POSIX the check skips as root (modes refuse nothing to root), saying so.
   - **Windows (the confirmation's C2, for the builder).** wasmtime 49 deletes a guest's file
     through Rust's `std::fs` (READ by the review, `filesystem/windows.rs`), which may delete a
     read-only file on Windows. The rows assert the guest's own unlink result first. If the
     guest's unlink succeeds on the Windows shard, the Windows rows skip with that reason ("a
     Windows guest deletes a read-only file itself"), the landing notes record it, and the README
     says nothing that suggests the read-only attribute protects a file from a guest. Criterion
     8's Windows row still guards the walk itself.
   - Main keeps the file (EXECUTED by the review, `r1-*-main.log`), so this guards the design,
     not a defect of main. Stand-in: Decision 4's repair as first drafted (`fchmod` to `0700`
     on `PermissionError`; on Windows `os.chmod(p, stat.S_IWRITE)`): `secret` is deleted
     (EXECUTED by the review against the first prototype, `r1-*-proto.log`).
4. **`test_a_tree_deeper_than_the_descriptor_limit_is_removed`** (unit,
   `tests/unit/test_runner_sweep.py`, no artifacts).
   - **POSIX:** the test builds a folder 1,000 levels deep with one file at each level (2,000
     entries). A child with three free descriptors calls `runner._remove_tree` on it: True, and
     the folder is gone.
   - **Counted** (in the test's own process, no limit): with `os.open`, `os.scandir`,
     `os.unlink`, `os.rmdir`, `os.chmod`, `os.fchmod`, `os.mkdir` and `os.rename` wrapped to
     count calls, a removal of the same tree makes at most 5 counted calls per entry, plus 5,
     and no `os.chmod`, `os.fchmod`, `os.mkdir` or `os.rename` call. (The prototype made 3.5
     per entry, `t_walk.out`.)
   - **Windows:** a folder 300 levels deep of `a`, one file at each level, built through `\\?\`
     paths (more than 600 characters): `_remove_tree` returns True and it is gone; the same
     counts.
   - Seen failing on main: `shutil.rmtree` leaves such a tree under a low limit (EXECUTED in
     kind: 2,000 levels at a soft limit of 64, `t_walk.out`: "left", 61 errors). Stand-ins:
     (a) and (b) of criterion 1; (c) the walk renames each folder into a holding folder
     (`proto_remove.py`'s design): the `os.rename` count is not 0.
5. **`test_the_path_walk_removes_a_deep_tree`** (unit, POSIX only: on Windows criterion 4 is this
   case). `runner._dir_fd_ok` patched to return False, so `_remove_tree` takes Decision 3's
   branch with plain absolute paths: a 300-level tree with a file at each level and a link to a
   canary folder at level 150 is removed, and the canary is intact.
6. **`test_the_removal_never_follows_a_link`** (unit). A canary folder outside the tree holds a
   file `keep`.
   - **Static links:** the tree holds a link to the canary folder, a link to `keep`, a link
     `../..`, and at depth 50 a link to the canary folder again; a second case replaces the top
     itself with a link to the canary. Each tree is removed (`_remove_tree` True; the name gone;
     in the second case the link itself is unlinked) and the canary holds `keep` with its bytes.
   - **A folder swapped for a link mid-walk** (POSIX; the review's attack B, by a hook on
     `os.open`): when the walk is about to open level 3, the test moves level 3 aside and puts a
     link to the canary in its place. `_remove_tree` returns False, the canary holds `keep`, and
     the link is left (Decision 2).
   - Windows: the static cases, wherever `os.symlink` succeeds for the test's user (GitHub's
     runners hold the privilege); where it raises `OSError` the case skips and says so.
   - Stand-in: entries classified with `is_dir()` that follows links: the canary is emptied.
7. **`test_the_walk_never_climbs_out_of_a_moved_folder`** (unit, POSIX; the review's F2, by hooks
   as in its `r2_walk_attacks.py`). A six-level tree with a file at each level, and a canary
   folder `outside/keep` beside it. Three cases, each made by a hook at an exact step:
   - a subtree (level 4) moved into `outside/` just after the walk opened it;
   - level 4 renamed up to the top just after the walk opened it;
   - level 3 moved into `outside/` while the walk is in level 4.
   In each, `_remove_tree` returns False and `outside/keep` exists with its bytes. Stand-in: the
   identity check removed (the comparison of `..` with the recorded parent made always false):
   the canary is emptied in all three (EXECUTED against the revised prototype, `r2_walk2.out`).
8. **`test_read_only_content_is_left_and_named`** (unit; criterion 6 of the first draft,
   inverted by the review's F1).
   - **POSIX:** a top holding a folder at `0500` with a file in it, a folder at `0000` holding
     a file, and an empty folder at `0000`. `_remove_tree` returns False; the `0500` folder and
     its file, and the non-empty `0000` folder, are there with their modes unchanged (each
     `stat` as before); the empty `0000` folder is gone (N1: `rmdir` by name). Through a `_Private` with the same content:
     `remove()` keeps the folder and its lock file and queues one `RuntimeWarning` naming it.
     Skipped as root, saying so.
   - **Windows:** a file with the read-only attribute in a folder: the same, and the attribute
     still set.
   - Seen failing on main in kind: `rmtree` leaves the content too, but no warning is given (the
     warning assertion fails). Stand-ins: a permission repair: the content is deleted; no
     `rmdir` before recording a folder that cannot be opened: the empty `0000` folder is left.
9. **`test_a_writer_cannot_keep_a_home_removal_going`** (unit; the review's F3 and C1).
   `runner._REMOVE_BUDGET` patched to 10,000; a hook on `os.unlink` adds a new file to the same
   folder after each unlink, up to 50,000 files.
   - **A `HOME`'s removal** (`_remove_home` on a `.home-…` folder in a caller-style folder, with
     its handle): it returns with the folder left, the counted calls (opens, listings, unlinks,
     `rmdir`s) number at most 10,000, and one warning names the folder. With the budget at its
     default and the writer stopped at 2,000 files, the folder is gone.
   - **A private folder has no budget** (C1): a `_Private` holding 12,000 files (more than the
     patched budget), no writer: `remove()` removes it whole, with more than 10,000 counted
     calls, and no warning.
   - Stand-ins: no budget on the `HOME`: the 50,000 files are all unlinked (the writer, not the
     walk, decides when it ends); the budget passed by `_Private.remove` too: the private folder
     is left.
10. **`test_what_a_removal_leaves_is_retried_by_the_next_calls_sweep`** (unit).
    - A `_Private("wasi-python-root-")` with a file in it; `runner._remove_tree` patched to fail
      once, then the real one. `remove()` returns; both the folder and its lock file are kept;
      the name is not in `_held`; after a flush, one `RuntimeWarning` names the folder;
      `_sweep_state["claimed"]` is False.
    - The next `_sweep_once()` removes both: `swept` is 1 and the temporary folder is empty.
    - **The order of the drop and the re-arm** (the review's F6): with `runner._drop` patched to
      call `_sweep_once()` before it drops the name, the folder is still removed by the next
      `_sweep_once()` after `remove()` returns.
    - **The bound:** with `_remove_tree` patched to fail always, a `remove()` followed by six
      `_sweep_once()` calls makes four `_remove_tree` calls for that name (its own and three
      sweeps), queues one warning, and leaves the sweep claimed after the third failure.
    - **The re-arm comes after the loop:** a sweep over two failing folders re-arms once, and
      `claimed` is True at every `_remove_tree` call inside it.
    - Seen failing on main: no re-arm, so the second sweep is never run (`swept` 0). Stand-ins:
      no re-arm (`swept` 0); no bound (six sweeps, seven calls); the re-arm before the drop (the
      drop-order case is not swept); the re-arm inside the loop (`claimed` False during it).
11. **`test_a_deep_dead_root_is_swept`** (unit). A dead root (a folder and its unlocked lock file
    naming this kernel, as `dead()` makes them) holding a 1,000-level tree. A child with three
    free descriptors (POSIX) calls `_sweep_once()`: `swept` is 1 and the temporary folder is
    empty. Windows: a 300-level tree built through `\\?\` paths, no limit. Seen failing on main
    (POSIX): `swept` 0, both entries left.
12. **`test_a_removal_that_raises_still_lets_go`** (unit). `runner._remove_tree` patched to raise
    `RecursionError`. `remove()` returns; the name is not in `_held`; the lock file is kept and a
    second descriptor on it can take the lock (`_try_lock` True: the first was closed). Seen
    failing on main in kind: `shutil.rmtree` patched to raise `RecursionError` makes `remove()`
    raise, with the name still held. Stand-in: the `finally` dropped: the name stays held.
13. **`test_a_warning_filter_never_makes_the_call_raise`** (unit). Under
    `warnings.simplefilter("error")`, a `_Private` whose removal fails, then `_flush_warnings()`:
    neither raises, and the folder and its lock file are kept for the sweep. Stand-in: the
    warning unguarded: the flush raises `RuntimeWarning`.
14. **`test_the_warning_is_given_outside_every_runner_lock`** (unit; the review's F6). A
    `warnings.showwarning` replaced by a function that records, for each warning, whether
    `runner._lock`, `runner._zip_lock` and `runner._held_lock` can each be taken without
    blocking (`acquire(blocking=False)`, then released), and calls `wasi_python.stats()`.
    - A private folder whose removal fails inside `_zip_folder`'s re-make path (the zip folder's
      `_Private` with `_remove_tree` patched to fail, its folder deleted so `_zip_folder` makes
      it again under `_zip_lock`), then a `run` of `print(1)`: the warning is given once, after
      the lock was released (every `acquire` succeeded), and `stats()` returned.
    - Stand-in: `warnings.warn` called inside `_Private.remove`: the record shows `_zip_lock`
      held (a non-blocking `acquire` from the same thread fails, since the lock is not
      re-entrant).
15. **The restated check** (Decision 9) passes with its new body, gives one `RuntimeWarning`, and
    fails if `_Private.remove` unlinks the lock file while the folder exists.
16. **CPython 3.11** (the review's F8). No release job runs 3.11 (`UV_PYTHON` is 3.14.2). The
    builder runs criteria 1 and 4 once under CPython 3.11 on darwin (a scratch environment, as
    `p311.py` did) and records the result in the landing notes: both pass, and no
    `RecursionError` at 1,500 levels under a soft limit of 8,192 with the built code.
17. **Windows.** The release's dry run on the built branch passes every job on all three
    systems, and its `own-runner` and `own-embedding` shards on `windows-2025` show these nodes
    `PASSED`: criteria 1, 2 and 3 (both rows each), 4, 8 to 15; criterion 6's static cases
    `PASSED` (GitHub's runners can make links) or skipped with their reason. Criteria 5 and 7,
    and criterion 6's swap case, are POSIX only by their nature. (If the job's output does not list nodes, the builder uses spec 077's
    throwaway `-rA` branch, Decision 5 there.) A stray `RuntimeWarning` in criterion 1's "no
    warning" assertion on Windows points first at a scanner holding a file (the review, §3).
18. **The judge.** The fast tier and one full run, `-n 3`, against main's set: no failure, no
    lost pass, no growth; the ratchet's only moves are the new checks' gains and the judge
    change. `ruff check` and `ruff format --check` clean on `src/` and `tests/`.
19. **The docs.**
    - The README's *Safety* and *Not protected* say: a private root and a fresh `HOME` are
      removed whatever the guest built, holding two descriptors and creating nothing; the
      removal never changes a mode or an attribute, so content the host made read-only is left,
      even if the guest moved it into its folder; a folder a removal could not remove (such
      content, a file another program holds open on Windows, a full descriptor table, a writer
      past the budget) keeps its lock file, is named in a `RuntimeWarning` and is retried by the
      next call's sweep, up to three times per process, then by the next process; a `HOME` left
      in the caller's own folder is warned about and not retried; a concurrent call on the same
      root can hold another call's `HOME` removal for up to about a million system calls (about
      50 s on an arm64 Mac, given as a benchmark fact), and a `HOME` past that is left and
      named, while a private folder has no such limit; and
      Windows guests can make links where the user holds the symbolic-link privilege (no
      sentence says they cannot).
    - The CHANGELOG's 0.1.0a8 section has two **Fixed** entries: the private root and `HOME`
      that a deep tree left behind (the 0.1.0a7 security review's F1); and, separately, "on
      CPython 3.11 a guest could make `run` raise `RecursionError` and keep its lock for the
      process's life" (found by this spec's research; the lane may add a one-line addendum to the
      0.1.0a7 security review, as the review proposes).

## Judge changes

- **New checks**, a judge change: criteria 1 to 3 in `tests/checks/test_v1_4_embedding.py`
  (goal v1.4, six nodes) and criteria 4 to 14 in `tests/unit/test_runner_sweep.py` (the unit
  suite). They record no fuel and no bytes; each counts entries, descriptors or calls.
- **One restated check** (Decision 9): its name kept, its body patching `runner._remove_tree`,
  and one warning asserted.
- **Nothing else.** No golden output, no `tests/known_gaps.toml` entry, no upstream allowance, no
  `tests/release_shards.toml` change (both files are already in shards on all three systems), no
  `tests/public_api.txt` line.
- **For the lane:** `--accept-judge "spec 084: a private root and a fresh HOME are removed by a
  walk that holds two descriptors, changes no mode and has a budget; new checks for deep, linked,
  moved and read-only trees, a writer, the sweep's retry and the warning; one sweep check
  restated to fail the removal through _remove_tree"`. No `--accept-growth` is expected: the
  runner's change is host-side and adds no guest fuel.

## Disposition of the pre-build review

The review (verdict "ready once F1 to F3 are written in") and the lane's instructions, finding by
finding:

- **F1 (high).** Taken. Decision 4 now forbids any permission repair, on POSIX and Windows;
  Decision 3's read-only bullet says the attribute is never cleared. Criterion 6 of the draft is
  inverted as criterion 8; the review's case is criterion 3, both rows. Measured as asked
  (EXECUTED, `p_guest_modes.out`): a guest cannot make a folder or file unwritable or unreadable
  through preview1 and wasmtime (its `mkdir` modes, `O_CREAT` modes and `os.chmod` have no
  effect on the host's modes), so dropping the repair costs nothing for what a guest makes;
  host-made read-only content is left, warned about and retried. The revised walk keeps the
  protected file in both of the review's cases (EXECUTED, `r1_escalation_walk2.out`).
- **F2 (medium).** Taken: criterion 7, the three attacks by hook, with "identity check removed"
  as its stand-in (EXECUTED against the revised prototype: the canary is emptied in all three
  without the check, kept with it, `r2_walk2.out`).
- **F3 (medium).** Taken as a bound, not a named hang: Decision 12, a budget of 2**20 counted
  calls per removal (the `HOME` removals only, after the confirmation's C1), and criterion 9 (EXECUTED, `t_writer.out`). Decision 12 says why a budget
  rather than a cap on listings per visit. The README names the residual (a concurrent call can
  hold another call's `HOME` removal for up to that many calls).
- **F4 (low).** Gone with F1: no chmod remains, by name or by descriptor.
- **F5 (low).** Taken as the lane asks: Decision 2 now says a folder swapped for a link mid-walk
  is left and the removal returns False; criterion 6 adds the swap by hook.
- **F6 (low).** Taken, all three: the name is dropped before the re-arm (Decision 5, the Design,
  criterion 10's drop-order case); the sweep re-arms after its loop (Decision 5, criterion 10);
  the warning is queued and given outside every runner lock, including 078's home lock
  (Decision 7, Decision 11's 078 entry, criterion 14).
- **F7 (low).** Taken: criterion 2 is `[run]` and `[session]`; the session row reaches
  `_remove_home`.
- **F8 (low).** Taken: the problem statement gives the review's 3.11 run at a soft limit of
  1,024 (990 levels removed, 1,010 raise); the CHANGELOG gets its own **Fixed** bullet
  (criterion 19); the builder records one 3.11 run of criteria 1 and 4 (criterion 16; criterion
  4 is the draft's criterion 3, renumbered).
- **F9 (nit).** Taken, all four: "another device" with the bind-mount sentence (Decision 2);
  "creates and renames nothing", with the copy-on-write case (Decision 2); Decision 8's claim
  limited to POSIX; Windows guests can make links with the symbolic-link privilege, and the
  runner's two comments that say otherwise are corrected (Decision 3, the Design, criterion 19).
- **F10 (nit).** Taken: Decision 11 names 073.
- **The restated check.** Wrapped in `pytest.warns(RuntimeWarning)` (Decision 9, criterion 15).
- **The review's builder notes.** Trees deeper than about 500 levels are built through `dir_fd`,
  and "three free descriptors" counts the holes (the criteria's preamble); the walk calls no
  `unlink` on an empty top (Decision 2).
- **The owner's points stand:** a warning, not a `stats()` key (Decision 7); a retry bound of
  three (Decision 5). The review agrees with both.

**The confirmation (2026-10-19, "confirmed once C1 is written in"):**

- **C1.** Taken, the first of the review's two fixes: the budget applies to the two `HOME`
  removals only (Decision 12, the Design, Decision 1's form); `_Private.remove` and
  `_sweep_entry` pass none, so the Intent's promise holds for a private folder of any size.
  Decision 12 says why no private folder has a writer (the guest ended, the store closed, a
  random `0700` name no field carries, no grant reaching the temporary folder, the lock for a
  dead root) and that I found no case where one does. Criterion 9 adds a private-folder row
  with no budget, and a stand-in that passes the budget there. The README gives "about a million
  calls is roughly 50 s on an arm64 Mac" as a benchmark fact (criterion 19), from the review's
  `r7_entry_rate.log`.
- **C2.** Written in for the builder (criterion 3's Windows bullet): the rows check the guest's
  own unlink first, and skip with the reason if a Windows guest deletes a read-only file itself.
- **N1.** Taken: a folder the walk cannot open is tried once with `rmdir` by name before it is
  recorded as failed (Decision 2); criterion 8's empty `0000` folder is now removed, with a
  stand-in.

The criteria are renumbered: the draft's 1 and 2 keep their numbers; 3 is new (F1); the draft's
3, 4 and 5 are 4, 5 and 6; 7 is new (F2); the draft's 6, inverted, is 8; 9 is new (F3); the
draft's 7 to 11 are 10, 11, 12, 13 and 15; 14 (F6) and 16 (F8) are new; the draft's 12 to 14 are
17 to 19.

## Landing notes

### What was built

On `spec/084-a-private-root-never-outlives-its-call`, rebased onto main `9d89535` (065 landed):
the draft and its two revisions (`cf23d50`, `c2f5ee7`, `2a9708d`), then `0cefbc0` (the checks
and the code), `e4d418f` (README, CHANGELOG, and the retry check strengthened), then these notes.
Every guest run used a private `cp -Rp` copy of `build/sets/s-c50ca51fae5eb55b-c9dcb5b8`
(`SHA256SUMS` identical, the zip's link count 1).

- `src/wasi_python/runner.py`: `_remove_tree` and its two walks (`_remove_at` by descriptors,
  `_remove_by_path` by extended-length paths), `_Removal` (the count, the budget, the first
  error), `_enter`, `_listing`, `_is_folder`, `_long_path`; `_Private.remove` (guarded, the drop
  in a `finally`, then the queued warning and the re-arm); `_sweep_once` (re-arms after its loop)
  and `_sweep_entry` (the walk, the per-name count, the bound `_SWEEP_TRIES = 3`);
  `_remove_fresh_home` (budgeted) used by `_call_deferred` and `_remove_home`; `_warn_later` and
  `_flush_warnings`; `_run_checked_flushed`; the two comments on Windows links.
- `tests/unit/test_runner_sweep.py`: criteria 4 to 15 (the fixture `temp` also resets the new
  state); `tests/checks/test_v1_4_embedding.py`: criteria 1 to 3.

### Seen failing first (EXECUTED, `build/084-checks-on-main.log` in the worktree)

The new checks against main's code: 23 failed, 26 passed (the passes are the file's existing
cases). By behaviour: criterion 1 (both rows: the root and its lock file left), criterion 2
(both rows: `.home-…` left), criterion 3 (both rows: the file kept, but no warning), criterion
11 (`swept` 0 under three free descriptors), the restated check (did not warn). The rest by
`AttributeError` on `_remove_tree` or `_flush_warnings`.

### The stand-ins (EXECUTED, `build/084-standins.log`, `build/084-standins-c10.log`)

Each mutant applied to `runner.py`, its checks run, the file restored from the saved text:

| stand-in | checks that failed |
|---|---|
| `_remove_tree` replaced by `shutil.rmtree` (criterion 1 (a)) | criteria 1 (2 rows), 2 (2 rows), 4, 11 |
| a descriptor kept per level (criterion 1 (b)) | criteria 1 (2 rows), 4 |
| the `HOME` in `_call_deferred` on `rmtree` | criterion 2 `[run]` |
| `_remove_home` on `rmtree` | criterion 2 `[session]` |
| the permission repair (`fchmod` on `PermissionError`) | criteria 3 (both rows), 8 |
| no `rmdir` before recording an unopenable folder (N1) | criterion 8 |
| `is_dir()` that follows links | criteria 5, 6 |
| the identity check removed | criterion 7 (all three rows) |
| no budget on the `HOME` | criterion 9 |
| the budget on private folders too | criterion 9 |
| no re-arm | criterion 10 (two functions) |
| no bound (`_SWEEP_TRIES` = 10**9) | criterion 10 (the bound) |
| the re-arm before the drop | criterion 10 (the drop order) |
| the re-arm inside the sweep's loop | criterion 10 (the bound) |
| the guard in `remove` dropped | criterion 12 |
| the flush unguarded | criterion 13 |
| the warning given inside `remove` | criterion 14 |
| the lock file unlinked while the folder exists | criterion 15 |

The first run of the stand-ins found two that did not bite: "no re-arm" passed criterion 10's
first function, since the fixture leaves the sweep unclaimed (the function now claims it first,
`e4d418f`); and the first "re-arm before the drop" mutant kept the later re-arm too (the
mutant was wrong, not the check). Both are fixed in the logs above.

### The counted calls (EXECUTED, `b_counts.out`)

| tree | entries | counted calls (open, listing, unlink, rmdir) | per entry | peak descriptors |
|---|---|---|---|---|
| 1,000 levels, a file at each (criteria 4 and 11) | 2,000 | 7,003 (2,001 opens, 3,001 listings, 1,000 unlinks, 1,001 `rmdir`s) | 3.50 | 2 |
| 5,000 files and 300 folders in one folder | 5,300 | 6,504 | 1.23 | 2 |

No `chmod`, `fchmod`, `mkdir` or `rename` in either. Criterion 4's bound is 5 per entry plus 5
(10,005 for its tree). The same tree is removed in a child left exactly three free descriptors.

### Criterion 16: CPython 3.11 (EXECUTED, `build/084-py311.log`)

In a scratch environment (`UV_PROJECT_ENVIRONMENT` in the scratchpad, `uv run --frozen --python
3.11`, CPython 3.11.14), against the same set: criteria 1 (both rows) and 4 passed, 3 of 3.
`p311.py` at a soft limit of 8,192 and 1,500 levels, which made main's `run` raise
`RecursionError`, now returns exit 0 and leaves no root.

### The judge

Against the private copy of main's set, in the worktree (no build; the upstream groups and the
rebuild checks need source trees a build makes, so they are blocked here):
- fast tier (`uv run pytest -m "not slow" -n 3`, on `e4d418f`'s code with the docs then
  uncommitted, `build/fast-084-build.log`): `484/629 pass · 1 gap · 25 blocked · 0 fail · 119 deselected (unit suite
  1595/1603, 8 skipped)`; `2079 passed, 33 skipped, 1 xfailed`; `ratchet vs b91e0eaa4e: lost 0 ·
  absent 0 · unrun 0 · unrun locally 23 · gained 6 · grew 0 · upstream unrun 99 · not selected 43
  · judge changed: tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_sweep.py`;
- full (`uv run pytest -n 3`, on `e4d418f`, `build/full-084-build.log`): `501/629 pass · 3 gap · 125 blocked · 0 fail (unit suite 1595/1603, 8
  skipped)`; `2096 passed, 133 skipped, 3 xfailed`; `ratchet vs b91e0eaa4e: lost 0 · absent 0 ·
  unrun 0 · unrun locally 49 · gained 6 · grew 0 · upstream unrun 99 · judge changed:
  tests/checks/test_v1_4_embedding.py, tests/unit/test_runner_sweep.py`. The 6 gained are the six
  new embedding nodes; the 125 blocked are the upstream groups and rebuild checks this worktree
  has no source trees for.

`build/progress/latest.json` is kept in the worktree for the lane.

### Departures from the specification

- **Criterion 14** holds `runner._zip_lock` around `remove()` itself, as `_zip_folder` does,
  rather than driving `_zip_folder`'s re-make path and a `run`: the same lock, the same queue,
  with no artifacts. The flush as `run` returns is covered by criterion 3, whose child records
  the warning around `run` without flushing itself.
- **The flush points.** `run` and `run_async` (both through `_run_checked_flushed`), the
  `Session` constructor (around `_open_session`), the end of `_end_session` (close, idle,
  lifetime, a turn that ends the session, the exit hook's ending) and the exit hook `_release`.
  Not `Session.run` itself: a turn that does not end its session removes nothing and runs no
  sweep, so it queues nothing; one that ends it flushes in `_end_session`.
- **`_remove_tree` takes `errors=`**, a list it appends its first error to, for the warning's
  text: beyond the spec's form, private.
- **Criteria 6 and 10 are several functions.** Criterion 6: `test_the_removal_never_follows_a_link`
  (static) and `test_a_folder_swapped_for_a_link_mid_walk_is_left` (the swap, POSIX). Criterion
  10: `test_what_a_removal_leaves_is_retried_by_the_next_calls_sweep`,
  `test_the_name_is_dropped_before_the_sweep_is_re_armed` and
  `test_a_folder_is_retried_by_at_most_three_sweeps` (which also asserts the re-arm after the
  loop). The judge counts 16 new unit nodes and 6 new embedding nodes.
- **Criterion 4's stand-in (c)** (the rename design) was not written as a mutant: the check's
  `os.rename` count of 0 is what it would fail.
- **Criterion 9's `HOME` rows** call `_remove_home` on a caller-style folder with a handle, as a
  session's release does, not through a `run`.
- **The path walk's top** is also treated as a link when `lstat` shows a reparse point
  (Windows), so a junction in a folder's place is unlinked, never entered.
- **Windows is not run here.** Criteria 1 to 4, 6, 8 and 9 to 15 have Windows legs; criterion
  17 is the lane's dry run. C2 (whether a Windows guest deletes a read-only file itself) is
  settled there: criterion 3's Windows rows skip with that reason if it does.

### For the lane

- `--accept-judge "spec 084: a private root and a fresh HOME are removed by a walk that holds
  two descriptors, changes no mode, and (for a HOME) has a budget; new checks for deep, linked,
  moved and read-only trees, a writer, the sweep's retry and the warning; one sweep check
  restated to fail the removal through _remove_tree"`. No `--accept-growth`: nothing grew.
- The Windows dry run (criterion 17), with the named nodes `PASSED` on `windows-2025`.
- The pre-build review is in the lane's scratchpad, to be copied to `../reviews/`.
