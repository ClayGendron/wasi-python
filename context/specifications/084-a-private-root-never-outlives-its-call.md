# 084 — A private root never outlives its call

- **Status:** drafted 2026-10-19 on `spec/084-a-private-root-never-outlives-its-call` from main
  `a6dfc17`. It changes neither the guest's imports nor its exports, the artifact set nor the
  build recipe, so §5.6 asks no review before build. It closes a finding of a release's security
  review with a new failure path, so the lane may ask for one. A different agent reviews the
  build. Due before 0.1.0 final (the 0.1.0a7 security review, F1).
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** the runner, the judge and docs; **parallel-safe**, not build-class (§5.7). The code:
  `src/wasi_python/runner.py` only (`_Private.remove`, `_sweep_once`, `_sweep_entry`, the fresh
  `HOME`'s removal in `_call_deferred` and `_remove_home`, and one new private function,
  `_remove_tree`). The checks: `tests/unit/test_runner_sweep.py` (new cases, and one case's
  body restated, Decision 9) and `tests/checks/test_v1_4_embedding.py` (two new checks). The
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
  recurses. Below the descriptor limit it fails as above (256 and 400: left). Above it, a tree
  of 1,500 levels at a soft limit of 8,192 makes **`run` raise `RecursionError`**, out of
  `_Private.remove` (EXECUTED, `p311.log`: the traceback runs `run`, `_run_checked`, `remove`,
  `rmtree`, `_rmtree_safe_fd` ×995). `remove` then never reaches `_unlock_close` or `_drop`, so
  the lock stays held and the name stays in `_held` for the process's life, and no sweep of this
  process ever tries it (READ, `runner.py`). 3.12.12 and 3.14.2 do not raise (`p312.log`,
  `m-more.log`).
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
   - Its form: `_remove_tree(path, *, dir_fd=None) -> bool`. With `dir_fd`, `path` is a name in
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
   - **How it lists.** It reads a folder with `os.scandir(fd)` lazily. It unlinks each entry that
     is not a folder as it reads, and stops at the first folder, closing the listing before it
     descends. After climbing back it lists the folder again. Every entry read is removed or
     recorded as failed, so a folder's entries are read about once. A listing that removes
     nothing and finds no folder to enter ends that folder.
   - **Links are never followed.** An entry is a folder only if `DirEntry.is_dir(follow_symlinks=
     False)` says so. A link, to anything, is unlinked like a file. A folder swapped for a link
     between the listing and the open fails the `O_NOFOLLOW` open and is unlinked on the next
     listing.
   - **One filesystem.** A folder whose `st_dev` differs from the top's is never entered; it is
     left and the removal fails. A guest cannot mount anything; only the host could put one
     there.
   - **The top.** `lstat` first. A name that is no longer a folder (a link or a file in its
     place) is unlinked, never followed: the runner made that name, and it is the runner's to
     remove. A folder is opened with `O_NOFOLLOW` and checked against the `lstat` by
     `(st_dev, st_ino)`, as `_sweep_entry` already checks the lock file.
   - **It makes and renames nothing.** So it needs no free disk space (the third alternative below
     says why that matters).
   - **Descriptors.** The folder it is in, plus one: the next folder down, `..`, or the
     listing's dup. At most two at once, three with the parent handle a `dir_fd` call already
     holds. The check gives it three free and no more (criterion 3).
   - **Why not the alternatives.**
     - `shutil.rmtree`: one descriptor per level (READ; EXECUTED above), and on 3.11 one Python
       frame per level, which raises.
     - `os.fwalk`, bounded or not: it keeps each level's descriptor on its stack until that
       level is done (READ), so the same failure.
     - **Renaming each deep folder up into a holding folder**, so the tree becomes wide and each
       piece is removed at depth two (the review's first suggestion): it works, at four
       descriptors (EXECUTED, `proto_remove.py`, `t_proto.out`), but it must make a folder and
       add entries. A guest can fill the disk before it ends ("tens of GiB in the default 60
       s"). On a full 8 MiB volume the rename design failed at its first `mkdir` with `ENOSPC`,
       and the walk removed the same 300-level tree (EXECUTED, `t_full.out`).
     - **`rmtree` first, the walk only on `EMFILE`** (the review's second suggestion): two code
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
   - **The read-only attribute.** A delete refused with `PermissionError` clears the attribute
     once for that entry (`os.chmod(path, stat.S_IWRITE)`) and tries once more. A guest cannot
     set it (no preview1 call does); an embedder's tool or another program can.
   - **Open handles.** The call's own handles are closed before the removal: the store, and every
     walked folder (Windows holds them until then, `_run_checked`'s `finally`). A file another
     program holds open without delete sharing (an antivirus scanner, the search indexer) makes
     the removal fail. That folder is retried (Decision 5).

4. **A folder the user made unwritable is made writable, once.** On POSIX a removal refused with
   `PermissionError` (`EACCES` or `EPERM`) inside a folder makes that folder `0700` once, through
   its descriptor (`os.fchmod`), and tries again. A folder it cannot open at all (mode `0000`)
   is made `0700` by name: with `follow_symlinks=False` where `os.chmod in
   os.supports_follow_symlinks` (macOS), else after the `lstat` that saw a folder (Linux; nothing
   writes a dead root, so the name cannot change in between). A guest cannot change permissions
   (preview1 has no such call, READ), so this guards folders the host changed: an embedder's
   tool, or a umask. It costs nothing when nothing is refused. As root (`euid` 0) modes do not
   refuse, so the case does not arise.

5. **What a removal leaves is retried by the next call's sweep.**
   - **The call's own removal.** When `_remove_tree` leaves the folder, `_Private.remove` keeps
     the lock file (as today), unlocks and closes it, drops the name from `_held`, and **re-arms
     this process's sweep**: `_sweep_state["claimed"]` goes back to False, under `_lock`. The
     next call's `_sweep_once` then lists the temporary folder again and finds that folder like
     a dead process's: unlocked, this kernel's, not held. It removes it with the same walk.
   - **The bound.** `_sweep_state` keeps a count of failed attempts per name. A sweep that fails
     to remove a folder re-arms only while that name has failed fewer than three sweeps in this
     process. So a folder that cannot be removed (a file held open for good) costs this process
     its own removal and at most three more sweeps, then waits for the next process's first
     call. A dead process's folder is retried the same way: at most three re-armed sweeps.
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
   - **Why a warning.** The review found the call "reports nothing". A warning is Python's way to
     tell a host about trouble that did not stop the call, and the runner already uses one for a
     module cache it refuses (`_private`).
   - **Why not a field or a `stats()` key.** A field in `Completed` reports the guest's call, and
     the folder's removal comes after the guest; a key would change the frozen public API
     (spec 049) for a diagnostic the warning already gives. Neither is needed to close F1.

8. **A live call is never raced.** The rules that keep a sweep off a live call's folder stand:
   the owning call removes its folder after its store and its walked handles are closed, holding
   its lock; a sweep removes only a folder whose lock it took, of this kernel, not a name this
   process holds; a session removes its folders at its release, after its store. The walk adds
   its identity checks, so even a folder moved during the walk (only a host process of the same
   user could) cannot lead it outside the tree.

9. **One existing check is restated, not weakened.** `test_a_folder_rmtree_could_not_remove_keeps
   _its_lock_file` makes the removal fail by replacing `shutil.rmtree`, which the runner no
   longer calls for its folders. It replaces `runner._remove_tree` with one that returns False
   instead, and asserts what it asserted: both entries kept, then one sweep removes both. Its
   name is kept, so the ratchet sees the same pass. The judge-hash line shows the file.

10. **Where the checks run.** `tests/unit/test_runner_sweep.py` is in the release's `own-runner`
    shard and `tests/checks/test_v1_4_embedding.py` in `own-embedding`, each on macOS, Linux and
    Windows (`tests/release_shards.toml`). On POSIX the deep cases set `RLIMIT_NOFILE` in a child
    process, so they count descriptors and entries and time nothing. Windows has no
    `RLIMIT_NOFILE`, and its removal never held a handle per level; there the deep cases build
    trees whose host paths pass 260 characters, the limit the old removal met there. Criterion 12
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
      its store closes, not on the caller's; that is 078's ordering to keep. Whichever lands
      second rebases the `finally` blocks textually.
    - **083 (the judge's driver, confirmed for build).** The driver removes its run folders with
      `shutil.rmtree(ignore_errors=True)`. 084's checks call `wasi_python.run` and `Session` in
      child processes with temporary folders of their own, never the driver, so they neither
      depend on 083 nor leave anything in its folders. The driver may call `runner._remove_tree`
      once 084 lands; that is not in this scope.
    - **068 (the open-file cap).** The store closes before the clean-up, so the walk's two
      descriptors are there unless other calls hold the whole table. Then the removal fails, the
      folder keeps its lock file, and the next sweep retries it.

## Intent

A folder the runner makes for a call is gone when the call returns, whatever the guest built in
it: deep, wide, full of links. If something outside the guest stops that (a file another program
holds open, a full descriptor table), the folder keeps its lock file, the embedder gets one
warning, and the next call retries it. The removal holds two descriptors whatever the depth, and
needs no free disk space.

## Design

- **`_remove_tree(path, *, dir_fd=None) -> bool`** (`runner.py`, beside `_Private`). POSIX
  (`_dir_fd_ok()` true): Decision 2's walk, through descriptors. Elsewhere: Decision 3's walk,
  through extended-length paths (the `\\?\` prefix only on Windows; the same code with plain
  absolute paths when a test forces this branch on POSIX). Both: Decision 4's permission repair,
  the identity check at the top, `False` on any failure, `True` when the name is gone.
- **`_Private.remove`**: `gone = _remove_tree(self.path)` guarded (Decision 6); unlock and close;
  the lock file unlinked only if the folder is gone (as today); else `_left(self.path, error)`:
  warn once (Decision 7) and re-arm the sweep (Decision 5); `_drop(self.name)` in a `finally`.
- **`_sweep_once`**: claims as today. **`_sweep_entry`**: `_remove_tree(path)` in place of
  `rmtree`; on failure, the per-name count, the warning, and the re-arm while the count is below
  three. A name at its bound is skipped by later sweeps of this process.
- **The `HOME`**: `_remove_tree(name, dir_fd=tmp_fd)` where there is a handle, else
  `_remove_tree(tmp / name)`; on failure, the warning only.
- **State**: `_sweep_state` gains `"failed": dict[str, int]` (names to failed sweeps) beside
  `"claimed"` and `"swept"`, and the warned names live in a set beside it, all under `_lock` or
  `_held_lock` as the existing fields are. They grow only with failures.

## Scope

In: Decisions 1 to 11; the README's *Safety* and *Not protected* sentences on the private root,
the `HOME` and what a removal leaves; a CHANGELOG entry under 0.1.0a8.

Out, each with its reason:
- **A bound on depth or on entries.** 072's work for paths; disk use inside a call stays as
  *Not protected* says, bounded by the call's deadline, but no longer adds up across calls.
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
checks run. "Three free descriptors" means the child sets its soft `RLIMIT_NOFILE` so that
exactly three descriptor numbers below it are unused, after its imports.

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
     with these parameters, `m-check-params.log`). On Windows it guards the long-path case and
     may pass on main.
   - Stand-ins: (a) `_remove_tree` replaced by `shutil.rmtree(…, ignore_errors=True)` and
     `True`: the root is left; (b) the walk keeps each level's descriptor open until it climbs:
     the root is left.
2. **`test_a_deep_fresh_home_is_removed`** (`tests/checks/test_v1_4_embedding.py`, artifacts). In
   a child at a soft limit of 128, a guest given a caller's root builds 256 levels under its
   `HOME`. Afterwards the root's `tmp` holds no `.home-*` entry, and no warning was raised.
   Windows: 120 levels of a ten-character name, no limit. Seen failing on main (POSIX): `.home-…`
   is left (EXECUTED, `p_home.out`). Stand-in: the `HOME` removal left on `shutil.rmtree`: the
   `.home-…` entry is left.
3. **`test_a_tree_deeper_than_the_descriptor_limit_is_removed`** (unit,
   `tests/unit/test_runner_sweep.py`, no artifacts).
   - **POSIX:** the test builds a folder 1,000 levels deep with one file at each level (2,000
     entries). A child with three free descriptors calls `runner._remove_tree` on it: True, and
     the folder is gone.
   - **Counted** (in the test's own process, no limit): with `os.open`, `os.scandir`,
     `os.unlink`, `os.rmdir`, `os.chmod`, `os.fchmod`, `os.mkdir` and `os.rename` wrapped to
     count calls, a removal of the same tree makes at most 5 counted calls per entry, plus 5,
     and no `os.mkdir` or `os.rename` call. (The prototype made 3.5 per entry, `t_walk.out`.)
   - **Windows:** a folder 300 levels deep of `a`, one file at each level, built through `\\?\`
     paths (more than 600 characters): `_remove_tree` returns True and it is gone; the same
     counts.
   - Seen failing on main: `shutil.rmtree` leaves the 1,000-level tree under three free
     descriptors (EXECUTED in kind: 2,000 levels at a soft limit of 64, `t_walk.out`: "left", 61 errors). Stand-ins:
     (a) and (b) of criterion 1; (c) the walk renames each folder into a holding folder
     (`proto_remove.py`'s design): the `os.rename` count is not 0.
4. **`test_the_path_walk_removes_a_deep_tree`** (unit, POSIX only: on Windows criterion 3 is this
   case). `runner._dir_fd_ok` patched to return False, so `_remove_tree` takes Decision 3's
   branch with plain absolute paths: a 300-level tree with a file at each level and a link to a
   canary folder at level 150 is removed, and the canary is intact.
5. **`test_the_removal_never_follows_a_link`** (unit). A canary folder outside the tree holds a
   file `keep`. The tree holds a link to the canary folder, a link to `keep`, a link `../..`, and
   at depth 50 a link to the canary folder again; a second case replaces the top itself with a
   link to the canary.
   - Each tree is removed (`_remove_tree` True; the name gone; in the second case the link
     itself is unlinked) and the canary holds `keep` with its bytes.
   - Windows: the same, wherever `os.symlink` succeeds for the test's user; where it raises
     `OSError` (no privilege to make links) the case skips and says so.
   - Stand-in: entries classified with `is_dir()` that follows links: the canary is emptied.
6. **`test_the_removal_makes_a_read_only_folder_writable`** (unit).
   - **POSIX:** a top at `0500` holding a folder at `0500` with a file and a sub-folder at
     `0500` with a file, and an empty folder at `0000`: all removed. Skipped as root (modes
     refuse nothing), saying so.
   - **Windows:** a file and a folder with the read-only attribute (`os.chmod(p, stat.S_IREAD)`),
     the folder holding a read-only file: all removed.
   - Seen failing on main: `shutil.rmtree` leaves the POSIX tree (EACCES). Stand-in: no
     permission repair: `_remove_tree` returns False and the tree is left.
7. **`test_what_a_removal_leaves_is_retried_by_the_next_calls_sweep`** (unit).
   - A `_Private("wasi-python-root-")` with a file in it; `runner._remove_tree` patched to fail
     once, then the real one. `remove()` returns; both the folder and its lock file are kept; the
     name is not in `_held`; one `RuntimeWarning` names the folder; `_sweep_state["claimed"]` is
     False.
   - The next `_sweep_once()` removes both: `swept` is 1 and the temporary folder is empty.
   - **The bound:** with `_remove_tree` patched to fail always, a `remove()` followed by six
     `_sweep_once()` calls makes four `_remove_tree` calls for that name (its own and three
     sweeps), warns once, and leaves the sweep claimed after the third failure.
   - Seen failing on main: no re-arm, so the second sweep is never run (`swept` 0). Stand-ins:
     no re-arm (`swept` 0); no bound (six sweeps, seven calls).
8. **`test_a_deep_dead_root_is_swept`** (unit). A dead root (a folder and its unlocked lock file
   naming this kernel, as `dead()` makes them) holding a 1,000-level tree. A child with three
   free descriptors (POSIX) calls `_sweep_once()`: `swept` is 1 and the temporary folder is
   empty. Windows: a 300-level tree built through `\\?\` paths, no limit. Seen failing on main
   (POSIX): `swept` 0, both entries left.
9. **`test_a_removal_that_raises_still_lets_go`** (unit). `runner._remove_tree` patched to raise
   `RecursionError`. `remove()` returns; the name is not in `_held`; the lock file is kept and a
   second descriptor on it can take the lock (`_try_lock` True: the first was closed).
   Seen failing on main in kind: `shutil.rmtree` patched to raise `RecursionError` makes
   `remove()` raise, with the name still held. Stand-in: the `finally` dropped: the name stays
   held.
10. **`test_a_warning_filter_never_makes_the_call_raise`** (unit). Under
    `warnings.simplefilter("error")`, a `_Private` whose removal fails: `remove()` returns, and
    the folder and its lock file are kept for the sweep. Stand-in: the warning unguarded:
    `remove()` raises `RuntimeWarning`.
11. **The restated check** (Decision 9) passes with its new body, and fails if `_Private.remove`
    unlinks the lock file while the folder exists.
12. **Windows.** The release's dry run on the built branch passes every job on all three
    systems, and its `own-runner` and `own-embedding` shards on `windows-2025` show these nodes
    `PASSED`: criteria 1 (both), 2, 3, 6 and 7 to 11; criterion 5 `PASSED` or skipped with its
    reason; criterion 4 is POSIX only by its nature. (If the job's output does not list nodes,
    the builder uses spec 077's throwaway `-rA` branch, Decision 5 there.)
13. **The judge.** The fast tier and one full run, `-n 3`, against main's set: no failure, no
    lost pass, no growth; the ratchet's only moves are the new checks' gains and the judge
    change. `ruff check` and `ruff format --check` clean on `src/` and `tests/`.
14. **The docs.** The README's *Safety* and *Not protected* say that a private root and a fresh
    `HOME` are removed whatever the guest built, with two descriptors and no free space; that a
    folder a removal could not remove (a file another program holds open on Windows, a full
    descriptor table) keeps its lock file, is named in a `RuntimeWarning` and is retried by the
    next call's sweep, up to three times per process, then by the next process; and that a
    `HOME` left in the caller's own folder is warned about and not retried. The CHANGELOG's
    0.1.0a8 section has a **Fixed** entry naming the 0.1.0a7 security review's F1, the 3.11
    `RecursionError`, and the `HOME`.

## Judge changes

- **New checks**, a judge change: criteria 1 and 2 in `tests/checks/test_v1_4_embedding.py`
  (goal v1.4) and criteria 3 to 10 in `tests/unit/test_runner_sweep.py` (the unit suite). They
  record no fuel and no bytes; each counts entries, descriptors or calls.
- **One restated check** (Decision 9): its name kept, its body patching `runner._remove_tree`.
- **Nothing else.** No golden output, no `tests/known_gaps.toml` entry, no upstream allowance, no
  `tests/release_shards.toml` change (both files are already in shards on all three systems), no
  `tests/public_api.txt` line.
- **For the lane:** `--accept-judge "spec 084: a private root and a fresh HOME are removed by a
  walk that holds two descriptors; new checks for deep, linked and read-only trees and the
  sweep's retry; one sweep check restated to fail the removal through _remove_tree"`. No
  `--accept-growth` is expected: the runner's change is host-side and adds no guest fuel.

## Landing notes

Not built yet.
