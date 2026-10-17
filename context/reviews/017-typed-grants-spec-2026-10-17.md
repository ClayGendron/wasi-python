# Review of 017 — Typed grants (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the specification. I read
  `AGENTS.md`, the constitution (§4.4, §4.9, §4.10, §4.15 with its alpha exception, §5.2),
  `context/reviews/README.md`, and the 015 pre-build review (for the format). I read the
  specification, the research memo `2026-10-17-typed-grants.md` (all of it, 7b closely), and
  spec 016 as it now stands ("ready to build"). In the runner I read `run`, `run_async`,
  `_checked`, `_run_checked`, `_call_deferred`, `_open_dir`, `_instance`, `_drive`, `_linker`,
  `_place_stdlib`, `_place_private`, `_place_checked`, `_stamp`, `_real_dir`, `_cache_dir`,
  `_engine`, `_module_miss`, `_private` and `_epoch_ticker._tick`. I read the README's "Running
  it", "Any other embedder" and "Safety" sections, and the existing checks that pass `root=` or
  list the temporary folder. In prior art I read wasmtime `v49.0.3` (`f96eaba`): `crates/wasi/src/p1.rs`,
  `crates/wasi/src/ctx.rs`, `crates/c-api/src/wasi.rs`, `crates/wasi/src/filesystem.rs`,
  `filesystem/unix.rs`, `filesystem/windows.rs`, `primitives/rustix/fs/metadata_ext.rs` and
  `primitives/windows/fs/symlink_unchecked.rs`. I also read the Rust 1.95 standard library
  (`std/src/hash/random.rs`, `core/src/hash/mod.rs`, `std/src/sys/fs/windows.rs`) from the
  local toolchain. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/017-typed-grants.md` as drafted (untracked), against the
  runner at `25f23a7`. Its tracked files match that commit.
- **Ran (EXECUTED, darwin-arm64, macOS 25.5, APFS, host CPython 3.14.2, wasmtime-py 49.0.0,
  `WASI_PYTHON_ARTIFACTS=build/artifacts`, `WASI_PYTHON_CACHE=build/cwasm-cache`).**
  - The repo was not edited, except to write this file.
  - The probes call the runner's own `_run_checked` through the memo's harness (copied, unchanged).
    That harness swaps the runner's one preopen for a list of grants. With `place=False`, nothing
    is put in the root, which is the layout this specification makes.
  - Scripts and outputs are under
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rev017/`:
    - `ident.py` → `ident.txt`: SipHash-1-3 against wasmtime's `ino`, the fd order, the macOS
      firmlinks, a store whose deadline has passed, and a swap of an intermediate component;
    - `inrun.py` → `inrun.txt`: a check module inside the real `_drive`, before the guest, on
      both binaries;
    - `raw_ext.py` → `raw_ext.txt`: the memo's raw preview1 probe plus eighteen more calls;
    - `guest_ext.py`, `py_ext.py` → `py_ext.txt`: more writes through Python, on both binaries;
    - `zip_root.py` → `zip_root.txt`: a root that holds a different `python315.zip`, every
      spelling a guest might use, and links it makes in the root;
    - `existing.py` → `existing.txt`: the first-run guest code of today's `root=` checks, under
      this specification's layout;
    - `hostpath.py` → `hostpath.txt`: the host-path rule on this machine's real paths;
    - `home.py` → `home.txt`: a root together with a caller's grant at `/tmp`.
  - I did not run `uv run pytest`. Nothing is built yet, and the scoreboard is the build
    review's job.
  - The memo's own 7b probe (the check module and the 30-line SipHash) is not in `grants/` or
    `grants2/` (`grants2/` holds two empty folders). So I wrote mine from scratch (finding 14).

## What holds

- **The identity hash is reproduced.** EXECUTED (`ident.txt`). I preopened five folders in two
  orders. For all ten, the `ino` from `fd_filestat_get` equalled SipHash-1-3, with zero keys,
  over `(st_dev, st_ino)` packed as two native-endian u64 words. `dev` was always 1.
  - READ: `DefaultHasher::new()` is `SipHasher13::new_with_keys(0, 0)`
    (`std/src/hash/random.rs:106-107`).
  - READ: `Hash for u64` writes `to_ne_bytes()` (`core/src/hash/mod.rs:380-381`). That is
    native-endian, not little-endian. It is the same thing on every host the project supports.
- **fd order is preopen order.** READ: `Descriptors::new` pushes stdin, stdout and stderr, then
  each preopen in the order `get_directories` returns it (`p1.rs:419-428`). EXECUTED
  (`ident.txt`): preopen *i* was fd 3+*i* in both orders, and `fd_prestat_dir_name` named it.
- **The check module changes nothing the guest sees.** EXECUTED (`inrun.txt`). I instantiated
  the check module in the call's store inside the real `_drive`, before the guest, on both
  binaries.
  - Exit code and stdout were identical with and without it.
  - `fuel_used` stayed within its run-to-run spread. The snapshot gave 87.16 to 87.26 M either
    way, and the plain binary 4,996 to 4,998 M.
  - The module itself spent 69 instructions (`ident.txt`). The runner sets `UNMETERED` before
    and the real cap after the guest's instantiation (`runner.py:582`, `:676`). So spec 008's
    count is not touched, provided the check runs before `set_fuel(fuel)`.
  - READ: the descriptor table belongs to the store's WASI context, not the instance
    (`p1.rs:579-583`). The guest therefore sees the same table the check read.
- **APFS firmlinks give no false refusal.** EXECUTED (`ident.txt`): `/Users` and
  `/System/Volumes/Data/Users` have one `(dev, ino)`, and so do `/tmp` and `/private/tmp`, and
  `/var` and `/private/var`.
- **Read-only is enforced for everything I tried, on both binaries.** EXECUTED
  (`raw_ext.txt`, `py_ext.txt`). The host tree, its bytes and `f.txt`'s mtime were unchanged
  each time.
  - EPERM: `path_filestat_set_times` through an in-grant link, with and without follow;
    `path_open` through that link with TRUNC, or with all rights.
  - EPERM: `path_create_directory`, `path_open(CREAT)` and `fd_filestat_set_times` through a
    subdirectory's descriptor.
  - EPERM from Python: `os.replace` read-only → writable, writable → read-only (a new name or
    over a file), a directory rename out, `os.utime` and `open('w'/'a')` and `os.truncate`
    through a link.
  - Allowed, but nothing changes: `fd_advise` (DONTNEED and WILLNEED), `fd_sync`,
    `fd_datasync` and `posix_fadvise`.
  - `fd_allocate` on a directory gives EBADF. `fd_fdstat_set_flags(SYNC)` gives EINVAL.
  - `mmap` exists in the guest, but `ACCESS_WRITE` and `ACCESS_COPY` both raise `OSError`.
  - `shutil.move` read-only → writable copies the file to the writable side and then fails to
    unlink (EPERM). The read-only side is untouched.
  - `fd_renumber(4, 3)` replaces the read-only preopen's fd with a writable one, after which a
    create "on fd 3" succeeds. It lands in the writable folder. The read-only tree was asserted
    unchanged.
- **Imports always reach the grant, never the root.** EXECUTED (`zip_root.txt`, both binaries).
  The root held a different `python315.zip`, with `email/parser` and `csv` taken out. Even so,
  `email.parser`, `csv` and `statistics` imported from the grant, and `sys.path` was
  `['/usr/local/lib/python315.zip']`.
  - A guest's `email/parser.py`, planted under the root's `usr/old/lib/python3.15/`, never ran.
  - The grant's zip kept its SHA-256.
  - A write by any spelling that reaches the grant is EPERM. Spellings that differ before the
    prefix ends (`/usr/./local/…`, `/usr/local//lib/…`) land in the root as shadows, as memo §2
    says.
- **macOS's usual paths pass the link rule.** EXECUTED (`hostpath.txt`). The only links on the
  way to the temporary folder, the cache and `/tmp` are `/var` and `/tmp`. Both sit in `/`,
  which this user cannot write.
- **The judge's roots sit clear of the runtime's files.** READ: `guest_workdir` is under
  `build/harness/`. That folder is beside `build/artifacts` and `build/cwasm-cache`, not above
  them (`tests/checks/conftest.py:61-65`, `tests/harness/paths.py:31`).
- **§4.4 holds.** INFERRED from READ. The check module is the runner's own, and it imports only
  preview1 calls. The guest binary's imports do not change.

## Acceptance criteria against evidence

1. *The checks exist and were seen failing first.* Each new check can fail before the change.
   But `test_a_swapped_grant_is_refused`, as worded, replaces an expected value through a seam.
   It would pass on the design that finding 1 shows is open.
2. *`uv run pytest` is green with `--accept-judge`.* This cannot be met as written. Today's
   `root=` checks are said to stay unchanged, but at least six of them fail under this layout
   (finding 2).
3. *A dry run of the release workflow passes.* Yes. But the identity is checked only where the
   build job runs, which is macOS (finding 6).
4. *§4.15's exception is removed, and the release review covers this change.* Yes, as worded.

## Findings, most severe first

1. **High. Decision 5 compares the wrong pair, so the swap it exists to catch passes.**
   - What the spec says. The runner opens the grant's path itself with
     `O_NOFOLLOW | O_DIRECTORY`, `fstat`s it, and compares that with what wasmtime opened.
   - Why that fails. `O_NOFOLLOW` covers only the last component. Both opens follow a link
     swapped into an *intermediate* component after Decision 4's walk, so they agree with each
     other.
   - EXECUTED (`ident.txt`, last block):
     1. Decision 4's walk sees `work/a/data` with no link.
     2. A concurrent guest with `work` writable renames `a` and makes `a -> ../secret`. Memo §2
        shows a guest can make such a relative link.
     3. The runner's own open then lands in the secret (`checked dir: False`).
     4. wasmtime's `ino` equals the hash of the runner's `fstat` (`True`), so Decision 5 accepts.
        The grant lists `['key.txt']`.
     5. Compared with the walk's own identity, the swap shows (`False`).
   - Fix:
     - The walk itself must yield the identity. Open each component with
       `openat(dirfd, name, O_NOFOLLOW | O_DIRECTORY)`, following a link only where the rule
       allows it.
     - Keep the final descriptor open until the check module has compared. Holding it also stops
       the inode number being reused.
     - Preopen the resolved path.
     - Compare wasmtime's `ino` with the hash of *that* descriptor's `fstat`.
     - Rewrite the check: through a seam that runs between the walk and `preopen_dir`, rename a
       real intermediate folder and put a relative link in its place. Assert `RuntimeError` and
       a door count of 0.
     - Say in the spec that this ordering is the answer to "check, then open, then preopen": the
       open *is* the check.

2. **High. "The existing checks of `root=` are unchanged and must stay green" is false.** Several
   of them fail under the layout this specification makes.
   - EXECUTED (`existing.txt`). This is today's first-run guest code, with a root at `/` and the
     zip read-only at `/usr/local/lib`:
     - `test_runner_keeps_the_artifact_zip_out_of_the_guests_reach`
       (`test_v1_4_embedding.py:295-307`): the vandal's write is EPERM, so it exits 1 where the
       check wants 0. Its last line also reads the zip from the root, where Decision 2 puts none.
       The new `test_the_zip_is_read_only_and_shared` asserts the opposite.
     - `test_runner_never_follows_a_link_a_guest_left[the zip]` and `[its directory]`
       (`:310-336`): `os.remove` and `os.rename('/usr/local/lib', …)` are EPERM, so both exit 1.
     - `test_runner_replaces_a_directory_left_in_the_zips_place` (`:339-347`): exits 1.
     - `test_planted_code_never_runs`, both binaries (`test_v1_2_hostile_guest.py:105-120`):
       `PLANT`'s `makedirs('/usr/local/lib/python3.15')` is EPERM, so it exits 1.
     - `test_a_call_without_a_root_shares_nothing` (`:157-168`): `listdir('/')` is now
       `['left-behind', 'tmp']`, and the check wants `[… 'usr']`.
   - INFERRED from READ. Three checks list the temporary folder after a call, and each would see
     the new `wasi-python-zip-*` folder and its lock file:
     - the descriptors check expects `[]` (`test_v1_2_hostile_guest.py:378-410`);
     - `CANCEL_ASYNC` filters on `wasi-python` and expects `[]` (`test_v1_4_embedding.py:741,
       782, 796`);
     - `shares_nothing` does too when it is the process's first call, so its result depends on
       test order.
   - Spec 016's own new checks ("the directory then holds nothing") would also see the folder.
   - Fix:
     - List every check that changes. Give each its new assertion and the reason, as a judge
       change under `--accept-judge` (AGENTS rule 4).
     - Keep what each one guards. The guest's write is refused with EPERM, the next call works,
       and nothing outside is written. `PLANT` keeps its `/usr/local/bin` routes and asserts that
       the `/usr/local/lib/python3.X` routes are now refused.
     - Decide what listing checks may see. Either they filter the zip folder by name, or they
       run in a child that sets `tempfile.tempdir` before its first call.
     - Run `test_the_zip_is_read_only_and_shared` in a child process. In the judge's process an
       earlier test has already copied the zip, so the "copied once" counter cannot be read
       there.

3. **Medium-high. Path-string comparisons let a writable root reach the module cache on macOS.**
   - Decision 4 compares resolved paths, with `normcase` only on Windows. APFS is
     case-insensitive by default, and `os.path.realpath` keeps the caller's case.
   - EXECUTED (`hostpath.txt`):
     - `realpath('~/LIBRARY/caches')` returns `/Users/claygendron/LIBRARY/caches`;
     - `~/Library/Caches` and `~/LIBRARY/caches` have the same `(dev, ino)`;
     - `commonpath` of the cache and `~/Library` comes out as `/Users/claygendron`.
   - So `root=Path.home() / "LIBRARY" / "CACHES"` passes the string tests, though it is the
     `.cwasm` cache's parent. A `.cwasm` is native code the next process loads, so this is the
     path §4.15 forbids. Bind mounts on Linux do the same thing by another route (INFERRED).
     The read-only-inside-writable rule has the same weakness.
   - Fix:
     - Compare identities, not strings.
     - For "equal to or above": collect `(st_dev, st_ino)` of each protected folder and every
       ancestor of it. Refuse a writable grant whose identity is in that set.
     - For "inside": walk the grant's own ancestors and refuse if any of them is a protected
       folder. Do the same for read-only inside writable.
     - Add a check on macOS with a case-changed spelling of the cache's parent.
     - Name the residual in the README: a folder reachable by two routes (a bind mount, a mount
       inside a grant) is judged by the route given.

4. **Medium. The shared zip folder's lifecycle is not decided, and spec 016's sweep would never
   remove it.**
   - READ: 016 sweeps `wasi-python-(root-)?[0-9a-f]{16}\.lock` (016 line 96). That does not
     match `wasi-python-zip-<16 hex>.lock`. So, against Decision 2's own words, a killed
     process's copy is never swept.
   - Nothing says the folder is removed when the process exits normally. If it is not, every
     process leaves 11 MB behind.
   - "Once per process" ignores `artifacts=`, which can name a different set on each call.
     Build-time profiles (§2) are separate sets. INFERRED: two sets with different zips in one
     process would get the wrong zip, or re-copy on every switch. The snapshot needs its own
     zip's exact bytes (memo §3).
   - The copy and hash (about 10 ms, memo §5, more on a slow or full disk) would run "under
     `_lock`". READ: the epoch ticker takes `_lock` every round (`runner.py:1502-1503`), and so
     do `_engine`, `_linker` and `stats`. Today's placement uses its own guard.
   - Decision 2's stamp drops `st_ctime_ns`, which today's `_stamp` keeps (`runner.py:1250-1251`).
     A same-user host process can set mtime back, but not ctime.
   - Fix:
     - Key the folder by the zip's digest and version tag: one folder per distinct zip.
     - Add `zip-` to 016's pattern, and keep the folder in the held set.
     - Remove it at exit.
     - Guard the copy with its own lock.
     - Keep ctime in the stamp.

5. **Medium. The Windows exemption rests on a premise that is not true everywhere.**
   - Decision 5 skips the check on Windows because "a guest cannot make a link there". But
     wasmtime 49 makes a guest's link with Rust's `symlink_dir` and `symlink_file`
     (`primitives/windows/fs/symlink_unchecked.rs`). Those pass
     `SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE` (READ, `std/src/sys/fs/windows.rs:1424-1434`).
   - So under Developer Mode, or in an elevated process (GitHub's Windows runners), a guest can
     make links (INFERRED). The repo's own check already says "Windows without the privilege"
     (`test_v1_4_embedding.py:323`).
   - READ: wasmtime hashes `(dwVolumeSerialNumber, 64-bit file index)` on Windows
     (`filesystem/windows.rs:85-91`). CPython's `st_dev`/`st_ino` may match it on NTFS
     (INFERRED, not run).
   - Fix:
     - Try the same comparison on the Windows `verify` job. If it matches, check there too.
     - If it does not, the README names the residual precisely (Developer Mode or elevated), not
       "cannot".
     - Correct the comment at `runner.py:527-529` in the same change.

6. **Medium. The identity is never checked on Linux or Windows.**
   - The unit test lives in `tests/unit/`, and the swap check in a v1.2 file. The `verify` job
     runs only `test_v1_1…`, `test_v1_2_portable_and_sealed`, `test_v1_3…` and `test_v1_4…`
     (`release.yml:194-197`). The build job runs on macOS.
   - The memo ran macOS only. On Linux, wasmtime may take `dev` from `statx`
     (`metadata_ext.rs:136`). That should equal CPython's `st_dev` for every 12-bit major
     (INFERRED), but it has never been run.
   - A mismatch would refuse every call on Linux, loudly, after a release.
   - READ: Rust sign-extends a negative `dev_t` (`metadata_ext.rs:92-104`), so the runner must
     mask `st_dev` to 64 bits before packing.
   - Fix:
     - Add the identity unit test and the swap check to `verify`'s file list, as 016 did for its
       sweep tests.
     - Mask `st_dev & (2**64 - 1)`.
     - Say "native-endian" in Decision 5.

7. **Medium. `HOME` points at a folder that does not exist when there is a root and a grant at
   `/tmp`.**
   - Decision 3 decides `HOME` only for `root=False`. With a root, the runner makes
     `.home-<hex>` in the root's `tmp/`, but the guest's `/tmp` is the grant.
   - EXECUTED (`home.txt`): `HOME=/tmp/.home-2bbb…`, and `os.path.isdir(HOME)` is `False`.
   - Fix:
     - One rule for every root value. A writable grant at `/tmp` holds the fresh `HOME`, made
       and removed through a no-follow directory descriptor as `_call_deferred` does today.
     - A read-only grant at `/tmp` means no `HOME`.
     - Add a check for each case.

8. **Medium. Some existing `root=` values become errors, and the spec says `root` "keeps its
   meaning".**
   - Rule f refuses a writable root at or above any of:
     - the cache: the home folder;
     - the artifact folder: a project folder whose `.venv` holds the wheel, or a source checkout
       holding `build/artifacts`;
     - the temporary folder.
   - INFERRED from READ: "else the wheel's own copy", README "Running it".
   - The spec does not say whether `root` gets Decision 4's link rule and Decision 5's check.
     Memo 7a says `root=` has the same threat. Applying the link rule refuses a user's own link
     in their home folder (`~/data -> /Volumes/…`).
   - These are breaking changes, and §4.15 makes them right. But they must be stated.
   - Fix:
     - Decide whether `root` is walked and post-checked. It should be.
     - CHANGELOG: name the refused values under "changed".
     - README: say which roots are refused.
     - The `ValueError` tells the caller how to grant a link they trust: pass its resolved path.

9. **Low-medium. Without the root's own `usr/local/lib`, `realpath` reaches into a guest's
   files, and `/usr` disappears.**
   - EXECUTED (`zip_root.txt`). In a reused root, a guest renamed `/usr/./local` and linked
     `local -> old`. After that, `os.path.realpath('/usr/local/lib/python315.zip')` returned
     `/usr/old/lib/python315.zip`, a file in the root the guest wrote.
   - So `Path.resolve()` of any path under a grant can lead into the root's files. That matters
     for matplotlib's data grant later. Memo §2 says a shadow is invisible "to every exact
     spelling", but `realpath` is not an exact spelling.
   - EXECUTED (`existing.txt`): in a fresh root, `listdir('/')` loses `usr`. That is a change
     the guest can see, and the spec does not state it.
   - Fix:
     - Keep calling `_real_dir(root, ("usr", "local", "lib"))` before each call, for private and
       `root=` roots. It removes a guest's link, as it does today, and costs one `lstat` per
       component.
     - Add a README fact: `realpath` of a path under a grant consults the root's folders above
       it.

10. **Low. `Grant`'s fields and `root=`'s new value need type rules.**
    - `writable="no"` or `1` would be truthy, and so writable. That breaks "safe by default" by
      a typo.
    - Fix:
      - Require `type(writable) is bool`, and raise `TypeError` for `root=True`.
      - Refuse a `PathLike` whose `__fspath__` gives `bytes`.
      - Turn `grants` into a tuple inside `_checked`, so `run_async` does not hand its worker a
        used-up iterator. Spec 015 passes the checked dict through.

11. **Low. Say where the check module runs, and read the names.**
    - EXECUTED (`ident.txt`): in a store whose epoch deadline has passed, the check module
      traps with `INTERRUPT`. The engine's epoch is shared, so another call's ticker can move it.
      Outside `_drive`, that trap would escape `run` as an exception.
    - Fix:
      - Run the check inside `_drive`, after the "cancelled before the guest ran" test and before
        `linker.instantiate(store, module)` (`runner.py:671-674`). A trap there then reads
        `"deadline"`, and the check runs before `set_fuel(fuel)`.
      - Add `fd_prestat_dir_name` as a third import. Refuse if the count of preopens, or any
        name, differs from what the runner gave.
      - Keep the compiled module with the engine's linker, and clear it in `_release`.

12. **Low. Decision 4's link rule needs exact words.**
    - Say "refused with `ValueError`", not only "resolved without following".
    - A followed link's target is walked component by component under the same rule, with an
      `ELOOP` bound.
    - On Windows a junction counts as a link (`os.path.isjunction`).
    - Use `os.access(…, effective_ids=True)` where `os.supports_effective_ids` has it. Under
      setuid the guest writes as the effective user. EXECUTED: it is available on macOS.
    - Name the scope. A link in a folder that only another user can write (group-writable, or a
      shared folder) is followed. The rule protects against this process's guests, not other
      users' processes (INFERRED).

13. **Low. The read-only check should name the rows it covers.**
    - List the extra rows above in `test_a_read_only_grant_refuses_every_write`:
      - the calls that are allowed but change nothing (`fd_advise`, `fd_sync`, `fd_datasync`);
      - `fd_renumber` of a writable preopen over the read-only one;
      - writes through an in-grant link;
      - writes through a subdirectory's descriptor;
      - `os.replace` both ways.
    - For `shutil.move`, assert only the read-only side, since the writable side gains a copy.

14. **Low. Memo 7b's evidence is not saved (§4.10).**
    - The check module and the SipHash script behind "EXECUTED … 14205808286320391386" are in
      neither `grants/` nor `grants2/`.
    - Fix: save them, or cite this review's `ident.py`.
    - Also tell users in the CHANGELOG that a root's old `usr/local/lib/python315.zip` from
      0.1.0a2 is no longer used or updated, and can be deleted. EXECUTED: imports never read it.

15. **Low. The judge's reference embedder keeps the old contract.**
    - `tests/harness/guest.py` says it does "only what any embedder must do: preopen one
      directory at `/`", and it puts the zip in that writable root (lines 3, 139).
    - After this change, README step 1 says otherwise.
    - Fix: either move the harness to the new step 1 (the zip read-only at `/usr/local/lib`; it
      already takes extra preopens), or state why it keeps the old one and fix its docstring.

## Constitution checks

- **§4.4:** holds (see "What holds").
- **§4.9:** every check named counts something: exit codes, bytes, listings, a counter, a fixed
  seed. None measures time.
- **§4.10:**
  - finding 14;
  - the Linux and Windows identity claims are INFERRED, and should stay labelled so until
    finding 6's job runs.
- **§4.15:** ending the exception is right, and the read-only zip grant is enforced
  (EXECUTED). But "the runtime's own files are never in a writable grant" has a hole by case
  spelling (finding 3), and Decision 5 does not yet close the swap (finding 1).
- **§5.2:** these choices are still undecided:
  - the zip folder's lifetime, sweep, per-zip key and lock (finding 4);
  - `HOME` with a root and a `/tmp` grant (finding 7);
  - whether `root` is walked and post-checked (finding 8);
  - the root's `usr/local/lib` (finding 9).

  Question 24 is open, as the spec says, and this specification needs no answer to it.
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 — Fixed: Decision 4's walk opens each component with `dir_fd` and `O_NOFOLLOW` and
   keeps the final descriptor; Decision 5 compares wasmtime's `ino` with that descriptor's hash,
   so a middle-component swap after the walk is a mismatch. `test_a_swapped_grant_is_refused`
   makes a real swap through a seam at that instant.
2. Finding 2 — Fixed: Decision 8 lists every changed check with its new assertion and what it
   still guards; the listing checks set `tempfile.tempdir` in their child or filter the zip
   folder, each saying which; the zip check runs in a child.
3. Finding 3 — Fixed: every comparison uses `(st_dev, st_ino)` of walked directories and their
   ancestors; a case-changed spelling of the cache's parent is a refusal case.
4. Finding 4 — Fixed: one folder per zip digest per process; 016's `_LOCK_NAME` gains `zip-`; the
   folders are removed at exit; `_zip_lock`; the stamp adds `ctime_ns`, device and inode.
5. Finding 5 — Fixed: the identity check runs on Windows too (`GetFileInformationByHandle` on the
   runner's own `CreateFileW` handle, the identity wasmtime hashes), and the residual is named
   exactly: a party that can make links racing between the walk and that open.
6. Finding 6 — Fixed: `st_dev` is masked to 64 bits and packed native-endian; the identity unit
   test is in `tests/unit/test_runner_grants.py`, which `verify` runs on every OS.
7. Finding 7 — Fixed: Decision 3 makes `HOME` in a writable `/tmp` grant whether or not there is
   a root; `test_home_follows_a_writable_tmp_grant` covers both.
8. Finding 8 — Fixed: `root` is walked and checked like a writable grant, and the post-check
   covers it; the newly refused `root=` values are named, and the CHANGELOG calls it a change.
9. Finding 9 — Taken: the root keeps real `usr/local/lib` folders, with no zip.
10. Finding 10 — Fixed: `writable` must be a `bool`; `root=True` and `bytes` paths are refused;
    `grants` becomes a tuple in `_checked`.
11. Finding 11 — Fixed: the check module runs inside `_drive` before the guest; a passed
    deadline is reported as `"deadline"`; `fd_prestat_dir_name` confirms each name.
12. Finding 12 — Fixed: `ValueError`, link targets walked by the same rule (at most 40), junctions
    are links, `effective_ids=True` where supported, and the scope (other users' links are
    followed) is stated.
13. Finding 13 — Fixed: the read-only check gains your rows.
14. Finding 14 — Fixed: the 7b probe and its output are in
    `context/research/2026-10-17-typed-grants/`; the CHANGELOG says an old zip in a root may be
    deleted.
15. Finding 15 — Fixed: `tests/harness/guest.py` follows the new contract and says so.

## Verdict

**Revise.** The design is sound: grants, the read-only zip, and an identity check after the
preopen. But Decision 5 as written accepts the swap it is meant to refuse (finding 1). The spec
also promises a judge that cannot stay green (finding 2), and leaves several choices undecided
(findings 4, 7, 8 and 9).

## Confirmation

- **Date:** 2026-10-17. **Reviewer:** the same fresh agent. I read the revised specification in
  full (untracked, 227 lines), the dispositions above, and the saved probe
  `context/research/2026-10-17-typed-grants/identity_probe.py` with its output. The new probes
  are in the same scratch folder (`rev017/`):
  - `walk.py` → `walk.txt`: a stand-in for Decision 4's walk, worded as the spec words it
    (`dir_fd`, `O_NOFOLLOW`, `faccessat` on the held parent with effective ids, link targets
    under the same rule, at most 40 links), and Decision 5's comparison against the walk's own
    descriptor;
  - `harness_fuel.py` → `harness_fuel.txt`: the judge's seeded harness with the zip in the root,
    then in a read-only preopen at `/usr/local/lib`, as Decision 6 makes it.
  - I did not run `uv run pytest`. Nothing is built yet.

### What the revision closes

- **Finding 1 is closed.** EXECUTED (`walk.txt`):
  - I swapped a middle component after the walk (`a` renamed, `a -> ../outside` in its place).
    wasmtime then opened the outside folder (`['key.txt']`), and the walk descriptor's hash did
    not equal wasmtime's `ino`. So the call is refused.
  - The same swap made *inside* the walk, between one component's `lstat` and its open, was
    refused by `O_NOFOLLOW`. On macOS it fails with `ENOTDIR`, not `ELOOP`. So an
    implementation must tell a link apart by `lstat`, not by the error.
  - An unswapped grant matched.
  - Memo 7a's reproducer was refused.
  - The temporary folder, `/tmp` and `~/Library/Caches` all walked, and their final identities
    equalled `os.stat`'s. Each followed only `/var` or `/tmp`, which sit in `/`, a folder this
    user cannot write.
  - READ, Python 3.14.2: `os.access` is in both `os.supports_dir_fd` and
    `os.supports_effective_ids` here. So `os.access(".", W_OK, dir_fd=parent,
    effective_ids=True)` asks about the held parent, not a path that could change.
- **Finding 3 is closed.** EXECUTED (`walk.txt`): `~/LIBRARY/CACHES` walked to an identity that
  is among the module cache's ancestors, where the string test said it was not. One condition
  applies (C1).
- **Findings 2, 4 and 6 to 15** are taken as dispositioned, except where C3 to C5 below say
  otherwise.
- **Finding 5 is taken, with a residual that is now named honestly.**
  - READ: wasmtime hashes `(dwVolumeSerialNumber, file index)` (`filesystem/windows.rs:85-91`),
    and the runner computes the same from `GetFileInformationByHandle`. The `verify` job runs it
    on Windows. Not run here.
  - Note for the build (INFERRED): Windows has no `dir_fd`, so the Windows walk is by path, and
    `CreateFileW` follows reparse points in middle components. The window between the walk and
    that open is exactly the residual the spec names.
  - It could be closed. After `CreateFileW`, compare `GetFinalPathNameByHandleW` of the handle
    with the walked path. A middle component swapped into a junction or link resolves somewhere
    else, and the guest cannot rename a folder outside its grants into place. That is optional,
    since the residual is stated.
  - Two wording points:
    - `CreateFileW` returns a handle, so `msvcrt.get_osfhandle` has no part in it.
    - The handle should share read, write and delete, and be closed before a private root is
      removed.
  - READ, CPython `Modules/posixmodule.c:3357-3368`: on Windows, `os.access(dir, W_OK)` is always
    true for a directory. So on Windows *every* link and junction on a host path is refused. The
    "the system's links are followed" sentence holds only on POSIX, and the README should say so.

### Conditions left (each one sentence or two in the spec)

1. **C1 (medium): the runtime's files may not exist yet when the checks run.**
   - On a first run, the module cache does not exist until `_module` makes it. The zip folder
     does not exist until the first call makes it. Both happen after the checks "before any
     work".
   - EXECUTED (`walk.txt`): a walk of a cache path that is not there yet fails with
     `FileNotFoundError`.
   - If an implementation skips a missing protected folder, `root=Path.home()` passes on a fresh
     machine. The runner then makes the `.cwasm` cache inside a writable root, and the next
     process loads native code a guest may have written. That is the path §4.15 forbids.
   - Fix: each protected folder's chain starts at its deepest *existing* ancestor. For a zip
     folder not made yet, that is the temporary folder.
   - Also: protected folders' chains follow every link, and are never refused by the grant
     rule. A cache reached through a user's own link, or a Linux venv's `lib64 -> lib`, must not
     make `run` raise.
2. **C2 (medium): the judge's fuel grows past the ratchet's tolerance, and the acceptance
   criteria do not say so.**
   - EXECUTED (`harness_fuel.txt`). The harness repeats fuel exactly, run to run. Moving the zip
     to its own preopen grows it:
     - snapshot, `import email.parser, json, statistics`: +0.020%;
     - plain binary, pandas: +0.0135%;
     - plain binary, `email+json`: +0.0070%;
     - plain binary, `print`: +0.0031%;
     - snapshot, `print` and pandas: 0.
   - The tolerance is 0.01% (`tests/harness/scoreboard.py:31`), so at least two harness checks
     turn red as "grew".
   - Fix: acceptance criterion 2 says `--accept-judge "…" --accept-growth "the zip is a separate
     preopen: wasi-libc compares one more prefix per path lookup"`, with the figures in the
     landing notes.
3. **C3 (medium): two changed checks lose what they guard.** AGENTS rule 4 says never weaken the
   judge.
   - EXECUTED (`zip_root.txt`): a guest still reaches the root's own `usr/local/lib` through the
     spellings `/usr/./local/…` and `/usr/local//lib/…`. It can rename it, link it
     (`local -> old`), and plant `python3.15/email/parser.py` there.
   - So the runner's `_real_dir` (Decision 2 keeps it) still meets guest-made links each call.
     And planted code in the root still exists to be refused.
   - Asserting only "the write to `/usr/local/lib…` is EPERM" drops both guards. That applies to
     `test_runner_never_follows_a_link_a_guest_left[the zip]` / `[its directory]` and to
     `test_planted_code_never_runs`.
   - Fix: keep the EPERM assertions, and *also* plant through `/usr/./local/…`:
     - a link to `outside` in place of the root's `usr/local/lib` or `usr/local`, after which the
       next call works and `outside` stays empty;
     - the `python3.X` modules and `.pth` files under the root's shadow, which never import or
       run.
4. **C4 (low): one more check changes.** `tests/unit/test_guest.py::test_cpython_sees_only_its_root`
   asserts that `/` lists `['data', 'usr']`. It runs here: `build/brett-3.14.7/python.wasm` is
   present (EXECUTED). Once the harness grants the stdlib apart from its root, `/` lists
   `['data']` (INFERRED from `existing.txt`'s fresh-root listing).
   - Fix: the harness makes real `usr/local/lib` folders in its root, as the runner does, or
     Decision 8 lists this check.
   - The harness must also grant a stdlib *directory* (the reference build's `lib/python3.14`),
     not only a zip.
5. **C5 (low): a `root=` that does not exist yet.**
   - Today `_real_dir` creates it (`root.mkdir(parents=True, exist_ok=True)`, READ). The walk
     refuses it (EXECUTED: `FileNotFoundError`).
   - Fix: decide which. Either refuse it with `ValueError` and list that among the changed
     `root=` values in the CHANGELOG, or create only the missing tail through the walk's
     descriptors.
6. **C6 (low): name the mount residual from finding 3.** A folder reachable by two routes (a
   bind mount, or a mount inside a grant) is judged by the route given. Add that to the README
   facts in Decision 7.

### Verdict

**Revise again.** The two hard parts are confirmed by running them. The walk's descriptor
catches a middle-component swap, and identity comparison catches a case-changed spelling. What
is left is C1 to C3: one sentence in Decision 4 (deepest existing ancestor), one in the
acceptance criteria (`--accept-growth`, with its reason), and two changed checks that must keep
planting through the root. With those, and C4 to C6, the spec is ready to build. These edits do
not need another full review: the author can record them in the Disposition, and a check of
those lines confirms them.

## Disposition of the confirmation (filled in by the author)

- C1 — Fixed: a protected folder's chain starts at its deepest existing ancestor (the temporary
  folder for the zip folder), following every link, and its walk never refuses; so
  `root=Path.home()` is refused on a fresh machine.
- C2 — Fixed: acceptance criterion 2 now names `--accept-growth` with your measured reason.
- C3 — Fixed: both changed checks also plant through `/usr/./local/lib` and assert the links are
  never followed, `outside` stays empty, and the planted code never runs.
- C4 — Fixed: the harness keeps real `usr/local/lib` folders in its root and grants the stdlib
  (a zip, or the reference build's directory) by its own read-only preopen;
  `test_cpython_sees_only_its_root` stays unchanged, and Decision 8 says why.
- C5 — Decided: a missing root is still made, as today, but through the walk (deepest existing
  ancestor walked, each missing component made with `mkdir(dir_fd=…)` and walked); a grant's host
  path must exist. The CHANGELOG says so.
- C6 — Fixed: the README names the two-routes residual (bind mounts, a share mounted twice).
- Also taken: links are recognised by `lstat` (macOS gives `ENOTDIR`); on Windows every link and
  junction is refused, and the README does not claim otherwise; the optional
  `GetFinalPathNameByHandleW` comparison is taken, which closes the Windows residual, so it is no
  longer named; `msvcrt.get_osfhandle` is dropped.

## Second confirmation

- **Date:** 2026-10-17. **Reviewed:** `git show 690a1ee -- context/specifications/017-typed-grants.md`
  against conditions C1 to C6 and the dispositions above. No new probes were run. The labels
  below say where each claim comes from.
- **Met:**
  - **C1**: the deepest existing ancestor, following every link, and a protected walk that
    never refuses. This is the shape `walk.txt` exercised.
  - **C2**: `--accept-growth`, with the measured reason.
  - **C3**: both changed checks also plant through `/usr/./local/lib`.
  - **C4**: the harness keeps `usr/local/lib`, and grants a zip or a stdlib directory.
  - **C6**: the two-routes fact is in the README.
  - Recognising a link by `lstat`, and refusing every link on Windows.
- **Two lines still need a change.**
  1. **The Windows path comparison would refuse correct grants (medium).** Decision 5 requires
     `GetFinalPathNameByHandleW` of the handle to equal the walked path "after
     `os.path.normcase`". The final path is not spelled the way the walk spelled it:
     - It starts with `\\?\`, or `\\?\UNC\` for a share. READ: `ntpath.realpath` strips both
       (CPython `Lib/ntpath.py:674-690`). `normcase` does not.
     - It expands 8.3 short names. READ: `tempfile` only `abspath`s `%TEMP%`
       (`Lib/tempfile.py:200, 246`). INFERRED: GitHub's Windows runners set `%TEMP%` to
       `C:\Users\RUNNER~1\AppData\Local\Temp`. If so, every private root, and every grant under
       the temporary folder, fails the comparison there. `verify` would catch it, but only as a
       failed release dry run (criterion 3).
     - It resolves `subst` drives, and gives a mapped drive as `\\?\UNC\…` (INFERRED).
     - Fix, one of:
       - **(a)** Compare two paths made by the same function. During the walk, open each
         component with `CreateFileW(… FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT)`,
         and refuse one whose attributes carry `FILE_ATTRIBUTE_REPARSE_POINT`. Record
         `GetFinalPathNameByHandleW` of the last component's handle as the expected path. Then
         require the later handle, the one the identity is read from, to give that same final
         path. Never compare it with the string the caller passed.
       - **(b), simpler and stronger:** hold each walked component's handle with share read and
         write but **not** delete until the check module has compared. INFERRED from Windows
         sharing rules: no held directory can then be renamed or replaced, so the path wasmtime
         opens is the walked one, and no path string is compared at all. The handles are closed
         before a private root is removed.

       Either way, add a Windows case to `test_runner_grants.py` with a grant under the runner's
       real temporary folder, so `verify` runs it.
  2. **A missing root's rules must be decided before any `mkdir` (low).** The spec says how a
     missing root is made (C5), but not when Decision 4's rules run.
     - If an implementation makes the folders first, a refused root leaves them behind. That is
       work before the refusal, which specs 013 and 014 forbid.
     - If it judges the new root by its deepest existing ancestor's identity, then
       `root=~/newproj` is "above" the module cache and is refused by mistake.
     - Fix, one sentence: the rules are decided on the existing chain before any `mkdir`. A root
       still to be made is inside whatever its deepest existing ancestor is inside. It is above
       nothing, since a folder not yet made holds nothing.

### Verdict

**Revise again, by these two sentences only.** Everything else is ready to build. Once Decision 5's
Windows bullet takes (a) or (b) and Decision 4's root bullet says the rules come before any
`mkdir`, the specification is ready to build without another review. The author records the two
edits in the Disposition, and that record is the confirmation.

## Disposition of the second confirmation (filled in by the author)

1. Taken (b): on Windows the walk opens every component with `CreateFileW` (backup semantics,
   reparse points opened, not followed, and refused), holding each handle without
   `FILE_SHARE_DELETE` until the comparison; no path string is compared. The identity unit test
   gains a Windows grant under the real temporary folder.
2. Fixed: a missing root's rules are decided on its existing chain first; a root still to be made
   is inside what its deepest existing ancestor is inside and above nothing; a refused root makes
   no folder.

Your verdict made the spec ready to build once these two lines changed.
